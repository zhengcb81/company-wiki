"""FF public transport -> ET public CLI/worker -> CWP import -> verified original.

Only HTTP is replaced; all provider parsing, usage, subprocess supervision,
canonical storage and original verification execute their production owners.
"""
from __future__ import annotations

from datetime import date
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


CWP = Path(__file__).resolve().parents[1]
FF = Path(os.environ.get("FF_V2_CODE_ROOT", CWP.parent / "filing-fetch"))
ET = Path(os.environ.get("ET_CODE_ROOT", CWP.parent / "earnings-transcripts/earnings-transcripts"))
sys.path.insert(0, str(FF / "scripts"))
from transcript_tool_transport import EarningsTranscriptsTransport  # noqa: E402


def _fixture(tmp_path, monkeypatch):
    root = tmp_path / "lake"
    (root / "companies").mkdir(parents=True)
    (root / "config").mkdir()
    (root / "config/source_catalog.yaml").write_text(
        "schema_version: '1.0'\ncatalog_dir: .source_catalog\nroots:\n"
        "  - root_id: company_raw\n    path: companies\n    kind: company_raw\n"
        "    priority: 10\n    adapter_id: company_raw_v1\n    read_only: false\n",
        encoding="utf-8")
    scan_env = dict(os.environ, PYTHONPATH=str(CWP / "src"), PYTHONUTF8="1")
    scan = subprocess.run([sys.executable, "-B", "-m", "company_wiki.source_catalog.cli",
        "--config", str(root / "config/source_catalog.yaml"), "scan"],
        capture_output=True, env=scan_env, timeout=30)
    assert scan.returncode == 0, scan.stderr
    guard = tmp_path / "http-fixture"
    guard.mkdir()
    payload = [{"symbol": "ACME", "year": 2026, "quarter": 2,
        "date": "2026-09-20", "content": "CEO: " + "new products " * 1480000}]
    original = json.dumps(payload, separators=(",", ":")).encode()
    assert 17 * 1024 * 1024 < len(original) < 22 * 1024 * 1024
    original_path = guard / "provider-original.json"
    original_path.write_bytes(original)
    calls = guard / "http-calls.txt"
    (guard / "sitecustomize.py").write_text('''import os
from pathlib import Path
import socket
import requests
def refuse(*args, **kwargs):
 raise RuntimeError("No real network in decoupling integration")
socket.socket.connect = refuse
socket.create_connection = refuse
def request(self, method, url, **kwargs):
 if method.upper() != "GET" or not url.startswith("https://financialmodelingprep.com/"):
  raise RuntimeError("Unexpected HTTP operation")
 with Path(os.environ["DECOUPLING_HTTP_CALLS"]).open("a") as stream:
  stream.write("GET\\n")
 response = requests.Response()
 response.status_code = 200
 response.url = requests.Request(method, url, params=kwargs.get("params")).prepare().url
 response.headers = {"Content-Type": "application/json"}
 response._content = Path(os.environ["DECOUPLING_HTTP_BODY"]).read_bytes()
 response._content_consumed = True
 return response
requests.sessions.Session.request = request
''',encoding="utf-8")
    monkeypatch.setenv("PYTHONPATH", str(guard) + os.pathsep + str(CWP / "src"))
    monkeypatch.setenv("FMP_API_KEY", "synthetic-decoupling-token")
    monkeypatch.delenv("FMP_API_KEY_FILE", raising=False)
    monkeypatch.setenv("DECOUPLING_HTTP_BODY", str(original_path))
    monkeypatch.setenv("DECOUPLING_HTTP_CALLS", str(calls))
    identity = {"market": "US", "security_id": "ACME", "exchange": "NASDAQ",
        "canonical_name": "Acme Inc.", "verified": True, "active": True}
    query = dict(identity=identity, fiscal_year=2026, fiscal_quarter=2,
        as_of_date=date.today().isoformat(), provider=None)
    return root, original, calls, query


def test_large_fmp_original_reaches_storage_and_is_not_downloaded_twice(tmp_path, monkeypatch):
    root, original, calls, query = _fixture(tmp_path, monkeypatch)
    transport = EarningsTranscriptsTransport(wiki_root=root,
        transcript_tool=ET / "transcript_tool.py", deadline=time.monotonic()+100)
    assert transport.lookup_exact(**query) is None
    result = transport.acquire_exact(**query,
        acquisition_limits={"timeout_seconds": 90, "max_bytes": 22*1024*1024, "max_cost_usd": "0"})
    assert result["status"] == "downloaded", result
    assert result["provider_requests"] == 1
    assert result["provider_response_bytes"] == len(original)
    ref = result["source_ref"]
    assert ref["byte_size"] == len(original)
    assert ref["content_sha256"] == hashlib.sha256(original).hexdigest()
    from ff_company_wiki_connection import command_for
    opened = subprocess.run([*command_for(root, "open"), "--document-id", ref["document_id"],
        "--source-id", ref["source_id"], "--content-sha256", ref["content_sha256"],
        "--purpose", "preview"], capture_output=True, env=transport._wiki_env(), timeout=30)
    assert opened.returncode == 0, opened.stderr
    assert opened.stdout == original
    # Unknown publication remains unknown; it never causes another paid retrieval.
    again = transport.lookup_exact(**query)
    assert again is not None
    assert calls.read_text().splitlines() == ["GET"]
    assert not list(root.rglob("transcript-*"))


def test_true_response_limit_stops_before_import(tmp_path, monkeypatch):
    root, original, calls, query = _fixture(tmp_path, monkeypatch)
    transport = EarningsTranscriptsTransport(wiki_root=root,
        transcript_tool=ET / "transcript_tool.py", deadline=time.monotonic()+50)
    assert transport.lookup_exact(**query) is None
    result = transport.acquire_exact(**query,
        acquisition_limits={"timeout_seconds": 30, "max_bytes": 16*1024*1024, "max_cost_usd": "0"})
    assert result["status"] != "downloaded"
    assert result.get("reason") in {"byte_limit", "provider_result_oversized"}, result
    assert calls.read_text().splitlines() == ["GET"]
    assert not list((root / "companies").rglob("*.json"))
