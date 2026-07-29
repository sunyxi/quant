# Limitations

- The current repository is a research skeleton, not a live trading system.
- No real broker order placement is implemented.
- The backtest engine is simplified and does not yet model realistic queue position, partial fills, bid/ask spread, or market impact.
- JP regular sessions, lunch break, weekends, manual holidays, and close-entry cutoff are modeled for research filtering.
- Official JP holiday source integration, special quotes, halts, and limit-up or limit-down states are not fully modeled.
- Order book snapshot features are implemented for fixtures and research, but live WebSocket ingestion, incremental book building, cancellation inference, refill inference, and strategy integration are not implemented.
- Machine learning, meta-labeling, model registry, and degradation monitoring are out of scope for the current code.
- US market execution through IBKR is future work.
- Nothing in this repository is financial advice or a guarantee of profit.
