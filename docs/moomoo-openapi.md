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

## Security

Repository code must never call `unlock_trade`. Any future live-trading unlock requires a separately reviewed Issue and manual action in the OpenD GUI. The default for any future order experiment remains paper trading, but ISSUE-035 and ISSUE-036 expose no order path.

## Official References

- [Moomoo API overview](https://openapi.moomoo.com/moomoo-api-doc/jp/)
- [Moomoo trade context](https://openapi.moomoo.com/moomoo-api-doc/jp/trade/base.html)
- [Moomoo API authority limits](https://openapi.moomoo.com/moomoo-api-doc/jp/intro/authority.html)
