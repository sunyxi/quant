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
PYTHONPATH=src python3 -m autotrade.cli moomoo-paper-order-dry-run --discovery-report moomoo-discovery-reports/moomoo-readonly-discovery-report.json --client-order-id paper-dry-run-001 --strategy-id us_paper_validation --code US.AAPL --quantity 10 --limit-price 150.25 --stop-price 148.00 --take-profit-price 154.00 --created-at 2026-08-01T14:30:00+00:00
```

Exit code `0` means a deterministic `SIMULATE` plan was built, `1` means readiness or order policy blocked it, and `2` means the input or report was invalid. The command does not import the SDK, select an account, or submit an order.

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

## Demo Backtest

```bash
PYTHONPATH=src python3 -m autotrade.backtest.demo
```

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
