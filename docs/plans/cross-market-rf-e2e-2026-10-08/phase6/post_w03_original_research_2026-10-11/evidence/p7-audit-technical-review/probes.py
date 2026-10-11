"""Six independent read-only-source pure/local CLI probes. No remote calls."""
from __future__ import annotations
import copy
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

OUTPUT_NORMAL = Path(__file__).resolve().parent
OUT = Path("\\\\?\\" + str(OUTPUT_NORMAL))
SOURCE = Path(r"C:\Users\郑曾波\Projects\_harness_worktrees\p7\audit")
SCRIPTS = SOURCE / "skills" / "revenue-forecast-audit" / "scripts"
NATIVE_BUDGET = Path(r"C:\Users\郑曾波\Projects\company-wiki\src\company_wiki\source_catalog\download_budget.py")
FAKE = SOURCE / "tests" / "fixtures" / "p7_audit" / "fake_native_child.py"
sys.path.insert(0, str(SCRIPTS))
import execution_request as er

spec = importlib.util.spec_from_file_location("technical_review_cwp_budget", NATIVE_BUDGET)
budget = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = budget
spec.loader.exec_module(budget)

SCOPE = {"profile": "P1", "resource_limits": {"max_request_bytes":4096,
         "max_response_bytes":100, "max_tokens":100, "max_cost_usd":"1.00"},
         "config_refs":[], "env_refs":[]}
DEPLOY = {"profile":"P1", "caps":dict(SCOPE["resource_limits"])}
TEMPLATE = {"request_id":"TECH-P7-001", "purpose":"local_record_boundary_probe",
            "profile":"P1", "limits":{"max_response_bytes":100,
            "max_tokens":100,"max_cost_usd":"1.00"},
            "command":[sys.executable,"-B",str(FAKE),"{request}"],
            "request":{"profile":"P2","max_response_bytes":1000,
            "max_tokens":1000,"max_cost_usd":"10.00"}}


def observed(thunk):
    try:
        value = thunk()
    except Exception as exc:
        return {"state":"rejected", "error_type":type(exc).__name__,"error":str(exc)}
    return {"state":"accepted", "value":value}


def native_budget(amount):
    value = budget.AcquisitionBudget.from_limits(max_response_bytes=100,
             max_seconds=2,max_cost_usd=amount)
    return {"max_cost_usd":str(value.max_cost_usd),
            "provider_started":value.provider_started, "cost_reported":value.cost_reported,
            "note":"constructor only; no provider execution or fee observation"}


rows=[]
zero_scope=copy.deepcopy(SCOPE)
zero_deploy=copy.deepcopy(DEPLOY)
zero_template=copy.deepcopy(TEMPLATE)
zero_scope["resource_limits"]["max_cost_usd"]="0.00"
zero_deploy["caps"]["max_cost_usd"]="0.00"
zero_template["limits"]["max_cost_usd"]="0.00"
zero_template["request"]={"note":"free local operation"}
rows.append({"probe_id":"P01","name":"explicit_zero_cost_compatibility",
             "audit":observed(lambda: str(er.build_execution_request(zero_scope,
                zero_deploy,zero_template,OUT / 'pure-zero.json',environ={})[1]["effective_scope"])),
             "native_cwp_constructor":observed(lambda:native_budget("0.00")),
             "native_acquisition_executed":False})
for probe_id, name, amount in [("P02","negative_cost_rejection","-0.01"),
                               ("P03","nan_cost_rejection","NaN")]:
    rows.append({"probe_id":probe_id,"name":name,
                 "audit":observed(lambda amount=amount:str(er.cap_value("max_cost_usd",amount))),
                 "native_cwp_constructor":observed(lambda amount=amount:native_budget(amount)),
                 "native_acquisition_executed":False})
body, record=er.build_execution_request(SCOPE,DEPLOY,TEMPLATE,OUT/'pure-discrepancy.json',environ={})
rows.append({"probe_id":"P04","name":"outer_body_discrepancy",
             "state":"accepted","request":json.loads(body),
             "effective_scope":record["effective_scope"],"diagnostics":record["diagnostics"],
             "request_sha256":record["request_sha256"],
             "actual_request_sha256":hashlib.sha256(body).hexdigest(),
             "native_acquisition_executed":False})

