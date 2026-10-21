"""Behaviour controls for complete paid bytes, not a response cache."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from company_wiki.automation.models import (
    Event,
    Job,
    JobStatus,
    RiskClass,
    RuntimeState,
    make_job_key,
)
from company_wiki.automation.narrative_http_model import NarrativeHTTPModel
from company_wiki.automation.narrative_model import NarrativeModelRequest
from company_wiki.automation.narrative_model_caller import (
    BudgetedNarrativeCaller,
    NarrativeBudgetCallError,
)
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from company_wiki.automation.store import AutomationStore
from company_wiki.source_catalog.narrative_artifact_store import (
    LocalNarrativeObjectStore,
)

T0, T1, T2 = "2026-10-18T10:00:00Z", "2026-10-18T10:01:00Z", "2026-10-18T10:09:00Z"
REQUEST = NarrativeModelRequest("prompt/1", "data only", "{}", "a" * 64)
BODY = json.dumps(
    {
        "model": "model",
        "choices": [
            {"message": {"content": "not valid summary JSON"}, "finish_reason": "stop"}
        ],
        "usage": {"prompt_tokens": 73, "completion_tokens": 19},
    },
    separators=(",", ":"),
).encode()


@pytest.fixture
def http(monkeypatch):
    """Real adapter path, synthetic transport only; never opens a socket."""
    state = SimpleNamespace(body=BODY, declared=None, calls=0)

    class Response:
        status = 200

        def __init__(self):
            self.closed = False

        def getheader(self, name):
            return (
                str(state.declared if state.declared is not None else len(state.body))
                if name == "Content-Length"
                else None
            )

        def isclosed(self):
            return self.closed

        def read1(self, n):
            self.closed = True
            return state.body[:n]

    class Connection:
        sock = None

        def __init__(self, *args, **kwargs):
            pass

        def request(self, *args, **kwargs):
            state.calls += 1

        def getresponse(self):
            return Response()

        def close(self):
            pass

    monkeypatch.setattr("http.client.HTTPConnection", Connection)
    monkeypatch.setenv("DU11_SYNTHETIC_KEY", "synthetic-test-value")
    state.model = NarrativeHTTPModel(
        endpoint="http://127.0.0.1/v1/chat/completions",
        allow_local_http=True,
        model_id="model",
        api_key_env="DU11_SYNTHETIC_KEY",
        max_output_tokens=256,
    )
    return state


def seed_owned(tmp_path, http, *, dependent=False):
    auto = AutomationStore(tmp_path / "auto.db")
    event = Event(
        "event",
        "source.revision_registered",
        "source_revision",
        "item",
        "b" * 64,
        "{}",
        "p",
        T0,
        T0,
    )
    auto.put_event(event)
    job = Job(
        "job",
        make_job_key(
            "source.narrative_summarize", "source_revision", "item", "b" * 64, "p", "1"
        ),
        "source.narrative_summarize",
        "source_revision",
        "item",
        "b" * 64,
        "p",
        "1",
        RiskClass.LOW,
        JobStatus.READY,
        10,
        T0,
        5,
        "event",
        T0,
        T0,
        None,
        None,
    )
    auto.put_job(job)
    generation = auto.set_runtime_gate(
        RuntimeState.ENABLED, updated_at=T0
    ).control_generation
    job_ids = ("job",)
    if dependent:
        verify = replace(
            job, job_id="verify", job_type="source.narrative_verify",
            job_key=make_job_key("source.narrative_verify", "source_revision", "item", "b" * 64, "p", "1"),
            status=JobStatus.DEAD_LETTER, last_error_code="DEPENDENCY_TERMINAL",
            last_error_detail="summary failed",
        )
        auto.put_job(verify)
        auto.add_job_dependency("verify", "job")
        job_ids += ("verify",)
    runs = NarrativeRunStore(auto.db_path)
    runs.create_run(
        run_id="run",
        input_hash="c" * 64,
        job_ids=job_ids,
        model_id="model",
        prompt_version="prompt/1",
        pricing_version="price/1",
        input_micro_usd_per_million_tokens=300000,
        output_micro_usd_per_million_tokens=1200000,
        max_tokens=100000,
        max_micro_usd=100000,
        max_output_bytes=2 * 1024 * 1024,
        created_at=T0,
    )
    claimed = auto.claim_next_ready(
        worker_id="worker",
        attempt_id="paid",
        lease_token="lease",
        now=T1,
        lease_until=T2,
        expected_generation=generation,
        allowed_job_ids=("job",),
    )

    def context(claim=claimed):
        return SimpleNamespace(
            job=claim.job, attempt=claim.attempt, checkpoint=lambda: None
        )

    return SimpleNamespace(
        auto=auto,
        runs=runs,
        context=context,
        claim=claimed,
        http=http,
        objects=LocalNarrativeObjectStore(tmp_path / "objects"),
        generation=generation,
    )


@pytest.fixture
def owned(tmp_path, http):
    return seed_owned(tmp_path, http)


def caller(owned, **kwargs):
    from company_wiki.automation.narrative_paid_response import PaidResponseArtifacts

    return BudgetedNarrativeCaller(
        store=owned.runs,
        run_id="run",
        model=owned.http.model,
        paid_responses=PaidResponseArtifacts(owned.objects, max_response_bytes=262144),
        clock=lambda: T1,
        **kwargs,
    )


def test_modules_are_owned_worktree_not_editable_main():
    from company_wiki.automation import narrative_model_caller

    assert (
        Path(narrative_model_caller.__file__).resolve()
        == Path(__file__).resolve().parents[3]
        / "src/company_wiki/automation/narrative_model_caller.py"
    )


def test_complete_body_is_captured_before_any_envelope_decode(http, monkeypatch):
    captured = []

    def crash(*args, **kwargs):
        raise SystemExit("decode interrupted")

    monkeypatch.setattr(http.model, "_response", crash)
    with pytest.raises(SystemExit):
        http.model.generate(
            REQUEST,
            response_sink=lambda body, **metadata: captured.append((body, metadata)),
        )
    assert captured[0][0] == BODY
    assert captured[0][1]["http_status"] == 200
    assert type(captured[0][1]["duration_ms"]) is int
    assert http.calls == 1


def test_incomplete_declared_body_is_not_captured(http):
    http.declared = len(BODY) + 10
    captured = []
    with pytest.raises(Exception):
        http.model.generate(
            REQUEST, response_sink=lambda body, **meta: captured.append(body)
        )
    assert not captured


def test_saved_body_replay_uses_original_elapsed_metadata_and_no_post(http):
    result = http.model.replay_response(REQUEST, BODY, http_status=200, duration_ms=123)
    assert result.response_bytes == b"not valid summary JSON"
    assert result.duration_ms == 123 and http.calls == 0
    assert result.response_sha256 != hashlib.sha256(BODY).hexdigest()


def test_crash_before_envelope_then_reopen_replays_same_paid_attempt(
    owned, monkeypatch
):
    original = owned.http.model._response
    monkeypatch.setattr(
        owned.http.model,
        "_response",
        lambda *a, **k: (_ for _ in ()).throw(SystemExit("crash")),
    )
    with pytest.raises(SystemExit):
        caller(owned).generate(owned.context(), REQUEST)
    record = owned.runs.get_reservation("run", "paid")
    assert record.paid_response_json is not None
    assert record.usage_status == "reserved"
    monkeypatch.setattr(owned.http.model, "_response", original)
    owned.runs = NarrativeRunStore(owned.auto.db_path)
    response, metrics = caller(owned).generate(owned.context(), REQUEST)
    assert response.response_bytes == b"not valid summary JSON" and metrics.tokens == 92
    assert owned.http.calls == 1
    assert len(owned.runs.reservations_for_run("run")) == 1
    assert owned.runs.get_reservation("run", "paid").charged_tokens == 92
    again, _ = caller(owned).generate(owned.context(), REQUEST)
    assert again.response_bytes == response.response_bytes and owned.http.calls == 1


@pytest.mark.parametrize("change", ["request", "missing", "tamper"])
def test_paid_replay_binding_or_bytes_failure_never_resends(owned, change):
    caller(owned).generate(owned.context(), REQUEST)
    request = REQUEST
    if change == "request":
        request = replace(REQUEST, input_sha256="d" * 64)
    else:
        pin = json.loads(owned.runs.get_reservation("run", "paid").paid_response_json)
        target = owned.objects.root / pin["object_key"]
        if change == "missing":
            target.unlink()
        else:
            target.write_bytes(b"tampered")
    with pytest.raises(NarrativeBudgetCallError):
        caller(owned).generate(owned.context(), request)
    assert owned.http.calls == 1
    assert len(owned.runs.reservations_for_run("run")) == 1


def test_paid_persistence_failure_stays_uncertain_without_an_automatic_second_post(
    owned, monkeypatch
):
    monkeypatch.setattr(
        owned.objects, "put", lambda _: (_ for _ in ()).throw(OSError("disk full"))
    )
    with pytest.raises(NarrativeBudgetCallError) as failure:
        caller(owned).generate(owned.context(), REQUEST)
    assert failure.value.code == "MODEL_PAID_RESPONSE_UNAVAILABLE"
    with pytest.raises(NarrativeBudgetCallError):
        caller(owned).generate(owned.context(), REQUEST)
    assert owned.http.calls == 1
    assert owned.runs.get_reservation("run", "paid").usage_status == "unknown"


def test_response_cap_applies_before_object_write(owned, monkeypatch):
    from company_wiki.automation.narrative_paid_response import PaidResponseArtifacts

    writes = []
    monkeypatch.setattr(owned.objects, "put", lambda data: writes.append(data))
    artifacts = PaidResponseArtifacts(owned.objects, max_response_bytes=8)
    with pytest.raises(Exception):
        artifacts.put(
            BODY,
            request_sha256="e" * 64,
            model_id="model",
            adapter_id="adapter",
            prompt_version="prompt/1",
            http_status=200,
            duration_ms=1,
        )
    assert not writes


def test_paid_usage_survives_lease_loss_and_replay_uses_new_fence(owned, monkeypatch):
    # The old worker has proof of a paid return, even if its publication lease is lost.
    original = owned.http.model._response

    def expire(*args, **kwargs):
        owned.auto.set_runtime_gate(RuntimeState.PAUSED, updated_at=T1)
        return original(*args, **kwargs)

    monkeypatch.setattr(owned.http.model, "_response", expire)
    caller(owned).generate(owned.context(), REQUEST)
    assert owned.runs.get_reservation("run", "paid").charged_tokens == 92
    pin = owned.runs.get_reservation("run", "paid").paid_response_json
    assert pin and owned.http.calls == 1
    # Current-result fencing stays in AutomationStore, not relaxed by byte capture.
    from company_wiki.automation.models import (
        HandlerMetrics,
        HandlerOutcome,
        HandlerResult,
    )

    with pytest.raises(Exception):
        owned.auto.finish_attempt(
            attempt_id="paid",
            lease_token="lease",
            runtime_generation=owned.generation,
            finished_at=T1,
            result=HandlerResult(
                HandlerOutcome.SUCCEEDED, {}, (), (), HandlerMetrics(0, 0, 0), None
            ),
        )


def test_old_hash_without_complete_pin_is_not_replayable_or_free(owned):
    body = owned.http.model.request_bytes(REQUEST)
    from company_wiki.automation.models import canonical_json_hash

    owned.runs.reserve_model_attempt(
        run_id="run",
        job_id="job",
        attempt_id="paid",
        lease_token="lease",
        runtime_generation=owned.generation,
        request_sha256=canonical_json_hash(
            {
                "schema_version": "narrative-model-attempt/2",
                "model_input_sha256": REQUEST.input_sha256,
                "http_body_sha256": hashlib.sha256(body).hexdigest(),
            }
        ),
        model_id="model",
        prompt_version="prompt/1",
        pricing_version="price/1",
        input_tokens_bound=len(body) + 128,
        max_output_tokens=256,
        output_bytes_bound=2 * 1024 * 1024,
        now=T1,
    )
    owned.runs.settle_model_usage(
        run_id="run",
        attempt_id="paid",
        usage=None,
        response_sha256=hashlib.sha256(b"prefix only").hexdigest(),
        error_code="MODEL_RESPONSE_INVALID",
        settled_at=T1,
    )
    with pytest.raises(NarrativeBudgetCallError):
        caller(owned).generate(owned.context(), REQUEST)
    assert owned.http.calls == 0
    assert owned.runs.get_reservation("run", "paid").usage_status == "unknown"


def test_same_pin_is_idempotent_but_different_pin_cannot_replace_paid_bytes(owned):
    from company_wiki.automation.narrative_run_store import ReservationConflictError

    caller(owned).generate(owned.context(), REQUEST)
    record = owned.runs.get_reservation("run", "paid")
    kwargs = dict(
        run_id="run",
        attempt_id="paid",
        lease_token="lease",
        runtime_generation=owned.generation,
        request_sha256=record.request_sha256,
        paid_response_json=record.paid_response_json,
        recorded_at=T1,
    )
    assert (
        owned.runs.attach_paid_response(**kwargs).paid_response_json
        == record.paid_response_json
    )
    changed = json.loads(record.paid_response_json)
    changed["duration_ms"] += 1
    kwargs["paid_response_json"] = json.dumps(
        changed, sort_keys=True, separators=(",", ":")
    )
    with pytest.raises(ReservationConflictError):
        owned.runs.attach_paid_response(**kwargs)
    assert (
        owned.runs.get_reservation("run", "paid").paid_response_json
        == record.paid_response_json
    )


def test_terminal_paid_failure_can_reopen_only_its_existing_output_slot_without_refunding_usage(
    owned,
):
    from company_wiki.automation.models import (
        HandlerError,
        HandlerMetrics,
        HandlerOutcome,
        HandlerResult,
    )

    caller(owned).generate(owned.context(), REQUEST)
    paid = owned.runs.get_reservation("run", "paid")
    result = HandlerResult(
        HandlerOutcome.TERMINAL_FAILURE,
        {},
        (),
        (),
        HandlerMetrics(92, 0.001, 1),
        HandlerError("SUMMARY_INVALID", "synthetic decode failure"),
    )
    owned.auto.finish_attempt(
        attempt_id="paid",
        lease_token="lease",
        runtime_generation=owned.generation,
        finished_at=T1,
        result=result,
    )
    assert owned.runs.get_reservation("run", "paid").output_bytes == 0
    owned.auto.retry_paid_narrative_summary(
        run_id="run",
        job_id="job",
        request_sha256=paid.request_sha256,
        now=T1,
        expected_generation=owned.generation,
    )
    replay = owned.auto.claim_next_ready(
        worker_id="worker",
        attempt_id="replay",
        lease_token="newlease",
        now=T1,
        lease_until=T2,
        expected_generation=owned.generation,
        allowed_job_ids=("job",),
    )
    response, _ = caller(owned).generate(owned.context(replay), REQUEST)
    assert response.response_bytes == b"not valid summary JSON"
    paid_after = owned.runs.get_reservation("run", "paid")
    assert paid_after.output_bytes is None and paid_after.charged_tokens == 92
    assert len(owned.runs.reservations_for_run("run")) == 1 and owned.http.calls == 1
    # Replay remains charged to original receipt; no provider reservation on the new lease.
    assert owned.runs.get_reservation("run", "replay") is None
    assert owned.auto.get_attempt("paid").result_json is not None
    with pytest.raises(Exception):
        owned.runs.reopen_paid_output(
            run_id="run",
            paid_attempt_id="paid",
            current_attempt_id="replay",
            lease_token="newlease",
            runtime_generation=owned.generation,
            request_sha256=paid.request_sha256,
            verified_response_sha256=json.loads(paid.paid_response_json)["body_sha256"],
            now=T1,
        )


@pytest.mark.parametrize("kind", ["no_pin", "changed_request", "positive_output"])
def test_output_reopen_refuses_unproven_or_already_positive_state(owned, kind):
    caller(owned).generate(owned.context(), REQUEST)
    record = owned.runs.get_reservation("run", "paid")
    if kind == "no_pin":
        import sqlite3

        with sqlite3.connect(owned.auto.db_path) as conn:
            conn.execute(
                "UPDATE narrative_model_reservations SET paid_response_json=NULL WHERE attempt_id='paid'"
            )
    if kind == "positive_output":
        owned.runs.settle_output(
            run_id="run",
            attempt_id="paid",
            output_bytes=10,
            output_sha256="f" * 64,
            settled_at=T1,
        )
    else:
        owned.runs.settle_output(
            run_id="run",
            attempt_id="paid",
            output_bytes=0,
            output_sha256=None,
            settled_at=T1,
        )
    with pytest.raises(Exception):
        owned.runs.reopen_paid_output(
            run_id="run",
            paid_attempt_id="paid",
            current_attempt_id="paid",
            lease_token="lease",
            runtime_generation=owned.generation,
            request_sha256="f" * 64
            if kind == "changed_request"
            else record.request_sha256,
            verified_response_sha256=json.loads(record.paid_response_json)[
                "body_sha256"
            ],
            now=T1,
        )


def test_space_preflight_happens_before_admission_and_post(owned):
    from company_wiki.automation.narrative_paid_response import PaidResponseArtifacts

    def full(_):
        raise OSError("quota full")

    artifacts = PaidResponseArtifacts(
        owned.objects, max_response_bytes=262144, preflight=full
    )
    attempt = BudgetedNarrativeCaller(
        store=owned.runs,
        run_id="run",
        model=owned.http.model,
        paid_responses=artifacts,
        clock=lambda: T1,
    )
    with pytest.raises(NarrativeBudgetCallError) as failed:
        attempt.generate(owned.context(), REQUEST)
    assert failed.value.code == "MODEL_PAID_RESPONSE_SPACE_DENIED"
    assert not owned.runs.reservations_for_run("run") and owned.http.calls == 0


def test_schema6_upgrade_adds_nullable_receipt_without_new_tables(tmp_path):
    import sqlite3
    from company_wiki.automation import migrations

    db = tmp_path / "v6.db"
    with sqlite3.connect(db) as conn:
        for version in range(1, 7):
            for statement in getattr(migrations, f"_DDL_V{version}_STATEMENTS"):
                conn.execute(statement)
        conn.execute("PRAGMA user_version=6")
        before = set(
            x[0]
            for x in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        )
    migrations.migrate_database(db)
    with sqlite3.connect(db) as conn:
        columns = {
            x[1]
            for x in conn.execute("PRAGMA table_info(narrative_model_reservations)")
        }
        after = set(
            x[0]
            for x in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        )
    assert "paid_response_json" in columns and before == after
    assert migrations.inspect_schema(db).user_version == migrations.SCHEMA_VERSION


def test_replay_needs_no_credentials_and_creates_no_new_response_copy(
    owned, monkeypatch
):
    caller(owned).generate(owned.context(), REQUEST)
    paths_before = tuple(sorted(owned.objects.root.rglob("*.json")))
    monkeypatch.delenv("DU11_SYNTHETIC_KEY")
    response, _ = caller(owned).generate(owned.context(), REQUEST)
    assert response.input_tokens == 73 and response.output_tokens == 19
    assert (
        owned.http.calls == 1
        and tuple(sorted(owned.objects.root.rglob("*.json"))) == paths_before
    )
    assert len(paths_before) == 1


@pytest.mark.parametrize("field", ["model_id", "adapter_id", "prompt_version"])
def test_receipt_identity_bound_is_checked_before_any_paid_post(owned, field):
    request = REQUEST
    if field == "prompt_version":
        request = replace(REQUEST, prompt_version="x" * 257)
    else:
        setattr(owned.http.model, field, "x" * 257)
    with pytest.raises(NarrativeBudgetCallError) as error:
        caller(owned).generate(owned.context(), request)
    assert error.value.code == "MODEL_PAID_RESPONSE_BINDING_INVALID"
    assert owned.http.calls == 0 and not owned.runs.reservations_for_run("run")


@pytest.mark.parametrize("body", [b"", b"not JSON"])
def test_complete_but_invalid_envelope_is_saved_and_replayed_without_a_second_post(
    owned, body
):
    owned.http.body = body
    for _ in range(2):
        with pytest.raises(NarrativeBudgetCallError) as failed:
            caller(owned).generate(owned.context(), REQUEST)
        assert failed.value.code == "MODEL_RESPONSE_INVALID"
    record = owned.runs.get_reservation("run", "paid")
    assert record.paid_response_json and record.usage_status == "unknown"
    assert owned.http.calls == 1


@pytest.mark.parametrize("field", ["input_hash", "handler_version"])
def test_replay_refuses_changed_frozen_job_binding_without_a_new_post(owned, field):
    import sqlite3

    caller(owned).generate(owned.context(), REQUEST)
    with sqlite3.connect(owned.auto.db_path) as connection:
        connection.execute(
            f"UPDATE jobs SET {field}=? WHERE job_id='job'",
            ("d" * 64 if field == "input_hash" else "changed",),
        )
    with pytest.raises(NarrativeBudgetCallError):
        caller(owned).generate(owned.context(), REQUEST)
    assert owned.http.calls == 1
