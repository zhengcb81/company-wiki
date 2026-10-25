"""Frozen legacy summary input survives the software projection upgrade."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

import pytest

from company_wiki.automation.narrative_batch import _thaw_generations
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from integration.test_narrative_generation_reuse import (
    setup_source, request_path, invoke, public_read, official,
    record_proof,
    loopback_model_server as _loopback_fixture,
)

loopback_model_server = _loopback_fixture


def _fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size, path.stat().st_mtime_ns


@pytest.fixture(autouse=True)
def protect_canonical_config():
    repo = Path(__file__).resolve().parents[2]
    saved = {p: _fingerprint(p) for p in (repo / "config.yaml", repo / "config/source_catalog.yaml")}
    yield
    assert all(_fingerprint(p) == value for p, value in saved.items())


@pytest.fixture
def versioned_replies(monkeypatch):
    """Record the shared provider helper's real replies without another protocol."""
    original = official.batch_fixtures.response_draft
    emitted = []

    def response(data):
        body = original(data)
        emitted.append((data["schema_version"], body))
        return body

    monkeypatch.setattr(official.batch_fixtures, "response_draft", response)
    return emitted


def _historical_manifest_binding(version):
    # Call the real explicit software-generation API. Never change either
    # projection constant: the current default must remain independently bound.
    return '''from company_wiki.automation import narrative_batch
from company_wiki.automation.narrative_generation import generation_manifest
def historical_generation(*args, **kwargs):
    kwargs["reading_model_projection"] = VERSION
    return generation_manifest(*args, **kwargs)
narrative_batch.generation_manifest = historical_generation
'''.replace("VERSION", repr(version))


def _assert_historical_manifest(run, key, version):
    manifest = _thaw_generations(json.loads(run.binding_json))[key]
    if version is None:
        assert "reading_model_projection" not in manifest
    else:
        assert manifest["reading_model_projection"] == version


def _assert_historical_wire(data, version):
    if version == "reading-model-input/2":
        assert data["schema_version"] == "narrative-model-request/3"
        assert data["reading_strategy"]["schema_version"] == version
        assert set(data["response_schema"]["properties"]["draft"]["properties"]) == {"claims"}
        return
    assert data["schema_version"] == "narrative-model-request/1.4"
    # This test freezes a legacy projection choice against today's native
    # selection. Exact pre-upgrade context/1 bytes are covered by immutable
    # golden packets and the separate old-code lifecycle replay.
    assert data["reading_strategy"]["schema_version"] == (
        "du-production-reading/3" if version is None else version)
    assert {"source_id", "source_sha256", "language"} <= set(
        data["response_schema"]["properties"]["draft"]["properties"])


def _proof(root, server, result, projection, phase):
    """Optional owned evidence survives cleanup even if the next assertion fails."""
    ledger = NarrativeRunStore(root / "AUTO.sqlite")
    run = ledger.get_run(result["run_id"])
    binding = json.loads(run.binding_json) if run and run.binding_json else {}
    manifests = _thaw_generations(binding) if "generation_settings" in binding else {}
    record_proof(f"{projection or 'missing'}-{phase}", server, result, extra={
        "run_prompt_version": run.prompt_version if run else None,
        "job_prompt_versions": binding.get("job_prompt_versions"),
        "manifest_prompt_versions": {key: value["execution_versions"]["prompt"] for key, value in manifests.items()},
        "native_reservations": [asdict(row) for row in ledger.reservations_for_run(result["run_id"])],
    })


@pytest.mark.parametrize("historical_projection", [None, "reading-model-input/1", "reading-model-input/2"],
                         ids=["missing", "reading-v1", "reading-v2"])
