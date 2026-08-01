"""CW-2.28 receipt contract tests (task_plan §12.2.9 = RED test T2-15).

These lock down the immutable attempt-receipt format before any Phase 2R product
code is written. The validator lives in ``tests/helpers/cw228_receipt.py`` and
the JSON Schema at ``docs/contracts/cw-2.28-receipt.schema.json``.

Each §12.2.9 negative case must be rejected; each positive case must pass.
"""

from __future__ import annotations

import json
import pathlib


from helpers.cw228_receipt import (
    ALL_STATUSES,
    load_schema,
    scan_secrets,
    validate_chain,
    validate_receipt,
    validate_receipt_rules,
    validate_receipt_shape,
)


# ---------------------------------------------------------------------
# Fixtures: a complete, well-formed receipt.
# ---------------------------------------------------------------------


def _valid_command(command_id: str = "cmd-1", exit_code: int = 0) -> dict:
    return {
        "command_id": command_id,
        "argv": ["python", "-m", "pytest", "-q", "tests/contract/test_x.py"],
        "cwd": "C:\\repo",
        "started_at": "2026-07-26T15:00:00Z",
        "completed_at": "2026-07-26T15:00:05Z",
        "exit_code": exit_code,
        "summary": "3 passed",
        "stdout_sha256": "a" * 64,
        "stderr_sha256": "b" * 64,
        "failed_tests": [],
        "skipped_tests": [],
        "xfailed_tests": [],
    }


def _valid_receipt(phase: int = 2, status: str = "PASS") -> dict:
    return {
        "schema_version": "1.0",
        "work_unit": "CW-2.28C",
        "phase": phase,
        "attempt_id": f"phase-{phase}-attempt-0001",
        "status": status,
        "started_at": "2026-07-26T15:00:00Z",
        "completed_at": "2026-07-26T15:30:00Z",
        "executor": "claude-code/glm-5.2",
        "project_root": "C:\\repo",
        "git_heads": {"company-wiki": "a571606"},
        "supersedes_receipt_sha256": None,
        "product_file_hashes_before": {"src/x.py": {"sha256": "c" * 64, "size": 100}},
        "product_file_hashes_after": {"src/x.py": {"sha256": "d" * 64, "size": 120}},
        "command_results": [_valid_command()],
        "invariant_results": [{"name": "raw_immutable", "passed": True, "detail": None}],
        "authorization_used": ["offline_phase_2"],
        "concurrent_change_detected": False,
        "network_used": False,
        "downloader_invocations": 0,
        "llm_invocations": 0,
        "files_created": [],
        "files_modified": [],
        "diff_allowlist_result": "PASS",
        "secret_scan_result": "0 active secrets",
        "errors": [],
        "blocker": None,
        "next_phase": "CW-2.28D",
    }


def _write_attempt(dir_path: pathlib.Path, receipt: dict) -> pathlib.Path:
    """Write a receipt to phase-{N}-attempt-{NNNN}.json matching its attempt_id."""
    name = f"phase-{receipt['phase']}-attempt-0001.json"
    # keep filename consistent with attempt_id suffix used here (0001)
    path = dir_path / name
    path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return path


def _write_index(
    dir_path: pathlib.Path, entries: dict[str, dict]
) -> pathlib.Path:
    path = dir_path / "receipt-index.json"
    path.write_text(
        json.dumps({"phases": entries}, indent=2), encoding="utf-8"
    )
    return path


# ---------------------------------------------------------------------
# Positive cases.
# ---------------------------------------------------------------------


def test_schema_file_is_loadable_json_schema():
    schema = load_schema()
    assert schema["title"] == "CW-2.28 phase attempt receipt"
    # status enum is exactly the §12.2.5 seven-value set.
    assert set(schema["properties"]["status"]["enum"]) == ALL_STATUSES


def test_valid_pass_receipt_is_accepted():
    assert validate_receipt(_valid_receipt(status="PASS")) == []


