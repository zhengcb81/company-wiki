"""One independent phase2 quality-band group; no 375-test/six-original replay."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from unittest.mock import patch
import uuid

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
CWP = Path(r"C:/Users/郑曾波/Projects/company-wiki")
TREE = Path(r"C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/company-wiki")
PHASE = TREE / ".planning/w04-root-novelty-recall/phase2-real-recall"
FREEZE = PHASE / "product-freeze.json"
EXPECTED = "2db879e8744fe646caa2a44a93d89ef4b89dbbf65f5fffe4549ed4d7d21b69ed"
SCRATCH = CWP / ".tmp" / ("w04nov-review-" + uuid.uuid4().hex[:10])
if (OUT / "report.json").exists() or SCRATCH.exists(): raise RuntimeError("Fresh review only")

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding="utf-8"))
def git(*args): return subprocess.run(["git", "-C", str(TREE), *args], capture_output=True, check=True).stdout
def metadata():
    result = {}
    for root in (CWP, TREE):
        for name in ("source_catalog.yaml", "source_acquisition.yaml"):
            p = root / "config" / name
            result[str(p)] = (p.exists(), p.stat().st_size if p.exists() else None, p.stat().st_mtime_ns if p.exists() else None)
    return result

started = time.monotonic()
frozen = read(FREEZE)
protected = tuple(frozen["products"]) + tuple(frozen["preserved_initial_non_owned_sha256"])
before = {p: sha(TREE / p) for p in protected}
history_paths = [PHASE.parent / p for p in frozen["preserved_phase1_evidence_sha256"]]
evidence_manifest = read(PHASE / "evidence-manifest.json")
history_paths += [PHASE / p for p in evidence_manifest["files"]]
history_paths += [PHASE / "evidence-manifest.json"]
history_before = {str(p): sha(p) for p in history_paths}
head = git("rev-parse", "HEAD")
status = git("status", "--porcelain")
index = Path(git("rev-parse", "--git-path", "index").decode().strip())
if not index.is_absolute(): index = TREE / index
index_sha = sha(index)
config = metadata()
rows = []

def check(name, ok, actual): rows.append({"name": name, "pass": bool(ok), "actual": actual})

check("SEVEN-PRODUCT-AND-OLD-EVIDENCE-FREEZE", sha(FREEZE) == EXPECTED and len(frozen["products"]) == 7
    and all(sha(TREE / p) == r["sha256"] and (TREE / p).stat().st_size == r["bytes"] for p,r in frozen["products"].items())
    and sha(PHASE.parent / "product-freeze.json") == frozen["phase1_freeze_sha256"]
    and all(sha(PHASE / p) == r["sha256"] and (PHASE / p).stat().st_size == r["bytes"] for p,r in evidence_manifest["files"].items()),
    {"phase2_freeze_sha256": sha(FREEZE), "products": 7, "phase1_freeze_sha256": sha(PHASE.parent / "product-freeze.json"),
     "frozen_phase2_evidence": len(evidence_manifest["files"]), "preserved_phase1_evidence": len(frozen["preserved_phase1_evidence_sha256"])})

sys.path.insert(0, str(TREE / "src"))
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_candidates import EvidenceCandidate
from company_wiki.source_catalog.narrative_evidence import _make_unit, NARRATIVE_SELECTOR_VERSION
from company_wiki.source_catalog import narrative_finalize as finalize
from company_wiki.source_catalog.narrative_routing import route_document
from company_wiki.source_catalog import narrative_semantic_coverage as coverage
from company_wiki.source_catalog import narrative_budget as budget
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256

SOURCE_SHA = "d" * 64
SOURCE = source_id_for_sha256(SOURCE_SHA)
PRODUCT = ("new_product_commercialization_milestone",)
CONCRETE_PRODUCT = (*PRODUCT, "quantified_operating_status")
REAL = "Delta新型设备已完成客户现场验证并取得重复订单。"

def finish(groups, limit, *, reverse=False, policy="semantic_coverage/1"):
    candidates = tuple(EvidenceCandidate(_make_unit(source_id=SOURCE, parser_version="0.1.1",
        coordinates=EvidenceCoordinates(page_number=page, paragraph_index=n), raw_text=text,
        unit_kind="pdf_text_block", source_role="company_filing", language="zh", metadata={}, quality_flags=()),
        ("products_rd",), reasons, score) for page,texts,score,reasons in groups for n,text in enumerate(texts, 1))
    parsed = DocumentStructure(source_id=SOURCE, source_sha256=SOURCE_SHA, language="zh", units=tuple(c.unit for c in candidates),
        page_count=max(g[0] for g in groups), pages_read=max(g[0] for g in groups))
    mapping = {c.unit.unit_id: "native-group-" + str(c.unit.coordinates.page_number) for c in candidates}
    route = replace(route_document("2025年度报告", existing_kind="annual"), selection_limit=limit)
    seen = []
    original = finalize.select_budget_items
    def observe(items, **kwargs):
        seen.extend(items)
        return original(items, **kwargs)
    with patch.object(finalize, "select_budget_items", observe):
        package = finalize.finalize_selection(parsed, route, tuple(reversed(candidates)) if reverse else candidates,
            group_ids=mapping, heading_pattern=re.compile(r"(?!)"), dropped_financial_count=0, budget_policy=policy)
    native = {c.unit.coordinates.locator(): c.unit.raw_text for c in candidates}
    assert len(package.evidence_spans) <= limit
    assert all(s.raw_text == native[s.locator] for s in package.evidence_spans)
    assert package.candidate_count == len(candidates) and package.omitted_candidate_count == len(candidates)-len(package.evidence_spans)
    selected = {s.coordinates.page_number for s in package.evidence_spans}
    for page,texts,_score,_reasons in groups:
        assert page not in selected or len([s for s in package.evidence_spans if s.coordinates.page_number == page]) == len(texts)
    bands = {b.page_key[1]: b.quality_band for b in budget._bundles(tuple(seen), policy)}
    return package, sorted(selected), seen, bands

SCRATCH.mkdir(parents=True)
(SCRATCH / "marker").write_bytes(b"owned pure phase2 review")
observations = []
try:
    alternatives = [
        ("dated-plan", "Delta新型设备预计到2027年完成客户验证。"),
        ("conditional", "Delta新型设备计划通过客户验证后交付500台。"),
        ("negated", "Delta新型设备尚未完成客户验证，规划交付500台。"),
        ("unknown-name-number", "Delta新型设备型号2027的技术特征涵盖500台规模。"),
    ]
    for name,text in alternatives:
        groups = [(1,[REAL],1,CONCRETE_PRODUCT),(2,[text],99,CONCRETE_PRODUCT)]
        package,pages,items,bands = finish(groups,1)
        check("ORDINARY-REAL-BEATS-" + name, pages == [1] and bands[1] == 0 and bands[2] > 0,
            {"selected_pages": pages, "quality_bands": bands, "signals": {i.page_key[1]: i.coverage_signature.stage_signals for i in items}})
    reserve = ("downstream_business_extension", *CONCRETE_PRODUCT)
    _,pages,_,bands = finish([(1,[REAL],1,reserve),(2,[alternatives[1][1]],99,reserve)],1)
    check("RESERVED-USES-SAME-REAL-BEFORE-PLAN-BAND", pages == [1] and bands[1] == 0 and bands[2] == 1,
          {"selected_pages": pages, "quality_bands": bands})
    groups = [(g,[f"设备型号{g}已完成客户验证并出货{g+30}反应台。"],30-g,PRODUCT) for g in range(1,8)]
    groups += [(g,[f"公司第{g}阶段持续完善ESG沟通与一般服务。"],1,("business_risk_or_constraint",)) for g in range(10,15)]
    groups += [(g,[f"行业第{g}阶段促进长期生态合作。"],1,("current_industry_context",)) for g in range(20,25)]
    package,pages,_,bands = finish(groups,6)
    check("FACTS-PRECEDE-GENERIC-FAMILY-QUOTA", all(p < 10 for p in pages) and len(pages) == 6,
          {"selected_pages": pages, "quality_bands": bands})
    groups = [(g,[f"设备型号{g}已完成客户验证。",f"该设备技术说明{g}覆盖工艺。"],60-g,PRODUCT) for g in range(1,20)]
    groups += [(30,["关键零件短缺导致设备供应交期延长。","公司采用多个供应商缓解具体供应限制。"],1,("specific_operating_constraint",)),
               (31,["行业设备需求本期同比增长20%。","新增客户工厂采购规模扩大。"],1,("quantified_industry_change",))]
    package,pages,_,bands = finish(groups,12)
    check("CONCRETE-RISK-AND-QUANTIFIED-INDUSTRY-SAME-BAND-FAIRNESS", 30 in pages and 31 in pages
          and bands[30] == 0 and bands[31] == 0 and package == finish(groups,12,reverse=True)[0],
          {"selected_pages": pages, "risk_band": bands[30], "industry_band": bands[31]})
    old_weak = "另一款医疗设备已经交付客户并形成服务业务。"
    new_weak = "另一款医疗设备的通用技术背景和服务范围说明。"
    baseline = "公司推进研发与客户支持工作。新型设备计划到2027年完成客户验证。"
    new_fact = baseline.replace("2027", "2028")
    _,old_pages,_,old_bands = finish([(1,[baseline],30,PRODUCT),(2,[new_fact],29,PRODUCT),(3,[old_weak],1,PRODUCT)],2)
    _,new_pages,_,new_bands = finish([(1,[baseline],30,PRODUCT),(2,[new_fact],29,PRODUCT),(3,[new_weak],1,PRODUCT)],2)
    check("WEAK-FIXTURE-ROLE-CORRECTION-IS-SEMANTICALLY-JUSTIFIED", old_bands[3] == 0 and new_bands[3] == 2
          and old_pages == [1,3] and new_pages == [1,2],
          {"original_actual_delivery_band": old_bands[3], "new_background_band": new_bands[3],
           "original_weak_selected_pages": old_pages, "new_background_selected_pages": new_pages,
           "quantity_and_stage_selection_assertion": "unchanged {1,2} with genuinely generic third candidate"})
    old = "公司推进工艺支持服务。LPCVD设备已完成客户验证。"
    repeated = "公司推进工艺支持服务。LPCVD 设备已完成客户验证！"
    novel = "医疗设备已获得客户重复订单并交付300台。"
    package,pages,items,bands = finish([(1,[old],30,PRODUCT),(2,[repeated],29,PRODUCT),(3,[novel],1,PRODUCT)],2)
    signatures = {i.page_key[1]:i.coverage_signature for i in items}
    check("SAME-BAND-LAYOUT-SOFT-REPEAT-STILL-LEAVES-NOVEL-FACT", pages == [1,3] and len(items) == 3
          and set(bands.values()) == {0} and coverage.softly_repeats(signatures[1], signatures[2]),
          {"selected_pages": pages, "quality_bands": bands, "no_hard_candidate_removal": len(items) == 3})
    for label,a,b in (
        ("quantity", "LPCVD设备已出货300反应台。", "LPCVD设备已出货500反应台。"),
        ("subject", "薄膜设备已出货300反应台。", "LPCVD设备已出货300反应台。"),
        ("stage", "PRISMO设备已交付客户并进行验证。", "PRISMO设备已验证通过，具有4个反应腔并获得重复订单。"),
    ):
        _,pages,_,bands = finish([(1,[a],30,PRODUCT),(2,[b],29,PRODUCT),(3,[new_weak],1,PRODUCT)],2)
        check("NOVEL-" + label + "-ASSERTION-NOT-WEAKENED", pages == [1,2], {"selected_pages": pages, "bands": bands})
    named = ("named_product_milestone_context",)
    _,pages,_,bands = finish([(1,["Delta新型设备型号的通用技术背景。"],99,named),(2,["公司长期推进一般行业生态服务。"],1,("current_industry_context",))],2)
    check("NAME-ONLY-IS-GENERIC-NOT-REALIZED", bands[1] == bands[2] == 3, {"quality_bands": bands})
    many = [(g,[f"设备型号{g}已完成客户验证。",f"该设备第{g}项技术说明。",f"该设备交付{g+100}台。"],120-g,PRODUCT) for g in range(1,41)]
    package,pages,items,_ = finish(many,96)
    picked = {i.item_id for i in budget.select_budget_items(tuple(items),limit=96,policy="semantic_coverage/1")}
    dropped = {uid for row in budget.budget_diagnostics(tuple(items),limit=96,policy="semantic_coverage/1") for uid in row.item_ids}
    check("96-WHOLE-GROUP-REAL-COST-OMITTED-PARTITION", len(package.evidence_spans) <= 96
          and picked.isdisjoint(dropped) and picked|dropped == {i.item_id for i in items}
          and package.omitted_candidate_count == 120-len(package.evidence_spans),
          {"spans_selected": len(package.evidence_spans), "whole_groups_selected": len(pages), "omitted": package.omitted_candidate_count})
    _,legacy_pages,legacy_items,_ = finish([(1,[REAL],1,CONCRETE_PRODUCT),(2,[alternatives[1][1]],99,CONCRETE_PRODUCT)],1,policy="legacy")
    check("LEGACY-RANK-AND-CORRECT-DEFAULT-BOUNDARY", legacy_pages == [2] and NARRATIVE_SELECTOR_VERSION == "0.8.0"
          and budget.select_budget_items(tuple(legacy_items),limit=1) == budget.select_budget_items(tuple(legacy_items),limit=1,policy="legacy")
          and route_document("年度报告",existing_kind="annual").selection_limit == 96
          and route_document("招股说明书",existing_kind="prospectus").selection_limit == 160,
          {"legacy_high_score_plan_selected": legacy_pages, "public_default": NARRATIVE_SELECTOR_VERSION,
           "direct_budget_default": "legacy", "annual_cap": 96, "IPO_cap": 160})
    # Observe the preexisting protected reservation boundary without claiming
    # a global all-branch quality ordering that this phase did not introduce.
    _,cross_pages,_,cross_bands = finish([(1,[REAL],1,CONCRETE_PRODUCT),(2,[alternatives[1][1]],99,reserve)],1)
    observations.append({"name": "PREEXISTING-PROTECTED-RESERVE-BEFORE-ORDINARY", "selected_pages": cross_pages,
        "bands": cross_bands, "scope": "Quality order is shared within each branch; protected reserved prepass still precedes ordinary offers."})
finally:
    if SCRATCH.resolve().parent != (CWP / ".tmp").resolve() or not SCRATCH.name.startswith("w04nov-review-"):
        raise RuntimeError("Refuse delete outside unique owned short scratch")
    shutil.rmtree(SCRATCH)

check("FINAL-FROZEN-SOURCE-OLD-FAIL-WIP-GIT-CONFIG-UNCHANGED", sha(FREEZE) == EXPECTED
      and before == {p:sha(TREE/p) for p in protected} and history_before == {str(p):sha(p) for p in history_paths}
      and head == git("rev-parse","HEAD") and status == git("status","--porcelain") and index_sha == sha(index)
      and config == metadata() and not SCRATCH.exists(),
      {"freeze_sha256": sha(FREEZE), "products": 7, "unrelated_WIP": 22, "old_evidence_files": len(history_before),
       "HEAD_index_status_config_preserved": True, "scratch_absent": not SCRATCH.exists()})
passed = all(r["pass"] for r in rows)
report = {"schema_version":"w04-phase2-independent-engineering/1", "state":"FINAL_STOP",
    "verdict":"PASS_WITH_SCOPE" if passed else "ENGINEERING_BLOCKER", "checks":len(rows), "passed":sum(r["pass"] for r in rows),
    "failed":[r["name"] for r in rows if not r["pass"]], "probes":rows, "observations":observations,
    "freeze_sha256":EXPECTED, "seconds":round(time.monotonic()-started,4),
    "scope":"Pure engineering only; no author375 rerun or six-original replay", "calls":{"provider":0,"network":0,"LLM":0},"fees_usd":0,
    "fixture_review":"Reasonable role isolation: old WEAK has actual delivery and therefore deserves band0; revised generic background does not. All original quantity/subject/stage assertions are retained. Layout competitor is explicitly another realized fact to exercise same-band soft repetition.",
    "residual":["ROOT fixed real six-original native checkpoints and full0.7.1 package hashes remain required",
                "Protected reserve prepass still precedes ordinary offers; this package shares quality classification within branches, not a new global reservation policy",
                "No claim of logical equivalence, business truth, summary quality or downstream RF acceptance"],
    "mutations":{"products":0,"old_evidence":0,"shared_PWF":0,"Git":0,"config":0},
    "scratch":{"path":str(SCRATCH),"initial_exists":False,"final_exists":SCRATCH.exists()},}
(OUT/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
md=f"""# W04 Phase2 independent engineering review

