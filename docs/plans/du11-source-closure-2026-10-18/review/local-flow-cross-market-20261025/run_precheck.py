"""Bounded independent source/input precheck; no calls, downloads, Store or raw copies."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "pyproject.toml").exists())
sys.path.insert(0, str(ROOT / "src"))
from company_wiki.automation.narrative_model_scoped import MAX_SUMMARY_CLAIMS, SCOPED_MODEL_PROJECTION_VERSION, compile_scoped_model_view
from company_wiki.document_normalization import normalize_document
from company_wiki.document_understanding.geometry_intent.reading import PdfReadingContext
from company_wiki.resource_budget import WorkBudgetExceeded, budget_policy_path, new_document_work_budget
from company_wiki.source_catalog import narrative_evidence as engine
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.narrative_business_policy import assess_reading_business_fact
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader

MARKET = HERE.parent / "market-family-upgrade-20261024"
CASES = [
    ("us-10k", "99d693f6c1544144ebeee92954f151a85bc62111837530a42855953bc01d0bbe", 8158067, "text/html", "Microsoft 10-K FY2025", "annual_report", "en", ROOT / "tools/document_understanding_benchmark/gold/us-10k.du11-v2-20261024.json"),
    ("du5-hk-kingsoft-interim", "4f589193fae39fb53cb7d2121d93925b382bb052cfecbdc24e8e8271ea41bd36", 3396644, "application/pdf", "2025 中期報告", "semi_annual_report", "zh-hant", MARKET / "m1-source-checkpoints/gold/du5-hk-kingsoft-interim.json"),
    ("cn-ipo", "19cdb41e03b2d86ac15007753784f5859e1450a2bf79b514a7c0d4bd6830be67", 11211796, "application/pdf", "中微公司：首次公开发行股票并在科创板上市招股说明书", "prospectus", "zh", None),
]


def plain(value):
    if isinstance(value, Mapping):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(x) for x in value]
    return value


def digest(value):
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return digest(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def compact(value):
    return "".join(value.split())


def snapshot():
    paths = sorted((ROOT / "src/company_wiki").rglob("*.py"))
    paths.append(ROOT / "src/company_wiki/document_understanding/profiles/reading_catalog.json")
    return {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in paths}


def write(path, value):
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    if (HERE / "run-manifest.json").exists():
        raise FileExistsError("This is a single-attempt bounded precheck")
    cfg_path = ROOT / "config/source_catalog.yaml"
    cfg = load_catalog_config(cfg_path, project_root=ROOT)
    protected = [cfg_path, cfg.database_path, budget_policy_path()]
    protected_before = {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in protected}
    sources_before = snapshot()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    tracked_wip = subprocess.check_output(["git", "status", "--porcelain", "-uno"], cwd=ROOT, text=True)
    frozen = load(HERE.parent / "annual14-local-flow-regrade-20261025/verification.json")["product_test_sha256"]
    frozen_checks = {p: {"frozen_sha256": expected, "actual_sha256": digest((ROOT / p).read_bytes())} for p, expected in frozen.items()}
    if any(x["frozen_sha256"] != x["actual_sha256"] for x in frozen_checks.values()):
        raise ValueError("Successful-source owner17 changed; do not switch baseline silently")
    write(HERE / "start-bindings.json", {"head": head, "tracked_wip": tracked_wip,
        "source_sha256": sources_before, "source_owner17": frozen_checks, "protected_sha256": protected_before,
        "gold_sha256": {str(c[7].relative_to(ROOT)): digest(c[7].read_bytes()) for c in CASES if c[7]},
        "runner_sha256": digest(Path(__file__).read_bytes())})
    catalog = SourceCatalog(cfg)
    rows = []
    try:
        for case_id, sha, size, mime, title, kind, language, gold_path in CASES:
            output = HERE / (case_id + ".json")
            if output.exists():
                raise FileExistsError(output)
            started = time.monotonic()
            ref = SourceRef(document_id="urn:company-wiki:document:sha256:" + sha,
                source_id="urn:company-wiki:source:sha256:" + sha, content_sha256=sha, byte_size=size, mime_type=mime)
            verified = SourceVersionReader(catalog).open_version(ref, purpose="preview")
            if digest(verified.data) != sha or catalog._store is not None:
                raise ValueError("Immutable source verification or Store boundary failed")
            budget = new_document_work_budget()
            if budget.max_work_units != 16_000_000:
                raise ValueError("Configured work limit changed")
            row = {"case_id": case_id, "source_ref": asdict(ref), "source_sha_verified": True,
                "title": title, "declared_kind": kind, "language": language,
                "gold_path": str(gold_path.relative_to(ROOT)) if gold_path else None,
                "gold_sha256": digest(gold_path.read_bytes()) if gold_path else None,
                "gold_status": "FROZEN_DEVELOPMENT_GOLD" if gold_path else "NO_FORMAL_GOLD_CONTENT_NOT_GRADED",
                "selector": "0.9.0", "requested_max_selected": 112, "summary_projection": SCOPED_MODEL_PROJECTION_VERSION,
                "parse_select_share_same_WorkBudget": mime == "application/pdf", "model_calls": 0, "downloads": 0, "raw_copies": 0}
            parsed = package = None
            try:
                if mime == "application/pdf":
                    parsed = engine.parse_pdf_bytes(verified.data, source_id=ref.source_id, source_sha256=sha,
                        language=language, selector_version="0.9.0", reading_context=PdfReadingContext(title, kind, language), work_budget=budget)
                    row["parse_entry"] = "parse_pdf_bytes(selector=0.9.0, same WorkBudget)"
                else:
                    normalized = normalize_document(verified.data, source_id=ref.source_id, source_sha256=sha, mime_type=mime)
                    parsed = normalized.structure
                    row["parse_entry"] = "normalize_document(text/html), existing finite NormalizationLimits; HTML parser has no WorkBudget parameter"
                row["parse_work"] = budget.used
                row["parsed_unit_count"] = len(parsed.units)
                row["parsed_page_count"] = getattr(parsed, "page_count", None)
                if budget.exhausted:
                    raise WorkBudgetExceeded("Stopped after exhausted parse", used=budget.used, limit=budget.max_work_units)
                package = engine.select_narrative_evidence(parsed, title=title, existing_kind=kind,
                    max_selected=112, selector_version="0.9.0", work_budget=budget)
                row["selection"] = {k: plain(getattr(package, k)) for k in ("status", "coverage_complete", "selection_limit", "candidate_count", "omitted_candidate_count", "dropped_financial_count")}
                row["selection"]["diagnostics"] = plain(package.selection_diagnostics)
                spans = tuple(package.evidence_spans)
                row["selection"].update({"selected_count": len(spans), "selected_chars": sum(len(s.raw_text) for s in spans)})
                if len(spans) > 112 or package.selection_limit > 112:
                    raise ValueError("112 span cap expanded")
                row["reading_route"] = plain(package.reading_context.get("route"))
                row["reading_policy"] = plain(package.reading_context.get("reading_policies"))
                row["selected_quotes"] = [{"span_id": s.span_id, "locator": s.locator, "full_quote": s.raw_text,
                    "page": s.coordinates.page_number, "quote_sha256": digest(s.raw_text.encode()), "quality_flags": list(s.quality_flags),
                    "source_role": s.structured_value.get("source_role"), "selection_reasons": plain(s.structured_value.get("selection_reasons", [])),
                    "topics": plain(s.structured_value.get("topics", []))} for s in spans]
                if not budget.exhausted:
                    view = compile_scoped_model_view(SimpleNamespace(evidence_spans=spans, reading_context=plain(package.reading_context)), max_claims=MAX_SUMMARY_CLAIMS)
                    payload = view.to_model_dict()
                    row["actual_model_payload_sha256"] = canonical(payload)
                    row["actual_model_binding_sha256"] = view.binding_sha256
                    row["actual_task_count"] = len(payload["tasks"])
                    row["tasks"] = [{"key": t.key, "kind": t.kind, "section_role": t.section_role,
                        "support": list(t.support_ids), "context": list(t.context_ids), "members": list(t.member_ids)} for t in view.plan.tasks]
                    row["actual_payload_available_task_keys"] = [t["key"] for t in payload["tasks"]]
                    row["compiler_status"] = "COMPILED_ACTUAL_V4_INPUT_NOT_SENT"
                else:
                    row["compiler_status"] = "NOT_COMPILED_BUDGET_EXHAUSTED_STOP"
                row["status"] = "WORK_EXHAUSTED_STOP" if budget.exhausted else "COMPLETE_BOUNDED_SOURCE_INPUT_PRECHECK"
            except WorkBudgetExceeded as exc:
                row["status"] = "WORK_EXHAUSTED_STOP"
                row["budget_exception"] = {k: getattr(exc, k, None) for k in ("phase", "used", "requested", "limit")}
                row["compiler_status"] = "NOT_COMPILED_BUDGET_EXHAUSTED_STOP"
            if parsed is not None and gold_path:
                # These are source-side observations, not semantic PASS labels.
                gold = load(gold_path)
                source_by_page = {}
                for u in parsed.units:
                    pg = u.coordinates.page_number
                    source_by_page.setdefault(pg, []).append(u.raw_text)
                whole = compact("\n".join(u.raw_text for u in parsed.units))
                row["gold_source_observations"] = []
                for fact in gold["facts"]:
                    sets = []
                    for group in fact.get("any_support_sets", []):
                        checks = []
                        for atom in group:
                            source = whole if atom.get("location_kind") == "document" else compact("\n".join(source_by_page.get(atom.get("page"), [])))
                            quote = compact(atom["exact_quote"])
                            candidate = []
                            for s in row.get("selected_quotes", []):
                                if quote in compact(s["full_quote"]):
                                    candidate.append(s["span_id"])
                            checks.append({"atom": atom, "in_parsed_source": quote in source,
                                "exact_selected_candidate_span_ids": candidate})
                        sets.append(checks)
                    row["gold_source_observations"].append({"fact_id": fact["id"], "target_kind": fact.get("target_kind"),
                        "any_support_sets": sets, "semantic_status": "PENDING_INDEPENDENT_MANUAL_REVIEW"})
            row["work_budget"] = {"used": budget.used, "limit": budget.max_work_units, "exhausted": budget.exhausted}
            row["elapsed_seconds"] = round(time.monotonic() - started, 3)
            row["source_stable"] = sources_before == snapshot()
            row["protected_unchanged"] = protected_before == {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in protected}
            if not row["source_stable"] or not row["protected_unchanged"] or catalog._store is not None:
                raise ValueError("Source/config/DB drift during probe")
            write(output, row)
            rows.append({k: row.get(k) for k in ("case_id", "status", "selection", "actual_task_count", "compiler_status", "work_budget", "elapsed_seconds")})
            print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
    finally:
        catalog.close()
    controls = []
    for text, eligible, actual_growth in [
        ("The auditor tested revenue: includes manual inspection of contract samples.", False, False),
        ("Training for revenue: includes instructions for reviewing deferred revenue.", False, False),
        ("Our service revenue: includes cloud subscriptions and support services.", True, False),
        ("Paid seats: number of licensed users and our paid seats increased 20% to 240 in 2026.", True, True),
        ("Paid seats: number of licensed users at the end of the period.", True, False),
    ]:
        fact, financial = assess_reading_business_fact(text, {})
        reasons = list(fact.reasons)
        observed_growth = "operating_metric_change" in reasons
        controls.append({"text": text, "eligible": fact.eligible, "reasons": reasons,
            "purpose": fact.purpose, "financial_only": financial, "expected_eligible": eligible,
            "expected_actual_growth": actual_growth, "passed": fact.eligible == eligible and observed_growth == actual_growth})
    manifest = {"schema_version": "independent-local-flow-cross-market-run/1", "created_at": datetime.now(timezone.utc).isoformat(),
        "head_before": head, "head_after": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_stable": sources_before == snapshot(), "source_tree_sha256": canonical(sources_before),
        "source_owner17_unchanged": all(x["frozen_sha256"] == x["actual_sha256"] for x in frozen_checks.values()),
        "protected_unchanged": protected_before == {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in protected},
        "write_store_constructed": False, "case_summaries": rows, "neutral_controls": controls,
        "calls": {"model": 0, "api": 0, "download": 0, "raw_copy": 0}, "temporary_directories_created": 0,
        "model_response_semantics": "NOT_REVIEWED", "current_rf_consumption": "OPEN"}
    write(HERE / "run-manifest.json", manifest)
    print(json.dumps({"manifest": str(HERE / "run-manifest.json"), "all_controls_pass": all(x["passed"] for x in controls)}, ensure_ascii=False))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
