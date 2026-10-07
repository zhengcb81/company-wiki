"""G3-CWP-MAINT: read-only inventories and historical journal reads.

``DuplicateCleanupService.list_groups`` and ``DuplicateCleanupJournal.read_all``
are the retained read surface after the maintenance retirement: they must
construct no ``CatalogStore``, run no DDL and write no bytes — the exact
source/document/location IDs, SHA, root ordering, canonical-vs-semantic
distinction, pagination and unknown-identity diagnostics stay available, and
``eligible_for_recycle`` is uniformly false (inventory only, 0 original
deletions, reclaimable values are a registered upper bound).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

import company_wiki.source_catalog as module
from company_wiki.source_catalog.duplicate_cleanup import (
    DuplicateCleanupJournal,
    DuplicateCleanupService,
)
from support.legacy_source_artifact_fixture import legacy_normalize

X_BODY = b"ACME fiscal 2025 annual report. " * 16
Y_BODY = b"ACME fiscal 2025 quarterly report " * 16
X_NEAR = b"ACME fiscal 2025 annual repoZt. " * 16  # same size, different bytes

REQUIRED_JOURNAL_KEYS = {
    "schema_version",
    "event_id",
    "action_id",
    "event",
    "recorded_at",
    "location_id",
    "absolute_path",
    "canonical_location_id",
    "canonical_path",
    "source_id",
    "content_sha256",
    "error_type",
    "error",
}


def _journal_event(event_id: str, event: str = "requested") -> dict:
    return {
        "schema_version": "1.0",
        "event_id": event_id,
        "action_id": "action-1",
        "event": event,
        "recorded_at": "2026-01-01T00:00:00Z",
        "location_id": "loc-1",
        "absolute_path": "x.pdf",
        "canonical_location_id": "loc-0",
        "canonical_path": "y.pdf",
        "source_id": "src-1",
        "content_sha256": "a" * 64,
        "error_type": None,
        "error": None,
    }


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build_catalog(tmp_path: Path):
    project = tmp_path / "project"
    alpha = tmp_path / "roots" / "alpha"
    beta = tmp_path / "roots" / "beta"
    alpha.mkdir(parents=True)
    beta.mkdir(parents=True)

    (alpha / "zebra-annual.txt").write_bytes(X_BODY)
    (beta / "zebra-annual-copy.txt").write_bytes(X_BODY)
    (alpha / "zebra-annual-near.txt").write_bytes(X_NEAR)
    (alpha / "quarterly.txt").write_bytes(Y_BODY)
    (beta / "quarterly-copy.txt").write_bytes(Y_BODY)
    (alpha / "sem-a.txt").write_text("Revenue 100.\n\nProfit 20.", encoding="utf-8")
    (beta / "sem-b.txt").write_text("Revenue   100.\r\n\tProfit 20.", encoding="utf-8")

    catalog = module.SourceCatalog(
        module.CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(
                module.RootSpec("alpha", alpha, "directory", priority=10),
                module.RootSpec("beta", beta, "directory", priority=30),
            ),
        )
    )
    catalog.scan()
    legacy_normalize(catalog)
    return catalog


def _fingerprints(catalog) -> dict:
    config = catalog.config
    with sqlite3.connect(f"file:{config.database_path}?mode=ro", uri=True) as con:
        schema = con.execute(
            "SELECT type, name, sql FROM sqlite_master ORDER BY type, name"
        ).fetchall()
    journal = DuplicateCleanupJournal(config.catalog_dir)
    return {
        "database_sha256": _sha(config.database_path),
        "schema": schema,
        "catalog_dir": sorted(
            str(p.relative_to(config.catalog_dir)).replace("\\", "/")
            for p in config.catalog_dir.rglob("*")
        ),
        "journal_bytes": journal.path.read_bytes() if journal.path.is_file() else None,
        "raw": {
            str(path.relative_to(path.parents[2])): (
                _sha(path),
                path.stat().st_mtime_ns,
            )
            for root in config.roots
            for path in sorted(root.path.iterdir())
        },
    }


def test_list_groups_is_read_only_and_constructs_no_store(tmp_path):
    catalog = _build_catalog(tmp_path)

    # write phase closed: drop the writer reference before the read phase
    catalog._store = None
    fingerprint = _fingerprints(catalog)

    service = DuplicateCleanupService(catalog)
    first = service.list_groups(limit=50, include_semantic=True)
    second = service.list_groups(limit=50, include_semantic=True)

    assert first == second
    assert catalog._store is None
    assert _fingerprints(catalog) == fingerprint
    catalog.close()


def test_list_groups_keeps_ids_sha_root_order_and_inventory_only_fields(tmp_path):
    catalog = _build_catalog(tmp_path)
    service = DuplicateCleanupService(catalog)

    inventory = service.list_groups(limit=50, include_semantic=True)

    assert inventory["inventory_only"] is True
    assert inventory["original_delete_count"] == 0
    assert inventory["reclaimable_is_upper_bound"] is True
    assert inventory["total_reclaimable_copies"] >= 2
    assert inventory["total_reclaimable_bytes"] > 0

    exact = [
        group for group in inventory["groups"] if group["relation_type"] == "exact_copy"
    ]
    assert len(exact) == 2
    for group in exact:
        members = [group["canonical"], *group["duplicates"]]
        assert group["document_id"] and group["source_id"]
        assert group["content_sha256"]  # group SHA retained (one source = one SHA)
        assert [member["root_priority"] for member in members] == sorted(
            member["root_priority"] for member in members
        )
        assert [member["root_id"] for member in members] == ["alpha", "beta"]
        assert all(member["location_id"] for member in members)
        # inventory-only: the compat flag is uniformly false, canonical protected
        assert group["canonical"]["eligible_for_recycle"] is False
        assert group["canonical"]["protection_reason"] == "canonical_copy"
        assert all(
            member["eligible_for_recycle"] is False for member in group["duplicates"]
        )
        assert all(member["protection_reason"] for member in group["duplicates"])
        assert "confirmation_token" not in group["duplicates"][0]

    # a same-size different-bytes file is never part of an exact-copy group
    zebra = next(
        group
        for group in exact
        if "zebra-annual" in group["canonical"]["relative_path"]
        or "zebra-annual" in group["duplicates"][0]["relative_path"]
    )
    member_paths = {
        member["relative_path"] for member in [zebra["canonical"], *zebra["duplicates"]]
    }
    assert "zebra-annual-near.txt" not in member_paths

    semantic = [
        group
        for group in inventory["groups"]
        if group["relation_type"] == "semantic_copy"
    ]
    assert len(semantic) == 1
    assert semantic[0]["reclaimable_copy_count"] == 0
    assert semantic[0]["reclaimable_bytes"] == 0
    assert all(
        member["eligible_for_recycle"] is False
        for member in [semantic[0]["canonical"], *semantic[0]["duplicates"]]
    )
    assert all(
        member["protection_reason"] == "semantic_review_only"
        for member in [semantic[0]["canonical"], *semantic[0]["duplicates"]]
    )
    # semantic near-duplicates are never presented as byte copies
    assert all(
        member["duplicate_relation"] == "semantic_copy"
        for member in [semantic[0]["canonical"], *semantic[0]["duplicates"]]
    )
    catalog.close()


def test_list_groups_pagination_text_filter_and_positional_shape(tmp_path):
    catalog = _build_catalog(tmp_path)
    service = DuplicateCleanupService(catalog)

    # frozen card signature: positional (text, limit, offset, include_semantic)
    positional = service.list_groups(None, 5, 0, False)
    full = service.list_groups(limit=200)
    assert positional["groups"] == full["groups"]
    assert full["total_groups"] >= 2

    page_1 = service.list_groups(limit=1, offset=0)
    page_2 = service.list_groups(limit=1, offset=1)
    page_3 = service.list_groups(limit=1, offset=2)
    assert page_1["total_groups"] == full["total_groups"]
    assert page_2["total_groups"] == full["total_groups"]
    assert [
        group["duplicate_group_id"]
        for group in page_1["groups"] + page_2["groups"] + page_3["groups"]
    ] == [group["duplicate_group_id"] for group in full["groups"]]
    beyond = service.list_groups(limit=5, offset=full["total_groups"] + 10)
    assert beyond["groups"] == []
    assert beyond["total_groups"] == full["total_groups"]

    zebra = service.list_groups(text="zebra-annual")
    assert zebra["total_groups"] == 1
    assert all("zebra-annual" in json.dumps(group) for group in zebra["groups"])
    catalog.close()


def test_list_groups_rejects_bad_limit_and_offset(tmp_path):
    catalog = _build_catalog(tmp_path)
    service = DuplicateCleanupService(catalog)

    with pytest.raises(ValueError, match="limit"):
        service.list_groups(limit=0)
    with pytest.raises(ValueError, match="limit"):
        service.list_groups(limit=201)
    with pytest.raises(ValueError, match="offset"):
        service.list_groups(offset=-1)
    catalog.close()


def test_journal_read_all_keeps_history_and_rejects_corrupt_records(tmp_path):
    journal = DuplicateCleanupJournal(tmp_path)
    assert journal.read_all() == ()  # no journal yet

    events = (_journal_event("urn:1"), _journal_event("urn:2", event="recycled"))
    journal.path.write_text(
        "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8"
    )
    before = journal.path.read_bytes()
    read = journal.read_all()
    assert [item["event_id"] for item in read] == ["urn:1", "urn:2"]
    assert [item["event"] for item in read] == ["requested", "recycled"]
    assert journal.path.read_bytes() == before  # reads never rewrite history

    journal.path.write_text(
        json.dumps(events[0]) + "\n" + '{"schema_version": "1.0", "eve',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="invalid duplicate cleanup journal line"):
        journal.read_all()

    incomplete = dict(events[0])
    incomplete.pop("content_sha256")
    journal.path.write_text(json.dumps(incomplete) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid duplicate cleanup journal fields"):
        journal.read_all()

    wrong_schema = dict(events[0])
    wrong_schema["schema_version"] = "0.9"
    journal.path.write_text(json.dumps(wrong_schema) + "\n", encoding="utf-8")
    with pytest.raises(
        ValueError, match="unsupported duplicate cleanup journal schema"
    ):
        journal.read_all()


def test_readonly_phase_after_fixture_build_is_zero_store_zero_ddl_zero_write(
    tmp_path,
):
    # --- write phase: fixture via the existing catalog entry points ---
    catalog = _build_catalog(tmp_path)
    journal = DuplicateCleanupJournal(catalog.config.catalog_dir)
    journal.path.write_text(
        json.dumps(_journal_event("urn:history")) + "\n", encoding="utf-8"
    )
    rows_before = None
    with sqlite3.connect(
        f"file:{catalog.config.database_path}?mode=ro", uri=True
    ) as con:
        rows_before = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    assert rows_before >= 1

    # --- close the writer, then record fingerprints ---
    catalog._store = None
    fingerprint = _fingerprints(catalog)

    # --- read phase: two bounded read-only passes ---
    for _ in range(2):
        inventory = DuplicateCleanupService(catalog).list_groups(
            limit=50, include_semantic=True
        )
        assert inventory["inventory_only"] is True
        history = DuplicateCleanupJournal(catalog.config.catalog_dir).read_all()
        assert [item["event_id"] for item in history] == ["urn:history"]
        assert catalog._store is None

    assert _fingerprints(catalog) == fingerprint
    with sqlite3.connect(
        f"file:{catalog.config.database_path}?mode=ro", uri=True
    ) as con:
        assert (
            con.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == rows_before
        )
    catalog.close()
