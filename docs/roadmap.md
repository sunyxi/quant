# Roadmap

This roadmap turns the automated trading concept into gated implementation work. The first production target is JP equities research and shadow trading; live execution remains blocked until data, risk, OMS, reconciliation, and incident controls pass review.

## Phase 0

Foundation and governance.

- Freeze first scope: JP equities, long-only, no overnight, research-first.
- Document broker decision, risk policy, operations, rollback, and PR workflow.
- Establish task catalog, Repository Gates, and localization expectations.
- Exit when documentation, branch workflow, and test-first rules are usable.

## Phase 1

Data and backtesting foundation.

- Add JP market calendar, trading session rules, lunch break handling, and forced close logic.
- Normalize market snapshots and symbol metadata.
- Harden fill and cost modeling beyond the current simplified engine.
- Exit when replayable fixtures and unit tests cover order, fill, position, and PnL behavior.

## Phase 1.5

Order book intelligence foundation.

- Capture best bid/ask, five-level depth, relative spread, order book imbalance, microprice, and data freshness.
- Use board information for signal confirmation, trade filtering, and execution risk control.
- Keep board information out of standalone live trade direction until enough historical evidence exists.
- Exit when snapshots can be replayed and stale or unhealthy books block execution.

## Phase 2

Strategy research.

- Improve opening range breakout and VWAP reversion with regime filters.
- Add candidate pool ranking, relative volume, relative strength, and cost-aware reporting.
- Validate out-of-sample behavior, cost sensitivity, and parameter stability.
- Exit when at least one strategy candidate survives walk-forward review.

## Phase 3

Execution and risk infrastructure.

- Add OMS state machine, idempotent order intents, broker boundaries, reconciliation, and kill switch.
- Implement pre-trade, in-trade, and post-trade risk checks.
- Add failure fixtures for timeouts, unknown orders, partial fills, restarts, and stale data.
- Exit only after fault injection passes.

## Phase 4

Replay, simulation, and Shadow Mode.

- Run historical replay with deterministic event order.
- Connect live market data to simulated orders.
- Prioritize a Moomoo OpenAPI proof of concept on macOS: first sanitized read-only US account/market capability discovery, then paper trading only through separately approved Issues.
- Run Shadow Mode against real broker state without placing orders.
- Exit when shadow results, slippage, and operational health match acceptance thresholds.

## Phase 5

Minimum live JP pilot.

- Keep kabu Station as the JP cash-equity execution candidate because Moomoo JP does not currently support live JP cash-equity API trading.
- Enable one strategy, limited symbols, lowest practical order size, strict daily stop, and no overnight exposure.
- Use board information only for filtering and execution optimization.
- Roll back to Shadow Mode on unexplained PnL, position mismatch, repeated order anomalies, or abnormal slippage.

## Phase 6

Platform hardening.

- Add model registry, meta-labeling, feature versioning, degradation detection, and multi-strategy budget allocation.
- Expand observability and incident response.
- Keep live capital increases gated by review and evidence.

## Phase 7

US market extension.

- Evaluate Moomoo OpenAPI first; retain IBKR as the fallback adapter.
- Add US calendar, US fee and margin assumptions, LULD handling, and normal-hours-only pilot rules.
- Re-run the full backtest, replay, simulation, shadow, and minimum live flow.
