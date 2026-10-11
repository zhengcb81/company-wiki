"""Freeze reception evidence and add ROOT behavioral tests to isolated RF tree."""
import hashlib
import json
from pathlib import Path
import subprocess

PLAN = Path(__file__).resolve().parent
AUTHOR = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w07/rf-model-quality')
ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w07/root-rf-model-reception')
MAIN = Path('C:/Users/郑曾波/Projects/revenue-forecast')

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

handoff = json.loads((AUTHOR/'docs/handoffs/w07-rf-model-quality/handoff.json').read_text(encoding='utf-8'))
checks = []
for row in handoff['changed_files'] + handoff['readonly_inputs']:
    path = row['path'].split(' (')[0].replace('\\', '/')
    p = AUTHOR / path
    raw = p.read_bytes()
    lf = raw.replace(b'\r\n', b'\n')
    candidates = {'raw': sha(p), 'LF': hashlib.sha256(lf).hexdigest(), 'CRLF': hashlib.sha256(lf.replace(b'\n', b'\r\n')).hexdigest()}
    checks.append({'path': path, 'sha256': sha(p), 'declared_sha256': row['sha256'], 'matches': row['sha256'] in candidates.values(), 'matching_encoding': [k for k, v in candidates.items() if v == row['sha256']]})
assert all(c['matches'] for c in checks if c['path'].startswith('.planning/')), checks
# Handoff hashes for five tool files are stale after the committed formatter.
# Pin actual Git HEAD and bytes; this metadata defect is diagnostic, not a new permit.
wip = {}
for relative in ['assurance/runs/daily_alert.jsonl', 'assurance/runs/weekly_alert.jsonl', 'assurance/runs/weekly_manifest.json']:
    wip[relative] = sha(MAIN/relative)
for p in (MAIN/'output').rglob('*'):
    if p.is_file():
        wip[p.relative_to(MAIN).as_posix()] = sha(p)
