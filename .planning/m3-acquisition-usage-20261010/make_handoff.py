"""One-off generator: handoff.json + runtime_file_closure.json (PWF audit copy)."""
import hashlib
import json
import subprocess
import time
from pathlib import Path

W = Path(r"C:/Users/郑曾波/.codex/worktrees/m3-acquisition-usage-20261010")
P = W / "company-wiki" / ".planning" / "m3-acquisition-usage-20261010"


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def blob(root, rel):
    out = subprocess.run(["git", "-C", str(root), "rev-parse", f"HEAD:{rel}"],
                         capture_output=True, text=True, encoding="utf-8").stdout.strip()
    return out or None


repos = {
    "company-wiki": {
        "base_head": "3c791e3c2a16c12627cc25d0bd8681cc9458e48b",
        "head": "d65e421cbd48e4f8622b5af19b9239ef0a878d8e",
        "runtime": [
            "src/company_wiki/source_catalog/acquisition_observation.py",
            "src/company_wiki/source_catalog/acquisition_failure.py",
            "src/company_wiki/source_catalog/acquisition_service.py",
            "src/company_wiki/source_catalog/adapter_process.py",
            "src/company_wiki/source_catalog/bounded_http.py",
            "src/company_wiki/source_catalog/dayu_sdk_cli.py",
            "src/company_wiki/source_catalog/download_budget.py",
            "src/company_wiki/source_catalog/source_operation.py",
        ],
        "tests": [
            "tests/unit/test_m3_acquisition_usage_observation.py",
            "tests/integration/test_m3_acquisition_usage_cwp.py",
        ],
        "reason": "CWP producer: acquisition-observation/1 sibling DTO, budget exchange/fee evidence, adapter receipt extensions",
    },
    "filing-fetch": {
        "base_head": "41ba0150c9c634f6021c9346744cada391ec2c4c",
        "head": "f0f4e36319d6b3afc17e896f12a2aa1b183894b0",
        "runtime": [
            "scripts/fetch_filing.py",
            "scripts/ff_provider_cause.py",
            "scripts/ff_v2_envelope.py",
            "scripts/filing_contracts.py",
        ],
        "tests": ["tests/test_m3_acquisition_usage_ff.py"],
        "reason": "FF faithful pass-through: validated sibling on the v2 envelope top level",
    },
    "revenue-forecast": {
        "base_head": "0c248d9a07a2dd7a2c756946d88507479d5e9d15",
        "head": "741f7c01fc2e13d42f919aa0fc8053eb8cabfe08",
        "runtime": [
            "scripts/filing_fetch_client.py",
            "scripts/filing_upstream_cause.py",
            "scripts/source_preparation.py",
        ],
        "tests": [
            "tests/test_m3_acquisition_usage_rf.py",
            "tests/test_m3_acquisition_usage_e2e.py",
        ],
        "reason": "RF pass-through: failure_observation projection, client/preparation error documents, cross-repo E2E",
    },
}

closure = {"schema": "m3-usage-runtime-closure/1", "repos": {}}
handoff_repos = []
for name, spec in repos.items():
    root = W / name
    files = []
    for rel in spec["runtime"] + spec["tests"]:
        files.append({
            "path": rel,
            "byte_sha256": sha256(root / rel),
            "git_blob_sha": blob(root, rel),
            "runtime": rel in spec["runtime"],
            "reason": spec["reason"] if rel in spec["runtime"] else "lane test evidence",
        })
    closure["repos"][name] = {"head": spec["head"],
                              "runtime_files": [f for f in files if f["runtime"]]}
    if name == "company-wiki":
        status_note = ("clean except untracked pre-existing docs/plans/.../"
                       "m3_root_implementation_2026-10-10/ (W06 seed records, "
                       "left read-only per card)")
        ci = {"status": "not_available",
              "evidence": ["GitHub API head_sha=d65e421c query -> 0 runs",
                           ".github/workflows/ci.yml on.push.branches=[master] only"],
              "note": "workflow does not trigger on codex/* branches; exact CI not_available for this head"}
        ci_head = None
    else:
        status_note = "clean; only lane source/tests/.planning records changed"
        ci = {"status": "pass",
              "evidence": ["quality workflow completed success at head "
                           + spec["head"][:12] + " (GitHub API head_sha query)"],
              "note": "exact-head run"}
        ci_head = spec["head"]
    handoff_repos.append({
        "repository": name,
        "worktree": str(root),
        "branch": "codex/m3-acquisition-usage-20261010",
        "base_head": spec["base_head"],
        "head": spec["head"],
        "changed_files": files,
        "git_status_explanation": status_note,
        "push": {"status": "pass",
                 "evidence": ["git push -u origin codex/m3-acquisition-usage-20261010 (new branch)"],
                 "note": "pushed in CWP->FF->RF order"},
        "ci": ci,
        "remote_head": spec["head"],
        "ci_head": ci_head,
    })

