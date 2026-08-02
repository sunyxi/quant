from __future__ import annotations

import inspect
import json
import tempfile
import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from unittest.mock import patch

from autotrade.execution import moomoo_paper_submit
from autotrade.execution.moomoo import (
    MIN_MOOMOO_API_VERSION,
    MoomooConfigurationError,
    MoomooEndpoint,
    MoomooPaperAccountPreflightResult,
    MoomooQuoteContext,
)
from autotrade.execution.moomoo_paper_order import MoomooPaperOrderDryRunPlanner
from autotrade.execution.moomoo_paper_submit import (
    MoomooPaperOrderSubmitter,
    MoomooPaperOrderSubmissionReportReader,
    MoomooPaperOrderSubmissionReportWriter,
    MoomooPaperOrderSubmissionStatus,
)
from tests.test_moomoo_paper_order import order_intent, ready_decision
from tests.test_moomoo_preflight import eligible_account


def successful_preflight() -> MoomooPaperAccountPreflightResult:
    return MoomooPaperAccountPreflightResult(
        sdk_version=MIN_MOOMOO_API_VERSION,
        readiness_schema_version=1,
        connection_status="ok",
        account_selection_status="unique",
        eligible_account_count=1,
        account_type="MARGIN",
        sim_account_type="STOCK_AND_OPTION",
        account_status="ACTIVE",
        funds_query_status="ok",
        positions_query_status="ok",
        orders_query_status="ok",
    )


def paper_plan():
    return MoomooPaperOrderDryRunPlanner().plan(
        order_intent(),
        readiness=ready_decision(),
    )


class FakeSubmitContext:
    def __init__(self) -> None:
        self.accounts: tuple[int, object] = (0, [eligible_account()])
        self.place_response: tuple[int, object] = (
            0,
            [{"order_id": "sensitive-broker-order-id"}],
        )
        self.orders_response: tuple[int, object] = (
            0,
            [{"remark": "paper-dry-run-001", "order_id": "sensitive-id"}],
        )
        self.place_calls: list[dict[str, object]] = []
        self.order_query_calls: list[dict[str, object]] = []
        self.closed = False

    def get_acc_list(self) -> tuple[int, object]:
        return self.accounts

    def accinfo_query(self, **kwargs: object) -> tuple[int, object]:
        raise NotImplementedError("submit path never queries account info")

    def position_list_query(self, **kwargs: object) -> tuple[int, object]:
        raise NotImplementedError("submit path never queries positions")

    def place_order(self, **kwargs) -> tuple[int, object]:
        self.place_calls.append(kwargs)
        return self.place_response

    def order_list_query(self, **kwargs) -> tuple[int, object]:
        self.order_query_calls.append(kwargs)
        return self.orders_response

    def close(self) -> None:
        self.closed = True


class RaisingSubmitContext(FakeSubmitContext):
    def place_order(self, **kwargs) -> tuple[int, object]:
        self.place_calls.append(kwargs)
        raise TimeoutError("sensitive uncertain submission")


class RaisingAccountListContext(FakeSubmitContext):
    def get_acc_list(self) -> tuple[int, object]:
        raise ConnectionError("sensitive account-list network failure")


class FakeSubmitSdk:
    version = MIN_MOOMOO_API_VERSION
    ret_ok = 0
    simulate_trade_environment = "SIMULATE"
    buy_trade_side = "BUY"
    normal_order_type = "NORMAL"
    day_time_in_force = "DAY"
    rth_session = "RTH"

    def __init__(self, context: FakeSubmitContext | None = None) -> None:
        self.context = context or FakeSubmitContext()
        self.create_calls = 0

    def create_quote_context(self, endpoint: MoomooEndpoint) -> MoomooQuoteContext:
        raise NotImplementedError("submit path never uses quote context")

    def create_us_trade_context(self, endpoint: MoomooEndpoint) -> FakeSubmitContext:
        self.create_calls += 1
        return self.context


