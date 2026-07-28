"""Calibration & market-efficiency analysis (Phase 1).

Core question: when Kalshi says p, does the event happen with frequency p —
and if not, is the gap tradable after fees and spread?

Methodology notes (these choices matter, don't change them casually):
- Prices come from pre-resolution candles at fixed horizons before close,
  NEVER from settlement-time prices (those have already converged).
- Calibration is measured on the MID; tradability is measured on the ASK side
  (buy YES at yes_ask, buy NO at 1 - yes_bid) so reported EV includes both
  spread crossing and the taker fee.
- Wide/no-book quotes (spread > max_spread) are excluded: a 0-bid/1-ask book
  has a "mid" of 0.5 that reflects nothing.
- Every stat carries a Wilson interval; nothing is reported on raw rates.
"""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass, field

import duckdb

from .fees import taker_fee_per_contract

# (horizon_minutes, staleness_minutes): observation = last candle in
# [close - horizon - staleness, close - horizon]. Staleness bounds how old a
# quote may be and still count as "the market's belief at that horizon".
HORIZONS: list[tuple[int, int]] = [
    (5, 15),        # 5 min before close
    (60, 90),       # 1 hour
    (360, 240),     # 6 hours
    (1440, 480),    # 1 day
    (4320, 720),    # 3 days
    (10080, 1440),  # 7 days
]

BUCKET_EDGES = [0.0, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50,
                0.60, 0.70, 0.80, 0.90, 0.95, 1.0000001]

DEFAULT_MAX_SPREAD = 0.10


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, center - half), min(1.0, center + half)


# Family-corrected / uncorrected MDE constant ratio, kept greppable:
# (z_family + z_beta) / (z_single + z_beta) for the standard 36-cell family.
FAMILY36_RATIO = 3.8360 / 2.8016  # = 1.3692


def mde_mean(
    values: list[float],
    power: float = 0.80,
    alpha: float = 0.05,
    family_size: int = 1,
) -> float:
    """Minimum detectable mean effect at the given power (registry std #8).

    A null result is only a statement about effects LARGER than this: with
    per-observation SD `s` (empirical, not the 0.4 binary heuristic) and n
    observations, effects below ≈ (z_crit + z_β)·s/√n were invisible.

    `family_size` applies the Bonferroni-corrected critical value the
    registry's standard #5 actually uses for scanned families ("z ≳ 3" came
    from 0.05/36): a cell found by scanning ~36 cells must clear a higher
    bar, so its MDE is ~37% larger than the naive figure. family_size=1 is
    ONLY for pre-named single tests; per registry, using it must be
    justified per cell. Constants are explicit, not computed, so the values
    stay greppable and reviewable:
      family 1:  z 1.9600 + z_β 0.8416 = 2.8016
      family 36: z 2.9944 + z_β 0.8416 = 3.8360   (0.05/36, one-sided conv.)
      family 46: z 3.0646 + z_β 0.8416 = 3.9062   (R-4: one cell per pair)
    """
    n = len(values)
    if n < 2:
        return float("inf")
    z = {
        (0.80, 0.05, 1): 2.8016,
        (0.90, 0.05, 1): 3.2415,
        (0.80, 0.05, 36): 3.8360,
        (0.80, 0.05, 46): 3.9062,
    }.get((power, alpha, family_size))
    if z is None:
        raise ValueError("unsupported power/alpha/family; add the z constant explicitly")
    return z * statistics.stdev(values) / math.sqrt(n)


def bootstrap_mean_ci(
    values: list[float],
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int = 7,
) -> tuple[float, float]:
    """Percentile bootstrap CI for the mean. Registry standard for EV claims:
    a positive-EV finding requires this interval to exclude zero."""
    if not values:
        return 0.0, 0.0
    rng = random.Random(seed)
    n = len(values)
    means = sorted(
        sum(rng.choice(values) for _ in range(n)) / n for _ in range(n_boot)
    )
    lo_i = int((alpha / 2) * n_boot)
    hi_i = min(n_boot - 1, int((1 - alpha / 2) * n_boot))
    return means[lo_i], means[hi_i]


