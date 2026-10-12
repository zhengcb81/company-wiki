"""Independent oracle for run records (schema ``narrative-g2-replay/1``).

The oracle owns the FIXED expectations of the W08-CWP-G2-REPLAY card.  A run
record reports what happened; it may never rewrite what the card requires.

It rejects the known false-PASS shapes:

- ``false_pass_empty_case_set``            -- nothing was actually exercised.
- ``false_pass_required_case_missing``     -- a required case never ran.
- ``false_pass_required_group_missing``    -- a whole document-type group dropped.
- ``false_pass_unknown_case``              -- an unrequested case inflates coverage.
- ``false_pass_no_raw_receipt``            -- "PASS" with no raw receipt/evidence.
- ``false_pass_bad_raw_sha``               -- raw hash absent or not a SHA-256.
- ``false_pass_locator_not_replayed``      -- locator claimed without real replay.
- ``false_pass_second_run_new_post``       -- the reuse run issued a new model POST.
- ``false_pass_fixed_expectation_mutated`` -- the record rewrote ``expected``.
- ``false_pass_skip_published_summary``    -- a skip case published a summary.
- ``false_pass_narrative_skipped``         -- a narrative case produced no summary.
- ``false_pass_document_kind_changed``     -- document_kind was not preserved.
- ``false_pass_transcript_converted``      -- TXT original became a PDF.
- ``false_pass_transcript_language_changed`` -- original language was altered.
- ``false_pass_format_coverage_missing``   -- <2 container formats exercised.
- ``false_pass_scope_overclaim``           -- synthetic identity or semantic
  quality claimed as real, or paid calls claimed zero with nonzero usage.

A malformed record is INVALID_RECORD -- a harness problem, never a product
defect.  ``evaluate_run()`` never raises on bad input.
"""

from __future__ import annotations

import copy
import math
import re
from dataclasses import dataclass

from tools.narrative_g2_replay import specs

SCHEMA_VERSION = "narrative-g2-replay/1"

STATUS_PASS = specs.STATUS_PASS
STATUS_PARTIAL = specs.STATUS_PARTIAL
STATUS_FAIL = specs.STATUS_FAIL
STATUS_UNKNOWN = specs.STATUS_UNKNOWN
STATUS_NOT_RUN = specs.STATUS_NOT_RUN
STATUS_INVALID = "INVALID_RECORD"

_ALL_STATUSES = (
    STATUS_PASS, STATUS_PARTIAL, STATUS_FAIL, STATUS_UNKNOWN, STATUS_NOT_RUN,
)

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")

#: The reuse run index; the card requires zero new model POSTs here.
_REUSE_RUN_INDEX = 2

_TOP_LEVEL = (
    "scope", "code_binding", "case_specs", "coverage", "run_plan", "runs",
    "model_accounting", "rf_consumption", "cases", "bytes", "cleanup",
    "known_baseline_failures",
)

_CASE_FIELDS = (
    "case_id", "group_id", "expected", "status", "actual", "request", "result",
    "artifacts", "model", "evidence", "failure", "cleanup",
)


@dataclass(frozen=True)
class Finding:
    code: str
    case_id: str | None
    detail: str
    #: None is a diagnostic; mandatory contract findings default to FAIL.
    outcome: str | None = STATUS_FAIL


@dataclass(frozen=True)
class OracleVerdict:
    statuses: dict[str, str]
    findings: tuple[Finding, ...]
    overall: str


def _finding(code: str, case_id: str | None, detail: str, *,
             outcome: str | None = STATUS_FAIL) -> Finding:
    return Finding(code, case_id, detail, outcome)


def _is_sha(value: object) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.fullmatch(value))


def _invalid(detail: str) -> OracleVerdict:
    return OracleVerdict(
        {"run": STATUS_INVALID},
        (_finding("invalid_record_shape", None, detail, outcome=STATUS_INVALID),),
        STATUS_INVALID,
    )


