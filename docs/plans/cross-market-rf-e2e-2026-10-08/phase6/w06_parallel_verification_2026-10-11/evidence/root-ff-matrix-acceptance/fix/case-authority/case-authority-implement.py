"""Write only ROOT-authorized W06 tool/test source changes."""
from pathlib import Path
import json

FF=Path(r'C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root')
TOOLS=FF/'tools/offline_contract_matrix'
original=json.loads((FF/'tests/fixtures/w06_contract_matrix/authority/original-41-report.json').read_text(encoding='utf-8'))
metadata={c['id']:{k:c[k] for k in ('declared_layer','scope','expected')} for c in original['cases']}
source=r'''"""Fixed executable case authority shared by runner and oracle.

Reports are observations, never case definitions. JSON strings keep nested
definitions immutable; projections return fresh copies. No authorization or
identity database is introduced. Fixed company inputs are synthetic fixtures.
"""
from dataclasses import dataclass
import importlib
import json
from fixture_builder import CN, HK, US

AUTHORITY_VERSION = "w06-cases/1"

def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)

@dataclass(frozen=True)
class RunSpec:
    request_json: str
    fixture_json: str = "null"
    with_fmp_key: bool = True

    def request(self):
        return json.loads(self.request_json)

    def fixture(self):
        return json.loads(self.fixture_json)

@dataclass(frozen=True)
class CaseSpec:
    id: str
    handler: str
    arguments_json: str
    runs: tuple[RunSpec, ...]
    declared_layer: str
    scope: str
    expected_json: str

    def expected(self):
        return json.loads(self.expected_json)

    def metadata_errors(self, case):
        errors=[]
        for key,wanted in (("id",self.id),("declared_layer",self.declared_layer),("scope",self.scope),("expected",self.expected())):
            if case.get(key)!=wanted:
                errors.append(f"{key} differs from {AUTHORITY_VERSION}:{self.id}")
        return errors

    def request_errors(self, index, request):
        if index>=len(self.runs):
            return ["unexpected extra run"]
        wanted=self.runs[index].request()
        if request==wanted:
            return []
        return [f"request fields differ: {sorted(k for k in set(request)|set(wanted) if request.get(k)!=wanted.get(k) or (k in request)!=(k in wanted))}"]

    def fixture_errors(self,index,state,with_fmp_key):
        if index>=len(self.runs):
            return ["unexpected extra run"]
        run=self.runs[index];expected=run.fixture();errors=[]
        if with_fmp_key!=run.with_fmp_key:
            errors.append("credential presence differs from fixed vector")
        if expected is not None:
            for key,value in expected.items():
                if state.get(key)!=value:
                    errors.append(f"fixture {key} differs from fixed vector")
        return errors

    def execute(self,ctx):
        module,name=self.handler.split(":")
        args=json.loads(self.arguments_json)
        args=[{"CN":CN,"HK":HK,"US":US}[arg["identity"]] if isinstance(arg,dict) and set(arg)=={"identity"} else arg for arg in args]
        return getattr(importlib.import_module(module),name)(ctx,*args)

def _request(identity=US, *, kind="annual_report", year=2025, period="FY", intent="reuse_only", asof="2026-12-31", companion=None,limits=None):
    request={"schema_version":"2.0","company_query":identity.canonical_name,"market":identity.market,"document_kind":kind,"fiscal_year":year,"as_of_date":asof,"filing_intent":intent}
    if period is not None:request["fiscal_period"]=period
    if intent=="fetch_if_missing":request["acquisition_limits"]=limits or {"max_bytes":2000000,"timeout_seconds":25,"max_cost_usd":"0"}
    if companion is not None:request["companion_transcript"]=companion
    return request

def _companion(year,quarter,intent="fetch_if_missing",limits=None):
    row={"intent":intent,"fiscal_year":year,"provider":"fmp"}
    if quarter is not None:row["fiscal_quarter"]=quarter
    if intent=="fetch_if_missing":row["acquisition_limits"]=limits or {"max_bytes":1000000,"timeout_seconds":25,"max_cost_usd":"0"}
    return row

def _fixture(scenario="success",provider="serve",**values):
    return {"scenario":scenario,"provider_scenario":provider,"call_date":"2025-12-01","response_bytes":512,"content_utf8":"",**values}

def _run(request,fixture=None,key=True):
    return RunSpec(_json(request),_json(fixture),key)

def _spec(cid,handler,args,runs):
    meta=_METADATA[cid]
    return CaseSpec(cid,handler,_json(args),tuple(runs),meta["declared_layer"],meta["scope"],_json(meta["expected"]))

def _build():
    rows=[_spec("chainA_download_reuse","matrix_cases:case_chain_a",[],[
        _run(_request(companion=_companion(2025,1)),_fixture(content_utf8="Synthetic original-language AAPL FY2025 Q1 earnings call transcript.")),
        _run(_request(companion=_companion(2025,1)),_fixture())])]
    kinds=(("annual_report","annual","FY"),("semi_annual_report","semi","S1"),("quarterly_report","quarterly","Q1"))
    for identity in (CN,HK,US):
        for kind,short,period in kinds:
            cid=f"fin_{identity.market.lower()}_{short}_hit"
            rows.append(_spec(cid,"matrix_cases:case_fin_local_hit",[{"identity":identity.market},kind,2024,period,cid],[_run(_request(identity,kind=kind,year=2024,period=period))]))
    for identity in (CN,HK,US):
        for kind,short,period in kinds:
            cid=f"fin_{identity.market.lower()}_{short}_fetch"
            request=_request(identity,kind=kind,year=2026,period=period,intent="fetch_if_missing")
            rows.append(_spec(cid,"matrix_cases:case_fin_fetch",[{"identity":identity.market},kind,2026,cid,period],[_run(request,_fixture()),_run(request,_fixture())]))
    for cid,identity,kind in (("nonperiod_prospectus",US,"prospectus"),("nonperiod_equity_offering",US,"equity_offering_prospectus"),("nonperiod_convertible_bond",US,"convertible_bond_prospectus"),("nonperiod_investor_relations",HK,"investor_relations")):
        rows.append(_spec(cid,"matrix_cases:case_nonperiod",[{"identity":identity.market},kind,cid],[_run(_request(identity,kind=kind,period=None,intent="fetch_if_missing"),_fixture())]))
    rows.extend([
        _spec("call_fy_only_no_q","matrix_cases:case_call_fy_only",[],[_run(_request(companion=_companion(2025,None)))]),
        _spec("call_past_cutoff","matrix_cases:case_call_past_cutoff",[],[_run(_request(companion=_companion(2025,2)),_fixture(call_date="2027-06-01",content_utf8="Synthetic transcript dated after cutoff."))]),
        _spec("call_wrong_quarter","matrix_cases:case_call_wrong_quarter",[],[_run(_request(companion=_companion(2025,3)),_fixture("wrong_quarter",content_utf8="Synthetic transcript with mismatched quarter."))]),
        _spec("err_request_error","matrix_cases:case_err_request",[],[_run({"schema_version":"2.0","company_query":"Apple Inc.","market":"US","document_kind":"annual_report","as_of_date":"2026-01-01","filing_intent":"reuse_only"})]),
        _spec("err_402_entitlement","matrix_cases:case_err_402",[],[_run(_request(companion=_companion(2025,4)),_fixture("entitlement_402"))]),
        _spec("err_missing_creds","matrix_cases:case_err_missing_creds",[],[_run(_request(companion=_companion(2026,1)),key=False)]),
        _spec("err_unknown_usage","matrix_cases:case_err_unknown_usage",[],[_run(_request(companion=_companion(2026,2)),_fixture("worker_loss"))]),
        _spec("local_txt_exact_reuse","extended_cases:case_local_txt",[],[_run(_request(companion=_companion(2024,2,"reuse_only")),_fixture("worker_loss"))]),
        _spec("reuse_only_missing_period","extended_cases:case_reuse_only_gap",[],[_run(_request(CN,year=2030),_fixture("worker_loss"))]),
    ])
    for cid,scenario,reasons,quarter,max_bytes,seconds in (("call_wrong_symbol","wrong_symbol",["provider_identity_or_host"],1,1000000,5),("call_wrong_mime","wrong_mime",["provider_identity_or_host"],2,1000000,5),("call_max_bytes","oversize",["byte_limit"],3,256,5),("call_hard_timeout","stall",["provider_deadline"],4,1000000,1)):
        # Dedicated runner reads its arguments from this same definition.
        rows.append(_spec(cid,"case_specs:_negative_transcript",[scenario,cid,reasons,2028,quarter,max_bytes,seconds],[_run(_request(companion=_companion(2028,quarter,limits={"max_bytes":max_bytes,"timeout_seconds":seconds,"max_cost_usd":"0"})),_fixture(scenario,response_bytes=2000 if scenario=="oversize" else 512))]))
    rows.append(_spec("request_after_failure_retry","extended_cases:case_failure_then_retry",[],[
        _run(_request(companion=_companion(2029,1,limits={"max_bytes":1000000,"timeout_seconds":5,"max_cost_usd":"0"})),_fixture("request_failure")),
        _run(_request(companion=_companion(2029,1)),_fixture(content_utf8="Synthetic retry original content."))]))
    for cid,scenario in (("original_wrong_sha","bad_sha"),("original_wrong_mime","bad_mime"),("original_max_bytes","oversize")):
        rows.append(_spec(cid,"extended_cases:filing_negative",[scenario,cid],[_run(_request(CN,kind="prospectus",year=2031,period=None,intent="fetch_if_missing",limits={"max_bytes":50 if scenario=="oversize" else 2000000,"timeout_seconds":5,"max_cost_usd":"0"}),_fixture(provider=scenario))]))
    rows.append(_spec("incomplete_sidecar_metadata_gap","extended_cases:case_unverified_sidecar",[],[_run(_request(CN,year=2032,asof="2033-12-31"))]))
    return tuple(rows)

def _negative_transcript(ctx,scenario,cid,reasons,year,quarter,max_bytes,seconds):
    from extended_cases import transcript_negative
    return transcript_negative(ctx,scenario,cid,set(reasons),year=year,quarter=quarter,max_bytes=max_bytes,seconds=seconds)

def case_specs():
    return _SPECS

def get_spec(cid):
    return next((spec for spec in _SPECS if spec.id==cid),None)

def audit_coverage(cases):
    wanted={s.id for s in _SPECS};observed=[c.get("id") for c in cases]
    missing=wanted-set(observed);extra=set(observed)-wanted
    duplicate={cid for cid in observed if observed.count(cid)>1}
    return [f"missing={sorted(missing)}, unknown={sorted(str(x) for x in extra)}, duplicate={sorted(str(x) for x in duplicate)}"] if missing or extra or duplicate else []

'''
source+='\n# Reviewed fixed input/expected definitions; not loaded from a runtime report.\n_METADATA='+repr(metadata)+'\n_SPECS=_build()\n'
(TOOLS/'case_specs.py').write_text(source,encoding='utf-8')

