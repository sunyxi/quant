# Strategy Market Quality Filters

ISSUE-007 connects execution-quality checks to strategy signal generation. The filters are conservative: they can block a signal, but they do not create direction by themselves.

## Scope

The first implementation applies to:

- Opening Range Breakout.
- VWAP Reversion.
- Relative spread checks through `max_spread_bps`.
- Stale order book checks through `require_fresh_order_book`.
- Unhealthy order book flags through `order_book_unhealthy`.

## Feature Inputs

Strategies read market quality from `MarketSnapshot`.

- `snapshot.spread_bps`: computed from best bid and ask.
- `features["order_book_stale"]`: any value greater than zero marks the book as stale.
- `features["order_book_unhealthy"]`: any value greater than zero blocks signals.

These feature flags are intended to be produced later by live order book ingestion or replay fixtures. Until then, tests and research fixtures set them explicitly.

## ORB Behavior

Opening Range Breakout keeps its existing price, relative volume, and VWAP checks. It now also refuses to emit a signal when:

- the current spread is wider than `max_spread_bps`, when configured;
- fresh order book data is required and the snapshot is marked stale;
- the snapshot is marked order-book unhealthy.

## VWAP Reversion Behavior

VWAP Reversion keeps its existing VWAP, z-score, and trend-state checks. It now applies the same market-quality guard before evaluating mean reversion.

## Operational Use

Start with strict filtering in research and Shadow Mode. For early live pilots, these filters should only reduce or suppress trades; they should not authorize extra size or independent microstructure trades.

## Rollback

Rollback is limited to strategy configuration and code:

1. Remove `max_spread_bps` and `require_fresh_order_book` from strategy configuration.
2. Revert the ISSUE-007 branch if behavior must return to pre-filter strategy evaluation.
