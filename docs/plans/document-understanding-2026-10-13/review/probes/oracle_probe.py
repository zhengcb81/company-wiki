"""Read-only probes of recall membership; results are single checks, not full evaluation."""

import importlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
check = importlib.import_module("tools.document_understanding_benchmark.checkers").check_recall_fact
fact = {"id": "project", "importance": "critical", "any_support_sets": [[
    {"page": 12, "exact_quote": "项目甲"}, {"page": 12, "exact_quote": "建设期两年"}]],
    "must_preserve": [], "must_not_assert": []}
cases = {
    "ungrounded_text": {"selected_locators": [], "selected_text": "项目甲 建设期两年",
                        "coverage": {"native_scan": "complete"}},
    "different_page_claims": {"selected_locators": ["page:80:unrelated"], "selected_text": "",
                              "claims": [{"text": text, "evidence_locators": ["page:80:unrelated"]}
                                         for text in ("项目甲", "建设期两年")],
                              "coverage": {"native_scan": "complete"}},
}
rows = [{"case": name, "result": check(fact, value)} for name, value in cases.items()]
alternative = {"id": "equivalent", "importance": "critical", "any_support_sets": [
    [{"page": 1, "exact_quote": "目标甲"}], [{"page": 2, "exact_quote": "目标甲"}]],
    "must_preserve": [], "must_not_assert": []}
rows.append({"case": "one_valid_alternative", "result": check(alternative, {
    "selected_locators": ["page:2"], "selected_text": "目标甲",
    "coverage": {"native_scan": "partial", "opaque_pages": [1]}})})
print(json.dumps(rows, ensure_ascii=False, indent=2))
