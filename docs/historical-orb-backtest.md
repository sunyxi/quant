# Historical ORB Backtest

ISSUE-043 adds `historical-orb-backtest`, a broker-independent research boundary for verified local five-minute RTH data. It does not download data, import the Moomoo SDK, create an account Context, or call any quote or trade API.

## Cache Contract

The loader accepts schema version 1 JSON manifests with an adjacent, non-symlink `gzip-csv` artifact. Before parsing bars it validates every required manifest field plus the filename, format, exact CSV columns, row count, date range, sorted symbol set, and SHA-256 digest. Additive manifest metadata is allowed for forward compatibility but cannot replace or weaken a required field. Pickle is intentionally unsupported because loading an untrusted pickle can execute code.

Required CSV columns are:

```text
timestamp,symbol,open,high,low,close,volume,turnover,atr,vwap,relative_volume
```

The first implementation accepts only five-minute RTH bars with no price rehabilitation. Local cache files belong under ignored `historical-data/`; they are research inputs, not repository fixtures or broker evidence.

## Lifecycle

The ORB engine uses the first 15 minutes as its default opening range and evaluates breakouts only after that range is complete. A qualifying signal enters at the next bar open, so a last-bar signal cannot create a trade. The default is long-only.

Stop distance is the smaller of:

```text
0.6 * daily ATR
0.5 * opening range width
```

The default target remains `1.5R`. Every position exits by target, stop, maximum holding time, or session close. If one bar touches both target and stop, the simulator resolves the ambiguity as stop first. This is conservative but still cannot model the true intrabar event order.

Stop sizing uses the signal bar ATR because it is the latest ATR known before the next-bar-open entry. Using the entry bar ATR would consume that bar's high, low, and close before they are known and introduce lookahead. The optional short path remains available only with `long_only=False`; both live-strategy and historical short stop, target, exit, and PnL paths have regression fixtures.

## Metrics

The schema version 2 report includes gross and net PnL per trade plus aggregate trade count, win rate, mean net basis points, profit factor, annualized daily Sharpe, compounded return, maximum drawdown, and total net PnL. `default_parameter_full_period` explicitly labels the default-parameter run over the complete dataset; it is not presented as a parameter-matched comparison with out-of-sample folds. The cost sensitivity section reports zero, baseline, and doubled side-cost assumptions. Each side cost is applied to that execution leg's actual notional, so entry and exit charges can differ when price moves. Symbol attribution uses the same baseline-cost calculation and includes symbols with zero trades.

## Walk-Forward

Walk-Forward folds use ordered trading dates and require `test_days <= step_days <= train_days`, preventing overlapping out-of-sample windows and gaps in rolling training coverage. Each fold selects one candidate from its training dates only, requires a configurable minimum trade count, non-negative training Sharpe, and training Profit Factor of at least `1.0`, freezes the selected parameters, and then reports the following test window. Train and test dates never overlap. A fold with no eligible training candidate is reported without selected parameters or test metrics; the engine never promotes a merely "least bad" losing candidate. Evaluated and eligible counts plus the best observed rejected training metrics remain in the report for audit.

Walk-Forward output is research evidence, not permission to trade. Parameter search remains deliberately small and centered on the current ORB defaults to reduce overfitting.

## CLI

Validate a cache without running research:

```bash
PYTHONPATH=src python3 -m autotrade.cli historical-orb-backtest \
  --manifest historical-data/moomoo-us-rth-5m-manifest.json
```

Run the default-parameter full-period reference and Walk-Forward research and write a create-only report:

```bash
PYTHONPATH=src python3 -m autotrade.cli historical-orb-backtest \
  --manifest historical-data/moomoo-us-rth-5m-manifest.json \
  --run --side-cost-bps 2.5 \
  --train-days 100 --test-days 20 --step-days 20 --min-trades 20 \
  --min-train-sharpe 0 --min-train-profit-factor 1.0 \
  --report-output historical-backtest-reports/orb-walk-forward.json
```

An existing report path is never overwritten. Report content is serialized and flushed to a sibling temporary file, then published with an atomic create-only link; failed publication removes the temporary file and leaves no partial destination. The command has no connection, credential, account, order, or trading-environment option.

## Limitations

- Five-minute OHLC cannot reveal the true order when stop and target occur in one bar.
- Historical bid/ask, order book, queue position, partial fill, and market impact are unavailable.
- Side costs are scenarios, not calibrated execution evidence.
- The initial local sample has a small, current high-liquidity US universe and therefore has selection bias.
- Corporate events, halts, LULD, survivorship changes, and tax effects are not modeled.
- VWAP reversion remains disabled because preliminary zero-cost results were negative.
