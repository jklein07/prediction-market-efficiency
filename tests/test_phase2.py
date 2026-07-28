"""Synthetic-data tests for the R-2 jump detector and R-3 maker-fill
simulator. Both engines are SQL-heavy; a silent join or ordering bug would
produce confident nonsense, so every behavior is pinned on toy markets."""

import unittest
from datetime import datetime, timedelta, timezone

import duckdb

from analysis.jumps import jump_drift_stats
from analysis.maker import maker_sim

T0 = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)


def _con():
    con = duckdb.connect(":memory:")
    con.execute("""
        CREATE TABLE kalshi_settled (
            ticker TEXT, event_ticker TEXT, result TEXT, close_time TIMESTAMPTZ,
            volume DOUBLE);
        CREATE TABLE kalshi_events (event_ticker TEXT, category TEXT);
        CREATE TABLE kalshi_series (series_ticker TEXT, category TEXT);
        CREATE TABLE kalshi_candles (
            ticker TEXT, period_minutes INT, end_ts TIMESTAMPTZ,
            yes_bid DOUBLE, yes_ask DOUBLE, trade_price DOUBLE,
            volume DOUBLE, open_interest DOUBLE);
        CREATE TABLE calibration_obs (
            ticker TEXT, h_min INT, yes_bid DOUBLE, yes_ask DOUBLE,
            mid DOUBLE, spread DOUBLE, outcome INT, category TEXT,
            event_ticker TEXT, volume DOUBLE, close_time TIMESTAMPTZ,
            life_hours DOUBLE);
    """)
    return con


def _add_market(con, ticker, result, close_h, category="Mentions"):
    con.execute("INSERT INTO kalshi_settled VALUES (?,?,?,?,?)",
                [ticker, f"{ticker.split('-')[0]}-EV", result,
                 T0 + timedelta(hours=close_h), 100.0])
    con.execute("INSERT INTO kalshi_series VALUES (?,?)",
                [ticker.split("-")[0], category])


def _candle(con, ticker, hours, bid, ask, trade, vol, period=60):
    con.execute("INSERT INTO kalshi_candles VALUES (?,?,?,?,?,?,?,?)",
                [ticker, period, T0 + timedelta(hours=hours),
                 bid, ask, trade, vol, 0.0])


class TestJumpDetection(unittest.TestCase):
    def test_upward_jump_detected_and_entered_next_candle(self):
        con = _con()
        _add_market(con, "KXM-A", "yes", close_h=10)
        # flat, then +10c trade jump confirmed by mid, then entry candle
        _candle(con, "KXM-A", 0, 0.28, 0.32, 0.30, 5)
        _candle(con, "KXM-A", 1, 0.38, 0.42, 0.40, 5)   # jump candle
        _candle(con, "KXM-A", 2, 0.40, 0.44, 0.41, 2)   # entry candle
        stats = jump_drift_stats(con)
        self.assertEqual(len(stats), 1)
        s = stats[0]
        self.assertEqual((s.label, s.direction, s.n), ("Mentions", "up", 1))
        # buy YES at entry ask 0.44, resolves yes: EV = 1-0.44-fee(0.44)=0.54
        self.assertAlmostEqual(s.ev, 1 - 0.44 - 0.02, places=6)
        self.assertEqual(s.win_rate, 1.0)

    def test_quote_only_jump_is_ignored(self):
        con = _con()
        _add_market(con, "KXM-B", "no", close_h=10)
        _candle(con, "KXM-B", 0, 0.28, 0.32, 0.30, 5)
        _candle(con, "KXM-B", 1, 0.38, 0.42, 0.40, 0)   # no volume -> not a jump
        _candle(con, "KXM-B", 2, 0.40, 0.44, 0.41, 2)
        self.assertEqual(jump_drift_stats(con), [])

    def test_unconfirmed_jump_is_ignored(self):
        con = _con()
        _add_market(con, "KXM-C", "no", close_h=10)
        _candle(con, "KXM-C", 0, 0.28, 0.32, 0.30, 5)
        _candle(con, "KXM-C", 1, 0.29, 0.33, 0.40, 5)   # trade jump, mid flat
        _candle(con, "KXM-C", 2, 0.40, 0.44, 0.41, 2)
        self.assertEqual(jump_drift_stats(con), [])

    def test_jump_too_close_to_close_is_excluded(self):
        con = _con()
        _add_market(con, "KXM-D", "yes", close_h=2.5)   # jump at h=1, close 2.5
        _candle(con, "KXM-D", 0, 0.28, 0.32, 0.30, 5)
        _candle(con, "KXM-D", 1, 0.38, 0.42, 0.40, 5)   # 1.5h to close < 2h min
        _candle(con, "KXM-D", 2, 0.40, 0.44, 0.41, 2)
        self.assertEqual(jump_drift_stats(con), [])

    def test_downward_jump_buys_no(self):
        con = _con()
        _add_market(con, "KXM-E", "no", close_h=10)
        _candle(con, "KXM-E", 0, 0.48, 0.52, 0.50, 5)
        _candle(con, "KXM-E", 1, 0.38, 0.42, 0.40, 5)
        _candle(con, "KXM-E", 2, 0.36, 0.40, 0.38, 2)   # entry: NO at 1-0.36=0.64
        s = jump_drift_stats(con)[0]
        self.assertEqual(s.direction, "down")
        self.assertAlmostEqual(s.ev, 1 - 0.64 - 0.02, places=6)

    def test_only_first_jump_per_market_counts(self):
        con = _con()
        _add_market(con, "KXM-F", "yes", close_h=20)
        _candle(con, "KXM-F", 0, 0.28, 0.32, 0.30, 5)
        _candle(con, "KXM-F", 1, 0.38, 0.42, 0.40, 5)   # jump 1
        _candle(con, "KXM-F", 2, 0.40, 0.44, 0.41, 2)
        _candle(con, "KXM-F", 3, 0.50, 0.54, 0.52, 5)   # jump 2 (ignored)
        _candle(con, "KXM-F", 4, 0.52, 0.56, 0.53, 2)
        stats = jump_drift_stats(con)
        self.assertEqual(sum(s.n for s in stats), 1)


