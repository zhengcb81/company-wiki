"""Narrative history composes read and write capabilities from their owners."""

from contextlib import nullcontext
import json
from types import SimpleNamespace

import pytest

from company_wiki.automation import models, narrative_batch as batch
from company_wiki.automation.store import AutomationStore
from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.narrative_artifact_store import NarrativeArtifactNotVisibleError
from company_wiki.source_catalog.reader import CatalogReaderUnavailable
from company_wiki.source_catalog.service import SourceCatalog
from unit.test_automation_store import T0, _make_effect, _make_event, _make_job
from unit.test_narrative_artifact_store import _catalog, _draft


def _source_catalog(tmp_path):
    roots = (RootSpec("local", tmp_path / "sources", "company_raw"),)
    return SourceCatalog(CatalogConfig(tmp_path, tmp_path / "catalog", roots))


def test_catalog_artifact_reader_does_not_initialize_missing_store(tmp_path, monkeypatch):
    catalog = _source_catalog(tmp_path)

    def forbidden_writer(_catalog):
        pytest.fail("a read-only artifact request initialized the catalog writer")

    monkeypatch.setattr(SourceCatalog, "store", property(forbidden_writer))
    with pytest.raises(CatalogReaderUnavailable):
        catalog.open_narrative_artifact_reader()
    assert not any(tmp_path.iterdir())


def test_catalog_owns_lock_footprint_and_legacy_control_locator(tmp_path, monkeypatch):
    catalog = _source_catalog(tmp_path)
    assert catalog.narrative_database_sizes() == (0, 0, 0)
    assert catalog.narrative_object_bytes() == 0
    assert catalog.legacy_narrative_generation_directory() == tmp_path / "catalog/narrative-generations"
    assert catalog.storage_is_within(tmp_path)
    assert not catalog.storage_is_within(tmp_path / "work")
    assert not any(tmp_path.iterdir())

    database = catalog.config.database_path
    database.parent.mkdir()
    for suffix, size in zip(("", "-wal", "-shm"), (11, 12, 13)):
        database.with_name(database.name + suffix).write_bytes(b"x" * size)
    objects = catalog.config.catalog_dir / "objects/sha256/aa"
    objects.mkdir(parents=True)
    (objects / "bundle.json").write_bytes(b"object")
    assert catalog.narrative_database_sizes() == (11, 12, 13)
    assert catalog.narrative_object_bytes() == len(b"object")

    locked = []

    def operation_lock(root, *, operation):
        locked.append((root, operation))
        return nullcontext()

    monkeypatch.setattr("company_wiki.source_catalog.service.CatalogOperationLock", operation_lock)
    with catalog.operation_lock(operation="batch-state-test"):
        assert locked == [(catalog.config.catalog_dir, "batch-state-test")]


@pytest.mark.parametrize("tracks_control", [False, True])
def test_legacy_budget_measures_through_owners_and_keeps_original_baseline(tmp_path, tracks_control):
    work = tmp_path / "work"
    work.mkdir()
    control = tmp_path / "historical-control"
    control.mkdir()
    (control / "pending.json").write_bytes(b"control")
    catalog = SimpleNamespace(
        narrative_database_sizes=lambda: (5, 6, 7), narrative_object_bytes=lambda: 14,
        legacy_narrative_generation_directory=lambda: control,
    )
    request = SimpleNamespace(run_id="run", max_persistent_bytes=100_000, max_scratch_bytes=100_000)
    sizes = [0, 0, 0, 1, 2, 3, 8, 0] + ([2] if tracks_control else [])
    frozen = json.dumps({"input_hash": "a" * 64, "sizes": sizes}).encode("utf-8")
    baseline = work / "storage-baseline.json"
    baseline.write_bytes(frozen)
    guard = batch._storage_guard(request, catalog, tmp_path / "absent-auto.db", work,
                                 "a" * 64, read_only=True)

    assert guard.baseline == tuple(sizes)
    assert guard.snapshot().persistent_added_bytes == 12 + 6 + len(frozen) + (5 if tracks_control else 0)
    assert baseline.read_bytes() == frozen
    pointer = batch._generation_pointer(catalog, {"generation": "frozen"})
    assert pointer.parent == control and pointer.suffix == ".json"
    assert tuple(control.iterdir()) == (control / "pending.json",)