p=TOOLS/'cli_main.py';text=p.read_text(encoding='utf-8')
start=text.index('def _case_registry()');end=text.index('\n\ndef _fresh_proofs',start)
text=text[:start]+'''def _case_registry() -> list[tuple[str, Callable[[Context], CaseResult]]]:
    from case_specs import case_specs
    return [(spec.id, spec.execute) for spec in case_specs()]
'''+text[end:]
text=text.replace('from matrix_cases import (  # noqa: E402\n    case_chain_a, case_fin_local_hit, case_fin_fetch, case_nonperiod,\n    case_call_fy_only, case_call_past_cutoff, case_call_wrong_quarter,\n    case_err_request, case_err_402, case_err_missing_creds, case_err_unknown_usage, seed_all,\n)','from matrix_cases import seed_all  # noqa: E402')
text=text.replace('from fixture_builder import CN, US, HK  # noqa: E402\n','')
text=text.replace('                ctx.begin_case()\n                result = runner(ctx)','                ctx.begin_case()\n                from case_specs import get_spec\n                ctx.active_case_spec = get_spec(cid)\n                result = runner(ctx)\n                errors = ctx.active_case_spec.metadata_errors(result.to_dict())\n                if errors:\n                    raise ValueError("case runner contract drift: " + "; ".join(errors))')
# Handler failure keeps the authoritative metadata; observation remains FAIL/PARTIAL.
text=text.replace('            elapsed = time.monotonic() - case_start','            from case_specs import get_spec\n            spec = get_spec(cid)\n            result.declared_layer, result.scope, result.expected = spec.declared_layer, spec.scope, spec.expected()\n            elapsed = time.monotonic() - case_start')
text=text.replace('            results.append(CaseResult(id=cid, title=cid, declared_layer="unknown", result="NOT_RUN", diagnostics=[error or "batch deadline exhausted"]))','            from case_specs import get_spec\n            spec = get_spec(cid)\n            results.append(CaseResult(id=cid, title=cid, declared_layer=spec.declared_layer, scope=spec.scope, expected=spec.expected(), result="NOT_RUN", diagnostics=[error or "batch deadline exhausted"]))')
p.write_text(text,encoding='utf-8')

