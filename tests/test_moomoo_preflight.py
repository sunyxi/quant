from __future__ import annotations

import inspect
import tempfile
import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from types import SimpleNamespace

from autotrade.execution.moomoo import (
    MIN_MOOMOO_API_VERSION,
    MoomooApiSdk,
    MoomooConfigurationError,
    MoomooEndpoint,
    MoomooPaperAccountPreflight,
    MoomooPaperAccountPreflightReportReader,
    MoomooPaperAccountPreflightReportWriter,
)
from autotrade.execution.moomoo_readiness import MoomooPaperReadinessGate
from tests.test_moomoo_readiness import ready_discovery


SENSITIVE_ACCOUNT_ID = "sensitive-paper-account-id"


def ready_decision():
    return MoomooPaperReadinessGate().evaluate(ready_discovery())


def eligible_account(account_id: str = SENSITIVE_ACCOUNT_ID) -> dict[str, object]:
    return {
        "acc_id": account_id,
        "trd_env": "SIMULATE",
        "acc_type": "MARGIN",
        "sim_acc_type": "STOCK_AND_OPTION",
        "trdmarket_auth": ["US"],
        "acc_status": "ACTIVE",
        "card_num": "sensitive-card-number",
    }


class FakePaperTradeContext:
    def __init__(
        self,
        *,
        accounts: tuple[int, object] | None = None,
        funds: tuple[int, object] | None = None,
        positions: tuple[int, object] | None = None,
        orders: tuple[int, object] | None = None,
    ) -> None:
        self.accounts = accounts or (0, [eligible_account()])
        self.funds = funds or (0, [{"cash": 100_000.0}])
        self.positions = positions or (0, [{"code": "US.AAPL"}])
        self.orders = orders or (0, [{"order_id": "sensitive-order-id"}])
        self.query_calls: list[tuple[str, dict[str, object]]] = []
        self.closed = False

    def get_acc_list(self) -> tuple[int, object]:
        return self.accounts

    def accinfo_query(self, **kwargs) -> tuple[int, object]:
        self.query_calls.append(("funds", kwargs))
        return self.funds

    def position_list_query(self, **kwargs) -> tuple[int, object]:
        self.query_calls.append(("positions", kwargs))
        return self.positions

    def order_list_query(self, **kwargs) -> tuple[int, object]:
        self.query_calls.append(("orders", kwargs))
        return self.orders

    def close(self) -> None:
        self.closed = True


class RaisingPaperTradeContext(FakePaperTradeContext):
    def position_list_query(self, **kwargs) -> tuple[int, object]:
        raise RuntimeError("sensitive SDK exception")


class FakePreflightSdk:
    ret_ok = 0
    version = MIN_MOOMOO_API_VERSION
    simulate_trade_environment = "SIMULATE"

    def __init__(self, context: FakePaperTradeContext | None = None) -> None:
        self.context = context or FakePaperTradeContext()
        self.create_calls = 0

    def create_us_trade_context(
        self,
        endpoint: MoomooEndpoint,
    ) -> FakePaperTradeContext:
        self.create_calls += 1
        return self.context


