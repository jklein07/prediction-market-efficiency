"""Synthetic-data tests for the Phase-1 momentum / mean-reversion engine.

The stratification here is the whole result: a contract lands in a price
region and a direction bucket, and an off-by-one in either boundary silently
moves observations between cells that are then compared against each other.
The self-join across two horizons is the other hazard — it applies the
spread filter twice, once per horizon, which is a real sample restriction
and is pinned below rather than assumed.
"""

import unittest
from datetime import datetime, timezone

import duckdb

from analysis.behavior import DELTA_THRESHOLD, momentum_stats
from analysis.calibration import mde_mean
from analysis.fees import taker_fee_per_contract

T0 = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)
H_FAR, H_NEAR = 1440, 360


def _con():
    con = duckdb.connect(":memory:")
    con.execute("""
        CREATE TABLE calibration_obs (
            ticker TEXT, h_min INT, yes_bid DOUBLE, yes_ask DOUBLE,
            mid DOUBLE, spread DOUBLE, outcome INT, category TEXT,
            event_ticker TEXT, volume DOUBLE, close_time TIMESTAMPTZ,
            life_hours DOUBLE);
    """)
    return con


def _pair(con, ticker, far_mid, near_bid, near_ask, outcome,
          far_spread=0.02, category="Sports"):
    """One contract observed at both horizons."""
    rows = [
        (H_FAR, far_mid - far_spread / 2, far_mid + far_spread / 2,
         far_mid, far_spread),
        (H_NEAR, near_bid, near_ask,
         (near_bid + near_ask) / 2, near_ask - near_bid),
    ]
    for h, bid, ask, mid, spread in rows:
        con.execute(
            "INSERT INTO calibration_obs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            [ticker, h, bid, ask, mid, spread, outcome, category,
             f"{ticker.split('-')[0]}-EV", 100.0, T0, 48.0])


def _only(stats):
    assert len(stats) == 1, f"expected one cell, got {len(stats)}"
    return stats[0]


class TestDirectionStratification(unittest.TestCase):
    def test_upward_move_prices_the_with_move_trade_as_buy_yes(self):
        con = _con()
        _pair(con, "KXB-A", 0.40, 0.48, 0.52, outcome=1)
        s = _only(momentum_stats(con, H_FAR, H_NEAR))
        self.assertEqual((s.region, s.direction, s.n), ((0.35, 0.65), "up", 1))
        self.assertAlmostEqual(s.mean_mid, 0.50, places=9)
        self.assertEqual(s.yes_rate, 1.0)
        self.assertAlmostEqual(s.gap, 0.50, places=9)
        # with-move = buy YES at the ask; fade = buy NO at 1 - bid
        fee = taker_fee_per_contract(0.52, 1)
        self.assertAlmostEqual(s.ev_with_move, (1 - 0.52) - fee, places=9)
        self.assertAlmostEqual(s.ev_against_move, (0 - 0.52) - fee, places=9)

    def test_downward_move_prices_the_with_move_trade_as_buy_no(self):
        con = _con()
        _pair(con, "KXB-B", 0.60, 0.48, 0.52, outcome=0)
        s = _only(momentum_stats(con, H_FAR, H_NEAR))
        self.assertEqual(s.direction, "down")
        # NO costs 1 - bid = 0.52 and pays 1 when the outcome is no
        fee = taker_fee_per_contract(1 - 0.48, 1)
        self.assertAlmostEqual(s.ev_with_move, (1 - 0.52) - fee, places=9)

    def test_delta_threshold_boundaries_are_inclusive_at_the_edge(self):
        for far_mid, expected in ((0.47, "up"), (0.48, "flat"), (0.53, "down")):
            with self.subTest(far_mid=far_mid):
                con = _con()
                _pair(con, "KXB-C", far_mid, 0.48, 0.52, outcome=1)
                self.assertEqual(_only(momentum_stats(con, H_FAR, H_NEAR)).direction,
                                 expected)
        self.assertEqual(DELTA_THRESHOLD, 0.03)


