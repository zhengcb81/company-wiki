"""Write only ROOT-assigned FF tests, after freezing the read-only baseline."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root")
OUT = Path(__file__).resolve().parent
OWNED = ["scripts/transcript_tool_transport.py", "scripts/et_v2_contract.py",
         "tests/test_transcript_launch_contract.py", "tests/test_transcript_companion_transport.py",
         "tests/test_et_s0b_contract.py"]

def entry(rel):
    data = (ROOT / rel).read_bytes()
    return {"path": rel, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}

protected = subprocess.check_output(["git", "ls-files", "--", "tools/offline_contract_matrix",
    "tests/fixtures/w06_contract_matrix", "tests/fixtures/et_s0b", "tests/golden",
    "tests/test_w06*", "docs/handoffs/w06-ff-matrix", ".planning/w06-ff-matrix"],
    cwd=ROOT).decode().splitlines()
baseline = {"schema_version": "ff-cutoff-baseline/1", "base":
    "88997b85ce5be20dc3d563b5c040706590df6dbb",
    "owned": [entry(p) for p in OWNED], "protected": [entry(p) for p in protected]}
(OUT / "baseline.json").write_text(json.dumps(baseline, indent=2), encoding="utf-8")

LAUNCH = '''


@pytest.mark.parametrize("schema,diagnostic,reason", [
    ("earnings-transcript-result/2", "call_after_as_of", "call_after_as_of"),
    ("earnings-transcript-result/1", "publication_after_as_of", "publication_after_as_of"),
    ("earnings-transcript-result/2", None, "exact_transcript_missing"),
    ("earnings-transcript-result/1", None, "exact_transcript_missing"),
    ("earnings-transcript-result/2", "child_free_text_never_public", "exact_transcript_missing"),
    ("earnings-transcript-result/2", ["call_after_as_of"], "exact_transcript_missing"),
    ("earnings-transcript-result/2", "provider_deadline", "exact_transcript_missing"),
])
@pytest.mark.parametrize("usage_complete", [True, False])
def test_not_found_result_preserves_date_cause_without_claiming_provider_outage(
    tmp_path, monkeypatch, schema, diagnostic, reason, usage_complete,
):
    result = {"schema_version": schema, "request_id": "w07", "provider": "fmp",
              "status": "not_found", "fiscal_period": "2026-Q4", "candidate_count": 0}
    if diagnostic is not None:
        result["error_code"] = diagnostic
    usage = {"schema_version": "earnings-retrieval-usage/1", "request_id": "w07",
             "usage_complete": True, "usage": {"requests_used": 1, "response_bytes_used": 512}}
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        return json.dumps(result).encode(), json.dumps(usage).encode() if usage_complete else b"", 0
    monkeypatch.setattr(transport_module, "_run_bounded_json", run)
    # A synthetic environment seam; never resolve/read any host credential.
    transport = _transport(tmp_path)
    monkeypatch.setattr(transport, "_et_environment", lambda: ({}, None))
    public = transport._et_result(request=_request(), limits=_limits())
    assert public["status"] == "not_found"
    assert public["reason"] == reason
    assert public["retryable"] is False
    assert len(calls) == 1
    assert public["provider_calls"] == 1
    assert public["provider_usage_complete"] is usage_complete
    assert public["provider_requests"] == (1 if usage_complete else None)
    assert public["provider_response_bytes"] == (512 if usage_complete else None)
    assert public["provider_started"] is (True if usage_complete else None)
    assert "child_free_text_never_public" not in json.dumps(public)
    assert "source_ref" not in public
'''

COMPANION = '''


@pytest.mark.parametrize("diagnostic,reason", [
    ("call_after_as_of", "call_after_as_of"),
    ("publication_after_as_of", "publication_after_as_of"),
    (None, "exact_transcript_missing"),
])
@pytest.mark.parametrize("usage_complete", [True, False])
def test_not_found_transcript_stops_before_import_and_survives_public_envelope(
    tmp_path, monkeypatch, diagnostic, reason, usage_complete,
):
    from ff_v2_envelope import _transcript_result

    tool = tmp_path / "transcript_tool.py"
    tool.write_text("# synthetic supplier receipt only", encoding="utf-8")
    request_id = "urn:company-wiki:source-request:sha256:" + "c" * 64
    commands = []
    def run(command, *, input_bytes=None, **kwargs):
        commands.append(command)
        if "source_query_cli" in " ".join(command):
            payload = {"schema_version": "2.0", "status": "not_found", "reason": "no_local_match",
                       "request_id": request_id, "matches": [], "candidates": [],
                       "source_read_policy_sha256": "d" * 64}
            return json.dumps(payload).encode(), b"", 0
        assert str(tool) in command, "not_found must never import or open a source"
        request = json.loads(input_bytes)
        payload = {"schema_version": "earnings-transcript-result/2", "request_id": request["request_id"],
                   "provider": "fmp", "status": "not_found", "fiscal_period": "2026-Q3",
                   "candidate_count": 0}
        if diagnostic is not None:
            payload["error_code"] = diagnostic
        receipt = {"schema_version": "earnings-retrieval-usage/1", "request_id": request_id,
                   "usage_complete": True, "usage": {"requests_used": 1, "response_bytes_used": 512}}
        return json.dumps(payload).encode(), json.dumps(receipt).encode() if usage_complete else b"", 0
    monkeypatch.setattr(transcript_tool_transport, "_run_bounded_json", run)
    transport = EarningsTranscriptsTransport(wiki_root=tmp_path, transcript_tool=tool,
                                            deadline=time.monotonic() + 30)
    monkeypatch.setattr(transport, "_et_environment", lambda: ({}, None))
    result = resolve_companion_transcript(request=_request(), filing_handle=_filing(), transport=transport)
    public = _transcript_result(result)
    assert public["status"] == "not_found"
    assert public["reason"] == reason
    assert public["retryable"] is False
    assert public["provider_calls"] == 1
    assert public["provider_usage_complete"] is usage_complete
    assert public["provider_requests"] == (1 if usage_complete else None)
    assert public["provider_response_bytes"] == (512 if usage_complete else None)
    assert public["provider_started"] is (True if usage_complete else None)
    assert "source_ref" not in public
    assert len(commands) == 2
    assert sum(str(tool) in command for command in commands) == 1
    assert transport.company_wiki_calls == 1
'''

BOUNDARY = '''


def _not_found_receipt(diagnostic=None):
    request = fixture("fmp_v2.request.json")
    result = {"schema_version": "earnings-transcript-result/2", "request_id": request["request_id"],
              "status": "not_found", "provider": "fmp", "fiscal_period": "2026-Q3",
              "candidate_count": 0}
    if diagnostic is not None:
        result["error_code"] = diagnostic
    return request, result


@pytest.mark.parametrize("diagnostic,reason", [
    (None, "exact_transcript_missing"),
    ("call_after_as_of", "call_after_as_of"),
    ("publication_after_as_of", "publication_after_as_of"),
])
def test_not_found_consumer_contract_preserves_optional_date_diagnostic(diagnostic, reason):
    request, result = _not_found_receipt(diagnostic)
    original = copy.deepcopy(result)
    assert normalize_et_v2_result(result, request) == {"status": "not_found", "reason": reason}
    assert result == original


@pytest.mark.parametrize("field,value", [
    ("request_id", "unrelated-request"), ("provider", "unrelated-provider"),
    ("fiscal_period", "2026-Q4"), ("candidate_count", 1), ("candidate_count", True),
    ("error_code", "child_free_text_never_public"), ("error_code", ["call_after_as_of"]),
    ("reason", "call_after_as_of"),
])
def test_not_found_consumer_contract_rejects_invalid_binding_or_unknown_diagnostic(field, value):
    request, result = _not_found_receipt("call_after_as_of")
    result[field] = value
    with pytest.raises(ETContractError):
        normalize_et_v2_result(result, request)
'''

for rel, body in [(OWNED[2], LAUNCH), (OWNED[3], COMPANION), (OWNED[4], BOUNDARY)]:
    path = ROOT / rel
    data = path.read_bytes()
    assert b"test_not_found_" not in data, f"test already appended: {rel}"
    newline = b"\r\n" if b"\r\n" in data else b"\n"
    path.write_bytes(data + body.encode().replace(b"\n", newline))
print(json.dumps({"baseline_owned": len(OWNED), "protected": len(protected), "test_files": 3}))
