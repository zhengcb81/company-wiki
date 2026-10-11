# W05-CWP-OCR Node C real single-page E2E.
# Phase 1: SourceVersionReader -> exact PPTX/media -> current local OCR -> normal
#          compose (single-page OCR path, 90s hard cutoff).
# Phase 2: locator reopen via replay with a fresh adapter (90s hard cutoff).
# Network forbidden; one JSON log with per-phase timeout/exit status.
import hashlib
import io
import json
import os
import socket
import sys
import threading
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
WORKTREE = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(WORKTREE, "src"))

OUT = os.path.join(HERE, "e2e-slide7-result.json")
HARD_TIMEOUT = 90

REPLAY_CONFIG = "\\\\?\\C:\\Users\\郑曾波\\Projects\\company-wiki\\.source-preservation\\w04-temp-20261011\\US-MSFT\\replay-config.yaml"
REPLAY_CONFIG_SHA = "c9635ab393464ee01f85fcba4e907ecd40cdf3e39ae76ebd9c8e11c0a0ce0b86"
PPTX_SHA = "c02f4ea1a2719b74d5752559ad7b907d89dd4b47d292424ade8988396fb2dcd4"
MEDIA_PART = "ppt/media/image7.png"
MEDIA_SHA = "d4edf0903db8d061555fc3d0a99409f21c9f034fe8e31df59a37ae69de5f31ea"
CONFIG_PATH = os.path.join(WORKTREE, "config", "local_ocr.json")
CONFIG_SHA = "3ef4d36adff892e66115271a15e3e73dd20a530af615e24d80cdb35f4cf20105"
ROOT_CAUSE_JSON = os.path.join(HERE, "..", "input", "slide7-root-cause.json")
MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

SOURCE_REF = {
    "document_id": "urn:company-wiki:document:sha256:" + PPTX_SHA,
    "source_id": "urn:company-wiki:source:sha256:" + PPTX_SHA,
    "content_sha256": PPTX_SHA,
    "byte_size": 4016522,
    "mime_type": MIME,
    "schema_version": "2.0",
}

state = {"status": "RUNNING", "started_at": time.time(), "phases": {}}
_phase = {"name": None, "finished": True}


def persist():
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)


def hard_stop():
    # Late timers must never clobber a finished phase's record.
    if _phase["finished"]:
        return
    name = _phase["name"] or "unknown"
    state["phases"].setdefault(name, {})["status"] = "HARD_TIMEOUT"
    state["phases"][name]["hard_timeout_seconds"] = HARD_TIMEOUT
    state["status"] = "HARD_TIMEOUT"
    persist()
    os._exit(124)


class phase_bound:
    """90s hard cutoff for one phase; records elapsed and exit status."""

    def __init__(self, name):
        self.name = name

    def __enter__(self):
        _phase["name"] = self.name
        _phase["finished"] = False
        state["phases"].setdefault(self.name, {})
        self.timer = threading.Timer(HARD_TIMEOUT, hard_stop)
        self.timer.start()
        self.started = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        record = state["phases"][self.name]
        record["elapsed_seconds"] = round(time.perf_counter() - self.started, 3)
        record.setdefault("status", "FAILED" if exc_type else "COMPLETED")
        _phase["finished"] = True
        self.timer.cancel()
        return False


def forbid(*a, **kw):
    raise AssertionError("network must never be reached")


