"""W04 storage/capture contracts using owned raw and loopback HTTP only."""
from contextlib import contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import threading
import time

import pytest

from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog import canonical_writer as writer_module
from company_wiki.source_catalog import official_source_flow as flow

_SOCKET_CONNECT = socket.socket.connect
BODY = b"<html><p>Issuer expanded new business and overseas customers.</p></html>"


def import_request(body=BODY, *, title=None, kind="investor_relations"):
    sha = hashlib.sha256(body).hexdigest()
    return {
        "schema_version": "official-source-import-request/1", "request_id": "capture-fixture",
        "source": {"entity": "跨国示例公司", "market": "HK", "security_id": "01234",
                   "document_kind": kind, "title": title or "Issuer business update",
                   "publisher": "Issuer", "source_url": "https://issuer.example/update",
                   "published_date": "2026-09-30", "language": "en",
                   "provider_document_id": "provider-book-" + "a" * 180},
        "mime_type": "text/html", "content_sha256": sha, "max_bytes": 1048576,
        "capture_receipt": {"capture_method": "local_document", "tool_name": "fixture",
                            "tool_call_id": "actual-local-observation", "captured_at": "2026-10-09T00:00:00Z",
                            "response_bytes": len(body), "content_sha256": sha},
    }


@contextmanager
def lake(tmp_path, *, deep=False):
    root = tmp_path / "lake"
    if deep:
        root = root / ("deep-" + "r" * max(1, 130 - len(str(root)) - 6))
    companies = root / "companies"
    companies.mkdir(parents=True)
    catalog = SourceCatalog(CatalogConfig(project_root=root, catalog_dir=root / "catalog",
                            roots=(RootSpec("company_raw", companies, "company_raw"),)))
    try:
        yield root, catalog
    finally:
        catalog.close()


def retained(catalog):
    return list((catalog.config.catalog_dir / "staging").glob("*.capture.json"))


@pytest.mark.parametrize("kind", ["annual_report", "regulatory_filing", "investor_relations", "prospectus"])
def test_long_title_uses_content_name_and_keeps_complete_metadata(tmp_path, kind):
    title = ("Global Medium Term Note Programme offering circular and business risks " * 12).strip()
    with lake(tmp_path, deep=True) as (_, catalog):
        req = import_request(title=title, kind=kind)
        out = flow.import_official_source(catalog, original=BODY, request=req)
        location = catalog.store.fetchone("SELECT absolute_path FROM locations WHERE source_id=? AND role='original_primary'", (out["source_ref"]["source_id"],))
        path = Path(location["absolute_path"])
        assert len(path.name) <= 70
        assert len(str(path) + ".source.json.9999999999.tmp") <= 259
        metadata = json.loads(path.with_name(path.name + ".source.json").read_text(encoding="utf-8"))
        assert metadata["source_title"] == title
        assert metadata["provider_document_id"] == req["source"]["provider_document_id"]
        assert metadata["receipt"]["adapter_name"] == "official-original-import"
        assert "http_status" not in metadata["receipt"]


