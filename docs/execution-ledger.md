# Local Execution Ledger

ISSUE-009 adds the first local execution ledger. It is an in-memory research and simulation component; it does not persist records, reconcile broker state, or place live orders.

## Scope

The ledger currently supports:

- idempotent order recording by `client_order_id`;
- fill rejection when the referenced order is unknown;
- duplicate fill suppression for identical fill keys;
- position quantity tracking;
- average price tracking;
- realized PnL when an open position is reduced or closed.

## Position Rules

The ledger stores signed quantities.

- Positive quantity means long.
- Negative quantity means short.
- Zero quantity means flat.

Buying into an existing long position recalculates weighted average price. Selling out of a long position realizes PnL as:

```text
(sell price - average price) * closed quantity
```

When the position becomes flat, average price resets to zero.

## Limitations

The ledger is intentionally narrow. It does not yet include:

- durable persistence;
- broker reconciliation;
- fees and commissions in realized PnL;
- corporate actions;
- multi-account accounting;
- tax lots.

## Rollback

This change has no live broker side effects. Rollback by reverting the ISSUE-009 branch or by removing ledger use from future integration code.