# --------------------------------------------------------------------------
# structure
# --------------------------------------------------------------------------


def _validate_structure(record: object) -> str | None:
    """Return a problem description, or None when the record is well formed."""
    if not isinstance(record, dict):
        return "record is not an object"
    if record.get("schema_version") != SCHEMA_VERSION:
        return f"schema_version is not {SCHEMA_VERSION}"
    for key in _TOP_LEVEL:
        if key not in record:
            return f"missing top-level field: {key}"

    scope = record["scope"]
    if not isinstance(scope, dict):
        return "scope is not an object"
    for key in ("lane_id", "supplier_fixture", "llm_semantic_quality",
                "source_truth_verified", "paid_calls"):
        if key not in scope:
            return f"scope missing field: {key}"

    binding = record["code_binding"]
    if not isinstance(binding, dict):
        return "code_binding is not an object"
    for key in ("base_head", "modules", "rf_snapshot_modules"):
        if key not in binding:
            return f"code_binding missing field: {key}"
    for block in ("modules", "rf_snapshot_modules"):
        entries = binding[block]
        if not isinstance(entries, list) or not entries:
            return f"code_binding.{block} is not a non-empty list"
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                return f"code_binding.{block} entry without path"
            if not _is_sha(entry.get("sha256")):
                return f"code_binding.{block} entry without a SHA-256"

    if not isinstance(record["case_specs"], list) or not record["case_specs"]:
        return "case_specs is not a non-empty list"
    coverage = record["coverage"]
    if not isinstance(coverage, dict) or not isinstance(
        coverage.get("required_case_ids"), list
    ):
        return "coverage.required_case_ids is not a list"
    for key in ("executed_case_ids", "missing_case_ids", "unknown_case_ids"):
        if not isinstance(coverage.get(key), list):
            return f"coverage.{key} is not a list"

    plan = record["run_plan"]
    if not isinstance(plan, dict):
        return "run_plan is not an object"
    for key in ("deadline_seconds", "per_command_seconds"):
        value = plan.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            return f"run_plan.{key} is not a finite positive number"

    runs = record["runs"]
    if not isinstance(runs, list) or len(runs) < 2:
        return "runs must record the first and the reuse run"
    for run in runs:
        if not isinstance(run, dict):
            return "run entry is not an object"
        if type(run.get("run_index")) is not int or run["run_index"] <= 0:
            return "run entry without a positive run_index"
        if type(run.get("model_posts")) is not int or run["model_posts"] < 0:
            return "run entry without a nonnegative model_posts"

    accounting = record["model_accounting"]
    if not isinstance(accounting, dict):
        return "model_accounting is not an object"
    for key in ("run1_posts", "run2_posts", "total_posts", "provider_calls",
                "llm_calls"):
        if type(accounting.get(key)) is not int or accounting[key] < 0:
            return f"model_accounting.{key} is not a nonnegative integer"
    if type(accounting.get("paid_usd")) not in (int, float):
        return "model_accounting.paid_usd is not a number"

    rf = record["rf_consumption"]
    if not isinstance(rf, dict):
        return "rf_consumption is not an object"
    for key in ("consumer", "read_ok", "period_preserved", "language_preserved"):
        if key not in rf:
            return f"rf_consumption missing field: {key}"
    if not isinstance(rf.get("gaps_reported"), list):
        return "rf_consumption.gaps_reported is not a list"

    cases = record["cases"]
    if not isinstance(cases, list):
        return "cases is not a list"
    seen: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            return "case is not an object"
        for key in _CASE_FIELDS:
            if key not in case:
                return f"case missing field: {key}"
        if not isinstance(case["case_id"], str) or not case["case_id"]:
            return "case_id is not text"
        if case["case_id"] in seen:
            return f"duplicate case_id: {case['case_id']}"
        seen.add(case["case_id"])
        if not isinstance(case["expected"], dict):
            return "case.expected is not an object"
        if case["status"] not in _ALL_STATUSES:
            return f"case status is not a known status: {case['status']!r}"
        for key in ("actual", "request", "result", "model", "evidence", "cleanup"):
            if not isinstance(case[key], dict):
                return f"case.{key} is not an object"
        if not isinstance(case["artifacts"], list):
            return "case.artifacts is not a list"
        if case["failure"] is not None and not isinstance(case["failure"], dict):
            return "case.failure is not an object or null"

    body = record["bytes"]
    if not isinstance(body, dict):
        return "bytes is not an object"
    for key in ("raw_bytes", "derived_bytes"):
        if type(body.get(key)) is not int or body[key] < 0:
            return f"bytes.{key} is not a nonnegative integer"

    cleanup = record["cleanup"]
    if not isinstance(cleanup, dict):
        return "cleanup is not an object"
    for key in ("baseline", "after", "deleted_within_owned", "restored", "remaining"):
        if key not in cleanup:
            return f"cleanup missing field: {key}"
    for side in ("baseline", "after"):
        block = cleanup[side]
        if not isinstance(block, dict) or not isinstance(block.get("sentinels"), list):
            return f"cleanup.{side}.sentinels is not a list"
    if not isinstance(cleanup["remaining"], list):
        return "cleanup.remaining is not a list"

    if not isinstance(record["known_baseline_failures"], list):
        return "known_baseline_failures is not a list"
    return None