def test_valid_fail_receipt_with_nonzero_exit_is_accepted():
    """A FAIL receipt legitimately records a nonzero exit and failed tests."""
    receipt = _valid_receipt(status="FAIL")
    receipt["command_results"] = [_valid_command(exit_code=1)]
    receipt["command_results"][0]["failed_tests"] = ["test_x"]
    receipt["errors"] = ["1 test failed"]
    assert validate_receipt(receipt) == []


def test_valid_red_contract_pass_receipt_is_accepted():
    """A RED phase (§12.1.2) PASSes when its probe fails for the right reason.

    The command is marked red_contract=True, exits nonzero with expected failed
    tests, and the receipt carries the attesting invariant. This is the honest
    representation of a RED phase; it does not weaken case 3 because the marker
    is explicit and the invariant is required.
    """
    receipt = _valid_receipt(status="PASS")
    red_cmd = _valid_command(exit_code=1)
    red_cmd["command_id"] = "red-backfill-contract"
    red_cmd["red_contract"] = True
    red_cmd["failed_tests"] = [
        "test_backfill_unsupported_has_terminal_reason",
        "test_backfill_terminal_reason_distinguishes_empty_from_parse_failure",
        "test_backfill_cli_shows_eligible_pending_counts",
    ]
    red_cmd["xfailed_tests"] = [
        "test_parser_failure_does_not_block_next_document",
        "test_failed_documents_have_retryable_status",
        "test_worker_pause_interrupts_backfill_cleanly",
    ]
    red_cmd["summary"] = "3 failed + 3 xfailed + 3 passed (RED established for right reason)"
    receipt["command_results"] = [red_cmd]
    receipt["invariant_results"] = [
        {"name": "red_fails_for_right_reason", "passed": True, "detail": "no import/fixture/path errors"}
    ]
    assert validate_receipt(receipt) == []


def test_red_contract_without_attesting_invariant_is_rejected():
    """A red_contract command under PASS must have the attesting invariant."""
    receipt = _valid_receipt(status="PASS")
    red_cmd = _valid_command(exit_code=1)
    red_cmd["red_contract"] = True
    red_cmd["failed_tests"] = ["test_x"]
    receipt["command_results"] = [red_cmd]
    errors = validate_receipt_rules(receipt)
    assert any("red_fails_for_right_reason" in e for e in errors), errors


# ---------------------------------------------------------------------
# §12.2.9 negative cases — single-receipt shape/rules.
# ---------------------------------------------------------------------


def test_case1_missing_required_field_rejected():
    receipt = _valid_receipt()
    del receipt["attempt_id"]
    errors = validate_receipt_shape(receipt)
    assert any("attempt_id" in e for e in errors), errors


def test_case2_invalid_status_rejected():
    receipt = _valid_receipt()
    receipt["status"] = "SUCCESS"  # not in the enum
    errors = validate_receipt_shape(receipt)
    assert any("status" in e for e in errors), errors


def test_case3_nonzero_exit_with_pass_rejected():
    receipt = _valid_receipt(status="PASS")
    receipt["command_results"] = [_valid_command(exit_code=1)]
    # Shape is fine; the cross-field rule must catch the lie.
    assert validate_receipt_shape(receipt) == []
    errors = validate_receipt_rules(receipt)
    assert any("exit_code=1" in e for e in errors), errors


def test_case4_skip_or_xfail_with_pass_rejected():
    receipt = _valid_receipt(status="PASS")
    receipt["command_results"] = [
        _valid_command(exit_code=0),
    ]
    receipt["command_results"][0]["xfailed_tests"] = ["test_future_work"]
    errors = validate_receipt_rules(receipt)
    assert any("xfailed_tests" in e for e in errors), errors

    receipt2 = _valid_receipt(status="PASS")
    receipt2["command_results"][0]["skipped_tests"] = ["test_slow"]
    errors2 = validate_receipt_rules(receipt2)
    assert any("skipped_tests" in e for e in errors2), errors2


