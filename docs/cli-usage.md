# CLI Usage

Current commands are local research utilities only. They must not place real broker orders.

## Moomoo OpenAPI Status

Moomoo OpenAPI is the prioritized broker API proof of concept. ISSUE-035 exposes a macOS-capable read-only discovery command, with fake SDKs used for repository tests. Its implementation baseline is OpenD and `moomoo-api` `>=10.4.6408`, with the package imported as `moomoo` and the loopback endpoint defaulting to `127.0.0.1:11111`. The SDK remains an optional dependency.

Validate configuration only, without importing the SDK or connecting:

```bash
PYTHONPATH=src python3 -m autotrade.cli moomoo-readonly-discovery
```

After OpenD is running and logged in, explicitly run sanitized read-only discovery:

```bash
PYTHONPATH=src python3 -m autotrade.cli moomoo-readonly-discovery --connect --report-output moomoo-discovery-reports/moomoo-readonly-discovery-report.json
```

The command must make no live orders or paper orders and must not call `unlock_trade`. It queries only global state, quote-entitlement metadata, and account-list shape. Reports are create-only and exclude raw account data. Sanitized JSON is printed to stdout before an optional report write; a write failure still returns exit code `2`, even though discovery output remains available.

Evaluate a sanitized discovery report offline:

```bash
PYTHONPATH=src python3 -m autotrade.cli moomoo-paper-readiness --discovery-report moomoo-discovery-reports/moomoo-readonly-discovery-report.json
```

This command creates no SDK Context, socket, or broker request. It returns `0` for `READY`, `1` for `BLOCKED`, and `2` for an invalid, non-UTF-8, or unreadable report without a traceback. Login evidence retains `null` when a check was never reached. `READY` does not authorize paper orders or live trading.

Build a sanitized US paper-order plan offline:

```bash
PYTHONPATH=src python3 -m autotrade.cli moomoo-paper-order-dry-run --discovery-report moomoo-discovery-reports/moomoo-readonly-discovery-report.json --client-order-id paper-dry-run-001 --strategy-id us_paper_validation --code US.AAPL --order-style AGGRESSIVE_LIMIT --quantity 10 --limit-price 150.25 --stop-price 148.00 --take-profit-price 154.00 --created-at 2026-08-01T14:30:00+00:00
```

`--order-style` accepts `PASSIVE_LIMIT` (default) or `AGGRESSIVE_LIMIT`; both map to Moomoo `NORMAL` while preserving the source style. Client order IDs must contain 8-64 safe characters. Buy stops must be below the limit price and optional take-profit prices must be above it. Exit code `0` means a deterministic `SIMULATE` plan was built, `1` means readiness or order policy blocked it, and `2` means the input or report was invalid, including NaN or infinite prices. The command does not import the SDK, select an account, or submit an order. Market and side remain fixed to US and BUY as a deliberate command-level safety boundary.

Validate the connected paper-account preflight configuration without loading the SDK:

```bash
PYTHONPATH=src python3 -m autotrade.cli moomoo-paper-account-preflight --discovery-report moomoo-discovery-reports/moomoo-readonly-discovery-report.json
```

After OpenD is running and the retained report evaluates to `READY`, explicitly run the read-only preflight:

```bash
PYTHONPATH=src python3 -m autotrade.cli moomoo-paper-account-preflight --discovery-report moomoo-discovery-reports/moomoo-readonly-discovery-report.json --connect --report-output moomoo-preflight-reports/moomoo-paper-account-preflight-report.json
```

The connected command accepts only loopback OpenD endpoints and an eligible US `SIMULATE` `STOCK_AND_OPTION` account. It refreshes and reads funds, positions, and orders, but prints no account or order identifiers and performs no order mutation. Reports are create-only. Exit code `0` means all reads succeeded, `1` means readiness or compatibility blocked the preflight, and `2` means configuration or report persistence failed.

Preview one Moomoo paper-order submission without loading the SDK:

```bash
PYTHONPATH=src python3 -m autotrade.cli moomoo-paper-order-submit --discovery-report moomoo-discovery-reports/moomoo-readonly-discovery-report.json --preflight-report moomoo-preflight-reports/moomoo-paper-account-preflight-report.json --client-order-id paper-canary-001 --strategy-id us_paper_validation --code US.AAPL --quantity 1 --limit-price 100.00 --stop-price 95.00 --created-at 2026-08-01T14:30:00+00:00
```

Submission is disabled unless `--connect`, `--submit-paper-order`, and `--acknowledge-paper-order-side-effect` are all present. Do not add these flags until the exact paper canary has separate operator approval. Exit `0` requires fresh verification by client-order remark. Exit `1`, `submitted`, or `unknown` requires manual account inspection and must never be retried automatically.

After separate approval of the concrete canary, persist its sanitized post-attempt submission report:

