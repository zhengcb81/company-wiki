"""ROOT tool-layer fixes only; no native scripts/config/forecast changes."""
from pathlib import Path

ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w07/root-rf-model-reception')
PACKAGE = ROOT/'tools/model_generalization_matrix'

def edit(name, before, after):
    p = PACKAGE/name
    text = p.read_text(encoding='utf-8')
    assert before in text, (name, before[:100])
    p.write_text(text.replace(before, after, 1), encoding='utf-8')

edit('bootstrap.py', 'from revenue_core import run_forecast', 'from revenue_core import run_forecast, validate_document')
edit('bootstrap.py', 'from research.input_quantities import convert_input_quantity', 'from research.evidence_roles import analyze_operating_research\n    from research.input_quantities import convert_input_quantity')
edit('bootstrap.py', 'run_forecast=run_forecast,', 'run_forecast=run_forecast,\n        validate_document=validate_document,\n        analyze_operating_research=analyze_operating_research,')

edit('native.py', '"request_sha256": self.request_sha256,', '"request_sha256": self.request_sha256,\n            "request": self.request,\n            "result": self.result,')
edit('native.py', '        val = self._rt.period_flow_months(start, end)', '''        try:
            val = self._rt.period_flow_months(start, end)
        except Exception as exc:
            ref.exception_type = type(exc).__name__
            ref.exception_message = str(exc)
            raise''')
p = PACKAGE/'native.py'
p.write_text(p.read_text(encoding='utf-8')+'''
    def analyze_operating_research(self, data: dict[str, Any]) -> dict[str, Any]:
        ref = NativeRef(entry="research.evidence_roles.analyze_operating_research",
                        request_sha256=_sha(data), request=copy.deepcopy(data))
        self.refs.append(ref)
        try:
            checked = copy.deepcopy(data)
            out = self._rt.analyze_operating_research(checked, self._rt.validate_document(checked))
        except Exception as exc:
            ref.exception_type = type(exc).__name__
            ref.exception_message = str(exc)
            raise
        ref.result = out
        ref.result_sha256 = _sha(out)
        return out
''', encoding='utf-8')

edit('runner.py', 'import copy\n', 'import copy\nimport math\n')
edit('runner.py', '    if isinstance(a, (int, float)) and isinstance(b, (int, float)):\n        return abs(a - b) <= TOL * max(1.0, abs(b))', '''    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isfinite(a) and math.isfinite(b) and abs(a - b) <= TOL * max(1.0, abs(b))''')
edit('runner.py', '    started = time.time()\n', '    started = time.time()\n    ref_start = len(engine.refs)\n')
edit('runner.py', '        res.native_refs = [r.to_json() for r in engine.refs]', '''        res.native_refs = [r.to_json() for r in engine.refs[ref_start:]]
        if res.status in {"PASS", "REJECT_OK"} and not res.native_refs:
            res.status = "NOT_RUN"
            res.diagnostics["error"] = "case has no native execution record"''')
edit('runner.py', '    res.observed.setdefault("annual", observed.get("annual"))', '''    res.observed.setdefault("annual", observed.get("annual"))
    if not spec.expected.reject:
        res.assertions.extend(_compare_map("annual", spec.expected.values["annual"], observed.get("annual", {})))''')
edit('runner.py', '    msg = f"{type(exc).__name__}: {exc}"\n    res.observed', '''    if not _is_contract_reject(exc):
        res.status = "ERROR"
        res.diagnostics["error"] = f"{type(exc).__name__}: {exc}"
        return res
    msg = f"{type(exc).__name__}: {exc}"
    res.observed''')
edit('runner.py', 'is_contract_error = isinstance(exc, Exception) and bool(str(exc).strip())', 'is_contract_error = _is_contract_reject(exc) and bool(str(exc).strip())')
edit('runner.py', '''        if field_name in observed:
            obs_val = observed[field_name]
            # Unknown must be null, never 0.
            passed = obs_val is None
            assertions.append(
                Assertion(name=f"unknown[{field_name}]", expected=None, observed=obs_val,
                          passed=passed, kind="unknown")
            )''', '''        obs_val = observed.get(field_name, {"__missing__": True})
        assertions.append(
            Assertion(name=f"unknown[{field_name}]", expected=None, observed=obs_val,
                      passed=field_name in observed and obs_val is None, kind="unknown")
        )''')