@pytest.mark.parametrize("fault", ["copy", "rename", "provenance", "catalog", "facts"])
def test_failed_commit_keeps_exact_raw_receipt_and_recovery_avoids_network(tmp_path, monkeypatch, fault):
    with lake(tmp_path) as (root, catalog):
        sentinel = catalog.config.catalog_dir / "staging" / "other-owner.txt"
        sentinel.parent.mkdir(parents=True)
        sentinel.write_bytes(b"pre-existing owner raw")
        req = import_request()
        req["source"]["provider_document_id"] = "short-fixture"
        def fail(*args, **kwargs):
            raise OSError("fixture-" + fault)
        with monkeypatch.context() as patch:
            if fault == "copy":
                patch.setattr(writer_module.shutil, "copyfile", fail)
            elif fault == "rename":
                original_replace = writer_module.os.replace
                def rename(src, dst):
                    if str(dst).endswith(".html") and "companies" in str(dst):
                        fail()
                    return original_replace(src, dst)
                patch.setattr(writer_module.os, "replace", rename)
            elif fault == "provenance":
                patch.setattr(writer_module.CanonicalSourceWriter, "_write_provenance", fail)
            elif fault == "catalog":
                patch.setattr(writer_module, "register_catalog_sources", fail)
            else:
                patch.setattr(catalog, "record_source_facts", fail)
            with pytest.raises(OSError, match="fixture-") as caught:
                flow.import_official_source(catalog, original=BODY, request=req)
        items = retained(catalog)
        assert len(items) == 1, "validated original must survive failed import"
        state = json.loads(items[0].read_text(encoding="utf-8"))
        body = items[0].parent / state["staged_name"]
        assert body.read_bytes() == BODY
        assert state["request"]["capture_receipt"] == req["capture_receipt"]
        assert caught.value.capture_id == state["capture_id"]
        assert flow.list_retained_official_captures(catalog)[0]["capture_id"] == state["capture_id"]
        # The existing journal is authoritative; it must point to the retained original.
        from company_wiki.source_catalog.acquisition_journal import AcquisitionJournal
        attempts = AcquisitionJournal(catalog.config.catalog_dir).read_all()
        assert attempts[-1].outcome == "failed"
        assert attempts[-1].canonical_path == str(body.resolve())
        out = flow.recover_official_source(catalog, capture_id=state["capture_id"])
        assert out["source_ref"]["content_sha256"] == hashlib.sha256(BODY).hexdigest()
        assert not body.exists() and not retained(catalog)
        assert sentinel.read_bytes() == b"pre-existing owner raw"
        assert str(root) not in json.dumps(out)


@contextmanager
def loopback(monkeypatch, mode="normal"):
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass
        def do_GET(self):
            requests.append(self.path)
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(BODY)))
            self.end_headers()
            try:
                if mode == "stall":
                    self.wfile.write(BODY[:8])
                    self.wfile.flush()
                    time.sleep(2)
                    self.wfile.write(BODY[8:])
                elif mode == "trickle":
                    for part in BODY:
                        self.wfile.write(bytes([part]))
                        self.wfile.flush()
                        time.sleep(0.04)
                else:
                    self.wfile.write(BODY)
            except (OSError, BrokenPipeError):
                pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    def local_only(sock, address):
        assert address[0] in {"127.0.0.1", "::1"}, "no external HTTP is permitted"
        return _SOCKET_CONNECT(sock, address)
    monkeypatch.setattr(socket.socket, "connect", local_only)
    try:
        yield f"http://127.0.0.1:{server.server_port}/original", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def capture_request(url, *, seconds=5, expected=None):
    req = import_request()
    return {"schema_version": "official-source-capture-request/1", "request_id": "real-loopback",
            "source": {**req["source"], "source_url": url}, "mime_type": "text/html",
            "max_bytes": 1048576, "max_seconds": seconds, "max_cost_usd": "0",
            **({"expected_content_sha256": expected} if expected else {})}


def test_real_capture_then_known_same_sha_reuses_without_second_get(tmp_path, monkeypatch):
    with lake(tmp_path) as (_, catalog), loopback(monkeypatch) as (url, calls):
        first = flow.capture_official_source(catalog, request=capture_request(url))
        assert first["capture_receipt"]["http_status"] == 200
        assert first["capture_receipt"]["http_requests"] == 1
        assert first["download_events"] == 1
        req = capture_request(url, expected=hashlib.sha256(BODY).hexdigest())
        req["source"]["title"] *= 30
        second = flow.capture_official_source(catalog, request=req)
        assert second["source_ref"] == first["source_ref"]
        assert second["download_events"] == 0
        assert second["acquisition_usage"]["response_bytes"] == 0
        assert calls == ["/original"]
        assert not retained(catalog)


