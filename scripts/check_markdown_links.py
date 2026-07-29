from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote


REPO_ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def iter_markdown_files() -> list[Path]:
    ignored = {".git", "__pycache__", ".venv"}
    files: list[Path] = []
    for path in REPO_ROOT.rglob("*.md"):
        if ignored.intersection(path.parts):
            continue
        files.append(path)
    return sorted(files)


def target_exists(source: Path, target: str) -> bool:
    if target.startswith(("http://", "https://", "mailto:")):
        return True
    clean_target = unquote(target.split("#", 1)[0])
    if not clean_target:
        return True
    return (source.parent / clean_target).resolve().exists()


def main() -> int:
    failures: list[str] = []
    for path in iter_markdown_files():
        text = path.read_text(encoding="utf-8")
        for match in LINK_RE.finditer(text):
            target = match.group(1).strip()
            if not target_exists(path, target):
                rel_path = path.relative_to(REPO_ROOT)
                failures.append(f"{rel_path}: broken link `{target}`")

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
