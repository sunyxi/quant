from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from autotrade.execution.kabu_station import (
    KabuStationClientError,
    KabuStationEnvironment,
    KabuStationProbeReportReader,
    KabuStationProbeReportWriter,
    KabuStationReadOnlyProbe,
    KabuStationTokenClient,
    KabuStationLocalhostHttpTransport,
    KabuStationTransportConnectionError,
    KabuStationTransportPolicyError,
    KabuStationTransportSystemError,
    KabuStationTransportTimeoutError,
)


class FakeTokenClient:
    def __init__(self, token: str = "token-123", error: Exception | None = None) -> None:
        self.token = token
        self.error = error
        self.passwords: list[str] = []

    def fetch_token(self, api_password: str) -> str:
        self.passwords.append(api_password)
        if self.error is not None:
            raise self.error
        return self.token


class FakeReadOnlyClient:
    def __init__(
        self,
        orders: list[dict[str, Any]] | None = None,
        positions: list[dict[str, Any]] | None = None,
        orders_error: Exception | None = None,
        positions_error: Exception | None = None,
    ) -> None:
        self.orders = orders or []
        self.positions = positions or []
        self.orders_error = orders_error
        self.positions_error = positions_error
        self.tokens: list[str] = []

    def get_orders(
        self,
        api_token: str,
        product: str | None = None,
        symbol: str | None = None,
        details: bool | None = None,
    ) -> list[dict[str, Any]]:
        self.tokens.append(api_token)
        if self.orders_error is not None:
            raise self.orders_error
        return self.orders

    def get_positions(
        self,
        api_token: str,
        product: str | None = None,
        symbol: str | None = None,
    ) -> list[dict[str, Any]]:
        self.tokens.append(api_token)
        if self.positions_error is not None:
            raise self.positions_error
        return self.positions


@dataclass(frozen=True)
class FailingMapper:
    def to_broker_state_snapshot(
        self,
        *,
        orders: list[dict[str, Any]],
        positions: list[dict[str, Any]],
    ) -> Any:
        raise KabuStationClientError("bad broker payload")


