"""Read-only audit probes. Stdlib only; no product main, DB or network calls.

Prints results to stdout. Caller may persist them with apply_patch in this audit
directory. AST extraction executes only named, already reviewed pure functions.
"""
from __future__ import annotations
import ast
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
REV = ROOT.parent / "revenue-forecast"

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def selected_functions(path, names, namespace):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in selected} == set(names)
    module = ast.Module(body=selected, type_ignores=[])
    exec(compile(module, str(path), "exec"), namespace)
    return namespace

def probes():
    daily = selected_functions(REV / "tools/daily_t2_schedule.py", ["_iso_to_utc", "freshness_status", "task_status"],
        {"datetime": datetime, "UTC": timezone.utc, "timedelta": timedelta, "MAX_AGE_HOURS": 24, "TASK_NAME": "revenue_daily_t2"})
    weekly = selected_functions(REV / "tools/weekly_t3_schedule.py", ["_suite_outcome"], {"subprocess": SimpleNamespace(CompletedProcess=object)})
    scenario = selected_functions(REV / "assurance/unified_completion/uc/scenarios.py", ["closure_report"], {"Any": object})
    future = daily["freshness_status"]({"ok": True, "started_at": "2099-01-01T00:00:00+00:00"}, now="2026-09-05T21:00:00+00:00")
    empty_evidence = scenario["closure_report"]({"counts": {"unique_total": 1}, "scenarios": {"BR-01": {"tier": "T2", "status": "passed", "evidence_path": None, "fixture_hash": None}}})
    daily["_schtasks"] = lambda args: SimpleNamespace(returncode=1, stdout="", stderr="Access is denied")
    gate = selected_functions(REV / "tools/release_gate.py", ["canonical_hash", "validate_report", "compute_sli", "release_decision"],
        {"hashlib": hashlib, "json": json, "datetime": datetime, "UTC": timezone.utc, "timedelta": timedelta,
         "SLI_KEYS": ("reuse", "download_avoidance", "artifact", "consumer_ready", "broker_fidelity", "misattribution", "mine_conflict", "forecast", "backtest", "render"),
         "REQUIRED_REPORT_FIELDS": ("run_id", "started_at", "triplet", "ok", "report_sha256")})
    report = {"run_id": "fixture", "started_at": "2026-09-05T20:59:00+00:00", "triplet": {"revenue": "not-a-commit", "filing": "x", "wiki": "y"}, "ok": False}
    report["report_sha256"] = gate["canonical_hash"](report)
    release = gate["release_decision"]({"only_one_sli": {"ok": True}}, report, None, now="2026-09-05T21:00:00+00:00")
    impl = {"kind": "implementer", "implementer": "alice"}
    revision = selected_functions(REV / "assurance/unified_completion/uc/revision.py", ["select"],
        {"Any": object, "Path": Path, "canonical_hash": lambda value: "h"})
    revision["_load_receipts"] = lambda path: {"11.json": impl, "12.json": {"kind": "reviewer", "reviewer": "bob", "verdict": "rejected", "reviewed_object_sha256": "h"}}
    rejection = revision["select"](Path("in-memory-only"))
    window = selected_functions(REV / "tests/test_ca206_soak_window.py", ["_parse", "daily_window"],
        {"datetime": datetime, "UTC": timezone.utc, "timedelta": timedelta, "DAILY_TARGET": 7, "SoakRun": object})
    same_day = [SimpleNamespace(run_id=str(i), started_at="2026-09-05T12:00:00+00:00", kind="daily", ok=True) for i in range(7)]
    return {"future_timestamp": future, "missing_t2_evidence": empty_evidence,
        "release_not_ok_bad_commits_one_sli_no_ledger": release,
        "rejected_latest_pair": rejection,
        "soak_seven_runs_same_instant": window["daily_window"](same_day, now="2026-09-05T21:00:00+00:00"),
        "permission_denied_schedule": daily["task_status"](),
        "weekly_partial_skip": weekly["_suite_outcome"](SimpleNamespace(returncode=0, stdout="1 passed, 2 skipped", stderr="")),
        "weekly_empty_output": weekly["_suite_outcome"](SimpleNamespace(returncode=0, stdout="", stderr="")),
        "safety": "AST pure functions only; no DB/network/task/product writes"}

def inventory():
    state = read_json(REV / "assurance/unified_completion/state.json")
    rows = []
    for unit, cell in state["units"].items():
        directory = REV / "assurance/unified_completion/receipts" / unit
        receipts = []
        for path in sorted(directory.glob("*.json")):
            try:
                value = read_json(path)
            except (OSError, ValueError) as error:
                receipts.append({"path": str(path.relative_to(REV)), "error": str(error)})
                continue
            if not isinstance(value, dict):
                continue
            if "implementer" not in path.name and "reviewer" not in path.name and "closure" not in path.name:
                continue
            receipts.append({"path": str(path.relative_to(REV)), "raw_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                **{key: value.get(key) for key in ("kind", "schema_version", "verdict", "result_triplet", "reviewed_object_sha256", "canonical_hash")},
                "scope_excerpt": str(value.get("scope", ""))[:500], "notes_excerpt": str(value.get("notes", ""))[:900],
                "implementation_excerpt": str(value.get("implementation", ""))[:600]})
        rows.append({"unit": unit, "state": cell.get("status"), "receipts": receipts})
    registry = read_json(REV / "assurance/unified_completion/scenarios/scenario_registry.json")
    return {"observed_utc": datetime.now(timezone.utc).isoformat(), "units": rows, "unit_count": len(rows),
        "scenarios": {"counts": registry["counts"], "scenarios": registry["scenarios"]}}

def coverage():
    audit_dir = Path(__file__).resolve().parent
    inv = read_json(audit_dir / "evidence-inventory.json")
    tables = {}
    for filename in ("assurance-audit.md", "wiki-audit.md", "filing-audit.md", "revenue-audit.md"):
        for number, line in enumerate((audit_dir / filename).read_text(encoding="utf-8").splitlines(), 1):
            match = re.match(r"\|\s*(CA|ZR)-?(\d{3,4})\s*\|", line)
            if match:
                key = match[1] + "-" + match[2]
                tables.setdefault(key, []).append({"document": filename, "line": number, "row": line})
    rows = [{"unit": u["unit"], "old_state": u["state"], "evidence": tables.get(u["unit"], [])} for u in inv["units"]]
    return {"total": len(rows), "missing": [r["unit"] for r in rows if not r["evidence"]], "rows": rows}

if __name__ == "__main__":
    result = coverage() if "--coverage" in sys.argv else inventory() if "--inventory" in sys.argv else probes()
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":"), default=str))
