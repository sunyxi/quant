from __future__ import annotations

import json
import socket
import unittest
from typing import Any
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.request import Request
from urllib.response import addinfourl

from autotrade.execution.kabu_station import (
    KabuStationAuthError,
    KabuStationClientError,
    KabuStationEnvironment,
    KabuStationLocalhostHttpTransport,
    KabuStationRateLimitError,
    KabuStationServerError,
    KabuStationTokenClient,
    KabuStationTransportConnectionError,
    KabuStationTransportTimeoutError,
    _LoopbackRedirectHandler,
)


class FakeResponse:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self._body = body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def read(self) -> bytes:
        return self._body

    def getcode(self) -> int:
        return self.status


class FakeOpener:
    def __init__(
        self,
        payload: Any = {"ok": True},
        *,
        status: int = 200,
        raw_body: bytes | None = None,
        error: Exception | None = None,
    ) -> None:
        self.payload = payload
        self.status = status
        self.raw_body = raw_body
        self.error = error
        self.requests: list[dict[str, Any]] = []

    def open(self, request: Any, timeout: float) -> FakeResponse:
        body = request.data
        self.requests.append(
            {
                "method": request.get_method(),
                "url": request.full_url,
                "api_key": request.get_header("X-api-key"),
                "content_type": request.get_header("Content-type"),
                "payload": json.loads(body.decode("utf-8")) if body else None,
                "timeout": timeout,
            }
        )
        if self.error is not None:
            raise self.error
        response_body = (
            self.raw_body
            if self.raw_body is not None
            else json.dumps(self.payload).encode("utf-8")
        )
        if self.status >= 400:
            raise HTTPError(
                request.full_url,
                self.status,
                "error",
                hdrs=None,
                fp=addinfourl(
                    fp=BytesReader(response_body),
                    headers={},
                    url=request.full_url,
                    code=self.status,
                ),
            )
        return FakeResponse(self.status, response_body)


class BytesReader:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def read(self, *args: Any) -> bytes:
        return self.body

    def close(self) -> None:
        return None


class KabuStationLocalhostHttpTransportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base_url = "http://localhost:18081"

    def tearDown(self) -> None:
        return None

    def test_post_json_sends_payload_and_headers_to_localhost(self) -> None:
        opener = FakeOpener()
        transport = KabuStationLocalhostHttpTransport(opener=opener)

        response = transport.post_json(
            f"{self.base_url}/kabusapi/token",
            {"APIPassword": "test-password"},
            headers={"X-API-KEY": "token-123"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.payload, {"ok": True})
        self.assertEqual(
            opener.requests,
            [
                {
                    "method": "POST",
                    "url": "http://localhost:18081/kabusapi/token",
                    "api_key": "token-123",
                    "content_type": "application/json",
                    "payload": {"APIPassword": "test-password"},
                    "timeout": 5.0,
                }
            ],
        )

    def test_put_json_sends_payload_to_localhost(self) -> None:
        opener = FakeOpener()
        transport = KabuStationLocalhostHttpTransport(
            opener=opener, policy=lambda method, url: None
        )

        response = transport.put_json(
            f"{self.base_url}/kabusapi/custom-put-contract",
            {"OrderId": "order-1"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(opener.requests[0]["method"], "PUT")
        self.assertEqual(
            opener.requests[0]["payload"],
            {"OrderId": "order-1"},
        )

    def test_get_json_encodes_query_and_headers_to_localhost(self) -> None:
        opener = FakeOpener(payload=[{"ID": "order-1"}])
        transport = KabuStationLocalhostHttpTransport(opener=opener)

        response = transport.get_json(
            f"{self.base_url}/kabusapi/orders",
            query={"product": "1", "symbol": "7203"},
            headers={"X-API-KEY": "token-123"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.payload, [{"ID": "order-1"}])
        self.assertEqual(opener.requests[0]["method"], "GET")
        self.assertEqual(
            opener.requests[0]["url"],
            "http://localhost:18081/kabusapi/orders?product=1&symbol=7203",
        )
        self.assertEqual(opener.requests[0]["api_key"], "token-123")

    def test_empty_body_raises_client_error(self) -> None:
        transport = KabuStationLocalhostHttpTransport(opener=FakeOpener(raw_body=b""))

        with self.assertRaises(KabuStationClientError):
            transport.get_json(f"{self.base_url}/kabusapi/orders")

    def test_non_json_response_raises_client_error(self) -> None:
        transport = KabuStationLocalhostHttpTransport(
            opener=FakeOpener(raw_body=b"not-json")
        )

        with self.assertRaises(KabuStationClientError):
            transport.get_json(f"{self.base_url}/kabusapi/orders")

    def test_http_error_preserves_status_and_payload(self) -> None:
        transport = KabuStationLocalhostHttpTransport(
            opener=FakeOpener(status=400, payload={"Code": 4001001})
        )

        response = transport.get_json(f"{self.base_url}/kabusapi/orders")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.payload, {"Code": 4001001})

    def test_rejects_non_localhost_url_before_request(self) -> None:
        opener = FakeOpener()
        transport = KabuStationLocalhostHttpTransport(opener=opener)

        with self.assertRaises(KabuStationClientError):
            transport.get_json("https://example.com/kabusapi/orders")

        self.assertEqual(opener.requests, [])

    def test_rejects_remote_redirect(self) -> None:
        opener = FakeOpener(
            error=HTTPError(
                f"{self.base_url}/kabusapi/orders",
                302,
                "Found",
                hdrs={"Location": "http://example.com/kabusapi/orders"},
                fp=None,
            )
        )
        transport = KabuStationLocalhostHttpTransport(opener=opener)

        with self.assertRaises(KabuStationClientError):
            transport.get_json(f"{self.base_url}/kabusapi/orders")

    def test_rejects_userinfo_url_before_request(self) -> None:
        transport = KabuStationLocalhostHttpTransport()

        with self.assertRaises(KabuStationClientError):
            transport.get_json("http://user:pass@localhost:18081/kabusapi/orders")

    def test_default_policy_rejects_mutating_broker_endpoints(self) -> None:
        opener = FakeOpener()
        transport = KabuStationLocalhostHttpTransport(opener=opener)

        with self.assertRaises(KabuStationClientError):
            transport.post_json(f"{self.base_url}/kabusapi/sendorder", {})
        with self.assertRaises(KabuStationClientError):
            transport.put_json(f"{self.base_url}/kabusapi/cancelorder", {})

        self.assertEqual(opener.requests, [])

    def test_default_policy_rejects_percent_encoded_mutating_path(self) -> None:
        opener = FakeOpener()
        transport = KabuStationLocalhostHttpTransport(opener=opener)

        with self.assertRaises(KabuStationClientError):
            transport.post_json(
                f"{self.base_url}/%2Fkabusapi%2Fsendorder",
                {},
            )

        self.assertEqual(opener.requests, [])

    def test_redirect_handler_reapplies_readonly_policy(self) -> None:
        handler = _LoopbackRedirectHandler()
        request = Request(
            f"{self.base_url}/kabusapi/token",
            data=b"{}",
            method="POST",
        )

        with self.assertRaises(KabuStationClientError):
            handler.redirect_request(
                request,
                None,
                302,
                "Found",
                {},
                f"{self.base_url}/kabusapi/sendorder",
            )

    def test_empty_http_error_body_preserves_status_typed_error(self) -> None:
        cases = (
            (401, KabuStationAuthError),
            (429, KabuStationRateLimitError),
            (500, KabuStationServerError),
        )
        for status, expected_error in cases:
            with self.subTest(status=status):
                transport = KabuStationLocalhostHttpTransport(
                    opener=FakeOpener(status=status, raw_body=b"")
                )
                client = KabuStationTokenClient(
                    environment=KabuStationEnvironment.test(),
                    transport=transport,
                )

                with self.assertRaises(expected_error):
                    client.fetch_token("test-password")

    def test_non_json_http_error_body_preserves_status_typed_error(self) -> None:
        cases = (
            (401, KabuStationAuthError),
            (429, KabuStationRateLimitError),
            (503, KabuStationServerError),
        )
        for status, expected_error in cases:
            with self.subTest(status=status):
                transport = KabuStationLocalhostHttpTransport(
                    opener=FakeOpener(status=status, raw_body=b"<html>down</html>")
                )
                client = KabuStationTokenClient(
                    environment=KabuStationEnvironment.test(),
                    transport=transport,
                )

                with self.assertRaises(expected_error):
                    client.fetch_token("test-password")

    def test_default_opener_is_built_once_per_transport(self) -> None:
        opener = FakeOpener()
        with patch(
            "autotrade.execution.kabu_station.build_opener",
            return_value=opener,
        ) as build:
            transport = KabuStationLocalhostHttpTransport()
            transport.get_json(f"{self.base_url}/kabusapi/orders")
            transport.get_json(f"{self.base_url}/kabusapi/positions")

        build.assert_called_once()

    def test_connection_refused_raises_sanitized_connection_error(self) -> None:
        transport = KabuStationLocalhostHttpTransport(
            opener=FakeOpener(error=URLError(ConnectionRefusedError())),
            timeout_seconds=0.1,
        )

        with self.assertRaises(KabuStationTransportConnectionError):
            transport.get_json("http://localhost:1/kabusapi/orders")

    def test_timeout_raises_sanitized_timeout_error(self) -> None:
        class TimeoutOpener:
            def open(self, request: Any, timeout: float) -> Any:
                raise socket.timeout("secret-token-123")

        transport = KabuStationLocalhostHttpTransport(
            opener=TimeoutOpener(),
            timeout_seconds=0.1,
        )

        with self.assertRaises(KabuStationTransportTimeoutError) as context:
            transport.get_json(
                f"{self.base_url}/kabusapi/orders",
                headers={"X-API-KEY": "secret-token-123"},
            )

        self.assertNotIn("secret-token-123", str(context.exception))

    def test_opener_error_does_not_leak_password_or_token(self) -> None:
        class FailingOpener:
            def open(self, request: Any, timeout: float) -> Any:
                raise URLError("bad-password token-123")

        transport = KabuStationLocalhostHttpTransport(
            opener=FailingOpener(),
            timeout_seconds=0.1,
        )

        with self.assertRaises(KabuStationTransportConnectionError) as context:
            transport.post_json(
                f"{self.base_url}/kabusapi/token",
                {"APIPassword": "bad-password"},
                headers={"X-API-KEY": "token-123"},
            )

        self.assertNotIn("bad-password", str(context.exception))
        self.assertNotIn("token-123", str(context.exception))

    def test_permission_error_is_not_misclassified_as_connection_failure(self) -> None:
        transport = KabuStationLocalhostHttpTransport(
            opener=FakeOpener(
                error=URLError(PermissionError("socket denied secret-token-123"))
            )
        )

        with self.assertRaises(KabuStationClientError) as context:
            transport.get_json(f"{self.base_url}/kabusapi/orders")

        self.assertNotIsInstance(
            context.exception,
            KabuStationTransportConnectionError,
        )
        self.assertIn("operating system", str(context.exception))
        self.assertNotIn("secret-token-123", str(context.exception))


if __name__ == "__main__":
    unittest.main()
