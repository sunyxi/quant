from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from autotrade.execution.moomoo import (
    MIN_MOOMOO_API_VERSION,
    MoomooApiSdk,
    MoomooConfigurationError,
    MoomooDependencyError,
    MoomooDiscoveryReportReader,
    MoomooDiscoveryReportWriter,
    MoomooEndpoint,
    MoomooReadOnlyDiscovery,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class FakeQuoteContext:
    def __init__(
        self,
        *,
        global_state: tuple[int, object],
        user_info: tuple[int, object],
    ) -> None:
        self.global_state = global_state
        self.user_info = user_info
        self.closed = False

    def get_global_state(self) -> tuple[int, object]:
        return self.global_state

    def get_user_info(self) -> tuple[int, object]:
        return self.user_info

    def close(self) -> None:
        self.closed = True


class FakeTradeContext:
    def __init__(self, accounts: tuple[int, object]) -> None:
        self.accounts = accounts
        self.closed = False

    def get_acc_list(self) -> tuple[int, object]:
        return self.accounts

    def close(self) -> None:
        self.closed = True


class NonListRecordsPayload:
    def to_dict(self, orient: str) -> tuple[str, ...]:
        if orient != "records":
            raise AssertionError("unexpected orientation")
        return ("not-a-record-list",)

    def __iter__(self):
        return iter(("sensitive-column-name",))


class FakeSdk:
    ret_ok = 0

    def __init__(
        self,
        *,
        version: str = MIN_MOOMOO_API_VERSION,
        global_state: tuple[int, object] | None = None,
        user_info: tuple[int, object] | None = None,
        accounts: tuple[int, object] | None = None,
    ) -> None:
        if global_state is None:
            global_state = (
                0,
                {
                    "server_ver": "10.9.6918",
                    "qot_logined": True,
                    "trd_logined": True,
                },
            )
        if user_info is None:
            user_info = (
                0,
                {
                    "user_id": "sensitive-user-id",
                    "nick_name": "sensitive-name",
                    "us_qot_right": "LV3",
                    "jp_qot_right": "LV1",
                },
            )
        if accounts is None:
            accounts = (
                0,
                [
                    {
                        "acc_id": "sensitive-paper-account",
                        "card_num": "sensitive-card",
                        "trd_env": "SIMULATE",
                        "trdmarket_auth": ["US"],
                    },
                    {
                        "acc_id": "sensitive-real-account",
                        "trd_env": "REAL",
                        "trdmarket_auth": ["US"],
                    },
                ],
            )
        self.version = version
        self.quote_context = FakeQuoteContext(
            global_state=global_state,
            user_info=user_info,
        )
        self.trade_context = FakeTradeContext(accounts)
        self.create_quote_count = 0
        self.create_trade_count = 0

    def create_quote_context(self, endpoint: MoomooEndpoint) -> FakeQuoteContext:
        self.create_quote_count += 1
        return self.quote_context

    def create_us_trade_context(self, endpoint: MoomooEndpoint) -> FakeTradeContext:
        self.create_trade_count += 1
        return self.trade_context


class MoomooEndpointTests(unittest.TestCase):
    def test_accepts_supported_loopback_hosts(self) -> None:
        for host in ["127.0.0.1", "localhost", "::1"]:
            with self.subTest(host=host):
                endpoint = MoomooEndpoint(host=host, port=11111)
                self.assertEqual(host, endpoint.host)

    def test_rejects_remote_hosts_and_invalid_ports(self) -> None:
        for host, port in [("192.168.1.10", 11111), ("example.com", 11111), ("127.0.0.1", 0)]:
            with self.subTest(host=host, port=port):
                with self.assertRaises(MoomooConfigurationError):
                    MoomooEndpoint(host=host, port=port)


class MoomooApiSdkTests(unittest.TestCase):
    def test_load_maps_missing_distribution_to_sanitized_dependency_error(self) -> None:
        with patch(
            "autotrade.execution.moomoo.importlib.import_module",
            side_effect=ModuleNotFoundError("sensitive local path"),
        ):
            with self.assertRaises(MoomooDependencyError) as caught:
                MoomooApiSdk.load()

        self.assertNotIn("sensitive", str(caught.exception))

    def test_load_maps_sdk_initialization_failure_to_sanitized_dependency_error(self) -> None:
        with patch(
            "autotrade.execution.moomoo.importlib.import_module",
            side_effect=RuntimeError("sensitive SDK initialization detail"),
        ):
            with self.assertRaises(MoomooDependencyError) as caught:
                MoomooApiSdk.load()

        self.assertNotIn("sensitive", str(caught.exception))

    def test_load_disables_sdk_console_logging(self) -> None:
        console_log_settings: list[bool] = []
        module = SimpleNamespace(
            __version__="10.9.6908",
            SysConfig=SimpleNamespace(enable_console_log=console_log_settings.append),
        )
        with patch(
            "autotrade.execution.moomoo.importlib.import_module",
            return_value=module,
        ):
            MoomooApiSdk.load()

        self.assertEqual([False], console_log_settings)

    def test_context_factories_use_us_futujp_read_only_boundary(self) -> None:
        calls: list[tuple[str, dict[str, object]]] = []
        quote_context = object()
        trade_context = object()

        def open_quote_context(**kwargs: object) -> object:
            calls.append(("quote", kwargs))
            return quote_context

        def open_trade_context(**kwargs: object) -> object:
            calls.append(("trade", kwargs))
            return trade_context

        module = SimpleNamespace(
            __version__="10.9.6918",
            RET_OK=0,
            OpenQuoteContext=open_quote_context,
            OpenSecTradeContext=open_trade_context,
            TrdMarket=SimpleNamespace(US="US"),
            SecurityFirm=SimpleNamespace(FUTUJP="FUTUJP"),
        )
        sdk = MoomooApiSdk(module=module)  # type: ignore[arg-type]
        endpoint = MoomooEndpoint()

        self.assertIs(quote_context, sdk.create_quote_context(endpoint))
        self.assertIs(trade_context, sdk.create_us_trade_context(endpoint))

        self.assertEqual(
            [
                ("quote", {"host": "127.0.0.1", "port": 11111}),
                (
                    "trade",
                    {
                        "filter_trdmarket": "US",
                        "host": "127.0.0.1",
                        "port": 11111,
                        "security_firm": "FUTUJP",
                    },
                ),
            ],
            calls,
        )


class MoomooReadOnlyDiscoveryTests(unittest.TestCase):
    def test_discovers_sanitized_capabilities_and_closes_contexts(self) -> None:
        sdk = FakeSdk(version="10.9.6918")

        result = MoomooReadOnlyDiscovery(
            endpoint=MoomooEndpoint(),
            sdk=sdk,
        ).run()

        self.assertIsNone(result.sanitized_failure_category)
        self.assertEqual("10.9.6918", result.sdk_version)
        self.assertEqual("10.9.6918", result.server_version)
        self.assertEqual("LV3", result.us_quote_entitlement)
        self.assertEqual("LV1", result.jp_quote_entitlement)
        self.assertEqual(2, result.account_count)
        self.assertEqual(1, result.paper_account_count)
        self.assertEqual(1, result.real_account_count)
        self.assertTrue(result.paper_account_available)
        self.assertTrue(result.us_market_authorized)
        self.assertTrue(sdk.quote_context.closed)
        self.assertTrue(sdk.trade_context.closed)

        serialized = json.dumps(result.to_dict(), sort_keys=True)
        for secret in [
            "sensitive-user-id",
            "sensitive-name",
            "sensitive-paper-account",
            "sensitive-real-account",
            "sensitive-card",
        ]:
            self.assertNotIn(secret, serialized)

    def test_rejects_old_sdk_before_constructing_contexts(self) -> None:
        sdk = FakeSdk(version="10.4.6407")

        result = MoomooReadOnlyDiscovery(
            endpoint=MoomooEndpoint(),
            sdk=sdk,
        ).run()

        self.assertEqual("version", result.sanitized_failure_category)
        self.assertEqual(0, sdk.create_quote_count)
        self.assertEqual(0, sdk.create_trade_count)

    def test_rejects_malformed_short_version_before_constructing_contexts(self) -> None:
        sdk = FakeSdk(version="10.5")

        result = MoomooReadOnlyDiscovery(
            endpoint=MoomooEndpoint(),
            sdk=sdk,
        ).run()

        self.assertEqual("version", result.sanitized_failure_category)
        self.assertEqual("UNKNOWN", result.sdk_version)
        self.assertEqual(0, sdk.create_quote_count)
        self.assertEqual(0, sdk.create_trade_count)

    def test_malformed_version_values_are_not_copied_to_output(self) -> None:
        sdk = FakeSdk(version="sensitive-sdk-version")

        result = MoomooReadOnlyDiscovery(
            endpoint=MoomooEndpoint(),
            sdk=sdk,
        ).run()

        self.assertEqual("version", result.sanitized_failure_category)
        self.assertEqual("UNKNOWN", result.sdk_version)

    def test_malformed_server_version_is_not_copied_to_output(self) -> None:
        sdk = FakeSdk(
            global_state=(
                0,
                {
                    "server_ver": "sensitive server payload",
                    "qot_logined": True,
                    "trd_logined": True,
                },
            )
        )

        result = MoomooReadOnlyDiscovery(
            endpoint=MoomooEndpoint(),
            sdk=sdk,
        ).run()

        self.assertIsNone(result.sanitized_failure_category)
        self.assertEqual("UNKNOWN", result.server_version)

    def test_numeric_server_build_is_reported(self) -> None:
        sdk = FakeSdk(
            global_state=(
                0,
                {
                    "server_ver": 6908,
                    "qot_logined": True,
                    "trd_logined": True,
                },
            )
        )

        result = MoomooReadOnlyDiscovery(
            endpoint=MoomooEndpoint(),
            sdk=sdk,
        ).run()

        self.assertEqual("6908", result.server_version)

    def test_sanitizes_sdk_response_failures_and_closes_contexts(self) -> None:
        sdk = FakeSdk(global_state=(-1, "secret token and account payload"))

        result = MoomooReadOnlyDiscovery(
            endpoint=MoomooEndpoint(),
            sdk=sdk,
        ).run()

        self.assertEqual("response", result.sanitized_failure_category)
        self.assertTrue(sdk.quote_context.closed)
        self.assertEqual(0, sdk.create_trade_count)
        self.assertNotIn("secret", json.dumps(result.to_dict()))

    def test_missing_quote_entitlements_are_reported_as_unknown(self) -> None:
        sdk = FakeSdk(user_info=(0, {"user_id": "sensitive"}))

        result = MoomooReadOnlyDiscovery(
            endpoint=MoomooEndpoint(),
            sdk=sdk,
        ).run()

        self.assertEqual("UNKNOWN", result.us_quote_entitlement)
        self.assertEqual("UNKNOWN", result.jp_quote_entitlement)

    def test_rejects_non_list_records_conversion_without_iterable_fallback(self) -> None:
        sdk = FakeSdk(accounts=(0, NonListRecordsPayload()))

        result = MoomooReadOnlyDiscovery(
            endpoint=MoomooEndpoint(),
            sdk=sdk,
        ).run()

        self.assertEqual("response", result.sanitized_failure_category)
        self.assertEqual(0, result.account_count)
        self.assertTrue(sdk.quote_context.closed)
        self.assertTrue(sdk.trade_context.closed)

    def test_fake_sdk_default_payloads_are_isolated_per_instance(self) -> None:
        first = FakeSdk()
        second = FakeSdk()
        first_accounts = first.trade_context.accounts[1]
        second_accounts = second.trade_context.accounts[1]
        self.assertIsInstance(first_accounts, list)
        self.assertIsInstance(second_accounts, list)

        try:
            first_accounts.append({"trd_env": "REAL"})
            self.assertEqual(2, len(second_accounts))
        finally:
            first_accounts.pop()


class MoomooDiscoveryReportTests(unittest.TestCase):
    def test_report_round_trip_is_deterministic_and_create_only(self) -> None:
        result = MoomooReadOnlyDiscovery(
            endpoint=MoomooEndpoint(),
            sdk=FakeSdk(version="10.9.6918"),
        ).run()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "discovery.json"
            writer = MoomooDiscoveryReportWriter()
            self.assertEqual(path, writer.write(path, result))
            payload = path.read_text(encoding="utf-8")
            self.assertTrue(payload.endswith("\n"))
            self.assertEqual(result, MoomooDiscoveryReportReader().read(path))
            with self.assertRaises(MoomooConfigurationError):
                writer.write(path, result)

    def test_reader_rejects_unknown_schema(self) -> None:
        result = MoomooReadOnlyDiscovery(
            endpoint=MoomooEndpoint(),
            sdk=FakeSdk(),
        ).run().to_dict()
        result["schema_version"] = 2

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "discovery.json"
            path.write_text(json.dumps(result), encoding="utf-8")
            with self.assertRaises(MoomooConfigurationError):
                MoomooDiscoveryReportReader().read(path)

    def test_reader_rejects_invalid_field_types(self) -> None:
        result = MoomooReadOnlyDiscovery(
            endpoint=MoomooEndpoint(),
            sdk=FakeSdk(),
        ).run().to_dict()

        for field, invalid_value in [
            ("schema_version", True),
            ("endpoint", "sensitive remote endpoint"),
            ("sdk_version", "sensitive SDK payload"),
            ("account_count", True),
            ("paper_account_count", -1),
            ("qot_logged_in", "true"),
            ("sanitized_failure_category", "sensitive-internal-error"),
        ]:
            with self.subTest(field=field):
                malformed = dict(result)
                malformed[field] = invalid_value
                with tempfile.TemporaryDirectory() as tmpdir:
                    path = Path(tmpdir) / "discovery.json"
                    path.write_text(json.dumps(malformed), encoding="utf-8")
                    with self.assertRaises(MoomooConfigurationError):
                        MoomooDiscoveryReportReader().read(path)


class MoomooPackagingTests(unittest.TestCase):
    def test_sdk_is_declared_as_an_optional_versioned_dependency(self) -> None:
        pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertIn("moomoo = [", pyproject)
        self.assertIn('"moomoo-api>=10.4.6408"', pyproject)

    def test_feature_document_captures_safe_runtime_boundary(self) -> None:
        document = (REPO_ROOT / "docs/moomoo-openapi.md").read_text(
            encoding="utf-8"
        )

        for term in [
            "moomoo-readonly-discovery",
            "validate-only",
            "--connect",
            "127.0.0.1:11111",
            "unlock_trade",
            "sanitized",
            "no live orders",
        ]:
            self.assertIn(term, document)


if __name__ == "__main__":
    unittest.main()
