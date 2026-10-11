"""Local OCR configuration, offline construction, bounds and process ownership."""

from dataclasses import replace
from enum import Enum
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

from company_wiki.document_normalization import NormalizationLimitError
from company_wiki.document_normalization.local_ocr import (
    ImageOCRResult,
    LocalOCRError,
    LocalOCRAdapter,
    LocalOCRConfig,
    OCRLimits,
    OCRLine,
    OCRDroppedRegion,
    OCRModelFile,
    OCRRegionDiagnostics,
    OCRRegionRecovery,
    OCRRecoveryAttempt,
    image_dimensions,
)
from conftest import tiny_png, build_pptx


def config(tmp_path):
    files = {}
    for name in ("det", "cls", "rec"):
        p = tmp_path / (name + ".onnx")
        p.write_bytes(name.encode())
        files[name] = OCRModelFile(str(p), hashlib.sha256(name.encode()).hexdigest())
    return LocalOCRConfig(
        **files,
        engine_version="test-engine",
        runtime_version="test-runtime",
        base_config_sha256="a" * 64,
    )


def test_config_identity_is_pathless_strict_and_sensitive_to_actual_settings(tmp_path):
    cfg = config(tmp_path)
    assert LocalOCRConfig.from_dict(cfg.to_dict()) == cfg
    moved = replace(cfg, det=replace(cfg.det, path=str(tmp_path / "elsewhere.onnx")))
    assert moved.fingerprint == cfg.fingerprint
    assert str(tmp_path) not in json.dumps(cfg.identity_manifest)
    for changed in (
        replace(cfg, rec=replace(cfg.rec, sha256="f" * 64)),
        replace(cfg, engine_version="test-engine-2"),
        replace(cfg, runtime_version="test-runtime-2"),
        replace(cfg, base_config_sha256="b" * 64),
        replace(cfg, text_score=0.4),
        replace(cfg, low_confidence_threshold=0.7),
        replace(cfg, max_side_len=2000),
        replace(cfg, intra_op_threads=1),
    ):
        assert changed.fingerprint != cfg.fingerprint
    bad = cfg.to_dict()
    bad["provider"] = "guessed"
    with pytest.raises(ValueError):
        LocalOCRConfig.from_dict(bad)
    bad = cfg.to_dict()
    del bad["models"]["rec"]
    with pytest.raises(ValueError):
        LocalOCRConfig.from_dict(bad)


@pytest.mark.parametrize(
    "mode,code",
    [
        ("missing", "OCR_MODEL_MISSING"),
        ("sha", "OCR_MODEL_SHA_MISMATCH"),
        ("relative", "OCR_MODEL_PATH_NOT_LOCAL"),
    ],
)
def test_model_failure_is_named_before_engine_or_download(
    tmp_path, monkeypatch, mode, code
):
    cfg = config(tmp_path)
    if mode == "missing":
        Path(cfg.det.path).unlink()
    if mode == "sha":
        cfg = replace(cfg, det=replace(cfg.det, sha256="b" * 64))
    if mode == "relative":
        cfg = replace(cfg, det=replace(cfg.det, path="remote.onnx"))

    def forbid(*a, **kw):
        raise AssertionError("network must never be reached")

    monkeypatch.setattr(socket, "create_connection", forbid)
    monkeypatch.setattr(socket.socket, "connect", forbid)
    with pytest.raises(LocalOCRError, match=code):
        LocalOCRAdapter(cfg).transcribe(tiny_png(), limits=OCRLimits())