ci_path = P / "exact_ci_observation.json"
ci = json.loads(ci_path.read_text(encoding="utf-8"))
ci["repos"]["company-wiki"] = {
    "head_sha": repos["company-wiki"]["head"],
    "run_count": 0,
    "runs": [],
    "status": "not_available",
    "note": "ci.yml triggers on master only; codex/* pushes produce no runs",
}
ci_path.write_text(json.dumps(ci, ensure_ascii=False, indent=2), encoding="utf-8")


def test_entry(name, phase, argv, cwd, log_name, scope, result, exit_code):
    log = P / log_name
    return {"name": name, "phase": phase, "argv": argv, "cwd": cwd,
            "exit_code": exit_code, "log": str(log), "log_sha256": sha256(log),
            "scope": scope, "result": result}


tests = [
    test_entry("CWP integration RED at base", "RED",
               ["python", "-X", "utf8", "-B", "-m", "pytest", "-q",
                "tests/integration/test_m3_acquisition_usage_cwp.py", "-p", "no:cacheprovider"],
               str(W / "company-wiki"), "red_cwp_integration.log", "integration",
               "9 failed, all KeyError acquisition_observation (product: no observation channel at base)", 1),
    test_entry("CWP unit+integration GREEN", "GREEN",
               ["python", "-X", "utf8", "-B", "-m", "pytest", "-q",
                "tests/unit/test_m3_acquisition_usage_observation.py",
                "tests/integration/test_m3_acquisition_usage_cwp.py",
                "plus 8 responsibility suites", "-p", "no:cacheprovider"],
               str(W / "company-wiki"), "green_cwp_final.log", "integration",
               "146 passed (20 new + 126 responsibility incl. acquisition-failure diagnostics/recovery/adapter budget/CLI e2e)", 0),
    test_entry("FF projection RED at base", "RED",
               ["python", "-X", "utf8", "-B", "-m", "pytest", "-q",
                "tests/test_m3_acquisition_usage_ff.py", "-p", "no:cacheprovider"],
               str(W / "filing-fetch"), "red_ff_projection.log", "contract",
               "21 failed (product: no validated sibling / envelope projection at base)", 1),
    test_entry("FF contract GREEN", "GREEN",
               ["python", "-X", "utf8", "-B", "-m", "pytest", "-q",
                "tests/test_m3_acquisition_usage_ff.py",
                "plus 6 responsibility suites", "-p", "no:cacheprovider"],
               str(W / "filing-fetch"), "green_ff_final.log", "contract",
               "167 passed (21 new + 146 responsibility incl. test_failure_usage_continuity)", 0),
    test_entry("RF projection RED at base", "RED",
               ["python", "-X", "utf8", "-B", "-m", "pytest", "-q",
                "tests/test_m3_acquisition_usage_rf.py", "-p", "no:cacheprovider"],
               str(W / "revenue-forecast"), "red_rf_projection.log", "contract",
               "15 failed / 4 passed (product: observation never projected at base)", 1),
    test_entry("RF contract GREEN", "GREEN",
               ["python", "-X", "utf8", "-B", "-m", "pytest", "-q",
                "tests/test_m3_acquisition_usage_rf.py",
                "plus 5 responsibility suites", "-p", "no:cacheprovider"],
               str(W / "revenue-forecast"), "green_rf_final.log", "contract",
               "187 passed (19 new + 168 responsibility incl. test_source_failure_observations)", 0),
    test_entry("Cross-repo public E2E", "GREEN",
               ["python", "-X", "utf8", "-B", "-m", "pytest", "-q",
                "tests/test_m3_acquisition_usage_e2e.py", "-p", "no:cacheprovider"],
               str(W / "revenue-forecast"), "green_e2e_final.log", "public_cli",
               "2 passed: real subprocess RF preparation -> FF CLI -> CWP CLI -> loopback provider; "
               "us_download (3 exchanges, wire 191 < entity 4553, cost 0.0009), us_reuse (0 body GET), "
               "cn_download (second market), us_missing (RF exit 3 keeps full observation); "
               "argv/stdout/stderr/exit saved in e2e_logs/", 0),
    test_entry("TEMP restore", "RESTORE",
               ["python", "-c", "<restore receipt generator>"],
               str(W / "company-wiki"), "restore_receipt.json", "restore",
               "production config source_catalog.yaml byte-identical (3d159a4e...) across worktrees; "
               "all fixtures in TemporaryDirectory contexts; no extra originals; loopback servers shut down", 0),
]

