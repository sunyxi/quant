# Replay Execution Engine

ISSUE-014 adds a local replay execution loop. It connects strategy signals, risk approval, OMS state transitions, simulated broker submission, conservative fills, and reconciliation reports.

## Scope

The replay engine currently supports:

- strategy evaluation over supplied market snapshots;
- risk approval through `RiskManager`;
- OMS registration and transitions;
- simulated broker submission;
- conservative fill modeling;
- injected simulated broker fills;
- reconciliation checks after each snapshot.

## Flow

```text
MarketSnapshot
-> Strategy
-> RiskManager
-> OrderStateMachine
-> SimulatedBrokerAdapter
-> ConservativeFillModel
-> ReconciliationEngine
```

The engine does not call live broker APIs.

## Risk Rejection

If risk rejects a signal, replay does not submit anything to the OMS or simulated broker.

## Review-driven Safety Behavior

ISSUE-016 hardens replay behavior based on review findings:

- duplicate `client_order_id` values within one replay run are skipped instead of forcing an invalid OMS transition;
- simulated orders that do not fill immediately are cancelled before reconciliation so broker open orders do not remain unintentionally active;
- critical reconciliation discrepancies raise `ReplayExecutionError` instead of silently pausing risk for the rest of the run;
- default replay runs create isolated OMS and simulated broker objects so a later run cannot mutate a previous result;
- replay validates that every snapshot calendar date matches the supplied `trading_date`;
- replay and backtest share `MarketCalendar` from `autotrade.calendar.protocols`.

## Shadow Mode Readiness Gate

ISSUE-025 adds a local readiness gate for replay results that may later feed Shadow Mode review.

`ShadowModeReadinessGate` evaluates an existing `ReplayExecutionResult` and returns a decision with stable metrics:

- intents;
- fills;
- reconciliation reports;
- critical reconciliation reports;
- remaining open simulated broker orders.

The gate passes only when reconciliation evidence exists, no critical reconciliation report exists, no simulated broker open orders remain, and any supplied `RiskManager` is not paused.

The gate does not run strategies, read market data, query brokers, submit orders, cancel orders, or persist operational state.

## Shadow Mode Run Summary

ISSUE-026 adds `ShadowModeRunSummary`, a local audit-friendly summary built from an existing readiness decision.

The summary records:

- trading date;
- readiness status;
- blocking reasons;
- readiness metrics.

It exposes a JSON-compatible dictionary representation and copies reasons and metrics at creation time so later mutation of the source decision does not change the summary.

The summary builder does not run replay, read market data, query brokers, submit orders, cancel orders, or persist operational state.

## Shadow Mode Summary Writer

ISSUE-027 adds `ShadowModeSummaryWriter`, a local JSON writer for existing run summaries.

The writer creates missing parent directories, rejects overwriting an existing file by default, writes deterministic JSON with sorted keys and a trailing newline, and returns the output path.

The writer does not run replay, read market data, query brokers, submit orders, or cancel orders.

## Shadow Mode Summary Reader

ISSUE-028 adds `ShadowModeSummaryReader`, a local JSON reader for summary files written by `ShadowModeSummaryWriter`.

The reader validates required fields, known readiness status values, string-list reasons, and integer-valued metrics before returning a `ShadowModeRunSummary`.

The reader does not run replay, read market data, query brokers, submit orders, or cancel orders.

## Shadow Mode Summary Schema

ISSUE-029 adds `schema_version` to Shadow Mode run summaries. The current local JSON schema version is `1`.

Writers include `schema_version` in summary JSON. Readers require version `1` and reject missing or unsupported versions before using a summary as fixture review evidence.

## Shadow Mode Summary Review

ISSUE-030 adds `ShadowModeSummaryReview`, a local aggregate over existing run summaries.

The review reports total, passed, and blocked run counts, sorted trading dates, and blocking reason counts across blocked summaries.

The review does not read files, run replay, read market data, query brokers, submit orders, or cancel orders.

## Shadow Mode Review Writer

ISSUE-031 adds `ShadowModeReviewWriter`, a local JSON writer for existing summary review aggregates.

The writer creates missing parent directories, rejects overwriting an existing file by default, writes deterministic JSON with sorted keys and a trailing newline, and returns the output path.

The writer does not discover files, run replay, read market data, query brokers, submit orders, or cancel orders.

## Limitations

This is not a production execution loop. It does not yet include:

- durable event logs;
- broker error injection;
- submit timeout simulation;
- restart recovery;
- configurable cancellation policy;
- cost attribution in the replay result.

## Rollback

This change has no live broker side effects. Rollback by reverting the ISSUE-014 branch or by removing replay execution use from future integration code.
