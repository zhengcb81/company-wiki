"""Frozen legacy summary input survives the software projection upgrade."""
from dataclasses import asdict
import json

from company_wiki.automation.narrative_batch import _thaw_generations
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from integration.test_narrative_generation_reuse import (
    setup_source, request_path, invoke, public_read, official,
    loopback_model_server as _loopback_fixture,
)

loopback_model_server = _loopback_fixture


def test_old_missing_projection_pauses_before_model_and_resumes_exact_legacy_bytes(
    loopback_model_server, monkeypatch,
):
    monkeypatch.setenv("DEEPSEEK_API_KEY", official.batch_fixtures.KEY)
    with setup_source(loopback_model_server.endpoint) as (root, catalog, config, llm, imported, kind):
        protected = {p: p.read_bytes() for p in (config, llm, *(root / "companies").rglob("*")) if p.is_file()}
        try:
            launcher = root / "pause-before-paid-call.py"
            launcher.write_text('''from pathlib import Path
import json
from company_wiki.automation import narrative_model
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
    narrative_model.READING_MODEL_PROJECTION_VERSION = None
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
                "from company_wiki.automation import narrative_model\nnarrative_model.READING_MODEL_PROJECTION_VERSION=None\n"
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
            error_type = (root / "pause-error-type.txt").read_text(encoding="utf-8") if (root / "pause-error-type.txt").exists() else None
            assert process.returncode == 2 and paused["status"] == "paused", (paused, error_type)
            assert not loopback_model_server.requests
            recorded = json.loads((root / "pre-http-request.json").read_text(encoding="utf-8"))
            assert json.loads(recorded["data_json"])["reading_strategy"]["schema_version"] == "du-production-reading/1"
            runs = NarrativeRunStore(root / "AUTO.sqlite")
            old = runs.get_run("unpaid-old-input")
            assert not runs.reservations_for_run("unpaid-old-input")
            process, completed = invoke(root, config, path, llm, "unpaid-old-input")
            assert process.returncode == 0 and completed["status"] == "completed", completed
            assert len(loopback_model_server.requests) == 1 and not loopback_model_server.errors
            actual = json.loads(loopback_model_server.requests[0][1])
            assert actual["messages"][0]["content"] == recorded["instruction"]
            assert actual["messages"][1]["content"] == recorded["data_json"]
            assert runs.get_run("unpaid-old-input").binding_json == old.binding_json
            public_read(root, config, imported, kind)
        finally:
            assert all(p.read_bytes() == body for p, body in protected.items())


def test_old_missing_projection_paid_outbox_recovers_then_new_generation_is_cached(
    loopback_model_server, monkeypatch,
):
    monkeypatch.setenv("DEEPSEEK_API_KEY", official.batch_fixtures.KEY)
    with setup_source(loopback_model_server.endpoint) as (root, catalog, config, llm, imported, kind):
        sentinel = root / "keep.txt"
        sentinel.write_bytes(b"preserve existing fixture")
        protected = {p: p.read_bytes() for p in (config, llm, sentinel, *(root / "companies").rglob("*")) if p.is_file()}
        try:
            launcher = root / "old-model-input.py"
            launcher.write_text('''from company_wiki.automation import narrative_model
from company_wiki.source_catalog.narrative_artifact_store import NarrativeArtifactStore
from company_wiki.source_catalog.lock import CatalogOperationLockedError
from narrative_batch_configured import main
def hold(*args, **kwargs):
    raise CatalogOperationLockedError("old paid output awaits activation")
if __name__ == "__main__":
    narrative_model.READING_MODEL_PROJECTION_VERSION = None
    NarrativeArtifactStore.activate = hold
    raise SystemExit(main())
''', encoding="utf-8")
            old_path = request_path(root, imported, loopback_model_server.endpoint, "old-input", selector_version="0.9.0")
            process, prepared = invoke(root, config, old_path, llm, "old-input", launcher=launcher)
            assert process.returncode == 2 and prepared["documents"][0]["status"] == "activation_pending", prepared
            assert len(loopback_model_server.requests) == 1
            runs = NarrativeRunStore(root / "AUTO.sqlite")
            old = runs.get_run("old-input")
            key = imported["source_ref"]["document_id"]
            assert "reading_model_projection" not in _thaw_generations(json.loads(old.binding_json))[key]
            before = tuple(asdict(row) for row in runs.reservations_for_run("old-input"))
            old_body = json.loads(loopback_model_server.requests[0][1])
            old_data = json.loads(old_body["messages"][1]["content"])
            assert old_data["reading_strategy"]["schema_version"] == "du-production-reading/1"
            process, restored = invoke(root, config, old_path, llm, "old-input")
            assert process.returncode == 0 and restored["status"] == "completed", restored
            assert len(loopback_model_server.requests) == 1
            assert runs.get_run("old-input").binding_json == old.binding_json
            after = tuple(asdict(row) for row in runs.reservations_for_run("old-input"))
            assert all(before[0][key] == after[0][key] for key in ("attempt_id", "request_sha256", "input_tokens", "output_tokens", "estimated_micro_usd"))
            _, legacy_bundle, _ = public_read(root, config, imported, kind)
            new_path = request_path(root, imported, loopback_model_server.endpoint, "new-input", selector_version="0.9.0")
            process, current = invoke(root, config, new_path, llm, "new-input")
            assert process.returncode == 0 and current["status"] == "completed", current
            assert len(loopback_model_server.requests) == 2
            manifest = _thaw_generations(json.loads(runs.get_run("new-input").binding_json))[key]
            assert manifest["reading_model_projection"] == "reading-model-input/1"
            data = json.loads(json.loads(loopback_model_server.requests[1][1])["messages"][1]["content"])
            assert data["reading_strategy"]["schema_version"] == "reading-model-input/1"
            assert data["evidence"] == old_data["evidence"]
            assert runs.reservations_for_run("new-input")[0].request_sha256 != after[0]["request_sha256"]
            assert current["documents"][0]["artifact_ref"] != restored["documents"][0]["artifact_ref"]
            process, same = invoke(root, config, new_path, llm, "new-input")
            assert process.returncode == 0 and same["documents"] == current["documents"]
            cross_path = request_path(root, imported, loopback_model_server.endpoint, "new-input-reuse", selector_version="0.9.0", max_cost_usd="0", max_tokens=1)
            process, reused = invoke(root, config, cross_path, llm, "new-input-reuse", database=root / "other.sqlite")
            assert process.returncode == 0 and reused["status"] == "completed", reused
            assert reused["documents"][0]["artifact_ref"] == current["documents"][0]["artifact_ref"]
            assert reused["budget"]["tokens"] == reused["budget"]["estimated_micro_usd"] == 0
            assert len(loopback_model_server.requests) == 2 and not loopback_model_server.errors
            _, new_bundle, _ = public_read(root, config, imported, kind)
            assert new_bundle["reading_context"] == legacy_bundle["reading_context"]
        finally:
            assert all(p.read_bytes() == body for p, body in protected.items())
