from pathlib import Path
FF=Path(r'C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root')
p=FF/'tools/offline_contract_matrix/oracle.py'
text=p.read_text(encoding='utf-8')
text=text.replace('from matrix_outcome import count, source_ref','from matrix_outcome import count, source_ref\nfrom case_specs import audit_coverage, get_spec')
old='''    if report.get("runner"):
        required = set(report.get("required_cases") or [])
        observed = [c.get("id") for c in cases]
        if not required or required != set(observed) or len(observed) != len(set(observed)):
            findings.append(Finding("coverage_gap", None, "required case registry is missing, incomplete or duplicated"))
'''
new='''    # Fixed code registry is authoritative even if runner/required_cases is erased.
    for detail in audit_coverage(cases):
        findings.append(Finding("coverage_gap", None, detail))
    if report.get("runner"):
'''
text=text.replace(old,new)
start=text.index('    for case in cases:\n');end=text.index('    # 6. production bytes',start)
loop=text[start:end]
loop=loop.replace('    for case in cases:\n        case_id = case.get("id")\n        declared = case.get("declared_layer")\n        expected = case.get("expected") or {}','''    for case in cases:
        case_id = case.get("id")
        spec = get_spec(case_id)
        if spec is None:
            findings.append(Finding("unknown_case", case_id, "case has no fixed executable definition"))
            continue
        findings.extend(audit_case(spec, case))
''')
# Extract per-case checks behind one public scoped interface. It cannot certify a matrix.
body=loop[loop.index('        actual = case.get("actual") or {}'):]
body='\n'.join(line[4:] if line.startswith('    ') else line for line in body.splitlines())
text=text[:start]+loop[:loop.index('        actual =')]+text[end:]
text=text.replace('    if report.get("runner"):\n        findings.extend(_bound_evidence(report))','    findings.extend(_bound_evidence(report))')
insert='''
def audit_case(spec, case: dict[str, Any]) -> list[Finding]:
    """Audit one fixed case's declarations and mandatory assertions.

    This is a component check, not complete matrix acceptance; audit() also
    checks mandatory coverage and bound actual request/response/fixture bytes.
    """
    findings = []
    case_id = spec.id
    declared, expected = spec.declared_layer, spec.expected()
    for detail in spec.metadata_errors(case):
        findings.append(Finding("case_contract_mismatch", case_id, detail))
    if case.get("result") != "PASS":
        findings.append(Finding("case_not_passed", case_id, f"actual result {case.get('result')} cannot certify required case"))
'''+body+'''\n    return findings

'''
pos=text.index('\ndef passes(');text=text[:pos]+insert+text[pos:]
text=text.replace('''        if case.get("result") != "PASS":
            continue
        if not runs or root is None:''','''        spec = get_spec(cid)
        if spec and case.get("result") == "PASS" and len(runs) != len(spec.runs):
            findings.append(Finding("case_run_count_mismatch", cid, "required number of attempts not observed"))
        if not runs or root is None:''')
text=text.replace('''        for run in runs:
            request, response = {}, {}''','''        for index, run in enumerate(runs):
            request, response = {}, {}''')
needle='''            if run.get("et_fixture_requests", 0) > 0:'''
addition='''            if spec:
                for detail in spec.request_errors(index, request):
                    findings.append(Finding("case_request_mismatch", cid, detail))
                if index < len(spec.runs) and spec.runs[index].fixture() is not None:
                    try:
                        fixture_path = (root / run["fixture_ref"]).resolve()
                        if not fixture_path.is_relative_to(root):
                            raise ValueError("fixture receipt escapes attempt")
                        raw = fixture_path.read_bytes()
                        if hashlib.sha256(raw).hexdigest() != run["fixture_sha256"]:
                            raise ValueError("fixture receipt bytes changed")
                        fixture = json.loads(raw)
                        for detail in spec.fixture_errors(index, fixture["state"], fixture["with_fmp_key"]):
                            findings.append(Finding("case_fixture_mismatch", cid, detail))
                    except Exception as exc:
                        findings.append(Finding("missing_case_fixture_evidence", cid, f"{type(exc).__name__}: {exc}"))
                elif index < len(spec.runs) and "fixture_ref" in run:
                    # Key-presence vector is mandatory even without supplier fixture.
                    try:
                        fixture_path=(root / run["fixture_ref"]).resolve()
                        if not fixture_path.is_relative_to(root): raise ValueError("fixture escapes attempt")
                        raw=fixture_path.read_bytes()
                        if hashlib.sha256(raw).hexdigest()!=run["fixture_sha256"]: raise ValueError("fixture bytes changed")
                        fixture=json.loads(raw)
                        for detail in spec.fixture_errors(index,fixture["state"],fixture["with_fmp_key"]):
                            findings.append(Finding("case_fixture_mismatch",cid,detail))
                    except Exception as exc:
                        findings.append(Finding("invalid_bound_evidence",cid,f"fixture: {exc}"))
'''
text=text.replace(needle,addition+needle)
text=text.replace('''        if (case.get("expected") or {}).get("run_twice") and len(runs) >= 2:''','''        if spec and spec.expected().get("run_twice") and len(runs) >= 2:''')
p.write_text(text,encoding='utf-8')

# Existing pure vector controls now use named fixed cases rather than unowned c1.
p=FF/'tests/test_w06_contract_matrix.py';text=p.read_text(encoding='utf-8')
text=text.replace('_case("c1", declared="real-3layer"','_case("chainA_download_reuse", declared="real-3layer"')
text=text.replace('_case("c1", expected={"run_twice": True}', '_case("chainA_download_reuse", expected={"run_twice": True}')
text=text.replace('_case("c1", expected={"past_cutoff": True}', '_case("call_past_cutoff", expected={"past_cutoff": True}')
text=text.replace('_case("c1", expected={"unknown_usage": True}', '_case("err_unknown_usage", expected={"unknown_usage": True}')
text=text.replace('_case("unknown_reuse", expected={"run_twice": True}', '_case("chainA_download_reuse", expected={"run_twice": True}')
text=text.replace('_case("unknown_usage", expected={"unknown_usage": True}', '_case("err_unknown_usage", expected={"unknown_usage": True}')
text=text.replace('def test_oracle_clean_report_passes():','def test_single_vector_control_cannot_certify_full_matrix():')
text=text.replace('''    assert findings == []
    assert oracle_mod.passes(findings) is True''','''    assert any(f.vector == "coverage_gap" for f in findings)
    assert oracle_mod.passes(findings) is False''')
p.write_text(text,encoding='utf-8')
p=FF/'tools/offline_contract_matrix/report.py';text=p.read_text(encoding='utf-8').replace('RUNNER_VERSION = "2.0.0"','RUNNER_VERSION = "2.1.0"');p.write_text(text,encoding='utf-8')
print('Oracle consumes CaseSpec rather than mutable report declarations')