@pytest.mark.parametrize("mode", ["trickle", "stall"])
def test_real_total_deadline_stops_stream_and_retains_usage(tmp_path, monkeypatch, mode):
    with lake(tmp_path) as (_, catalog), loopback(monkeypatch, mode=mode) as (url, calls):
        began = time.monotonic()
        with pytest.raises(Exception) as caught:
            flow.capture_official_source(catalog, request=capture_request(url, seconds=0.35))
        elapsed = time.monotonic() - began
        assert caught.value.error_code == "deadline_exceeded"
        assert elapsed < 1.3, "total deadline must interrupt a blocking/drip read"
        assert 0 < caught.value.acquisition_usage["response_bytes"] < len(BODY)
        assert caught.value.acquisition_usage_complete is False
        assert caught.value.provider_started is True
        assert calls == ["/original"]
        assert not list((catalog.config.project_root / "companies").rglob("*.html"))
        items = retained(catalog)
        assert len(items) == 1
        state = json.loads(items[0].read_text(encoding="utf-8"))
        assert state["complete"] is False
        assert (items[0].parent / state["staged_name"]).read_bytes() == BODY[:state["request"]["capture_receipt"]["response_bytes"]]
        with pytest.raises(flow.OfficialSourceError, match="incomplete_capture_requires_new_request"):
            flow.recover_official_source(catalog, capture_id=state["capture_id"])
        assert calls == ["/original"]


def test_distinct_bytes_same_full_title_never_overwrite_original(tmp_path):
    changed = BODY.replace(b"new business", b"second business")
    with lake(tmp_path) as (_, catalog):
        first = flow.import_official_source(catalog, original=BODY, request=import_request())
        second = flow.import_official_source(catalog, original=changed, request=import_request(changed))
        assert first["source_ref"]["source_id"] != second["source_ref"]["source_id"]
        from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader
        for out, expected in ((first, BODY), (second, changed)):
            opened, _ = SourceVersionReader(catalog).open_described_version(SourceRef(**out["source_ref"]))
            assert opened.data == expected
            assert hashlib.sha256(opened.data).hexdigest() == out["source_ref"]["content_sha256"]


def test_capture_import_failure_retains_actual_http_receipt_then_recovers(tmp_path, monkeypatch):
    with lake(tmp_path) as (_, catalog), loopback(monkeypatch) as (url, calls):
        with monkeypatch.context() as patch:
            def fail(*_args, **_kwargs):
                raise OSError("fixture-catalog")
            patch.setattr(writer_module, "register_catalog_sources", fail)
            with pytest.raises(OSError) as caught:
                flow.capture_official_source(catalog, request=capture_request(url))
        state = json.loads(retained(catalog)[0].read_text(encoding="utf-8"))
        assert state["request"]["capture_receipt"]["http_status"] == 200
        assert caught.value.acquisition_usage["response_bytes"] == len(BODY)
        assert caught.value.acquisition_usage_complete is True
        out = flow.recover_official_source(catalog, capture_id=state["capture_id"])
        assert out["capture_receipt"]["http_requests"] == 1
        assert calls == ["/original"]


def test_journal_failure_never_masks_primary_or_discards_raw(tmp_path, monkeypatch):
    from company_wiki.source_catalog.acquisition_journal import AcquisitionJournal
    with lake(tmp_path) as (_, catalog):
        with monkeypatch.context() as patch:
            def primary(*_args, **_kwargs):
                raise OSError("fixture-copy-primary")
            def journal(*_args, **_kwargs):
                raise OSError("fixture-journal-secondary")
            patch.setattr(writer_module.shutil, "copyfile", primary)
            patch.setattr(AcquisitionJournal, "record", journal)
            with pytest.raises(OSError, match="fixture-copy-primary") as caught:
                flow.import_official_source(catalog, original=BODY, request=import_request())
        assert len(retained(catalog)) == 1
        assert "capture journal failed: OSError" in caught.value.__notes__
        out = flow.recover_official_source(catalog, capture_id=caught.value.capture_id)
        assert out["source_ref"]["content_sha256"] == hashlib.sha256(BODY).hexdigest()