edit('runner.py', '''    res.assertions.extend(assertions)
    res.status = "PASS" if all(a.passed for a in res.assertions) else "FAIL"''', '''    res.assertions.extend(assertions)
    res.status = "PASS" if assertions and all(a.passed for a in res.assertions) else "FAIL"''')
edit('runner.py', '    all_rejected = True\n', '''    if not attempts:
        res.status = "NOT_RUN"
        res.diagnostics["error"] = "no conversion attempts declared"
        return res
    all_rejected = True
''')
edit('runner.py', '''        except Exception as exc:  # noqa: BLE001
            messages.append(f"{in_u}->{eng_u}: {type(exc).__name__}: {exc}")''', '''        except Exception as exc:  # noqa: BLE001
            if not _is_contract_reject(exc):
                raise
            all_rejected = all_rejected and bool(str(exc).strip())
            messages.append(f"{in_u}->{eng_u}: {type(exc).__name__}: {exc}")''')
edit('runner.py', '''        from research.evidence_roles import analyze_operating_research
        from revenue_core import validate_document

        data["operating_research"]["calibrations"][0]["observed_range"] = None
        diag = analyze_operating_research(data, validate_document(data))''', '''        data["operating_research"]["calibrations"][0]["observed_range"] = None
        diag = engine.analyze_operating_research(data)''')
edit('runner.py', '''    drop_once = abs(delta.get("2026", 0.0) - (-20.0)) <= TOL * 20.0''', '''    expected_drop = -float(spec.drivers["deferred"])
    drop_once = _num_eq(expected_drop, delta.get("2026"))''')
edit('runner.py', 'name="shock_applied_once", expected=-20.0,', 'name="shock_applied_once", expected=expected_drop,')

# Existing fixture has calendar fiscal year end and independent exponential
# forecast drivers. The H1 flow is unreferenced, so its value MUST NOT be added
# to annual revenue. Do not pretend this fixture tests acquisition/control.
edit('cases.py', 'expected=_e({"months": 6.0}),', 'expected=_e({"months": 6.0, "annual": {"2026": 144.0, "2027": 172.8}}),')
edit('cases.py', 'a cross-calendar partial window inside the FY is accepted at its real coverage', 'a calendar H1 evidence flow keeps six-month coverage and is not added to the annual forecast')
edit('cases.py', '# A six-month flow that crosses calendar years but sits inside the FY window.', '# A calendar H1 evidence flow; unrelated to the annual forecast driver.')

edit('report.py', 'from .runner import CaseResult', 'from .runner import CaseResult\nfrom . import cases as C')
edit('report.py', '''    for cls, rs in by_class.items():
        ok = all(r.status in {"PASS", "REJECT_OK"} for r in rs)
        class_status[cls] = "PASS" if ok else "FAIL"

    return {''', '''    required = {c.case_id: c for c in C.CASES}
    observed_ids = [r.case_id for r in results]
    missing = sorted(set(required) - set(observed_ids))
    unexpected = sorted(set(observed_ids) - set(required))
    duplicates = sorted({cid for cid in observed_ids if observed_ids.count(cid) > 1})
    for cls in sorted({c.cls for c in C.CASES}):
        rs = by_class.get(cls, [])
        expected_ids = {c.case_id for c in C.CASES if c.cls == cls}
        ok = (len(rs) == len(expected_ids) and {r.case_id for r in rs} == expected_ids
              and all(r.status in {"PASS", "REJECT_OK"} for r in rs))
        class_status[cls] = "PASS" if ok else "FAIL"
    coverage = {"missing_cases": missing, "unexpected_cases": unexpected, "duplicate_cases": duplicates}
    clean = (bool(results) and not missing and not unexpected and not duplicates
             and all(s == "PASS" for s in class_status.values())
             and not residuals and cleanup.get("restored_absent") is True
             and cleanup.get("readonly_unchanged") is True
             and cleanup.get("owned_root_restored", True) is True)

    return {
        "status": "COMPLETE" if clean else "FAILED",
        "vector_coverage": coverage,
        "combination_coverage": {
            "status": "PARTIAL",
            "remaining": [
                "M01 explicit CNY/HKD labels and same-currency scaling",
                "M04 dated acquisition/control, cross-FY and missing-quarter ancestry",
                "M06 correlated joint volume/price scenarios",
                "M07 cumulative target and gross/net/cannibalization",
                "M08 future actual/WAPE null through draft output",
            ],
            "note": "Class PASS describes declared vectors only, not every card boundary.",
        },''')
