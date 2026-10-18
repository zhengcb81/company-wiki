"""Read-only identity audit of one catalog: export facts vs read facts.

The lane compares what the export side claims about a source with what the read
side actually returns, using only published contracts.  It never writes to the
catalog, never re-parses a document and never produces research semantics.
"""

from __future__ import annotations

from .core import MAX_EVIDENCE_SPANS, MAX_SOURCE_REFS, audit
from .receipt import P3_RECEIPT_SCHEMA, P3_REQUEST_SCHEMA

__all__ = [
    "MAX_EVIDENCE_SPANS",
    "MAX_SOURCE_REFS",
    "P3_RECEIPT_SCHEMA",
    "P3_REQUEST_SCHEMA",
    "audit",
]
