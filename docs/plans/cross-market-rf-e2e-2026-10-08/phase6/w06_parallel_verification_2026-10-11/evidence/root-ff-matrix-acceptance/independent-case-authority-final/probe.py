"""One bounded, independent pure CaseSpec acceptance. No product execution."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from unittest.mock import patch

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
BASE = OUT.parent
FF = Path(r"C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root")
FIX = BASE / "fix/case-authority"
OLD = BASE / "independent-final"
SCRATCH = OUT / "s"
FIXTURES = FF / "tests/fixtures/w06_contract_matrix/authority"
EXPECTED_FREEZE = "e2bf72bde855935db1beeca45ad10d4a9b205f4ca1137dab07db4d827e3f7fe3"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def inventory(root, entries):
    rows = []
    for item in entries:
        p = (root / item["path"]).resolve()
        if not p.is_relative_to(root.resolve()):
            raise RuntimeError("manifest outside declared read-only root")
        actual_sha, actual_bytes = sha(p), p.stat().st_size
        rows.append({"path": item["path"], "sha256": actual_sha, "bytes": actual_bytes,
                     "matches": actual_sha == item["sha256"] and actual_bytes == item["bytes"]})
    return rows


if SCRATCH.exists() or (OUT / "report.json").exists():
    raise RuntimeError("Fresh acceptance only; do not overwrite evidence or preexisting scratch")
started = time.monotonic()
freeze = read(FIX / "manifest.json")
freeze_before = inventory(FF, freeze["files"])
evidence_before = inventory(FIX, freeze["evidence"])
historical_paths = [BASE / "fix/freeze-manifest.json", BASE / "fix/offline-evidence.zip",
                    BASE / "fix/root_handoff.json", OLD / "manifest.json"]
historical_paths += [OLD / row["path"] for row in read(OLD / "manifest.json")["files"]]
historical_before = {str(p): sha(p) for p in historical_paths}
old_freeze = read(BASE / "fix/freeze-manifest.json")
old_review = read(OLD / "final-review.json")
original = read(OLD / "original-41-report-copy.json")
producer_rows = [row for dep in read(BASE / "fix/root_handoff.json")["producer_bindings"]
                 for row in dep["modules"]]
producer_rows.append({"path": "src/company_wiki/__init__.py",
                      "file": r"C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/__init__.py",
                      "sha256": original["code_binding"]["company_wiki"]["sha256"]})
# The old import-binding path has historical console-encoding damage. Resolve
# its verified module at the exact canonical CWP repository, never its spelling.
producer_rows[-1]["file"] = str(Path(r"C:/Users/郑曾波/Projects/company-wiki/src/company_wiki/__init__.py"))
producer_before = [{"path": r["file"], "sha256": sha(Path(r["file"])),
                    "matches": sha(Path(r["file"])) == r["sha256"]} for r in producer_rows]

sys.path.insert(0, str(FF / "tools/offline_contract_matrix"))
import oracle
from case_specs import audit_coverage, case_specs, get_spec
from cli_main import _case_registry
from run import Context, ProductionGuard

guard = ProductionGuard(FF, Path(r"C:/Users/郑曾波/Projects/company-wiki"),
                        Path(r"C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts"))
probes = []


def check(name, passed, actual):
    probes.append({"name": name, "pass": bool(passed), "actual": actual})


def case(report, cid):
    return next(c for c in report["cases"] if c["id"] == cid)


def findings(report):
    return [f.to_dict() for f in oracle.audit(report)]


def vectors(rows, vector, cid=None):
    return [r for r in rows if r["vector"] == vector and (cid is None or r["case_id"] == cid)]


check("FREEZE-205-PRODUCT-19-EVIDENCE", sha(FIX / "manifest.json") == EXPECTED_FREEZE
      and len(freeze_before) == 205 and all(r["matches"] for r in freeze_before + evidence_before),
      {"freeze_sha256": sha(FIX / "manifest.json"), "products": len(freeze_before),
       "evidence": len(evidence_before), "mismatches": [r for r in freeze_before + evidence_before if not r["matches"]]})
historical_expected = {
    "freeze": "e098e5bca867a33802d8fcf6945af7370bb092aec13a4397be475244c43e1246",
    "zip": "dd8fc402a337ef02b3db456a760162f59129c9e7ae5667c62d281294d903bea3",
    "report": "aa2ab10add76f89e6e259fa0a05c8ad961f562f46b3fd21a1e94c1b2a3acc72f",
}
old20 = [{k: row[k] for k in ("path", "sha256", "bytes")} for row in old_review["final_freeze"]]
check("HISTORICAL-20-FREEZE-REPORT-ZIP", len(old_freeze["files"]) == 20
      and old_freeze["files"] == old20
      and sha(BASE / "fix/freeze-manifest.json") == historical_expected["freeze"]
      and sha(BASE / "fix/offline-evidence.zip") == historical_expected["zip"]
      and sha(OLD / "original-41-report-copy.json") == historical_expected["report"],
      {"old_freeze_entries": len(old20), "hashes": historical_expected,
       "scope": "Historical 20-entry manifest and previous review retained; repaired live tools use new 205-entry freeze."})
check("TEN-PRODUCER-BINDINGS", len(producer_before) == 10 and all(r["matches"] for r in producer_before), producer_before)

SCRATCH.mkdir()
sentinel = SCRATCH / "preexisting-control.txt"
sentinel.write_bytes(b"independent synthetic scratch sentinel\r\n")
sentinel_before = sha(sentinel)
try:
    shutil.copytree(FIXTURES / "artifacts", SCRATCH / "artifacts")
    exact = read(FIX / "exact-inputs.json")
    input_shas = {name: sha(OLD / name) for name in (
        "omitted-required-22-cases-counterexample.json",
        "removed-cutoff-expectation-report-copy.json", "modified-request-vector.json")}
    check("THREE-ORIGINAL-INPUT-SHA", all(exact.get(name) == value for name, value in input_shas.items()), input_shas)
    # Use the original report bytes in memory; only the evidence-root location
    # changes because the old reports' scratch was correctly removed.
    omitted = read(OLD / "omitted-required-22-cases-counterexample.json")
    omitted["evidence_root"] = str(SCRATCH / "artifacts")
    fs = findings(omitted)
    check("EXACT-OMITTED-22", bool(vectors(fs, "coverage_gap")), vectors(fs, "coverage_gap"))
    cutoff = read(OLD / "removed-cutoff-expectation-report-copy.json")
    cutoff["evidence_root"] = str(SCRATCH / "artifacts")
    fs = findings(cutoff)
    check("EXACT-CUTOFF-EXPECTATION-ERASED", bool(vectors(fs, "wrong_cutoff", "call_past_cutoff"))
          and bool(vectors(fs, "case_contract_mismatch", "call_past_cutoff")),
          [r for r in fs if r["case_id"] == "call_past_cutoff"])
    modified = read(OLD / "modified-request-vector.json")
    rel = modified["target_case"]["actual"]["runs"][0]["request_ref"]
    target = (SCRATCH / "artifacts" / rel).resolve()
    if not target.is_relative_to((SCRATCH / "artifacts").resolve()):
        raise RuntimeError("request outside owned scratch")
    # Original reviewer used Windows write_text (CRLF), so replay that exact
    # representation rather than changing it to a new LF byte serialization.
    target.write_text(json.dumps(modified["executed_request"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    check("EXACT-MODIFIED-REQUEST-BYTES", sha(target) == modified["request_sha256"],
          {"expected": modified["request_sha256"], "actual": sha(target)})
    mreport = deepcopy(original)
    mreport["cases"] = [c for c in mreport["cases"] if c["result"] == "PASS"]
    mreport["required_cases"] = [c["id"] for c in mreport["cases"]]
    mreport["evidence_root"] = str(SCRATCH / "artifacts")
    ix = next(i for i, c in enumerate(mreport["cases"]) if c["id"] == "fin_cn_annual_hit")
    mreport["cases"][ix] = deepcopy(modified["target_case"])
    fs = findings(mreport)
    check("EXACT-HASHED-WRONG-MARKET", bool(vectors(fs, "case_request_mismatch", "fin_cn_annual_hit")),
          vectors(fs, "case_request_mismatch", "fin_cn_annual_hit"))

    # Registry controls are component checks, not full producer acceptance.
    rows = deepcopy(original["cases"])
    check("POSITIVE-FULL-FIXED-REGISTRY", audit_coverage(rows) == [], {"count": len(rows)})
    for name, altered in (
        ("REGISTRY-MISSING", rows[1:]),
        ("REGISTRY-DUPLICATE", rows + [deepcopy(rows[0])]),
        ("REGISTRY-EXTRA", rows + [{"id": "synthetic-extra-case"}]),
    ):
        errors = audit_coverage(altered)
        check(name, bool(errors), errors)
    registry = _case_registry()
    check("RUNNER-ORACLE-SAME-AUTHORITY", tuple(c for c, _ in registry) == tuple(s.id for s in case_specs())
          and all(runner.__self__ is spec for (_, runner), spec in zip(registry, case_specs())),
          {"case_count": len(registry), "authority": "w06-cases/1"})
    good_case = case(original, "fin_cn_annual_hit")
    spec = get_spec(good_case["id"])
    check("POSITIVE-NAMED-SINGLE-CASE", oracle.audit_case(spec, good_case) == []
          and spec.request_errors(0, spec.runs[0].request()) == []
          and spec.fixture_errors(0, {}, True) == [], {"id": spec.id, "scope": "component only"})
    drifted = []
    for field, value in (("company_query", "wrong"), ("market", "HK"), ("document_kind", "quarterly_report"),
                         ("fiscal_year", 2025), ("fiscal_period", "Q1"), ("as_of_date", "2025-01-01"),
                         ("filing_intent", "fetch_if_missing"), ("mode", "latest_as_of")):
        request = spec.runs[0].request()
        request[field] = value
        drifted.append({"field": field, "rejected": bool(spec.request_errors(0, request))})
    other = get_spec("call_max_bytes")
    for field, value in (("fiscal_quarter", 2), ("max_bytes", 1000000)):
        request = other.runs[0].request()
        if field == "max_bytes": request["companion_transcript"]["acquisition_limits"][field] = value
        else: request["companion_transcript"][field] = value
        drifted.append({"field": "companion." + field, "rejected": bool(other.request_errors(0, request))})
    check("FULL-REQUEST-DIMENSION-DRIFT", all(r["rejected"] for r in drifted), drifted)
    stage = get_spec("call_past_cutoff")
    fixture_drift = []
    for field, value in (("scenario", "wrong_quarter"), ("call_date", "2025-06-01"),
                         ("content_utf8", "different"), ("response_bytes", 999)):
        state = stage.runs[0].fixture()
        state[field] = value
        fixture_drift.append({"field": field, "rejected": bool(stage.fixture_errors(0, state, True))})
    fixture_drift.append({"field": "with_fmp_key", "rejected": bool(stage.fixture_errors(0, stage.runs[0].fixture(), False))})
    check("FIXTURE-SCENARIO-DATE-CONTENT-BYTES-KEY", all(r["rejected"] for r in fixture_drift), fixture_drift)
    all_requests = []
    for c in original["cases"]:
        fixed = get_spec(c["id"])
        errors = fixed.metadata_errors(c)
        for n, r in enumerate(c["actual"]["runs"]):
            errors += fixed.request_errors(n, read(FIXTURES / "artifacts" / r["request_ref"]))
        all_requests.append({"case_id": c["id"], "errors": errors})
    check("ORIGINAL-41-REQUEST-VECTORS-UNCHANGED", all(not r["errors"] for r in all_requests),
          {"cases": len(all_requests), "mismatches": [r for r in all_requests if r["errors"]]})
    fail_laundering = []
    for c in original["cases"]:
        if c["result"] != "FAIL": continue
        fake = deepcopy(c)
        fake["result"] = "PASS"
        errors = oracle.audit_case(get_spec(c["id"]), fake)
        rejected = [f.to_dict() for f in errors if f.vector == "case_assertion_failed"]
        fail_laundering.append({"case_id": c["id"], "rejected": bool(rejected), "findings": rejected})
    check("FIXED-BUSINESS-ASSERTIONS-21-FAIL-AS-PASS", len(fail_laundering) == 21
          and all(r["rejected"] for r in fail_laundering), fail_laundering)

    ctx = Context(ff_root=SCRATCH / "fake_ff", cwp_root=SCRATCH / "fake_cwp",
                  et_root=SCRATCH / "fake_et", scratch=SCRATCH / "c",
                  out_root=SCRATCH / "o")
    prelaunch = []
    for kind in ("request", "fixture"):
        active = spec if kind == "request" else stage
        request = active.runs[0].request()
        if kind == "request": request["market"] = "HK"
        else:
            ctx.write_state(scenario="success", calls_file=ctx.env.calls_file(active.id),
                            call_date="2025-06-01", receipt_tag=active.id)
        with patch("run.run_process") as launch:
            try:
                ctx.run_ff(request, case_id=active.id)
                rejected = False
            except ValueError:
                rejected = True
            prelaunch.append({"kind": kind, "rejected": rejected, "process_launches": launch.call_count})
    check("SHARED-PREFLIGHT-NO-LAUNCH-ON-DRIFT", all(r["rejected"] and r["process_launches"] == 0 for r in prelaunch), prelaunch)

    unknown = deepcopy(case(original, "err_unknown_usage"))
    transcript = unknown["actual"]["runs"][0]["response"]["transcript"]
    check("UNKNOWN-USAGE-ORIGINAL-BUSINESS-AND-MATRIX", unknown["result"] == "FAIL"
          and transcript.get("status") == "not_requested" and transcript.get("provider_requests") is None
          and original["cost"]["unknown_charge"] is None,
          {"case_result": unknown["result"], "business_status": transcript.get("status"),
           "business_reason": transcript.get("reason"), "provider_requests": transcript.get("provider_requests"),
           "provider_usage_complete": transcript.get("provider_usage_complete"),
           "unknown_charge": original["cost"]["unknown_charge"], "matrix_state": "PARTIAL_PRODUCT_FAILURES"})
    # Explicit synthetic component control only. No bound original response,
    # receipt or product report is changed or claimed to have executed this.
    synthetic = deepcopy(unknown)
    synthetic["result"] = "PASS"
    synthetic["actual"].update(provider_requests=None, provider_usage_complete=False,
                               calls_swallowed=False, unknown_usage_reported_as_zero=False)
    synthetic_transcript = synthetic["actual"]["runs"][0]["response"]["transcript"]
    synthetic_transcript.update(status="upstream_error", reason="worker_loss",
                                provider_requests=None, provider_usage_complete=False)
    errors = oracle.audit_case(get_spec(unknown["id"]), synthetic)
    check("POSITIVE-SYNTHETIC-NAMED-UNKNOWN-NULL-COMPONENT", not errors,
          {"findings": [f.to_dict() for f in errors], "scope": "synthetic component only; no business execution or bound evidence"})
    synthetic_transcript["provider_requests"] = 0
    errors = oracle.audit_case(get_spec(unknown["id"]), synthetic)
    check("UNKNOWN-USAGE-FAKE-ZERO-REJECTED", any(f.vector in {"fake_zero_cost", "case_assertion_failed"} for f in errors),
          [f.to_dict() for f in errors])
    bounded_original = deepcopy(original)
    bounded_original["evidence_root"] = str(FIXTURES / "artifacts")
    fs = findings(bounded_original)
    missing_receipts = vectors(fs, "missing_case_fixture_evidence")
    check("ORIGINAL-MATRIX-REMAINS-INCOMPLETE-NO-RECEIPT-MANUFACTURE", len(missing_receipts) == 40
          and Counter(c["result"] for c in original["cases"]) == {"PASS": 19, "FAIL": 21, "PARTIAL": 1}
          and bool(vectors(fs, "case_not_passed")),
          {"counts": dict(Counter(c["result"] for c in original["cases"])),
           "finding_counts": dict(Counter(f["vector"] for f in fs)), "missing_fixture_receipts": len(missing_receipts),
           "oracle_pass": not fs})
    check("SYNTHETIC-SENTINEL-UNCHANGED", sha(sentinel) == sentinel_before, {"sha256": sha(sentinel)})
finally:
    if SCRATCH.resolve().parent != OUT.resolve() or SCRATCH.name != "s":
        raise RuntimeError("Refuse deletion outside unique owned acceptance scratch")
    shutil.rmtree(SCRATCH)

# Git reads only. The byte-preservation attribute applies solely below the
# synthetic fixture directory, not production documents, code, CI or config.
attribute = FIXTURES / ".gitattributes"
lines = [l for l in attribute.read_text(encoding="utf-8").splitlines() if l.strip()]
attribute_ok = len(lines) == 2 and lines[0].startswith("artifacts/** -text ")
attribute_ok = attribute_ok and lines[1].startswith("original-41-report.json -text ")
index_checks = []
for rel in ("tests/fixtures/w06_contract_matrix/authority/.gitattributes",
            "tests/fixtures/w06_contract_matrix/authority/original-41-report.json",
            "tests/fixtures/w06_contract_matrix/authority/artifacts/fin_cn_annual_hit.run1.request.json"):
    proc = subprocess.run(["git", "-C", str(FF), "show", ":" + rel], capture_output=True, check=False)
    index_sha = hashlib.sha256(proc.stdout).hexdigest()
    equal = index_sha == sha(FF / rel)
    if rel.endswith("/.gitattributes"):
        equal = proc.stdout.replace(b"\r\n", b"\n") == (FF / rel).read_bytes().replace(b"\r\n", b"\n")
    index_checks.append({"path": rel, "index_sha256": index_sha, "raw_sha256": sha(FF / rel),
                         "equal": proc.returncode == 0 and equal,
                         "comparison": "logical text after ordinary CRLF normalization" if rel.endswith("/.gitattributes") else "exact raw bytes"})
check("NARROW-FIXTURE-ATTRIBUTES-INDEX-RAW", attribute_ok and all(r["equal"] for r in index_checks),
      {"lines": lines, "representatives": index_checks})
changed = subprocess.run(["git", "-C", str(FF), "diff", "--name-only", "HEAD"], capture_output=True, check=True).stdout.decode("utf-8").splitlines()
production_changes = [p for p in changed if p.startswith(("scripts/", "config/", ".github/"))]
check("NO-PRODUCTION-SCRIPTS-CONFIG-CI-DIFF", not production_changes, {"forbidden_changed_paths": production_changes})
freeze_after = inventory(FF, freeze["files"])
evidence_after = inventory(FIX, freeze["evidence"])
producer_after = [{"path": r["file"], "sha256": sha(Path(r["file"])),
                   "matches": sha(Path(r["file"])) == r["sha256"]} for r in producer_rows]
check("FINAL-FREEZE-HISTORY-TEN-PRODUCERS-UNCHANGED", freeze_before == freeze_after
      and evidence_before == evidence_after and producer_before == producer_after
      and historical_before == {str(p): sha(p) for p in historical_paths}
      and sha(FIX / "manifest.json") == EXPECTED_FREEZE and guard.unchanged(guard.snapshot()),
      {"product_inventory_sha256": canonical_digest(freeze_after),
       "evidence_inventory_sha256": canonical_digest(evidence_after), "producer_count": len(producer_after),
       "historical_files": len(historical_paths), "production_metadata_unchanged": guard.unchanged(guard.snapshot())})
check("SCRATCH-RESTORED-INITIAL-ABSENCE", not SCRATCH.exists(), {"initial_exists": False, "final_exists": SCRATCH.exists()})
passed = all(p["pass"] for p in probes)
report = {
    "schema_version": "w06-independent-case-authority-final/1",
    "verdict": "PASS_WITH_SCOPE" if passed else "TOOL_BLOCKER",
    "author_state": "FROZEN_STOP", "reviewer_state": "FINAL_STOP",
    "scope": "One bounded pure counterexample/static group; tools acceptance only, not product matrix completion.",
    "freeze_sha256": EXPECTED_FREEZE, "freeze_products": len(freeze_after),
    "original_matrix": {"PASS": 19, "FAIL": 21, "PARTIAL": 1, "status": "PARTIAL_PRODUCT_FAILURES"},
    "unknown_usage_semantics": "Negative case may PASS while business remains failed/unknown; null is preserved and overall incomplete matrix never FULL_PASS.",
    "scope_gaps": ["ROOT producer/source-fact fix pending", "Unchanged 41-case real offline integration rerun pending",
                   "40 historical new fixture receipts absent; no retroactive manufacture"],
    "probes": probes, "probe_count": len(probes), "passed_count": sum(p["pass"] for p in probes),
    "failed": [p["name"] for p in probes if not p["pass"]],
    "seconds": round(time.monotonic() - started, 4),
    "provider_process_launches": 0, "provider_network_calls": 0, "llm_calls": 0, "fees_usd": 0,
    "git_mutations": 0, "production_mutations": 0,
    "scratch": {"initial_exists": False, "final_exists": SCRATCH.exists(), "restored": not SCRATCH.exists()},
    "reviewer_environment_retries": {"count": 2,
                                     "reasons": ["WinError 3 copying long synthetic fixture paths before probes; reduced own scratch names",
                                                 "Sandbox git -C external worktree Permission denied at final static index checks; same pure group rerun outside sandbox"],
                                     "prior_scratch_restored": True, "product_execution_on_prior_attempts": False},
    "reviewer_probe_corrections": {"retained_attempt_report": "reviewer-attempt-1-report.json",
                                   "reason": "Reviewer probe initially assumed LF serialization, an original unknown case PASS, and byte-equality for the attribute file itself; corrected to exact Windows CRLF, observed original FAIL and ordinary attribute text normalization. Product unchanged."},
}
(OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
md = f"""# FF CaseSpec independent final acceptance

