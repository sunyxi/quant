# Moomoo OpenAPI Read-only Discovery

ISSUE-035 adds a macOS-capable Moomoo OpenAPI discovery boundary. It validates local OpenD compatibility and emits sanitized evidence. It is not a broker order adapter and places no live orders or paper orders.

## Runtime Boundary

- OpenD and `moomoo-api` must be version `10.4.6408` or newer.
- The default endpoint is loopback-only `127.0.0.1:11111`.
- Supported host values are `127.0.0.1`, `localhost`, and `::1`.
- The Python distribution is `moomoo-api`; its import name is `moomoo`.
- The SDK is an optional dependency because its `protobuf` requirement may conflict with unrelated tools.

Install it in the project virtual environment only when running the explicit discovery:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev,moomoo]"
```

OpenD must be running and logged in before `--connect` is used. The repository does not manage OpenD credentials.

## CLI

Use `validate-only` mode to validate configuration without importing the SDK, constructing a Context, or opening a socket:

```bash
PYTHONPATH=src python3 -m autotrade.cli moomoo-readonly-discovery
```

Run the explicit read-only discovery and write a create-only report:

```bash
mkdir -p moomoo-discovery-reports
PYTHONPATH=src python3 -m autotrade.cli moomoo-readonly-discovery \
  --connect \
  --report-output moomoo-discovery-reports/moomoo-readonly-discovery-report.json
```

The CLI has no password argument, trade environment argument, order command, cancellation command, subscription command, or `unlock_trade` option.

## Read Operations

The implementation creates only:

- `OpenQuoteContext` for `get_global_state` and `get_user_info`;
- `OpenSecTradeContext` filtered to `TrdMarket.US` and `SecurityFirm.FUTUJP` for `get_acc_list`.

Every Context is closed after success or failure. The discovery does not request quote subscriptions or automatically purchase market-data rights.

## Sanitized Evidence

Schema version 1 reports contain only:

- loopback endpoint;
- SDK and OpenD server versions;
- quote and trade connection status;
- quote and trade login booleans;
- US and JP quote entitlement enums;
- total, paper, and real account counts;
- paper-account availability;
- whether an account advertises US market authorization;
- a sanitized failure category.

Reports exclude account identifiers, card numbers, user identifiers, nicknames, credentials, tokens, raw account rows, raw quote payloads, and SDK exception messages. Report files are create-only and ignored by Git. Sanitized discovery JSON is emitted to stdout before an optional report write. A report path conflict or write failure still returns exit code `2`; stdout is diagnostic evidence and does not mean the report was persisted.

## Failure Categories

- `version`: SDK version is missing, invalid, or below the minimum.
- `connection`: a local OpenD Context cannot be created.
- `response`: a read-only SDK call fails or returns an unsupported shape.
- `system`: an unexpected local runtime failure occurs.

A failed discovery blocks paper trading, Shadow Mode, and live trading. A successful discovery proves compatibility only; it does not approve orders.

## Offline Paper Readiness

ISSUE-036 adds an offline gate that consumes only a validated schema version 1 discovery report:

```bash
PYTHONPATH=src python3 -m autotrade.cli moomoo-paper-readiness \
  --discovery-report moomoo-discovery-reports/moomoo-readonly-discovery-report.json
```

The gate creates no SDK Context or socket and performs no broker request. A `READY` result requires successful quote and trade connections, both login booleans, at least one paper account, US market authorization, and a known non-`NO` US quote entitlement. Otherwise it emits `BLOCKED` with fixed reason codes in policy order.

The decision is an immutable, hashable snapshot containing only readiness schema version 1, status, fixed reason codes, discovery schema version, booleans, paper-account count, and the sanitized US entitlement enum. Login evidence preserves `true`, `false`, or `null`; `null` means the check was not reached. Exit code `0` means `READY`, `1` means `BLOCKED`, and `2` means the report is invalid, non-UTF-8, or unreadable. `READY` allows only consideration of a separately reviewed US paper-order adapter Issue; it does not authorize paper orders, Shadow Mode, live orders, or JP cash-equity trading.

## Offline Paper-order Dry Run

ISSUE-037 adds `moomoo-paper-order-dry-run`. It combines a retained discovery report with explicit broker-independent order fields and produces an immutable, sanitized plan without importing the SDK or contacting OpenD:

```bash
PYTHONPATH=src python3 -m autotrade.cli moomoo-paper-order-dry-run \
  --discovery-report moomoo-discovery-reports/moomoo-readonly-discovery-report.json \
  --client-order-id paper-dry-run-001 \
  --strategy-id us_paper_validation \
  --code US.AAPL --order-style AGGRESSIVE_LIMIT --quantity 10 \
  --limit-price 150.25 --stop-price 148.00 \
  --take-profit-price 154.00 \
  --created-at 2026-08-01T14:30:00+00:00
