"""One-parse exact replay for current and frozen normalization versions."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import re
from .errors import ReplayError
from .limits import NormalizationLimits
from .units import FORMAT_DOCX, FORMAT_HTML, PARSER_NAME, verify_unit_identity


def _plain(value):
    if isinstance(value, Mapping):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def _parse(
    original,
    *,
    source_id,
    source_sha256,
    mime_type,
    version,
    limits,
    ocr,
    ocr_limits,
    locators,
):
    from . import normalize_document

    if (
        not isinstance(original, bytes)
        or hashlib.sha256(original).hexdigest() != source_sha256
    ):
        raise ReplayError("source bytes do not match source_sha256")
    if version == "2.0.0":
        from .local_ocr import LocalOCRError
        from .ocr_composition import adapter_identity, enrich_pptx

        if ocr is None:
            raise LocalOCRError("OCR_ADAPTER_REQUIRED")
        # Verify the entire source package once, then infer only selected media.
        pure = normalize_document(
            original,
            source_id=source_id,
            source_sha256=source_sha256,
            mime_type=mime_type,
            parser_version="1.1.0",
            limits=limits,
        )
        _, fingerprint = adapter_identity(ocr)
        assets = {
            (a.slide_number, a.shape_path, a.media_sha256)
            for a in pure.opaque_assets
            if a.asset_kind == "image" and a.original_bytes is not None
        }
        selected = set()
        for locator in locators:
            if not isinstance(locator, str):
                raise ReplayError("selected source locator must be text")
            if locator.startswith("cwp-pptx-image-ocr/1|"):
                match = re.fullmatch(
                    r"cwp-pptx-image-ocr/1\|s=([1-9][0-9]*)\|p=([0-9]+(?:\.[0-9]+)*)\|m=([0-9a-f]{64})\|ocr=([0-9a-f]{64})\|l=([0-9]+)\|b=(.+)",
                    locator,
                )
                if match is None or match.group(4) != fingerprint:
                    raise ReplayError("selected OCR locator/config identity is invalid")
                key = (int(match.group(1)), match.group(2), match.group(3))
                if key not in assets:
                    raise ReplayError(
                        "selected OCR media/shape differs from verified package"
                    )
                selected.add(match.group(3))
            elif not locator.startswith("cwp-pptx-shape/2|") or not locator.endswith(
                "|ocr=" + fingerprint
            ):
                raise ReplayError("selected OCR parser locator/config is invalid")
        return enrich_pptx(
            pure,
            ocr=ocr,
            limits=limits,
            ocr_limits=ocr_limits,
            selected_media_sha256s=frozenset(selected),
        )
    return normalize_document(
        original,
        source_id=source_id,
        source_sha256=source_sha256,
        mime_type=mime_type,
        parser_version=version,
        limits=limits,
        ocr=None,
        ocr_limits=None,
    )


def _by_locator(document):
    return _index_units(document.units)


def _index_units(units):
    index = {}
    for unit in units:
        locator = unit.metadata["source_locator"]
        if locator in index:
            raise ReplayError("ambiguous normalized source locator")
        index[locator] = unit
    return index


def replay_units(
    original: bytes,
    *,
    source_sha256: str,
    units,
    limits: NormalizationLimits,
    ocr=None,
    ocr_limits=None,
) -> tuple[str, ...]:
    """Replay all requested units in one parse/OCR pass; incomplete recall stays visible."""
    units = tuple(units)
    if not units:
        raise ReplayError("replay requires at least one unit")
    first = units[0]
    format_name = str(first.metadata.get("format", ""))
    for unit in units:
        verify_unit_identity(unit, format_name=format_name)
        if (unit.source_id, unit.parser_name, unit.parser_version) != (
            first.source_id,
            PARSER_NAME,
            first.parser_version,
        ):
            raise ReplayError("mixed source/parser identity")
        if unit.metadata.get("source_sha256") != source_sha256:
            raise ReplayError("unit source_sha256 differs")
    mime = (
        "text/html"
        if format_name == FORMAT_HTML
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if format_name == FORMAT_DOCX
        else "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    doc = _parse(
        original,
        source_id=first.source_id,
        source_sha256=source_sha256,
        mime_type=mime,
        version=first.parser_version,
        limits=limits,
        ocr=ocr,
        ocr_limits=ocr_limits,
        locators=[u.metadata.get("source_locator") for u in units],
    )
    index = _by_locator(doc)
    result = []
    for unit in units:
        candidate = index.get(unit.metadata["source_locator"])
        if candidate is None:
            raise ReplayError("locator not found in source")
        fields = (
            "unit_id",
            "source_id",
            "parser_name",
            "parser_version",
            "coordinates",
            "raw_text",
            "unit_kind",
            "source_role",
            "language",
            "quality_flags",
        )
        if any(getattr(candidate, k) != getattr(unit, k) for k in fields) or _plain(
            candidate.metadata
        ) != _plain(unit.metadata):
            raise ReplayError(
                "replayed source differs from claimed unit identity/text/coordinates/metadata"
            )
        result.append(candidate.raw_text)
    return tuple(result)


def replay_unit(
    original: bytes,
    *,
    source_sha256: str,
    unit,
    limits: NormalizationLimits,
    ocr=None,
    ocr_limits=None,
) -> str:
    return replay_units(
        original,
        source_sha256=source_sha256,
        units=(unit,),
        limits=limits,
        ocr=ocr,
        ocr_limits=ocr_limits,
    )[0]


def replay_evidence_spans(
    original: bytes,
    *,
    source_id: str,
    source_sha256: str,
    mime_type: str,
    evidence_spans,
    limits: NormalizationLimits,
    ocr=None,
    ocr_limits=None,
) -> int:
    """Re-derive all selected span locators once, including OCR image/config bindings.

    This proves the selected spans, not exhaustive OCR recall. The caller must
    report the retained document extraction quality separately.
    """
    spans = tuple(evidence_spans)
    if not spans:
        raise ReplayError("replay requires at least one evidence span")
    version = spans[0].parser_version
    for span in spans:
        if not isinstance(span.structured_value, Mapping):
            raise ReplayError("selected span requires normalized source metadata")
        if (span.source_id, span.parser_name, span.parser_version) != (
            source_id,
            PARSER_NAME,
            version,
        ):
            raise ReplayError("mixed span source/parser identity")
    document = _parse(
        original,
        source_id=source_id,
        source_sha256=source_sha256,
        mime_type=mime_type,
        version=version,
        limits=limits,
        ocr=ocr,
        ocr_limits=ocr_limits,
        locators=[s.structured_value.get("source_locator") for s in spans],
    )
    return verify_parsed_evidence_spans(
        document.units, source_id=source_id, evidence_spans=spans
    )


def verify_parsed_evidence_spans(units, *, source_id, evidence_spans) -> int:
    """Prove selected normalized spans against this already parsed source.

    The caller owns verified bytes and parsing. This pure matching port is
    shared by initial selection and later original replay; it never opens,
    reparses, downloads or enriches a document.

    Parser quality is source-owned and cannot be removed. Selection may append
    conservative diagnostics from EvidenceSpan's existing quality vocabulary;
    these do not prove an extraction method or replace parser/media locators.
    """
    spans = tuple(evidence_spans)
    if not spans:
        raise ReplayError("replay requires at least one evidence span")
    index = _index_units(units)
    for span in spans:
        if not isinstance(span.structured_value, Mapping):
            raise ReplayError("selected span requires normalized source metadata")
        metadata = _plain(span.structured_value)
        candidate = index.get(metadata.get("source_locator"))
        if (
            candidate is None
            or (span.source_id, span.parser_name, span.parser_version)
            != (source_id, PARSER_NAME, candidate.parser_version)
            or candidate.source_id != source_id
            or candidate.parser_name != PARSER_NAME
            or span.raw_text != candidate.raw_text
            or span.coordinates != candidate.coordinates
            or not set(candidate.quality_flags).issubset(span.quality_flags)
        ):
            raise ReplayError(
                "selected span text/coordinates/quality differs from source"
            )
        if any(metadata.get(k) != _plain(v) for k, v in candidate.metadata.items()):
            raise ReplayError("selected span source metadata differs")
        if (
            metadata.get("unit_kind") != candidate.unit_kind
            or metadata.get("source_role") != candidate.source_role
            or metadata.get("text_sha256") != candidate.text_sha256
        ):
            raise ReplayError("selected span role/text identity differs")
    return len(spans)


__all__ = ["replay_unit", "replay_units", "replay_evidence_spans", "verify_parsed_evidence_spans"]
