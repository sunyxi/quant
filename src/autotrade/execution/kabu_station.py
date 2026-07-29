from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from autotrade.core.models import Market, OrderIntent, OrderStyle, Side


class KabuStationClientError(RuntimeError):
    pass


class KabuStationAuthError(KabuStationClientError):
    pass


class KabuStationRateLimitError(KabuStationClientError):
    pass


class KabuStationServerError(KabuStationClientError):
    pass


class KabuStationMappingError(ValueError):
    pass


class JsonPostResponse(Protocol):
    status_code: int
    payload: dict[str, Any]


class JsonPostTransport(Protocol):
    def post_json(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> JsonPostResponse:
        ...


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
class KabuStationTokenClient:
    environment: KabuStationEnvironment
    transport: JsonPostTransport
    mapper: KabuStationOrderMapper | None = None

    def fetch_token(self, api_password: str) -> str:
        mapper = self.mapper or KabuStationOrderMapper()
        try:
            payload = mapper.to_token_payload(api_password)
        except KabuStationMappingError as exc:
            raise KabuStationClientError(str(exc)) from exc

        response = self.transport.post_json(self.environment.token_url, payload)
        raise_for_kabu_station_status(response.status_code, "token request")
        token = response.payload.get("Token")
        if not isinstance(token, str) or not token:
            raise KabuStationClientError("token response did not include Token")
        return token


@dataclass(frozen=True)
class KabuStationSendOrderClient:
    environment: KabuStationEnvironment
    transport: JsonPostTransport
    mapper: KabuStationOrderMapper | None = None

    def submit_cash_order(self, intent: OrderIntent, api_token: str) -> str:
        if not api_token:
            raise KabuStationClientError("API token is required")

        mapper = self.mapper or KabuStationOrderMapper()
        try:
            payload = mapper.to_cash_sendorder_payload(intent)
        except KabuStationMappingError as exc:
            raise KabuStationClientError(str(exc)) from exc

        response = self.transport.post_json(
            self.environment.sendorder_url,
            payload,
            headers={"X-API-KEY": api_token},
        )
        raise_for_kabu_station_status(response.status_code, "sendorder request")
        order_id = response.payload.get("OrderId")
        if not isinstance(order_id, str) or not order_id:
            raise KabuStationClientError("sendorder response did not include OrderId")
        return order_id


def raise_for_kabu_station_status(status_code: int, operation: str) -> None:
    if status_code == 200:
        return
    if status_code in {401, 403}:
        raise KabuStationAuthError(f"kabu Station {operation} was unauthorized")
    if status_code == 429:
        raise KabuStationRateLimitError(f"kabu Station {operation} was rate limited")
    if status_code >= 500:
        raise KabuStationServerError(f"kabu Station {operation} failed server-side")
    raise KabuStationClientError(
        f"kabu Station {operation} failed with status {status_code}"
    )


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
