# Overview

This repository implements a research-first intraday trading platform skeleton. The initial target is JP equities, with live broker execution explicitly out of scope until risk, order management, reconciliation, and shadow trading gates pass.

The first release scope remains JP equities, long-only, no overnight, and Shadow Mode before live trading. Moomoo OpenAPI on macOS is now the first API proof of concept for sanitized read-only account, US equities, and JP quote-entitlement discovery, with no live orders. JP equity market data is supported when the account has the required quote entitlement, but Moomoo JP does not currently support live JP cash-equity API trading. ISSUE-035 requires OpenD and `moomoo-api` `>=10.4.6408`, keeps the dependency isolated, and prohibits `unlock_trade`. kabu Station remains the future JP target and IBKR remains a US fallback.

ISSUE-035 now implements the optional `moomoo-api` boundary and `moomoo-readonly-discovery` CLI. Validate-only mode imports no SDK and opens no socket; explicit `--connect` reads only OpenD global state, quote-entitlement metadata, and sanitized account-list shape. Sanitized JSON remains available on stdout if optional report persistence fails, while exit code `2` remains blocking. It exposes no subscriptions, paper orders, live orders, cancellations, or trade unlock.

ISSUE-036 adds `moomoo-paper-readiness`, which evaluates a validated discovery report offline and emits an immutable deterministic `READY` or `BLOCKED` snapshot. Login evidence preserves `null` for "not checked" and `false` for "checked but not logged in". It creates no SDK Context or broker request. `READY` only permits consideration of a later reviewed US paper-order Issue and does not authorize paper orders, Shadow Mode, live orders, or JP trading.

ISSUE-037 adds an offline `moomoo-paper-order-dry-run` contract for a ready US long limit intent. It supports passive or aggressive source styles, validates an 8-64 character client order ID and BUY risk-price ordering, and emits fixed `SIMULATE`, `NORMAL`, `DAY`, and `RTH` values with quantity and notional caps. It does not import the SDK, select an account, submit an order, or authorize paper or live trading.

ISSUE-038 adds the explicitly connected, read-only `moomoo-paper-account-preflight`. It selects exactly one active US `SIMULATE` `STOCK_AND_OPTION` account in memory, refreshes funds, positions, and order-list reads, and emits only sanitized classifications and counts. It never exposes the account ID, mutates orders, or authorizes paper or live trading.

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

The execution layer also has a local Shadow Mode readiness gate that evaluates replay results, reconciliation evidence, open simulated orders, and risk pause state without live broker access.

Shadow Mode readiness decisions can be converted into local run summaries with trading date, status, blocking reasons, and metrics for fixture review.

Shadow Mode run summaries can be written as local deterministic JSON files for fixture review.

Shadow Mode run summary JSON files can be read back with local schema validation.

Shadow Mode run summary JSON now carries local `schema_version` 1 for compatibility checks.

Shadow Mode run summaries can be aggregated locally into review counts for passed and blocked fixture runs.

Shadow Mode summary reviews can be written as local deterministic JSON files for fixture review.

Repository agent rules are captured in `AGENT.md`.

Replay execution now skips duplicate client order IDs within a run, fails fast on critical reconciliation discrepancies, isolates default run results, and rejects snapshots that do not match the supplied trading date.

The execution layer now includes a local-only kabu Station order mapper for future adapter-boundary tests; it does not place live orders.

The mapper also has local official request-contract helpers for token and cash sendorder payloads, still without authentication or network calls.

The kabu Station token client can be tested with a fake transport and maps authentication, rate-limit, and server failures without connecting to kabu Station.

The kabu Station localhost HTTP transport can be explicitly constructed for localhost-only JSON transport tests and the Windows read-only probe. Its default policy allows token authentication plus read-only orders and positions queries only; real sendorder and cancelorder remain blocked.

The localhost boundary now reapplies loopback and read-only policy checks to redirects, rejects encoded endpoint paths, preserves typed status errors for empty or non-JSON HTTP error bodies, and distinguishes configuration, connection, timeout, and operating-system failures while retaining confirmed authentication evidence.

The kabu Station read-only probe and report writer produce sanitized schema-versioned JSON evidence with statuses and counts only. Mac-side tests use fake transports/openers; real authentication and response compatibility still require Windows with kabu Station running.

The kabu Station sendorder client can also be tested with a fake transport and does not place live orders.

The kabu Station cancelorder client can also be tested with a fake transport and does not cancel live orders.

The kabu Station read-only client can also be tested with a fake transport and does not query real orders or positions.

The kabu Station snapshot mapper converts local read-only payload fixtures into broker snapshots for reconciliation tests without querying a real account.

The kabu Station read-only reconciler can run local reconciliation over injected read-only client data, OMS state, and ledger state without creating a real transport or broker side effects.

Repository CI runs Python unit tests, Task Catalog drift checks, Markdown link/style checks, and a basic secret scan for pull requests and pushes to `main`.

See `docs/roadmap.md`, `docs/task-catalog.md`, `docs/scope.md`, `docs/risk-policy.md`, `docs/broker-decision.md`, `docs/implementation-plan.md`, `docs/market-calendar.md`, `docs/order-book-intelligence.md`, `docs/backtest-fill-cost.md`, `docs/strategy-market-quality.md`, `docs/oms.md`, `docs/execution-ledger.md`, `docs/risk-paused-state.md`, `docs/reconciliation.md`, `docs/simulated-broker.md`, `docs/replay-execution.md`, `docs/kabu-station-mapper.md`, `docs/moomoo-openapi.md`, `docs/operations.md`, `docs/limitations.md`, and `docs/rollback.md`.