p=TOOLS/'run.py';text=p.read_text(encoding='utf-8')
needle='        et_before = self.fixture_requests(calls) if calls else 0'
addition='''        from case_specs import get_spec
        spec = getattr(self, "active_case_spec", None) or get_spec(case_id)
        index = len(self.traces.get(case_id, []))
        if spec is None:
            raise ValueError("unknown case id")
        errors = spec.request_errors(index, request) + spec.fixture_errors(index, state, with_fmp_key)
        if errors:
            raise ValueError("case input contract drift: " + "; ".join(errors))
        # Execute the fixed projection after equality was checked, never silently
        # substitute a different vector to conceal handler drift.
        request = spec.runs[index].request()
        fixture_path = self.artifacts / f"{case_id}.{run_label}.fixture.json"
        fixture_path.write_text(json.dumps({"state":state,"with_fmp_key":with_fmp_key}, ensure_ascii=False, indent=2), encoding="utf-8")
'''
text=text.replace(needle,addition+needle)
text=text.replace('            "fixture_scenario": state.get("scenario"),','            "fixture_scenario": state.get("scenario"),\n            "fixture_ref": fixture_path.name,\n            "fixture_sha256": sha256_file(fixture_path),')
p.write_text(text,encoding='utf-8')

# Remove the second duplicate executable registry; callers consume CaseSpec.
p=TOOLS/'extended_cases.py';text=p.read_text(encoding='utf-8');start=text.index('\ndef additional_cases():')
text=text[:start]+'\n'
p.write_text(text,encoding='utf-8')
print('Shared CaseSpec and runner input authority written')
