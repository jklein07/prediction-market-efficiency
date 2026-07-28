"""Fee math is the platform's most safety-critical code: a wrong sign or a
missing ceil here silently converts losing trades into 'opportunities'."""

import unittest

from analysis.fees import (
    breakeven_edge,
    fee_rate_for_ticker,
    maker_fee,
    net_ev_buy_no,
    net_ev_buy_yes,
    taker_fee,
    taker_fee_per_contract,
)


class TestFeeSchedule(unittest.TestCase):
    """Known values from the 2026-02-05 fee schedule PDF (per-ORDER fees)."""

    def test_published_table_values(self):
        self.assertAlmostEqual(taker_fee(0.50, 100), 1.75)   # 100 @ $0.50
        self.assertAlmostEqual(taker_fee(0.90, 100), 0.63)   # 100 @ $0.90
        self.assertAlmostEqual(taker_fee(0.05, 100), 0.34)   # 100 @ $0.05 (ceil 0.3325)

    def test_per_order_vs_per_contract_divergence(self):
        # At P=0.90 the raw single-contract fee is $0.0063: rounding-up makes
        # 1 contract pay 1.00c/contract while 100 pay 0.63c/contract.
        self.assertAlmostEqual(taker_fee_per_contract(0.90, 1), 0.01)
        self.assertAlmostEqual(taker_fee_per_contract(0.90, 100), 0.0063)
        # At P=0.50 the raw fee exceeds a cent, so sizes barely differ.
        self.assertAlmostEqual(taker_fee_per_contract(0.50, 1), 0.02)
        self.assertAlmostEqual(taker_fee_per_contract(0.50, 100), 0.0175)
        for p in (0.05, 0.10, 0.50, 0.90, 0.95):
            for c in (1, 10, 100, 1000):
                per = taker_fee_per_contract(p, c)
                self.assertLessEqual(per, taker_fee_per_contract(p, 1) + 1e-12)
                self.assertGreaterEqual(per, 0.07 * p * (1 - p) - 1e-12)

    def test_index_rate_by_ticker(self):
        for t in ("KXINX-26JUL27-B6000", "KXINXU-26JUL27", "KXNASDAQ100-X",
                  "KXNASDAQDUD-26", "INXD-OLD"):
            self.assertEqual(fee_rate_for_ticker(t), 0.035)
        for t in ("KXBTCD-26JUL0821-T53599.99", "KXPRESNOMD-28-AOC", None, ""):
            self.assertEqual(fee_rate_for_ticker(t), 0.07)
        # index rate feeds through: 100 @ $0.50 at half rate = $0.875 -> ceil $0.88
        self.assertAlmostEqual(taker_fee(0.50, 100, rate=0.035), 0.88)

    def test_maker_fee_quarter_rate(self):
        # 0.0175 * 100 * 0.25 = $0.4375 -> ceil $0.44
        self.assertAlmostEqual(maker_fee(0.50, 100), 0.44)
        self.assertAlmostEqual(maker_fee(0.50, 1), 0.01)


class TestTakerFee(unittest.TestCase):
    def test_midpoint_fee_matches_published_schedule(self):
        # 0.07 * 0.5 * 0.5 = $0.0175 -> ceil to $0.02
        self.assertEqual(taker_fee(0.50), 0.02)

    def test_longshot_fee(self):
        # 0.07 * 0.05 * 0.95 = $0.003325 -> ceil to $0.01
        self.assertEqual(taker_fee(0.05), 0.01)

    def test_scales_with_contracts_before_rounding(self):
        # 100 * 0.0175 = $1.75 exactly; no rounding artifact
        self.assertEqual(taker_fee(0.50, 100), 1.75)

    def test_degenerate_prices_free(self):
        self.assertEqual(taker_fee(0.0), 0.0)
        self.assertEqual(taker_fee(1.0), 0.0)


class TestNetEV(unittest.TestCase):
    def test_fair_priced_market_is_negative_ev(self):
        self.assertLess(net_ev_buy_yes(0.50, 0.50), 0.0)
        self.assertLess(net_ev_buy_no(0.50, 0.50), 0.0)

    def test_edge_must_exceed_fee(self):
        # 1c edge at midpoint: gross +0.01, fee 0.02 -> net negative
        self.assertLess(net_ev_buy_yes(0.51, 0.50), 0.0)
        # 5c edge: gross +0.05, fee 0.02 -> net +0.03
        self.assertAlmostEqual(net_ev_buy_yes(0.55, 0.50), 0.03)

    def test_no_side_symmetry(self):
        self.assertAlmostEqual(net_ev_buy_no(0.45, 0.50), 0.03)

    def test_breakeven_edge_equals_fee(self):
        self.assertEqual(breakeven_edge(0.50), 0.02)


if __name__ == "__main__":
    unittest.main()
