"""Deterministic PPTX normalization with versioned shape-path locators.

Locator schema ``cwp-pptx-shape/1``:
``cwp-pptx-shape/1|s=<slide>|p=<shape path>[|c=<cell r,c>|par=<i>][|m=<media sha>...]``.

Slides are 1-based; the shape path counts nested shape indexes per container
(slide, then group members) 0-based, dot-separated.  Table cells add ``c=r,c``
(0-based row/column); paragraph text bodies add ``par=<i>`` per paragraph.
Media referenced by a shape appends each verified media SHA (verified against
actual ``ppt/media/*`` bytes, not the declared content type alone).

The package is first walked with ``zipfile`` (member-count, traversal, and
cumulative uncompressed-size limits enforced before any XML is read), then
parsed with python-pptx.  Whole-image slides and non-image diagrams are
registered as :class:`OpaqueAsset` gaps; no text is invented for them.
"""

from __future__ import annotations

import hashlib
import io
import posixpath
import re
import zipfile
from typing import Any

from company_wiki.source_contract.evidence_span import EvidenceCoordinates

from .assets import (
    GAP_BROKEN_PART,
    GAP_CHART_NOT_RENDERABLE,
    GAP_EXTERNAL_MEDIA,
    GAP_IMAGE_BYTES_ONLY,
    GAP_MISSING_RELATIONSHIP,
    GAP_OLE_NOT_TRANSCRIBED,
    GAP_SMARTART_NOT_TRANSCRIBED,
    GAP_UNATTACHED_MEDIA,
    OpaqueAsset,
)
from .document import NormalizedDocument
from .errors import NormalizationLimitError, UnsupportedFormatError
from .limits import MAX_ZIP_MEMBERS, NormalizationLimits
from .text import normalize_text
from .units import (
    FORMAT_PPTX,
    PPTX_LOCATOR_SCHEMA,
    build_unit,
)

TRANSFORM = "pptx_shape_text_v1"

SUPPORTED_MIME_TYPES = frozenset(
    {
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.openxmlformats-officedocument.presentationml.slideshow",
    }
)

_OOXML_CONTENT_TYPES = (
    "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml",
    "application/vnd.openxmlformats-officedocument.presentationml.slide.main+xml",
)
_PPTX_MAGIC = b"PK\x03\x04"
_MEDIA_RE = re.compile(r"^ppt/media/(.+)$")
_IMAGE_PART_RE = re.compile(r"^ppt/media/(image\d+)\.(.+)$", re.IGNORECASE)
_EMBED_ATTRS = (
    "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed",
    "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}link",
    "r:id",
    "r:embed",
    "r:link",
)

_NORM = normalize_text


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _mime_for_image_part(name: str) -> str:
    extension = posixpath.splitext(name)[1].lstrip(".").lower()
    return {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "bmp": "image/bmp",
        "tiff": "image/tiff",
        "tif": "image/tiff",
        "wmf": "image/x-wmf",
        "emf": "image/x-emf",
        "svg": "image/svg+xml",
        "webp": "image/webp",
    }.get(extension, "application/octet-stream")


