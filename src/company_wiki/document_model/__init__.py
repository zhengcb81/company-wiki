"""Neutral in-memory document model and shared source observations.

This package is the owner of the structures that describe *one parsed source
document*, independent of where that document came from:

* :mod:`company_wiki.document_model.narrative` — ``NarrativeUnit``,
  ``DocumentStructure`` and the selected-evidence package built from them;
* :mod:`company_wiki.document_model.turns` — the bounded natural call-heading,
  speaker-label and end-control grammar shared by the transcript readers;
* :mod:`company_wiki.document_model.form_fields`,
  :mod:`company_wiki.document_model.table_shapes` and
  :mod:`company_wiki.document_model.text_matching` — literal source shapes and
  transient text matching shared by parsers and readers.

Nothing here opens a catalog root, a database, an acquisition adapter or an
automation store, so HTML/DOCX/PPTX normalization and the shared
document-understanding engine can import the model on their own.  The legacy
``company_wiki.source_catalog.narrative_document`` / ``transcript_layout``
paths re-export these exact objects for existing consumers.
"""

from __future__ import annotations

from . import form_fields as form_fields, table_shapes as table_shapes, text_matching as text_matching
from .narrative import (
    DocumentStructure,
    NarrativeEvidencePackage,
    NarrativeParseResult,
    NarrativeUnit,
    selected_summary_input,
)
from .turns import (
    END,
    NATURAL_START,
    QA_HEADING,
    AnonymousTurnObserver,
    body_start,
    legacy_speaker_fields,
    speaker_fields,
    valid_speaker,
)

__all__ = [
    "DocumentStructure",
    "END",
    "NATURAL_START",
    "NarrativeEvidencePackage",
    "NarrativeParseResult",
    "NarrativeUnit",
    "QA_HEADING",
    "AnonymousTurnObserver",
    "body_start",
    "form_fields",
    "legacy_speaker_fields",
    "selected_summary_input",
    "speaker_fields",
    "table_shapes",
    "text_matching",
    "valid_speaker",
]