# --------------------------------------------------------------------------
# per-case checks (only policed on PASS claims)
# --------------------------------------------------------------------------


def _check_case(case: dict, record: dict, findings: list[Finding]) -> None:
    case_id = case["case_id"]
    try:
        spec = specs.spec_by_id(case_id)
        expected = specs.FIXED_EXPECTATIONS[case_id]
    except KeyError:
        # An unrequested case is a coverage defect, reported as FAIL.  It must
        # never become INVALID_RECORD, which would disguise a harness problem.
        findings.append(_finding(
            "false_pass_unknown_case", case_id,
            "case is not part of the fixed CaseSpec matrix"))
        return
    actual = case["actual"]

    if case["expected"] != expected:
        findings.append(_finding(
            "false_pass_fixed_expectation_mutated", case_id,
            "record rewrote the fixed case expectation"))

    # -- raw receipt / SHA -------------------------------------------------
    evidence = case["evidence"]
    if evidence.get("raw_receipt_present") is not True:
        findings.append(_finding(
            "false_pass_no_raw_receipt", case_id,
            "PASS claimed without a raw receipt/evidence record"))
    if not _is_sha(evidence.get("raw_sha256")):
        findings.append(_finding(
            "false_pass_bad_raw_sha", case_id,
            "raw SHA is absent or not a SHA-256"))

    # -- request/result surfaces ------------------------------------------
    request = case["request"]
    if not _is_sha(request.get("sha256")) or not isinstance(
        request.get("path_ref"), str
    ):
        findings.append(_finding(
            "false_pass_no_raw_receipt", case_id,
            "typed request ref/hash not recorded"))
    result = case["result"]
    if result.get("exit_code") != 0:
        findings.append(_finding(
            "false_pass_unreported_product_failure", case_id,
            "typed request did not exit 0 but the case is PASS"))

    # -- locator replay ----------------------------------------------------
    # A skip case legitimately selects zero spans, so it is required to publish
    # no locators rather than at least one.
    is_skip_case = bool(expected.get("skip_expected"))
    if expected.get("requires_summary") or spec.expectation == specs.EXPECT_TYPED_ONLY:
        if not case["artifacts"]:
            findings.append(_finding(
                "false_pass_locator_not_replayed", case_id,
                "no artifact recorded, so no locator could be replayed"))
        for artifact in case["artifacts"]:
            if not isinstance(artifact, dict):
                findings.append(_finding("false_pass_locator_not_replayed", case_id,
                                         "artifact is not an object"))
                continue
            if not _is_sha(artifact.get("sha256")):
                findings.append(_finding("false_pass_bad_raw_sha", case_id,
                                         "artifact without a SHA-256"))
            locators = artifact.get("locators")
            if not isinstance(locators, list) or not locators:
                findings.append(_finding("false_pass_locator_not_replayed", case_id,
                                         "artifact without any locator"))
            if artifact.get("locator_replay_verified") is not True:
                findings.append(_finding(
                    "false_pass_locator_not_replayed", case_id,
                    "locators were not replayed against the original bytes"))
    elif is_skip_case and case["artifacts"]:
        for artifact in case["artifacts"]:
            if not isinstance(artifact, dict):
                continue
            if artifact.get("locators"):
                findings.append(_finding(
                    "false_pass_skip_case_has_evidence", case_id,
                    "a skipped document published narrative evidence"))

    # -- summary semantics -------------------------------------------------
    summary_status = actual.get("summary_status")
    if expected.get("skip_expected"):
        if summary_status not in (None, "skipped_no_narrative", expected["skip_expected"]):
            findings.append(_finding(
                "false_pass_skip_published_summary", case_id,
                f"skip case published a summary: {summary_status!r}"))
    elif expected.get("requires_summary"):
        if summary_status in (None, "skipped_no_narrative", "absent"):
            findings.append(_finding(
                "false_pass_narrative_skipped", case_id,
                f"narrative case produced no summary: {summary_status!r}"))

    # -- typed identity ----------------------------------------------------
    if actual.get("document_kind") != expected["document_kind_preserved"]:
        findings.append(_finding(
            "false_pass_document_kind_changed", case_id,
            f"document_kind {actual.get('document_kind')!r} != "
            f"{expected['document_kind_preserved']!r}"))
    if actual.get("language") != expected["language"]:
        findings.append(_finding(
            "false_pass_transcript_language_changed", case_id,
            f"language {actual.get('language')!r} != {expected['language']!r}"))

    # -- transcript byte identity -----------------------------------------
    if expected.get("transcript_must_stay_txt"):
        if actual.get("converted_to_pdf") is not False:
            findings.append(_finding(
                "false_pass_transcript_converted", case_id,
                "original-language TXT was converted to PDF or left unknown"))
        if actual.get("mime_type") != "text/plain":
            findings.append(_finding(
                "false_pass_transcript_converted", case_id,
                "transcript mime_type is not text/plain"))
        if actual.get("source_sha256_changed") is not False:
            findings.append(_finding(
                "false_pass_transcript_converted", case_id,
                "transcript original SHA changed or was not checked"))

    # -- model accounting per case ----------------------------------------
    posts = case["model"].get("posts")
    if type(posts) is not int or posts < 0:
        findings.append(_finding("false_pass_second_run_new_post", case_id,
                                 "case model POST count is not a nonnegative integer"))

    # -- cleanup -----------------------------------------------------------
    if case["cleanup"].get("restored") is not True:
        findings.append(_finding(
            "false_pass_case_scratch_not_restored", case_id,
            "case scratch was not restored", outcome=STATUS_PARTIAL))


