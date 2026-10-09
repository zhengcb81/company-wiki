"""Authorized real local page7 media initial + exact selected replay, zero providers.

The source package is read-only. Pure ZIP normalization discovers its original
locators; only the approved media is OCR'd. One child process has 60 seconds.
No AUTO/job/request/generation mutation and no full-deck OCR is performed.
"""

from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
MEDIA = "d4edf0903db8d061555fc3d0a99409f21c9f034fe8e31df59a37ae69de5f31ea"
MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def identity(path):
    before = path.stat()
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return {
        "path": str(path),
        "sha256": h.hexdigest(),
        "size": before.st_size,
        "mtime_ns": before.st_mtime_ns,
        "mode": before.st_mode,
        "file_attributes": getattr(before, "st_file_attributes", None),
    }


def write(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def selection_receipt(selected):
    """Use the actual public package fields; pure serialization is independently tested."""
    return {
        "status": selected.status,
        "coverage_complete": selected.coverage_complete,
        "candidate_count": selected.candidate_count,
        "selected_count": len(selected.evidence_spans),
        "dropped_financial_count": selected.dropped_financial_count,
        "max_selected": selected.selection_limit,
        "omitted_count": selected.omitted_candidate_count,
    }


def child(root):
    start = time.monotonic()
    deadline = start + 58
    denied = []

    def no_network(*args, **kwargs):
        denied.append("network connection attempted")
        raise RuntimeError("real local sample forbids network")

    socket.socket.connect = no_network
    socket.socket.connect_ex = no_network
    socket.create_connection = no_network
    sys.path.insert(0, str(PROJECT / "src"))
    from company_wiki import document_normalization as dn
    from company_wiki.document_normalization.ocr_composition import enrich_pptx
    from company_wiki.source_catalog.narrative_evidence import (
        select_narrative_evidence,
        NARRATIVE_SELECTOR_VERSION,
    )
    from company_wiki.source_catalog.narrative_normalization import (
        NarrativeNormalization,
    )
    from company_wiki.source_catalog.narrative_language import (
        detect_narrative_text_language,
    )
    from company_wiki.source_contract import source_id_for_sha256

    calls = []
    config = dn.LocalOCRConfig.from_dict(load(root / "local_ocr.json"))
    native = dn.LocalOCRAdapter(config)
    native.validate_environment()

    class ObservedLocal:
        identity_manifest = native.identity_manifest
        fingerprint = native.fingerprint
        phase = "initial"

        def transcribe(self, data, *, limits):
            digest = hashlib.sha256(data).hexdigest()
            assert digest == MEDIA and len(calls) < 2
            began = time.monotonic()
            row = {"phase": self.phase, "media_sha256": digest, "completed": False}
            calls.append(row)
            result = native.transcribe(data, limits=limits)
            row.update(
                completed=True,
                seconds=time.monotonic() - began,
                line_count=len(result.lines),
                width=result.width,
                height=result.height,
            )
            return result

    adapter = ObservedLocal()
    raw = (root / "sample.pptx").read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    source_id = source_id_for_sha256(digest)
    limits = dn.NormalizationLimits(deadline=deadline)
    ocr_limits = dn.OCRLimits(max_images=1, deadline=deadline)
    pure = dn.normalize_document(
        raw, source_id=source_id, source_sha256=digest, mime_type=MIME, limits=limits
    )
    approved = [a for a in pure.opaque_assets if a.media_sha256 == MEDIA]
    assert len(approved) == 1 and approved[0].slide_number == 7
    document = enrich_pptx(
        pure,
        ocr=adapter,
        limits=limits,
        ocr_limits=ocr_limits,
        selected_media_sha256s=frozenset({MEDIA}),
    )
    ocr_units = [u for u in document.units if u.unit_kind == "pptx_image_ocr_line"]
    assert ocr_units and all(u.coordinates.page_number == 7 for u in ocr_units)
    language = detect_narrative_text_language("\n".join(u.raw_text for u in ocr_units))
    structure = NarrativeNormalization.language_structure(document, language)
    selected = select_narrative_evidence(
        structure,
        title="FY27 Segment reporting changes",
        existing_kind="investor_relations",
        max_selected=8,
    )
    spans = selected.evidence_spans
    assert (
        language == "en"
        and spans
        and selected.status == "partial"
        and not selected.coverage_complete
    )
    assert all(
        s.parse_status == "parsed"
        and s.structured_value["media_sha256"] == MEDIA
        and not {"low_ocr_confidence", "locator_unstable"}.intersection(s.quality_flags)
        for s in spans
    )
    adapter.phase = "selected_replay"
    verified = dn.replay_evidence_spans(
        raw,
        source_id=source_id,
        source_sha256=digest,
        mime_type=MIME,
        evidence_spans=spans,
        limits=limits,
        ocr=adapter,
        ocr_limits=ocr_limits,
    )
    assert verified == len(spans) and len(calls) == 2 and not denied
    result = {
        "schema_version": "main-ocr-selection-page7-child/1",
        "status": "PASS",
        "selector_version": NARRATIVE_SELECTOR_VERSION,
        "parser_version": "2.0.0",
        "source_sha256": digest,
        "media_sha256": MEDIA,
        "display_page": 7,
        "language": language,
        "ocr_fingerprint": config.fingerprint,
        "model_hashes": {
            key: getattr(config, key).sha256 for key in ("det", "cls", "rec")
        },
        "calls": calls,
        "seconds": time.monotonic() - start,
        "selection": selection_receipt(selected),
        "verified_count": verified,
        "evidence_spans": [s.to_dict() for s in spans],
        "actual_ocr_lines": [
            {
                "index": u.metadata["ocr_line_index"],
                "text": u.raw_text,
                "box": list(u.metadata["ocr_box"]),
                "confidence": u.metadata["ocr_confidence"],
            }
            for u in ocr_units
        ],
        "two_segment_statement_detected": any(
            "transition to two" in u.raw_text for u in ocr_units
        ),
        "network_attempts": len(denied),
        "supplier_calls": 0,
        "model_calls": 0,
        "model_tokens": 0,
        "model_cost_micro_usd": 0,
        "unknown_provider_usage": 0,
        "budget_authority": "No AUTO/model/provider was invoked; local CPU sample only",
    }
    write(root / "child_receipt.json", result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "calls": len(calls),
                "lines": len(ocr_units),
                "selected": len(spans),
                "verified": verified,
                "seconds": result["seconds"],
            }
        )
    )


