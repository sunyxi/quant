from __future__ import annotations

import unittest
from dataclasses import dataclass
from typing import Any

from autotrade.execution.kabu_station import (
    KabuStationAuthError,
    KabuStationClientError,
    KabuStationEnvironment,
    KabuStationRateLimitError,
    KabuStationServerError,
    KabuStationTokenClient,
)


@dataclass(frozen=True)
class FakeResponse:
    status_code: int
    payload: dict[str, Any]


class FakeTransport:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.requests: list[dict[str, Any]] = []

    def post_json(self, url: str, payload: dict[str, Any]) -> FakeResponse:
        self.requests.append({"url": url, "payload": payload})
        return self.response


class KabuStationTokenClientTests(unittest.TestCase):
    def test_fetch_token_posts_password_to_test_token_endpoint(self) -> None:
        transport = FakeTransport(
            FakeResponse(
                status_code=200,
                payload={"ResultCode": 0, "Token": "token-123"},
            )
        )
        client = KabuStationTokenClient(
            environment=KabuStationEnvironment.test(),
            transport=transport,
        )

        token = client.fetch_token("test-password")

        self.assertEqual(token, "token-123")
        self.assertEqual(
            transport.requests,
            [
                {
                    "url": "http://localhost:18081/kabusapi/token",
                    "payload": {"APIPassword": "test-password"},
                }
            ],
        )

    def test_fetch_token_rejects_empty_password_before_transport(self) -> None:
        transport = FakeTransport(FakeResponse(status_code=200, payload={}))
        client = KabuStationTokenClient(
            environment=KabuStationEnvironment.test(),
            transport=transport,
        )

        with self.assertRaises(KabuStationClientError):
            client.fetch_token("")

        self.assertEqual(transport.requests, [])

    def test_fetch_token_maps_unauthorized_response(self) -> None:
        client = KabuStationTokenClient(
            environment=KabuStationEnvironment.test(),
            transport=FakeTransport(FakeResponse(status_code=401, payload={})),
        )

        with self.assertRaises(KabuStationAuthError):
            client.fetch_token("bad-password")

    def test_fetch_token_maps_rate_limit_response(self) -> None:
        client = KabuStationTokenClient(
            environment=KabuStationEnvironment.test(),
            transport=FakeTransport(FakeResponse(status_code=429, payload={})),
        )

        with self.assertRaises(KabuStationRateLimitError):
            client.fetch_token("test-password")

    def test_fetch_token_maps_server_error_response(self) -> None:
        client = KabuStationTokenClient(
            environment=KabuStationEnvironment.test(),
            transport=FakeTransport(FakeResponse(status_code=500, payload={})),
        )

        with self.assertRaises(KabuStationServerError):
            client.fetch_token("test-password")

    def test_fetch_token_requires_token_field_on_success(self) -> None:
        client = KabuStationTokenClient(
            environment=KabuStationEnvironment.test(),
            transport=FakeTransport(FakeResponse(status_code=200, payload={})),
        )

        with self.assertRaises(KabuStationClientError):
            client.fetch_token("test-password")


if __name__ == "__main__":
    unittest.main()