def test_case10_high_confidence_secret_rejected():
    receipt = _valid_receipt()
    receipt["executor"] = "key=AKIAIOSFODNN7EXAMPLE drop"
    errors = validate_receipt(receipt)
    assert any("secret" in e for e in errors), errors
    assert scan_secrets(receipt), "scan_secrets should surface the AKIA hit"


# ---------------------------------------------------------------------
# §12.2.9 negative cases — chain (phase ordering, index integrity).
# ---------------------------------------------------------------------


def test_chain_valid_two_phase_pass(tmp_path):
    p0 = _write_attempt(tmp_path, _valid_receipt(phase=0, status="PASS"))
    p1 = _write_attempt(tmp_path, _valid_receipt(phase=1, status="PASS"))
    from helpers.cw228_receipt import sha256_file

    _write_index(
        tmp_path,
        {
            "phase-0": {"path": p0.name, "sha256": sha256_file(p0)},
            "phase-1": {"path": p1.name, "sha256": sha256_file(p1)},
        },
    )
    assert validate_chain(tmp_path) == [], validate_chain(tmp_path)


def test_case5_phase_order_jump_rejected(tmp_path):
    """phase 2 PASS present, phase 1 absent → must fail the previous-PASS gate."""
    _write_attempt(tmp_path, _valid_receipt(phase=2, status="PASS"))
    _write_index(tmp_path, {})
    errors = validate_chain(tmp_path)
    assert any("phase 1 has no PASS attempt" in e for e in errors), errors


def test_case6_previous_receipt_not_pass_rejected(tmp_path):
    """phase 0 PASS, phase 1 FAIL, phase 2 PASS → phase 2 must be rejected."""
    _write_attempt(tmp_path, _valid_receipt(phase=0, status="PASS"))
    fail1 = _valid_receipt(phase=1, status="FAIL")
    fail1["command_results"] = [_valid_command(exit_code=1)]
    fail1["command_results"][0]["failed_tests"] = ["t"]
    _write_attempt(tmp_path, fail1)
    _write_attempt(tmp_path, _valid_receipt(phase=2, status="PASS"))
    _write_index(tmp_path, {})
    errors = validate_chain(tmp_path)
    assert any("phase 1 has no PASS attempt" in e for e in errors), errors


def test_case7_index_sha_mismatch_rejected(tmp_path):
    p0 = _write_attempt(tmp_path, _valid_receipt(phase=0, status="PASS"))
    _write_index(
        tmp_path,
        {"phase-0": {"path": p0.name, "sha256": "0" * 64}},
    )
    errors = validate_chain(tmp_path)
    assert any("sha256 mismatch" in e for e in errors), errors


def test_case8_index_points_to_missing_file_rejected(tmp_path):
    _write_attempt(tmp_path, _valid_receipt(phase=0, status="PASS"))
    _write_index(
        tmp_path,
        {"phase-1": {"path": "phase-1-attempt-0001.json", "sha256": "f" * 64}},
    )
    errors = validate_chain(tmp_path)
    assert any("does not exist" in e for e in errors), errors


def test_case9_legacy_receipt_cannot_be_indexed_as_attempt(tmp_path):
    """A legacy phase-N-receipt.json must not appear in the index."""
    _write_attempt(tmp_path, _valid_receipt(phase=0, status="PASS"))
    legacy = tmp_path / "phase-1-receipt.json"
    legacy.write_text(json.dumps(_valid_receipt(phase=1, status="PASS")), encoding="utf-8")
    _write_index(
        tmp_path,
        {"phase-1": {"path": legacy.name, "sha256": "ab"}},
    )
    errors = validate_chain(tmp_path)
    assert any("non-attempt file" in e for e in errors), errors


def test_index_missing_is_reported(tmp_path):
    _write_attempt(tmp_path, _valid_receipt(phase=0, status="PASS"))
    errors = validate_chain(tmp_path)
    assert any("receipt-index.json missing" in e for e in errors), errors
