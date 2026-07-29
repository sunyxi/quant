from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from autotrade.core.models import Market, OrderIntent, OrderStyle, Side


class KabuStationMappingError(ValueError):
    pass


@dataclass(frozen=True)
class KabuStationOrderMapper:
    exchange: str = "TSE"

    def to_order_payload(self, intent: OrderIntent) -> dict[str, Any]:
        if intent.market != Market.JP:
            raise KabuStationMappingError("kabu Station mapper only supports JP market")
        if intent.quantity % 100 != 0:
            raise KabuStationMappingError("JP equity quantity must be a 100 share lot")

        symbol = self._symbol_code(intent.symbol)
        return {
            "symbol": symbol,
            "exchange": self.exchange,
            "side": self._side(intent.side),
            "quantity": intent.quantity,
            "order_type": self._order_type(intent.order_style),
            "limit_price": intent.limit_price,
            "client_order_id": intent.client_order_id,
        }

    @staticmethod
    def _symbol_code(symbol: str) -> str:
        if not symbol.endswith(".T"):
            raise KabuStationMappingError("JP symbol must use .T suffix")

        code = symbol[:-2]
        if not code:
            raise KabuStationMappingError("JP symbol code is required")
        return code

    @staticmethod
    def _side(side: Side) -> str:
        if side == Side.BUY:
            return "BUY"
        if side == Side.SELL:
            return "SELL"
        raise KabuStationMappingError(f"unsupported side: {side}")

    @staticmethod
    def _order_type(order_style: OrderStyle) -> str:
        if order_style in {OrderStyle.PASSIVE_LIMIT, OrderStyle.AGGRESSIVE_LIMIT}:
            return "LIMIT"
        raise KabuStationMappingError(
            f"unsupported order style for kabu Station mapper: {order_style}"
        )
