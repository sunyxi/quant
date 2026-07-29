from __future__ import annotations

import unittest
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from autotrade.core.models import Market, OrderIntent, OrderStyle, Side
from autotrade.execution.kabu_station import (
    KabuStationAuthError,
    KabuStationClientError,
    KabuStationEnvironment,
    KabuStationRateLimitError,
    KabuStationSendOrderClient,
    KabuStationServerError,
)


@dataclass(frozen=True)
class FakeResponse:
    status_code: int
    payload: dict[str, Any]


class FakeTransport:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.requests: list[dict[str, Any]] = []

    def post_json(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> FakeResponse:
        self.requests.append({"url": url, "payload": payload, "headers": headers})
        return self.response


def _intent() -> OrderIntent:
    return OrderIntent(
        client_order_id="client-1",
        strategy_id="test_strategy",
        symbol="7203.T",
        market=Market.JP,
        side=Side.BUY,
        quantity=100,
        order_style=OrderStyle.PASSIVE_LIMIT,
        limit_price=1000,
        stop_price=990,
        take_profit_price=1020,
        created_at=datetime(2026, 7, 28, 9, 30, tzinfo=ZoneInfo("Asia/Tokyo")),
    )


class KabuStationSendOrderClientTests(unittest.TestCase):
    def test_submit_cash_order_posts_payload_with_api_key_header(self) -> None:
        transport = FakeTransport(
            FakeResponse(status_code=200, payload={"Result": 0, "OrderId": "order-1"})
        )
        client = KabuStationSendOrderClient(
            environment=KabuStationEnvironment.test(),
            transport=transport,
        )

        order_id = client.submit_cash_order(_intent(), api_token="token-123")

        self.assertEqual(order_id, "order-1")
        self.assertEqual(len(transport.requests), 1)
        self.assertEqual(
            transport.requests[0]["url"],
            "http://localhost:18081/kabusapi/sendorder",
        )
        self.assertEqual(transport.requests[0]["headers"], {"X-API-KEY": "token-123"})
        self.assertEqual(transport.requests[0]["payload"]["Symbol"], "7203")
        self.assertEqual(transport.requests[0]["payload"]["Side"], "2")

    def test_submit_cash_order_rejects_empty_token_before_transport(self) -> None:
        transport = FakeTransport(FakeResponse(status_code=200, payload={}))
        client = KabuStationSendOrderClient(
            environment=KabuStationEnvironment.test(),
            transport=transport,
        )

        with self.assertRaises(KabuStationClientError):
            client.submit_cash_order(_intent(), api_token="")

        self.assertEqual(transport.requests, [])

    def test_submit_cash_order_maps_unauthorized_response(self) -> None:
        client = KabuStationSendOrderClient(
            environment=KabuStationEnvironment.test(),
            transport=FakeTransport(FakeResponse(status_code=401, payload={})),
        )

        with self.assertRaises(KabuStationAuthError):
            client.submit_cash_order(_intent(), api_token="bad-token")

    def test_submit_cash_order_maps_rate_limit_response(self) -> None:
        client = KabuStationSendOrderClient(
            environment=KabuStationEnvironment.test(),
            transport=FakeTransport(FakeResponse(status_code=429, payload={})),
        )

        with self.assertRaises(KabuStationRateLimitError):
            client.submit_cash_order(_intent(), api_token="token-123")

    def test_submit_cash_order_maps_server_error_response(self) -> None:
        client = KabuStationSendOrderClient(
            environment=KabuStationEnvironment.test(),
            transport=FakeTransport(FakeResponse(status_code=500, payload={})),
        )

        with self.assertRaises(KabuStationServerError):
            client.submit_cash_order(_intent(), api_token="token-123")

    def test_submit_cash_order_requires_order_id_on_success(self) -> None:
        client = KabuStationSendOrderClient(
            environment=KabuStationEnvironment.test(),
            transport=FakeTransport(FakeResponse(status_code=200, payload={})),
        )

        with self.assertRaises(KabuStationClientError):
            client.submit_cash_order(_intent(), api_token="token-123")


if __name__ == "__main__":
    unittest.main()
