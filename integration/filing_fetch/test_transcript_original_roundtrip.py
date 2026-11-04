from __future__ import annotations


import hashlib

import json


import os


from pathlib import Path


import subprocess


import sys


import time




from typing import Any




from transcript_companion import resolve_companion_transcript




from transcript_tool_transport import EarningsTranscriptsTransport




_FIL_REF = {
    "schema_version": "2.0",
    "document_id": "urn:company-wiki:document:sha256:" + "a" * 64,
    "source_id": "urn:company-wiki:source:sha256:" + "a" * 64,
    "content_sha256": "a" * 64,
    "byte_size": 100,
    "mime_type": "application/pdf",
}


def _request() -> dict[str, Any]:
    return {
        "as_of_date": "2026-09-30",
        "companion_transcript": {
            "intent": "fetch_if_missing",
            "fiscal_year": 2026,
            "fiscal_quarter": 3,
            "provider": "fmp",
            "acquisition_limits": {
                "max_bytes": 1_000_000,
                "timeout_seconds": 10,
                "max_cost_usd": "0.00",
            },
        },
    }


def _filing() -> dict[str, Any]:
    return {
        "source_ref": _FIL_REF,
        "company_identity": {
            "canonical_name": "Microsoft Corporation",
            "market": "US",
            "security_id": "MSFT",
            "ticker": "MSFT",
            "exchange": "NASDAQ",
            "verified": True,
            "active": True,
        },
    }


def _completed(command: list[str], *, stdout: bytes = b"", stderr: bytes = b""):
    return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr=stderr)


