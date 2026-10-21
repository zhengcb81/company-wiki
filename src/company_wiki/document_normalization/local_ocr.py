"""Explicit CPU-only OCR over local model bytes; no downloads or providers."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.metadata
import io
import json
import math
from pathlib import Path
import re
from typing import Protocol

from .errors import NormalizationError, NormalizationLimitError
from .text import normalize_text

SHA = re.compile(r"[0-9a-f]{64}\Z")


class LocalOCRError(NormalizationError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _positive(value, name):
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True)
class OCRLimits:
    max_image_pixels: int = 16_000_000
    max_total_pixels: int = 96_000_000
    max_images: int = 100
    deadline: float | None = None

    def __post_init__(self):
        for name in ("max_image_pixels", "max_total_pixels", "max_images"):
            _positive(getattr(self, name), name)
        if self.deadline is not None and (
            isinstance(self.deadline, bool)
            or not isinstance(self.deadline, (int, float))
            or not math.isfinite(self.deadline)
        ):
            raise ValueError("deadline must be finite")

    def check_deadline(self):
        import time

        if self.deadline is not None and time.monotonic() >= self.deadline:
            raise NormalizationLimitError("deadline", self.deadline, "local OCR")

    def require_within(self, name, value):
        if value > getattr(self, name):
            raise NormalizationLimitError(name, getattr(self, name), "local OCR")


OCR_REGION_DIAGNOSTICS_SCHEMA = "cwp-ocr-region-diagnostics/1"
OCR_REGION_RECOVERY_SCHEMA = "cwp-ocr-region-recovery/1"
# The engine is constructed with this floor instead of the configured
# text_score so score-filtered regions stay observable; the adapter applies
# the configured threshold itself.
ENGINE_TEXT_SCORE_FLOOR = 0.0

_RECOVERY_STATUSES = frozenset(
    {"recovered", "unrecovered", "budget_exhausted", "not_attempted"}
)
_ATTEMPT_OUTCOMES = frozenset({"accepted", "rejected", "error"})


def _checked_box(value, error_code: str):
    if len(value) != 4 or any(
        isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
        for v in value
    ):
        raise LocalOCRError(error_code)
    x0, y0, x1, y1 = value
    if x0 < 0 or y0 < 0 or x1 <= x0 or y1 <= y0:
        raise LocalOCRError(error_code)
    return tuple(float(v) for v in value)


def _checked_confidence(value, error_code: str):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not 0 <= value <= 1
    ):
        raise LocalOCRError(error_code)
    return float(value)


@dataclass(frozen=True)
class OCRDroppedRegion:
    """One recognizer region removed by score filtering; diagnostic only.

    ``text`` keeps the garbled recognizer output for diagnosis.  It never
    becomes an OCRLine, unit text or evidence span.
    """

    box: tuple[float, float, float, float]
    confidence: float
    text: str
    reason: str

    def __post_init__(self):
        object.__setattr__(self, "box", _checked_box(self.box, "OCR_BOX_INVALID"))
        object.__setattr__(
            self, "confidence", _checked_confidence(self.confidence, "OCR_CONFIDENCE_INVALID")
        )
        if not isinstance(self.text, str) or not self.text:
            raise LocalOCRError("OCR_TEXT_INVALID")
        if not isinstance(self.reason, str) or not self.reason:
            raise LocalOCRError("OCR_DROP_REASON_INVALID")


@dataclass(frozen=True)
class OCRRecoveryAttempt:
    """One bounded re-recognition attempt over a deterministic transform."""

    transform: str
    params: dict
    outcome: str
    lines: tuple[tuple[str, float], ...] = ()
    error: str | None = None
    note: str | None = None

    def __post_init__(self):
        if not isinstance(self.transform, str) or not self.transform:
            raise LocalOCRError("OCR_RECOVERY_RECORD_INVALID")
        if not isinstance(self.params, dict):
            raise LocalOCRError("OCR_RECOVERY_RECORD_INVALID")
        if self.outcome not in _ATTEMPT_OUTCOMES:
            raise LocalOCRError("OCR_RECOVERY_RECORD_INVALID")
        if (self.outcome == "error") != (self.error is not None):
            raise LocalOCRError("OCR_RECOVERY_RECORD_INVALID")
        checked = []
        for text, score in self.lines:
            if not isinstance(text, str) or not isinstance(score, (int, float)):
                raise LocalOCRError("OCR_RECOVERY_RECORD_INVALID")
            checked.append((text, float(score)))
        object.__setattr__(self, "lines", tuple(checked))
        if self.error is not None and (not isinstance(self.error, str) or not self.error):
            raise LocalOCRError("OCR_RECOVERY_RECORD_INVALID")
        if self.note is not None and (not isinstance(self.note, str) or not self.note):
            raise LocalOCRError("OCR_RECOVERY_RECORD_INVALID")


@dataclass(frozen=True)
class OCRRegionRecovery:
    """Per-dropped-region recovery status and its attempt records."""

    box: tuple[float, float, float, float]
    status: str
    attempts: tuple[OCRRecoveryAttempt, ...] = ()
    recovered_text: str | None = None
    recovered_box: tuple[float, float, float, float] | None = None
    recovered_confidence: float | None = None

    def __post_init__(self):
        object.__setattr__(self, "box", _checked_box(self.box, "OCR_BOX_INVALID"))
        if self.status not in _RECOVERY_STATUSES:
            raise LocalOCRError("OCR_RECOVERY_RECORD_INVALID")
        for attempt in self.attempts:
            if not isinstance(attempt, OCRRecoveryAttempt):
                raise LocalOCRError("OCR_RECOVERY_RECORD_INVALID")
        if self.status == "recovered":
            if (
                not isinstance(self.recovered_text, str)
                or not self.recovered_text
                or self.recovered_box is None
                or self.recovered_confidence is None
            ):
                raise LocalOCRError("OCR_RECOVERY_RECORD_INVALID")
        if self.recovered_box is not None:
            object.__setattr__(
                self, "recovered_box", _checked_box(self.recovered_box, "OCR_BOX_INVALID")
            )
        if self.recovered_confidence is not None:
            object.__setattr__(
                self,
                "recovered_confidence",
                _checked_confidence(
                    self.recovered_confidence, "OCR_CONFIDENCE_INVALID"
                ),
            )
        object.__setattr__(self, "attempts", tuple(self.attempts))

    def to_dict(self):
        return {
            "box": list(self.box),
            "status": self.status,
            "attempts": [
                {
                    "transform": a.transform,
                    "params": a.params,
                    "outcome": a.outcome,
                    "lines": [[t, s] for t, s in a.lines],
                    "error": a.error,
                    "note": a.note,
                }
                for a in self.attempts
            ],
            "recovered_text": self.recovered_text,
            "recovered_box": None if self.recovered_box is None else list(self.recovered_box),
            "recovered_confidence": self.recovered_confidence,
        }


@dataclass(frozen=True)
class OCRRegionDiagnostics:
    """Stage counts plus regions lost to backend score filtering.

    ``detected`` is ``None`` when the backend seam cannot observe the
    pre-recognition count.  ``recognized`` never implies exhaustive recall.
    """

    detected: int | None
    recognized: int | None
    accepted: int | None
    dropped: tuple[OCRDroppedRegion, ...] = ()
    recovery: tuple[OCRRegionRecovery, ...] = ()

    def __post_init__(self):
        for name in ("detected", "recognized", "accepted"):
            value = getattr(self, name)
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value < 0
            ):
                raise LocalOCRError("OCR_DIAGNOSTICS_INVALID")
        for seq, kind in ((self.dropped, OCRDroppedRegion), (self.recovery, OCRRegionRecovery)):
            for item in seq:
                if not isinstance(item, kind):
                    raise LocalOCRError("OCR_DIAGNOSTICS_INVALID")
        object.__setattr__(self, "dropped", tuple(self.dropped))
        object.__setattr__(self, "recovery", tuple(self.recovery))

    def to_dict(self):
        return {
            "schema_version": OCR_REGION_DIAGNOSTICS_SCHEMA,
            "detected": self.detected,
            "recognized": self.recognized,
            "accepted": self.accepted,
            "dropped": [
                {
                    "box": list(r.box),
                    "confidence": r.confidence,
                    "text": r.text,
                    "reason": r.reason,
                }
                for r in self.dropped
            ],
            "recovery": [r.to_dict() for r in self.recovery],
        }


@dataclass(frozen=True)
class OCRLine:
    text: str
    box: tuple[float, float, float, float]
    confidence: float

    def __post_init__(self):
        if not self.text or self.text != normalize_text(self.text):
            raise LocalOCRError("OCR_TEXT_INVALID")
        if len(self.box) != 4 or any(
            isinstance(v, bool)
            or not isinstance(v, (int, float))
            or not math.isfinite(v)
            for v in self.box
        ):
            raise LocalOCRError("OCR_BOX_INVALID")
        x0, y0, x1, y1 = self.box
        if x0 < 0 or y0 < 0 or x1 <= x0 or y1 <= y0:
            raise LocalOCRError("OCR_BOX_INVALID")
        if (
            isinstance(self.confidence, bool)
            or not isinstance(self.confidence, (int, float))
            or not math.isfinite(self.confidence)
            or not 0 <= self.confidence <= 1
        ):
            raise LocalOCRError("OCR_CONFIDENCE_INVALID")
        object.__setattr__(self, "box", tuple(float(v) for v in self.box))
        object.__setattr__(self, "confidence", float(self.confidence))


@dataclass(frozen=True)
class ImageOCRResult:
    width: int
    height: int
    lines: tuple[OCRLine, ...]
    region_diagnostics: OCRRegionDiagnostics | None = None

    def __post_init__(self):
        _positive(self.width, "width")
        _positive(self.height, "height")
        for line in self.lines:
            if (
                not isinstance(line, OCRLine)
                or line.box[2] > self.width
                or line.box[3] > self.height
            ):
                raise LocalOCRError("OCR_BOX_OUTSIDE_IMAGE")
        diagnostics = self.region_diagnostics
        if diagnostics is not None:
            if not isinstance(diagnostics, OCRRegionDiagnostics):
                raise LocalOCRError("OCR_DIAGNOSTICS_INVALID")
            for record in (
                *(r.box for r in diagnostics.dropped),
                *(r.box for r in diagnostics.recovery),
                *(
                    box
                    for r in diagnostics.recovery
                    if r.recovered_box is not None
                    for box in (r.recovered_box,)
                ),
            ):
                if record[2] > self.width or record[3] > self.height:
                    raise LocalOCRError("OCR_BOX_OUTSIDE_IMAGE")
        object.__setattr__(self, "lines", tuple(self.lines))


class OCRAdapter(Protocol):
    identity_manifest: dict
    fingerprint: str

    def transcribe(self, data: bytes, *, limits: OCRLimits) -> ImageOCRResult: ...


@dataclass(frozen=True)
class OCRModelFile:
    path: str
    sha256: str

    def __post_init__(self):
        if (
            not isinstance(self.path, str)
            or not self.path
            or not isinstance(self.sha256, str)
            or not SHA.fullmatch(self.sha256)
        ):
            raise ValueError("explicit local model path and SHA-256 required")

    def verify(self):
        p = Path(self.path)
        if not p.is_absolute() or self.path.startswith(("\\\\", "//")):
            raise LocalOCRError("OCR_MODEL_PATH_NOT_LOCAL")
        if not p.is_file():
            raise LocalOCRError("OCR_MODEL_MISSING")
        digest = hashlib.sha256()
        with p.open("rb") as model:
            for chunk in iter(lambda: model.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != self.sha256:
            raise LocalOCRError("OCR_MODEL_SHA_MISMATCH")


@dataclass(frozen=True)
class LocalOCRConfig:
    det: OCRModelFile
    cls: OCRModelFile
    rec: OCRModelFile
    engine_version: str
    runtime_version: str
    base_config_sha256: str
    text_score: float = 0.5
    low_confidence_threshold: float = 0.8
    max_side_len: int = 3000
    intra_op_threads: int = 2
    inter_op_threads: int = 1

    def __post_init__(self):
        for m in (self.det, self.cls, self.rec):
            if not isinstance(m, OCRModelFile):
                raise TypeError("models must be OCRModelFile")
        if (
            not isinstance(self.engine_version, str)
            or not self.engine_version
            or not isinstance(self.runtime_version, str)
            or not self.runtime_version
            or not isinstance(self.base_config_sha256, str)
            or not SHA.fullmatch(self.base_config_sha256)
        ):
            raise ValueError("exact engine/runtime/default config versions required")
        for name in ("max_side_len", "intra_op_threads", "inter_op_threads"):
            _positive(getattr(self, name), name)
        for value in (self.text_score, self.low_confidence_threshold):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or not 0 <= value <= 1
            ):
                raise ValueError("confidence thresholds must be within [0,1]")

    @property
    def identity_manifest(self):
        return {
            "schema_version": "cwp-local-ocr-config/1",
            "adapter": "rapidocr-cpu/1",
            "engine_version": self.engine_version,
            "runtime_version": self.runtime_version,
            "base_config_sha256": self.base_config_sha256,
            "models": {k: getattr(self, k).sha256 for k in ("det", "cls", "rec")},
            "device": "cpu",
            "text_score": self.text_score,
            "low_confidence_threshold": self.low_confidence_threshold,
            "max_side_len": self.max_side_len,
            "intra_op_threads": self.intra_op_threads,
            "inter_op_threads": self.inter_op_threads,
            "box_round_decimals": 3,
            "confidence_round_decimals": 6,
            "reading_order": "top-left-box/1",
            "transform": "rapidocr-image-rgb/1",
            # Region diagnostics/recovery seam (W05): the engine is constructed
            # with a 0.0 text_score floor and the configured threshold is applied
            # inside this adapter so dropped regions stay observable.  Bump these
            # schema strings whenever the diagnostic or recovery algorithm changes;
            # the fingerprint (cache identity) changes with them.
            "region_diagnostics": OCR_REGION_DIAGNOSTICS_SCHEMA,
            "engine_text_score_floor": ENGINE_TEXT_SCORE_FLOOR,
            "region_recovery": OCR_REGION_RECOVERY_SCHEMA,
            "region_recovery_algorithm": "bounded-source-roi/2",
        }

    @property
    def fingerprint(self):
        return hashlib.sha256(
            json.dumps(
                self.identity_manifest,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode()
        ).hexdigest()

    def to_dict(self):
        return {
            **{
                k: getattr(self, k)
                for k in (
                    "engine_version",
                    "runtime_version",
                    "base_config_sha256",
                    "text_score",
                    "low_confidence_threshold",
                    "max_side_len",
                    "intra_op_threads",
                    "inter_op_threads",
                )
            },
            "schema_version": "cwp-local-ocr-config/1",
            "models": {
                k: {"path": getattr(self, k).path, "sha256": getattr(self, k).sha256}
                for k in ("det", "cls", "rec")
            },
        }

    @classmethod
    def from_dict(cls, value):
        keys = {
            "schema_version",
            "models",
            "engine_version",
            "runtime_version",
            "base_config_sha256",
            "text_score",
            "low_confidence_threshold",
            "max_side_len",
            "intra_op_threads",
            "inter_op_threads",
        }
        if (
            not isinstance(value, dict)
            or set(value) != keys
            or value["schema_version"] != "cwp-local-ocr-config/1"
        ):
            raise ValueError("unsupported local OCR configuration")
        models = value["models"]
        if not isinstance(models, dict) or set(models) != {"det", "cls", "rec"}:
            raise ValueError("explicit three models required")
        parsed = {}
        for k, v in models.items():
            if not isinstance(v, dict) or set(v) != {"path", "sha256"}:
                raise ValueError("invalid model config")
            parsed[k] = OCRModelFile(**v)
        return cls(
            det=parsed["det"], cls=parsed["cls"], rec=parsed["rec"],
            **{k: v for k, v in value.items() if k not in {"schema_version", "models"}},
        )


def image_dimensions(data: bytes, limits: OCRLimits):
    limits.check_deadline()
    try:
        from PIL import Image

        with Image.open(io.BytesIO(data)) as image:
            width, height = image.size
            limits.require_within("max_image_pixels", width * height)
            if getattr(image, "n_frames", 1) != 1:
                raise LocalOCRError("OCR_MULTIFRAME_IMAGE_UNSUPPORTED")
            return width, height
    except (ImportError, ModuleNotFoundError):
        raise LocalOCRError("OCR_DEPENDENCY_MISSING") from None
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        if isinstance(exc, NormalizationError):
            raise
        raise LocalOCRError("OCR_IMAGE_INVALID") from None


class LocalOCRAdapter:
    def __init__(self, config: LocalOCRConfig):
        self.config = config
        self.identity_manifest = config.identity_manifest
        self.fingerprint = config.fingerprint
        self._engine = None

    def _load_engine(self):
        for model in (self.config.det, self.config.cls, self.config.rec):
            model.verify()
        try:
            if (
                importlib.metadata.version("rapidocr") != self.config.engine_version
                or importlib.metadata.version("onnxruntime")
                != self.config.runtime_version
            ):
                raise LocalOCRError("OCR_RUNTIME_VERSION_MISMATCH")
            import rapidocr
            import onnxruntime as ort
        except (ImportError, importlib.metadata.PackageNotFoundError):
            raise LocalOCRError("OCR_DEPENDENCY_MISSING") from None
        default = Path(rapidocr.__file__).parent / "config.yaml"
        if (
            not default.is_file()
            or hashlib.sha256(default.read_bytes()).hexdigest()
            != self.config.base_config_sha256
        ):
            raise LocalOCRError("OCR_DEFAULT_CONFIG_MISMATCH")
        # Require the ONNX embedded dictionary before RapidOCR can reach any
        # character-dictionary download fallback. Explicit paths bypass model downloads.
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = self.config.intra_op_threads
        opts.inter_op_num_threads = self.config.inter_op_threads
        rec = ort.InferenceSession(
            self.config.rec.path, sess_options=opts, providers=["CPUExecutionProvider"]
        )
        if not rec.get_modelmeta().custom_metadata_map.get("character"):
            raise LocalOCRError("OCR_CHARACTER_DICTIONARY_MISSING")
        del rec
        params = {
            k + ".model_path": getattr(self.config, k.lower()).path
            for k in ("Det", "Cls", "Rec")
        }
        params.update(
            {
                k + ".engine_type": rapidocr.EngineType("onnxruntime")
                for k in ("Det", "Cls", "Rec")
            }
        )
        params.update(
            {
                "Global.log_level": "warning",
                # 0.0 floor: the engine must not filter low-score regions away;
                # the configured threshold is applied inside transcribe() so the
                # dropped regions remain observable as diagnostics.
                "Global.text_score": ENGINE_TEXT_SCORE_FLOOR,
                "Global.max_side_len": self.config.max_side_len,
                "Global.return_word_box": False,
                "Global.return_single_char_box": False,
                "EngineConfig.onnxruntime.intra_op_num_threads": self.config.intra_op_threads,
                "EngineConfig.onnxruntime.inter_op_num_threads": self.config.inter_op_threads,
                **{
                    "EngineConfig.onnxruntime." + k: False
                    for k in ("use_cuda", "use_dml", "use_cann", "use_coreml")
                },
            }
        )
        try:
            self._engine = rapidocr.RapidOCR(params=params)
        except Exception:
            raise LocalOCRError("OCR_ENGINE_INIT_FAILED") from None

    def validate_environment(self) -> None:
        """Verify local hashes/runtime/dictionary and initialize CPU engines, no inference.

        Identity construction and from_dict stay free of I/O. An explicit parent
        composition preflight can call this; every worker still owns its engine.
        """
        if self._engine is None:
            self._load_engine()

    def transcribe(self, data: bytes, *, limits: OCRLimits):
        width, height = image_dimensions(data, limits)
        limits.check_deadline()
        self.validate_environment()
        limits.check_deadline()
        try:
            from PIL import Image

            with Image.open(io.BytesIO(data)) as image:
                pixels = image.convert("RGB")
                engine = self._engine
                if engine is None:
                    raise LocalOCRError("OCR_ENGINE_UNAVAILABLE")
                result = engine(pixels)
        except (OSError, ValueError):
            raise LocalOCRError("OCR_INFERENCE_FAILED") from None
        limits.check_deadline()  # Native ONNX is NOT cooperatively interruptible.
        try:
            texts = result.txts or ()
            scores = result.scores or ()
            boxes = result.boxes if result.boxes is not None else ()
        except AttributeError:
            raise LocalOCRError("OCR_RESULT_INVALID") from None
        if not (len(texts) == len(scores) == len(boxes)):
            raise LocalOCRError("OCR_RESULT_INVALID")
        lines = []
        dropped = []
        for text, score, points in zip(texts, scores, boxes, strict=True):
            text = normalize_text(text)
            if not text:
                continue
            box = (
                round(max(0.0, float(min(p[0] for p in points))), 3),
                round(max(0.0, float(min(p[1] for p in points))), 3),
                round(min(float(width), float(max(p[0] for p in points))), 3),
                round(min(float(height), float(max(p[1] for p in points))), 3),
            )
            score = round(float(score), 6)
            if score < self.config.text_score:
                # The engine runs with a 0.0 floor so filtered regions stay
                # observable here; the configured threshold is applied only by
                # this adapter.  Dropped text is diagnostic, never a line.
                dropped.append(
                    OCRDroppedRegion(box, score, text, "low_text_score")
                )
                continue
            lines.append(OCRLine(text, box, score))
        lines.sort(
            key=lambda line: (
                line.box[1],
                line.box[0],
                line.box[3],
                line.box[2],
                line.text,
            )
        )
        diagnostics = OCRRegionDiagnostics(
            detected=None,  # pre-recognition count is not observable at this seam
            recognized=len(texts),
            accepted=len(lines),
            dropped=tuple(dropped),
        )
        return ImageOCRResult(width, height, tuple(lines), diagnostics)
