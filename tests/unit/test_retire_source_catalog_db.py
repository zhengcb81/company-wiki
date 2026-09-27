"""Isolated rehearsal for the active-only, stream-verified retirement tool."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
from contextlib import closing
from types import SimpleNamespace

import pytest

from scripts.retire_source_catalog_db import RetirementRefused, prepare
from scripts.cutover_source_catalog_db import CONTRACT_FILES, CutoverRefused, cutover, rollback, smoke, retire
import scripts.cutover_source_catalog_db as cutover_module


def _zstd_fixture_path() -> Path:
    executable = shutil.which("zstd") or shutil.which("zstd.exe")
    if executable is None:
        pytest.skip("zstd executable is required for the retirement rehearsal")
    return Path(executable)


def _fixture_project(root: Path) -> tuple[Path, Path]:
    project = root / "project"
    catalog = project / ".source_catalog"
    catalog.mkdir(parents=True)
    (catalog / "worker_control.json").write_text(
        json.dumps({"desired_state": "paused"}), encoding="utf-8"
    )
    database = catalog / "catalog.sqlite3"
    with closing(sqlite3.connect(database)) as connection:
        connection.executescript(
            """
            CREATE TABLE catalog_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE sources(source_id TEXT PRIMARY KEY,content_sha256 TEXT);
            CREATE TABLE documents(document_id TEXT PRIMARY KEY,
                primary_source_id TEXT REFERENCES sources(source_id),
                source_status TEXT NOT NULL);
            CREATE TABLE evidence_spans(span_id TEXT PRIMARY KEY,
                document_id TEXT REFERENCES documents(document_id),
                source_id TEXT REFERENCES sources(source_id),
                locator TEXT NOT NULL,raw_text TEXT NOT NULL);
            CREATE TABLE artifacts(artifact_id TEXT PRIMARY KEY,document_id TEXT);
            CREATE TABLE producer_events(event_id TEXT PRIMARY KEY,artifact_id TEXT);
            CREATE TRIGGER trg_artifact_event AFTER INSERT ON artifacts BEGIN
              INSERT INTO producer_events VALUES('event-' || NEW.artifact_id,NEW.artifact_id);
            END;
            CREATE INDEX idx_spans_document ON evidence_spans(document_id);
            INSERT INTO catalog_meta VALUES('schema_version','1.2.0');
            INSERT INTO sources VALUES('active-source','a');
            INSERT INTO sources VALUES('retired-source','b');
            INSERT INTO documents VALUES('active-doc','active-source','active');
            INSERT INTO documents VALUES('retired-doc','retired-source','retired');
            INSERT INTO evidence_spans VALUES('active-span','active-doc',
                'active-source','loc:v1/page:1','selected business text');
            INSERT INTO evidence_spans VALUES('retired-span','retired-doc',
                'retired-source','loc:v1/page:2','old text');
            INSERT INTO artifacts VALUES('artifact-a','active-doc');
            """
        )
    return project, database


def test_prepare_preserves_source_and_stream_verifies_without_full_restore(tmp_path):
    project, database = _fixture_project(tmp_path)
    Path(str(database) + "-wal").touch()
    Path(str(database) + "-shm").write_bytes(bytes(32768))
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    result = prepare(
        project,
        "20260926T170000Z-a1b2c3d4",
        _zstd_fixture_path(),
    )
    assert result["source_sha256"] == before
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before
    assert result["decompressed_sha256"] == before
    assert result["decompressed_bytes"] == database.stat().st_size
    assert result["full_disk_restore_performed"] is False
    assert result["tables"]["evidence_spans"]["rows"] == 1
    assert result["trigger_names"] == ["trg_artifact_event"]
    assert Path(result["backup_path"]).is_file()
    assert not list(Path(result["backup_path"]).parent.glob("*restored*"))
    with closing(sqlite3.connect(result["shadow_path"])) as shadow:
        assert shadow.execute("SELECT span_id FROM evidence_spans").fetchall() == [
            ("active-span",)
        ]
        assert shadow.execute(
            "SELECT value FROM catalog_meta WHERE key='legacy_evidence_retention'"
        ).fetchone() == ("active_only",)
        assert shadow.execute("PRAGMA quick_check").fetchone() == ("ok",)
        assert shadow.execute("SELECT COUNT(*) FROM producer_events").fetchone() == (1,)
    assert json.loads(
        (Path(result["backup_path"]).parent / "prepared.json").read_text(
            encoding="utf-8"
        )
    )["cutover_performed"] is False


def test_prepare_refuses_unpaused_worker(tmp_path):
    project, database = _fixture_project(tmp_path)
    (project / ".source_catalog" / "worker_control.json").write_text(
        json.dumps({"desired_state": "running"}), encoding="utf-8"
    )
    with pytest.raises(RetirementRefused, match="paused"):
        prepare(
            project,
            "20260926T170000Z-a1b2c3d4",
            _zstd_fixture_path(),
        )
    assert database.is_file()
    assert not (project / ".source_catalog" / "retirement").exists()


def test_prepare_refuses_nonempty_wal(tmp_path):
    project, database = _fixture_project(tmp_path)
    Path(str(database) + "-wal").write_bytes(b"uncheckpointed")
    with pytest.raises(RetirementRefused, match="WAL"):
        prepare(
            project,
            "20260926T170000Z-a1b2c3d4",
            _zstd_fixture_path(),
        )


def test_cutover_requires_audits_and_can_rollback_exact_files(tmp_path):
    project, database = _fixture_project(tmp_path)
    Path(str(database) + "-wal").touch()
    Path(str(database) + "-shm").write_bytes(bytes(32768))
    result = prepare(
        project,
        "20260926T170000Z-a1b2c3d4",
        _zstd_fixture_path(),
    )
    receipt = Path(result["backup_path"]).parent / "prepared.json"
    with pytest.raises(FileNotFoundError):
        cutover(receipt)
    assert database.is_file()
    assert Path(result["shadow_path"]).is_file()
    _write_audits(receipt, result)
    cut = cutover(receipt)
    assert cut["production_sha256"] == result["shadow_sha256"]
    assert hashlib.sha256(database.read_bytes()).hexdigest() == result["shadow_sha256"]
    assert Path(str(database) + "-wal").exists() is False
    assert Path(str(database) + "-shm").exists() is False
    old = Path(cut["old_database"])
    assert hashlib.sha256(old.read_bytes()).hexdigest() == result["source_sha256"]
    rolled = rollback(receipt)
    assert rolled["source_sha256"] == result["source_sha256"]
    assert hashlib.sha256(database.read_bytes()).hexdigest() == result["source_sha256"]
    assert Path(str(database) + "-wal").exists()
    assert Path(str(database) + "-shm").exists()
    assert not old.exists()


def _write_audits(receipt: Path, result: dict):
    project = Path(result["project_root"])
    contract_hashes = {}
    for relative in CONTRACT_FILES:
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture contract", encoding="utf-8")
        contract_hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    sibling_root = Path(result["project_root"]).parent
    dependency_files = {
        "stockwiki_config_sha256": sibling_root / "StockWiki" / "config" / "source_provider.yaml",
        "forecast_client_sha256": sibling_root / "revenue-forecast" / "scripts" / "filing_fetch_client.py",
        "filing_fetch_sha256": sibling_root / "filing-fetch" / "scripts" / "fetch_filing.py",
    }
    for path in dependency_files.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture consumer", encoding="utf-8")
    (receipt.parent / "evidence_audit.json").write_text(json.dumps({
        "schema": "catalog-retirement-evidence-audit-v1",
        "status": "passed",
        "old_source_sha256": result["source_sha256"],
        "shadow_sha256": result["shadow_sha256"],
    }), encoding="utf-8")
    (receipt.parent / "consumer_audit.json").write_text(json.dumps({
        "schema": "catalog-retirement-consumer-audit-v1",
        "status": "passed",
        "source_sha256": result["source_sha256"],
        "shadow_sha256": result["shadow_sha256"],
        "contracts_checked": ["fixture-consumer"],
        **{key: hashlib.sha256(path.read_bytes()).hexdigest()
           for key, path in dependency_files.items()},
        "company_wiki_contract_sha256": contract_hashes,
    }), encoding="utf-8")


def test_retire_requires_separated_smokes_and_deletes_only_exact_old_files(tmp_path, monkeypatch):
    project, database = _fixture_project(tmp_path)
    Path(str(database) + "-wal").touch()
    Path(str(database) + "-shm").write_bytes(bytes(32768))
    result = prepare(project, "20260926T170000Z-a1b2c3d4",
                     _zstd_fixture_path())
    receipt = Path(result["backup_path"]).parent / "prepared.json"
    _write_audits(receipt, result)
    old = Path(cutover(receipt)["old_database"])

    class _Evidence:
        def lookup(self, **kwargs):
            return SimpleNamespace(document_id="active-doc")

    monkeypatch.setattr("scripts.cutover_source_catalog_db.EvidenceQueryService",
                        lambda path: _Evidence())
    assert smoke(receipt, 1)["status"] == "passed"
    assert smoke(receipt, 2)["status"] == "passed"
    with pytest.raises(CutoverRefused, match="too close"):
        retire(receipt)
    deleted = retire(receipt, minimum_interval_seconds=0)
    assert deleted["deleted_database"] == str(old)
    assert not old.exists()
    assert not Path(str(old) + "-wal").exists()
    assert not Path(str(old) + "-shm").exists()
    assert hashlib.sha256(database.read_bytes()).hexdigest() == result["shadow_sha256"]
    assert Path(result["backup_path"]).is_file()
    with pytest.raises(CutoverRefused, match="deletion has already begun"):
        rollback(receipt)


def test_cutover_interrupted_after_old_rename_restores_old_and_sidecars(tmp_path, monkeypatch):
    project, database = _fixture_project(tmp_path)
    Path(str(database) + "-wal").touch()
    Path(str(database) + "-shm").write_bytes(bytes(32768))
    result = prepare(project, "20260926T170000Z-a1b2c3d4",
                     _zstd_fixture_path())
    receipt = Path(result["backup_path"]).parent / "prepared.json"
    _write_audits(receipt, result)
    real_rename = cutover_module._rename

    def fail_shadow(source, target):
        if source.name == "catalog.active.sqlite3":
            raise PermissionError("injected failure after old rename")
        real_rename(source, target)

    monkeypatch.setattr(cutover_module, "_rename", fail_shadow)
    with pytest.raises(PermissionError, match="injected failure"):
        cutover(receipt)
    assert hashlib.sha256(database.read_bytes()).hexdigest() == result["source_sha256"]
    assert Path(str(database) + "-wal").exists()
    assert Path(str(database) + "-shm").exists()
    assert Path(result["shadow_path"]).exists()
    assert not Path(str(database) + ".retiring." + result["run_id"]).exists()
