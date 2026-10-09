"""ACKed prepared output resumes publication before another run can reuse it."""

from integration.test_narrative_generation_reuse import (
    setup_source,
    request_path,
    invoke,
    public_read,
    record_proof,
    official,
    loopback_model_server as _loopback_fixture,
)
from company_wiki.automation.narrative_run_store import NarrativeRunStore


loopback_model_server = _loopback_fixture


def test_prepared_ack_refuses_new_generation_then_owner_publishes_without_second_post(
    loopback_model_server, monkeypatch
):
    monkeypatch.setenv("DEEPSEEK_API_KEY", official.batch_fixtures.KEY)
    with setup_source(loopback_model_server.endpoint) as (
        root,
        catalog,
        config,
        llm,
        imported,
        kind,
    ):
        launcher = root / "hold-activation.py"
        launcher.write_text(
            """import sys
from company_wiki.source_catalog.narrative_artifact_store import NarrativeArtifactStore
from company_wiki.source_catalog.lock import CatalogOperationLockedError
from narrative_batch_configured import main

def hold(*args, **kwargs):
    print("fixture_activation_held=1", file=sys.stderr)
    raise CatalogOperationLockedError("fixture activation interrupted")
if __name__ == "__main__":
    NarrativeArtifactStore.activate = hold
    raise SystemExit(main())
""",
            encoding="utf-8",
        )
        first_path = request_path(
            root, imported, loopback_model_server.endpoint, "outbox-a"
        )
        process, prepared = invoke(
            root, config, first_path, llm, "outbox-a", launcher=launcher
        )
        assert process.returncode == 2 and prepared["status"] == "partial", prepared
        assert "fixture_activation_held=1" in process.stderr
        assert prepared["documents"][0]["status"] == "activation_pending"
        assert (
            len(loopback_model_server.requests) == 1
            and prepared["budget"]["tokens"] == 92
        )
        row = catalog.reader.fetchone(
            "SELECT status,content_sha256 FROM narrative_artifact_versions"
        )
        assert row["status"] == "prepared"
        old = NarrativeRunStore(root / "AUTO.sqlite").reservations_for_run("outbox-a")
        assert old[0].usage_status == "known" and old[0].output_bytes is None
        next_path = request_path(
            root, imported, loopback_model_server.endpoint, "outbox-b"
        )
        process, refused = invoke(
            root, config, next_path, llm, "outbox-b", database=root / "other.sqlite"
        )
        assert (
            process.returncode == 2
            and refused["error"] == "BATCH_GENERATION_RECOVERY_REQUIRED"
        ), refused
        assert (
            len(loopback_model_server.requests) == 1
            and not (root / "other.sqlite").exists()
        )
        process, completed = invoke(root, config, first_path, llm, "outbox-a")
        assert process.returncode == 0 and completed["status"] == "completed", completed
        assert len(loopback_model_server.requests) == 1
        settled = NarrativeRunStore(root / "AUTO.sqlite").reservations_for_run(
            "outbox-a"
        )
        assert (
            settled[0].usage_status == "known"
            and settled[0].charged_tokens == old[0].charged_tokens
        )
        assert (
            settled[0].output_bytes
            == completed["documents"][0]["artifact_ref"]["byte_size"]
        )
        process, reused = invoke(
            root, config, next_path, llm, "outbox-b", database=root / "other.sqlite"
        )
        assert process.returncode == 0 and reused["status"] == "completed", reused
        assert (
            reused["documents"][0]["artifact_ref"]
            == completed["documents"][0]["artifact_ref"]
        )
        assert (
            reused["budget"]["tokens"] == reused["budget"]["estimated_micro_usd"] == 0
        )
        assert (
            len(loopback_model_server.requests) == 1
            and not loopback_model_server.errors
        )
        _, _, receipt = public_read(root, config, imported, kind)
        record_proof(
            "prepared-outbox-recovery",
            loopback_model_server,
            completed,
            receipt,
            extra={"initial_receipt": prepared, "other_db_refusal": refused},
        )
        record_proof(
            "prepared-outbox-other-db-reuse", loopback_model_server, reused, receipt
        )
