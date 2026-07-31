# Project Scope

This scope defines the first implementable release boundary for the automated trading system. Anything outside this boundary must stay out of the first production pilot unless a later Issue explicitly changes the scope.

## First Release

- Market: JP equities.
- Direction: long-only.
- Holding style: intraday only, no overnight exposure.
- Execution mode: research, replay, simulation, and Shadow Mode before any live order placement.
- Strategy families: opening range breakout and VWAP reversion.
- Trading unit: JP equity lot sizing, initially rounded down to the configured lot size.
- First API PoC: Moomoo OpenAPI on macOS for sanitized read-only account, entitlement, US capability, and JP equity market-data discovery, followed by paper-trading validation in separately approved Issues.
- JP broker target: kabu Station remains the future JP cash-equity execution adapter because Moomoo JP does not currently support live JP cash-equity API trading.
- US broker order: evaluate Moomoo OpenAPI first; retain IBKR as a later fallback.

## Explicitly In Scope

- Research-first strategy development.
- Event-driven market snapshot processing.
- Standard `Signal` and `OrderIntent` boundaries.
- Risk checks before any order intent is accepted.
- Backtesting improvements that model cost and fill uncertainty.
- Order book intelligence for filtering, confirmation, and execution quality.
- Documentation, gates, rollback, and PR governance.

## Explicitly Out of Scope

- Real broker order placement in the current code.
- Browser automation against broker web pages.
- High-frequency, co-located, or direct exchange access trading.
- Short selling in the first release.
- Options, futures, margin optimization, and leverage expansion.
- Machine learning models that directly generate buy or sell orders.
- News, social media, or language-model-driven trade direction.

## Readiness Levels

1. Research: strategy logic runs against historical or fixture data.
2. Replay: historical events are replayed through the same runtime boundary.
3. Simulation: live-like data drives a simulated broker.
4. Shadow Mode: real broker state can be read, but no live orders are placed.
5. Minimum live pilot: only after independent review, fault testing, and human approval.

No live pilot can begin until Shadow Mode has produced enough evidence to review signal quality, order timing, data freshness, slippage assumptions, and risk behavior.
