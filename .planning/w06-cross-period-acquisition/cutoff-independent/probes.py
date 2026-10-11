"""Non-author probes: cutoff facts belong to ET; receipt mapping belongs to FF."""
import json
from pathlib import Path
import socket
import sys
import time

import pytest

ET = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w06/et-cutoff-root")
FF = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root")
sys.path.insert(0, str(ET))
sys.path.insert(0, str(FF / "scripts"))
import transcript_api as et
import transcript_tool_transport as ff
from transcript_companion import resolve_companion_transcript
from ff_v2_envelope import _transcript_result

TRACE = Path(__file__).with_name("trace.jsonl")
FMP = "https://financialmodelingprep.com/stable/earning-call-transcript"
QUOTE = "https://www.fool.com/quote/nasdaq/beta/"
LATE = "https://www.fool.com/earnings/call-transcripts/2025/03/21/beta-q2-2024-earnings-transcript/"
BOUNDARY = LATE.replace("/03/21/", "/03/20/")
BODY = b"<html><body><h1>Beta Q2 2024 Call</h1><main><p>Original English business update, sales progress and expansion. " + b"Commercial launches and overseas demand. " * 12 + b"</p></main></body></html>"


def trace(kind, **data):
    with TRACE.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"kind": kind, **data}, ensure_ascii=False) + "\n")


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def reject(*args, **kwargs):
        raise AssertionError("independent cutoff review is offline")
    monkeypatch.setattr(socket.socket, "connect", reject)
    monkeypatch.setattr(socket, "getaddrinfo", reject)
    monkeypatch.setattr(socket, "create_connection", reject)


def request(provider="fmp"):
    return {"schema_version": "earnings-transcript-request/1", "request_id": "independent-cutoff-beta",
            "ticker": "BETA", "exchange": "nasdaq", "fiscal_year": 2024, "fiscal_quarter": 2,
            "as_of_date": "2025-03-20", "provider": provider, "download_authorized": True,
            "timeout_seconds": 5, "max_body_bytes": 100000, "max_response_bytes": 150000,
            "max_cost_usd": "0"}


class Response:
    def __init__(self, url, data, mime="application/json"):
        self.url, self.status_code = url, 200
        self.headers, self.data = {"Content-Type": mime}, data
    def iter_content(self, chunk_size):
        yield self.data
    def close(self):
        pass


class Session:
    def __init__(self, responses):
        self.headers, self.responses, self.calls = {}, responses, []
    def get(self, url, **kwargs):
        self.calls.append(url)
        assert url in self.responses, "unexpected extra provider request"
        return self.responses[url]
    def close(self):
        pass


def source_row(**updates):
    row = {"symbol": "BETA", "year": 2024, "quarter": 2, "date": "2025-03-21",
           "content": "Original language business update and overseas launch details. " * 8}
    row.update(updates)
    return row


@pytest.mark.parametrize("case,rows,status,code", [
    ("target_late", [source_row()], "not_found", "call_after_as_of"),
    ("empty", [], "not_found", None),
    ("wrong_company", [source_row(symbol="OTHER")], "provenance_rejected", "provider_identity_or_host"),
    ("wrong_quarter", [source_row(quarter=1)], "provenance_rejected", "provider_identity_or_host"),
    ("wrong_year", [source_row(year=2023)], "provenance_rejected", "provider_identity_or_host"),
    ("bad_date", [source_row(date="2025-3-21")], "provenance_rejected", "provider_identity_or_host"),
    ("boundary", [source_row(date="2025-03-20")], "fetched", None),
    ("two_valid_future", [source_row(), source_row(date="2025-03-22")], "ambiguous", None),
])
@pytest.mark.parametrize("version", [1, 2])
def test_fmp_scope_precedes_cutoff(case, rows, status, code, version, tmp_path):
    payload = json.dumps(rows).encode()
    session = Session({FMP: Response(FMP, payload)})
    before = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*"))
    result = et.fetch_transcript(request(), session_factory=lambda: session,
                                 fmp_api_key="independent-synthetic-key", include_source_payload=version == 2)
    assert result["schema_version"] == f"earnings-transcript-result/{version}"
    assert result["status"] == status and result.get("error_code") == code
    assert session.calls == [FMP]
    if status == "fetched":
        assert result["publication_date"] is None and result["as_of_cutoff_verified"] is False
    else:
        assert "content_utf8" not in result and "provider_payload_base64" not in result
    assert before == sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*"))
    trace("fmp", case=case, version=version, status=result["status"], code=result.get("error_code"), calls=session.calls)


