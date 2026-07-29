from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class CIWorkflowTests(unittest.TestCase):
    def test_ci_workflow_exists(self) -> None:
        self.assertTrue((REPO_ROOT / ".github/workflows/ci.yml").is_file())

    def test_ci_workflow_runs_repository_gates(self) -> None:
        workflow = (REPO_ROOT / ".github/workflows/ci.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("python -m unittest discover -s tests", workflow)
        self.assertIn("scripts/check_markdown_links.py", workflow)
        self.assertIn("scripts/generate_task_catalog.py", workflow)
        self.assertIn("git diff --exit-code -- docs/task-catalog.md", workflow)
        self.assertIn("Secret Scan", workflow)


if __name__ == "__main__":
    unittest.main()