def test_local_import_outcome_and_old_journal_records_are_compatible(tmp_path):
    from company_wiki.source_catalog.acquisition_journal import AcquisitionJournal
    with lake(tmp_path) as (_, catalog):
        catalog.config.catalog_dir.mkdir(parents=True, exist_ok=True)
        journal = AcquisitionJournal(catalog.config.catalog_dir)
        old = journal.record(request_id="old-request", outcome="downloaded_new", provider="old-provider")
        flow.import_official_source(catalog, original=BODY, request=import_request())
        attempts = journal.read_all()
        assert attempts[0] == old
        assert attempts[-1].outcome == "imported_original"


def test_impossible_canonical_root_is_named_and_retains_source(tmp_path, monkeypatch):
    with lake(tmp_path) as (_, catalog):
        with monkeypatch.context() as patch:
            original = writer_module._safe_component
            patch.setattr(writer_module, "_safe_component", lambda value, **kw: "x" * 200)
            with pytest.raises(writer_module.CanonicalImportError, match="canonical_root_path_limit") as caught:
                flow.import_official_source(catalog, original=BODY, request=import_request())
            assert original("Acme", limit=80) == "Acme"
        out = flow.recover_official_source(catalog, capture_id=caught.value.capture_id)
        assert out["source_ref"]["content_sha256"] == hashlib.sha256(BODY).hexdigest()


def _cli(root, request, *, operation):
    import os
    import subprocess
    import sys
    config = root / "config/catalog.json"
    config.parent.mkdir(exist_ok=True)
    config.write_text(json.dumps({"schema_version": "1.0", "catalog_dir": "catalog",
                                 "roots": [{"root_id": "company_raw", "path": "companies", "kind": "company_raw"}]}), encoding="utf-8")
    path = root / (operation + "-request.json")
    path.write_text(json.dumps(request), encoding="utf-8")
    repo = Path(__file__).resolve().parents[2]
    return subprocess.run([sys.executable, "-X", "utf8", "-B", "-m",
                           "company_wiki.source_catalog.official_source_cli", "--operation", operation,
                           "--config", str(config), "--request", str(path)],
                          cwd=root, env={**os.environ, "PYTHONPATH": str(repo / "src")},
                          capture_output=True, text=True, encoding="utf-8", timeout=20)


def test_public_capture_cli_zero_get_reuse_and_pathless_recovery(tmp_path, monkeypatch):
    with lake(tmp_path) as (root, catalog), loopback(monkeypatch) as (url, calls):
        first = _cli(root, capture_request(url), operation="capture")
        assert first.returncode == 0, first.stderr
        out = json.loads(first.stdout)
        assert str(root) not in first.stdout
        assert out["source_ref"]["content_sha256"] == hashlib.sha256(BODY).hexdigest()
        second = _cli(root, capture_request(url, expected=hashlib.sha256(BODY).hexdigest()), operation="capture")
        assert second.returncode == 0, second.stderr
        assert json.loads(second.stdout)["download_events"] == 0
        assert calls == ["/original"]
        def fail(*_args, **_kwargs):
            raise OSError("fixture-copy")
        # New bytes ensure this is a failed copy, not already-completed dedup.
        changed = BODY.replace(b"new business", b"new services")
        with monkeypatch.context() as patch:
            patch.setattr(writer_module.shutil, "copyfile", fail)
            with pytest.raises(OSError) as caught:
                flow.import_official_source(catalog, original=changed, request=import_request(changed))
        inv = _cli(root, {"schema_version": "official-source-recovery-request/1"}, operation="recover")
        assert inv.returncode == 0, inv.stderr
        assert json.loads(inv.stdout)["captures"][0]["capture_id"] == caught.value.capture_id
        recovered = _cli(root, {"schema_version": "official-source-recovery-request/1", "capture_id": caught.value.capture_id}, operation="recover")
        assert recovered.returncode == 0, recovered.stderr
        assert json.loads(recovered.stdout)["source_ref"]["content_sha256"] == hashlib.sha256(changed).hexdigest()
        assert str(root) not in recovered.stdout
        assert not retained(catalog)


