"""M3-USAGE public E2E: real RF preparation -> FF CLI -> CWP CLI -> loopback provider.

Set ``FF_V2_CODE_ROOT`` and ``CWP_V2_CODE_ROOT`` to the isolated checkouts (the
same convention as test_source_ref_v2_three_repo_e2e.py). Every subprocess's
argv, stdout, stderr and exit code is captured to ``M3_E2E_LOG_ROOT`` when set.

Controls: US download (2 metadata GET + 1 gzip body GET across two CWP
invocations), US reuse (no body GET), CN download (second market), and a
missing-source operation whose observed usage must reach the RF preparation
error document unchanged. No production provider, key or model is touched; the
loopback server accepts loopback peers only.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from pathlib import Path
import subprocess
import sys

import pytest

from _rf_system_paths import RF_CODE_ROOT  # noqa: E402
RF_ROOT = RF_CODE_ROOT
sys.path.insert(0, str(RF_ROOT / "scripts"))

META1 = b'{"index": "fixture-metadata-one", "rows": 3}'
META2 = b'{"index": "fixture-metadata-two", "rows": 5, "updated": "2026-10-10"}'
BODY_ENTITY = b"Fixture annual report entity. " * 148
BODY_GZ = gzip.compress(BODY_ENTITY, mtime=0)

PROVIDER = r'''
import argparse, gzip, hashlib, http.client, json, os, sys
from pathlib import Path
from urllib.parse import urlsplit

p = argparse.ArgumentParser()
p.add_argument("mode"); p.add_argument("log"); p.add_argument("action"); p.add_argument("--staging-dir")
a = p.parse_args()
request = json.loads(sys.stdin.read())
with Path(a.log).open("a", encoding="utf-8") as f:
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
        self.entity = 0; self.wire = 0; self.exchanges = 0; self.last = None
    def record(self, response, body, coding):
        self.wire += len(body); self.exchanges += 1
        if coding == "identity":
            self.entity += len(body)
        self.last = observation(response)


meter = Meter()


def usage(cost):
    return {"schema_version": "1.0", "response_bytes": meter.entity, "cost_usd": cost}


def extra():
    return {"acquisition_cost_observed": True,
            "http_wire_bytes": meter.wire, "http_wire_usage_complete": True,
            "http_exchanges": meter.exchanges, "http_observation": meter.last}


market = "CN" if a.mode == "market-cn" else "US"
if a.action == "discover":
    for path, status in (("/meta1", 200), ("/meta2", 500 if a.mode == "metadata-error" else 200)):
        conn.request("GET", path, headers={"accept-encoding": "identity"})
        response = conn.getresponse()
        body = response.read()
        meter.record(response, body, "identity")
        if response.status != 200:
            # A real provider child failure; the initial fee counter is not a
            # provider billing receipt. CWP publishes its observation through
            # MAIN's structured_error sibling, then FF and RF preserve it.
            sys.stderr.write(json.dumps({"schema_version": "1.0", "status": "failed", "adapter": identity,
                "error": {"code": "upstream_unavailable", "retryable": False,
                          "message": "controlled metadata failure", "acquisition_usage": usage("0")},
                **extra(), "acquisition_cost_observed": False}) + "\n")
            raise SystemExit(1)
    candidates = [] if a.mode == "empty" else [{"candidate_id": "one", "provider": "loopback",
        "provider_document_id": "accession-one", "market": market, "entity": request["entity"],
        "title": "Fixture Annual Report", "source_url": "https://fixture.invalid/report.txt",
        "document_kind": "annual_report", "form_type": "10-K", "filing_date": "2026-03-20",
        "fiscal_year": request.get("fiscal_year"), "fiscal_period": "FY", "language": "en"}]
    sys.stdout.write(json.dumps({"schema_version": "1.0", "status": "ok", "adapter": identity,
                                 "acquisition_usage": usage("0.0003"), **extra(),
                                 "candidates": candidates}))
    raise SystemExit(0)

conn.request("GET", "/body", headers={"accept-encoding": "identity"})
response = conn.getresponse()
body = response.read()
coding = (response.getheader("content-encoding") or "identity").strip().lower()
entity = gzip.decompress(body) if coding != "identity" else body
meter.record(response, body, coding)
meter.entity += len(entity)
path = Path(a.staging_dir) / "report.txt"
path.write_bytes(entity)
sys.stdout.write(json.dumps({"schema_version": "1.0", "status": "ok", "adapter": identity,
    "acquisition_usage": usage("0.0006"), **extra(),
    "receipt": {"candidate_id": request["candidate_id"], "provider": request["provider"],
        "provider_document_id": request["provider_document_id"], "source_url": request["source_url"],
        "staged_path": str(path), "content_sha256": hashlib.sha256(entity).hexdigest(),
        "byte_size": len(entity), "mime_type": "text/plain",
        "retrieved_at": "2026-10-10T00:00:00Z", "http_status": 200,
        "adapter_name": identity["name"], "adapter_version": identity["version"]}}))
'''


class _Handler(BaseHTTPRequestHandler):
    server_mode = "ok"

    def do_GET(self):  # noqa: N802
        assert self.client_address[0] in ("127.0.0.1", "::1"), "loopback only"
        if self.path == "/meta1":
            self._serve(200, META1, "application/json", None)
        elif self.path == "/meta2":
            self._serve(500 if self.server_mode == "metadata-error" else 200,
                        META2, "application/json", None)
        elif self.path == "/body":
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
    _Handler.server_mode = "ok"
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server
    server.shutdown()
    server.server_close()


@pytest.fixture()
def roots():
    ff_root = os.environ.get("FF_V2_CODE_ROOT")
    cwp_root = os.environ.get("CWP_V2_CODE_ROOT")
    if not ff_root or not cwp_root:
        pytest.skip("set FF_V2_CODE_ROOT and CWP_V2_CODE_ROOT")
    ff = Path(ff_root).resolve(strict=True)
    cwp = Path(cwp_root).resolve(strict=True)
    assert (ff / "scripts" / "fetch_filing.py").is_file()
    assert (cwp / "src" / "company_wiki" / "source_catalog" / "cli.py").is_file()
    return ff, cwp


def _env(cwp_src: Path, base_url: str) -> dict:
    names = {"SYSTEMROOT", "WINDIR", "PATH", "PATHEXT", "COMSPEC", "TEMP", "TMP",
             "USERPROFILE", "APPDATA", "LOCALAPPDATA", "HOMEDRIVE", "HOMEPATH"}
    env = {key: value for key, value in os.environ.items() if key.upper() in names}
    env.update(PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1", PYTHON_DOTENV_DISABLED="1",
               COMPANY_WIKI_NETWORK="blocked", COMPANY_WIKI_REAL_LLM="0",
               M3_LOOPBACK_BASE_URL=base_url)
    env["PYTHONPATH"] = str(cwp_src) + os.pathsep + env.get("PYTHONPATH", "")
    return env


def _wiki(tmp_path: Path, ff_root: Path, cwp_root: Path, mode: str, port: int):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "m3_isolated_wiki", Path(__file__).parent / "e2e_support" / "isolated_wiki.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.PRODUCTION_WIKI = cwp_root
    wiki = module.IsolatedWiki(tmp_path / "wiki")
    script = tmp_path / "provider.py"
    script.write_text(PROVIDER, encoding="utf-8", newline="\n")
    log = tmp_path / "provider_calls.txt"
    project = tmp_path / "proj"
    project.mkdir()
    spec_dict = {"name": "m3-loopback", "version": "1.0.0", "interface": "json_command_v1",
                 "project_root": str(project), "config_root": None,
                 "command": [sys.executable, "-B", str(script), mode, str(log)],
                 "supports_acquisition_budget": True}
    (wiki.root / "config" / "source_acquisition.yaml").write_text(
        json.dumps({"schema_version": "1.1", "staging_root": str(wiki.root / ".source_catalog" / "staging"),
                    "timeout_seconds": 10,
                    "adapters": {m: dict(spec_dict, interface="json_command_v1" if m == "cn" else "dayu_sdk_bounded_v1")
                                 for m in ("cn", "hk", "us")}}),
        encoding="utf-8")
    return wiki, log


def _run(label, argv, env, cwd, log_root):
    result = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                            env=env, cwd=cwd, timeout=240, check=False)
    if log_root is not None:
        log_root.mkdir(parents=True, exist_ok=True)
        record = {"label": label, "argv": [str(item) for item in argv], "cwd": str(cwd),
                  "exit_code": result.returncode,
                  "stdout_sha256": hashlib.sha256(result.stdout.encode("utf-8")).hexdigest(),
                  "stderr_sha256": hashlib.sha256(result.stderr.encode("utf-8")).hexdigest()}
        (log_root / f"{label}.argv.json").write_text(json.dumps(record, ensure_ascii=False, indent=2),
                                                    encoding="utf-8")
        (log_root / f"{label}.stdout.txt").write_text(result.stdout, encoding="utf-8")
        (log_root / f"{label}.stderr.txt").write_text(result.stderr, encoding="utf-8")
    return result


def _request(market, security_id, company_query, *, missing=False):
    # security_id is derived by identify from the company identity; the v2
    # request schema does not accept it directly.
    return {"schema_version": "2.0", "company_query": company_query, "market": market,
            "document_kind": "annual_report", "fiscal_year": 2025,
            "as_of_date": "2026-10-10", "filing_intent": "fetch_if_missing",
            "acquisition_limits": {"max_bytes": 20000, "timeout_seconds": 30, "max_cost_usd": "1"}}


def test_full_chain_download_reuse_and_second_market(tmp_path, roots, loopback):
    ff_root, cwp_root = roots
    log_root = Path(os.environ["M3_E2E_LOG_ROOT"]) if os.environ.get("M3_E2E_LOG_ROOT") else None
    base_url = f"http://127.0.0.1:{loopback.server_address[1]}"
    cwp_src = cwp_root / "src"
    env = _env(cwp_src, base_url)

    wiki, log = _wiki(tmp_path, ff_root, cwp_root, "ok", loopback.server_address[1])
    request_file = tmp_path / "request.json"
    argv = [sys.executable, "-X", "utf8", "-B", str(RF_ROOT / "scripts" / "source_preparation.py"),
            "--request-file", str(request_file), "--result-envelope", "--allow-download",
            "--filing-fetch-root", str(ff_root),
            "--company-wiki-config", str(wiki.root / "company_wiki.json"),
            "--company-wiki-catalog-config", str(wiki.config_path),
            "--timeout-seconds", "120"]

    # 1) US download through the whole chain.
    request_file.write_text(json.dumps(_request("US", "AAPL", "Apple Inc.")), encoding="utf-8")
    result = _run("us_download", argv, env, tmp_path, log_root)
    assert result.returncode == 0, result.stderr + result.stdout
    value = json.loads(result.stdout)
    observation = value["filing_fetch"]["acquisition_observation"]
    assert observation["outcome"] == "downloaded_new"
    assert observation["usage_complete"] is True
    assert observation["http_exchanges"] == 3
    assert observation["wire_body_bytes"] == len(META1) + len(META2) + len(BODY_GZ)
    assert observation["entity_body_bytes"] == len(META1) + len(META2) + len(BODY_ENTITY)
    assert observation["wire_body_bytes"] < observation["entity_body_bytes"]
    assert observation["cost_usd"] == "0.0009"
    assert value["filing_fetch"]["filing"]["download_events"] == 1
    assert value["filing_fetch"]["downloads"] == 1
    assert "acquisition_failure" not in value["filing_fetch"]["filing"]

    # 2) Same request again: reuse, no body GET.
    result = _run("us_reuse", argv, env, tmp_path, log_root)
    assert result.returncode == 0, result.stderr + result.stdout
    value = json.loads(result.stdout)
    observation = value["filing_fetch"]["acquisition_observation"]
    assert observation["outcome"] in ("reused_before_download", "reused_after_discovery")
    assert value["filing_fetch"]["filing"]["download_events"] == 0
    assert observation["wire_body_bytes"] < len(META1) + len(META2) + len(BODY_GZ)
    assert observation["entity_body_bytes"] < len(META1) + len(META2) + len(BODY_ENTITY)
    assert value["filing_fetch"]["downloads"] == 0

    # 3) Second market on a fresh wiki: same semantics end to end.
    wiki_cn, _log_cn = _wiki(tmp_path / "cn", ff_root, cwp_root, "market-cn",
                             loopback.server_address[1])
    request_file_cn = tmp_path / "request_cn.json"
    request_file_cn.write_text(json.dumps(_request("CN", "300750", "宁德时代")), encoding="utf-8")
    argv_cn = [argv[0], argv[1], argv[2], str(RF_ROOT / "scripts" / "source_preparation.py"),
               "--request-file", str(request_file_cn), "--result-envelope", "--allow-download",
               "--filing-fetch-root", str(ff_root),
               "--company-wiki-config", str(wiki_cn.root / "company_wiki.json"),
               "--company-wiki-catalog-config", str(wiki_cn.config_path),
               "--timeout-seconds", "120"]
    result = _run("cn_download", argv_cn, env, tmp_path, log_root)
    assert result.returncode == 0, result.stderr + result.stdout
    value = json.loads(result.stdout)
    observation = value["filing_fetch"]["acquisition_observation"]
    assert observation["outcome"] == "downloaded_new"
    assert observation["http_exchanges"] == 3
    assert observation["cost_usd"] == "0.0009"
    assert log.read_text().splitlines()[:2] == ["discover", "fetch"]


def test_full_chain_missing_carries_observed_usage_to_rf_error(tmp_path, roots, loopback):
    ff_root, cwp_root = roots
    log_root = Path(os.environ["M3_E2E_LOG_ROOT"]) if os.environ.get("M3_E2E_LOG_ROOT") else None
    base_url = f"http://127.0.0.1:{loopback.server_address[1]}"
    env = _env(cwp_root / "src", base_url)

    wiki, _log = _wiki(tmp_path, ff_root, cwp_root, "empty", loopback.server_address[1])
    request_file = tmp_path / "request.json"
    request_file.write_text(json.dumps(_request("US", "AAPL", "Apple Inc.")), encoding="utf-8")
    argv = [sys.executable, "-X", "utf8", "-B", str(RF_ROOT / "scripts" / "source_preparation.py"),
            "--request-file", str(request_file), "--result-envelope", "--allow-download",
            "--filing-fetch-root", str(ff_root),
            "--company-wiki-config", str(wiki.root / "company_wiki.json"),
            "--company-wiki-catalog-config", str(wiki.config_path),
            "--timeout-seconds", "120"]
    result = _run("us_missing", argv, env, tmp_path, log_root)
    assert result.returncode == 3, result.stderr + result.stdout
    value = json.loads(result.stderr)
    observation = value["acquisition_observation"]
    assert observation["outcome"] == "missing"
    assert observation["http_exchanges"] == 2  # metadata discovery only
    assert observation["entity_body_bytes"] == len(META1) + len(META2)
    assert observation["cost_usd"] == "0.0003"
    assert value["calls"] >= 1 and value["downloads"] == 0
    assert "acquisition_failure" not in value  # a missing result is not a failure receipt


def test_full_chain_hard_failure_preserves_primary_cause_and_unknown_cost(tmp_path, roots, loopback):
    ff_root, cwp_root = roots
    log_root = Path(os.environ["M3_E2E_LOG_ROOT"]) if os.environ.get("M3_E2E_LOG_ROOT") else None
    _Handler.server_mode = "metadata-error"
    base_url = f"http://127.0.0.1:{loopback.server_address[1]}"
    env = _env(cwp_root / "src", base_url)
    wiki, calls = _wiki(tmp_path, ff_root, cwp_root, "metadata-error", loopback.server_address[1])
    request = tmp_path / "request.json"
    request.write_text(json.dumps(_request("US", "AAPL", "Apple Inc.")), encoding="utf-8")
    argv = [sys.executable, "-X", "utf8", "-B", str(RF_ROOT / "scripts" / "source_preparation.py"),
            "--request-file", str(request), "--result-envelope", "--allow-download",
            "--filing-fetch-root", str(ff_root),
            "--company-wiki-config", str(wiki.root / "company_wiki.json"),
            "--company-wiki-catalog-config", str(wiki.config_path), "--timeout-seconds", "120"]
    result = _run("us_hard_failure", argv, env, tmp_path, log_root)
    assert result.returncode == 3, result.stderr + result.stdout
    assert not result.stdout
    value = json.loads(result.stderr)
    assert value["error_code"] == "upstream"
    assert value["upstream_cause"]["code"] == "upstream_unavailable"
    assert value["acquisition_failure"]["code"] == "upstream_unavailable"
    observation = value["acquisition_observation"]
    assert observation["outcome"] == "failed"
    assert observation["provider_started"] is True
    assert observation["http_exchanges"] == 2
    assert observation["wire_body_bytes"] == len(META1) + len(META2)
    assert observation["entity_body_bytes"] == len(META1) + len(META2)
    assert observation["cost_usd"] is None  # Initial child counter zero is not a fee statement.
    assert observation["http_observation"]["status_code"] == 500
    assert value["downloads"] == 0
    assert calls.read_text().splitlines() == ["discover"]  # No automatic charged retry or body fetch.
