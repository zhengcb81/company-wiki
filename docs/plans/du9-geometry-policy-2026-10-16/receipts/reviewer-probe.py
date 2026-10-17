"""Independent finite read-only source probes; only the requested receipt is written."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from company_wiki.document_understanding.profiles import get_profile, route_document
from company_wiki.document_understanding.profiles import registry
from company_wiki.document_understanding.profiles.geometry_policy import compile_geometry_policy
from fixtures.document_understanding_profiles.builders import observation, unit


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def resolve(data):
    route = route_document(data)
    profile = registry.resolve_reading_profile(get_profile(route["profile_id"]), data, route)
    return route, profile, compile_geometry_policy(profile)


def main():
    rows = []
    data = observation([unit("cover", 0, "FORM 10-Q", kind="heading"),
                        unit("body", 1, "Management Discussion and Analysis")],
                       title="FORM 10-Q", form_type="10-Q", regime="sec", declared_kind="quarterly_report")
    original = deepcopy(registry._CATALOG)
    for field in ("aliases", "heading_path", "questions"):
        try:
            before = digest(registry._CATALOG)
            _, profile, _ = resolve(data)
            if field == "heading_path":
                profile["section_rules"][0][field][0].append("INDEPENDENT_MUTATION")
            else:
                profile["section_rules"][0][field].append("INDEPENDENT_MUTATION")
            after = digest(registry._CATALOG)
            _, fresh, _ = resolve(data)
            leaked = "INDEPENDENT_MUTATION" in json.dumps(fresh["section_rules"])
            rows.append({"check": "resolved_nested_isolation_" + field,
                         "expected": "catalog unchanged and later resolved profile unaffected",
                         "catalog_changed": before != after, "next_profile_affected": leaked,
                         "pass": before == after and not leaked})
        finally:
            registry._CATALOG = deepcopy(original)
    ir = observation([unit("cover", 0, "投资者关系活动记录表", kind="heading"),
                      unit("body", 1, "经营情况 Business Review")],
                     title="投资者关系活动记录表", regime="cn_exchange", declared_kind="investor_relations")
    route, profile, policy = resolve(ir)
    after_fix = "--after-fix" in sys.argv
    rows.append({"check": "weak_declared_ir_conservatively_unknown" if after_fix else "declared_ir_roundtrip_family", "route_profile": route["profile_id"],
                 "actual_family": profile["family_policy"]["id"],
                 "component_ids": [r["id"] for r in policy["policy_components"]],
                 "expected": "Weak title-only evidence stays unknown" if after_fix else "IR-labeled test must resolve investor_qa_record to count as its coverage",
                 "pass": profile["family_policy"]["id"] == (None if after_fix else "investor_qa_record")})
    if after_fix:
        rich_ir = observation([unit("ir0", 0, "投资者关系活动记录表", kind="heading"),
                               unit("ir1", 1, "问：新产品出海进度如何？"),
                               unit("ir2", 2, "答：公司正开展海外客户认证，尚未披露确认收入。"),
                               unit("ir3", 3, "问：产能和订单情况如何？"),
                               unit("ir4", 4, "答：二期工程建设中，客户订单按实际验收确认收入。")],
                              title="投资者关系活动记录表", regime="cn_exchange", declared_kind="investor_relations")
        _, rich_profile, rich_policy = resolve(rich_ir)
        rows.append({"check": "independent_rich_ir_actual_family", "actual_family": rich_profile["family_policy"]["id"],
                     "component_ids": [r["id"] for r in rich_policy["policy_components"]],
                     "pass": rich_profile["family_policy"]["id"] == "investor_qa_record"})
    output = {"reviewer_agent_id": "/root/du9_policy_final_review", "checks": rows,
              "supplier_calls": 0, "original_reads": 0, "production_writes": 0,
              "catalog_restored_in_memory": registry._CATALOG == original}
    Path(sys.argv[1]).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return int(any(not row["pass"] for row in rows))


if __name__ == "__main__":
    raise SystemExit(main())
