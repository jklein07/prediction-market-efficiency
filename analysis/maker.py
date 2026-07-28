"""R-3 / H-R3 — maker conversion of the in-play favorite drift.

Simulates a resting bid placed at (yes_bid + improve) at the h=60m mark on
favorites in match-winner markets, held until close.

Fill models (both reported; the STRICT one is the registry's primary):
- strict:  filled only if a later minute candle traded strictly BELOW the
           order level with volume > 0 (price traded through us — we were in
           the way and cannot have been skipped).
- at:      filled if a later candle traded AT or below the level (optimistic:
           assumes no queue ahead of us).

Adverse selection is inherent to the model: we only ever "fill" when the
price subsequently moved against the position. If EV survives that, the edge
is real for makers.

Fees: Kalshi charges taker fees; resting orders on these series pay none
(maker_fee parameter exists for series where that's false).
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from .fees import taker_fee_per_contract
from .calibration import bootstrap_mean_ci, mde_mean


@dataclass
class MakerResult:
    label: str
    orders: int
    fills: int
    fill_rate: float
    ev_per_fill: float
    ev_ci: tuple[float, float]
    ev_per_order: float          # fill_rate × ev_per_fill (capacity view)
    taker_ev_baseline: float     # same universe, buy at ask at h=60 (reference)
    mde: float = float("nan")    # 80%-power minimum detectable EV per fill


def maker_sim(
    con: duckdb.DuckDBPyConnection,
    series: list[str],
    mid_lo: float = 0.70,
    mid_hi: float = 0.95,
    improve: float = 0.01,
    horizon_min: int = 60,
    strict: bool = True,
    maker_fee: float = 0.0,
    max_spread: float = 0.10,
    close_before: str | None = None,
    close_from: str | None = None,
    label: str = "maker",
    order_size: int = 1,
) -> MakerResult:
    time_conds = ""
    params: list[object] = [horizon_min, max_spread, mid_lo, mid_hi]
    if close_before:
        time_conds += " AND o.close_time < ?"
        params.append(close_before)
    if close_from:
        time_conds += " AND o.close_time >= ?"
        params.append(close_from)
    series_cond = f"({','.join('?' * len(series))})"
    params.extend(series)
    params.append(improve)

    # For each qualifying observation, the fill condition is evaluated over
    # candles after the h=60m mark; outcome comes from the settled record.
    rows = con.execute(f"""
        WITH obs AS (
            SELECT o.ticker, o.yes_bid, o.yes_ask, o.outcome, o.close_time
            FROM calibration_obs o
            WHERE o.h_min = ? AND o.spread <= ?
              AND o.mid >= ? AND o.mid < ?
              {time_conds}
              AND split_part(o.event_ticker, '-', 1) IN {series_cond}
        )
        SELECT
            obs.ticker, obs.yes_bid, obs.yes_ask, obs.outcome,
            obs.yes_bid + ? AS level,
            min(c.trade_price) FILTER (
                WHERE c.volume > 0 AND c.trade_price IS NOT NULL
            ) AS min_traded_after
        FROM obs
        -- LEFT JOIN: an observation with no post-mark candles is still an
        -- order placed (unfilled). An inner join here silently shrinks the
        -- denominator and overstates fill rate.
        LEFT JOIN kalshi_candles c
          ON c.ticker = obs.ticker AND c.period_minutes = 1
         AND c.end_ts > obs.close_time - INTERVAL {int(horizon_min)} MINUTE
        GROUP BY 1, 2, 3, 4, 5
    """, params).fetchall()

    evs = []
    taker_evs = []
    for _, yes_bid, yes_ask, outcome, level, min_traded in rows:
        taker_evs.append(
            (outcome - yes_ask) - taker_fee_per_contract(yes_ask, order_size)
        )
        if min_traded is None:
            continue
        filled = (min_traded < level) if strict else (min_traded <= level)
        if filled:
            evs.append((outcome - level) - maker_fee)

    orders = len(rows)
    fills = len(evs)
    return MakerResult(
        label=label,
        orders=orders,
        fills=fills,
        fill_rate=fills / orders if orders else 0.0,
        ev_per_fill=sum(evs) / fills if fills else 0.0,
        ev_ci=bootstrap_mean_ci(evs),
        ev_per_order=(sum(evs) / orders) if orders else 0.0,
        taker_ev_baseline=sum(taker_evs) / orders if orders else 0.0,
        mde=mde_mean(evs),
    )


def format_maker_results(results: list[MakerResult]) -> str:
    lines = [
        "| sim | orders | fills | fill rate | EV/fill | EV 95% CI | MDE | EV/order | taker baseline |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r.label} | {r.orders} | {r.fills} | {r.fill_rate:.2f} "
            f"| {r.ev_per_fill*100:+.1f}c | [{r.ev_ci[0]*100:+.1f}c, {r.ev_ci[1]*100:+.1f}c] "
            # R-3 is a single pre-registered test (family=1, justified in
            # registry): uncorrected MDE is the applicable figure.
            f"| {r.mde*100:.1f}c (fam=1) | {r.ev_per_order*100:+.1f}c | {r.taker_ev_baseline*100:+.1f}c |"
        )
    return "\n".join(lines)
