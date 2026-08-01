from __future__ import annotations

import inspect
import json
import tempfile
import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

from autotrade.execution.moomoo import (
    MIN_MOOMOO_API_VERSION,
    MoomooConfigurationError,
    MoomooEndpoint,
)
from autotrade.execution.moomoo_paper_reconcile import (
    MoomooPaperOrderReconciler,
    MoomooPaperOrderReconciliationReportReader,
    MoomooPaperOrderReconciliationReportWriter,
    MoomooPaperOrderReconciliationStatus,
)
from tests.test_moomoo_paper_order import ready_decision
from tests.test_moomoo_preflight import eligible_account
from tests.test_moomoo_paper_submit import (
    FakeSubmitContext,
    FakeSubmitSdk,
    successful_preflight,
)


class FakeReconcileContext(FakeSubmitContext):
    def __init__(self) -> None:
        super().__init__()
        self.orders_response = (
            0,
            [{"remark": "paper-dry-run-001", "order_id": "secret"}],
        )


class FakeReconcileSdk(FakeSubmitSdk):
    version = MIN_MOOMOO_API_VERSION

    def __init__(self, context: FakeReconcileContext | None = None) -> None:
        super().__init__(context or FakeReconcileContext())


class RaisingOrderQueryContext(FakeReconcileContext):
    def order_list_query(self, **kwargs: object) -> tuple[int, object]:
        self.order_query_calls.append(kwargs)
        raise TimeoutError("sensitive broker timeout")


class RaisingVersionSdk(FakeReconcileSdk):
    @property
    def version(self) -> str:
        raise RuntimeError("sensitive SDK failure")


