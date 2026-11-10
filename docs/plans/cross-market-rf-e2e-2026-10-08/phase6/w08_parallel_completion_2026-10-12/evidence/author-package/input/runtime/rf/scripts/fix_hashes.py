"""Recompute and sync schema input-side hashes.

The schema input embeds a small hash ring. Only two layers are *computable*
from the input itself; the other two are opaque external fingerprints that must
be *copied* from the source capture, never recomputed:

  1. ``source.capture.receipt_sha256`` = ``canonical_sha256(capture without receipt_sha256)``
  2. ``claim.excerpt_sha256``           = ``text_sha256(excerpt)``           (stripped)
  3. ``claim.capture_receipt_sha256``   = its source capture's ``receipt_sha256`` (copy)
  4. ``claim.content_sha256``           = its source capture's ``snapshot_sha256`` (copy)

``snapshot_sha256`` is opaque (produced by the capture tool); this tool never
overwrites it. The canonical serialization is reused verbatim from
``contracts.evidence`` so recomputed hashes match the engine byte-for-byte.

CLI mirrors ``revenue_forecast.py``: positional input path, exit 0 on success /
exit 2 on expected error or detected drift in ``--check`` mode.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from contracts.evidence import ForecastInputError, canonical_sha256, text_sha256  # noqa: F401

_HEX64 = re.compile(r"[0-9a-f]{64}")


def _corrected_receipts(data: dict[str, Any]) -> dict[str, str]:
    """Map each source_id to the recomputed (correct) capture receipt hash."""
    receipts: dict[str, str] = {}
    for source in data.get("sources", []):
        if not isinstance(source, dict):
            continue
        capture = source.get("capture")
        if not isinstance(capture, dict):
            continue
        payload = {key: value for key, value in capture.items() if key != "receipt_sha256"}
        receipts[source.get("source_id")] = canonical_sha256(payload)
    return receipts


def _source_by_id(data: dict[str, Any]) -> dict[Any, dict[str, Any]]:
    return {
        source.get("source_id"): source
        for source in data.get("sources", [])
        if isinstance(source, dict)
    }


def _format_warnings(data: dict[str, Any]) -> list[str]:
    """Opaque snapshot hashes are not recomputed; only surface malformed ones."""
    warnings: list[str] = []
    for i, source in enumerate(data.get("sources", [])):
        capture = source.get("capture") if isinstance(source, dict) else None
        if isinstance(capture, dict):
            snapshot = capture.get("snapshot_sha256")
            if not (isinstance(snapshot, str) and _HEX64.fullmatch(snapshot)):
                warnings.append(f"sources[{i}].capture.snapshot_sha256 is not a 64-hex digest (opaque, left unchanged)")
    return warnings


def find_hash_drift(data: dict[str, Any]) -> list[dict[str, str]]:
    """Return one entry per input-side hash whose stored value != recomputed value."""
    drift: list[dict[str, str]] = []
    corrected_receipts = _corrected_receipts(data)

    for i, source in enumerate(data.get("sources", [])):
        capture = source.get("capture") if isinstance(source, dict) else None
        if not isinstance(capture, dict):
            continue
        expected = corrected_receipts.get(source.get("source_id"))
        if capture.get("receipt_sha256") != expected:
            drift.append({
                "path": f"sources[{i}].capture.receipt_sha256",
                "kind": "capture_receipt",
                "stored": str(capture.get("receipt_sha256")),
                "expected": str(expected),
            })

    source_by_id = _source_by_id(data)
    for i, claim in enumerate(data.get("evidence_claims", [])):
        if not isinstance(claim, dict):
            continue
        expected_excerpt = text_sha256(str(claim.get("excerpt", "")))
        if claim.get("excerpt_sha256") != expected_excerpt:
            drift.append({
                "path": f"evidence_claims[{i}].excerpt_sha256",
                "kind": "claim_excerpt",
                "stored": str(claim.get("excerpt_sha256")),
                "expected": expected_excerpt,
            })
        capture = source_by_id.get(claim.get("source_id"), {}).get("capture")
        if not isinstance(capture, dict):
            continue
        expected_receipt = corrected_receipts.get(claim.get("source_id"))
        if expected_receipt is not None and claim.get("capture_receipt_sha256") != expected_receipt:
            drift.append({
                "path": f"evidence_claims[{i}].capture_receipt_sha256",
                "kind": "claim_capture_receipt",
                "stored": str(claim.get("capture_receipt_sha256")),
                "expected": expected_receipt,
            })
        expected_snapshot = capture.get("snapshot_sha256")
        if claim.get("content_sha256") != expected_snapshot:
            drift.append({
                "path": f"evidence_claims[{i}].content_sha256",
                "kind": "claim_content",
                "stored": str(claim.get("content_sha256")),
                "expected": str(expected_snapshot),
            })
    return drift


def apply_hash_fixes(data: dict[str, Any]) -> list[str]:
    """Recompute and sync every drifting input-side hash in place; return changed paths."""
    changes: list[str] = []
    corrected_receipts = _corrected_receipts(data)

    for i, source in enumerate(data.get("sources", [])):
        capture = source.get("capture") if isinstance(source, dict) else None
        if not isinstance(capture, dict):
            continue
        expected = corrected_receipts.get(source.get("source_id"))
        if capture.get("receipt_sha256") != expected:
            capture["receipt_sha256"] = expected
            changes.append(f"sources[{i}].capture.receipt_sha256")

    source_by_id = _source_by_id(data)
    for i, claim in enumerate(data.get("evidence_claims", [])):
        if not isinstance(claim, dict):
            continue
        expected_excerpt = text_sha256(str(claim.get("excerpt", "")))
        if claim.get("excerpt_sha256") != expected_excerpt:
            claim["excerpt_sha256"] = expected_excerpt
            changes.append(f"evidence_claims[{i}].excerpt_sha256")
        capture = source_by_id.get(claim.get("source_id"), {}).get("capture")
        if not isinstance(capture, dict):
            continue
        expected_receipt = corrected_receipts.get(claim.get("source_id"))
        if expected_receipt is not None and claim.get("capture_receipt_sha256") != expected_receipt:
            claim["capture_receipt_sha256"] = expected_receipt
            changes.append(f"evidence_claims[{i}].capture_receipt_sha256")
        expected_snapshot = capture.get("snapshot_sha256")
        if claim.get("content_sha256") != expected_snapshot:
            claim["content_sha256"] = expected_snapshot
            changes.append(f"evidence_claims[{i}].content_sha256")
    return changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input", type=Path, help="input JSON path (see contracts.constants.FORECAST_SCHEMA_VERSION)")
    parser.add_argument("--output", type=Path, help="write fixed JSON here instead of in place")
    parser.add_argument("--check", action="store_true", help="report drift only, write nothing (exit 2 on drift)")
    parser.add_argument("--dry-run", action="store_true", help="print planned fixes, write nothing")
    args = parser.parse_args(argv)

    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ForecastInputError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    for warning in _format_warnings(data):
        print(f"warning: {warning}", file=sys.stderr)

    drift = find_hash_drift(data)

    if args.check:
        for entry in drift:
            print(f"drift: {entry['path']} ({entry['kind']}) expected {entry['expected']}")
        if drift:
            return 2
        print("ok: no hash drift")
        return 0

    if not drift:
        print("ok: no hash drift")
        return 0

    if args.dry_run:
        for entry in drift:
            print(f"would fix: {entry['path']} ({entry['kind']})")
        return 0

    for change in apply_hash_fixes(data):
        print(f"fixed: {change}")
    target = args.output if args.output else args.input
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
