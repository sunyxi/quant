from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class Issue002PolicyDocsTests(unittest.TestCase):
    def test_scope_risk_broker_and_implementation_docs_exist(self) -> None:
        required_docs = [
            "docs/scope.md",
            "docs/risk-policy.md",
            "docs/broker-decision.md",
            "docs/implementation-plan.md",
        ]

        missing_docs = [
            doc_path for doc_path in required_docs if not (REPO_ROOT / doc_path).is_file()
        ]

        self.assertEqual([], missing_docs)

    def test_scope_defines_first_release_boundaries(self) -> None:
        scope = (REPO_ROOT / "docs/scope.md").read_text(encoding="utf-8")

        self.assertIn("JP equities", scope)
        self.assertIn("long-only", scope)
        self.assertIn("no overnight", scope)
        self.assertIn("Shadow Mode", scope)

    def test_risk_policy_defines_required_control_layers(self) -> None:
        risk_policy = (REPO_ROOT / "docs/risk-policy.md").read_text(encoding="utf-8")

        self.assertIn("Pre-trade", risk_policy)
        self.assertIn("In-trade", risk_policy)
        self.assertIn("Post-trade", risk_policy)
        self.assertIn("Kill Switch", risk_policy)

    def test_broker_decision_records_jp_and_us_boundaries(self) -> None:
        broker_decision = (REPO_ROOT / "docs/broker-decision.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("kabu Station", broker_decision)
        self.assertIn("IBKR", broker_decision)
        self.assertIn("SBI", broker_decision)
        self.assertIn("manual confirmation", broker_decision)

    def test_implementation_plan_maps_epics_to_initial_tasks(self) -> None:
        implementation_plan = (
            REPO_ROOT / "docs/implementation-plan.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Iteration 1", implementation_plan)
        self.assertIn("Iteration 2", implementation_plan)
        self.assertIn("Go / No-Go", implementation_plan)
        self.assertIn("ISSUE-003", implementation_plan)


if __name__ == "__main__":
    unittest.main()
