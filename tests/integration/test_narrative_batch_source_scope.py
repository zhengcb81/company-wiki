"""A completed public CLI run can relocate without rework or ledger changes."""

from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3

import pytest

from company_wiki.automation.models import canonical_json
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from support import narrative_batch_fixtures as fixtures

from .test_narrative_batch_cli_e2e import _invoke, _originals, _prepare
from .test_narrative_batch_cli_e2e import r6_protected_inputs as _protected_inputs_fixture
from .test_narrative_batch_budget_and_resume import _dump


loopback_model_server = fixtures.loopback_model_server
r6_protected_inputs = _protected_inputs_fixture


@pytest.mark.parametrize("real_source", [False, pytest.param(
    True, marks=[pytest.mark.real_data, pytest.mark.e2e], id="real-txt")])
def test_completed_cli_has_source_scoped_binding_and_relocates_without_rework(
    tmp_path_factory, loopback_model_server, monkeypatch, real_source, r6_protected_inputs,
):
    if real_source:
        source = os.environ.get("CWP_E2E_TRANSCRIPT_PATH")
        if not source:
            pytest.skip("requires an explicit read-only transcript input")
        original_path = Path(source)
        original = original_path.read_bytes()
        r6_protected_inputs([original_path])
        # Actual original bytes with isolated Acme identity and loopback model.
        # This tests storage/recovery, not production MSFT metadata or quality.
        monkeypatch.setattr(fixtures, "source_documents", lambda **_kwargs: [
            ("en", "real-body.txt", "Isolated real transcript bytes", "investor_call_transcript", original),
        ])
    with fixtures.isolated_batch_directory(tmp_path_factory) as root:
        state = _prepare(root, loopback_model_server.endpoint, one_source=True)
        try:
            originals = _originals(state)
            process, first = _invoke(state)
            assert process.returncode == 0 and first["status"] == "completed", first
            assert len(loopback_model_server.requests) == 1
            run = NarrativeRunStore(state.store.db_path).get_run("cli-e2e")
            assert run is not None
            frozen = json.loads(run.binding_json)
            assert frozen["schema_version"] == "narrative-run-binding/3"
            assert frozen["read_policy_schema_version"] == "3.0"
            assert set(frozen["source_read_policies"]) == set(state.indexed)
            auto_before = _dump(state.store.db_path)
            catalog_before = _dump(state.catalog.config.database_path)
            baseline = (root / "run-work/storage-baseline.json").read_bytes()
            object_root = root / "catalog/objects"
            objects = {p.relative_to(object_root): p.read_bytes()
                       for p in object_root.rglob("*") if p.is_file()}
            state.catalog.close()

            config = json.loads(state.config_path.read_text(encoding="utf-8"))
            config["roots"].append({"root_id": "unrelated", "path": "other-documents",
                                   "kind": "directory", "adapter_id": "sidecar_filing_v1"})
            state.config_path.write_text(canonical_json(config), encoding="utf-8")

            def resumed_without_work():
                call, receipt = _invoke(state)
                assert call.returncode == 0 and receipt["status"] == "completed", receipt
                assert receipt["documents"] == first["documents"]
                assert receipt["budget"] == first["budget"]
                assert _dump(state.store.db_path) == auto_before
                assert len(loopback_model_server.requests) == 1
                assert (root / "run-work/storage-baseline.json").read_bytes() == baseline

            resumed_without_work()
            assert _dump(root / "catalog/catalog.sqlite3") == catalog_before
            (root / "catalog").rename(root / "relocated-catalog")
            config["catalog_dir"] = "relocated-catalog"
            (root / "companies").rename(root / "relocated-companies")
            config["roots"][0]["path"] = "relocated-companies"
            state.config_path.write_text(canonical_json(config), encoding="utf-8")
            resumed_without_work()
            assert _dump(root / "relocated-catalog/catalog.sqlite3") == catalog_before
            assert {p.relative_to(root / "relocated-catalog/objects"): p.read_bytes()
                    for p in (root / "relocated-catalog/objects").rglob("*") if p.is_file()} == objects

            def refused(code):
                call, receipt = _invoke(state)
                assert call.returncode == 2 and receipt["error"] == code, receipt
                assert _dump(state.store.db_path) == auto_before
                assert len(loopback_model_server.requests) == 1

            config["roots"][0]["max_file_size"] = max(ref.byte_size for ref, *_ in state.indexed.values()) + 4096
            state.config_path.write_text(canonical_json(config), encoding="utf-8")
            resumed_without_work()
            config["roots"][0]["max_file_size"] = 1
            state.config_path.write_text(canonical_json(config), encoding="utf-8")
            refused("root_admission_denied")
            config["roots"][0].pop("max_file_size")
            state.config_path.write_text(canonical_json(config), encoding="utf-8")
            relocated_originals = {root / "relocated-companies" / p.relative_to(root / "companies"): b
                                   for p, b in originals.items()}
            path, body = next(iter(relocated_originals.items()))
            path.write_bytes(b"X" + body[1:])
            refused("no_verified_location")
            path.write_bytes(body)
            # Invalid source membership is not repaired by a new policy map.
            with closing(sqlite3.connect(state.store.db_path, isolation_level=None)) as connection:
                connection.execute("UPDATE narrative_runs SET binding_json=? WHERE run_id=?",
                    (canonical_json({**frozen, "source_read_policies": {}}), run.run_id))
            corrupted = _dump(state.store.db_path)
            call, receipt = _invoke(state)
            assert call.returncode == 2 and receipt["error"] == "BATCH_FROZEN_BINDING_INVALID", receipt
            assert _dump(state.store.db_path) == corrupted
            assert len(loopback_model_server.requests) == 1
            assert {p: p.read_bytes() for p in relocated_originals} == relocated_originals
            assert not loopback_model_server.errors
        finally:
            state.catalog.close()


def test_completed_batch_resumes_after_auxiliary_metadata_and_permissive_limit_change(
    tmp_path_factory, loopback_model_server, r6_protected_inputs,
):
    with fixtures.isolated_batch_directory(tmp_path_factory) as root:
        state = _prepare(root, loopback_model_server.endpoint, one_source=True)
        try:
            call, first = _invoke(state)
            assert call.returncode == 0 and first['status'] == 'completed', first
            before = _dump(state.store.db_path)
            run = NarrativeRunStore(state.store.db_path).get_run('cli-e2e')
            original_binding = run.binding_json
            source = next(iter(state.indexed.values()))[0]
            with closing(sqlite3.connect(state.catalog.config.database_path)) as connection:
                row = connection.execute('SELECT metadata_json FROM documents WHERE document_id=?',
                                         (source.document_id,)).fetchone()
                metadata = json.loads(row[0])
                metadata['acquisition']['source_title'] = 'Corrected display title'
                metadata['acquisition']['language'] = 'zh'
                connection.execute('UPDATE documents SET metadata_json=? WHERE document_id=?',
                                   (json.dumps(metadata), source.document_id))
            config = json.loads(state.config_path.read_text(encoding='utf-8'))
            config['roots'][0]['max_file_size'] = source.byte_size + 4096
            state.config_path.write_text(canonical_json(config), encoding='utf-8')
            call, second = _invoke(state)
            assert call.returncode == 0 and second['status'] == 'completed', second
            assert second['documents'] == first['documents']
            assert second['budget'] == first['budget']
            assert len(loopback_model_server.requests) == 1
            assert _dump(state.store.db_path) == before
            assert NarrativeRunStore(state.store.db_path).get_run('cli-e2e').binding_json == original_binding
        finally:
            state.catalog.close()