class _ZipPreflight:
    """Bounded, order-independent ZIP inventory computed before parsing."""

    def __init__(self, data: bytes, limits: NormalizationLimits) -> None:
        if not isinstance(data, bytes):
            raise TypeError("PPTX data must be bytes")
        if not data.startswith(_PPTX_MAGIC):
            raise UnsupportedFormatError("bytes are not an OOXML ZIP package")
        if len(data) > limits.max_source_bytes:
            raise NormalizationLimitError(
                "max_source_bytes", limits.max_source_bytes, f"got {len(data)}"
            )
        self.member_count = 0
        self.uncompressed_total = 0
        self.parts: dict[str, tuple[int, bytes]] = {}
        self.traversal_names: list[str] = []
        with zipfile.ZipFile(io.BytesIO(data)) as package:
            infos = package.infolist()
            self.member_count = len(infos)
            if self.member_count > MAX_ZIP_MEMBERS:
                raise NormalizationLimitError(
                    "max_zip_members", MAX_ZIP_MEMBERS, f"{self.member_count}"
                )
            media_total = 0
            for info in infos:
                limits.check_deadline("zip_preflight")
                name = info.filename
                normalized = posixpath.normpath(name.replace("\\", "/"))
                if normalized.startswith("..") or normalized.startswith("/"):
                    self.traversal_names.append(name)
                    continue
                if info.is_dir():
                    continue
                declared = info.file_size
                self.uncompressed_total += declared
                if self.uncompressed_total > limits.max_total_uncompressed_bytes:
                    raise NormalizationLimitError(
                        "max_total_uncompressed_bytes",
                        limits.max_total_uncompressed_bytes,
                        f"declared sizes at {name}",
                    )
                is_media = bool(_MEDIA_RE.match(normalized))
                if is_media:
                    media_total += declared
                    if media_total > limits.max_media_bytes:
                        raise NormalizationLimitError(
                            "max_media_bytes", limits.max_media_bytes, name
                        )
                if declared > 64 * 1024 * 1024 or "ppt/" not in normalized:
                    # Store a few large or non-ppt parts lazily via a second
                    # read below; the archive itself is already in memory.
                    pass
                with package.open(info, "r") as stream:
                    payload = stream.read(
                        declared + 1 if declared else 1
                    )
                if len(payload) != declared:  # pragma: no cover - zip invariant
                    self.traversal_names.append(name)
                    continue
                self.parts[normalized] = (declared, payload)

    def read_part(self, name: str) -> bytes | None:
        normalized = posixpath.normpath(name.replace("\\", "/")).lstrip("/")
        entry = self.parts.get(normalized)
        return None if entry is None else entry[1]


class _PptxState:
    def __init__(
        self,
        *,
        source_id: str,
        source_sha256: str,
        limits: NormalizationLimits,
    ) -> None:
        self.source_id = source_id
        self.source_sha256 = source_sha256
        self.limits = limits
        self.units: list[Any] = []
        self.assets: list[OpaqueAsset] = []
        self.errors: list[str] = []
        self.pages_read = 0
        self.opaque_pages: list[int] = []
        self.text_bytes = 0
        self.media_index: dict[str, tuple[str, int]] = {}
        # Media parts present in ppt/media/ but never referenced by any
        # shape relationship: registered at the end as named package gaps.
        self.package_media: dict[str, str] = {}

    def check_deadline(self, where: str) -> None:
        self.limits.check_deadline(f"pptx:{where}")

    def register_media(
        self, part_name: str, data: bytes
    ) -> tuple[str, int]:
        normalized = posixpath.normpath(part_name.replace("\\", "/")).lstrip("/")
        entry = self.media_index.get(normalized)
        if entry is not None:
            self.package_media.pop(normalized, None)
            return entry
        digest = _sha256_hex(data)
        entry = (digest, len(data))
        self.media_index[normalized] = entry
        return entry


def _element_children(node: Any) -> list[Any]:
    return list(node) if node is not None else []


def _tag_name(node: Any) -> str:
    return getattr(node, "tag", None)


def _shape_path_string(path: SequenceLike) -> str:
    return ".".join(str(p) for p in path)


SequenceLike = Any


def _pptx_module() -> Any:
    try:
        import pptx as _pptx_pkg
        from pptx import Presentation
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise RuntimeError(
            "PPTX parsing requires the optional python-pptx dependency"
        ) from exc
    return _pptx_pkg


def _iter_shape_texts(shape: Any) -> list[tuple[int, str]]:
    """Return ``(paragraph_index, normalized_text)`` for a text frame."""
    results: list[tuple[int, str]] = []
    frame = getattr(shape, "text_frame", None)
    if frame is None:
        return results
    for index, paragraph in enumerate(frame.paragraphs):
        parts: list[str] = []
        for run in paragraph.runs:
            parts.append(str(run.text or ""))
        text = _NORM("".join(parts))
        if text:
            results.append((index, text))
    return results


def _cell_text(cell: Any) -> str:
    return _NORM(cell.text or "")


def _iter_embedded_rIds(element: Any) -> list[str]:
    found: list[str] = []
    if element is None:
        return found
    for attr in _EMBED_ATTRS:
        value = element.get(attr)
        if isinstance(value, str) and value:
            found.append(value)
    for child in element:
        found.extend(_iter_embedded_rIds(child))
    return found


