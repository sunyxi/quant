# ORB Parameter Tuning

ISSUE-044 adds explicit bounded nested `--tune` research to `historical-orb-backtest`. It does not download data, load Moomoo, contact OpenD, query an account, or call an order API. Its purpose is to reject fragile parameters and report honest out-of-sample evidence, not to search until a profitable curve appears.

## Candidate Boundary

`bounded_orb_candidates` creates exactly 192 deterministic, unique, long-only combinations. The first 96 retain the original price/volume boundary:

```text
opening range minutes:       15, 30
minimum relative volume:     1.2, 1.5, 2.0
breakout ATR buffer:         0.0, 0.05
opening-range stop fraction: 0.35, 0.5
target R multiple:           1.0, 1.5
maximum holding minutes:     30, 60
```

The other 96 apply one predeclared structure-filter profile to the same combinations:

```text
max_signal_minutes_after_open: 90
min_breakout_close_location:   0.7
require_rising_vwap:           true
```

The signal cutoff excludes late breakouts, close location requires a long breakout bar to close in its upper 30%, and rising VWAP requires signal-bar VWAP to exceed the preceding bar. Daily ATR stop multiple remains `0.6`, notional remains fixed at the research default, and all candidates use the same side-cost assumption. The engine rejects an empty grid, duplicate keys, mixed side costs, or more candidates than the declared bound.

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

The schema version 4 report retains `default_parameter_full_period` as context and adds `tuning`. The tuning result includes all candidate evaluations, selected parameters, frozen outer-test results, aggregate symbol attribution, zero/baseline/double-cost scenarios, and an explicit `candidate` or `no-go` decision with reasons.

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
candidates:            192
outer folds:           4
selected folds:        1 of 4
decision:              no-go
aggregate OOS trades:  9
mean net bps:          -5.912413
Profit Factor:         0.767845
daily Sharpe:          -0.541354
double-cost mean bps:  -10.912185
```

The first three outer folds selected no candidate. In the fourth fold, 31 structure-filtered candidates passed the inner gates and the selected parameters used `max_signal_minutes_after_open=90`, `min_breakout_close_location=0.7`, and `require_rising_vwap=true`. Its frozen outer test lost 53.72 on nine trades, and the aggregate failed trade-count, Sharpe, Profit Factor, double-cost, symbol-concentration, selected-fold, and fold-positivity gates.

This extension is exploratory because the structure filters were added after inspecting the earlier result and rerun over the same preserved dates. It is useful for rejecting the proposed structure on known data, but it is not independent out-of-sample proof. A future promotion attempt must freeze the complete strategy and use newly reserved dates. Relaxing gates or reporting the fourth fold's strong inner-validation metrics as performance would be data snooping.

## Limitations

- The cache contains five current, high-liquidity US symbols and has selection and survivorship bias.
- One hundred ninety-two combinations increase multiple-comparison risk.
- Five-minute bars do not model bid/ask, queue position, partial fills, or true intrabar order.
- Cost assumptions are scenarios rather than calibrated broker execution evidence.
- The structure-filter extension reused observed dates, so it is contaminated exploratory evidence and cannot authorize paper or live trading.
- The current no-go result indicates that neither bounded parameter tuning nor this structure-filter profile recovers a robust ORB edge on the preserved cache.
