"""M3-USAGE CWP integration: real CLI subprocess against a bounded loopback HTTP provider.

The loopback server binds 127.0.0.1 only and refuses any other peer; the
provider subprocess is the sole HTTP client and counts wire body bytes after
transfer decoding and before content decoding via ``http.client`` (no
transparent decompression). One operation performs two metadata GETs (discover
invocation) plus one gzip body GET (fetch invocation); the shared budget must
accumulate both invocations into one operation observation.

Failure-observation scenarios run the CLI through ``_patched_runner.py``,
which emulates the documented three-line MAIN patch for
``error_taxonomy.structured_error`` (see INTERFACE_CHANGE.md §6.1); the patch
itself is not part of this lane's commits.
"""
from __future__ import annotations

import gzip
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

import pytest


META1 = b'{"index": "fixture-metadata-one", "rows": 3}'
META2 = b'{"index": "fixture-metadata-two", "rows": 5, "updated": "2026-10-10"}'
BODY_TEXT = b"Fixture annual report entity. " * 148  # 9472 decompressed bytes
BODY_ENTITY = BODY_TEXT
BODY_GZ = gzip.compress(BODY_ENTITY, mtime=0)

_RUNNER = '''
import company_wiki.source_catalog.error_taxonomy as et
import company_wiki.source_catalog.cli as cli

_original = et.structured_error

def _patched(exc):
    result = _original(exc)
    try:
        from company_wiki.source_catalog.acquisition_observation import (
            published_acquisition_observation,
        )
    except ModuleNotFoundError:
        return result  # pre-GREEN producer: nothing to publish yet
    observation = published_acquisition_observation(exc)
    if observation is not None:
        result["acquisition_observation"] = observation
    return result

et.structured_error = _patched
raise SystemExit(cli.main())
'''

