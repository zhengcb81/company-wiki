"""Independent W04 pure engineering acceptance; no six-original replay."""
from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import inspect
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
FREEZE = TREE / ".planning/w04-root-novelty-recall/product-freeze.json"
EXPECTED = "b17fafe79199ccc2091356de1e2a012becfa6dd001a7d4a541b30b471a60a6db"
SCRATCH = CWP / ".tmp" / ("w04nov-review-" + uuid.uuid4().hex[:10])
if (OUT / "report.json").exists() or SCRATCH.exists():
    raise RuntimeError("Fresh owned review output/scratch required")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def git(*args):
    return subprocess.run(["git", "-C", str(TREE), *args], capture_output=True, check=True).stdout


def inventory(paths):
    return {rel: sha(TREE / rel) for rel in paths}


def metadata(path):
    return {"exists": path.exists(), "size": path.stat().st_size if path.exists() else None,
            "mtime_ns": path.stat().st_mtime_ns if path.exists() else None}


started = time.monotonic()
frozen = read(FREEZE)
before = inventory(frozen["products"])
baseline = read(FREEZE.parent / frozen["initial_manifest"])
nonowned = tuple(frozen["preserved_initial_non_owned_sha256"])
wip_before = inventory(nonowned)
head_before = git("rev-parse", "HEAD").decode().strip()
status_before = git("status", "--porcelain")
git_index_path = Path(git("rev-parse", "--git-path", "index").decode().strip())
if not git_index_path.is_absolute(): git_index_path = TREE / git_index_path
index_before = sha(git_index_path)
config_paths = [TREE / "config/source_catalog.yaml", TREE / "config/source_acquisition.yaml",
                CWP / "config/source_catalog.yaml", CWP / "config/source_acquisition.yaml"]
config_before = {str(p): metadata(p) for p in config_paths}
rows = []


def check(name, ok, actual):
    rows.append({"name": name, "pass": bool(ok), "actual": actual})


check("FROZEN-SIX-PRODUCTS", sha(FREEZE) == EXPECTED and len(before) == 6
      and all(before[k] == v["sha256"] and (TREE / k).stat().st_size == v["bytes"]
              for k, v in frozen["products"].items()), {"freeze_sha256": sha(FREEZE), "products": before})
check("INITIAL-22-WIP-HEAD", len(nonowned) == 22 and head_before == frozen["head"]
      and all(wip_before[k] == baseline["sha256"][k] for k in nonowned),
      {"head": head_before, "protected_wip_files": len(nonowned)})

sys.path.insert(0, str(TREE / "src"))
from company_wiki.source_catalog.narrative_candidates import EvidenceCandidate
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_evidence import _make_unit, select_narrative_evidence
from company_wiki.source_catalog import narrative_finalize as finalize
from company_wiki.source_catalog.narrative_routing import route_document
from company_wiki.source_catalog import narrative_semantic_coverage as coverage
from company_wiki.source_catalog.narrative_budget import budget_diagnostics, LEGACY_BUDGET_POLICY
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256

SHA = "e" * 64
SOURCE = source_id_for_sha256(SHA)
REASONS = ("new_product_commercialization_milestone",)
BG = "公司持续完善研发与工艺支持，扩展客户服务能力，提升技术水平及运营效率。"
WEAK = "另一款医疗设备已完成交付，形成新的医疗服务业务。"


def unit(page, paragraph, text, score):
    native = _make_unit(source_id=SOURCE, parser_version="0.1.1",
        coordinates=EvidenceCoordinates(page_number=page, paragraph_index=paragraph),
        raw_text=text, unit_kind="pdf_text_block", source_role="company_filing",
        language="zh", metadata={}, quality_flags=())
    return EvidenceCandidate(native, ("products_rd",), REASONS, score)


def finish(groups, *, limit=2, policy="semantic_coverage/1", reverse=False, default=False):
    candidates = tuple(unit(page, paragraph, text, score) for page, members, score in groups
                       for paragraph, text in members)
    mapping = {c.unit.unit_id: "group-" + str(c.unit.coordinates.page_number) for c in candidates}
    structure = DocumentStructure(source_id=SOURCE, source_sha256=SHA, language="zh",
        units=tuple(c.unit for c in candidates), page_count=max(g[0] for g in groups), pages_read=max(g[0] for g in groups))
    route = replace(route_document("2025年度报告", existing_kind="annual"), selection_limit=limit)
    seen = []
    planner = finalize.select_budget_items
    def observe(items, **kwargs):
        seen.extend(items)
        return planner(items, **kwargs)
    options = {} if default else {"budget_policy": policy}
    with patch.object(finalize, "select_budget_items", observe):
        result = finalize.finalize_selection(structure, route, tuple(reversed(candidates)) if reverse else candidates,
            group_ids=mapping, heading_pattern=re.compile(r"(?!)"), dropped_financial_count=0, **options)
    raw = {c.unit.coordinates.locator(): c.unit.raw_text for c in candidates}
    assert all(span.raw_text == raw[span.locator] for span in result.evidence_spans)
    assert len(result.evidence_spans) <= limit
    assert result.candidate_count == len(candidates)
    assert result.omitted_candidate_count == len(candidates) - len(result.evidence_spans)
    return result, seen, structure


