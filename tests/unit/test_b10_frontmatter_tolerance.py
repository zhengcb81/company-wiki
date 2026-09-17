"""B10-3 batch 2: the frontmatter builder tolerates a malformed shared column.

`_frontmatter` is called at normalizer.py:1726 - OUTSIDE `normalize_catalog`'s per-document
try/except - so before batch 2 a single unreadable `documents.metadata_json` raised
JSONDecodeError straight out of the normalizer and aborted the WHOLE run, instead of
degrading that one document.  These tests pin the converged behaviour: the parse goes
through the single chain (`store.metadata_object`), a malformed column degrades to "no
metadata", and the metadata path still works when the column IS readable.
"""

from __future__ import annotations

import json

from company_wiki.source_catalog.normalizer import _Normalized, _frontmatter

SECURITY_ID = "601899"
READABLE = json.dumps(
    {"acquisition": {"security_ids": [SECURITY_ID], "canonical_entity_id": "test-issuer"}},
    ensure_ascii=False,
)


class _Row:
    """A minimal stand-in for sqlite3.Row: NOT a dict, index access only."""

    def __init__(self, **data: object) -> None:
        self._data = data

    def __getitem__(self, key: str) -> object:
        return self._data[key]


def _document(metadata_json: object, *, as_row: bool) -> object:
    fields = {
        "document_id": "urn:company-wiki:document:sha256:" + "a" * 64,
        "primary_source_id": "urn:company-wiki:source:sha256:" + "b" * 64,
        "content_sha256": "c" * 64,
        "title": "Test Filing",
        "document_kind": "annual_report",
        "published_date": "2026-06-18",
        "metadata_json": metadata_json,
    }
    return _Row(**fields) if as_row else fields


def _normalized() -> _Normalized:
    return _Normalized(
        body="# heading\n\nbody text\n",
        parser_results=(),
        parser_name="test-parser",
        parser_version="1.0.0",
        status="ok",
        quality_flags=(),
        page_count=1,
        first_page_text="Test Filing\nbody text",
    )


def test_b10_frontmatter_uses_readable_metadata() -> None:
    """Control: when the column IS readable, its values reach the frontmatter.

    The rendered markers are the ones the module actually emits (measured, not assumed):
    ``declared_entity: test-issuer`` and ``declared_security_ids_count: 1``.
    """
    for as_row in (True, False):
        rendered = _frontmatter(_document(READABLE, as_row=as_row), _normalized())
        assert isinstance(rendered, str) and rendered.startswith("---\n")
        assert "declared_entity: test-issuer" in rendered, (
            "the readable metadata path stopped working"
        )
        assert "declared_security_ids_count: 1" in rendered


def test_b10_frontmatter_tolerates_malformed_metadata() -> None:
    """The converged behaviour: unreadable content degrades, it does NOT abort the run."""
    for bad in ("not json at all", "", None, "[1, 2, 3]", b"\xff\xfe"):
        for as_row in (True, False):
            rendered = _frontmatter(_document(bad, as_row=as_row), _normalized())
            assert isinstance(rendered, str) and rendered.startswith("---\n"), (
                f"malformed metadata ({bad!r}, as_row={as_row}) must still render"
            )
            assert "declared_entity: test-issuer" not in rendered, (
                "degraded metadata must not invent the declared identity"
            )
            assert "declared_security_ids_count: 1" not in rendered


def test_b10_frontmatter_marks_unreadable_metadata_visibly() -> None:
    """B-VR-B10R2-03 (P1): degraded metadata must NOT be recorded as a passing identity.

    With nothing readable to verify against, the homepage check still says "consistent"
    because the only value left to compare is the document's own title.  Missing evidence
    must not read as a pass, so the flag is added and the verdict is downgraded.

    NOTE the boundary: an EMPTY or NULL column is "no metadata" in the chain's contract
    (`json.loads(raw or "{}")`), not "unreadable metadata", so it carries no flag - the
    distinction is deliberate and is asserted in both directions here.
    """
    for bad in ("not json at all", "[1, 2, 3]", '"a string"', "123", b"\xff\xfe"):
        rendered = _frontmatter(_document(bad, as_row=True), _normalized())
        assert "metadata_unreadable" in rendered, (
            f"an unreadable column ({bad!r}) must add the metadata_unreadable quality flag"
        )
        assert "verdict: consistent" not in rendered, (
            "an unreadable column must not keep the consistent identity verdict"
        )
        assert "verdict: unverifiable" in rendered


def test_b10_frontmatter_distinguishes_empty_from_unreadable() -> None:
    """The chain's documented falsy contract: empty/NULL is "no metadata", not "unreadable"."""
    for empty in ("", None):
        rendered = _frontmatter(_document(empty, as_row=True), _normalized())
        assert "metadata_unreadable" not in rendered, (
            f"{empty!r} is the chain's 'no metadata' case, not an unreadable one"
        )


def test_b10_frontmatter_keeps_consistent_verdict_for_readable_metadata() -> None:
    """Control: readable metadata keeps the normal verdict (no false downgrade)."""
    rendered = _frontmatter(_document(READABLE, as_row=True), _normalized())
    assert "metadata_unreadable" not in rendered
    assert "verdict: consistent" in rendered