socket.create_connection = forbid
socket.socket.connect = forbid


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main():
    from pathlib import Path

    from company_wiki.source_catalog.config import load_catalog_config
    from company_wiki.source_catalog.service import SourceCatalog
    from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader
    from company_wiki.document_normalization import (
        NormalizationLimits,
        normalize_document,
        replay_units,
    )
    from company_wiki.document_normalization.local_ocr import (
        LocalOCRAdapter,
        LocalOCRConfig,
        OCRLimits,
    )
    from company_wiki.document_normalization.ocr_composition import enrich_pptx

    assert sha(open(REPLAY_CONFIG, "rb").read()) == REPLAY_CONFIG_SHA
    cfg_bytes = open(CONFIG_PATH, "rb").read()
    assert sha(cfg_bytes) == CONFIG_SHA, "config sha changed"

    with phase_bound("phase1_source_ocr_compose"):
        catalog = SourceCatalog(load_catalog_config(Path(REPLAY_CONFIG)))
        reader = SourceVersionReader(catalog)
        ref = SourceRef(**SOURCE_REF)
        verified = reader.open_version(ref, purpose="source_export")
        pptx_bytes = verified.data
        state["source_read"] = {
            "via": "SourceVersionReader.open_version",
            "purpose": "source_export",
            "content_sha256": verified.content_sha256,
            "byte_size": verified.byte_size,
            "policy_sha256": verified.policy_sha256,
        }
        assert sha(pptx_bytes) == PPTX_SHA and len(pptx_bytes) == 4016522

        with zipfile.ZipFile(io.BytesIO(pptx_bytes)) as zf:
            media_bytes = zf.read(MEDIA_PART)
        assert sha(media_bytes) == MEDIA_SHA and len(media_bytes) == 331246

        config = LocalOCRConfig.from_dict(json.loads(cfg_bytes.decode("utf-8")))
        adapter = LocalOCRAdapter(config)
        ocr_started = time.perf_counter()
        ocr_limits = OCRLimits(deadline=time.monotonic() + 85)
        pure = normalize_document(
            pptx_bytes,
            source_id=ref.source_id,
            source_sha256=PPTX_SHA,
            mime_type=MIME,
            parser_version="1.1.0",
            limits=NormalizationLimits(deadline=time.monotonic() + 88),
        )
        doc = enrich_pptx(
            pure,
            ocr=adapter,
            limits=NormalizationLimits(deadline=time.monotonic() + 88),
            ocr_limits=ocr_limits,
            selected_media_sha256s=frozenset({MEDIA_SHA}),
        )
        ocr_elapsed = time.perf_counter() - ocr_started

    image_units = [u for u in doc.units if u.unit_kind == "pptx_image_ocr_line"]
    baseline = json.load(open(ROOT_CAUSE_JSON, encoding="utf-8"))
    expected = baseline["configured_probe"]["normalized_lines"]
    original_units = [u for u in image_units if not u.metadata.get("ocr_recovered")]
    recovered_units = [u for u in image_units if u.metadata.get("ocr_recovered")]

    # 1. The original 22 accepted lines are unchanged (text/box/confidence).
    assert len(original_units) == 22, f"expected 22 original lines, got {len(original_units)}"
    for unit, exp in zip(original_units, expected):
        assert unit.raw_text == exp["text"], unit.raw_text
        box = [round(v, 3) for v in unit.metadata["ocr_box"]]
        assert box == exp["box"], (box, exp["box"])
        assert round(unit.metadata["ocr_confidence"], 5) == round(exp["score"], 5)

    # 2. Exactly two recovered lines carry the visible business definitions.
    assert len(recovered_units) == 2, f"expected 2 recovered, got {len(recovered_units)}"
    line1 = next(u for u in recovered_units if "Agents and Infra" in u.raw_text)
    line2 = next(u for u in recovered_units if "Productivity and server licensing" in u.raw_text)
    for term in ("Agents and Infra", "Microsoft Cloud", "productivity and server licensing"):
        assert term.lower() in line1.raw_text.lower(), (term, line1.raw_text)
    for term in ("Productivity and server licensing", "licensing offerings across our products"):
        assert term.lower() in line2.raw_text.lower(), (term, line2.raw_text)

    # 3. Recovered lines passed the same acceptance threshold; no garble added.
    for unit in recovered_units:
        assert unit.metadata["ocr_confidence"] >= config.text_score
        assert "ocr_recovered" in unit.quality_flags
        assert unit.metadata["recall_status"] == "unverified"
        assert unit.metadata["source_locator"].startswith("cwp-pptx-image-ocr/1|")

    # 4. Locators reopen: replay both recovered units + one original line.
    with phase_bound("phase2_locator_replay_reopen"):
        replay_targets = (line1, line2, original_units[0])
        fresh = LocalOCRAdapter(
            LocalOCRConfig.from_dict(json.loads(cfg_bytes.decode("utf-8")))
        )
        replayed = replay_units(
            pptx_bytes,
            source_sha256=PPTX_SHA,
            units=replay_targets,
            limits=NormalizationLimits(),
            ocr=fresh,
            ocr_limits=OCRLimits(),
        )
    assert replayed == tuple(u.raw_text for u in replay_targets)

    # 5. Quality accounting: dropped regions diagnosed, recovery recorded.
    page = next(p for p in doc.metadata["ocr"]["pages"] if p["page_number"] == 7)
    image_record = page["images"][0]
    diagnostics = image_record["region_diagnostics"]
    assert diagnostics["dropped"], "dropped regions must be diagnosed"
    assert image_record["dropped_regions"] == 3
    assert image_record["recovered_lines"] == 2
    assert image_record["unrecovered_regions"] == 1  # the "·" bullet stays flagged
    assert doc.structure.coverage_complete is False

    # 6. Original and media identity unchanged end to end.
    assert sha(pptx_bytes) == PPTX_SHA and sha(media_bytes) == MEDIA_SHA

    # Save the two recovered ROI crops as evidence (bounded).
    from PIL import Image

    from company_wiki.document_normalization.ocr_region_recovery import build_margin_crop

    for unit, name in (
        (line1, "roi-line1-margin-crop.png"),
        (line2, "roi-line2-margin-crop.png"),
    ):
        region = None
        for rec in diagnostics["recovery"]:
            if rec["status"] == "recovered" and rec["recovered_text"] == unit.raw_text:
                region = rec["box"]
        data, _transform = build_margin_crop(
            Image.open(io.BytesIO(media_bytes)).convert("RGB"), tuple(region)
        )
        with open(os.path.join(HERE, name), "wb") as f:
            f.write(data)

    state.update(
        {
            "status": "COMPLETED",
            "ocr_elapsed_seconds": round(ocr_elapsed, 3),
            "slide7": {
                "page_number": 7,
                "image_units_total": len(image_units),
                "original_lines_kept": len(original_units),
                "recovered_lines": [u.raw_text for u in recovered_units],
                "recovered_boxes": [u.metadata["ocr_box"] for u in recovered_units],
                "recovered_confidences": [
                    u.metadata["ocr_confidence"] for u in recovered_units
                ],
                "recovered_locators": [u.metadata["source_locator"] for u in recovered_units],
                "dropped_regions": diagnostics["dropped"],
                "recovery_records": diagnostics["recovery"],
            },
            "page_record": page,
            "replay": {
                "targets": [u.raw_text for u in replay_targets],
                "exact_match": True,
                "fresh_adapter": True,
            },
            "baseline_match": {
                "source": "input/slide7-root-cause.json normalized_lines",
                "lines_compared": 22,
                "text_box_confidence_exact": True,
            },
            "sha_unchanged": {
                "pptx": PPTX_SHA,
                "media": MEDIA_SHA,
                "config": CONFIG_SHA,
            },
            "network_calls": 0,
            "paid_calls": 0,
        }
    )
    persist()
    print("WROTE", OUT, flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        if state["status"] != "HARD_TIMEOUT":
            state["status"] = "FAILED"
        state["error"] = f"{type(exc).__name__}: {exc}"
        persist()
        raise