class MoomooPaperOrderReconcilerTests(unittest.TestCase):
    def test_unique_exact_remark_match_is_sanitized_and_closes_context(self) -> None:
        context = FakeReconcileContext()
        result = MoomooPaperOrderReconciler(
            endpoint=MoomooEndpoint(),
            sdk=FakeReconcileSdk(context),
        ).reconcile(
            "paper-dry-run-001",
            readiness=ready_decision(),
            preflight=successful_preflight(),
        )

        self.assertEqual(MoomooPaperOrderReconciliationStatus.UNIQUE, result.status)
        self.assertEqual(1, result.match_count)
        self.assertEqual("ok", result.query_status)
        self.assertIsNone(result.sanitized_failure_category)
        self.assertEqual(
            [{"trd_env": "SIMULATE", "acc_id": 987654321, "refresh_cache": True}],
            context.order_query_calls,
        )
        self.assertTrue(context.closed)
        self.assertNotIn("987654321", str(result.to_dict()))
        self.assertNotIn("'order_id':", str(result.to_dict()))
        self.assertNotIn("secret", str(result.to_dict()))
        with self.assertRaises(FrozenInstanceError):
            result.match_count = 2

    def test_absent_and_duplicate_are_distinct_non_success_evidence(self) -> None:
        cases = [
            (
                [{"remark": "paper-dry-run-001-extra"}],
                MoomooPaperOrderReconciliationStatus.ABSENT,
                "not_visible",
                0,
            ),
            (
                [
                    {"remark": "paper-dry-run-001"},
                    {"remark": "paper-dry-run-001"},
                ],
                MoomooPaperOrderReconciliationStatus.DUPLICATE,
                "ambiguous",
                2,
            ),
        ]
        for rows, status, category, count in cases:
            context = FakeReconcileContext()
            context.orders_response = (0, rows)
            with self.subTest(status=status):
                result = MoomooPaperOrderReconciler(
                    endpoint=MoomooEndpoint(),
                    sdk=FakeReconcileSdk(context),
                ).reconcile(
                    "paper-dry-run-001",
                    readiness=ready_decision(),
                    preflight=successful_preflight(),
                )

            self.assertEqual(status, result.status)
            self.assertEqual(category, result.sanitized_failure_category)
            self.assertEqual(count, result.match_count)
            self.assertEqual(1, len(context.order_query_calls))

    def test_invalid_evidence_or_client_id_blocks_before_context(self) -> None:
        cases = [
            (
                "bad",
                ready_decision(),
                successful_preflight(),
                "client_order_id",
            ),
            (
                "paper-dry-run-001",
                replace(ready_decision(), status="BLOCKED"),
                successful_preflight(),
                "readiness",
            ),
            (
                "paper-dry-run-001",
                ready_decision(),
                replace(successful_preflight(), orders_query_status="failed"),
                "preflight",
            ),
            (
                "paper-dry-run-001",
                ready_decision(),
                replace(successful_preflight(), schema_version=2),
                "preflight",
            ),
        ]
        for client_order_id, readiness, preflight, category in cases:
            sdk = FakeReconcileSdk()
            with self.subTest(category=category):
                result = MoomooPaperOrderReconciler(
                    endpoint=MoomooEndpoint(),
                    sdk=sdk,
                ).reconcile(
                    client_order_id,
                    readiness=readiness,
                    preflight=preflight,
                )

            self.assertEqual(
                MoomooPaperOrderReconciliationStatus.BLOCKED,
                result.status,
            )
            self.assertEqual(category, result.sanitized_failure_category)
            self.assertEqual(0, sdk.create_calls)

    def test_requires_exactly_one_positive_integer_eligible_account(self) -> None:
        cases = [
            [],
            [eligible_account(0)],
            [eligible_account(1), eligible_account(2)],
        ]
        for accounts in cases:
            context = FakeReconcileContext()
            context.accounts = (0, accounts)
            with self.subTest(accounts=accounts):
                result = MoomooPaperOrderReconciler(
                    endpoint=MoomooEndpoint(),
                    sdk=FakeReconcileSdk(context),
                ).reconcile(
                    "paper-dry-run-001",
                    readiness=ready_decision(),
                    preflight=successful_preflight(),
                )

            self.assertEqual(
                MoomooPaperOrderReconciliationStatus.BLOCKED,
                result.status,
            )
            self.assertEqual("account", result.sanitized_failure_category)
            self.assertEqual([], context.order_query_calls)
            self.assertTrue(context.closed)

    def test_invalid_sdk_version_blocks_before_context(self) -> None:
        sdk = FakeReconcileSdk()
        sdk.version = "10.5"

        result = MoomooPaperOrderReconciler(
            endpoint=MoomooEndpoint(),
            sdk=sdk,
        ).reconcile(
            "paper-dry-run-001",
            readiness=ready_decision(),
            preflight=successful_preflight(),
        )

        self.assertEqual(
            MoomooPaperOrderReconciliationStatus.BLOCKED,
            result.status,
        )
        self.assertEqual("version", result.sanitized_failure_category)
        self.assertEqual(0, sdk.create_calls)

    def test_sdk_version_failure_is_sanitized_before_context(self) -> None:
        sdk = RaisingVersionSdk()

        result = MoomooPaperOrderReconciler(
            endpoint=MoomooEndpoint(),
            sdk=sdk,
        ).reconcile(
            "paper-dry-run-001",
            readiness=ready_decision(),
            preflight=successful_preflight(),
        )

        self.assertEqual(
            MoomooPaperOrderReconciliationStatus.BLOCKED,
            result.status,
        )
        self.assertEqual("dependency", result.sanitized_failure_category)
        self.assertEqual(0, sdk.create_calls)
        self.assertNotIn("sensitive", str(result.to_dict()))

    def test_query_exception_is_unknown_and_never_retried(self) -> None:
        context = RaisingOrderQueryContext()
        result = MoomooPaperOrderReconciler(
            endpoint=MoomooEndpoint(),
            sdk=FakeReconcileSdk(context),
        ).reconcile(
            "paper-dry-run-001",
            readiness=ready_decision(),
            preflight=successful_preflight(),
        )

        self.assertEqual(
            MoomooPaperOrderReconciliationStatus.UNKNOWN,
            result.status,
        )
        self.assertEqual("query", result.sanitized_failure_category)
        self.assertEqual("failed", result.query_status)
        self.assertEqual(1, len(context.order_query_calls))
        self.assertTrue(context.closed)
        self.assertNotIn("sensitive", str(result.to_dict()))

    def test_malformed_query_response_is_unknown(self) -> None:
        context = FakeReconcileContext()
        context.orders_response = (0, object())

        result = MoomooPaperOrderReconciler(
            endpoint=MoomooEndpoint(),
            sdk=FakeReconcileSdk(context),
        ).reconcile(
            "paper-dry-run-001",
            readiness=ready_decision(),
            preflight=successful_preflight(),
        )

        self.assertEqual(
            MoomooPaperOrderReconciliationStatus.UNKNOWN,
            result.status,
        )
        self.assertEqual("query", result.sanitized_failure_category)
        self.assertEqual(1, len(context.order_query_calls))

    def test_source_contains_no_order_mutation_live_or_retry_path(self) -> None:
        source = inspect.getsource(MoomooPaperOrderReconciler)
        self.assertNotIn("def _read_records", source)
        for forbidden in [
            "place_order",
            "modify_order",
            "cancel_order",
            "unlock_trade",
            "subscribe",
            "TrdEnv.REAL",
            "retry",
        ]:
            self.assertNotIn(forbidden, source)


