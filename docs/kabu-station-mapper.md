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

## Cancelorder Client

ISSUE-021 adds a fake-transport-testable cancelorder client. It sends the official cancel payload to the configured localhost cancelorder endpoint through an injected transport, sets the `X-API-KEY` header, and returns the `OrderId` field from a successful response.

The cancelorder client uses the same local error categories as token and sendorder clients:

- `401` and `403`: authentication error;
- `429`: rate limit error;
- `5xx`: server error;
- other non-`200`: generic client error.

The cancelorder client does not create a real HTTP transport and does not cancel live orders. A later issue must explicitly approve any real localhost probe or live cancel path.

## Read-only Client

ISSUE-022 adds a fake-transport-testable read-only client for orders and positions. It sends GET requests to the configured localhost `orders` and `positions` endpoints through an injected transport, sets the `X-API-KEY` header, and returns successful list payloads.

Orders requests may include:

```python
{
    "product": "1",
    "symbol": "7203",
    "details": "false",
}
```

Positions requests may include:

```python
{
    "product": "1",
    "symbol": "7203",
}
```

The read-only client uses the same local error categories as token, sendorder, and cancelorder clients:

- `401` and `403`: authentication error;
- `429`: rate limit error;
- `5xx`: server error;
- other non-`200`: generic client error.

The read-only client validates that successful orders and positions responses are list payloads. It does not create a real HTTP transport, query a real account, or prove kabu Station runtime availability. A later issue must explicitly approve any real localhost probe.

## Snapshot Mapper

ISSUE-023 adds a local-only mapper from kabu Station read-only payloads into the broker snapshot structure used by reconciliation fixtures.

The mapper currently expects the read-only order payload to include:

```python
{
    "ID": "broker-order-1",
    "Symbol": "7203",
    "LeavesQty": 100,
}
```

Orders with positive `LeavesQty` are represented as open broker orders. Orders with zero `LeavesQty` are excluded from open order snapshots.

The mapper currently expects the read-only position payload to include:

```python
{
    "ExecutionID": "position-1",
    "Symbol": "7203",
    "Side": "2",
    "LeavesQty": 100,
}
```

Buy-side positions use positive quantities. Sell-side positions use negative quantities. Flat positions are excluded.

Symbols are normalized from broker code form, such as `7203`, into internal JP symbol form, such as `7203.T`.

Missing required fields raise local client errors. This mapper does not query kabu Station, prove real response completeness, or reconcile a live account by itself.

## Read-only Reconciler

ISSUE-024 adds a local-only read-only reconciler that orchestrates the fake-transport-testable kabu Station read-only client, snapshot mapper, and broker-independent reconciliation engine.

The reconciler:

- fetches orders and positions through an injected read-only client;
- passes the supplied API token to both read-only requests;
- optionally forwards product, symbol, and order details filters;
- maps the returned payloads into `BrokerStateSnapshot`;
- compares the broker snapshot with the supplied local OMS and execution ledger;
- returns critical discrepancies for broker open orders missing from the local OMS and position quantity mismatches;
- pauses a supplied `RiskManager` when reconciliation returns any critical discrepancy.

Client and mapper errors propagate to the caller. The reconciler does not create a real HTTP transport, query a real account, call `sendorder`, or call `cancelorder`.

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
- live order submission;
- cancel requests;
- cash queries.

## Rollback

This change has no live broker side effects. Rollback by reverting the relevant kabu Station feature branch or by removing mapper/client use from future adapter contract tests.
