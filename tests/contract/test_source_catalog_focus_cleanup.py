"""Reference-aware cleanup contracts for the focus admission policy."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
from company_wiki.source_catalog.focus_cleanup import FocusScopeCleanupService


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
        json.dumps(
            {"market": "HK", "security_id": "ACME", "source_title": "投资笔记"}
        ),
        encoding="utf-8",
    )
    shared_outside = outside / "copy.txt"
    shared_outside.write_bytes(shared_target.read_bytes())

    orphan = legacy / "股票池.txt"
    orphan.write_text("target-only source", encoding="utf-8")
    orphan_sidecar = orphan.with_name(orphan.name + ".source.json")
    orphan_sidecar.write_text(
        json.dumps(
            {"market": "HK", "security_id": "ACME", "source_title": "股票池"}
        ),
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
    catalog.normalize()
    catalog.summarize()

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

    originals = [focus / name for name in ("投资笔记.txt", "股票池.txt", "Acme招股说明书.txt")]
    original_manifest = {str(path): (_sha(path), path.stat().st_mtime_ns) for path in originals}
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


def test_focus_cleanup_preview_is_read_only_and_reference_aware(tmp_path: Path):
    fixture = _legacy_catalog(tmp_path)
    catalog = fixture["catalog"]
    before = {
        table: catalog.store.fetchone(f"SELECT count(*) AS n FROM {table}")["n"]
        for table in ("locations", "documents", "sources", "artifacts", "evidence_spans")
    }

    preview = FocusScopeCleanupService(catalog).preview(
        root_id="dropbox_stock", relative_prefix="重点关注"
    )

    after = {
        table: catalog.store.fetchone(f"SELECT count(*) AS n FROM {table}")["n"]
        for table in before
    }
    assert after == before
    assert preview["mode"] == "dry_run"
    assert preview["original_delete_count"] == 0
    assert preview["sidecars_to_delete"] == 2
    assert preview["shared_documents_preserved"] == 1
    assert preview["orphan_documents_to_delete"] >= 1
    assert preview["confirmation_token"]


def test_focus_cleanup_apply_dedupes_duplicate_artifact_paths(tmp_path: Path):
    # Multiple artifact rows may reference the same derived file; apply must
    # archive/delete each file exactly once and still report completed.
    fixture = _legacy_catalog(tmp_path)
    catalog = fixture["catalog"]
    service = FocusScopeCleanupService(catalog)
    archive_dir = tmp_path / "dedupe-archive"
    preview = service.preview(root_id="dropbox_stock", relative_prefix="重点关注")
    duplicate_path = fixture["orphan_artifact_paths"][0]
    with catalog.store.transaction() as connection:
        row = connection.execute(
            "SELECT * FROM artifacts WHERE path=? LIMIT 1", (str(duplicate_path),)
        ).fetchone()
        connection.execute(
            """INSERT INTO artifacts(artifact_id,document_id,source_id,artifact_role,
            path,content_sha256,byte_size,mime_type,generator_name,generator_version,
            status,error,metadata_json,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(row["artifact_id"]) + "-dup",
                row["document_id"],
                row["source_id"],
                str(row["artifact_role"]) + "_duplicate",
                row["path"],
                row["content_sha256"],
                row["byte_size"],
                row["mime_type"],
                row["generator_name"],
                row["generator_version"],
                row["status"],
                row["error"],
                row["metadata_json"],
                row["created_at"],
            ),
        )

    result = service.apply(
        root_id="dropbox_stock",
        relative_prefix="重点关注",
        confirmation_token=preview["confirmation_token"],
        snapshot_path=tmp_path / "dedupe-snapshot.jsonl",
        receipt_path=tmp_path / "dedupe-receipt.json",
        archive_dir=archive_dir,
    )

    assert result["status"] == "completed"
    assert result["filesystem_errors"] == []
    assert result["archived_files"] >= 1
    assert not duplicate_path.exists()
    manifest = json.loads(
        (archive_dir / "manifest.json").read_text(encoding="utf-8")
    )
    paths = [entry["original_path"] for entry in manifest["files"]]
    assert paths.count(str(duplicate_path)) == 1


