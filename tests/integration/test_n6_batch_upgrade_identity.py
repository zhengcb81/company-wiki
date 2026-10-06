"""Actual AUTO batches do not mix generations when selection is upgraded."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from company_wiki.automation.narrative_transport import NarrativeTransportReader
from company_wiki.automation.narrative_transport_contracts import NarrativeReadRequest
from company_wiki.automation.narrative_contracts import SourceRefValue
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from company_wiki.source_catalog.narrative_artifact_store import (
    LocalNarrativeObjectStore, NarrativeArtifactStore,
)
from company_wiki.source_catalog.narrative_evidence import NARRATIVE_SELECTOR_VERSION
from integration import test_narrative_batch_cli_e2e as cli_fixtures
from support import narrative_batch_fixtures as batch_fixtures


loopback_model_server = batch_fixtures.loopback_model_server
protected_inputs = cli_fixtures.r6_protected_inputs
REPO = Path(__file__).resolve().parents[2]


def _upgrade_launcher(root, monkeypatch):
    bootstrap = root / "upgrade-bootstrap"
    bootstrap.mkdir()
    (bootstrap / "sitecustomize.py").write_text('''
import os
from company_wiki.source_catalog import narrative_evidence
from company_wiki.automation import narrative_batch_request, narrative_select
for module in (narrative_evidence, narrative_batch_request, narrative_select):
    module.NARRATIVE_SELECTOR_VERSION = os.environ["CWP_N6_TEST_UPGRADE_VERSION"]
''', encoding="utf-8")
    launcher = root / "upgrade.py"
    launcher.write_text('''
import os
from pathlib import Path
import sys
bootstrap = str(Path(__file__).parent / "upgrade-bootstrap")
sys.path.insert(0, bootstrap)
os.environ["PYTHONPATH"] = bootstrap + os.pathsep + os.environ["PYTHONPATH"]
import sitecustomize
from company_wiki.automation.narrative_batch_cli import main
if __name__ == "__main__":
    args = sys.argv[1:]
    if os.environ.get("CWP_N6_TEST_UPGRADE_WORK_DIR"):
        args[args.index("--work-dir") + 1] = os.environ["CWP_N6_TEST_UPGRADE_WORK_DIR"]
    raise SystemExit(main(args))
''', encoding="utf-8")
    version = NARRATIVE_SELECTOR_VERSION + ".n6-test-next"
    monkeypatch.setenv("CWP_N6_TEST_UPGRADE_VERSION", version)
    return launcher, version


def test_real_batches_keep_old_generation_and_create_separate_upgraded_jobs(
    tmp_path_factory, loopback_model_server, monkeypatch, protected_inputs,
):
    protected_inputs([])
    policies = [source for source in batch_fixtures.source_documents() if source[3] == "ir_policy"]
    assert len(policies) == 1
    monkeypatch.setattr(batch_fixtures, "source_documents", lambda **_kwargs: policies)
    with batch_fixtures.isolated_batch_directory(tmp_path_factory) as root:
        state = cli_fixtures._prepare(root, loopback_model_server.endpoint)
        try:
            originals = cli_fixtures._originals(state)
            first_process, first = cli_fixtures._invoke(state)
            assert first_process.returncode == 0 and first["status"] == "completed"
            assert len(loopback_model_server.requests) == 0 and loopback_model_server.errors == []
            runs = NarrativeRunStore(state.store.db_path)
            old_run = runs.get_run("cli-e2e")
            old_budget = runs.budget_snapshot("cli-e2e")
            assert old_run is not None and len(old_run.job_ids) == 3
            assert old_budget.charged_tokens == old_budget.charged_micro_usd == 0
            old_jobs = tuple(state.store.get_job(job_id) for job_id in old_run.job_ids)
            artifacts = NarrativeArtifactStore(
                state.catalog.store, LocalNarrativeObjectStore(state.catalog.config.catalog_dir),
            )
            transport = NarrativeTransportReader(artifacts, state.reader)
            ref, _language, _kind = next(iter(state.indexed.values()))
            public_ref = SourceRefValue.from_dict(asdict(ref))
            reference = transport.reference(public_ref)
            request = NarrativeReadRequest.from_dict({
                "schema_version": "narrative-read-request/1", "narrative_ref": reference.to_dict(),
                "as_of_date": "2026-10-06", "expected_source": {
                    "canonical_entity_id": "ent-acme", "market": "US", "security_id": "ACME",
                    "document_kind": "investor_relations", "fiscal_year": 2026, "fiscal_period": "Q1",
                },
            })
            old_bytes = transport.read(request).data
            assert json.loads(old_bytes)["versions"]["selector"] == NARRATIVE_SELECTOR_VERSION
            jobs_before = tuple(state.store.list_jobs())
            launcher, upgraded_version = _upgrade_launcher(root, monkeypatch)
            rejected_process, rejected = cli_fixtures._invoke(state, launcher=launcher)
            assert rejected_process.returncode != 0 and rejected["status"] == "failed"
            assert runs.get_run("cli-e2e") == old_run
            assert runs.budget_snapshot("cli-e2e") == old_budget
            assert tuple(state.store.list_jobs()) == jobs_before
            assert transport.read(request).data == old_bytes
            next_request = json.loads(state.request_path.read_text(encoding="utf-8"))
            next_request["run_id"] = "cli-e2e-next"
            state.request_path.write_text(json.dumps(next_request), encoding="utf-8")
            monkeypatch.setenv("CWP_N6_TEST_UPGRADE_WORK_DIR", str(root / "run-work-next"))
            next_process, next_result = cli_fixtures._invoke(
                state, launcher=launcher, expected_run_id="cli-e2e-next",
            )
            assert next_process.returncode == 0 and next_result["status"] == "completed"
            new_run = runs.get_run("cli-e2e-next")
            assert new_run is not None and len(new_run.job_ids) == 3
            assert not set(old_run.job_ids).intersection(new_run.job_ids)
            assert new_run.input_hash != old_run.input_hash
            assert next_result["documents"][0]["artifact_ref"] != first["documents"][0]["artifact_ref"]
            new_reference = transport.reference(public_ref)
            new_read = transport.read(NarrativeReadRequest.from_dict({
                **request.to_dict(), "narrative_ref": new_reference.to_dict(),
            }))
            new_bundle = json.loads(new_read.data)
            assert new_bundle["versions"]["selector"] == upgraded_version
            assert new_bundle["selection"]["status"] == "skipped_no_narrative"
            assert new_bundle["summary"]["status"] == "summary_not_needed"
            assert transport.read(request).data == old_bytes
            assert tuple(state.store.get_job(job_id) for job_id in old_run.job_ids) == old_jobs
            assert runs.get_run("cli-e2e") == old_run and runs.budget_snapshot("cli-e2e") == old_budget
            after_jobs = tuple(state.store.list_jobs())
            repeat_process, repeat = cli_fixtures._invoke(
                state, launcher=launcher, expected_run_id="cli-e2e-next",
            )
            assert repeat_process.returncode == 0 and repeat["documents"] == next_result["documents"]
            assert repeat["budget"] == next_result["budget"] == first["budget"]
            assert tuple(state.store.list_jobs()) == after_jobs
            assert len(loopback_model_server.requests) == 0 and loopback_model_server.errors == []
            batch_fixtures.assert_originals_and_foreign_jobs_untouched(
                state, originals, output=first_process.stdout + rejected_process.stdout
                + next_process.stdout + repeat_process.stdout,
            )
        finally:
            state.catalog.close()
