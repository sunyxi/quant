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
