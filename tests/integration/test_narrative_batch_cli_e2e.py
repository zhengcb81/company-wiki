"""Actual finite batch CLI, spawned production workers and bounded local HTTP."""

from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys

import pytest

from company_wiki.automation.models import RuntimeState
from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
from company_wiki.automation.narrative_projection import NarrativeBundleReader
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from company_wiki.automation.policy import PolicyConfig
from company_wiki.automation.registry import create_default_registry
from company_wiki.automation.scheduler import AutomationScheduler
from company_wiki.automation.store import AutomationStore
from company_wiki.source_catalog.narrative_artifact_store import LocalNarrativeObjectStore, NarrativeArtifactStore

from support import narrative_batch_fixtures as batch_fixtures
from support.narrative_batch_fixtures import (
    KEY, KEY_ENV, T0, assert_originals_and_foreign_jobs_untouched,
    foreign_ready_jobs, isolated_batch_directory, prepare_source_catalog,
)
from tools.n4c_live_preflight import consumer_bootstrap


loopback_model_server = batch_fixtures.loopback_model_server


@pytest.fixture
def r6_protected_inputs():
    """Check real read-only inputs even if the end-to-end assertion fails."""
    def snapshot(path):
        if not path.exists():
            return None
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return path.stat().st_size, path.stat().st_mtime_ns, digest.hexdigest()

    repo = Path(__file__).resolve().parents[2]
    protected = {p: snapshot(p) for p in [repo / "config/source_catalog.yaml",
                  repo / "config/source_acquisition.yaml", repo / ".source_catalog/catalog.sqlite3"]}

    def capture(paths):
        protected.update({p: snapshot(p) for p in paths})

    try:
        yield capture
    finally:
        assert {p: snapshot(p) for p in protected} == protected, "read-only inputs changed"