def test_offline_engine_has_explicit_three_paths_embedded_dictionary_and_cpu(
    tmp_path, monkeypatch
):
    cfg = config(tmp_path)
    default = tmp_path / "config.yaml"
    default.write_bytes(b"pinned-defaults")
    cfg = replace(
        cfg, base_config_sha256=hashlib.sha256(default.read_bytes()).hexdigest()
    )
    captured = {}
    inferences = []

    def forbid(*a, **kw):
        raise AssertionError("network must never be reached")

    monkeypatch.setattr(socket, "create_connection", forbid)
    monkeypatch.setattr(socket.socket, "connect", forbid)
    monkeypatch.setattr(
        "importlib.metadata.version",
        lambda name: cfg.engine_version if name == "rapidocr" else cfg.runtime_version,
    )

    class EngineType(Enum):
        ONNX = "onnxruntime"

    class Engine:
        def __init__(self, *, params):
            captured.update(params)

        def __call__(self, image):
            inferences.append(1)
            assert image.mode == "RGB" and image.size == (1, 1)
            return SimpleNamespace(
                txts=["Local body"],
                scores=[0.95555555],
                boxes=[[(0, 0), (1, 0), (1, 1), (0, 1)]],
            )

    class Session:
        def __init__(self, path, *, sess_options, providers):
            assert path == cfg.rec.path and providers == ["CPUExecutionProvider"]

        def get_modelmeta(self):
            return SimpleNamespace(custom_metadata_map={"character": "abc"})

    monkeypatch.setitem(
        sys.modules,
        "rapidocr",
        SimpleNamespace(
            __file__=str(tmp_path / "__init__.py"),
            RapidOCR=Engine,
            EngineType=EngineType,
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "onnxruntime",
        SimpleNamespace(SessionOptions=SimpleNamespace, InferenceSession=Session),
    )
    adapter = LocalOCRAdapter(cfg)
    adapter.validate_environment()
    assert not inferences
    result = adapter.transcribe(tiny_png(), limits=OCRLimits())
    assert inferences == [1]
    assert result.lines[0].confidence == 0.955556
    for name in ("Det", "Cls", "Rec"):
        assert captured[name + ".model_path"] == getattr(cfg, name.lower()).path
        assert captured[name + ".engine_type"] is EngineType.ONNX
    assert all(
        captured["EngineConfig.onnxruntime." + name] is False
        for name in ("use_cuda", "use_dml", "use_cann", "use_coreml")
    )
    # Dictionary fallback is forbidden, even with all three model files present.
    Session.get_modelmeta = lambda self: SimpleNamespace(custom_metadata_map={})
    with pytest.raises(LocalOCRError, match="OCR_CHARACTER_DICTIONARY_MISSING"):
        LocalOCRAdapter(cfg).transcribe(tiny_png(), limits=OCRLimits())


def test_corrupt_image_pixel_and_result_bounds(tmp_path):
    from PIL import Image
    import io

    with pytest.raises(LocalOCRError, match="OCR_IMAGE_INVALID"):
        image_dimensions(b"bad image", OCRLimits())
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2)).save(buffer, format="PNG")
    with pytest.raises(NormalizationLimitError, match="max_image_pixels"):
        image_dimensions(buffer.getvalue(), OCRLimits(max_image_pixels=3))
    with pytest.raises(LocalOCRError, match="OCR_BOX_OUTSIDE_IMAGE"):
        ImageOCRResult(1, 1, (OCRLine("body", (0, 0, 2, 1), 0.9),))
    for confidence in (-1, float("nan"), True, 1.1):
        with pytest.raises(LocalOCRError, match="OCR_CONFIDENCE_INVALID"):
            OCRLine("body", (0, 0, 1, 1), confidence)


def test_soft_deadline_checks_native_return_without_a_success_result(tmp_path):
    adapter = LocalOCRAdapter(config(tmp_path))

    def slow(image):
        time.sleep(0.03)
        return SimpleNamespace(txts=[], scores=[], boxes=[])

    adapter._engine = slow
    with pytest.raises(NormalizationLimitError, match="deadline"):
        adapter.transcribe(
            tiny_png(), limits=OCRLimits(deadline=time.monotonic() + 0.01)
        )