commands=[]
def local(argv):
    result=subprocess.run(list(map(str,argv)),cwd=OUT,capture_output=True,
                          text=True,encoding="utf-8",timeout=30,
                          env=dict(os.environ,PYTHONUTF8="1",PYTHONDONTWRITEBYTECODE="1"))
    commands.append({"argv":list(map(str,argv)),"exit_code":result.returncode,
                     "stdout":result.stdout,"stderr":result.stderr})
    if result.returncode:
        raise RuntimeError(f"local CLI exit {result.returncode}: {result.stderr}")
    return json.loads(result.stdout)


def chain(probe_id, mutate=False):
    root=OUT / "local-evidence-retry" / probe_id
    root.mkdir(parents=True,exist_ok=False)
    for name,document in [("scope",SCOPE),("deploy",DEPLOY),("template",TEMPLATE)]:
        (root/f"{name}.json").write_text(json.dumps(document),encoding="utf-8")
    init=local([sys.executable,"-X","utf8","-B",SCRIPTS/'audit_run.py',"init",
                "--root",root/'runs',"--company","Technical Reception Synthetic",
                "--as-of","2026-10-11","--run-id",probe_id.lower()])
    run=Path(init["run"])
    built=local([sys.executable,"-X","utf8","-B",SCRIPTS/'execution_request.py',
                 "build","--scope",root/'scope.json',"--deploy",root/'deploy.json',
                 "--template",root/'template.json',"--out-root",run/'execution'/'requests'])
    request_file=Path(built["request_file"])
    if mutate:
        changed=json.loads(request_file.read_bytes())
        changed["technical_review_mutation"]="changed after builder before capture"
        request_file.write_text(json.dumps(changed,sort_keys=True)+"\n",encoding="utf-8")
    index_args=[]
    for index in built["input_argv_positions"]:
        index_args.extend(["--freeze-arg-index",str(index)])
    captured=local([sys.executable,"-X","utf8","-B",SCRIPTS/'audit_run.py',
                   "capture","--run",run,"--role","executor","--freeze-input",request_file,
                   "--timeout-seconds","10",*index_args,"--",*built["argv"]])
    snapshot=captured["input_snapshots"][0]
    child=json.loads(Path(captured["stdout_artifact"]).read_text(encoding="utf-8"))
    frozen=Path(snapshot["frozen_path"]).read_bytes()
    return {"probe_id":probe_id,"name":"post_build_mutation_capture" if mutate
            else "unchanged_discrepant_body_capture", "synthetic_local_child":True,
            "native_acquisition_executed":False,"build_record":built,
            "capture_summary":captured,"child":child,
            "builder_sha256":built["request_sha256"],"snapshot_sha256":snapshot["sha256"],
            "actual_frozen_sha256":hashlib.sha256(frozen).hexdigest(),
            "child_sha256":child["consumed_request_sha256"],
            "three_party_sha_equal":built["request_sha256"]==snapshot["sha256"]==child["consumed_request_sha256"],
            "frozen_child_sha_equal":snapshot["sha256"]==child["consumed_request_sha256"],
            "child_body":json.loads(frozen),"builder_diagnostics":built["diagnostics"],
            "mutation_performed":mutate,"mutation_scope":"reviewer-owned generated request only" if mutate else None}

rows.append(chain("P05"))
rows.append(chain("P06",mutate=True))
report={"schema_version":"p7-audit-technical-probes/1", "observed_at":dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_worktree":str(SOURCE),"source_delivery_head":"18a52f16e605e2ca33bcf5dff5b7d4176077aa1c",
        "read_only_source":True,"source_sha256":{
        "execution_request.py":hashlib.sha256((SCRIPTS/'execution_request.py').read_bytes()).hexdigest(),
        "audit_run.py":hashlib.sha256((SCRIPTS/'audit_run.py').read_bytes()).hexdigest(),
        "native_cwp_budget":hashlib.sha256(NATIVE_BUDGET.read_bytes()).hexdigest()},
        "probe_count":len(rows),"probes":rows,"local_commands":commands,
        "get_calls":0,"provider_calls":0,"model_calls":0,"cost_usd":"0.00",
        "full_suite_rerun":False,"ci":"not_triggered","remote":"no_remote",
        "quality_claim":False}
(OUT/'probe-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
for row in rows:
    print(json.dumps({key:row[key] for key in ["probe_id","name","state","audit",
        "native_cwp_constructor","three_party_sha_equal","frozen_child_sha_equal"] if key in row},ensure_ascii=False))
print("RESULTS="+str(OUT/'probe-results.json'))