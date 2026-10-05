"""Behavioral recovery/original protection tests against real legacy fixtures."""
from __future__ import annotations

from pathlib import Path

from support.p5_storage_catalog_fixture import build_catalog
from legacy_storage.inventory import run_inventory
from legacy_storage.retirement import run_retire_derived


def _scope(config, role="normalized"):
    manifest = run_inventory(config).manifest
    candidate = next(item for item in manifest["candidates"] if item["artifact_role"] == role)
    manifest["candidates"] = [candidate]
    return manifest, candidate


def test_manifest_cannot_add_a_raw_file_to_managed_deletions(tmp_path):
    config, store, _ = build_catalog(tmp_path)
    manifest, entry = _scope(config, "sections")
    raw = Path(store.fetchone("SELECT absolute_path FROM locations LIMIT 1")["absolute_path"])
    original = raw.read_bytes()
    entry["managed_files"].append({"path": str(raw), "byte_size": len(original)})
    report = run_retire_derived(config, manifest, dry_run=False)
    assert raw.read_bytes() == original
    assert report["status"] != "succeeded"


def test_unreferenced_index_is_not_swept_by_a_different_scope(tmp_path):
    config, _, _ = build_catalog(tmp_path)
    manifest, _ = _scope(config)
    index = config.derived_dir / "unknown/sections/index.json"
    index.parent.mkdir(parents=True)
    index.write_bytes(b"[]")
    run_retire_derived(config, manifest, dry_run=False)
    assert index.read_bytes() == b"[]"


def test_retired_metadata_resumes_an_unfinished_file_unlink(tmp_path):
    config, store, _ = build_catalog(tmp_path)
    manifest, entry = _scope(config)
    target = Path(entry["path"])
    with store.transaction() as connection:
        connection.execute("UPDATE artifacts SET status='retired' WHERE artifact_id=?", (entry["artifact_id"],))
    result = run_retire_derived(config, manifest, dry_run=False)
    assert not target.exists()
    assert result["status"] == "succeeded"
    assert len(result["deleted"]) == 1
    rerun = run_retire_derived(config, manifest, dry_run=False)
    assert rerun["deleted"] == []
    assert rerun["files_bytes_before"] == rerun["files_bytes_after"]


def test_missing_file_still_retires_its_completed_handle(tmp_path):
    config, store, _ = build_catalog(tmp_path)
    manifest, entry = _scope(config)
    Path(entry["path"]).unlink()
    result = run_retire_derived(config, manifest, dry_run=False)
    row = store.fetchone("SELECT status FROM artifacts WHERE artifact_id=?", (entry["artifact_id"],))
    assert row["status"] == "retired"
    assert result["status"] == "succeeded"
    assert result["deleted"] == []
    assert len(result["already_absent"]) == 1


def test_changed_registered_path_cannot_delete_the_old_manifest_file(tmp_path):
    config, store, _ = build_catalog(tmp_path)
    manifest, entry = _scope(config)
    target = Path(entry["path"])
    moved = target.with_name("changed.md")
    moved.write_bytes(target.read_bytes())
    with store.transaction() as connection:
        connection.execute("UPDATE artifacts SET path=? WHERE artifact_id=?", (str(moved), entry["artifact_id"]))
    report = run_retire_derived(config, manifest, dry_run=False)
    assert target.exists() and moved.exists()
    assert report["status"] != "succeeded"


def test_current_generator_cannot_be_changed_into_a_legacy_manifest_claim(tmp_path):
    config, store, _ = build_catalog(tmp_path)
    manifest, entry = _scope(config)
    target = Path(entry["path"])
    with store.transaction() as connection:
        connection.execute("UPDATE artifacts SET generator_name='new_producer' WHERE artifact_id=?", (entry["artifact_id"],))
    report = run_retire_derived(config, manifest, dry_run=False)
    assert target.exists()
    assert report["status"] != "succeeded"


def test_changed_section_bytes_are_preserved_and_reported(tmp_path):
    config, _, _ = build_catalog(tmp_path)
    manifest, entry = _scope(config, "sections")
    target = Path(entry["managed_files"][0]["path"])
    target.write_bytes(b"new version of section")
    result = run_retire_derived(config, manifest, dry_run=False)
    assert target.read_bytes() == b"new version of section"
    assert result["status"] != "succeeded"


def test_an_unlink_failure_is_not_reported_as_success_and_can_resume(tmp_path, monkeypatch):
    config, _, _ = build_catalog(tmp_path)
    manifest, entry = _scope(config)
    target = Path(entry["path"])
    unlink = Path.unlink
    def unavailable(path, *args, **kwargs):
        if path == target:
            raise PermissionError("fixture sharing violation")
        return unlink(path, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", unavailable)
        failed = run_retire_derived(config, manifest, dry_run=False)
        assert failed["status"] != "succeeded"
    assert target.exists()
    resumed = run_retire_derived(config, manifest, dry_run=False)
    assert resumed["status"] == "succeeded"
    assert not target.exists()
