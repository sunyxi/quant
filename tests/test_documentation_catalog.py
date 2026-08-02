from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class DocumentationCatalogTests(unittest.TestCase):
    def test_required_planning_and_governance_docs_exist(self) -> None:
        required_docs = [
            "AGENT.md",
            "docs/roadmap.md",
            "docs/task-catalog.md",
            "docs/cli-usage.md",
            "docs/operations.md",
            "docs/limitations.md",
            "docs/rollback.md",
            "docs/moomoo-openapi.md",
            "docs/locales/en/overview.md",
            "docs/locales/ja/overview.md",
            "docs/locales/zh-CN/overview.md",
        ]

        missing_docs = [
            doc_path for doc_path in required_docs if not (REPO_ROOT / doc_path).is_file()
        ]

        self.assertEqual([], missing_docs)

    def test_agent_rules_document_captures_required_workflow(self) -> None:
        agent_doc = (REPO_ROOT / "AGENT.md").read_text(encoding="utf-8")

        required_terms = [
            "Test-first",
            "Repository Gates",
            "Documentation",
            "Generated Files",
            "Git and PR",
            "Draft PR",
            "GitHub App",
            "Do not merge",
        ]

        missing_terms = [term for term in required_terms if term not in agent_doc]

        self.assertEqual([], missing_terms)

    def test_agent_rules_issue_is_marked_complete(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-015"]["status"])

    def test_replay_review_issue_is_marked_complete(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-016"]["status"])

    def test_kabu_station_mapper_issue_is_marked_complete(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-017"]["status"])

    def test_kabu_station_contract_issue_is_marked_complete(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-018"]["status"])

    def test_kabu_station_token_client_issue_is_marked_complete(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-019"]["status"])

    def test_kabu_station_sendorder_client_issue_is_marked_complete(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-020"]["status"])

    def test_kabu_station_cancelorder_client_issue_is_marked_complete(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-021"]["status"])

    def test_kabu_station_readonly_client_issue_is_marked_complete(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-022"]["status"])

    def test_kabu_station_snapshot_mapper_issue_is_marked_complete(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-023"]["status"])

    def test_kabu_station_readonly_reconciler_issue_is_marked_complete(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-024"]["status"])

    def test_shadow_mode_readiness_gate_issue_is_marked_complete(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-025"]["status"])

    def test_shadow_mode_run_summary_issue_is_marked_complete(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-026"]["status"])

    def test_shadow_mode_summary_writer_issue_is_marked_complete(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-027"]["status"])

    def test_shadow_mode_summary_reader_issue_is_marked_complete(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-028"]["status"])

    def test_shadow_mode_summary_schema_version_issue_is_marked_complete(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-029"]["status"])

    def test_shadow_mode_summary_review_issue_is_marked_complete(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-030"]["status"])

    def test_shadow_mode_review_writer_issue_is_marked_complete(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-031"]["status"])

    def test_kabu_station_localhost_http_transport_issue_is_marked_complete(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-032"]["status"])

    def test_kabu_station_localhost_hardening_issue_is_marked_complete(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-033"]["status"])

    def test_moomoo_readonly_discovery_issue_is_marked_complete(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-035"]["status"])

    def test_moomoo_paper_readiness_issue_is_marked_complete(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-036"]["status"])

    def test_moomoo_paper_order_dry_run_issue_is_marked_complete(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-037"]["status"])

    def test_moomoo_paper_account_preflight_issue_is_marked_complete(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-038"]["status"])

    def test_moomoo_paper_order_submit_issue_is_marked_complete(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-039"]["status"])

    def test_moomoo_paper_order_reconcile_issue_is_marked_complete(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-040"]["status"])

    def test_moomoo_reconciliation_report_issue_is_marked_complete(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-041"]["status"])

    def test_moomoo_submission_report_issue_is_marked_complete(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}

        self.assertEqual("complete", tasks["ISSUE-042"]["status"])

    def test_moomoo_feature_doc_captures_offline_readiness_boundary(self) -> None:
        document = (REPO_ROOT / "docs/moomoo-openapi.md").read_text(
            encoding="utf-8"
        )

        for term in [
            "moomoo-paper-readiness",
            "offline",
            "READY",
            "BLOCKED",
            "does not authorize paper orders",
        ]:
            self.assertIn(term, document)

    def test_moomoo_feature_doc_captures_paper_order_dry_run_boundary(self) -> None:
        document = (REPO_ROOT / "docs/moomoo-openapi.md").read_text(
            encoding="utf-8"
        )

        for term in [
            "moomoo-paper-order-dry-run",
            "SIMULATE",
            "NORMAL",
            "DAY",
            "RTH",
            "does not select an account",
            "does not authorize a paper order",
        ]:
            self.assertIn(term, document)

    def test_moomoo_feature_doc_captures_paper_account_preflight_boundary(
        self,
    ) -> None:
        document = (REPO_ROOT / "docs/moomoo-openapi.md").read_text(
            encoding="utf-8"
        )

        for term in [
            "moomoo-paper-account-preflight",
            "refresh_cache=True",
            "STOCK_AND_OPTION",
            "does not include account identifiers",
            "does not authorize a paper order",
        ]:
            self.assertIn(term, document)

    def test_moomoo_feature_doc_captures_paper_submit_boundary(self) -> None:
        document = (REPO_ROOT / "docs/moomoo-openapi.md").read_text(
            encoding="utf-8"
        )

        for term in [
            "moomoo-paper-order-submit",
            "--acknowledge-paper-order-side-effect",
            "at most once",
            "UNKNOWN",
            "does not automatically retry",
            "SIMULATE only",
            "requires separate approval",
        ]:
            self.assertIn(term, document)

    def test_moomoo_docs_capture_paper_reconciliation_boundary(self) -> None:
        feature_doc = (REPO_ROOT / "docs/moomoo-openapi.md").read_text(
            encoding="utf-8"
        )
        for term in [
            "moomoo-paper-order-reconcile",
            "ABSENT",
            "not proof that no submission occurred",
            "refresh_cache=True",
            "does not automatically resubmit",
        ]:
            self.assertIn(term, feature_doc)

        for locale in ["en", "ja", "zh-CN"]:
            overview = (
                REPO_ROOT / f"docs/locales/{locale}/overview.md"
            ).read_text(encoding="utf-8")
            self.assertIn("moomoo-paper-order-reconcile", overview)
            self.assertIn("ABSENT", overview)

    def test_moomoo_docs_capture_reconciliation_report_boundary(self) -> None:
        feature_doc = (REPO_ROOT / "docs/moomoo-openapi.md").read_text(
            encoding="utf-8"
        )
        for term in [
            "--report-output",
            "create-only",
            "schema version 1",
            "offline",
            "moomoo-reconciliation-reports",
        ]:
            self.assertIn(term, feature_doc)

        gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("moomoo-reconciliation-reports/", gitignore)

        for locale in ["en", "ja", "zh-CN"]:
            overview = (
                REPO_ROOT / f"docs/locales/{locale}/overview.md"
            ).read_text(encoding="utf-8")
            self.assertIn("schema version 1", overview)
            self.assertIn("create-only", overview)

    def test_moomoo_docs_capture_submission_report_boundary(self) -> None:
        feature_doc = (REPO_ROOT / "docs/moomoo-openapi.md").read_text(
            encoding="utf-8"
        )
        for term in [
            "moomoo-submission-reports",
            "submission report",
            "place_order_call_count",
            "create-only",
            "offline",
        ]:
            self.assertIn(term, feature_doc)

        gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("moomoo-submission-reports/", gitignore)

        for locale in ["en", "ja", "zh-CN"]:
            overview = (
                REPO_ROOT / f"docs/locales/{locale}/overview.md"
            ).read_text(encoding="utf-8")
            self.assertIn("submission report", overview)
            self.assertIn("create-only", overview)

    def test_historical_orb_backtest_issue_is_complete_and_documented(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}
        feature_doc = (REPO_ROOT / "docs/historical-orb-backtest.md").read_text(
            encoding="utf-8"
        )

        self.assertEqual("complete", tasks["ISSUE-043"]["status"])
        self.assertIn(
            "Fixture / E2E Design Tests", tasks["ISSUE-043"]["gates"]
        )
        self.assertNotIn("Fixture Tests", tasks["ISSUE-043"]["gates"])
        for term in [
            "historical-orb-backtest",
            "Walk-Forward",
            "stop first",
            "cost sensitivity",
            "long-only",
            "does not download",
            "schema version 2",
            "default_parameter_full_period",
            "actual notional",
            "signal bar ATR",
            "test_days <= step_days <= train_days",
            "atomic",
        ]:
            self.assertIn(term, feature_doc)
        gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("historical-backtest-reports/", gitignore)
        for locale in ["en", "ja", "zh-CN"]:
            overview = (
                REPO_ROOT / f"docs/locales/{locale}/overview.md"
            ).read_text(encoding="utf-8")
            self.assertIn("ISSUE-043", overview)
            self.assertIn("Walk-Forward", overview)

    def test_orb_parameter_tuning_issue_is_complete_and_documented(self) -> None:
        source = json.loads(
            (REPO_ROOT / "docs/task-source.json").read_text(encoding="utf-8")
        )
        tasks = {task["id"]: task for task in source["tasks"]}
        feature_doc = (REPO_ROOT / "docs/orb-parameter-tuning.md").read_text(
            encoding="utf-8"
        )

        self.assertEqual("complete", tasks["ISSUE-044"]["status"])
        for term in [
            "historical-orb-backtest",
            "--tune",
            "192",
            "nested",
            "double-cost",
            "positive_parameter_neighbors",
            "max_signal_minutes_after_open",
            "min_breakout_close_location",
            "require_rising_vwap",
            "default_parameter_full_period",
            "schema version 4",
            "selected folds:        1 of 4",
            "no-go",
            "exploratory",
            "does not download",
        ]:
            self.assertIn(term, feature_doc)
        for locale in ["en", "ja", "zh-CN"]:
            overview = (
                REPO_ROOT / f"docs/locales/{locale}/overview.md"
            ).read_text(encoding="utf-8")
            self.assertIn("ISSUE-044", overview)
            self.assertIn("no-go", overview)

    def test_task_catalog_links_first_issue_to_roadmap_and_gates(self) -> None:
        task_catalog = (REPO_ROOT / "docs/task-catalog.md").read_text(encoding="utf-8")

        self.assertIn("ISSUE-001", task_catalog)
        self.assertIn("Roadmap", task_catalog)
        self.assertIn("Repository Gates", task_catalog)
        self.assertIn("Test-first Evidence", task_catalog)

    def test_task_catalog_is_generated_from_source_of_truth(self) -> None:
        script_path = REPO_ROOT / "scripts/generate_task_catalog.py"
        spec = importlib.util.spec_from_file_location("generate_task_catalog", script_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        source = module.json.loads(module.SOURCE_PATH.read_text(encoding="utf-8"))
        expected = module.render_catalog(source)
        actual = module.OUTPUT_PATH.read_text(encoding="utf-8")

        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
