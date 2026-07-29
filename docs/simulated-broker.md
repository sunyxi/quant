# Simulated Broker Adapter

ISSUE-012 adds a broker-interface-compatible simulator. It is designed for unit tests, replay, simulation, and later shadow plumbing. It does not call any live broker API.

## Scope

The simulated broker currently supports:

- idempotent order submission by `client_order_id`;
- deterministic simulated broker order ids;
- cancel by broker order id;
- open order queries;
- fill queries;
- injected fills for test and replay fixtures;
- remaining quantity reduction after partial fills.

## Idempotency

Submitting the same `client_order_id` more than once returns the same simulated broker order id and does not create a duplicate open order.

## Fills

`record_fill()` is fixture-driven. A full fill removes the open order. A partial fill reduces the remaining open order quantity.

The simulator does not independently match orders against market data. That remains the role of the backtest fill model and future replay orchestration.

## Reconciliation Snapshot

`state_snapshot()` exports the simulator's open orders and non-flat positions as a `BrokerStateSnapshot`. This uses the same fixture structure consumed by reconciliation checks.

Open order snapshots include:

- `client_order_id`;
- `symbol`.

Position snapshots include:

- `symbol`;
- signed `quantity`.

## Limitations

The simulator does not implement:

- live broker requests;
- broker errors;
- order rejection rules;
- market sessions;
- margin or cash checks;
- exchange status;
- queue position.

## Rollback

This change has no live broker side effects. Rollback by reverting the ISSUE-012 branch or by removing simulator use from future integration code.