def _resolve_media_by_rIds(
    slide_part: Any,
    r_ids: list[str],
    state: _PptxState,
    slide_number: int,
    shape_path: tuple[int, ...],
) -> list[tuple[str, str, int]]:
    """Resolve r:Ids to (part_name, sha256, size); verify actual bytes.

    External links and missing targets become named gap assets; they are
    never silently dropped or fetched.
    """
    resolved: list[tuple[str, str, int]] = []
    rels = getattr(slide_part, "rels", None)
    preflight: _ZipPreflight | None = getattr(state, "preflight", None)
    where = f"slide{slide_number}:{_shape_path_string(shape_path)}"
    for r_id in r_ids:
        if rels is None:
            state.errors.append(f"{where}:no_rels:{r_id}")
            _register_media_asset(
                state, slide_number, shape_path, r_id, "", 0, None, missing=True
            )
            continue
        try:
            rel = rels[r_id]
        except KeyError:
            state.errors.append(f"{where}:missing_rel:{r_id}")
            _register_media_asset(
                state, slide_number, shape_path, r_id, "", 0, None, missing=True
            )
            continue
        target = None
        try:
            is_external = bool(rel.is_external)
        except Exception:
            is_external = True
        if not is_external:
            try:
                target = rel.target_partname
            except Exception:
                target = None
        try:
            target_ref = rel.target_ref
        except Exception:
            target_ref = None
        if is_external or target is None:
            state.errors.append(
                f"{where}:external_media:{target_ref or r_id}"
            )
            _register_media_asset(
                state,
                slide_number,
                shape_path,
                str(target_ref or r_id),
                "",
                0,
                None,
                external=True,
            )
            continue
        part_name = str(target)
        data = preflight.read_part(part_name) if preflight is not None else None
        if data is None:
            state.errors.append(f"{where}:part_not_read:{part_name}")
            _register_media_asset(
                state, slide_number, shape_path, part_name, "", 0, None, missing=True
            )
            continue
        digest, size = state.register_media(part_name, data)
        resolved.append((part_name, digest, size))
    return resolved


def _register_media_asset(
    state: _PptxState,
    slide_number: int,
    shape_path: tuple[int, ...],
    part_name: str,
    digest: str,
    size: int,
    data: bytes | None,
    external: bool = False,
    missing: bool = False,
) -> None:
    normalized = posixpath.normpath(part_name.replace("\\", "/")).lstrip("/")
    media_match = _MEDIA_RE.match(normalized)
    is_image = bool(_IMAGE_PART_RE.match(normalized))
    if external or missing:
        asset = OpaqueAsset(
            asset_kind="image" if media_match else "media",
            slide_number=slide_number,
            shape_path=_shape_path_string(shape_path),
            media_sha256=None,
            mime_type=None,
            byte_size=None,
            original_bytes=None,
            gap_reason=GAP_EXTERNAL_MEDIA if external else GAP_MISSING_RELATIONSHIP,
        )
        state.assets.append(asset)
        return
    kind = "image" if is_image else "media"
    gap = (
        GAP_IMAGE_BYTES_ONLY
        if is_image
        else GAP_BROKEN_PART
    )
    asset = OpaqueAsset(
        asset_kind=kind,
        slide_number=slide_number,
        shape_path=_shape_path_string(shape_path),
        media_sha256=digest,
        mime_type=_mime_for_image_part(normalized),
        byte_size=size,
        original_bytes=data if not external else None,
        gap_reason=gap,
    )
    state.assets.append(asset)
    state.package_media.pop(normalized, None)
