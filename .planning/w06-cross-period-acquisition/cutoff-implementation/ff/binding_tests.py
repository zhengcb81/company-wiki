"""Append real production-boundary counterexamples after ROOT concrete review."""
from pathlib import Path
import hashlib
import json

ROOT = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root")
OUT = Path(__file__).resolve().parent
freeze = json.loads((OUT/"product-freeze.json").read_text(encoding="utf-8"))
for e in freeze["files"]:
    assert hashlib.sha256((ROOT/e["path"]).read_bytes()).hexdigest() == e["sha256"]
body = '''


@pytest.mark.parametrize("field,value,exit_code,reason", [
    ("request_id", "unrelated-request", 0, "provider_result_invalid"),
    ("schema_version", "earnings-transcript-result/3", 0, "provider_result_invalid"),
    ("provider", "unrelated-provider", 0, "provider_result_invalid"),
    ("fiscal_period", "2026-Q3", 0, "provider_result_invalid"),
    ("candidate_count", 1, 0, "provider_result_invalid"),
    ("candidate_count", True, 0, "provider_result_invalid"),
    ("candidate_count", "0", 0, "provider_result_invalid"),
    (None, None, 2, "provider_tool_failed"),
])
def test_not_found_envelope_cannot_claim_cutoff_for_unrelated_or_failed_child(
    tmp_path, monkeypatch, field, value, exit_code, reason,
):
    result = {"schema_version": "earnings-transcript-result/2", "request_id": "w07",
              "provider": "fmp", "status": "not_found", "fiscal_period": "2026-Q4",
              "candidate_count": 0, "error_code": "call_after_as_of"}
    if field is not None:
        result[field] = value
    receipt = {"schema_version": "earnings-retrieval-usage/1", "request_id": "w07",
               "usage_complete": True, "usage": {"requests_used": 1, "response_bytes_used": 512}}
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        return json.dumps(result).encode(), json.dumps(receipt).encode(), exit_code
    monkeypatch.setattr(transport_module, "_run_bounded_json", run)
    transport = _transport(tmp_path)
    monkeypatch.setattr(transport, "_et_environment", lambda: ({}, None))
    public = transport._et_result(request=_request(), limits=_limits())
    assert public["status"] == "provider_unavailable"
    assert public["reason"] == reason
    assert public["retryable"] is False
    assert public["provider_requests"] == 1
    assert public["provider_response_bytes"] == 512
    assert public["provider_usage_complete"] is True
    assert public["provider_started"] is True
    assert public["provider_calls"] == 1
    assert "call_after_as_of" not in json.dumps(public)
    assert "source_ref" not in public
    assert len(calls) == 1
'''
p=ROOT/"tests/test_transcript_launch_contract.py"
data=p.read_bytes()
newline=b"\r\n" if b"\r\n" in data else b"\n"
p.write_bytes(data+body.encode().replace(b"\n",newline))
plan=ROOT/".planning/w06-cutoff-result/task_plan.md"
text=plan.read_text(encoding="utf-8")
text=text.replace("C — author complete; frozen STOP for ROOT reception.", "D — ROOT concrete production receipt binding finding; repair in progress.")
text=text.replace("ROOT runs the concentrated ET+FF responsibility node and original unchanged 41-case matrix, then owns commit/merge/push/install.",
                  "Seal production receipt binding counterexample RED, repair the single existing boundary, then ROOT reruns concentrated responsibility B.")
text += "\n### D — ROOT production envelope finding\n- [x] New counterexamples belong to the actual transport, not merely the test-only contract.\n- [ ] Preserve RED for wrong request/schema/provider/period/count and nonzero child exit.\n- [ ] One lightweight receipt envelope check at the existing transport boundary, retain real usage; no duplicate success/source identity validator.\n- [ ] Focused affected GREEN, new independent freeze; preserve prior RED/GREEN/concentrated124PASS4SKIP as superseded intermediate receipts.\n"
plan.write_text(text,encoding="utf-8")
with (ROOT/".planning/w06-cutoff-result/progress.md").open("a",encoding="utf-8") as f:
    f.write("\n## ROOT concrete envelope finding\n- ROOT concentrated A:124 PASS / 4 SKIP /5.00s (6.617s outer). Three W07 real-ET cases lacked explicit test tool path; one real-CWP import/replay case lacked source checkout. These are SKIP, not PASS; parent owns original41 real integration.\n"
            "- ROOT found production not_found branch lacked response-envelope/child-exit binding; previous negative binding tests covered only the test boundary. Added 8 actual transport counterexamples from valid receipts, one-field corruptions/nonzero exit. Prior freeze is historical intermediate, not final accepted publication.\n")
print("Appended eight production binding RED counterexamples; no product edits.")