def test_public_stall_cli_total_deadline_reports_observed_progress(tmp_path, monkeypatch):
    with lake(tmp_path) as (root, catalog), loopback(monkeypatch, mode="stall") as (url, calls):
        # The total deadline includes TLS transport setup. A slow Windows child
        # may stop before GET; that truthful outcome is not an acquisition bug.
        result = _cli(root, capture_request(url, seconds=0.35), operation="capture")
        assert result.returncode == 2
        failure = json.loads(result.stderr)
        assert failure["error_code"] == "deadline_exceeded"
        assert type(failure["provider_started"]) is bool
        received = failure["acquisition_usage"]["response_bytes"]
        assert type(received) is int and 0 <= received <= 8
        if not calls:
            assert calls == [] and failure["provider_started"] is False and received == 0
            assert failure["acquisition_usage_complete"] is True
        else:
            assert calls == ["/original"] and failure["provider_started"] is True
            assert failure["acquisition_usage_complete"] is False
        descriptor = retained(catalog)[0]
        state = json.loads(descriptor.read_text(encoding="utf-8"))
        raw = (descriptor.parent / state["staged_name"]).read_bytes()
        receipt = state["request"]["capture_receipt"]
        assert state["complete"] is False and state["capture_id"] == failure["capture_id"]
        assert raw == BODY[:received] and len(raw) == receipt["response_bytes"] == received
        assert hashlib.sha256(raw).hexdigest() == receipt["content_sha256"]
        assert receipt["acquisition_usage"] == failure["acquisition_usage"]
        assert receipt["usage_complete"] == failure["acquisition_usage_complete"]
        assert str(root) not in result.stderr and BODY.decode() not in result.stderr


def test_capture_receipt_write_failure_keeps_raw_and_actual_usage(tmp_path, monkeypatch):
    with lake(tmp_path) as (_, catalog), loopback(monkeypatch) as (url, calls):
        original_open = Path.open
        with monkeypatch.context() as patch:
            def open_path(path, *args, **kwargs):
                if path.name.endswith(".capture.json") and args and args[0] == "x":
                    raise OSError("fixture-receipt-storage")
                return original_open(path, *args, **kwargs)
            patch.setattr(Path, "open", open_path)
            with pytest.raises(OSError, match="fixture-receipt-storage") as caught:
                flow.capture_official_source(catalog, request=capture_request(url))
        assert caught.value.acquisition_usage["response_bytes"] == len(BODY)
        assert caught.value.acquisition_usage_complete is True
        assert caught.value.provider_started is True
        inv = flow.list_retained_official_captures(catalog)
        assert inv[0]["capture_id"] == caught.value.capture_id
        assert inv[0]["status"] == "receipt_unavailable"
        raw = catalog.config.catalog_dir / "staging" / (caught.value.capture_id + ".html")
        assert raw.read_bytes() == BODY
        with pytest.raises(flow.OfficialSourceError, match="retained_capture_receipt_unavailable"):
            flow.recover_official_source(catalog, capture_id=caught.value.capture_id)
        assert calls == ["/original"]


def test_local_original_mime_parser_runs_once(tmp_path, monkeypatch):
    with lake(tmp_path) as (_, catalog):
        actual = flow._validate_bytes
        calls = []
        def observe(body, mime):
            calls.append(mime)
            return actual(body, mime)
        monkeypatch.setattr(flow, "_validate_bytes", observe)
        flow.import_official_source(catalog, original=BODY, request=import_request())
        assert calls == ["text/html"], "local import must not repeat expensive format parsing"


