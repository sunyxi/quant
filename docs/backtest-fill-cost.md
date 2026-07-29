# Backtest Fill and Cost Model

ISSUE-005 replaces unconditional immediate fills with a conservative fill model and explicit cost attribution.

## Fill Model

`ConservativeFillModel` only fills marketable limit orders:

- Buy orders require `limit_price >= ask`.
- Sell orders require `limit_price <= bid`.
- Fill quantity is capped by `snapshot.volume * max_participation_rate`.

If the limit price is not marketable, the order intent remains recorded but no fill is created.

## Cost Model

`CostModel` estimates:

- commission
- half-spread cost
- slippage
- impact

`CostBreakdown.total` is the sum of all components.

## Backtest Result

`BacktestResult` now includes:

- `intents`
- `fills`
- `costs`

`costs` is keyed by `client_order_id` so reports can attribute execution friction to each order.

## Current Limitations

- Queue position is not modeled.
- Minute high/low touch logic is not implemented.
- Fill probability is deterministic and intentionally conservative.
- Costs are parameterized placeholders and must be calibrated from real fills later.
