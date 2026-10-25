"""Assemble manual independent checkpoint decisions; never rerun sources."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "pyproject.toml").exists())


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# Source propositions are the old immutable development gold. The judgement
# deliberately checks the proposition, not merely its permissive OR atom hit.
US = {
 "f-azure-is-consumption-based": ("PASS", ["t20"], "Azure/IaaS/PaaS consumption-based mechanism is in one complete support paragraph; no seat-based mechanism is substituted."),
 "f-azure-inside-intelligent-cloud": ("PARTIAL", ["t19", "t20", "t7"], "The old OR accepts the Intelligent Cloud introduction alone. Actual t19 ends 'This segment primarily comprises:' without the list child; t20's Azure mechanism and t7's Server/Azure growth have no Intelligent Cloud owner in their own task context. The full nested scope is not one closed local source basis."),
 "f-three-segments": ("PASS", ["t8"], "Three named reporting segments and count appear together; Microsoft Cloud is not introduced as a fourth segment."),
 "f-segment-change-in-august-2024": ("PASS", ["t9", "t12", "t46"], "August 2024 composition change, Microsoft365 Commercial movement, FY2025 basis and prior-period recast are directly visible."),
 "f-m365-consumer-vs-commercial-metric": ("PASS", ["t5", "t6"], "Each complete business paragraph names its own product family: Commercial products14%, cloud15%, seats6%; Consumer products/cloud11%, subscribers8% to89.0million. Separate subjects and metrics preserved."),
 "f-azure-growth-inside-combined-line": ("PASS", ["t7"], "Same support binds Server products/services +23% to the upper line and Azure and other services +34% to the combined child line, not standalone Azure."),
 "f-rpo-scope-and-amount": ("PASS", ["t50"], "One complete support includes RPO definition, total375billion, commercial368billion, June30 2025 and forward invoicing; not unearned revenue."),
 "f-rpo-recognition-is-forward": ("PASS", ["t50"], "Same RPO support explicitly expects approximately40% over next12months; not current-period realized revenue."),
}
HK = {
 "gross-margin-decline": ("PARTIAL", "PASS", ["t37"], "Gross profit +7.4%, margin15.2% vs16.7%, AI server costs and client upfront costs are complete in one support. This bare compiler material has no verified shared document-period field or applicable period context. A source-owner-verified shared period in a full request would suffice once; repeating p5 per task is not required. An unrelated cash-flow header is not a document-level qualifier."),
 "no-material-investments-or-capex-plans": ("PASS", "PASS", ["t40"], "As-of June30 2025, >=5% material investment definition and both no-current-investment/no-future-material-capital-plan negations are in one support."),
 "h2-2025-business-outlook": ("MISSING", "MISSING", [], "Source has the exact H2 AI and Xiaomi/Kingsoft ecosystem plan, but no selected support contains the plan. Selected p11 R&D platform description does not substitute a H2 plan."),
 "single-operating-segment": ("PARTIAL", "PARTIAL", ["t59"], "Single operating segment and CODM basis are present. The complementary mainland revenue/assets and no geographic segment statement is absent; public/industry service categories must not become reportable segments."),
 "cloud-revenue-operating-drivers": ("PARTIAL", "PASS", ["t28"], "AI customer/industry-project expansion and deliberate CDN contraction offset are complete in support. This bare compiler material supplies no verified shared H1 period nor applicable local period. A verified document-level period in the full request may supply it once; full request was not built in this run, so no blanket production failure is claimed."),
 "cloud-service-growth-causal-split": ("PARTIAL", "PARTIAL", ["t1", "t35"], "Public cloud +23% and AI cause are complete. Industry-cloud support p13/9 stops after prior-period1,245.4, lacking its unit/7.6%/IT-demand and vertical-solution continuation. Its quality_flags are empty; both frozen causal branches are not locally available."),
 "idc-purchase-commitment-stage": ("MISSING", "MISSING", [], "Neither the June1 noncancellable1year IDC agreement, 630000 minimum nor576101 remaining commitment/unit context is selected. No source-input basis for this business contract stage exists."),
}


def target_rows(case, decisions, hk=False):
    data = load(HERE / (case + ".json"))
    gold = load(ROOT / data["gold_path"])
    tasks = {t["key"]: t for t in data["tasks"]}
    quotes = {q["span_id"]: q for q in data["selected_quotes"]}
    visible = set(data["actual_payload_available_task_keys"])
    rows = []
    for f in gold["facts"]:
        if f.get("target_kind") != "required_business":
            continue
        decision = decisions[f["id"]]
        status, core, keys, reason = decision if hk else (decision[0], decision[0], decision[1], decision[2])
        evidence = {}
        for key in keys:
            if key not in visible:
                raise ValueError("Judgement references a task not actually visible")
            for sid in tasks[key]["members"]:
                if sid not in evidence:
                    evidence[sid] = dict(quotes[sid])
                    evidence[sid]["actual_roles"] = []
                evidence[sid]["actual_roles"].append({"task": key, "role": "support" if sid in tasks[key]["support"] else "context"})
        observed = next(x for x in data["gold_source_observations"] if x["fact_id"] == f["id"])
        literal_or_present = any(all(a["exact_selected_candidate_span_ids"] for a in st) for st in observed["any_support_sets"])
        rows.append({"fact_id": f["id"], "frozen_gold": f, "source_input_status": status,
            "operating_core_body_status": core, "reason": reason, "actual_task_keys": keys,
            "evidence": list(evidence.values()), "all_required_source_atoms_found_in_parsed_original": any(all(a["in_parsed_source"] for a in st) for st in observed["any_support_sets"]),
            "legacy_exact_quote_OR_selected": literal_or_present,
            "model_response_semantics": "NOT_REVIEWED", "RF_consumption": "OPEN"})
    return rows


def main():
    output = HERE / "final-report.json"
    if output.exists():
        raise FileExistsError(output)
    run = load(HERE / "run-manifest.json")
    start = load(HERE / "start-bindings.json")
    us = target_rows("us-10k", US)
    hk = target_rows("du5-hk-kingsoft-interim", HK, hk=True)
    assert len(us) == 8 and len(hk) == 7
    summaries = []
    for ident in ("us-10k", "du5-hk-kingsoft-interim", "cn-ipo"):
        data = load(HERE / (ident + ".json"))
        selection = dict(data.get("selection", {}))
        selection["diagnostics"] = [{k: v for k, v in d.items() if k not in ("targets",)} for d in selection.get("diagnostics", [])]
        summaries.append({"case_id": ident, "source_ref": data["source_ref"], "status": data["status"],
            "selection": selection, "parse_work": data.get("parse_work"), "work_budget": data["work_budget"],
            "parse_entry": data["parse_entry"], "PDF_shared_account": data["parse_select_share_same_WorkBudget"],
            "compiler_status": data["compiler_status"], "actual_task_count": data.get("actual_task_count"),
            "actual_model_payload_sha256": data.get("actual_model_payload_sha256"),
            "actual_model_binding_sha256": data.get("actual_model_binding_sha256"),
            "policy_families": sorted({p["family"] for p in data.get("reading_policy", [])}),
            "route_note": "The harness queried a non-existent reading_context.route key; null is telemetry not captured, not proof of missing product routing. Policy family is directly observed; declared_kind is explicit input metadata.",
            "elapsed_seconds": data["elapsed_seconds"], "content_status": "NOT_GRADED_NO_FORMAL_GOLD_BUDGET_STOP" if ident == "cn-ipo" else "GRADED_REQUIRED_SOURCE_INPUT_ONLY"})
    market = HERE.parent / "market-family-upgrade-20261024"
    existing = [market / "m1-source-checkpoints/source-bindings.json",
        market / "m3-implementation-20261024/m3-independent-final/checks.json",
        market / "m3-implementation-20261024/m3-independent-final/r5/report.md"]
    evidence_files = [*(HERE / n for n in ("run_precheck.py", "start-bindings.json", "run-manifest.json", "us-10k.json", "du5-hk-kingsoft-interim.json", "cn-ipo.json", "startup-attempt1-bindings.json", "startup-attempt1-error.json")), *existing]
    report = {"schema_version": "independent-local-flow-cross-market-final/1", "created_at": datetime.now(timezone.utc).isoformat(),
        "verdict": "SOURCE_INPUT_GAPS_FOUND; IPO_WORK_EXHAUSTED_STOP; MODEL_NOT_REVIEWED; RF_OPEN",
        "binding": {"head_before": run["head_before"], "head_after": run["head_after"],
            "tracked_WIP_at_run": start["tracked_wip"], "source_tree_sha256": run["source_tree_sha256"],
            "source_file_count": len(start["source_sha256"]), "source_owner17": start["source_owner17"],
            "protected_config_DB_budget_sha256": start["protected_sha256"],
            "frozen_gold_sha256": start["gold_sha256"],
            "evidence_sha256": {str(p.relative_to(ROOT)): sha(p) for p in evidence_files}},
        "run_controls": {k: run[k] for k in ("source_stable", "source_owner17_unchanged", "protected_unchanged", "write_store_constructed", "calls", "temporary_directories_created")},
        "summary": summaries,
        "required_source_input_counts": {"us-10k": dict(Counter(x["source_input_status"] for x in us)),
            "du5-hk-kingsoft-interim": dict(Counter(x["source_input_status"] for x in hk)),
            "cn-ipo": "NOT_GRADED; no formal source gold, no actual model input after budget exhaustion"},
        "HK_body_only_counts_not_complete_gold_acceptance": dict(Counter(x["operating_core_body_status"] for x in hk)),
        "required_targets": {"us-10k": us, "du5-hk-kingsoft-interim": hk},
        "nonrequired_financial_meta_targets": {"status": "SOURCE_ATOMS_OBSERVED_BUT_NOT_REQUIRED_NARRATIVE_RECALL_OR_MODEL_CORRECTNESS_SIGNOFF", "must_not_assert_checks": "Preserved in original gold; no model output exists here to test semantic violations."},
        "findings": [
            {"id": "CM-01", "severity": "P2", "owner": "CWP source hierarchy/context closure and actual scoped task admission", "case": "us-10k",
             "fact": "f-azure-inside-intelligent-cloud", "actual_tasks": ["t19", "t20", "t7"],
             "reproduction": "t19 ends primarily comprises: without the child list; Azure and Server facts have no IC owner in their own context. Old gold OR permits weak IC introduction alone.",
             "action": "Trace DOM list/heading relation and retain required scope in child tasks; regression must use neutral parent/child and sibling negatives, not Azure name rules. Do not alter gold to make current selection pass."},
            {"id": "CM-02", "severity": "P2", "owner": "CWP native PDF sentence continuation/qualification closure and support admission", "case": "du5-hk-kingsoft-interim",
             "reproduction": "Actual t1 support p13/9 ends at prior-year1,245.4, lacks the next line/unit/growth/causal branch, quality_flags=[]; t59 lacks complementary geographic non-segmentation clause.",
             "action": "Follow original unit continuation dependencies and reject/defer incomplete factual support or retain the full qualified sentence. Preserve business sibling scope and table units; use neutral PDF line-split tests."},
            {"id": "CM-03", "severity": "P2", "owner": "CWP document period qualification and strategy/selection allocation", "case": "du5-hk-kingsoft-interim",
             "reproduction": "Business t37/t28/t35 lack the frozen six-month anchor; H2 AI/eco-system plan and IDC purchase-stage fact absent although source atoms exist and work budget is not exhausted.",
             "action": "Distinguish source inventory, admitted candidate, budget choice and actual task qualification; provide one source-owner-verified shared document period or applicable local context, without requiring a duplicate p5 fragment per task. Inspect the actual full request before concluding production period is missing. Investigate generic outlook and contract-stage allocation without issuer names or cap increase."},
            {"id": "CM-04", "severity": "OPEN_EFFICIENCY_CAPACITY", "owner": "Shared work planner/inventory processing; exact exhausted phase not localized by this precheck", "case": "cn-ipo",
             "reproduction": "429pages/14025 parsed units, parse420052 then composed work15,999,740/16M; candidate_count8361,0 selected, honest needs_review. Old m3 separate parse/select account and160-span replay is not comparable.",
             "action": "Retain hard ceiling and stop; investigate bounded/resumable candidate planning and unnecessary repeated work in a separate owner node. No budget increase, retry, content grade or model compiler after exhaustion in this run."}
        ],
        "neutral_controls": run["neutral_controls"],
        "document_period_boundary": {"reviewed_surface": "Bare compile_scoped_model_view.to_model_dict material only",
            "shared_head_fields": ["schema_version", "scope", "max_claims", "available_task_count", "fragment_defaults", "task_defaults", "shared_fragments", "tasks"],
            "verified_shared_document_period_observed": False,
            "formal_full_NarrativeModelRequest": "NOT_BUILT_IN_THIS_RUN",
            "static_full_request_observation": "Current build_scoped_request adds source.language/title/document_kind and reading_strategy; explicit period/fiscal_period is not in the small source header. A verified title or another verified shared field may supply a document period; this bare-material run cannot exclude such full-request context.",
            "acceptance_rule": "A source-owner-verified shared document period can qualify all applicable tasks once. Do not duplicate p5 into every task. A different task's cash-flow header is not equivalent to a verified shared document period.",
            "HK_count_boundary": "1PASS/4PARTIAL/2MISSING is bare-material coverage of the frozen joint propositions, not a claim that every production full request lacks period metadata."},
        "source_gold_observations": [
            "Original required gold source quotes are found in the SHA-verified original's parser units; this is recorded separately from actual selected task coverage.",
            "US hierarchy OR supports are weaker than its full reason/proposition. Both the literal result and stricter source-input semantic judgement are retained, with no gold rewrite.",
            "US HTML legacy page1 is virtual document location, never a physical PDF page.",
            "US RPO gold reason mentions7,265 million as an unearned-revenue distractor, while its separate correct balance target says67,265 million; preserve this stale explanation inconsistency, do not repair the original gold here or invent a model error.",
            "HK IDC source body uses yuan while section header is thousand-yuan presentation; full unit qualification remains necessary, and the current fact is not selected.",
            "cn-ipo is AMEC, not SMIC or the scanned Dinglong administrative confirmation. It has no formal content gold; existing M3 checks are historical source/binding checks only."],
        "limits": [
            "Single actual production attempt per source after a harness-only pre-parse serialization startup error. That startup error performed no parse/select and is preserved separately.",
            "PDF parse and select charge the same configured16M account; max_selected112. No old helper with separate phase accounts was executed.",
            "HTML uses existing finite NormalizationLimits but its frontend has no WorkBudget argument; parse_work0 does not mean zero parsing effort. Its observed work total covers the shared selector account, not an invented HTML parse charge.",
            "Actual v4 model inputs were compiled once for US/HK and hashed. Model responses, formal summary recovery and RF adoption are not reviewed.",
            "Gold source quote observations use the parser units from verified bytes; this is not visual layout inspection or exhaustive independent re-rendering of every selected span.",
            "No product, old gold, PWF, production configuration, database, original document or external author-worktree writes. No temp directories were created.",
            "Findings require owner root-cause investigation; this independent precheck did not modify code or create source-specific passing exceptions."],
        "model_response_semantics": "NOT_REVIEWED", "current_RF_consumption": "OPEN"}
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"counts": report["required_source_input_counts"], "report_sha256": sha(output), "bytes": output.stat().st_size}))


if __name__ == "__main__":
    main()
