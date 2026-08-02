# Historical ORB Backtest

ISSUE-043 adds `historical-orb-backtest`, a broker-independent research boundary for verified local five-minute RTH data. It does not download data, import the Moomoo SDK, create an account Context, or call any quote or trade API.

## Cache Contract

The loader accepts schema version 1 JSON manifests with an adjacent, non-symlink `gzip-csv` artifact. Before parsing bars it validates the exact filename, format, columns, row count, date range, sorted symbol set, and SHA-256 digest. Pickle is intentionally unsupported because loading an untrusted pickle can execute code.

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

## Metrics

The report includes gross and net PnL per trade plus aggregate trade count, win rate, mean net basis points, profit factor, annualized daily Sharpe, compounded return, maximum drawdown, and total net PnL. The cost sensitivity section reports zero, baseline, and doubled side-cost assumptions. Symbol attribution uses the same baseline-cost calculation.

## Walk-Forward

Walk-Forward folds use ordered trading dates. Each fold selects one candidate from its training dates only, requires a configurable minimum trade count, non-negative training Sharpe, and training Profit Factor of at least `1.0`, freezes the selected parameters, and then reports the following test window. Train and test dates never overlap. A fold with no eligible training candidate is reported without selected parameters or test metrics; the engine never promotes a merely "least bad" losing candidate. Evaluated and eligible counts plus the best observed rejected training metrics remain in the report for audit.

Walk-Forward output is research evidence, not permission to trade. Parameter search remains deliberately small and centered on the current ORB defaults to reduce overfitting.

## CLI

Validate a cache without running research:

```bash
PYTHONPATH=src python3 -m autotrade.cli historical-orb-backtest \
  --manifest historical-data/moomoo-us-rth-5m-manifest.json
```

Run baseline and Walk-Forward research and write a create-only report:

```bash
PYTHONPATH=src python3 -m autotrade.cli historical-orb-backtest \
  --manifest historical-data/moomoo-us-rth-5m-manifest.json \
  --run --side-cost-bps 2.5 \
  --train-days 100 --test-days 20 --step-days 20 --min-trades 20 \
  --min-train-sharpe 0 --min-train-profit-factor 1.0 \
  --report-output historical-backtest-reports/orb-walk-forward.json
```

An existing report path is never overwritten. The command has no connection, credential, account, order, or trading-environment option.

## Limitations

- Five-minute OHLC cannot reveal the true order when stop and target occur in one bar.
- Historical bid/ask, order book, queue position, partial fill, and market impact are unavailable.
- Side costs are scenarios, not calibrated execution evidence.
- The initial local sample has a small, current high-liquidity US universe and therefore has selection bias.
- Corporate events, halts, LULD, survivorship changes, and tax effects are not modeled.
- VWAP reversion remains disabled because preliminary zero-cost results were negative.