class MoomooPaperOrderReconciliationReportTests(unittest.TestCase):
    def _unique_result(self):
        return MoomooPaperOrderReconciler(
            endpoint=MoomooEndpoint(),
            sdk=FakeReconcileSdk(),
        ).reconcile(
            "paper-dry-run-001",
            readiness=ready_decision(),
            preflight=successful_preflight(),
        )

    def test_deterministic_create_only_round_trip(self) -> None:
        result = self._unique_result()
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "nested" / "reconciliation.json"
            written = MoomooPaperOrderReconciliationReportWriter().write(
                report_path,
                result,
            )
            content = report_path.read_text(encoding="utf-8")
            loaded = MoomooPaperOrderReconciliationReportReader().read(report_path)

            with self.assertRaises(MoomooConfigurationError):
                MoomooPaperOrderReconciliationReportWriter().write(
                    report_path,
                    result,
                )

        self.assertEqual(report_path, written)
        self.assertEqual(result, loaded)
        self.assertEqual(
            json.dumps(result.to_dict(), sort_keys=True) + "\n",
            content,
        )
        self.assertNotIn("acc_id", content)
        self.assertNotIn('"order_id":', content)

    def test_reader_rejects_invalid_schema_shape_types_and_state(self) -> None:
        valid = self._unique_result().to_dict()
        cases = [
            {**valid, "schema_version": 2},
            {**valid, "unexpected": True},
            {key: value for key, value in valid.items() if key != "match_count"},
            {**valid, "status": "settled"},
            {**valid, "endpoint": "broker.example:11111"},
            {**valid, "sdk_version": "10.5"},
            {**valid, "client_order_id": "bad"},
            {**valid, "match_count": True},
            {**valid, "status": "absent", "match_count": 1},
            {**valid, "status": "duplicate", "match_count": 2},
            {
                **valid,
                "status": "blocked",
                "query_status": "not-run",
                "match_count": 0,
                "sanitized_failure_category": "account",
            },
            {
                **valid,
                "status": "unknown",
                "query_status": "not-run",
                "match_count": 0,
                "sanitized_failure_category": "account",
            },
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            for index, payload in enumerate(cases):
                path = Path(tmpdir) / f"invalid-{index}.json"
                path.write_text(json.dumps(payload), encoding="utf-8")
                with self.subTest(index=index), self.assertRaises(
                    MoomooConfigurationError
                ):
                    MoomooPaperOrderReconciliationReportReader().read(path)

            malformed = Path(tmpdir) / "malformed.json"
            malformed.write_text("{", encoding="utf-8")
            with self.assertRaises(MoomooConfigurationError):
                MoomooPaperOrderReconciliationReportReader().read(malformed)

    def test_reader_accepts_producer_blocked_and_unknown_states(self) -> None:
        blocked_context = FakeReconcileContext()
        blocked_context.accounts = (0, [])
        results = [
            MoomooPaperOrderReconciler(
                endpoint=MoomooEndpoint(),
                sdk=FakeReconcileSdk(blocked_context),
            ).reconcile(
                "paper-dry-run-001",
                readiness=ready_decision(),
                preflight=successful_preflight(),
            ),
            MoomooPaperOrderReconciler(
                endpoint=MoomooEndpoint(),
                sdk=FakeReconcileSdk(RaisingOrderQueryContext()),
            ).reconcile(
                "paper-dry-run-001",
                readiness=ready_decision(),
                preflight=successful_preflight(),
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            for index, result in enumerate(results):
                path = Path(tmpdir) / f"valid-{index}.json"
                MoomooPaperOrderReconciliationReportWriter().write(path, result)
                with self.subTest(status=result.status):
                    self.assertEqual(
                        result,
                        MoomooPaperOrderReconciliationReportReader().read(path),
                    )

    def test_writer_filesystem_failure_is_sanitized(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            parent_file = Path(tmpdir) / "not-a-directory"
            parent_file.write_text("occupied", encoding="utf-8")
            with self.assertRaisesRegex(
                MoomooConfigurationError,
                "could not write",
            ):
                MoomooPaperOrderReconciliationReportWriter().write(
                    parent_file / "report.json",
                    self._unique_result(),
                )

    def test_writer_treats_dangling_symlink_as_create_only_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "reconciliation.json"
            report_path.symlink_to(Path(tmpdir) / "missing-target.json")

            with self.assertRaisesRegex(
                MoomooConfigurationError,
                "already exists",
            ):
                MoomooPaperOrderReconciliationReportWriter().write(
                    report_path,
                    self._unique_result(),
                )


if __name__ == "__main__":
    unittest.main()
