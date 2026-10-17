"""Independent data-delta and boundary audit; no original files or author scripts."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from company_wiki.document_understanding.profiles import get_profile, list_profiles, route_document
from company_wiki.document_understanding.profiles import registry
from company_wiki.document_understanding.profiles.geometry_policy import compile_geometry_policy, GeometryPolicyError
from fixtures.document_understanding_profiles.builders import observation, unit


def main():
    old = json.loads(subprocess.check_output(["git", "show", "8b7a46ac:src/company_wiki/document_understanding/profiles/reading_catalog.json"], cwd=ROOT))
    new = json.loads((ROOT / "src/company_wiki/document_understanding/profiles/reading_catalog.json").read_text(encoding="utf-8"))
    deltas = []
    def walk(a, b, at=""):
        if isinstance(a, dict) and isinstance(b, dict):
            for key in sorted(set(a) | set(b)):
                if key == "geometry_intent":
                    continue
                if key == "version" and at.startswith(("/families/", "/fallback")):
                    continue
                if key not in a or key not in b:
                    deltas.append(at + "/" + key)
                else:
                    walk(a[key], b[key], at + "/" + key)
        elif isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                deltas.append(at)
            else:
                for index, (left, right) in enumerate(zip(a, b)):
                    walk(left, right, at + "/" + str(index))
        elif a != b:
            deltas.append(at)
    walk(old, new)
    convertible_index = next(i for i, r in enumerate(new["families"]) if r["id"] == "offering_cn_convertible")
    expected_delta = [f"/families/{convertible_index}/sections/{i}/heading_path/0" for i in range(4)]
    assert sorted(deltas) == sorted(expected_delta), deltas
    families = []
    for record in new["families"] + [new["fallback"]]:
        sections = [dict(s, section_role=s["role"], family_id=record["id"], family_version=record["version"])
                    for s in record["sections"]]
        result = compile_geometry_policy({"section_rules": sections})
        assert len(result["rules"]) == len(record["sections"])
        assert all(r["family_id"] == record["id"] for r in result["rules"])
        families.append({"id": record["id"], "rules": len(sections),
                         "intents": [{"role": r["section_role"], **r["geometry_intent"]} for r in result["rules"]]})
    errors = []
    base = {"profile_id": "any", "section_rules": [{"section_role": "business"}]}
    for field, value, code in [("priority", 0, "GEOMETRY_POLICY_BAD_PRIORITY"),
                                ("priority", 1.0, "GEOMETRY_POLICY_BAD_PRIORITY"),
                                ("priority", False, "GEOMETRY_POLICY_BAD_PRIORITY"),
                                ("heading_path", [[], ["Business"]], "GEOMETRY_POLICY_BAD_PATH"),
                                ("heading_path", [[""]], "GEOMETRY_POLICY_BAD_PATH"),
                                ("heading_path", {"a": "b"}, "GEOMETRY_POLICY_BAD_PATH"),
                                ("aliases", [""], "GEOMETRY_POLICY_BAD_ALIASES"),
                                ("questions", "text", "GEOMETRY_POLICY_BAD_QUESTIONS"),
                                ("geometry_intent", {"discover": []}, "GEOMETRY_POLICY_BAD_INTENT"),
                                ("geometry_intent", {"fine": None}, "GEOMETRY_POLICY_BAD_INTENT"),
                                ("role", "risk", "GEOMETRY_POLICY_BAD_ROLE")]:
        data = deepcopy(base)
        data["section_rules"][0][field] = value
        try:
            compile_geometry_policy(data)
        except GeometryPolicyError as error:
            assert error.code == code, (field, error.code, code)
            errors.append({"field": field, "value": value, "code": error.code})
        else:
            raise AssertionError((field, value, "accepted malformed input"))
    sample = {"profile_id": "sample", "section_rules": [{"section_role": "business", "geometry_intent": {"fine": "on_candidate"}}],
              "policy_components": [{"kind": "family", "nested": {"a": ["keep"]}}]}
    before = deepcopy(sample)
    compiled = compile_geometry_policy(sample)
    compiled["policy_components"][0]["nested"]["a"].append("changed")
    assert sample == before
    assert compile_geometry_policy(sample)["rules"][0]["geometry_intent"] == {"discover": "unknown", "fine": "on_candidate", "demand_class": "unknown"}
    start = time.perf_counter()
    for _ in range(1000):
        compile_geometry_policy(sample)
    timing = time.perf_counter() - start
    report = {"agent": "/root/du9_policy_final_review", "status": "PASS",
              "data_deltas_other_than_intent_and_version": deltas,
              "families_and_fallback": families, "malformed_diagnostics": errors,
              "partial_intent_defaults_unknown": True, "component_copy_isolated": True,
              "finite_1000_compilations_seconds_observation_only": timing,
              "supplier_calls": 0, "original_copies": 0, "production_writes": 0}
    Path(sys.argv[1]).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "families_and_fallback"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
