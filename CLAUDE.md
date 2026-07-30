# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install in editable mode (no runtime dependencies)
pip install -e ".[dev]"

# Run all tests
pytest

# Run a single test file
pytest tests/test_oms.py

# Run a single test
pytest tests/test_oms.py::TestOrderStateMachine::test_register

# Run the backtest demo
python -m autotrade.backtest.demo

# Rebuild generated task catalog (never edit docs/task-catalog.md manually)
python3 scripts/generate_task_catalog.py

# CI checks run on every PR — run locally before pushing:
python3 scripts/check_markdown_links.py
python3 scripts/check_secrets.py
```

Tests use `pytest` with `src/` on the Python path (configured in `pyproject.toml`). No external dependencies are required.

## Architecture

The system is a research-first intraday trading skeleton targeting JP equities. Real broker order placement is not implemented. The mandatory execution pipeline is:

```
MarketData → Strategy → RiskManager → OMS → BrokerAdapter
```

This pipeline is enforced by design: strategies only return `Signal` objects; they cannot call broker interfaces directly.

### Core models (`src/autotrade/core/`)

- `models.py` — frozen dataclasses: `MarketSnapshot`, `Signal`, `OrderIntent`, `Fill`, plus `Market`, `Side`, `OrderStyle` enums.
- `ids.py` — deterministic `client_order_id` generation (SHA-based, ensures idempotency).

### Execution layer (`src/autotrade/execution/`)

- `broker.py` — `BrokerAdapter` abstract base class (the interface future real adapters must implement).
- `oms.py` — `OrderStateMachine` with explicit allowed transitions. Duplicate `client_order_id` registration is idempotent. `UNKNOWN` state handles network ambiguity and must be resolved by reconciliation.
- `ledger.py` — `LocalExecutionLedger`: in-memory orders, fills, positions, and realized PnL. Deduplicates fills by `(id, timestamp, qty, price)`.
- `reconciliation.py` — `ReconciliationEngine` compares OMS + ledger against a `BrokerStateSnapshot`. CRITICAL discrepancies auto-pause the `RiskManager`.
- `simulated_broker.py` — `SimulatedBrokerAdapter` implements `BrokerAdapter` for testing and replay. Holds its own `LocalExecutionLedger` and exports `BrokerStateSnapshot`.
- `replay.py` — `ReplayExecutionEngine` wires strategies → risk → OMS → simulated broker → fill model → reconciliation into a single `run(snapshots, trading_date)` call.

### Backtest layer (`src/autotrade/backtest/`)

- `engine.py` — `BacktestEngine` runs the strategy/risk/fill/cost loop without OMS or broker state.
- `fill_model.py` — `ConservativeFillModel`: fills only when order is marketable; caps at 10% of bar volume; fills at ask (buy) or bid (sell).
- `cost_model.py` — `CostModel` attributes half-spread, slippage, commission, and market impact.

### Risk (`src/autotrade/risk/`)

- `manager.py` — `RiskManager` enforces: max single-trade risk (0.15% equity), max open risk (0.75% equity), daily loss stop (0.75% equity), max symbol notional (10% equity), JP lot sizing (100-share units). Returns `OrderIntent` or `None`. Supports `pause(reason)` / `resume()`.

### Strategies (`src/autotrade/strategies/`)

- `base.py` — `Strategy` ABC: `on_snapshot(snapshot) -> Signal | None`.
- `opening_range.py` — Opening range breakout with VWAP-side and volume filters.
- `vwap_reversion.py` — VWAP mean-reversion with trend-state exclusion.
- `market_quality.py` — Market quality filter (spread, OBI, microprice) used by strategies.

### Market data (`src/autotrade/market_data/`)

- `order_book.py` — `OrderBookSnapshot` with five-level depth, OBI, microprice, spread, and stale-book detection.

### Calendar (`src/autotrade/calendar/`)

- `jp.py` — JP trading session rules: morning/afternoon sessions, lunch break, close cutoff, weekend and holiday rejection. Loaded from `config/markets/jp.yaml`.

## Key constraints

- **No real orders**: `BrokerAdapter` is abstract; only `SimulatedBrokerAdapter` exists.
- **No overnight positions**: enforced by calendar and risk policy.
- **JP lot sizing**: quantities are always rounded down to 100-share units for JP market orders.
- **Task catalog is generated**: `docs/task-catalog.md` is rebuilt from `docs/task-source.json` — never edit the catalog file directly.
- **Gate reporting**: every PR issue must report each gate as `passed`, `failed`, `not-run`, or `skipped`. A gate that did not execute must never be reported as `passed`.
- **Readiness levels**: Research → Replay → Simulation → Shadow Mode → Minimum live pilot. No live pilot without Shadow Mode evidence.
