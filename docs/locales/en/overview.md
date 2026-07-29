# Overview

This repository implements a research-first intraday trading platform skeleton. The initial target is JP equities, with live broker execution explicitly out of scope until risk, order management, reconciliation, and shadow trading gates pass.

The first release scope is JP equities, long-only, no overnight, and Shadow Mode before live trading. kabu Station is the future JP broker target; IBKR is reserved for a later US phase.

The current calendar layer covers JP regular sessions, lunch break, weekend rejection, manual holidays, and close-entry cutoff for research filtering.

The current order book layer covers immutable snapshots, spread, visible depth, OBI, microprice, freshness, and stale-book health status for research fixtures.

The backtest layer records conservative fills and cost attribution for commission, half-spread, slippage, and impact placeholders.

The strategy layer can now block ORB and VWAP signals when spread limits are exceeded or order book health flags mark the snapshot as stale or unhealthy.

The execution layer now has a broker-independent OMS state machine for idempotent local order registration and auditable lifecycle transitions.

The execution layer also has an in-memory ledger for local orders, fills, positions, average price, and realized PnL in research fixtures.

The risk layer can now enter a paused state with an incident reason and reject all new order approvals until resumed.

The execution layer can compare local OMS and ledger state with broker snapshots and pause risk on critical reconciliation discrepancies.

The execution layer now includes a simulated broker adapter for idempotent order submission, cancellation, open order queries, and fixture-driven fills without live broker access.

The simulated broker can export broker state snapshots for reconciliation tests.

The execution layer now has a local replay execution loop that connects strategies, risk, OMS, simulated broker fills, and reconciliation.

Repository CI runs Python unit tests, Task Catalog drift checks, Markdown link/style checks, and a basic secret scan for pull requests and pushes to `main`.

See `docs/roadmap.md`, `docs/task-catalog.md`, `docs/scope.md`, `docs/risk-policy.md`, `docs/broker-decision.md`, `docs/implementation-plan.md`, `docs/market-calendar.md`, `docs/order-book-intelligence.md`, `docs/backtest-fill-cost.md`, `docs/strategy-market-quality.md`, `docs/oms.md`, `docs/execution-ledger.md`, `docs/risk-paused-state.md`, `docs/reconciliation.md`, `docs/simulated-broker.md`, `docs/replay-execution.md`, `docs/operations.md`, `docs/limitations.md`, and `docs/rollback.md`.
