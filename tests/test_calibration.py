"""The calibration statistics must be verified before any research conclusion
is drawn from them — a wrong interval or EV sign here produces confident
nonsense downstream."""

import unittest

import duckdb

from analysis.calibration import (
    BucketStat,
    bootstrap_mean_ci,
    bucket_stats,
    mde_mean,
    significant_cells,
    wilson_interval,
)


class TestMDE(unittest.TestCase):
    def test_binary_payoff_heuristic_scale(self):
        # ~half wins/losses at 50c: per-obs SD ~0.5 -> MDE ~ 2.8*0.5/sqrt(n)
        vals = [0.48, -0.52] * 5750  # n=11,500
        m = mde_mean(vals)
        self.assertAlmostEqual(m, 2.8016 * 0.5 / (11500 ** 0.5), places=3)
        self.assertLess(m, 0.014)  # ~1.3c: large-n cells resolve ~1c effects

    def test_floor_cell_cannot_see_small_edges(self):
        vals = ([0.45] * 150) + ([-0.55] * 150)  # n=300, the registry floor
        self.assertGreater(mde_mean(vals), 0.06)  # >6c invisible zone

    def test_scales_inverse_sqrt_n(self):
        v = [0.4, -0.6] * 100
        self.assertAlmostEqual(mde_mean(v * 4) / mde_mean(v), 0.5, places=2)

    def test_degenerate_samples(self):
        self.assertEqual(mde_mean([]), float("inf"))
        self.assertEqual(mde_mean([0.1]), float("inf"))
        self.assertEqual(mde_mean([0.1] * 50), 0.0)

    def test_family_correction_constants(self):
        vals = [0.4, -0.6] * 200
        base = mde_mean(vals)
        self.assertAlmostEqual(mde_mean(vals, family_size=36) / base,
                               3.8360 / 2.8016, places=4)
        self.assertAlmostEqual(mde_mean(vals, family_size=46) / base,
                               3.9062 / 2.8016, places=4)
        with self.assertRaises(ValueError):
            mde_mean(vals, family_size=7)


class TestBootstrap(unittest.TestCase):
    def test_degenerate_sample_has_point_interval(self):
        lo, hi = bootstrap_mean_ci([0.05] * 50)
        self.assertAlmostEqual(lo, 0.05)
        self.assertAlmostEqual(hi, 0.05)

    def test_interval_contains_mean_and_excludes_zero_for_clear_positive(self):
        vals = [0.04, 0.06, 0.05, 0.03, 0.07] * 40  # mean 0.05, tight
        lo, hi = bootstrap_mean_ci(vals)
        self.assertGreater(lo, 0.0)
        self.assertLess(lo, 0.05)
        self.assertGreater(hi, 0.05 - 0.01)

    def test_noisy_zero_mean_interval_straddles_zero(self):
        vals = [0.5, -0.5] * 30
        lo, hi = bootstrap_mean_ci(vals)
        self.assertLess(lo, 0.0)
        self.assertGreater(hi, 0.0)

    def test_deterministic_given_seed(self):
        vals = [0.1, -0.2, 0.3, 0.05] * 10
        self.assertEqual(bootstrap_mean_ci(vals), bootstrap_mean_ci(vals))


class TestWilson(unittest.TestCase):
    def test_known_value(self):
        # 8/10: Wilson 95% ≈ (0.490, 0.943)
        lo, hi = wilson_interval(8, 10)
        self.assertAlmostEqual(lo, 0.490, places=2)
        self.assertAlmostEqual(hi, 0.943, places=2)

    def test_zero_successes(self):
        lo, hi = wilson_interval(0, 100)
        self.assertEqual(lo, 0.0)
        self.assertLess(hi, 0.05)  # rule-of-three neighborhood

    def test_empty_sample_is_uninformative(self):
        self.assertEqual(wilson_interval(0, 0), (0.0, 1.0))

    def test_interval_narrows_with_n(self):
        w10 = wilson_interval(5, 10)
        w1000 = wilson_interval(500, 1000)
        self.assertLess(w1000[1] - w1000[0], w10[1] - w10[0])


def _mem_con_with_obs(rows):
    """rows: (mid, yes_ask, yes_bid, outcome) at h_min=60, spread 0.02."""
    con = duckdb.connect(":memory:")
    con.execute("""
        CREATE TABLE calibration_obs (
            ticker TEXT, h_min INT, yes_bid DOUBLE, yes_ask DOUBLE,
            mid DOUBLE, spread DOUBLE, outcome INT, category TEXT,
            volume DOUBLE, close_time TIMESTAMP, life_hours DOUBLE
        )
    """)
    for i, (mid, ask, bid, outcome) in enumerate(rows):
        con.execute(
            "INSERT INTO calibration_obs VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [f"T{i}", 60, bid, ask, mid, ask - bid, outcome,
             "Test", 100.0, "2026-07-01 00:00:00", 24.0],
        )
    return con


class TestBucketStats(unittest.TestCase):
    def test_perfectly_calibrated_market_is_fee_negative(self):
        # 100 obs at mid 0.50 (bid .49/ask .51), exactly half resolve yes:
        # buying either side must lose spread/2 + fee.
        rows = [(0.50, 0.51, 0.49, 1 if i % 2 == 0 else 0) for i in range(100)]
        con = _mem_con_with_obs(rows)
        stats = bucket_stats(con, 60)
        self.assertEqual(len(stats), 1)
        b = stats[0]
        self.assertEqual(b.n, 100)
        self.assertAlmostEqual(b.yes_rate, 0.50)
        # EV = 0.50 - 0.51 - fee(0.51) = -0.01 - 0.02 = -0.03
        self.assertAlmostEqual(b.ev_yes, -0.03, places=6)
        self.assertAlmostEqual(b.ev_no, -0.03, places=6)
        self.assertEqual(significant_cells(stats), [])

    def test_mispriced_longshot_detected(self):
        # Market says 8% but it never happens: buying NO at 0.93 wins 0.07 - fee(0.93)=0.01 -> +6c
        rows = [(0.08, 0.09, 0.07, 0)] * 400
        con = _mem_con_with_obs(rows)
        stats = bucket_stats(con, 60)
        b = stats[0]
        self.assertEqual(b.yes_rate, 0.0)
        self.assertAlmostEqual(b.ev_no, 0.07 - 0.01, places=6)
        self.assertEqual(len(significant_cells(stats)), 1)
        self.assertIn("YES overpriced", significant_cells(stats)[0])

    def test_spread_filter_excludes_no_book_quotes(self):
        rows = [(0.50, 1.00, 0.00, 1)] * 50  # empty book: spread = 1.0
        con = _mem_con_with_obs(rows)
        self.assertEqual(bucket_stats(con, 60), [])

    def test_oos_split_partitions_by_close_time(self):
        rows = [(0.50, 0.51, 0.49, 1)] * 10
        con = _mem_con_with_obs(rows)
        before = bucket_stats(con, 60, close_before="2026-06-01")
        after = bucket_stats(con, 60, close_from="2026-06-01")
        self.assertEqual(before, [])
        self.assertEqual(after[0].n, 10)


if __name__ == "__main__":
    unittest.main()
