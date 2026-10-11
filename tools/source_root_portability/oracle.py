"""Oracle for run records (schema cwp-root-portability/1).

The oracle owns the FIXED expectations of the W06-CWP-PORTABILITY card; a run
record may report outcomes but never rewrite them.  It judges each scenario's
evidence for the known false-PASS shapes:

- ``false_pass_missing_reopen``            – migration "reopens" that reuse an
  old Python buffer or the same process instead of a fresh verified read.
- ``false_pass_sha_metadata_only``         – SHA "checked" from metadata, a
  forged receipt, or reader APIs bypassed entirely.
- ``false_pass_consumer_raw_open``         – the pathless consumer opened raw
  fixture files itself instead of the official reader.
- ``false_pass_fake_dates_after_move``     – a root move minted new dates/period
  facts, or gave a nonperiodic original a fictitious fiscal year.
- ``false_pass_physical_dup_as_logical_source`` – two physical copies of the
  same bytes reported as two business sources.
- ``false_pass_no_policy_observation``     – config-remap policy SHA change
  claimed or denied without observed before/after values.
- ``false_pass_cleanup_out_of_scope`` / ``false_pass_lost_sentinel`` – cleanup
  touched paths outside the owned root, or dropped a baseline sentinel.
- ``false_pass_fixed_expectation_mutated`` – the record rewrote ``expected``.
- ``false_pass_unknown_identity_mix``      – a ROOT-decidable identity question
  silently promoted to a passed same-ID migration.
- ``false_pass_fake_verified_receipt``     – verified bytes claimed while the
  raw location was unavailable.

A malformed record is INVALID_RECORD — a harness problem, never a product
defect.  evaluate_run() never raises on bad input.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SCHEMA_VERSION = "cwp-root-portability/1"

STATUS_PASS = "PASS"
STATUS_PARTIAL = "PARTIAL"
STATUS_FAIL = "FAIL"
STATUS_UNKNOWN = "UNKNOWN"
STATUS_INVALID = "INVALID_RECORD"

_ALL_STATUSES = (STATUS_PASS, STATUS_PARTIAL, STATUS_FAIL, STATUS_UNKNOWN)
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_READER_METHODS = frozenset({"open_version", "verify_version"})
_VERIFIED_CHANNEL = "reader_verified_bytes"
_FRESH_ORIGIN = "fresh_read"
_CHOSE_BY_PRIORITY = "root_priority_not_disk_path"

# Fields whose stability the read interface actually promises (SourceRef 2.0
# identity plus catalog-owned period/kind facts).  document_id is deliberately
# absent: the card forbids pre-assuming permanent document ids.
PROMISED_STABILITY_FIELDS = frozenset(
    {"content_sha256", "byte_size", "mime_type", "schema_version",
     "document_kind", "published_date"}
)

# Fixed expectations straight from the W06-CWP-PORTABILITY construction card.
FIXED_EXPECTATIONS: dict[str, dict[str, object]] = {
    "S1": {
        "exact_sha": True,
        "period_kind_preserved": True,
        "channel": "reader_verified_bytes",
    },
    "S2": {
        "same_root_id_relative_path": True,
        "old_ref_same_bytes": True,
        "abs_old_path_not_consumer_dependency": True,
        "policy_change_is_not_auth_gate": True,
    },
    "S3": {
        "re_register_normal_flow": True,
        "record_id_relationships": True,
        "identity_stability_only_promised_fields": True,
    },
    "S4": {
        "one_logical_source": True,
        "candidate_by_root_priority": True,
        "fallback_copy_readable_after_delete": True,
    },
    "S5": {
        "no_fake_verified_receipt": True,
        "sha_rejects_corruption": True,
        "new_content_new_version": True,
    },
    "S6": {
        "asof_period_kind_stable": True,
        "nonperiodic_no_fake_fy": True,
    },
    "S7": {
        "fresh_process_reopen": True,
        "pathless_consumer": True,
    },
}


@dataclass(frozen=True)
class Finding:
    code: str
    scenario_id: str | None
    detail: str


@dataclass(frozen=True)
class OracleVerdict:
    statuses: dict[str, str]
    findings: tuple[Finding, ...]
    overall: str


def _finding(code: str, scenario_id: str | None, detail: str) -> Finding:
    return Finding(code, scenario_id, detail)


def _is_sha(value: object) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.fullmatch(value))


def _invalid(detail: str) -> OracleVerdict:
    return OracleVerdict(
        {"run": STATUS_INVALID},
        (_finding("invalid_record_shape", None, detail),),
        STATUS_INVALID,
    )


def _validate_structure(record: dict) -> str | None:
    """Return a problem description, or None when the record is well formed."""
    if record.get("schema_version") != SCHEMA_VERSION:
        return "schema_version is not " + SCHEMA_VERSION
    for key in ("run", "fixture", "scenarios", "consumer_access", "cost", "cleanup"):
        if key not in record:
            return f"missing top-level field: {key}"
    run = record["run"]
    if not isinstance(run, dict):
        return "run is not an object"
    for key in ("run_id", "started_at", "finished_at", "code_identity", "config_summary"):
        if key not in run:
            return f"run missing field: {key}"
    if not isinstance(run.get("runner_pid"), int):
        return "run.runner_pid is not an integer"
    if not isinstance(run.get("elapsed_seconds"), (int, float)):
        return "run.elapsed_seconds is not a number"
    identity = run["code_identity"]
    if not isinstance(identity, dict) or not isinstance(identity.get("modules"), list):
        return "run.code_identity.modules is not a list"
    if not isinstance(record["fixture"], dict) or not isinstance(
        record["fixture"].get("originals"), list
    ):
        return "fixture.originals is not a list"
    for original in record["fixture"]["originals"]:
        if not isinstance(original, dict) or "doc_key" not in original:
            return "fixture original without doc_key"
        for key in ("content_sha256", "byte_size", "document_kind", "published_date",
                    "nonperiodic", "synthetic"):
            if key not in original:
                return f"fixture original missing field: {key}"
    scenarios = record["scenarios"]
    if not isinstance(scenarios, list) or not scenarios:
        return "scenarios is not a non-empty list"
    seen: set[str] = set()
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            return "scenario is not an object"
        for key in ("id", "expected", "status", "actual", "failure", "evidence", "cleanup"):
            if key not in scenario:
                return f"scenario missing field: {key}"
        if not isinstance(scenario["id"], str) or not scenario["id"]:
            return "scenario id is not text"
        if scenario["id"] in seen:
            return f"duplicate scenario id: {scenario['id']}"
        seen.add(scenario["id"])
        if not isinstance(scenario["expected"], dict):
            return "scenario expected is not an object"
        if scenario["status"] not in _ALL_STATUSES:
            return "scenario status is not a known status"
        if not isinstance(scenario["evidence"], dict):
            return "scenario evidence is not an object"
        if scenario["failure"] is not None and not isinstance(scenario["failure"], dict):
            return "scenario failure is not an object or null"
    consumer_access = record["consumer_access"]
    if not isinstance(consumer_access, dict) or not isinstance(
        consumer_access.get("entries"), list
    ):
        return "consumer_access.entries is not a list"
    for entry in consumer_access["entries"]:
        if not isinstance(entry, dict):
            return "consumer access entry is not an object"
        for key in ("pid", "path_class", "attributed_to", "path_ref"):
            if key not in entry:
                return f"consumer access entry missing field: {key}"
    cost = record["cost"]
    if not isinstance(cost, dict) or not isinstance(cost.get("http_calls"), int):
        return "cost.http_calls is not an integer"
    cleanup = record["cleanup"]
    if not isinstance(cleanup, dict):
        return "cleanup is not an object"
    for key in ("owned_root", "baseline", "after", "deleted_within_owned",
                "restored", "raw_unchanged"):
        if key not in cleanup:
            return f"cleanup missing field: {key}"
    for side in ("baseline", "after"):
        block = cleanup[side]
        if not isinstance(block, dict) or not isinstance(block.get("sentinels"), list):
            return f"cleanup.{side}.sentinels is not a list"
    return None


def _check_verified_read(
    read: object, *, expected_sha: str, expected_size: int | None,
    scenario_id: str, findings: list[Finding],
) -> None:
    """One read counts only when the reader verified real bytes."""
    if not isinstance(read, dict):
        findings.append(_finding("false_pass_sha_metadata_only", scenario_id,
                                 "read evidence is not an object"))
        return
    if read.get("method") not in _READER_METHODS:
        findings.append(_finding(
            "false_pass_sha_metadata_only", scenario_id,
            f"read method {read.get('method')!r} bypasses the official reader"))
        return
    verification = read.get("verification")
    if not isinstance(verification, dict):
        findings.append(_finding("false_pass_sha_metadata_only", scenario_id,
                                 "read has no byte-verification block"))
        return
    if (
        read.get("channel") != _VERIFIED_CHANNEL
        or verification.get("sha_computed_from") != "read_bytes"
        or verification.get("byte_hash_match") is not True
    ):
        findings.append(_finding(
            "false_pass_sha_metadata_only", scenario_id,
            "SHA was not computed from the returned read bytes"))
        return
    if not _is_sha(read.get("read_sha256")) or read.get("read_sha256") != expected_sha:
        findings.append(_finding("false_pass_sha_metadata_only", scenario_id,
                                 "read_sha256 does not match the fixture original"))
        return
    if expected_size is not None and read.get("byte_size") != expected_size:
        findings.append(_finding("false_pass_sha_metadata_only", scenario_id,
                                 "read byte_size does not match the fixture original"))


def _logical_originals(record: dict) -> list[dict]:
    return [
        original for original in record["fixture"]["originals"]
        if not original.get("is_physical_copy_of")
    ]


def _original_by_key(record: dict) -> dict[str, dict]:
    return {original["doc_key"]: original for original in record["fixture"]["originals"]}


def _check_s1(scenario: dict, record: dict, findings: list[Finding]) -> None:
    originals = _original_by_key(record)
    evidence = scenario["evidence"]
    registration = evidence.get("registration")
    if not isinstance(registration, dict) or registration.get("channel") != "register_sources":
        findings.append(_finding("false_pass_sha_metadata_only", "S1",
                                 "registration did not go through register_sources"))
    reads = evidence.get("reads")
    if not isinstance(reads, list):
        findings.append(_finding("false_pass_sha_metadata_only", "S1",
                                 "reads evidence is not a list"))
        return
    by_key = {
        read.get("doc_key"): read for read in reads if isinstance(read, dict)
    }
    for doc_key, original in originals.items():
        if doc_key not in by_key:
            findings.append(_finding("false_pass_sha_metadata_only", "S1",
                                     f"no verified read recorded for {doc_key}"))
            continue
        _check_verified_read(
            by_key[doc_key], expected_sha=original["content_sha256"],
            expected_size=original["byte_size"], scenario_id="S1", findings=findings,
        )
    facts_fields = ("document_kind", "published_date", "fiscal_year", "period_end")
    describes = {
        item.get("doc_key"): item for item in evidence.get("describes") or []
        if isinstance(item, dict)
    }
    for original in _logical_originals(record):
        described = describes.get(original["doc_key"])
        if not isinstance(described, dict) or any(
            described.get(field) != original.get(field) for field in facts_fields
        ):
            findings.append(_finding(
                "false_pass_fake_dates_after_move", "S1",
                f"describe facts for {original['doc_key']} do not keep "
                "period/document-kind"))
    export = evidence.get("export")
    if not isinstance(export, dict):
        findings.append(_finding("false_pass_path_leak", "S1",
                                 "export evidence is not an object"))
        return
    if export.get("path_fields_present") is not False:
        findings.append(_finding("false_pass_path_leak", "S1",
                                 "export bundle carries path fields"))
    if (
        export.get("channel") not in {"source_export_v2_cli", "SourceExportBundleV2"}
        or export.get("exit_code") != 0
    ):
        findings.append(_finding("false_pass_unreported_product_failure", "S1",
                                 "export did not run through the versioned export surface"))
    manifests = {
        item.get("doc_key"): item for item in export.get("manifests") or []
        if isinstance(item, dict)
    }
    for original in _logical_originals(record):
        manifest = manifests.get(original["doc_key"])
        if not isinstance(manifest, dict) or any(
            manifest.get(field) != original.get(field) for field in facts_fields
        ) or manifest.get("content_sha256") != original["content_sha256"]:
            findings.append(_finding(
                "false_pass_sha_metadata_only", "S1",
                f"export manifest for {original['doc_key']} does not carry the "
                "verified identity/period facts"))


def _check_s2(scenario: dict, record: dict, findings: list[Finding]) -> None:
    evidence = scenario["evidence"]
    move = evidence.get("move")
    if not isinstance(move, dict) or move.get("same_root_ids") is not True \
            or move.get("same_relative_paths") is not True:
        findings.append(_finding("expectation_unmet", "S2",
                                 "move is not same root_id + same relative_path"))
    observation = evidence.get("policy_observation")
    if not isinstance(observation, dict):
        findings.append(_finding("false_pass_no_policy_observation", "S2",
                                 "no policy observation block"))
    else:
        before = observation.get("before_policy_sha256")
        after = observation.get("after_policy_sha256")
        if not _is_sha(before) or not _is_sha(after):
            findings.append(_finding(
                "false_pass_no_policy_observation", "S2",
                "policy SHA change claimed or denied without observed values"))
        elif observation.get("change_observed") != (before != after):
            findings.append(_finding(
                "false_pass_no_policy_observation", "S2",
                "change_observed contradicts the observed policy SHAs"))
        if observation.get("change_is_auth_gate") is not False:
            findings.append(_finding("expectation_unmet", "S2",
                                     "policy change treated as an authorization gate"))
    if evidence.get("consumer_abs_path_dependency") is not False:
        findings.append(_finding("false_pass_old_path_dependency", "S2",
                                 "consumer kept an absolute old-path dependency"))
    supported = scenario.get("actual", {}).get("supported")
    if supported is False or scenario.get("failure") is not None:
        if scenario["status"] == STATUS_PASS:
            findings.append(_finding("false_pass_unreported_product_failure", "S2",
                                     "product gap marked as PASS"))
        return
    if scenario["status"] != STATUS_PASS:
        return
    originals = _original_by_key(record)
    reads = evidence.get("reads_after_move")
    if not isinstance(reads, list) or not reads:
        findings.append(_finding("false_pass_sha_metadata_only", "S2",
                                 "no verified reads recorded after the root move"))
        return
    for read in reads:
        if not isinstance(read, dict):
            continue
        original = originals.get(read.get("doc_key"))
        if original is None:
            findings.append(_finding("false_pass_sha_metadata_only", "S2",
                                     "read for unknown doc_key"))
            continue
        _check_verified_read(
            read, expected_sha=original["content_sha256"],
            expected_size=original["byte_size"], scenario_id="S2", findings=findings,
        )
        if read.get("ref_identity_preserved") is not True:
            findings.append(_finding("expectation_unmet", "S2",
                                     "old SourceRef identity not preserved"))
        if read.get("resolution") != "current_root":
            findings.append(_finding("false_pass_old_path_dependency", "S2",
                                     "bytes resolved from a cached old path"))


def _check_s3(scenario: dict, record: dict, findings: list[Finding]) -> None:
    evidence = scenario["evidence"]
    before = evidence.get("before")
    after = evidence.get("after")
    if not isinstance(before, dict) or not isinstance(after, dict):
        findings.append(_finding("false_pass_id_relationship_forged", "S3",
                                 "before/after identity blocks missing"))
        return
    if before.get("content_sha256") != after.get("content_sha256"):
        findings.append(_finding("false_pass_id_relationship_forged", "S3",
                                 "content_sha256 changed across re-registration"))
    if not isinstance(evidence.get("revision_relation"), str) or not evidence.get(
        "revision_relation"
    ):
        findings.append(_finding("false_pass_id_relationship_forged", "S3",
                                 "revision relation not recorded"))
    stability = evidence.get("identity_stability")
    claimed_fields = set(evidence.get("stability_claimed_fields") or [])
    if stability == "PROMISED_FIELDS_ONLY":
        if not claimed_fields <= PROMISED_STABILITY_FIELDS:
            findings.append(_finding(
                "false_pass_identity_overreach", "S3",
                "identity stability claimed outside the promised fields"))
    elif stability == "UNKNOWN_ROOT_DECIDES":
        if scenario["status"] == STATUS_PASS:
            findings.append(_finding(
                "false_pass_unknown_identity_mix", "S3",
                "ROOT-decidable identity question promoted to a passed migration"))
    else:
        findings.append(_finding("false_pass_unknown_identity_mix", "S3",
                                 "identity stability classification missing"))
    outcome = evidence.get("old_ref_outcome")
    if not isinstance(outcome, dict) or outcome.get("classification") not in {
        "old_ref_reads_via_current_location", "named_old_location_unavailable",
        "old_ref_unavailable_other",
    }:
        findings.append(_finding("expectation_unmet", "S3",
                                 "old-ref outcome not classified"))
        return
    if outcome.get("status") == "readable":
        original = _original_by_key(record).get(before.get("doc_key"))
        expected_sha = original["content_sha256"] if original else before.get(
            "content_sha256"
        )
        _check_verified_read(
            outcome.get("read"), expected_sha=expected_sha,
            expected_size=original["byte_size"] if original else None,
            scenario_id="S3", findings=findings,
        )


def _check_s4(scenario: dict, record: dict, findings: list[Finding]) -> None:
    evidence = scenario["evidence"]
    dup = evidence.get("dup")
    code = "false_pass_physical_dup_as_logical_source"
    if not isinstance(dup, dict):
        findings.append(_finding(code, "S4", "dup evidence block missing"))
        return
    copies = dup.get("copies") or []
    ranks = sorted(
        item.get("candidate_rank") for item in copies if isinstance(item, dict)
    )
    canonicals = [
        item for item in copies
        if isinstance(item, dict) and item.get("is_canonical") is True
    ]
    if (
        dup.get("logical_source_count") != 1
        or dup.get("physical_copy_count") != 2
        or not isinstance(copies, list) or len(copies) != 2
        or len({item.get("root_id") for item in copies if isinstance(item, dict)}) != 2
        or ranks != [1, 2]
        or len(canonicals) != 1
    ):
        findings.append(_finding(code, "S4",
                                 "two physical copies reported as two logical sources"))
    sha = dup.get("content_sha256")
    same_sha_logical = [
        original for original in _logical_originals(record)
        if original.get("content_sha256") == sha
    ]
    if len(same_sha_logical) != 1:
        findings.append(_finding(code, "S4",
                                 "fixture claims >1 logical source for one digest"))
    selection = evidence.get("selection")
    if not isinstance(selection, dict) or selection.get("chose_by") != _CHOSE_BY_PRIORITY:
        findings.append(_finding("false_pass_consumer_path_selection", "S4",
                                 "candidate was chosen by disk path, not root priority"))
    after_delete = evidence.get("after_delete")
    if not isinstance(after_delete, dict) or after_delete.get("synthetic_only") is not True:
        findings.append(_finding("expectation_unmet", "S4",
                                 "copy deletion not confined to synthetic copies"))
        return
    _check_verified_read(
        after_delete.get("read"), expected_sha=sha,
        expected_size=dup.get("physical_byte_size"),
        scenario_id="S4", findings=findings,
    )


def _check_s5(scenario: dict, record: dict, findings: list[Finding]) -> None:
    evidence = scenario["evidence"]
    unavailable = evidence.get("raw_unavailable")
    if not isinstance(unavailable, dict):
        findings.append(_finding("false_pass_fake_verified_receipt", "S5",
                                 "raw-unavailable evidence block missing"))
    elif (
        unavailable.get("bytes_claimed_verified") is not False
        or unavailable.get("receipt_issued") is not False
    ):
        findings.append(_finding("false_pass_fake_verified_receipt", "S5",
                                 "index claimed verified bytes while raw was unavailable"))
    originals = _original_by_key(record)
    restored = evidence.get("restored")
    if isinstance(restored, dict) and isinstance(restored.get("read"), dict):
        original = originals.get(restored["read"].get("doc_key"))
        _check_verified_read(
            restored["read"],
            expected_sha=original["content_sha256"] if original else "",
            expected_size=original["byte_size"] if original else None,
            scenario_id="S5", findings=findings,
        )
    else:
        findings.append(_finding("expectation_unmet", "S5",
                                 "no verified read recorded after restore"))
    corruption = evidence.get("corruption")
    if not isinstance(corruption, dict):
        findings.append(_finding("false_pass_corruption_accepted", "S5",
                                 "corruption evidence block missing"))
    elif corruption.get("refused") is not True:
        findings.append(_finding("false_pass_corruption_accepted", "S5",
                                 "corrupted bytes were not refused"))
    elif corruption.get("reason") not in {
        "content_sha256_mismatch", "byte_size_mismatch", "changed_during_read",
    }:
        findings.append(_finding("false_pass_sha_metadata_only", "S5",
                                 "corruption refusal is not a real byte-check reason"))
    elif (
        corruption.get("sha_computed_from") != "read_bytes"
        or corruption.get("channel") != _VERIFIED_CHANNEL
    ):
        findings.append(_finding("false_pass_sha_metadata_only", "S5",
                                 "corruption detected from metadata, not read bytes"))
    new_version = evidence.get("new_version")
    if not isinstance(new_version, dict):
        findings.append(_finding("false_pass_version_overwrite", "S5",
                                 "new-version evidence block missing"))
        return
    old_sha = new_version.get("old_content_sha256")
    new_sha = new_version.get("new_content_sha256")
    if (
        new_version.get("distinct") is not True
        or not _is_sha(old_sha) or not _is_sha(new_sha) or old_sha == new_sha
    ):
        findings.append(_finding("false_pass_version_overwrite", "S5",
                                 "new content did not become a new version"))
    old_ref = new_version.get("old_ref_after_new_content")
    if not isinstance(old_ref, dict) or old_ref.get("status") == "ok":
        findings.append(_finding("false_pass_version_overwrite", "S5",
                                 "old ref silently served new content"))


def _check_s6(scenario: dict, record: dict, findings: list[Finding]) -> None:
    facts_fields = ("document_kind", "published_date", "fiscal_year", "period_end")
    originals = _original_by_key(record)
    docs = scenario["evidence"].get("docs")
    if not isinstance(docs, list):
        docs = []
    by_key = {doc.get("doc_key"): doc for doc in docs if isinstance(doc, dict)}
    for original in _logical_originals(record):
        doc = by_key.get(original["doc_key"])
        if not isinstance(doc, dict):
            findings.append(_finding("false_pass_fake_dates_after_move", "S6",
                                     f"no before/after facts for {original['doc_key']}"))
            continue
        before = doc.get("before")
        after = doc.get("after")
        if not isinstance(before, dict) or not isinstance(after, dict) or before != after:
            findings.append(_finding("false_pass_fake_dates_after_move", "S6",
                                     f"root move changed facts for {original['doc_key']}"))
            continue
        if any(before.get(field) != original.get(field) for field in facts_fields):
            findings.append(_finding("false_pass_fake_dates_after_move", "S6",
                                     f"facts for {original['doc_key']} differ from "
                                     "the fixture truth"))
        if original.get("nonperiodic") and before.get("fiscal_year") is not None:
            findings.append(_finding("false_pass_fake_dates_after_move", "S6",
                                     f"nonperiodic {original['doc_key']} gained "
                                     "a fictitious fiscal year"))


def _check_s7(scenario: dict, record: dict, findings: list[Finding]) -> None:
    evidence = scenario["evidence"]
    run_pid = record["run"]["runner_pid"]
    consumer = evidence.get("consumer_process")
    if not isinstance(consumer, dict):
        findings.append(_finding("false_pass_missing_reopen", "S7",
                                 "consumer process evidence missing"))
        return
    reopen = consumer.get("reopen")
    if (
        consumer.get("distinct_from_runner") is not True
        or consumer.get("pid") == run_pid
        or not isinstance(reopen, dict)
        or reopen.get("bytes_origin") != _FRESH_ORIGIN
    ):
        findings.append(_finding("false_pass_missing_reopen", "S7",
                                 "bytes came from a preexisting buffer/process, "
                                 "not a fresh verified reopen"))
    else:
        originals = _original_by_key(record)
        original = originals.get(reopen.get("doc_key"))
        _check_verified_read(
            reopen,
            expected_sha=original["content_sha256"] if original else "",
            expected_size=original["byte_size"] if original else None,
            scenario_id="S7", findings=findings,
        )
    if evidence.get("buffer_reuse_claimed") is not False:
        findings.append(_finding("false_pass_missing_reopen", "S7",
                                 "record admits buffer reuse"))
    export = evidence.get("export_process")
    if not isinstance(export, dict) or export.get("exit_code") != 0:
        findings.append(_finding("false_pass_unreported_product_failure", "S7",
                                 "export process did not succeed"))


_SCENARIO_CHECKS = {
    "S1": _check_s1,
    "S2": _check_s2,
    "S3": _check_s3,
    "S4": _check_s4,
    "S5": _check_s5,
    "S6": _check_s6,
    "S7": _check_s7,
}


def _global_checks(record: dict, findings: list[Finding]) -> None:
    for entry in record["consumer_access"]["entries"]:
        if entry.get("path_class") == "raw" and entry.get("attributed_to") != "company_wiki":
            findings.append(_finding(
                "false_pass_consumer_raw_open", "S7",
                f"consumer frame opened raw path {entry.get('path_ref')!r}"))
    if record["cost"]["http_calls"] != 0:
        findings.append(_finding("offline_violation", None,
                                 "run performed network calls"))
    cleanup = record["cleanup"]
    if cleanup["baseline"]["sentinels"] != cleanup["after"]["sentinels"]:
        findings.append(_finding("false_pass_lost_sentinel", None,
                                 "baseline sentinels changed or disappeared"))
    if cleanup["deleted_within_owned"] is not True:
        findings.append(_finding("false_pass_cleanup_out_of_scope", None,
                                 "cleanup deleted outside the owned root"))
    if cleanup["restored"] is not True:
        findings.append(_finding("cleanup_not_restored", None,
                                 "owned root not restored to its baseline"))
    if cleanup["raw_unchanged"] is not True:
        findings.append(_finding("false_pass_cleanup_out_of_scope", None,
                                 "non-synthetic raw content was modified"))
    modules = record["run"]["code_identity"]["modules"]
    if not modules or any(
        not isinstance(module, dict) or not _is_sha(module.get("sha256"))
        for module in modules
    ):
        findings.append(_finding("code_identity_missing", None,
                                 "actual module files/SHA not recorded"))


def evaluate_run(record: dict) -> OracleVerdict:
    """Judge one cwp-root-portability/1 run record.

    Never raises: a malformed record yields INVALID_RECORD (a harness problem),
    never a claimed product defect.
    """
    if not isinstance(record, dict):
        return _invalid("record is not an object")
    problem = _validate_structure(record)
    if problem is not None:
        return _invalid(problem)

    findings: list[Finding] = []
    statuses: dict[str, str] = {}
    for scenario in record["scenarios"]:
        scenario_id = scenario["id"]
        if scenario["expected"] != FIXED_EXPECTATIONS.get(scenario_id):
            findings.append(_finding(
                "false_pass_fixed_expectation_mutated", scenario_id,
                "record rewrote the fixed scenario expectation"))
        check = _SCENARIO_CHECKS.get(scenario_id)
        if check is None:
            findings.append(_finding("false_pass_fixed_expectation_mutated",
                                     scenario_id, "unknown scenario id"))
        elif scenario["status"] == STATUS_PASS:
            # Strict evidence checks police PASS claims.  An accurate PARTIAL /
            # UNKNOWN report is honest reporting, not a false pass.
            check(scenario, record, findings)
        statuses[scenario_id] = scenario["status"]

    _global_checks(record, findings)

    forced_fail = {
        finding.scenario_id for finding in findings
        if finding.code.startswith("false_pass") and finding.scenario_id is not None
    }
    for scenario_id in forced_fail:
        if scenario_id in statuses:
            statuses[scenario_id] = STATUS_FAIL

    false_pass_run = any(finding.code.startswith("false_pass") for finding in findings)
    hard_defect = any(
        finding.code in {"offline_violation", "code_identity_missing"}
        for finding in findings
    )
    if false_pass_run or hard_defect:
        overall = STATUS_FAIL
    elif STATUS_FAIL in statuses.values():
        overall = STATUS_FAIL
    elif STATUS_PARTIAL in statuses.values():
        overall = STATUS_PARTIAL
    elif any(finding.code == "cleanup_not_restored" for finding in findings):
        overall = STATUS_PARTIAL
    elif STATUS_UNKNOWN in statuses.values():
        overall = STATUS_UNKNOWN
    else:
        overall = STATUS_PASS
    return OracleVerdict(statuses, tuple(findings), overall)
