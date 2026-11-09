"""Run-owned storage accounting and bounded immutable-object I/O."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
from pathlib import Path
import sqlite3
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

from company_wiki.source_catalog import narrative_artifact_store as artifacts
from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.service import SourceCatalog


def _source_catalog(tmp_path, catalog_dir):
    roots = (RootSpec("raw", tmp_path / "raw", "company_raw"),)
    return SourceCatalog(CatalogConfig(tmp_path, catalog_dir, roots))


@pytest.mark.parametrize("race", [False, True])
def test_cas_existing_object_validation_never_reads_beyond_input_bound(tmp_path, monkeypatch, race):
    data = b"{}"
    digest = hashlib.sha256(data).hexdigest()
    key = f"objects/sha256/{digest[:2]}/{digest}.json"
    objects = artifacts.LocalNarrativeObjectStore(tmp_path)
    target = tmp_path / key
    target.parent.mkdir(parents=True)
    if not race:
        target.write_bytes(b"damaged object much larger than this input")
    else:
        def conflicting_link(_source, destination):
            Path(destination).write_bytes(b"damaged concurrent object")
            raise FileExistsError("another writer won")
        monkeypatch.setattr(artifacts.os, "link", conflicting_link)
    real_open = Path.open
    reads = []

    @contextmanager
    def observed_open(path, mode="r", *args, **kwargs):
        with real_open(path, mode, *args, **kwargs) as stream:
            if path == target and mode == "rb":
                class BoundedStream:
                    def read(self, size=-1):
                        reads.append(size)
                        assert size == len(data) + 1, "unbounded disk-object verification"
                        return stream.read(size)
                yield BoundedStream()
            else:
                yield stream

    monkeypatch.setattr(Path, "open", observed_open)
    with pytest.raises(artifacts.NarrativeObjectIntegrityError):
        objects.put(data)
    assert reads == [len(data) + 1]
    assert not list(target.parent.glob("*.partial"))


def test_cas_reused_object_is_not_rewritten(tmp_path):
    objects = artifacts.LocalNarrativeObjectStore(tmp_path)
    key = objects.put(b"unchanged")
    original = (tmp_path / key).stat()
    assert objects.put(b"unchanged") == key
    after = (tmp_path / key).stat()
    assert (after.st_size, after.st_mtime_ns) == (original.st_size, original.st_mtime_ns)


def test_batch_storage_does_not_attribute_other_catalog_writers(tmp_path):
    from company_wiki.automation.narrative_batch import _storage_guard
    from company_wiki.automation.store import AutomationStore
    db = tmp_path / "auto.db"
    AutomationStore(db)
    catalog_dir = tmp_path / "catalog"
    catalog_dir.mkdir()
    work = tmp_path / "work"
    work.mkdir()
    catalog = _source_catalog(tmp_path, catalog_dir)
    request = SimpleNamespace(run_id="run-a", max_persistent_bytes=100_000,
                              max_scratch_bytes=100_000)
    guard = _storage_guard(request, catalog, db, work, "a" * 64)
    before = guard.snapshot().persistent_added_bytes
    foreign = artifacts.LocalNarrativeObjectStore(catalog_dir)
    foreign.put(b"another writer's source output")
    catalog.config.database_path.write_bytes(b"another writer's SQLite growth")
    assert guard.snapshot().persistent_added_bytes == before


def test_idle_guard_polling_does_not_rescan_storage_trees(tmp_path, monkeypatch):
    from company_wiki.automation.narrative_batch import BatchStorageBudget
    original = Path.rglob
    scans = []
    def counted(path, pattern):
        scans.append(path)
        return original(path, pattern)
    monkeypatch.setattr(Path, "rglob", counted)
    guard = BatchStorageBudget(files=(), persistent_dirs=(tmp_path,), scratch_dirs=(),
                               max_persistent_bytes=100_000, max_scratch_bytes=100_000)
    initial = len(scans)
    for _ in range(100):
        guard.check(force=False)
    assert len(scans) <= initial + 1


def _run_guard(tmp_path, *, run_id="run-a", limit=100_000):
    from company_wiki.automation.narrative_batch import BatchStorageBudget
    from company_wiki.automation.store import AutomationStore
    db = tmp_path / "auto.db"
    AutomationStore(db)
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT OR IGNORE INTO narrative_runs (run_id,input_hash,scope_sha256,"
                     "model_id,prompt_version,pricing_version,input_micro_usd_per_million_tokens,"
                     "output_micro_usd_per_million_tokens,max_tokens,max_micro_usd,max_output_bytes,"
                     "state,created_at,updated_at) VALUES (?,?,?,?,?,?,0,0,100,100,100,'open',?,?)",
                     (run_id, "a" * 64, "b" * 64, "model", "prompt", "price",
                      "2026-11-01T00:00:00Z", "2026-11-01T00:00:00Z"))
    return BatchStorageBudget(files=(), persistent_dirs=(), scratch_dirs=(),
                              max_persistent_bytes=limit, max_scratch_bytes=100_000,
                              owned_accounting=(db, run_id))


def _budgeted_objects(root, guard, max_final_bytes):
    return artifacts.LocalNarrativeObjectStore(root, write_policy=guard.object_write_policy(max_final_bytes))


def test_only_cas_writer_creation_is_charged_and_restored(tmp_path):
    guard = _run_guard(tmp_path)
    shared = tmp_path / "catalog"
    objects = _budgeted_objects(shared, guard, 100_000)
    key = objects.put(b"owned")
    assert objects.put(b"owned") == key
    assert guard.snapshot().persistent_added_bytes == 5
    artifacts.LocalNarrativeObjectStore(shared).put(b"unrelated much larger object")
    assert guard.snapshot().persistent_added_bytes == 5
    assert _run_guard(tmp_path).snapshot().persistent_added_bytes == 5
    other = _run_guard(tmp_path, run_id="run-b", limit=0)
    assert _budgeted_objects(shared, other, 100_000).put(b"owned") == key
    assert other.snapshot().persistent_added_bytes == 0


def test_owned_storage_limit_is_enforced_before_filesystem_creation(tmp_path):
    guard = _run_guard(tmp_path, limit=2)
    objects = _budgeted_objects(tmp_path / "catalog", guard, 100_000)
    with pytest.raises(ValueError, match="PERSISTENT_BYTES_EXCEEDED"):
        objects.put(b"too big")
    assert guard.snapshot().persistent_added_bytes == 0
    assert not list((tmp_path / "catalog").rglob("*.json"))


def test_existing_cas_object_needs_no_scratch_allocation(tmp_path):
    guard = _run_guard(tmp_path)
    guard.max_scratch_bytes = 2
    root = tmp_path / "catalog"
    original = artifacts.LocalNarrativeObjectStore(root).put(b"shared")
    objects = _budgeted_objects(root, guard, 1000)
    assert objects.put(b"shared") == original
    assert guard.snapshot().scratch_peak_bytes == 0
    with pytest.raises(ValueError, match="SCRATCH_BYTES_EXCEEDED"):
        objects.put(b"new")
    assert guard.snapshot().persistent_added_bytes == 0
    assert len(list((root / "objects").rglob("*.json"))) == 1


def test_crash_after_cas_write_retains_conservative_allocation(tmp_path, monkeypatch):
    from company_wiki.automation.narrative_run_store import NarrativeRunStore
    guard = _run_guard(tmp_path)
    objects = _budgeted_objects(tmp_path / "catalog", guard, 100_000)
    original = NarrativeRunStore._settle_storage_object
    def interrupted(*args, **kwargs):
        raise RuntimeError("simulated process interruption before settlement")
    monkeypatch.setattr(NarrativeRunStore, "_settle_storage_object", interrupted)
    with pytest.raises(RuntimeError, match="simulated process"):
        objects.put(b"paid body")
    monkeypatch.setattr(NarrativeRunStore, "_settle_storage_object", original)
    resumed = _run_guard(tmp_path)
    assert resumed.snapshot().persistent_added_bytes == len(b"paid body")
    _budgeted_objects(tmp_path / "catalog", resumed, 100_000).put(b"paid body")
    assert resumed.snapshot().persistent_added_bytes == len(b"paid body")


def test_concurrent_cas_winner_is_not_charged_to_loser(tmp_path, monkeypatch):
    guard = _run_guard(tmp_path)
    data = b"same body"
    def another_writer_wins(_source, destination):
        Path(destination).write_bytes(data)
        raise FileExistsError("another writer")
    monkeypatch.setattr(artifacts.os, "link", another_writer_wins)
    _budgeted_objects(tmp_path / "catalog", guard, 100_000).put(data)
    assert guard.snapshot().persistent_added_bytes == 0


def test_old_active_baseline_is_frozen_once_then_uses_owner_accounting(tmp_path):
    import json
    from company_wiki.automation.narrative_batch import _storage_guard
    _run_guard(tmp_path, limit=10_000_000)
    catalog_dir = tmp_path / "catalog"
    catalog_dir.mkdir()
    work = tmp_path / "work"
    work.mkdir()
    baseline = work / "storage-baseline.json"
    baseline.write_text(json.dumps({"input_hash": "a" * 64, "sizes": [0] * 8}), encoding="utf-8")
    original = baseline.read_bytes()
    catalog = _source_catalog(tmp_path, catalog_dir)
    request = SimpleNamespace(run_id="run-a", max_persistent_bytes=10_000_000,
                              max_scratch_bytes=100_000)
    guard = _storage_guard(request, catalog, tmp_path / "auto.db", work, "a" * 64, read_only=True)
    assert guard.owned_accounting is None
    guard.adopt_owned_accounting(tmp_path / "auto.db", "run-a", work, create_floor=True)
    before = guard.snapshot().persistent_added_bytes
    artifacts.LocalNarrativeObjectStore(catalog_dir).put(b"foreign after resume")
    catalog.config.database_path.write_bytes(b"foreign database after resume")
    assert guard.snapshot().persistent_added_bytes == before
    restored = _storage_guard(request, catalog, tmp_path / "auto.db", work, "a" * 64, read_only=True)
    assert restored.snapshot().persistent_added_bytes == before
    assert baseline.read_bytes() == original


def test_v7_upgrade_preserves_history_and_inspection_is_readonly(tmp_path):
    from company_wiki.automation import migrations
    db = tmp_path / "v7.db"
    with sqlite3.connect(db) as conn:
        for statements in (migrations._DDL_V1_STATEMENTS, migrations._DDL_V2_STATEMENTS,
                           migrations._DDL_V3_STATEMENTS, migrations._DDL_V4_STATEMENTS,
                           migrations._DDL_V5_STATEMENTS, migrations._DDL_V6_STATEMENTS,
                           migrations._DDL_V7_STATEMENTS):
            for statement in statements:
                conn.execute(statement)
        conn.execute("PRAGMA user_version=7")
    before = db.read_bytes()
    assert migrations.inspect_schema(db).user_version == 7
    assert db.read_bytes() == before
    def backup(path, _old, _new):
        target = path.with_suffix(".backup")
        target.write_bytes(path.read_bytes())
        return target
    report = migrations.migrate_database(db, backup_hook=backup)
    assert report.applied_versions == (8,)
    assert "narrative_storage_allocations" in migrations.inspect_schema(db).tables
    assert db.with_suffix(".backup").read_bytes() == before


def test_loopback_rank_reply_reads_declared_task_columns():
    from support.official_json_batch_fixture import model_draft
    reply = model_draft({"schema_version": "narrative-model-request/6", "material": {
        "task_columns": ["support", "key", "context", "reading_hint_index"],
        "tasks": [[[0], "task-a", [], 0]],
    }})
    assert reply == {"decisions": [{"task": "task-a", "priority": "normal", "disposition": "consider"}]}


def test_late_cas_loser_cannot_erase_another_writer_actual_bytes(tmp_path):
    guard = _run_guard(tmp_path, limit=100)
    ledger = guard.accounting_store()
    identity = dict(run_id="run-a", store_id="same-store", object_key="same", byte_size=60, max_bytes=100)
    first = ledger._admit_storage_object(**identity)
    second = ledger._admit_storage_object(**identity)
    settlement = {key: identity[key] for key in ("run_id", "store_id", "object_key")}
    ledger._settle_storage_object(**settlement, created_bytes=60, new_allocation=second)
    assert ledger.storage_bytes("run-a") == 60
    ledger._settle_storage_object(**settlement, created_bytes=0, new_allocation=first)
    assert ledger.storage_bytes("run-a") == 60


def test_cas_admission_does_not_mix_two_owner_usage_snapshots(tmp_path, monkeypatch):
    guard = _run_guard(tmp_path, limit=100)
    original = guard.snapshot
    count = 0
    objects = _budgeted_objects(tmp_path / "catalog", guard, 1000)
    def interleaved_snapshot(*args, **kwargs):
        nonlocal count
        count += 1
        observed = original(*args, **kwargs)
        if count == 1:
            monkeypatch.setattr(guard, "snapshot", original)
            objects.put(b"B" * 60)
            monkeypatch.setattr(guard, "snapshot", interleaved_snapshot)
        return observed
    monkeypatch.setattr(guard, "snapshot", interleaved_snapshot)
    with pytest.raises(ValueError, match="PERSISTENT_BYTES_EXCEEDED"):
        objects.put(b"A" * 60)
    assert count == 1
    assert guard.snapshot().persistent_added_bytes == 60
    assert sum(file.stat().st_size for file in (tmp_path / "catalog/objects").rglob("*.json")) == 60


def test_same_object_has_one_short_writer_scope_and_holds_pending_capacity(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event, current_thread
    guard = _run_guard(tmp_path, limit=100)
    first_inside, release_first, second_started, second_inside = (Event() for _ in range(4))
    original = artifacts.LocalNarrativeObjectStore.put_with_usage
    def observed(self, data, **kwargs):
        if data == b"X" * 60 and current_thread().name.startswith("second"):
            second_inside.set()
        return original(self, data, **kwargs)
    real_link = artifacts.os.link
    def held_link(source, destination):
        if not first_inside.is_set():
            first_inside.set()
            assert release_first.wait(5)
        return real_link(source, destination)
    monkeypatch.setattr(artifacts.LocalNarrativeObjectStore, "put_with_usage", observed)
    monkeypatch.setattr(artifacts.os, "link", held_link)
    def second_write():
        second_started.set()
        return _budgeted_objects(tmp_path / "catalog", guard, 1000).put(b"X" * 60)
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="first") as first_pool, \
            ThreadPoolExecutor(max_workers=1, thread_name_prefix="second") as second_pool:
        first = first_pool.submit(_budgeted_objects(tmp_path / "catalog", guard, 1000).put, b"X" * 60)
        try:
            assert first_inside.wait(5)
            second = second_pool.submit(second_write)
            assert second_started.wait(5)
            assert not second_inside.wait(0.15), "two puts entered the same durable owner scope"
            assert guard.accounting_store().storage_bytes("run-a") == 60
        finally:
            release_first.set()
        assert first.result(timeout=5) == second.result(timeout=5)
    assert guard.accounting_store().storage_bytes("run-a") == 60
    with pytest.raises(ValueError, match="PERSISTENT_BYTES_EXCEEDED"):
        _budgeted_objects(tmp_path / "catalog", guard, 1000).put(b"Y" * 60)


def test_killed_writer_releases_os_mutex_without_refunding_pending_space(tmp_path):
    guard = _run_guard(tmp_path, limit=100)
    body = b"X" * 60
    digest = hashlib.sha256(body).hexdigest()
    key = f"objects/sha256/{digest[:2]}/{digest}.json"
    script = """
