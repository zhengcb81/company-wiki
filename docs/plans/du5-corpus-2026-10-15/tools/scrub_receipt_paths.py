"""Redact machine-local absolute original paths from committed receipts.

INTERFACES forbids committing local absolute original bindings. Receipts keep
every hash, count and verdict verbatim; only the machine-local path prefixes
become <ORIGINALS_ROOT> / <HOME> placeholders. The unredacted originals live
only on this host (the uncommitted bindings file).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEEP = {
    "construction_card.md",
    "task_plan.md",
    "INTERFACES.md",
    "handoff.md",
    "findings.md",
    "progress.md",
}

COMPANY_ROOTS = (
    ("C:\\\\Users\\\\郑曾波\\\\Projects\\\\company-wiki\\\\companies", "<ORIGINALS_ROOT>/companies"),
    ("C:\\Users\\郑曾波\\Projects\\company-wiki\\companies", "<ORIGINALS_ROOT>/companies"),
    ("C:/Users/郑曾波/Projects/company-wiki/companies", "<ORIGINALS_ROOT>/companies"),
)
HOME_RE = (
    (re.compile(r"C:\\\\\\\\Users\\\\\\\\郑曾波"), "<HOME>"),
    (re.compile(r"C:\\\\Users\\\\郑曾波"), "<HOME>"),
    (re.compile(r"C:\\Users\\郑曾波"), "<HOME>"),
    (re.compile(r"C:/Users/郑曾波"), "<HOME>"),
)


def main() -> int:
    changed: list[str] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".txt", ".json", ".log", ".md"}:
            continue
        if path.name in KEEP:
            continue
        try:
            text = path.read_bytes().decode("utf8")
        except UnicodeDecodeError:
            continue
        original = text
        for source, target in COMPANY_ROOTS:
            text = text.replace(source, target)
        for pattern, target in HOME_RE:
            text = pattern.sub(target, text)
        if text != original:
            path.write_bytes(text.encode("utf8"))
            changed.append(str(path.relative_to(ROOT)))
    print(f"scrubbed {len(changed)} files")
    for name in changed:
        print(" ", name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
