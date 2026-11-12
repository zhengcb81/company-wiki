"""Catalog identity projection shared by registration and exact-version reads."""
from __future__ import annotations

import re
import sqlite3
from typing import Any, Protocol
from collections.abc import Callable
from company_wiki.source_contract.source_version import SourceReadError, SourceRef
from .reader import CatalogReaderUnavailable

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")

class SourceIdentityReader(Protocol):
    def exact_source_version(self, document_id: str) -> Any: ...

class PairIdentityReader(Protocol):
    def exact_source_pair(self, document_id: str, source_id: str) -> Any: ...
    def document(self, document_id: str) -> Any: ...

def query_source_reference(
    reader_factory: Callable[[], SourceIdentityReader], document_id: str, source_id: str, expected_sha256: str
) -> SourceRef:
    """Pure catalog SELECT; availability and current action policy are open gates."""
    if not isinstance(document_id, str) or not document_id.strip():
        raise ValueError("document_id must be non-empty text")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("source_id must be non-empty text")
    if not isinstance(expected_sha256, str) or not _SHA256.fullmatch(
        expected_sha256
    ):
        raise ValueError("expected_sha256 must be lowercase SHA-256")
    try:
        row = reader_factory().exact_source_version(document_id)
    except (CatalogReaderUnavailable, sqlite3.Error):
        raise SourceReadError("unavailable", "catalog_unavailable") from None
    if row is None:
        raise SourceReadError("not_indexed", "document_not_indexed")
    if row["source_status"] != "active":
        raise SourceReadError("blocked", "source_not_active")
    if row["source_id"] != source_id:
        raise SourceReadError("not_found", "document_source_mismatch")
    if not row["content_sha256"]:
        raise SourceReadError("not_indexed", "source_version_not_indexed")
    if row["content_sha256"] != expected_sha256:
        raise SourceReadError("unavailable", "expected_version_mismatch")
    return SourceRef(
        document_id=document_id,
        source_id=source_id,
        content_sha256=expected_sha256,
        byte_size=int(row["byte_size"]),
        mime_type=str(row["mime_type"]),
    )

def query_exact_pair_reference(
    reader_factory: Callable[[], PairIdentityReader], document_id: str, source_id: str, expected_sha256: str
) -> SourceRef:
    """Pair-precise catalog SELECT for one exact version read.

    A NON-primary (history/attachment) source registered under the same
    document resolves to ITS OWN version row, never to the document's
    current primary; a pair that was never registered under this document
    fails closed with the document-level distinction intact.  Registration
    keeps the primary semantics of :func:`query_source_reference`.
    """
    if not isinstance(document_id, str) or not document_id.strip():
        raise ValueError("document_id must be non-empty text")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("source_id must be non-empty text")
    if not isinstance(expected_sha256, str) or not _SHA256.fullmatch(
        expected_sha256
    ):
        raise ValueError("expected_sha256 must be lowercase SHA-256")
    try:
        reader = reader_factory()
        row = reader.exact_source_pair(document_id, source_id)
        if row is None and reader.document(document_id) is None:
            raise SourceReadError("not_indexed", "document_not_indexed")
    except (CatalogReaderUnavailable, sqlite3.Error):
        raise SourceReadError("unavailable", "catalog_unavailable") from None
    if row is None:
        raise SourceReadError("not_found", "document_source_mismatch")
    if row["source_status"] != "active":
        raise SourceReadError("blocked", "source_not_active")
    if not row["content_sha256"] or not row["byte_size"] or not row["mime_type"]:
        raise SourceReadError("not_indexed", "source_version_not_indexed")
    if str(row["content_sha256"]) != expected_sha256:
        raise SourceReadError("unavailable", "expected_version_mismatch")
    return SourceRef(
        document_id=document_id,
        source_id=source_id,
        content_sha256=expected_sha256,
        byte_size=int(row["byte_size"]),
        mime_type=str(row["mime_type"]),
    )
