"""Opt-in fixed-deck local check; parent hard deadline, no full OCR persistence.

Only the small per-page statistics and selected evidence excerpts reach output.
Uses explicitly supplied configuration and the read-only benchmark object.
"""

from __future__ import annotations
import argparse
from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time

EXPECTED_SHA = "c02f4ea1a2719b74d5752559ad7b907d89dd4b47d292424ade8988396fb2dcd4"
MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


def plain(value):
    if isinstance(value, Mapping):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value


def child(args):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
    from company_wiki.document_normalization import (
        LocalOCRAdapter,
        LocalOCRConfig,
        NormalizationLimits,
        OCRLimits,
        normalize_document,
        replay_evidence_spans,
        normalization_identity,
    )
    import socket
    import urllib.request
    import requests

    network = {"attempts": 0, "supplier_posts": 0}

    def forbidden(*a, **kw):
        network["attempts"] += 1
        raise AssertionError("network/download is forbidden in this local check")

    socket.create_connection = forbidden
    socket.socket.connect = forbidden
    socket.socket.connect_ex = forbidden
    urllib.request.urlopen = forbidden
    requests.sessions.Session.request = forbidden
    from rapidocr.utils.download_file import DownloadFile

    DownloadFile.run = forbidden
    cfg = LocalOCRConfig.from_dict(
        json.loads(Path(args.ocr_config).read_text(encoding="utf-8"))
    )
    suite = json.loads(Path(args.suite).read_text(encoding="utf-8"))
    candidates = [
        s for c in suite["cases"] for s in c["sources"] if s["sha256"] == EXPECTED_SHA
    ]
    assert len(candidates) == 1
    source = candidates[0]
    imported = json.loads(Path(args.import_receipt).read_text(encoding="utf-8"))
    ref = imported["source_ref"]
    assert imported["schema_version"] == "official-source-import-result/1"
    assert imported["status"] in {"imported_new", "deduplicated"}
    assert ref["content_sha256"] == EXPECTED_SHA and ref["mime_type"] == MIME
    source_id = ref["source_id"]
    root = Path(args.object_root).resolve()
    original = (root / source["object_relative"]).resolve()
    assert original.is_relative_to(root)
    before = original.stat()
    data = original.read_bytes()
    assert hashlib.sha256(data).hexdigest() == EXPECTED_SHA
    soft_deadline = time.monotonic() + args.timeout - 10
    limits = NormalizationLimits(
        max_source_bytes=8 * 1024 * 1024,
        max_total_uncompressed_bytes=32 * 1024 * 1024,
        max_media_bytes=8 * 1024 * 1024,
        max_pages=22,
        max_units=3000,
        max_text_output_bytes=200000,
        deadline=soft_deadline,
    )
    ocr_limits = OCRLimits(
        max_image_pixels=4_000_000,
        max_total_pixels=90_000_000,
        max_images=22,
        deadline=soft_deadline,
    )

    class Tracking:
        def __init__(self):
            self.adapter = LocalOCRAdapter(cfg)
            self.identity_manifest = self.adapter.identity_manifest
            self.fingerprint = self.adapter.fingerprint
            self.calls = []

        def transcribe(self, data, *, limits):
            start = time.perf_counter()
            result = self.adapter.transcribe(data, limits=limits)
            self.calls.append(
                {
                    "media_sha256": hashlib.sha256(data).hexdigest(),
                    "elapsed_seconds": round(time.perf_counter() - start, 6),
                    "line_count": len(result.lines),
                    "min_confidence": min(
                        (line.confidence for line in result.lines), default=None
                    ),
                    "mean_confidence": statistics.mean(
                        line.confidence for line in result.lines
                    )
                    if result.lines
                    else None,
                }
            )
            return result

    adapter = Tracking()
    pure = normalize_document(
        data,
        source_id=source_id,
        source_sha256=EXPECTED_SHA,
        mime_type=MIME,
        limits=limits,
    )
    start = time.perf_counter()
    doc = normalize_document(
        data,
        source_id=source_id,
        source_sha256=EXPECTED_SHA,
        mime_type=MIME,
        limits=limits,
        ocr=adapter,
        ocr_limits=ocr_limits,
    )
    elapsed = time.perf_counter() - start
    assert len(adapter.calls) == 22 and doc.structure.pages_read == 22
    initial_calls = list(adapter.calls)
    timings = {r["media_sha256"]: r for r in initial_calls}
    page_stats = []
    for page in doc.metadata["ocr"]["pages"]:
        row = plain(page)
        row["elapsed_seconds"] = sum(
            timings[i["media_sha256"]]["elapsed_seconds"] for i in row["images"]
        )
        units = [
            u for u in doc.units if u.coordinates.page_number == row["page_number"]
        ]
        scores = [u.metadata["ocr_confidence"] for u in units]
        row["min_confidence"] = min(scores, default=None)
        row["mean_confidence"] = statistics.mean(scores) if scores else None
        page_stats.append(row)
    selected = []
    for page in (1, 7, 12, 18):
        lines = [u for u in doc.units if u.coordinates.page_number == page]
        # Bound persisted excerpts; complete OCR remains only in the document memory.
        selected.extend(lines[:2])
    spans = tuple(
        u.to_evidence_span(
            topics=["business_progress"], selection_reasons=["local_visual_qa"]
        )
        for u in selected
    )
    replay_start = time.perf_counter()
    replayed = replay_evidence_spans(
        data,
        source_id=source_id,
        source_sha256=EXPECTED_SHA,
        mime_type=MIME,
        evidence_spans=spans,
        limits=limits,
        ocr=adapter,
        ocr_limits=ocr_limits,
    )
    replay_seconds = time.perf_counter() - replay_start
    assert len(adapter.calls) - len(initial_calls) == 4 and replayed == len(spans)
    report = {
        "schema_version": "cwp-local-ocr-real-check/1",
        "status": "recognized_with_unverified_recall",
        "case": "US-MSFT",
        "source_id": source_id,
        "benchmark_legacy_alias": source["source_id"],
        "isolated_source_ref": ref,
        "source_sha256": EXPECTED_SHA,
        "original_bytes": len(data),
        "original_stat_unchanged": original.stat().st_size == before.st_size
        and original.stat().st_mtime_ns == before.st_mtime_ns,
        "original_sha256_after": hashlib.sha256(original.read_bytes()).hexdigest(),
        "normalization_identity": normalization_identity(MIME, ocr=adapter),
        "pure_parser_version": pure.parser_version,
        "pure_units": len(pure.units),
        "pure_pages_read": pure.structure.pages_read,
        "pure_opaque_pages": plain(pure.structure.opaque_pages),
        "ocr_parser_version": doc.parser_version,
        "elapsed_seconds": round(elapsed, 6),
        "ocr_inference_calls": len(initial_calls),
        "unique_media_count": doc.metadata["ocr"]["unique_media_count"],
        "total_decoded_pixels": doc.metadata["ocr"]["total_decoded_pixels"],
        "recognized_lines": len(doc.units),
        "pages_read": doc.structure.pages_read,
        "coverage_complete": doc.structure.coverage_complete,
        "errors": plain(doc.structure.errors),
        "opaque_pages": plain(doc.structure.opaque_pages),
        "recall_status": "unverified",
        "table_cells_inferred": False,
        "reading_order": "top-left-box/1",
        "page_statistics": page_stats,
        "selected_spans": [s.to_dict() for s in spans],
        "multi_span_replay": {
            "spans": replayed,
            "normalizations": 1,
            "inference_calls": len(adapter.calls) - len(initial_calls),
            "elapsed_seconds": round(replay_seconds, 6),
        },
        "network": network,
        "parent_hard_deadline_seconds": args.timeout,
        "native_call_cooperative_cancellation": False,
    }
    # Additional QA snippets are bounded, not an exhaustive OCR transcript.
    previews = {}
    for page in (1, 7, 12, 18):
        lines = [u for u in doc.units if u.coordinates.page_number == page]
        indexes = sorted(
            set(
                [
                    0,
                    1,
                    2,
                    3,
                    4,
                    len(lines) // 2,
                    len(lines) - 3,
                    len(lines) - 2,
                    len(lines) - 1,
                ]
            )
        )
        previews[str(page)] = [
            {
                "index": i,
                "text": lines[i].raw_text[:280],
                "confidence": lines[i].metadata["ocr_confidence"],
                "box": plain(lines[i].metadata["ocr_box"]),
            }
            for i in indexes
            if 0 <= i < len(lines)
        ]
    report["qa_bounded_previews"] = previews
    print(json.dumps(report, ensure_ascii=False, allow_nan=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", required=True)
    parser.add_argument("--object-root", required=True)
    parser.add_argument("--ocr-config", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--import-receipt", required=True)
    parser.add_argument("--timeout", type=float, default=240)
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args()
    if not 20 <= args.timeout <= 300:
        parser.error("timeout must be finite in [20,300]")
    if args.child:
        child(args)
        return
    command = [
        sys.executable,
        "-X",
        "utf8",
        "-B",
        str(Path(__file__).resolve()),
        *sys.argv[1:],
        "--child",
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=args.timeout,
        check=False,
    )
    if result.returncode:
        raise SystemExit(result.stderr or f"child failed: {result.returncode}")
    report = json.loads(result.stdout)
    assert (
        report["network"]["attempts"] == 0 and report["network"]["supplier_posts"] == 0
    )
    output = Path(args.output)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(output),
                "lines": report["recognized_lines"],
                "pages": report["pages_read"],
                "seconds": report["elapsed_seconds"],
                "replay_seconds": report["multi_span_replay"]["elapsed_seconds"],
                "network": report["network"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
