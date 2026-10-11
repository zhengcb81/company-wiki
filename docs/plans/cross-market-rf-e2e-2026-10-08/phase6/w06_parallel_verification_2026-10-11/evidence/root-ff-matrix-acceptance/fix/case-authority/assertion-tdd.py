from pathlib import Path
FF=Path(r'C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root')
p=FF/'tests/test_w06_case_authority.py'
text=p.read_text(encoding='utf-8')
text+='''
@pytest.mark.parametrize("cid",[c["id"] for c in frozen_report()["cases"] if c["result"]=="FAIL"])
def test_authority_failed_response_cannot_be_laundered_as_pass(cid):
    report=frozen_report();c=case(report,cid);c["result"]="PASS"
    assert any(f.vector=="case_assertion_failed" and f.case_id==cid for f in oracle.audit(report))

def test_authority_fixed_fixture_scenario_cannot_be_self_declared():
    from case_specs import get_spec
    spec=get_spec("call_past_cutoff")
    state=spec.runs[0].fixture();state["call_date"]="2025-06-01"
    assert spec.fixture_errors(0,state,True)
    state=spec.runs[0].fixture();state["scenario"]="wrong_quarter"
    assert spec.fixture_errors(0,state,True)
    assert spec.fixture_errors(0,spec.runs[0].fixture(),False)
    missing=get_spec("err_missing_creds")
    assert missing.fixture_errors(0,{},True)
'''
p.write_text(text,encoding='utf-8')