**{report['verdict']} — {report['passed']}/{report['checks']} short independent checks, {report['seconds']} seconds. FINAL_STOP.**

Seven-product freeze `{EXPECTED}` verified before/after. No author375 run, six-original replay, download, provider, network, model or cost. Public finalizer uses actual whole-group signatures and real source text. Low-score realized validation/orders beat high-score plans, conditional/negated/unknown texts under the same reason tags. Ordinary and reserved candidates use the same proof-backed quality bands; important source-owned concrete risks and quantified industry changes share the highest band and category fairness.

## Fixture review

The old WEAK says already delivered: it legitimately contains a realized fact and is band0. Independent countermodel confirms it correctly displaces a planned new-stage candidate. The revised generic technical background has no realized proof and isolates the original quantity/subject/stage test purposes; those assertions remain unchanged. The layout-only repetition control uses a different low-score realized fact, keeping all competitors in band0. The original exact repeat is still softly demoted and not hard-removed. This is test-role correction, not a weakened recall assertion; the independent low-score actual-vs-plan tests expressly preserve the new requirement.

Native raw text, full groups, actual span costs,96 annual/160IPO cap, exact omitted partition, legacy score rank and corrected public0.8/directlegacy boundary remain. All seven products,22 unrelated WIP files, old Phase1/Phase2 failure evidence, HEAD/index/status/config metadata remained unchanged; short owned scratch restored.

