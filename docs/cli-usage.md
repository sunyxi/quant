# CLI Usage

Current commands are local research utilities only. They must not place real broker orders.

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

These tests evaluate local replay result fixtures, run summaries, and local summary JSON writing only. They do not connect to market data, connect to brokers, submit orders, or cancel orders.

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
