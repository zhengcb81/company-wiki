"""Independent bounded coverage diagnostic semantic-equivalence probes."""
import ast
from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
import random
import subprocess
import types
from types import SimpleNamespace
from typing import Any

from company_wiki.document_understanding import structure
from company_wiki.resource_budget import WorkBudget, WorkBudgetExceeded

root = Path(__file__).resolve().parents[3]
path = "src/company_wiki/document_understanding/structure/__init__.py"
source = subprocess.check_output(["git", "show", "HEAD:" + path], cwd=root).decode("utf-8")
definition = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == "_coverage_diagnostics")
old_globals = {"Mapping": Mapping, "Any": Any}
exec(compile(ast.Module(body=[definition], type_ignores=[]), "<baseline coverage>", "exec"), old_globals)
baseline = old_globals["_coverage_diagnostics"]
legacy_structure = types.ModuleType("company_wiki.document_understanding.structure._coverage_review_baseline")
legacy_structure.__package__ = structure.__name__
exec(compile(source, "<baseline structure>", "exec"), legacy_structure.__dict__)
rng = random.Random(20261026)
for i in range(500):
    units = [SimpleNamespace(unit_id=f"u{j}", page=rng.choice([None, 0, 1, 2, 3, 4])) for j in range(rng.randrange(70))]
    coverage = {"opaque_pages": [rng.randrange(8) for _ in range(rng.randrange(12))],
                "deferred_pages": [rng.randrange(8) for _ in range(rng.randrange(12))],
                "native_scan": rng.choice(["complete", "partial", "unavailable"])}
    budget = WorkBudget(100_000)
    actual = structure._coverage_diagnostics({}, coverage, units, work_budget=budget)
    assert actual == baseline({}, coverage, units), i

class Unpaid(list):
    def __iter__(self):
        raise AssertionError("unpaid source iteration")

budget = WorkBudget(0)
try:
    structure._coverage_diagnostics({}, {"opaque_pages": [1], "deferred_pages": [], "native_scan": "partial"}, Unpaid([None]), work_budget=budget)
except WorkBudgetExceeded:
    pass
else:
    raise AssertionError("zero budget did not stop diagnostic work")
assert budget.used == 0 and budget.exhausted

units = [SimpleNamespace(unit_id="u0", page=1)]
duplicate = structure._coverage_diagnostics({}, {"opaque_pages": [1, 1], "native_scan": "complete"}, units)
duplicate[0]["unit_ids"].append("local mutation")
assert duplicate[1]["unit_ids"] == ["u0"]
for case in range(24):
    count = 3 + case
    observation = {"schema_version": "du-input/1", "source_ref": {"source_id": "s", "source_sha256": "a"*64},
                   "metadata": {}, "coverage": {"native_scan": ["complete", "partial", "unavailable"][case%3],
                     "opaque_pages": [1, 1, 999] if case%2 else [], "deferred_pages": [2, 999] if case%4 else []},
                   "units": [{"unit_id": f"u{i}", "ordinal": i, "locator": f"loc:{i}", "page": i%3,
                              "text": "Business" if i == 0 else "During the period we launched a product.",
                              "kind": "heading" if i == 0 else "paragraph", "role": "company_filing", "language": "en",
                              "layout": {}, "hints": {"heading_level": 1} if i == 0 else {}} for i in range(count)]}
    expected = legacy_structure.build_structure(observation, work_budget=WorkBudget(2_000_000))
    actual = structure.build_structure(observation, work_budget=WorkBudget(2_000_000))
    assert actual == expected, case
result = {"baseline_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root).decode().strip(),
          "source_sha256": hashlib.sha256((root / path).read_bytes()).hexdigest(),
          "diagnostic_differential_cases": 500, "zero_budget_no_iteration": "PASS",
          "full_structure_differential_cases": 24,
          "duplicate_output_lists_independent": "PASS", "downloads": 0, "paid_calls": 0}
Path(__file__).with_name("coverage-results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
