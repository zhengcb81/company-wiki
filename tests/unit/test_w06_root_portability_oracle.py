"""Oracle counterexamples: the suite must refuse every known false PASS shape.

Phase A of W06-CWP-PORTABILITY.  Each test builds a run record (schema
cwp-root-portability/1) that claims success while exhibiting one shortcut the
construction card forbids, then requires the oracle to reject it with a named
finding.  A truthful record must pass; a malformed record must come back as
INVALID_RECORD (a tooling problem, never a production defect).
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.source_root_portability import oracle  # noqa: E402


SHA_PDF = "a" * 64
SHA_HTML = "b" * 64
SHA_TXT = "c" * 64
SHA_TXT_COPY = SHA_TXT  # same bytes in a second root: one logical source
NEW_SHA = "d" * 64

NONPERIODIC = {
    "htm": {"document_kind": "prospectus", "published_date": "2026-05-06",
            "fiscal_year": None, "period_end": None},
    "txt": {"document_kind": "investor_relations", "published_date": "2026-04-10",
            "fiscal_year": None, "period_end": None},
}
PERIODIC = {
    "pdf": {"document_kind": "annual_report", "published_date": "2026-03-01",
            "fiscal_year": 2025, "period_end": "2025-12-31"},
}
DOC_FACTS = {**PERIODIC, **NONPERIODIC}
DOC_SHA = {"pdf": SHA_PDF, "htm": SHA_HTML, "txt": SHA_TXT, "txt_copy": SHA_TXT_COPY}
DOC_SIZES = {"pdf": 320, "htm": 96, "txt": 120, "txt_copy": 120}


def _verified_read(doc_key: str, *, method: str = "open_version") -> dict:
    return {
        "doc_key": doc_key,
        "method": method,
        "purpose": "source_export",
        "channel": "reader_verified_bytes",
        "read_sha256": DOC_SHA[doc_key],
        "byte_size": DOC_SIZES[doc_key],
        "receipt": {
            "policy_sha256": "1" * 64,
            "source_read_policy_sha256": "2" * 64,
            "read_at": "2026-10-11T00:00:00Z",
        },
        "verification": {"byte_hash_match": True, "sha_computed_from": "read_bytes"},
    }


def _scenario(scenario_id: str, *, status: str = "PASS", evidence: dict,
              failure: dict | None = None) -> dict:
    return {
        "id": scenario_id,
        "expected": copy.deepcopy(oracle.FIXED_EXPECTATIONS[scenario_id]),
        "status": status,
        "actual": {"supported": True},
        "failure": failure,
        "evidence": evidence,
        "cleanup": {"touched_paths_refs": [], "restored": True},
    }


def _s1() -> dict:
    return _scenario("S1", evidence={
        "registration": {"channel": "register_sources",
                         "root_ids": ["local_company", "external_dayu", "external_dropbox"],
                         "doc_keys": ["pdf", "htm", "txt", "txt_copy"]},
        "reads": [_verified_read(key) for key in ("pdf", "htm", "txt", "txt_copy")],
        "describes": [{"doc_key": key, **DOC_FACTS[key]} for key in ("pdf", "htm", "txt")],
        "export": {
            "channel": "source_export_v2_cli", "exit_code": 0,
            "bundle_sha256": "3" * 64, "path_fields_present": False,
            "manifests": [{"doc_key": key, "source_id": f"urn:source:{DOC_SHA[key]}",
                           "content_sha256": DOC_SHA[key], **DOC_FACTS[key]}
                          for key in ("pdf", "htm", "txt")],
        },
    })


def _s2() -> dict:
    return _scenario("S2", evidence={
        "move": {"same_root_ids": True, "same_relative_paths": True,
                 "before_roots": [{"root_id": "local_company", "path_ref": "lake_A/local company 根"}],
                 "after_roots": [{"root_id": "local_company", "path_ref": "lake_B/local company 根"}]},
        "policy_observation": {"before_policy_sha256": "4" * 64,
                               "after_policy_sha256": "5" * 64,
                               "change_observed": True,
                               "change_is_auth_gate": False},
        "reads_after_move": [
            {**_verified_read(key), "ref_identity_preserved": True,
             "resolution": "current_root"}
            for key in ("pdf", "htm", "txt")
        ],
        "consumer_abs_path_dependency": False,
        "supported": True,
    })


def _s3() -> dict:
    return _scenario("S3", evidence={
        "before": {"doc_key": "pdf", "root_id": "local_company",
                   "relative_path": "2025 年度报告/年报 文件.pdf",
                   "document_id": "urn:doc:" + SHA_PDF, "source_id": "urn:source:" + SHA_PDF,
                   "content_sha256": SHA_PDF},
        "after": {"root_id": "external_dayu", "relative_path": "迁移/年报 文件.pdf",
                  "document_id": "urn:doc:" + SHA_PDF, "source_id": "urn:source:" + SHA_PDF,
                  "content_sha256": SHA_PDF},
        "revision_relation": "same_content_same_ids",
        "old_ref_outcome": {"status": "readable", "reason": None,
                            "classification": "old_ref_reads_via_current_location",
                            "read": {**_verified_read("pdf"),
                                     "ref_identity_preserved": True,
                                     "resolution": "current_root"}},
        "identity_stability": "PROMISED_FIELDS_ONLY",
        "stability_claimed_fields": ["content_sha256", "byte_size", "mime_type",
                                     "document_kind", "published_date"],
    })


def _s4() -> dict:
    return _scenario("S4", evidence={
        "dup": {"content_sha256": SHA_TXT, "logical_source_count": 1,
                "physical_copy_count": 2, "source_id": "urn:source:" + SHA_TXT,
                "copies": [{"root_id": "external_dayu", "candidate_rank": 1,
                            "is_canonical": True},
                           {"root_id": "external_dropbox", "candidate_rank": 2,
                            "is_canonical": False}]},
        "selection": {"chose_by": "root_priority_not_disk_path",
                      "selected_root_id": "external_dayu"},
        "after_delete": {"deleted_root_id": "external_dayu", "synthetic_only": True,
                         "read": {**_verified_read("txt"),
                                  "byte_hash_match": True}},
    })


def _s5() -> dict:
    return _scenario("S5", evidence={
        "raw_unavailable": {"tried": True, "status": "unavailable",
                            "reason": "read_failed",
                            "bytes_claimed_verified": False, "receipt_issued": False},
        "restored": {"read": _verified_read("txt")},
        "corruption": {"refused": True, "reason": "content_sha256_mismatch",
                       "sha_computed_from": "read_bytes",
                       "channel": "reader_verified_bytes"},
        "new_version": {"old_content_sha256": SHA_TXT, "new_content_sha256": NEW_SHA,
                        "distinct": True,
                        "old_ref_after_new_content": {"status": "unavailable",
                                                      "reason": "content_sha256_mismatch"}},
    })


def _s6() -> dict:
    return _scenario("S6", evidence={
        "docs": [{"doc_key": key, "nonperiodic": key in NONPERIODIC,
                  "before": dict(DOC_FACTS[key]), "after": dict(DOC_FACTS[key])}
                 for key in ("pdf", "htm", "txt")],
    })


def _s7() -> dict:
    return _scenario("S7", evidence={
        "export_process": {"pid": 41001, "exit_code": 0,
                           "channel": "source_export_v2_cli",
                           "bundle_sha256": "3" * 64},
        "consumer_process": {"pid": 41002, "distinct_from_runner": True,
                             "reopen": {**_verified_read("txt"),
                                        "bytes_origin": "fresh_read",
                                        "byte_hash_match": True}},
        "buffer_reuse_claimed": False,
    })


def _truthful_record() -> dict:
    sentinels = [{"path_ref": "owned/baseline.sentinel", "sha256": "e" * 64}]
    return {
        "schema_version": oracle.SCHEMA_VERSION,
        "run": {
            "run_id": "attempt-0001", "runner_pid": 41000,
            "started_at": "2026-10-11T00:00:00Z", "finished_at": "2026-10-11T00:01:00Z",
            "elapsed_seconds": 60.0,
            "code_identity": {
                "head": "0" * 40, "branch": "codex/w06-cwp-portability",
                "modules": [{"path": "src/company_wiki/source_catalog/source_reader.py",
                             "sha256": "f" * 64, "source": "worktree"}],
                "python_binding": {"company_wiki_file": "src/company_wiki/__init__.py",
                                   "bound_root": "worktree/src"},
            },
            "config_summary": {
                "roots": [{"root_id": "local_company", "path_ref": "lake_A/local company 根",
                           "kind": "directory", "priority": 10,
                           "adapter_id": "sidecar_filing_v1"}],
                "catalog_dir_ref": "owned/catalog", "schema_version": "1.0",
            },
        },
        "fixture": {
            "originals": [
                {"doc_key": "pdf", "root_id": "local_company",
                 "relative_path": "2025 年度报告/年报 文件.pdf",
                 "content_sha256": SHA_PDF, "byte_size": DOC_SIZES["pdf"],
                 "mime_type": "application/pdf", **DOC_FACTS["pdf"],
                 "nonperiodic": False, "synthetic": True,
                 "is_physical_copy_of": None},
                {"doc_key": "htm", "root_id": "external_dropbox",
                 "relative_path": "募集说明书 文件.html",
                 "content_sha256": SHA_HTML, "byte_size": DOC_SIZES["htm"],
                 "mime_type": "text/html", **DOC_FACTS["htm"],
                 "nonperiodic": True, "synthetic": True,
                 "is_physical_copy_of": None},
                {"doc_key": "txt", "root_id": "external_dayu",
                 "relative_path": "业绩说明会 纪要.txt",
                 "content_sha256": SHA_TXT, "byte_size": DOC_SIZES["txt"],
                 "mime_type": "text/plain", **DOC_FACTS["txt"],
                 "nonperiodic": True, "synthetic": True,
                 "is_physical_copy_of": None},
                {"doc_key": "txt_copy", "root_id": "external_dropbox",
                 "relative_path": "副本/业绩说明会 纪要.txt",
                 "content_sha256": SHA_TXT_COPY, "byte_size": DOC_SIZES["txt"],
                 "mime_type": "text/plain", **DOC_FACTS["txt"],
                 "nonperiodic": True, "synthetic": True,
                 "is_physical_copy_of": "txt"},
            ],
        },
        "scenarios": [_s1(), _s2(), _s3(), _s4(), _s5(), _s6(), _s7()],
        "consumer_access": {"entries": [
            {"pid": 41002, "path_class": "raw", "attributed_to": "company_wiki",
             "path_ref": "lake_B/…/业绩说明会 纪要.txt"},
            {"pid": 41002, "path_class": "catalog", "attributed_to": "company_wiki",
             "path_ref": "owned/catalog/catalog.sqlite3"},
        ]},
        "cost": {"source_read_calls": 12, "http_calls": 0, "model_calls": 0,
                 "paid_usd": 0.0},
        "cleanup": {
            "owned_root": "owned",
            "baseline": {"exists": False, "sentinels": sentinels},
            "after": {"exists": True, "sentinels": copy.deepcopy(sentinels)},
            "deleted_within_owned": True, "restored": True, "raw_unchanged": True,
        },
        "findings": [],
    }


def _codes(verdict: oracle.OracleVerdict) -> set[str]:
    return {finding.code for finding in verdict.findings}


def test_truthful_record_is_accepted():
    verdict = oracle.evaluate_run(_truthful_record())
    assert verdict.overall == oracle.STATUS_PASS
    assert verdict.findings == ()
    assert all(status == oracle.STATUS_PASS for status in verdict.statuses.values())


def test_counterexample_missing_reopen_is_rejected():
    record = _truthful_record()
    reopen = record["scenarios"][6]["evidence"]["consumer_process"]["reopen"]
    reopen["bytes_origin"] = "preexisting_object"
    record["scenarios"][6]["evidence"]["consumer_process"]["distinct_from_runner"] = False
    verdict = oracle.evaluate_run(record)
    assert verdict.statuses["S7"] == oracle.STATUS_FAIL
    assert "false_pass_missing_reopen" in _codes(verdict)


def test_counterexample_reopen_in_same_process_is_rejected():
    record = _truthful_record()
    record["scenarios"][6]["evidence"]["consumer_process"]["pid"] = record["run"]["runner_pid"]
    verdict = oracle.evaluate_run(record)
    assert verdict.statuses["S7"] == oracle.STATUS_FAIL
    assert "false_pass_missing_reopen" in _codes(verdict)


def test_counterexample_sha_only_metadata_is_rejected():
    record = _truthful_record()
    read = record["scenarios"][0]["evidence"]["reads"][0]
    read["channel"] = "metadata_only"
    read["verification"] = {"byte_hash_match": True, "sha_computed_from": "metadata_field"}
    verdict = oracle.evaluate_run(record)
    assert verdict.statuses["S1"] == oracle.STATUS_FAIL
    assert "false_pass_sha_metadata_only" in _codes(verdict)


def test_counterexample_forged_receipt_skipping_reader_is_rejected():
    record = _truthful_record()
    read = record["scenarios"][0]["evidence"]["reads"][1]
    read["method"] = "manual_receipt"
    read["channel"] = "fixture_sha_planted"
    verdict = oracle.evaluate_run(record)
    assert verdict.statuses["S1"] == oracle.STATUS_FAIL
    assert "false_pass_sha_metadata_only" in _codes(verdict)


def test_counterexample_consumer_sneaks_raw_open_is_rejected():
    record = _truthful_record()
    record["consumer_access"]["entries"].append(
        {"pid": 41002, "path_class": "raw", "attributed_to": "consumer",
         "path_ref": "lake_B/…/年报 文件.pdf"},
    )
    verdict = oracle.evaluate_run(record)
    assert verdict.statuses["S7"] == oracle.STATUS_FAIL
    assert "false_pass_consumer_raw_open" in _codes(verdict)


def test_counterexample_fake_dates_after_move_are_rejected():
    record = _truthful_record()
    after = record["scenarios"][5]["evidence"]["docs"][1]["after"]
    after["published_date"] = "2026-10-11"  # move must never mint a new date
    verdict = oracle.evaluate_run(record)
    assert verdict.statuses["S6"] == oracle.STATUS_FAIL
    assert "false_pass_fake_dates_after_move" in _codes(verdict)


def test_counterexample_fake_fy_on_nonperiodic_is_rejected():
    record = _truthful_record()
    after = record["scenarios"][5]["evidence"]["docs"][2]["after"]
    after["fiscal_year"] = 2026  # IR originals do not acquire a fictitious FY
    verdict = oracle.evaluate_run(record)
    assert verdict.statuses["S6"] == oracle.STATUS_FAIL
    assert "false_pass_fake_dates_after_move" in _codes(verdict)


def test_counterexample_physical_duplicate_as_logical_source_is_rejected():
    record = _truthful_record()
    record["scenarios"][3]["evidence"]["dup"]["logical_source_count"] = 2
    verdict = oracle.evaluate_run(record)
    assert verdict.statuses["S4"] == oracle.STATUS_FAIL
    assert "false_pass_physical_dup_as_logical_source" in _codes(verdict)


def test_counterexample_missing_policy_observation_is_rejected():
    record = _truthful_record()
    observation = record["scenarios"][1]["evidence"]["policy_observation"]
    observation["before_policy_sha256"] = None
    observation["after_policy_sha256"] = None
    verdict = oracle.evaluate_run(record)
    assert verdict.statuses["S2"] == oracle.STATUS_FAIL
    assert "false_pass_no_policy_observation" in _codes(verdict)


def test_counterexample_policy_change_claim_without_values_is_rejected():
    record = _truthful_record()
    observation = record["scenarios"][1]["evidence"]["policy_observation"]
    observation.pop("before_policy_sha256")
    observation.pop("after_policy_sha256")
    verdict = oracle.evaluate_run(record)
    assert verdict.statuses["S2"] == oracle.STATUS_FAIL
    assert "false_pass_no_policy_observation" in _codes(verdict)


def test_counterexample_cleanup_out_of_scope_is_rejected():
    record = _truthful_record()
    record["cleanup"]["deleted_within_owned"] = False
    verdict = oracle.evaluate_run(record)
    assert "false_pass_cleanup_out_of_scope" in _codes(verdict)
    assert verdict.overall == oracle.STATUS_FAIL


def test_counterexample_lost_sentinel_is_rejected():
    record = _truthful_record()
    record["cleanup"]["after"]["sentinels"] = []
    verdict = oracle.evaluate_run(record)
    assert "false_pass_lost_sentinel" in _codes(verdict)
    assert verdict.overall == oracle.STATUS_FAIL


def test_counterexample_mutated_fixed_expectation_is_rejected():
    record = _truthful_record()
    record["scenarios"][1]["expected"]["old_ref_same_bytes"] = False
    verdict = oracle.evaluate_run(record)
    assert "false_pass_fixed_expectation_mutated" in _codes(verdict)
    assert verdict.overall == oracle.STATUS_FAIL


def test_unknown_identity_stability_cannot_pass_as_same_id_migration():
    record = _truthful_record()
    scenario = record["scenarios"][2]
    scenario["evidence"]["identity_stability"] = "UNKNOWN_ROOT_DECIDES"
    scenario["status"] = oracle.STATUS_PASS
    verdict = oracle.evaluate_run(record)
    assert verdict.statuses["S3"] in {oracle.STATUS_FAIL, oracle.STATUS_UNKNOWN}
    assert verdict.statuses["S3"] != oracle.STATUS_PASS
    assert "false_pass_unknown_identity_mix" in _codes(verdict)


def test_corruption_detected_only_via_metadata_is_rejected():
    record = _truthful_record()
    record["scenarios"][4]["evidence"]["corruption"]["sha_computed_from"] = "metadata_field"
    verdict = oracle.evaluate_run(record)
    assert verdict.statuses["S5"] == oracle.STATUS_FAIL
    assert "false_pass_sha_metadata_only" in _codes(verdict)


def test_fake_verified_receipt_while_raw_missing_is_rejected():
    record = _truthful_record()
    record["scenarios"][4]["evidence"]["raw_unavailable"]["bytes_claimed_verified"] = True
    verdict = oracle.evaluate_run(record)
    assert verdict.statuses["S5"] == oracle.STATUS_FAIL
    assert "false_pass_fake_verified_receipt" in _codes(verdict)


def test_accurate_partial_report_is_not_a_false_pass():
    record = _truthful_record()
    scenario = record["scenarios"][1]
    scenario["status"] = oracle.STATUS_PARTIAL
    scenario["actual"] = {"supported": False}
    scenario["failure"] = {"code": "product_gap_root_remap",
                           "detail": "current implementation cannot remap moved root"}
    verdict = oracle.evaluate_run(record)
    assert verdict.statuses["S2"] == oracle.STATUS_PARTIAL
    assert "false_pass" not in " ".join(_codes(verdict))
    assert verdict.overall == oracle.STATUS_PARTIAL


def test_malformed_record_is_invalid_not_a_product_bug():
    verdict = oracle.evaluate_run({"schema_version": "other/9"})
    assert verdict.overall == oracle.STATUS_INVALID
    assert verdict.statuses.get("run") == oracle.STATUS_INVALID
    assert all(not finding.code.startswith("false_pass") for finding in verdict.findings)


def test_non_dict_record_is_invalid():
    verdict = oracle.evaluate_run(["not", "a", "record"])
    assert verdict.overall == oracle.STATUS_INVALID


def test_offline_contract_requires_zero_http_calls():
    record = _truthful_record()
    record["cost"]["http_calls"] = 1
    verdict = oracle.evaluate_run(record)
    assert "offline_violation" in _codes(verdict)
    assert verdict.overall == oracle.STATUS_FAIL


def test_code_identity_must_be_recorded():
    record = _truthful_record()
    record["run"]["code_identity"]["modules"] = []
    verdict = oracle.evaluate_run(record)
    assert "code_identity_missing" in _codes(verdict)
