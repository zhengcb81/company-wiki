"""Independent CWP G1 probes. Writes only this report directory and owned TEMP."""
from pathlib import Path
from copy import deepcopy
from dataclasses import replace
from collections import Counter
from tempfile import TemporaryDirectory
import hashlib, json, os, shutil, subprocess, sys, types
import yaml
REPO=Path(r"C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/company-wiki")
OUT=Path(__file__).resolve().parent
PLAN=REPO/"docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w04_post_pw03_common_roots_2026-10-11"
sys.path[:0]=[str(REPO/"src"),str(REPO/"tests")]
sys.dont_write_bytecode=True
network_attempts=[]
def block_network(event,args):
    if event in {"socket.connect","socket.getaddrinfo","http.client.connect"}:
        network_attempts.append(event)
        raise RuntimeError("G1 zero network boundary")
sys.addaudithook(block_network)
def sha(b): return hashlib.sha256(b).hexdigest()
def encoded(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
checks=[]
def check(name,value,details=None):
    if not value: raise AssertionError(name)
    checks.append({"name":name,"status":"PASS","details":details})
    print(name+": PASS",flush=True)
handoff_path=PLAN/"evidence/implementation/wp01/handoff.json"
handoff=json.loads(handoff_path.read_bytes())
check("sealed_handoff_sha",sha(handoff_path.read_bytes())=="e5c71592eec4bcbee9cc26a08cc89e0483536a13133f9161ab3f09e650acaa66")
source_hashes={}
for row in handoff["product_files"]:
    path=REPO/row["path"]
    source_hashes[row["path"]]=sha(path.read_bytes())
    check("owner_source_sha:"+row["path"],source_hashes[row["path"]]==row["working_sha256"])
for name in ["src/company_wiki/automation/narrative_generation.py","tests/unit/test_w04_generation_identity.py","src/company_wiki/automation/narrative_contracts.py","src/company_wiki/automation/narrative_http_model.py","src/company_wiki/source_catalog/official_json_projection.py","src/company_wiki/automation/narrative_official_json.py"]:
    source_hashes[name]=sha((REPO/name).read_bytes())
check("frozen_overlay_sha",sha((PLAN/"ROOT_EXECUTION_OVERLAY.md").read_bytes())==handoff["overlay_sha256"])
for name,row in handoff["evidence_artifacts"].items():
    check("owner_evidence_sha:"+name,sha((handoff_path.parent/name).read_bytes())==row["sha256"])
root_green=json.loads((PLAN/"evidence/implementation/wp07/generation-green.json").read_bytes())
check("root_98_log_sha",sha((PLAN/"evidence/implementation/wp07/generation-green.log").read_bytes())==root_green["log_sha256"])
fixture=handoff["producer_fixture"]
protected=[Path(x["original"]) for x in fixture["originals"]]+[Path(fixture["config"]),Path(fixture["us_config"])]
before={str(x):sha(x.read_bytes()) for x in protected}
from company_wiki.automation.models import canonical_json
from company_wiki.automation.narrative_transport_contracts import NarrativeReadRequest
from company_wiki.automation.narrative_transport import NarrativeTransportReader
from company_wiki.automation.narrative_evidence_view import NarrativeEvidenceViewReader,NarrativeEvidenceViewQuery
from company_wiki.automation.narrative_official_json import open_verified_projection
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceVersionReader,SourceRef
from company_wiki.source_catalog.narrative_artifact_store import NarrativeArtifactStore,LocalNarrativeObjectStore
from company_wiki.source_catalog.resolver import SourceRequest
CLI='import sys; sys.dont_write_bytecode=True; sys.addaudithook(lambda e,a: (_ for _ in ()).throw(RuntimeError("G1 zero network")) if e in {"socket.connect","socket.getaddrinfo","http.client.connect"} else None); from company_wiki.source_catalog.narrative_transport_cli import main; sys.exit(main())'
wire={}
def invoke(config,operation,request,label,extra=()):
    data=request if isinstance(request,bytes) else encoded(request)+b"\n"
    cmd=[sys.executable,"-X","utf8","-B","-c",CLI,"--config",str(config),"--operation",operation,*extra]
    r=subprocess.run(cmd,input=data,capture_output=True,timeout=50,cwd=REPO,env={**os.environ,"PYTHONPATH":str(REPO/"src"),"PYTHONDONTWRITEBYTECODE":"1","PYTHON_DOTENV_DISABLED":"1","COMPANY_WIKI_NETWORK":"blocked","COMPANY_WIKI_REAL_LLM":"0"})
    for suffix,b in [("stdin",data),("stdout",r.stdout),("stderr",r.stderr)]:
        (OUT/(label+"."+suffix+".json")).write_bytes(b)
    wire[label]={"stdin_bytes":len(data),"stdout_bytes":len(r.stdout),"stderr_bytes":len(r.stderr),"exit":r.returncode}
    check("receipt_cap:"+label,len(r.stderr)<=16384)
    return r
with TemporaryDirectory(prefix="g1cw-") as temp:
    owned=Path(temp).resolve()
    check("owned_TEMP_within_TEMP",owned.is_relative_to(Path(os.environ["TEMP"]).resolve()),str(owned))
    clone=owned/"fixture"
    shutil.copytree(Path(fixture["owned_fixture"]),clone)
    for cfg in clone.rglob("config.yaml"):
        conf=yaml.safe_load(cfg.read_bytes())
        conf["catalog_dir"]=str(clone/Path(conf["catalog_dir"]).relative_to(Path(fixture["owned_fixture"])))
        for root in conf["roots"]:
            root["path"]=str(clone/Path(root["path"]).relative_to(Path(fixture["owned_fixture"])))
        cfg.write_text(yaml.safe_dump(conf,allow_unicode=True,sort_keys=False),encoding="utf-8")
    cn=clone/"CN-688012/config.yaml"
    us=clone/"US-MSFT/config.yaml"
    ref=invoke(cn,"reference",fixture["reference_request"],"real-reference")
    check("public_reference_success",ref.returncode==0)
    reference=json.loads(ref.stdout)
    check("compact_ref_exact_six",set(reference)=={"schema_version","artifact_version_id","artifact_sha256","byte_size","generation_sha256","subject_ref"} and set(reference["subject_ref"])=={"schema_version","kind","item_key","subject_sha256"})
    check("compact_request_ref_cap_includes_LF",len(encoded(fixture["reference_request"]))+1<=16384 and len(ref.stdout)+1<=16384)
    read_request=deepcopy(fixture["read_request"])
    read_request["narrative_ref"]=reference
    read=invoke(cn,"read",read_request,"real-read")
    check("public_read_exact_pinned_bytes",read.returncode==0 and sha(read.stdout)==fixture["bundle_sha256"] and read.stdout==(handoff_path.parent/"real-read3.stdout.json").read_bytes())
    bundle=json.loads(read.stdout)
    receipt=json.loads(read.stderr)
    parents=bundle["subject_binding"]["parent_source_refs"]
    lineage=sha(canonical_json(bundle["subject_binding"]).encode())
    check("read_65_complete_parents",len(parents)==65 and receipt["parent_count"]==65)
    check("lineage_real_full_subject_hash",receipt["lineage_sha256"]==lineage and lineage not in {reference["subject_ref"]["subject_sha256"],parents[0]["content_sha256"]})
    check("read_receipt_exact_eleven",set(receipt)=={"schema_version","status","narrative_ref","as_of_date","observed_at","locator_count","parent_count","lineage_sha256","selection_status","quality_status","replay_status"})
    evidence=invoke(cn,"evidence-list",read_request,"real-evidence-page",("--limit","1","--offset","1"))
    view=json.loads(evidence.stdout)
    ev_receipt=json.loads(evidence.stderr)
    check("evidence_page_complete_lineage",evidence.returncode==0 and view["schema_version"]=="narrative-evidence-view/3" and view["subject_binding"]==bundle["subject_binding"] and view["parent_source_refs"]==parents and len(view["items"])==1 and view["offset"]==1 and view["total"]>1)
    check("evidence_receipt_exact_eleven",set(ev_receipt)=={"schema_version","status","view_sha256","byte_size","narrative_ref","as_of_date","observed_at","replay_status","locator_count","parent_count","lineage_sha256"} and ev_receipt["lineage_sha256"]==lineage and ev_receipt["parent_count"]==65)
    for mutation,reason in [("issuer","projection_issuer_mismatch"),("asof","projection_after_as_of"),("generation","artifact_reference_mismatch"),("artifact","artifact_reference_mismatch")]:
        req=deepcopy(read_request)
        if mutation=="issuer": req["expected_issuer"]={"market":"CN","security_id":"000001"}
        elif mutation=="asof": req["as_of_date"]="2026-10-07"
        elif mutation=="generation": req["narrative_ref"]["generation_sha256"]="f"*64
        else: req["narrative_ref"]["artifact_sha256"]="f"*64
        r=invoke(cn,"read",req,"refusal-"+mutation)
        check("public_refusal:"+mutation,r.returncode==2 and not r.stdout and json.loads(r.stderr)["reason"]==reason)
    too_big=b" "*(16384-len(encoded(read_request)))+encoded(read_request)+b"\n"
    r=invoke(cn,"read",too_big,"refusal-wire-over-LF-cap")
    check("public_request_cap_counts_LF",len(too_big)==16385 and r.returncode==2 and not r.stdout and json.loads(r.stderr)["reason"]=="invalid_request")
    config=load_catalog_config(cn)
    cat=SourceCatalog(config)
    art=NarrativeArtifactStore.for_reading(config.database_path,LocalNarrativeObjectStore(config.catalog_dir))
    original_open=SourceVersionReader.open_version
    opens=[]
    def counted(self,ref,**kw):
        opens.append(ref.content_sha256)
        return original_open(self,ref,**kw)
    SourceVersionReader.open_version=counted
    try:
        resolver=lambda subject:open_verified_projection(cat,projection_id=subject.item_key,expected_projection_sha256=subject.subject_sha256)
        reader=NarrativeTransportReader(art,SourceVersionReader(cat),projection_ref_resolver=resolver)
        got=reader.read(NarrativeReadRequest.from_dict(read_request))
        check("actual_public_resolver_opens_each_parent_once",Counter(opens)==Counter(p["content_sha256"] for p in parents) and len(opens)==65,{"opens":len(opens),"distinct":len(set(opens))})
        opens.clear()
        got_evidence=NarrativeEvidenceViewReader(reader).read(NarrativeReadRequest.from_dict(read_request),NarrativeEvidenceViewQuery("evidence-list",limit=1))
        check("evidence_resolver_opens_each_parent_once",Counter(opens)==Counter(p["content_sha256"] for p in parents) and len(opens)==65)
        parent=parents[-1]
        loc=cat.reader.fetchone("SELECT root_id,relative_path FROM locations WHERE document_id=? AND source_id=?",(parent["document_id"],parent["source_id"]))
        root=next(r.path for r in config.roots if r.root_id==loc["root_id"])
        raw=root/loc["relative_path"]
        sealed=raw.read_bytes()
        try:
            raw.write_bytes(sealed+b" ")
            r=invoke(cn,"read",read_request,"refusal-last-parent-bytes")
            check("last_parent_byte_corruption_refused",r.returncode==2 and not r.stdout and json.loads(r.stderr)["reason"]=="no_verified_location")
        finally:
            raw.write_bytes(sealed)
        check("owned_last_parent_restored",sha(raw.read_bytes())==parent["content_sha256"])
    finally:
        SourceVersionReader.open_version=original_open
        art.close()
        cat.close()
    cfg=load_catalog_config(us)
    cat=SourceCatalog(cfg)
    try:
        source_reader=SourceVersionReader(cat)
        observations=[]
        for candidate in fixture["nonperiod_candidates"]:
            ref=SourceRef(**candidate["source_ref"])
            described=source_reader.describe_candidate(ref)
            opened=source_reader.open_version(ref,purpose="source_export")
            check("real_nonperiod:"+candidate["document_kind"],described["capture_ready"] and described["fiscal_year"] is None and described["fiscal_period"] is None and described["period_end"] is None and sha(opened.data)==candidate["snapshot_sha256"])
            observations.append({"kind":described["document_kind"],"fiscal_year":described["fiscal_year"],"fiscal_period":described["fiscal_period"],"published_date":described["published_date"]})
            query=source_reader.query_local(SourceRequest(entity="MICROSOFT CORP",market="US",security_id="MSFT",document_kind=candidate["document_kind"],fiscal_year=2027,as_of_date="2026-10-08"))
            check("no_date_borrowed_for_FY:"+candidate["document_kind"],not query.matches)
    finally: cat.close()
check("owned_TEMP_removed",not owned.exists())
from company_wiki.automation.narrative_http_model import NarrativeHTTPModel
from company_wiki.automation.narrative_model import NarrativeModelRequest
from company_wiki.automation.narrative_generation import generation_sha256,_projection_effective_model,generation_manifest
from company_wiki.automation.narrative_contracts import SourceMetadataValue,SourceRevisionEventPayload
from unit.test_narrative_batch import _request,_module,Reader
from unit.test_narrative_generation import manifest
request=_request()
model_request=NarrativeModelRequest("prompt/1","Use source data only.",'{"text":"business growth"}',"a"*64)
def http_bytes(options):
    allowed={k:v for k,v in options.items() if k in {"model_id","endpoint","max_output_tokens","thinking","reasoning_effort","temperature","reasoning_split","output_token_field"}}
    return NarrativeHTTPModel(api_key_env="G1_UNREAD_KEY",**allowed).request_bytes(model_request)
identity={}
for key in ["thinking","temperature","reasoning_split","reasoning_effort"]:
    options=request.model_options
    options.pop(key,None)
    null={**options,key:None}
    omitted=replace(request,model_options_json=canonical_json(options))
    nullable=replace(request,model_options_json=canonical_json(null))
    check("actual_HTTP_null_omitted:"+key,http_bytes(options)==http_bytes(null) and _projection_effective_model(options)==_projection_effective_model(null) and manifest(omitted)==manifest(nullable))
    identity[key]={"omitted_sha":generation_sha256(manifest(omitted)),"null_sha":generation_sha256(manifest(nullable)),"http_body_sha":sha(http_bytes(options))}
for key,values in {"thinking":["disabled","enabled"],"temperature":[0.2,0.8],"reasoning_split":[False,True],"reasoning_effort":["low","high"],"max_output_tokens":[100,200],"output_token_field":["max_tokens","max_completion_tokens"],"model_id":["first","second"],"endpoint":["https://one.invalid/v1/chat/completions","https://two.invalid/v1/chat/completions"]}.items():
    left={**request.model_options,key:values[0]}
    right={**request.model_options,key:values[1]}
    check("effective_change_invalidates:"+key,_projection_effective_model(left)!=_projection_effective_model(right) and generation_sha256(manifest(replace(request,model_options_json=canonical_json(left))))!=generation_sha256(manifest(replace(request,model_options_json=canonical_json(right)))))
    if key!="endpoint": check("actual_HTTP_change:"+key,http_bytes(left)!=http_bytes(right))
check("same_effective_purpose_reuses",manifest(replace(request,model_options_json=canonical_json({**request.model_options,"purpose":"narrative"})))==manifest(request))
base=subprocess.run(["git","--git-dir=C:/Users/郑曾波/Projects/company-wiki/.git","show","3d540797:src/company_wiki/automation/narrative_generation.py"],capture_output=True,check=True,cwd="C:/Users/郑曾波/Projects/company-wiki").stdout
baseline=types.ModuleType("company_wiki.automation._g1_baseline");baseline.__package__="company_wiki.automation"
exec(compile(base,"baseline_narrative_generation.py","exec"),baseline.__dict__)
module=_module()
event=module.build_batch_events(request,Reader(),now="2026-10-09T00:00:00Z").events[0]
payload=SourceRevisionEventPayload.from_dict(json.loads(event.payload_json))
old_manifest=baseline.generation_manifest(request,payload,execution_versions=module._execution_versions(request))
check("old_omitted_manifest_SHA_preserved",old_manifest==manifest(request) and baseline.generation_sha256(old_manifest)==generation_sha256(manifest(request)),{"old":baseline.generation_sha256(old_manifest),"current":generation_sha256(manifest(request)),"base_source_sha":sha(base)})
for metadata,projected in [
    ({"source_class":"official_json","title":None,"document_kind":"investor_relations","language":"unknown"},True),
    ({"source_class":"transcript","title":"call","document_kind":"investor_call_transcript","language":"en","declared_language":"en-US"},False)]:
    check("metadata_valid:"+metadata["source_class"],SourceMetadataValue.from_dict(metadata,projected=projected).to_dict()==metadata)
for field,bad in [("source_class",1),("title",[]),("document_kind",{}),("language",True),("declared_language",7)]:
    md={"source_class":"official_json","title":None,"document_kind":"investor_relations","language":"unknown"}
    md[field]=bad
    try: SourceMetadataValue.from_dict(md,projected=True)
    except ValueError: rejected=True
    else: rejected=False
    check("metadata_wrong_type_refused:"+field,rejected)
check("protected_raw_and_configs_unchanged",before=={str(x):sha(x.read_bytes()) for x in protected},{"paths":len(protected),"raws":len(fixture["originals"])})
check("source_SHA_unchanged_after_review",source_hashes=={name:sha((REPO/name).read_bytes()) for name in source_hashes})
check("zero_network_attempts",not network_attempts)
result={"schema_version":"w04-g1-cwp-independent-checks/1","checks":checks,"source_sha256":source_hashes,"wire":wire,"generation_identity":identity,"protected_baseline":before,"provider_calls":0,"model_calls":0,"http_calls":0,"network_attempts":network_attempts,"cost_usd":0,"TEMP_removed":True,"old_110_and_98_not_reexecuted":True}
(OUT/"checks.json").write_bytes(encoded(result)+b"\n")
print(json.dumps({"checks":len(checks),"provider_calls":0,"model_calls":0,"TEMP_removed":True},ensure_ascii=False))
