"""Actual native JSON and immutable historical selector generation."""
from __future__ import annotations

from copy import deepcopy
from functools import partial
import json

import pytest

from company_wiki.automation.models import HandlerOutcome
from company_wiki.automation.narrative_contracts import NarrativeSelectResult
from company_wiki.automation.narrative_select import NarrativeSelectHandler
from company_wiki.automation.narrative_verify import NarrativeVerifyHandler
from company_wiki.automation.narrative_summarize import NarrativeSummarizeHandler
from company_wiki.automation.narrative_official_json import open_verified_projection, select_verified_projection
from company_wiki.automation import narrative_batch as batch
from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
from company_wiki.automation.narrative_generation import generation_sha256, find_reuse_pin
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from company_wiki.source_catalog import narrative_evidence as policy
from company_wiki.source_catalog.narrative_artifact_store import NarrativeArtifactReader, LocalNarrativeObjectStore
from integration import test_official_json_verify_handler as official
from integration import test_narrative_legacy_effort_history as history
from support.narrative_batch_fixtures import isolated_batch_directory, prepare_source_catalog

loopback_model_server = history.loopback_model_server
NATIVE = "行业出口许可政策近期收紧，出口审批周期延长。"
QUESTION = "传闻海外项目已经获得20个客户订单，是否属实？"


@pytest.mark.parametrize("version", ["0.6.0", "0.7.0"])
def test_official_actual_version_keeps_native_parent_roles_whitespace_partial_and_replays(tmp_path, version):
    with official.owned_catalog(tmp_path) as (catalog, _root):
        page = official.flat_page(1)
        page["result"].update(page_count=3, item_total=3)
        page["result"]["items"][0]["a"] = "公司主营业务的新产品已完成客户验证并开始商业化交付。"
        page["result"]["items"][0]["q"] = QUESTION
        second = official.flat_page(2)
        second["result"].update(page_count=3, item_total=3)
        second["result"]["items"][0]["a"] = "\t  " + NATIVE + "\r\n"
        second["result"]["items"][0]["q"] = "哪些行业政策最近发生变化？"
        ref, original = official.import_page(catalog, page)
        ref2, original2 = official.import_page(catalog, second)
        projection = official.persist(catalog, [ref, ref2])  # page 3 deliberately missing => partial
        handler = NarrativeSelectHandler(reader=official.NoRawReader(), projection_catalog=catalog, selector_version=version)
        selected = handler(official.make_context(projection, language="zh"))
        assert selected.outcome is HandlerOutcome.SUCCEEDED, selected.error
        assert selected.result["selector"]["version"] == version
        view = open_verified_projection(catalog, projection_id=projection.projection_id,
            expected_projection_sha256=projection.projection_sha256)
        expected = select_verified_projection(view, title="owned official projection",
            selector=partial(policy.select_narrative_evidence, selector_version=version), selector_version=version)
        assert NarrativeSelectResult.from_dict(selected.result).to_dict()["evidence_spans"] == [span.to_dict() for span in expected.evidence_spans]
        joined = "".join(span["raw_text"] for span in selected.result["evidence_spans"])
        assert (NATIVE in joined) is (version == "0.7.0")
        if version == "0.7.0":
            assert any(span["raw_text"].startswith("\t  ") for span in selected.result["evidence_spans"])
        assert selected.result["selection"]["coverage_complete"] is False
        dependencies = {"source.narrative_select": selected}
        summarized = NarrativeSummarizeHandler(model=official.OfflineProjectionModel())(
            official.make_context(projection, language="zh", job_type="source.narrative_summarize", dependencies=dependencies))
        assert summarized.outcome is HandlerOutcome.SUCCEEDED, summarized.error
        dependencies["source.narrative_summarize"] = summarized
        verified = NarrativeVerifyHandler(reader=official.NoRawReader(), projection_catalog=catalog,
            generation_sha256=lambda _subject: official.GENERATION, selector_version=version)(
            official.make_context(projection, language="zh", job_type="source.narrative_verify", dependencies=dependencies))
        assert verified.outcome is HandlerOutcome.SUCCEEDED, verified.error
        assert verified.result["versions"]["selector"] == version
        assert verified.result["evidence_spans"] == selected.result["evidence_spans"]
        assert official.SourceVersionReader(catalog).open_version(ref).data == original
        assert official.SourceVersionReader(catalog).open_version(ref2).data == original2


