"""Implementation identities of shared, format-neutral reading observations."""

from __future__ import annotations

from pathlib import Path

from company_wiki.implementation_identity import code_sha256, owned_algorithm_hashes

from . import table_shapes, text_matching, turns


_OWNER = "company_wiki.document_model"
_ROOT = Path(__file__).resolve().parent
_READING_ROOTS = ("form_fields", "table_shapes", "text_matching")


def reading_algorithm_hashes() -> dict[str, str]:
    """Fingerprint the rules the reader uses independently of parser code."""
    return owned_algorithm_hashes(
        _OWNER,
        _ROOT,
        (f"{_OWNER}.{name}" for name in _READING_ROOTS),
        includes=lambda name: name != _OWNER,
    )


def table_shapes_sha256() -> str:
    return code_sha256(table_shapes.__file__)


def text_matching_sha256() -> str:
    return code_sha256(text_matching.__file__)


def turn_grammar_sha256() -> str:
    return code_sha256(turns.__file__)


__all__ = ["reading_algorithm_hashes", "table_shapes_sha256", "text_matching_sha256", "turn_grammar_sha256"]