class TestSampleRestrictions(unittest.TestCase):
    def test_spread_filter_applies_at_both_horizons(self):
        # near book is tight; the far book is not. The pair is still dropped.
        con = _con()
        _pair(con, "KXB-D", 0.40, 0.48, 0.52, outcome=1, far_spread=0.20)
        self.assertEqual(momentum_stats(con, H_FAR, H_NEAR), [])

        con = _con()
        _pair(con, "KXB-E", 0.40, 0.30, 0.70, outcome=1)   # near spread 0.40
        self.assertEqual(momentum_stats(con, H_FAR, H_NEAR), [])

    def test_contract_priced_at_only_one_horizon_is_dropped(self):
        con = _con()
        con.execute(
            "INSERT INTO calibration_obs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            ["KXB-F", H_NEAR, 0.48, 0.52, 0.50, 0.04, 1, "Sports",
             "KXB-EV", 100.0, T0, 48.0])
        self.assertEqual(momentum_stats(con, H_FAR, H_NEAR), [])

    def test_price_regions_are_half_open_and_exclude_the_tails(self):
        cases = [(0.05, (0.05, 0.35)), (0.35, (0.35, 0.65)),
                 (0.65, (0.65, 0.95)), (0.04, None), (0.95, None)]
        for near_mid, expected in cases:
            with self.subTest(near_mid=near_mid):
                con = _con()
                _pair(con, "KXB-G", near_mid - 0.10,
                      near_mid - 0.01, near_mid + 0.01, outcome=1)
                stats = momentum_stats(con, H_FAR, H_NEAR)
                if expected is None:
                    self.assertEqual(stats, [])
                else:
                    self.assertEqual(_only(stats).region, expected)

    def test_series_filter_selects_on_the_ticker_prefix(self):
        con = _con()
        _pair(con, "KXNBA-A", 0.40, 0.48, 0.52, outcome=1)
        _pair(con, "KXNFL-A", 0.40, 0.48, 0.52, outcome=1)
        self.assertEqual(_only(momentum_stats(con, H_FAR, H_NEAR)).n, 2)
        # the filter matches the series prefix of event_ticker, not the whole
        # ticker: "KXNBA-EV" is selected by "KXNBA"
        self.assertEqual(
            _only(momentum_stats(con, H_FAR, H_NEAR, series=["KXNBA"])).n, 1)
        self.assertEqual(momentum_stats(con, H_FAR, H_NEAR, series=["KXNBA-EV"]), [])


class TestReportedStatistics(unittest.TestCase):
    def test_gap_and_rate_aggregate_over_the_cell(self):
        con = _con()
        for i, outcome in enumerate([1, 1, 1, 0]):
            _pair(con, f"KXB-H{i}", 0.40, 0.48, 0.52, outcome=outcome)
        s = _only(momentum_stats(con, H_FAR, H_NEAR))
        self.assertEqual((s.n, s.yes_rate), (4, 0.75))
        self.assertAlmostEqual(s.gap, 0.75 - 0.50, places=9)
        self.assertLess(s.ci_lo, 0.75)
        self.assertGreater(s.ci_hi, 0.75)

    def test_mde_does_not_depend_on_which_side_is_priced(self):
        """The MDE is computed from the buy-YES EV series for every cell,
        including down-move cells whose with-move trade is buy-NO. That is
        not a leak: at fixed quotes the two series differ by a sign and a
        constant, so their dispersion — and the MDE — is identical."""
        con = _con()
        for i, outcome in enumerate([1, 0, 1, 0, 1]):
            _pair(con, f"KXB-I{i}", 0.60, 0.48, 0.52, outcome=outcome)
        s = _only(momentum_stats(con, H_FAR, H_NEAR))
        self.assertEqual(s.direction, "down")
        fee_no = taker_fee_per_contract(1 - 0.48, 1)
        evs_no = [((1 - o) - 0.52) - fee_no for o in (1, 0, 1, 0, 1)]
        self.assertAlmostEqual(s.mde, mde_mean(evs_no), places=9)
        self.assertGreater(s.mde, 0.0)


if __name__ == "__main__":
    unittest.main()
