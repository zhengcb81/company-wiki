"""Apply the ROOT-authorized two-file consumer repair after behavioral RED."""
from pathlib import Path
import hashlib
import json

ROOT = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root")
OUT = Path(__file__).resolve().parent
baseline = json.loads((OUT / "baseline.json").read_text(encoding="utf-8"))
assert json.loads((OUT / "business-red.json").read_text(encoding="utf-8"))["exit_code"] == 1
for e in baseline["owned"][:2]:
    assert hashlib.sha256((ROOT/e["path"]).read_bytes()).hexdigest() == e["sha256"]

def replace(rel, old, new):
    path = ROOT/rel
    data = path.read_bytes()
    newline = b"\r\n" if b"\r\n" in data else b"\n"
    old_b = old.encode().replace(b"\n", newline)
    new_b = new.encode().replace(b"\n", newline)
    assert data.count(old_b) == 1, f"replacement must have one match: {rel}"
    path.write_bytes(data.replace(old_b, new_b))

replace("scripts/et_v2_contract.py", '''_FAILURE_KEYS = frozenset({''', '''# Additive not_found diagnostics share one finite vocabulary with the transport.
# Importing this constant does not add another production contract validator.
ET_NOT_FOUND_DIAGNOSTICS = frozenset({"call_after_as_of", "publication_after_as_of"})
_NOT_FOUND_KEYS = frozenset({
    "schema_version", "request_id", "status", "provider", "fiscal_period", "candidate_count",
})
_FAILURE_KEYS = frozenset({''')

replace("scripts/et_v2_contract.py", '''def _success_identity(result: dict[str, Any], request: dict[str, Any]) -> str:''', '''def _not_found_result(result: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    """Read ordinary/legacy missing results and additive actual date exclusions."""
    fields = frozenset(result)
    if not (_NOT_FOUND_KEYS <= fields <= (_NOT_FOUND_KEYS | {"error_code"})):
        _fail("not_found_keys")
    if result.get("provider") != request.get("provider"):
        _fail("provider")
    if result.get("fiscal_period") != _period(request):
        _fail("fiscal_period")
    if type(result.get("candidate_count")) is not int or result["candidate_count"] != 0:
        _fail("candidate_count")
    reason = "exact_transcript_missing"
    if "error_code" in result:
        diagnostic = result["error_code"]
        if not isinstance(diagnostic, str) or diagnostic not in ET_NOT_FOUND_DIAGNOSTICS:
            _fail("not_found_diagnostic")
        reason = diagnostic
    return {"status": "not_found", "reason": reason}


def _success_identity(result: dict[str, Any], request: dict[str, Any]) -> str:''')

replace("scripts/et_v2_contract.py", '''    _check_header(result, request)
    if result.get("status") != "fetched":''', '''    _check_header(result, request)
    if result.get("status") == "not_found":
        return _not_found_result(result, request)
    if result.get("status") != "fetched":''')

replace("scripts/transcript_tool_transport.py", '''from typing import Any
''', '''from typing import Any

from et_v2_contract import ET_NOT_FOUND_DIAGNOSTICS
''')

replace("scripts/transcript_tool_transport.py", '''        if result.get("status") != "fetched":
            error_code = result.get("error_code")''', '''        if result.get("status") == "not_found":
            # A completed lookup with no eligible transcript is not a provider
            # outage. Only a producer-declared finite date diagnostic can name
            # a cutoff; neither zero candidates nor child free text proves one.
            diagnostic = result.get("error_code")
            reason = (diagnostic if isinstance(diagnostic, str)
                      and diagnostic in ET_NOT_FOUND_DIAGNOSTICS else "exact_transcript_missing")
            return {
                "status": "not_found",
                "reason": reason,
                "retryable": False,
                "provider_calls": 1,
                "provider_started": self._provider_started(self._last_provider_usage),
                **self._last_provider_usage,
            }
        if result.get("status") != "fetched":
            error_code = result.get("error_code")''')

plan = ROOT / ".planning/w06-cutoff-result/task_plan.md"
text = plan.read_text(encoding="utf-8")
text = text.replace("A — freeze baseline and executable business RED.", "B — implement the bounded two-file consumer mapping.")
text = text.replace("Append behavioral tests to the three existing responsibility test files, then retain real assertion failures before product edits.",
                    "Run focused GREEN on the unchanged new behavior tests, then hand frozen five-file delivery to ROOT for the shared responsibility node.")
for line in ["Snapshot five owned files plus frozen tools/fixtures/goldens before edits.",
             "Assert named cutoff, ordinary/legacy not_found, unknown diagnostics, usage complete/unknown and zero import; run only new behavior tests. Do not count import errors as RED.",
             "Keep existing provider failure mapping; preserve not_found with finite error-code mapping.",
             "Ordinary/legacy or unknown code becomes exact_transcript_missing, never guessed cutoff.",
             "Update existing et_v2_contract test-only boundary for the optional not_found diagnostic; do not wire another production validator."]:
    text = text.replace("- [ ] " + line, "- [x] " + line)
plan.write_text(text, encoding="utf-8")
progress = ROOT / ".planning/w06-cutoff-result/progress.md"
with progress.open("a", encoding="utf-8") as f:
    f.write("\n## Behavioral RED and implementation\n- Baseline froze 5 owned files and 354 protected tools/fixtures/goldens/old PWF/handoff files.\n"
            "- Executed new business tests: 23 FAIL / 8 PASS / 77 deselected, pytest 1.09s, unique scratch restored. All failures are behavior/contract failures, no imports/setup failures.\n"
            "- Two-file repair implemented after RED; transport reuses only a finite constant from existing et_v2_contract, never calls its validator. Provider failures unchanged; no import/retry/receipt schema changes.\n")
print("Implemented two-file product repair after preserved behavioral RED.")