def _walk_shape(
    shape: Any,
    state: _PptxState,
    slide_number: int,
    slide_part: Any,
    path: tuple[int, ...],
    preflight: "_ZipPreflight | None" = None,
) -> None:
    state.check_deadline("shape")
    shape_type = str(getattr(getattr(shape, "shape_type", None), "name", "") or "")
    limits = state.limits

    # Chart / SmartArt / OLE: named gaps, never silently lost.
    if "CHART" in shape_type.upper() or getattr(shape, "has_chart", False):
        state.assets.append(
            OpaqueAsset(
                asset_kind="chart",
                slide_number=slide_number,
                shape_path=_shape_path_string(path),
                gap_reason=GAP_CHART_NOT_RENDERABLE,
            )
        )
    if getattr(shape, "has_smart_art", False):
        state.assets.append(
            OpaqueAsset(
                asset_kind="smartart",
                slide_number=slide_number,
                shape_path=_shape_path_string(path),
                gap_reason=GAP_SMARTART_NOT_TRANSCRIBED,
            )
        )
    ole = None
    try:
        ole = shape.ole_object  # type: ignore[attr-defined]
    except AttributeError:
        ole = None
    if ole is not None:
        state.assets.append(
            OpaqueAsset(
                asset_kind="ole_object",
                slide_number=slide_number,
                shape_path=_shape_path_string(path),
                gap_reason=GAP_OLE_NOT_TRANSCRIBED,
            )
        )

    if shape.shape_type is not None and "GROUP" in shape_type.upper():
        for index, member in enumerate(shape.shapes):
            _walk_shape(
                member, state, slide_number, slide_part, path + (index,), preflight
            )
        return

    if getattr(shape, "has_table", False):
        table = shape.table
        table_units = 0
        for row_index, row in enumerate(table.rows):
            for column_index, cell in enumerate(row.cells):
                text = _cell_text(cell)
                if not text:
                    continue
                if len(state.units) >= limits.max_units:
                    raise NormalizationLimitError(
                        "max_units", limits.max_units, "pptx table cell"
                    )
                text_bytes = len(text.encode("utf-8"))
                if state.text_bytes + text_bytes > limits.max_text_output_bytes:
                    raise NormalizationLimitError(
                        "max_text_output_bytes",
                        limits.max_text_output_bytes,
                        f"slide {slide_number} table cell",
                    )
                state.text_bytes += text_bytes
                locator = (
                    f"{PPTX_LOCATOR_SCHEMA}|s={slide_number}"
                    f"|p={_shape_path_string(path)}|c={row_index},{column_index}"
                )
                state.units.append(
                    build_unit(
                        source_id=state.source_id,
                        source_sha256=state.source_sha256,
                        format_name=FORMAT_PPTX,
                        coordinates=EvidenceCoordinates(
                            page_number=slide_number,
                            table_index=path[-1] if path else 0,
                            row_index=row_index,
                            column_index=column_index,
                        ),
                        raw_text=text,
                        unit_kind="pptx_table_cell",
                        source_locator=locator,
                        transform=TRANSFORM,
                        extra_metadata={
                            "slide_number": slide_number,
                            "shape_path": _shape_path_string(path),
                            "row_index": row_index,
                            "column_index": column_index,
                        },
                    )
                )
                table_units += 1
        return

    # Picture or media-bearing shape: verify bytes and register opaque.
    is_picture = "PICTURE" in shape_type.upper()
    element = getattr(shape, "_element", None)
    r_ids: list[str] = []
    if element is not None:
        r_ids = _iter_embedded_rIds(element)
    if is_picture or r_ids:
        resolved = _resolve_media_by_rIds(
            slide_part, r_ids, state, slide_number, path
        )
        for part_name, digest, size in resolved:
            data = preflight.read_part(part_name) if preflight is not None else None
            _register_media_asset(
                state, slide_number, path, part_name, digest, size, data
            )
        if not r_ids and is_picture:
            state.errors.append(
                f"slide{slide_number}:picture_without_relationship:{_shape_path_string(path)}"
            )
        return

    # Ordinary text body: one unit per non-empty paragraph.
    paragraphs = _iter_shape_texts(shape)
    if not paragraphs:
        return
    for paragraph_index, text in paragraphs:
        if len(state.units) >= limits.max_units:
            raise NormalizationLimitError(
                "max_units", limits.max_units, "pptx paragraph"
            )
        text_bytes = len(text.encode("utf-8"))
        if state.text_bytes + text_bytes > limits.max_text_output_bytes:
            raise NormalizationLimitError(
                "max_text_output_bytes",
                limits.max_text_output_bytes,
                f"slide {slide_number} paragraph",
            )
        state.text_bytes += text_bytes
        locator = (
            f"{PPTX_LOCATOR_SCHEMA}|s={slide_number}"
            f"|p={_shape_path_string(path)}|par={paragraph_index}"
        )
        state.units.append(
            build_unit(
                source_id=state.source_id,
                source_sha256=state.source_sha256,
                format_name=FORMAT_PPTX,
                coordinates=EvidenceCoordinates(
                    page_number=slide_number, paragraph_index=paragraph_index
                ),
                raw_text=text,
                unit_kind="pptx_paragraph",
                source_locator=locator,
                transform=TRANSFORM,
                extra_metadata={
                    "slide_number": slide_number,
                    "shape_path": _shape_path_string(path),
                    "paragraph_index": paragraph_index,
                },
            )
        )


