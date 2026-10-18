"""One real loopback POST survives decoder death and a new AUTO lease."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import socket
import threading
from types import SimpleNamespace

import pytest

from company_wiki.automation.models import (
    HandlerError,
    HandlerMetrics,
    HandlerOutcome,
    HandlerResult,
)
from company_wiki.automation.narrative_http_model import NarrativeHTTPModel
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from unit.test_narrative_http_model import _CONNECT, _CREATE_CONNECTION
from unit.du11_paid_response.test_paid_response import (
    BODY,
    REQUEST,
    T1,
    T2,
    caller,
    seed_owned,
)


def test_complete_paid_body_survives_decoder_crash_and_new_lease_without_resend(
    tmp_path, monkeypatch
):
    state = SimpleNamespace(calls=0, forbid=False)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            state.calls += 1
            assert not state.forbid, "recovery attempted a second paid POST"
            self.send_response(200)
            self.send_header("Content-Length", str(len(BODY)))
            self.end_headers()
            self.wfile.write(BODY)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = False
    address = ("127.0.0.1", server.server_port)
    # Permit only this test-owned loopback endpoint.
    def connect(sock, target):
        assert target == address
        return _CONNECT(sock, target)

    def create_connection(target, *args, **kwargs):
        assert target == address
        return _CREATE_CONNECTION(target, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket, "create_connection", create_connection)
    monkeypatch.setenv("DU11_SYNTHETIC_KEY", "synthetic-test-value")
    model = NarrativeHTTPModel(
        endpoint=f"http://127.0.0.1:{server.server_port}/v1/chat/completions",
        allow_local_http=True,
        model_id="model",
        api_key_env="DU11_SYNTHETIC_KEY",
        max_output_tokens=256,
    )
    env = seed_owned(tmp_path, SimpleNamespace(model=model))
    source_decode = model._response

    def interrupted(*args, **kwargs):
        raise SystemExit(
            "simulated worker died after durable body, before envelope decode"
        )

    monkeypatch.setattr(model, "_response", interrupted)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01))
    thread.start()
    try:
        with pytest.raises(SystemExit):
            caller(env).generate(env.context(), REQUEST)
        assert env.runs.get_reservation("run", "paid").paid_response_json
        failed = HandlerResult(
            HandlerOutcome.RETRYABLE,
            {},
            (),
            (),
            HandlerMetrics(0, 0, 0),
            HandlerError("WORKER_LOST", "simulated interruption"),
        )
        env.auto.finish_attempt(
            attempt_id="paid",
            lease_token="lease",
            runtime_generation=env.generation,
            finished_at=T1,
            retry_not_before=T1,
            result=failed,
        )
        env.runs.settle_finished_attempt_reservations(run_id="run", settled_at=T1)
        record = env.runs.get_reservation("run", "paid")
        assert record.usage_status == "unknown"
        env.auto.retry_paid_narrative_summary(
            run_id="run",
            job_id="job",
            request_sha256=record.request_sha256,
            now=T1,
            expected_generation=env.generation,
        )
        replay = env.auto.claim_next_ready(
            worker_id="reopened",
            attempt_id="reopened",
            lease_token="new-lease",
            now=T1,
            lease_until=T2,
            expected_generation=env.generation,
            allowed_job_ids=("job",),
        )
        env.runs = NarrativeRunStore(env.auto.db_path)
        monkeypatch.setattr(model, "_response", source_decode)
        monkeypatch.delenv("DU11_SYNTHETIC_KEY")
        state.forbid = True
        response, metrics = caller(env).generate(env.context(replay), REQUEST)
        assert (
            response.response_bytes == b"not valid summary JSON"
            and metrics.tokens == 92
        )
        assert state.calls == 1
        reservations = env.runs.reservations_for_run("run")
        assert len(reservations) == 1 and reservations[0].attempt_id == "paid"
        assert (
            reservations[0].usage_status == "known"
            and reservations[0].charged_tokens == 92
        )
        assert env.auto.get_attempt("paid").result_json is not None
        assert len(tuple(env.objects.root.rglob("*.json"))) == 1
        assert not tuple(env.objects.root.rglob("*.partial"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive()
