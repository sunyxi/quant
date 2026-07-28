from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from autotrade.backtest.engine import BacktestEngine
from autotrade.core.models import Market, MarketSnapshot
from autotrade.risk.manager import RiskConfig, RiskManager
from autotrade.strategies.opening_range import OpeningRangeBreakout
from autotrade.strategies.vwap_reversion import VwapReversion


def main() -> None:
    strategy = OpeningRangeBreakout(atr=20)
    strategy.set_opening_range(high=1000, low=980)

    snapshots = [
        MarketSnapshot(
            symbol="7203.T",
            market=Market.JP,
            timestamp=datetime(2026, 7, 28, 9, 16, tzinfo=ZoneInfo("Asia/Tokyo")),
            bid=1001,
            ask=1002,
            last=1002,
            volume=500_000,
            vwap=995,
            features={"relative_volume": 2.0},
        )
    ]

    engine = BacktestEngine(
        strategies=[strategy, VwapReversion()],
        risk_manager=RiskManager(RiskConfig(account_equity=2_000_000)),
    )
    result = engine.run(snapshots, trading_date="2026-07-28")
    for intent in result.intents:
        print(f"{intent.symbol} {intent.side} {intent.quantity} @ {intent.limit_price}")


if __name__ == "__main__":
    main()
