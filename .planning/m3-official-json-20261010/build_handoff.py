"""One-shot generator for handoff.json (lane evidence, no runtime effect)."""
import datetime
import hashlib
import json
import subprocess

ROOT = ".planning/m3-official-json-20261010"


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def blob(p):
    return subprocess.run(["git", "rev-parse", f"HEAD:{p}"], capture_output=True,
                          text=True, encoding="utf-8").stdout.strip()


REASONS = {
    "src/company_wiki/source_catalog/canonical_writer.py":
        "shared _shared storage intent for owner-less pages; shared destination + provenance without display owner",
    "src/company_wiki/source_catalog/official_json_import.py":
        "official-source-import-request/2 entry: subject validation, shared raw commit, retained-capture failure, recovery",
    "src/company_wiki/source_catalog/official_json_layout.py":
        "declared layout registry official-json-layout/1 (official-paged-qa, official-flat-list), record classification",
    "src/company_wiki/source_catalog/official_json_projection.py":
        "source-projection-ref/1 build/persist/replay/export and evidence spans over exact parent bytes",
    "src/company_wiki/source_catalog/official_json_structure.py":
        "bounded RFC6901 structure parser with token/body byte identity (cwp_json_structure_parser/1.0.0)",
    "src/company_wiki/source_catalog/official_json_subject.py":
        "typed source subjects (single_issuer/multi_issuer_event/unattributed) and import request/2 validation",
    "src/company_wiki/source_catalog/official_source_cli.py":
        "public CLI: /2 import dispatch plus project/read/replay/export operations",
    "src/company_wiki/source_catalog/official_source_flow.py":
        "staging/journal/recovery dispatch for /2 requests; journal tolerates subject-only source; completed capture /2 attachments",
    "src/company_wiki/source_contract/source_manifest.py":
        "SourceSubjectManifest 2.0.0 beside strict 1.0.0 (unknown/partial attribution)",
    "tests/unit/test_m3_official_json_parser.py":
        "responsibility tests: structure parser unit matrix + frozen byte anchors",
    "tests/contract/test_m3_official_json_contract.py":
        "responsibility tests: layout/subject/manifest/projection contracts",
    "tests/contract/test_m3_official_json_frozen_pages.py":
        "responsibility tests: read-only frozen 86-page verification",
    "tests/integration/test_m3_official_json_projection.py":
        "responsibility tests: public import/project/read/replay/export chain + recovery/idempotency",
}
PLANNING_REASON = "PWF lane plan/evidence/log or preserved historical W02 seed (non-runtime)"

files = subprocess.run(["git", "show", "--name-only", "--format=", "HEAD"],
                       capture_output=True, text=True, encoding="utf-8").stdout.split()
changed = [{
    "path": f,
    "byte_sha256": sha(f),
    "git_blob_sha": blob(f),
    "runtime": f.startswith("src/"),
    "reason": REASONS.get(f, PLANNING_REASON),
} for f in files]

LOGDIR = ROOT + "/logs"
CWD = "C:/Users/郑曾波/.codex/worktrees/m3-official-json-20261010/company-wiki"


def test_entry(name, phase, argv, cwd, exit_code, log, scope, result):
    return {"name": name, "phase": phase, "argv": argv, "cwd": cwd,
            "exit_code": exit_code, "log": log, "log_sha256": sha(log),
            "scope": scope, "result": result}


