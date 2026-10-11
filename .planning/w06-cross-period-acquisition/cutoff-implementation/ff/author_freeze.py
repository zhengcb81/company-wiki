"""Read-only checks plus the assigned FF author PWF/handoff freeze."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

ROOT = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root")
OUT = Path(__file__).resolve().parent
base = json.loads((OUT/"baseline.json").read_text(encoding="utf-8"))
env = {k: os.environ[k] for k in ("SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP") if k in os.environ}
env.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"})
owned = [e["path"] for e in base["owned"]]

def record(rel):
    data = (ROOT/rel).read_bytes()
    return {"path": rel, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}

checks = {}
for label, args in [
    ("lint", [sys.executable, "-B", "-m", "ruff", "check", "--no-cache", *owned]),
    ("diff-check", ["git", "diff", "--check"]),
    ("status", ["git", "status", "--short"]),
    ("diff-stat", ["git", "diff", "--stat"]),
]:
    r = subprocess.run(args, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=30, check=False)
    (OUT/(label+".log")).write_bytes(r.stdout)
    checks[label] = {"command": args, "exit_code": r.returncode,
                     "sha256": hashlib.sha256(r.stdout).hexdigest()}
    assert r.returncode == 0, (label, r.stdout.decode(errors="replace"))

changed = [e["path"] for e in base["protected"] if record(e["path"]) != e]
assert not changed, f"protected bytes changed: {changed}"
prefixes = [{"path": e["path"], "original_prefix_preserved":
    hashlib.sha256((ROOT/e["path"]).read_bytes()[:e["bytes"]]).hexdigest() == e["sha256"]}
    for e in base["owned"][2:]]
assert all(e["original_prefix_preserved"] for e in prefixes)
current_owned = [record(p) for p in owned]
green = json.loads((OUT/"focused-green.json").read_text(encoding="utf-8"))
assert all(record(e["path"])["sha256"] == e["sha256"] for e in green["files"])
red = json.loads((OUT/"business-red.json").read_text(encoding="utf-8"))
assert red["exit_code"] == 1 and green["exit_code"] == 0
assert red["scratch_restored"] and green["scratch_restored"]
assert not list(OUT.glob("s-*")), "owned scratch remains"

(OUT/"tracked-product.patch").write_bytes(subprocess.check_output(
    ["git", "diff", "--", *owned], cwd=ROOT, env=env))
freeze = {"schema_version": "ff-cutoff-author-freeze/1", "state": "AUTHOR_FROZEN_PENDING_ROOT",
          "base": base["base"], "files": current_owned, "protected_count": len(base["protected"]),
          "protected_changed": changed, "original_tests": prefixes,
          "test_sha_unchanged_between_red_green": True, "checks": checks,
          "real_key_reads": 0, "real_provider_calls": 0, "llm_calls": 0,
          "scratch_restored": True}
(OUT/"product-freeze.json").write_text(json.dumps(freeze, indent=2), encoding="utf-8")
freeze_sha = hashlib.sha256((OUT/"product-freeze.json").read_bytes()).hexdigest()

plan = ROOT/".planning/w06-cutoff-result/task_plan.md"
text = plan.read_text(encoding="utf-8")
text = text.replace("B — implement the bounded two-file consumer mapping.", "C — author complete; frozen STOP for ROOT reception.")
text = text.replace("Run focused GREEN on the unchanged new behavior tests, then hand frozen five-file delivery to ROOT for the shared responsibility node.",
    "ROOT runs the concentrated ET+FF responsibility node and original unchanged 41-case matrix, then owns commit/merge/push/install.")
text = text.replace("- [ ] Focused GREEN", "- [x] Focused GREEN")
text = text.replace("- [ ] Verify frozen", "- [x] Verify frozen")
text = text.replace("- [ ] Update own PWF", "- [x] Update own PWF")
text = text.replace("- [ ] STOP without", "- [x] STOP without")
plan.write_text(text, encoding="utf-8")
with (ROOT/".planning/w06-cutoff-result/findings.md").open("a", encoding="utf-8") as f:
    f.write("\n## Final bounded implementation\n- One finite ET_NOT_FOUND_DIAGNOSTICS vocabulary contains two actual date exclusions. Transport imports only the constant; no call to test-only normalize_et_v2_result.\n"
            "- Production not_found preserves state, maps only those two codes, and never forwards child text. Ordinary/legacy/unknown diagnostic returns exact_transcript_missing. Existing provider failures, retryability, bounded process and measured usage unchanged.\n"
            "- Test-only /2 boundary accepts old six-field not_found plus one optional finite error_code; preserves existing strict success/failure goldens. Header, period and zero-count checks remain in their existing responsibility layer.\n"
            "- Protected file SHA comparison: 354 unchanged. All original contents of the three tests remain byte-for-byte prefix; only new tests appended. No CWP/ET product/tools/fixtures/config writes.\n")
with (ROOT/".planning/w06-cutoff-result/progress.md").open("a", encoding="utf-8") as f:
    f.write("\n## Author focused GREEN / freeze\n- Unchanged new tests: 31 PASS / 77 deselected, pytest0.54s; runner3.19s. Both unique short scratch directories fully restored.\n"
            "- Ruff --no-cache on the five assigned files and git diff --check passed. 354 frozen protected files unchanged; RED/GREEN test SHA identical.\n"
            f"- Product freeze SHA: {freeze_sha}. Author stopped without commit/merge/push/install.\n"
            "- GREEN is limited author responsibility evidence. ROOT concentrated old/new responsibility tests and actual ET/CWP original41 are still required; no claim of end-to-end COMPLETE.\n")
handoff = ROOT/"docs/handoffs/w06-cutoff-result"
assert not handoff.exists(), "preserve existing handoff"
handoff.mkdir(parents=True)
report = {"schema_version": "ff-cutoff-author-report/1", "verdict": "AUTHOR_COMPLETE_PENDING_ROOT_ACCEPTANCE",
    "worktree": str(ROOT), "base": base["base"], "product_freeze_sha256": freeze_sha,
    "evidence_directory": str(OUT), "files": current_owned,
    "red": {"failed": 23, "passed": 8, "deselected": 77, "pytest_seconds": 1.09,
            "receipt": str(OUT/"business-red.json")},
    "focused_green": {"passed": 31, "deselected": 77, "pytest_seconds": 0.54,
                      "receipt": str(OUT/"focused-green.json")},
    "protected_count": len(base["protected"]), "protected_changed": changed,
    "test_sha_same_red_green": True, "real_key_reads": 0, "real_provider_calls": 0, "llm_calls": 0,
    "scratch_restored": True,
    "root_responsibility_files": ["tests/test_transcript_launch_contract.py", "tests/test_transcript_companion_transport.py",
        "tests/test_et_s0b_contract.py", "tests/test_transcript_response_budget.py", "tests/test_transcript_companion.py"],
    "still_required": ["ROOT concentrated ET+FF responsibility tests", "ROOT unchanged original41 real offline matrix", "ROOT publication"],
    "notes": ["No manual approvals, receipts or canary gates added.", "No duplicate production validator.",
        "Do not infer cutoff from zero candidates or unknown publication.",
        "The products are not committed; do not omit the appended tests and own PWF when ROOT receives."]}
(OUT/"report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
md = f'''# W06 cutoff result — FF author handoff

**AUTHOR_COMPLETE_PENDING_ROOT_ACCEPTANCE; FROZEN STOP.**

Base: `{base['base']}`. Independent worktree: `{ROOT}`.

## Root cause and repair
ET correctly excluded a legal requested-period transcript published after the information cutoff but omitted a reason. FF then flattened every non-fetched result into provider_unavailable. ROOT parent owns ET typed date diagnostics; this delivery preserves ordinary not_found and the two additive error codes call_after_as_of / publication_after_as_of. Ordinary/legacy/unknown codes mean exact_transcript_missing. Unknown child strings do not pass through. No cutoff is guessed from zero candidates.

Transport imports only one shared finite vocabulary from the existing test contract module. It does not call that module's validator or introduce another production identity/byte check. Companion and public v2 envelope already preserve status/reason/usage and remain unchanged. No extra provider, import, raw original, grant JSON or canary.

## Delivery / TDD
- Exactly two products plus three responsibility tests; see product-freeze.json.
- Behavioral RED: 23 FAIL / 8 PASS / 77 deselected, pytest1.09s; no import/setup failure used as RED.
- Same test bytes GREEN: 31 PASS / 77 deselected, pytest0.54s. Author did not duplicate the full responsibility node.
- Ruff and git diff --check green; 354 protected files and all original test prefixes unchanged. Unique owned scratch restored; zero real keys/supplier/network/LLM requests.
- Product freeze SHA: `{freeze_sha}`.

## ROOT next action
Once ET producer delivery is ready, run a single concentrated responsibility node in each repository using isolated environment and one short owned scratch:

```powershell
python -B -m pytest -p no:cacheprovider --basetemp <unique-owned-short-scratch> -q tests/test_transcript_launch_contract.py tests/test_transcript_companion_transport.py tests/test_et_s0b_contract.py tests/test_transcript_response_budget.py tests/test_transcript_companion.py
```

Then run the original unchanged 41-case matrix. Product integration is not COMPLETE based on this focused GREEN. ROOT owns acceptance, commit/merge/push/install. Author remains STOP.

Canonical evidence: `{OUT}`. Original frozen tool/test matrix and previous failing receipts remain untouched.
'''
(OUT/"report.md").write_text(md, encoding="utf-8")
(handoff/"handoff.md").write_text(md, encoding="utf-8")
(handoff/"handoff.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
manifest_files = list(OUT.glob("*")) + list((ROOT/".planning/w06-cutoff-result").glob("*.md")) + list(handoff.glob("*"))
manifest = [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
    for p in sorted(manifest_files) if p.is_file() and p.name != "manifest.json"]
(OUT/"manifest.json").write_text(json.dumps({"schema_version":"ff-cutoff-evidence-manifest/1", "files":manifest},
    ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"state": freeze["state"], "protected_unchanged": len(base["protected"]),
                  "freeze_sha256": freeze_sha, "product_files": len(current_owned)}))
