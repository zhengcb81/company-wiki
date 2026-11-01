"""Generation ownership follows execution, with billed-response reuse preserved."""

from dataclasses import asdict

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


def test_terminal_http_rejection_allows_explicit_new_run_and_keeps_old_unknown_hold(
    loopback_model_server, monkeypatch,
):
    monkeypatch.setenv("DEEPSEEK_API_KEY", official.batch_fixtures.KEY)
    with setup_source(loopback_model_server.endpoint) as (
        root, catalog, config, llm, imported, kind,
    ):
        loopback_model_server.response_status = 401
        first_path = request_path(root, imported, loopback_model_server.endpoint, "rejected")
        process, first = invoke(root, config, first_path, llm, "rejected")
        assert process.returncode == 2 and first["status"] != "completed", first
        assert len(loopback_model_server.requests) == 1, (first, process.stderr)
        ledger = NarrativeRunStore(root / "AUTO.sqlite")
        old = tuple(asdict(row) for row in ledger.reservations_for_run("rejected"))
        assert len(old) == 1 and old[0]["usage_status"] == "unknown"
        assert old[0]["paid_response_json"] is None and old[0]["output_bytes"] == 0
        assert first["budget"]["unknown_reservations"] == 1
        loopback_model_server.response_status = 200
        next_path = request_path(root, imported, loopback_model_server.endpoint, "corrected")
        process, completed = invoke(root, config, next_path, llm, "corrected")
        assert process.returncode == 0 and completed["status"] == "completed", completed
        assert len(loopback_model_server.requests) == 2
        assert tuple(asdict(row) for row in ledger.reservations_for_run("rejected")) == old
        assert ledger.budget_snapshot("rejected").charged_tokens == first["budget"]["tokens"]
        assert ledger.budget_snapshot("rejected").charged_micro_usd == first["budget"]["estimated_micro_usd"]
        _, _, receipt = public_read(root, config, imported, kind)
        assert receipt["replay_status"] == "verified"
        process, cached = invoke(root, config, next_path, llm, "corrected")
        assert process.returncode == 0 and cached["status"] == "completed"
        assert len(loopback_model_server.requests) == 2 and not loopback_model_server.errors


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


def test_published_unknown_usage_reuses_artifact_without_refund_or_another_post(
    loopback_model_server, monkeypatch,
):
    from company_wiki.automation.narrative_batch import _generation_owner_finished

    monkeypatch.setenv("DEEPSEEK_API_KEY", official.batch_fixtures.KEY)
    loopback_model_server.response_usage = {}
    with setup_source(loopback_model_server.endpoint) as (
        root, catalog, config, llm, imported, kind,
    ):
        first_path = request_path(root, imported, loopback_model_server.endpoint, "unknown-published")
        process, first = invoke(root, config, first_path, llm, "unknown-published")
        assert process.returncode == 0 and first["status"] == "completed", first
        ledger = NarrativeRunStore(root / "AUTO.sqlite")
        old = tuple(asdict(row) for row in ledger.reservations_for_run("unknown-published"))
        assert len(old) == 1 and old[0]["usage_status"] == "unknown"
        # This legacy generative fixture has no paid-response pin; output and
        # actual publication still prove successful reuse despite unknown usage.
        assert old[0]["output_bytes"] > 0 and old[0]["output_sha256"] is not None
        assert _generation_owner_finished(root / "AUTO.sqlite", "unknown-published")
        next_path = request_path(root, imported, loopback_model_server.endpoint, "unknown-reuse")
        process, reused = invoke(root, config, next_path, llm, "unknown-reuse")
        assert process.returncode == 0 and reused["status"] == "completed", reused
        assert reused["documents"][0]["artifact_ref"] == first["documents"][0]["artifact_ref"]
        assert reused["budget"]["tokens"] == reused["budget"]["estimated_micro_usd"] == 0
        assert tuple(asdict(row) for row in ledger.reservations_for_run("unknown-published")) == old
        assert len(loopback_model_server.requests) == 1 and not loopback_model_server.errors