PROVIDER = r'''
import argparse, gzip, hashlib, http.client, json, os, sys, time
from pathlib import Path
from urllib.parse import urlsplit

p = argparse.ArgumentParser()
p.add_argument("mode"); p.add_argument("log"); p.add_argument("action"); p.add_argument("--staging-dir")
a = p.parse_args()
request = json.loads(sys.stdin.read())
log = Path(a.log)
with log.open("a", encoding="utf-8") as f:
    f.write(a.action + "\n")
identity = {"name": "m3-loopback", "version": "1.0.0"}
parts = urlsplit(os.environ["M3_LOOPBACK_BASE_URL"])
conn = http.client.HTTPConnection(parts.hostname, parts.port, timeout=20)


def observation(response):
    length = (response.getheader("content-length") or "").strip()
    size = int(length) if length.isdigit() and len(length) <= 20 else None
    return {"status_code": response.status,
            "mime_type": (response.getheader("content-type") or "").split(";")[0].strip().lower()[:128],
            "content_encoding": (response.getheader("content-encoding") or "identity").strip().lower()[:128],
            "wire_content_length": size}


class Meter:
    def __init__(self):
        self.entity = 0
        self.wire = 0
        self.exchanges = 0
        self.last = None

    def record(self, response, body, coding):
        self.wire += len(body)
        self.exchanges += 1
        if coding == "identity":
            self.entity += len(body)
        self.last = observation(response)


meter = Meter()


def usage(cost):
    return {"schema_version": "1.0", "response_bytes": meter.entity, "cost_usd": cost}


def extra():
    if a.mode == "legacy":
        return {}
    return {"acquisition_cost_observed": True,
            "http_wire_bytes": meter.wire, "http_wire_usage_complete": True,
            "http_exchanges": meter.exchanges, "http_observation": meter.last}


def fail(code, cost):
    sys.stderr.write(json.dumps({"schema_version": "1.0", "status": "failed", "adapter": identity,
                                 "error": {"code": code, "retryable": False,
                                           "message": "loopback controlled failure",
                                           "acquisition_usage": usage(cost)},
                                 **extra()}) + "\n")
    raise SystemExit(1)


def progress(cost):
    line = {"schema_version": "1.0", "status": "progress", "adapter": identity,
            "acquisition_usage": usage(cost), "http_wire_bytes": meter.wire,
            "http_wire_usage_complete": False, "http_exchanges": meter.exchanges,
            "http_observation": meter.last}
    sys.stderr.write(json.dumps(line) + "\n")
    sys.stderr.flush()


market = "CN" if a.mode == "market-cn" else "US"
if a.action == "discover" and a.mode == "remove-root":
    import shutil
    project_root = os.getcwd()
    os.chdir(os.path.dirname(project_root))
    shutil.rmtree(project_root, ignore_errors=True)
if a.action == "discover":
    try:
        conn.request("GET", "/meta1", headers={"accept-encoding": "identity"})
        response = conn.getresponse()
        body = response.read()
        meter.record(response, body, "identity")
        conn.request("GET", "/meta2", headers={"accept-encoding": "identity"})
        response = conn.getresponse()
        body = response.read()
        meter.record(response, body, "identity")
        if response.status != 200:
            fail("upstream_unavailable", "0.0003")
    except SystemExit:
        raise
    result = {"schema_version": "1.0", "status": "ok", "adapter": identity,
              "acquisition_usage": usage("0.0003"), **extra(),
              "candidates": [{"candidate_id": "one", "provider": "loopback",
                              "provider_document_id": "accession-one", "market": market,
                              "entity": request["entity"], "title": "Fixture Annual Report",
                              "source_url": "https://fixture.invalid/report.txt",
                              "document_kind": "annual_report", "form_type": "10-K",
                              "filing_date": "2026-03-20", "fiscal_year": request.get("fiscal_year"),
                              "fiscal_period": "FY", "language": "en"}]}
    sys.stdout.write(json.dumps(result))
    raise SystemExit(0)

if a.mode == "stall-silent":
    time.sleep(30)
progress("0.0002")
try:
    conn.request("GET", "/body", headers={"accept-encoding": "identity"})
    response = conn.getresponse()
    body = response.read()
except http.client.IncompleteRead as exc:
    meter.wire += len(exc.partial)
    meter.exchanges += 1
    meter.last = observation(response)
    fail("incomplete_response", "0.0002")
coding = (response.getheader("content-encoding") or "identity").strip().lower()
entity = gzip.decompress(body) if coding != "identity" else body
meter.record(response, body, coding)
meter.entity += len(entity)
path = Path(a.staging_dir) / "report.txt"
path.write_bytes(entity)
result = {"schema_version": "1.0", "status": "ok", "adapter": identity,
          "acquisition_usage": usage("0.0006"), **extra(),
          "receipt": {"candidate_id": request["candidate_id"], "provider": request["provider"],
                      "provider_document_id": request["provider_document_id"],
                      "source_url": request["source_url"], "staged_path": str(path),
                      "content_sha256": hashlib.sha256(entity).hexdigest(),
                      "byte_size": len(entity), "mime_type": "text/plain",
                      "retrieved_at": "2026-10-10T00:00:00Z", "http_status": 200,
                      "adapter_name": identity["name"], "adapter_version": identity["version"]}}
sys.stdout.write(json.dumps(result))
'''


