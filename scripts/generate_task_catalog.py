from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = REPO_ROOT / "docs" / "task-source.json"
OUTPUT_PATH = REPO_ROOT / "docs" / "task-catalog.md"


def render_catalog(source: dict) -> str:
    lines = [
        "# Task Catalog",
        "",
        "<!-- GENERATED FILE: rebuild with `python3 scripts/generate_task_catalog.py`. -->",
        "",
        f"Catalog version: `{source['catalog_version']}`",
        f"Source of Truth: `{source['source_of_truth']}`",
        "",
        "## Repository Gates",
        "",
        "Every Issue reports each applicable gate as `passed`, `failed`, `not-run`, or `skipped`.",
        "A gate that did not execute must never be reported as passed.",
        "",
    ]

    for task in source["tasks"]:
        anchor = task["phase"].lower().replace(" ", "-").replace(".", "")
        lines.extend(
            [
                f"## {task['id']}: {task['title']}",
                "",
                f"- Status: `{task['status']}`",
                f"- Phase: `{task['phase']}`",
                f"- Dependencies: {', '.join(task['dependencies']) if task['dependencies'] else 'None'}",
                f"- Roadmap: see `docs/roadmap.md#{anchor}`",
                f"- Summary: {task['summary']}",
                "",
                "### Acceptance Criteria",
                "",
            ]
        )
        lines.extend(f"- {item}" for item in task["acceptance_criteria"])
        lines.extend(["", "### Gates", ""])
        lines.extend(f"- {gate}" for gate in task["gates"])
        lines.extend(["", "### Changed Assets", ""])
        lines.extend(f"- `{asset}`" for asset in task["changed_assets"])
        lines.extend(
            [
                "",
                "### Test-first Evidence",
                "",
                "- Red: required before implementation starts.",
                "- Green: required after implementation.",
                "- Refactor: optional, but must keep gates accurate.",
                "",
                f"Rollback: {task['rollback']}",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    OUTPUT_PATH.write_text(render_catalog(source), encoding="utf-8")


if __name__ == "__main__":
    main()
