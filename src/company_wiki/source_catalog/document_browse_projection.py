"""Shared pathless wire projection for an indexed document version."""

from __future__ import annotations

import base64
import hashlib
from typing import Any

from ..source_contract.source_version import SOURCE_REF_SCHEMA_VERSION
from .models import CatalogBrowseVersion

DOCUMENT_VERSION_ID_PREFIX = "cwpdv1-"


def document_version_id(document_id: str, source_id: str, content_sha256: str) -> str:
    """Generate the opaque token for one exact document/source/hash triple."""
    digest = hashlib.sha256(
        b"company-wiki:document-version:1\0"
        + document_id.encode("utf-8") + b"\0"
        + source_id.encode("utf-8") + b"\0"
        + content_sha256.encode("utf-8")
    ).digest()
    return DOCUMENT_VERSION_ID_PREFIX + base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def version_sort_key(version: CatalogBrowseVersion) -> tuple[Any, ...]:
    published = version.published_date or ""
    return (
        version.document_kind or "",
        -(version.fiscal_year or 0),
        0 if published else 1,
        tuple(-ord(ch) for ch in published),
        version.title or "",
        version.document_id,
        0 if version.primary else 1,
        -version.ordinal,
        version.source_id,
    )


def version_revision_member(version: CatalogBrowseVersion) -> list[Any]:
    """Keep all visible version facts in the established revision field order."""
    return [
        version.document_id, version.source_id, version.content_sha256,
        version.byte_size, version.mime_type, version.primary, version.ordinal,
        version.title, version.document_kind, version.published_date,
        version.source_status, version.fiscal_year, version.period_start,
        version.period_end, version.language, version.market,
        version.canonical_entity_id, version.display_name, version.first_seen_at,
        sorted(version.roles), version.resolvable,
    ]


def version_item(version: CatalogBrowseVersion) -> dict[str, Any]:
    return {
        "document_version_id": document_version_id(
            version.document_id, version.source_id, version.content_sha256,
        ),
        "document_id": version.document_id,
        "title": version.title,
        "document_kind": version.document_kind,
        "published_at": version.published_date,
        "period_start": version.period_start,
        "period_end": version.period_end,
        "fiscal_year": version.fiscal_year,
        "language": version.language,
        "market": version.market,
        "version_label": str(version.ordinal),
        "is_current_version": version.primary,
        "processing_state": version.source_status,
        "location_roles": sorted(version.roles),
        "first_seen_at": version.first_seen_at,
        "storage_state": "resolvable" if version.resolvable else "not_resolvable",
        "source_ref": {
            "document_id": version.document_id,
            "source_id": version.source_id,
            "content_sha256": version.content_sha256,
            "byte_size": version.byte_size,
            "mime_type": version.mime_type,
            "schema_version": SOURCE_REF_SCHEMA_VERSION,
        },
    }