class MoomooPaperAccountPreflightTests(unittest.TestCase):
    def test_selects_unique_simulate_account_and_runs_fresh_read_queries(self) -> None:
        context = FakePaperTradeContext(
            positions=(0, [{"code": "US.AAPL"}, {"code": "US.MSFT"}]),
            orders=(0, [{"order_id": "sensitive-order-id"}]),
        )
        result = MoomooPaperAccountPreflight(
            endpoint=MoomooEndpoint(),
            sdk=FakePreflightSdk(context),
        ).run(readiness=ready_decision())

        self.assertEqual(
            {
                "schema_version": 1,
                "endpoint": "127.0.0.1:11111",
                "sdk_version": MIN_MOOMOO_API_VERSION,
                "readiness_schema_version": 1,
                "connection_status": "ok",
                "account_selection_status": "unique",
                "eligible_account_count": 1,
                "account_type": "MARGIN",
                "sim_account_type": "STOCK_AND_OPTION",
                "account_status": "ACTIVE",
                "funds_query_status": "ok",
                "positions_query_status": "ok",
                "orders_query_status": "ok",
                "position_count": 2,
                "order_record_count": 1,
                "refresh_cache": True,
                "sanitized_failure_category": None,
            },
            result.to_dict(),
        )
        expected_kwargs = {
            "trd_env": "SIMULATE",
            "acc_id": SENSITIVE_ACCOUNT_ID,
            "refresh_cache": True,
        }
        self.assertEqual(
            [
                ("funds", expected_kwargs),
                ("positions", expected_kwargs),
                ("orders", expected_kwargs),
            ],
            context.query_calls,
        )
        self.assertTrue(context.closed)
        self.assertNotIn(SENSITIVE_ACCOUNT_ID, str(result.to_dict()))
        with self.assertRaises(FrozenInstanceError):
            result.position_count = 99

    def test_blocked_readiness_prevents_context_creation(self) -> None:
        sdk = FakePreflightSdk()
        blocked = MoomooPaperReadinessGate().evaluate(
            replace(ready_discovery(), us_market_authorized=False)
        )

        result = MoomooPaperAccountPreflight(
            endpoint=MoomooEndpoint(),
            sdk=sdk,
        ).run(readiness=blocked)

        self.assertEqual("readiness", result.sanitized_failure_category)
        self.assertEqual(0, sdk.create_calls)

    def test_requires_exactly_one_eligible_account(self) -> None:
        ineligible = [
            {**eligible_account(), "trd_env": "REAL"},
            {**eligible_account(), "sim_acc_type": "STOCK"},
            {**eligible_account(), "trdmarket_auth": ["HK"]},
            {**eligible_account(), "acc_status": "DISABLED"},
        ]
        cases = [
            (ineligible, 0),
            ([eligible_account("one"), eligible_account("two")], 2),
        ]

        for accounts, expected_count in cases:
            context = FakePaperTradeContext(accounts=(0, accounts))
            with self.subTest(expected_count=expected_count):
                result = MoomooPaperAccountPreflight(
                    endpoint=MoomooEndpoint(),
                    sdk=FakePreflightSdk(context),
                ).run(readiness=ready_decision())
            self.assertEqual("account", result.sanitized_failure_category)
            self.assertEqual(expected_count, result.eligible_account_count)
            self.assertEqual([], context.query_calls)
            self.assertTrue(context.closed)

    def test_classifies_each_read_response_failure_without_leaking_payload(self) -> None:
        cases = [
            ("funds", {"funds": (1, "sensitive funds error")}),
            ("positions", {"positions": (1, "sensitive positions error")}),
            ("orders", {"orders": (1, "sensitive orders error")}),
        ]

        for category, overrides in cases:
            context = FakePaperTradeContext(**overrides)
            with self.subTest(category=category):
                result = MoomooPaperAccountPreflight(
                    endpoint=MoomooEndpoint(),
                    sdk=FakePreflightSdk(context),
                ).run(readiness=ready_decision())
            self.assertEqual(category, result.sanitized_failure_category)
            self.assertNotIn("sensitive", str(result.to_dict()))
            self.assertTrue(context.closed)

    def test_closes_context_and_sanitizes_unexpected_sdk_exception(self) -> None:
        context = RaisingPaperTradeContext()

        result = MoomooPaperAccountPreflight(
            endpoint=MoomooEndpoint(),
            sdk=FakePreflightSdk(context),
        ).run(readiness=ready_decision())

        self.assertEqual("system", result.sanitized_failure_category)
        self.assertTrue(context.closed)
        self.assertNotIn("sensitive", str(result.to_dict()))

    def test_report_round_trip_is_create_only_and_rejects_unknown_schema(self) -> None:
        result = MoomooPaperAccountPreflight(
            endpoint=MoomooEndpoint(),
            sdk=FakePreflightSdk(),
        ).run(readiness=ready_decision())

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "preflight.json"
            writer = MoomooPaperAccountPreflightReportWriter()
            writer.write(report_path, result)
            restored = MoomooPaperAccountPreflightReportReader().read(report_path)
            self.assertEqual(result, restored)
            with self.assertRaises(MoomooConfigurationError):
                writer.write(report_path, result)

            payload = report_path.read_text(encoding="utf-8").replace(
                '"schema_version": 1',
                '"schema_version": 2',
            )
            invalid_path = Path(tmpdir) / "invalid.json"
            invalid_path.write_text(payload, encoding="utf-8")
            with self.assertRaises(MoomooConfigurationError):
                MoomooPaperAccountPreflightReportReader().read(invalid_path)

    def test_preflight_source_has_no_order_or_unlock_operation(self) -> None:
        source = inspect.getsource(MoomooPaperAccountPreflight)

        for forbidden in [
            "place_order",
            "modify_order",
            "unlock_trade",
            "subscribe",
            "TrdEnv.REAL",
        ]:
            self.assertNotIn(forbidden, source)


class MoomooApiSdkPreflightContractTests(unittest.TestCase):
    def test_exposes_only_the_simulate_environment_value(self) -> None:
        module = SimpleNamespace(
            TrdEnv=SimpleNamespace(SIMULATE="SIMULATE", REAL="REAL"),
        )

        sdk = MoomooApiSdk(module=module)  # type: ignore[arg-type]

        self.assertEqual("SIMULATE", sdk.simulate_trade_environment)


if __name__ == "__main__":
    unittest.main()