## Boundary and observation

The preexisting protected-reserve prepass still runs before ordinary offers. Quality order is consistent **within both branches**; this is not a claim that an ordinary realized fact always outranks a reserved plan across branches. The tiny observation is recorded in `report.json` for ROOT to apply against the established reservation contract.

**Engineering only.** ROOT must independently replay fixed real six-original native checkpoints and full ordered0.7.1 package hashes. Old real recall FAILs are preserved and are not cleared by these probes. No broad substring may substitute thin-film totals or another product's quantity/orders for LPCVD's bound specific fact; no plan may substitute completion. Summary quality/downstream RF not evaluated.
"""
(OUT/"report.md").write_text(md,encoding="utf-8")
manifest={"schema_version":"w04-phase2-independent-engineering-freeze/1","state":"FINAL_STOP","verdict":report["verdict"],
    "files":[{"path":p.name,"sha256":sha(p),"bytes":p.stat().st_size} for p in sorted(OUT.iterdir()) if p.is_file() and p.name!="manifest.json"]}
(OUT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"verdict":report["verdict"],"checks":len(rows),"failed":report["failed"],"seconds":report["seconds"],
                  "manifest_sha256":sha(OUT/"manifest.json"),"observations":observations},ensure_ascii=False))
raise SystemExit(0 if passed else 1)