def build_observations(con: duckdb.DuckDBPyConnection) -> int:
    """Materialize calibration_obs: one row per (settled market, horizon)."""
    values = ", ".join(f"({h}, {s})" for h, s in HORIZONS)
    con.execute(f"""
        CREATE OR REPLACE TABLE calibration_obs AS
        WITH horizon(h_min, stale_min) AS (VALUES {values}),
        ranked AS (
            SELECT
                c.ticker, h.h_min,
                c.yes_bid, c.yes_ask,
                (c.yes_bid + c.yes_ask) / 2 AS mid,
                c.yes_ask - c.yes_bid       AS spread,
                row_number() OVER (
                    PARTITION BY c.ticker, h.h_min ORDER BY c.end_ts DESC
                ) AS rn
            FROM kalshi_candles c
            JOIN kalshi_settled s USING (ticker)
            CROSS JOIN horizon h
            WHERE c.end_ts <= s.close_time - h.h_min * INTERVAL 1 MINUTE
              AND c.end_ts >= s.close_time - (h.h_min + h.stale_min) * INTERVAL 1 MINUTE
              AND c.yes_bid IS NOT NULL AND c.yes_ask IS NOT NULL
        )
        SELECT
            r.ticker, r.h_min, r.yes_bid, r.yes_ask, r.mid, r.spread,
            (s.result = 'yes')::INT                      AS outcome,
            coalesce(e.category, sr.category, 'Unknown') AS category,
            s.event_ticker,
            s.volume,
            s.close_time,
            epoch(s.close_time - s.open_time) / 3600.0   AS life_hours
        FROM ranked r
        JOIN kalshi_settled s USING (ticker)
        LEFT JOIN kalshi_events e USING (event_ticker)
        LEFT JOIN kalshi_series sr
            ON sr.series_ticker = split_part(s.event_ticker, '-', 1)
        WHERE r.rn = 1 AND s.result IN ('yes', 'no')
    """)
    return con.execute("SELECT count(*) FROM calibration_obs").fetchone()[0]


@dataclass
class BucketStat:
    lo: float
    hi: float
    n: int
    mean_mid: float
    yes_rate: float
    ci_lo: float
    ci_hi: float
    mean_ask: float          # avg cost to buy YES
    mean_no_ask: float       # avg cost to buy NO (1 - yes_bid)
    ev_yes: float            # net EV/contract: buy YES at ask, hold to resolution
    ev_no: float             # net EV/contract: buy NO at (1 - bid)
    ev_yes_ci: tuple[float, float] | None = field(default=None, compare=False)
    ev_no_ci: tuple[float, float] | None = field(default=None, compare=False)
    mde: float = field(default=float("nan"), compare=False)  # 80%-power min detectable EV

    @property
    def gap(self) -> float:
        """Calibration gap: realized minus implied. >0 = market underpriced YES."""
        return self.yes_rate - self.mean_mid