def test_catalog_artifact_factory_applies_policy_and_opens_read_only_facade(tmp_path):
    catalog = _source_catalog(tmp_path)
    catalog.config.catalog_dir.mkdir()
    _catalog(catalog.config.catalog_dir)
    payload = b'{"summary":"business context"}'
    admissions = []

    def deny(store_id, size, write):
        assert store_id == str(catalog.config.catalog_dir.resolve())
        assert size == len(payload)

        def before_create(key, byte_count):
            admissions.append((key, byte_count))
            raise ValueError("PERSISTENT_BYTES_EXCEEDED")

        return write(before_create).object_key

    draft = _draft()
    with pytest.raises(ValueError, match="PERSISTENT_BYTES_EXCEEDED"):
        catalog.open_narrative_artifact_store(write_policy=deny).prepare(draft, payload)
    assert not list(catalog.config.catalog_dir.rglob("*.json"))

    def allow(store_id, size, write):
        result = write(lambda key, byte_count: admissions.append((key, byte_count)))
        assert result.created_bytes == size == len(payload)
        return result.object_key

    writer = catalog.open_narrative_artifact_store(write_policy=allow)
    prepared = writer.prepare(draft, payload)
    assert admissions == [(prepared.object_key, len(payload))] * 2
    visible = writer.activate(draft.effect_id, verified_after_hash=prepared.content_sha256, activated_at=T0)
    artifacts = catalog.open_narrative_artifact_reader()
    try:
        assert artifacts.visible_version_for_effect(draft.effect_id) == visible
        assert not hasattr(artifacts, "prepare")
    finally:
        artifacts.close()


def test_paid_response_object_port_exposes_no_path_or_unbudgeted_writer(tmp_path):
    catalog = _source_catalog(tmp_path)
    admissions = []

    def account(store_id, size, write):
        result = write(lambda _key, count: admissions.append(count))
        assert store_id == str(catalog.config.catalog_dir.resolve())
        assert size == result.created_bytes == 4
        return result.object_key

    objects = catalog.open_narrative_object_access(write_policy=account)
    assert not hasattr(objects, "root")
    assert not hasattr(objects, "put_with_usage")
    assert not any(tmp_path.iterdir())
    key = objects.put(b"paid")
    assert key.startswith("objects/sha256/")
    assert admissions == [4]
    assert not catalog.config.database_path.exists()


def test_auto_effect_delivery_query_is_scoped_and_never_opens_writer(tmp_path, monkeypatch):
    store = AutomationStore(tmp_path / "auto.db")
    store.put_event(_make_event())
    job = store.put_job(_make_job()).value
    foreign = store.put_job(_make_job(job_id="foreign-job", subject_id="foreign-source")).value
    delivered = store.put_effect(_make_effect(job_id=job.job_id)).value
    undelivered = store.put_effect(_make_effect(
        job_id=job.job_id, effect_id="undelivered", target="undelivered",
        effect_key=models.make_effect_key("artifact_write", "undelivered", job.input_hash, "1.0.0"),
    )).value
    store.put_effect(_make_effect(
        job_id=foreign.job_id, effect_id="foreign-effect", target="foreign",
        effect_key=models.make_effect_key("artifact_write", "foreign", job.input_hash, "1.0.0"),
    ))
    store.put_outbox_entry("delivery-id-is-opaque", delivered.effect_id, "{}", "delivered", T0)
    before = store.db_path.read_bytes()

    def forbidden_writer():
        pytest.fail("history query opened the writable AUTO connection")

    monkeypatch.setattr(store, "_connect", forbidden_writer)
    # Scope follows the request, including batches above the old 900-ID shortcut.
    scope = (job.job_id, job.job_id, *(f"unrelated-{i}" for i in range(1000)))
    deliveries = store.effect_deliveries_for_jobs(scope)
    assert {(row.effect_id, row.job_id, row.effect_type, row.effect_status, row.outbox_status)
            for row in deliveries} == {
        (delivered.effect_id, job.job_id, delivered.effect_type, delivered.status.value, "delivered"),
        (undelivered.effect_id, job.job_id, undelivered.effect_type, undelivered.status.value, None),
    }
    assert store.effect_deliveries_for_jobs(()) == ()
    assert store.db_path.read_bytes() == before


@pytest.mark.parametrize("outbox_status,visible,expected", [
    ("pending", True, False), ("delivered", False, False), ("delivered", True, True),
])
def test_completed_history_needs_no_paths_connections_or_tables(outbox_status, visible, expected):
    job = SimpleNamespace(job_id="job", job_type="source.narrative_verify", status=models.JobStatus.SUCCEEDED)
    delivery = SimpleNamespace(effect_id="effect", job_id=job.job_id, effect_type=batch.EFFECT_TYPE,
                               effect_status="verified", outbox_status=outbox_status)
    calls = []

    def deliveries(scope):
        calls.append(("effects", scope))
        return (delivery,)

    def visible_version(effect_id):
        calls.append(("visible", effect_id))
        if not visible:
            raise NarrativeArtifactNotVisibleError("still pending activation")

    def open_artifacts():
        calls.append("open")
        return SimpleNamespace(visible_version_for_effect=visible_version, close=lambda: calls.append("close"))

    store = SimpleNamespace(effect_deliveries_for_jobs=deliveries)
    assert batch._completed_read_history(open_artifacts, store, (job,)) is expected
    assert calls == [("effects", (job.job_id,))] + (
        ["open", ("visible", delivery.effect_id), "close"] if outbox_status == "delivered" else []
    )