def test_focus_cleanup_apply_preserves_originals_and_shared_document(tmp_path: Path):
    fixture = _legacy_catalog(tmp_path)
    catalog = fixture["catalog"]
    service = FocusScopeCleanupService(catalog)
    preview = service.preview(root_id="dropbox_stock", relative_prefix="重点关注")
    snapshot = tmp_path / "affected-rows.jsonl"
    receipt = tmp_path / "cleanup-receipt.json"

    result = service.apply(
        root_id="dropbox_stock",
        relative_prefix="重点关注",
        confirmation_token=preview["confirmation_token"],
        snapshot_path=snapshot,
        receipt_path=receipt,
    )

    assert result["status"] == "completed"
    assert result["original_delete_count"] == 0
    assert snapshot.is_file() and receipt.is_file()
    assert all(path.is_file() for path in fixture["originals"])
    assert {
        str(path): (_sha(path), path.stat().st_mtime_ns) for path in fixture["originals"]
    } == fixture["original_manifest"]
    assert not (fixture["focus"] / "投资笔记.txt.source.json").exists()
    assert not (fixture["focus"] / "股票池.txt.source.json").exists()
    assert fixture["allowed_sidecar"].is_file()

    shared = catalog.store.fetchone(
        "SELECT document_id FROM documents WHERE document_id=?",
        (fixture["shared_document"],),
    )
    orphan = catalog.store.fetchone(
        "SELECT document_id FROM documents WHERE document_id=?",
        (fixture["orphan_document"],),
    )
    assert shared is not None
    assert orphan is None
    assert catalog.store.fetchone(
        """SELECT count(*) AS n FROM locations
        WHERE document_id=? AND relative_path='其他/copy.txt'""",
        (fixture["shared_document"],),
    )["n"] == 1
    assert all(not path.exists() for path in fixture["orphan_artifact_paths"])
    assert catalog.store.fetchone("PRAGMA foreign_key_check") is None

    second = service.preview(root_id="dropbox_stock", relative_prefix="重点关注")
    second_result = service.apply(
        root_id="dropbox_stock",
        relative_prefix="重点关注",
        confirmation_token=second["confirmation_token"],
        snapshot_path=tmp_path / "affected-rows-2.jsonl",
        receipt_path=tmp_path / "cleanup-receipt-2.json",
    )
    assert second_result["database_locations_deleted"] == 0
    assert second_result["sidecars_deleted"] == 0


def test_focus_cleanup_two_rescans_do_not_recreate_rejected_catalog_state(
    tmp_path: Path,
):
    fixture = _legacy_catalog(tmp_path)
    catalog = fixture["catalog"]
    service = FocusScopeCleanupService(catalog)
    preview = service.preview(root_id="dropbox_stock", relative_prefix="重点关注")
    service.apply(
        root_id="dropbox_stock",
        relative_prefix="重点关注",
        confirmation_token=preview["confirmation_token"],
        snapshot_path=tmp_path / "snapshot.jsonl",
        receipt_path=tmp_path / "receipt.json",
    )

    first = catalog.scan(root_ids={"dropbox_stock"})
    document_count_after_first = catalog.store.fetchone(
        "SELECT count(*) AS n FROM documents"
    )["n"]
    second = catalog.scan(root_ids={"dropbox_stock"})

    target_rows = catalog.store.fetchall(
        """SELECT l.relative_path,l.role,d.document_kind
        FROM locations l JOIN documents d ON d.document_id=l.document_id
        WHERE l.root_id='dropbox_stock' AND l.relative_path LIKE '重点关注/%'
        ORDER BY l.relative_path"""
    )
    assert [(row["relative_path"], row["role"], row["document_kind"]) for row in target_rows] == [
        ("重点关注/Acme招股说明书.txt", "original_primary", "prospectus"),
        ("重点关注/Acme招股说明书.txt.source.json", "metadata", "prospectus"),
    ]
    assert first.policy_excluded == 2
    assert second.policy_excluded == 2
    assert catalog.store.fetchone("SELECT count(*) AS n FROM documents")["n"] == (
        document_count_after_first
    )
    assert not (fixture["focus"] / "投资笔记.txt.source.json").exists()
    assert not (fixture["focus"] / "股票池.txt.source.json").exists()


