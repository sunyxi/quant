# Limitations

- The current repository is a research skeleton, not a live trading system.
- No real broker order placement is implemented.
- The backtest engine now has conservative limit-order fills and cost attribution, but does not yet model queue position, minute high/low touch logic, or calibrated fill probability.
- JP regular sessions, lunch break, weekends, manual holidays, and close-entry cutoff are modeled for research filtering.
- Official JP holiday source integration, special quotes, halts, and limit-up or limit-down states are not fully modeled.
- Order book snapshot features are implemented for fixtures and research, but live WebSocket ingestion, incremental book building, cancellation inference, and refill inference are not implemented.
- Strategy market quality filters can block ORB and VWAP signals by spread or order book health, but they are not calibrated fill-probability or alpha models.
- Machine learning, meta-labeling, model registry, and degradation monitoring are out of scope for the current code.
- US market execution through IBKR is future work.
- Nothing in this repository is financial advice or a guarantee of profit.
