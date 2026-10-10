"""Keep unknown historical effort immutable, without executing an old batch."""

from __future__ import annotations

from contextlib import closing
from copy import deepcopy
from dataclasses import asdict
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

import pytest

from company_wiki.automation import narrative_batch as batch
from company_wiki.automation.models import canonical_json
from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
from company_wiki.automation.narrative_generation import generation_sha256, find_reuse_pin
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from company_wiki.automation.store import AutomationStore
from company_wiki.source_catalog.narrative_artifact_store import (
    LocalNarrativeObjectStore, NarrativeArtifactReader,
)
from support.narrative_batch_fixtures import (
    KEY_ENV, isolated_batch_directory, prepare_source_catalog,
    loopback_model_server as _loopback_model_server,
)

REPO = Path(__file__).resolve().parents[2]
loopback_model_server = _loopback_model_server


def _request(state, endpoint, schema):
    ref = next(iter(state.indexed.values()))[0]
    wire = {
        "schema_version": "narrative-batch-request/" + schema,
        "run_id": "legacy-effort-" + schema,
        "profile": "P2", "max_seconds": 30, "max_tokens": 200000,
        "max_cost_usd": "2",
        "model": {
            "model_id": "stub-model", "endpoint": endpoint, "api_key_env": KEY_ENV,
            "max_output_tokens": 400, "timeout_seconds": 5,
            "allow_local_http": True, "reasoning_effort": "low",
        },
        "pricing": {
            "version": "fixture-price/1",
            "input_micro_usd_per_million_tokens": 1000000,
            "output_micro_usd_per_million_tokens": 2000000,
        },
    }
    if schema == "1":
        wire["sources"] = [asdict(ref)]
    else:
        wire["items"] = [{"kind": "raw", "source_ref": asdict(ref)}]
    return NarrativeBatchRequest.from_dict(wire), wire


def _database_dump(path):
    with closing(sqlite3.connect("file:" + path.as_posix() + "?mode=ro", uri=True)) as conn:
        return tuple(conn.iterdump())


def _resume(state, request):
    store = AutomationStore(state.root / "automation.db")
    runs = NarrativeRunStore(store.db_path)
    run = runs.get_run(request.run_id)
    return batch._resume_binding(
        request, state.reader, store, runs, run, deadline=time.monotonic() + 10,
        prepared_sources=batch._current_sources(request, state.reader),
    )


def _invoke(state, request, wire):
    path = state.root / "request.json"
    path.write_text(canonical_json(wire), encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=str(REPO / "src"),
               PYTHONDONTWRITEBYTECODE="1", COMPANY_WIKI_DISABLE_DOTENV="1")
    process = subprocess.run([
        sys.executable, "-X", "utf8", "-B", "-m",
        "company_wiki.automation.narrative_batch_cli",
        "--project-root", str(state.root), "--catalog-config", str(state.config_path),
        "--automation-db", str(state.root / "automation.db"),
        "--work-dir", str(state.root / "work"), "--request", str(path),
    ], env=env, cwd=state.root, capture_output=True, text=True, encoding="utf-8", timeout=45)
    return process, json.loads(process.stdout)


