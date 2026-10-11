"""Prepare the frozen real-data checkpoint before observing new selection."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
TREE = Path('C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/company-wiki')
PLAN = ROOT / '.planning/w04-root-novelty-recall'
target = PLAN / 'native_novelty_replay.py'
assert not target.exists(), 'Do not overwrite a prior acceptance checkpoint'
source = (TREE / '.planning/w04-root-selector-recall/native_assertion_replay.py').read_text(encoding='utf-8')
source = source.replace('import sys, json, hashlib, gzip, dataclasses, datetime, time',
                        'import sys, json, hashlib, gzip, dataclasses, datetime, time, re')
source = source.replace('OUT=ROOT/".planning/w04-root-selector-recall"',
                       'OUT=Path(__file__).resolve().parent')
source = source.replace('"native-budget-six"', '"native-novelty-six"')
source = source.replace('Path("src/company_wiki/source_catalog/narrative_budget.py"),',
                       'Path("src/company_wiki/source_catalog/narrative_semantic_coverage.py"),Path("src/company_wiki/source_catalog/narrative_budget.py"),')
source = source.replace('return unit.coordinates.page_number in source.get("focus_pages",[])',
                       'return (key == "cn-annual" and unit.coordinates.page_number == 56) or unit.coordinates.page_number in source.get("focus_pages",[])')
needle = '    previous=frozen_semantic.get(key,source)'
assert source.count(needle) == 1
source = source.replace(needle, '''    complete_selected_groups = []
    for bundle in bundles:
        ordered = sorted(bundle.items, key=lambda item: item.order_key)
        if all(item.locator in chosen for item in ordered):
            text = "".join(units[item.locator].raw_text for item in ordered)
            complete_selected_groups.append({"group_id": bundle.key,
                "locators": [item.locator for item in ordered], "raw_text": text,
                "raw_text_sha256": H(text.encode()), "span_cost": len(ordered)})
''' + needle)
source = source.replace('"focus_decisions":decisions,',
                       '"complete_selected_groups":complete_selected_groups,"focus_decisions":decisions,')
start = source.index('result["status"] = ("FAIL_LEGACY"')
end = source.index('result["scratch_restore"]', start)
source = source[:start] + '''# Fixed, subject-bound checks on one complete native-order group. No
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
        compact = re.sub(r"\\s+", "", group["raw_text"])
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
''' + source[end:]
source = source.replace('json.dumps(result["critical_business_recall"])',
                       'json.dumps({name: row["complete"] for name, row in result["bound_fact_recall"].items()})')
target.write_text(source, encoding='utf-8')
record = {
    'schema': 'root-w04-fixed-native-checkpoints/1',
    'script_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
    'policy': 'same six originals and 0.7.1 full ordered package hash; same 96/160 caps; complete groups only',
    'before_result': True,
    'no_new_result_observed': True,
    'extra_fact_source': 'Annual page 56 raw PDF text read before replay; PRISMO PD5, not UniMax or aggregate MOCVD',
    'original_failure_preserved': '.planning/w04-root-selector-recall/native-budget-six-assertion-closure.json.gz',
}
(PLAN / 'native-checkpoints.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(record, ensure_ascii=False))
