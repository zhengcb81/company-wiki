"""Opaque asset record for content the pure-parsing layer cannot transcribe.

An image (or chart, SmartArt, OLE object, corrupt part) is never silently
dropped: it is registered here with its byte identity so MAIN can decide how
to spend model budget on it.  ``original_bytes`` lives in memory for the
lifetime of the :class:`NormalizedDocument` only; the default ``repr`` and any
log line produced by this module exclude it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Named gap reasons.  Images carry their verified bytes (MAIN may run vision
# models on them under the existing budget); everything else names why no
# transcription exists yet.
GAP_IMAGE_BYTES_ONLY = "image_bytes_only_no_ocr"
GAP_EXTERNAL_MEDIA = "external_media_not_fetched"
GAP_MISSING_RELATIONSHIP = "missing_relationship_target"
GAP_CHART_NOT_RENDERABLE = "chart_xml_not_renderable"
GAP_SMARTART_NOT_TRANSCRIBED = "smartart_not_transcribed"
GAP_OLE_NOT_TRANSCRIBED = "ole_object_not_transcribed"
GAP_BROKEN_PART = "part_unreadable"
GAP_UNATTACHED_MEDIA = "media_relationship_without_shape"
GAP_SVG_NOT_TRANSCRIBED = "svg_not_transcribed"

ASSET_KINDS = (
    "image",
    "svg",
    "chart",
    "smartart",
    "ole_object",
    "media",
    "unknown",
)


@dataclass(frozen=True)
class OpaqueAsset:
    """One non-transcribed asset with its verified byte identity."""

    asset_kind: str
    slide_number: int | None
    shape_path: str
    media_sha256: str | None = None
    mime_type: str | None = None
    byte_size: int | None = None
    original_bytes: bytes | None = field(
        default=None, repr=False, compare=False, hash=False
    )
    gap_reason: str | None = None

    def __post_init__(self) -> None:
        if self.asset_kind not in ASSET_KINDS:
            raise ValueError(f"unknown asset_kind: {self.asset_kind!r}")
        if self.slide_number is not None:
            if isinstance(self.slide_number, bool) or not isinstance(
                self.slide_number, int
            ) or self.slide_number < 1:
                raise ValueError("slide_number must be a 1-based int or None")
        if not self.shape_path or not isinstance(self.shape_path, str):
            raise ValueError("shape_path must be non-empty text")
        for name in ("media_sha256", "mime_type", "gap_reason"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                raise TypeError(f"{name} must be text or None")
        if self.byte_size is not None:
            if isinstance(self.byte_size, bool) or not isinstance(
                self.byte_size, int
            ) or self.byte_size < 0:
                raise ValueError("byte_size must be a non-negative int or None")
        if self.original_bytes is not None and not isinstance(
            self.original_bytes, bytes
        ):
            raise TypeError("original_bytes must be bytes or None")
        if self.original_bytes is not None and self.byte_size is not None:
            if len(self.original_bytes) != self.byte_size:
                raise ValueError("byte_size must match original_bytes length")

    def log_record(self) -> dict[str, object]:
        """A loggable view that never contains asset bytes."""
        return {
            "asset_kind": self.asset_kind,
            "slide_number": self.slide_number,
            "shape_path": self.shape_path,
            "media_sha256": self.media_sha256,
            "mime_type": self.mime_type,
            "byte_size": self.byte_size,
            "gap_reason": self.gap_reason,
            "has_original_bytes": self.original_bytes is not None,
        }


__all__ = [
    "ASSET_KINDS",
    "GAP_BROKEN_PART",
    "GAP_CHART_NOT_RENDERABLE",
    "GAP_EXTERNAL_MEDIA",
    "GAP_IMAGE_BYTES_ONLY",
    "GAP_MISSING_RELATIONSHIP",
    "GAP_OLE_NOT_TRANSCRIBED",
    "GAP_SMARTART_NOT_TRANSCRIBED",
    "GAP_SVG_NOT_TRANSCRIBED",
    "GAP_UNATTACHED_MEDIA",
    "OpaqueAsset",
]