tests = [
    test_entry(
        "parser unit RED (module absent)", "RED",
        ["python", "-X", "utf8", "-B", "-m", "pytest", "-q",
         "tests/unit/test_m3_official_json_parser.py"],
        CWD, 2, LOGDIR + "/red_unit_parser.log", "unit",
        "ModuleNotFoundError official_json_structure: honest product RED before implementation"),
    test_entry(
        "public CLI RED on sealed latest-01 (import/1)", "RED",
        ["python", "-X", "utf8", "-B", "-m",
         "company_wiki.source_catalog.official_source_cli",
         "--operation", "import", "--config", "<TEMP>/config/catalog.json",
         "--project-root", "<TEMP>", "--request", "<TEMP>/import.json",
         "--input-file", "<ABSOLUTE_SEALED_RAW>/qa-latest-form-01.raw"],
        "<TEMP>", 2, LOGDIR + "/red_public_cli_import.log", "public_cli",
        "exit 2 official-source-failure/1 invalid_text_original: paged multi-record JSON refused by single-content transcript path"),
    test_entry(
        "parser unit GREEN", "GREEN",
        ["python", "-X", "utf8", "-B", "-m", "pytest", "-q",
         "tests/unit/test_m3_official_json_parser.py"],
        CWD, 0, LOGDIR + "/green_unit_parser.log", "unit", "57 passed"),
    test_entry(
        "contract RED (modules absent)", "RED",
        ["python", "-X", "utf8", "-B", "-m", "pytest", "-q",
         "tests/contract/test_m3_official_json_contract.py"],
        CWD, 2, LOGDIR + "/red_contract_layout.log", "contract",
        "ModuleNotFoundError official_json_layout: honest product RED"),
    test_entry(
        "contract GREEN", "GREEN",
        ["python", "-X", "utf8", "-B", "-m", "pytest", "-q",
         "tests/contract/test_m3_official_json_contract.py"],
        CWD, 0, LOGDIR + "/green_contract_layout.log", "contract",
        "26 passed: layouts, subjects, manifest 2.0.0, projection DTO, roles/times, second unseen layout"),
    test_entry(
        "integration RED (chain incomplete)", "RED",
        ["python", "-X", "utf8", "-B", "-m", "pytest", "-q",
         "tests/integration/test_m3_official_json_projection.py"],
        CWD, 1, LOGDIR + "/red_integration_chain.log", "integration",
        "9 failed 1 passed: public chain not implemented yet; v1 compat baseline already green"),
    test_entry(
        "integration GREEN", "GREEN",
        ["python", "-X", "utf8", "-B", "-m", "pytest", "-q",
         "tests/integration/test_m3_official_json_projection.py"],
        CWD, 0, LOGDIR + "/green_integration_chain.log", "integration",
        "11 passed incl. multi-page partial pagination honesty and retained-capture recovery"),
    test_entry(
        "related regression (compatibility of modified entry paths)", "COMPATIBILITY",
        ["python", "-X", "utf8", "-B", "-m", "pytest", "-q",
         "tests/contract/test_official_capture_recovery.py",
         "tests/integration/test_official_source_flow.py",
         "tests/contract/test_source_manifest_contract.py",
         "tests/contract/test_official_transcript_layouts.py",
         "tests/contract/test_source_version_reader.py",
         "tests/contract/test_source_export_v2.py"],
        CWD, 0, LOGDIR + "/green_regression_related.log", "integration",
        "173 passed: old TXT/FMP transcript content contract, manifest 1.0.0, export v2.0.0 unchanged"),
    test_entry(
        "final responsibility suite (parser+contract+frozen+integration)", "GREEN",
        ["python", "-X", "utf8", "-B", "-m", "pytest", "-q",
         "tests/unit/test_m3_official_json_parser.py",
         "tests/contract/test_m3_official_json_contract.py",
         "tests/contract/test_m3_official_json_frozen_pages.py",
         "tests/integration/test_m3_official_json_projection.py"],
        CWD, 0, LOGDIR + "/green_final_all.log", "integration", "107 passed"),
    test_entry(
        "ruff changed scope", "STATIC",
        ["ruff", "check", "src/company_wiki",
         "tests/unit/test_m3_official_json_parser.py",
         "tests/contract/test_m3_official_json_contract.py",
         "tests/contract/test_m3_official_json_frozen_pages.py",
         "tests/integration/test_m3_official_json_projection.py"],
        CWD, 0, LOGDIR + "/static_ruff_changed.log", "static", "All checks passed"),
    test_entry(
        "mypy changed scope", "STATIC",
        ["mypy",
         "src/company_wiki/source_catalog/official_json_structure.py",
         "src/company_wiki/source_catalog/official_json_layout.py",
         "src/company_wiki/source_catalog/official_json_subject.py",
         "src/company_wiki/source_catalog/official_json_import.py",
         "src/company_wiki/source_catalog/official_json_projection.py",
         "src/company_wiki/source_catalog/official_source_cli.py",
         "src/company_wiki/source_contract/source_manifest.py"],
        CWD, 0, LOGDIR + "/static_mypy_changed.log", "static",
        "Success: no issues found in 7 source files"),
]

