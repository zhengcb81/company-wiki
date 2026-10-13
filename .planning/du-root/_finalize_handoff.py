"""Finalize the ROOT handoff: completion state, final counts, and the exact open gate."""

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / ".planning" / "du-root" / "handoff.json"

FINAL_STATS = {
    "profiles": 150,
    "structure": 47,
    "root": 99,
    "benchmark": 65,
    "total": 361,
    "note": "all four suites in ONE pytest invocation, as CI runs it: 361 passed, 5 skipped",
}

ROOT_INTERFACES = [
    {
        "module": "company_wiki.document_understanding",
        "symbol": "build_observation",
        "signature": "build_observation(units, *, source_id, source_sha256, title='', declared_kind='unknown', mime_type=..., language=None, native_scan='complete', opaque_pages=(), deferred_pages=()) -> dict  # du-input/1",
    },
    {
        "module": "company_wiki.document_understanding",
        "symbol": "understand_units",
        "signature": "understand_units(units, *, source_id, source_sha256, ..., limits=None, max_packages=400) -> dict  # du-pipeline/1",
    },
    {
        "module": "company_wiki.document_understanding",
        "symbol": "build_summary_input",
        "signature": "build_summary_input(pipeline_result, *, max_packages=40, max_chars=48000) -> dict  # du-summary-input/1",
    },
    {
        "module": "company_wiki.document_understanding",
        "symbol": "build_dependency_packages",
        "signature": "build_dependency_packages(structure, *, route=None, profile=None, max_packages=None, max_members=64) -> dict  # du-packages/1",
    },
    {
        "module": "company_wiki.document_understanding",
        "symbol": "is_selectable / selectable_unit_ids",
        "signature": "is_selectable(unit) -> bool; selectable_unit_ids(observation) -> list[str]",
    },
]

COMPLETED = [
    "Three lanes received by merge: DU-PROFILES (150 tests), DU-STRUCTURE (47), DU-BENCH (65).",
    "Parent package written: src/company_wiki/document_understanding/__init__.py.",
    "Adapter: existing NarrativeUnit -> du-input/1, including heading_level from numbering, "
    "measured columns, table header/caption/table_id, and the Q&A shadow marking.",
    "Orchestration: structure -> du-packages/1 with profile-driven section priority first and "
    "semantic kind as the within-band tiebreak.",
    "Selection bridge: dependency closure that only ever adds, keeping required context and "
    "negations attached.",
    "End-to-end pipeline: understand_units (du-pipeline/1), one call for the whole chain.",
    "Summary request: build_summary_input (du-summary-input/1), profile focus + ordered "
    "evidence with provenance + budget accounting + honest unread list. Never calls a model.",
    "B node: offline cross-layer suite (no network, no model).",
    "C node: real-original node runs and passes on the owner's originals (no skip), with "
    "SHA/mtime verified unchanged and zero copies into the worktree.",
    "Plan docs updated: plan README/progress/task_plan, docs/ARCHITECTURE.md, and an 8-line "
    "navigation prepend to the mother PWF (existing bytes preserved).",
]

OPEN_GATE = {
    "item": "implementation.md step 7 paid model node and step 8 production switch",
    "status": "NOT RUN - deliberately deferred, with a concrete reason",
    "reasons": [
        "The plan itself sequences this work into the parent plan's G4/G5 window: "
        "'生产切换与真实模型大节点按母计划 G4/G5 另行执行'. The plan also states this layer's "
        "G4/G5 acceptance must not be replaced or marked complete by this lane.",
        "The layer is intentionally not wired into the production parse/select/summarize entry "
        "point, so a 'same-config real summary' would first require the step-8 wiring that the "
        "plan places AFTER G4/G5.",
        "No cumulative USD/token cap is present in config.yaml (only per-call limits: "
        "llm.max_tokens=8192, llm_max_input_chars=120000). The historical llm_cost_log.csv "
        "already records ~43.0 USD and ~282.7M tokens over 7025 rows, far above the plan's "
        "cited $20/2M figure, so headroom against the real cumulative cap cannot be "
        "established from the files available here. Spending without that cannot be justified.",
    ],
    "provider_keys": (
        "Model credentials do exist in the main checkout's .env (DEEPSEEK/MINIMAX/MIMO), so "
        "this is a budget-and-sequencing gate, NOT a missing-configuration gate."
    ),
    "how_to_proceed": (
        "Confirm the current cumulative budget headroom, wire the layer into the production "
        "summary path, then run the real-model node and the parent plan G4/G5 reviews."
    ),
}


def main() -> int:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    data["status"] = "integrated_tested_not_wired_to_production"
    data["tests_passed"] = FINAL_STATS["total"]
    data["test_counts_by_suite"] = FINAL_STATS
    data["public_interfaces_root"] = ROOT_INTERFACES
    data["completed"] = COMPLETED
    data["open_gate"] = OPEN_GATE
    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"handoff.json updated: {len(data)} keys")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
