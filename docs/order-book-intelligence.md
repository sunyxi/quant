# Order Book Intelligence

ISSUE-004 introduces the first order book data model for research and backtest fixtures. It is not a live market data adapter and does not place orders.

## Snapshot Model

`OrderBookSnapshot` stores:

- symbol
- market
- timestamp
- sorted bid levels
- sorted ask levels

Bid levels must be sorted from highest to lowest price. Ask levels must be sorted from lowest to highest price. Crossed books are rejected.

## P0 Features

The current model computes:

- best bid and best ask
- mid price
- relative spread in basis points
- bid depth by level count
- ask depth by level count
- order book imbalance
- microprice
- freshness
- health status

## Health Status

`health_status()` returns:

- `NORMAL` when the book is fresh.
- `STALE` when the book age is greater than the configured maximum age.

This is a research-layer health indicator only. Later risk and execution Issues must use it to block stale-book trading decisions.

## Current Limitations

- No WebSocket ingestion.
- No broker or exchange sequence number handling.
- No incremental book builder.
- No cancellation or refill inference.
- No strategy integration yet.
