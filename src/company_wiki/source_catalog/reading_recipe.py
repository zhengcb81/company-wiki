"""Compose reading identities returned by the owners of each algorithm."""

from __future__ import annotations

from pathlib import Path

from company_wiki.document_model.reading_identity import turn_grammar_sha256
from company_wiki.document_normalization.reading_identity import (
    reading_algorithm_hashes as normalization_algorithm_hashes,
)
from company_wiki.document_understanding.reading_identity import (
    reading_algorithm_hashes as understanding_algorithm_hashes,
)
from company_wiki.implementation_identity import owned_algorithm_hashes
from company_wiki.source_contract.selection_annotations import selection_annotations_sha256


_OWNER = "company_wiki.source_catalog"
_ROOT = Path(__file__).resolve().parent
_READING_ROOTS = ("narrative_reading", "reading_recipe")
_PDF_ROOTS = ("narrative_pdf_layout", "narrative_pdf_intent", "narrative_evidence")
_PDF_ONLY = ("narrative_pdf", "narrative_native_ranges")


def business_algorithm_hashes(*, pdf_frontend: bool) -> dict[str, str]:
    """Bind source selection, engine rules and the actual carrier front end."""
    def includes(name: str) -> bool:
        relative = name.removeprefix(_OWNER + ".")
        if relative == "narrative_decision_inventory":
            return False
        return ((pdf_frontend or not relative.startswith(_PDF_ONLY))
                and (relative.startswith("narrative_")
                     or relative in {"reading_recipe", "n6_candidate_operating_facts"}))

    entries = (*_READING_ROOTS, *_PDF_ROOTS) if pdf_frontend else _READING_ROOTS
    algorithms = {
        **owned_algorithm_hashes(
            _OWNER, _ROOT, (f"{_OWNER}.{name}" for name in entries), includes=includes,
        ),
        **understanding_algorithm_hashes(pdf_frontend=pdf_frontend),
        **normalization_algorithm_hashes(pdf_frontend=pdf_frontend),
        "company_wiki.source_contract.selection_annotations": selection_annotations_sha256(),
    }
    if pdf_frontend:
        algorithms["company_wiki.document_model.turns"] = turn_grammar_sha256()
    return algorithms
