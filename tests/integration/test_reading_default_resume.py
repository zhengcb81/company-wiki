"""A supported default upgrade cannot repeat already paid frozen model work."""

from __future__ import annotations

from contextlib import closing
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

from company_wiki.automation import narrative_batch as batch
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from integration.test_narrative_generation_reuse import (
    exact_ref,
    invoke,
    loopback_model_server as _loopback_fixture,
    official,
    public_read,
    record_proof,
    request_path,
    setup_source,
)


loopback_model_server = _loopback_fixture


def _fingerprint(path):
    stat = path.stat()
    return hashlib.sha256(path.read_bytes()).hexdigest(), stat.st_size, stat.st_mtime_ns


def _dump(path):
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as connection:
        return tuple(connection.iterdump())


@pytest.fixture
def protected_config():
    repo = Path(__file__).resolve().parents[2]
    protected = {
        path: _fingerprint(path)
        for path in (repo / "config.yaml", repo / "config/source_catalog.yaml")
    }
    yield
    assert all(_fingerprint(path) == saved for path, saved in protected.items())


def _launcher(root, name, *, hold=False, default="0.9.0", prompt=None):
    path = root / (name + ".py")
    lines = [
        "import sys",
        "from company_wiki.automation import narrative_batch_request as request",
        "from company_wiki.source_catalog.narrative_artifact_store import NarrativeArtifactStore",
        "from company_wiki.source_catalog.lock import CatalogOperationLockedError",
        "from narrative_batch_configured import main",
        "def hold(*args, **kwargs):",
        "    print('fixture_activation_held=1', file=sys.stderr)",
        "    raise CatalogOperationLockedError('fixture interrupted publication')",
        "if __name__ == '__main__':",
        f"    request.NARRATIVE_SELECTOR_VERSION = {default!r}",
    ]
    if prompt is not None:
        lines.append(f"    request.NARRATIVE_PROMPT_VERSION = {prompt!r}")
    if hold:
        lines.append("    NarrativeArtifactStore.activate = hold")
    lines.append("    raise SystemExit(main())")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.mark.parametrize("schema", ["narrative-batch-request/1", "narrative-batch-request/2"])
