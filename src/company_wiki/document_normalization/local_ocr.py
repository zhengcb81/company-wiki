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
            **parsed,
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
                "Global.text_score": self.config.text_score,
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
                result = self._engine(pixels)
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
        for text, score, points in zip(texts, scores, boxes, strict=True):
            text = normalize_text(text)
            if not text:
                continue
            box = (
                max(0.0, float(min(p[0] for p in points))),
                max(0.0, float(min(p[1] for p in points))),
                min(float(width), float(max(p[0] for p in points))),
                min(float(height), float(max(p[1] for p in points))),
            )
            lines.append(
                OCRLine(text, tuple(round(v, 3) for v in box), round(float(score), 6))
            )
        lines.sort(
            key=lambda line: (
                line.box[1],
                line.box[0],
                line.box[3],
                line.box[2],
                line.text,
            )
        )
        return ImageOCRResult(width, height, tuple(lines))
