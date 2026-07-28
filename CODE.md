# Prediction-market efficiency study — analysis code

Companion code for the write-up *"What I found when I went looking for edge in
prediction markets"* (2026).

Contents:

- `analysis/fees.py` — Kalshi fee model (schedule effective 2026-02-05):
  per-**order** cent rounding, general/index taker rates, maker rate, and the
  per-contract helper that makes the size dependence explicit.
- `analysis/calibration.py` — calibration engine: probability buckets, Wilson
  intervals, percentile-bootstrap confidence intervals on expected value,
  minimum-detectable-effect (MDE) machinery with family-wise correction, and
  outcome-independent deduplication of correlated contracts.
- `analysis/jumps.py` — post-jump drift study (trade-confirmed jump detection,
  delayed entry at the touched side, per-category statistics).
- `analysis/maker.py` — resting-order fill simulation with a pessimistic
  trade-through fill rule, for measuring adverse selection.
- `analysis/behavior.py` — momentum / mean-reversion stratification.
- `tests/` — synthetic-fixture test suites for all of the above.

## No market data is included

Kalshi's Data Terms of Use restrict providing archived or cached datasets to
other parties without written consent, so no raw or derived market data is
redistributed here. The study corpus (June–July 2026, ~2.2M resolved
contracts) is also not re-crawlable past the venue's history horizon.
Every headline result in the write-up carries its sample size, detection
threshold, and cost assumptions, so the arithmetic can be checked without the
underlying rows. Illustrative figures inside the narrative sections are
sourced from those same tables rather than restating every denominator.

The code runs against the synthetic fixtures in `tests/`, and against any
DuckDB database matching the table shapes documented in the module docstrings.

## Running the tests

Python 3.10 or newer (developed on 3.14; the suite is verified on 3.10).

```
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Linux/macOS: .venv/bin/python
.venv/Scripts/python -m unittest discover -s tests -t .
```

The suite is offline and takes a few seconds.

## How this was built

The analysis code here was written with AI assistance, using Claude Code,
working from my research design and reviewed by me as it went. The
pre-registration, the decisions about what to test and what to kill, and the
verdicts are mine.

*Note on this package: its first snapshot did not import, because the modules
were copied out of a private repository without being run in their new layout.
An external reviewer caught it. The verification procedure is now "clone to a
fresh directory and run the suite there," which is how the current snapshot
was checked.*