def _check_skip_case_did_not_post(case: dict, findings: list[Finding]) -> None:
    """A skipped document must not have cost a model call."""
    case_id = case["case_id"]
    try:
        spec = specs.spec_by_id(case_id)
    except KeyError:
        return
    if spec.expectation != specs.EXPECT_SKIP:
        return
    if case["status"] != STATUS_PASS:
        return
    if case["model"].get("posts") not in (0, None):
        findings.append(_finding(
            "false_pass_skip_case_model_call", case_id,
            "skip case issued a model POST"))


# --------------------------------------------------------------------------
# global checks
# --------------------------------------------------------------------------


def _check_coverage(record: dict, findings: list[Finding]) -> tuple[str, ...]:
    cases = record["cases"]
    reported = tuple(case["case_id"] for case in cases)
    required = specs.required_case_ids()

    if not cases:
        findings.append(_finding("false_pass_empty_case_set", None,
                                 "no case was actually executed"))
        return reported

    missing = [case_id for case_id in required if case_id not in reported]
    if missing:
        findings.append(_finding(
            "false_pass_required_case_missing", None,
            "required cases never ran: " + ", ".join(missing)))

    unknown = [case_id for case_id in reported if case_id not in required]
    if unknown:
        findings.append(_finding(
            "false_pass_unknown_case", None,
            "unrequested cases inflate coverage: " + ", ".join(unknown)))

    present = set(reported)
    for group, ids in specs.CASE_GROUPS.items():
        if any(case_id not in present for case_id in ids):
            findings.append(_finding(
                "false_pass_required_group_missing", group,
                f"group {group} is not fully covered"))

    declared = record["coverage"]
    if list(declared.get("required_case_ids") or []) != list(required):
        findings.append(_finding(
            "false_pass_fixed_expectation_mutated", None,
            "coverage.required_case_ids differs from the fixed CaseSpec matrix"))
    if sorted(declared.get("executed_case_ids") or []) != sorted(reported):
        findings.append(_finding(
            "false_pass_coverage_mismatch", None,
            "coverage.executed_case_ids differs from the actual cases"))
    if list(declared.get("missing_case_ids") or []) != missing:
        findings.append(_finding(
            "false_pass_coverage_mismatch", None,
            "coverage.missing_case_ids differs from the actual gaps"))
    return reported


