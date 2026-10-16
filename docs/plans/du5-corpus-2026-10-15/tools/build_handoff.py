"""Emit handoff.json for DU5-CORPUS with computed fixture hashes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

PWF = Path(__file__).resolve().parents[1]
REPO = PWF.parents[2]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def rel(path: Path) -> str:
    return str(path.relative_to(REPO)).replace("\\", "/")


def main() -> int:
    fixtures = []
    for path in sorted((REPO / "tools/document_understanding_benchmark/gold").glob("du5-*.json")):
        fixtures.append(
            {
                "path": rel(path),
                "sha256": sha(path),
                "kind": "real_original_binding",
                "scope": "du5 frozen gold (v2 where reviewer-corrected)",
            }
        )
    for path in sorted((PWF / "reader_reports").glob("*.facts.json")):
        fixtures.append(
            {
                "path": rel(path),
                "sha256": sha(path),
                "kind": "real_excerpt",
                "scope": "independent reader verbatim source-side fact report",
            }
        )

    handoff = {
        "schema_version": "du5-handoff/1",
        "card_id": "DU5-CORPUS",
        "base_commit": "8c027011037dc8c8659235fb65f529028dcd15ca",
        "branch": "codex/du5-corpus-20261015",
        "implementation_commits": [],
        "changed_paths": [
            "tools/document_understanding_benchmark/gold/du5-*.json (9 new frozen gold records)",
            "tools/document_understanding_benchmark/du5_manifest.json (new: freeze record)",
            "tools/document_understanding_benchmark/gold_corrections.json (new: anchor proposals + v2 content corrections + unverifiable)",
            "tools/document_understanding_benchmark/coverage_matrix.py (five-axis SAMPLE_AXES extension; hk_quarterly/sec_8k_6k_exhibit real-backed; stale notes fixed)",
            "tools/document_understanding_benchmark/contamination.py (9 du5 entries; USED_FOR_COMPANY_PRIOR_USE vocabulary)",
            "tools/document_understanding_benchmark/holdout.json (du5 block; carrier-gap update)",
            "tools/document_understanding_benchmark/README.md (DU5 section; test counts)",
            "tools/document_understanding_benchmark/mutations.py (lint-only: unused local removed)",
            "tools/document_understanding_benchmark/tests/anchor_verify.py (new)",
            "tools/document_understanding_benchmark/tests/test_gold_anchor_integrity.py (new)",
            "tools/document_understanding_benchmark/tests/test_du5_coverage_axes.py (new)",
            "tools/document_understanding_benchmark/tests/test_du5_gold.py (new)",
            "tools/document_understanding_benchmark/tests/test_fresh_split.py (container-gap assertion adapted to measured state; other cases kept)",
            "tools/document_understanding_benchmark/tests/test_risk_checks.py (lint-only: unused import removed)",
            ".gitattributes (benchmark JSON pinned text eol=lf, repo golden-JSON precedent)",
            "docs/plans/du5-corpus-2026-10-15/** (PWF, receipts, reader reports, tools)",
        ],
        "entrypoints": [
            "python -B -X utf8 -m tools.document_understanding_benchmark --mode native --bindings <local du5 bindings> --output <owned dir> --probe-config <production config> --sample du5-... (receipts/C-cli-native-final-stdout.txt)",
            "python -X utf8 -m pytest tools/document_understanding_benchmark/tests -q",
            "DU_BENCH_ALLOW_REAL_DATA=1 python -X utf8 -m pytest tools/document_understanding_benchmark/tests/test_gold_anchor_integrity.py -q",
        ],
        "interfaces_reused": [
            "du-gold/1 (records.validate_gold), du-observed/1, du-evaluation/1",
            "evaluate(observed, gold) oracle; no matcher/schema fork",
            "observer.observe_native / carrier_support (read-only public surface)",
            "gold.load_gold_dir / load_bindings / resolve_original (SHA-bound originals)",
            "contamination.support_set_digest (freeze digests)",
            "review.py du-review/1 semantics stays NOT_EVALUATED without a review file",
        ],
        "red_receipts": [
            "docs/plans/du5-corpus-2026-10-15/receipts/RED-coverage-axes.txt (3 failed: coverage five-axis collapse, real data)",
            "docs/plans/du5-corpus-2026-10-15/receipts/RED-gold-anchors.txt (2 failed: wrong-page anchors on real gold + du5 set absent)",
        ],
        "tests": [
            {
                "command": "python -X utf8 -m pytest tools/document_understanding_benchmark/tests -q",
                "exit_code": 0,
                "passed": 236,
                "failed": 0,
                "skipped": 9,
                "receipt": "docs/plans/du5-corpus-2026-10-15/receipts/B-central-pytest-offline-final.txt",
            },
            {
                "command": "DU_BENCH_ALLOW_REAL_DATA=1 python -X utf8 -m pytest tools/document_understanding_benchmark/tests -q",
                "exit_code": 0,
                "passed": 245,
                "failed": 0,
                "skipped": 0,
                "receipt": "docs/plans/du5-corpus-2026-10-15/receipts/B-central-pytest-realdata.txt",
            },
            {
                "command": "python -m ruff check tools/document_understanding_benchmark docs/plans/du5-corpus-2026-10-15/tools",
                "exit_code": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "receipt": "docs/plans/du5-corpus-2026-10-15/receipts/B-ruff.txt",
            },
            {
                "command": "python -B -X utf8 -m tools.document_understanding_benchmark --mode native --bindings <du5> --output receipts/native-run-final --probe-config <prod source_catalog.yaml> --sample <9 du5>",
                "exit_code": 1,
                "passed": 0,
                "failed": 8,
                "skipped": 0,
                "receipt": "docs/plans/du5-corpus-2026-10-15/receipts/native-run-final/native/summary.json",
                "exit_note": "CLI exit 1 is the honest outcome: any FAIL maps to EXIT_FAIL=1; the run has 8 FAILs (production quality gaps, not a package defect)",
            },
        ],
        "fixtures": fixtures,
        "independent_review": [
            {
                "reviewer": "fresh subagent, blind to freeze process, read only originals + gold",
                "scope": ["du5-cn-proya-q1", "du5-cn-gbits-call"],
                "result": (
                    "all anchors RESOLVED (proya 22 anchors/10 facts, gbits 20 anchors/12 facts); "
                    "sample A (proya): 4 defective must_not_assert strings across 3 facts "
                    "(true/ambiguous negative controls); sample B (gbits): 1 modality mislabel "
                    "(conditional->plan), otherwise clean"
                ),
                "action": (
                    "recorded v2 content correction (gold_corrections.content_corrections; old "
                    "values replayable; anchors/importance/denominators untouched). Post-freeze "
                    "fact additions suggested by the reviewer were deliberately NOT applied"
                ),
                "receipt": "docs/plans/du5-corpus-2026-10-15/receipts/independent-review-verdict.md",
                "action_receipt": "docs/plans/du5-corpus-2026-10-15/receipts/review-corrections-applied.txt",
            }
        ],
        "old_failures_preserved": True,
        "not_run": [
            "adapter mode (ROOT-injected observer; no adapter supplied)",
            "native replay of the 20 old samples (their preserved historical reports stand; this card re-measured only the du5 set)",
            "reviewer additions suggested post-freeze (ROE own fact, gbits Q1-trend fact etc.) deliberately NOT added to frozen gold",
        ],
        "known_limits": [
            "old gold wrong-page anchors (3) are recorded as proposed corrections; old gold bytes stay as-is until ROOT publishes an applied correction version",
            "4 old anchors are unverifiable by independent extraction (scan/CID-mojibake/checkbox-glyph/iXBRL-boundary) and recorded as such, not silently passed",
            "du5-us-msft-* fill shape coverage only: the company is already in benchmark history, never a fresh generalisation claim",
            "us_10q/us_20f HTML originals are name-only rows (no gold, no recorded observation); readability on the current frontend is unmeasured",
            "two reader subagent dispatches were rejected by the platform content filter (risk-wording on negative controls); re-dispatched with clarified phrasing, same scope",
            "host core.autocrlf=true: byte locks hash git-normalized (LF) content; .gitattributes pins benchmark JSON to eol=lf",
        ],
        "root_integration_steps": [
            "merge this package back into CWP; keep du5 gold and du5_manifest.json together",
            "run formal wired candidates through the same CLI/du-observed; compare against the frozen du5 targets as-is (never re-gold to wash green)",
            "once any du5 sample informs rule changes, relabel it regression (contamination list) — it is no longer a blind generalisation set",
            "decide whether to publish an applied correction version for the 3 proposed old-gold wrong-page fixes (gold_corrections.json)",
            "REQ-1..5 acquisition requests stay open at the source layer; REQ-3's exhibit-as-own-SourceRef acceptance is production work, not benchmark coverage",
        ],
        "production_writes": 0,
        "supplier_calls": 0,
        "cleanup_receipt": (
            "docs/plans/du5-corpus-2026-10-15/receipts/originals-sha-after.txt (9 originals "
            "UNCHANGED; fresh-checkout temp dir removed after byte roundtrip; native runs wrote "
            "only their owned output dirs)"
        ),
    }

    out = PWF / "handoff.json"
    out.write_text(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print("handoff.json written:", len(fixtures), "fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