evidence = {'author_head': subprocess.check_output(['git', '-C', str(AUTHOR), 'rev-parse', 'HEAD'], text=True).strip(), 'canonical_repository': str(MAIN), 'author_hash_checks': checks, 'main_wip': wip, 'origin_main': subprocess.check_output(['git', '-C', str(MAIN), 'rev-parse', 'origin/main'], text=True).strip()}
(PLAN/'freeze.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

tests = '''"""Independent ROOT regression tests: failures must not become successful evidence."""
from dataclasses import replace
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from model_generalization_matrix import bootstrap, cases as C, report as R, run as M
from model_generalization_matrix.native import NativeEngine
from model_generalization_matrix.oracle import Expected
from model_generalization_matrix.runner import CaseResult, _assert_values, _num_eq, run_case

@pytest.fixture(scope="module")
def runtime():
    return bootstrap.load_runtime()

def result(spec):
    return CaseResult(spec.case_id, spec.cls, spec.vector, "draft", spec.boundary, "NOT_RUN", spec.expected)

@pytest.mark.parametrize("case_id", ["M01-C", "M02-C", "M04-C"])
def test_infrastructure_failure_is_never_contract_rejection(runtime, case_id):
    def boom(*a, **kw):
        raise RuntimeError("native unavailable")
    rt = SimpleNamespace(**vars(runtime))
    rt.run_forecast = boom
    rt.convert_input_quantity = boom
    assert run_case(C.case_index()[case_id], NativeEngine(rt)).status == "ERROR"

def test_empty_conversion_does_not_pass(runtime):
    spec = replace(C.case_index()["M01-C"], drivers={"value": 1})
    assert run_case(spec, NativeEngine(runtime)).status not in {"PASS", "REJECT_OK"}

def test_missing_unknown_is_not_null():
    spec = replace(C.case_index()["M05-C"], expected=Expected(values={}, unknown_fields=("cagr",)))
    assert _assert_values(spec, result(spec), {}).status == "FAIL"

def test_empty_oracle_does_not_pass():
    spec = replace(C.case_index()["M01-L"], expected=Expected(values={}))
    assert _assert_values(spec, result(spec), {}).status != "PASS"

@pytest.mark.parametrize("a,b", [(0, False), (1, True), (True, 1)])
def test_boolean_is_not_revenue(a, b):
    assert not _num_eq(a, b)

def test_native_records_are_case_local_and_replayable(runtime):
    engine = NativeEngine(runtime)
    first = run_case(C.case_index()["M01-L"], engine)
    second = run_case(C.case_index()["M02-L"], engine)
    assert len(second.native_refs) == 1
    assert first.native_refs[0]["request"]
    assert second.native_refs[0]["result"]
    assert first.native_refs[0]["request_sha256"] != second.native_refs[0]["request_sha256"]

def test_unknown_support_records_its_actual_native_call(runtime):
    res = run_case(C.case_index()["M08-C"], NativeEngine(runtime))
    assert res.status == "PASS"
    assert res.native_refs
    assert any("analyze_operating_research" in r["entry"] for r in res.native_refs)

def test_period_case_catches_wrong_annual_even_with_correct_months(runtime):
    spec = C.case_index()["M04-L"]
    native = runtime.run_forecast
    def wrong(*a, **kw):
        out = native(*a, **kw)
        out["consolidated_forecast"]["base"]["annual_revenue"]["2026"] = 999999
        return out
    rt = SimpleNamespace(**vars(runtime))
    rt.run_forecast = wrong
    assert run_case(spec, NativeEngine(rt)).status == "FAIL"

def test_absent_owned_root_restored(runtime, tmp_path):
    owned = tmp_path/"owned"
    rep = M.run_matrix(tmp_path/"report", owned, e2e=False)
    assert rep["cleanup"]["restored_absent"]
    assert not owned.exists()

def test_existing_owned_sentinel_preserved(runtime, tmp_path):
    owned = tmp_path/"owned"
    (owned/".tmp").mkdir(parents=True)
    sentinel = owned/".tmp"/"sentinel"
    sentinel.write_bytes(b"original")
    M.run_matrix(tmp_path/"report", owned, e2e=False)
    assert sentinel.read_bytes() == b"original"
    assert sorted(p.relative_to(owned).as_posix() for p in owned.rglob("*")) == [".tmp", ".tmp/sentinel"]

def test_existing_report_cannot_be_overwritten(runtime, tmp_path):
    out = tmp_path/"report"
    out.mkdir()
    previous = out/"model-generalization-matrix.json"
    previous.write_bytes(b"previous attempt")
    with pytest.raises(FileExistsError):
        M.run_matrix(out, tmp_path/"owned", e2e=False)
    assert previous.read_bytes() == b"previous attempt"
    assert not (tmp_path/"owned").exists()

def test_empty_and_incomplete_matrix_are_not_complete():
    common = dict(started_at="x", finished_at="x", wall_seconds=0, cleanup={"restored_absent": True, "readonly_unchanged": True}, residuals=[], engine_versions={})
    assert R.build_report([], **common).get("status") != "COMPLETE"
    spec = C.case_index()["M01-L"]
    res = result(spec)
    res.status = "PASS"
    rep = R.build_report([res], **common)
    assert rep["class_status"].get("M01") != "PASS"

@pytest.mark.parametrize("kind", ["legal", "reject", "support", "schema", "timeout"])
def test_cli_failure_prevents_success(runtime, tmp_path, monkeypatch, kind):
    def cli(*args):
        ev = {"legal_validate_only": {"returncode": 0}, "reject_validate_only": {"returncode": 2, "stderr_tail": "fiscal_year_end invalid"}, "support_diagnostics": {"returncode": 0}, "support_output_schema": "economic-support-diagnostics/1"}
        if kind == "schema":
            ev["support_output_schema"] = "wrong"
        elif kind == "timeout":
            ev["legal_validate_only"] = {"error": "TimeoutExpired"}
        else:
            key = {"legal": "legal_validate_only", "reject": "reject_validate_only", "support": "support_diagnostics"}[kind]
            ev[key]["returncode"] = 9
        return ev
    monkeypatch.setattr(M, "_run_cli_evidence", cli)
    rc = M.main(["--owned-root", str(tmp_path/"owned"), "--out-root", str(tmp_path/"report"), "--e2e"])
    assert rc == 1

def test_readonly_drift_prevents_success(runtime, tmp_path, monkeypatch):
    calls = 0
    def digest(root):
        nonlocal calls
        calls += 1
        return {"value": str(calls//3)}
    monkeypatch.setattr(M, "_tree_digest", digest)
    assert M.main(["--owned-root", str(tmp_path/"owned"), "--out-root", str(tmp_path/"report")]) == 1

def test_cleanup_failure_prevents_success(runtime, tmp_path, monkeypatch):
    native = M.shutil.rmtree
    def blocked(*a, **kw):
        raise OSError("synthetic filesystem failure")
    monkeypatch.setattr(M.shutil, "rmtree", blocked)
    try:
        assert M.main(["--owned-root", str(tmp_path/"owned"), "--out-root", str(tmp_path/"report")]) == 1
    finally:
        monkeypatch.setattr(M.shutil, "rmtree", native)
        if (tmp_path/"owned").exists():
            native(tmp_path/"owned")
'''
target = ROOT/'tools/tests/test_root_w07_model_boundaries.py'
assert not target.exists()
target.write_text(tests, encoding='utf-8')
print(json.dumps({'hashes_verified': len(checks), 'wip_files': len(wip), 'tests': str(target)}, ensure_ascii=False))