@pytest.mark.real_data
@pytest.mark.e2e
def test_partial_model_summary_configured_cli_public_views_and_committed_rf(
    tmp_path_factory, loopback_model_server, monkeypatch, r6_protected_inputs,
):
    """Real immutable TXT; fixture identity and HTTP, never a live supplier call."""
    transcript = os.environ.get("CWP_E2E_TRANSCRIPT_PATH")
    rf_project = os.environ.get("CWP_RF_PROJECT_ROOT")
    if not transcript or not rf_project:
        pytest.skip("requires explicit read-only original and RF checkout inputs")
    original_path, rf_root = Path(transcript), Path(rf_project)
    original = original_path.read_bytes()
    original_before = (original_path.stat().st_size, original_path.stat().st_mtime_ns,
                       hashlib.sha256(original).hexdigest())
    assert original_before[2] == "4ac3b4f0fa1be928b56b4ef9775cac694a1712d46785bb1fa28d2a6a68d7852a"
    rf_head = "6e6b817a1a6e4567293a4dcb835815f3be508a03"
    owner_paths = [rf_root / "assurance/runs/weekly_alert.jsonl", rf_root / "assurance/runs/weekly_manifest.json"]
    owner_before = {p: p.read_bytes() for p in owner_paths}
    r6_protected_inputs([original_path, *owner_paths])
    monkeypatch.setenv("DEEPSEEK_API_KEY", KEY)
    monkeypatch.setattr(batch_fixtures, "source_documents", lambda **_kwargs: [
        ("en", "real-body.txt", "Isolated real transcript bytes", "investor_call_transcript", original),
    ])
    sentinel = "PROVIDER_UNUSED_EXTENSION_SENTINEL"

    def partial_response(data):
        row = next(row for row in data["evidence"] if
                   (row[2] if len(row) > 2 else data["default_source_role"]) == "management")
        claim = {"claim_id": "kept", "text": row[1][:200].strip(), "evidence_ids": [row[0]],
                 "claim_type": "company_statement", "modality": "actual", "needs_review": False}
        return {"draft": {"source_id": data["source"]["source_id"],
                          "source_sha256": data["source"]["source_sha256"],
                          "language": data["source"]["language"], "status": "draft",
                          "claims": [claim, {**claim, "claim_id": "discarded",
                                             "evidence_ids": [row[0], "e404"]}],
                          "provider_unused": sentinel}}

    monkeypatch.setattr(batch_fixtures, "response_draft", partial_response)
    with isolated_batch_directory(tmp_path_factory) as root:
        state = _prepare(root, loopback_model_server.endpoint, one_source=True)
        try:
            # Public readers infer the project from config/<file>; batch CLI
            # also supplies project-root explicitly. Use one fixture layout.
            public_config = root / "config/catalog.json"
            public_config.parent.mkdir()
            public_config.write_bytes(state.config_path.read_bytes())
            state.config_path = public_config
            config_path = root / "llm.yaml"
            config_path.write_text("llm:\n  provider: deepseek\n  model: stub-model\n  base_url: "
                                   + loopback_model_server.endpoint.removesuffix('/chat/completions')
                                   + "\n  max_tokens: 8192\n  temperature: 0.7\n", encoding="utf-8")
            originals, config_before = _originals(state), config_path.read_bytes()
            process, result = _invoke(state, llm_config=config_path)
            assert process.returncode == 0 and result["status"] == "completed", (process.stderr, result)
            assert len(loopback_model_server.requests) == 1 and loopback_model_server.errors == []
            assert result["budget"] == {"tokens": 92, "estimated_micro_usd": 111,
                                        "unknown_reservations": 0, "unsettled_reservations": 0}
            assert result["documents"][0]["artifact_ref"] is not None
            exported = root / "rf-consumer"
            exported.mkdir()
            assert len(consumer_bootstrap(rf_root, rf_head, exported)) == 6
            env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"),
                       PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHON_DOTENV_DISABLED="1")

            def invoke(command, request):
                call = subprocess.run(command, input=json.dumps(request).encode(), env=env,
                                      cwd=root, capture_output=True, timeout=40)
                assert call.returncode == 0, call.stderr.decode(errors="replace")
                assert KEY.encode() not in call.stdout + call.stderr
                return call

            ref, _language, _kind = next(iter(state.indexed.values()))
            source_ref = {"schema_version": ref.schema_version, "document_id": ref.document_id,
                          "source_id": ref.source_id, "content_sha256": ref.content_sha256,
                          "byte_size": ref.byte_size, "mime_type": ref.mime_type}
            transport = [sys.executable, "-B", "-m", "company_wiki.source_catalog.narrative_transport_cli",
                         "--config", str(state.config_path)]
            direct_reference = json.loads(invoke(transport + ["--operation", "reference"],
                                                {"schema_version": "narrative-reference-request/1",
                                                 "source_ref": source_ref}).stdout)
            rf_command = [sys.executable, "-B", str(exported / "narrative_source_preparation.py"),
                          "--company-wiki-catalog-config", str(state.config_path)]
            reference = json.loads(invoke(rf_command + ["--operation", "reference"],
                                          {"schema_version": "narrative-reference-request/1",
                                           "source_ref": source_ref}).stdout)
            assert reference == direct_reference
            request = {"schema_version": "narrative-read-request/1", "narrative_ref": reference,
                       "as_of_date": "2026-10-06", "expected_source": {
                           "canonical_entity_id": "ent-acme", "market": "US", "security_id": "ACME",
                           "document_kind": "investor_call_transcript", "fiscal_year": 2026,
                           "fiscal_period": "Q1"}}
            context = json.loads(invoke(rf_command, request).stdout)
            assert context["quality_status"] == "needs_review"
            assert context["read_receipt"]["replay_status"] == "verified"
            assert context["summary"]["translate"] is False
            assert [claim["claim_id"] for claim in context["summary"]["draft"]["claims"]] == ["kept"]
            assert context["summary"]["draft"]["status"] == "needs_review"
            assert sentinel not in json.dumps(context)
            span = context["evidence_spans"][0]
            for operation, options in [("evidence-search", ["--query", "Copilot"]),
                                       ("evidence-lookup", ["--span-id", span["span_id"]])]:
                viewed = invoke(transport + ["--operation", operation, *options], request)
                view, receipt = json.loads(viewed.stdout), json.loads(viewed.stderr)
                assert view["quality_status"] == "needs_review" and view["items"]
                assert receipt["replay_status"] == "verified"
                assert receipt["locator_count"] == len(context["evidence_spans"])
            again, resumed = _invoke(state, llm_config=config_path)
            assert again.returncode == 0 and resumed["documents"] == result["documents"]
            assert resumed["budget"] == result["budget"] and len(loopback_model_server.requests) == 1
            record, = NarrativeRunStore(state.store.db_path).reservations_for_run("cli-e2e")
            assert record.usage_status == "known" and (record.input_tokens, record.output_tokens) == (73, 19)
            assert config_path.read_bytes() == config_before
            assert_originals_and_foreign_jobs_untouched(state, originals,
                output=process.stdout + process.stderr + again.stdout + again.stderr)
        finally:
            state.catalog.close()
    assert original_before == (original_path.stat().st_size, original_path.stat().st_mtime_ns,
                               hashlib.sha256(original_path.read_bytes()).hexdigest())
    assert {p: p.read_bytes() for p in owner_paths} == owner_before