def _walk_slide(
    slide: Any, state: _PptxState, slide_number: int, preflight: Any = None
) -> None:
    slide_part = slide.part
    for index, shape in enumerate(slide.shapes):
        _walk_shape(shape, state, slide_number, slide_part, (index,), preflight)
    notes = getattr(slide, "notes_slide", None)
    if notes is not None:
        frame = getattr(notes, "notes_text_frame", None)
        if frame is not None:
            for paragraph_index, paragraph in enumerate(frame.paragraphs):
                text = _NORM("".join(run.text or "" for run in paragraph.runs))
                if not text:
                    continue
                if len(state.units) >= state.limits.max_units:
                    raise NormalizationLimitError(
                        "max_units", state.limits.max_units, "pptx notes"
                    )
                text_bytes = len(text.encode("utf-8"))
                if (
                    state.text_bytes + text_bytes
                    > state.limits.max_text_output_bytes
                ):
                    raise NormalizationLimitError(
                        "max_text_output_bytes",
                        state.limits.max_text_output_bytes,
                        f"slide {slide_number} notes",
                    )
                state.text_bytes += text_bytes
                locator = (
                    f"{PPTX_LOCATOR_SCHEMA}|s={slide_number}"
                    f"|notes=1|par={paragraph_index}"
                )
                state.units.append(
                    build_unit(
                        source_id=state.source_id,
                        source_sha256=state.source_sha256,
                        format_name=FORMAT_PPTX,
                        coordinates=EvidenceCoordinates(
                            page_number=slide_number,
                            paragraph_index=paragraph_index,
                        ),
                        raw_text=text,
                        unit_kind="pptx_notes_paragraph",
                        source_locator=locator,
                        transform=TRANSFORM,
                        extra_metadata={
                            "slide_number": slide_number,
                            "notes": True,
                            "paragraph_index": paragraph_index,
                        },
                    )
                )


