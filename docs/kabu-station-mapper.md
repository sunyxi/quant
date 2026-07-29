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

## Official Request Contract

ISSUE-018 adds local constructors for the official kabu Station request contract documented at `https://kabucom.github.io/kabusapi/reference/index.html`.

Token request:

```python
{
    "APIPassword": "test-password",
}
```

Cash equity limit sendorder request:

```python
{
    "Symbol": "7203",
    "Exchange": 27,
    "SecurityType": 1,
    "Side": "2",
    "CashMargin": 1,
    "DelivType": 2,
    "FundType": "02",
    "AccountType": 4,
    "Qty": 100,
    "FrontOrderType": 20,
    "Price": 1000,
    "ExpireDay": 0,
}
```

The contract helpers are still local-only. They do not send HTTP requests, store API passwords, acquire tokens, or place orders.

The current default `Exchange` is `27` for TSE+. This value is configurable because the official reference distinguishes exchange routing codes and broker-side availability can vary by product and maintenance state.

## Token Client

ISSUE-019 adds a fake-transport-testable token client. It posts the official token payload to the configured localhost token endpoint through an injected transport and returns the `Token` field from a successful response.

The token client maps common HTTP statuses into local errors:

- `401` and `403`: authentication error;
- `429`: rate limit error;
- `5xx`: server error;
- other non-`200`: generic client error.

The token client does not store API passwords and does not construct a real HTTP transport. A later issue must explicitly approve any real localhost probe.

## Sendorder Client

ISSUE-020 adds a fake-transport-testable sendorder client. It posts the official cash order payload to the configured localhost sendorder endpoint through an injected transport, sets the `X-API-KEY` header, and returns the `OrderId` field from a successful response.

The sendorder client maps common HTTP statuses into the same local error categories used by the token client:

- `401` and `403`: authentication error;
- `429`: rate limit error;
- `5xx`: server error;
- other non-`200`: generic client error.

The sendorder client does not create a real HTTP transport and does not place live orders. A later issue must explicitly approve any real localhost probe or live submission path.

## Rejections

The mapper rejects:

- non-JP markets;
- symbols that do not use the `.T` suffix;
- quantities that are not multiples of 100;
- market-protected order style until a later adapter issue defines protected order semantics.

## Limitations

This is not a broker adapter. It does not implement:

- token handling;
- real HTTP requests;
- WebSocket subscriptions;
- broker error mapping;
- live order submission;
- cancel requests;
- order status queries;
- positions or cash queries.

## Rollback

This change has no live broker side effects. Rollback by reverting the ISSUE-017 branch or by removing mapper use from future adapter contract tests.
