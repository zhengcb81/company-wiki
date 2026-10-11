"""One configured source image through current hard boundary, single 85s budget."""

import hashlib
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import time
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w05/cwp-ocr-root")
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))
OUT = HERE / "probe-one-image.json"
TRACE = HERE / "probe-one-image-trace.jsonl"
CONFIG = ROOT / "config/local_ocr.json"
EXPECTED_CONFIG_SHA = "3ef4d36adff892e66115271a15e3e73dd20a530af615e24d80cdb35f4cf20105"
REPLAY_CONFIG = Path(r"\\?\C:\Users\郑曾波\Projects\company-wiki\.source-preservation\w04-temp-20261011\US-MSFT\replay-config.yaml")
EXPECTED_REPLAY_SHA = "c9635ab393464ee01f85fcba4e907ecd40cdf3e39ae76ebd9c8e11c0a0ce0b86"
PPTX_SHA = "c02f4ea1a2719b74d5752559ad7b907d89dd4b47d292424ade8988396fb2dcd4"
MEDIA_SHA = "d4edf0903db8d061555fc3d0a99409f21c9f034fe8e31df59a37ae69de5f31ea"
sha = lambda data: hashlib.sha256(data).hexdigest()


def forbid(*args, **kwargs):
    raise AssertionError("network forbidden")


socket.create_connection = forbid
socket.socket.connect = forbid
os.environ["CWP_OCR_PERF_TRACE"] = str(TRACE)
if TRACE.exists() or OUT.exists():
    raise RuntimeError("immutable diagnostic output already exists")

from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader
from company_wiki.document_normalization.isolated_ocr import IsolatedOCRAdapter
from company_wiki.document_normalization.local_ocr import LocalOCRConfig, OCRLimits
from measured_backend import MeasuredLocalOCRAdapter, event


def main():
    config_data = CONFIG.read_bytes()
    assert sha(config_data) == EXPECTED_CONFIG_SHA
    assert sha(REPLAY_CONFIG.read_bytes()) == EXPECTED_REPLAY_SHA
    catalog = SourceCatalog(load_catalog_config(REPLAY_CONFIG))
    reader = SourceVersionReader(catalog)
    ref = SourceRef(
        document_id="urn:company-wiki:document:sha256:" + PPTX_SHA,
        source_id="urn:company-wiki:source:sha256:" + PPTX_SHA,
        content_sha256=PPTX_SHA,
        byte_size=4016522,
        mime_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        schema_version="2.0",
    )
    verified = reader.open_version(ref, purpose="source_export")
    assert sha(verified.data) == PPTX_SHA and len(verified.data) == 4016522
    with zipfile.ZipFile(io.BytesIO(verified.data)) as archive:
        media = archive.read("ppt/media/image7.png")
    assert sha(media) == MEDIA_SHA and len(media) == 331246
    config = LocalOCRConfig.from_dict(json.loads(config_data))
    scratch = Path(tempfile.mkdtemp(prefix="cwp-ocr-perf-"))
    started = time.monotonic()
    deadline = started + 85.0
    status = {"status": "RUNNING", "budget_seconds": 85.0, "config_sha": sha(config_data),
              "source_sha": sha(verified.data), "media_sha": sha(media), "network_calls": 0,
              "config": config.to_dict(), "executable": sys.executable}
    adapter = IsolatedOCRAdapter(config, deadline=deadline, scratch_dir=scratch,
                                 _backend_factory=MeasuredLocalOCRAdapter)
    try:
        event("parent_start", deadline=deadline)
        adapter._ensure_worker(deadline)
        event("parent_ready", worker_pid=adapter.worker_pid)
        adapter.validate_environment()
        event("parent_preflight_done")
        result = adapter.transcribe(media, limits=OCRLimits(deadline=deadline))
        event("parent_image_done", lines=len(result.lines))
        status["status"] = "PASS"
        status["accepted_lines"] = len(result.lines)
        status["dropped_regions"] = len(result.region_diagnostics.dropped)
    except Exception as error:
        status["status"] = "FAIL"
        status["error_type"] = type(error).__name__
        status["error"] = str(error)
        event("parent_failure", error_type=type(error).__name__, error=str(error))
    finally:
        adapter.close()
        status["elapsed_seconds"] = time.monotonic() - started
        status["scratch_children_after_close"] = [p.name for p in scratch.iterdir()]
        assert not any(scratch.iterdir())
        assert scratch.name.startswith("cwp-ocr-perf-") and scratch.parent == Path(tempfile.gettempdir())
        scratch.rmdir()
        assert sha(CONFIG.read_bytes()) == EXPECTED_CONFIG_SHA
        assert sha(REPLAY_CONFIG.read_bytes()) == EXPECTED_REPLAY_SHA
        status["scratch_restored"] = not scratch.exists()
        OUT.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({k: status[k] for k in ("status", "elapsed_seconds", "scratch_restored")}, ensure_ascii=False))
    return 0 if status["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