@pytest.mark.parametrize("schema", ["1", "2"])
def test_completed_real_legacy_binding_reads_without_resigning_or_model(
    tmp_path_factory, loopback_model_server, monkeypatch, schema,
):
    with isolated_batch_directory(tmp_path_factory) as root:
        state = prepare_source_catalog(root, one_source=True, include_policy=False)
        try:
            request, wire = _request(state, loopback_model_server.endpoint, schema)
            original_generation = batch.generation_manifest

            def previous_generation(*args, **kwargs):
                manifest = original_generation(*args, **kwargs)
                manifest["model"].pop("reasoning_effort", None)
                return manifest

            # Reproduce the previous producer's actual omission. All other
            # source/worker/publish/run paths are real and model HTTP is loopback.
            with monkeypatch.context() as patch:
                patch.setattr(batch, "generation_manifest", previous_generation)
                first = batch.run_batch(
                    request, project_root=root, catalog_config_path=state.config_path,
                    db_path=root / "automation.db", work_dir=root / "work",
                )
            assert first["status"] == "completed", first
            assert len(loopback_model_server.requests) == 1
            assert json.loads(loopback_model_server.requests[0][1])["reasoning_effort"] == "low"
            before_auto = _database_dump(root / "automation.db")
            before_catalog = _database_dump(state.catalog.config.database_path)
            original_bytes = {path: path.read_bytes() for path in state.raw_paths.values()}
            runs = NarrativeRunStore(root / "automation.db")
            frozen_run = runs.get_run(request.run_id)
            saved = json.loads(frozen_run.binding_json)
            historical = batch._thaw_generations(saved)
            key, manifest = next(iter(historical.items()))
            assert "reasoning_effort" not in manifest["model"]
            binding, _versions, jobs = _resume(state, request)
            assert binding.generation_manifests == historical
            assert all(job.status in batch._TERMINAL for job in jobs)
            assert runs.get_run(request.run_id).binding_json == frozen_run.binding_json

            process, resumed = _invoke(state, request, wire)
            assert process.returncode == 0 and resumed["status"] == "completed", resumed
            container = "documents" if schema == "1" else "items"
            assert resumed[container] == first[container]
            assert resumed["budget"] == first["budget"]
            assert len(loopback_model_server.requests) == 1
            assert _database_dump(root / "automation.db") == before_auto
            assert _database_dump(state.catalog.config.database_path) == before_catalog
            assert {path: path.read_bytes() for path in original_bytes} == original_bytes

            # Unknown old effort is not a cache hit for either explicit effort.
            payload = batch._current_sources(request, state.reader)[0][0]
            artifacts = NarrativeArtifactReader(
                state.catalog.config.database_path,
                LocalNarrativeObjectStore(state.catalog.config.catalog_dir),
            )
            try:
                new_manifests = []
                for effort in ("low", "max"):
                    changed = deepcopy(wire)
                    changed["model"]["reasoning_effort"] = effort
                    new_request = NarrativeBatchRequest.from_dict(changed)
                    current = batch.generation_manifest(
                        new_request, payload, execution_versions=batch._execution_versions(new_request),
                    )
                    new_manifests.append(current)
                    facts = batch._current_sources(new_request, state.reader)[1][0]
                    assert find_reuse_pin(artifacts, state.reader, payload, current, facts) is None
                assert len({generation_sha256(manifest), *(generation_sha256(m) for m in new_manifests)}) == 3
            finally:
                artifacts.close()

            # All-terminal does not imply read-only: an undelivered publication,
            # absent visibility, or an unfinished model task must remain refused.
            store = AutomationStore(root / "automation.db")
            summarize = next(job for job in jobs if job.job_type == "source.narrative_summarize")
            verify = next(job for job in jobs if job.job_type == "source.narrative_verify")
            mutations = [
                ("jobs", "status", "ready", "job_id", summarize.job_id, summarize.status.value),
                ("outbox", "status", "pending", "effect_id", store.list_effects(verify.job_id)[0].effect_id, "delivered"),
            ]
            for table, column, value, id_column, ident, old_value in mutations:
                with closing(sqlite3.connect(root / "automation.db")) as conn, conn:
                    conn.execute(f"UPDATE {table} SET {column}=? WHERE {id_column}=?", (value, ident))
                try:
                    with pytest.raises(batch.BatchResumeError, match="BATCH_FROZEN_BINDING_INVALID"):
                        _resume(state, request)
                finally:
                    with closing(sqlite3.connect(root / "automation.db")) as conn, conn:
                        conn.execute(f"UPDATE {table} SET {column}=? WHERE {id_column}=?", (old_value, ident))
            with state.catalog.store.transaction() as conn:
                conn.execute("UPDATE narrative_artifact_versions SET status='prepared'")
            try:
                with pytest.raises(batch.BatchResumeError, match="BATCH_FROZEN_BINDING_INVALID"):
                    _resume(state, request)
            finally:
                with state.catalog.store.transaction() as conn:
                    conn.execute("UPDATE narrative_artifact_versions SET status='visible'")
            assert len(loopback_model_server.requests) == 1
            assert loopback_model_server.errors == []
        finally:
            state.catalog.close()


def test_history_comparator_is_narrow_and_does_not_mutate():
    frozen = {"schema_version": "narrative-generation/1", "model": {"model_id": "m"}, "other": [1]}
    expected = deepcopy(frozen)
    expected["model"]["reasoning_effort"] = "low"
    before = deepcopy((expected, frozen))
    compare = batch._completed_history_generation_matches
    assert compare(expected, frozen, completed_history=True)
    assert not compare(expected, frozen, completed_history=False)
    assert (expected, frozen) == before
    changed = deepcopy(expected)
    changed["model"]["model_id"] = "other"
    assert not compare(changed, frozen, completed_history=True)
    changed = deepcopy(expected)
    changed["other"] = [2]
    assert not compare(changed, frozen, completed_history=True)
    projected = deepcopy(frozen)
    projected["schema_version"] = "narrative-generation/2"
    projected_expected = deepcopy(expected)
    projected_expected["schema_version"] = "narrative-generation/2"
    assert not compare(projected_expected, projected, completed_history=True)