class MissingConstantSubmitSdk(FakeSubmitSdk):
    @property
    def rth_session(self):
        raise AttributeError("sensitive missing constant")


class GetOnlyRow:
    def __init__(self, values: dict[str, object]) -> None:
        self.values = values

    def get(self, name: str) -> object:
        return self.values.get(name)


class NonListFrame:
    def __init__(self) -> None:
        self.iterated = False

    def to_dict(self, orient: str) -> tuple[object, ...]:
        return ()

    def __iter__(self):
        self.iterated = True
        raise AssertionError("must not iterate malformed frame")


class MoomooPaperOrderSubmitterTests(unittest.TestCase):
    def test_fakes_expose_the_complete_shared_moomoo_protocols(self) -> None:
        sdk = FakeSubmitSdk()

        self.assertTrue(callable(getattr(sdk, "create_quote_context", None)))
        self.assertTrue(callable(getattr(sdk.context, "accinfo_query", None)))
        self.assertTrue(
            callable(getattr(sdk.context, "position_list_query", None))
        )

    def test_uses_public_shared_moomoo_contracts(self) -> None:
        source = inspect.getsource(moomoo_paper_submit)

        for private_import in [
            "    _field,",
            "    _records,",
            "    _safe_close,",
            "    _safe_version,",
            "    _version_at_least,",
        ]:
            self.assertNotIn(private_import, source)
        self.assertNotIn("class MoomooPaperSubmitSdk", source)
        self.assertNotIn("class MoomooPaperSubmitContext", source)
        self.assertIn("sdk: MoomooSdkSource", source)
        self.assertIn("context: MoomooTradeContext | None", source)

    def test_submits_once_and_verifies_by_client_remark(self) -> None:
        context = FakeSubmitContext()
        result = MoomooPaperOrderSubmitter(
            endpoint=MoomooEndpoint(),
            sdk=FakeSubmitSdk(context),
        ).submit(
            paper_plan(),
            readiness=ready_decision(),
            preflight=successful_preflight(),
            acknowledged=True,
        )

        self.assertEqual(MoomooPaperOrderSubmissionStatus.VERIFIED, result.status)
        self.assertEqual(1, result.place_order_call_count)
        self.assertEqual(1, result.verification_match_count)
        self.assertEqual(
            [{
                "price": 150.25,
                "qty": 10,
                "code": "US.AAPL",
                "trd_side": "BUY",
                "order_type": "NORMAL",
                "trd_env": "SIMULATE",
                "acc_id": 987654321,
                "remark": "paper-dry-run-001",
                "time_in_force": "DAY",
                "fill_outside_rth": False,
                "session": "RTH",
            }],
            context.place_calls,
        )
        self.assertEqual(
            [{
                "trd_env": "SIMULATE",
                "acc_id": 987654321,
                "refresh_cache": True,
            }],
            context.order_query_calls,
        )
        self.assertTrue(context.closed)
        self.assertNotIn("987654321", str(result.to_dict()))
        self.assertNotIn("sensitive", str(result.to_dict()))
        with self.assertRaises(FrozenInstanceError):
            result.place_order_call_count = 2

    def test_blocks_before_context_when_any_evidence_or_ack_is_missing(self) -> None:
        cases = [
            {"acknowledged": False},
            {"readiness": replace(ready_decision(), status="BLOCKED")},
            {"preflight": replace(successful_preflight(), schema_version=2)},
            {
                "preflight": replace(
                    successful_preflight(),
                    sanitized_failure_category="orders",
                )
            },
        ]
        for overrides in cases:
            sdk = FakeSubmitSdk()
            kwargs = {
                "readiness": ready_decision(),
                "preflight": successful_preflight(),
                "acknowledged": True,
            }
            kwargs.update(overrides)
            with self.subTest(overrides=overrides):
                result = MoomooPaperOrderSubmitter(
                    endpoint=MoomooEndpoint(),
                    sdk=sdk,
                ).submit(paper_plan(), **kwargs)
                self.assertEqual(
                    MoomooPaperOrderSubmissionStatus.BLOCKED,
                    result.status,
                )
                self.assertEqual(0, sdk.create_calls)

    def test_requires_exactly_one_positive_integer_account(self) -> None:
        cases = [[], [eligible_account(0)], [eligible_account(1), eligible_account(2)]]
        for accounts in cases:
            context = FakeSubmitContext()
            context.accounts = (0, accounts)
            with self.subTest(accounts=accounts):
                result = MoomooPaperOrderSubmitter(
                    endpoint=MoomooEndpoint(),
                    sdk=FakeSubmitSdk(context),
                ).submit(
                    paper_plan(),
                    readiness=ready_decision(),
                    preflight=successful_preflight(),
                    acknowledged=True,
                )
                self.assertEqual(
                    MoomooPaperOrderSubmissionStatus.BLOCKED,
                    result.status,
                )
                self.assertEqual([], context.place_calls)
                self.assertTrue(context.closed)

    def test_accepts_sdk_row_with_callable_get(self) -> None:
        context = FakeSubmitContext()
        context.accounts = (0, [GetOnlyRow(eligible_account())])

        result = MoomooPaperOrderSubmitter(
            endpoint=MoomooEndpoint(),
            sdk=FakeSubmitSdk(context),
        ).submit(
            paper_plan(),
            readiness=ready_decision(),
            preflight=successful_preflight(),
            acknowledged=True,
        )

        self.assertEqual(MoomooPaperOrderSubmissionStatus.VERIFIED, result.status)
        self.assertEqual(1, len(context.place_calls))

    def test_malformed_frame_does_not_fall_through_to_iteration(self) -> None:
        context = FakeSubmitContext()
        frame = NonListFrame()
        context.accounts = (0, frame)

        result = MoomooPaperOrderSubmitter(
            endpoint=MoomooEndpoint(),
            sdk=FakeSubmitSdk(context),
        ).submit(
            paper_plan(),
            readiness=ready_decision(),
            preflight=successful_preflight(),
            acknowledged=True,
        )

        self.assertEqual(MoomooPaperOrderSubmissionStatus.BLOCKED, result.status)
        self.assertFalse(frame.iterated)
        self.assertEqual([], context.place_calls)

    def test_short_sdk_version_is_blocked_before_context_creation(self) -> None:
        sdk = FakeSubmitSdk()
        sdk.version = "10.5"

        result = MoomooPaperOrderSubmitter(
            endpoint=MoomooEndpoint(),
            sdk=sdk,
        ).submit(
            paper_plan(),
            readiness=ready_decision(),
            preflight=successful_preflight(),
            acknowledged=True,
        )

        self.assertEqual(MoomooPaperOrderSubmissionStatus.BLOCKED, result.status)
        self.assertEqual("version", result.sanitized_failure_category)
        self.assertEqual(0, sdk.create_calls)

    def test_rejected_response_is_sanitized_and_not_verified(self) -> None:
        context = FakeSubmitContext()
        context.place_response = (1, "sensitive rejection")

        result = MoomooPaperOrderSubmitter(
            endpoint=MoomooEndpoint(),
            sdk=FakeSubmitSdk(context),
        ).submit(
            paper_plan(),
            readiness=ready_decision(),
            preflight=successful_preflight(),
            acknowledged=True,
        )

        self.assertEqual(MoomooPaperOrderSubmissionStatus.REJECTED, result.status)
        self.assertEqual(1, result.place_order_call_count)
        self.assertEqual([], context.order_query_calls)
        self.assertNotIn("sensitive", str(result.to_dict()))

    def test_missing_sdk_constant_blocks_before_place_order_call(self) -> None:
        sdk = MissingConstantSubmitSdk()

        result = MoomooPaperOrderSubmitter(
            endpoint=MoomooEndpoint(),
            sdk=sdk,
        ).submit(
            paper_plan(),
            readiness=ready_decision(),
            preflight=successful_preflight(),
            acknowledged=True,
        )

        self.assertEqual(MoomooPaperOrderSubmissionStatus.BLOCKED, result.status)
        self.assertEqual("dependency", result.sanitized_failure_category)
        self.assertEqual(0, result.place_order_call_count)
        self.assertEqual([], sdk.context.place_calls)
        self.assertNotIn("sensitive", str(result.to_dict()))

    def test_uncertain_exception_is_unknown_and_never_retried(self) -> None:
        context = RaisingSubmitContext()

        result = MoomooPaperOrderSubmitter(
            endpoint=MoomooEndpoint(),
            sdk=FakeSubmitSdk(context),
        ).submit(
            paper_plan(),
            readiness=ready_decision(),
            preflight=successful_preflight(),
            acknowledged=True,
        )

        self.assertEqual(MoomooPaperOrderSubmissionStatus.UNKNOWN, result.status)
        self.assertEqual(1, result.place_order_call_count)
        self.assertEqual(1, len(context.place_calls))
        self.assertEqual([], context.order_query_calls)
        self.assertTrue(context.closed)
        self.assertNotIn("sensitive", str(result.to_dict()))

    def test_account_list_network_failure_has_distinct_sanitized_category(
        self,
    ) -> None:
        result = MoomooPaperOrderSubmitter(
            endpoint=MoomooEndpoint(),
            sdk=FakeSubmitSdk(RaisingAccountListContext()),
        ).submit(
            paper_plan(),
            readiness=ready_decision(),
            preflight=successful_preflight(),
            acknowledged=True,
        )

        self.assertEqual(MoomooPaperOrderSubmissionStatus.BLOCKED, result.status)
        self.assertEqual("connection", result.sanitized_failure_category)
        self.assertEqual("not-run", result.account_selection_status)
        self.assertEqual(0, result.place_order_call_count)
        self.assertNotIn("sensitive", str(result.to_dict()))

    def test_success_status_with_empty_payload_is_unknown(self) -> None:
        context = FakeSubmitContext()
        context.place_response = (0, [])

        result = MoomooPaperOrderSubmitter(
            endpoint=MoomooEndpoint(),
            sdk=FakeSubmitSdk(context),
        ).submit(
            paper_plan(),
            readiness=ready_decision(),
            preflight=successful_preflight(),
            acknowledged=True,
        )

        self.assertEqual(MoomooPaperOrderSubmissionStatus.UNKNOWN, result.status)
        self.assertEqual("submission", result.sanitized_failure_category)
        self.assertEqual(1, len(context.place_calls))

    def test_verification_mismatch_preserves_submitted_status(self) -> None:
        context = FakeSubmitContext()
        context.orders_response = (0, [{"remark": "different-order"}])

        result = MoomooPaperOrderSubmitter(
            endpoint=MoomooEndpoint(),
            sdk=FakeSubmitSdk(context),
        ).submit(
            paper_plan(),
            readiness=ready_decision(),
            preflight=successful_preflight(),
            acknowledged=True,
        )

        self.assertEqual(MoomooPaperOrderSubmissionStatus.SUBMITTED, result.status)
        self.assertEqual("verification", result.sanitized_failure_category)

    def test_source_has_no_live_unlock_modify_cancel_subscribe_or_retry(self) -> None:
        source = inspect.getsource(MoomooPaperOrderSubmitter)
        self.assertNotIn("def _read_records", source)
        for forbidden in [
            "unlock_trade",
            "modify_order",
            "cancel_order",
            "subscribe",
            "TrdEnv.REAL",
            "retry",
        ]:
            self.assertNotIn(forbidden, source)


