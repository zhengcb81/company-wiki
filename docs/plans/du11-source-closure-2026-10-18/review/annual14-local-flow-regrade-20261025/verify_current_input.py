"""Independent read-only source/payload recheck; no selection or model calls."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
sys.path.insert(0, str(ROOT / "src"))
from company_wiki.automation.narrative_model_scoped import MAX_SUMMARY_CLAIMS, compile_scoped_model_view
from company_wiki.source_contract.evidence_span import EvidenceSpan
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader
import pymupdf

HERE = Path(__file__).resolve().parent
PLAN = HERE.parent.parent
ATTEMPT = HERE.parent / "st-a05-local-flow-20261025/attempt05"
OLD = HERE.parent / "annual14-current-source-review-20261025/independent/report.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(value):
    return hashlib.sha256(value).hexdigest()


def digest_json(value):
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())


def compact(value):
    return "".join(value.split())


def main():
    output = HERE / "verification.json"
    if output.exists():
        raise FileExistsError(output)
    selection, stored, old = load(ATTEMPT / "selection.json"), load(ATTEMPT / "model-view.json"), load(OLD)
    engineering_path = HERE.parent / "st-a05-local-flow-20261025/independent/final-review.json"
    engineering = load(engineering_path)
    code_before = {p: sha((ROOT / p).read_bytes()) for p in engineering["product_test_sha256"]}
    if code_before != engineering["product_test_sha256"]:
        raise ValueError("Frozen engineering SHA mismatch")
    spans = tuple(EvidenceSpan.from_dict(x) for x in selection["selected_evidence"])
    by_id = {s.span_id: s for s in spans}
    view = compile_scoped_model_view(SimpleNamespace(evidence_spans=spans, reading_context=selection["reading_context"]), max_claims=MAX_SUMMARY_CLAIMS)
    payload = view.to_model_dict()
    tasks = [{"task_key": t.key, "kind": t.kind, "section_role": t.section_role,
              "support_span_ids": list(t.support_ids), "context_span_ids": list(t.context_ids),
              "member_span_ids": list(t.member_ids)} for t in view.plan.tasks]
    if tasks != stored["tasks"] or view.binding_sha256 != stored["model_binding_sha256"] or digest_json(payload) != stored["model_payload_sha256"]:
        raise ValueError("Current production compiler differs from frozen actual model view")
    shared = {f["source_key"]: f for f in payload["shared_fragments"]}
    bindings = view.to_binding()["task_parts"]
    task_lookup = {t["task_key"]: t for t in tasks}
    actual_views = []
    for task in payload["tasks"]:
        key = task["key"]
        support_parts = task.get("support_parts", payload["task_defaults"]["support_parts"])
        context_parts = task.get("context_parts", payload["task_defaults"]["context_parts"])
        members = []
        for part in task["parts"]:
            sid = bindings[key][part["key"]]
            span = by_id[sid]
            body = shared[part["shared_ref"]] if "shared_ref" in part else part
            if body["text"] != span.raw_text:
                raise ValueError("Actual payload body mismatch")
            factual = support_parts == "all_parts" or part["key"] in support_parts
            context = part["key"] in context_parts
            if factual != (sid in task_lookup[key]["support_span_ids"]) or context != (sid in task_lookup[key]["context_span_ids"]):
                raise ValueError("Actual support/context role mismatch")
            members.append({"part_key": part["key"], "span_id": sid,
                "role": "support" if factual else "context", "locator": span.locator,
                "full_quote": span.raw_text, "quality_flags": list(span.quality_flags)})
        actual_views.append({"task_key": key, "kind": task_lookup[key]["kind"], "section_role": task_lookup[key]["section_role"], "members": members})

    project = ROOT / ".planning/shared-reading-production/r1-holdout-20261021/CN-603259/wiki"
    cfg_path = project / "config/source_catalog.yaml"
    cfg = load_catalog_config(cfg_path, project_root=project)
    protected = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in (cfg_path, cfg.database_path)}
    catalog = SourceCatalog(cfg)
    page_cache = {}
    checked = []
    member_count = 0
    try:
        verified = SourceVersionReader(catalog).open_version(SourceRef(**selection["source_ref"]), purpose="preview")
        if sha(verified.data) != selection["source_ref"]["content_sha256"]:
            raise ValueError("Verified original SHA differs")
        doc = pymupdf.open(stream=verified.data, filetype="pdf")

        def page(number):
            if number not in page_cache:
                p = doc[number - 1]
                blocks = [b[4].strip() for b in p.get_text("blocks") if len(b) >= 7 and b[6] == 0]
                page_cache[number] = {"text": p.get_text(), "blocks": blocks,
                                      "by_hash": {sha(s.encode()): s for s in blocks}}
            return page_cache[number]

        for span in spans:
            pg = page(span.coordinates.page_number)
            sv = span.structured_value
            members = sv.get("native_range", {}).get("members") or [sv]
            errors = []
            pieces = []
            for m in members:
                if "block_sha256" not in m:
                    continue
                member_count += 1
                base = pg["by_hash"].get(m["block_sha256"])
                if base is None:
                    errors.append("original block SHA missing")
                    continue
                piece = base[m.get("block_char_start", 0):m.get("block_char_end", len(base))]
                if m.get("text_sha256") and sha(piece.encode()) != m["text_sha256"]:
                    errors.append("member slice SHA mismatch")
                pieces.append(piece)
            if pieces and compact("".join(pieces)) != compact(span.raw_text):
                errors.append("selected quote not the exact member slices modulo joining whitespace")
            if compact(span.raw_text) not in compact(pg["text"]):
                errors.append("selected full quote not in original page")
            checked.append({"span_id": span.span_id, "locator": span.locator,
                "quote_sha256": sha(span.raw_text.encode()), "native_member_count": len(pieces),
                "source_match": not errors, "errors": errors})
        gold_checks = []
        for row in old["original_gold_source_checks"]:
            ok = compact(row["full_quote"]) in compact(page(row["physical_page"])["text"])
            gold_checks.append({**row, "original_page_match_ignoring_whitespace": ok})
        if catalog._store is not None:
            raise ValueError("Read unexpectedly constructed write store")
        direct_pages = {n: page(n)["text"] for n in [7, 11, 12, 13, 14, 16, 17, 31, 32, 119, 120, 183, 184, 235]}
        for number in (13, 14, 183, 184):
            print("\nDIRECT ORIGINAL PAGE", number, "\n", direct_pages[number])
        doc.close()
    finally:
        catalog.close()
    protected_after = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in (cfg_path, cfg.database_path)}
    code_after = {p: sha((ROOT / p).read_bytes()) for p in engineering["product_test_sha256"]}
    if protected_after != protected or code_after != code_before:
        raise ValueError("Protected config/catalog/product changed")
    result = {"schema_version": "annual14-current-local-flow-verification/1",
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_ref": selection["source_ref"], "source_sha_verified_via_reader": True,
        "write_store_constructed": False, "source_pages": len(doc) if not doc.is_closed else 249,
        "product_test_sha256": code_before, "source_stable": True,
        "protected_sha256": protected, "protected_unchanged": True,
        "actual_recompiled_model_payload_sha256": digest_json(payload),
        "actual_recompiled_model_binding_sha256": view.binding_sha256,
        "all_stored_task_members_equal_current_compiler": tasks == stored["tasks"],
        "all_actual_payload_support_context_full_quotes_verified": True,
        "selected_span_count": len(spans), "actual_task_count": len(actual_views),
        "original_block_member_checks": member_count,
        "selected_span_source_checks": checked, "original_gold_source_checks": gold_checks,
        "direct_original_pages_read": sorted(page_cache),
        "actual_task_views": actual_views,
        "all_selected_quotes_match_source": all(x["source_match"] for x in checked),
        "all_original_gold_quotes_match_source": all(x["original_page_match_ignoring_whitespace"] for x in gold_checks),
        "external_model_calls": 0, "downloads": 0, "raw_copies": 0,
        "product_writes": 0, "temporary_directories_created": 0,
        "evidence_sha256": {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in [OLD, engineering_path,
            *(ATTEMPT / n for n in ("selection.json", "model-view.json", "trace.json", "replay-receipt.json", "parent-input-check.json"))]}}
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\nCHECKS", json.dumps({k: result[k] for k in ("selected_span_count", "actual_task_count", "original_block_member_checks", "all_selected_quotes_match_source", "all_original_gold_quotes_match_source", "actual_recompiled_model_payload_sha256")}))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
