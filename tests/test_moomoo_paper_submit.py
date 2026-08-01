from __future__ import annotations

import inspect
import unittest
from dataclasses import FrozenInstanceError, replace

from autotrade.execution import moomoo_paper_submit
from autotrade.execution.moomoo import (
    MIN_MOOMOO_API_VERSION,
    MoomooEndpoint,
    MoomooPaperAccountPreflightResult,
)
from autotrade.execution.moomoo_paper_order import MoomooPaperOrderDryRunPlanner
from autotrade.execution.moomoo_paper_submit import (
    MoomooPaperOrderSubmitter,
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
        for forbidden in [
            "unlock_trade",
            "modify_order",
            "cancel_order",
            "subscribe",
            "TrdEnv.REAL",
            "retry",
        ]:
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
