"""Contracts for normalized-text fingerprinting (semantic duplicate basis)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from company_wiki.source_catalog.normalizer import (
    backfill_text_fingerprints,
    compute_text_fingerprint,
)


def test_fingerprint_is_stable_and_whitespace_insensitive():
    assert compute_text_fingerprint("Revenue 100. Profit 20.") == compute_text_fingerprint(
        "Revenue 100. Profit 20."
    )
    # Whitespace differences (spaces, tabs, newlines, CRLF) must not change it.
    assert compute_text_fingerprint("Revenue 100.\n\nProfit 20.") == compute_text_fingerprint(
        "Revenue   100.\r\n\tProfit 20."
    )
    assert compute_text_fingerprint("Revenue 100. Profit 20.") == compute_text_fingerprint(
        "   Revenue 100. Profit 20.   "
    )


def test_fingerprint_distinguishes_different_text():
    a = compute_text_fingerprint("Revenue 100. Profit 20.")
    b = compute_text_fingerprint("Revenue 101. Profit 20.")
    assert a != b
    assert isinstance(a, str) and len(a) == 64
    int(a, 16)  # must be hex
    assert a == hashlib.sha256("Revenue 100. Profit 20.".encode("utf-8")).hexdigest()


def test_fingerprint_none_for_empty_or_whitespace_only():
    assert compute_text_fingerprint("") is None
    assert compute_text_fingerprint("   \n\t  \r\n ") is None


def _catalog_with(tmp_path: Path, files: dict[str, str]):
    import company_wiki.source_catalog as module

    project = tmp_path / "project"
    source_root = tmp_path / "sources"
    source_root.mkdir()
    for name, content in files.items():
        (source_root / name).write_text(content, encoding="utf-8")
    catalog = module.SourceCatalog(
        module.CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(module.RootSpec("external", source_root, "directory"),),
        )
    )
    catalog.scan()
    catalog.normalize()
    return catalog


def test_normalize_populates_text_fingerprint(tmp_path):
    catalog = _catalog_with(tmp_path, {"brief.txt": "Revenue 100.\n\nProfit 20."})

    rows = catalog.store.fetchall("SELECT text_fingerprint FROM documents ORDER BY document_id")
    fingerprints = [row["text_fingerprint"] for row in rows]
    assert len(fingerprints) == 1
    fp = fingerprints[0]
    assert isinstance(fp, str) and len(fp) == 64


def test_same_text_different_bytes_share_fingerprint(tmp_path):
    """Two files with identical words but different whitespace/bytes -> same fingerprint."""
    catalog = _catalog_with(
        tmp_path,
        {
            "a.txt": "Revenue 100.\n\nProfit 20.",
            "b.txt": "Revenue   100.\r\n\tProfit 20.",
        },
    )

    rows = catalog.store.fetchall("SELECT text_fingerprint FROM documents ORDER BY document_id")
    fingerprints = [row["text_fingerprint"] for row in rows]
    assert len(fingerprints) == 2
    assert fingerprints[0] is not None
    assert fingerprints[0] == fingerprints[1]


def test_backfill_restores_null_fingerprints_idempotently(tmp_path):
    catalog = _catalog_with(tmp_path, {"brief.txt": "Revenue 100.\n\nProfit 20."})
    original = catalog.store.fetchone(
        "SELECT text_fingerprint FROM documents"
    )["text_fingerprint"]
    assert original is not None

    # Simulate a pre-migration catalog: fingerprints not yet computed.
    with catalog.store.transaction() as connection:
        connection.execute("UPDATE documents SET text_fingerprint=NULL")

    report = backfill_text_fingerprints(catalog.config, catalog.store)
    assert report.completed == 1
    restored = catalog.store.fetchone("SELECT text_fingerprint FROM documents")[
        "text_fingerprint"
    ]
    assert restored == original

    # Idempotent: no NULL rows remain, so a second run does nothing.
    report2 = backfill_text_fingerprints(catalog.config, catalog.store)
    assert report2.completed == 0
