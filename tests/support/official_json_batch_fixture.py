"""Owned real catalogs and loopback model for mixed production CLI batches.

No hand-written HandlerResult and no live provider. The HTTP endpoint consumes
real prompts from spawned production workers. Fixture key is loopback-only.
"""

from contextlib import contextmanager
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Lock, Thread
from types import SimpleNamespace

import pytest

from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
from company_wiki.automation.narrative_transport_contracts import NarrativeReadRequest
from company_wiki.narrative_subject import NarrativeSubject
from company_wiki.source_catalog.official_json_import import import_official_json_source
from company_wiki.source_catalog.official_json_projection import (
    build_projection_from_refs,
    persist_projection,
)
from support.narrative_batch_fixtures import prepare_source_catalog

KEY_ENV = "OFFICIAL_JSON_LOOPBACK_MODEL_KEY"
KEY = "synthetic-local-key-never-production"
REPO = Path(__file__).resolve().parents[2]


def encoded(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def model_draft(data):
    projected = data["schema_version"] == "narrative-model-request/2"
    assert data["schema_version"] == (
        "narrative-model-request/2" if projected else "narrative-model-request/1.4"
    )
    identity = data["subject"] if projected else data["source"]
    if projected:
        assert "source" not in data
        assert set(identity) == {
            "subject_id",
            "subject_sha256",
            "language",
            "title",
            "document_kind",
        }
    else:
        assert "subject" not in data
    assert "records" not in data and "parent_source_refs" not in data
    rows = [
        (row, row[2] if len(row) > 2 else data["default_source_role"])
        for row in data["evidence"]
    ]
    row, role = next(
        (row, role) for row, role in rows if role in {"company_filing", "management"}
    )
    draft = {
        "language": identity["language"],
        "claims": [
            {
                "claim_id": "business-update",
                "text": row[1][:180].strip(),
                "evidence_ids": [row[0]],
                "evidence_group_ids": [],
                "claim_type": "company_statement",
                "modality": "planned",
            }
        ],
        "status": "draft",
    }
    if projected:
        draft.update(
            subject_id=identity["subject_id"], subject_sha256=identity["subject_sha256"]
        )
    else:
        draft.update(
            source_id=identity["source_id"], source_sha256=identity["source_sha256"]
        )
    return {"draft": draft}


@pytest.fixture
def official_json_loopback_model(monkeypatch, hermetic_runtime):
    state = SimpleNamespace(requests=[], errors=[])
    lock = Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            try:
                assert self.path == "/v1/chat/completions"
                assert self.headers["Authorization"] == "Bearer " + KEY
                raw = self.rfile.read(int(self.headers["Content-Length"]))
                assert KEY.encode() not in raw
                envelope = json.loads(raw)
                assert envelope["model"] == "stub-model"
                assert [message["role"] for message in envelope["messages"]] == [
                    "system",
                    "user",
                ]
                assert "No translation" in envelope["messages"][0]["content"]
                data = json.loads(envelope["messages"][1]["content"])
                draft = model_draft(data)
                with lock:
                    state.requests.append(data)
                reply = encoded(
                    {
                        "model": "stub-model",
                        "choices": [
                            {
                                "message": {"content": encoded(draft).decode()},
                                "finish_reason": "stop",
                            }
                        ],
                        "usage": {"prompt_tokens": 73, "completion_tokens": 19},
                    }
                )
                self.send_response(200)
            except Exception as exc:
                with lock:
                    state.errors.append(type(exc).__name__)
                reply = b'{"error":"invalid synthetic test prompt"}'
                self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(reply)))
            self.end_headers()
            self.wfile.write(reply)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = False
    thread = Thread(target=lambda: server.serve_forever(poll_interval=0.01))
    thread.start()
    monkeypatch.setenv(KEY_ENV, KEY)
    state.endpoint = (
        "http://127.0.0.1:" + str(server.server_port) + "/v1/chat/completions"
    )
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        assert not thread.is_alive()


