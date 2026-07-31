# Broker Decision

This document records the first broker boundary for implementation. It does not approve live trading.

## Decision

- The first API proof of concept uses Moomoo OpenAPI on macOS, limited to US equities read-only account/market discovery and paper-trading capability validation.
- JP execution target: kabu Station API remains the later JP cash-equity path because Moomoo OpenAPI for Moomoo JP does not support live JP cash-equity trading.
- US execution priority: Moomoo OpenAPI is evaluated before IBKR. IBKR remains a later fallback if Moomoo account capability, reliability, market-data entitlement, or execution behavior does not pass the project gates.
- Existing Japanese brokers such as SBI and Rakuten remain account, research, backup, or manual confirmation paths until their automated execution boundaries are proven and explicitly approved.
- Browser scripting, screen scraping, or private endpoint automation is out of scope.

## Rationale

Moomoo OpenAPI is now the first integration candidate because the official Moomoo JP documentation supports OpenD on macOS and provides a Python SDK. This removes the immediate Windows dependency for the first authenticated API experiment. OpenD exposes a local TCP gateway, normally on `127.0.0.1:11111`, and remains an external process rather than an embedded strategy dependency.

The first Moomoo OpenAPI experiment is intentionally narrower than a broker adapter. ISSUE-035 may validate gateway reachability, API version, account-list shape, US market capability, and sanitized read-only evidence. It must place no live orders and must not unlock trading.

The official support matrix currently allows Moomoo JP customers to use API trading for US stocks and ETFs, but it marks Japanese stocks, ETFs, and REITs as unsupported for live API trading. Japanese market-data access is entitlement-dependent and must be observed from the account rather than assumed. Therefore this decision does not change the first strategy research universe from JP equities and does not claim that Moomoo can replace the JP execution path.

kabu Station remains the practical later JP automation boundary because it provides a documented local API surface for orders, cancels, account state, positions, and streaming market information. Existing kabu Station code and tests remain supported, but Windows runtime validation is no longer the next dependency.

IBKR remains a US-market fallback because it has mature APIs for US equities, account state, order management, and paper trading workflows. Moomoo and IBKR behavior must each be validated independently; results from one broker or market cannot be assumed to transfer.

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

No Moomoo OpenAPI live trading is approved. The Moomoo path cannot progress beyond read-only and paper capability discovery until later Issues prove the same broker-independent controls required of every adapter:

- Idempotent order submission.
- Correct handling of partial fills.
- Timeout recovery without duplicate orders.
- Startup reconciliation from broker state.
- Kill Switch behavior.
- Shadow Mode evidence.

The kabu Station path remains subject to the same conditions before any JP live pilot.

## Confirmed Capability Sources

- [Moomoo API overview](https://openapi.moomoo.com/moomoo-api-doc/jp/) documents OpenD, Python support, macOS support, market data, and broker-specific trading support.
- [Moomoo JP API help](https://www.moomoo.com/jp/support/topic7_474) documents the Moomoo JP account requirement, read/market functions, trading functions, and supported platforms.
- [Moomoo API authority limits](https://openapi.moomoo.com/moomoo-api-doc/jp/intro/authority.html) documents entitlement-dependent Japanese and US market-data access.
- [Moomoo trade context](https://openapi.moomoo.com/moomoo-api-doc/jp/trade/base.html) documents the local OpenD host and port boundary.