**{report['verdict']} — tools only. Reviewer FINAL_STOP.**

One bounded pure group: {report['passed_count']}/{len(probes)} checks correct in {report['seconds']} seconds. No 195-test rerun, no 41-case public CLI run, no provider/model/network calls, $0. Production scripts/config/CI and all 10 bound producer files unchanged; scratch restored to initial absence. Git operations were read-only.

## Results

- The exact three original independent adversarial input files retain their SHA. Coverage erasure, cutoff expectation erasure and a rehashed wrong company/market request are rejected by the fixed executable CaseSpec authority.
- Fixed registry detects missing/duplicate/extra IDs. A legitimate full registry and named single-case component remain valid. Complete original request vectors, company/market/kind/FY/period/as-of/intent/mode/companion/limits drift, fixture scenario/date/content/size/key drift and rejection before mocked process launch are covered.
- All 21 original FAIL responses still fail the fixed business assertions if only their labels are changed to PASS. Observed responses cannot be replaced by summary booleans.
- Freeze {EXPECTED_FREEZE} ({len(freeze_after)} product/fixture/PWF/handoff files) and {len(evidence_after)} author evidence files verified before/after. Historical 20-entry manifest, report and ZIP retained. Intentional repaired tool changes are governed by the new freeze, not falsely claimed byte-identical to old live tools.
- `.gitattributes` has exactly two patterns beneath the synthetic fixture directory; representative staged/raw fixture bytes match exactly. The attribute file itself follows ordinary text CRLF normalization, with equivalent content. It does not alter production originals, code or CI.

