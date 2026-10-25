"""Verify the bounded Wuxi annual14 source replay without changing artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[6]
EVIDENCE = ROOT / "companies/药明康德/raw/financial_reports/药明康德：2025年年度报告.pdf"
CHECKLIST = ROOT / "docs/plans/du11-source-closure-2026-10-18/review/r1-w08-crosspage-20261024/annual14/review.json"
OBSERVER = ROOT / "docs/plans/du11-source-closure-2026-10-18/review/r1-w08-crosspage-20261024/annual14-v2/trace_targets.py"
SOURCE_DIR = ROOT / "src/company_wiki"
CODE = SOURCE_DIR / "document_understanding/structure/sections.py"
TEST = ROOT / "tests/unit/document_understanding_selection/test_reading_native_list_ancestry.py"
OUTPUT = HERE / "parent-context-check-v3.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def require(condition: bool, message: str) -> None:
    """Keep evidence checks active under every Python optimization mode."""
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    selection_path = HERE / "selection.json"
    trace_path = HERE / "trace.json"
    receipt_path = HERE / "replay-receipt.json"
    wrapper_path = HERE / "replay_all_targets.py"
    require(not OUTPUT.exists(), f"Refusing to overwrite {OUTPUT.name}")
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    # Bind every replay input/output named in the receipt before interpreting it.
    require(receipt["selection_sha256"] == sha256(selection_path), "Selection hash differs from replay receipt")
    require(receipt["trace_sha256"] == sha256(trace_path), "Trace hash differs from replay receipt")
    require(receipt["wrapper_sha256"] == sha256(wrapper_path), "Runner hash differs from replay receipt")
    require(receipt["observer_sha256"] == sha256(OBSERVER), "Observer hash differs from replay receipt")
    require(receipt["checklist_sha256"] == sha256(CHECKLIST), "Checklist hash differs from replay receipt")

    # The observer hashed the full production Python tree before and after replay.
    source_files = sorted(SOURCE_DIR.rglob("*.py"))
    source_inventory = {
        str(path.relative_to(ROOT)): sha256(path) for path in source_files
    }
    source_digest = hashlib.sha256(
        json.dumps(source_inventory, sort_keys=True).encode("utf-8")
    ).hexdigest()
    require(len(source_files) == receipt["source_count"], "Production source-file count changed since replay")
    require(source_digest == receipt["source_digest"], "Production source-tree digest changed since replay")

    page14_units = [
        row for row in trace["targets"]
        if row.get("coordinates", {}).get("page_number") == 14
    ]
    parent_rows = [
        row for row in page14_units
        if "TIDES" in row.get("text_excerpt", "")
        and ("多肽" in row.get("text_excerpt", "") or "寡核苷酸" in row.get("text_excerpt", ""))
    ]
    require(len(parent_rows) == 1, "Expected one source-marked TIDES parent on page 14")
    parent_id = parent_rows[0]["id"]

    child_rows = {
        "ST-A08": [
            row for row in page14_units
            if "ST-A08" in row.get("target", []) and "TIDES D&M" in row.get("text_excerpt", "")
        ],
        "ST-A09": [
            row for row in page14_units
            if "ST-A09" in row.get("target", []) and "100,000L" in row.get("text_excerpt", "")
        ],
    }
    require(all(len(rows) == 1 for rows in child_rows.values()), "Expected exact page-14 child targets")
    child_ids = {name: rows[0]["id"] for name, rows in child_rows.items()}

    eligible_parent_context: dict[str, bool] = {}
    for name, child_id in child_ids.items():
        packages = [
            package for package in trace["eligible_targets"]
            if child_id in package.get("member_unit_ids", ())
        ]
        require(bool(packages), f"No eligible package contains {name} child")
        eligible_parent_context[name] = all(
            parent_id in package.get("required_context_unit_ids", ()) for package in packages
        )
    require(all(eligible_parent_context.values()), "A child package lost its source parent context")

    parent_decisions = [
        row for row in trace["budget_target_decisions"] if row.get("id") == parent_id
    ]
    require(len(parent_decisions) == 1, "Expected one parent budget decision")
    parent_selected_as_context = bool(
        parent_decisions[0].get("selected") and parent_decisions[0].get("context_only")
    )
    require(parent_selected_as_context, "The TIDES parent must remain context, not a business claim")

    selected_spans = selection["selected_spans"]
    date_spans = [
        row for row in selected_spans
        if "2025年9月" in compact(row.get("raw_text", ""))
        and "提前完成" in compact(row.get("raw_text", ""))
        and "100,000L" not in compact(row.get("raw_text", ""))
    ]
    capacity_spans = [
        row for row in selected_spans
        if "100,000L" in compact(row.get("raw_text", ""))
        and "2025年9月" not in compact(row.get("raw_text", ""))
    ]
    require(bool(date_spans and capacity_spans), "Both source facts should be selected separately")
    require(
        not ({row["span_id"] for row in date_spans} & {row["span_id"] for row in capacity_spans}),
        "Date and capacity must remain separate spans",
    )

    pair_edges = [
        edge for edge in trace["target_adjacency_edges"]
        if "2025" in edge.get("left_excerpt", "")
        and "泰兴" in edge.get("left_excerpt", "")
        and "100,000L" in edge.get("right_excerpt", "")
    ]
    require(bool(pair_edges), "Expected the date/capacity adjacency to be observed")
    no_inferred_link = all(not edge.get("dependency_added") for edge in pair_edges)
    require(no_inferred_link, "Date and capacity must not be converted into a causal dependency")

    source_ref = selection["source_ref"]
    original_sha = sha256(EVIDENCE)
    require(source_ref["content_sha256"] == original_sha, "SourceRef SHA differs from original document")
    require(source_ref["byte_size"] == EVIDENCE.stat().st_size, "SourceRef byte size differs from original document")
    require(selection["selection_limit"] == 112, "Replay did not use the reported production selection limit")
    require(selection["selected_count"] <= selection["selection_limit"], "Selection exceeds its reported limit")
    require(selection["selected_chars"] <= 48_000, "Selection exceeds the production character limit")
    require(selection["work_budget"]["used"] <= 16_000_000, "Replay exceeds the production work budget")
    require(selection["work_budget"]["limit"] == 16_000_000, "Replay work-budget limit changed")
    require(receipt["source_stable"] and receipt["protected_unchanged"], "Source or protected configuration changed during replay")
    require(
        receipt["downloads"] == receipt["external_model_calls"] == receipt["raw_copies"] == 0,
        "Replay must remain offline with no downloads, model calls, or raw copies",
    )

    checks = {
        "schema_version": "wuxi-annual14-parent-context-check/3",
        "replay_receipt_sha256": sha256(receipt_path),
        "verifier_sha256": sha256(Path(__file__).resolve()),
        "wrapper_sha256": sha256(wrapper_path),
        "observer_sha256": sha256(OBSERVER),
        "checklist_sha256": sha256(CHECKLIST),
        "selection_sha256": sha256(selection_path),
        "trace_sha256": sha256(trace_path),
        "source_count": len(source_files),
        "source_tree_sha256": source_digest,
        "code_sha256": sha256(CODE),
        "test_sha256": sha256(TEST),
        "original_sha256": original_sha,
        "original_bytes": EVIDENCE.stat().st_size,
        "production_selection_limit": selection["selection_limit"],
        "selected_count": selection["selected_count"],
        "selected_chars": selection["selected_chars"],
        "work_used": selection["work_budget"]["used"],
        "parent_unit_id": parent_id,
        "parent_context_in_child_packages": eligible_parent_context,
        "parent_selected_as_context_only": parent_selected_as_context,
        "separate_date_span_count": len(date_spans),
        "separate_capacity_span_count": len(capacity_spans),
        "date_capacity_dependency_added": any(edge.get("dependency_added") for edge in pair_edges),
        "content_quality_regraded": False,
        "external_model_calls": 0,
        "downloads": 0,
        "raw_copies": 0,
    }
    try:
        with OUTPUT.open("x", encoding="utf-8") as result_file:
            result_file.write(json.dumps(checks, ensure_ascii=False, indent=2) + "\n")
    except FileExistsError as exc:
        raise RuntimeError(f"Refusing to overwrite {OUTPUT.name}") from exc
    print(json.dumps(checks, ensure_ascii=False))


if __name__ == "__main__":
    main()