import os,sys
from pathlib import Path
from company_wiki.automation.narrative_run_store import NarrativeRunStore
ledger=NarrativeRunStore(Path(sys.argv[1]))
def write(admit):
    admit(sys.argv[3],60)
    os._exit(23)
ledger.account_storage_write(run_id='run-a',store_id=sys.argv[2],max_bytes=100,write=write)
"""
    objects_root = tmp_path / "catalog"
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")}
    process = subprocess.run([sys.executable, "-B", "-c", script,
                              str(tmp_path / "auto.db"), str(objects_root.resolve()), key],
                             env=env, capture_output=True, timeout=10)
    assert process.returncode == 23, process.stderr.decode(errors="replace")
    assert guard.accounting_store().storage_bytes("run-a") == 60
    _budgeted_objects(objects_root, guard, 1000).put(body)
    assert guard.accounting_store().storage_bytes("run-a") == 60
    assert len(list((objects_root / "objects").rglob("*.json"))) == 1


def test_control_locator_uses_local_only_snapshot_for_atomic_admission(tmp_path, monkeypatch):
    from company_wiki.automation.narrative_batch import _write_generation_owner
    db = tmp_path / "auto.db"
    control = tmp_path / "control"
    control.mkdir()
    pointer = control / "generation.json"
    _write_generation_owner(pointer, db, "run-a")
    size = pointer.stat().st_size
    pointer.unlink()
    guard = _run_guard(tmp_path, limit=size + 30)
    original = guard.snapshot
    first = True
    def interleaved(*args, **kwargs):
        nonlocal first
        observed = original(*args, **kwargs)
        if first:
            first = False
            monkeypatch.setattr(guard, "snapshot", original)
            _budgeted_objects(tmp_path / "catalog", guard, 1000).put(b"B" * 60)
            monkeypatch.setattr(guard, "snapshot", interleaved)
        return observed
    monkeypatch.setattr(guard, "snapshot", interleaved)
    with pytest.raises(ValueError, match="PERSISTENT_BYTES_EXCEEDED"):
        _write_generation_owner(pointer, db, "run-a", storage_guard=guard)
    assert not pointer.exists()
    assert guard.accounting_store().storage_bytes("run-a") == 60
