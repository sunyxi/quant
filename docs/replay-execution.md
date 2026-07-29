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