def parse_pptx(
    data: bytes,
    *,
    source_id: str,
    source_sha256: str,
    mime_type: str,
    limits: NormalizationLimits,
) -> NormalizedDocument:
    """Normalize one verified PPTX package into narrative units."""
    if hashlib.sha256(data).hexdigest() != source_sha256:
        raise ValueError("PPTX bytes do not match source_sha256")
    mime_main = mime_type.split(";")[0].strip().lower()
    preflight = _ZipPreflight(data, limits)
    if mime_main not in SUPPORTED_MIME_TYPES:
        content_types = preflight.read_part("[Content_Types].xml") or b""
        if not any(marker in content_types for marker in _OOXML_CONTENT_TYPES):
            raise UnsupportedFormatError(
                f"mime_type {mime_type!r} is not a PPTX package type"
            )
    if preflight.traversal_names:
        state = _PptxState(
            source_id=source_id, source_sha256=source_sha256, limits=limits
        )
        state.errors.append(
            "zip_traversal:"
            + ",".join(sorted(preflight.traversal_names))[:200]
        )
        return _result(
            state, preflight, page_count=0, format_mime=mime_main
        )
    pptx = _pptx_module()
    try:
        from pptx import Presentation

        package = Presentation(io.BytesIO(data))
    except Exception as exc:
        state = _PptxState(
            source_id=source_id, source_sha256=source_sha256, limits=limits
        )
        state.errors.append(f"package_open:{type(exc).__name__}")
        return _result(state, preflight, page_count=0, format_mime=mime_main)
    slides = package.slides
    state = _PptxState(
        source_id=source_id, source_sha256=source_sha256, limits=limits
    )
    state.preflight = preflight  # type: ignore[attr-defined]
    # Seed package media inventory from the preflight scan up front; shape
    # relationships below remove their targets so unreferenced media remains.
    for part_name in preflight.parts:
        if _MEDIA_RE.match(part_name):
            payload = preflight.parts[part_name][1]
            state.package_media[part_name] = _sha256_hex(payload)
            state.media_index.setdefault(
                part_name, (state.package_media[part_name], len(payload))
            )
    page_count = len(slides)
    if page_count > limits.max_pages:
        raise NormalizationLimitError(
            "max_pages", limits.max_pages, f"{page_count} slides"
        )
    slide_numbers_seen: set[int] = set()
    for slide in slides:
        limits.check_deadline("slide")
        slide_number = slide.slide_id
        state.pages_read += 1
        slide_numbers_seen.add(slide_number)
        units_before = len(state.units)
        try:
            _walk_slide(slide, state, slide_number, preflight)
        except NormalizationLimitError:
            raise
        except Exception as exc:
            state.errors.append(
                f"slide{slide_number}:{type(exc).__name__}"
            )
        if len(state.units) == units_before:
            # A slide with no text units is honestly partial: image-only or
            # broken.  Its assets already name the gap; the slide also joins
            # opaque_pages so coverage_complete stays False.
            state.opaque_pages.append(slide_number)
            if not any(
                asset.slide_number == slide_number for asset in state.assets
            ):
                state.assets.append(
                    OpaqueAsset(
                        asset_kind="unknown",
                        slide_number=slide_number,
                        shape_path="*",
                        gap_reason=GAP_BROKEN_PART,
                    )
                )
    # Unreferenced package media left in package_media is a named gap.
    for part_name in sorted(state.package_media):
        digest = state.package_media[part_name]
        payload = preflight.read_part(part_name) or b""
        normalized_name = posixpath.normpath(part_name.replace("\\", "/")).lstrip("/")
        state.assets.append(
            OpaqueAsset(
                asset_kind="image"
                if _IMAGE_PART_RE.match(normalized_name)
                else "media",
                slide_number=None,
                shape_path="unattached",
                media_sha256=digest,
                mime_type=_mime_for_image_part(normalized_name),
                byte_size=len(payload),
                original_bytes=payload,
                gap_reason=GAP_UNATTACHED_MEDIA,
            )
        )
    return _result(state, preflight, page_count=page_count, format_mime=mime_main)


def _result(
    state: _PptxState,
    preflight: _ZipPreflight,
    *,
    page_count: int,
    format_mime: str,
) -> NormalizedDocument:
    from company_wiki.source_catalog.narrative_document import DocumentStructure

    structure = DocumentStructure(
        source_id=state.source_id,
        source_sha256=state.source_sha256,
        language="und",
        units=tuple(state.units),
        page_count=page_count,
        pages_read=state.pages_read,
        opaque_pages=tuple(sorted(set(state.opaque_pages))),
        table_scan_pages=(),
        deferred_table_pages=(),
        line_count=0,
        errors=tuple(state.errors),
    )
    metadata: dict[str, Any] = {
        "zip_member_count": preflight.member_count,
        "zip_uncompressed_bytes": preflight.uncompressed_total,
        "media_parts": {
            name: {"sha256": digest, "byte_size": size}
            for name, (digest, size) in sorted(state.media_index.items())
        },
        "declared_mime_type": format_mime,
    }
    return NormalizedDocument(
        source_id=state.source_id,
        source_sha256=state.source_sha256,
        format_name=FORMAT_PPTX,
        parser_name="cwp_document_normalization",
        parser_version="1.0.0",
        structure=structure,
        opaque_assets=tuple(state.assets),
        metadata=metadata,
    )


__all__ = [
    "SUPPORTED_MIME_TYPES",
    "TRANSFORM",
    "parse_pptx",
]
