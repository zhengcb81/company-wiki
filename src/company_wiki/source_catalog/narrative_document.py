"""Legacy import path for the neutral document model.

The pure values live in :mod:`company_wiki.document_model.narrative`.  This
module keeps the historical ``source_catalog.narrative_document`` path working
for existing catalog, automation and test consumers by re-exporting the *same*
class objects — it is not a second definition, so ``isinstance`` and
serialization do not split across two DTO families.

Only the module's documented names are re-exported.  Import ``EvidenceSpan`` and
friends from :mod:`company_wiki.source_contract`, not from here.
"""

from __future__ import annotations

from company_wiki.document_model.narrative import (
    DocumentStructure as DocumentStructure,
    NarrativeEvidencePackage as NarrativeEvidencePackage,
    NarrativeParseResult as NarrativeParseResult,
    NarrativeUnit as NarrativeUnit,
    selected_summary_input as selected_summary_input,
)

__all__ = [
    "DocumentStructure",
    "NarrativeEvidencePackage",
    "NarrativeParseResult",
    "NarrativeUnit",
    "selected_summary_input",
]
