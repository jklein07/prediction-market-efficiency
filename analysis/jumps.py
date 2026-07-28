"""R-2 / H-R2 — post-jump drift study (news-latency proxy).

Detects trade-confirmed jumps in pre-resolution candles and measures whether
entering AFTER the jump, in its direction, at the touched side, earns positive
EV held to resolution.

Definitions (registry H-R2, amended 2026-07-10 before first analysis):
- Hourly-candled markets (life > 26h): jump = |Δ trade_price| ≥ min_jump
  between consecutive hourly candles that both traded (volume > 0),
  quote-confirmed (mid moved ≥ quote_confirm same direction).
- Minute-candled markets (short-lived; sports in-play control): same, over a
  15-minute lag.
- Entry: `entry_delay` candles after the jump candle, at the touched side
  (jump up → buy YES at ask; jump down → buy NO at 1 − bid), taker fee paid.
- One observation per market (first qualifying jump) — repeated jumps in one
  market are not independent.
- Entry must occur ≥ min_hours_to_close before close (manual tradability).
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from .fees import taker_fee_per_contract
from .calibration import FAMILY36_RATIO, bootstrap_mean_ci, mde_mean, wilson_interval


@dataclass
class JumpStat:
    label: str
    direction: str          # up | down
    n: int
    mean_entry: float       # avg touched-side entry price for the drift trade
    win_rate: float         # trade resolves in entrant's favor
    ev: float               # net EV/contract, hold to resolution
    ev_ci: tuple[float, float]
    mde: float              # 80%-power minimum detectable EV for this cell


def _jump_rows(
    con: duckdb.DuckDBPyConnection,
    period_minutes: int,
    lag_candles: int,
    min_jump: float,
    quote_confirm: float,
    entry_delay: int,
    min_hours_to_close: float,
    categories: list[str] | None,
    max_entry_spread: float = 0.10,
    entry_min_volume: float = 0.0,
    close_before: str | None = None,
    close_from: str | None = None,
) -> list[tuple]:
    """One row per market: (category, direction, entry_yes_bid, entry_yes_ask,
    outcome). Entry candle is entry_delay candles after the jump candle."""
    cat_cond = ""
    # Positional params must match the ?-order in the SQL text exactly:
    # seq CTE (lag, lag, period) -> jumps CTE (min_jump, confirm) ->
    # outer SELECT (entry_delay, max_spread) -> category list.
    min_close_minutes = int(min_hours_to_close * 60)
    params: list[object] = [
        lag_candles, lag_candles, period_minutes,
        min_jump, quote_confirm,
        entry_delay, max_entry_spread, entry_min_volume,
    ]
    if categories:
        cat_cond += f" AND cat.category IN ({','.join('?' * len(categories))})"
        params.extend(categories)
    if close_before:
        cat_cond += " AND cat.close_time < ?"
        params.append(close_before)
    if close_from:
        cat_cond += " AND cat.close_time >= ?"
        params.append(close_from)
    return con.execute(f"""
        WITH cat AS (
            SELECT s.ticker, s.event_ticker, s.close_time,
                   (s.result = 'yes')::INT AS outcome,
                   coalesce(e.category, sr.category, 'Unknown') AS category
            FROM kalshi_settled s
            LEFT JOIN kalshi_events e USING (event_ticker)
            LEFT JOIN kalshi_series sr
                ON sr.series_ticker = split_part(s.event_ticker, '-', 1)
            WHERE s.result IN ('yes', 'no')
        ),
        seq AS (
            SELECT c.ticker, c.end_ts, c.trade_price, c.volume,
                   (c.yes_bid + c.yes_ask) / 2 AS mid,
                   c.yes_bid, c.yes_ask,
                   lag(c.trade_price, ?) OVER w AS prev_trade,
                   lag((c.yes_bid + c.yes_ask) / 2, ?) OVER w AS prev_mid,
                   row_number() OVER w AS rn
            FROM kalshi_candles c
            WHERE c.period_minutes = ?
            WINDOW w AS (PARTITION BY c.ticker ORDER BY c.end_ts)
        ),
        jumps AS (
            SELECT s.ticker, s.rn, s.end_ts,
                   CASE WHEN s.trade_price > s.prev_trade THEN 'up' ELSE 'down' END AS direction,
                   row_number() OVER (PARTITION BY s.ticker ORDER BY s.end_ts) AS jn
            FROM seq s
            JOIN cat ON cat.ticker = s.ticker
            WHERE s.prev_trade IS NOT NULL AND s.volume > 0
              AND abs(s.trade_price - s.prev_trade) >= ?
              AND abs(s.mid - s.prev_mid) >= ?
              AND sign(s.mid - s.prev_mid) = sign(s.trade_price - s.prev_trade)
              AND s.end_ts <= cat.close_time - INTERVAL {min_close_minutes} MINUTE
        )
        SELECT cat.category, j.direction, e.yes_bid, e.yes_ask, cat.outcome
        FROM jumps j
        JOIN seq e ON e.ticker = j.ticker AND e.rn = j.rn + ?
        JOIN cat ON cat.ticker = j.ticker
        WHERE j.jn = 1
          AND e.yes_bid IS NOT NULL AND e.yes_ask IS NOT NULL
          AND e.yes_ask - e.yes_bid <= ?
          -- entry_min_volume > 0 requires the entry candle to have actually
          -- traded: guards against "edges" priced off stale resting quotes
          -- that would reprice before a real order arrived.
          AND coalesce(e.volume, 0) >= ?
          AND e.yes_ask > 0.02 AND e.yes_bid < 0.98
          {cat_cond}
    """, params).fetchall()


def jump_drift_stats(
    con: duckdb.DuckDBPyConnection,
    period_minutes: int = 60,
    lag_candles: int = 1,
    min_jump: float = 0.05,
    quote_confirm: float = 0.03,
    entry_delay: int = 1,
    min_hours_to_close: float = 2.0,
    categories: list[str] | None = None,
    group_by_category: bool = True,
    max_entry_spread: float = 0.10,
    entry_min_volume: float = 0.0,
    close_before: str | None = None,
    close_from: str | None = None,
    order_size: int = 1,
    fee_rate: float = 0.07,
) -> list[JumpStat]:
    rows = _jump_rows(con, period_minutes, lag_candles, min_jump, quote_confirm,
                      entry_delay, min_hours_to_close, categories,
                      max_entry_spread=max_entry_spread,
                      entry_min_volume=entry_min_volume,
                      close_before=close_before, close_from=close_from)
    groups: dict[tuple[str, str], list[tuple]] = {}
    for cat, direction, bid, ask, outcome in rows:
        key = (cat if group_by_category else "all", direction)
        groups.setdefault(key, []).append((bid, ask, outcome))
    out = []
    fee = lambda p: taker_fee_per_contract(p, order_size, fee_rate)
    for (label, direction), sel in sorted(groups.items()):
        evs, entries, wins = [], [], 0
        for bid, ask, outcome in sel:
            if direction == "up":     # buy YES at ask
                evs.append((outcome - ask) - fee(ask))
                entries.append(ask)
                wins += outcome
            else:                     # buy NO at 1 - bid
                no_ask = 1 - bid
                evs.append(((1 - outcome) - no_ask) - fee(no_ask))
                entries.append(no_ask)
                wins += 1 - outcome
        n = len(evs)
        out.append(JumpStat(
            label=label, direction=direction, n=n,
            mean_entry=sum(entries) / n,
            win_rate=wins / n,
            ev=sum(evs) / n,
            ev_ci=bootstrap_mean_ci(evs),
            mde=mde_mean(evs),
        ))
    return out


def format_jump_table(stats: list[JumpStat]) -> str:
    lines = [
        "| group | move | n | avg entry | win rate | EV | EV 95% CI | MDE (1 / fam36) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in stats:
        lines.append(
            f"| {s.label} | {s.direction} | {s.n} | {s.mean_entry:.3f} "
            f"| {s.win_rate:.3f} | {s.ev*100:+.1f}c "
            f"| [{s.ev_ci[0]*100:+.1f}c, {s.ev_ci[1]*100:+.1f}c] "
            f"| {s.mde*100:.1f}c / {s.mde*FAMILY36_RATIO*100:.1f}c |"
        )
    return "\n".join(lines)