@pytest.mark.parametrize("operation", ["fetch", "discover"])
@pytest.mark.parametrize("case,urls,status,code", [
    ("target_late", [LATE], "not_found", "publication_after_as_of"),
    ("empty", [], "not_found", None),
    ("wrong_quarter_late", [LATE.replace("q2-2024", "q1-2024")], "not_found", None),
    ("wrong_company_late", [LATE.replace("beta-q2", "other-q2")], "not_found", None),
    ("boundary", [BOUNDARY], "eligible", None),
])
def test_motley_target_period_owns_publication_cause(operation, case, urls, status, code, tmp_path):
    listing = ("<html><body>" + "".join(f'<a href="{url}">call</a>' for url in urls) + "</body></html>").encode()
    session = Session({QUOTE: Response(QUOTE, listing, "text/html"),
                       BOUNDARY: Response(BOUNDARY, BODY, "text/html")})
    method = et.fetch_transcript if operation == "fetch" else et.discover_transcripts
    result = method(request("motley_fool"), session_factory=lambda: session,
                    provider_settings=et.ProviderSettings(motley_fool_enabled=True))
    expected = ("fetched" if operation == "fetch" else "discovered") if status == "eligible" else status
    assert result["status"] == expected and result.get("error_code") == code
    assert len(session.calls) == (2 if case == "boundary" and operation == "fetch" else 1)
    if expected == "not_found":
        assert "content_utf8" not in result and "provider_payload_base64" not in result
    assert list(tmp_path.rglob("*")) == []
    trace("motley", case=case, operation=operation, status=result["status"], code=result.get("error_code"), calls=session.calls)


def ff_request():
    return {"request_id": "independent-cutoff-beta", "security_id": "BETA", "exchange": "NASDAQ",
            "fiscal_year": 2024, "fiscal_quarter": 2, "as_of_date": "2025-03-20"}


def limits():
    return {"timeout_seconds": 5, "max_bytes": 150000, "max_cost_usd": "0"}


def receipt(**updates):
    result = {"schema_version": "earnings-transcript-result/2", "request_id": "independent-cutoff-beta",
              "status": "not_found", "provider": "fmp", "fiscal_period": "2024-Q2", "candidate_count": 0,
              "error_code": "call_after_as_of"}
    result.update(updates)
    return result


def usage(request_id="independent-cutoff-beta"):
    return json.dumps({"schema_version": "earnings-retrieval-usage/1", "request_id": request_id,
                       "usage_complete": True, "usage": {"requests_used": 1, "response_bytes_used": 987}}).encode()


def transport(tmp_path, monkeypatch, out, err, code=0):
    tool = tmp_path / "injected_et.py"
    tool.write_text("# never executed; injected receipt boundary", encoding="utf-8")
    obj = ff.EarningsTranscriptsTransport(wiki_root=tmp_path, transcript_tool=tool, deadline=time.monotonic() + 20)
    monkeypatch.setattr(obj, "_et_environment", lambda: ({}, None))
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        return out, err, code
    monkeypatch.setattr(ff, "_run_bounded_json", run)
    return obj, calls


@pytest.mark.parametrize("schema,diagnostic,reason,complete", [
    ("earnings-transcript-result/2", "call_after_as_of", "call_after_as_of", True),
    ("earnings-transcript-result/2", "publication_after_as_of", "publication_after_as_of", True),
    ("earnings-transcript-result/1", None, "exact_transcript_missing", True),
    ("earnings-transcript-result/2", "unbounded-child-text", "exact_transcript_missing", True),
    ("earnings-transcript-result/2", ["call_after_as_of"], "exact_transcript_missing", True),
    ("earnings-transcript-result/2", "call_after_as_of", "call_after_as_of", False),
])
def test_ff_closed_reason_and_observed_usage(tmp_path, monkeypatch, schema, diagnostic, reason, complete):
    payload = receipt(schema_version=schema)
    if diagnostic is None:
        payload.pop("error_code")
    else:
        payload["error_code"] = diagnostic
    obj, calls = transport(tmp_path, monkeypatch, json.dumps(payload).encode(), usage() if complete else b"")
    result = obj._et_result(request=ff_request(), limits=limits())
    assert result["status"] == "not_found" and result["reason"] == reason
    assert result["provider_usage_complete"] is complete
    assert result["provider_requests"] == (1 if complete else None)
    assert result["provider_response_bytes"] == (987 if complete else None)
    assert len(calls) == 1 and "source_ref" not in result
    assert "unbounded-child-text" not in json.dumps(result)
    trace("ff_projection", input=payload, output=result, launches=len(calls))


