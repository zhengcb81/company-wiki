"""Physical deletion closes every legacy handle, never an unrelated reader."""
from pathlib import Path

import pytest

from support.p5_storage_catalog_fixture import build_catalog
from legacy_storage.inventory import run_inventory
from legacy_storage.retirement import run_retire_derived
import legacy_storage.retirement as retirement


def _scope(config, role="normalized"):
    manifest = run_inventory(config).manifest
    entry = next(c for c in manifest["candidates"] if c["artifact_role"] == role)
    manifest["candidates"] = [entry]
    return manifest, entry


def _alias(store, entry, **changes):
    row = dict(store.fetchone("SELECT * FROM artifacts WHERE artifact_id=?", (entry["artifact_id"],)))
    row.update(artifact_id="shared-alias", generator_name="plain_text", generator_version="1.0.0")
    row.update(changes)
    with store.transaction() as connection:
        connection.execute(
            f"INSERT INTO artifacts ({','.join(row)}) VALUES ({','.join('?' for _ in row)})",
            tuple(row.values()),
        )
    return row


@pytest.mark.parametrize("stale", [False, True])
def test_old_manifest_retires_all_same_document_legacy_handles(tmp_path, stale):
    config, store, _ = build_catalog(tmp_path)
    manifest, entry = _scope(config)
    alias = _alias(store, entry, content_sha256="a" * 64 if stale else entry["content_sha256"])
    before = Path(entry["path"]).stat().st_size
    report = run_retire_derived(config, manifest, dry_run=False)
    assert report["status"] == "succeeded"
    rows = store.fetchall("SELECT status,content_sha256 FROM artifacts WHERE path=?", (entry["path"],))
    assert {r["status"] for r in rows} == {"retired"}
    assert alias["content_sha256"] in {r["content_sha256"] for r in rows}
    assert not Path(entry["path"]).exists()
    assert sum(d["byte_size"] for d in report["deleted"]) == before
    assert report["source_facts_before"] == report["source_facts_after"]
    assert report["protected_objects_before"] == report["protected_objects_after"]
    assert run_retire_derived(config, manifest, dry_run=False)["status"] == "succeeded"


@pytest.mark.parametrize("changes", [
    {"generator_name": "future_model"},
    {"generator_version": "99.0.0"},
    {"artifact_role": "future_final"},
    {"status": "prepared"},
])
def test_shared_unknown_or_active_handle_blocks_entire_object(tmp_path, changes):
    config, store, _ = build_catalog(tmp_path)
    manifest, entry = _scope(config)
    _alias(store, entry, **changes)
    report = run_retire_derived(config, manifest, dry_run=False)
    assert report["status"] != "succeeded"
    assert Path(entry["path"]).exists()
    assert store.fetchone("SELECT status FROM artifacts WHERE artifact_id=?", (entry["artifact_id"],))["status"] == "completed"


def test_cross_document_alias_blocks_object(tmp_path):
    config, store, facts = build_catalog(tmp_path)
    manifest, entry = _scope(config)
    other = next(f for f in facts.values() if f["document_id"] != entry["document_id"])
    _alias(store, entry, document_id=other["document_id"], source_id=other["source_id"])
    assert run_retire_derived(config, manifest, dry_run=False)["status"] != "succeeded"
    assert Path(entry["path"]).exists()


def test_cross_source_alias_blocks_object(tmp_path):
    config, store, facts = build_catalog(tmp_path)
    manifest, entry = _scope(config)
    other = next(f for f in facts.values() if f["source_id"] != store.fetchone("SELECT source_id FROM artifacts WHERE artifact_id=?", (entry["artifact_id"],))["source_id"])
    _alias(store, entry, source_id=other["source_id"])
    assert run_retire_derived(config, manifest, dry_run=False)["status"] != "succeeded"
    assert Path(entry["path"]).exists()


def test_alias_inserted_after_snapshot_is_detected_before_any_retirement(tmp_path, monkeypatch):
    config, store, _ = build_catalog(tmp_path)
    manifest, entry = _scope(config)
    original = retirement._live_rows

    def racing_snapshot(database):
        result = original(database)
        _alias(store, entry, generator_name="new_final")
        return result

    monkeypatch.setattr(retirement, "_live_rows", racing_snapshot)
    report = run_retire_derived(config, manifest, dry_run=False)
    assert report["status"] != "succeeded"
    assert Path(entry["path"]).exists()
    assert store.fetchone("SELECT status FROM artifacts WHERE artifact_id=?", (entry["artifact_id"],))["status"] == "completed"


def test_unlink_retry_closes_aliases_and_preserves_other_files(tmp_path, monkeypatch):
    config, store, _ = build_catalog(tmp_path)
    manifest, entry = _scope(config)
    _alias(store, entry, content_sha256="a" * 64)
    target = Path(entry["path"])
    original = Path.unlink

    def fail_target(path, *args, **kwargs):
        if path == target:
            assert {r["status"] for r in store.fetchall("SELECT status FROM artifacts WHERE path=?", (str(target),))} == {"retired"}
            raise PermissionError(13, "injected unlink failure")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_target)
    assert run_retire_derived(config, manifest, dry_run=False)["status"] == "failed"
    assert target.exists()
    monkeypatch.setattr(Path, "unlink", original)
    assert run_retire_derived(config, manifest, dry_run=False)["status"] == "succeeded"
    assert not target.exists()


