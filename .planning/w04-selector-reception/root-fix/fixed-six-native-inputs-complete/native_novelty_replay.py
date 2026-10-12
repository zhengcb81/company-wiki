"""Finite native replay; no downloads, raw copies, or paid/model calls."""
from pathlib import Path
import sys, json, hashlib, gzip, dataclasses, datetime, time, re
ROOT=Path.cwd(); sys.path.insert(0,str(ROOT/"src"))
from company_wiki.source_catalog.narrative_evidence import parse_pdf_bytes, select_narrative_evidence
from company_wiki.source_catalog.narrative_normalization import NarrativeNormalization
from company_wiki.document_normalization import normalize_document
from company_wiki.source_catalog.narrative_finalize import finalize_selection
from company_wiki.source_catalog.narrative_budget import _bundles, budget_diagnostics, SEMANTIC_BUDGET_POLICY
EV=ROOT/"docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w04_post_pw03_common_roots_2026-10-11/evidence/implementation"
OUT=Path(__file__).resolve().parent
STEM=sys.argv[1] if len(sys.argv)>1 else "native-novelty-six"
assert STEM.replace("-", "").isalnum()
assert not (OUT/(STEM+".json.gz")).exists(), "new replay requires a new evidence name"
H=lambda data:hashlib.sha256(data).hexdigest()
canonical=lambda value:json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",", ":")).encode()
load=lambda path:json.loads(Path(path).read_text(encoding="utf-8"))
old_path=Path(r"C:/Users/郑曾波/.codex/worktrees/w04-narrative-semantics-20261011/company-wiki")/EV.relative_to(ROOT)/"wp02/native-semantic-replay.json"
old_bytes=old_path.read_bytes(); frozen_old={row["key"]:row for row in json.loads(old_bytes)["items"]}
source_rows=load(EV/"wp02-stage-classification/native-stage-replay.json")["items"]
frozen_final=json.loads(gzip.decompress((EV/"wp02-stage-classification/native-stage-final-focused.json.gz").read_bytes()))
frozen_semantic={row["key"]:row for row in frozen_final["items"]}
result={"schema_version":"w04-root-native-budget/1","observed_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"status":"RUNNING","paid_calls":0,"model_calls":0,"http_calls":0,"raw_copies":0,"physical_parse_count":0,"legacy_baseline_ref":{"path":str(old_path),"sha256":H(old_bytes)},"implementation":{str(p):H((ROOT/p).read_bytes()) for p in [Path("src/company_wiki/source_catalog/narrative_semantic_coverage.py"),Path("src/company_wiki/source_catalog/narrative_budget.py"),Path("src/company_wiki/source_catalog/narrative_finalize.py"),Path("src/company_wiki/source_catalog/narrative_business_groups.py"),Path("src/company_wiki/source_catalog/narrative_evidence.py"),Path("src/company_wiki/source_catalog/narrative_stage_assertions.py"),Path("src/company_wiki/source_catalog/narrative_candidates.py"),Path("src/company_wiki/source_catalog/narrative_group_candidates.py"),Path("config.yaml"),Path("config/source_catalog.yaml")]},"items":[]}
def save():
    data=canonical(result)
    compressed=gzip.compress(data,compresslevel=9,mtime=0)
    (OUT/(STEM+".json.gz")).write_bytes(compressed)
    (OUT/(STEM+"-storage.json")).write_text(json.dumps({"compressed_sha256":H(compressed),"compressed_bytes":len(compressed),"uncompressed_sha256":H(data),"uncompressed_bytes":len(data),"roundtrip_verified":gzip.decompress(compressed)==data},indent=2)+"\n",encoding="utf-8")
for source in source_rows:
    key=source["key"]; started=time.monotonic(); print("START",key,flush=True)
    path=Path(source["path"])
    if len(str(path))>=245:path=Path("\\\\?\\"+str(path))
    data=path.read_bytes(); assert H(data)==source["sha"]
    sid="urn:company-wiki:source:sha256:"+source["sha"]
    if source["mime"]=="application/pdf":
        structure=parse_pdf_bytes(data,source_id=sid,source_sha256=source["sha"],parser_version="0.1.1",language=source["language"])
    else:
        doc=normalize_document(data,source_id=sid,source_sha256=source["sha"],mime_type=source["mime"])
        structure=NarrativeNormalization.language_structure(doc,source["language"])
    result["physical_parse_count"]+=1
    legacy=select_narrative_evidence(structure,title=Path(source["path"]).name,existing_kind=source["kind"],selector_version="0.7.1")
    legacy_sha=H(canonical([span.to_dict() for span in legacy.evidence_spans]))
    captured={}
    def observe(frame,event,arg):
        if event=="return" and frame.f_code is finalize_selection.__code__:captured.update(frame.f_locals)
    sys.setprofile(observe)
    try:package=select_narrative_evidence(structure,title=Path(source["path"]).name,existing_kind=source["kind"],selector_version="0.8.0")
    finally:sys.setprofile(None)
    assert captured["budget_policy"]==SEMANTIC_BUDGET_POLICY
    units={unit.coordinates.locator():unit for unit in structure.units}
    chosen={span.locator for span in package.evidence_spans}
    assert len(package.evidence_spans)<=package.selection_limit
    assert all(span.raw_text==units[span.locator].raw_text for span in package.evidence_spans)
    assert package.omitted_candidate_count==package.candidate_count-len(package.evidence_spans)
    bundles=_bundles(captured["budget_items"],SEMANTIC_BUDGET_POLICY)
    for b in bundles:
        locations={i.locator for i in b.items}
        assert not locations & chosen or locations <= chosen
    diagnostics=budget_diagnostics(captured["budget_items"],limit=package.selection_limit,policy=SEMANTIC_BUDGET_POLICY)
    candidate_by_id={c.unit.unit_id:c for c in captured["candidates"]}
    bundle_by_id={i.item_id:b for b in bundles for i in b.items}
    def focus(unit):
        return (key == "cn-annual" and unit.coordinates.page_number == 56) or unit.coordinates.page_number in source.get("focus_pages",[]) or unit.coordinates.paragraph_index in source.get("focus_paragraphs",[])
    decisions=[]
    for unit in structure.units:
        if not focus(unit):continue
        c=candidate_by_id.get(unit.unit_id);b=bundle_by_id.get(unit.unit_id)
        decisions.append({"locator":unit.coordinates.locator(),"raw_text":unit.raw_text,"selected":unit.coordinates.locator() in chosen,"candidate":c is not None,"score":c.score if c else None,"reasons":c.reasons if c else [],"budget_category":b.category if b else None,"group_id":b.items[0].group_id if b else None,"group_cost":b.cost if b else None})
    complete_selected_groups = []
    for bundle in bundles:
        ordered = sorted(bundle.items, key=lambda item: item.order_key)
        if all(item.locator in chosen for item in ordered):
            text = "".join(units[item.locator].raw_text for item in ordered)
            complete_selected_groups.append({"group_id": bundle.key,
                "locators": [item.locator for item in ordered], "raw_text": text,
                "raw_text_sha256": H(text.encode()), "span_cost": len(ordered)})
    previous=frozen_semantic.get(key,source)
    prior={s["locator"] for s in previous["focus_selected_spans"]}
    common={u["locator"] for u in previous["focus_units"]}&{d["locator"] for d in decisions}
    row={"key":key,"path":source["path"],"sha256":source["sha"],"source_bytes":len(data),"raw_sha_after":H(path.read_bytes()),"source_units":len(structure.units),"legacy_package_sha256":legacy_sha,"legacy_matches_frozen":legacy_sha==frozen_old[key]["selected_package_sha256"],"selector":"0.8.0","budget_policy":captured["budget_policy"],"candidate_count":package.candidate_count,"selected_count":len(package.evidence_spans),"selection_limit":package.selection_limit,"omitted_count":package.omitted_candidate_count,"status":package.status,"parser_coverage_complete":package.coverage_complete,"selected_package_sha256":H(canonical([s.to_dict() for s in package.evidence_spans])),"selected_spans":[s.to_dict() for s in package.evidence_spans],"complete_selected_groups":complete_selected_groups,"focus_decisions":decisions,"budget_diagnostics":[dataclasses.asdict(d) for d in diagnostics],"focus_gained":sorted((chosen-prior)&common),"focus_lost":sorted((prior-chosen)&common),"elapsed_seconds":time.monotonic()-started}
    assert row["raw_sha_after"]==source["sha"]
    result["items"].append(row);save()
    print("DONE",key,row["selected_count"],row["legacy_matches_frozen"],"gained",len(row["focus_gained"]),"lost",len(row["focus_lost"]),round(row["elapsed_seconds"],3),flush=True)
annual = next(row for row in result["items"] if row["key"] == "cn-annual")
checks = {"lpcvd_shipments_and_repeat_orders": (41, range(19, 22)),
          "tungsten_validation_and_repeat_orders": (44, range(11, 16)),
          "supplier_lead_time_constraint": (62, range(30, 33))}
selected = {span["locator"] for span in annual["selected_spans"]}
result["critical_business_recall"] = {
    name: {"locators": [f"loc:v1/page:{page}/paragraph:{p}" for p in paragraphs],
           "complete": all(f"loc:v1/page:{page}/paragraph:{p}" in selected for p in paragraphs)}
    for name, (page, paragraphs) in checks.items()}
# Fixed, subject-bound checks on one complete native-order group. No
# company/page special case is added to production; these are frozen test facts.
# Exact original locator results above remain a separate permanent diagnostic.
patterns = {
    "lpcvd_shipments": (r"LPCVD设备累计出货量突破三百个反应台",),
    "tungsten_validation_and_repeat_orders": (
        r"CVD", r"HAR", r"ALD", r"钨设备", r"该系列设备均已通过关键存储客户端现场验证",
        r"获得客户重复量产订单"),
    "supplier_lead_time_constraint": (r"关键零部件供应商", r"多厂商策略",
        r"若未来上游供应链产能紧张形势延续，将对公司设备交期产生影响"),
    "prismo_pd5_new_facts": (r"PRISMOPD5", r"4个反应腔", r"6英寸与8英寸工艺",
        r"PRISMOPD5设备已在客户生产线上验证通过并获得重复订单"),
}
result["bound_fact_recall"] = {}
for name, required in patterns.items():
    witnesses = []
    for group in annual["complete_selected_groups"]:
        compact = re.sub(r"\s+", "", group["raw_text"])
        if all(re.search(pattern, compact) for pattern in required):
            witnesses.append(group)
    result["bound_fact_recall"][name] = {
        "patterns_frozen_before_replay": list(required), "complete": bool(witnesses),
        "witnesses": witnesses}
result["claim_boundary"] = {
    "lpcvd_quantity": "LPCVD-specific three-hundred reaction stations; thin-film total cannot substitute",
    "repeat_orders": "The page-41 text attributes repetition to some new equipment, not specifically LPCVD",
    "prismo": "PD5 production validation, four chambers and 6/8-inch switching are jointly new facts",
    "equivalence": "One actually selected complete group, one source SHA, native order, all bound predicates; no cross-group concatenation",
}
result["status"] = ("FAIL_LEGACY" if not all(row["legacy_matches_frozen"] for row in result["items"])
    else "PASS" if all(c["complete"] for c in result["bound_fact_recall"].values())
    else "FAIL_CRITICAL_RECALL")
result["semantic_acceptance"] = "fixed native annual subject-bound fact checks; summary and research still not_evaluated"
result["scratch_restore"] = {"raw_copies": 0, "downloaded_files": 0, "temporary_input_files": 0,
    "note": "small owned compressed replay evidence only; source directories never written"}
save(); print("ALL_DONE", result["status"], json.dumps({name: row["complete"] for name, row in result["bound_fact_recall"].items()}), flush=True)
if result["status"] != "PASS": sys.exit(1)