@pytest.mark.parametrize("field,value,exit_code", [
    ("request_id", "different-task", 0),
    ("schema_version", "earnings-transcript-result/3", 0),
    ("fiscal_period", "2024-Q1", 0),
    ("candidate_count", True, 0),
    (None, None, 2),
])
def test_ff_one_receipt_binding_refuses_false_cutoff(tmp_path, monkeypatch, field, value, exit_code):
    payload = receipt()
    if field:
        payload[field] = value
    obj, calls = transport(tmp_path, monkeypatch, json.dumps(payload).encode(), usage(), exit_code)
    result = obj._et_result(request=ff_request(), limits=limits())
    assert result["status"] == "provider_unavailable"
    assert result["reason"] == ("provider_tool_failed" if exit_code else "provider_result_invalid")
    assert result["provider_requests"] == 1 and result["provider_response_bytes"] == 987
    assert result["provider_usage_complete"] is True
    assert len(calls) == 1 and "call_after_as_of" not in json.dumps(result)
    trace("ff_binding", field=field, output=result, launches=len(calls))


@pytest.mark.parametrize("wire", [b"{broken-json", b"[]", b"null"])
def test_ff_malformed_stdout_does_not_erase_valid_usage(tmp_path, monkeypatch, wire):
    obj, calls = transport(tmp_path, monkeypatch, wire, usage())
    result = obj._et_result(request=ff_request(), limits=limits())
    trace("ff_malformed_wire", wire=wire.decode(), output=result, launches=len(calls))
    assert result["status"] == "provider_unavailable" and result["reason"] == "provider_result_invalid"
    assert result["provider_usage_complete"] is True
    assert result["provider_requests"] == 1 and result["provider_response_bytes"] == 987
    assert len(calls) == 1


@pytest.mark.parametrize("diagnostic", ["call_after_as_of", "publication_after_as_of"])
def test_public_companion_stops_before_import_and_keeps_usage(tmp_path, monkeypatch, diagnostic):
    tool = tmp_path / "injected_et.py"
    tool.write_text("# receipt only", encoding="utf-8")
    obj = ff.EarningsTranscriptsTransport(wiki_root=tmp_path, transcript_tool=tool, deadline=time.monotonic() + 20)
    monkeypatch.setattr(obj, "_et_environment", lambda: ({}, None))
    commands = []
    def run(command, **kwargs):
        commands.append(command)
        if "source_query_cli" in " ".join(command):
            return json.dumps({"schema_version": "2.0", "status": "not_found", "reason": "no_local_match",
                               "request_id": "independent-cutoff-beta", "matches": [], "candidates": [],
                               "source_read_policy_sha256": "d" * 64}).encode(), b"", 0
        assert str(tool) in command, "no import/open process may run for cutoff"
        return json.dumps(receipt(error_code=diagnostic)).encode(), usage(), 0
    monkeypatch.setattr(ff, "_run_bounded_json", run)
    option = {"intent": "fetch_if_missing", "provider": "fmp", "fiscal_year": 2024,
              "fiscal_quarter": 2, "acquisition_limits": limits()}
    filing = {"company_identity": {"canonical_name": "Beta Systems", "market": "US", "security_id": "BETA",
                                   "ticker": "BETA", "exchange": "NASDAQ", "active": True, "verified": True}}
    result = resolve_companion_transcript(request={"as_of_date": "2025-03-20", "companion_transcript": option},
                                         filing_handle=filing, transport=obj)
    public = _transcript_result(result)
    trace("public_companion", output=public, commands=commands)
    assert public["status"] == "not_found" and public["reason"] == diagnostic
    assert public["provider_requests"] == 1 and public["provider_response_bytes"] == 987
    assert public["provider_usage_complete"] is True and "source_ref" not in public
    assert len(commands) == 2 and sum(str(tool) in command for command in commands) == 1
    assert obj.company_wiki_calls == 1
