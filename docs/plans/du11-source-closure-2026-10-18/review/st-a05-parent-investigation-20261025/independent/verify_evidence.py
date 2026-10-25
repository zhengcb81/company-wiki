"""Read-only cross-check of the frozen ST-A05 replay artifacts.

Reads only already-produced JSON evidence; does not load source originals,
configuration, credentials, network services, or project code.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[6]
NODE = ROOT / "docs/plans/du11-source-closure-2026-10-18/review/st-a05-parent-investigation-20261025"
REVIEW = ROOT / "docs/plans/du11-source-closure-2026-10-18/review/annual14-current-source-review-20261025/independent/report.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


baseline = load(REVIEW)
old = load(NODE / "attempt01/model-view.json")
selection = load(NODE / "attempt02/selection.json")
model = load(NODE / "attempt02/model-view.json")
receipt = load(NODE / "attempt02/replay-receipt.json")
test_receipt = load(NODE / "review-final/final-receipt.json")

selected = {row["span_id"]: row for row in selection["selected_spans"]}
payload_roles: dict[str, set[str]] = {}
for task in model["tasks"]:
    for role in ("support_span_ids", "context_span_ids", "member_span_ids"):
        for span_id in task.get(role, []):
            payload_roles.setdefault(span_id, set()).add(role)

passed_targets = [row for row in baseline["targets"] if row["source_input_status"] == "PASS"]
require(len(passed_targets) == 10, "baseline no longer contains exactly ten PASS targets")
target_results = []
for target in passed_targets:
    evidence_ids = target["selected_span_ids"]
    absent = [span_id for span_id in evidence_ids if span_id not in selected or span_id not in payload_roles]
    if target["target_id"] != "ST-A03":
        require(not absent, f"previous PASS evidence absent from current payload: {target['target_id']}")
        target_results.append({"target_id": target["target_id"], "result": "all prior spans selected and in model payload"})
        continue

    # A03's old p16 paragraph 19 was an ambiguous table row. Verify the current
    # model input instead carries the exact p11 geography facts and p16
    # customer-parent-location note that the prior review relied on.
    missing_rows = [row for row in target["evidence"] if row["span_id"] in absent]
    require(len(absent) == 1 and len(missing_rows) == 1, "unexpected ST-A03 evidence drift")
    require("table_structure_ambiguous" in missing_rows[0].get("quality_flags", []),
            "ST-A03 missing prior span was not the reviewed ambiguous table row")
    geography_id = "urn:company-wiki:evidence-span:sha256:0f0490413de7b4c10c3cf177acfe4c98919f10ced32d725e0a5f759b8d24ede7"
    basis_id = "urn:company-wiki:evidence-span:sha256:9c4b962c24f4e14cf7977bb9270f87e8e1c4e71971c94aeb80512cdad4d49505"
    require(geography_id in selected and geography_id in payload_roles, "ST-A03 p11 region facts not in actual payload")
    require(basis_id in selected and basis_id in payload_roles, "ST-A03 p16 geography basis note not in actual payload")
    require("table_structure_ambiguous" in missing_rows[0].get("quality_flags", []), "ambiguous table exception changed")
    target_results.append({
        "target_id": "ST-A03",
        "result": "current p11 region-revenue fact and p16 parent-location basis note are in model payload; old ambiguous p16 table row is omitted",
        "omitted_locator": missing_rows[0]["locator"],
    })

old_a13 = set(old["a13"]["policy_span_ids"])
current_a13 = set(model["a13"]["policy_span_ids"])
require(len(current_a13) == 7 and current_a13 == old_a13, "A13 source input set changed")
page119 = [locator for locator in model["a13"]["policy_locators"] if "page:119/" in locator]
require(len(page119) == 2, "A13's two page-119 policy locators are not retained")
require(all(span_id in selected and span_id in payload_roles for span_id in current_a13),
        "A13 policy input is selected but not actually present in compiled task payload")

# Confirm current A05 has relevant local facts but lacks the cross-page parent
# in the actual D&M/TIDES tasks; candidate selection alone is not acceptance.
chemistry_parent = next(
    row for row in selection["selected_spans"]
    if row["locator"].startswith("loc:v1/page:13/paragraph:21")
    and row["raw_text"].startswith("(1) 化学业务")
)
dm_fact = next(row for row in selection["selected_spans"] if row["locator"].startswith("loc:v1/page:14/paragraph:3"))
tides_fact = next(row for row in selection["selected_spans"] if row["locator"].startswith("loc:v1/page:14/paragraph:12"))
descendant_tasks = [
    task for task in model["tasks"]
    if dm_fact["span_id"] in task.get("support_span_ids", [])
    or tides_fact["span_id"] in task.get("support_span_ids", [])
]
require(descendant_tasks, "current D&M/TIDES facts are absent from actual model tasks")
require(all(chemistry_parent["span_id"] not in (
    task.get("support_span_ids", []) + task.get("context_span_ids", []) + task.get("member_span_ids", [])
) for task in descendant_tasks), "A05 parent unexpectedly appears in descendant task input")
deferred_pages = selection["reading_context"]["layout_coverage"]["deferred_pages"]
require(selection["coverage_complete"] is False, "A05 replay unexpectedly claims complete coverage")
require(13 not in deferred_pages and 14 not in deferred_pages, "local A05 endpoint pages changed coverage state")
require(any(page not in {13, 14} for page in deferred_pages), "no unrelated deferred-page case remains to assess")
require(receipt["source_stable"] is True and selection["source_original_sha_verified"] is True,
        "real SourceRef replay is not stable/original-byte verified")
require(receipt["selected_count"] == 112 and receipt["selected_chars"] == 9030,
        "production selection cap or replay output changed")
require(receipt["work_budget"]["used"] == 12978295 and receipt["work_budget"]["limit"] == 16000000,
        "shared work budget evidence changed")
require(receipt["external_model_calls"] == receipt["downloads"] == receipt["raw_copies"] == 0,
        "replay crossed an external or raw-copy boundary")
require(test_receipt["exit_code"] == 0 and test_receipt["elapsed_seconds"] < 20,
        "focused final test run did not pass within expected time")
require(test_receipt["owned_test_root_restored_to_absent"] is True,
        "focused pytest temp root was not restored")

paths = [
    "src/company_wiki/document_understanding/structure/__init__.py",
    "src/company_wiki/document_understanding/structure/layout.py",
    "src/company_wiki/document_understanding/structure/sections.py",
    "tests/unit/document_understanding_structure/test_page_counter_furniture.py",
    "tests/unit/document_understanding_selection/test_reading_multilevel_native_ancestry.py",
    "tests/unit/document_understanding_selection/test_reading_decision_inventory.py",
    "docs/plans/du11-source-closure-2026-10-18/review/st-a05-parent-investigation-20261025/attempt02/replay-receipt.json",
    "docs/plans/du11-source-closure-2026-10-18/review/st-a05-parent-investigation-20261025/attempt02/selection.json",
    "docs/plans/du11-source-closure-2026-10-18/review/st-a05-parent-investigation-20261025/attempt02/model-view.json",
    "docs/plans/du11-source-closure-2026-10-18/review/st-a05-parent-investigation-20261025/review-final/final-receipt.json",
    "docs/plans/du11-source-closure-2026-10-18/review/annual14-current-source-review-20261025/independent/report.json",
    "docs/plans/du11-source-closure-2026-10-18/review/st-a05-parent-investigation-20261025/independent/verify_evidence.py",
]

print(json.dumps({
    "schema_version": "independent-st-a05-evidence-probe/1",
    "head": __import__("subprocess").check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "result": "PASS_ENGINEERING_SUBNODE__A05_OVERALL_OPEN",
    "old_10_pass": {"count": len(passed_targets), "targets": target_results},
    "a13": {
        "span_count": len(current_a13),
        "same_span_set_as_attempt01": True,
        "all_spans_in_compiled_payload": True,
        "page119_locators": page119,
    },
    "a05": {
        "local_facts_in_actual_tasks": [dm_fact["locator"], tides_fact["locator"]],
        "chemistry_parent_selected_but_absent_from_descendant_tasks": chemistry_parent["locator"],
        "coverage_complete": selection["coverage_complete"],
        "endpoint_pages_in_deferred_list": [page for page in (13, 14) if page in deferred_pages],
        "unrelated_deferred_page_count": len(deferred_pages),
    },
    "limits": {
        "selected_spans": receipt["selected_count"], "selected_chars": receipt["selected_chars"],
        "work_used": receipt["work_budget"]["used"], "work_limit": receipt["work_budget"]["limit"],
        "external_model_calls": receipt["external_model_calls"], "downloads": receipt["downloads"],
        "raw_copies": receipt["raw_copies"],
    },
    "focused_tests": {
        "exit_code": test_receipt["exit_code"], "elapsed_seconds": test_receipt["elapsed_seconds"],
        "pytest_temp_root_restored": test_receipt["owned_test_root_restored_to_absent"],
    },
    "sha256": {path: sha(ROOT / path) for path in paths},
}, ensure_ascii=False, indent=2))
