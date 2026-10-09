"""Opt-in numeric visual check on one verified image; no full transcript output."""

from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--object", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args()
    if not args.child:
        result = subprocess.run(
            [
                sys.executable,
                "-X",
                "utf8",
                "-B",
                str(Path(__file__).resolve()),
                *sys.argv[1:],
                "--child",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
        if result.returncode:
            raise SystemExit(result.stderr)
        report = json.loads(result.stdout)
        output = Path(__file__).resolve().parent / "numeric_visual_qa.json"
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "output": str(output),
                    "selected": len(report["selected_spans"]),
                    "inference_calls": report["inference_calls"],
                    "network_attempts": report["network_attempts"],
                }
            )
        )
        return
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
    from company_wiki.document_normalization import (
        LocalOCRAdapter,
        LocalOCRConfig,
        NormalizationLimits,
        OCRLimits,
        normalize_document,
        replay_evidence_spans,
    )
    from company_wiki.document_normalization.ocr_composition import enrich_pptx
    import socket
    import urllib.request
    import requests

    attempts = []

    def forbidden(*a, **kw):
        attempts.append(1)
        raise AssertionError("network forbidden")

    socket.create_connection = forbidden
    socket.socket.connect = forbidden
    socket.socket.connect_ex = forbidden
    urllib.request.urlopen = forbidden
    requests.sessions.Session.request = forbidden
    from rapidocr.utils.download_file import DownloadFile

    DownloadFile.run = forbidden
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    ref = receipt["source_ref"]
    data = args.object.read_bytes()
    assert hashlib.sha256(data).hexdigest() == ref["content_sha256"]
    cfg = LocalOCRConfig.from_dict(json.loads(args.config.read_text(encoding="utf-8")))

    class Tracking(LocalOCRAdapter):
        calls = 0

        def transcribe(self, data, *, limits):
            self.calls += 1
            return super().transcribe(data, limits=limits)

    adapter = Tracking(cfg)
    limits = NormalizationLimits(deadline=time.monotonic() + 45)
    ocr_limits = OCRLimits(
        max_images=1,
        max_image_pixels=4_000_000,
        max_total_pixels=4_000_000,
        deadline=limits.deadline,
    )
    pure = normalize_document(
        data,
        source_id=ref["source_id"],
        source_sha256=ref["content_sha256"],
        mime_type=ref["mime_type"],
        limits=limits,
    )
    media = frozenset(
        a.media_sha256
        for a in pure.opaque_assets
        if a.slide_number == 18 and a.asset_kind == "image"
    )
    start = time.perf_counter()
    doc = enrich_pptx(
        pure,
        ocr=adapter,
        limits=limits,
        ocr_limits=ocr_limits,
        selected_media_sha256s=media,
    )
    lines = [u for u in doc.units if u.coordinates.page_number == 18]
    selected = [
        u
        for u in lines
        if (390 <= u.metadata["ocr_box"][1] <= 450 and u.metadata["ocr_box"][0] >= 1400)
    ]
    selected += [
        u
        for u in lines
        if 390 <= u.metadata["ocr_box"][1] <= 450 and u.metadata["ocr_box"][0] < 1000
    ]
    selected = selected[:8]
    assert selected
    spans = tuple(
        u.to_evidence_span(
            topics=["business_progress"],
            selection_reasons=["numeric_visual_check_only"],
        )
        for u in selected
    )
    replayed = replay_evidence_spans(
        data,
        source_id=ref["source_id"],
        source_sha256=ref["content_sha256"],
        mime_type=ref["mime_type"],
        evidence_spans=spans,
        limits=limits,
        ocr=adapter,
        ocr_limits=ocr_limits,
    )
    assert adapter.calls == 2 and replayed == len(spans) and not attempts
    report = {
        "schema_version": "cwp-local-ocr-numeric-visual-check/1",
        "source_ref": ref,
        "page_number": 18,
        "media_sha256": list(media),
        "scope": "selected_media",
        "coverage_complete": False,
        "selected_spans": [s.to_dict() for s in spans],
        "inference_calls": adapter.calls,
        "normalizations_for_replay": 1,
        "elapsed_seconds": round(time.perf_counter() - start, 6),
        "network_attempts": len(attempts),
        "table_cells_inferred": False,
        "meaning": "raw OCR excerpts for visual comparison only; row/column relations are not inferred",
    }
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
