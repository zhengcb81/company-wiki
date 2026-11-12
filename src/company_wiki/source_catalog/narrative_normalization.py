"""Explicit local normalization composition; parsers remain deployment independent."""

from __future__ import annotations
from collections.abc import Sequence
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
from typing import Any, TypedDict
from company_wiki import document_normalization as dn
from company_wiki.document_normalization.units import (
    require_parser_version,
    supported_parser_versions,
)
from company_wiki.document_normalization.isolated_ocr import IsolatedOCRAdapter
from company_wiki.source_contract import EvidenceSpan
from company_wiki.source_contract.source_version import VerifiedContent

PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


class _ParseOptions(TypedDict):
    limits: dn.NormalizationLimits
    ocr: Any
    ocr_limits: dn.OCRLimits | None


class NarrativeNormalization:
    """Own one immutable config and one lazy adapter in the calling process."""

    def __init__(
        self, config=None, *, adapter_factory=None, deadline=None, parser_versions=None,
        config_loader=None,
    ):
        if config is not None and not isinstance(config, dn.LocalOCRConfig):
            raise TypeError("normalization config must be LocalOCRConfig")
        if deadline is not None and (
            isinstance(deadline, bool)
            or not isinstance(deadline, (int, float))
            or not math.isfinite(deadline)
        ):
            raise ValueError("normalization deadline must be finite")
        supported_versions = supported_parser_versions()
        if parser_versions is not None and (
            not isinstance(parser_versions, dict)
            or any(
                not isinstance(k, str)
                or not k
                or not isinstance(v, str)
                or v not in supported_versions
                for k, v in parser_versions.items()
            )
        ):
            raise ValueError("NARRATIVE_NORMALIZATION_OPTIONS_INVALID")
        if config_loader is not None and not callable(config_loader):
            raise TypeError("normalization config loader must be callable")
        self._config = config
        self._config_loader = config_loader
        self._config_resolved = config is not None or config_loader is None
        self.deadline = deadline
        self.parser_versions = dict(parser_versions or {})
        self._adapter_factory = adapter_factory
        self._adapter = None
        self._validated = False

    @property
    def config(self):
        """The bound OCR config, read once and only when a caller needs it."""
        if not self._config_resolved:
            self._config_resolved = True
            loader = self._config_loader
            self._config = None if loader is None else loader()
        return self._config

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
            raw = stream.read()
        return cls.from_snapshot(json.loads(raw.decode("utf-8")), **kwargs)

    @classmethod
    def deferred_from_project(cls, project_root, **kwargs):
        """Bind the project OCR config now and read it only if a replay needs it.

        The caller owns the configuration location.  The file is opened at most
        once, and only when a normalization actually asks for the config, so a
        deployment without OCR work never touches the file.
        """
        path = Path(project_root) / "config/local_ocr.json"

        def load():
            if not path.exists():
                return None
            with path.open("rb") as stream:
                raw = stream.read()
            return dn.LocalOCRConfig.from_dict(json.loads(raw.decode("utf-8")))

        return cls(None, config_loader=load, **kwargs)

    def snapshot(self):
        return None if self.config is None else self.config.to_dict()

    @property
    def ocr_adapter(self):
        if self.config is None:
            return None
        if self._adapter is None:
            self._adapter = (
                IsolatedOCRAdapter(self.config, deadline=self.deadline)
                if self._adapter_factory is None
                else self._adapter_factory(self.config)
            )
        return self._adapter

    def _prepare_ocr(self):
        adapter = self.ocr_adapter
        if adapter is None:
            raise dn.LocalOCRError("OCR_ADAPTER_REQUIRED")
        if not self._validated:
            adapter.validate_environment()
            self._validated = True
        return adapter

    def close(self):
        """Release the configured native child; injected adapters stay compatible."""
        adapter, self._adapter = self._adapter, None
        self._validated = False
        closer = getattr(adapter, "close", None)
        if closer is not None:
            closer()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

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
        return dn.normalize_document(
            data,
            source_id=source_id,
            source_sha256=source_sha256,
            mime_type=mime_type,
            parser_version=identity["parser_version"],
            **self._parse_options(identity["parser_version"]),
        )

    def normalize_verified(
        self, content: VerifiedContent, *, mime_type: str, parser_version: str | None = None,
    ) -> dn.NormalizedDocument:
        """Normalize a source-owner buffer using the configured parser generation."""
        if type(self).normalize is not NarrativeNormalization.normalize:
            options = {"parser_version": parser_version} if parser_version is not None else {}
            return self.normalize(
                content.data, source_id=content.source_id, source_sha256=content.content_sha256,
                mime_type=mime_type, document_id=content.document_id, **options,
            )
        identity = self.identity(
            mime_type, document_id=content.document_id, parser_version=parser_version,
        )
        return dn.normalize_verified_document(
            content, mime_type=mime_type, parser_version=identity["parser_version"],
            **self._parse_options(identity["parser_version"]),
        )

    def _parse_options(self, version: str) -> _ParseOptions:
        adapter = self._prepare_ocr() if version == "2.0.0" else None
        return {
            "limits": dn.NormalizationLimits(deadline=self.deadline),
            "ocr": adapter,
            "ocr_limits": dn.OCRLimits(deadline=self.deadline) if adapter else None,
        }

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
        return self._replay(
            data, source_id=source_id, source_sha256=source_sha256, mime_type=mime_type,
            evidence_spans=evidence_spans, language=language, parser_version=parser_version,
        )

    def replay_verified(
        self, content: VerifiedContent, *, mime_type: str, evidence_spans: Sequence[EvidenceSpan],
        language: str | None = None, parser_version: str | None = None,
    ) -> int:
        """Replay the immutable source-owner observation without rechecking its SHA."""
        if type(self).replay is not NarrativeNormalization.replay:
            return self.replay(
                content.data, source_id=content.source_id, source_sha256=content.content_sha256,
                mime_type=mime_type, evidence_spans=evidence_spans, language=language,
                parser_version=parser_version,
            )
        return self._replay(
            content, source_id=content.source_id, source_sha256=content.content_sha256,
            mime_type=mime_type, evidence_spans=evidence_spans, language=language,
            parser_version=parser_version,
        )

    def _replay(
        self, original: bytes | VerifiedContent, *, source_id: str, source_sha256: str,
        mime_type: str, evidence_spans: Sequence[EvidenceSpan], language: str | None,
        parser_version: str | None,
    ) -> int:
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
            if isinstance(original, VerifiedContent):
                document = self.normalize_verified(
                    original, mime_type=mime_type, parser_version=version,
                )
            else:
                document = self.normalize(
                    original, source_id=source_id, source_sha256=source_sha256,
                    mime_type=mime_type, parser_version=version,
                )
            if not document.structure.coverage_complete:
                raise dn.ReplayError(
                    "empty selection requires complete source coverage"
                )
            return 0
        options = self._parse_options(identity["parser_version"])
        if isinstance(original, VerifiedContent):
            return dn.replay_verified_evidence_spans(
                original, mime_type=mime_type, evidence_spans=spans, **options,
            )
        return dn.replay_evidence_spans(
            original,
            source_id=source_id,
            source_sha256=source_sha256,
            mime_type=mime_type,
            evidence_spans=spans,
            **options,
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
        seen: set[str] = set()
        total_pixels = 0
        limits = dn.OCRLimits(max_images=max_images, deadline=self.deadline)
        from company_wiki.document_normalization.local_ocr import image_dimensions

        for asset in document.opaque_assets:
            media_sha256 = asset.media_sha256
            if (
                asset.asset_kind != "image"
                or not asset.rendered
                or asset.original_bytes is None
                or media_sha256 is None
                or media_sha256 in seen
            ):
                continue
            if len(seen) >= max_images:
                break
            seen.add(media_sha256)
            if hashlib.sha256(asset.original_bytes).hexdigest() != media_sha256:
                raise dn.LocalOCRError("OCR_MEDIA_SHA_MISMATCH")
            width, height = image_dimensions(asset.original_bytes, limits)
            total_pixels += width * height
            limits.require_within("max_total_pixels", total_pixels)
            adapter = self._prepare_ocr()
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

__all__ = [
    'NarrativeNormalization',
    'PPTX_MIME',
]