def pages(package):
    return sorted({s.coordinates.page_number for s in package.evidence_spans})


def whole_groups(package, candidates):
    picked = {s.coordinates.locator() for s in package.evidence_spans}
    sets = {}
    for item in candidates:
        sets.setdefault(item.group_id, set()).add(item.locator)
    return all(not (locators & picked) or locators <= picked for locators in sets.values())


SCRATCH.mkdir(parents=True)
marker = SCRATCH / "baseline.txt"
marker.write_bytes(b"owned independent synthetic marker\r\n")
marker_before = sha(marker)
try:
    pairs = [
        ("number-CN", "LPCVD设备累计出货300反应台。", "LPCVD设备累计出货500反应台。"),
        ("number-Chinese", "LPCVD设备累计出货三百反应台。", "LPCVD设备累计出货五百反应台。"),
        ("decimal-unit", "LPCVD设备产能达到2.5万台。", "LPCVD设备产能达到3.5万台。"),
        ("percentage", "LPCVD设备良率达到85.5%。", "LPCVD设备良率达到95.5%。"),
        ("range", "LPCVD设备交付周期为6-8周。", "LPCVD设备交付周期为8-12周。"),
        ("unit", "LPCVD设备累计交付300台。", "LPCVD设备累计交付300套。"),
        ("subject-total-vs-type", "薄膜设备总累计出货300反应台。", "LPCVD设备累计出货300反应台。"),
        ("plan-vs-realized", "新型设备计划通过客户验证。", "新型设备已通过客户验证。"),
        ("ongoing-vs-completed", "新型设备正在进行客户验证。", "新型设备已完成客户验证。"),
        ("negation", "新型设备已获得重复订单。", "新型设备尚未获得重复订单。"),
        ("English-number", "LPCVD equipment has shipped 300 reactors.", "LPCVD equipment has shipped 500 reactors."),
        ("English-phase", "The equipment has passed customer validation.", "The equipment plans to pass customer validation."),
        ("English-negation", "The equipment has received repeat orders.", "The equipment has not received repeat orders."),
        ("PRISMO-new-stage", "PRISMO设备已交付客户并正在进行生产验证。", "PRISMO设备已验证通过，具有4个反应腔，可切换6和8英寸晶圆。"),
        ("short-subset-new-fact", "新型设备已完成客户验证。", "新型设备已完成客户验证。新型设备获得新增订单，具备4个反应腔。"),
    ]
    for name, a, b in pairs:
        groups = [(1, [(1, BG + a)], 30), (2, [(1, BG + b)], 29), (3, [(1, WEAK)], 1)]
        package, items, _ = finish(groups)
        signatures = {i.page_key[1]: i.coverage_signature for i in items}
        repeats = coverage.softly_repeats(signatures[2], signatures[1])
        check("PUBLIC-FINALIZER-" + name, pages(package) == [1, 2] and not repeats,
              {"selected_pages": pages(package), "soft_repeats": repeats,
               "complete": [signatures[1].complete, signatures[2].complete]})
    token_pairs = [("300", "500"), ("2.5", "3.5"), ("85%", "95%"), ("6-8", "8-12")]
    check("ACTUAL-TOKENIZER-NUMERIC-VECTORS", all(coverage.coverage_tokens("设备出货" + a + "台")
          != coverage.coverage_tokens("设备出货" + b + "台") for a, b in token_pairs), token_pairs)
    groups = [(1, [(10, "备累计交付300反应台；ALD设备累计交付500反应台。"), (9, BG + "LPCVD设")], 30),
              (2, [(10, "备累计交付500反应台；ALD设备累计交付300反应台。"), (9, BG + "LPCVD设")], 29),
              (3, [(1, WEAK)], 1)]
    package, items, _ = finish(groups, limit=4, reverse=True)
    same, _, _ = finish(groups, limit=4)
    signatures = {i.page_key[1]: i.coverage_signature for i in items}
    check("NATIVE-9-10-SUBJECT-NUMBER-REJOIN", pages(package) == [1, 2] and package == same
          and whole_groups(package, items) and signatures[1].complete
          and "lpcvd设备累计交付300反应台" in signatures[1].protected_sentences[-2]
          and not coverage.softly_repeats(signatures[1], signatures[2]),
          {"selected_pages": pages(package), "whole_groups": whole_groups(package, items),
           "first_protected_sentences": signatures[1].protected_sentences,
           "per_group_shared_signature": all(i.coverage_signature == signatures[i.page_key[1]] for i in items)})
    groups = [(1, [(1, BG + "LPCVD设备已累计交付300反应台。")], 30),
              (2, [(1, BG + "LPCVD 设备已累计交付 300 反应台！")], 29),
              (3, [(1, WEAK)], 1)]
    package, items, structure = finish(groups)
    signatures = {i.page_key[1]: i.coverage_signature for i in items}
    check("LAYOUT-ONLY-POSITIVE-SOFT-REPEAT", len(items) == 3 and pages(package) == [1, 3]
          and coverage.softly_repeats(signatures[1], signatures[2]),
          {"selected_pages": pages(package), "planner_candidates": len(items), "hard_dedup_did_not_remove_candidate": len(items) == 3})
    words = "amber birch cedar dune elm fir gorse heath iris jade kelp lime maple nut oak pine quill reed sage teak umber vine willow yarrow zinc"
    near = words + " lavender"
    short = " ".join(words.split()[:13])
    a, b, c = map(coverage.coverage_signature, (words, near, short))
    check("HIGH-SYMMETRIC-85-PERCENT-ONLY", coverage.softly_repeats(a, b)
          and not coverage.softly_repeats(a, c) and not coverage.softly_repeats(c, a),
          {"tokens": [len(s.tokens) for s in (a, b, c)], "complete": [s.complete for s in (a, b, c)]})
    unbound = coverage.coverage_signature("持续完善工艺流程并提升水平。累计达到300个。")
    truncated = coverage.group_coverage_signature(["设备" * 5000, "设备新出货500台。"])
    check("UNBOUND-OR-TRUNCATED-NO-PENALTY", not unbound.complete and not truncated.complete
          and not coverage.softly_repeats(unbound, unbound) and not coverage.softly_repeats(truncated, truncated),
          {"unbound_complete": unbound.complete, "truncated_complete": truncated.complete, "bounded_tokens": len(truncated.tokens)})
    legacy, _, _ = finish(groups, default=True)
    explicit, _, _ = finish(groups, policy=LEGACY_BUDGET_POLICY)
    selector_params = inspect.signature(select_narrative_evidence).parameters
    public_default = select_narrative_evidence(structure, title="2025年年度报告", existing_kind="annual")
    public_071 = select_narrative_evidence(structure, title="2025年年度报告", existing_kind="annual", selector_version="0.7.1")
    public_080 = select_narrative_evidence(structure, title="2025年年度报告", existing_kind="annual", selector_version="0.8.0")
    check("LEGACY-DEFAULT-AND-080-OPTIN", legacy == explicit and public_default == public_071
          and selector_params["selector_version"].default is None,
          {"finalizer_default": inspect.signature(finalize.finalize_selection).parameters["budget_policy"].default,
           "selector_default": str(selector_params["selector_version"].default), "synthetic_071_spans": len(public_071.evidence_spans),
           "synthetic_080_spans": len(public_080.evidence_spans), "real_071_package_hash": "pending ROOT six-original replay"})
    large = [(g + 1, [(p, f"设备{g+1}已交付{p+1}反应台，完成客户验证。") for p in range(3)], 120-g) for g in range(40)]
    package, items, _ = finish(large, limit=96)
    omitted = budget_diagnostics(tuple(items), limit=96, policy="semantic_coverage/1")
    selected_ids = {i.item_id for i in finalize.select_budget_items(tuple(items), limit=96, policy="semantic_coverage/1")}
    omitted_ids = {uid for row in omitted for uid in row.item_ids}
    check("96-CAP-WHOLE-GROUP-EXACT-PARTITION", len(package.evidence_spans) <= 96
          and whole_groups(package, items) and selected_ids.isdisjoint(omitted_ids)
          and selected_ids | omitted_ids == {i.item_id for i in items}
          and package.omitted_candidate_count == 120-len(package.evidence_spans),
          {"input_spans": 120, "selected": len(package.evidence_spans), "omitted": package.omitted_candidate_count,
           "whole_groups": whole_groups(package, items)})
    check("ORIGINAL-ANNUAL-IPO-CAPS", route_document("2025年年度报告", existing_kind="annual").selection_limit == 96
          and route_document("首次公开发行股票并上市招股说明书", existing_kind="prospectus").selection_limit == 160,
          {"annual": route_document("2025年年度报告", existing_kind="annual").selection_limit,
           "prospectus": route_document("首次公开发行股票并上市招股说明书", existing_kind="prospectus").selection_limit})
    check("OWNED-MARKER-PRESERVED", sha(marker) == marker_before, {"sha256": sha(marker)})