def _check_formats(record: dict, findings: list[Finding]) -> None:
    present = {case["case_id"] for case in record["cases"]}
    exercised = {
        spec.mime_type for spec in specs.case_specs() if spec.case_id in present
    }
    if not set(specs.REQUIRED_FORMATS) <= exercised:
        findings.append(_finding(
            "false_pass_format_coverage_missing", None,
            "one batch must exercise at least these container formats: "
            + ", ".join(specs.REQUIRED_FORMATS)))


def _check_model_accounting(record: dict, findings: list[Finding]) -> None:
    accounting = record["model_accounting"]
    runs = {run["run_index"]: run for run in record["runs"]}
    reuse = runs.get(_REUSE_RUN_INDEX)
    if reuse is None:
        findings.append(_finding("false_pass_second_run_new_post", None,
                                 "the reuse run was not recorded"))
    elif reuse["model_posts"] != 0:
        findings.append(_finding(
            "false_pass_second_run_new_post", None,
            f"reuse run issued {reuse['model_posts']} new model POST(s); "
            "identical version/spec must not re-post"))

    declared_run2 = accounting["run2_posts"]
    if reuse is not None and declared_run2 != reuse["model_posts"]:
        findings.append(_finding("false_pass_second_run_new_post", None,
                                 "model_accounting.run2_posts differs from the run"))
    first = runs.get(1)
    if first is not None and accounting["run1_posts"] != first["model_posts"]:
        findings.append(_finding("false_pass_coverage_mismatch", None,
                                 "model_accounting.run1_posts differs from the run"))
    total = sum(run["model_posts"] for run in record["runs"])
    if accounting["total_posts"] != total:
        findings.append(_finding("false_pass_coverage_mismatch", None,
                                 "model_accounting.total_posts is not the run sum"))
    if accounting["llm_calls"] < accounting["total_posts"]:
        findings.append(_finding("false_pass_coverage_mismatch", None,
                                 "llm_calls cannot be below actual model POSTs"))


