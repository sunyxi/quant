from __future__ import annotations

import json
import unittest
from dataclasses import replace

from autotrade.execution.moomoo import MoomooDiscoveryResult
from autotrade.execution.moomoo_readiness import (
    MoomooPaperReadinessGate,
    MoomooPaperReadinessReason,
    MoomooPaperReadinessStatus,
)


def ready_discovery() -> MoomooDiscoveryResult:
    return MoomooDiscoveryResult(
        endpoint="127.0.0.1:11111",
        sdk_version="10.9.6908",
        server_version="1009",
        quote_connection_status="ok",
        trade_connection_status="ok",
        qot_logged_in=True,
        trd_logged_in=True,
        us_quote_entitlement="LV1",
        jp_quote_entitlement="UNKNOWN",
        account_count=2,
        paper_account_count=1,
        real_account_count=1,
        paper_account_available=True,
        us_market_authorized=True,
    )


class MoomooPaperReadinessGateTests(unittest.TestCase):
    def test_ready_decision_contains_only_sanitized_evidence(self) -> None:
        decision = MoomooPaperReadinessGate().evaluate(ready_discovery())

        self.assertEqual(MoomooPaperReadinessStatus.READY, decision.status)
        self.assertTrue(decision.is_ready)
        self.assertEqual([], decision.reason_codes)
        self.assertEqual(
            {
                "discovery_schema_version": 1,
                "quote_connection_ok": True,
                "trade_connection_ok": True,
                "qot_logged_in": True,
                "trd_logged_in": True,
                "paper_account_count": 1,
                "paper_account_available": True,
                "us_market_authorized": True,
                "us_quote_entitlement": "LV1",
            },
            decision.evidence,
        )
        self.assertEqual(
            {
                "schema_version": 1,
                "status": "READY",
                "reason_codes": [],
                "evidence": decision.evidence,
            },
            decision.to_dict(),
        )

    def test_each_missing_requirement_has_a_fixed_blocking_reason(self) -> None:
        cases = [
            (
                {"quote_connection_status": "not-run"},
                MoomooPaperReadinessReason.QUOTE_CONNECTION_NOT_OK,
            ),
            (
                {"trade_connection_status": "not-run"},
                MoomooPaperReadinessReason.TRADE_CONNECTION_NOT_OK,
            ),
            (
                {"qot_logged_in": False},
                MoomooPaperReadinessReason.QUOTE_NOT_LOGGED_IN,
            ),
            (
                {"trd_logged_in": False},
                MoomooPaperReadinessReason.TRADE_NOT_LOGGED_IN,
            ),
            (
                {"paper_account_count": 0, "paper_account_available": False},
                MoomooPaperReadinessReason.PAPER_ACCOUNT_UNAVAILABLE,
            ),
            (
                {"us_market_authorized": False},
                MoomooPaperReadinessReason.US_MARKET_UNAUTHORIZED,
            ),
            (
                {"us_quote_entitlement": "UNKNOWN"},
                MoomooPaperReadinessReason.US_QUOTE_ENTITLEMENT_UNAVAILABLE,
            ),
            (
                {"us_quote_entitlement": "NO"},
                MoomooPaperReadinessReason.US_QUOTE_ENTITLEMENT_UNAVAILABLE,
            ),
        ]

        for changes, reason in cases:
            with self.subTest(reason=reason):
                decision = MoomooPaperReadinessGate().evaluate(
                    replace(ready_discovery(), **changes)
                )
                self.assertEqual(MoomooPaperReadinessStatus.BLOCKED, decision.status)
                self.assertEqual([reason], decision.reason_codes)

    def test_failed_discovery_blocks_without_derived_noise(self) -> None:
        discovery = replace(
            ready_discovery(),
            quote_connection_status="not-run",
            trade_connection_status="not-run",
            sanitized_failure_category="connection",
        )

        decision = MoomooPaperReadinessGate().evaluate(discovery)

        self.assertEqual(MoomooPaperReadinessStatus.BLOCKED, decision.status)
        self.assertEqual(
            [MoomooPaperReadinessReason.DISCOVERY_FAILED],
            decision.reason_codes,
        )

    def test_untrusted_entitlement_is_sanitized_and_blocked(self) -> None:
        decision = MoomooPaperReadinessGate().evaluate(
            replace(
                ready_discovery(),
                us_quote_entitlement="sensitive entitlement payload",
            )
        )

        self.assertEqual(MoomooPaperReadinessStatus.BLOCKED, decision.status)
        self.assertEqual(
            [MoomooPaperReadinessReason.US_QUOTE_ENTITLEMENT_UNAVAILABLE],
            decision.reason_codes,
        )
        serialized = json.dumps(decision.to_dict(), sort_keys=True)
        self.assertNotIn("sensitive", serialized)
        self.assertEqual("UNKNOWN", decision.evidence["us_quote_entitlement"])

    def test_multiple_reasons_have_deterministic_policy_order(self) -> None:
        discovery = replace(
            ready_discovery(),
            quote_connection_status="not-run",
            trd_logged_in=False,
            paper_account_count=0,
            paper_account_available=False,
            us_market_authorized=False,
            us_quote_entitlement="UNKNOWN",
        )

        decision = MoomooPaperReadinessGate().evaluate(discovery)

        self.assertEqual(
            [
                MoomooPaperReadinessReason.QUOTE_CONNECTION_NOT_OK,
                MoomooPaperReadinessReason.TRADE_NOT_LOGGED_IN,
                MoomooPaperReadinessReason.PAPER_ACCOUNT_UNAVAILABLE,
                MoomooPaperReadinessReason.US_MARKET_UNAUTHORIZED,
                MoomooPaperReadinessReason.US_QUOTE_ENTITLEMENT_UNAVAILABLE,
            ],
            decision.reason_codes,
        )


if __name__ == "__main__":
    unittest.main()
