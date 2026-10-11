"""Only three scope-corrected positive controls; do not rerun the 28 probes."""
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
FREEZE = TREE / ".planning/w04-root-novelty-recall/product-freeze.json"
EXPECTED = "b17fafe79199ccc2091356de1e2a012becfa6dd001a7d4a541b30b471a60a6db"
AMEND = TREE / "docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w04_post_pw03_common_roots_2026-10-11/WP02_SELECTOR_INTERFACE_AMENDMENT.md"
SCRATCH = CWP / ".tmp" / ("w04nov-review-" + uuid.uuid4().hex[:10])

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding="utf-8"))
def git(*args): return subprocess.run(["git", "-C", str(TREE), *args], capture_output=True, check=True).stdout
def configmeta():
    output = {}
    for root in (TREE, CWP):
        for name in ("source_catalog.yaml", "source_acquisition.yaml"):
            p = root / "config" / name
            output[str(p)] = (p.exists(), p.stat().st_size if p.exists() else None, p.stat().st_mtime_ns if p.exists() else None)
    return output

if (OUT / "scope-controls.json").exists() or SCRATCH.exists(): raise RuntimeError("Fresh correction only")
initial = read(OUT / "report.json")
assert initial["passed"] == 27 and initial["checks"] == 28 and initial["failed"] == ["LEGACY-DEFAULT-AND-080-OPTIN"]
frozen = read(FREEZE)
protected = tuple(frozen["products"]) + tuple(frozen["preserved_initial_non_owned_sha256"])
before = {p: sha(TREE / p) for p in protected}
head = git("rev-parse", "HEAD")
status = git("status", "--porcelain")
config = configmeta()
index_path = Path(git("rev-parse", "--git-path", "index").decode().strip())
if not index_path.is_absolute(): index_path = TREE / index_path
index_sha = sha(index_path)
assert sha(FREEZE) == EXPECTED

sys.path.insert(0, str(TREE / "src"))
from company_wiki.source_catalog import narrative_evidence as policy
from company_wiki.source_catalog import narrative_finalize as finalizer
from company_wiki.source_catalog.narrative_budget import BudgetItem, select_budget_items
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_candidates import EvidenceCandidate
from company_wiki.source_catalog.narrative_routing import route_document
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256
from company_wiki.automation.narrative_selector_binding import bind_narrative_selector

fixture = TREE / "tests/fixtures/narrative_real_transcript/MSFT_Q4_2026_earnings_call.txt"
fixture_sha = "4ac3b4f0fa1be928b56b4ef9775cac694a1712d46785bb1fa28d2a6a68d7852a"
assert sha(fixture) == fixture_sha
parsed = policy.parse_transcript_text(fixture.read_text(encoding="utf-8"), source_id=source_id_for_sha256(fixture_sha),
    source_sha256=fixture_sha, language="en", parser_version="0.3.1")
seen = []
original_finalize = policy.finalize_selection
def observe(*args, **kwargs):
    seen.append(kwargs["budget_policy"])
    return original_finalize(*args, **kwargs)

def fingerprint(package):
    data = {"fixture_sha256": fixture_sha, "document_kind": package.document_kind, "status": package.status,
        "selection_limit": package.selection_limit, "candidate_count": package.candidate_count,
        "dropped_financial_count": package.dropped_financial_count, "source_units": package.source_units,
        "omitted_candidate_count": package.omitted_candidate_count, "coverage_complete": package.coverage_complete,
        "spans": [span.to_dict() for span in package.evidence_spans]}
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

