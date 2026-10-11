"""Explicit local normalization composition; parsers remain deployment independent."""

from __future__ import annotations
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
from company_wiki import document_normalization as dn
from company_wiki.document_normalization.units import require_parser_version

PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


class NarrativeNormalization:
    """Own one immutable config and one lazy adapter in the calling process."""

    def __init__(
        self, config=None, *, adapter_factory=None, deadline=None, parser_versions=None
    ):
        if config is not None and not isinstance(config, dn.LocalOCRConfig):
            raise TypeError("normalization config must be LocalOCRConfig")
        if deadline is not None and (
            isinstance(deadline, bool)
            or not isinstance(deadline, (int, float))
            or not math.isfinite(deadline)
        ):
            raise ValueError("normalization deadline must be finite")
        if parser_versions is not None and (
            not isinstance(parser_versions, dict)
            or any(
                not isinstance(k, str)
                or not k
                or not isinstance(v, str)
                or v not in {"1.0.0", "1.1.0", "2.0.0"}
                for k, v in parser_versions.items()
            )
        ):
            raise ValueError("NARRATIVE_NORMALIZATION_OPTIONS_INVALID")
        self.config = config
        self.deadline = deadline
        self.parser_versions = dict(parser_versions or {})
        self._adapter_factory = adapter_factory or dn.LocalOCRAdapter
        self._adapter = None
        self._validated = False

    @classmethod
    def from_snapshot(cls, snapshot, **kwargs):
        return cls(
            None if snapshot is None else dn.LocalOCRConfig.from_dict(snapshot),
            **kwargs,
        )

    @classmethod
    def from_project(cls, project_root, *, enabled=True, **kwargs):
        path = Path(project_root) / "config/local_ocr.json"
        if not enabled or not path.exists():
            return cls(**kwargs)
        with path.open("rb") as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError("OCR_CONFIG_TOO_LARGE")
        return cls.from_snapshot(json.loads(raw.decode("utf-8")), **kwargs)

    @classmethod
    def from_reader(cls, reader, *, enabled=True, **kwargs):
        catalog = getattr(reader, "catalog", None)
        return (
            cls.from_project(catalog.config.project_root, enabled=enabled, **kwargs)
            if catalog is not None
            else cls(**kwargs)
        )

    def snapshot(self):
        return None if self.config is None else self.config.to_dict()

    @property
    def ocr_adapter(self):
        if self.config is None:
            return None
        if self._adapter is None:
            self._adapter = self._adapter_factory(self.config)
        return self._adapter

    def _prepare_ocr(self):
        adapter = self.ocr_adapter
        if adapter is None:
            raise dn.LocalOCRError("OCR_ADAPTER_REQUIRED")
        if not self._validated:
            adapter.validate_environment()
            self._validated = True
        return adapter

    def identity(self, mime_type, *, document_id=None, parser_version=None):
        version = parser_version or self.parser_versions.get(document_id)
        pptx = mime_type.split(";")[0].strip().lower() == PPTX_MIME
        format_identity = dn.normalization_identity(mime_type)
        if version is not None:
            try:
                require_parser_version(format_identity["format"], version)
            except ValueError as exc:
                raise ValueError("unsupported normalization parser") from exc
        use_ocr = pptx and (
            version == "2.0.0" or version is None and self.config is not None
        )
        if use_ocr and self.config is None:
            raise dn.LocalOCRError("OCR_ADAPTER_REQUIRED")
        identity = dn.normalization_identity(
            mime_type, ocr=self.config if use_ocr else None
        )
        if version is not None:
            identity["parser_version"] = version
        return identity

    def normalize(
        self,
        data,
        *,
        source_id,
        source_sha256,
        mime_type,
        document_id=None,
        parser_version=None,
    ):
        identity = self.identity(
            mime_type, document_id=document_id, parser_version=parser_version
        )
        adapter = self._prepare_ocr() if identity["parser_version"] == "2.0.0" else None
        return dn.normalize_document(
            data,
            source_id=source_id,
            source_sha256=source_sha256,
            mime_type=mime_type,
            parser_version=identity["parser_version"],
            limits=dn.NormalizationLimits(deadline=self.deadline),
            ocr=adapter,
            ocr_limits=dn.OCRLimits(deadline=self.deadline) if adapter else None,
        )

    def replay(
        self,
        data,
        *,
        source_id,
        source_sha256,
        mime_type,
        evidence_spans,
        language=None,
        parser_version=None,
    ):
        spans = tuple(evidence_spans)
        version = spans[0].parser_version if spans else parser_version
        identity = self.identity(mime_type, parser_version=version)
        if any(
            span.parser_name != identity["parser_name"]
            or span.parser_version != identity["parser_version"]
            or "low_ocr_confidence" in span.quality_flags
            or "locator_unstable" in span.quality_flags
            or language is not None
            and span.structured_value.get("language") != language
            for span in spans
        ):
            raise dn.ReplayError("selected parser/language/quality is not reliable")
        if not spans:
            document = self.normalize(
                data,
                source_id=source_id,
                source_sha256=source_sha256,
                mime_type=mime_type,
                parser_version=version,
            )
            if not document.structure.coverage_complete:
                raise dn.ReplayError(
                    "empty selection requires complete source coverage"
                )
            return 0
        adapter = self._prepare_ocr() if version == "2.0.0" else None
        return dn.replay_evidence_spans(
            data,
            source_id=source_id,
            source_sha256=source_sha256,
            mime_type=mime_type,
            evidence_spans=spans,
            limits=dn.NormalizationLimits(deadline=self.deadline),
            ocr=adapter,
            ocr_limits=dn.OCRLimits(deadline=self.deadline) if adapter else None,
        )

    def sample_text(self, data, mime_type, *, max_images=3):
        """Use native text first, then at most three verified unique image samples."""
        digest = hashlib.sha256(data).hexdigest()
        source_id = "urn:company-wiki:source:sha256:" + digest
        document = dn.normalize_document(
            data,
            source_id=source_id,
            source_sha256=digest,
            mime_type=mime_type,
            limits=dn.NormalizationLimits(deadline=self.deadline),
        )
        text = "\n".join(unit.raw_text for unit in document.units)[:100000]
        from .narrative_language import (
            detect_narrative_text_language,
            NarrativeLanguageError,
        )

        try:
            detect_narrative_text_language(text)
            return text
        except NarrativeLanguageError as exc:
            if exc.code != "SOURCE_LANGUAGE_UNDETERMINED":
                raise
        if self.config is None:
            return text
        adapter = self._prepare_ocr()
        seen: set[str] = set()
        total_pixels = 0
        limits = dn.OCRLimits(max_images=max_images, deadline=self.deadline)
        from company_wiki.document_normalization.local_ocr import image_dimensions

        for asset in document.opaque_assets:
            if (
                asset.asset_kind != "image"
                or asset.original_bytes is None
                or asset.media_sha256 in seen
            ):
                continue
            if len(seen) >= max_images:
                break
            seen.add(asset.media_sha256)
            if hashlib.sha256(asset.original_bytes).hexdigest() != asset.media_sha256:
                raise dn.LocalOCRError("OCR_MEDIA_SHA_MISMATCH")
            width, height = image_dimensions(asset.original_bytes, limits)
            total_pixels += width * height
            limits.require_within("max_total_pixels", total_pixels)
            try:
                result = adapter.transcribe(asset.original_bytes, limits=limits)
            except dn.LocalOCRError:
                continue
            text += "\n" + "\n".join(
                line.text
                for line in result.lines
                if line.confidence >= self.config.low_confidence_threshold
            )
            if len(text) >= 100000:
                break
        return text[:100000]

    @staticmethod
    def language_structure(document, language):
        """Keep honest source diagnostics; remove unreliable text from candidates."""
        quality = {
            "coverage_complete": document.structure.coverage_complete,
            "opaque_pages": list(document.structure.opaque_pages),
            "errors": list(document.structure.errors),
        }
        if "ocr" in document.metadata:
            ocr = document.metadata["ocr"]
            quality["ocr"] = {
                "fingerprint": ocr["fingerprint"],
                "recall_status": ocr["recall_status"],
                "unattempted_image_pages": list(ocr["unattempted_image_pages"]),
                "page_statuses": {
                    str(page["page_number"]): page["status"] for page in ocr["pages"]
                },
            }
        units = tuple(
            replace(
                unit,
                language=language,
                metadata={**unit.metadata, "normalization_quality": quality},
            )
            for unit in document.units
            if not {"low_ocr_confidence", "locator_unstable"}.intersection(
                unit.quality_flags
            )
        )
        return replace(document.structure, language=language, units=units)
