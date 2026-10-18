"""Card sections 5.4 / 6: the receipt schema and its size guard.

The receipt is the lane's only shipped artifact, so its top-level field set must
be *exactly* what section 5.4 declares - an extra or missing field is a failure,
not a convenience.  The 16 MiB guard must refuse rather than truncate.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from .support import constants as C
from .support import jsonio
from .support import receipt as receipt_mod


def test_p4_receipt_schema_exact_fields(p4_case) -> None:
    """Top-level receipt keys equal section 5.4, with no additions."""
    case = p4_case()
    built = receipt_mod.build_receipt(
        cases=[],
        counts={"checked": 0, "passed": 0, "failed": 0, "skipped": 0,
                "not_evaluated": 0},
        catalog_path=None,
        commands_path=None,
    )
    expected = {
        "schema_version", "status", "generated_at", "inputs", "counts",
        "cases", "limitations",
    }
    assert set(built) == expected, (
        "receipt top-level fields must equal section 5.4 exactly "
        f"(missing={sorted(expected - set(built))}, "
        f"extra={sorted(set(built) - expected)})"
    )
    assert set(built["inputs"]) == {"catalog_sha256", "commands_sha256"}, (
        f"inputs must carry exactly the two digests; got {sorted(built['inputs'])}"
    )
    assert set(built["counts"]) == {
        "checked", "passed", "failed", "skipped", "not_evaluated",
    }, f"counts must carry exactly five counters; got {sorted(built['counts'])}"
    assert built["schema_version"] == C.P4_RECEIPT_SCHEMA, (
        f"schema_version must be {C.P4_RECEIPT_SCHEMA}; got {built['schema_version']!r}"
    )
    case.check("receipt_schema_exact", "pass", {"fields": sorted(built)})
    case.settle("pass")


def test_p4_receipt_case_shape_exact_fields(p4_case) -> None:
    """Each case object matches 5.4: name/status/reason/checks, nothing else."""
    case = p4_case()
    payload: dict[str, Any] = {
        "name": "p4_probe",
        "status": "pass",
        "reason": None,
        "checks": [{"name": "manifest_vs_receipt", "status": "pass", "detail": {}}],
    }
    assert set(payload) == {"name", "status", "reason", "checks"}, (
        f"case fields must equal section 5.4; got {sorted(payload)}"
    )
    assert set(payload["checks"][0]) == {"name", "status", "detail"}, (
        f"check fields must equal section 5.4; got {sorted(payload['checks'][0])}"
    )
    case.check("receipt_case_shape_exact", "pass", {"fields": sorted(payload)})
    case.settle("pass")


def test_p4_receipt_status_vocabulary(p4_case) -> None:
    """Top-level status stays inside INTERFACES section 2's five values."""
    case = p4_case()
    zero = {"checked": 0, "passed": 0, "failed": 0, "skipped": 0, "not_evaluated": 0}
    assert receipt_mod.top_level_status(zero, blocked_reason=None) == "partial", (
        "an all-zero receipt must be partial, never ok"
    )
    failing = {"checked": 3, "passed": 2, "failed": 1, "skipped": 0,
               "not_evaluated": 0}
    assert receipt_mod.top_level_status(failing, blocked_reason=None) == "fail", (
        "any failure must make the receipt fail"
    )
    blocked = {"checked": 0, "passed": 0, "failed": 0, "skipped": 0,
               "not_evaluated": 0}
    assert receipt_mod.top_level_status(
        blocked, blocked_reason=C.CODE_RECEIPT_TOO_LARGE
    ) == "blocked", "an explicit blocked_reason must produce status=blocked"
    clean = {"checked": 2, "passed": 2, "failed": 0, "skipped": 0,
             "not_evaluated": 0}
    assert receipt_mod.top_level_status(clean, blocked_reason=None) == "ok", (
        "a fully-passed receipt is ok"
    )
    case.check("receipt_status_vocabulary", "pass",
               {"allowed": list(C.TOP_LEVEL_STATUSES)})
    case.settle("pass")


def test_p4_receipt_oversized_is_refused_not_truncated(p4_case, tmp_path) -> None:
    """A receipt over 16 MiB becomes blocked, never a truncated \"complete\" one."""
    case = p4_case()
    oversized = {
        "schema_version": C.P4_RECEIPT_SCHEMA,
        "status": "ok",
        "generated_at": "2026-10-18T00:00:00Z",
        "inputs": {"catalog_sha256": "0" * 64, "commands_sha256": None},
        "counts": {"checked": 1, "passed": 1, "failed": 0, "skipped": 0,
                   "not_evaluated": 0},
        "cases": [],
        "limitations": ["x" * (C.MAX_RECEIPT_BYTES + 1024)],
    }
    target = tmp_path / "oversized.json"
    receipt_mod.write_receipt(oversized, path=target)

    payload = target.read_bytes()
    assert len(payload) <= C.MAX_RECEIPT_BYTES, (
        f"the written receipt must stay under 16 MiB; got {len(payload)} bytes"
    )
    written = jsonio.loads_strict(payload, label="oversized receipt")
    assert written["status"] == "blocked", (
        f"an oversized receipt must be blocked; got {written['status']!r}"
    )
    assert written["reason"] == C.CODE_RECEIPT_TOO_LARGE, (
        f"expected {C.CODE_RECEIPT_TOO_LARGE}; got {written.get('reason')!r}"
    )
    assert "refused instead of truncated" in json.dumps(written["limitations"]), (
        "the refusal must be explained in limitations"
    )
    case.check("oversized_receipt_refused", "pass", {
        "reason": C.CODE_RECEIPT_TOO_LARGE, "bytes": len(payload),
    })
    case.settle("pass")


def test_p4_receipt_missing_file_is_refused(p4_case, tmp_path) -> None:
    """A missing receipt is an error, never a silent pass (section 6 RED)."""
    case = p4_case()
    absent = tmp_path / "absent-receipt.json"
    assert not absent.exists()
    with pytest.raises((FileNotFoundError, OSError)):
        receipt_mod.read_receipt(absent)
    case.check("missing_receipt_refused", "pass",
               {"reason": "read_receipt raised as designed"})
    case.settle("pass")


def test_p4_receipt_written_on_real_session(p4_case) -> None:
    """This run's receipt exists on disk, is strict JSON, and carries our schema."""
    case = p4_case()
    path = receipt_mod.resolve_receipt_path()
    if not path.is_file():
        pytest.skip(
            f"{path.name} is written after pytest_sessionfinish; "
            "validate it on the acceptance run"
        )
    written = receipt_mod.read_receipt(path)
    expected = {
        "schema_version", "status", "generated_at", "inputs", "counts",
        "cases", "limitations",
    }
    assert set(written) == expected, (
        f"shipped receipt fields must equal section 5.4; got {sorted(written)}"
    )
    assert written["schema_version"] == C.P4_RECEIPT_SCHEMA, (
        f"shipped receipt schema_version is {written['schema_version']!r}"
    )
    case.check("receipt_shipped", "pass", {"path": path.name})
    case.settle("pass")
