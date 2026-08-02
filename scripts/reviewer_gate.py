#!/usr/bin/env python3
"""Create an independent review decision bound to candidate and rerun receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def evaluate_review(
    candidate_receipt: dict[str, Any],
    rerun_receipt: dict[str, Any],
    candidate_sha256: str,
    rerun_sha256: str,
    reviewer_id: str,
    implementer_id: str,
) -> dict[str, Any]:
    findings: list[str] = []
    if not reviewer_id or reviewer_id == implementer_id:
        findings.append("reviewer must be non-empty and different from implementer")
    if candidate_receipt.get("result") != "pass" or candidate_receipt.get("status") != "candidate":
        findings.append("candidate receipt is not a passing candidate")
    if rerun_receipt.get("result") != "pass" or rerun_receipt.get("status") != "candidate":
        findings.append("independent rerun is not a passing candidate")
    if candidate_receipt.get("workspace_digest") != rerun_receipt.get("workspace_digest"):
        findings.append("workspace digest differs between candidate and rerun")
    if candidate_receipt.get("work_unit") != rerun_receipt.get("work_unit"):
        findings.append("work unit differs between candidate and rerun")
    return {
        "schema_version": 1,
        "work_unit": candidate_receipt.get("work_unit"),
        "receipt_sha256": candidate_sha256,
        "rerun_receipt_sha256": rerun_sha256,
        "reviewer": reviewer_id,
        "implementer": implementer_id,
        "independent": reviewer_id != implementer_id and bool(reviewer_id),
        "decision": "approved" if not findings else "rejected",
        "findings": findings,
        "reviewed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-receipt", type=Path, required=True)
    parser.add_argument("--rerun-receipt", type=Path, required=True)
    parser.add_argument("--reviewer-id", required=True)
    parser.add_argument("--implementer-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args()
    review = evaluate_review(
        load_object(args.candidate_receipt),
        load_object(args.rerun_receipt),
        sha256_file(args.candidate_receipt),
        sha256_file(args.rerun_receipt),
        args.reviewer_id,
        args.implementer_id,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(review, ensure_ascii=False, indent=2))
    return 0 if review["decision"] == "approved" else 2


if __name__ == "__main__":
    raise SystemExit(main())