def test_focus_cleanup_rejects_wrong_scope_and_stale_confirmation(tmp_path: Path):
    fixture = _legacy_catalog(tmp_path)
    service = FocusScopeCleanupService(fixture["catalog"])
    preview = service.preview(root_id="dropbox_stock", relative_prefix="重点关注")

    for root_id, prefix in (
        ("company_raw", "重点关注"),
        ("dropbox_stock", ""),
        ("dropbox_stock", "重点关注旧"),
        ("dropbox_stock", "../重点关注"),
    ):
        try:
            service.preview(root_id=root_id, relative_prefix=prefix)
        except ValueError:
            pass
        else:
            raise AssertionError("unsafe cleanup scope was accepted")

    (fixture["focus"] / "新投资笔记.txt").write_text("new", encoding="utf-8")
    try:
        service.apply(
            root_id="dropbox_stock",
            relative_prefix="重点关注",
            confirmation_token=preview["confirmation_token"],
            snapshot_path=tmp_path / "snapshot.jsonl",
            receipt_path=tmp_path / "receipt.json",
        )
    except ValueError as exc:
        assert "confirmation" in str(exc).lower()
    else:
        raise AssertionError("stale cleanup confirmation was accepted")


def test_focus_cleanup_apply_archives_deleted_files_and_restores(tmp_path: Path):
    # Blocker 4+5: deleted sidecars/derived files must be archived with SHA and
    # restorable byte-for-byte; DB rows must be rebuildable from the snapshot.
    fixture = _legacy_catalog(tmp_path)
    catalog = fixture["catalog"]
    service = FocusScopeCleanupService(catalog)
    archive_dir = tmp_path / "cleanup-archive"
    preview = service.preview(root_id="dropbox_stock", relative_prefix="重点关注")
    snapshot = tmp_path / "affected-rows.jsonl"
    receipt = tmp_path / "cleanup-receipt.json"

    deleted_sidecars = [
        fixture["focus"] / "投资笔记.txt.source.json",
        fixture["focus"] / "股票池.txt.source.json",
    ]
    before_bytes = {str(p): p.read_bytes() for p in deleted_sidecars}
    before_sha = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in deleted_sidecars
    }
    before_counts = {
        table: catalog.store.fetchone(f"SELECT count(*) AS n FROM {table}")["n"]
        for table in ("locations", "documents", "sources", "artifacts")
    }

    result = service.apply(
        root_id="dropbox_stock",
        relative_prefix="重点关注",
        confirmation_token=preview["confirmation_token"],
        snapshot_path=snapshot,
        receipt_path=receipt,
        archive_dir=archive_dir,
    )

    assert result["status"] == "completed"
    assert not any(p.exists() for p in deleted_sidecars)
    manifest_path = archive_dir / "manifest.json"
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    archived = {
        entry["original_path"]: entry
        for entry in manifest["files"]
        if entry["original_path"] in before_sha
    }
    assert set(archived) == set(before_sha)
    for original_path, entry in archived.items():
        assert entry["content_sha256"] == before_sha[original_path]
        member = archive_dir / entry["archive_member"]
        assert hashlib.sha256(member.read_bytes()).hexdigest() == entry[
            "content_sha256"
        ]

    # Restore drill: bytes come back identical.
    restore_dir = tmp_path / "restored"
    service.restore_files(manifest_path=manifest_path, dest_root=restore_dir)
    for path_text, data in before_bytes.items():
        original = Path(path_text)
        relative = original.relative_to(fixture["focus"].parent)
        restored = restore_dir / relative
        assert restored.is_file()
        assert restored.read_bytes() == data

    # DB row rebuild from the JSONL snapshot (FK-safe reverse order).
    restored = service.restore_database(
        snapshot_path=snapshot,
        database_path=catalog.config.database_path,
    )
    assert restored["total_rows"] > 0
    assert restored["foreign_key_violations"] == 0
    after_counts = {
        table: catalog.store.fetchone(f"SELECT count(*) AS n FROM {table}")["n"]
        for table in before_counts
    }
    assert after_counts == before_counts
    shared = catalog.store.fetchone(
        "SELECT document_id FROM documents WHERE document_id=?",
        (fixture["shared_document"],),
    )
    orphan = catalog.store.fetchone(
        "SELECT document_id FROM documents WHERE document_id=?",
        (fixture["orphan_document"],),
    )
    assert shared is not None and orphan is not None
    assert catalog.store.fetchone("PRAGMA foreign_key_check") is None


def test_focus_cleanup_cli_defaults_to_dry_run_and_apply_requires_all_guards(
    tmp_path: Path, capsys
):
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
    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["mode"] == "dry_run"
    assert dry_receipt.is_file()
    assert catalog.store.fetchone("SELECT count(*) AS n FROM locations")["n"] == before

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
    assert error["error_type"] == "ValueError"
    assert "requires" in error["error"]
    assert catalog.store.fetchone("SELECT count(*) AS n FROM locations")["n"] == before
