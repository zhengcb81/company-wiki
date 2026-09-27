"""Read-only G1 sample runner for selective narrative evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLAN_ROOT = PROJECT_ROOT / "docs" / "plans" / "narrative-evidence-pilot-2026-09-26"
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from company_wiki.source_catalog.narrative_evidence import (  # noqa: E402
    NARRATIVE_PARSER_NAME,
    NARRATIVE_PARSER_VERSION,
    NARRATIVE_SELECTOR_NAME,
    NARRATIVE_SELECTOR_VERSION,
    parse_pdf,
    parse_transcript_text,
    select_narrative_evidence,
    verify_pdf_evidence_spans,
    verify_transcript_evidence_spans,
)
from company_wiki.source_catalog.narrative_retrieval import (  # noqa: E402
    NARRATIVE_EVIDENCE_BUNDLE_SCHEMA_VERSION,
)
from company_wiki.source_contract import source_id_for_sha256  # noqa: E402


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _measure_json_file_bytes(serialized: bytes, *, temp_root: Path | None = None) -> int:
    """Write the exact per-source package to scratch storage and measure it."""
    temp_options = {"prefix": "cw-narrative-package-measure-"}
    if temp_root is not None:
        temp_root.mkdir(parents=True, exist_ok=True)
        temp_options["dir"] = str(temp_root.resolve(strict=True))
    with tempfile.TemporaryDirectory(**temp_options) as directory:
        path = Path(directory) / "summary-input.json"
        with path.open("xb") as stream:
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        measured = path.stat().st_size
        if measured != len(serialized):
            raise OSError("temporary summary package length differs from serialized bytes")
        return measured


def _resolve_sample(sample: dict, company_root: Path, transcript_root: Path) -> Path:
    root = transcript_root if sample["language"] == "en" else company_root
    path = (root / sample["path"]).resolve(strict=True)
    if not path.is_relative_to(root.resolve(strict=True)):
        raise ValueError(f"sample path escapes its read-only root: {sample['id']}")
    return path


def _normalized_anchor(value: str) -> str:
    return re.sub(r"\s+", "", value).casefold()


def _anchor_evidence_ids(spans: list, term: str) -> tuple[str, ...]:
    """Return the narrowest selected span window containing an anchor term.

    A page/role-level match remains useful for recall, but it is not a precise
    citation. This helper maps a matched anchor to the smallest contiguous
    selected evidence window, or returns no IDs when the parser selected the
    page but not the anchor-bearing text.
    """
    needle = _normalized_anchor(term)
    if not needle:
        return ()

    def position(span: object) -> tuple[int, ...]:
        coordinates = span.coordinates
        return (
            coordinates.page_number or 0,
            coordinates.paragraph_index or 0,
            coordinates.table_index or 0,
            coordinates.row_index or 0,
            coordinates.column_index or 0,
            coordinates.char_start or 0,
        )

    ordered = sorted(spans, key=position)
    texts = [_normalized_anchor(span.raw_text or "") for span in ordered]
    direct = [
        span.span_id
        for span, text in zip(ordered, texts, strict=True)
        if needle in text
    ]
    if direct:
        return (direct[0],)

    best: tuple[int, int] | None = None
    for start in range(len(ordered)):
        combined = ""
        for end in range(start, len(ordered)):
            combined += texts[end]
            if needle in combined:
                candidate = (start, end)
                if best is None or end - start < best[1] - best[0]:
                    best = candidate
                break
    if best is None:
        return ()
    return tuple(ordered[index].span_id for index in range(best[0], best[1] + 1))


def _one_sample(
    sample: dict,
    path: Path,
    *,
    temp_root: Path | None = None,
    collect_package: bool = False,
) -> dict:
    started = time.perf_counter()
    source_sha = _sha256(path)
    expected_prefix = sample["sha256_prefix"]
    if not source_sha.startswith(expected_prefix):
        raise ValueError(
            f"sample hash changed for {sample['id']}: expected {expected_prefix}, got {source_sha[:12]}"
        )
    source_id = source_id_for_sha256(source_sha)
    if sample["language"] == "en":
        raw = path.read_bytes().decode("utf-8-sig", errors="strict")
        parsed = parse_transcript_text(
            raw,
            source_id=source_id,
            source_sha256=source_sha,
            language="en",
        )
    else:
        raw = None
        parsed = parse_pdf(
            path,
            source_id=source_id,
            source_sha256=source_sha,
            full_table_scan=bool(sample.get("full_table_scan", False)),
            table_pages=sample.get("table_pages"),
        )

    package = select_narrative_evidence(
        parsed,
        title=sample["title"],
        existing_kind=sample["existing_kind"],
    )
    if sample["language"] == "en":
        verified_ids, failed_ids = verify_transcript_evidence_spans(
            raw or "",
            source_id=source_id,
            source_sha256=source_sha,
            evidence_spans=package.evidence_spans,
            language=sample["language"],
        )
    else:
        verified_ids, failed_ids = verify_pdf_evidence_spans(
            path,
            source_id=source_id,
            source_sha256=source_sha,
            evidence_spans=package.evidence_spans,
        )
    wire = package.summary_input()
    serialized_package = json.dumps(
        wire,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    package_bytes = len(serialized_package)
    persisted_package_bytes = _measure_json_file_bytes(
        serialized_package,
        temp_root=temp_root,
    )
    if persisted_package_bytes != package_bytes:
        raise OSError("persisted summary package does not match in-memory serialization")
    selected = []
    selected_pages = sorted(
        {
            span.coordinates.page_number
            for span in package.evidence_spans
            if span.coordinates.page_number is not None
        }
    )
    focus_pages = sorted(int(page) for page in sample.get("table_pages", []))
    for span in package.evidence_spans:
        selected.append(
            {
                "span_id": span.span_id,
                "locator_v1": span.locator,
                "coordinates": {
                    "page_number": span.coordinates.page_number,
                    "paragraph_index": span.coordinates.paragraph_index,
                    "table_index": span.coordinates.table_index,
                    "row_index": span.coordinates.row_index,
                    "column_index": span.coordinates.column_index,
                    "char_start": span.coordinates.char_start,
                    "char_end": span.coordinates.char_end,
                },
                "quality_flags": list(span.quality_flags),
                "topics": span.structured_value.get("topics", []),
                "selection_reasons": span.structured_value.get("selection_reasons", []),
                "source_role": span.structured_value.get("source_role", "unknown"),
                "qa_group_id": span.structured_value.get("qa_group_id"),
                "selection_group_id": span.structured_value.get("selection_group_id"),
                "excerpt": (span.raw_text or "")[:240],
            }
        )
    anchor_results = []
    for check in sample.get("anchor_checks", ()):
        page_number = check.get("page_number")
        source_role = check.get("source_role")
        matching_spans = [
            span
            for span in package.evidence_spans
            if (page_number is None or span.coordinates.page_number == int(page_number))
            and (source_role is None or span.structured_value.get("source_role") == source_role)
        ]
        compact_text = "".join(
            re.sub(r"\s+", "", span.raw_text or "") for span in matching_spans
        ).casefold()
        matched_term = next(
            (
                term
                for term in check.get("any_of", ())
                if re.sub(r"\s+", "", str(term)).casefold() in compact_text
            ),
            None,
        )
        anchor_results.append(
            {
                "check_id": check["id"],
                "page_number": page_number,
                "source_role": source_role,
                "passed": matched_term is not None,
                "matched_term": matched_term,
                "required_any": list(check.get("any_of", ())),
                "matched_evidence_ids": (
                    list(_anchor_evidence_ids(matching_spans, matched_term))
                    if matched_term is not None
                    else []
                ),
                "match_scope": (
                    "selected_span_window"
                    if matched_term is not None
                    and _anchor_evidence_ids(matching_spans, matched_term)
                    else "page_or_role_context_only"
                ),
                "evidence_ids": [span.span_id for span in matching_spans],
            }
        )
    result = {
        "sample_id": sample["id"],
        "title": sample["title"],
        "source_sha256": source_sha,
        "source_file_bytes": path.stat().st_size,
        "document_kind": package.document_kind,
        "status": package.status,
        "selection_limit": package.selection_limit,
        "coverage_complete": package.coverage_complete,
        "page_count": parsed.page_count,
        "pages_read": parsed.pages_read,
        "opaque_pages": list(parsed.opaque_pages),
        "table_scan_page_count": len(parsed.table_scan_pages),
        "deferred_table_pages": list(parsed.deferred_table_pages),
        "focus_pages": focus_pages,
        "selected_focus_pages": sorted(set(focus_pages) & set(selected_pages)),
        "line_count": parsed.line_count,
        "parse_errors": list(parsed.errors),
        "source_units": package.source_units,
        "candidate_count": package.candidate_count,
        "selected_span_count": len(package.evidence_spans),
        "locator_roundtrip_verified_count": len(verified_ids),
        "locator_roundtrip_failed_count": len(failed_ids),
        "locator_roundtrip_failed_span_ids": list(failed_ids),
        "dropped_financial_count": package.dropped_financial_count,
        "omitted_candidate_count": package.omitted_candidate_count,
        "selected_text_bytes": package.selected_text_bytes,
        "summary_input_bytes": package_bytes,
        "summary_input_file_bytes": persisted_package_bytes,
        "summary_input_to_source_ratio": round(package_bytes / max(1, path.stat().st_size), 6),
        "anchor_checks": anchor_results,
        "anchor_check_failure_count": sum(not item["passed"] for item in anchor_results),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "selected_evidence_preview": selected,
    }
    if collect_package:
        suffix = Path(sample["path"]).suffix.casefold()
        if suffix == ".pdf":
            source_format = "pdf"
            parser_options = {
                "full_table_scan": bool(sample.get("full_table_scan", False)),
                "table_pages": (
                    None
                    if sample.get("table_pages") is None
                    else list(sample["table_pages"])
                ),
            }
        elif suffix == ".txt":
            source_format = "transcript_txt"
            parser_options = {}
        else:
            raise ValueError(f"unsupported replay format for {sample['id']}: {suffix}")
        representative_span = package.evidence_spans[0] if package.evidence_spans else None
        result["_package_record"] = {
            "sample_id": sample["id"],
            "title": sample["title"],
            "selection_status": package.status,
            "coverage_complete": package.coverage_complete,
            "source_file_bytes": path.stat().st_size,
            "selected_text_bytes": package.selected_text_bytes,
            "replay_contract": {
                "schema_version": "narrative-evidence-replay/0.1.0",
                "source_format": source_format,
                "language": sample["language"],
                "existing_kind": sample["existing_kind"],
                "parser_name": (
                    representative_span.parser_name
                    if representative_span is not None
                    else NARRATIVE_PARSER_NAME
                ),
                "parser_version": (
                    representative_span.parser_version
                    if representative_span is not None
                    else NARRATIVE_PARSER_VERSION
                ),
                "parser_options": parser_options,
                "selector_name": NARRATIVE_SELECTOR_NAME,
                "selector_version": NARRATIVE_SELECTOR_VERSION,
                "max_selected": package.selection_limit,
            },
            "summary_input": wire,
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--company-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument(
        "--transcript-root",
        type=Path,
        default=PROJECT_ROOT.parent / "earnings-transcripts" / "earnings-transcripts" / "transcripts",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
    )
    parser.add_argument(
        "--run-root",
        type=Path,
        help="Isolated test root; inputs, outputs, and scratch files must stay beneath it.",
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--package-output",
        type=Path,
        default=None,
        help="Optional selected-evidence bundle; allowed only beneath --run-root.",
    )
    parser.add_argument("--sample-id", action="append", default=[])
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    run_root = None
    package_output = None
    if args.run_root is not None:
        if not args.run_root.is_dir():
            raise ValueError("run root must be an existing isolated directory")
        run_root = args.run_root.resolve(strict=True)
        if args.manifest is None:
            raise ValueError("--manifest is required with --run-root and must be staged under it")
        manifest_path = args.manifest.resolve(strict=True)
        if not manifest_path.is_relative_to(run_root):
            raise ValueError("isolated manifest must remain inside --run-root")
        output = (args.output or run_root / "outputs" / "g1_pilot_metrics.json").resolve()
        if not output.is_relative_to(run_root):
            raise ValueError("isolated pilot output must remain inside --run-root")
        if args.package_output is not None:
            package_output = args.package_output.resolve()
            if not package_output.is_relative_to(run_root):
                raise ValueError("selected evidence package must remain inside --run-root")
            outputs_root = (run_root / "outputs").resolve()
            if not package_output.is_relative_to(outputs_root):
                raise ValueError("selected evidence package must be under --run-root/outputs")
            if package_output in {manifest_path, output}:
                raise ValueError("selected evidence package must use a distinct output path")
        temp_root = run_root / "state" / "measure_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
    else:
        if args.package_output is not None:
            raise ValueError("--package-output requires --run-root to isolate selected source text")
        plan_root = PLAN_ROOT.resolve(strict=True)
        manifest_path = (args.manifest or PLAN_ROOT / "g1_sample_manifest.json").resolve(strict=True)
        output = (args.output or PLAN_ROOT / "g1_pilot_metrics.json").resolve()
        if not output.is_relative_to(plan_root):
            raise ValueError("pilot output must remain inside the planning directory")
        temp_root = None
    if output.exists() and not args.overwrite:
        raise FileExistsError("pilot output exists; pass --overwrite after reviewing it")
    if package_output is not None and package_output.exists() and not args.overwrite:
        raise FileExistsError("selected evidence package exists; pass --overwrite after reviewing it")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    samples = manifest["samples"]
    if args.sample_id:
        wanted = set(args.sample_id)
        samples = [sample for sample in samples if sample["id"] in wanted]
        found = {sample["id"] for sample in samples}
        if found != wanted:
            raise ValueError(f"unknown sample IDs: {sorted(wanted - found)}")
    run_started = time.perf_counter()
    results = []
    package_records = []
    for sample in samples:
        path = _resolve_sample(sample, args.company_root, args.transcript_root)
        if run_root is not None and not path.is_relative_to(run_root):
            raise ValueError(f"isolated sample input must remain inside --run-root: {sample['id']}")
        if package_output is not None and path.resolve(strict=True) == package_output:
            raise ValueError("selected evidence package cannot overwrite a staged source")
        result = _one_sample(
            sample,
            path,
            temp_root=temp_root,
            collect_package=package_output is not None,
        )
        if package_output is not None:
            package_records.append(result.pop("_package_record"))
        results.append(result)

    report = {
        "schema_version": "narrative-g1-pilot/0.1.0",
        "runner": "scripts/narrative_evidence_pilot.py",
        "read_only_roots": [
            str(args.company_root.resolve(strict=True)),
            str(args.transcript_root.resolve(strict=True)),
        ],
        "generated_from_manifest": str(manifest_path),
        "elapsed_seconds": round(time.perf_counter() - run_started, 3),
        "samples": results,
        "totals": {
            "documents": len(results),
            "source_file_bytes": sum(row["source_file_bytes"] for row in results),
            "summary_input_bytes": sum(row["summary_input_bytes"] for row in results),
            "summary_input_file_bytes": sum(row["summary_input_file_bytes"] for row in results),
            "selected_span_count": sum(row["selected_span_count"] for row in results),
            "locator_roundtrip_verified_count": sum(
                row["locator_roundtrip_verified_count"] for row in results
            ),
            "locator_roundtrip_failed_count": sum(
                row["locator_roundtrip_failed_count"] for row in results
            ),
            "selected_documents": sum(row["status"] == "selected" for row in results),
            "partial_documents": sum(row["status"] == "partial" for row in results),
            "skipped_documents": sum(row["status"] == "skipped_no_narrative" for row in results),
            "needs_review_documents": sum(row["status"] == "needs_review" for row in results),
            "blocked_documents": sum(row["status"] == "blocked" for row in results),
            "anchor_check_failure_count": sum(
                row["anchor_check_failure_count"] for row in results
            ),
        },
        "limitations": [
            "This is a 12-document pilot, not a corpus recall estimate.",
            "The selector uses deterministic candidate rules; a model did not generate summaries.",
            "summary_input_file_bytes is the exact logical file length for a temporary, fsynced per-source JSON file; the file is removed after measurement.",
            "Temporary JSON file lengths exclude database indexes, filesystem allocation rounding, and future exports.",
            "A status of selected means the parser covered the file, not that a human approved every candidate.",
            "Locator round-trip verifies same-parser extraction; it does not certify downstream support for table-cell sub-locators.",
        ],
    }
    if package_output is not None:
        package_bundle = {
            "schema_version": NARRATIVE_EVIDENCE_BUNDLE_SCHEMA_VERSION,
            "sources": package_records,
        }
        serialized_bundle = json.dumps(
            package_bundle,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8") + b"\n"
        package_output.parent.mkdir(parents=True, exist_ok=True)
        package_output.write_bytes(serialized_bundle)
        report["selected_evidence_package"] = {
            "path": package_output.relative_to(run_root).as_posix(),
            "byte_size": len(serialized_bundle),
            "sha256": hashlib.sha256(serialized_bundle).hexdigest(),
        }
        report["totals"]["selected_package_output_bytes"] = len(serialized_bundle)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(report["totals"], ensure_ascii=False, sort_keys=True))
    return 2 if report["totals"]["anchor_check_failure_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