def test_paid_outbox_resumes_frozen_selector_across_default_upgrade_without_new_post(
    loopback_model_server, monkeypatch, protected_config, schema,
):
    monkeypatch.setenv("DEEPSEEK_API_KEY", official.batch_fixtures.KEY)
    with setup_source(loopback_model_server.endpoint) as (
        root, catalog, config, llm, imported, kind,
    ):
        sentinel = root / "preexisting.txt"
        sentinel.write_bytes(b"keep this preexisting test document")
        preserved = {
            path: _fingerprint(path)
            for path in (config, llm, sentinel, *(root / "companies").rglob("*"))
            if path.is_file()
        }
        try:
            result_field = "items" if schema.endswith("/2") else "documents"
            path = request_path(root, imported, loopback_model_server.endpoint, "default-old")
            intent = json.loads(path.read_text(encoding="utf-8"))
            assert "selector_version" not in intent
            if schema == "narrative-batch-request/2":
                intent["schema_version"] = schema
                intent["items"] = [
                    {"kind": "raw", "source_ref": ref} for ref in intent.pop("sources")
                ]
                path.write_text(json.dumps(intent), encoding="utf-8")
            hold = _launcher(root, "hold-old", hold=True, default="0.8.0")
            process, prepared = invoke(root, config, path, llm, "default-old", launcher=hold)
            assert process.returncode == 2 and prepared["status"] == "partial", prepared
            assert prepared[result_field][0]["status"] == "activation_pending"
            assert len(loopback_model_server.requests) == 1
            assert prepared["budget"]["tokens"] == 92
            runs = NarrativeRunStore(root / "AUTO.sqlite")
            saved_run = runs.get_run("default-old")
            frozen = json.loads(saved_run.binding_json)
            assert frozen["execution_versions"]["selector"] == "0.8.0"
            reservations = tuple(asdict(row) for row in runs.reservations_for_run("default-old"))
            assert len(reservations) == 1 and reservations[0]["usage_status"] == "known"
            objects = {
                p: p.read_bytes() for p in (root / "catalog/objects").rglob("*.json")
            }
            assert len(objects) == 1
            upgraded = _launcher(root, "new-default")
            if schema == "narrative-batch-request/1":
                before = _dump(root / "AUTO.sqlite")
                path.write_text(json.dumps({**intent, "selector_version": "0.9.0"}), encoding="utf-8")
                process, refused = invoke(root, config, path, llm, "default-old", launcher=upgraded)
                assert process.returncode == 2 and refused["error"] == "BATCH_REQUEST_CHANGED", refused
                assert _dump(root / "AUTO.sqlite") == before
                path.write_text(json.dumps(intent), encoding="utf-8")
                unavailable = _launcher(root, "unavailable-prompt", prompt="unsupported-test-prompt/99")
                process, refused = invoke(root, config, path, llm, "default-old", launcher=unavailable)
                assert process.returncode == 2 and refused["error"] == (
                    "BATCH_EXECUTION_VERSION_UNAVAILABLE_NEW_RUN_REQUIRED"
                ), refused
                assert _dump(root / "AUTO.sqlite") == before
                assert len(loopback_model_server.requests) == 1
                changed_llm = root / "changed-llm.yaml"
                changed_llm.write_text(
                    llm.read_text(encoding="utf-8").replace("temperature: 0.7", "temperature: 0.9"),
                    encoding="utf-8",
                )
                process, refused = invoke(
                    root, config, path, changed_llm, "default-old", launcher=upgraded,
                )
                assert process.returncode == 2 and refused["error"] == "BATCH_REQUEST_CHANGED", refused
                assert _dump(root / "AUTO.sqlite") == before
                assert len(loopback_model_server.requests) == 1
            process, completed = invoke(root, config, path, llm, "default-old", launcher=upgraded)
            assert process.returncode == 0 and completed["status"] == "completed", completed
            assert len(loopback_model_server.requests) == 1
            assert runs.get_run("default-old").binding_json == saved_run.binding_json
            assert runs.get_run("default-old").job_ids == saved_run.job_ids
            assert completed["budget"] == prepared["budget"]
            settled = tuple(asdict(row) for row in runs.reservations_for_run("default-old"))
            for key in ("attempt_id", "run_id", "job_id", "usage_status", "input_tokens",
                        "output_tokens", "estimated_micro_usd", "usage_settled_at"):
                assert settled[0][key] == reservations[0][key]
            assert settled[0]["output_bytes"] == completed[result_field][0]["artifact_ref"]["byte_size"]
            assert all(p.read_bytes() == data for p, data in objects.items())
            pin = completed[result_field][0]["artifact_ref"]
            public_pin = pin if schema.endswith("/2") else exact_ref(imported, pin)
            _, bundle, receipt = public_read(root, config, imported, kind, exact=public_pin)
            assert bundle["versions"]["selector"] == "0.8.0"
            assert "reading_context" not in bundle
            before = _dump(root / "AUTO.sqlite")
            process, repeated = invoke(root, config, path, llm, "default-old", launcher=upgraded)
            assert process.returncode == 0 and repeated[result_field] == completed[result_field]
            assert _dump(root / "AUTO.sqlite") == before
            cross = request_path(
                root, imported, loopback_model_server.endpoint, "explicit-old-reuse",
                selector_version="0.8.0", max_cost_usd="0", max_tokens=1,
            )
            process, reused = invoke(
                root, config, cross, llm, "explicit-old-reuse", launcher=upgraded,
                database=root / "other.sqlite",
            )
            assert process.returncode == 0 and reused["status"] == "completed", reused
            assert exact_ref(imported, reused["documents"][0]["artifact_ref"]) == public_pin
            assert reused["budget"]["tokens"] == reused["budget"]["estimated_micro_usd"] == 0
            assert len(loopback_model_server.requests) == 1 and not loopback_model_server.errors
            assert tuple(asdict(row) for row in runs.reservations_for_run("default-old")) == settled
            record_proof(
                "default-upgrade-" + schema.rsplit("/", 1)[1], loopback_model_server,
                completed, receipt, extra={"initial": prepared, "cross_run": reused},
            )
        finally:
            assert all(_fingerprint(p) == saved for p, saved in preserved.items())


def _request():
    return SimpleNamespace(
        selector_version=None,
        execution_versions={"selector": "0.9.0", "prompt": "p/1", "parser": "x/1"},
    )


def test_effective_resolver_pins_supported_omitted_selector_only():
    request = _request()
    frozen = {**batch._execution_versions(request), "selector": "0.8.0"}
    saved = deepcopy(frozen)
    effective = batch._effective_execution_versions(request, frozen, require_available=True)
    assert effective == frozen and frozen == saved
    assert batch._effective_execution_versions(request)["selector"] == "0.9.0"
    request.selector_version = "0.9.0"
    with pytest.raises(batch.BatchResumeError, match="BATCH_EXECUTION_VERSION_UNAVAILABLE"):
        batch._effective_execution_versions(request, frozen, require_available=True)


@pytest.mark.parametrize("changed", ["prompt", "parser", "handlers", "selector"])
def test_unavailable_frozen_execution_is_not_hidden_by_default_compatibility(changed):
    request = _request()
    frozen = deepcopy(batch._execution_versions(request))
    if changed == "handlers":
        frozen[changed]["source.narrative_select"] = "unavailable/99"
    else:
        frozen[changed] = "unavailable/99"
    with pytest.raises(batch.BatchResumeError, match="BATCH_EXECUTION_VERSION_UNAVAILABLE"):
        batch._effective_execution_versions(request, frozen, require_available=True)
    # Terminal historical reads may still use the old metadata. They do not
    # execute an unavailable handler/parser/prompt or refund historical usage.
    assert batch._effective_execution_versions(request, frozen) == frozen
