"""Compatibility imports for the source-owned official JSON view."""

from company_wiki.source_catalog.narrative_official_json import (
    NARRATIVE_OFFICIAL_JSON_ADAPTER_VERSION,
    OfficialProjectionAdapterError,
    VerifiedProjectionView,
    open_verified_projection,
    select_verified_projection,
)

__all__ = [
    "NARRATIVE_OFFICIAL_JSON_ADAPTER_VERSION", "OfficialProjectionAdapterError",
    "VerifiedProjectionView", "open_verified_projection", "select_verified_projection",
]