def bucket_stats(
    con: duckdb.DuckDBPyConnection,
    horizon_min: int,
    category: str | None = None,
    max_spread: float = DEFAULT_MAX_SPREAD,
    close_before: str | None = None,
    close_from: str | None = None,
    min_volume: float = 0.0,
    dedupe_events: bool = False,
    series: list[str] | None = None,
    bootstrap: bool = False,
    order_size: int = 1,
) -> list[BucketStat]:
    """Per-bucket calibration and tradability stats with all filters applied.

    close_before / close_from (ISO strings) implement the in-sample /
    out-of-sample time split. dedupe_events keeps only the highest-volume
    market per event — a robustness check against correlated observations
    (one game outcome resolves many strike markets at once).
    """
    conds = ["h_min = ?", "spread <= ?", "volume >= ?"]
    params: list[object] = [horizon_min, max_spread, min_volume]
    if category:
        conds.append("category = ?")
        params.append(category)
    if close_before:
        conds.append("close_time < ?")
        params.append(close_before)
    if close_from:
        conds.append("close_time >= ?")
        params.append(close_from)
    if series:
        conds.append(
            f"split_part(event_ticker, '-', 1) IN ({','.join('?' * len(series))})"
        )
        params.extend(series)

    source = "calibration_obs"
    if dedupe_events:
        # Dedupe rule MUST be outcome-independent. Ordering by volume here
        # selects the most dramatically-traded market per event — H-001's
        # selection bias reintroduced within events (caught in R-1, 2026-07-10
        # when max-volume dedupe manufactured 60-point calibration gaps that
        # the pooled analysis didn't have). Lexicographic ticker is arbitrary
        # but independent of the outcome.
        source = """(
            SELECT *, row_number() OVER (
                PARTITION BY event_ticker, h_min ORDER BY ticker
            ) AS _rne FROM calibration_obs
        )"""
        conds.append("_rne = 1")

    rows = con.execute(f"""
        SELECT mid, yes_ask, yes_bid, outcome
        FROM {source}
        WHERE {' AND '.join(conds)}
    """, params).fetchall()

    out: list[BucketStat] = []
    for lo, hi in zip(BUCKET_EDGES, BUCKET_EDGES[1:]):
        sel = [r for r in rows if lo <= r[0] < hi]
        n = len(sel)
        if n == 0:
            continue
        k = sum(r[3] for r in sel)
        mean_mid = sum(r[0] for r in sel) / n
        mean_ask = sum(r[1] for r in sel) / n
        mean_no_ask = sum(1 - r[2] for r in sel) / n
        ci = wilson_interval(k, n)
        # Net EV per contract at the given order size (order_size=1 reproduces
        # every historical figure; larger sizes lower the per-contract fee
        # because Kalshi's round-up-to-cent applies per ORDER — see fees.py).
        fee = lambda p: taker_fee_per_contract(p, order_size)
        evs_yes = [(r[3] - r[1]) - fee(r[1]) for r in sel]
        evs_no = [((1 - r[3]) - (1 - r[2])) - fee(1 - r[2]) for r in sel]
        out.append(BucketStat(
            lo=lo, hi=min(hi, 1.0), n=n, mean_mid=mean_mid,
            yes_rate=k / n, ci_lo=ci[0], ci_hi=ci[1],
            mean_ask=mean_ask, mean_no_ask=mean_no_ask,
            ev_yes=sum(evs_yes) / n, ev_no=sum(evs_no) / n,
            ev_yes_ci=bootstrap_mean_ci(evs_yes) if bootstrap else None,
            ev_no_ci=bootstrap_mean_ci(evs_no) if bootstrap else None,
            mde=mde_mean(evs_yes),
        ))
    return out


def format_bucket_table(stats: list[BucketStat]) -> str:
    lines = [
        "| bucket | n | implied | realized | 95% CI | gap | EV buy-YES | EV buy-NO | MDE (1 / fam36) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for b in stats:
        lines.append(
            f"| {b.lo:.2f}–{b.hi:.2f} | {b.n} | {b.mean_mid:.3f} | {b.yes_rate:.3f} "
            f"| [{b.ci_lo:.3f}, {b.ci_hi:.3f}] | {b.gap:+.3f} "
            f"| {b.ev_yes*100:+.1f}c | {b.ev_no*100:+.1f}c "
            f"| {b.mde*100:.1f}c / {b.mde*FAMILY36_RATIO*100:.1f}c |"
        )
    return "\n".join(lines)


def significant_cells(stats: list[BucketStat]) -> list[str]:
    """Buckets where the implied probability lies outside the realized 95% CI."""
    flags = []
    for b in stats:
        if b.mean_mid < b.ci_lo or b.mean_mid > b.ci_hi:
            direction = "YES underpriced" if b.gap > 0 else "YES overpriced"
            flags.append(
                f"{b.lo:.2f}–{b.hi:.2f}: implied {b.mean_mid:.3f} vs realized "
                f"{b.yes_rate:.3f} [{b.ci_lo:.3f},{b.ci_hi:.3f}] n={b.n} ({direction})"
            )
    return flags