def _check_scope(record: dict, findings: list[Finding]) -> None:
    scope = record["scope"]
    if scope.get("supplier_fixture") is not True:
        findings.append(_finding("false_pass_scope_overclaim", None,
                                 "fixture provenance not declared"))
    if scope.get("llm_semantic_quality") != "not_evaluated":
        findings.append(_finding(
            "false_pass_scope_overclaim", None,
            "synthetic fixtures cannot claim evaluated model semantic quality"))
    if not isinstance(scope.get("source_truth_verified"), str) or not scope[
        "source_truth_verified"
    ]:
        findings.append(_finding("false_pass_scope_overclaim", None,
                                 "source truth scope is not described"))
    if "synthetic" not in str(scope.get("source_truth_verified", "")).lower():
        findings.append(_finding(
            "false_pass_scope_overclaim", None,
            "source truth scope must state that the originals are synthetic"))
    if scope.get("paid_calls") != 0:
        findings.append(_finding("offline_violation", None,
                                 "this package must make zero paid calls"))
    accounting = record["model_accounting"]
    if accounting["provider_calls"] != 0 or accounting["paid_usd"] != 0:
        findings.append(_finding("offline_violation", None,
                                 "provider calls / paid usage must be zero"))


def _check_fixture_truth(record: dict, findings: list[Finding]) -> None:
    declared = record["case_specs"]
    if not isinstance(declared, list):
        return
    truth = {spec.case_id: spec.to_dict() for spec in specs.case_specs()}
    if len(declared) != len(truth) or {
        item.get("case_id") for item in declared if isinstance(item, dict)
    } != set(truth):
        findings.append(_finding(
            "false_pass_fixture_truth_rewritten", None,
            "declared case_specs do not cover the fixed matrix"))
        return
    for item in declared:
        expected = truth[item["case_id"]]
        if item != expected:
            findings.append(_finding(
                "false_pass_fixture_truth_rewritten", item["case_id"],
                "declared CaseSpec was rewritten"))


def _check_rf_consumption(record: dict, findings: list[Finding]) -> None:
    rf = record["rf_consumption"]
    if rf.get("read_ok") is not True:
        findings.append(_finding(
            "rf_read_not_verified", None,
            "the fixed RF reader did not verify a public read",
            outcome=STATUS_PARTIAL))
    for key, code in (("period_preserved", "rf_period_lost"),
                      ("language_preserved", "rf_language_lost")):
        if rf.get(key) is not True:
            findings.append(_finding(code, None,
                                     f"RF consumption did not preserve {key}",
                                     outcome=STATUS_PARTIAL))
    if not isinstance(rf.get("consumer"), str) or not rf["consumer"]:
        findings.append(_finding("rf_read_not_verified", None,
                                 "RF consumer entry point not recorded",
                                 outcome=STATUS_PARTIAL))


def _check_cleanup(record: dict, findings: list[Finding]) -> None:
    cleanup = record["cleanup"]
    if cleanup.get("deleted_within_owned") is not True:
        findings.append(_finding("false_pass_cleanup_out_of_scope", None,
                                 "cleanup deleted outside the owned root"))
    if cleanup.get("remaining"):
        findings.append(_finding(
            "false_pass_scratch_remaining", None,
            "scratch remains after the run: "
            + ", ".join(str(item) for item in cleanup["remaining"]),
            outcome=STATUS_PARTIAL))
    if cleanup.get("restored") is not True:
        findings.append(_finding(
            "false_pass_scratch_not_restored", None,
            "owned root was not restored to its baseline",
            outcome=STATUS_PARTIAL))
    if cleanup.get("baseline") != cleanup.get("after"):
        findings.append(_finding(
            "false_pass_lost_sentinel", None,
            "baseline sentinels changed or disappeared",
            outcome=STATUS_PARTIAL))


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------