def parent(main):
    cases = load(main / "benchmarks/cross_market_rf/cases.json")
    case = next(c for c in cases["cases"] if c["case"] == "US-MSFT")
    source = next(
        s for s in case["sources"] if s["filename"] == "fy2027_segments_metrics.pptx"
    )
    index = load(main / cases["audit_index"])
    artifact = next(
        a
        for a in index["artifacts"]
        if a.get("sha256") == source["sha256"] and a.get("storage") == "retained_object"
    )
    deck = Path(artifact["archive_path"])
    protected_paths = [
        deck,
        main / "config/source_catalog.yaml",
        main / "config/local_ocr.json",
        main / "config.yaml",
        *(
            main / "docs/plans/cross-market-rf-e2e-2026-10-08" / name
            for name in ("task_plan.md", "findings.md", "progress.md")
        ),
        main
        / "docs/plans/cross-market-rf-e2e-2026-10-08/phase6/ocr_major_node/run_acceptance.py",
        Path(r"C:\Users\郑曾波\AppData\Local\Temp\mOCR-srw9_9oe\auto\first.sqlite3"),
    ]
    before = {str(p): identity(p) for p in protected_paths}
    assert (
        before[str(deck)]["sha256"] == source["sha256"]
        and before[str(deck)]["size"] == 4016522
    )
    root = Path(tempfile.mkdtemp(prefix="mOS-")).resolve()
    write(
        root / "marker.json", {"owner": "main-ocr-selection-page7", "root": str(root)}
    )
    sample = root / "sample.pptx"
    sample.write_bytes(deck.read_bytes())
    os.chmod(sample, stat.S_IREAD)
    assert identity(sample)["sha256"] == source["sha256"]
    (root / "local_ocr.json").write_bytes((main / "config/local_ocr.json").read_bytes())
    began = time.monotonic()
    try:
        completed = subprocess.run(
            [sys.executable, "-B", str(Path(__file__).resolve()), "--child", str(root)],
            cwd=PROJECT,
            capture_output=True,
            text=True,
            timeout=60,
            env={
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": str(PROJECT / "src"),
            },
        )
        execution = {
            "returncode": completed.returncode,
            "stdout": completed.stdout[-2500:],
            "stderr": completed.stderr[-2500:],
            "terminated": True,
            "timeout": False,
        }
    except subprocess.TimeoutExpired:
        execution = {"returncode": None, "terminated": True, "timeout": True}
    wall = time.monotonic() - began
    after = {str(p): identity(p) for p in protected_paths}
    receipt = (
        load(root / "child_receipt.json")
        if (root / "child_receipt.json").exists()
        else None
    )
    success = (
        execution["returncode"] == 0
        and receipt is not None
        and receipt["status"] == "PASS"
        and before == after
        and wall < 60
    )
    result = {
        "schema_version": "main-ocr-selection-page7/1",
        "status": "PASS" if success else "FAILED_RETAIN_SAMPLE",
        "base": "ea76998cc152317f653f101441de69bcb8aeb4fa",
        "worktree_head_at_execution": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True
        ).strip(),
        "local_code_uncommitted_at_execution": True,
        "owned_root": str(root),
        "sample_readonly": True,
        "command": [
            sys.executable,
            "-B",
            str(Path(__file__).resolve()),
            "--main-project",
            str(main),
        ],
        "outer_seconds": wall,
        "deadline_seconds": 60,
        "execution": execution,
        "protected_before": before,
        "protected_after": after,
        "protected_unchanged": before == after,
        "origin_auto_retained": True,
        "cleanup": "pending bounded PowerShell cleanup after child terminal",
        "supplier_calls": 0,
        "model_tokens": 0,
        "model_cost_micro_usd": 0,
        "unknown_provider_usage": 0,
        "native_local_ocr": receipt,
    }
    write(HERE / "page7_real_receipt.json", result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "owned_root": str(root),
                "seconds": wall,
                "protected_unchanged": before == after,
                "supplier_calls": 0,
                "native": None if receipt is None else receipt["selection"],
            }
        )
    )
    return 0 if success else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-project", type=Path)
    parser.add_argument("--child", type=Path)
    args = parser.parse_args()
    if args.child is not None:
        child(args.child)
    else:
        if args.main_project is None:
            parser.error("--main-project is required")
        raise SystemExit(parent(args.main_project.resolve()))
