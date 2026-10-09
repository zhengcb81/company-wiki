"""Isolated original documents and loopback HTTP for production narrative E2E."""

from __future__ import annotations

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
import shutil
from threading import Thread
from types import SimpleNamespace

import pytest

from company_wiki.automation.models import Event, JobStatus, canonical_json
from company_wiki.automation.narrative_contracts import SourceRevisionEventPayload
from company_wiki.source_catalog import SourceCatalog
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.source_reader import SourceVersionReader
from support.narrative_model_request_fixture import response_draft


KEY_ENV = "NARRATIVE_PRODUCTION_E2E_KEY"
KEY = "synthetic-loopback-key-only"
T0 = "2026-09-28T22:00:00Z"


@pytest.fixture
def loopback_model_server(monkeypatch, hermetic_runtime):
    """Serve one valid prompt-derived draft per actual local HTTP POST."""
    state = SimpleNamespace(requests=[], errors=[], response_status=200, error_body=b"", response_body=None, response_usage=None)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            try:
                assert self.path == "/v1/chat/completions"
                assert self.headers["Authorization"] == f"Bearer {KEY}"
                body = self.rfile.read(int(self.headers["Content-Length"]))
                assert KEY.encode() not in body
                request = json.loads(body)
                assert [message["role"] for message in request["messages"]] == ["system", "user"]
                data = json.loads(request["messages"][1]["content"])
                draft = response_draft(data)
                assert "No translation" in request["messages"][0]["content"]
                state.requests.append((data, body))
                reply = json.dumps({
                    "model": "stub-model", "choices": [{"message": {"content": json.dumps(draft, ensure_ascii=False)},
                                                             "finish_reason": "stop"}],
                    "usage": state.response_usage if state.response_usage is not None else {"prompt_tokens": 73, "completion_tokens": 19},
                }, ensure_ascii=False).encode("utf-8")
                if state.response_body is not None:
                    reply = state.response_body
                if state.response_status != 200:
                    reply = state.error_body
                self.send_response(state.response_status)
            except Exception as exc:
                state.errors.append(type(exc).__name__)
                reply = b'{"error":"invalid test request"}'
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
    state.endpoint = f"http://127.0.0.1:{server.server_port}/v1/chat/completions"
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        assert not thread.is_alive()


@contextmanager
def isolated_batch_directory(tmp_path_factory):
    """Remove every newly made fixture while preserving a pre-existing file."""
    test_dir = tmp_path_factory.mktemp("nb")
    (test_dir / "keep.txt").write_bytes(b"preexisting test file")
    baseline = {path.name: path.read_bytes() for path in test_dir.iterdir()}
    root = test_dir / "run"
    root.mkdir()
    try:
        yield root
    finally:
        assert root.resolve().parent == test_dir.resolve() and root.name == "run"
        shutil.rmtree(root)
        assert {path.name: path.read_bytes() for path in test_dir.iterdir()} == baseline


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def _pdf_bytes(text):
    fitz = pytest.importorskip("fitz")
    document = fitz.open()
    try:
        document.new_page().insert_text((72, 72), text)
        return document.tobytes()
    finally:
        document.close()


def source_documents(*, include_mixed=False, include_annual_pdf=False, include_policy=True, policy_title=None):
    documents = [
        ("en", "call-en.txt", "Acme 2026 Q1 earnings call", "investor_call_transcript",
         b"Full Conference Call Transcript\nCEO: We launched a new product and expanded overseas capacity.\n"),
        ("zh", "call-zh.txt", "Acme 2026年一季度电话会议", "investor_call_transcript",
         "Full Conference Call Transcript\nCEO: 公司完成海外产能扩张，新产品已完成客户认证并进入量产。\n".encode("utf-8")),
    ]
    if include_policy:
        documents.append((
            "en", "ir-policy.pdf", policy_title or "投资者关系管理办法（2025年8月）.pdf", "ir_policy",
            _pdf_bytes("This policy describes meeting administration procedures."),
        ))
    if include_mixed:
        documents.append((
            "mixed", "call-mixed.txt", "Acme 2026 Q2 earnings call", "investor_call_transcript",
            ("Full Conference Call Transcript\n"
             "Management discussed the overseas expansion plan. "
             "公司新产品已经完成客户认证，开始批量交付。\n").encode("utf-8"),
        ))
    if include_annual_pdf:
        documents.append((
            "en", "annual-report.pdf", "Acme annual report 2025", "annual_report",
            _pdf_bytes("Company launched a new product and expanded overseas capacity for customers."),
        ))
    return documents


