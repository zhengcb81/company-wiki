"""ROOT repair receipt: preserve all worker evidence and defer commit/install to ROOT."""
import hashlib
import json
from pathlib import Path
import subprocess

LEAF = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w06/audit-measures-root")
ORIGINAL = Path("C:/Users/郑曾波/Projects/_harness_worktrees/w06/audit-measures")
OUT = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

handoff = json.loads((ORIGINAL / "docs/handoffs/w06-audit-measures/handoff.json").read_text(encoding="utf-8"))
manifest = json.loads((ORIGINAL / "docs/handoffs/w06-audit-measures/manifest.json").read_text(encoding="utf-8"))
original_records = []
for group, rows in (("changed", handoff["changed_files"]), ("input", handoff["input_evidence"]), ("manifest", manifest["files"])):
    for row in rows:
        path = ORIGINAL / row["path"]
        original_records.append({"group": group, "path": row["path"], "sha256": sha(path),
                                 "sha_match": sha(path) == row["sha256"], "size_match": "bytes" not in row or path.stat().st_size == row["bytes"]})
assert all(r["sha_match"] and r["size_match"] for r in original_records)
write(OUT / "original-delivery-still-matches.json", original_records)

def git(*args):
    return subprocess.check_output(["git", "-C", str(LEAF), *args], encoding="utf-8").strip()

owned = ["skills/revenue-forecast-audit/scripts/financial_measure_audit.py",
         "skills/revenue-forecast-audit/references/financial-measure-audit.md",
         "tests/test_financial_measure_root_regressions.py", "tests/test_financial_measure_typed_contract.py",
         "tests/fixtures/financial_measures/root_acceptance_regressions.json"]
file_rows = [{"path": p, "sha256": sha(LEAF / p), "bytes": (LEAF / p).stat().st_size} for p in owned]
readonly = ["skills/revenue-forecast-audit/scripts/audit_contracts.py", "skills/revenue-forecast-audit/scripts/audit_run.py",
            "skills/revenue-forecast-audit/scripts/numeric_audit.py", "skills/revenue-forecast-audit/scripts/pool_progress.py",
            "tests/test_financial_measure_audit.py", "tests/test_financial_measure_audit_cli.py"]
readonly_rows = []
for p in readonly:
    base_bytes = subprocess.check_output(["git", "-C", str(LEAF), "show", "HEAD:" + p]) if not p.startswith("tests/test_financial_measure") else subprocess.check_output(["git", "-C", str(LEAF), "show", "6a50d7ed1b4cf389589c7ca62b4ab161b5dc0ad1:" + p])
    readonly_rows.append({"path": p, "sha256": sha(LEAF / p), "unchanged": sha(LEAF / p) == hashlib.sha256(base_bytes).hexdigest()})
assert all(r["unchanged"] for r in readonly_rows)
final_node = json.loads((OUT / "final-node.json").read_text(encoding="utf-8"))
assert final_node["status"] == "PASS" and final_node["restored"] and final_node["source_bytes_unchanged_during_test"]
report = {"schema_version": "w06-root-measures-repair/1", "status": "PASS_WITH_SCOPE",
          "workdir": str(LEAF), "branch": git("branch", "--show-current"), "head": git("rev-parse", "HEAD"),
          "merge_head": git("rev-parse", "MERGE_HEAD"), "committed": False,
          "source_files": file_rows, "readonly_compatibility": readonly_rows,
          "git_status": git("status", "--short").splitlines(), "full_tree_diff": git("diff", "HEAD", "--stat"),
          "original_delivery_sha_checks": len(original_records), "original_delivery_unchanged": True,
          "tests": {"frozen_red": "19 tests: 11 FAIL, 5 content-boundary ERROR, 3 PASS; no ImportError",
                    "typed_red": "17 tests: 29 failed subtests, 5 content-boundary ERROR; no ImportError",
                    "focused_green": "76 PASS; original 40 assertions unchanged, 19 frozen + 17 typed tests",
                    "full_current_main_suite": "296 PASS in 75.047s", "numeric_unchanged": "7 PASS",
                    "offline_cli_e2e": "three synthetic CN/HK/US ledgers exit 0/1/3, mutation FAIL, reports immutable, isolated attempts, sentinels and cleanup PASS",
                    "real_cli_defects_replayed": "missing result ref now 3/UNRESOLVED; changed result currency now 2/INVALID; wrong arity now 2/INVALID with structured report"},
          "root_causes_fixed": ["typed input/output dimension/entity/line/currency/time preconditions", "dependency/result status propagation and role preservation",
                                "relative Decimal precision/display quantum tolerance without one-unit floor", "schema/date/shape/arity/duplicate-id boundaries producing diagnostics",
                                "source availability and future target roles separated from arithmetic"],
          "interfaces": {"schema": "financial-measure-ledger/1 -> financial-measure-audit/1 unchanged",
                         "core": "audit_measures(ledger) -> report; existing shared helpers read-only",
                         "cli": "fresh exclusive attempt report with exits 2/1/3/0; old outputs never overwritten",
                         "report_additions": ["relation.arithmetic_status", "relation.input_contexts", "relation.result_evidence_role", "source_qualification_verified=false"]},
          "root_owned_docs": ["skills/revenue-forecast-audit/SKILL.md", "skills/revenue-forecast-audit/references/review-process.md", "skills/revenue-forecast-audit/references/review-analyst.md"],
          "limits": ["source bytes, complete company evidence coverage and economic reasonableness are not evaluated", "source availability missing is visible diagnostic, not source qualification",
                     "definition strings are opaque; reviewers evaluate the semantics of derived labels", "sum joins contiguous flow periods, not simultaneous segment contributions",
                     "unequal 52/53-week periods require an explicit comparability contract instead of guessing"],
          "cleanup": {"owned_root": final_node["owned_root"], "before": "absent", "after": "absent", "restored": True},
          "cost": {"provider_calls": 0, "model_calls": 0, "paid_usd": 0}, "source_truth_verified": False, "economic_reasonableness": "not_evaluated",
          "next": "ROOT independent review of frozen source, normal commit/merge and targeted install; no automatic commit, remote or production writes by this worker"}
