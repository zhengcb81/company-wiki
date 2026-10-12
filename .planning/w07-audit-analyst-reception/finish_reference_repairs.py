from pathlib import Path

ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w07/root-audit-analyst-reception')
target = ROOT / 'skills/revenue-forecast-audit/scripts/analyst_risk_audit.py'
code = target.read_text(encoding='utf-8')
assert 'def _reference_index(' not in code

def replace(old, new):
    global code
    assert code.count(old) == 1, old[:90]
    code = code.replace(old, new)

marker = '\ndef _finding('
helper = '''
def _reference_index(native_input):
    index = {}
    for key, kind, identity in (("parameters", "parameter", "parameter_id"),
                                ("evidence_claims", "claim", "claim_id")):
        for i, row in enumerate(native_input.get(key) or []):
            if isinstance(row, dict) and isinstance(row.get(identity), str):
                index[(kind, row[identity])] = {"document": "input", "pointer": f"/{key}/{i}"}
    for cid, (i, _) in _calibration_index(native_input).items():
        index[("calibration", cid)] = {"document": "input", "pointer": f"/operating_research/calibrations/{i}"}
    for i, row in enumerate((native_input.get("growth_driver_tree") or {}).get("drivers") or []):
        if isinstance(row, dict) and isinstance(row.get("driver_id"), str):
            index[("driver", row["driver_id"])] = {"document": "input", "pointer": f"/growth_driver_tree/drivers/{i}"}
    return index


def _attach_references(row, index):
    refs = []
    for key, kind in (("parameter_ids", "parameter"), ("claim_ids", "claim"),
                      ("driver_ids", "driver"), ("calibration_ids", "calibration")):
        for identity in row[key]:
            resolved = index.get((kind, identity))
            ref = {"kind": kind, "id": identity, "resolved": resolved is not None}
            if resolved:
                ref.update(resolved)
            refs.append(ref)
    row["native_evidence_refs"] = refs
    if row["status"] == "OBSERVED" and any(not ref["resolved"] for ref in refs):
        row["status"] = "UNRESOLVED"
        row["reasons"].append("native_reference_unresolved")
        row["missing_fields"].extend(f"{ref['kind']}:{ref['id']}" for ref in refs if not ref["resolved"])

'''
replace(marker, helper + marker)
replace('def _audit_a10(native_input, context):', 'def _audit_a10(native_input, context, measure_report):')
replace('''        status = "OBSERVED" if reasons == ["beat_baseline_indexed"] else "UNRESOLVED"
        findings.append(_finding(''', '''        measure_refs = []
        checks = {row.get("check_id"): (key, pos, row) for key in ("observation_checks", "relation_checks")
                  for pos, row in enumerate((measure_report or {}).get(key) or []) if isinstance(row, dict)}
        for check_id in _ids(fields.get("measure_check_ids") or statement.get("measure_check_ids")):
            if check_id not in checks:
                reasons.append("measure_reference_unresolved")
                missing.append("measure_check:%s" % check_id)
            else:
                key, pos, row = checks[check_id]
                measure_refs.append({"document": "measure_report", "pointer": f"/{key}/{pos}"})
                if row.get("status") != "PASS":
                    reasons.append("measure_evidence_unresolved")
        status = "OBSERVED" if reasons == ["beat_baseline_indexed"] else "UNRESOLVED"
        findings.append(_finding(''')
replace('''            pointers=[{"document": "context", "pointer": f"/statements/{i}"}],
            missing_fields=missing, source_text=statement.get("text"),
            detail="beat claim versus dated baseline, period, unit and comparison driver"))''', '''            pointers=[{"document": "context", "pointer": f"/statements/{i}"}] + measure_refs,
            missing_fields=missing, source_text=statement.get("text"),
            detail="beat claim versus dated baseline, period, unit and comparison driver"))''')
replace('        "A10": _audit_a10(native_input, context),', '        "A10": _audit_a10(native_input, context, measure_report),')
replace('''    declared = []
    findings = []
    for cid, (pos, cal)''', '''    declared = []
    findings = []
    known_claims = {c.get("claim_id") for c in native_input.get("evidence_claims") or [] if isinstance(c, dict)}
    for cid, (pos, cal)''')
replace('''        if not source_claim_ids:
            reasons.append("operating_range_unknown")
            missing.append("source_claim_ids")''', '''        if not source_claim_ids or any(cid not in known_claims for cid in source_claim_ids):
            reasons.append("operating_range_unknown")
            missing.append("source_claim_ids")''')
replace('''        if not source_claim_ids and derived != "observation":''', '''        if not source_claim_ids or any(cid not in known_claims for cid in source_claim_ids):''')
replace('''    zero_error = wape is not None and not observations''', '''    metric_evidence = any(r.get("record_schema_version") == "1.1"
                          and _finite(r.get("observations")) and r["observations"] > 0
                          and _finite(r.get("sum_absolute_actual")) and r["sum_absolute_actual"] > 0
                          for r in records)
    if wape is not None and observations and not metric_evidence:
        findings.append(_finding("A18", "UNRESOLVED", ["error_metric_without_actual_evidence"],
                                 missing_fields=["native historical actual evidence"],
                                 detail="a positive count alone cannot establish a measured error"))
    zero_error = wape is not None and not observations''')
replace('''                      "wape": wape if wape is not None and observations > 0 else None}''', '''                      "wape": wape if _finite(wape) and observations > 0 and metric_evidence else None}''')
replace('''    findings, checkpoints, remaining_review = [], [], []''', '''    findings, checkpoints, remaining_review = [], [], []
    reference_index = _reference_index(native_input)''')
replace('''        for n, row in enumerate(rows, 1):
            row["finding_id"]''', '''        for n, row in enumerate(rows, 1):
            _attach_references(row, reference_index)
            row["finding_id"]''')
target.write_text(code, encoding='utf-8', newline='\n')

# Fix synthetic builders' dangling default evidence, preserving every old assertion.
tests = ROOT / 'tests/test_w07_analyst_risk_audit.py'
test_code = tests.read_text(encoding='utf-8')
old = '''    return {
        "schema_version": "3.7", "company_name": "Test Co", "as_of_date": "2026-07-12",'''
assert test_code.count(old) == 1
test_code = test_code.replace(old, old.replace('return {', 'document = {'))
old_end = '''        "management_targets": management_targets or [],
    }


def make_forecast'''
new_end = '''        "management_targets": management_targets or [],
    }
    if claims is None:
        required = [cid for d in document["growth_driver_tree"]["drivers"]
                    for node in d.get("evidence_nodes") or [] for cid in node.get("claim_ids") or []]
        required.extend(cid for c in document["operating_research"]["calibrations"]
                        for cid in c.get("source_claim_ids") or [])
        known = {c["claim_id"] for c in document["evidence_claims"]}
        for cid in required:
            if cid not in known:
                document["evidence_claims"].append(claim(cid))
                known.add(cid)
    return document


def make_forecast'''
assert test_code.count(old_end) == 1
tests.write_text(test_code.replace(old_end, new_end), encoding='utf-8', newline='\n')
print('Reference resolution, scoped gaps and actual metric evidence repaired')