def test_engine_runs_with_score_floor_and_reports_dropped_regions(tmp_path, monkeypatch):
    cfg = config(tmp_path)
    default = tmp_path / "config.yaml"
    default.write_bytes(b"pinned-defaults")
    cfg = replace(cfg, base_config_sha256=hashlib.sha256(default.read_bytes()).hexdigest())
    captured = {}

    def forbid(*a, **kw):
        raise AssertionError("network must never be reached")

    monkeypatch.setattr(socket, "create_connection", forbid)
    monkeypatch.setattr(socket.socket, "connect", forbid)
    monkeypatch.setattr(
        "importlib.metadata.version",
        lambda name: cfg.engine_version if name == "rapidocr" else cfg.runtime_version,
    )

    from enum import Enum

    class EngineType(Enum):
        ONNX = "onnxruntime"

    width, height = 4, 3

    class Engine:
        def __init__(self, *, params):
            captured.update(params)

        def __call__(self, image):
            assert image.size == (width, height)
            return SimpleNamespace(
                txts=[
                    "FY27 Segment changes",
                    " l s    os    i  a i  s o o  on l ",
                    "·",
                ],
                scores=[0.99363, 0.43236, 0.45808],
                boxes=[
                    [(0, 0), (4, 0), (4, 1), (0, 1)],
                    [(0, 1), (4, 1), (4, 2), (0, 2)],
                    [(0, 2), (1, 2), (1, 3), (0, 3)],
                ],
            )

    class Session:
        def __init__(self, path, *, sess_options, providers):
            pass

        def get_modelmeta(self):
            return SimpleNamespace(custom_metadata_map={"character": "abc"})

    monkeypatch.setitem(
        sys.modules,
        "rapidocr",
        SimpleNamespace(
            __file__=str(tmp_path / "__init__.py"),
            RapidOCR=Engine,
            EngineType=EngineType,
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "onnxruntime",
        SimpleNamespace(SessionOptions=SimpleNamespace, InferenceSession=Session),
    )

    import io

    buffer = io.BytesIO()
    from PIL import Image

    Image.new("RGB", (width, height)).save(buffer, format="PNG")
    adapter = LocalOCRAdapter(cfg)
    result = adapter.transcribe(buffer.getvalue(), limits=OCRLimits())
    # Engine is constructed with a 0.0 floor; the configured threshold is the
    # adapter's own filter so dropped regions stay observable.
    assert captured["Global.text_score"] == 0.0
    assert [line.text for line in result.lines] == ["FY27 Segment changes"]
    diagnostics = result.region_diagnostics
    assert diagnostics is not None
    assert diagnostics.detected is None  # not observable at this backend seam
    assert diagnostics.recognized == 3
    assert diagnostics.accepted == 1
    assert [r.confidence for r in diagnostics.dropped] == [0.43236, 0.45808]
    assert [r.reason for r in diagnostics.dropped] == ["low_text_score", "low_text_score"]
    assert diagnostics.dropped[0].text == "l s os i a i s o o on l"  # normalized garble, diagnostic only
    assert diagnostics.dropped[0].box == (0.0, 1.0, 4.0, 2.0)
    manifest = adapter.identity_manifest
    assert manifest["region_diagnostics"] == "cwp-ocr-region-diagnostics/1"
    assert manifest["engine_text_score_floor"] == 0.0
    assert manifest["region_recovery"] == "cwp-ocr-region-recovery/1"


def test_legacy_three_argument_result_and_diagnostics_validation():
    legacy = ImageOCRResult(1, 1, ())
    assert legacy.region_diagnostics is None
    empty = ImageOCRResult(
        1, 1, (), OCRRegionDiagnostics(detected=None, recognized=0, accepted=0)
    )
    assert empty.region_diagnostics.dropped == ()
    assert empty.region_diagnostics.to_dict()["schema_version"] == "cwp-ocr-region-diagnostics/1"
    with pytest.raises(LocalOCRError, match="OCR_BOX_OUTSIDE_IMAGE"):
        ImageOCRResult(
            4,
            4,
            (),
            OCRRegionDiagnostics(
                detected=None,
                recognized=1,
                accepted=0,
                dropped=(OCRDroppedRegion((0, 0, 9, 2), 0.4, "x", "low_text_score"),),
            ),
        )
    for bad_counts in (-1, True, 1.5):
        with pytest.raises(LocalOCRError, match="OCR_DIAGNOSTICS_INVALID"):
            OCRRegionDiagnostics(bad_counts if bad_counts != 1.5 else None, bad_counts, bad_counts)
    with pytest.raises(LocalOCRError, match="OCR_BOX_INVALID"):
        OCRDroppedRegion((2, 0, 1, 4), 0.4, "x", "low_text_score")
    with pytest.raises(LocalOCRError, match="OCR_CONFIDENCE_INVALID"):
        OCRDroppedRegion((0, 0, 2, 2), 1.4, "x", "low_text_score")
    with pytest.raises(LocalOCRError, match="OCR_DROP_REASON_INVALID"):
        OCRDroppedRegion((0, 0, 2, 2), 0.4, "x", "")
    with pytest.raises(LocalOCRError, match="OCR_RECOVERY_RECORD_INVALID"):
        OCRRegionRecovery((0, 0, 2, 2), "recovered", recovered_text=None)
    with pytest.raises(LocalOCRError, match="OCR_RECOVERY_RECORD_INVALID"):
        OCRRecoveryAttempt("t/1", {}, "accepted", error="OCR_IMAGE_INVALID")
    record = OCRRegionRecovery(
        (0, 0, 2, 2),
        "recovered",
        (OCRRecoveryAttempt(
            "roi-margin-crop/1",
            {"margin_ratio": 0.35},
            "accepted",
            (("recovered text", 0.99),),
        ),),
        recovered_text="recovered text",
        recovered_box=(0, 0, 2, 2),
        recovered_confidence=0.99,
    )
    as_dict = record.to_dict()
    assert as_dict["attempts"][0]["transform"] == "roi-margin-crop/1"
    assert as_dict["recovered_confidence"] == 0.99


def test_parent_hard_deadline_kills_noncooperative_ocr_before_publish(tmp_path):
    import base64

    source = build_pptx(with_picture_only_slide=True)
    ready = tmp_path / "entered-native"
    published = tmp_path / "success.json"
    script = """
import hashlib,json,sys,time
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from company_wiki.document_normalization import normalize_document
from company_wiki.document_normalization.local_ocr import ImageOCRResult
class Blocking:
    identity_manifest={"adapter":"blocking-test/1"}
    fingerprint=hashlib.sha256(json.dumps(identity_manifest,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    def transcribe(self,data,*,limits):
        Path(sys.argv[2]).write_text("entered")
        time.sleep(30)
        return ImageOCRResult(1,1,())
import base64
data=base64.b64decode(sys.stdin.read())
doc=normalize_document(data,source_id="urn:company-wiki:source:sha256:"+hashlib.sha256(data).hexdigest(),source_sha256=hashlib.sha256(data).hexdigest(),mime_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",ocr=Blocking())
Path(sys.argv[3]).write_text(json.dumps({"success":True}))
"""
    with pytest.raises(subprocess.TimeoutExpired):
        subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                script,
                str(Path(__file__).resolve().parents[2] / "src"),
                str(ready),
                str(published),
            ],
            input=base64.b64encode(source).decode(),
            text=True,
            capture_output=True,
            # Cold interpreter import on Windows can exceed 2s under disk/AV
            # load; the child still blocks for 30s, so any TimeoutExpired here
            # proves the parent killed a non-cooperative OCR before publish.
            timeout=20,
            check=True,
        )
    assert ready.read_text() == "entered"
    assert not published.exists()
