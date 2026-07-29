# Risk Paused State

ISSUE-010 adds explicit risk pause and resume controls to the risk manager. This is a local safety control for research, replay, simulation, and later broker integration.

## Scope

The risk manager can now:

- enter a paused state with a required reason;
- reject all new order approvals while paused;
- retain the pause reason for operations and incident review;
- resume order approvals when normal risk limits pass.

## Operational Meaning

`RiskState.is_paused` means no new order intent should be approved. It is appropriate for:

- position mismatch;
- unknown order state;
- stale market data;
- manual review;
- incident handling.

The paused state does not cancel orders or flatten positions. Those actions require future OMS, broker adapter, and reconciliation workflows.

## Resume

`resume()` clears the paused flag and pause reason. Operators should only resume after the cause is reviewed and any required reconciliation has completed.

## Rollback

This change has no live broker side effects. Rollback by reverting the ISSUE-010 branch or by removing pause/resume use from future integration code.
