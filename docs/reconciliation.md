# Reconciliation Checks

ISSUE-011 adds the first broker snapshot reconciliation checks. The implementation is local and deterministic; it does not call a broker API.

## Scope

The reconciliation engine compares:

- local OMS order records;
- local execution ledger positions;
- broker open order snapshots;
- broker position snapshots.

It reports critical discrepancies for:

- local OMS orders in `UNKNOWN` state;
- broker open orders missing from the local OMS;
- local and broker position quantity mismatches.

## Risk Pause

When a `RiskManager` is passed to the reconciliation engine, any critical discrepancy calls:

```text
RiskManager.pause("reconciliation discrepancy")
```

This blocks new order approvals. It does not cancel orders, flatten positions, or resolve the discrepancy.

## Broker Snapshot Input

The current broker snapshot types are fixture-level data structures:

- `BrokerOrderSnapshot`
- `BrokerPositionSnapshot`
- `BrokerStateSnapshot`

Future broker adapters should normalize live broker responses into these structures before comparison.

## Limitations

Current checks cover order existence and position quantity only. They do not yet compare:

- broker order status;
- partial fill details;
- average price;
- cash;
- fees;
- realized PnL;
- account buying power.

## Rollback

This change has no live broker side effects. Rollback by reverting the ISSUE-011 branch or by removing reconciliation use from future integration code.
