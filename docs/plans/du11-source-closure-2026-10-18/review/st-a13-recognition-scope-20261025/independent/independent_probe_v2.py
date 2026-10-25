"""Independent neutral negative controls; no product writes or network."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import sys
from time import perf_counter

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
HERE = Path(__file__).resolve().parent
SOURCE_FILES = (
    "src/company_wiki/source_catalog/narrative_recognition_scope.py",
    "src/company_wiki/source_catalog/narrative_business_policy.py",
    "src/company_wiki/document_understanding/decision_inventory.py",
    "src/company_wiki/source_catalog/narrative_operating_relations.py",
    "tests/unit/document_understanding_selection/test_reading_recognition_scope.py",
)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    if len(sys.argv) != 2 or not sys.argv[1].replace("-", "").isalnum():
        raise SystemExit("usage: independent_probe.py NEW-REPORT-STEM")
    output = HERE / (sys.argv[1] + ".json")
    if output.exists():
        raise FileExistsError(output)
    before = {p: digest(ROOT / p) for p in SOURCE_FILES}
    from company_wiki.document_understanding import decision_inventory as inventory
    from company_wiki.source_catalog import narrative_recognition_scope as scope
    from company_wiki.source_catalog.narrative_business_policy import detect_reading_business_fact
    cases = [
        ("comma-other-owner-cn", False, "本集团的设备维护服务的客户在本集团履约时取得并消耗利益，而供应商的检测业务属于在某一时段内履行的履约义务。"),
        ("comma-other-owner-cn-without-conjunction", False, "本集团的设备维护服务的客户在本集团履约时取得并消耗利益，供应商的检测业务属于在某一时段内履行的履约义务。"),
        ("comma-other-owner-en", False, "Our instrument services are performance obligations, whereas the supplier's testing services are performance obligations satisfied over time."),
        ("same-owner-explicit-comma-reference", True, "本集团的设备维护服务的客户在本集团履约时取得并消耗利益，因此上述业务属于在某一时段内履行的履约义务。"),
        ("named-cn", True, "本公司的检测服务属于在某一时段内履行的履约义务。"),
        ("named-en", True, "Our instrument maintenance services are performance obligations satisfied over time because customers consume the benefits."),
        ("explicit-conditional-reference", True, "本公司的设备维护服务的客户在本公司履约时取得并消耗利益；或者客户控制履约形成的资产，因此上述业务属于在某一时段内履行的履约义务。"),
        ("customer-owned", False, "本集团客户的设备维护服务属于在某一时段内履行的履约义务。"),
        ("supplier-owned", False, "本集团供应商的设备维护服务属于在某一时段内履行的履约义务。"),
        ("customer-owned-explicit-possession", False, "本公司的客户的仪器校准服务属于在某一时段内履行的履约义务。"),
        ("different-owner-before-back-reference", False, "本集团的设备维护服务的客户在本集团履约时取得并消耗利益；供应商的检测业务适用另一合同安排，因此上述业务属于在某一时段内履行的履约义务。"),
        ("different-business-before-back-reference", False, "本集团的设备维护服务的客户在本集团履约时取得并消耗利益；本集团其他业务单独履约，因此上述业务属于在某一时段内履行的履约义务。"),
        ("generic-primary-cn", False, "本集团的主营业务属于在某一时段内履行的履约义务。"),
        ("generic-core-cn", False, "本集团的核心业务属于在某一时段内履行的履约义务。"),
        ("generic-core-en", False, "Our core services are performance obligations satisfied over time."),
        ("generic-other-cn", False, "本集团的其他业务属于在某一时段内履行的履约义务。"),
        ("supplier-direct", False, "供应商的仪器维护服务属于在某一时段内履行的履约义务。"),
        ("separate-sentence", False, "本集团的设备维护服务正在增长。其他业务属于在某一时段内履行的履约义务。"),
        ("negative-rule", False, "本集团的设备维护服务不属于在某一时段内履行的履约义务。"),
    ]
    results = []
    for name, expected, text in cases:
        actual = scope.named_recognition_scope(text)
        fact = detect_reading_business_fact(text)
        tagged = "business_recognition_scope" in fact.topics
        results.append({"name": name, "text": text, "expected": expected,
                        "helper_actual": actual, "production_tag_actual": tagged,
                        "pass": actual == expected and tagged == expected})
    helper = Path(scope.__file__).resolve()
    real_read = Path.read_bytes
    versions = inventory._versions()
    with patch.object(Path, "read_bytes", lambda path: real_read(path) + (
            b"\n# Independent simulated implementation mutation\n" if path.resolve() == helper else b"")):
        changed = inventory._versions()
    cache_changed = versions["business_algorithms"] != changed["business_algorithms"]
    scan_rows = []
    reference = getattr(scope, "_CN_RULE_REFERENCE", None)
    for count in (10, 20, 40, 80):
        text = "本集团的其他业务的客户在本集团履约时取得并消耗利益；" * count + "本集团其他业务属于在某一时段内履行的履约义务。"
        class Counter:
            calls = 0
            chars = 0
            def search(self, value):
                self.calls += 1
                self.chars += len(value)
                return reference.search(value)
        counter = Counter()
        start = perf_counter()
        if reference is not None:
            with patch.object(scope, "_CN_RULE_REFERENCE", counter):
                actual = scope.named_recognition_scope(text)
        else:
            actual = scope.named_recognition_scope(text)
        scan_rows.append({"count": count, "input_chars": len(text), "result": actual,
                          "reference_regex_present": reference is not None,
                          "reference_calls": counter.calls, "reference_scan_chars": counter.chars,
                          "declared_helper_work": scope.READING_RECOGNITION_SCOPE_SCAN_PASSES * len(text),
                          "seconds_observed_not_gate": perf_counter() - start})
    after = {p: digest(ROOT / p) for p in SOURCE_FILES}
    report = {"schema_version": "recognition-scope-independent-probes/1",
              "source_sha256": before, "source_stable": before == after,
              "cases": results, "case_pass_count": sum(x["pass"] for x in results),
              "case_total": len(results),
              "helper_only_byte_change_invalidates_cache": cache_changed,
              "scan_probe": scan_rows, "external_calls": 0, "downloads": 0}
    with output.open("x", encoding="utf8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"output": str(output), "case_pass": report["case_pass_count"],
                      "case_total": len(results), "cache_invalidates": cache_changed,
                      "source_stable": before == after}, ensure_ascii=False))
    return 0 if all(x["pass"] for x in results) and cache_changed and before == after else 1

if __name__ == "__main__":
    raise SystemExit(main())
