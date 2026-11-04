"""Legacy import path for the shared transcript turn grammar.

The grammar lives in :mod:`company_wiki.document_model.turns`.  This module
keeps the historical ``source_catalog.transcript_layout`` path working for the
transcript readers by re-exporting the *same* objects, so normalization and
catalog callers observe one ``AnonymousTurnObserver`` and one set of patterns.

``__all__`` names the grammar surface only; incidental module imports (``re``,
``sha256``, ``dataclass``) are no longer forwarded.
"""

from __future__ import annotations

from company_wiki.document_model.turns import (
    END as END,
    NATURAL_START as NATURAL_START,
    QA_HEADING as QA_HEADING,
    AnonymousTurnObserver as AnonymousTurnObserver,
    body_start as body_start,
    legacy_speaker_fields as legacy_speaker_fields,
    speaker_fields as speaker_fields,
    valid_speaker as valid_speaker,
)

__all__ = [
    "END",
    "NATURAL_START",
    "QA_HEADING",
    "AnonymousTurnObserver",
    "body_start",
    "legacy_speaker_fields",
    "speaker_fields",
    "valid_speaker",
]
