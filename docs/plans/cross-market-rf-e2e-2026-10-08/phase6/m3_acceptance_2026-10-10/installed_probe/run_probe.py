"""Independent, offline acceptance of the installed M3 runtime.

The coordinator process authors synthetic JSON fixtures using repository test
helpers. Every product execution is a fresh isolated Python process importing
only the explicitly selected installation. No source test/conftest is imported
by any child. Originals, production configs, and installations are read-only.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


REPORT_ROOT = Path(__file__).resolve().parent
RF_SOURCE = Path.home() / "Projects" / "revenue-forecast"
INSTALL_BASES = (Path.home() / ".agents" / "skills", Path.home() / ".codex" / "skills")

RF_MODULES = ("revenue_core", "revenue_report", "contracts.annual_consumption",
              "contracts.period_flow", "contracts.document", "contracts.constants",
              "schema_compatibility", "research.drivers", "filing_upstream_cause")

CLI_CHILD = r'''
import json, pathlib, runpy, sys
scripts = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(scripts))
sys.argv = sys.argv[2:]
try:
    runpy.run_path(sys.argv[0], run_name="__main__")
finally:
    origins = {name: str(pathlib.Path(sys.modules[name].__file__).resolve())
               for name in ("revenue_core", "revenue_report", "contracts.annual_consumption",
                            "contracts.period_flow", "contracts.document", "contracts.constants",
                            "schema_compatibility", "research.drivers") if name in sys.modules}
    assert len(origins) == 8, origins
    assert all(pathlib.Path(p).is_relative_to(scripts) for p in origins.values()), origins
    print("INSTALL_ORIGINS=" + json.dumps(origins, ensure_ascii=False), file=sys.stderr)
'''

COMPUTE_CHILD = r'''
import copy, json, pathlib, sys
scripts = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(scripts))
from revenue_core import run_forecast
from revenue_report import render_markdown, validate_published_forecast
from filing_upstream_cause import failure_observation
data = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
cli_result = json.loads(pathlib.Path(sys.argv[3]).read_text(encoding="utf-8"))
result = run_forecast(copy.deepcopy(data))
validate_published_forecast(result, data)
validate_published_forecast(cli_result, data)
markdown = render_markdown(result)
assert result["schema_version"] == "3.9"
assert result["engine_version"] == "4.2.0"
assert result["consolidated_forecast"] == cli_result["consolidated_forecast"]
assert result["consolidated_forecast"]["base"]["annual_revenue"]["2026"] == 165.00000000000003
assert "period_flow" in markdown
assert "2026-01-01" in markdown and "2026-12-31" in markdown
if sys.argv[4] == "derived":
    params = {p["parameter_id"]: p for p in result["parameter_trace"]}
    assert params["source_h1"]["value"] == 60
    assert params["source_h2"]["value"] == 50
    assert abs(params["0_base_2026"]["value"] - 110) < 1e-9
ff = json.loads(pathlib.Path(sys.argv[5]).read_text(encoding="utf-8"))
for payload in ff["errors"]:
    observed = failure_observation(payload)
    assert observed["acquisition_observation"] == payload["acquisition_observation"]
    assert observed["acquisition_failure"] == payload["filing"]["acquisition_failure"]
names = ("revenue_core", "revenue_report", "contracts.annual_consumption",
         "contracts.period_flow", "contracts.document", "contracts.constants",
         "schema_compatibility", "research.drivers", "filing_upstream_cause")
origins = {name: str(pathlib.Path(sys.modules[name].__file__).resolve()) for name in names}
assert all(pathlib.Path(p).is_relative_to(scripts) for p in origins.values()), origins
print(json.dumps({"schema_version": result["schema_version"], "engine_version": result["engine_version"],
                  "compute_strong_render": "pass", "ff_unknown_and_lower_bound_preserved": True,
                  "module_origins": origins}, ensure_ascii=False))
'''

FF_CHILD = r'''
import copy, json, pathlib, sys
scripts = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(scripts))
import fetch_filing
from ff_provider_cause import build_cause, validated_acquisition_observation
from ff_v2_envelope import success_envelope, error_envelope
obs = {"schema_version":"acquisition-observation/1", "usage_scope":"operation", "outcome":"failed",
       "provider_started":True, "usage_complete":False, "wire_body_bytes":101,
       "wire_usage_complete":False, "entity_body_bytes":202, "http_exchanges":2,
       "http_exchanges_complete":False, "cost_usd":None, "http_observation":None}
failure = {"schema_version":"acquisition-failure/1", "code":"network_failed", "retryable":False,
           "provider_started":True, "usage_complete":False, "usage_scope":"operation",
           "acquisition_usage":{"schema_version":"1.0", "response_bytes":202, "cost_usd":"0"}}
cause = build_cause("ensure", "network_failed", provider_started=True, usage_complete=False)
errors=[]
for cost in (None, "0.01"):
    observation=copy.deepcopy(obs); observation["cost_usd"]=cost
    error=error_envelope("upstream_error", "network_failed", retryable=False,
        stats={"calls":2,"downloads":0}, upstream_cause=cause,
        acquisition_failure=failure, acquisition_observation=observation, stage="ensure", attempts=1)
    assert error["schema_version"] == "2.0"
    assert error["status"] == error["filing"]["status"] == "upstream_error"
    assert error["acquisition_observation"] == observation
    assert "acquisition_observation" not in error["filing"]
    assert error["filing"]["acquisition_failure"] == failure
    assert error["filing"]["upstream_cause"] == cause
    errors.append(error)
for key, value in (("outcome", []), ("http_exchanges", None), ("cost_usd", "NaN")):
    malformed=copy.deepcopy(obs); malformed[key]=value
    assert validated_acquisition_observation(malformed) is None
    error=error_envelope("upstream_error", "network_failed", retryable=False,
        upstream_cause=cause, acquisition_failure=failure, acquisition_observation=malformed)
    assert error["status"] == "upstream_error" and "acquisition_observation" not in error
    assert error["filing"]["upstream_cause"] == cause
    assert error["filing"]["acquisition_failure"] == failure
sha="a"*64
ref={"schema_version":"2.0", "document_id":"urn:company-wiki:document:sha256:"+sha,
     "source_id":"urn:company-wiki:source:sha256:"+sha, "content_sha256":sha,
     "byte_size":3,"mime_type":"application/pdf"}
success_obs=copy.deepcopy(obs);success_obs.update(outcome="reused_before_download",provider_started=False,
    usage_complete=True,wire_body_bytes=0,entity_body_bytes=0,http_exchanges=0,
    wire_usage_complete=True,http_exchanges_complete=True,cost_usd=None)
success=success_envelope({}, {"source_ref":ref,"document_kind":"annual_report","fiscal_year":2025,
    "fiscal_period":"FY","resolution_outcome":"reused_before_download","download_events":0,
    "acquisition_observation":success_obs}, {"status":"not_applicable"}, {"calls":1,"downloads":0})
assert success["schema_version"] == "2.0"
assert success["acquisition_observation"] == success_obs
assert "acquisition_observation" not in success["filing"]
origins={name:str(pathlib.Path(sys.modules[name].__file__).resolve())
         for name in ("fetch_filing","ff_provider_cause","ff_v2_envelope","filing_contracts")}
assert all(pathlib.Path(p).is_relative_to(scripts) for p in origins.values()), origins
print(json.dumps({"errors":errors, "success":success,
                  "malformed_diagnostic_does_not_mask_error":True,"module_origins":origins},ensure_ascii=False))
'''


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def installed_manifest() -> dict[str, str]:
    result={}
    for base in INSTALL_BASES:
        for skill in ("filing-fetch", "revenue-forecast"):
            root=base/skill
            for path in root.rglob("*"):
                if path.is_file():
                    result[str(path)]=sha(path.read_bytes())
    return result


def fixture_documents() -> dict[str, dict]:
    # This parent-side fixture authoring never gets passed as a child PYTHONPATH.
    sys.path[:0]=[str(RF_SOURCE/"tests"),str(RF_SOURCE/"scripts")]
    from test_recognition_bridge import forecast_document
    from test_m3_period_flow_contract import add_flow_parameter
    base=forecast_document()
    base["schema_version"]="3.9"
    documents={}
    for parameter_id in ("0_base_2026","segment_a_base","reported_total"):
        data=copy.deepcopy(base)
        parameter=next(p for p in data["parameters"] if p["parameter_id"]==parameter_id)
        year=int(parameter["period"][2:])
        parameter.update(time_basis="period_flow",period_start=f"{year}-01-01",period_end=f"{year}-06-30")
        documents["half_"+parameter_id]=data
    full=copy.deepcopy(base)
    for parameter_id in ("0_base_2026","segment_a_base","reported_total"):
        parameter=next(p for p in full["parameters"] if p["parameter_id"]==parameter_id)
        year=int(parameter["period"][2:])
        parameter.update(time_basis="period_flow",period_start=f"{year}-01-01",period_end=f"{year}-12-31")
    documents["full"]=full
    derived=copy.deepcopy(base)
    add_flow_parameter(derived,"source_h1",60,"2026-01-01","2026-06-30",2026)
    add_flow_parameter(derived,"source_h2",50,"2026-07-01","2026-12-31",2026)
    parameter=next(p for p in derived["parameters"] if p["parameter_id"]=="0_base_2026")
    parameter.update(kind="derived_fact",formula="x0+x1",input_parameter_ids=["source_h1","source_h2"],
        time_basis="period_flow",period_start="2026-01-01",period_end="2026-12-31")
    documents["derived"]=derived
    return documents


def main() -> int:
    REPORT_ROOT.mkdir(parents=True,exist_ok=True)
    documents=fixture_documents()
    before=installed_manifest()
    evidence={"schema_version":"m3-installed-independent-probe/1",
        "started_at_utc":datetime.now(timezone.utc).isoformat(),"tests":[],
        "fixture_authoring":"repository test helpers only in parent; JSON-only children",
        "external_provider_calls":0,"external_model_calls":0,"paid_tokens":0,"paid_micro_usd":0,
        "originals_read_or_modified":False,"production_config_modified":False}
    temp_parent=Path.home()/"AppData"/"Local"/"Temp"
    with tempfile.TemporaryDirectory(prefix="m3ip-",dir=temp_parent) as directory:
        temp=Path(directory).resolve()
        assert temp.is_relative_to(temp_parent.resolve()) and temp.name.startswith("m3ip-")
        env={k:v for k,v in os.environ.items() if not k.startswith("PYTHON") and not k.startswith("GIT_")}
        env["PYTHONUTF8"]="1"
        for base in INSTALL_BASES:
            lane=base.parent.name.lstrip(".")
            owned=temp/lane
            owned.mkdir()
            env["REVENUE_PUBLICATION_REGISTRY"]=str(owned/"registry")
            rf_scripts=base/"revenue-forecast"/"scripts"
            ff_scripts=base/"filing-fetch"/"scripts"

            def run(name: str, code: str, args: list[str], expected: int=0) -> subprocess.CompletedProcess:
                argv=[sys.executable,"-I","-B","-X","utf8","-c",code,*args]
                started=datetime.now(timezone.utc).isoformat()
                result=subprocess.run(argv,cwd=owned,env=env,capture_output=True,timeout=90)
                log_name=lane+"-"+name
                for stream,data in (("stdout",result.stdout),("stderr",result.stderr)):
                    (REPORT_ROOT/(log_name+"."+stream+".log")).write_bytes(data)
                evidence["tests"].append({"name":log_name,"argv":argv,"cwd":str(owned),
                    "started_at_utc":started,"exit_code":result.returncode,"expected_exit_code":expected,
                    "stdout_log":log_name+".stdout.log","stdout_sha256":sha(result.stdout),
                    "stderr_log":log_name+".stderr.log","stderr_sha256":sha(result.stderr)})
                assert result.returncode==expected,(log_name,result.returncode,result.stderr.decode("utf-8",errors="replace"))
                return result

            ff=run("ff-siblings",FF_CHILD,[str(ff_scripts)])
            ff_path=owned/"ff.json"
            ff_path.write_bytes(ff.stdout)
            run("rf-version",CLI_CHILD,[str(rf_scripts),str(rf_scripts/"revenue_forecast.py"),"--version"])
            for name,data in documents.items():
                input_path=owned/(name+".json")
                encoded=json.dumps(data,ensure_ascii=False).encode("utf-8")
                input_path.write_bytes(encoded)
                evidence.setdefault("fixture_sha256",{})[name]=sha(encoded)
                if name.startswith("half_"):
                    result=run(name,CLI_CHILD,[str(rf_scripts),str(rf_scripts/"revenue_forecast.py"),
                        str(input_path),"--validate-only"],expected=2)
                    assert b"requires annual flow coverage" in result.stderr
                else:
                    output_path=owned/(name+"-output.json")
                    md_path=owned/(name+".md")
                    run(name+"-cli",CLI_CHILD,[str(rf_scripts),str(rf_scripts/"revenue_forecast.py"),
                        str(input_path),"--output",str(output_path),"--markdown",str(md_path)])
                    assert output_path.is_file() and md_path.is_file()
                    run(name+"-compute-strong-render",COMPUTE_CHILD,[str(rf_scripts),str(input_path),
                        str(output_path),name,str(ff_path)])
        evidence["test_owned_files_before_cleanup"]=sum(p.is_file() for p in temp.rglob("*"))
    evidence["owned_temp_removed"]=not temp.exists()
    after=installed_manifest()
    evidence["installation_files_before"]=len(before)
    evidence["installation_files_after"]=len(after)
    evidence["installation_mutations"]=sorted(k for k in set(before)|set(after) if before.get(k)!=after.get(k))
    assert evidence["owned_temp_removed"] and not evidence["installation_mutations"]
    evidence["finished_at_utc"]=datetime.now(timezone.utc).isoformat()
    evidence["status"]="pass"
    (REPORT_ROOT/"verification.json").write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":evidence["status"],"tests":len(evidence["tests"]),
        "installation_mutations":evidence["installation_mutations"],"owned_temp_removed":evidence["owned_temp_removed"],
        "report":str(REPORT_ROOT/"verification.json")},ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
