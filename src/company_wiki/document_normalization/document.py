"""NormalizedDocument: the frozen result of one normalization run.

The full text never leaves memory as one durable artifact: units live on the
structure, opaque assets keep only byte identity (images keep bytes for
MAIN-side model work under the existing budget), and nothing here writes to
disk.  ``format_name``/``parser_name``/``parser_version`` are explicit so
callers can pin versions across processes.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from company_wiki.source_catalog.narrative_document import (
    DocumentStructure,
    NarrativeUnit,
)

from .assets import OpaqueAsset
from .units import (
    FORMAT_HTML,
    FORMAT_PPTX,
    PARSER_NAME,
    require_parser_version,
)

KNOWN_FORMATS = (FORMAT_HTML, FORMAT_PPTX)


@dataclass(frozen=True)
class NormalizedDocument:
    """Format-neutral normalization output for exactly one verified source."""

    source_id: str
    source_sha256: str
    format_name: str
    parser_name: str
    parser_version: str
    structure: DocumentStructure
    opaque_assets: tuple[OpaqueAsset, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def units(self) -> tuple[NarrativeUnit, ...]:
        return self.structure.units

    def __post_init__(self) -> None:
        if self.format_name not in KNOWN_FORMATS:
            raise ValueError(f"unknown format_name: {self.format_name!r}")
        if self.parser_name != PARSER_NAME:
            raise ValueError(f"parser_name must be {PARSER_NAME!r}")
        require_parser_version(self.format_name, self.parser_version)
        if not isinstance(self.structure, DocumentStructure):
            raise TypeError("structure must be a DocumentStructure")
        if self.structure.source_id != self.source_id:
            raise ValueError("structure source_id must match the document")
        if self.structure.source_sha256 != self.source_sha256:
            raise ValueError("structure source_sha256 must match the document")
        assets = tuple(self.opaque_assets)
        for asset in assets:
            if not isinstance(asset, OpaqueAsset):
                raise TypeError("opaque_assets must contain OpaqueAsset values")
        object.__setattr__(self, "opaque_assets", assets)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def asset_log_records(self) -> tuple[dict[str, object], ...]:
        return tuple(asset.log_record() for asset in self.opaque_assets)


__all__ = ["KNOWN_FORMATS", "NormalizedDocument"]