def _evaluate_run(record: dict) -> OracleVerdict:
    problem = _validate_structure(record)
    if problem is not None:
        return _invalid(problem)

    findings: list[Finding] = []
    statuses: dict[str, str] = {}

    _check_coverage(record, findings)
    _check_formats(record, findings)
    _check_model_accounting(record, findings)
    _check_scope(record, findings)
    _check_fixture_truth(record, findings)
    _check_rf_consumption(record, findings)
    _check_cleanup(record, findings)
    if record["run_plan"].get("root_observation_contract") == "root-w08-observations/1":
        for case in record["cases"]:
            observed = case["evidence"].get("observations") or {}
            if case["status"] == STATUS_PASS and (case["model"].get("observed_from") !=
                    "loopback_request_source_id" or not all(observed.get(key) is True
                    for key in ("required_fact_present", "summary_supported", "period_preserved"))):
                findings.append(_finding("unproved_actual_observation", case["case_id"],
                                         "missing actual source request/fact/citation/period proof"))
        if sum(case["model"].get("posts", 0) for case in record["cases"]) != record["model_accounting"]["run1_posts"] or record["model_accounting"].get("stub_errors"):
            findings.append(_finding("source_post_count_mismatch", None,
                                     "per-source actual POSTs do not reconcile with first run"))
        invalidation = record.get("invalidation") or []
        if {item.get("kind") for item in invalidation} != {"source-version", "model-spec"} or any(
                item.get("status") != STATUS_PASS or item.get("model_posts") != 1 or
                item.get("pin_changed") is not True or item.get("original_unchanged") is not True
                for item in invalidation):
            findings.append(_finding("generation_invalidation_not_executed", None,
                                     "source version and generation spec need actual fresh execution"))


    for case in record["cases"]:
        statuses[case["case_id"]] = case["status"]
        if case["status"] == STATUS_PASS:
            # Strict evidence checks police PASS claims.  An accurate
            # PARTIAL/UNKNOWN/NOT_RUN report is honest reporting, not a
            # false pass.
            _check_case(case, record, findings)
            _check_skip_case_did_not_post(case, findings)
        if case["status"] == STATUS_NOT_RUN:
            findings.append(_finding(
                "not_run_case", case["case_id"],
                "case was not actually executed", outcome=STATUS_FAIL))

    for case in record["cases"]:
        if case["status"] == STATUS_PASS and case["failure"] is not None:
            findings.append(_finding(
                "false_pass_unreported_product_failure", case["case_id"],
                "failure is present on a PASS claim"))

    return _aggregate_verdict(statuses, findings)


_OUTCOME_PRIORITY = {
    STATUS_PASS: 0,
    STATUS_PARTIAL: 1,
    STATUS_UNKNOWN: 2,
    STATUS_NOT_RUN: 3,
    STATUS_FAIL: 4,
    STATUS_INVALID: 5,
}


def _aggregate_verdict(statuses: dict[str, str],
                       findings: list[Finding]) -> OracleVerdict:
    """A shared monotonic outcome rule; no field, case or code whitelist."""
    projected = dict(statuses)
    candidates = list(projected.values())
    for finding in findings:
        if finding.outcome is None:
            continue
        if finding.outcome not in _OUTCOME_PRIORITY:
            raise ValueError("unknown finding outcome")
        candidates.append(finding.outcome)
        if finding.case_id in projected:
            current = projected[finding.case_id]
            projected[finding.case_id] = max(
                (current, finding.outcome), key=_OUTCOME_PRIORITY.__getitem__
            )
    overall = max(candidates, key=_OUTCOME_PRIORITY.__getitem__, default=STATUS_PASS)
    return OracleVerdict(projected, tuple(findings), overall)


def evaluate_run(record: dict) -> OracleVerdict:
    """Malformed nested JSON is tooling INVALID_RECORD, never a runtime crash."""
    try:
        return _evaluate_run(copy.deepcopy(record))
    except (AttributeError, TypeError, KeyError, IndexError, ValueError) as exc:
        return _invalid(f"malformed nested evidence: {type(exc).__name__}")


__all__ = [
    "SCHEMA_VERSION",
    "STATUS_PASS", "STATUS_PARTIAL", "STATUS_FAIL", "STATUS_UNKNOWN",
    "STATUS_NOT_RUN", "STATUS_INVALID",
    "Finding", "OracleVerdict", "evaluate_run",
]
