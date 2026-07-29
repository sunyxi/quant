from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from autotrade.core.models import Market, OrderIntent, OrderStyle, Side


class KabuStationMappingError(ValueError):
    pass


@dataclass(frozen=True)
class KabuStationEnvironment:
    base_url: str

    @classmethod
    def production(cls) -> KabuStationEnvironment:
        return cls(base_url="http://localhost:18080")

    @classmethod
    def test(cls) -> KabuStationEnvironment:
        return cls(base_url="http://localhost:18081")

    @property
    def token_url(self) -> str:
        return f"{self.base_url}/kabusapi/token"

    @property
    def sendorder_url(self) -> str:
        return f"{self.base_url}/kabusapi/sendorder"


@dataclass(frozen=True)
class KabuStationOrderMapper:
    exchange: str = "TSE"
    official_exchange: int = 27
    account_type: int = 4
    buy_fund_type: str = "02"
    expire_day: int = 0

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

    def to_token_payload(self, api_password: str) -> dict[str, str]:
        if not api_password:
            raise KabuStationMappingError("API password is required")
        return {"APIPassword": api_password}

    def to_cash_sendorder_payload(self, intent: OrderIntent) -> dict[str, Any]:
        if intent.market != Market.JP:
            raise KabuStationMappingError("kabu Station mapper only supports JP market")
        if intent.quantity % 100 != 0:
            raise KabuStationMappingError("JP equity quantity must be a 100 share lot")

        return {
            "Symbol": self._symbol_code(intent.symbol),
            "Exchange": self.official_exchange,
            "SecurityType": 1,
            "Side": self._official_side(intent.side),
            "CashMargin": 1,
            "DelivType": self._cash_delivery_type(intent.side),
            "FundType": self._cash_fund_type(intent.side),
            "AccountType": self.account_type,
            "Qty": intent.quantity,
            "FrontOrderType": self._official_front_order_type(intent.order_style),
            "Price": intent.limit_price,
            "ExpireDay": self.expire_day,
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
    def _official_side(side: Side) -> str:
        if side == Side.BUY:
            return "2"
        if side == Side.SELL:
            return "1"
        raise KabuStationMappingError(f"unsupported side: {side}")

    @staticmethod
    def _cash_delivery_type(side: Side) -> int:
        if side == Side.BUY:
            return 2
        if side == Side.SELL:
            return 0
        raise KabuStationMappingError(f"unsupported side: {side}")

    def _cash_fund_type(self, side: Side) -> str:
        if side == Side.BUY:
            return self.buy_fund_type
        if side == Side.SELL:
            return "  "
        raise KabuStationMappingError(f"unsupported side: {side}")

    @staticmethod
    def _order_type(order_style: OrderStyle) -> str:
        if order_style in {OrderStyle.PASSIVE_LIMIT, OrderStyle.AGGRESSIVE_LIMIT}:
            return "LIMIT"
        raise KabuStationMappingError(
            f"unsupported order style for kabu Station mapper: {order_style}"
        )

    @staticmethod
    def _official_front_order_type(order_style: OrderStyle) -> int:
        if order_style in {OrderStyle.PASSIVE_LIMIT, OrderStyle.AGGRESSIVE_LIMIT}:
            return 20
        raise KabuStationMappingError(
            f"unsupported order style for kabu Station mapper: {order_style}"
        )