@contextmanager
def official_batch_state(tmp_path):
    before = {
        p.relative_to(tmp_path): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    }
    with TemporaryDirectory(prefix="official-batch-", dir=tmp_path) as owned:
        root = Path(owned)
        state = prepare_source_catalog(root, one_source=True, include_policy=False)
        try:
            raw_ref = asdict(next(iter(state.indexed.values()))[0])
            refs = []
            for page in (1, 2):
                records = []
                for issuer in (1, 2):
                    answer = (
                        "公司新产品完成客户验证，第四季度开始批量交付，海外订单持续增长。"
                        if issuer == 1
                        else "Our new product has completed customer qualification and overseas shipments begin in the fourth quarter."
                    )
                    question = (
                        "新产品客户验证和海外订单交付进展如何？"
                        if issuer == 1
                        else "When do new product qualification and overseas shipments begin?"
                    )
                    records.append(
                        {
                            "id": page * 100 + issuer,
                            "companyId": issuer,
                            "content": answer,
                            "questionContent": question,
                            "isAnswered": True,
                            "crtTime": "2026-09-01 10:00:00",
                            "updTime": "2026-09-02 10:00:00",
                            "contentEn": "Provider translation must not enter the summary. "
                            * 10
                            if issuer == 1
                            else None,
                        }
                    )
                body = encoded(
                    {
                        "success": True,
                        "code": 200,
                        "datas": [
                            {
                                "current": page,
                                "size": 2,
                                "pages": 2,
                                "total": 4,
                                "records": records,
                            }
                        ],
                    }
                )
                result = import_official_json_source(
                    state.catalog,
                    original=body,
                    request={
                        "schema_version": "official-source-import-request/2",
                        "request_id": "batch-page-" + str(page),
                        "max_bytes": 1048576,
                        "content_sha256": sha(body),
                        "mime_type": "application/json",
                        "document_kind": "investor_relations",
                        "source_subject": {
                            "kind": "multi_issuer_event",
                            "event_namespace": "offline-batch-fixture",
                            "event_id": "42",
                            "issuer_refs": [],
                            "attribution_status": "partial",
                        },
                        "capture_receipt": {
                            "capture_method": "local_document",
                            "tool_name": "offline-fixture",
                            "tool_call_id": "page-" + str(page),
                            "captured_at": "2026-10-10T00:00:00Z",
                            "response_bytes": len(body),
                            "content_sha256": sha(body),
                        },
                    },
                )
                refs.append(result["source_ref"])
            projections = tuple(
                build_projection_from_refs(
                    state.catalog,
                    refs=refs,
                    layout_id="official-paged-qa",
                    issuer={"provider_company_id": issuer},
                    as_of_date="2026-10-08",
                )
                for issuer in (1, 2)
            )
            for projection in projections:
                persist_projection(state.catalog, projection)
            subjects = tuple(NarrativeSubject.from_projection(p) for p in projections)
            public_config = root / "config" / "catalog.json"
            public_config.parent.mkdir()
            public_config.write_bytes(state.config_path.read_bytes())
            state.config_path = public_config
            state.raw_ref, state.parent_refs, state.subjects = (
                raw_ref,
                tuple(refs),
                subjects,
            )
            state.automation_db = root / "automation.db"
            state.originals = {
                p: p.read_bytes()
                for p in (root / "companies").rglob("*")
                if p.is_file()
            }
            state.config_bytes = state.config_path.read_bytes()
            state.calls = []
            assert (
                len([p for p in state.originals if not p.name.endswith(".source.json")])
                == 3
            )
            yield state
        finally:
            if hasattr(state, "originals"):
                assert {p: p.read_bytes() for p in state.originals} == state.originals
                assert state.config_path.read_bytes() == state.config_bytes
            state.catalog.close()
    assert {
        p.relative_to(tmp_path): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    } == before


def request_for(state, endpoint, run_id, *, refresh=False, items=None):
    membership = [
        {
            "kind": "official_json",
            "projection_id": s.item_key,
            "projection_sha256": s.subject_sha256,
        }
        for s in state.subjects
    ] + [{"kind": "raw", "source_ref": state.raw_ref}]
    request = NarrativeBatchRequest.from_dict(
        {
            "schema_version": "narrative-batch-request/2",
            "run_id": run_id,
            "items": membership if items is None else items,
            "profile": "P2",
            "refresh": refresh,
            "max_seconds": 40,
            "max_tokens": 200000,
            "max_cost_usd": "2",
            "model": {
                "model_id": "stub-model",
                "endpoint": endpoint,
                "api_key_env": KEY_ENV,
                "max_output_tokens": 400,
                "timeout_seconds": 5,
                "allow_local_http": True,
            },
            "pricing": {
                "version": "offline-fixture/1",
                "input_micro_usd_per_million_tokens": 1000000,
                "output_micro_usd_per_million_tokens": 2000000,
            },
        }
    )
    path = state.root / (run_id + ".json")
    path.write_bytes(encoded(request.to_dict()))
    assert KEY.encode() not in path.read_bytes()
    return path


