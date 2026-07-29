from __future__ import annotations

import unittest
from dataclasses import dataclass
from typing import Any

from autotrade.execution.kabu_station import (
    KabuStationAuthError,
    KabuStationCancelOrderClient,
    KabuStationClientError,
    KabuStationEnvironment,
    KabuStationRateLimitError,
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

    def put_json(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> FakeResponse:
        self.requests.append({"url": url, "payload": payload, "headers": headers})
        return self.response


class KabuStationCancelOrderClientTests(unittest.TestCase):
    def test_cancel_order_puts_order_id_with_api_key_header(self) -> None:
        transport = FakeTransport(
            FakeResponse(status_code=200, payload={"Result": 0, "OrderId": "order-1"})
        )
        client = KabuStationCancelOrderClient(
            environment=KabuStationEnvironment.test(),
            transport=transport,
        )

        order_id = client.cancel_order("order-1", api_token="token-123")

        self.assertEqual(order_id, "order-1")
        self.assertEqual(
            transport.requests,
            [
                {
                    "url": "http://localhost:18081/kabusapi/cancelorder",
                    "payload": {"OrderId": "order-1"},
                    "headers": {"X-API-KEY": "token-123"},
                }
            ],
        )

    def test_cancel_order_rejects_empty_token_before_transport(self) -> None:
        transport = FakeTransport(FakeResponse(status_code=200, payload={}))
        client = KabuStationCancelOrderClient(
            environment=KabuStationEnvironment.test(),
            transport=transport,
        )

        with self.assertRaises(KabuStationClientError):
            client.cancel_order("order-1", api_token="")

        self.assertEqual(transport.requests, [])

    def test_cancel_order_rejects_empty_order_id_before_transport(self) -> None:
        transport = FakeTransport(FakeResponse(status_code=200, payload={}))
        client = KabuStationCancelOrderClient(
            environment=KabuStationEnvironment.test(),
            transport=transport,
        )

        with self.assertRaises(KabuStationClientError):
            client.cancel_order("", api_token="token-123")

        self.assertEqual(transport.requests, [])

    def test_cancel_order_maps_unauthorized_response(self) -> None:
        client = KabuStationCancelOrderClient(
            environment=KabuStationEnvironment.test(),
            transport=FakeTransport(FakeResponse(status_code=401, payload={})),
        )

        with self.assertRaises(KabuStationAuthError):
            client.cancel_order("order-1", api_token="bad-token")

    def test_cancel_order_maps_rate_limit_response(self) -> None:
        client = KabuStationCancelOrderClient(
            environment=KabuStationEnvironment.test(),
            transport=FakeTransport(FakeResponse(status_code=429, payload={})),
        )

        with self.assertRaises(KabuStationRateLimitError):
            client.cancel_order("order-1", api_token="token-123")

    def test_cancel_order_maps_server_error_response(self) -> None:
        client = KabuStationCancelOrderClient(
            environment=KabuStationEnvironment.test(),
            transport=FakeTransport(FakeResponse(status_code=500, payload={})),
        )

        with self.assertRaises(KabuStationServerError):
            client.cancel_order("order-1", api_token="token-123")

    def test_cancel_order_requires_order_id_on_success(self) -> None:
        client = KabuStationCancelOrderClient(
            environment=KabuStationEnvironment.test(),
            transport=FakeTransport(FakeResponse(status_code=200, payload={})),
        )

        with self.assertRaises(KabuStationClientError):
            client.cancel_order("order-1", api_token="token-123")


if __name__ == "__main__":
    unittest.main()
