from __future__ import annotations

from dataclasses import dataclass

from autotrade.core.models import Fill, MarketSnapshot, OrderIntent, Side


@dataclass(frozen=True)
class ConservativeFillModel:
    max_participation_rate: float = 0.10

    def try_fill(self, intent: OrderIntent, snapshot: MarketSnapshot) -> Fill | None:
        if not self._is_marketable(intent, snapshot):
            return None

        max_quantity = int(snapshot.volume * self.max_participation_rate)
        quantity = min(intent.quantity, max_quantity)
        if quantity <= 0:
            return None

        return Fill(
            client_order_id=intent.client_order_id,
            symbol=intent.symbol,
            side=intent.side,
            quantity=quantity,
            price=self._fill_price(intent, snapshot),
            filled_at=snapshot.timestamp,
        )

    @staticmethod
    def _is_marketable(intent: OrderIntent, snapshot: MarketSnapshot) -> bool:
        if intent.side == Side.BUY:
            return intent.limit_price >= snapshot.ask
        return intent.limit_price <= snapshot.bid

    @staticmethod
    def _fill_price(intent: OrderIntent, snapshot: MarketSnapshot) -> float:
        return snapshot.ask if intent.side == Side.BUY else snapshot.bid