def test_old_missing_projection_pauses_before_model_and_resumes_exact_legacy_bytes(
    loopback_model_server, monkeypatch, versioned_replies, historical_projection,
):
    monkeypatch.setenv("DEEPSEEK_API_KEY", official.batch_fixtures.KEY)
    with setup_source(loopback_model_server.endpoint) as (root, catalog, config, llm, imported, kind):
        sentinel = root / "keep.txt"
        sentinel.write_bytes(b"preserve existing fixture")
        protected = {p: _fingerprint(p) for p in (config, llm, sentinel, *(root / "companies").rglob("*")) if p.is_file()}
        try:
            launcher = root / "pause-before-paid-call.py"
            launcher.write_text(_historical_manifest_binding(historical_projection) + '''from pathlib import Path
import json
from company_wiki.automation.models import RuntimeState
from company_wiki.automation.narrative_model_caller import BudgetedNarrativeCaller
from company_wiki.automation.store import AutomationStore
from narrative_batch_configured import main
original_generate = BudgetedNarrativeCaller.generate
def paused(self, context, request):
    marker = Path(__file__).parent / "pre-http-request.json"
    marker.write_text(json.dumps({"instruction": request.instruction, "data_json": request.with_output_budget(self._model.max_output_tokens).data_json}), encoding="utf-8")
    try:
        store = AutomationStore(self._store.db_path)
        gate = store.read_runtime_gate()
        store.set_runtime_gate(RuntimeState.PAUSED, updated_at=gate.updated_at, expected_generation=gate.control_generation)
        return original_generate(self, context, request)
    except Exception as error:
        (Path(__file__).parent / "pause-error-type.txt").write_text(type(error).__name__, encoding="utf-8")
        raise
if __name__ == "__main__":
    BudgetedNarrativeCaller.generate = paused
    raise SystemExit(main())
''', encoding="utf-8")
            # Both controller and actual worker child receive this test-only
            # bootstrap. It pauses before reservation, never replaces output.
            bootstrap = root / "pre-http-bootstrap"
            bootstrap.mkdir()
            # runpy returns the real observer function; startup module caching
            # must not leave the worker without its pre-HTTP interruption.
            (bootstrap / "sitecustomize.py").write_text(
                "import runpy\nfixture=runpy.run_path(" + repr(str(launcher)) + ",run_name='fixture_bootstrap')\n"
                "from company_wiki.automation.narrative_model_caller import BudgetedNarrativeCaller\n"
                "BudgetedNarrativeCaller.generate=fixture['paused']\n", encoding="utf-8")
            entry = root / "pause-entry.py"
            entry.write_text(
                "import os,sys,runpy\nfrom pathlib import Path\nbootstrap=" + repr(str(bootstrap)) + "\n"
                "sys.path.insert(0,bootstrap)\nos.environ['PYTHONPATH']=bootstrap+os.pathsep+os.environ['PYTHONPATH']\n"
                "runpy.run_path(str(Path(bootstrap)/'sitecustomize.py'))\nfrom narrative_batch_configured import main\n"
                "if __name__=='__main__': raise SystemExit(main())\n", encoding="utf-8")
            path = request_path(root, imported, loopback_model_server.endpoint, "unpaid-old-input", selector_version="0.9.0")
            process, paused = invoke(root, config, path, llm, "unpaid-old-input", launcher=entry)
            _proof(root, loopback_model_server, paused, historical_projection, "pre-model-pause")
            error_type = (root / "pause-error-type.txt").read_text(encoding="utf-8") if (root / "pause-error-type.txt").exists() else None
            assert process.returncode == 2 and paused["status"] == "paused", (paused, error_type)
            assert not loopback_model_server.requests and not versioned_replies
            recorded = json.loads((root / "pre-http-request.json").read_text(encoding="utf-8"))
            _assert_historical_wire(json.loads(recorded["data_json"]), historical_projection)
            runs = NarrativeRunStore(root / "AUTO.sqlite")
            old = runs.get_run("unpaid-old-input")
            _assert_historical_manifest(old, imported["source_ref"]["document_id"], historical_projection)
            assert not runs.reservations_for_run("unpaid-old-input")
            process, completed = invoke(root, config, path, llm, "unpaid-old-input")
            _proof(root, loopback_model_server, completed, historical_projection, "legacy-paid-resume")
            assert process.returncode == 0 and completed["status"] == "completed", completed
            assert len(loopback_model_server.requests) == 1 and not loopback_model_server.errors
            actual = json.loads(loopback_model_server.requests[0][1])
            assert actual["messages"][0]["content"] == recorded["instruction"]
            assert actual["messages"][1]["content"] == recorded["data_json"]
            assert set(versioned_replies[0][1]["draft"]) == ({"claims"} if historical_projection == "reading-model-input/2"
                else {"source_id", "source_sha256", "language", "claims", "status"})
            assert runs.get_run("unpaid-old-input").binding_json == old.binding_json
            ref, bundle, _ = public_read(root, config, imported, kind)
            usage = tuple(asdict(row) for row in runs.reservations_for_run("unpaid-old-input"))
            process, repeated = invoke(root, config, path, llm, "unpaid-old-input")
            assert process.returncode == 0 and repeated["documents"] == completed["documents"]
            assert repeated["budget"] == completed["budget"]
            assert tuple(asdict(row) for row in runs.reservations_for_run("unpaid-old-input")) == usage
            assert public_read(root, config, imported, kind, exact=ref)[1] == bundle
            assert len(loopback_model_server.requests) == 1
        finally:
            assert all(_fingerprint(p) == body for p, body in protected.items())


@pytest.mark.parametrize("historical_projection", [None, "reading-model-input/1", "reading-model-input/2"],
                         ids=["missing", "reading-v1", "reading-v2"])
