from __future__ import annotations


import base64




import json


import os


from pathlib import Path


import subprocess


import sys


import time




from typing import Any




from transcript_companion import resolve_companion_transcript




from transcript_tool_transport import EarningsTranscriptsTransport




_FIXTURE = Path(os.environ["FF_V2_CODE_ROOT"]) / "tests/fixtures" / "et_s0b" / "fmp_v2.fetched.json"


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
    monkeypatch.setenv("PYTHONPATH", str(source_root))
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
    tool.write_text(
        "import json, os, sys\n"
        "request = json.loads(sys.stdin.read())\n"
        "assert request['provider'] == 'fmp' and request['download_authorized'] is True\n"
        "assert request['fiscal_year'] == 2026 and request['fiscal_quarter'] == 3\n"
        "assert '--include-source-payload' in sys.argv\n"
        "assert '--allow-download' not in sys.argv\n"
        "with open(os.environ['ET_CALL_LOG'], 'a', encoding='utf-8') as stream: stream.write('call\\n')\n"
        "with open(os.environ['ET_FIXTURE_PATH'], encoding='utf-8') as stream: result = json.load(stream)\n"
        "result['request_id'] = request['request_id']\n"
        "print(json.dumps(result, separators=(',', ':')))\n",
        encoding="utf-8",
    )
    call_log = tmp_path / "et-calls.log"
    monkeypatch.setenv("ET_CALL_LOG", str(call_log))
    monkeypatch.setenv("ET_FIXTURE_PATH", str(_FIXTURE))
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
    original = base64.b64decode(
        json.loads(_FIXTURE.read_text(encoding="utf-8"))["provider_payload_base64"],
        validate=True,
    )
    originals = [
        path
        for path in (wiki_root / "companies").rglob("*")
        if path.is_file() and not path.name.endswith(".source.json")
    ]
    assert len(originals) == 1
    assert originals[0].read_bytes() == original
    assert str(wiki_root) not in json.dumps(first)

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