handoff = {
    "schema_version": "m3-lane-handoff/1",
    "lane_id": "M3-USAGE",
    "observed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "owner": "harness agent (external takeover after built-in terminal error)",
    "package_status": "complete",
    "repos": handoff_repos,
    "interfaces": [
        "acquisition-observation/1 (new sibling DTO; closed 12-key shape; usage_scope=operation)",
        "acquisition_usage/1.0 unchanged (response_bytes + cost_usd strict)",
        "acquisition-failure/1 unchanged (7-key closed DTO)",
        "operation DTO 1.0 additive optional acquisition_observation key (subset-tolerant consumers)",
        "FF v2 envelope 2.0 additive top-level acquisition_observation (success/gap/error; filing shape untouched)",
        "RF failure_observation projects the sibling (top-level first, detail fallback)",
    ],
    "tests": tests,
    "restore": {"status": "pass",
                "evidence": [str(P / "restore_receipt.json"),
                             "conftest production_config_integrity asserted in every suite"],
                "note": "pytest tmp trees auto-managed; nothing left in companies/raw/config"},
    "usage": {"external_provider_calls": 0, "external_model_calls": 0, "paid_tokens": 0,
              "paid_micro_usd": 0, "unknown_preserved": True},
    "main_integration": {"status": "pending",
                         "evidence": ["MAIN patch list in INTERFACE_CHANGE.md section 6",
                                      "runtime SHA closure in runtime_file_closure.json"],
                         "note": "shared entry integration and real-company major node are MAIN's task; not run by this lane"},
    "remaining": [
        "MAIN patch 1: CWP error_taxonomy.structured_error 3-line sibling publication (INTERFACE_CHANGE.md section 6.1); without it hard-failure stderr carries no observation (returned-gap/operation channels work today)",
        "MAIN patch 2: add tests/test_m3_acquisition_usage_ff.py to FF tools/ci_tests.py CI_TESTS list",
        "MAIN patch 3: none for source_catalog/cli.py (observation rides to_dict + facade under --source-ref-v2)",
        "MAIN major node: shared-entry integration and real three-company SEC/ET/official capture verification (this lane did not run public providers; 0 paid calls)",
        "Old 7 unknown model + 1 old FF unknown acquisition remain unknown; not backfilled, not netted (contract)",
    ],
}
out = P / "handoff.json"
out.write_text(json.dumps(handoff, ensure_ascii=False, indent=2), encoding="utf-8")
(P / "runtime_file_closure.json").write_text(json.dumps(closure, ensure_ascii=False, indent=2), encoding="utf-8")
print("handoff.json + runtime_file_closure.json written")
try:
    import jsonschema
    schema = json.loads(Path(
        r"C:/Users/郑曾波/Projects/company-wiki/docs/plans/cross-market-rf-e2e-2026-10-08/"
        r"phase6/m3_parallel_handoff_2026-10-10/handoff.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(handoff, schema)
    print("handoff.json VALID against handoff.schema.json")
except ImportError:
    print("jsonschema not installed; manual validation follows")