class MoomooPaperOrderSubmissionReportTests(unittest.TestCase):
    @staticmethod
    def _result(context: FakeSubmitContext | None = None):
        return MoomooPaperOrderSubmitter(
            endpoint=MoomooEndpoint(),
            sdk=FakeSubmitSdk(context),
        ).submit(
            paper_plan(),
            readiness=ready_decision(),
            preflight=successful_preflight(),
            acknowledged=True,
        )

    def test_deterministic_create_only_round_trip_for_producer_states(self) -> None:
        rejected = FakeSubmitContext()
        rejected.place_response = (1, "sensitive rejection")
        submitted = FakeSubmitContext()
        submitted.orders_response = (0, [{"remark": "different-order"}])
        results = [
            self._result(),
            self._result(rejected),
            self._result(RaisingSubmitContext()),
            self._result(submitted),
            self._result(RaisingAccountListContext()),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            for index, result in enumerate(results):
                path = Path(tmpdir) / "nested" / f"submission-{index}.json"
                written = MoomooPaperOrderSubmissionReportWriter().write(
                    path,
                    result,
                )
                content = path.read_text(encoding="utf-8")
                with self.subTest(status=result.status):
                    self.assertEqual(path, written)
                    with patch(
                        "autotrade.execution.moomoo.MoomooApiSdk.load",
                        side_effect=AssertionError("SDK loaded"),
                    ):
                        self.assertEqual(
                            result,
                            MoomooPaperOrderSubmissionReportReader().read(path),
                        )
                    self.assertEqual(
                        json.dumps(result.to_dict(), sort_keys=True) + "\n",
                        content,
                    )
                    self.assertNotIn("acc_id", content)
                    self.assertNotIn('"order_id":', content)

                with self.assertRaises(MoomooConfigurationError):
                    MoomooPaperOrderSubmissionReportWriter().write(path, result)

    def test_reader_rejects_invalid_schema_shape_types_and_state(self) -> None:
        valid = self._result().to_dict()
        cases = [
            {**valid, "schema_version": 2},
            {**valid, "unexpected": True},
            {key: value for key, value in valid.items() if key != "status"},
            {**valid, "status": "filled"},
            {**valid, "endpoint": "broker.example:11111"},
            {**valid, "sdk_version": "10.5"},
            {**valid, "client_order_id": "bad"},
            {**valid, "place_order_call_count": True},
            {**valid, "refresh_cache": False},
            {**valid, "status": "blocked"},
            {**valid, "status": "rejected"},
            {**valid, "status": "unknown"},
            {**valid, "status": "submitted"},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            for index, payload in enumerate(cases):
                path = Path(tmpdir) / f"invalid-{index}.json"
                path.write_text(json.dumps(payload), encoding="utf-8")
                with self.subTest(index=index), self.assertRaises(
                    MoomooConfigurationError
                ):
                    MoomooPaperOrderSubmissionReportReader().read(path)

            malformed = Path(tmpdir) / "malformed.json"
            malformed.write_text("{", encoding="utf-8")
            with self.assertRaises(MoomooConfigurationError):
                MoomooPaperOrderSubmissionReportReader().read(malformed)

    def test_writer_rejects_dangling_symlink_and_sanitizes_write_failure(
        self,
    ) -> None:
        result = self._result()
        with tempfile.TemporaryDirectory() as tmpdir:
            symlink = Path(tmpdir) / "submission.json"
            symlink.symlink_to(Path(tmpdir) / "missing.json")
            with self.assertRaisesRegex(
                MoomooConfigurationError,
                "already exists",
            ):
                MoomooPaperOrderSubmissionReportWriter().write(symlink, result)

            parent_file = Path(tmpdir) / "not-a-directory"
            parent_file.write_text("occupied", encoding="utf-8")
            with self.assertRaisesRegex(
                MoomooConfigurationError,
                "could not write",
            ):
                MoomooPaperOrderSubmissionReportWriter().write(
                    parent_file / "submission.json",
                    result,
                )


if __name__ == "__main__":
    unittest.main()
