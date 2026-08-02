#!/usr/bin/env python3
"""Derive Work Unit state from a candidate receipt and an independent review."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def derive_state(receipt_path: Path, review_path: Path | None = None) -> dict[str, Any]:
    receipt = load_object(receipt_path)
    receipt_hash = sha256_file(receipt_path)
    violations: list[str] = []
    if receipt.get("result") != "pass":
        violations.append("candidate receipt did not pass")
    if receipt.get("status") != "candidate":
        violations.append("candidate receipt status must be candidate")
    if not receipt.get("workspace_digest"):
        violations.append("candidate receipt lacks workspace digest")

    state = "rejected" if violations else "candidate"
    review_summary: dict[str, Any] = {"status": "missing"}
    if review_path is not None:
        review = load_object(review_path)
        review_summary = {
            "status": review.get("decision"),
            "reviewer": review.get("reviewer"),
            "independent": review.get("independent"),
        }
        if review.get("receipt_sha256") != receipt_hash:
            violations.append("review does not bind to this receipt SHA-256")
        if review.get("decision") != "approved":
            violations.append("review decision is not approved")
        if review.get("independent") is not True:
            violations.append("review is not marked independent")
        if not review.get("reviewer"):
            violations.append("reviewer identity is missing")
        state = "verified" if not violations else "rejected"

    return {
        "schema_version": 1,
        "work_unit": receipt.get("work_unit"),
        "derived_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "receipt_sha256": receipt_hash,
        "workspace_digest": receipt.get("workspace_digest"),
        "state": state,
        "violations": violations,
        "review": review_summary,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args()
    result = derive_state(args.receipt, args.review)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["state"] in {"candidate", "verified"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