## Acceptance boundary

The original actual matrix remains **19 PASS / 21 FAIL / 1 PARTIAL**. Forty old reports lack the newly required fixture receipts; they remain absent. These receipts are test observations, not production permissions. ROOT must fix the producer/source-fact cause and rerun the unchanged 41-case integration.

The original `err_unknown_usage` is **FAIL**: its actual transcript was `not_requested`, so no completed ET unknown-usage test is claimed. Its requests and the matrix unknown charge remain null. A separate explicitly synthetic component control confirms a named failed business call with null usage can satisfy the negative-test assertion; that does not certify successful business execution or an overall complete matrix. A fake zero is rejected. The existing single PARTIAL is `local_txt_exact_reuse` and is preserved.

Full evidence: `report.json`. Original evidence, producer code, configuration and Git were not written. This acceptance does not certify live supplier reachability/coverage or completed FF→ET→CWP integration.

Reviewer environment note: an initial fixture-copy preparation hit Windows' 260-character path limit; the short-name retry reached final static Git checks but the sandbox denied `git -C` on the external worktree. Both attempts restored scratch. The same pure group then ran outside the sandbox with short owned directories; no product run or producer correction was involved.

The first completed reviewer attempt is retained separately. Three probe assumptions were corrected using existing evidence: exact old modified-request bytes are Windows CRLF; the original unknown-usage case is FAIL; `.gitattributes` itself is ordinary text while its governed synthetic JSON artifacts retain exact bytes. No product fix was made for these reviewer issues.
"""
(OUT / "report.md").write_text(md, encoding="utf-8")
files = [p for p in OUT.iterdir() if p.is_file() and p.name != "manifest.json"]
manifest = {"schema_version": "w06-independent-case-authority-final-freeze/1",
            "state": "FINAL_STOP", "verdict": report["verdict"],
            "files": [{"path": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in sorted(files)]}
(OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"verdict": report["verdict"], "checks": len(probes), "failed": report["failed"],
                  "seconds": report["seconds"], "manifest_sha256": sha(OUT / "manifest.json")}, ensure_ascii=False))
raise SystemExit(0 if passed else 1)
