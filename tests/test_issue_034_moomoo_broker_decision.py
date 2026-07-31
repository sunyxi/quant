from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class Issue034MoomooBrokerDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.operational_docs = {
            path: (REPO_ROOT / path).read_text(encoding="utf-8")
            for path in [
                "docs/cli-usage.md",
                "docs/operations.md",
                "docs/limitations.md",
                "docs/rollback.md",
                "docs/locales/en/overview.md",
                "docs/locales/ja/overview.md",
                "docs/locales/zh-CN/overview.md",
            ]
        }
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        cls.tasks = {task["id"]: task for task in source["tasks"]}

    def _assert_contains_all(self, content: str, terms: list[str]) -> None:
        missing_terms = [term for term in terms if term not in content]
        self.assertEqual([], missing_terms, f"Missing terms: {missing_terms}")

    def test_broker_decision_prioritizes_moomoo_without_overstating_jp_support(
        self,
    ) -> None:
        decision = (REPO_ROOT / "docs/broker-decision.md").read_text(
            encoding="utf-8"
        )

        required_terms = [
            "Moomoo OpenAPI",
            "first API proof of concept",
            "macOS",
            "US equities",
            "JP equity market data is supported",
            "does not support live JP cash-equity trading",
            "moomoo-api",
            "10.4.6408",
            "127.0.0.1:11111",
            "kabu Station",
            "IBKR",
        ]

        self._assert_contains_all(decision, required_terms)

    def test_operational_docs_keep_moomoo_poc_read_only_and_non_live(self) -> None:
        paths = [
            "docs/cli-usage.md",
            "docs/operations.md",
            "docs/limitations.md",
            "docs/rollback.md",
        ]

        for path in paths:
            with self.subTest(path=path):
                self._assert_contains_all(
                    self.operational_docs[path],
                    ["Moomoo OpenAPI", "ISSUE-035", "no live orders"],
                )

    def test_operational_boundary_forbids_sdk_trade_unlock(self) -> None:
        for path in ["docs/operations.md", "docs/limitations.md"]:
            with self.subTest(path=path):
                self._assert_contains_all(
                    self.operational_docs[path], ["unlock_trade", "must not"]
                )

    def test_next_issue_records_sdk_and_dependency_compatibility(self) -> None:
        criteria = " ".join(self.tasks["ISSUE-035"]["acceptance_criteria"])

        required_terms = [
            "moomoo-api",
            "10.4.6408",
            "127.0.0.1:11111",
            "protobuf",
            "unlock_trade",
            "JP equity market data",
        ]

        self._assert_contains_all(criteria, required_terms)

    def test_localized_overviews_record_moomoo_priority_and_jp_boundary(self) -> None:
        expected_terms = {
            "docs/locales/en/overview.md": [
                "Moomoo OpenAPI",
                "US equities",
                "JP cash-equity",
            ],
            "docs/locales/ja/overview.md": [
                "Moomoo OpenAPI",
                "米国株",
                "日本株現物",
            ],
            "docs/locales/zh-CN/overview.md": [
                "Moomoo OpenAPI",
                "美股",
                "日股现货",
            ],
        }

        for path, terms in expected_terms.items():
            with self.subTest(path=path):
                self._assert_contains_all(self.operational_docs[path], terms)

    def test_task_source_records_decision_and_next_read_only_boundary(self) -> None:
        self.assertEqual("complete", self.tasks["ISSUE-034"]["status"])
        self.assertEqual(["ISSUE-034"], self.tasks["ISSUE-035"]["dependencies"])
        self.assertEqual("complete", self.tasks["ISSUE-035"]["status"])
        self.assertIn("read-only", self.tasks["ISSUE-035"]["summary"])
        self.assertIn("macOS", self.tasks["ISSUE-035"]["summary"])


if __name__ == "__main__":
    unittest.main()
