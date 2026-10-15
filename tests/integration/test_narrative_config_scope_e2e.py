"""Actual configured CLI must not rely on pytest's implicit loose config."""
from dataclasses import asdict
import json

from integration import test_narrative_generation_reuse as reuse
from integration import test_shared_reading_production_e2e as production
from company_wiki.automation.narrative_run_store import NarrativeRunStore

loopback_model_server = reuse.loopback_model_server


def test_configured_summary_and_restart_without_unconsumed_config(
    loopback_model_server, monkeypatch,
):
    server = loopback_model_server
    for name in ("PYTEST_CURRENT_TEST", "TAVILY_API_KEY", "WIKI_ROOT"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", reuse.official.batch_fixtures.KEY)
    with reuse.setup_source(server.endpoint) as (root, catalog, config, llm, imported, kind):
        with llm.open("a", encoding="utf8") as stream:
            stream.write("\npaths:\n  wiki_root: " + json.dumps(str(root / "missing-unused-wiki")) + "\n")
        assert not (root / "missing-unused-wiki").exists()
        protected = production._protected(root, config, llm)
        request = reuse.request_path(root, imported, server.endpoint, "strict-config", selector_version="0.9.0")
        process, receipt = reuse.invoke(root, config, request, llm, "strict-config")
        assert process.returncode == 0 and receipt["status"] == "completed", receipt
        assert len(server.requests) == 1 and not server.errors
        reference, bundle, replay = reuse.public_read(root, config, imported, kind)
        assert replay["replay_status"] == "verified"
        assert bundle["reading_context"]["schema_version"] == "du-production-reading/2"
        runs = NarrativeRunStore(root / "AUTO.sqlite")
        before = tuple(asdict(item) for item in runs.reservations_for_run("strict-config"))
        process, resumed = reuse.invoke(root, config, request, llm, "strict-config")
        assert process.returncode == 0 and resumed["status"] == "completed"
        assert resumed["documents"] == receipt["documents"]
        assert resumed["budget"] == receipt["budget"]
        assert len(server.requests) == 1
        assert tuple(asdict(item) for item in runs.reservations_for_run("strict-config")) == before
        published = receipt["documents"][0]["artifact_ref"]
        assert reference["artifact_version_id"] == published["artifact_version_id"]
        assert reference["artifact_sha256"] == published["content_sha256"]
        assert reference["byte_size"] == published["byte_size"]
        production._assert_protected(root, protected)
    assert not root.exists()
