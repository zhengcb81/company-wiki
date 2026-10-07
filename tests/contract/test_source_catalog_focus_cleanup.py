"""Reference-aware focus cleanup is retired (G3-CWP-MAINT).

The legacy focus-cleanup preview/apply/restore entries fail closed with the
unified retirement signal before any Store, lock, file or receipt is
touched.  What stays asserted is the honest read behaviour: originals are
preserved, rescans stay stable, and the CLI branch fails closed as retired
without writing a receipt or snapshot.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
from company_wiki.source_catalog.focus_cleanup import FocusScopeCleanupService
from company_wiki.source_catalog.maintenance_retirement import (
    RetiredMaintenanceError,
)
from support.legacy_source_artifact_fixture import legacy_normalize, legacy_summarize


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree(root: Path) -> list[str]:
    return sorted(str(p.relative_to(root)).replace("\\", "/") for p in root.rglob("*"))


def _legacy_catalog(tmp_path: Path):
    project = tmp_path / "project"
    root = tmp_path / "Dropbox" / "Stock"
    legacy = root / "legacy"
    outside = root / "其他"
    legacy.mkdir(parents=True)
    outside.mkdir()

    shared_target = legacy / "投资笔记.txt"
    shared_target.write_text("same bytes outside focus", encoding="utf-8")
    shared_sidecar = shared_target.with_name(shared_target.name + ".source.json")
    shared_sidecar.write_text(
        json.dumps({"market": "HK", "security_id": "ACME", "source_title": "投资笔记"}),
        encoding="utf-8",
    )
    shared_outside = outside / "copy.txt"
    shared_outside.write_bytes(shared_target.read_bytes())

    orphan = legacy / "股票池.txt"
    orphan.write_text("target-only source", encoding="utf-8")
    orphan_sidecar = orphan.with_name(orphan.name + ".source.json")
    orphan_sidecar.write_text(
        json.dumps({"market": "HK", "security_id": "ACME", "source_title": "股票池"}),
        encoding="utf-8",
    )

    allowed = legacy / "Acme招股说明书.txt"
    allowed.write_text("prospectus source", encoding="utf-8")
    allowed_sidecar = allowed.with_name(allowed.name + ".source.json")
    allowed_sidecar.write_text(
        json.dumps(
            {
                "market": "US",
                "security_id": "ACME",
                "source_title": "Acme招股说明书",
                "document_kind": "prospectus",
            }
        ),
        encoding="utf-8",
    )

    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("dropbox_stock", root, "directory", priority=30),),
        )
    )
    catalog.scan()
    legacy_normalize(catalog)
    legacy_summarize(catalog)

    focus = root / "重点关注"
    legacy.rename(focus)
    with catalog.store.transaction() as connection:
        rows = connection.execute(
            """SELECT location_id,relative_path FROM locations
            WHERE root_id='dropbox_stock' AND relative_path LIKE 'legacy/%'"""
        ).fetchall()
        for row in rows:
            relative = "重点关注/" + row["relative_path"][len("legacy/") :]
            absolute = root.joinpath(*relative.split("/")).resolve()
            connection.execute(
                "UPDATE locations SET relative_path=?,absolute_path=? WHERE location_id=?",
                (relative, str(absolute), row["location_id"]),
            )

    originals = [
        focus / name for name in ("投资笔记.txt", "股票池.txt", "Acme招股说明书.txt")
    ]
    original_manifest = {
        str(path): (_sha(path), path.stat().st_mtime_ns) for path in originals
    }
    orphan_document = catalog.store.fetchone(
        """SELECT document_id FROM locations
        WHERE root_id='dropbox_stock' AND relative_path='重点关注/股票池.txt'"""
    )["document_id"]
    shared_document = catalog.store.fetchone(
        """SELECT document_id FROM locations
        WHERE root_id='dropbox_stock' AND relative_path='重点关注/投资笔记.txt'"""
    )["document_id"]
    orphan_artifacts = catalog.store.fetchall(
        "SELECT path FROM artifacts WHERE document_id=?", (orphan_document,)
    )
    return {
        "catalog": catalog,
        "focus": focus,
        "originals": originals,
        "original_manifest": original_manifest,
        "orphan_document": orphan_document,
        "shared_document": shared_document,
        "orphan_artifact_paths": [Path(row["path"]) for row in orphan_artifacts],
        "allowed_sidecar": focus / "Acme招股说明书.txt.source.json",
    }


def _counts(catalog) -> dict[str, int]:
    return {
        table: catalog.store.fetchone(f"SELECT count(*) AS n FROM {table}")["n"]
        for table in (
            "locations",
            "documents",
            "sources",
            "artifacts",
            "evidence_spans",
        )
    }


def test_focus_cleanup_entries_retire_without_touching_catalog_or_files(
    tmp_path: Path,
):
    fixture = _legacy_catalog(tmp_path)
    catalog = fixture["catalog"]
    service = FocusScopeCleanupService(catalog)
    before = _counts(catalog)
    tree_before = _tree(tmp_path)

    with pytest.raises(RetiredMaintenanceError) as exc:
        service.preview(root_id="dropbox_stock", relative_prefix="重点关注")
    assert exc.value.operation == "focus-cleanup"

    with pytest.raises(RetiredMaintenanceError) as exc:
        service.apply(
            root_id="dropbox_stock",
            relative_prefix="重点关注",
            confirmation_token="stale-token",
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
            database_path=catalog.config.database_path,
        )
    assert exc.value.operation == "focus-cleanup-restore-database"

    assert _counts(catalog) == before
    assert _tree(tmp_path) == tree_before
    assert all(path.is_file() for path in fixture["originals"])
    assert {
        str(path): (_sha(path), path.stat().st_mtime_ns)
        for path in fixture["originals"]
    } == fixture["original_manifest"]
    assert (fixture["focus"] / "投资笔记.txt.source.json").is_file()
    assert (fixture["focus"] / "股票池.txt.source.json").is_file()
    assert fixture["allowed_sidecar"].is_file()
    assert not (tmp_path / "snapshot.jsonl").exists()
    assert not (tmp_path / "receipt.json").exists()
    assert not (catalog.config.catalog_dir / "focus_cleanup_archive").exists()


def test_focus_cleanup_scope_and_token_validation_is_retired(tmp_path: Path):
    fixture = _legacy_catalog(tmp_path)
    service = FocusScopeCleanupService(fixture["catalog"])
    preview_token = "any-token"

    for root_id, prefix in (
        ("company_raw", "重点关注"),
        ("dropbox_stock", ""),
        ("dropbox_stock", "重点关注旧"),
        ("dropbox_stock", "../重点关注"),
    ):
        with pytest.raises(RetiredMaintenanceError) as exc:
            service.preview(root_id=root_id, relative_prefix=prefix)
        assert exc.value.operation == "focus-cleanup"

    (fixture["focus"] / "新投资笔记.txt").write_text("new", encoding="utf-8")
    with pytest.raises(RetiredMaintenanceError) as exc:
        service.apply(
            root_id="dropbox_stock",
            relative_prefix="重点关注",
            confirmation_token=preview_token,
            snapshot_path=tmp_path / "snapshot.jsonl",
            receipt_path=tmp_path / "receipt.json",
        )
    assert exc.value.operation == "focus-cleanup"
    assert not (tmp_path / "snapshot.jsonl").exists()
    assert not (tmp_path / "receipt.json").exists()


def test_focus_cleanup_retirement_keeps_rescan_state_stable(tmp_path: Path):
    fixture = _legacy_catalog(tmp_path)
    catalog = fixture["catalog"]
    service = FocusScopeCleanupService(catalog)
    tree_before = _tree(tmp_path)

    with pytest.raises(RetiredMaintenanceError):
        service.apply(
            root_id="dropbox_stock",
            relative_prefix="重点关注",
            confirmation_token="stale",
            snapshot_path=tmp_path / "snapshot.jsonl",
            receipt_path=tmp_path / "receipt.json",
        )

    def snapshot():
        scan = catalog.scan(root_ids={"dropbox_stock"})
        rows = catalog.store.fetchall(
            """SELECT l.relative_path,l.role,d.document_kind
            FROM locations l JOIN documents d ON d.document_id=l.document_id
            WHERE l.root_id='dropbox_stock' AND l.relative_path LIKE '重点关注/%'
            ORDER BY l.relative_path"""
        )
        return (
            scan.policy_excluded,
            [tuple(row) for row in rows],
            _counts(catalog),
        )

    first = snapshot()
    second = snapshot()
    assert first == second  # two rescans do not drift without the cleanup
    assert (fixture["focus"] / "投资笔记.txt.source.json").is_file()
    assert (fixture["focus"] / "股票池.txt.source.json").is_file()
    assert fixture["allowed_sidecar"].is_file()
    assert _tree(tmp_path) == tree_before
    assert {
        str(path): (_sha(path), path.stat().st_mtime_ns)
        for path in fixture["originals"]
    } == fixture["original_manifest"]


def test_focus_cleanup_cli_fails_closed_as_retired(tmp_path: Path, capsys):
    import company_wiki.source_catalog.cli as cli

    fixture = _legacy_catalog(tmp_path)
    catalog = fixture["catalog"]
    config_path = catalog.config.project_root / "config" / "source_catalog.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0",
                "catalog_dir": "${PROJECT_ROOT}/.source_catalog",
                "roots": [
                    {
                        "root_id": "dropbox_stock",
                        "kind": "directory",
                        "path": str(catalog.config.roots[0].path),
                        "priority": 30,
                    }
                ],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    dry_receipt = tmp_path / "cli-dry-run.json"
    before = catalog.store.fetchone("SELECT count(*) AS n FROM locations")["n"]

    # dry-run branch reaches the retired library entry: named failure, no receipt
    exit_code = cli.main(
        [
            "--config",
            str(config_path),
            "focus-cleanup",
            "--root-id",
            "dropbox_stock",
            "--relative-prefix",
            "重点关注",
            "--receipt-path",
            str(dry_receipt),
        ]
    )
    error = json.loads(capsys.readouterr().err)
    assert exit_code == 1
    assert error["status"] == "failed"
    assert "retired" in error["error"]
    assert "focus-cleanup" in error["error"]
    assert not dry_receipt.exists()
    assert catalog.store.fetchone("SELECT count(*) AS n FROM locations")["n"] == before

    # --apply is also retired, without the old permit checks
    exit_code = cli.main(
        [
            "--config",
            str(config_path),
            "focus-cleanup",
            "--root-id",
            "dropbox_stock",
            "--relative-prefix",
            "重点关注",
            "--apply",
        ]
    )
    error = json.loads(capsys.readouterr().err)
    assert exit_code == 1
    assert error["error_type"] == "maintenance_operation_retired"
    assert error["error_code"] == "MAINTENANCE_OPERATION_RETIRED"
    assert catalog.store.fetchone("SELECT count(*) AS n FROM locations")["n"] == before

    # --apply with every guard supplied still fails closed as retired, 0 writes
    snapshot_path = tmp_path / "cli-snapshot.jsonl"
    receipt_path = tmp_path / "cli-receipt.json"
    exit_code = cli.main(
        [
            "--config",
            str(config_path),
            "focus-cleanup",
            "--root-id",
            "dropbox_stock",
            "--relative-prefix",
            "重点关注",
            "--apply",
            "--confirmation-token",
            "any-token",
            "--snapshot-path",
            str(snapshot_path),
            "--receipt-path",
            str(receipt_path),
        ]
    )
    error = json.loads(capsys.readouterr().err)
    assert exit_code == 1
    assert "retired" in error["error"]
    assert not snapshot_path.exists()
    assert not receipt_path.exists()
    assert catalog.store.fetchone("SELECT count(*) AS n FROM locations")["n"] == before