started = time.monotonic()
SCRATCH.mkdir(parents=True)
controls = []
try:
    with patch.object(policy, "finalize_selection", observe):
        default = policy.select_narrative_evidence(parsed, title=fixture.name, existing_kind="investor_call_transcript")
        current = policy.select_narrative_evidence(parsed, title=fixture.name, existing_kind="investor_call_transcript", selector_version="0.8.0")
        old = policy.select_narrative_evidence(parsed, title=fixture.name, existing_kind="investor_call_transcript", selector_version="0.7.1")
    bound = bind_narrative_selector()
    with patch.object(policy, "NARRATIVE_SELECTOR_VERSION", "0.7.1"):
        bound_result = bound(parsed, title=fixture.name, existing_kind="investor_call_transcript")
    controls.append({"name": "PUBLIC-DEFAULT-080-AND-BOUND-ONCE", "pass": default == current
        and bound.selector_version == "0.8.0" and bind_narrative_selector(bound) is bound and bound_result == current
        and seen[:2] == ["semantic_coverage/1", "semantic_coverage/1"],
        "actual": {"default_version": policy.NARRATIVE_SELECTOR_VERSION, "bound_version": bound.selector_version,
            "public_routes": seen[:2], "binding_retained_under_default_drift": bound_result == current}})
    golden = "c5e498acbb5d5c158a030b6e4d3bcec3713f408f2c49baa85717b3d63b905478"
    controls.append({"name": "EXPLICIT-071-ARCHIVED-FULL-FINGERPRINT-AND-LEGACY-ROUTE", "pass": fingerprint(old) == golden and seen[2] == "legacy",
        "actual": {"expected_full_ordered_sha256": golden, "actual_full_ordered_sha256": fingerprint(old), "route": seen[2],
            "scope": "one existing archived TXT fixture; not ROOT real six-original replay"}})
    source_sha = "e" * 64
    candidates = tuple(EvidenceCandidate(policy._make_unit(source_id=source_id_for_sha256(source_sha), parser_version="0.1.1",
        coordinates=EvidenceCoordinates(page_number=page, paragraph_index=0), raw_text=f"设备{page}已交付{page+3}反应台。",
        unit_kind="pdf_text_block", source_role="company_filing", language="zh", metadata={}, quality_flags=()),
        ("products_rd",), ("new_product_commercialization_milestone",), 30-page) for page in (1, 2, 3))
    structure = DocumentStructure(source_id=source_id_for_sha256(source_sha), source_sha256=source_sha, language="zh",
        units=tuple(c.unit for c in candidates), page_count=3, pages_read=3)
    route = replace(route_document("年度报告", existing_kind="annual"), selection_limit=2)
    kwargs = dict(group_ids={c.unit.unit_id: c.unit.unit_id for c in candidates}, heading_pattern=re.compile(r"(?!)"), dropped_financial_count=0)
    implicit = finalizer.finalize_selection(structure, route, candidates, **kwargs)
    explicit = finalizer.finalize_selection(structure, route, candidates, budget_policy="legacy", **kwargs)
    items = tuple(BudgetItem(item_id=str(i), group_id=None, page_key=("page", 1 if i < 2 else 2), locator=str(i), order_key=(i,),
        reasons=("specific_business_event",), score=20 if i == 0 else 10, is_heading=False, payload=None) for i in range(3))
    controls.append({"name": "DIRECT-FINALIZER-AND-BUDGET-DEFAULT-LEGACY", "pass": implicit == explicit
        and select_budget_items(items, limit=2) == select_budget_items(items, limit=2, policy="legacy"),
        "actual": {"finalizer_default_equals_explicit_legacy": implicit == explicit,
            "budget_default_equals_explicit_legacy": select_budget_items(items, limit=2) == select_budget_items(items, limit=2, policy="legacy")}})
finally:
    if SCRATCH.resolve().parent != (CWP / ".tmp").resolve() or not SCRATCH.name.startswith("w04nov-review-"):
        raise RuntimeError("Refuse scratch removal outside owned short prefix")
    shutil.rmtree(SCRATCH)

preserved = before == {p: sha(TREE / p) for p in protected} and sha(FREEZE) == EXPECTED
preserved = preserved and head == git("rev-parse", "HEAD") and status == git("status", "--porcelain")
preserved = preserved and config == configmeta() and index_sha == sha(index_path) and sha(fixture) == fixture_sha and not SCRATCH.exists()
assert preserved
supplement = {"schema_version": "w04-independent-scope-positive-controls/1", "controls": controls,
    "freeze_sha256": EXPECTED, "preserved_six_products_22_WIP_HEAD_index_config": preserved,
    "interface_amendment": str(AMEND), "interface_amendment_sha256": sha(AMEND), "seconds": round(time.monotonic()-started, 4),
    "scratch_initial_exists": False, "scratch_final_exists": SCRATCH.exists(), "calls": {"provider": 0, "network": 0, "LLM": 0}, "fees_usd": 0,
    "scope_correction": "Earlier ROOT plan said 0.8 opt-in; preexisting formal WP02 interface explicitly makes public selector default0.8 without permissions. Only direct finalizer/budget defaultlegacy.",
    "root_real_recall_state": "Three core real-recall gaps retained FAIL by ROOT; not evaluated or fixed here"}