write(OUT / "repair-report.json", report)
write(LEAF / "docs/handoffs/w06-audit-measures/root-repair/repair-report.json", report)
md = """# W06 financial measures — ROOT isolated repair

Status **PASS_WITH_SCOPE**, not yet committed or installed. ROOT tree merges original delivery
`6a50d7ed` onto current main `321d4c1`; original worker and all 23 receipt SHA/byte checks remain intact.

Five shared causes are repaired: typed operation input/output compatibility, dependency/unknown state
propagation, unit-aware Decimal precision and tolerance, schema/date/shape/arity boundaries, and explicit
source availability/target-period/evidence roles. No company names, identity repository, permit file,
provider or LLM are involved. Unknown context produces diagnostics rather than fabricated facts.

RED: 19 frozen tests (11 FAIL + 5 business-content ERROR); 17 extra typed tests (29 failed subtests +
5 business-content ERROR). GREEN: concentrated 76 PASS with the original 40 assertions unchanged.
One final current-main + W05 + W06 suite: **296 PASS / 75.047s**. Unchanged numeric helper: **7 PASS**.
Offline real-CLI synthetic CN/HK/US E2E and three actual earlier defect CLIs pass; all reports are
isolated/immutable. Owned scratch initial/final absent, sentinel bytes preserved, tested source SHA
unchanged across the final node. All new tests remain offline; this full suite is an engineering-node
check, not a new per-commit provider/cross-repo gate.

The schema names and CLI arguments stay unchanged. New relation diagnostics expose arithmetic_status,
input_contexts and result_evidence_role. source_truth_verified is always false; economic_reasonableness
stays not_evaluated. Future guidance/explicit assumptions stay legal and retain their roles; they cannot
be promoted to actual. Missing source or necessary unit/time context cannot receive a PASS relation.

Scope limits: this tool does not read sources or certify economic quality. Definition strings are
opaque: the independent process/analyst reviewers assess derived labels. Current sums join temporal
flow windows rather than same-period segment contributions; unequal 52/53-week periods need an explicit
comparability contract, not a guessed annualization. Unknown availability is visible, not permission.

ROOT's three skill/reviewer instruction files are preserved and included in final source freeze.
Product helpers audit_contracts/audit_run/numeric_audit and W05 pool_progress remain unchanged.
The complete SHA/status/runs/cleanup interface is in `repair-report.json`; detailed evidence resides
in company-wiki phase6/w06_parallel_verification_2026-10-11/evidence/root-audit-measures-acceptance/fix.
ROOT owns independent review, normal final commit/merge, installation and central PWF updates.
"""
(LEAF / "docs/handoffs/w06-audit-measures/root-repair/repair-report.md").write_text(md, encoding="utf-8")
(OUT / "repair-report.md").write_text(md, encoding="utf-8")
files = []
for p in sorted(OUT.iterdir()):
    if p.is_file() and p.name != "manifest.json":
        files.append({"path": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
write(OUT / "manifest.json", {"schema_version": "w06-root-repair-evidence-manifest/1", "status": "PASS_WITH_SCOPE",
                              "retained_bytes": sum(r["bytes"] for r in files), "files": files})
print(json.dumps({"status": report["status"], "source_files": file_rows, "retained_evidence_bytes": sum(r["bytes"] for r in files)}, ensure_ascii=False))
