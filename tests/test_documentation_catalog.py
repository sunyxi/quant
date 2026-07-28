from __future__ import annotations

import unittest
import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class DocumentationCatalogTests(unittest.TestCase):
    def test_required_planning_and_governance_docs_exist(self) -> None:
        required_docs = [
            "docs/roadmap.md",
            "docs/task-catalog.md",
            "docs/cli-usage.md",
            "docs/operations.md",
            "docs/limitations.md",
            "docs/rollback.md",
            "docs/locales/en/overview.md",
            "docs/locales/ja/overview.md",
            "docs/locales/zh-CN/overview.md",
        ]

        missing_docs = [
            doc_path for doc_path in required_docs if not (REPO_ROOT / doc_path).is_file()
        ]

        self.assertEqual([], missing_docs)

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