handoff = {
    "schema_version": "m3-lane-handoff/1",
    "lane_id": "M3-JSON",
    "observed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "owner": "Hermes Agent (external harness takeover of errored built-in agent)",
    "package_status": "complete",
    "repos": [{
        "repository": "company-wiki",
        "worktree": CWD,
        "branch": "codex/m3-official-json-20261010",
        "base_head": "3c791e3c2a16c12627cc25d0bd8681cc9458e48b",
        "head": "8abfad074057ff8d5c89e01aea8f87a73be5405f",
        "changed_files": changed,
        "git_status_explanation": (
            "Commit 8abfad07 contains exactly the lane write set: 9 runtime source files "
            "(source_catalog/official_json_* + official_source_flow/official_source_cli/"
            "canonical_writer + source_contract/source_manifest.py), 4 dedicated test files, "
            "and non-runtime planning artifacts (PWF .planning/m3-official-json-20261010 incl. "
            "logs, preserved W02 seed docs, .active_plan pointer). After the commit only the "
            "normal-commit.log (empty: pre-commit hooks silent on success; first failed attempt "
            "was overwritten by rerun) and normal-push.log remain as uncommitted evidence files. "
            "No production config touched (config/source_catalog.yaml SHA unchanged vs "
            "baseline_shas.txt)."),
        "push": {
            "status": "pass",
            "evidence": [
                LOGDIR + "/normal-push.log",
                "push output: * [new branch] codex/m3-official-json-20261010 -> codex/m3-official-json-20261010",
                "pre-push gate: 2637 passed in 238.30s - pre-push gate GREEN",
            ],
            "note": ("git push -u origin codex/m3-official-json-20261010 exit 0; remote branch "
                     "created at 8abfad074057ff8d5c89e01aea8f87a73be5405f"),
        },
        "ci": {
            "status": "not_available",
            "evidence": [
                ".github/workflows/ci.yml on.push.branches=[master], on.pull_request.branches=[master]",
                "GitHub commit status API for 8abfad07: state=pending total_count=0; check-runs: none",
                "branch push to codex/* does not trigger any workflow by configuration",
            ],
            "note": ("No workflow runs on non-master branch pushes by design (ci.yml trigger set). "
                     "Local pre-push gate ran the affected suites (2637 passed). Exact CI for this "
                     "SHA will exist only via PR to master; MAIN integration node should observe it then."),
        },
        "remote_head": "8abfad074057ff8d5c89e01aea8f87a73be5405f",
        "ci_head": None,
    }],
    "interfaces": [
        "official-source-import-request/2 + official-source-import-result/2 (typed source_subject, shared _shared raw storage)",
        "official-json-layout/1 registry: official-paged-qa/1.0.0 + official-flat-list/1.0.0 (declared, not hardcoded per company/ticker/page)",
        "source-projection-ref/1 (projection identity = parent refs + adapter + issuer + as-of + records + coverage; never the parent content_sha256)",
        "official-json-projection-request/1, official-source-read-request/1 (stdout = exact raw bytes), official-json-replay-request/1, source-projection-export-request/1",
        "source-projection-export/1 bundle with EvidenceSpan v1 (cwp-json-pointer/1 locators in structured_value.source_locator)",
        "source-manifest 2.0.0 (SourceSubjectManifest: unknown/partial attribution) alongside strict unchanged 1.0.0",
        "cwp_json_structure_parser/1.0.0 + cwp_official_json/1.0.0 (structure + layout composition identity)",
        "MAIN integration contract: see INTERFACE_CHANGE.md (official_json AUTO source class, source+projection dedup key, generation binding)",
    ],
    "tests": tests,
    "restore": {
        "status": "pass",
        "evidence": [
            "all fixtures use pytest tmp_path/tempfile.TemporaryDirectory auto-cleanup (owned TEMP roots only)",
            "sealed run C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/m3-20261009T184946-cn-688012 opened read-only; 86 pages byte-identical in frozen-page tests at end of run",
            "config/source_catalog.yaml and config.yaml unchanged (git status clean for config; baseline_shas.txt recorded at start)",
            "no provider/model/token/cost; no external network calls (tests assert against fixed fixtures)",
        ],
        "note": ("TEMP-only derived/imported files created inside test-owned roots and deleted with "
                 "their roots; no initial files outside the owned TEMP were modified or deleted. "
                 "Retained-capture recovery test proves the /2 failure path leaves its staging "
                 "bytes recoverable."),
    },
    "usage": {
        "external_provider_calls": 0,
        "external_model_calls": 0,
        "paid_tokens": 0,
        "paid_micro_usd": 0,
        "unknown_preserved": True,
    },
    "main_integration": {
        "status": "pending",
        "evidence": [
            ROOT + "/INTERFACE_CHANGE.md",
            "main_auto_integration deliberately pending: automation/* is MAIN-owned and untouched",
        ],
        "note": ("source_public_api complete; main_auto_integration (AUTO official_json class, "
                 "select/replay route, batch dedup by source+projection, generation binding) awaits "
                 "MAIN wiring per INTERFACE_CHANGE.md section 2 and its rerun commands."),
    },
    "remaining": [
        "MAIN: wire automation/narrative_formats source_class official_json, narrative_select/replay JSON route, NarrativeBatchRequest dedup by source+projection identity, generation binding to parser/adapter/projection/as-of (INTERFACE_CHANGE.md section 2; rerun the two listed test commands plus AUTO suites).",
        "MAIN: decide packaged compatibility policy registration for new contracts (manifest 2.0.0 / projection / projection-export) in schemas/source_contract_compatibility.v1.json + SOURCE_CONTRACT_NAMES.",
        "External unknowns (single-listed, not guessed): server-side companyfilter existence and real request fields (no public probing), provider timezone semantics for crtTime/updTime/auditTime, answer first-publication time and historical revision interface, cross-issuer Q/A real cases, second official real-world layout fixture.",
        "Real company/research validation and the three-repo real big node run under MAIN (this lane ran zero model calls and no revenue work).",
        "Exact CI observation: pending PR to master; ci.yml does not run on codex/* pushes (evidence in repos[0].ci).",
    ],
}

with open(ROOT + "/handoff.json", "w", encoding="utf-8", newline="\n") as fh:
    json.dump(handoff, fh, ensure_ascii=False, indent=2)
print("written", ROOT + "/handoff.json")
