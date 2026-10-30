"""M3b: terminal diagnostic metadata cannot replace full claims/source checks."""
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from unit.test_narrative_fidelity_artifacts import materials
from company_wiki.automation.narrative_summary_assessment import assess_summary, validate_assessment_wire
from company_wiki.automation.narrative_model_scoped import compile_scoped_model_view
from company_wiki.automation.narrative_summary_execution import extract_summary_execution, wrap_summary, parse_summary_job_result
from company_wiki.automation.narrative_verify import NarrativeVerifyHandler
from company_wiki.automation.narrative_contracts import NarrativeBundle


def rejects(call):
    try:
        call()
        return False
    except (ValueError, TypeError, KeyError):
        return True


def main():
    source, summary = materials()
    claims = summary.to_dict()["draft"]["claims"]
    view = compile_scoped_model_view(source, max_claims=40)
    report = assess_summary(source, claims, requested_task_keys=[task.key for task in view.model_tasks], plan_max_claims=40)
    terminal = {"schema_version": "narrative-terminal-receipt/1.0", "execution": report}
    result = {
        "terminal_keeps_valid_metadata": extract_summary_execution(terminal) == report,
        "full_wrapper_source_recheck": parse_summary_job_result(wrap_summary(summary, report), selected=source) == summary,
    }
    for name in ["semantic_upgrade", "bad_algebra", "unknown_field", "bad_digest_shape"]:
        bad = deepcopy(report)
        if name == "semantic_upgrade":
            bad["semantic_status"] = "verified"
        elif name == "bad_algebra":
            bad["requested_emission_complete"] = not bad["requested_emission_complete"]
        elif name == "unknown_field":
            bad["unexpected"] = "x"
        else:
            bad["claims_sha256"] = "not-a-hash"
        result[name + "_terminal_rejected"] = rejects(lambda: extract_summary_execution(
            {"schema_version": "narrative-terminal-receipt/1.0", "execution": bad}))
    for name in ["claims_hash_unbound", "foreign_risk_claim"]:
        bad = deepcopy(report)
        if name == "claims_hash_unbound":
            bad["claims_sha256"] = "f" * 64
        else:
            bad.update(diagnostic_claim_ids=["unknown-claim"], diagnostic_count=1, diagnostics=[],
                       diagnostics_limited=True, known_constraint_status="diagnostics_found")
        result[name + "_metadata_only_accepts"] = not rejects(lambda: validate_assessment_wire(bad, None))
        result[name + "_full_claim_validation_rejects"] = rejects(lambda: validate_assessment_wire(bad, claims))
        wire = NarrativeVerifyHandler._bundle(source, summary, source.prompt_review).to_dict()
        wire["summary_assessment"] = bad
        result[name + "_full_bundle_rejects"] = rejects(lambda: NarrativeBundle.from_dict(wire))
    result["metadata_is_not_source_or_claim_validation"] = True
    assert all(result.values())
    (Path(__file__).parent / "metadata-boundary-probe.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