def test_known_sha_retry_resumes_retained_capture_without_second_get(tmp_path, monkeypatch):
    with lake(tmp_path) as (_, catalog), loopback(monkeypatch) as (url, calls):
        with monkeypatch.context() as patch:
            def fail(*_args, **_kwargs):
                raise OSError("fixture-copy")
            patch.setattr(writer_module.shutil, "copyfile", fail)
            with pytest.raises(OSError):
                flow.capture_official_source(catalog, request=capture_request(url))
        retry = capture_request(url, expected=hashlib.sha256(BODY).hexdigest())
        retry["source"]["title"] *= 30
        out = flow.capture_official_source(catalog, request=retry)
        assert out["download_events"] == 0
        assert out["acquisition_usage"]["response_bytes"] == 0
        assert out["capture_receipt"]["http_requests"] == 1
        assert calls == ["/original"]
        assert not retained(catalog)


def test_shared_budget_receipt_reports_only_current_delta(tmp_path, monkeypatch):
    from company_wiki.source_catalog.download_budget import AcquisitionBudget
    with lake(tmp_path) as (_, catalog), loopback(monkeypatch) as (url, _):
        budget = AcquisitionBudget.from_limits(max_response_bytes=1024, max_seconds=10, max_cost_usd="1")
        budget.record_reported_usage(response_bytes=9, cost_usd="0.25")
        out = flow.capture_official_source(catalog, request=capture_request(url), budget=budget)
        assert out["acquisition_usage"]["response_bytes"] == len(BODY)
        assert out["acquisition_usage"]["cost_usd"] == "0.00"
        assert budget.response_bytes_used == 9 + len(BODY)
        assert str(budget.cost_usd_used) == "0.25"


def test_capture_different_sha_is_retained_and_cannot_recover_as_expected(tmp_path, monkeypatch):
    with lake(tmp_path) as (_, catalog), loopback(monkeypatch) as (url, calls):
        with pytest.raises(flow.OfficialSourceError, match="source_sha_mismatch") as caught:
            flow.capture_official_source(catalog, request=capture_request(url, expected="0" * 64))
        assert caught.value.acquisition_usage["response_bytes"] == len(BODY)
        assert caught.value.acquisition_usage_complete is True
        assert len(retained(catalog)) == 1
        with pytest.raises(flow.OfficialSourceError, match="source_sha_mismatch"):
            flow.recover_official_source(catalog, capture_id=caught.value.capture_id)
        assert calls == ["/original"]


# Independent M2 counterexamples: keep the initial delivery's contracts intact.
def _failed_local_capture(catalog, monkeypatch):
    with monkeypatch.context() as patch:
        def fail(*_args, **_kwargs):
            raise OSError("fixture-copy")
        patch.setattr(writer_module.shutil, "copyfile", fail)
        with pytest.raises(OSError, match="fixture-copy") as caught:
            flow.import_official_source(catalog, original=BODY, request=import_request())
    return caught.value.capture_id


def test_same_capture_id_replays_after_successful_response_is_lost(tmp_path, monkeypatch):
    with lake(tmp_path) as (root, catalog), loopback(monkeypatch) as (url, calls):
        with monkeypatch.context() as patch:
            def fail(*_args, **_kwargs):
                raise OSError("fixture-copy")
            patch.setattr(writer_module.shutil, "copyfile", fail)
            with pytest.raises(OSError) as caught:
                flow.capture_official_source(catalog, request=capture_request(url))
        capture_id = caught.value.capture_id
        first = flow.recover_official_source(catalog, capture_id=capture_id)
        assert not retained(catalog)
        # Simulate the caller losing the response and reopening its catalog.
        replay = _cli(root, {"schema_version": "official-source-recovery-request/1",
                             "capture_id": capture_id}, operation="recover")
        assert replay.returncode == 0, replay.stderr
        second = json.loads(replay.stdout)
        assert second["source_ref"] == first["source_ref"]
        assert second["capture_receipt"] == first["capture_receipt"]
        assert second["status"] == first["status"] == "imported_new"
        assert second["download_events"] == 0
        assert second["acquisition_usage"] == {"schema_version": "1.0", "response_bytes": 0, "cost_usd": "0"}
        third = flow.recover_official_source(catalog, capture_id=capture_id)
        assert third["source_ref"] == first["source_ref"]
        assert third["capture_receipt"]["http_requests"] == 1
        assert calls == ["/original"]
        assert str(root) not in replay.stdout
        records = list((catalog.config.catalog_dir / "staging").glob("*.result.json"))
        assert len(records) == 1 and records[0].stat().st_size <= 65536
        assert BODY not in records[0].read_bytes(), "completion projection must not duplicate source body"


