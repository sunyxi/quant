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

## Limitations

This is not a production execution loop. It does not yet include:

- durable event logs;
- broker error injection;
- submit timeout simulation;
- restart recovery;
- cancellation policy;
- cost attribution in the replay result.

## Rollback

This change has no live broker side effects. Rollback by reverting the ISSUE-014 branch or by removing replay execution use from future integration code.