def test_real_cwp_cli_import_and_unknown_publication_replay(tmp_path, monkeypatch) -> None:
    source_root = Path(os.environ["FILING_FETCH_V2_WIKI_SRC"]).resolve(strict=True)
    et_root = Path(os.environ["ET_CODE_ROOT"]).resolve(strict=True)
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join((str(tmp_path), str(source_root), str(et_root))))
    wiki_root = tmp_path / "company-wiki"
    (wiki_root / "companies").mkdir(parents=True)
    config = wiki_root / "config"
    config.mkdir()
    (config / "source_catalog.yaml").write_text(
        "schema_version: '1.0'\n"
        "catalog_dir: .source_catalog\n"
        "roots:\n"
        "  - root_id: company_raw\n"
        "    path: companies\n"
        "    kind: company_raw\n"
        "    priority: 10\n"
        "    adapter_id: company_raw_v1\n"
        "    read_only: false\n",
        encoding="utf-8",
    )
    tool = tmp_path / "transcript_tool.py"
    provider_fixture = tmp_path / "d4_fake_provider.py"
    provider_fixture.write_text(
        "import base64\n"
        "from pathlib import Path\n"
        "\n"
        "class Response:\n"
        "    def __init__(self, url, payload):\n"
        "        self.url = url\n"
        "        self.status_code = 200\n"
        "        self.headers = {'Content-Type': 'application/json'}\n"
        "        self.payload = payload\n"
        "    def iter_content(self, chunk_size):\n"
        "        for offset in range(0, len(self.payload), chunk_size):\n"
        "            yield self.payload[offset:offset + chunk_size]\n"
        "    def close(self):\n"
        "        pass\n"
        "\n"
        "class Session:\n"
        "    def __init__(self, spec):\n"
        "        self.spec = spec\n"
        "        self.headers = {}\n"
        "    def get(self, url, **kwargs):\n"
        "        with Path(self.spec['calls_file']).open('a', encoding='utf-8') as stream:\n"
        "            stream.write(url + '\\n')\n"
        "        if url != self.spec['url']:\n"
        "            raise AssertionError('unexpected provider URL: ' + url)\n"
        "        return Response(url, base64.b64decode(self.spec['payload_b64']))\n"
        "    def close(self):\n"
        "        pass\n"
        "\n"
        "def build_fake_session(spec, context):\n"
        "    return Session(spec)\n",
        encoding="utf-8",
    )
    tool.write_text(
        "import base64, io, json, os, sys\n"
        "from pathlib import Path\n"
        "et_root = Path(os.environ['ET_CODE_ROOT']).resolve(strict=True)\n"
        "sys.path.insert(0, str(et_root))\n"
        "from transcript_api import ProviderSettings\n"
        "from transcript_tool import main\n"
        "request = json.loads(sys.stdin.read())\n"
        "assert request['provider'] == 'fmp' and request['download_authorized'] is True\n"
        "assert request['fiscal_year'] == 2026 and request['fiscal_quarter'] == 3\n"
        "assert '--include-source-payload' in sys.argv\n"
        "assert '--allow-download' not in sys.argv\n"
        "os.environ['FMP_API_KEY'] = 'fake-key-for-d4-root-only'\n"
        "calls = Path(os.environ['ET_PROVIDER_CALLS'])\n"
        "temp_root = Path(os.environ['ET_TEMP_ROOT'])\n"
        "temp_root.mkdir(parents=True, exist_ok=False)\n"
        "provider_body = Path(os.environ['ET_PROVIDER_BODY']).read_bytes()\n"
        "spec = {'url': 'https://financialmodelingprep.com/stable/earning-call-transcript', 'payload_b64': base64.b64encode(provider_body).decode('ascii'), 'calls_file': str(calls)}\n"
        "sys.stdin = io.StringIO(json.dumps(request))\n"
        "rc = main(sys.argv[1:], _provider_settings=ProviderSettings(), _retrieval_launcher='d4_fake_provider:build_fake_session', _retrieval_spec=spec, _retrieval_temp_root=temp_root)\n"
        "with open(os.environ['ET_CALL_LOG'], 'a', encoding='utf-8') as stream: stream.write('call\\n')\n"
        "sys.stderr.buffer.write(b'diagnostic-noise' * 90000)\n"
        "sys.stderr.buffer.flush()\n"
        "raise SystemExit(rc)\n",
        encoding="utf-8",
    )
    call_log = tmp_path / "et-calls.log"
    provider_body = json.dumps(
        [{
            "symbol": "MSFT",
            "period": "Q3",
            "year": 2026,
            "date": "2026-07-22",
            "content": (
                "Management discussed customer demand, product launches, commercial execution, "
                "international expansion, data-center capacity, margins, and operating risks. "
            ) * 5,
        }],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    (tmp_path / "et-provider-body.json").write_bytes(provider_body)
    monkeypatch.setenv("ET_CALL_LOG", str(call_log))
    monkeypatch.setenv("ET_PROVIDER_CALLS", str(tmp_path / "et-provider-calls.jsonl"))
    monkeypatch.setenv("ET_PROVIDER_BODY", str(tmp_path / "et-provider-body.json"))
    monkeypatch.setenv("ET_TEMP_ROOT", str(tmp_path / "et-worker-runtime"))
    bootstrap = subprocess.run(
        [
            sys.executable,
            "-m",
            "company_wiki.source_catalog.cli",
            "--config",
            str(config / "source_catalog.yaml"),
            "scan",
            "--root-id",
            "company_raw",
        ],
        cwd=wiki_root,
        env=dict(os.environ),
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert bootstrap.returncode == 0, bootstrap.stderr.decode("utf-8", errors="replace")
    filing = _filing()
    request = _request()
    first_transport = EarningsTranscriptsTransport(
        wiki_root=wiki_root,
        transcript_tool=tool,
        deadline=time.monotonic() + 60,
    )
    first = resolve_companion_transcript(
        request=request,
        filing_handle=filing,
        transport=first_transport,
    )
    assert first["status"] == "downloaded", first
    assert first["publication_date"] is None
    assert first["as_of_cutoff_verified"] is False
    assert first["provider_calls"] == 1
    original = (tmp_path / "et-provider-body.json").read_bytes()
    original_sha256 = hashlib.sha256(original).hexdigest()
    assert first["source_ref"]["content_sha256"] == original_sha256
    assert first["source_ref"]["source_id"] == "urn:company-wiki:source:sha256:" + original_sha256
    originals = [
        path
        for path in (wiki_root / "companies").rglob("*")
        if path.is_file() and not path.name.endswith(".source.json")
    ]
    assert len(originals) == 1
    assert originals[0].read_bytes() == original
    assert str(wiki_root) not in json.dumps(first)
    assert (tmp_path / "et-provider-calls.jsonl").read_text(encoding="utf-8").splitlines() == [
        "https://financialmodelingprep.com/stable/earning-call-transcript"
    ]
    assert list((tmp_path / "et-worker-runtime").iterdir()) == []

    second_transport = EarningsTranscriptsTransport(
        wiki_root=wiki_root,
        transcript_tool=tool,
        deadline=time.monotonic() + 60,
    )
    second = resolve_companion_transcript(
        request=request,
        filing_handle=filing,
        transport=second_transport,
    )
    assert second["status"] == "unknown_publication", second
    assert second["source_ref"] == first["source_ref"]
    assert second["as_of_cutoff_verified"] is False
    assert second["provider_calls"] == 0
    assert call_log.read_text(encoding="utf-8").splitlines() == ["call"]
    originals_after = [
        path
        for path in (wiki_root / "companies").rglob("*")
        if path.is_file() and not path.name.endswith(".source.json")
    ]
    assert originals_after == originals