def subprocess_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(
        PYTHONPATH=os.pathsep.join((str(REPO / "src"), str(REPO / "scripts"))),
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONUTF8="1",
        PYTHON_DOTENV_DISABLED="1",
    )
    return env


def invoke_batch(state, request_path, run_id):
    command = [
        sys.executable,
        "-B",
        "-m",
        "company_wiki.automation.narrative_batch_cli",
        "--project-root",
        str(state.root),
        "--catalog-config",
        str(state.config_path),
        "--automation-db",
        str(state.automation_db),
        "--work-dir",
        str(state.root / ("work-" + run_id)),
        "--request",
        str(request_path),
    ]
    process = subprocess.run(
        command,
        cwd=state.root,
        env=subprocess_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert KEY not in process.stdout + process.stderr
    assert process.stdout.strip(), process.stderr
    result = json.loads(process.stdout)
    assert result["schema_version"] == "narrative-batch-result/2", (
        process.returncode,
        result,
        process.stderr,
    )
    assert result["run_id"] == run_id
    if process.returncode != 0:
        print(
            "OFFICIAL-CLI-FAILURE "
            + json.dumps(
                {
                    "exit_code": process.returncode,
                    "error": result.get("error"),
                    "status": result.get("status"),
                    "items": [
                        {
                            "item_key": item.get("item_key"),
                            "status": item.get("status"),
                            "errors": item.get("errors"),
                        }
                        for item in result.get("items", [])
                    ],
                    "budget": result.get("budget"),
                },
                ensure_ascii=False,
            )
        )
    state.calls.append(
        {
            "command": command,
            "exit_code": process.returncode,
            "receipt": result,
            "stderr": process.stderr,
        }
    )
    return process, result


def invoke_read(state, reference, *, issuer=None):
    projected = reference["schema_version"] == "narrative-ref/2"
    if projected:
        reference_request = {
            "schema_version": "narrative-reference-request/2",
            "subject_binding": reference["subject_binding"],
            "generation_sha256": reference["generation_sha256"],
        }
        discovery = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "company_wiki.source_catalog.narrative_transport_cli",
                "--config",
                str(state.config_path),
                "--operation",
                "reference",
            ],
            input=encoded(reference_request),
            cwd=state.root,
            env=subprocess_env(),
            capture_output=True,
            timeout=30,
        )
        assert discovery.returncode == 0, discovery.stderr.decode(errors="replace")
        assert json.loads(discovery.stdout) == reference, (
            "public discovery must use exact subject/generation, never shared anchor latest"
        )
        assert json.loads(discovery.stderr)["status"] == "metadata_only"
    wire = {
        "schema_version": "narrative-read-request/2"
        if projected
        else "narrative-read-request/1",
        "narrative_ref": reference,
        "as_of_date": "2026-10-08",
    }
    if projected:
        # Subject identity stores explicit unknowns. Read constraints instead
        # contain only concrete fields; keep the real provider issuer constraint.
        wire["expected_issuer"] = (
            None
            if issuer is None
            else {key: value for key, value in issuer.items() if value is not None}
        )
    else:
        wire["expected_source"] = {
            key: None
            for key in (
                "canonical_entity_id",
                "market",
                "security_id",
                "document_kind",
                "fiscal_year",
                "fiscal_period",
            )
        }
    NarrativeReadRequest.from_dict(wire)
    process = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "company_wiki.source_catalog.narrative_transport_cli",
            "--config",
            str(state.config_path),
            "--operation",
            "read",
        ],
        input=encoded(wire),
        cwd=state.root,
        env=subprocess_env(),
        capture_output=True,
        timeout=45,
    )
    assert process.returncode == 0, (process.stderr.decode(errors="replace"), reference)
    assert sha(process.stdout) == reference["artifact_sha256"]
    assert len(process.stdout) == reference["byte_size"]
    receipt = json.loads(process.stderr)
    assert receipt["status"] == "ok" and receipt["narrative_ref"] == reference
    return json.loads(process.stdout), receipt