edit('report.py', '    os.makedirs(out_root, exist_ok=True)', '    os.makedirs(out_root, exist_ok=False)')
edit('report.py', '''        f"- generated_at: {report['generated_at']}",''', '''        f"- execution status: {report['status']}",
        f"- combination coverage: {report['combination_coverage']['status']}",
        f"- generated_at: {report['generated_at']}",''')

edit('run.py', '''    # Fixed, read-only trees whose SHA must be unchanged at the end.''', '''    if out_root.exists():
        raise FileExistsError(f"report output already exists: {out_root}")
    if out_root == owned_root or owned_root in out_root.parents or out_root in owned_root.parents:
        raise ValueError("report and scratch roots must be separate")
    # Fixed, read-only trees whose SHA must be unchanged at the end.''')
edit('run.py', '''        if p.is_file():''', '''        if p.is_file() and not any(part in {"__pycache__", ".pytest_cache"} for part in p.parts):''')
edit('run.py', '''    return {"existed": True, "kind": "dir", "entries": entries}''', '''    return {"existed": True, "kind": "dir", "entries": entries,
            "files": _tree_digest(path),
            "directories": sorted(p.relative_to(path).as_posix() for p in path.rglob("*") if p.is_dir())}''')
edit('run.py', '''    owned_root.mkdir(parents=True, exist_ok=True)
    scratch_name = f".tmp/w07-{uuid.uuid4().hex[:8]}"
    scratch = owned_root / scratch_name
    scratch_before = _snapshot(scratch)
    scratch.mkdir(parents=True, exist_ok=True)''', '''    owned_before = _snapshot(owned_root)
    created_parents = []
    ancestor = owned_root
    while not ancestor.exists():
        created_parents.append(ancestor)
        ancestor = ancestor.parent
    owned_root.mkdir(parents=True, exist_ok=True)
    scratch = owned_root / f"w07-{uuid.uuid4().hex}"
    scratch_before = _snapshot(scratch)
    scratch.mkdir(exist_ok=False)''')
edit('run.py', '''                shutil.rmtree(scratch, ignore_errors=True)
            tmp_parent = scratch.parent
            if tmp_parent.name == ".tmp" and tmp_parent.exists() and not any(tmp_parent.iterdir()):
                tmp_parent.rmdir()
            cleanup["restored_absent"] = not scratch.exists()''', '''                if owned_root.resolve() not in scratch.resolve().parents:
                    raise ValueError("scratch escaped owned root")
                shutil.rmtree(scratch)
            for created in created_parents:
                if created.exists() and not any(created.iterdir()):
                    created.rmdir()
            cleanup["restored_absent"] = not scratch.exists()''')
edit('run.py', '''        # Read-only SHA re-check (recorded into the report, not just computed).''', '''        cleanup["owned_root_baseline"] = owned_before
        cleanup["owned_root_restored"] = owned_before == _snapshot(owned_root)
        if not cleanup["owned_root_restored"]:
            residuals.append("owned root baseline not restored")
        # Read-only SHA re-check (recorded into the report, not just computed).''')
edit('run.py', '''        # Finalize cleanup (restore + SHA re-check) BEFORE writing, so the report''', '''        if e2e:
            cli_ok = (
                cli_evidence.get("legal_validate_only", {}).get("returncode") == 0
                and cli_evidence.get("reject_validate_only", {}).get("returncode") == 2
                and "fiscal_year_end" in (cli_evidence.get("reject_validate_only", {}).get("stderr_tail", "")
                                         + cli_evidence.get("reject_validate_only", {}).get("stdout_tail", ""))
                and cli_evidence.get("support_diagnostics", {}).get("returncode") == 0
                and cli_evidence.get("support_output_schema") == "economic-support-diagnostics/1"
            )
            if not cli_ok:
                residuals.append("native CLI evidence incomplete, failed or wrong schema/rejection")
        # Finalize cleanup (restore + SHA re-check) BEFORE writing, so the report''')
edit('run.py', '''    clean = (
        counts["failed"] == 0
        and counts["errored"] == 0
        and counts["reject_mismatch"] == 0
        and counts["not_run"] == 0
    )''', '''    clean = rep["status"] == "COMPLETE"''')
print('Tool-layer shared logic fixes applied; coverage gaps explicitly remain.')
