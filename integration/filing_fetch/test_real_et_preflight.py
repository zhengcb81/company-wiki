"""W07 safe configured credential launch contracts; no live provider calls."""


from __future__ import annotations
import os




import json


import sys


import time


from pathlib import Path


import pytest


sys.path.insert(0, str(Path(os.environ["FF_V2_CODE_ROOT"]) / "scripts"))


import transcript_tool_transport as transport_module  # noqa: E402


SENTINEL = "w07-synthetic-credential-never-public"


@pytest.fixture(autouse=True)
def isolated_launch_environment(monkeypatch, tmp_path):
    # A failing mock must never expose the host process environment.
    safe = {name: transport_module.os.environ[name] for name in ("SYSTEMROOT", "PATH", "TEMP", "TMP", "PYTHONUTF8", "W07_ET_TOOL") if name in transport_module.os.environ}
    safe["USERPROFILE"] = str(tmp_path / "synthetic-profile")
    safe["HOME"] = str(tmp_path / "synthetic-profile")
    monkeypatch.setattr(transport_module.os, "environ", safe)


def _request():
    return {"request_id": "w07", "security_id": "MSFT", "exchange": "NASDAQ",
            "fiscal_year": 2026, "fiscal_quarter": 4, "as_of_date": "2026-10-08"}


def _limits():
    return {"timeout_seconds": 10, "max_bytes": 1000000, "max_cost_usd": "0.00"}


def _transport(tmp_path):
    tool = tmp_path / "transcript_tool.py"
    tool.write_text("# injected fixture", encoding="utf-8")
    return transport_module.EarningsTranscriptsTransport(
        wiki_root=tmp_path, transcript_tool=tool, deadline=time.monotonic() + 30)


def _failure(error_code="provider_entitlement_required"):
    result = {"schema_version": "earnings-transcript-result/2", "request_id": "w07",
              "status": "unavailable", "provider": "fmp", "error_code": error_code}
    usage = {"schema_version": "earnings-retrieval-usage/1", "request_id": "w07",
             "usage_complete": True, "usage": {"requests_used": 1, "response_bytes_used": 12}}
    return json.dumps(result).encode(), json.dumps(usage).encode(), 0


@pytest.mark.parametrize("exchange,reason", [("HKEX", "unsupported_market"),
    ("NASDAQ", "provider_credentials_missing"), ("TOKYO", "unsupported_exchange")])
def test_ff_real_et_cli_preserves_filing_and_measured_pre_http_zero(tmp_path, exchange, reason):
    from transcript_companion import resolve_companion_transcript
    from ff_v2_envelope import success_envelope
    from test_transcript_companion_transport import _request as companion_request, _filing
    configured = transport_module.os.environ.get("W07_ET_TOOL")
    if not configured:
        pytest.skip("W07 real ET checkout integration requires an explicit test tool path")
    tool = Path(configured)
    assert tool.is_file()
    transport = transport_module.EarningsTranscriptsTransport(wiki_root=tmp_path,
        transcript_tool=tool, deadline=time.monotonic() + 30)
    def empty_cwp_lookup(**kwargs):
        transport._pending = {"request_id": "w07", "kwargs": kwargs,
            "source_request": transport._source_request(identity=kwargs["identity"],
                fiscal_year=kwargs["fiscal_year"], fiscal_quarter=kwargs["fiscal_quarter"],
                as_of_date=kwargs["as_of_date"], allow_download=False,
                provider=kwargs.get("provider"))}
        return None
    transport.lookup_exact = empty_cwp_lookup
    filing = _filing()
    filing["company_identity"]["exchange"] = exchange
    if exchange == "HKEX":
        filing["company_identity"].update(market="HK", security_id="00700", ticker="00700")
    result = resolve_companion_transcript(request=companion_request(), filing_handle=filing, transport=transport)
    assert result["status"] == "provider_unavailable", result.get("reason")
    assert result["reason"] == reason
    assert result["provider_calls"] == 0
    assert result["provider_requests"] == 0
    assert result["provider_response_bytes"] == 0
    assert result["provider_usage_complete"] is True
    assert result["provider_started"] is False
    envelope = success_envelope(companion_request(), filing, result, {"calls": 0, "downloads": 0})
    assert envelope["status"] == "source_candidate"
    assert envelope["filing"]["source_ref"] == filing["source_ref"]
    assert envelope["transcript"]["provider_started"] is False


def _unicode_wire(value, key=SENTINEL):
    escaped = "".join("\\u%04x" % ord(char) for char in key)
    return json.dumps(value).replace(key, escaped).encode()


def _persistent_launch_config(tmp_path, *, tool_value=None):
    wiki = tmp_path / "wiki"
    (wiki / "config").mkdir(parents=True)
    (wiki / "config/source_catalog.yaml").write_text("schema_version: '1.0'\n", encoding="utf-8")
    tool = tmp_path / "tools" / "et.py"
    tool.parent.mkdir()
    tool.write_text(
        "import json, sys\n"
        "r=json.load(sys.stdin)\n"
        "print(json.dumps({'schema_version':'earnings-transcript-result/2',"
        "'request_id':r['request_id'],'status':'unsupported','provider':'fmp',"
        "'error_code':'unsupported_exchange'}))\n"
        "sys.stderr.write(json.dumps({'schema_version':'earnings-retrieval-usage/1',"
        "'request_id':r['request_id'],'usage_complete':True,'usage':"
        "{'requests_used':0,'response_bytes_used':0}})+'\\n')\n", encoding="utf-8")
    config = tmp_path / "company_wiki.json"
    config.write_text(json.dumps({"schema_version":"1.0", "company_wiki_root":str(wiki),
        "earnings_transcripts_tool":tool_value if tool_value is not None else "tools/et.py"}), encoding="utf-8")
    return wiki, tool, config
