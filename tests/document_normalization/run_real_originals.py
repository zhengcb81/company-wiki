"""Read-only harness entry for normalizing real archived originals.

Usage::

    python -B tests/document_normalization/run_real_originals.py \
        --html <path-to-sec-html> --pptx <path-to-image-pptx> \
        [--html-sha256 <expected>] [--pptx-sha256 <expected>] \
        --output <small-report.json>

Every input is read once, hashed, and parsed strictly in memory; the report
records sizes, unit counts, coverage, opaque assets, media byte totals, and
elapsed seconds — never full document text or extracted images.  Exit code
is non-zero when an expected SHA does not match or a parse raises.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from company_wiki.document_normalization import (  # noqa: E402
    NormalizationLimits,
    normalize_document,
    replay_unit,
)

HTML_MIME = "text/html"
PPTX_MIME = (
    "application/vnd.openxmlformats-officedocument."
    "presentationml.presentation"
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _summarize(label: str, data: bytes, mime: str, expected_sha: str | None) -> dict:
    started = time.perf_counter()
    sha = _sha256(data)
    if expected_sha and sha != expected_sha:
        raise SystemExit(
            f"{label}: SHA mismatch — expected {expected_sha}, got {sha}"
        )
    document = normalize_document(
        data,
        source_id="urn:company-wiki:source:sha256:" + sha,
        source_sha256=sha,
        mime_type=mime,
        limits=NormalizationLimits(),
    )
    elapsed = time.perf_counter() - started
    structure = document.structure
    kinds: dict[str, int] = {}
    for unit in document.units:
        kinds[unit.unit_kind] = kinds.get(unit.unit_kind, 0) + 1
    # Replay one unit of each kind as an end-to-end identity check.
    replay_checks = []
    seen_kinds: set[str] = set()
    for unit in document.units:
        if unit.unit_kind in seen_kinds:
            continue
        seen_kinds.add(unit.unit_kind)
        replay_started = time.perf_counter()
        text = replay_unit(
            data, source_sha256=sha, unit=unit, limits=NormalizationLimits()
        )
        replay_checks.append(
            {
                "unit_kind": unit.unit_kind,
                "ok": text == unit.raw_text,
                "seconds": round(time.perf_counter() - replay_started, 3),
            }
        )
        if len(seen_kinds) >= 3:
            break
    media_bytes = sum(
        asset.byte_size or 0 for asset in document.opaque_assets
    )
    return {
        "label": label,
        "sha256": sha,
        "declared_expected_sha256": expected_sha,
        "byte_size": len(data),
        "format": document.format_name,
        "parser_name": document.parser_name,
        "parser_version": document.parser_version,
        "unit_count": len(document.units),
        "unit_kinds": kinds,
        "page_count": structure.page_count,
        "pages_read": structure.pages_read,
        "opaque_page_count": len(structure.opaque_pages),
        "line_count": structure.line_count,
        "coverage_complete": structure.coverage_complete,
        "error_count": len(structure.errors),
        "error_samples": list(structure.errors[:5]),
        "opaque_asset_count": len(document.opaque_assets),
        "opaque_asset_kinds": {
            kind: sum(1 for a in document.opaque_assets if a.asset_kind == kind)
            for kind in sorted({a.asset_kind for a in document.opaque_assets})
        },
        "media_total_bytes": media_bytes,
        "replay_checks": replay_checks,
        "normalize_seconds": round(elapsed, 3),
        "limits": {
            "max_source_bytes": NormalizationLimits().max_source_bytes,
            "max_units": NormalizationLimits().max_units,
            "max_media_bytes": NormalizationLimits().max_media_bytes,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path)
    parser.add_argument("--pptx", type=Path)
    parser.add_argument("--html-sha256")
    parser.add_argument("--pptx-sha256")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.html and not args.pptx:
        parser.error("at least one of --html / --pptx is required")

    report: dict[str, object] = {
        "schema_version": "cmrf-format-real-originals/1",
        "read_only": True,
        "documents": [],
    }
    for label, path, mime, expected in (
        ("html", args.html, HTML_MIME, args.html_sha256),
        ("pptx", args.pptx, PPTX_MIME, args.pptx_sha256),
    ):
        if path is None:
            continue
        data = path.read_bytes()
        report["documents"].append(_summarize(label, data, mime, expected))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
