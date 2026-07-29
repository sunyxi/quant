# Implementation Plan

This plan converts the roadmap into the first concrete build sequence. It keeps infrastructure correctness ahead of strategy sophistication.

## Go / No-Go Rule

Each iteration ends with a Go / No-Go decision.

- Go: acceptance criteria and applicable gates passed.
- Conditional Go: non-critical issues are documented with an owner and follow-up Issue.
- No-Go: missing evidence, failed safety behavior, or unreviewed risk blocks the next phase.

No-Go is the default for any live-trading step when reconciliation, order state, or risk behavior is unknown.

## Iteration 1

Foundation documents and governance.

- ISSUE-001: Roadmap, Task Catalog, PR template, operations, rollback, localization entry points.
- ISSUE-002: Scope, risk policy, broker decision, and this implementation plan.
- Deliverable: a reviewable work queue and clear first-release boundaries.

## Iteration 2

Market rules and session correctness.

- ISSUE-003: JP market calendar and trading session rules.
- Add lunch break handling, close cutoff, no overnight guard, and session fixtures.
- Deliverable: snapshots and strategies can reject invalid trading times.

## Iteration 3

Backtest realism.

- ISSUE-005: conservative fill and cost model.
- Add half-spread, slippage, commission, impact placeholders, and cost attribution.
- Deliverable: research reports cannot ignore execution friction.

## Iteration 4

Order book intelligence P0.

- ISSUE-004: order book snapshot model and microstructure features.
- Add best bid/ask, five-level depth, relative spread, OBI, microprice, freshness, and book health checks.
- Deliverable: board information can filter and confirm signals, but cannot independently authorize live trades.

## Iteration 5

Strategy research hardening.

- Improve opening range breakout with regime, volume, VWAP, spread, and board confirmation filters.
- Improve VWAP reversion with trend-state exclusion and order flow recovery confirmation.
- Deliverable: strategy candidates have explainable signal reports and cost sensitivity.

## Iteration 6

OMS and risk runtime.

- Add order state machine, idempotency keys, local ledger, risk-paused state, and reconciliation hooks.
- Add failure fixtures for timeout, duplicate signal, partial fill, stale market data, and restart.
- Deliverable: order state is auditable before any broker adapter is enabled.

## Iteration 7

Broker adapter and simulation.

- Add kabu Station adapter boundary behind a simulator first.
- Validate request/response normalization, retry boundaries, and unknown order handling.
- Deliverable: adapter contract tests pass without live capital.

## Iteration 8

Shadow Mode.

- Connect live market and broker state reads without placing orders.
- Log theoretical signals, theoretical orders, theoretical fills, expected slippage, and reconciliation state.
- Deliverable: 20 or more trading days of shadow evidence before pilot review.

## Initial Epic Map

| Epic | First linked tasks | Exit evidence |
|---|---|---|
| Governance | ISSUE-001, ISSUE-002 | Docs and gates reviewed |
| Market Rules | ISSUE-003 | Session fixtures pass |
| Data and Backtest | ISSUE-005 | Cost-aware replay reports |
| Board Intelligence | ISSUE-004 | Snapshot and feature tests pass |
| Strategy Research | Later strategy Issues | Walk-forward report |
| Risk and OMS | Later execution Issues | Fault fixtures pass |
| Broker Integration | Later adapter Issues | Contract and shadow tests pass |

## Stop Conditions

- Tests fail without a documented reason.
- Generated catalog output is manually edited.
- A gate is claimed as passed without execution evidence.
- A feature branch contains unrelated work.
- Broker behavior cannot be reconciled.
- Human review blocks the next phase.
