"""Real finite batch recovers paid bytes after a test-only decoder fault."""

from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path

from company_wiki.automation import narrative_batch as batch
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from company_wiki.automation.store import AutomationStore
from company_wiki.automation.supervisor import AutomationSupervisor
from integration.test_narrative_legacy_effort_history import _request, _database_dump
from support import narrative_batch_fixtures as fixtures
from support.narrative_batch_fixtures import (
    isolated_batch_directory,
    prepare_source_catalog,
    loopback_model_server as _loopback_model_server,
)

loopback_model_server = _loopback_model_server


class Du11FaultSupervisor(AutomationSupervisor):
    """Substitute only test worker factory; real spawn/leases/store remain."""

    def __init__(self, config):
        super().__init__(
            replace(
                config,
                runtime_factory_path="unit.du11_paid_response.du11_fault_runtime:create_runtime",
            )
        )


def database_bytes(path):
    # SHM readmarks are transient. Missing and empty WAL both carry zero DB
    # bytes; SQLite readonly opens can create that empty sidecar. Main DB and
    # every nonempty WAL byte remain exact, without normalizing their content.
    wal = Path(str(path) + "-wal")
    return {
        str(path): path.read_bytes(),
        str(wal): wal.read_bytes() if wal.exists() else b"",
    }


def test_real_batch_recovers_paid_response_without_key_resend_or_duplicate_fee(
    tmp_path_factory,
    loopback_model_server,
    monkeypatch,
):
    def rank_reply(data):
        assert data["schema_version"] == "narrative-model-request/6"
        return {"decisions": []}

    monkeypatch.setattr(fixtures, "response_draft", rank_reply)
    monkeypatch.setattr(batch, "AutomationSupervisor", Du11FaultSupervisor)
    expected_owner = (
        Path(__file__).resolve().parents[3]
        / "src/company_wiki/automation/narrative_batch.py"
    )
    assert Path(batch.__file__).resolve() == expected_owner
    with isolated_batch_directory(tmp_path_factory) as root:
        state = prepare_source_catalog(root, one_source=True, include_policy=False)
        marker = root / "du11-fail-envelope-on-purpose"
        marker.write_text("test decoder fault, not a production flag", encoding="utf8")
        protected = {p: p.read_bytes() for p in state.raw_paths.values()}
        try:
            request, _ = _request(state, loopback_model_server.endpoint, "1")
            request = replace(request, selector_version="0.9.0", max_seconds=60)
            kwargs = dict(
                project_root=root,
                catalog_config_path=state.config_path,
                db_path=root / "automation.db",
                work_dir=root / "work",
            )
            failed = batch.run_batch(request, **kwargs)
            store = AutomationStore(root / "automation.db")
            jobs = store.list_jobs()
            summary = next(
                j for j in jobs if j.job_type == "source.narrative_summarize"
            )
            original_attempts = store.list_attempts(summary.job_id)
            assert failed["status"] == "failed", (
                failed,
                [(j.job_type, j.last_error_code) for j in jobs],
            )
            assert len(original_attempts) == 1 and original_attempts[0].result_json
            assert (
                len(loopback_model_server.requests) == 1
                and not loopback_model_server.errors
            )
            runs = NarrativeRunStore(root / "automation.db")
            original = runs.reservations_for_run(request.run_id)
            assert (
                len(original) == 1
                and original[0].paid_response_json
                and original[0].output_bytes == 0
            )
            paid_id = original[0].attempt_id
            pin = json.loads(original[0].paid_response_json)
            body = state.catalog.config.catalog_dir / pin["object_key"]
            assert len(body.read_bytes()) == pin["byte_size"]
            assert hashlib.sha256(body.read_bytes()).hexdigest() == pin["body_sha256"]
            old_attempt_dict = asdict(original_attempts[0])
            frozen_run = runs.get_run(request.run_id)
            marker.unlink()
            monkeypatch.delenv(fixtures.KEY_ENV)
            resumed = batch.run_batch(request, **kwargs)
            assert resumed["status"] == "completed", (
                resumed,
                [
                    (j.job_type, j.last_error_code, j.last_error_detail)
                    for j in store.list_jobs()
                ],
            )
            assert (
                len(loopback_model_server.requests) == 1
                and not loopback_model_server.errors
            )
            after = runs.reservations_for_run(request.run_id)
            assert len(after) == 1 and after[0].attempt_id == paid_id
            assert after[0].usage_status == "known" and after[0].charged_tokens == 92
            assert after[0].charged_micro_usd == 111
            assert after[0].output_bytes > 0 and after[0].output_sha256
            assert after[0].paid_response_json == original[0].paid_response_json
            assert runs.get_run(request.run_id).binding_json == frozen_run.binding_json
            attempts = store.list_attempts(summary.job_id)
            assert len(attempts) == 2 and attempts[-1].outcome.value == "succeeded"
            # Compaction can replace verbose result_json with a terminal pin,
            # but the old failed attempt/identity/error/charge is not deleted.
            old_after = store.get_attempt(paid_id)
            assert old_after and old_after.attempt_id == old_attempt_dict["attempt_id"]
            assert old_after.outcome == original_attempts[0].outcome
            assert old_after.error_code == original_attempts[0].error_code
            assert old_after.finished_at == original_attempts[0].finished_at
            assert old_after.result_json
            before_auto = database_bytes(root / "automation.db")
            before_catalog = database_bytes(state.catalog.config.database_path)
            logical_before = _database_dump(root / "automation.db")
            read = batch.run_batch(request, **kwargs)
            assert (
                read["status"] == "completed"
                and read["documents"] == resumed["documents"]
            )
            assert read["budget"] == resumed["budget"]
            assert database_bytes(root / "automation.db") == before_auto
            assert database_bytes(state.catalog.config.database_path) == before_catalog
            assert _database_dump(root / "automation.db") == logical_before
            assert len(loopback_model_server.requests) == 1
            assert {p: p.read_bytes() for p in protected} == protected
        finally:
            state.catalog.close()