def source_event(reader, ref, title, language, kind, event_id, *, policy_version="narrative-v1"):
    payload = {
        "schema_version": "source-revision-event/2.0",
        "source_ref": {"schema_version": ref.schema_version, "document_id": ref.document_id,
                       "source_id": ref.source_id, "content_sha256": ref.content_sha256,
                       "byte_size": ref.byte_size, "mime_type": ref.mime_type},
        "expected_read_policy_sha256": reader.read_policy_sha256(),
        "source_metadata": {"source_class": "transcript" if kind == "investor_call_transcript" else "filing",
                            "title": title, "document_kind": kind, "language": language},
    }
    parsed = SourceRevisionEventPayload.from_dict(payload)
    return Event(event_id, "source.revision_registered", "source_revision", ref.document_id,
                 parsed.input_hash, canonical_json(payload), policy_version, T0, T0)


def prepare_source_catalog(
    root,
    *,
    one_source=False,
    sparse_metadata=False,
    include_mixed=False,
    include_annual_pdf=False,
    include_policy=True,
    policy_title=None,
):
    """Scan real PDF/TXT bytes without materializing a batch or leasing work."""
    all_sources = source_documents(
        include_mixed=include_mixed,
        include_annual_pdf=include_annual_pdf,
        include_policy=include_policy,
        policy_title=policy_title,
    )
    sources = all_sources[:1] if one_source else all_sources
    paths = {}
    for language, name, title, kind, data in sources:
        group = (
            "transcripts" if kind == "investor_call_transcript"
            else "annual" if kind == "annual_report"
            else "policies"
        )
        directory = root / "companies" / "Acme" / "raw" / "investor_relations" / group
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / name
        path.write_bytes(data)
        paths[name] = path
        sidecar = {
            "schema_version": "1.0", "canonical_entity_id": "ent-acme", "display_name": "Acme",
            "market": "US", "security_id": "ACME", "document_kind": kind, "fiscal_year": 2026,
            "fiscal_period": "FY" if kind == "annual_report" else "Q1",
            "period_end": "2025-12-31" if kind == "annual_report" else "2026-03-31",
            "filing_date": "2026-03-30" if kind == "annual_report" else "2026-05-01",
            "provider": "fixture", "provider_document_id": name, "content_sha256": sha256(data),
            "source_url": "https://fixtures.invalid/" + name, "source_title": title,
            "retrieved_at": "2026-05-02T00:00:00Z", "collector_name": "production_e2e_fixture", "collector_version": "1.0.0",
        }
        if not sparse_metadata:
            sidecar["language"] = language
        path.with_name(name + ".source.json").write_text(json.dumps(sidecar), encoding="utf-8")
    config_path = root / "catalog.json"
    config_path.write_text(json.dumps({
        "schema_version": "1.0", "catalog_dir": "catalog", "roots": [{
            "root_id": "company_raw", "path": "companies", "kind": "company_raw",
            "adapter_id": "company_raw_v1", "read_only": True, "reusable_for_filing": True,
        }],
    }), encoding="utf-8")
    catalog = SourceCatalog(load_catalog_config(config_path, project_root=root))
    try:
        catalog.scan()
        reader = SourceVersionReader(catalog)
        indexed = {}
        for language, _name, title, kind, data in sources:
            row = catalog.reader.fetchone(
                "SELECT d.document_id,d.primary_source_id AS source_id FROM documents d "
                "JOIN sources s ON s.source_id=d.primary_source_id WHERE s.content_sha256=?", (sha256(data),),
            )
            assert row is not None
            ref = reader.query_ref(row["document_id"], row["source_id"], sha256(data))
            manifest = reader.describe_version(ref)
            catalog_kind = "investor_relations" if kind == "ir_policy" else kind
            expected_language = None if sparse_metadata else language
            assert (manifest["title"], manifest["document_kind"], manifest["language"]) == (title, catalog_kind, expected_language), manifest
            indexed[ref.document_id] = (ref, language, kind)
        return SimpleNamespace(root=root, config_path=config_path, catalog=catalog, reader=reader,
                               sources=sources, indexed=indexed, raw_paths=paths)
    except BaseException:
        catalog.close()
        raise


def foreign_ready_jobs(state, store, scheduler):
    ref, language, kind = next(iter(state.indexed.values()))
    event = source_event(state.reader, ref, state.sources[0][2], language, kind,
                         "outside-event", policy_version="outside-policy")
    before = {job.job_id for job in store.list_jobs()}
    store.put_event(event)
    scheduler.materialize_event(event)
    outside = tuple(job for job in store.list_jobs() if job.job_id not in before)
    assert len(outside) == 3 and any(job.status is JobStatus.READY for job in outside)
    return outside


def assert_originals_and_foreign_jobs_untouched(state, originals, *, output=""):
    assert {path: path.read_bytes() for path in originals} == originals
    assert tuple(state.store.get_job(job.job_id) for job in state.outside) == state.outside
    assert all(state.store.list_attempts(job.job_id) == () for job in state.outside)
    logs = "\n".join(path.read_text(encoding="utf-8") for path in state.root.rglob("*.log"))
    text = output + logs
    assert KEY not in text and '"response_schema"' not in text
    assert "We launched a new product" not in text and "公司完成海外产能扩张" not in text