```bash
PYTHONPATH=src python3 -m autotrade.cli moomoo-paper-order-submit --discovery-report moomoo-discovery-reports/moomoo-readonly-discovery-report.json --preflight-report moomoo-preflight-reports/moomoo-paper-account-preflight-report.json --client-order-id paper-canary-001 --strategy-id us_paper_validation --code US.AAPL --quantity 1 --limit-price 100.00 --stop-price 95.00 --created-at 2026-08-01T14:30:00+00:00 --connect --submit-paper-order --acknowledge-paper-order-side-effect --report-output moomoo-submission-reports/moomoo-paper-order-submission-report.json
```

`--report-output` requires all three confirmation flags and does not provide approval by itself. The create-only schema version 1 writer runs only when `place_order_call_count` is exactly one, including `rejected`, `unknown`, `submitted`, and `verified`. A pre-submit block, conflict, or write failure creates no report and returns exit code `2`. The strict reader validates retained evidence offline without OpenD or the SDK.

Validate Moomoo paper-order reconciliation inputs without loading the SDK:

```bash
PYTHONPATH=src python3 -m autotrade.cli moomoo-paper-order-reconcile --discovery-report moomoo-discovery-reports/moomoo-readonly-discovery-report.json --preflight-report moomoo-preflight-reports/moomoo-paper-account-preflight-report.json --client-order-id paper-canary-001
```

Add `--connect` to perform exactly one fresh read-only order-list query. Exit code `0` requires one exact client-order remark match. Exit code `1` means `absent`, `duplicate`, `blocked`, `unknown`, or a dependency failure; exit code `2` means invalid input or report data. The output contains no account or broker order ID. `absent` is point-in-time visibility evidence only and never authorizes automatic resubmission.

Persist a completed connected query as a create-only schema version 1 report:

```bash
PYTHONPATH=src python3 -m autotrade.cli moomoo-paper-order-reconcile --discovery-report moomoo-discovery-reports/moomoo-readonly-discovery-report.json --preflight-report moomoo-preflight-reports/moomoo-paper-account-preflight-report.json --client-order-id paper-canary-001 --connect --report-output moomoo-reconciliation-reports/moomoo-paper-order-reconciliation-report.json
```

`--report-output` is invalid without `--connect`. If connected execution stops before the order-list query reaches `query_status=ok` or `query_status=failed`, the command creates no file and returns exit code `2`. The report writer creates missing parent directories but never overwrites an existing file. Persistence conflicts or filesystem failures also return exit code `2` without a traceback. Reports contain only the sanitized reconciliation result and can be read offline with strict schema validation.

## Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

## Unit Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

Run the focused Moomoo paper reconciliation fixtures:

```bash
PYTHONPATH=src python3 -m unittest tests.test_moomoo_paper_reconcile
```

## Demo Backtest

```bash
PYTHONPATH=src python3 -m autotrade.backtest.demo
```

Validate a trusted local historical cache without importing Moomoo or running a backtest:

```bash
PYTHONPATH=src python3 -m autotrade.cli historical-orb-backtest \
  --manifest historical-data/moomoo-us-rth-5m-manifest.json
```

Run the long-only ORB default-parameter full-period reference and Walk-Forward research with atomic create-only schema version 2 output:

```bash
PYTHONPATH=src python3 -m autotrade.cli historical-orb-backtest \
  --manifest historical-data/moomoo-us-rth-5m-manifest.json \
  --run --side-cost-bps 2.5 \
  --min-train-sharpe 0 --min-train-profit-factor 1.0 \
  --report-output historical-backtest-reports/orb-walk-forward.json
```

`--report-output` requires `--run`. The report labels its full-period reference as `default_parameter_full_period`; it must not be compared as though it used each fold's selected parameters. Historical cache validation and research are offline and never load the Moomoo SDK or call a broker API.

Run bounded nested ORB parameter tuning with the predeclared robustness gates:

