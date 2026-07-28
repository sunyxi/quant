from __future__ import annotations

from dataclasses import dataclass

from autotrade.core.models import MarketSnapshot, Side, Signal
from autotrade.features.indicators import zscore
from autotrade.strategies.base import Strategy


@dataclass
class VwapReversion(Strategy):
    strategy_id: str = "jp_vwap_reversion_v1"
    entry_zscore: float = 2.2
    stop_zscore: float = 3.2

    def on_snapshot(self, snapshot: MarketSnapshot) -> Signal | None:
        if snapshot.vwap is None:
            return None

        sigma = snapshot.features.get("ewma_sigma", 0.0)
        trend_score = snapshot.features.get("trend_score", 0.0)
        if trend_score > 0.35:
            return None

        score = zscore(snapshot.mid, snapshot.vwap, sigma)
        if score <= -self.entry_zscore:
            stop = snapshot.vwap - self.stop_zscore * sigma
            return Signal(
                strategy_id=self.strategy_id,
                symbol=snapshot.symbol,
                market=snapshot.market,
                side=Side.BUY,
                confidence=0.55,
                entry_price=snapshot.ask,
                stop_price=stop,
                take_profit_price=snapshot.vwap,
                created_at=snapshot.timestamp,
                reason="price stretched below vwap in range regime",
            )

        if score >= self.entry_zscore:
            stop = snapshot.vwap + self.stop_zscore * sigma
            return Signal(
                strategy_id=self.strategy_id,
                symbol=snapshot.symbol,
                market=snapshot.market,
                side=Side.SELL,
                confidence=0.55,
                entry_price=snapshot.bid,
                stop_price=stop,
                take_profit_price=snapshot.vwap,
                created_at=snapshot.timestamp,
                reason="price stretched above vwap in range regime",
            )

        return None
