"""G3-CWP-MAINT: legacy maintenance write entries retire with zero side effects.

Every retired entry (focus cleanup, focus restore, retired-evidence archive,
retired-evidence prune, duplicate preview/recycle, recycle-bin helper and
duplicate journal writes) must raise the unified
``maintenance_retirement.RetiredMaintenanceError`` BEFORE any Store, lock,
file or journal is touched — regardless of missing ``now``, unknown
confirmation tokens, dry-run/``--apply`` flags or nonexistent paths.  The
read-only inventories and historical journal reads are covered by
``test_g3_readonly_inventory.py``.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest

import company_wiki.source_catalog as module
from company_wiki.source_catalog.archive_retired_evidence import (
    archive_retired_evidence,
)
from company_wiki.source_catalog.duplicate_cleanup import (
    DuplicateCleanupError,
    DuplicateCleanupJournal,
    DuplicateCleanupService,
    recycle_to_windows_bin,
)
from company_wiki.source_catalog.focus_cleanup import FocusScopeCleanupService
from company_wiki.source_catalog.maintenance_retirement import (
    RetiredMaintenanceError,
)
from company_wiki.source_catalog.prune_retired_evidence import (
    prune_retired_evidence,
)
from company_wiki.source_catalog.store import retire_document
from support.legacy_source_artifact_fixture import legacy_normalize

NOW = datetime(2026, 8, 15, tzinfo=timezone.utc)


class _ExplodingCatalog:
    """Any attribute access explodes: construction must never dereference."""

    def __getattr__(self, name: str):
        raise AssertionError(f"catalog attribute dereferenced: {name}")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree(root: Path) -> list[str]:
    return sorted(str(p.relative_to(root)).replace("\\", "/") for p in root.rglob("*"))


def test_retired_maintenance_error_contract():
    error = RetiredMaintenanceError("archive-retired-evidence")

    assert isinstance(error, RuntimeError)
    assert RetiredMaintenanceError.code == "MAINTENANCE_OPERATION_RETIRED"
    assert error.code == "MAINTENANCE_OPERATION_RETIRED"
    assert error.operation == "archive-retired-evidence"

    message = str(error)
    lowered = message.lower()
    assert "retired" in lowered
    assert "archive-retired-evidence" in message
    assert "inventory" in lowered
    for forbidden in ("confirmation", "token", "签收", "backup", "授权"):
        assert forbidden not in lowered, message


def test_focus_entries_retire_without_dereferencing_catalog_or_writing(tmp_path):
    service = FocusScopeCleanupService(_ExplodingCatalog())

    with pytest.raises(RetiredMaintenanceError) as exc:
        service.preview(root_id="dropbox_stock", relative_prefix="重点关注")
    assert exc.value.operation == "focus-cleanup"

    with pytest.raises(RetiredMaintenanceError) as exc:
        service.apply(
            root_id="dropbox_stock",
            relative_prefix="重点关注",
            confirmation_token="unknown-token",
            snapshot_path=tmp_path / "snapshot.jsonl",
            receipt_path=tmp_path / "receipt.json",
        )
    assert exc.value.operation == "focus-cleanup"

    with pytest.raises(RetiredMaintenanceError) as exc:
        service.restore_files(
            manifest_path=tmp_path / "missing-manifest.json",
            dest_root=tmp_path / "restored",
        )
    assert exc.value.operation == "focus-cleanup-restore-files"

    with pytest.raises(RetiredMaintenanceError) as exc:
        service.restore_database(
            snapshot_path=tmp_path / "missing-snapshot.jsonl",
            database_path=tmp_path / "missing.sqlite3",
        )
    assert exc.value.operation == "focus-cleanup-restore-database"

    assert _tree(tmp_path) == []


def test_archive_retires_for_cli_shape_and_with_now_without_touching_paths(tmp_path):
    missing_db = tmp_path / "missing.sqlite3"
    archive_root = tmp_path / "manifests"

    with pytest.raises(RetiredMaintenanceError) as exc:
        archive_retired_evidence(missing_db, archive_root)
    assert exc.value.operation == "archive-retired-evidence"
    assert not isinstance(exc.value, TypeError)

    with pytest.raises(RetiredMaintenanceError) as exc:
        archive_retired_evidence(missing_db, archive_root, now=NOW)
    assert exc.value.operation == "archive-retired-evidence"

    assert not archive_root.exists()
    assert not missing_db.exists()
    assert _tree(tmp_path) == []


def test_prune_retires_for_dry_run_apply_now_and_plan_shapes(tmp_path):
    config = _ExplodingCatalog()
    archive_root = tmp_path / "manifests"

    for kwargs in (
        {},  # CLI shape: no ``now``, no ``apply``
        {"apply": True},  # destructive flag
        {"now": NOW},  # explicit clock
        {"apply": True, "now": NOW, "plan": object()},  # frozen-plan shape
        {"apply": False, "now": NOW, "retention_days": 1},
    ):
        with pytest.raises(RetiredMaintenanceError) as exc:
            prune_retired_evidence(config, archive_root, **kwargs)
        assert exc.value.operation == "prune-retired-evidence"
        assert not isinstance(exc.value, TypeError)

    assert _tree(tmp_path) == []


def test_duplicate_write_entries_retire_with_zero_side_effects(tmp_path):
    config = module.CatalogConfig(
        project_root=tmp_path / "project",
        catalog_dir=tmp_path / "project" / ".source_catalog",
        roots=(module.RootSpec("external", tmp_path / "sources", "directory"),),
    )
    catalog = module.SourceCatalog(config)
    service = DuplicateCleanupService(catalog)
    assert catalog._store is None  # construction opened no Store

    target = tmp_path / "copy.txt"
    target.write_bytes(b"identical bytes")
    before = _sha(target)

    with pytest.raises(RetiredMaintenanceError) as exc:
        service.preview("loc-1")
    assert exc.value.operation == "duplicate-preview"
    assert isinstance(exc.value, DuplicateCleanupError)  # legacy catch compat

    recycler_calls: list[Path] = []
    service.recycler = lambda path: recycler_calls.append(path)
    with pytest.raises(RetiredMaintenanceError) as exc:
        service.recycle("loc-1", confirmation_token="stale-token")
    assert exc.value.operation == "duplicate-recycle"
    assert isinstance(exc.value, DuplicateCleanupError)
    assert recycler_calls == []

    with pytest.raises(RetiredMaintenanceError) as exc:
        recycle_to_windows_bin(target)
    assert exc.value.operation == "duplicate-recycle-bin"
    assert _sha(target) == before
    assert target.is_file()

    journal = DuplicateCleanupJournal(config.catalog_dir)
    with pytest.raises(RetiredMaintenanceError) as exc:
        journal.record(
            action_id="action-1",
            event="requested",
            location_id="loc-1",
            absolute_path=str(target),
            canonical_location_id="loc-0",
            canonical_path=str(target),
            source_id="src-1",
            content_sha256=before,
        )
    assert exc.value.operation == "duplicate-journal-record"

    assert catalog._store is None  # no read entrypoint constructed a Store
    assert not journal.path.exists()
    assert not config.catalog_dir.exists()
    assert _tree(tmp_path) == ["copy.txt"]


def test_journal_record_retirement_preserves_existing_history(tmp_path):
    journal = DuplicateCleanupJournal(tmp_path)
    journal.path.write_text(
        '{"schema_version": "1.0", "event": "requested"}\n', encoding="utf-8"
    )
    before = journal.path.read_bytes()

    with pytest.raises(RetiredMaintenanceError) as exc:
        journal.record(
            action_id="action-1",
            event="requested",
            location_id="loc-1",
            absolute_path="x",
            canonical_location_id="loc-0",
            canonical_path="x",
            source_id="src-1",
            content_sha256="a" * 64,
        )
    assert exc.value.operation == "duplicate-journal-record"
    assert journal.path.read_bytes() == before


def test_legacy_call_shapes_do_not_raise_typeerror_before_retirement(tmp_path):
    """Old callers (positional args, keyword-only combos) all hit the same
    retirement signal — never an argument-shape TypeError first."""
    with pytest.raises(RetiredMaintenanceError):
        archive_retired_evidence(str(tmp_path / "db.sqlite3"), str(tmp_path / "arc"))
    with pytest.raises(RetiredMaintenanceError):
        prune_retired_evidence(object(), tmp_path / "arc", now=None)


# ---------------------------------------------------------------------------
# E2E: scratch catalog with canonical / semantic / retired records, real
# inventory reads, then every legacy write/restore entry — named retirement,
# originals + DB + directory byte-identical afterwards.
# ---------------------------------------------------------------------------

TWIN = b"ACME fiscal 2025 annual report. " * 16
NEAR = b"ACME fiscal 2025 annual repoZt. " * 16  # same size, different bytes


def _scratch_catalog(tmp_path: Path):
    project = tmp_path / "project"
    root0 = tmp_path / "roots" / "alpha"
    root1 = tmp_path / "roots" / "beta"
    root2 = tmp_path / "roots" / "gamma"
    for root in (root0, root1, root2):
        root.mkdir(parents=True)

    (root0 / "annual.txt").write_bytes(TWIN)
    (root1 / "annual-copy.txt").write_bytes(TWIN)
    (root2 / "annual-near.txt").write_bytes(NEAR)
    (root0 / "sem-a.txt").write_text("Revenue 100.\n\nProfit 20.", encoding="utf-8")
    (root1 / "sem-b.txt").write_text("Revenue   100.\r\n\tProfit 20.", encoding="utf-8")
    (root0 / "retired-body.txt").write_text("retired filing body", encoding="utf-8")

    catalog = module.SourceCatalog(
        module.CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(
                module.RootSpec("alpha", root0, "directory", priority=10),
                module.RootSpec("beta", root1, "directory", priority=30),
                module.RootSpec("gamma", root2, "directory", priority=30),
            ),
        )
    )
    catalog.scan()
    legacy_normalize(catalog)
    retired = catalog.store.fetchone(
        """SELECT location_id FROM locations
        WHERE root_id='alpha' AND relative_path='retired-body.txt'"""
    )
    assert retired is not None
    document = catalog.store.fetchone(
        "SELECT document_id FROM locations WHERE location_id=?",
        (retired["location_id"],),
    )
    retire_document(
        catalog.store,
        document_id=document["document_id"],
        reason="g3-e2e-retirement",
        created_by="g3-cwp-maint",
    )
    return catalog


def _retired_write_calls(tmp_path: Path, catalog):
    """Yield ``(label, operation, callable)`` for every legacy write/restore entry."""
    service = FocusScopeCleanupService(catalog)
    duplicate = DuplicateCleanupService(catalog)
    archive_root = tmp_path / "manifests"
    config = catalog.config
    return [
        (
            "focus-preview",
            "focus-cleanup",
            lambda: service.preview(root_id="alpha", relative_prefix="重点关注"),
        ),
        (
            "focus-apply",
            "focus-cleanup",
            lambda: service.apply(
                root_id="alpha",
                relative_prefix="重点关注",
                confirmation_token="any-token",
                snapshot_path=tmp_path / "snap.jsonl",
                receipt_path=tmp_path / "receipt.json",
            ),
        ),
        (
            "focus-restore-files",
            "focus-cleanup-restore-files",
            lambda: service.restore_files(
                manifest_path=tmp_path / "manifest.json",
                dest_root=tmp_path / "restored",
            ),
        ),
        (
            "focus-restore-database",
            "focus-cleanup-restore-database",
            lambda: service.restore_database(
                snapshot_path=tmp_path / "snap.jsonl",
                database_path=config.database_path,
            ),
        ),
        (
            "archive-no-now",
            "archive-retired-evidence",
            lambda: archive_retired_evidence(config.database_path, archive_root),
        ),
        (
            "archive-with-now",
            "archive-retired-evidence",
            lambda: archive_retired_evidence(
                config.database_path, archive_root, now=NOW
            ),
        ),
        (
            "prune-dry-run",
            "prune-retired-evidence",
            lambda: prune_retired_evidence(config, archive_root, now=NOW),
        ),
        (
            "prune-apply",
            "prune-retired-evidence",
            lambda: prune_retired_evidence(config, archive_root, apply=True, now=NOW),
        ),
        (
            "prune-no-now",
            "prune-retired-evidence",
            lambda: prune_retired_evidence(config, archive_root, apply=True),
        ),
        (
            "duplicate-preview",
            "duplicate-preview",
            lambda: duplicate.preview("loc-1"),
        ),
        (
            "duplicate-recycle",
            "duplicate-recycle",
            lambda: duplicate.recycle("loc-1", confirmation_token="stale"),
        ),
        (
            "recycle-bin",
            "duplicate-recycle-bin",
            lambda: recycle_to_windows_bin(tmp_path / "roots" / "alpha" / "annual.txt"),
        ),
        (
            "journal-record",
            "duplicate-journal-record",
            lambda: DuplicateCleanupJournal(config.catalog_dir).record(
                action_id="a",
                event="requested",
                location_id="loc-1",
                absolute_path="x",
                canonical_location_id="loc-0",
                canonical_path="x",
                source_id="s",
                content_sha256="a" * 64,
            ),
        ),
    ]


def test_e2e_legacy_writes_retire_and_leave_originals_db_and_tree_unchanged(
    tmp_path,
):
    catalog = _scratch_catalog(tmp_path)

    # --- read phase: real inventory reads succeed ---
    inventory = DuplicateCleanupService(catalog).list_groups(
        limit=50, include_semantic=True
    )
    exact = [
        group for group in inventory["groups"] if group["relation_type"] == "exact_copy"
    ]
    semantic = [
        group
        for group in inventory["groups"]
        if group["relation_type"] == "semantic_copy"
    ]
    assert len(exact) == 1 and exact[0]["copy_count"] == 2
    assert len(semantic) == 1 and semantic[0]["copy_count"] == 2
    exact_paths = {
        item["absolute_path"]
        for item in [exact[0]["canonical"], *exact[0]["duplicates"]]
    }
    assert str((tmp_path / "roots" / "gamma" / "annual-near.txt").resolve()) not in (
        exact_paths
    )
    assert DuplicateCleanupJournal(catalog.config.catalog_dir).read_all() == ()

    retired_row = catalog.store.fetchone(
        """SELECT d.source_status FROM documents d
        JOIN locations l ON l.document_id=d.document_id
        WHERE l.relative_path='retired-body.txt'"""
    )
    assert retired_row["source_status"] == "retired"

    # --- snapshot AFTER the reads (card ordering), then retire every entry ---
    originals = [
        tmp_path / "roots" / "alpha" / "annual.txt",
        tmp_path / "roots" / "beta" / "annual-copy.txt",
    ]
    original_shas = {str(path): _sha(path) for path in originals}
    db_sha = _sha(catalog.config.database_path)
    tree_before = _tree(tmp_path)

    for label, operation, call in _retired_write_calls(tmp_path, catalog):
        with pytest.raises(RetiredMaintenanceError) as exc:
            call()
        assert exc.value.operation == operation, label

    for path_text, digest in original_shas.items():
        path = Path(path_text)
        assert path.is_file(), path_text
        assert _sha(path) == digest, path_text
    assert _sha(catalog.config.database_path) == db_sha
    assert _tree(tmp_path) == tree_before
    assert not (catalog.config.catalog_dir / "duplicate_cleanup_events.jsonl").exists()
