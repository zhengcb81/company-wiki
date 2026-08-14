"""Contracts for semantic (same-text, different-bytes) duplicate detection."""

from __future__ import annotations

from pathlib import Path

import pytest


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


def test_semantic_group_groups_same_text_different_bytes(tmp_path):
    catalog = _catalog_with(
        tmp_path,
        {
            "a.txt": "Revenue 100.\n\nProfit 20.",
            "b.txt": "Revenue   100.\r\n\tProfit 20.",  # same words, different bytes
        },
    )

    semantic = catalog.semantic_duplicate_groups()

    assert len(semantic) == 1
    group = semantic[0]
    assert group["relation_type"] == "semantic_copy"
    assert group["match_basis"] == "normalized_text"
    assert group["confidence"] == 0.95
    assert group["member_count"] == 2
    assert group["distinct_byte_hashes"] == 2
    assert group["text_fingerprint"] is not None

    # Exact duplicate view must remain empty: bytes differ, so no exact_copy.
    assert catalog.duplicate_groups() == []


def test_no_semantic_group_when_all_text_differs(tmp_path):
    catalog = _catalog_with(
        tmp_path,
        {"a.txt": "Revenue 100.", "b.txt": "Completely different content."},
    )

    assert catalog.semantic_duplicate_groups() == []


def test_semantic_location_lookup_is_ranked_once_not_correlated_per_document(
    tmp_path, monkeypatch
):
    catalog = _catalog_with(
        tmp_path,
        {"a.txt": "Revenue 100.", "b.txt": "Revenue   100."},
    )
    queries = []
    # ZR-203: semantic_duplicate_groups reads through the zero-write reader.
    fetchall = catalog.reader.fetchall

    def recording_fetchall(sql, params=()):
        queries.append(sql)
        return fetchall(sql, params)

    monkeypatch.setattr(catalog.reader, "fetchall", recording_fetchall)

    catalog.semantic_duplicate_groups()

    semantic_sql = next(sql for sql in queries if "d.text_fingerprint" in sql)
    assert "ROW_NUMBER() OVER" in semantic_sql
    assert "JOIN ranked_locations" in semantic_sql
    assert "SELECT l2.location_id" not in semantic_sql


def test_export_index_md_has_semantic_section(tmp_path):
    catalog = _catalog_with(
        tmp_path,
        {"a.txt": "Revenue 100.\n\nProfit 20.", "b.txt": "Revenue   100.\nProfit 20."},
    )

    exported = catalog.export_indexes()
    index_md = Path(exported["index_md"]).read_text(encoding="utf-8")

    assert "## Semantic duplicate groups" in index_md


def test_duplicate_cleanup_lists_semantic_as_non_recyclable(tmp_path):
    catalog = _catalog_with(
        tmp_path,
        {"a.txt": "Revenue 100.\n\nProfit 20.", "b.txt": "Revenue   100.\nProfit 20."},
    )
    import company_wiki.source_catalog as module

    service = module.DuplicateCleanupService(catalog, recycler=lambda path: None)
    inventory = service.list_groups(limit=50, include_semantic=True)

    semantic_groups = [
        g for g in inventory["groups"] if g["relation_type"] == "semantic_copy"
    ]
    assert len(semantic_groups) == 1
    group = semantic_groups[0]
    assert group["copy_count"] == 2
    # Semantic copies are review-only: never eligible for recycle.
    assert group["canonical"]["eligible_for_recycle"] is False
    assert group["canonical"]["protection_reason"] == "semantic_review_only"
    for item in group["duplicates"]:
        assert item["eligible_for_recycle"] is False
        assert item["protection_reason"] == "semantic_review_only"


def test_semantic_member_is_not_recyclable(tmp_path):
    """Recycle is structurally safe for semantic copies.

    The recycle flow operates purely on the exact-copy model (it counts
    same-document/same-source peers and requires duplicate_relation ==
    'exact_copy' with a matching byte hash). A semantic member that has no
    exact-copy peers is therefore rejected and its file is never touched. No
    explicit semantic_copy branch exists in recycle because _prepare's exact
    model never assigns that relation — this test pins the safety property.
    """
    catalog = _catalog_with(
        tmp_path,
        {"a.txt": "Revenue 100.\n\nProfit 20.", "b.txt": "Revenue   100.\nProfit 20."},
    )
    import company_wiki.source_catalog as module

    service = module.DuplicateCleanupService(catalog, recycler=lambda path: None)
    inventory = service.list_groups(limit=50, include_semantic=True)
    semantic = next(
        group
        for group in inventory["groups"]
        if group["relation_type"] == "semantic_copy"
    )

    duplicate_member_id = semantic["duplicates"][0]["location_id"]
    duplicate_member_path = Path(semantic["duplicates"][0]["absolute_path"])
    canonical_member_id = semantic["canonical"]["location_id"]

    with pytest.raises(module.DuplicateCleanupError):
        service.preview(duplicate_member_id)
    with pytest.raises(module.DuplicateCleanupError):
        service.preview(canonical_member_id)

    # No file was removed: both members are still on disk.
    assert duplicate_member_path.is_file()
    assert Path(semantic["canonical"]["absolute_path"]).is_file()
