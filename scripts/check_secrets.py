from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IGNORED_PARTS = {".git", "__pycache__", ".venv"}
IGNORED_SUFFIXES = {".pyc"}
SECRET_PATTERNS = [
    re.compile("AKIA" + r"[0-9A-Z]{16}"),
    re.compile("aws_" + "secret_" + "access_" + "key", re.IGNORECASE),
    re.compile("BEGIN " + r"(RSA|OPENSSH|PRIVATE)" + " KEY"),
    re.compile("ghp" + "_" + r"[A-Za-z0-9_]{20,}"),
    re.compile("github" + "_pat_" + r"[A-Za-z0-9_]+"),
]


def iter_files() -> list[Path]:
    files: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if IGNORED_PARTS.intersection(path.parts):
            continue
        if path.suffix in IGNORED_SUFFIXES:
            continue
        files.append(path)
    return sorted(files)


def main() -> int:
    failures: list[str] = []
    for path in iter_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if any(pattern.search(line) for pattern in SECRET_PATTERNS):
                rel_path = path.relative_to(REPO_ROOT)
                failures.append(f"{rel_path}:{line_number}: potential secret")

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