def test_inventory_counts_shared_file_only_once(tmp_path):
    config, store, _ = build_catalog(tmp_path)
    _, entry = _scope(config)
    _alias(store, entry, generator_name="source_catalog_normalizer", generator_version="historic")
    manifest = run_inventory(config).manifest
    files = {}
    for c in manifest["candidates"]:
        for item in [c, *c.get("managed_files", [])]:
            files[Path(item["path"]).resolve()] = item["byte_size"]
    assert manifest["aggregate"]["candidate_bytes"] == sum(files.values())


def test_blank_generator_summary_is_only_legacy_at_canonical_sha_path(tmp_path):
    config, store, _ = build_catalog(tmp_path)
    _, entry = _scope(config, "summary")
    with store.transaction() as connection:
        connection.execute("UPDATE artifacts SET generator_name='',generator_version='' WHERE artifact_id=?", (entry["artifact_id"],))
    manifest = run_inventory(config).manifest
    assert entry["artifact_id"] in {c["artifact_id"] for c in manifest["candidates"]}
    target = Path(entry["path"])
    unexpected = target.with_name("unknown.md")
    unexpected.write_bytes(target.read_bytes())
    with store.transaction() as connection:
        connection.execute("UPDATE artifacts SET path=? WHERE artifact_id=?", (str(unexpected), entry["artifact_id"]))
    assert entry["artifact_id"] not in {c["artifact_id"] for c in run_inventory(config).manifest["candidates"]}


def test_direct_parser_candidate_and_blank_summary_can_be_retired(tmp_path):
    config, store, _ = build_catalog(tmp_path)
    manifest = run_inventory(config).manifest
    chosen = [next(c for c in manifest["candidates"] if c["artifact_role"] == role) for role in ("normalized", "summary")]
    with store.transaction() as connection:
        connection.execute("UPDATE artifacts SET generator_name='plain_text',generator_version='1.0.0' WHERE artifact_id=?", (chosen[0]["artifact_id"],))
        connection.execute("UPDATE artifacts SET generator_name='',generator_version='' WHERE artifact_id=?", (chosen[1]["artifact_id"],))
    new_manifest = run_inventory(config).manifest
    new_manifest["candidates"] = [c for c in new_manifest["candidates"] if c["artifact_id"] in {entry["artifact_id"] for entry in chosen}]
    assert len(new_manifest["candidates"]) == 2
    assert run_retire_derived(config, new_manifest, dry_run=False)["status"] == "succeeded"
    assert all(not Path(entry["path"]).exists() for entry in chosen)


def test_modern_handle_on_section_child_keeps_entire_index_scope(tmp_path):
    config, store, _ = build_catalog(tmp_path)
    manifest, index = _scope(config, "sections")
    child = index["managed_files"][0]
    _alias(store, index, path=child["path"], artifact_role="markdown", generator_name="modern_final")
    report = run_retire_derived(config, manifest, dry_run=False)
    assert report["status"] != "succeeded"
    assert all(Path(item["path"]).exists() for item in [index, *index["managed_files"]])
    assert store.fetchone("SELECT status FROM artifacts WHERE artifact_id=?", (index["artifact_id"],))["status"] == "completed"


def test_selected_child_cannot_strand_unselected_sections_index(tmp_path):
    config, store, _ = build_catalog(tmp_path)
    manifest, index = _scope(config, "sections")
    child = index["managed_files"][0]
    row = _alias(store, index, path=child["path"], artifact_role="markdown", generator_name="source_catalog_normalizer", content_sha256=child["content_sha256"], byte_size=child["byte_size"])
    manifest["candidates"] = [row]
    assert run_retire_derived(config, manifest, dry_run=False)["status"] != "succeeded"
    assert all(Path(item["path"]).exists() for item in [index, *index["managed_files"]])


def test_selected_section_member_counts_once_and_unsafe_index_blocks_both(tmp_path):
    config, store, _ = build_catalog(tmp_path)
    _, index = _scope(config, "sections")
    child = index["managed_files"][0]
    row = _alias(store, index, path=child["path"], artifact_role="markdown", generator_name="source_catalog_normalizer", content_sha256=child["content_sha256"], byte_size=child["byte_size"])
    inventory = run_inventory(config).manifest
    physical = {Path(item["path"]).resolve(): item["byte_size"] for c in inventory["candidates"] for item in [c, *c.get("managed_files", [])]}
    assert inventory["aggregate"]["candidate_bytes"] == sum(physical.values())
    inventory["candidates"] = [c for c in inventory["candidates"] if c["artifact_id"] in {index["artifact_id"], row["artifact_id"]}]
    _alias(store, index, artifact_id="unsafe-index", generator_name="modern_final")
    report = run_retire_derived(config, inventory, dry_run=False)
    assert report["status"] != "succeeded"
    assert all(Path(item["path"]).exists() for item in [index, *index["managed_files"]])