(OUT / "scope-controls.json").write_text(json.dumps(supplement, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
for name in ("report.json", "report.md", "manifest.json"):
    (OUT / name).rename(OUT / ("initial-27-of-28-" + name))
report = dict(initial)
report["initial_attempt"] = {"report": "initial-27-of-28-report.json", "sha256": sha(OUT / "initial-27-of-28-report.json"),
    "passed": 27, "checked": 28, "superseded_scope_assertion": initial["failed"]}
report["probes"] = [r for r in initial["probes"] if r["pass"]] + controls
report["checks"] = len(report["probes"])
report["passed"] = sum(r["pass"] for r in report["probes"])
report["failed"] = [r["name"] for r in report["probes"] if not r["pass"]]
report["verdict"] = "PASS_WITH_SCOPE" if not report["failed"] else "ENGINEERING_BLOCKER"
report["scope_correction"] = supplement["scope_correction"]
report["supplement"] = "scope-controls.json"
report["supplement_seconds"] = supplement["seconds"]
report["residual_scope"].append(supplement["root_real_recall_state"])
(OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
md = f"""# W04 independent novelty engineering acceptance

**{report['verdict']} — 27 original valid checks + {sum(c['pass'] for c in controls)}/3 scope-corrected positive controls. FINAL_STOP.**

Initial 27/28 short group is retained in `initial-27-of-28-report.json/md/manifest.json`; it is not hidden or rerun. Its single failed assertion followed ROOT's mistaken “0.8 opt-in” scope wording. The prior formal `WP02_SELECTOR_INTERFACE_AMENDMENT.md` explicitly sets public selector default **0.8.0 without user opt-in or permission**. Its 0.7.1 explicit replay remains available. Direct finalizer and budget retain **default legacy**. No product change was needed for this correction.

Only three supplemental positive controls ran: public default equals explicit0.8 and an already-bound selector remains pinned through default drift; explicit0.7.1 retains the archived TXT fixture's complete ordered SHA `{golden}` and legacy algorithm route; direct finalizer/budget default equals explicitlegacy. Full observations: `scope-controls.json`. Original engineering probes covered actual tokenizer → native complete-group signature → public finalizer, quantitative/subject/stage/polarity novelty, honest PRISMO progress, conservative high symmetric repeat, bounded metadata, actual whole-group span costs, annual96/IPO160 limits and omitted partition.

Six-product freeze **{EXPECTED}**, 22 unrelated WIP files, HEAD/index/status/config metadata and archived TXT fixture bytes were preserved. Both uniquely owned short scratch directories were restored to absence. Zero provider/network/LLM calls and $0. No products, Git, shared PWF or configuration were edited.

## Boundary

**Engineering only.** ROOT's real six-original replay already retains three core recall gaps as FAIL and is outside this acceptance. This report does not clear those failures, certify six old0.7.1 full-package fingerprints, summarize documents or accept downstream RF. LPCVD quantity/subject ownership and realized stages must be demonstrated by honestly bound whole original groups; thin-film totals, other models' quantities, cross-group substrings or plans cannot substitute for them. No cap increase or weakened checkpoint is justified by engineering PASS.
"""
(OUT / "report.md").write_text(md, encoding="utf-8")
manifest = {"schema_version": "w04-independent-novelty-engineering-freeze/1", "state": "FINAL_STOP", "verdict": report["verdict"],
    "files": [{"path": p.name, "sha256": sha(p), "bytes": p.stat().st_size} for p in sorted(OUT.iterdir()) if p.is_file() and p.name != "manifest.json"]}
(OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"verdict": report["verdict"], "controls": len(controls), "failed": report["failed"],
                  "manifest_sha256": sha(OUT / "manifest.json"), "supplement_seconds": supplement["seconds"]}, ensure_ascii=False))
raise SystemExit(0 if not report["failed"] else 1)