def _prepare(
    root,
    endpoint,
    *,
    one_source=False,
    zero_budget=False,
    sparse_metadata=False,
    include_mixed=False,
    include_annual_pdf=False,
    include_policy=True,
    policy_title=None,
):
    state = prepare_source_catalog(
        root,
        one_source=one_source,
        sparse_metadata=sparse_metadata,
        include_mixed=include_mixed,
        include_annual_pdf=include_annual_pdf,
        include_policy=include_policy,
        policy_title=policy_title,
    )
    try:
        state.store = AutomationStore(root / "automation.db")
        state.store.set_runtime_gate(RuntimeState.ENABLED, updated_at=T0)
        scheduler = AutomationScheduler(state.store, create_default_registry(),
                                        PolicyConfig(allow_llm=True, allow_network=True))
        state.outside = foreign_ready_jobs(state, state.store, scheduler)
        state.store.set_runtime_gate(RuntimeState.PAUSED, updated_at=T0)
        request = NarrativeBatchRequest.from_dict({
            "schema_version": "narrative-batch-request/1", "run_id": "cli-e2e",
            "sources": [{"schema_version": ref.schema_version, "document_id": ref.document_id,
                         "source_id": ref.source_id, "content_sha256": ref.content_sha256,
                         "byte_size": ref.byte_size, "mime_type": ref.mime_type}
                        for ref, _language, _kind in state.indexed.values()],
            "profile": "P2", "max_seconds": 40, "max_tokens": 200_000,
            "max_cost_usd": "0" if zero_budget else "2",
            "model": {"model_id": "stub-model", "endpoint": endpoint, "api_key_env": KEY_ENV,
                      "max_output_tokens": 400, "timeout_seconds": 5, "allow_local_http": True},
            "pricing": {"version": "fixture-price/1", "input_micro_usd_per_million_tokens": 1_000_000,
                        "output_micro_usd_per_million_tokens": 2_000_000},
        })
        state.request_path = root / "request.json"
        state.request_path.write_text(json.dumps(request.to_dict(), ensure_ascii=False), encoding="utf-8")
        assert KEY not in state.request_path.read_text(encoding="utf-8")
        return state
    except BaseException:
        state.catalog.close()
        raise