class TestMakerSim(unittest.TestCase):
    def _obs(self, con, ticker, bid, ask, outcome, close_h=1.0):
        close = T0 + timedelta(hours=close_h)
        con.execute("INSERT INTO calibration_obs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    [ticker, 60, bid, ask, (bid + ask) / 2, ask - bid, outcome,
                     "Sports", f"{ticker.split('-')[0]}-EV", 100.0, close, 3.0])
        con.execute("INSERT INTO kalshi_settled VALUES (?,?,?,?,?)",
                    [ticker, f"{ticker.split('-')[0]}-EV",
                     "yes" if outcome else "no", close, 100.0])

    def test_strict_fill_requires_trade_through(self):
        con = _con()
        self._obs(con, "KXG-A", 0.79, 0.81, 1)
        # level = 0.80; trades at exactly 0.80 after the mark
        _candle(con, "KXG-A", 0.5, 0.78, 0.82, 0.80, 3, period=1)
        strict = maker_sim(con, ["KXG"], strict=True)
        loose = maker_sim(con, ["KXG"], strict=False)
        self.assertEqual((strict.orders, strict.fills), (1, 0))
        self.assertEqual((loose.orders, loose.fills), (1, 1))
        # loose fill: bought YES at 0.80, resolved yes, no maker fee
        self.assertAlmostEqual(loose.ev_per_fill, 0.20, places=6)

    def test_strict_fill_on_trade_through(self):
        con = _con()
        self._obs(con, "KXG-B", 0.79, 0.81, 0)
        _candle(con, "KXG-B", 0.5, 0.75, 0.79, 0.77, 3, period=1)  # through 0.80
        r = maker_sim(con, ["KXG"], strict=True)
        self.assertEqual(r.fills, 1)
        # bought YES at 0.80, resolved no: EV = -0.80
        self.assertAlmostEqual(r.ev_per_fill, -0.80, places=6)

    def test_no_candles_after_mark_means_no_fill(self):
        con = _con()
        self._obs(con, "KXG-C", 0.79, 0.81, 1)
        # only candle is before the h=60m mark (i.e. > 60m before close)
        _candle(con, "KXG-C", -0.5, 0.70, 0.74, 0.72, 3, period=1)
        r = maker_sim(con, ["KXG"], strict=True)
        self.assertEqual((r.orders, r.fills), (1, 0))

    def test_mid_range_filter(self):
        con = _con()
        self._obs(con, "KXG-D", 0.40, 0.44, 1)  # mid 0.42, outside favorites band
        _candle(con, "KXG-D", 0.5, 0.30, 0.34, 0.32, 3, period=1)
        r = maker_sim(con, ["KXG"])
        self.assertEqual(r.orders, 0)


if __name__ == "__main__":
    unittest.main()