```

The planner requires `READY`, US `BUY`, a canonical `US.<ticker>` code, an 8-64 character safe client order ID, whole shares, and a passive or aggressive limit intent. For a buy, the stop must be below the limit price and an optional take-profit price must be above it. Defaults cap quantity at 100 and notional at USD 25,000. Its fixed contract uses `SIMULATE`, `NORMAL`, `DAY`, and `RTH`. It does not select an account, inspect buying power, call the SDK, or submit an order. The output is design evidence only and does not authorize a paper order, Shadow Mode, or live trading. Non-finite CLI prices are invalid input and return exit code `2`.

## Connected Paper-account Preflight

ISSUE-038 adds `moomoo-paper-account-preflight`. Its default validate-only mode reads a validated discovery report but does not load the SDK or connect. Explicit `--connect` requires a `READY` decision, opens one US trade Context, and selects exactly one `ACTIVE`, US-authorized `SIMULATE` account whose `sim_acc_type` is `STOCK_AND_OPTION`:

```bash
mkdir -p moomoo-preflight-reports
PYTHONPATH=src python3 -m autotrade.cli moomoo-paper-account-preflight \
  --discovery-report moomoo-discovery-reports/moomoo-readonly-discovery-report.json \
  --connect \
  --report-output moomoo-preflight-reports/moomoo-paper-account-preflight-report.json
```

The selected account ID remains in memory only. The preflight calls `accinfo_query`, `position_list_query`, and `order_list_query` with the selected ID, `TrdEnv.SIMULATE`, and `refresh_cache=True`. It closes the Context on every path and reports only account classification, query statuses, aggregate position/order counts, SDK version, loopback endpoint, and a fixed failure category. The output does not include account identifiers, raw broker rows, credentials, order IDs, or SDK exception text.

This is a read compatibility check. It does not call `unlock_trade`, place, modify, or cancel an order, subscribe to market data, expose a `REAL` environment option, or authorize Shadow Mode. A successful preflight does not authorize a paper order; submission requires a separate reviewed Issue.

## Explicit Paper-order Submission

ISSUE-039 adds `moomoo-paper-order-submit` for one US BUY limit order in `SIMULATE only`. The default remains preview-only and does not load the SDK:

```bash
PYTHONPATH=src python3 -m autotrade.cli moomoo-paper-order-submit \
  --discovery-report moomoo-discovery-reports/moomoo-readonly-discovery-report.json \
  --preflight-report moomoo-preflight-reports/moomoo-paper-account-preflight-report.json \
  --client-order-id paper-canary-001 --strategy-id us_paper_validation \
  --code US.AAPL --quantity 1 --limit-price 100.00 --stop-price 95.00 \
  --created-at 2026-08-01T14:30:00+00:00
```

Actual paper submission additionally requires `--connect`, `--submit-paper-order`, and `--acknowledge-paper-order-side-effect`. Using those flags requires separate approval of the concrete symbol, quantity, and prices; repository tests never use them against real OpenD.

The service reselects exactly one eligible simulated account, calls `place_order` at most once with `NORMAL`, `DAY`, `RTH`, `fill_outside_rth=False`, and the client order ID as `remark`, then runs a fresh order query. It emits no account ID or broker order ID. A verified remark produces `verified`; a broker error produces `rejected`; an exception or malformed successful response produces `UNKNOWN`. An accepted order that cannot be uniquely verified remains `submitted`. The service does not automatically retry any submission.

The command has no `REAL`, SELL, market, extended-hours, option, JP, unlock, modify, cancel, or subscription path. Successful fake-SDK validation does not authorize a real OpenD canary; that requires separate approval.

## Read-only Paper-order Reconciliation

ISSUE-040 adds `moomoo-paper-order-reconcile`. Its default validate-only mode checks retained discovery and preflight evidence plus the client order ID without loading the SDK:

```bash
PYTHONPATH=src python3 -m autotrade.cli moomoo-paper-order-reconcile \
  --discovery-report moomoo-discovery-reports/moomoo-readonly-discovery-report.json \
  --preflight-report moomoo-preflight-reports/moomoo-paper-account-preflight-report.json \
  --client-order-id paper-canary-001
```

Add `--connect` only while OpenD is logged in. The service reselects exactly one eligible `SIMULATE` account and calls `order_list_query` once with `refresh_cache=True`. It compares the exact broker `remark` and emits `unique`, `absent`, `duplicate`, `blocked`, or `unknown` with sanitized counts and fixed failure categories only.

`ABSENT` means the order was not visible in that fresh query; it is not proof that no submission occurred. `DUPLICATE` and `UNKNOWN` are ambiguous. The command does not automatically resubmit, modify, cancel, unlock, subscribe, or access `REAL`, and operators must not rerun ISSUE-039 based only on reconciliation output.

## Security

Repository code must never call `unlock_trade`. Any future live-trading unlock requires a separately reviewed Issue and manual action in the OpenD GUI. Dry-run, preflight, paper-submit, and reconciliation output contain no account identifier or credential. A confirmed paper-submit invocation has a simulated broker side effect and must be reconciled manually if its result is not `verified`.

## Official References

- [Moomoo API overview](https://openapi.moomoo.com/moomoo-api-doc/jp/)
- [Moomoo trade context](https://openapi.moomoo.com/moomoo-api-doc/jp/trade/base.html)
- [Moomoo API authority limits](https://openapi.moomoo.com/moomoo-api-doc/jp/intro/authority.html)
