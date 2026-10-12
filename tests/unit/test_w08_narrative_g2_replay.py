"""W08-CWP-G2-REPLAY oracle and contract tests (behavior RED first).

These tests fix the *tool's* obligations, not the product's.  They are the
independent oracle the card demands: a run record must be rejected when it

- reports an empty case set,
- drops one of the required groups,
- self-reports PASS without the raw receipt/evidence,
- carries a bad raw SHA or an unreplayable locator,
- shows a new model POST on the second run,
- leaves scratch behind (failed recovery),
- rewrites the fixed expectations.

The heavy product E2E lives in ``tools/narrative_g2_replay/run.py`` and is
executed manually as the card's node C.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from tools.narrative_g2_replay import oracle, specs
from tools.narrative_g2_replay.oracle import (
    STATUS_FAIL,
    STATUS_INVALID,
    STATUS_PARTIAL,
    STATUS_PASS,
)


def _sha(char: str = "a") -> str:
    return char * 64


def _case(case_id: str, **overrides):
    """A case block that is *honestly* consistent with its fixed expectation.

    The default must be a genuinely passing case: a skip case carries no
    summary, a narrative case carries one, and a transcript keeps its TXT
    identity.  Tests then inject exactly one defect each.
    """
    spec = specs.spec_by_id(case_id)
    expectation = specs.FIXED_EXPECTATIONS[case_id]
    is_skip = expectation.get("expectation") == specs.EXPECT_SKIP
    is_transcript = bool(expectation.get("transcript_must_stay_txt"))
    actual = {
        "document_kind": expectation["document_kind_preserved"],
        "language": expectation["language"],
        "summary_status": "skipped_no_narrative" if is_skip else "published",
        "mime_type": spec.mime_type,
    }
    if is_transcript:
        actual["converted_to_pdf"] = False
        actual["source_sha256_changed"] = False
    case = {
        "case_id": case_id,
        "group_id": spec.group_id,
        "expected": copy.deepcopy(expectation),
        "status": STATUS_PASS,
        "actual": actual,
        "request": {"path_ref": f"requests/{case_id}.json", "sha256": _sha("b")},
        "result": {"receipt_ref": f"results/{case_id}.json", "exit_code": 0},
        "artifacts": ([] if is_skip else [
            {
                "kind": "narrative_bundle",
                "sha256": _sha("c"),
                "byte_size": 512,
                "locators": ["p1#b0", "p1#b1"],
                "locator_replay_verified": True,
            }
        ]),
        "model": {"posts": 0 if is_skip else 1},
        "evidence": {"raw_receipt_present": True, "raw_sha256": _sha("d")},
        "failure": None,
        "cleanup": {"restored": True, "remaining": []},
    }
    case.update(overrides)
    return case


def _record(**overrides):
    cases = [_case(case_id) for case_id in specs.required_case_ids()]
    run1_posts = sum(c["model"]["posts"] for c in cases)
    record = {
        "schema_version": oracle.SCHEMA_VERSION,
        "scope": {
            "lane_id": "W08-CWP-G2-REPLAY",
            "supplier_fixture": True,
            "llm_semantic_quality": "not_evaluated",
            "source_truth_verified": "local synthetic originals only",
            "paid_calls": 0,
        },
        "code_binding": {
            "base_head": "122bbe3ba142979a2e478f886eb25de76edf2e00",
            "branch": "codex/w08-cwp-g2-replay",
            "modules": [
                {"path": "src/company_wiki/automation/narrative_batch_cli.py",
                 "sha256": _sha("e"), "source": "worktree"},
            ],
            "rf_snapshot_modules": [
                {"path": "scripts/company_wiki_narrative_reader.py",
                 "sha256": _sha("f"), "source": "input_snapshot"},
            ],
        },
        "case_specs": [spec.to_dict() for spec in specs.case_specs()],
        "coverage": specs.coverage_report(specs.required_case_ids()),
        "run_plan": {
            "deadline_seconds": 180.0,
            "per_command_seconds": 30.0,
            "second_run_reuse": True,
            "rf_consumption": True,
        },
        "runs": [
            {"run_index": 1, "model_posts": run1_posts, "status": "completed"},
            {"run_index": 2, "model_posts": 0, "status": "completed"},
        ],
        "model_accounting": {
            "run1_posts": run1_posts,
            "run2_posts": 0,
            "total_posts": run1_posts,
            "provider_calls": 0,
            "llm_calls": run1_posts,
            "paid_usd": 0.0,
        },
        "rf_consumption": {
            "consumer": "scripts/company_wiki_narrative_reader.py",
            "read_ok": True,
            "period_preserved": True,
            "language_preserved": True,
            "gaps_reported": [],
        },
        "cases": cases,
        "bytes": {"raw_bytes": 4096, "derived_bytes": 8192},
        "cleanup": {
            "baseline": {"exists": True, "sentinels": [{"path_ref": "keep.txt"}]},
            "after": {"exists": True, "sentinels": [{"path_ref": "keep.txt"}]},
            "deleted_within_owned": True,
            "restored": True,
            "remaining": [],
        },
        "known_baseline_failures": [
            {"case_id": "w04-baseline-1", "test_id": "tests/integration/..."
             "test_cli_infers_sparse_languages_from_verified_pdf_and_transcript_bytes",
             "status": "FAIL", "root_cause": "recorded, not fixed here"},
        ],
    }
    record.update(overrides)
    return record


# --------------------------------------------------------------------------
# structural contract
# --------------------------------------------------------------------------


def test_a_well_formed_record_passes_the_oracle():
    verdict = oracle.evaluate_run(_record())
    assert verdict.overall == STATUS_PASS, verdict.findings
    assert all(s == STATUS_PASS for s in verdict.statuses.values())


def test_schema_version_must_be_narrative_g2_replay_1():
    assert oracle.SCHEMA_VERSION == "narrative-g2-replay/1"
    verdict = oracle.evaluate_run(_record(schema_version="something/else"))
    assert verdict.overall == STATUS_INVALID


def test_oracle_never_raises_on_malformed_input():
    for bad in (None, [], "text", {}, {"schema_version": oracle.SCHEMA_VERSION}):
        verdict = oracle.evaluate_run(bad)
        assert verdict.overall == STATUS_INVALID


# --------------------------------------------------------------------------
# card section 8: the oracle must refuse these false-PASS shapes
# --------------------------------------------------------------------------


def test_empty_case_set_is_refused():
    record = _record(cases=[], coverage=specs.coverage_report(()))
    verdict = oracle.evaluate_run(record)
    assert verdict.overall in {STATUS_FAIL, STATUS_INVALID}
    assert any("empty" in f.code or "missing" in f.code for f in verdict.findings)


def test_deleting_a_required_group_is_refused():
    kept = [c for c in _record()["cases"] if c["group_id"] != "offering-documents"]
    executed = tuple(c["case_id"] for c in kept)
    record = _record(cases=kept, coverage=specs.coverage_report(executed))
    verdict = oracle.evaluate_run(record)
    assert verdict.overall == STATUS_FAIL
    assert any("missing" in f.code or "group" in f.code for f in verdict.findings)


def test_self_reported_pass_without_raw_receipt_is_refused():
    cases = [_case(cid) for cid in specs.required_case_ids()]
    cases[0]["evidence"]["raw_receipt_present"] = False
    verdict = oracle.evaluate_run(_record(cases=cases))
    assert verdict.overall == STATUS_FAIL
    assert any("receipt" in f.code for f in verdict.findings)


def test_bad_raw_sha_is_refused():
    cases = [_case(cid) for cid in specs.required_case_ids()]
    cases[0]["evidence"]["raw_sha256"] = "not-a-sha"
    verdict = oracle.evaluate_run(_record(cases=cases))
    assert verdict.overall == STATUS_FAIL
    assert any("sha" in f.code for f in verdict.findings)


def test_unreplayable_locator_is_refused():
    cases = [_case(cid) for cid in specs.required_case_ids()]
    cases[0]["artifacts"][0]["locator_replay_verified"] = False
    verdict = oracle.evaluate_run(_record(cases=cases))
    assert verdict.overall == STATUS_FAIL
    assert any("locator" in f.code for f in verdict.findings)


def test_second_run_with_new_model_post_is_refused():
    record = _record(
        runs=[
            {"run_index": 1, "model_posts": 7, "status": "completed"},
            {"run_index": 2, "model_posts": 1, "status": "completed"},
        ],
        model_accounting={"run1_posts": 7, "run2_posts": 1, "total_posts": 8,
                          "provider_calls": 0, "llm_calls": 8, "paid_usd": 0.0},
    )
    verdict = oracle.evaluate_run(record)
    assert verdict.overall == STATUS_FAIL
    assert any("second_run" in f.code or "reuse" in f.code for f in verdict.findings)


def test_unrestored_scratch_is_reported_as_partial_not_pass():
    record = _record()
    record["cleanup"]["restored"] = False
    record["cleanup"]["remaining"] = ["owned/scratch-abc"]
    verdict = oracle.evaluate_run(record)
    assert verdict.overall == STATUS_PARTIAL
    assert any("restored" in f.code or "remaining" in f.code for f in verdict.findings)


def test_rewritten_fixed_expectation_is_refused():
    cases = [_case(cid) for cid in specs.required_case_ids()]
    cases[0]["expected"]["expectation"] = "whatever"
    verdict = oracle.evaluate_run(_record(cases=cases))
    assert verdict.overall == STATUS_FAIL
    assert any("expectation" in f.code for f in verdict.findings)


def test_required_case_ids_must_all_be_reported():
    cases = [c for c in _record()["cases"] if c["case_id"] != "prospectus"]
    executed = tuple(c["case_id"] for c in cases)
    record = _record(cases=cases, coverage=specs.coverage_report(executed))
    verdict = oracle.evaluate_run(record)
    assert verdict.overall == STATUS_FAIL


def test_unknown_case_id_is_refused():
    bogus = _case("annual-report")
    bogus["case_id"] = "not-a-case"
    cases = _record()["cases"] + [bogus]
    executed = tuple(c["case_id"] for c in cases)
    record = _record(cases=cases, coverage=specs.coverage_report(executed))
    verdict = oracle.evaluate_run(record)
    assert verdict.overall == STATUS_FAIL


# --------------------------------------------------------------------------
# card section 5: per-case semantics the oracle must enforce
# --------------------------------------------------------------------------


def test_skip_case_must_not_publish_a_summary():
    cases = [_case(cid) for cid in specs.required_case_ids()]
    skip = next(c for c in cases if c["case_id"] == "ir-policy")
    skip["actual"]["summary_status"] = "published"
    verdict = oracle.evaluate_run(_record(cases=cases))
    assert verdict.overall == STATUS_FAIL
    assert any("skip" in f.code for f in verdict.findings)


def test_narrative_case_must_reach_a_summary():
    cases = [_case(cid) for cid in specs.required_case_ids()]
    target = next(c for c in cases if c["case_id"] == "annual-report")
    target["actual"]["summary_status"] = "skipped_no_narrative"
    verdict = oracle.evaluate_run(_record(cases=cases))
    assert verdict.overall == STATUS_FAIL


def test_document_kind_must_be_preserved():
    cases = [_case(cid) for cid in specs.required_case_ids()]
    target = next(c for c in cases if c["case_id"] == "prospectus")
    target["actual"]["document_kind"] = "unknown"
    verdict = oracle.evaluate_run(_record(cases=cases))
    assert verdict.overall == STATUS_FAIL
    assert any("kind" in f.code for f in verdict.findings)


def test_transcript_must_not_be_converted_to_pdf():
    cases = [_case(cid) for cid in specs.required_case_ids()]
    target = next(c for c in cases if c["case_id"] == "call-txt-zh")
    target["actual"]["converted_to_pdf"] = True
    verdict = oracle.evaluate_run(_record(cases=cases))
    assert verdict.overall == STATUS_FAIL
    assert any("pdf" in f.code or "transcript" in f.code for f in verdict.findings)


def test_transcript_language_must_not_change():
    cases = [_case(cid) for cid in specs.required_case_ids()]
    target = next(c for c in cases if c["case_id"] == "call-txt-en")
    target["actual"]["language"] = "zh"
    verdict = oracle.evaluate_run(_record(cases=cases))
    assert verdict.overall == STATUS_FAIL


def test_both_container_formats_must_be_exercised():
    cases = [
        c for c in _record()["cases"]
        if c["case_id"] not in {"call-txt-zh", "call-txt-en"}
    ]
    executed = tuple(c["case_id"] for c in cases)
    record = _record(cases=cases, coverage=specs.coverage_report(executed))
    verdict = oracle.evaluate_run(record)
    assert verdict.overall == STATUS_FAIL
    assert any("format" in f.code for f in verdict.findings)


# --------------------------------------------------------------------------
# honesty boundaries
# --------------------------------------------------------------------------


def test_fixture_scope_cannot_claim_semantic_quality_or_paid_calls():
    record = _record()
    record["scope"]["llm_semantic_quality"] = "verified"
    verdict = oracle.evaluate_run(record)
    assert verdict.overall == STATUS_FAIL
    record = _record()
    record["scope"]["paid_calls"] = 1
    assert oracle.evaluate_run(record).overall == STATUS_FAIL


def test_zero_paid_calls_is_required_but_model_posts_may_be_nonzero():
    """A local loopback POST is a real call; it is not a paid provider call."""
    record = _record(
        runs=[
            {"run_index": 1, "model_posts": 7, "status": "completed"},
            {"run_index": 2, "model_posts": 0, "status": "completed"},
        ],
        model_accounting={"run1_posts": 7, "run2_posts": 0, "total_posts": 7,
                          "provider_calls": 0, "llm_calls": 7, "paid_usd": 0.0},
    )
    verdict = oracle.evaluate_run(record)
    assert verdict.overall == STATUS_PASS, verdict.findings


def test_not_run_and_unknown_are_never_pass():
    record = _record()
    record["cases"][0]["status"] = specs.STATUS_NOT_RUN
    verdict = oracle.evaluate_run(record)
    assert verdict.overall in {STATUS_FAIL, STATUS_PARTIAL}
    assert verdict.statuses.get("annual-report") != STATUS_PASS


def test_report_may_not_exceed_eight_mib(tmp_path: Path):
    from tools.narrative_g2_replay import report as report_mod

    assert report_mod.MAX_REPORT_BYTES == 8 * 1024 * 1024
    attempt = report_mod.create_attempt(tmp_path / "out")
    record = _record()
    path = report_mod.write_report(attempt, record)
    assert path.is_file()
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == (
        "narrative-g2-replay/1"
    )


def test_attempt_directories_are_never_overwritten(tmp_path: Path):
    from tools.narrative_g2_replay import report as report_mod

    first = report_mod.create_attempt(tmp_path / "out")
    second = report_mod.create_attempt(tmp_path / "out")
    assert first.path != second.path
    assert first.path.is_dir() and second.path.is_dir()


def test_case_spec_matrix_covers_every_card_required_type():
    ids = set(specs.required_case_ids())
    assert ids == {
        "annual-report", "half-year-report", "quarterly-report", "prospectus",
        "placement", "convertible-bond", "ir-policy", "call-txt-zh", "call-txt-en",
    }
    # placement and convertible bond share one group but keep distinct cases
    placement = specs.spec_by_id("placement")
    convertible = specs.spec_by_id("convertible-bond")
    assert placement.group_id == convertible.group_id == "offering-documents"
    assert placement.document_kind != convertible.document_kind
    # at least two container formats in one batch
    formats = {spec.mime_type for spec in specs.case_specs()}
    assert set(specs.REQUIRED_FORMATS) <= formats


def test_coverage_report_flags_missing_and_unknown():
    coverage = specs.coverage_report(("annual-report", "bogus"))
    assert "prospectus" in coverage["missing_case_ids"]
    assert coverage["unknown_case_ids"] == ["bogus"]
