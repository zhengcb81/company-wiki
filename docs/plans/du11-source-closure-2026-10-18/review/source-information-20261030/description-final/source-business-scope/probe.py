"""Independent M2 source-scope probe; no PDF, provider or production writes."""
from __future__ import annotations
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from company_wiki.document_understanding.operating_states import assertion_roles as current
from company_wiki.source_catalog.narrative_business_disclosures import reading_material_value
from company_wiki.source_catalog.narrative_business_policy import detect_business_fact
from unit.du11_production.test_source_information_binding import session_for, unit_id, observed_use

baseline = types.ModuleType("company_wiki.document_understanding.operating_states._m2_baseline")
baseline.__package__ = "company_wiki.document_understanding.operating_states"
sys.modules[baseline.__name__] = baseline
exec(subprocess.check_output([
    "git", "show", "6894f5ee21f4c883c7c4376984c962a88f0ed076:src/company_wiki/document_understanding/operating_states/assertion_roles.py"
], cwd=ROOT, text=True, encoding="utf-8"), baseline.__dict__)

CASES = [
    ("accounting_cn", "本公司已开发80项会计政策。", "non_operating_control"),
    ("accounting_en", "We have developed over 80 accounting policies.", "non_operating_control"),
    ("template_developed_en", "The template says: we have developed over 80 diagnostic assays.", "template_control"),
    ("template_developed_cn", "流程要求：公司已开发超过80种检测试剂时应填报本表。", "template_control"),
    ("question", "请问公司已开发超过80种检测试剂吗？", "question_control"),
    ("conditional", "如果公司已开发80种检测试剂，则申请专项补贴。", "modality_observation_not_actuality_test"),
    ("negative", "公司并未确认已开发超过80种检测试剂。", "negation_observation_not_zero_fact_test"),
    ("developed_actual", "本公司已开发超过80种检测试剂。", "positive"),
    ("developed_wrong_count_unit", "本公司已开发80吨检测试剂。", "count_grammar_control"),
    ("sold_future", "公司未来拟销售的产品主要为试剂和耗材。", "prospective_control"),
    ("sold_negative", "公司未曾销售的产品主要为试剂和耗材。", "negative_scope_control"),
    ("template_sold", "填报示例：公司已销售的产品主要为试剂和耗材。", "template_control"),
    ("target_customer", "Our target customers include hospitals and laboratories.", "prospective_control"),
    ("modified_future_customer", "Our future major customers include hospitals and laboratories.", "prospective_control"),
    ("template_customer", "模板示例：客户包括医院和实验室。", "template_control"),
    ("foreign_subject", "客户已开发80种检测试剂，本公司尚未开发相关产品。", "attribution_observation_not_issuer_fact_test"),
    ("software_governing_policy_tools", "Our software provides accounting policy management tools.", "positive_function_regression_control"),
    ("software_governing_policy_identification", "Our software identifies accounting policies and automates compliance.", "positive_function_regression_control"),
    ("policy_software_product", "Our products include accounting policy management software.", "positive_function_regression_control"),
]
capture = ROOT / ".planning/source-description-20261030/real-summary-v3/materials"
req = json.loads(gzip.open(next(capture.glob("*.input.json.gz")), "rt", encoding="utf-8").read())
payload = json.loads(req["messages"][1]["content"])
for task in payload["material"]["tasks"]:
    if task["key"] in {"t3", "t7"}:
        CASES.append(("captured_" + task["key"], task["parts"][-1]["text"], "real_capture_positive"))


def inspect_case(name, text, kind):
    new = current.prepare_source_assertions(text)
    old = baseline.prepare_source_assertions(text)
    session, budget = session_for([text])
    roles = session.source_assertions(unit_id(0))
    fact = session.fact(unit_id(0))
    use = observed_use(session, unit_id(0))
    relations = session.relations(unit_id(0))
    used = budget.used
    session.source_assertions(unit_id(0))
    session.fact(unit_id(0))
    cached_delta = budget.used - used
    value = current.matching_reading_text(text)
    details = []
    for clause in current._source_clauses(value, descriptions=False):
        for part in current._source_clauses(clause):
            details.append({
                "part": part,
                "compositions": [{**m.groupdict(), "closed": current._argument_closed(part, m.end("target"))}
                                 for m in current._COMPOSITION_CN.finditer(part)],
                "developed": [{**m.groupdict(), "closed": current._argument_closed(part, m.end())}
                              for m in current._DEVELOPED_SCOPE.finditer(part)],
            })
    return {
        "name": name, "kind": kind, "text": text,
        "before_material": any(c.material_payload for c in old.clauses),
        "after_material": any(c.material_payload for c in new.clauses),
        "before_event_helper": baseline.descriptive_operating_relation(text, include_source_descriptions=False),
        "after_event_helper": current.descriptive_operating_relation(text, include_source_descriptions=False),
        "legacy_detect_business_eligible": detect_business_fact(text).eligible,
        "reading_band": reading_material_value(fact, source_roles=roles),
        "reading_eligible": fact.eligible, "purpose": fact.purpose,
        "source_use": use, "relations": relations["relations"],
        "cached_observation_extra_work": cached_delta,
        "roles": [{"text": c.text, "independent_payload": c.independent_payload,
                   "material_payload": c.material_payload, "function_or_event": c.function_or_event,
                   "rule_purpose": c.rule_purpose} for c in new.clauses],
        "local_match_details": details,
    }


if __name__ == "__main__":
    product = ROOT / "src/company_wiki/document_understanding/operating_states/assertion_roles.py"
    result = {
        "schema_version": "independent-source-scope-probe/1",
        "baseline": "6894f5ee21f4c883c7c4376984c962a88f0ed076",
        "source_description_scan_passes": current.SOURCE_DESCRIPTION_SCAN_PASSES,
        "product_sha256": hashlib.sha256(product.read_bytes()).hexdigest(),
        "no_paid_no_pdf_parse": True,
        "cases": [inspect_case(*case) for case in CASES],
    }
    destination = Path(__file__).parent / "probe-result.json"
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for row in result["cases"]:
        print(row["name"], row["before_material"], "->", row["after_material"],
              row["reading_band"], row["source_use"][0],
              "event", row["before_event_helper"], "->", row["after_event_helper"])
