"""Bounded source-only retrieval views over a verified, pinned narrative final.

Transport owns identity, as-of, byte integrity and full locator replay. This layer
selects results from those bytes and uses the existing ephemeral BM25 algorithm;
it never opens legacy spans/artifacts or creates a persistent search index.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any

from company_wiki.source_catalog.narrative_document import selected_summary_input
from company_wiki.source_catalog.narrative_retrieval import (
    NARRATIVE_EVIDENCE_BUNDLE_SCHEMA_VERSION, NarrativeEvidenceSearch,
)

from .models import canonical_json
from .narrative_contracts import BUNDLE_MAX_BYTES, NarrativeBundle
from .narrative_transport import NarrativeTransportRead, NarrativeTransportReader
from .narrative_transport_contracts import (
    MAX_RECEIPT_BYTES, NarrativeReadRequest, NarrativeTransportError,
)


EVIDENCE_VIEW_OPERATIONS = ("evidence-list", "evidence-lookup", "evidence-search")
EVIDENCE_VIEW_SCHEMA = "narrative-evidence-view/1"
EVIDENCE_VIEW_RECEIPT_SCHEMA = "narrative-evidence-read-receipt/1"
MAX_EVIDENCE_VIEW_LIMIT = 500
MAX_EVIDENCE_QUERY_BYTES = 4096
MAX_EVIDENCE_VIEW_BYTES = BUNDLE_MAX_BYTES + MAX_RECEIPT_BYTES


def _text(value: object, maximum: int, *, trimmed: bool) -> bool:
    return (
        isinstance(value, str) and bool(value.strip())
        and (not trimmed or value == value.strip())
        and len(value.encode("utf-8")) <= maximum
    )


@dataclass(frozen=True)
class NarrativeEvidenceViewQuery:
    operation: str
    limit: int | None = None
    offset: int | None = None
    span_id: str | None = None
    locator: str | None = None
    query: str | None = None

    def __post_init__(self) -> None:
        """Validate all filters before any catalog or raw read is attempted."""
        if self.operation not in EVIDENCE_VIEW_OPERATIONS:
            raise ValueError("unsupported evidence operation")
        if self.limit is not None and (
            type(self.limit) is not int or not 1 <= self.limit <= MAX_EVIDENCE_VIEW_LIMIT
        ):
            raise ValueError("invalid evidence limit")
        if self.offset is not None and (type(self.offset) is not int or self.offset < 0):
            raise ValueError("invalid evidence offset")
        if self.operation == "evidence-lookup":
            if (
                (self.span_id is None) == (self.locator is None)
                or self.limit is not None or self.offset is not None or self.query is not None
                or not _text(self.span_id if self.span_id is not None else self.locator,
                             1024, trimmed=True)
            ):
                raise ValueError("lookup requires one exact anchor without other filters")
        elif self.span_id is not None or self.locator is not None:
            raise ValueError("anchors require lookup")
        elif self.operation == "evidence-search":
            if not _text(self.query, MAX_EVIDENCE_QUERY_BYTES, trimmed=False):
                raise ValueError("search requires bounded nonempty query")
        elif self.query is not None:
            raise ValueError("query requires search")

    @property
    def page_limit(self) -> int:
        return self.limit if self.limit is not None else (
            1 if self.operation == "evidence-lookup" else 100
        )

    @property
    def page_offset(self) -> int:
        return self.offset if self.offset is not None else 0


class NarrativeEvidenceViewReader:
    """Return a view only after the existing transport has verified the source."""

    def __init__(self, transport: NarrativeTransportReader):
        self._transport = transport

    def read(
        self, request: NarrativeReadRequest, query: NarrativeEvidenceViewQuery,
    ) -> NarrativeTransportRead:
        if not isinstance(query, NarrativeEvidenceViewQuery):
            raise ValueError("a validated evidence view query is required")
        verified = self._transport.read(request)
        bundle = NarrativeBundle.from_dict(json.loads(verified.data))
        items = self._items(bundle, query)
        view = {
            "schema_version": EVIDENCE_VIEW_SCHEMA, "operation": query.operation,
            "narrative_ref": request.narrative_ref.to_dict(),
            "source_metadata": bundle.source_metadata.to_dict(),
            "manifest": verified.receipt["manifest"],
            "selection": bundle.selection.to_dict(), "quality_status": bundle.quality_status,
            "versions": bundle.versions.to_dict(), "total": len(items),
            "limit": query.page_limit, "offset": query.page_offset,
            "items": items[query.page_offset:query.page_offset + query.page_limit],
        }
        data = canonical_json(view).encode("utf-8")
        if len(data) > MAX_EVIDENCE_VIEW_BYTES:
            raise NarrativeTransportError("blocked", "evidence_view_too_large")
        receipt = {
            "schema_version": EVIDENCE_VIEW_RECEIPT_SCHEMA, "status": "ok",
            "view_sha256": hashlib.sha256(data).hexdigest(), "byte_size": len(data),
            "narrative_ref": request.narrative_ref.to_dict(), "as_of_date": request.as_of_date,
            "source_read_policy_sha256": verified.receipt["source_read_policy_sha256"],
            "replay_status": verified.receipt["replay_status"],
            "locator_count": verified.receipt["locator_count"],
        }
        return NarrativeTransportRead(data=data, receipt=receipt)

    @staticmethod
    def _items(bundle: NarrativeBundle, query: NarrativeEvidenceViewQuery) -> list[dict[str, Any]]:
        if query.operation == "evidence-lookup":
            matches = [
                span for span in bundle.evidence_spans
                if (query.span_id is not None and span.span_id == query.span_id)
                or (query.locator is not None and span.locator == query.locator)
            ]
            if not matches:
                raise NarrativeTransportError("not_found", "narrative_evidence_not_found")
            if len(matches) != 1:
                raise NarrativeTransportError("unavailable", "narrative_evidence_ambiguous")
            return [matches[0].to_dict()]
        if query.operation == "evidence-list":
            return [span.to_dict() for span in bundle.evidence_spans]
        search = NarrativeEvidenceSearch({
            "schema_version": NARRATIVE_EVIDENCE_BUNDLE_SCHEMA_VERSION,
            "sources": [{
                "selection_status": bundle.selection.status,
                "coverage_complete": bundle.selection.coverage_complete,
                "summary_input": selected_summary_input(
                    source_id=bundle.source_ref.source_id,
                    source_sha256=bundle.source_ref.content_sha256,
                    document_kind=bundle.source_metadata.document_kind,
                    evidence_spans=bundle.evidence_spans,
                ),
            }],
        })
        assert query.query is not None
        # Count all matches in this one bounded final, then take the requested page.
        return [hit.to_dict() for hit in search.search(
            query.query, limit=max(1, search.indexed_group_count),
        )]