finally:
    if SCRATCH.resolve().parent != (CWP / ".tmp").resolve() or not SCRATCH.name.startswith("w04nov-review-"):
        raise RuntimeError("Refuse deletion outside unique owned test scratch")
    shutil.rmtree(SCRATCH)

check("FINAL-FREEZE-22-WIP-HEAD-INDEX-CONFIG", sha(FREEZE) == EXPECTED and inventory(frozen["products"]) == before
      and inventory(nonowned) == wip_before and git("rev-parse", "HEAD").decode().strip() == head_before
      and git("status", "--porcelain") == status_before and sha(git_index_path) == index_before
      and config_before == {str(p): metadata(p) for p in config_paths},
      {"freeze_sha256": sha(FREEZE), "head": head_before, "protected_wip_files": 22, "config_metadata_preserved": True})
check("SCRATCH-RESTORED-ABSENCE", not SCRATCH.exists(), {"initial_exists": False, "final_exists": SCRATCH.exists()})
passed = all(row["pass"] for row in rows)
report = {"schema_version": "w04-independent-novelty-engineering/1", "verdict": "PASS_WITH_SCOPE" if passed else "ENGINEERING_BLOCKER",
    "state": "FINAL_STOP", "freeze_sha256": EXPECTED, "engineering_only": True, "checks": len(rows),
    "passed": sum(r["pass"] for r in rows), "failed": [r["name"] for r in rows if not r["pass"]], "probes": rows,
    "seconds": round(time.monotonic()-started, 4), "calls": {"provider": 0, "network": 0, "LLM": 0}, "fees_usd": 0,
    "scratch": {"path": str(SCRATCH), "initial_exists": False, "final_exists": SCRATCH.exists()},
    "residual_scope": ["ROOT unchanged six-original recall including exact and honestly bound whole-group equivalents",
                       "Six 0.7.1 full ordered package fingerprints", "G2 summaries and downstream RF not evaluated"],
    "mutations": {"product": 0, "shared_PWF": 0, "git": 0, "config": 0},
    "findings": ["Protected full-context sentences conservatively disable penalty for changed facts; they are overlap hints, not proof of claim equivalence.",
                 "Engineering pass alone does not certify LPCVD/tungsten/supply/PRISMO real recall; missing real checkpoints must remain FAIL."],
}
(OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
md = f"""# W04 independent novelty engineering acceptance

**{report['verdict']} — {report['passed']}/{report['checks']} checks, {report['seconds']} seconds. FINAL_STOP.**

Read-only products: frozen six-file package {EXPECTED}. No author tests (365), six-original PDF replay, model, provider or network execution. Synthetic samples pass through the actual tokenizer, native whole-group signature and public finalizer, without manually invented overlap tokens.

Checks cover changed Chinese/Arabic/English quantities, decimals, percentages, ranges and units; different subjects and total-vs-type quantities; planned/ongoing/completed/negative stages; PRISMO new validation/chamber/wafer facts; short subset vs new longer content; numeric ownership rejoined at native paragraph 9/10 coordinates; format-only repeat positive; high symmetric overlap threshold; incomplete/unbound signatures; legacy/default and explicit 0.8 public entry; hard 96 span cap, whole groups and exact omitted partition; original annual96/IPO160 limits.

All six product SHA, 22 unrelated preexisting WIP files, HEAD, index, working-tree status and configured-file metadata were preserved. Unique short scratch was restored to initial absence. No product, Git, shared PWF or configuration edits.

## Boundary

This is **engineering-only** acceptance. ROOT still owns one unchanged real six-original replay, exact original-locator failures and honestly bound alternate whole-group facts, and six 0.7.1 complete ordered package fingerprints. No broad substring may replace LPCVD-specific quantity ownership; thin-film totals or another product's orders cannot certify it. PRISMO's later realized validation and new chambers/wafer dimensions must remain new facts. No cap increase or weakening of a failed real recall checkpoint is authorized by this report.

Full probe observations: `report.json`. Summary quality and downstream RF are not evaluated.
"""
(OUT / "report.md").write_text(md, encoding="utf-8")
files = [p for p in OUT.iterdir() if p.is_file() and p.name != "manifest.json"]
manifest = {"schema_version": "w04-independent-novelty-engineering-freeze/1", "state": "FINAL_STOP", "verdict": report["verdict"],
    "files": [{"path": p.name, "sha256": sha(p), "bytes": p.stat().st_size} for p in sorted(files)]}
(OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"verdict": report["verdict"], "checks": report["checks"], "failed": report["failed"],
                  "seconds": report["seconds"], "manifest_sha256": sha(OUT / "manifest.json")}, ensure_ascii=False))
raise SystemExit(0 if passed else 1)
