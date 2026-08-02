# ORB Parameter Tuning

ISSUE-044 adds explicit bounded nested `--tune` research to `historical-orb-backtest`. It does not download data, load Moomoo, contact OpenD, query an account, or call an order API. Its purpose is to reject fragile parameters and report honest out-of-sample evidence, not to search until a profitable curve appears.

## Candidate Boundary

`bounded_orb_candidates` creates exactly 96 deterministic, unique, long-only combinations:

```text
opening range minutes:       15, 30
minimum relative volume:     1.2, 1.5, 2.0
breakout ATR buffer:         0.0, 0.05
opening-range stop fraction: 0.35, 0.5
target R multiple:           1.0, 1.5
maximum holding minutes:     30, 60
```

Daily ATR stop multiple remains `0.6`, notional remains fixed at the research default, and all candidates use the same side-cost assumption. The engine rejects an empty grid, duplicate keys, mixed side costs, or more candidates than the declared bound.

## Nested Validation

Each outer Walk-Forward training window contains smaller chronological inner train and validation windows. Rule parameters require no statistical fitting on the inner train segment; candidate selection uses only the following inner validation dates. Outer test dates are never read during ranking or eligibility checks.

An inner candidate is rejected with explicit reasons when it fails any configured gate:

- minimum validation trade count;
- net validation Sharpe;
- validation Profit Factor;
- double-cost mean net basis points;
- worst inner-fold mean net basis points;
- maximum positive-profit symbol concentration;
- `positive_parameter_neighbors`, which rejects an isolated result without enough otherwise eligible one-dimension parameter neighbors.

Every candidate receives a deterministic robustness rank. Only an eligible candidate is frozen and run on the next outer test window. The aggregate contains trades from non-overlapping outer test windows only; training and inner-validation trades are excluded. Sharpe calculations include market dates with no trade as zero-return dates.

## Decision

The schema version 3 report retains `default_parameter_full_period` as context and adds `tuning`. The tuning result includes all candidate evaluations, selected parameters, frozen outer-test results, aggregate symbol attribution, zero/baseline/double-cost scenarios, and an explicit `candidate` or `no-go` decision with reasons.

The default decision gates require at least 20 outer-test trades, Sharpe `>= 0.8`, Profit Factor `>= 1.1`, non-negative double-cost mean basis points, acceptable positive-profit symbol concentration, a selected candidate in every outer fold, and positive mean net basis points in every outer fold. A `candidate` result is still research evidence and does not authorize paper or live trading.

## CLI

```bash
PYTHONPATH=src python3 -m autotrade.cli historical-orb-backtest \
  --manifest historical-data/moomoo-us-rth-5m-20251001-20260731-manifest.json \
  --run --tune --side-cost-bps 2.5 \
  --train-days 100 --test-days 20 --step-days 20 \
  --inner-train-days 60 --inner-validation-days 20 --inner-step-days 20 \
  --tuning-min-validation-trades 20 \
  --tuning-min-validation-sharpe 0 \
  --tuning-min-validation-profit-factor 1.0 \
  --tuning-min-double-cost-mean-bps 0 \
  --tuning-min-worst-fold-mean-bps 0 \
  --tuning-max-positive-symbol-share 0.6 \
  --tuning-min-positive-neighbors 1 \
  --tuning-min-outer-trades 20 \
  --tuning-min-outer-sharpe 0.8 \
  --tuning-min-outer-profit-factor 1.1 \
  --tuning-min-outer-double-cost-mean-bps 0 \
  --report-output historical-backtest-reports/orb-tuning.json
```

`--tune` requires `--run`. Report output remains atomic and create-only.

## Current Evidence

The preserved local cache run covers 76,860 five-minute RTH bars for AAPL, MSFT, NVDA, QQQ, and SPY from 2025-10-16 through 2026-07-31. With all default gates frozen before the run:

```text
candidates:            96
outer folds:           4
selected folds:        0
decision:              no-go
aggregate OOS trades:  0
```

All 96 candidates in every outer fold failed the double-cost mean-return gate. Some candidates were slightly positive under baseline cost in isolated inner windows, but they failed double-cost, worst-fold, symbol-concentration, or neighbor-stability checks. Relaxing those gates after seeing this result would be data snooping, not valid tuning.

## Limitations

- The cache contains five current, high-liquidity US symbols and has selection and survivorship bias.
- Ninety-six combinations still create multiple-comparison risk.
- Five-minute bars do not model bid/ask, queue position, partial fills, or true intrabar order.
- Cost assumptions are scenarios rather than calibrated broker execution evidence.
- The current no-go result indicates that parameter tuning alone does not recover a robust ORB edge; a later Issue should test predeclared strategy-structure filters with a newly reserved outer sample.
