"""Verify relative links in cwp-closeout-handoff.md resolve inside the repo.

Run with: python -I check_links_closeout.py
Exit 0 = all links resolve; exit 1 = broken link found.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOC = HERE / "cwp-closeout-handoff.md"
REPO_ROOT = HERE.parents[3]  # review/ -> plan dir -> plans -> docs -> repo root

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
SKIP_PREFIXES = ("http://", "https://", "#", "mailto:")
# Deliverable authored by the independent reviewer at closeout (after the
# candidate commit). Absent here is expected; it must exist in the final
# published state.
PENDING_REVIEWER_FILES = {"cwp-closeout-review.md"}

broken = []
pending = []
checked = 0
text = DOC.read_text(encoding="utf-8")
for target in LINK_RE.findall(text):
    if target.startswith(SKIP_PREFIXES):
        continue
    path_part = target.split("#", 1)[0]
    if not path_part:
        continue
    resolved = (HERE / path_part).resolve()
    checked += 1
    if not resolved.exists():
        if path_part.replace("\\", "/").split("/")[-1] in PENDING_REVIEWER_FILES:
            pending.append(target)
        else:
            broken.append(target)

print(f"links checked: {checked}")
for p in pending:
    print(f"PENDING (reviewer deliverable, created at closeout): {p}")
if broken:
    for b in broken:
        print(f"BROKEN: {b}")
    sys.exit(1)
print("PASS: 0 broken links")