def test_old_missing_projection_paid_outbox_recovers_then_new_generation_is_cached(
    loopback_model_server, monkeypatch, versioned_replies, historical_projection,
):
    monkeypatch.setenv("DEEPSEEK_API_KEY", official.batch_fixtures.KEY)
    with setup_source(loopback_model_server.endpoint) as (root, catalog, config, llm, imported, kind):
        sentinel = root / "keep.txt"
        sentinel.write_bytes(b"preserve existing fixture")
        protected = {p: _fingerprint(p) for p in (config, llm, sentinel, *(root / "companies").rglob("*")) if p.is_file()}
        try:
            launcher = root / "old-model-input.py"
            launcher.write_text(_historical_manifest_binding(historical_projection) + '''
from company_wiki.source_catalog.narrative_artifact_store import NarrativeArtifactStore
from company_wiki.source_catalog.lock import CatalogOperationLockedError
from narrative_batch_configured import main
def hold(*args, **kwargs):
    raise CatalogOperationLockedError("old paid output awaits activation")
if __name__ == "__main__":
    NarrativeArtifactStore.activate = hold
    raise SystemExit(main())
''', encoding="utf-8")
            old_path = request_path(root, imported, loopback_model_server.endpoint, "old-input", selector_version="0.9.0")
            process, prepared = invoke(root, config, old_path, llm, "old-input", launcher=launcher)
            _proof(root, loopback_model_server, prepared, historical_projection, "legacy-activation-pending")
            assert process.returncode == 2 and prepared["documents"][0]["status"] == "activation_pending", prepared
            assert len(loopback_model_server.requests) == 1
            runs = NarrativeRunStore(root / "AUTO.sqlite")
            old = runs.get_run("old-input")
            key = imported["source_ref"]["document_id"]
            _assert_historical_manifest(old, key, historical_projection)
            before = tuple(asdict(row) for row in runs.reservations_for_run("old-input"))
            old_body = json.loads(loopback_model_server.requests[0][1])
            old_data = json.loads(old_body["messages"][1]["content"])
            _assert_historical_wire(old_data, historical_projection)
            assert set(versioned_replies[0][1]["draft"]) == ({"claims"} if historical_projection == "reading-model-input/2"
                else {"source_id", "source_sha256", "language", "claims", "status"})
            process, restored = invoke(root, config, old_path, llm, "old-input")
            _proof(root, loopback_model_server, restored, historical_projection, "legacy-outbox-restored")
            assert process.returncode == 0 and restored["status"] == "completed", restored
            assert len(loopback_model_server.requests) == 1
            assert runs.get_run("old-input").binding_json == old.binding_json
            after = tuple(asdict(row) for row in runs.reservations_for_run("old-input"))
            assert all(before[0][key] == after[0][key] for key in ("attempt_id", "request_sha256", "input_tokens", "output_tokens", "estimated_micro_usd", "response_sha256"))
            legacy_ref, legacy_bundle, _ = public_read(root, config, imported, kind)
            new_path = request_path(root, imported, loopback_model_server.endpoint, "new-input", selector_version="0.9.0")
            process, current = invoke(root, config, new_path, llm, "new-input")
            _proof(root, loopback_model_server, current, historical_projection, "current-v4-summary-miss")
            assert process.returncode == 0 and current["status"] == "completed", current
            assert len(loopback_model_server.requests) == 2
            manifest = _thaw_generations(json.loads(runs.get_run("new-input").binding_json))[key]
            assert manifest["reading_model_projection"] == "reading-model-input/4"
            assert manifest["reading_model_boundary"]["reading_projection_version"] == "reading-model-input/4"
            data = json.loads(json.loads(loopback_model_server.requests[1][1])["messages"][1]["content"])
            assert data["schema_version"] == "narrative-model-request/5"
            assert data["reading_strategy"]["schema_version"] == "reading-model-input/4"
            assert set(versioned_replies[1][1]) == {"drafts_by_task"}
            assert "evidence_groups" not in data
            material = data['material']
            fragments = material['shared_fragments'] + [part for task in material['tasks']
                for part in task['parts'] if 'text' in part]
            fragments.sort(key=lambda row: int(row['source_key'][1:]))
            assert [row['text'] for row in fragments] == [row[1] for row in old_data['evidence']]
            assert runs.reservations_for_run("new-input")[0].request_sha256 != after[0]["request_sha256"]
            assert current["documents"][0]["artifact_ref"] != restored["documents"][0]["artifact_ref"]
            new_usage = tuple(asdict(row) for row in runs.reservations_for_run("new-input"))
            process, same = invoke(root, config, new_path, llm, "new-input")
            assert process.returncode == 0 and same["documents"] == current["documents"]
            assert same["budget"] == current["budget"]
            cross_path = request_path(root, imported, loopback_model_server.endpoint, "new-input-reuse", selector_version="0.9.0", max_cost_usd="0", max_tokens=1)
            process, reused = invoke(root, config, cross_path, llm, "new-input-reuse", database=root / "other.sqlite")
            assert process.returncode == 0 and reused["status"] == "completed", reused
            assert reused["documents"][0]["artifact_ref"] == current["documents"][0]["artifact_ref"]
            assert reused["budget"]["tokens"] == reused["budget"]["estimated_micro_usd"] == 0
            assert not NarrativeRunStore(root / "other.sqlite").reservations_for_run("new-input-reuse")
            assert tuple(asdict(row) for row in runs.reservations_for_run("new-input")) == new_usage
            assert tuple(asdict(row) for row in runs.reservations_for_run("old-input")) == after
            assert len(loopback_model_server.requests) == 2 and not loopback_model_server.errors
            _, new_bundle, _ = public_read(root, config, imported, kind)
            assert new_bundle["reading_context"] == legacy_bundle["reading_context"]
            assert public_read(root, config, imported, kind, exact=legacy_ref)[1] == legacy_bundle
        finally:
            assert all(_fingerprint(p) == body for p, body in protected.items())
