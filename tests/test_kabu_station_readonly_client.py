from __future__ import annotations

import unittest
from dataclasses import dataclass
from typing import Any

from autotrade.execution.kabu_station import (
    KabuStationAuthError,
    KabuStationClientError,
    KabuStationEnvironment,
    KabuStationRateLimitError,
    KabuStationReadOnlyClient,
    KabuStationServerError,
)


@dataclass(frozen=True)
class FakeResponse:
    status_code: int
    payload: Any


class FakeTransport:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.requests: list[dict[str, Any]] = []

    def get_json(
        self,
        url: str,
        query: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> FakeResponse:
        self.requests.append({"url": url, "query": query, "headers": headers})
        return self.response


class KabuStationReadOnlyClientTests(unittest.TestCase):
    def test_get_orders_sends_query_and_api_key_header(self) -> None:
        transport = FakeTransport(
            FakeResponse(
                status_code=200,
                payload=[
                    {
                        "ID": "order-1",
                        "Symbol": "7203",
                        "Side": "2",
                        "OrderQty": 100,
                        "CumQty": 0,
                        "State": 1,
                    }
                ],
            )
        )
        client = KabuStationReadOnlyClient(
            environment=KabuStationEnvironment.test(),
            transport=transport,
        )

        orders = client.get_orders(
            api_token="token-123",
            product="1",
            symbol="7203",
            details=False,
        )

        self.assertEqual(orders[0]["ID"], "order-1")
        self.assertEqual(
            transport.requests,
            [
                {
                    "url": "http://localhost:18081/kabusapi/orders",
                    "query": {
                        "product": "1",
                        "symbol": "7203",
                        "details": "false",
                    },
                    "headers": {"X-API-KEY": "token-123"},
                }
            ],
        )

    def test_get_positions_sends_product_query_and_api_key_header(self) -> None:
        transport = FakeTransport(
            FakeResponse(
                status_code=200,
                payload=[
                    {
                        "ExecutionID": "exec-1",
                        "Symbol": "7203",
                        "Side": "2",
                        "LeavesQty": 100,
                    }
                ],
            )
        )
        client = KabuStationReadOnlyClient(
            environment=KabuStationEnvironment.test(),
            transport=transport,
        )

        positions = client.get_positions(api_token="token-123", product="1")

        self.assertEqual(positions[0]["ExecutionID"], "exec-1")
        self.assertEqual(
            transport.requests,
            [
                {
                    "url": "http://localhost:18081/kabusapi/positions",
                    "query": {"product": "1"},
                    "headers": {"X-API-KEY": "token-123"},
                }
            ],
        )

    def test_get_orders_rejects_empty_token_before_transport(self) -> None:
        transport = FakeTransport(FakeResponse(status_code=200, payload=[]))
        client = KabuStationReadOnlyClient(
            environment=KabuStationEnvironment.test(),
            transport=transport,
        )

        with self.assertRaises(KabuStationClientError):
            client.get_orders(api_token="")

        self.assertEqual(transport.requests, [])

    def test_get_positions_requires_list_payload_on_success(self) -> None:
        client = KabuStationReadOnlyClient(
            environment=KabuStationEnvironment.test(),
            transport=FakeTransport(FakeResponse(status_code=200, payload={})),
        )

        with self.assertRaises(KabuStationClientError):
            client.get_positions(api_token="token-123")

    def test_get_orders_maps_unauthorized_response(self) -> None:
        client = KabuStationReadOnlyClient(
            environment=KabuStationEnvironment.test(),
            transport=FakeTransport(FakeResponse(status_code=401, payload={})),
        )

        with self.assertRaises(KabuStationAuthError):
            client.get_orders(api_token="bad-token")

    def test_get_orders_maps_rate_limit_response(self) -> None:
        client = KabuStationReadOnlyClient(
            environment=KabuStationEnvironment.test(),
            transport=FakeTransport(FakeResponse(status_code=429, payload={})),
        )

        with self.assertRaises(KabuStationRateLimitError):
            client.get_orders(api_token="token-123")

    def test_get_orders_maps_server_error_response(self) -> None:
        client = KabuStationReadOnlyClient(
            environment=KabuStationEnvironment.test(),
            transport=FakeTransport(FakeResponse(status_code=500, payload={})),
        )

        with self.assertRaises(KabuStationServerError):
            client.get_orders(api_token="token-123")


if __name__ == "__main__":
    unittest.main()
