from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class Issue034MoomooBrokerDecisionTests(unittest.TestCase):
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

        missing_terms = [term for term in required_terms if term not in decision]
        self.assertEqual([], missing_terms)

    def test_operational_docs_keep_moomoo_poc_read_only_and_non_live(self) -> None:
        paths = [
            "docs/cli-usage.md",
            "docs/operations.md",
            "docs/limitations.md",
            "docs/rollback.md",
        ]

        for path in paths:
            with self.subTest(path=path):
                content = (REPO_ROOT / path).read_text(encoding="utf-8")
                self.assertIn("Moomoo OpenAPI", content)
                self.assertIn("ISSUE-035", content)
                self.assertIn("no live orders", content)

    def test_operational_boundary_forbids_sdk_trade_unlock(self) -> None:
        operations = (REPO_ROOT / "docs/operations.md").read_text(encoding="utf-8")
        limitations = (REPO_ROOT / "docs/limitations.md").read_text(
            encoding="utf-8"
        )

        for content in [operations, limitations]:
            self.assertIn("unlock_trade", content)
            self.assertIn("must not", content)

    def test_next_issue_records_sdk_and_dependency_compatibility(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}
        issue_035 = json.dumps(tasks["ISSUE-035"], ensure_ascii=False)

        required_terms = [
            "moomoo-api",
            "10.4.6408",
            "127.0.0.1:11111",
            "protobuf",
            "unlock_trade",
            "JP equity market data",
        ]

        missing_terms = [term for term in required_terms if term not in issue_035]
        self.assertEqual([], missing_terms)

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
                content = (REPO_ROOT / path).read_text(encoding="utf-8")
                missing_terms = [term for term in terms if term not in content]
                self.assertEqual([], missing_terms)

    def test_task_source_records_decision_and_next_read_only_boundary(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-034"]["status"])
        self.assertEqual(["ISSUE-034"], tasks["ISSUE-035"]["dependencies"])
        self.assertEqual("pending", tasks["ISSUE-035"]["status"])
        self.assertIn("read-only", tasks["ISSUE-035"]["summary"])
        self.assertIn("macOS", tasks["ISSUE-035"]["summary"])


if __name__ == "__main__":
    unittest.main()
