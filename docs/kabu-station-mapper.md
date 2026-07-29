# kabu Station Order Mapper

ISSUE-017 adds a local-only order request mapper for the future kabu Station adapter boundary.

The mapper does not call kabu Station, does not authenticate, and does not place live orders. It only converts an approved `OrderIntent` into a stable local payload shape that later adapter contract tests can consume.

## Scope

The mapper currently supports:

- JP market order intents only;
- `.T` symbol suffix normalization, such as `7203.T` to `7203`;
- BUY and SELL side mapping;
- passive and aggressive limit order styles;
- JP equity 100-share lot validation;
- `client_order_id` pass-through for traceability.

## Payload Shape

```python
{
    "symbol": "7203",
    "exchange": "TSE",
    "side": "BUY",
    "quantity": 100,
    "order_type": "LIMIT",
    "limit_price": 1000,
    "client_order_id": "client-1",
}
```

This payload is an internal adapter-boundary structure. It is not claimed to be a final kabu Station REST request body.

## Rejections

The mapper rejects:

- non-JP markets;
- symbols that do not use the `.T` suffix;
- quantities that are not multiples of 100;
- market-protected order style until a later adapter issue defines protected order semantics.

## Limitations

This is not a broker adapter. It does not implement:

- token handling;
- HTTP requests;
- WebSocket subscriptions;
- broker error mapping;
- live order submission;
- cancel requests;
- order status queries;
- positions or cash queries.

## Rollback

This change has no live broker side effects. Rollback by reverting the ISSUE-017 branch or by removing mapper use from future adapter contract tests.
