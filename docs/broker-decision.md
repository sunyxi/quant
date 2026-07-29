# Broker Decision

This document records the first broker boundary for implementation. It does not approve live trading.

## Decision

- JP execution target: kabu Station API.
- US execution target: IBKR in a later phase.
- Existing Japanese brokers such as SBI and Rakuten remain account, research, backup, or manual confirmation paths until their automated execution boundaries are proven and explicitly approved.
- Browser scripting, screen scraping, or private endpoint automation is out of scope.

## Rationale

kabu Station is the most practical first JP automation boundary because it provides a documented local API surface for orders, cancels, account state, positions, and streaming market information. The implementation must still treat the broker adapter as an external dependency and never allow strategy code to call it directly.

IBKR is reserved for the US market phase because it has mature APIs for US equities, account state, order management, and paper trading workflows. US behavior must be validated independently; JP results cannot be assumed to transfer.

SBI is not selected as the first automated execution target because a general personal JP cash-equity API boundary is not part of the current implementation plan. SBI may still be used for holdings, funding, comparison, or manual confirmation.

Rakuten is not selected as the first primary execution target because the MarketSpeed II RSS path depends on Windows, Excel, client state, and spreadsheet automation. It can be revisited as a backup or operator-assisted workflow.

## Adapter Boundary

All broker implementations must expose the same internal interface:

- Submit order.
- Cancel order.
- Query open orders.
- Query fills.
- Query positions.
- Query available funds.
- Normalize broker errors.
- Reconnect and recover from unknown request state.

Strategies output `OrderIntent`; they do not call broker APIs.

## Manual Confirmation Mode

Manual confirmation is required for any market or broker path that does not have a tested adapter. A signal can be displayed to the operator, but the system must mark it as manual-only and must not assume it was executed unless reconciliation evidence is entered or imported.

## Approval Conditions

The kabu Station adapter cannot move toward live trading until later Issues prove:

- Idempotent order submission.
- Correct handling of partial fills.
- Timeout recovery without duplicate orders.
- Startup reconciliation from broker state.
- Kill Switch behavior.
- Shadow Mode evidence.