class KabuStationReadOnlyProbeTests(unittest.TestCase):
    def test_fake_transport_probe_success_returns_sanitized_counts(self) -> None:
        token_client = FakeTokenClient()
        readonly_client = FakeReadOnlyClient(
            orders=[{"ID": "order-1", "Symbol": "7203", "LeavesQty": 100}],
            positions=[
                {
                    "ExecutionID": "position-1",
                    "Symbol": "7203",
                    "Side": "2",
                    "LeavesQty": 100,
                }
            ],
        )
        probe = KabuStationReadOnlyProbe(
            environment_name="test",
            environment=KabuStationEnvironment.test(),
            token_client=token_client,
            readonly_client=readonly_client,
        )

        result = probe.run(api_password="secret-password")
        payload = result.to_dict()

        self.assertEqual(payload["connection_status"], "ok")
        self.assertEqual(payload["authentication_status"], "ok")
        self.assertEqual(payload["orders_payload_status"], "ok")
        self.assertEqual(payload["positions_payload_status"], "ok")
        self.assertEqual(payload["snapshot_mapping_status"], "ok")
        self.assertEqual(payload["order_count"], 1)
        self.assertEqual(payload["position_count"], 1)
        self.assertNotIn("secret-password", json.dumps(payload))
        self.assertNotIn("token-123", json.dumps(payload))
        self.assertNotIn("order-1", json.dumps(payload))
        self.assertNotIn("position-1", json.dumps(payload))

    def test_orders_error_stops_probe_with_sanitized_failure_category(self) -> None:
        probe = KabuStationReadOnlyProbe(
            environment_name="test",
            environment=KabuStationEnvironment.test(),
            token_client=FakeTokenClient(),
            readonly_client=FakeReadOnlyClient(
                orders_error=KabuStationClientError("orders failed token-123")
            ),
        )

        result = probe.run(api_password="secret-password")
        payload = result.to_dict()

        self.assertEqual(payload["orders_payload_status"], "failed")
        self.assertEqual(payload["positions_payload_status"], "not-run")
        self.assertEqual(payload["sanitized_failure_category"], "orders")
        self.assertNotIn("token-123", json.dumps(payload))

    def test_orders_connection_drop_is_reported_as_connection_failure(self) -> None:
        probe = KabuStationReadOnlyProbe(
            environment_name="test",
            environment=KabuStationEnvironment.test(),
            token_client=FakeTokenClient(),
            readonly_client=FakeReadOnlyClient(
                orders_error=KabuStationTransportConnectionError("connection lost")
            ),
        )

        payload = probe.run(api_password="secret-password").to_dict()

        self.assertEqual(payload["connection_status"], "ok")
        self.assertEqual(payload["orders_payload_status"], "failed")
        self.assertEqual(payload["sanitized_failure_category"], "connection")

    def test_positions_timeout_is_reported_as_timeout_failure(self) -> None:
        probe = KabuStationReadOnlyProbe(
            environment_name="test",
            environment=KabuStationEnvironment.test(),
            token_client=FakeTokenClient(),
            readonly_client=FakeReadOnlyClient(
                positions_error=KabuStationTransportTimeoutError("timed out")
            ),
        )

        payload = probe.run(api_password="secret-password").to_dict()

        self.assertEqual(payload["connection_status"], "ok")
        self.assertEqual(payload["positions_payload_status"], "failed")
        self.assertEqual(payload["sanitized_failure_category"], "timeout")

    def test_preconnection_policy_error_does_not_claim_connection_success(self) -> None:
        environment = KabuStationEnvironment(base_url="http://example.com:18081")
        transport = KabuStationLocalhostHttpTransport()
        probe = KabuStationReadOnlyProbe(
            environment_name="test",
            environment=environment,
            token_client=KabuStationTokenClient(
                environment=environment,
                transport=transport,
            ),
            readonly_client=FakeReadOnlyClient(),
        )

        payload = probe.run(api_password="secret-password").to_dict()

        self.assertEqual(payload["connection_status"], "not-run")
        self.assertEqual(payload["authentication_status"], "not-run")
        self.assertEqual(payload["sanitized_failure_category"], "configuration")

    def test_read_policy_errors_are_reported_as_configuration_failures(self) -> None:
        cases = (
            (
                FakeReadOnlyClient(
                    orders_error=KabuStationTransportPolicyError("redirect rejected")
                ),
                "orders_payload_status",
            ),
            (
                FakeReadOnlyClient(
                    positions_error=KabuStationTransportPolicyError(
                        "redirect rejected"
                    )
                ),
                "positions_payload_status",
            ),
        )
        for readonly_client, failed_status in cases:
            with self.subTest(status=failed_status):
                probe = KabuStationReadOnlyProbe(
                    environment_name="test",
                    environment=KabuStationEnvironment.test(),
                    token_client=FakeTokenClient(),
                    readonly_client=readonly_client,
                )

                payload = probe.run(api_password="secret-password").to_dict()

                self.assertEqual(payload["connection_status"], "ok")
                self.assertEqual(payload[failed_status], "failed")
                self.assertEqual(
                    payload["sanitized_failure_category"],
                    "configuration",
                )

    def test_system_errors_preserve_probe_stage_evidence(self) -> None:
        token_failure = KabuStationReadOnlyProbe(
            environment_name="test",
            environment=KabuStationEnvironment.test(),
            token_client=FakeTokenClient(
                error=KabuStationTransportSystemError("socket denied")
            ),
            readonly_client=FakeReadOnlyClient(),
        ).run(api_password="secret-password")
        orders_failure = KabuStationReadOnlyProbe(
            environment_name="test",
            environment=KabuStationEnvironment.test(),
            token_client=FakeTokenClient(),
            readonly_client=FakeReadOnlyClient(
                orders_error=KabuStationTransportSystemError("socket denied")
            ),
        ).run(api_password="secret-password")

        self.assertEqual(token_failure.connection_status, "not-run")
        self.assertEqual(token_failure.authentication_status, "not-run")
        self.assertEqual(token_failure.sanitized_failure_category, "system")
        self.assertEqual(orders_failure.connection_status, "ok")
        self.assertEqual(orders_failure.authentication_status, "ok")
        self.assertEqual(orders_failure.orders_payload_status, "failed")
        self.assertEqual(orders_failure.sanitized_failure_category, "system")

    def test_snapshot_mapping_error_is_reported_without_raw_payload(self) -> None:
        probe = KabuStationReadOnlyProbe(
            environment_name="test",
            environment=KabuStationEnvironment.test(),
            token_client=FakeTokenClient(),
            readonly_client=FakeReadOnlyClient(
                orders=[{"ID": "order-1", "Symbol": "7203", "LeavesQty": 100}],
                positions=[],
            ),
            mapper=FailingMapper(),
        )

        result = probe.run(api_password="secret-password")
        payload = result.to_dict()

        self.assertEqual(payload["snapshot_mapping_status"], "failed")
        self.assertEqual(payload["sanitized_failure_category"], "snapshot_mapping")
        self.assertNotIn("order-1", json.dumps(payload))

    def test_probe_report_json_round_trip_and_unknown_schema_rejected(self) -> None:
        result = KabuStationReadOnlyProbe(
            environment_name="test",
            environment=KabuStationEnvironment.test(),
            token_client=FakeTokenClient(),
            readonly_client=FakeReadOnlyClient(),
        ).run(api_password="secret-password")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "probe-report.json"
            KabuStationProbeReportWriter().write(path, result)
            loaded = KabuStationProbeReportReader().read(path)

            self.assertEqual(loaded.to_dict(), result.to_dict())
            raw = json.loads(path.read_text(encoding="utf-8"))
            raw["schema_version"] = "999"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaises(KabuStationClientError):
                KabuStationProbeReportReader().read(path)

    def test_probe_report_writer_wraps_filesystem_error(self) -> None:
        result = KabuStationReadOnlyProbe(
            environment_name="test",
            environment=KabuStationEnvironment.test(),
            token_client=FakeTokenClient(),
            readonly_client=FakeReadOnlyClient(),
        ).run(api_password="secret-password")

        with tempfile.TemporaryDirectory() as tmpdir:
            parent_file = Path(tmpdir) / "not-a-directory"
            parent_file.write_text("occupied", encoding="utf-8")
            with self.assertRaises(KabuStationClientError) as context:
                KabuStationProbeReportWriter().write(
                    parent_file / "probe.json",
                    result,
                )

        self.assertIn("could not write", str(context.exception))
        self.assertNotIn(str(parent_file), str(context.exception))


if __name__ == "__main__":
    unittest.main()