class _LoopbackHandler(BaseHTTPRequestHandler):
    server_mode = "ok"

    def do_GET(self):  # noqa: N802 - http.server API
        assert self.client_address[0] in ("127.0.0.1", "::1"), "loopback accepts local peers only"
        if self.path == "/meta1":
            self._serve(200, META1, "application/json", None)
        elif self.path == "/meta2":
            if self.server_mode == "metadata-error":
                self._serve(500, b'{"error": "controlled failure"}', "application/json", None)
            else:
                self._serve(200, META2, "application/json", None)
        elif self.path == "/body":
            if self.server_mode == "body-truncate":
                self.send_response(200)
                self.send_header("content-type", "text/plain")
                self.send_header("content-encoding", "gzip")
                self.send_header("content-length", str(len(BODY_GZ)))
                self.end_headers()
                self.wfile.write(BODY_GZ[: len(BODY_GZ) // 2])
                self.close_connection = True
            elif self.server_mode == "body-stall":
                self.send_response(200)
                self.send_header("content-type", "text/plain")
                self.send_header("content-encoding", "gzip")
                self.send_header("content-length", str(len(BODY_GZ)))
                self.end_headers()
                self.wfile.write(BODY_GZ[: len(BODY_GZ) // 2])
                time.sleep(600)
            else:
                self._serve(200, BODY_GZ, "text/plain", "gzip")
        else:
            self._serve(404, b"{}", "application/json", None)

    def _serve(self, status, body, mime, coding):
        self.send_response(status)
        self.send_header("content-type", mime)
        if coding:
            self.send_header("content-encoding", coding)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


@pytest.fixture()
def loopback():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _LoopbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()


def _fixture_root(root: Path, mode: str):
    (root / "config").mkdir()
    (root / "companies").mkdir()
    script = root / "provider.py"
    script.write_text(PROVIDER, encoding="utf-8", newline="\n")
    runner = root / "_patched_runner.py"
    runner.write_text(_RUNNER, encoding="utf-8", newline="\n")
    log = root / "provider_calls.txt"
    catalog = root / "config" / "source_catalog.yaml"
    catalog.write_text(json.dumps({"schema_version": "1.0", "catalog_dir": str(root / "catalog"),
        "roots": [{"root_id": "company_raw", "kind": "company_raw", "path": str(root / "companies"), "priority": 10}]}), encoding="utf-8")
    if mode == "launch-fail":
        # A missing executable (not a missing script) is the real pre-launch
        # proof: the OS never started any provider process.
        command = [str(root / "missing_m3_provider.exe"), "-B", str(script), mode, str(log)]
    else:
        command = [sys.executable, "-B", str(script), mode, str(log)]
    project = root / "proj"
    project.mkdir()
    spec = {"name": "m3-loopback", "version": "1.0.0", "interface": "json_command_v1",
            "project_root": str(project), "config_root": None, "command": command,
            "supports_acquisition_budget": True}
    acquisition = root / "config" / "source_acquisition.yaml"
    acquisition.write_text(json.dumps({"schema_version": "1.1", "staging_root": str(root / "staging"),
        "timeout_seconds": 5, "adapters": {m: dict(spec, interface="json_command_v1" if m == "cn" else "dayu_sdk_bounded_v1")
                                           for m in ("cn", "hk", "us")}}), encoding="utf-8")
    return catalog, acquisition, log, runner


def _cli(root: Path, mode: str, port: int, *, market: str = "US", patched: bool = False,
         max_bytes: int = 20000):
    catalog, acquisition, log, runner = _fixture_root(root, mode)
    entry = [sys.executable, "-X", "utf8", "-B", str(runner)] if patched else [
        sys.executable, "-X", "utf8", "-B", "-m", "company_wiki.source_catalog.cli"]
    args = [*entry, "--config", str(catalog),
            "ensure", "--entity", "Fixture", "--market", market, "--security-id", "FIXURE" if market == "US" else "FIXCN",
            "--document-kind", "annual_report", "--fiscal-year", "2025", "--as-of-date", "2026-10-10",
            "--max-download-bytes", str(max_bytes), "--max-download-seconds", "3", "--max-download-cost-usd", "1",
            "--acquisition-config", str(acquisition), "--allow-download", "--source-ref-v2"]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["M3_LOOPBACK_BASE_URL"] = f"http://127.0.0.1:{port}"
    return args, env, log


def _run(tmp_path, server, mode, *, market="US", patched=False, max_bytes=20000):
    _LoopbackHandler.server_mode = mode if mode in ("metadata-error", "body-truncate", "body-stall") else "ok"
    with TemporaryDirectory(prefix="m3-", dir=tmp_path) as temporary:
        root = Path(temporary)
        args, env, log = _cli(root, mode, server.server_address[1], market=market, patched=patched,
                              max_bytes=max_bytes)
        result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                                env=env, timeout=60, check=False)
        captured = {
            "calls": log.read_text().splitlines() if log.exists() else [],
            "staged": sorted(str(item.relative_to(root))
                             for item in (root / "companies").rglob("*.txt")),
        }
        return result, captured


def test_success_operation_observation_accumulates_two_metadata_and_gzip_body(tmp_path, loopback):
    result, captured = _run(tmp_path, loopback, "ok")
    assert result.returncode == 0, (result.stdout, result.stderr)
    value = json.loads(result.stdout)
    observation = value["acquisition_observation"]
    assert observation["schema_version"] == "acquisition-observation/1"
    assert observation["usage_scope"] == "operation"
    assert observation["outcome"] == "downloaded_new"
    assert observation["provider_started"] is True
    assert observation["usage_complete"] is True
    # Operation total: 2 identity metadata bodies + gzip wire body, versus
    # 2 metadata bodies + the decompressed entity.
    assert observation["http_exchanges"] == 3
    assert observation["http_exchanges_complete"] is True
    assert observation["wire_body_bytes"] == len(META1) + len(META2) + len(BODY_GZ)
    assert observation["entity_body_bytes"] == len(META1) + len(META2) + len(BODY_ENTITY)
    assert observation["wire_body_bytes"] < observation["entity_body_bytes"]
    assert observation["wire_usage_complete"] is True
    assert observation["cost_usd"] == "0.0009"
    assert observation["http_observation"] == {"status_code": 200, "mime_type": "text/plain",
                                               "content_encoding": "gzip",
                                               "wire_content_length": len(BODY_GZ)}
    assert "path" not in json.dumps(observation)
    assert captured["calls"] == ["discover", "fetch"]
    assert captured["staged"]


def test_reuse_after_import_performs_no_body_get(tmp_path, loopback):
    _LoopbackHandler.server_mode = "ok"
    with TemporaryDirectory(prefix="m3-reuse-", dir=tmp_path) as temporary:
        root = Path(temporary)
        args, env, log = _cli(root, "ok", loopback.server_address[1])
        first = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                               env=env, timeout=60, check=False)
        assert first.returncode == 0, first.stderr
        second = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                                env=env, timeout=60, check=False)
        assert second.returncode == 0, second.stderr
        a, b = json.loads(first.stdout), json.loads(second.stdout)
        assert a["source_ref"] == b["source_ref"]
        assert b["download_events"] == 0
        observation = b["acquisition_observation"]
        assert observation["outcome"] in ("reused_after_discovery", "reused_before_download")
        # No body GET on reuse: wire never includes the gzip body again.
        assert observation["wire_body_bytes"] < len(META1) + len(META2) + len(BODY_GZ)
        assert observation["entity_body_bytes"] < len(META1) + len(META2) + len(BODY_ENTITY)
        assert observation["http_exchanges"] < 3
        assert log.read_text().splitlines()[:2] == ["discover", "fetch"]


def test_second_market_same_semantics(tmp_path, loopback):
    result, captured = _run(tmp_path, loopback, "market-cn", market="CN")
    assert result.returncode == 0, (result.stdout, result.stderr)
    value = json.loads(result.stdout)
    observation = value["acquisition_observation"]
    assert observation["outcome"] == "downloaded_new"
    assert observation["http_exchanges"] == 3
    assert observation["cost_usd"] == "0.0009"
    assert observation["wire_body_bytes"] == len(META1) + len(META2) + len(BODY_GZ)
    assert captured["calls"] == ["discover", "fetch"]


def test_metadata_error_keeps_observed_usage_and_safe_projection(tmp_path, loopback):
    result, _captured = _run(tmp_path, loopback, "metadata-error", patched=True)
    assert result.returncode == 1, (result.stdout, result.stderr)
    value = json.loads(result.stderr)
    observation = value["acquisition_observation"]
    assert observation["outcome"] == "failed"
    assert observation["provider_started"] is True
    assert observation["usage_complete"] is True  # final handled failure receipt
    assert observation["http_exchanges"] == 2
    assert observation["wire_body_bytes"] == len(META1) + len(b'{"error": "controlled failure"}')
    assert observation["cost_usd"] == "0.0003"
    assert observation["http_observation"]["status_code"] == 500
    # The closed seven-key failure DTO stays untouched next to the sibling.
    assert set(value["acquisition_failure"]) == {"schema_version", "code", "retryable",
                                                 "provider_started", "usage_complete",
                                                 "acquisition_usage", "usage_scope"}


def test_mid_body_truncation_keeps_partial_wire_lower_bound_semantics(tmp_path, loopback):
    result, _captured = _run(tmp_path, loopback, "body-truncate", patched=True)
    assert result.returncode == 1, (result.stdout, result.stderr)
    value = json.loads(result.stderr)
    observation = value["acquisition_observation"]
    assert observation["outcome"] == "failed"
    assert observation["usage_complete"] is True  # the receipt is final for what was observed
    assert observation["http_exchanges"] == 3
    expected_wire = len(META1) + len(META2) + len(BODY_GZ) // 2
    assert observation["wire_body_bytes"] == expected_wire
    assert observation["entity_body_bytes"] == len(META1) + len(META2)  # partial gzip cannot materialize
    assert observation["cost_usd"] == "0.0005"
    assert value["acquisition_failure"]["code"] == "incomplete_response"


def test_post_send_timeout_is_never_marked_free(tmp_path, loopback):
    result, _captured = _run(tmp_path, loopback, "body-stall", patched=True)
    assert result.returncode == 1, (result.stdout, result.stderr)
    value = json.loads(result.stderr)
    observation = value["acquisition_observation"]
    assert observation["outcome"] == "failed"
    assert observation["usage_complete"] is False  # hard kill: checkpoint lower bound
    assert observation["provider_started"] is True
    assert observation["http_exchanges"] == 2  # metadata exchanges from the checkpoint
    assert observation["http_exchanges_complete"] is False
    assert observation["wire_body_bytes"] == len(META1) + len(META2)
    assert observation["wire_usage_complete"] is False
    # A charged checkpoint cost is an observed lower bound, never "free".
    assert observation["cost_usd"] == "0.0005"


def test_timeout_without_receipt_keeps_fee_unknown_not_zero(tmp_path, loopback):
    result, _captured = _run(tmp_path, loopback, "stall-silent", patched=True)
    assert result.returncode == 1, (result.stdout, result.stderr)
    value = json.loads(result.stderr)
    observation = value["acquisition_observation"]
    assert observation["outcome"] == "failed"
    assert observation["usage_complete"] is False
    # The discover invocation did deliver a cost receipt; the hard-killed
    # fetch invocation never did. Observed lower bound, never "free".
    assert observation["cost_usd"] == "0.0003"
    assert observation["wire_usage_complete"] is False
    assert observation["http_exchanges"] == 2  # discover receipts still observed
    assert observation["http_exchanges_complete"] is False
    assert observation["wire_body_bytes"] == len(META1) + len(META2)


def test_legacy_receipts_degrade_to_unknown_not_zero(tmp_path, loopback):
    result, _captured = _run(tmp_path, loopback, "legacy")
    assert result.returncode == 0, (result.stdout, result.stderr)
    value = json.loads(result.stdout)
    observation = value["acquisition_observation"]
    assert observation["http_exchanges"] == 0  # never fabricated
    assert observation["http_exchanges_complete"] is None  # unmeasured, not zero-final
    assert observation["wire_body_bytes"] == 0
    assert observation["wire_usage_complete"] is False
    assert observation["entity_body_bytes"] == len(META1) + len(META2) + len(BODY_ENTITY)
    assert observation["cost_usd"] == "0.0009"
    assert observation["http_observation"] is None


def test_unlaunched_adapter_reports_zero_exchanges_and_unknown_fee(tmp_path, loopback):
    # First invocation cannot launch (missing executable). Through the Windows
    # bootstrap this carries no typed never-started proof, so provider_started
    # stays unknown (None), never fabricated; observed exchanges are zero and
    # the fee is unknown, not a known zero.
    result, _captured = _run(tmp_path, loopback, "launch-fail", patched=True)
    assert result.returncode == 1, (result.stdout, result.stderr)
    value = json.loads(result.stderr)
    observation = value["acquisition_observation"]
    assert observation["outcome"] == "failed"
    assert observation["provider_started"] is None
    assert observation["usage_complete"] is False
    assert observation["http_exchanges"] == 0
    assert observation["http_exchanges_complete"] is False
    assert observation["wire_body_bytes"] == 0
    assert observation["entity_body_bytes"] == 0
    assert observation["cost_usd"] is None


def test_fetch_budget_exhausted_before_launch_keeps_operation_totals(tmp_path, loopback):
    # The byte budget is exactly the discovery metadata total: discovery
    # finishes at the cap (valid), then the fetch pre-launch gate refuses new
    # provider work. The rejected invocation contributes exactly zero exchanges,
    # and the observed fee is preserved rather than re-zeroed.
    metadata = len(META1) + len(META2)
    result, captured = _run(tmp_path, loopback, "ok", patched=True, max_bytes=metadata)
    assert result.returncode == 1, (result.stdout, result.stderr)
    value = json.loads(result.stderr)
    observation = value["acquisition_observation"]
    assert observation["outcome"] == "failed"
    assert observation["provider_started"] is True  # discovery ran
    assert observation["usage_complete"] is True  # discovery complete, fetch zero
    assert observation["http_exchanges"] == 2  # fetch contributed exactly zero
    assert observation["http_exchanges_complete"] is True
    assert observation["entity_body_bytes"] == metadata
    assert observation["wire_body_bytes"] == metadata
    assert observation["cost_usd"] == "0.0003"  # discovery receipt survives
    failure = value["acquisition_failure"]
    assert failure["code"] == "acquisition_budget_exceeded"
    assert failure["acquisition_usage"] == {"schema_version": "1.0",
        "response_bytes": metadata, "cost_usd": "0.0003"}
    assert captured["calls"] == ["discover"]  # fetch never launched