def test_complete_empty_projection_does_not_bypass_unknown_version(tmp_path):
    with official.owned_catalog(tmp_path) as (catalog, _root):
        page = official.flat_page(1)
        page["result"].update(item_total=1, page_count=1)
        page["result"]["items"][0].update(a="", q="")
        ref, _ = official.import_page(catalog, page)
        projection = official.persist(catalog, [ref])
        view = open_verified_projection(catalog, projection_id=projection.projection_id,
            expected_projection_sha256=projection.projection_sha256)
        assert view.language is None
        assert all(not (span.raw_text or "").strip() for span in view.evidence_spans)
        with pytest.raises(policy.NarrativeSelectorVersionError):
            select_verified_projection(view, title="empty", selector_version="unknown-policy")
        valid = select_verified_projection(view, title="empty", selector_version="0.7.0")
        assert valid.status == "skipped_no_narrative" and valid.coverage_complete


@pytest.mark.parametrize("schema", ["1", "2"])
def test_actual_finished_06_history_readonly_and_new07_cannot_reuse_old_generation(
    tmp_path_factory, loopback_model_server, monkeypatch, schema,
):
    with isolated_batch_directory(tmp_path_factory) as root:
        state = prepare_source_catalog(root, one_source=True, include_policy=False)
        try:
            from company_wiki.automation import narrative_batch_request as request_module
            monkeypatch.setattr(policy, "NARRATIVE_SELECTOR_VERSION", "0.6.0")
            monkeypatch.setattr(request_module, "NARRATIVE_SELECTOR_VERSION", "0.6.0")
            request, wire = history._request(state, loopback_model_server.endpoint, schema)
            assert request.execution_versions["selector"] == "0.6.0"
            first = batch.run_batch(request, project_root=root, catalog_config_path=state.config_path,
                db_path=root/"automation.db", work_dir=root/"work")
            assert first["status"] == "completed", first
            runs = NarrativeRunStore(root/"automation.db")
            old_run = runs.get_run(request.run_id)
            frozen = json.loads(old_run.binding_json)
            assert frozen["execution_versions"]["selector"] == "0.6.0"
            original_files = {path: path.read_bytes() for path in state.raw_paths.values()}
            before_auto = history._database_dump(root/"automation.db")
            before_catalog = history._database_dump(state.catalog.config.database_path)
            call_count = len(loopback_model_server.requests)
            # Installed default changes, while frozen execution remains unchanged.
            monkeypatch.setattr(policy, "NARRATIVE_SELECTOR_VERSION", "0.7.0")
            monkeypatch.setattr(request_module, "NARRATIVE_SELECTOR_VERSION", "0.7.0")
            resumed = batch.run_batch(request, project_root=root, catalog_config_path=state.config_path,
                db_path=root/"automation.db", work_dir=root/"work")
            container = "documents" if schema == "1" else "items"
            assert resumed[container] == first[container]
            assert resumed["status"] == first["status"]
            assert resumed["budget"] == first["budget"]
            assert len(loopback_model_server.requests) == call_count
            assert history._database_dump(root/"automation.db") == before_auto
            assert history._database_dump(state.catalog.config.database_path) == before_catalog
            assert {path: path.read_bytes() for path in original_files} == original_files
            new_wire = deepcopy(wire)
            new_wire["run_id"] = "new-policy-" + schema
            new_request = NarrativeBatchRequest.from_dict(new_wire)
            payload, facts = batch._current_sources(new_request, state.reader)
            new_manifest = batch.generation_manifest(new_request, payload[0], execution_versions=batch._execution_versions(new_request))
            old_manifest = next(iter(batch._thaw_generations(frozen).values()))
            assert new_manifest["execution_versions"]["selector"] == "0.7.0"
            assert generation_sha256(old_manifest) != generation_sha256(new_manifest)
            artifacts = NarrativeArtifactReader(state.catalog.config.database_path,
                LocalNarrativeObjectStore(state.catalog.config.catalog_dir))
            try:
                assert find_reuse_pin(artifacts, state.reader, payload[0], new_manifest, facts[0]) is None
            finally:
                artifacts.close()
            # A nonterminal old run must still fail typed instead of silently restarting.
            from contextlib import closing
            import sqlite3
            with closing(sqlite3.connect(root/"automation.db")) as conn, conn:
                conn.execute("UPDATE jobs SET status='ready' WHERE job_type='source.narrative_summarize'")
            try:
                with pytest.raises(batch.BatchResumeError, match="BATCH_EXECUTION_VERSION_UNAVAILABLE_NEW_RUN_REQUIRED"):
                    batch.run_batch(request, project_root=root, catalog_config_path=state.config_path,
                        db_path=root/"automation.db", work_dir=root/"work")
                assert len(loopback_model_server.requests) == call_count
            finally:
                with closing(sqlite3.connect(root/"automation.db")) as conn, conn:
                    conn.execute("UPDATE jobs SET status='succeeded' WHERE job_type='source.narrative_summarize'")
        finally:
            state.catalog.close()
