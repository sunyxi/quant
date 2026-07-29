# Order Management System

ISSUE-008 adds the first broker-independent OMS state machine. It is local infrastructure only and does not submit orders to a broker.

## Scope

The OMS currently supports:

- idempotent registration by `client_order_id`;
- order lifecycle state tracking;
- broker order id attachment after submission;
- explicit `UNKNOWN` state for uncertain broker outcomes;
- invalid transition rejection through `OrderStateError`.

## States

```text
CREATED
RISK_APPROVED
SUBMITTED
ACKNOWLEDGED
PARTIALLY_FILLED
FILLED
CANCEL_PENDING
CANCELLED
REJECTED
UNKNOWN
```

`FILLED`, `CANCELLED`, and `REJECTED` are terminal states. `UNKNOWN` is not terminal; future reconciliation can resolve it to a broker-confirmed state.

## Idempotency

Calling `register()` more than once with the same `client_order_id` returns the existing `OrderRecord` and does not create a duplicate order record.

## Unknown State

Network timeouts and lost broker responses must not be treated as failed orders. The OMS can move an order to `UNKNOWN` with a reason such as `submit timeout`. Later broker reconciliation must resolve the final state before live trading can continue.

## Rollback

This change has no live broker side effects. Rollback by reverting the ISSUE-008 branch or by removing OMS use from future integration code.
