"""Actual AUTO batches do not mix generations when selection is upgraded."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from company_wiki.automation.narrative_transport import NarrativeTransportReader
from company_wiki.automation.narrative_transport_contracts import NarrativeReadRequest
from company_wiki.automation.narrative_contracts import SourceRefValue
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from company_wiki.source_catalog.narrative_artifact_store import (
    LocalNarrativeObjectStore, NarrativeArtifactStore,
)
from integration import test_narrative_batch_cli_e2e as cli_fixtures
from support import narrative_batch_fixtures as batch_fixtures


loopback_model_server = batch_fixtures.loopback_model_server
protected_inputs = cli_fixtures.r6_protected_inputs
REPO = Path(__file__).resolve().parents[2]


def _upgrade_launcher(root, monkeypatch, version_kind, version):
    bootstrap = root / "upgrade-bootstrap"
    bootstrap.mkdir(exist_ok=True)
    (bootstrap / "sitecustomize.py").write_text('''
import json
import os
from pathlib import Path
import sys
from company_wiki.source_catalog import narrative_evidence
from company_wiki.automation import narrative_batch_request, narrative_select, narrative_formats
kind = os.environ["CWP_N6_TEST_UPGRADE_KIND"]
version = os.environ["CWP_N6_TEST_UPGRADE_VERSION"]
for module in (narrative_evidence, narrative_batch_request, narrative_select):
    setattr(module, "NARRATIVE_" + kind.upper() + "_VERSION", version)
if kind == "parser":
    # Use an actually supported legacy/current parser parameter, including the
    # format identity owner; no fabricated parser callback or version marker.
    narrative_formats.NARRATIVE_PARSER_VERSION = version
    parser = narrative_evidence.parse_pdf_bytes
    parser.__kwdefaults__["parser_version"] = version
    def observed_parse(frame, event, result):
        if frame.f_code is parser.__code__ and event == "return" and result is not None:
            record = {"requested": version, "received": frame.f_locals["parser_version"],
                      "unit_versions": sorted({unit.parser_version for unit in result.units}),
                      "pages_read": result.pages_read, "pages_total": result.page_count}
            with Path(os.environ["CWP_N6_PARSER_TRACE"]).open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record) + "\\n")
    sys.setprofile(observed_parse)
''', encoding="utf-8")
    launcher = root / "upgrade.py"
    launcher.write_text('''
import os
from pathlib import Path
import runpy
import sys
bootstrap = str(Path(__file__).parent / "upgrade-bootstrap")
sys.path.insert(0, bootstrap)
os.environ["PYTHONPATH"] = bootstrap + os.pathsep + os.environ["PYTHONPATH"]
runpy.run_path(str(Path(bootstrap) / "sitecustomize.py"))
from company_wiki.automation.narrative_batch_cli import main
if __name__ == "__main__":
    args = sys.argv[1:]
    if os.environ.get("CWP_N6_TEST_UPGRADE_WORK_DIR"):
        args[args.index("--work-dir") + 1] = os.environ["CWP_N6_TEST_UPGRADE_WORK_DIR"]
    raise SystemExit(main(args))
''', encoding="utf-8")
    monkeypatch.setenv("CWP_N6_TEST_UPGRADE_KIND", version_kind)
    monkeypatch.setenv("CWP_N6_TEST_UPGRADE_VERSION", version)
    monkeypatch.setenv("CWP_N6_PARSER_TRACE", str(root / "actual-parser-calls.jsonl"))
    return launcher, version


@pytest.mark.parametrize("version_kind", ["selector", "parser"])
def test_real_batches_keep_old_generation_and_create_separate_upgraded_jobs(
    tmp_path_factory, loopback_model_server, monkeypatch, protected_inputs, version_kind,
):
    protected_inputs([])
    policies = [source for source in batch_fixtures.source_documents() if source[3] == "ir_policy"]
    assert len(policies) == 1
    monkeypatch.setattr(batch_fixtures, "source_documents", lambda **_kwargs: policies)
    with batch_fixtures.isolated_batch_directory(tmp_path_factory) as root:
        state = cli_fixtures._prepare(root, loopback_model_server.endpoint)
        try:
            originals = cli_fixtures._originals(state)
            old_version, upgraded_version = {
                "selector": ("0.8.0", "0.9.0"),
                "parser": ("0.1.0", "0.1.1"),
            }[version_kind]
            assert all(ref.mime_type == "application/pdf" for ref, _language, _kind in state.indexed.values())
            old_launcher, _ = _upgrade_launcher(root, monkeypatch, version_kind, old_version)
            first_process, first = cli_fixtures._invoke(state, launcher=old_launcher)
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
            assert json.loads(old_bytes)["versions"][version_kind] == old_version
            jobs_before = tuple(state.store.list_jobs())
            launcher, upgraded_version = _upgrade_launcher(root, monkeypatch, version_kind, upgraded_version)
            historical_process, historical = cli_fixtures._invoke(state, launcher=launcher)
            assert historical_process.returncode == 0 and historical["status"] == "completed"
            assert historical["documents"] == first["documents"]
            assert historical["budget"] == first["budget"]
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
            assert new_bundle["versions"][version_kind] == upgraded_version
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
            if version_kind == "parser":
                observations = [json.loads(line) for line in (root / "actual-parser-calls.jsonl").read_text(encoding="utf-8").splitlines()]
                assert {row["received"] for row in observations} == {old_version, upgraded_version}
                assert all(row["received"] == row["requested"] for row in observations)
                assert all(row["unit_versions"] == [row["received"]] for row in observations)
                assert all(row["pages_read"] == row["pages_total"] == 1 for row in observations)
            batch_fixtures.assert_originals_and_foreign_jobs_untouched(
                state, originals, output=first_process.stdout + historical_process.stdout
                + next_process.stdout + repeat_process.stdout,
            )
        finally:
            state.catalog.close()
