"""Record this audit's unreleased repairs without relabeling old snapshots."""
from pathlib import Path

path = Path("C:/Users/郑曾波/Projects/revenue-forecast/CHANGELOG.md")
text = path.read_text(encoding="utf-8")
marker = "## 4.1.0 (2026-09-18)"
assert "## Unreleased — 2026-10-08 cross-market source audit" not in text
assert marker in text
entry = """## Unreleased — 2026-10-08 cross-market source audit

- Accept filing-fetch schema-2 pathless candidates and verify their source reference, identity and period against the actual producer read. Annual requests may omit FY; nonannual periods remain explicit.
- Preserve unknown historical retrieval timestamps as null; record the actual verified read timestamp for the new local capture. Publication and as-of checks remain enforced.
- Represent already-recognized mixed-policy aggregates truthfully, only for direct recognized-revenue models with explicit aggregation boundaries and policy evidence. Reject progress, lag and carry-in transforms on these aggregates.
- Fix publication audit's anchor lookup: generation conflict keys are tuples, whereas input anchors are strings. Keep chain, conflict and unregistered-claim checks; add real CLI positive and negative regressions.
- Clarify sensitivity ratio units: a 5-percentage-point shock is 0.05, not 5.0. The engine already implements that contract; this documentation prevents malformed research inputs.
- Runtime identifies as 4.1.0/schema 3.7 during this workspace audit. Pin exact source hashes and commit identity for these repairs; keep all old inputs, publications and snapshots intact. Do not relabel old outputs as having passed the repaired audit.

"""
path.write_text(text.replace(marker, entry + marker, 1), encoding="utf-8")
print(path)