def _invoke(state, *, llm_config=None, llm_provider=None, launcher=None):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"
    env["PYTHON_DOTENV_DISABLED"] = "1"
    entrypoint = [sys.executable, "-m", "company_wiki.automation.narrative_batch_cli"]
    if llm_config is not None:
        entrypoint = [sys.executable, str(Path(__file__).resolve().parents[2] / "scripts/narrative_batch_configured.py"),
                      "--llm-config", str(llm_config), "--allow-local-model-http"]
    elif launcher is not None:
        entrypoint = [sys.executable, str(launcher)]
    if llm_provider is not None:
        entrypoint += ["--llm-provider", llm_provider]
    process = subprocess.run([
        *entrypoint,
        "--project-root", str(state.root), "--catalog-config", str(state.config_path),
        "--automation-db", str(state.store.db_path), "--work-dir", str(state.root / "run-work"),
        "--request", str(state.request_path),
    ], cwd=state.root, env=env, capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert KEY not in process.stdout + process.stderr
    assert process.stdout.strip(), process.stderr
    result = json.loads(process.stdout)
    assert isinstance(result, dict) and result["schema_version"] == "narrative-batch-result/1"
    assert result["run_id"] == "cli-e2e"
    return process, result


def test_cli_finishes_when_owned_storage_file_disappears_during_sampling(
    tmp_path_factory, loopback_model_server,
):
    with isolated_batch_directory(tmp_path_factory) as root:
        state = _prepare(root, loopback_model_server.endpoint, one_source=True)
        try:
            launcher = root / "storage_race.py"
            launcher.write_text('''from pathlib import Path
import sys
import company_wiki.automation.narrative_batch as batch
from company_wiki.automation.narrative_batch_cli import main

original_tree_bytes = batch._tree_bytes
original_stat = Path.stat
transient = None
injected = False
removed = False

def stat_then_remove(path, *args, **kwargs):
    global removed
    result = original_stat(path, *args, **kwargs)
    if path == transient and not removed:
        removed = True
        path.unlink()
    return result

def measured(path):
    global transient, injected
    if path.name == "run-work" and (path / "storage-baseline.json").exists() and not injected:
        transient = path / "sampling.tmp"
        transient.write_bytes(b"bounded transient fixture")
        injected = True
    return original_tree_bytes(path)

if __name__ == "__main__":
    Path.stat = stat_then_remove
    batch._tree_bytes = measured
    try:
        code = main()
    finally:
        print(f"storage_race_injected={int(injected and removed)}", file=sys.stderr)
    raise SystemExit(code)
''', encoding="utf-8")
            originals = _originals(state)
            process, result = _invoke(state, launcher=launcher)
            assert "storage_race_injected=1" in process.stderr
            assert process.returncode == 0 and result["status"] == "completed", (process.stderr, result)
            assert len(loopback_model_server.requests) == 1
            assert all(item["artifact_ref"] is not None for item in result["documents"])
            assert result["budget"]["unknown_reservations"] == 0
            assert result["budget"]["unsettled_reservations"] == 0
            assert not (root / "run-work/sampling.tmp").exists()
            assert_originals_and_foreign_jobs_untouched(state, originals,
                output=process.stdout + process.stderr)
        finally:
            state.catalog.close()


@pytest.mark.parametrize("provider", ["minimax", "mimo", "deepseek"])
def test_configured_entrypoint_uses_existing_loader_through_real_worker_and_resume(
    tmp_path_factory, loopback_model_server, monkeypatch, provider,
):
    monkeypatch.setenv(provider.upper() + "_API_KEY", KEY)
    with isolated_batch_directory(tmp_path_factory) as root:
        state = _prepare(root, loopback_model_server.endpoint, one_source=True)
        try:
            config_path = root / "llm.yaml"
            endpoint = loopback_model_server.endpoint.removesuffix('/chat/completions')
            profile = f"  provider: {provider}\n  model: stub-model\n  base_url: {endpoint}\n"
            if provider == "mimo":
                # Exercise explicit fallback selection with a primary that must
                # never be contacted, rather than replacing production config.
                profile = ("  provider: minimax\n  model: stale-primary\n"
                           "  base_url: https://primary.invalid/v1\n  fallback:\n"
                           f"    provider: mimo\n    model: stub-model\n    base_url: {endpoint}\n")
            config_path.write_text("llm:\n" + profile
                                  + "  max_tokens: 8192\n  temperature: 0.7\n  reasoning_split: true\n",
                                  encoding="utf-8")
            config_before = config_path.read_bytes()
            raw = json.loads(state.request_path.read_text(encoding="utf-8"))
            # A stale competing copy cannot change the configured invocation.
            raw["model"].update(model_id="stale-model", endpoint="https://wrong.invalid/v1/chat/completions",
                                max_output_tokens=1, thinking="disabled")
            state.request_path.write_text(json.dumps(raw), encoding="utf-8")
            originals = _originals(state)
            process, result = _invoke(state, llm_config=config_path, llm_provider=provider)
            assert process.returncode == 0 and result["status"] == "completed", (process.stderr, result)
            assert loopback_model_server.errors == [] and len(loopback_model_server.requests) == 1
            body = json.loads(loopback_model_server.requests[0][1])
            token_field = "max_tokens" if provider == "deepseek" else "max_completion_tokens"
            assert body["model"] == "stub-model" and body[token_field] == 8192
            assert body["temperature"] == 0.7
            assert body.get("reasoning_split") is (True if provider == "minimax" else None)
            assert ({"max_tokens", "max_completion_tokens"} & body.keys()) == {token_field}
            assert "thinking" not in body
            again, repeated = _invoke(state, llm_config=config_path, llm_provider=provider)
            assert again.returncode == 0 and repeated["status"] == "completed"
            assert repeated["documents"] == result["documents"]
            assert repeated["budget"] == result["budget"]
            assert repeated["storage"]["persistent_added_bytes"] == result["storage"]["persistent_added_bytes"]
            assert len(loopback_model_server.requests) == 1  # Resume never repays.
            assert config_path.read_bytes() == config_before
            assert_originals_and_foreign_jobs_untouched(state, originals,
                output=process.stdout + process.stderr + again.stdout + again.stderr)
        finally:
            state.catalog.close()


def _originals(state):
    return {path: path.read_bytes() for path in (state.root / "companies").rglob("*") if path.is_file()}


@pytest.mark.parametrize("sparse_metadata", [False, True])
def test_cli_p2_publishes_two_languages_and_skips_policy_without_model_call(
    tmp_path_factory, loopback_model_server, sparse_metadata
):
    with isolated_batch_directory(tmp_path_factory) as root:
        state = _prepare(
            root,
            loopback_model_server.endpoint,
            sparse_metadata=sparse_metadata,
            policy_title="Investor Relations Policy" if sparse_metadata else None,
        )
        try:
            request = json.loads(state.request_path.read_text(encoding="utf-8"))
            request["model"]["thinking"] = "disabled"
            state.request_path.write_text(json.dumps(request), encoding="utf-8")
            originals = _originals(state)
            process, result = _invoke(state)
            assert process.returncode == 0 and result["status"] == "completed", (process.stderr, result)
            assert loopback_model_server.errors == [] and len(loopback_model_server.requests) == 2
            assert all(json.loads(body)["thinking"] == {"type": "disabled"}
                       for _data, body in loopback_model_server.requests)
            assert {data["source"]["language"] for data, _body in loopback_model_server.requests} == {"en", "zh"}
            assert result["budget"]["tokens"] == 184 and result["budget"]["estimated_micro_usd"] == 222
            assert result["budget"]["unknown_reservations"] == 0
            assert result["budget"]["unsettled_reservations"] == 0
            documents = {item["document_id"]: item for item in result["documents"]}
            assert documents.keys() == state.indexed.keys()
            artifacts = NarrativeArtifactStore(state.catalog.store, LocalNarrativeObjectStore(state.catalog.config.catalog_dir))
            reader = NarrativeBundleReader(artifacts)
            artifact_refs = {}
            for document_id, (ref, language, kind) in state.indexed.items():
                item = documents[document_id]
                assert isinstance(item["status"], str) and item["status"]
                loaded = reader.read(document_id=document_id, source_id=ref.source_id, source_sha256=ref.content_sha256)
                artifact_ref = item["artifact_ref"]
                assert artifact_ref["artifact_version_id"] == loaded.artifact.artifact_version_id
                assert artifact_ref["content_sha256"] == loaded.artifact.content_sha256
                assert artifact_ref["byte_size"] == loaded.artifact.byte_size
                assert loaded.bundle.source_metadata.language == language and loaded.bundle.summary.translate is False
                if kind == "ir_policy":
                    assert loaded.bundle.selection.status == "skipped_no_narrative"
                    assert loaded.bundle.summary.status == "summary_not_needed"
                else:
                    assert loaded.bundle.summary.draft.language == language
                    claim = loaded.bundle.summary.draft.claims[0].text
                    assert claim in " ".join(span.raw_text for span in loaded.bundle.evidence_spans)
                    assert ("新产品" in claim) if language == "zh" else ("new product" in claim)
                artifact_refs[document_id] = artifact_ref
            again, repeated = _invoke(state)
            assert again.returncode == 0 and repeated["status"] == "completed", (again.stderr, repeated)
            assert len(loopback_model_server.requests) == 2
            assert {item["document_id"]: item["artifact_ref"] for item in repeated["documents"]} == artifact_refs
            assert repeated["budget"] == result["budget"]
            assert_originals_and_foreign_jobs_untouched(state, originals,
                output=process.stdout + process.stderr + again.stdout + again.stderr)
            # A completed-run resume must re-read the original bytes, and a
            # refusal must retain the real charge already paid by that run.
            path = state.raw_paths["call-en.txt"]
            path.write_bytes(path.read_bytes() + b"Changed after completed publication.\n")
            changed_originals = _originals(state)
            changed, refused = _invoke(state)
            assert changed.returncode == 2 and refused["status"] == "failed", (changed.stderr, refused)
            assert len(loopback_model_server.requests) == 2 and refused["budget"] == result["budget"]
            assert_originals_and_foreign_jobs_untouched(state, changed_originals, output=changed.stdout + changed.stderr)
        finally:
            state.catalog.close()


def test_cli_infers_sparse_languages_from_verified_pdf_and_transcript_bytes(
    tmp_path_factory, loopback_model_server
):
    with isolated_batch_directory(tmp_path_factory) as root:
        state = _prepare(
            root,
            loopback_model_server.endpoint,
            sparse_metadata=True,
            include_mixed=True,
            include_annual_pdf=True,
            include_policy=False,
        )
        try:
            originals = _originals(state)
            process, result = _invoke(state)
            assert process.returncode == 0 and result["status"] == "completed", (process.stderr, result)
            assert loopback_model_server.errors == [] and len(loopback_model_server.requests) == 4
            assert {data["source"]["language"] for data, _body in loopback_model_server.requests} == {
                "en", "zh", "mixed",
            }
            assert all(
                "No translation" in json.loads(body)["messages"][0]["content"]
                for _data, body in loopback_model_server.requests
            )

            documents = {item["document_id"]: item for item in result["documents"]}
            assert documents.keys() == state.indexed.keys()
            artifacts = NarrativeArtifactStore(
                state.catalog.store,
                LocalNarrativeObjectStore(state.catalog.config.catalog_dir),
            )
            reader = NarrativeBundleReader(artifacts)
            for document_id, (ref, expected_language, kind) in state.indexed.items():
                loaded = reader.read(
                    document_id=document_id,
                    source_id=ref.source_id,
                    source_sha256=ref.content_sha256,
                )
                assert loaded.bundle.source_metadata.language == expected_language
                assert loaded.bundle.summary.translate is False
                if kind == "ir_policy":
                    assert loaded.bundle.selection.status == "skipped_no_narrative"
                else:
                    assert loaded.bundle.summary.draft.language == expected_language

            again, repeated = _invoke(state)
            assert again.returncode == 0 and repeated["status"] == "completed", (again.stderr, repeated)
            assert len(loopback_model_server.requests) == 4
            assert_originals_and_foreign_jobs_untouched(
                state,
                originals,
                output=process.stdout + process.stderr + again.stdout + again.stderr,
            )
        finally:
            state.catalog.close()


@pytest.mark.parametrize("failure", ["zero-budget", "changed-source-sha", "tiny-storage-cap"])
def test_cli_refuses_model_work_without_http_or_overwriting_originals(tmp_path_factory, loopback_model_server, failure):
    with isolated_batch_directory(tmp_path_factory) as root:
        state = _prepare(root, loopback_model_server.endpoint, one_source=True, zero_budget=failure == "zero-budget")
        try:
            if failure == "changed-source-sha":
                path = state.raw_paths["call-en.txt"]
                path.write_bytes(path.read_bytes() + b"Changed after the frozen source reference.\n")
            elif failure == "tiny-storage-cap":
                request = json.loads(state.request_path.read_text(encoding="utf-8"))
                request["max_persistent_bytes"] = 4096
                state.request_path.write_text(json.dumps(request), encoding="utf-8")
            originals = _originals(state)
            process, result = _invoke(state)
            expected = {"zero-budget": "budget_exhausted", "changed-source-sha": "failed",
                        "tiny-storage-cap": "storage_exhausted"}[failure]
            assert process.returncode == 2 and result["status"] == expected, (process.stderr, result)
            assert loopback_model_server.errors == [] and loopback_model_server.requests == []
            assert {item["document_id"] for item in result["documents"]} == state.indexed.keys()
            assert all(isinstance(item["status"], str) and item["status"] for item in result["documents"])
            assert all(item.get("artifact_ref") is None for item in result["documents"])
            assert result["budget"]["tokens"] == 0 and result["budget"]["estimated_micro_usd"] == 0
            assert result["budget"]["unknown_reservations"] == 0 and result["budget"]["unsettled_reservations"] == 0
            run_store = NarrativeRunStore(state.store.db_path)
            if run_store.get_run("cli-e2e") is not None:
                assert run_store.reservations_for_run("cli-e2e") == ()
            if failure == "tiny-storage-cap":
                assert {job.job_id for job in state.store.list_jobs()} == {job.job_id for job in state.outside}
            assert state.store.list_outbox_entries(status="pending") == ()
            assert_originals_and_foreign_jobs_untouched(state, originals, output=process.stdout + process.stderr)
        finally:
            state.catalog.close()


def test_cli_persists_safe_http_status_and_unknown_charge_without_provider_body(
    tmp_path_factory, loopback_model_server,
):
    sentinel = b"PROVIDER_ERROR_BODY_SENTINEL"
    loopback_model_server.response_status = 400
    loopback_model_server.error_body = sentinel + KEY.encode()
    with isolated_batch_directory(tmp_path_factory) as root:
        state = _prepare(root, loopback_model_server.endpoint, one_source=True)
        try:
            originals = _originals(state)
            process, result = _invoke(state)
            assert process.returncode == 2 and result["status"] == "failed"
            assert len(loopback_model_server.requests) == 1
            assert loopback_model_server.errors == []
            run_store = NarrativeRunStore(state.store.db_path)
            reservations = run_store.reservations_for_run("cli-e2e")
            assert len(reservations) == 1
            record = reservations[0]
            assert record.error_code == "MODEL_HTTP_CLIENT_ERROR"
            assert record.usage_status == "unknown"
            assert record.charged_tokens == record.reserved_tokens > 0
            assert result["budget"]["tokens"] == record.reserved_tokens
            assert result["budget"]["unknown_reservations"] == 1
            assert record.output_bytes == 0 and record.response_sha256 is None
            attempt = state.store.get_attempt(record.attempt_id)
            assert attempt.error_code == "MODEL_HTTP_CLIENT_ERROR"
            assert attempt.error_detail == (
                "metered model attempt did not complete (http_status=400)"
            )
            assert sentinel.decode() not in process.stdout + process.stderr
            assert sentinel not in state.store.db_path.read_bytes()
            assert KEY.encode() not in state.store.db_path.read_bytes()
            assert_originals_and_foreign_jobs_untouched(
                state, originals, output=process.stdout + process.stderr,
            )
        finally:
            state.catalog.close()


def test_cli_invalid_content_keeps_known_usage_and_safe_stage_on_resume(
    tmp_path_factory, loopback_model_server,
):
    loopback_model_server.response_body = json.dumps({
        "model": "stub-model", "choices": [{"message": {"content": "", "reasoning_content": KEY},
                                               "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 73, "completion_tokens": 19},
    }).encode()
    with isolated_batch_directory(tmp_path_factory) as root:
        state = _prepare(root, loopback_model_server.endpoint, one_source=True)
        try:
            originals = _originals(state)
            process, result = _invoke(state)
            assert process.returncode == 2 and result["status"] == "failed"
            assert len(loopback_model_server.requests) == 1 and loopback_model_server.errors == []
            assert result["budget"] == {"tokens": 92, "estimated_micro_usd": 111,
                                        "unknown_reservations": 0, "unsettled_reservations": 0}
            record, = NarrativeRunStore(state.store.db_path).reservations_for_run("cli-e2e")
            assert record.usage_status == "known" and (record.input_tokens, record.output_tokens) == (73, 19)
            assert record.error_code == "MODEL_RESPONSE_INVALID" and record.output_bytes == 0
            attempt = state.store.get_attempt(record.attempt_id)
            assert attempt.error_detail == "metered model attempt did not complete (http_status=200) (response_stage=empty_content)"
            again, repeated = _invoke(state)
            assert again.returncode == 2 and repeated["budget"] == result["budget"]
            assert len(loopback_model_server.requests) == 1
            assert_originals_and_foreign_jobs_untouched(state, originals,
                output=process.stdout + process.stderr + again.stdout + again.stderr)
        finally:
            state.catalog.close()