```bash
PYTHONPATH=src python3 -m autotrade.cli historical-orb-backtest \
  --manifest historical-data/moomoo-us-rth-5m-manifest.json \
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

`--tune` requires `--run`. It evaluates exactly 192 bounded combinations and writes schema version 4 output: 96 original combinations plus the same 96 with a 90-minute signal cutoff, 0.7 minimum breakout close location, and same-direction VWAP slope. The structure-filter extension is exploratory because it reused previously observed dates. Do not alter gates after observing outer-test results; freeze any future design in a new Issue with newly reserved data instead.

## Strategy Tests

```bash
PYTHONPATH=src python3 -m unittest tests.test_strategies
```

## OMS Tests

```bash
PYTHONPATH=src python3 -m unittest tests.test_oms
```

## Ledger Tests

```bash
PYTHONPATH=src python3 -m unittest tests.test_execution_ledger
```

## Risk Tests

```bash
PYTHONPATH=src python3 -m unittest tests.test_risk_manager
```

## Reconciliation Tests

```bash
PYTHONPATH=src python3 -m unittest tests.test_reconciliation
```

## Simulated Broker Tests

```bash
PYTHONPATH=src python3 -m unittest tests.test_simulated_broker
```

## Replay Execution Tests

```bash
PYTHONPATH=src python3 -m unittest tests.test_replay_execution
```

## Shadow Mode Readiness Gate Tests

```bash
PYTHONPATH=src python3 -m unittest tests.test_shadow_mode
```

These tests evaluate local replay result fixtures, run summaries, summary review aggregation and writing, summary schema versioning, and local summary JSON read/write behavior only. They do not connect to market data, connect to brokers, submit orders, or cancel orders.

## kabu Station Mapper Tests

```bash
PYTHONPATH=src python3 -m unittest tests.test_kabu_station_mapper
```

These tests cover local mapper behavior and official request-contract payload construction only. They do not connect to kabu Station.

## kabu Station Token Client Tests

```bash
PYTHONPATH=src python3 -m unittest tests.test_kabu_station_token_client
```

These tests use a fake transport only. They do not connect to kabu Station or require Windows.

## kabu Station Localhost HTTP Transport Tests

```bash
PYTHONPATH=src python3 -m unittest tests.test_kabu_station_http_transport
```

These tests use an injected fake opener and exercise the explicit localhost-only transport boundary. They do not open network sockets, connect to real kabu Station, require Windows, authenticate with real credentials, query a real account, submit orders, or cancel orders.

## kabu Station Read-only Probe Tests

```bash
PYTHONPATH=src python3 -m unittest tests.test_kabu_station_readonly_probe
```

These tests use fake token and read-only clients. They validate sanitized probe results, propagation of orders, positions, and snapshot-mapping failures, deterministic report JSON round trips, and unknown schema rejection without connecting to kabu Station.

## kabu Station Read-only Probe CLI

Default mode validates configuration only and does not connect to localhost:

```bash
PYTHONPATH=src python3 -m autotrade.cli kabu-readonly-probe --environment test
```

Windows-only real runtime verification, after kabu Station is installed and running, requires an explicit connection flag and the API password from an environment variable or secure prompt:

```bash
KABU_STATION_API_PASSWORD="..." PYTHONPATH=src python3 -m autotrade.cli kabu-readonly-probe --environment test --connect --report-output kabu-probe-reports/test-kabu-readonly-probe-report.json
```

Do not pass the password as a command-line argument. The CLI does not expose sendorder or cancelorder commands. Probe output is read-only and sanitized: it contains statuses, counts, endpoint, timestamp, schema version, and a failure category only; it must not contain the password, token, request headers, order payloads, position payloads, or account identifiers.

The report writer does not overwrite an existing file. Reusing an existing `--report-output` path or encountering a filesystem write failure prints a sanitized error and returns exit code `2` without a Python traceback. Choose a writable new report path or review and remove the old local artifact before retrying.

## kabu Station Sendorder Client Tests

```bash
PYTHONPATH=src python3 -m unittest tests.test_kabu_station_sendorder_client
```

These tests use a fake transport only. They do not connect to kabu Station, require Windows, or place orders.

## kabu Station Cancelorder Client Tests

```bash
PYTHONPATH=src python3 -m unittest tests.test_kabu_station_cancelorder_client
```

These tests use a fake transport only. They do not connect to kabu Station, require Windows, or cancel orders.

## kabu Station Read-only Client Tests

```bash
PYTHONPATH=src python3 -m unittest tests.test_kabu_station_readonly_client
```

These tests use a fake transport only. They do not connect to kabu Station, require Windows, query real orders, or query real positions.

## kabu Station Snapshot Mapper Tests

```bash
PYTHONPATH=src python3 -m unittest tests.test_kabu_station_snapshot_mapper
```

These tests use local fixture payloads only. They do not connect to kabu Station, require Windows, or reconcile a real account.

## kabu Station Read-only Reconciler Tests

```bash
PYTHONPATH=src python3 -m unittest tests.test_kabu_station_readonly_reconciler
```

These tests use injected fake clients only. They do not create a real transport, connect to kabu Station, call `sendorder`, call `cancelorder`, or reconcile a real account.

## Governance Documentation Tests

```bash
PYTHONPATH=src python3 -m unittest tests.test_documentation_catalog
```

## Rebuild Task Catalog

```bash
python3 scripts/generate_task_catalog.py
```

The generated `docs/task-catalog.md` must match `docs/task-source.json`.

## Check Markdown Links

```bash
python3 scripts/check_markdown_links.py
```

## Local CI Equivalent

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
python3 scripts/generate_task_catalog.py
git diff --exit-code -- docs/task-catalog.md
python3 scripts/check_markdown_links.py
git diff --check
python3 scripts/check_secrets.py
```
