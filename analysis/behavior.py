"""Behavioral bias tests (Phase 1).

Momentum vs mean-reversion, tested the only way that matters: conditional on
the market's current belief, does the recent price CHANGE carry incremental
information about the outcome — and is the residual tradable after spread+fee?

Design: for markets observed at a far horizon and a near horizon before close,
compute delta = mid_near - mid_far. Stratify by near-horizon price region and
delta direction. Within each stratum compare realized frequency to the
near-horizon implied probability:
  - realized > implied after upward moves  -> momentum (market under-reacts)
  - realized < implied after upward moves  -> over-reaction (mean reversion)
EV columns price the corresponding trade at the near-horizon book.
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from .fees import taker_fee_per_contract
from .calibration import mde_mean, wilson_interval

DELTA_THRESHOLD = 0.03   # price moves smaller than this are "flat"
PRICE_REGIONS = [(0.05, 0.35), (0.35, 0.65), (0.65, 0.95)]


@dataclass
class MomentumStat:
    region: tuple[float, float]
    direction: str           # up | flat | down
    n: int
    mean_mid: float          # near-horizon implied
    yes_rate: float
    ci_lo: float
    ci_hi: float
    gap: float               # realized - implied at near horizon
    ev_with_move: float      # net EV of trading in the move's direction
    ev_against_move: float   # net EV of fading the move
    mde: float = float("nan")  # 80%-power minimum detectable EV


def momentum_stats(
    con: duckdb.DuckDBPyConnection,
    h_far: int,
    h_near: int,
    category: str | None = None,
    max_spread: float = 0.10,
    delta_threshold: float = DELTA_THRESHOLD,
    series: list[str] | None = None,
    order_size: int = 1,
) -> list[MomentumStat]:
    conds = ["far.h_min = ?", "near.h_min = ?",
             "far.spread <= ?", "near.spread <= ?"]
    params: list[object] = [h_far, h_near, max_spread, max_spread]
    if category:
        conds.append("near.category = ?")
        params.append(category)
    if series:
        conds.append(
            f"split_part(near.event_ticker, '-', 1) IN ({','.join('?' * len(series))})"
        )
        params.extend(series)
    rows = con.execute(f"""
        SELECT near.mid, near.yes_ask, near.yes_bid,
               near.mid - far.mid AS delta, near.outcome
        FROM calibration_obs near
        JOIN calibration_obs far USING (ticker)
        WHERE {' AND '.join(conds)}
    """, params).fetchall()

    out: list[MomentumStat] = []
    for lo, hi in PRICE_REGIONS:
        region_rows = [r for r in rows if lo <= r[0] < hi]
        for direction in ("up", "flat", "down"):
            if direction == "up":
                sel = [r for r in region_rows if r[3] >= delta_threshold]
            elif direction == "down":
                sel = [r for r in region_rows if r[3] <= -delta_threshold]
            else:
                sel = [r for r in region_rows if abs(r[3]) < delta_threshold]
            n = len(sel)
            if n == 0:
                continue
            k = sum(r[4] for r in sel)
            mean_mid = sum(r[0] for r in sel) / n
            ci = wilson_interval(k, n)
            fee = lambda p: taker_fee_per_contract(p, order_size)
            # trade in move direction: up -> buy YES at ask; down -> buy NO at 1-bid
            evs_yes = [(r[4] - r[1]) - fee(r[1]) for r in sel]
            ev_yes = sum(evs_yes) / n
            ev_no = sum(((1 - r[4]) - (1 - r[2])) - fee(1 - r[2]) for r in sel) / n
            if direction == "down":
                ev_with, ev_against = ev_no, ev_yes
            else:  # up (and flat, reported as buy-YES vs buy-NO)
                ev_with, ev_against = ev_yes, ev_no
            out.append(MomentumStat(
                region=(lo, hi), direction=direction, n=n, mean_mid=mean_mid,
                yes_rate=k / n, ci_lo=ci[0], ci_hi=ci[1], gap=k / n - mean_mid,
                ev_with_move=ev_with, ev_against_move=ev_against,
                mde=mde_mean(evs_yes),
            ))
    return out


def format_momentum_table(stats: list[MomentumStat]) -> str:
    lines = [
        "| price region | move | n | implied | realized | 95% CI | gap | EV with-move | EV fade |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for s in stats:
        lines.append(
            f"| {s.region[0]:.2f}–{s.region[1]:.2f} | {s.direction} | {s.n} "
            f"| {s.mean_mid:.3f} | {s.yes_rate:.3f} | [{s.ci_lo:.3f}, {s.ci_hi:.3f}] "
            f"| {s.gap:+.3f} | {s.ev_with_move*100:+.1f}c | {s.ev_against_move*100:+.1f}c |"
        )
    return "\n".join(lines)