def test_current_cap_applies_to_retained_canonical_and_completed_reuse(tmp_path, monkeypatch):
    with lake(tmp_path) as (root, catalog), loopback(monkeypatch) as (url, calls):
        with monkeypatch.context() as patch:
            def fail(*_args, **_kwargs):
                raise OSError("fixture-copy")
            patch.setattr(writer_module.shutil, "copyfile", fail)
            with pytest.raises(OSError) as caught:
                flow.capture_official_source(catalog, request=capture_request(url))
        capture_id = caught.value.capture_id
        descriptor = retained(catalog)[0]
        unchanged = descriptor.read_bytes()
        state = json.loads(unchanged)
        raw = descriptor.parent / state["staged_name"]
        retry = capture_request(url, expected=hashlib.sha256(BODY).hexdigest())
        retry["max_bytes"] = 10
        with pytest.raises(flow.OfficialSourceError, match="source_byte_limit"):
            flow.capture_official_source(catalog, request=retry)
        with pytest.raises(flow.OfficialSourceError, match="source_byte_limit"):
            flow.recover_official_source(catalog, capture_id=capture_id, max_bytes=10)
        refused = _cli(root, {"schema_version": "official-source-recovery-request/1",
                              "capture_id": capture_id, "max_bytes": 10}, operation="recover")
        assert refused.returncode == 2
        assert json.loads(refused.stderr)["error_code"] == "source_byte_limit"
        assert descriptor.read_bytes() == unchanged and raw.read_bytes() == BODY
        assert calls == ["/original"]
        accepted = flow.recover_official_source(catalog, capture_id=capture_id, max_bytes=len(BODY))
        assert accepted["source_ref"]["byte_size"] == len(BODY)
        with pytest.raises(flow.OfficialSourceError, match="source_byte_limit"):
            flow.capture_official_source(catalog, request=retry)
        with pytest.raises(flow.OfficialSourceError, match="source_byte_limit"):
            flow.recover_official_source(catalog, capture_id=capture_id, max_bytes=10)
        assert calls == ["/original"]


@pytest.mark.parametrize("damage", ["list", "null", "request_list", "receipt_list", "cap_bool", "mime_list", "source_kind_list", "status_list"])
def test_invalid_retained_json_shapes_are_safe_and_keep_original(tmp_path, monkeypatch, damage):
    with lake(tmp_path) as (root, catalog):
        capture_id = _failed_local_capture(catalog, monkeypatch)
        descriptor = retained(catalog)[0]
        state = json.loads(descriptor.read_text(encoding="utf-8"))
        raw = descriptor.parent / state["staged_name"]
        if damage == "list":
            state = []
        elif damage == "null":
            state = None
        elif damage == "request_list":
            state["request"] = []
        elif damage == "receipt_list":
            state["request"]["capture_receipt"] = []
        elif damage == "cap_bool":
            state["request"]["max_bytes"] = True
        elif damage == "mime_list":
            state["request"]["mime_type"] = []
        elif damage == "source_kind_list":
            state["request"]["source"]["document_kind"] = []
        else:
            state["request"]["capture_receipt"]["http_status"] = []
        descriptor.write_text(json.dumps(state), encoding="utf-8")
        inventory = flow.list_retained_official_captures(catalog)
        assert inventory == [{"capture_id": capture_id, "status": "unavailable"}]
        refused = _cli(root, {"schema_version": "official-source-recovery-request/1",
                              "capture_id": capture_id}, operation="recover")
        assert refused.returncode == 2, refused.stderr
        failure = json.loads(refused.stderr)
        assert failure["error_code"] == "invalid_retained_capture"
        assert "Traceback" not in refused.stderr and str(root) not in refused.stderr
        assert "acquisition_usage" not in failure and "provider_started" not in failure
        assert raw.read_bytes() == BODY and descriptor.is_file()


