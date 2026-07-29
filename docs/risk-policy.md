# Risk Policy

This policy defines the first control baseline. It is intentionally conservative because the system is not yet live-trading ready.

## Risk Principles

- Survival is more important than trade frequency.
- No strategy can bypass `RiskManager`.
- No live position may intentionally become overnight exposure.
- No averaging down, martingale, unlimited re-entry, or loss-recovery sizing.
- Unknown broker state must pause trading, not assume safety.
- Board information can reduce or block execution, but cannot independently authorize live trading in early phases.

## Initial Limits

| Limit | Initial value |
|---|---:|
| Single-trade risk | 0.10% to 0.15% of account equity |
| Total open risk | 0.75% of account equity |
| Daily loss stop | 0.50% to 0.75% of account equity |
| Weekly loss reduction | 2.0% drawdown review |
| Maximum development drawdown stop | 10.0% before live pilot review |
| Single symbol exposure | 10.0% of account equity |
| Simultaneous positions | 1 to 3 during pilot |

The larger 20% maximum drawdown discussed in planning is not a first-release operating target. Early live pilots must stop far earlier.

## Pre-trade Controls

Pre-trade checks run before an `OrderIntent` can reach execution.

- Trading session is valid.
- Market data and order book data are fresh.
- Symbol is in the approved candidate pool.
- Side is allowed by scope.
- Quantity respects market lot size.
- Entry, stop, and take-profit prices are coherent.
- Single-trade risk is within limit.
- Daily loss stop has not triggered.
- Spread and expected cost are within configured limits.
- Existing exposure and open risk remain within limits.

## In-trade Controls

In-trade checks run while a position or open order exists.

- Stop-loss and time-stop conditions are monitored.
- Market data staleness pauses new actions.
- Abnormal spread or liquidity loss triggers risk pause.
- Partial fills update exposure immediately.
- Position state must stay reconcilable with local ledger assumptions.
- No new position is opened after a daily stop.

## Post-trade Controls

Post-trade checks run after fills, cancels, rejects, or session close.

- Fills are attributed to strategy and signal IDs.
- Slippage is measured against expected execution cost.
- PnL is updated using local and broker-side evidence.
- Positions, open orders, fills, and cash are reconciled.
- Unexpected broker state moves the system to risk-paused mode.
- End-of-day review confirms no unintended overnight position remains.

## Kill Switch

The Kill Switch must execute in this order:

1. Stop new signals.
2. Block new order intents.
3. Cancel open orders.
4. Query broker positions and fills.
5. Reconcile local and broker state.
6. Flatten positions only through approved emergency logic.
7. Lock automatic restart until human review is complete.

The current repository does not implement live Kill Switch execution yet. This policy is the acceptance target for later implementation.
