"""Public implementation identities for document understanding operations."""

from __future__ import annotations

from pathlib import Path

from company_wiki.implementation_identity import code_sha256, owned_algorithm_hashes, owned_tree_hashes


_OWNER = "company_wiki.document_understanding"
_ROOT = Path(__file__).resolve().parent
_READING_ROOTS = ("operating_states", "statement_grammar")
_PDF_ROOTS = ("geometry_intent", "geometry_intent.reading", "profiles.geometry_policy", "pdf_table_observations")


def reading_algorithm_hashes(*, pdf_frontend: bool) -> dict[str, str]:
    """Return the reading engine's code and grammar fingerprints for one carrier."""
    from .statement_grammar import resource_identity

    def includes(name: str) -> bool:
        relative = name.removeprefix(_OWNER + ".")
        return (not relative.startswith("decision_")
                and (pdf_frontend or not relative.startswith(_PDF_ROOTS)))

    entries = (*_READING_ROOTS, *_PDF_ROOTS) if pdf_frontend else _READING_ROOTS
    # Start at the public package as well as the separately exposed grammars,
    # so a new reading API re-export brings its implementation into the recipe.
    hashes = owned_algorithm_hashes(
        _OWNER, _ROOT, (_OWNER, *(f"{_OWNER}.{name}" for name in entries)), includes=includes,
    )
    if pdf_frontend:
        hashes["company_wiki.document_normalization.pdf_table_observations.adapter"] = hashes.pop(
            f"{_OWNER}.pdf_table_observations",
        )
    from . import structure
    hashes.update(owned_tree_hashes(structure.__name__, (Path(root) for root in structure.__path__)))
    hashes["statement_grammar_resources"] = resource_identity()
    return hashes


def continuity_algorithm_hashes() -> dict[str, str]:
    from . import (
        hanging_indent_geometry, indented_tail_geometry, narrative_continuity, source_turn_markers,
    )

    return {
        module.__name__: code_sha256(module.__file__)
        for module in (narrative_continuity, source_turn_markers,
                       indented_tail_geometry, hanging_indent_geometry)
    }


def pdf_reading_algorithm_hashes() -> dict[str, str]:
    from .geometry_intent import contracts, planner, reading
    from .profiles import geometry_policy

    return {
        module.__name__: code_sha256(module.__file__)
        for module in (reading, planner, contracts, geometry_policy)
    }


def assertion_frames_sha256(*, universal_newlines: bool = False) -> str:
    from . import assertion_frames

    return code_sha256(assertion_frames.__file__, universal_newlines=universal_newlines)


def reading_context_sha256(*, universal_newlines: bool = False) -> str:
    from . import reading_context_contract

    return code_sha256(reading_context_contract.__file__, universal_newlines=universal_newlines)


def source_card_allocation_sha256(*, universal_newlines: bool = False) -> str:
    from . import source_card_allocation

    return code_sha256(source_card_allocation.__file__, universal_newlines=universal_newlines)


def source_cards_sha256(*, universal_newlines: bool = False) -> str:
    from . import source_cards

    return code_sha256(source_cards.__file__, universal_newlines=universal_newlines)


def summary_tasks_sha256(*, universal_newlines: bool = False) -> str:
    from . import summary_tasks

    return code_sha256(summary_tasks.__file__, universal_newlines=universal_newlines)


__all__ = [
    "assertion_frames_sha256", "continuity_algorithm_hashes", "pdf_reading_algorithm_hashes",
    "reading_algorithm_hashes", "reading_context_sha256", "source_card_allocation_sha256",
    "source_cards_sha256", "summary_tasks_sha256",
]
