"""Kalshi fee model and fee-adjusted expected value.

This module exists because fees are the single biggest reason naive
prediction-market "edges" are illusory. Every opportunity score in this
platform must pass through these functions — never compare fair value to
market price directly.

Schedule (verified against kalshi.com/docs/kalshi-fee-schedule.pdf,
effective 2026-02-05):

    general taker fee   = round_up_to_cent(0.07   * C * P * (1 - P))
    maker fee (if any)  = round_up_to_cent(0.0175 * C * P * (1 - P))
    S&P500 / Nasdaq100  = round_up_to_cent(0.035  * C * P * (1 - P))  (taker)

per ORDER of C contracts at price P dollars. No settlement or membership
fees; resting-order cancellation is free; maker fees apply only on the
markets that carry them.

CRITICAL — per-order vs per-contract rounding: the ceiling applies once per
order, so the effective per-contract fee falls with size wherever the raw fee
is below a cent. Example at P=0.90: 1 contract pays ceil($0.0063) = 1.00c,
but 100 contracts pay ceil($0.63) = $0.63 = 0.63c/contract — a 37% difference
concentrated exactly in the 70–95c favorite zone. Analyses that price a
1-contract order (the conservative default everywhere in this codebase)
overstate the hurdle for any realistic size; use `order_size` parameters /
`taker_fee_per_contract` to see both.
"""

from __future__ import annotations

import math

TAKER_FEE_RATE = 0.07
MAKER_FEE_RATE = 0.0175          # only on markets that carry maker fees
INDEX_TAKER_FEE_RATE = 0.035     # S&P 500 (INX*) and Nasdaq-100 (NASDAQ100*)

# Series-ticker prefixes billed at the index taker rate. Verified against
# kalshi_settled on 2026-07-27: the S&P/Nasdaq-100 family appears as KXINX,
# KXINXU, KXINXDUD, KXNASDAQ100, KXNASDAQ100U, KXNASDAQ100MAXY, KXNASDAQDUD —
# so match the broad KXINX/KXNASDAQ stems (plus legacy non-KX forms).
_INDEX_PREFIXES = ("INX", "NASDAQ", "KXINX", "KXNASDAQ")


def fee_rate_for_ticker(ticker: str | None) -> float:
    """Taker fee rate for a market/series ticker (0.035 index, 0.07 general)."""
    if not ticker:
        return TAKER_FEE_RATE
    series = ticker.split("-")[0].upper()
    if series.startswith(_INDEX_PREFIXES):
        return INDEX_TAKER_FEE_RATE
    return TAKER_FEE_RATE


def _fee(rate: float, price: float, contracts: int) -> float:
    if not 0.0 < price < 1.0:
        return 0.0
    raw = rate * contracts * price * (1.0 - price)
    # Kalshi rounds up on exact decimal math; round away binary-float dust
    # first so e.g. 1.7500000000000002 doesn't ceil to 1.76.
    return math.ceil(round(raw * 100.0, 6)) / 100.0


def taker_fee(price: float, contracts: int = 1, rate: float = TAKER_FEE_RATE) -> float:
    """Fee in dollars for one taker ORDER of `contracts` at `price` (0-1)."""
    return _fee(rate, price, contracts)


def maker_fee(price: float, contracts: int = 1) -> float:
    """Maker fee in dollars, on markets that carry one (most carry none)."""
    return _fee(MAKER_FEE_RATE, price, contracts)


def taker_fee_per_contract(
    price: float, contracts: int = 1, rate: float = TAKER_FEE_RATE
) -> float:
    """Per-contract taker fee for an order of `contracts`.

    NOT the same as `taker_fee(price, 1)`: rounding-to-cent happens once per
    order, so at sizes where the raw fee exceeds a cent the round-up washes
    out and the per-contract cost approaches the unrounded 0.07·P·(1−P).
    `contracts=1` reproduces the platform's historical (conservative) figures.
    """
    if contracts <= 0:
        return 0.0
    return taker_fee(price, contracts, rate) / contracts


def net_ev_buy_yes(fair_p: float, yes_ask: float, contracts: int = 1) -> float:
    """Expected profit in dollars, held to resolution, buying YES at the ask."""
    gross = contracts * (fair_p - yes_ask)
    return gross - taker_fee(yes_ask, contracts)


def net_ev_buy_no(fair_p: float, no_ask: float, contracts: int = 1) -> float:
    """Expected profit in dollars, held to resolution, buying NO at the ask."""
    gross = contracts * ((1.0 - fair_p) - no_ask)
    return gross - taker_fee(no_ask, contracts)


def breakeven_edge(price: float, contracts: int = 1) -> float:
    """Minimum |fair - price| per contract for positive EV at this price/size."""
    return taker_fee_per_contract(price, contracts)