def test_completion_record_write_failure_keeps_raw_and_can_resume(tmp_path, monkeypatch):
    with lake(tmp_path) as (_, catalog):
        capture_id = _failed_local_capture(catalog, monkeypatch)
        descriptor = retained(catalog)[0]
        state = json.loads(descriptor.read_text(encoding="utf-8"))
        raw = descriptor.parent / state["staged_name"]
        original_replace = flow.os.replace
        with monkeypatch.context() as patch:
            def replace(src, dst):
                if str(dst).endswith(".result.json"):
                    raise OSError("fixture-completed-result-storage")
                return original_replace(src, dst)
            patch.setattr(flow.os, "replace", replace)
            with pytest.raises(OSError, match="fixture-completed-result-storage"):
                flow.recover_official_source(catalog, capture_id=capture_id)
        assert raw.read_bytes() == BODY and descriptor.is_file()
        from company_wiki.source_catalog.acquisition_journal import AcquisitionJournal
        assert any(row.outcome == "imported_original" for row in AcquisitionJournal(catalog.config.catalog_dir).read_all())
        first = flow.recover_official_source(catalog, capture_id=capture_id)
        second = flow.recover_official_source(catalog, capture_id=capture_id)
        assert first["source_ref"] == second["source_ref"]
        assert first["capture_receipt"] == second["capture_receipt"] == state["request"]["capture_receipt"]
        assert not raw.exists() and not descriptor.exists()


@pytest.mark.parametrize("damage", ["list", "receipt_list", "source_ref_list"])
def test_completed_result_wrong_shape_is_safe_json(tmp_path, monkeypatch, damage):
    with lake(tmp_path) as (root, catalog):
        capture_id = _failed_local_capture(catalog, monkeypatch)
        flow.recover_official_source(catalog, capture_id=capture_id)
        records = list((catalog.config.catalog_dir / "staging").glob("*.result.json"))
        assert len(records) == 1
        record = records[0]
        result = json.loads(record.read_text(encoding="utf-8"))
        if damage == "list":
            result = []
        elif damage == "receipt_list":
            result["capture_receipt"] = []
        else:
            result["source_ref"] = []
        record.write_text(json.dumps(result), encoding="utf-8")
        refused = _cli(root, {"schema_version": "official-source-recovery-request/1",
                              "capture_id": capture_id}, operation="recover")
        assert refused.returncode == 2
        assert json.loads(refused.stderr)["error_code"] == "invalid_completed_capture"
        assert "Traceback" not in refused.stderr and "acquisition_usage" not in json.loads(refused.stderr)
        assert len(list((root / "companies").rglob("*.html"))) == 1


def test_completed_replay_revalidates_actual_canonical_sha(tmp_path, monkeypatch):
    from company_wiki.source_catalog.source_reader import SourceReadError
    with lake(tmp_path) as (_, catalog):
        capture_id = _failed_local_capture(catalog, monkeypatch)
        first = flow.recover_official_source(catalog, capture_id=capture_id)
        location = catalog.store.fetchone("SELECT absolute_path FROM locations WHERE source_id=? AND role='original_primary'", (first["source_ref"]["source_id"],))
        canonical = Path(location["absolute_path"])
        canonical.write_bytes(BODY.replace(b"new", b"old"))  # Owned synthetic raw only.
        with pytest.raises(SourceReadError):
            flow.recover_official_source(catalog, capture_id=capture_id)
        assert canonical.read_bytes() != BODY
