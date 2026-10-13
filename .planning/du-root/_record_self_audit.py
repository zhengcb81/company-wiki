"""Record the self-audit findings and the corrected verification numbers in the handoff."""

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / ".planning" / "du-root" / "handoff.json"

SELF_AUDIT = {
    "method": (
        "Audited this layer's own work rather than re-running the suites: for every public "
        "symbol, is it referenced anywhere in src outside the module that defines it "
        "(.planning/du-root/_audit_dead_decisions.py)? The first version of that audit was "
        "itself wrong -- it ignored 'from x import y', which made every export look unused -- "
        "and was corrected before any conclusion was drawn."
    ),
    "defects_found_in_our_own_work": [
        {
            "defect": "the Q&A selectability decision was declared but never applied",
            "detail": (
                "The adapter marked text-layer units (hints.qa_text_shadow) and is_selectable() "
                "existed with 8 tests, but no code path consulted either. Two consumers were "
                "reachable on a real Q&A original: selection_bridge.dependency_closure could "
                "*add* a shadow unit back as required context or as negation protection, and "
                "summary_input.build_summary_input materialised shadow members into the "
                "model-facing evidence, sending every answer twice."
            ),
            "impact_measured": (
                "On the real 万润 IR original: 213 shadow units were being sent as evidence, "
                "and 53 of 74 packages were built purely from the duplicate copy."
            ),
            "fix": (
                "The decision now flows through the chain: understand_units derives the "
                "non-selectable ids, build_dependency_packages carries them, "
                "dependency_closure refuses to add them (reporting NOT_SELECTABLE_WITHHELD), "
                "and build_summary_input filters them, reports excluded.not_selectable, and "
                "defers a package left with nothing selectable as NOT_SELECTABLE."
            ),
            "verified_on_real_data": (
                "万润 IR: 213 units withheld, packages 40 -> 21, evidence text 6968 -> 3983 "
                "chars (~43% of what would have been sent was duplicate), 0 shadow units in "
                "the request, and the real negation (公司现无生产VC) still present via its "
                "structured unit. The other three originals show shdw=0 and are unchanged."
            ),
            "regression_lock": (
                "tests/unit/document_understanding_root/test_du_root_selectability_wiring.py "
                "(10 tests, written RED first: 6 failed before the fix)"
            ),
        },
        {
            "defect": "summary_input dropped structure's deferred_pages signal",
            "detail": (
                "The honest 'what was not read' report listed opaque pages but silently omitted "
                "caller-deferred pages, which is a different fact about a page."
            ),
            "fix": "unread now reports opaque_pages and deferred_pages separately.",
            "regression_lock": "test_unread_reports_scan_gaps, test_unread_keys_match_what_structure_actually_emits",
        },
    ],
    "checked_and_found_correct": [
        "Every key summary_input reads from structure.coverage is really emitted by the "
        "structure lane (asserted by a test, so a silent empty gap cannot reappear).",
        "The 5 previously-skipped benchmark tests are honest opt-in skips: with bindings "
        "generated outside the worktree and DU_BENCH_ALLOW_REAL_DATA=1 they all pass.",
        "HEAD was not broken during the session; two apparent failures (a missing "
        "_locator_of and a missing is_selectable import) were transient mid-write states of "
        "the concurrent writer, confirmed by re-reading after the files settled.",
    ],
    "verification_numbers": {
        "default_run": "371 passed, 5 skipped (real-data opt-ins off)",
        "maximum_coverage": (
            "383 passed, 0 skipped, with DU_BENCH_ALLOW_REAL_DATA=1 and DU_ROOT_BINDINGS set"
        ),
        "ruff": "All checks passed over src tests/unit tools",
        "acceptance_harness": "6 passed, 0 skipped, 0 failed, exit 0 (with real data enabled)",
        "benchmark_real_data": "70 passed, 49.6s (was 65 passed + 5 skipped)",
    },
    "still_open": (
        "No production caller imports this layer. That is step 8 by design, and it is the "
        "same gate recorded in open_gate (the paid model node and the production switch)."
    ),
}


def main() -> int:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    data["self_audit"] = SELF_AUDIT
    data["tests_passed"] = 383
    data["test_counts_by_suite"] = {
        "profiles": 150,
        "structure": 47,
        "root": 121,
        "benchmark": 70,
        "total_with_real_data": 383,
        "note": (
            "383 passed / 0 skipped across the four suites in ONE invocation with real data "
            "enabled; 371 passed / 5 skipped without the benchmark's real-data opt-in"
        ),
    }
    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"handoff.json updated: {len(data)} keys, {len(SELF_AUDIT['defects_found_in_our_own_work'])} self-found defects")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
