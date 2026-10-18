"""``p4-contract-receipt/1`` writer (card 5.4).

The receipt is assembled after ``pytest_sessionfinish`` from the ledger, then
written to the fixed path.  ``counts`` always reflects the real pytest summary;
a receipt over 16 MiB becomes ``blocked`` with ``reason="receipt_too_large"``
rather than being truncated as if complete.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import constants as C
from .jsonio import JsonRejected, load_strict_file, sha256_file


CASE_STATUS_TO_COUNT = {
    "pass": "passed",
    "fail": "failed",
    "skip": "skipped",
    "not_evaluated": "not_evaluated",
}


def utc_now() -> str:
    """UTC ISO-8601, second precision, ``Z`` - one time source for the receipt."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def counts_from_cases(cases: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "checked": 0, "passed": 0, "failed": 0, "skipped": 0, "not_evaluated": 0,
    }
    for case in cases:
        status = case.get("status")
        if status in {"pass", "fail"}:
            counts["checked"] += 1
        key = CASE_STATUS_TO_COUNT.get(str(status))
        if key is not None:
            counts[key] += 1
    return counts


def counts_from_pytest(summary: dict[str, int]) -> dict[str, int]:
    """Map pytest's own counters onto the receipt's five counters."""
    passed = int(summary.get("passed", 0))
    failed = int(summary.get("failed", 0)) + int(summary.get("error", 0))
    skipped = int(summary.get("skipped", 0))
    not_evaluated = int(summary.get("not_evaluated", 0))
    return {
        "checked": passed + failed,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "not_evaluated": not_evaluated,
    }


def top_level_status(counts: dict[str, int], *, blocked_reason: str | None) -> str:
    if blocked_reason is not None:
        return "blocked"
    if counts["failed"]:
        return "fail"
    if counts["checked"] == 0:
        return "partial"
    if counts["skipped"] or counts["not_evaluated"]:
        return "partial"
    return "ok"


def resolve_receipt_path() -> Path:
    """The card's fixed receipt path (card section 5.4); no override exists."""
    return C.RECEIPT_PATH


def input_digests(catalog_path: Path | None, commands_path: Path | None) -> dict[str, Any]:
    """Only digests enter the receipt; never an environment value or a path."""
    return {
        "catalog_sha256": (
            sha256_file(catalog_path) if catalog_path and catalog_path.is_file()
            else None
        ),
        "commands_sha256": (
            sha256_file(commands_path) if commands_path and commands_path.is_file()
            else None
        ),
    }


def build_receipt(
    *,
    cases: list[dict[str, Any]],
    counts: dict[str, int],
    catalog_path: Path | None,
    commands_path: Path | None,
    limitations: list[str] | None = None,
    blocked_reason: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": C.P4_RECEIPT_SCHEMA,
        "status": top_level_status(counts, blocked_reason=blocked_reason),
        "generated_at": generated_at or utc_now(),
        "inputs": input_digests(catalog_path, commands_path),
        "counts": counts,
        "cases": cases,
        "limitations": list(limitations or C.LIMITATIONS),
    }


def write_receipt(receipt: dict[str, Any], path: Path | None = None) -> Path:
    target = path or resolve_receipt_path()
    payload = (
        json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    if len(payload) > C.MAX_RECEIPT_BYTES:
        payload = (
            json.dumps(
                {
                    "schema_version": C.P4_RECEIPT_SCHEMA,
                    "status": "blocked",
                    "generated_at": receipt.get("generated_at") or utc_now(),
                    "inputs": receipt.get("inputs", {}),
                    "counts": receipt.get("counts", {}),
                    "cases": [],
                    "limitations": [
                        "receipt exceeded 16 MiB; refused instead of truncated"
                    ],
                    "reason": C.CODE_RECEIPT_TOO_LARGE,
                },
                ensure_ascii=False, sort_keys=True, indent=2,
            ) + "\n"
        ).encode("utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return target


def read_receipt(path: Path) -> dict[str, Any]:
    payload = load_strict_file(path, limit=C.MAX_RECEIPT_BYTES, label="receipt")
    if not isinstance(payload, dict):
        raise JsonRejected(C.CODE_INVALID_JSON, "receipt is not an object")
    return payload
