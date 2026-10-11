from pathlib import Path
import shutil
import json
import hashlib

FF=Path(r'C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root')
EVIDENCE=Path(__file__).resolve().parent/'case-authority'
REVIEW=Path(__file__).resolve().parent.parent/'independent-final'
EVIDENCE.mkdir(exist_ok=True)
fixture=FF/'tests/fixtures/w06_contract_matrix/authority'
fixture.mkdir(parents=True,exist_ok=True)
original=REVIEW/'original-41-report-copy.json'
shutil.copyfile(original,fixture/'original-41-report.json')
report=json.loads(original.read_text(encoding='utf-8'))
artifacts=fixture/'artifacts'; artifacts.mkdir(exist_ok=True)
# Only synthetic sealed request/response/ET receipts, not originals or keys.
for p in Path(report['evidence_root']).iterdir():
 if p.is_file(): shutil.copyfile(p,artifacts/p.name)
inputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in REVIEW.iterdir() if p.name in ['original-41-report-copy.json','omitted-required-22-cases-counterexample.json','removed-cutoff-expectation-report-copy.json','modified-request-vector.json']}
(EVIDENCE/'exact-inputs.json').write_text(json.dumps(inputs,indent=2),encoding='utf-8')
tests=r'''"""Case-authority TDD. Pure tool proofs, never product execution or supplier claims."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import pytest

TOOLS=Path(__file__).resolve().parents[1]/"tools/offline_contract_matrix"
sys.path.insert(0,str(TOOLS))
import oracle

FIXTURE=Path(__file__).parent/"fixtures/w06_contract_matrix/authority"

def frozen_report():
    report=json.loads((FIXTURE/"original-41-report.json").read_text(encoding="utf-8"))
    report["evidence_root"]=str(FIXTURE/"artifacts")
    return report

def case(report,cid):
    return next(c for c in report["cases"] if c["id"]==cid)

def test_authority_omitted_required_cases_cannot_be_declared_away():
    report=frozen_report()
    report["cases"]=[c for c in report["cases"] if c["result"]=="PASS"]
    report["required_cases"]=[c["id"] for c in report["cases"]]
    assert any(f.vector=="coverage_gap" for f in oracle.audit(report))

def test_authority_removed_cutoff_expectation_cannot_remove_check():
    report=frozen_report()
    case(report,"call_past_cutoff")["expected"]={}
    findings=oracle.audit(report)
    assert any(f.vector=="wrong_cutoff" and f.case_id=="call_past_cutoff" for f in findings)

def test_authority_hashed_wrong_market_request_is_still_wrong(tmp_path):
    report=frozen_report()
    shutil.copytree(FIXTURE/"artifacts",tmp_path/"artifacts")
    report["evidence_root"]=str(tmp_path/"artifacts")
    run=case(report,"fin_cn_annual_hit")["actual"]["runs"][0]
    path=tmp_path/"artifacts"/run["request_ref"]
    request=json.loads(path.read_text(encoding="utf-8"))
    request.update(company_query="Tencent Holdings Limited",market="HK")
    raw=json.dumps(request,ensure_ascii=False).encode("utf-8")
    path.write_bytes(raw);run["request_sha256"]=hashlib.sha256(raw).hexdigest()
    assert any(f.vector=="case_request_mismatch" and f.case_id=="fin_cn_annual_hit" for f in oracle.audit(report))

@pytest.mark.parametrize("index",range(41))
def test_authority_every_required_case_is_mandatory_even_if_list_changes(index):
    from case_specs import audit_coverage
    report=frozen_report();removed=report["cases"].pop(index)
    report["required_cases"]= [c["id"] for c in report["cases"]]
    issues=audit_coverage(report["cases"])
    assert issues and any(removed["id"] in detail for detail in issues)

@pytest.mark.parametrize("index",range(41))
def test_authority_duplicate_or_extra_cannot_replace_required_case(index):
    from case_specs import audit_coverage
    rows=frozen_report()["cases"]; removed=rows.pop(index)
    rows.append(deepcopy(rows[0]))
    assert audit_coverage(rows)
    rows[-1]["id"]="extra-case-"+removed["id"]
    assert audit_coverage(rows)

def test_authority_valid_full_registry_and_single_case_contract_positive():
    from case_specs import audit_coverage,get_spec
    report=frozen_report()
    assert audit_coverage(report["cases"])==[]
    c=case(report,"fin_cn_annual_hit")
    assert get_spec(c["id"]).metadata_errors(c)==[]
    run=c["actual"]["runs"][0]
    request=json.loads((FIXTURE/"artifacts"/run["request_ref"]).read_text(encoding="utf-8"))
    assert get_spec(c["id"]).request_errors(0,request)==[]

@pytest.mark.parametrize("field,value",[("company_query","wrong"),("market","HK"),("document_kind","quarterly_report"),("fiscal_year",2025),("fiscal_period","Q1"),("as_of_date","2025-01-01"),("filing_intent","fetch_if_missing"),("mode","latest_as_of")])
def test_authority_request_contract_covers_all_source_dimensions(field,value):
    from case_specs import get_spec
    spec=get_spec("fin_cn_annual_hit");request=spec.runs[0].request()
    request[field]=value
    assert spec.request_errors(0,request)

def test_authority_companion_limits_and_execution_scope_are_fixed():
    from case_specs import get_spec
    spec=get_spec("call_max_bytes");request=spec.runs[0].request()
    request["companion_transcript"]["fiscal_quarter"]=2
    assert spec.request_errors(0,request)
    request=spec.runs[0].request();request["companion_transcript"]["acquisition_limits"]["max_bytes"]=1000000
    assert spec.request_errors(0,request)
    c=case(frozen_report(),spec.id);c["declared_layer"]="ff-only"
    assert spec.metadata_errors(c)
    # Registry is immutable even if callers mutate a returned projection.
    request=spec.runs[0].request();request["market"]="HK"
    assert spec.runs[0].request()["market"]=="US"
'''
(FF/'tests/test_w06_case_authority.py').write_text(tests,encoding='utf-8')
print('Frozen exact counterexamples and focused formal tests')
