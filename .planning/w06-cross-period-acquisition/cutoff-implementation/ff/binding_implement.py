"""One existing production receipt boundary, after eight actual behavior REDs."""
from pathlib import Path
import json

ROOT=Path("C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root")
OUT=Path(__file__).resolve().parent
assert json.loads((OUT/"binding-red.json").read_text(encoding="utf-8"))["exit_code"] == 1
p=ROOT/"scripts/transcript_tool_transport.py"
data=p.read_bytes()
newline=b"\r\n" if b"\r\n" in data else b"\n"
old='''        if result.get("status") == "not_found":
            # A completed lookup with no eligible transcript is not a provider'''
new='''        if result.get("status") == "not_found":
            # Bind this one process receipt to the current request. This is not
            # another company-identity lookup or a source-byte validation.
            invalid = (
                result.get("schema_version") not in {
                    "earnings-transcript-result/1", "earnings-transcript-result/2",
                }
                or result.get("request_id") != et_request["request_id"]
                or result.get("provider") != et_request["provider"]
                or result.get("fiscal_period")
                != f"{et_request['fiscal_year']}-Q{et_request['fiscal_quarter']}"
                or type(result.get("candidate_count")) is not int
                or result["candidate_count"] != 0
            )
            if code != 0 or invalid:
                return {
                    "status": "provider_unavailable",
                    "reason": "provider_tool_failed" if code != 0 else "provider_result_invalid",
                    "retryable": False,
                    "provider_calls": 1,
                    "provider_started": self._provider_started(self._last_provider_usage),
                    **self._last_provider_usage,
                }
            # A completed lookup with no eligible transcript is not a provider'''
oldb=old.encode().replace(b"\n",newline)
assert data.count(oldb)==1
p.write_bytes(data.replace(oldb,new.encode().replace(b"\n",newline)))
with (ROOT/".planning/w06-cutoff-result/progress.md").open("a",encoding="utf-8") as f:
    f.write("\n- Production binding RED:8 FAIL /108 deselected /pytest1.03s, all actual transport returned not_found for wrong envelope/failed child; scratch restored.\n"
            "- Added one constant-time receipt check in _et_result for schema /1 or /2, current request ID/provider/period and integer zero candidate count; nonzero child exit is provider_tool_failed. Actual usage retained. No success validator/source/identity lookup called.\n")
print("Implemented one lightweight production receipt binding after eight behavioral REDs.")
