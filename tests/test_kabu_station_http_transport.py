from __future__ import annotations

import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from autotrade.execution.kabu_station import (
    KabuStationClientError,
    KabuStationLocalhostHttpTransport,
)


class RecordingHandler(BaseHTTPRequestHandler):
    requests: list[dict[str, Any]] = []
    response_status = 200
    response_payload: dict[str, Any] | list[dict[str, Any]] | None = {"ok": True}

    def do_POST(self) -> None:
        self._record_with_body()

    def do_PUT(self) -> None:
        self._record_with_body()

    def do_GET(self) -> None:
        self._record(None)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _record_with_body(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b""
        payload = json.loads(body.decode("utf-8")) if body else None
        self._record(payload)

    def _record(self, payload: dict[str, Any] | None) -> None:
        type(self).requests.append(
            {
                "method": self.command,
                "path": self.path,
                "api_key": self.headers.get("X-API-KEY"),
                "content_type": self.headers.get("Content-Type"),
                "payload": payload,
            }
        )
        self.send_response(type(self).response_status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if type(self).response_payload is not None:
            self.wfile.write(
                json.dumps(type(self).response_payload).encode("utf-8")
            )


class KabuStationLocalhostHttpTransportTests(unittest.TestCase):
    def setUp(self) -> None:
        RecordingHandler.requests = []
        RecordingHandler.response_status = 200
        RecordingHandler.response_payload = {"ok": True}
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), RecordingHandler)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_post_json_sends_payload_and_headers_to_localhost(self) -> None:
        transport = KabuStationLocalhostHttpTransport()

        response = transport.post_json(
            f"{self.base_url}/kabusapi/token",
            {"APIPassword": "test-password"},
            headers={"X-API-KEY": "token-123"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.payload, {"ok": True})
        self.assertEqual(
            RecordingHandler.requests,
            [
                {
                    "method": "POST",
                    "path": "/kabusapi/token",
                    "api_key": "token-123",
                    "content_type": "application/json",
                    "payload": {"APIPassword": "test-password"},
                }
            ],
        )

    def test_put_json_sends_payload_to_localhost(self) -> None:
        transport = KabuStationLocalhostHttpTransport()

        response = transport.put_json(
            f"{self.base_url}/kabusapi/cancelorder",
            {"OrderId": "order-1"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(RecordingHandler.requests[0]["method"], "PUT")
        self.assertEqual(
            RecordingHandler.requests[0]["payload"],
            {"OrderId": "order-1"},
        )

    def test_get_json_encodes_query_and_headers_to_localhost(self) -> None:
        RecordingHandler.response_payload = [{"ID": "order-1"}]
        transport = KabuStationLocalhostHttpTransport()

        response = transport.get_json(
            f"{self.base_url}/kabusapi/orders",
            query={"product": "1", "symbol": "7203"},
            headers={"X-API-KEY": "token-123"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.payload, [{"ID": "order-1"}])
        self.assertEqual(RecordingHandler.requests[0]["method"], "GET")
        self.assertEqual(
            RecordingHandler.requests[0]["path"],
            "/kabusapi/orders?product=1&symbol=7203",
        )
        self.assertEqual(RecordingHandler.requests[0]["api_key"], "token-123")

    def test_empty_body_returns_empty_payload(self) -> None:
        RecordingHandler.response_payload = None
        transport = KabuStationLocalhostHttpTransport()

        response = transport.get_json(f"{self.base_url}/kabusapi/orders")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.payload, {})

    def test_rejects_non_localhost_url_before_request(self) -> None:
        transport = KabuStationLocalhostHttpTransport()

        with self.assertRaises(KabuStationClientError):
            transport.get_json("https://example.com/kabusapi/orders")

        self.assertEqual(RecordingHandler.requests, [])

    def test_transport_errors_raise_client_error(self) -> None:
        transport = KabuStationLocalhostHttpTransport(timeout_seconds=0.1)

        with self.assertRaises(KabuStationClientError):
            transport.get_json("http://localhost:1/kabusapi/orders")


if __name__ == "__main__":
    unittest.main()
