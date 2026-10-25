"""Independent bounded CF3 differential and scope probes; no source mutations."""
import hashlib
import json
import random
import subprocess
import tempfile
import types
from pathlib import Path

from company_wiki.document_understanding.structure import relations as current
from company_wiki.document_understanding.structure.contract import ObservationUnit
from company_wiki.document_understanding.structure.layout import Ordering
from company_wiki.document_understanding.layout_hints.contract import WorkBudget
from company_wiki.document_understanding import decision_inventory

ROOT = Path(__file__).resolve().parents[3]
FILES = ["src/company_wiki/document_understanding/structure/relations.py",
         "src/company_wiki/document_understanding/decision_inventory.py",
         "tests/unit/test_cf3_relation_work.py", "tests/unit/test_cf3_algorithm_identity.py"]
bindings = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in FILES}
old = types.ModuleType("company_wiki.document_understanding.structure._review_baseline")
old.__package__ = current.__package__
code = subprocess.check_output(["git", "show", "HEAD:" + FILES[0]], cwd=ROOT).decode("utf-8")
exec(compile(code, "<git HEAD relations>", "exec"), old.__dict__)

def unit(i, *, lane=None, page=1, lang="en", kind="paragraph", source="a", dom=None, x=0, y=10):
    hints = {"source_id": source}
    if dom is not None:
        hints["dom_path"] = dom
    layout = {"bbox": [x, y, x+80, y+8]}
    if lane is not None:
        layout["column"] = lane
    return ObservationUnit({"unit_id": f"u{i}", "ordinal": i, "page": page,
        "text": "Business operating mechanism" if lang == "en" else "經營活動進展",
        "language": lang, "kind": kind, "hints": hints, "layout": layout}, i)

def observe(module, units):
    budget = WorkBudget(16_000_000)
    b = module.RelationBuilder({u.unit_id for u in units}, max_relations=100_000, work_budget=budget)
    module.language_lane_relations(b, units, Ordering(tuple(units), frozenset(), frozenset(), frozenset(), ()))
    return b.relations(), budget.used

rng = random.Random(20261025)
cases = 0
positive_cases = 0
kind_fix_cases = 0
for mode in ("columns", "dom", "geometry"):
    for _ in range(250):
        units = []
        for i in range(rng.randrange(2, 25)):
            lane = rng.randrange(3) if mode == "columns" else None
            u = unit(i, lane=lane, page=rng.randrange(1, 4),
                lang=rng.choice(["en", "zh", "zh-Hant", None]),
                kind=rng.choice(["paragraph", "heading", "header", "table_row"]),
                dom=f"0.{rng.randrange(3)}.{i}" if mode == "dom" else None,
                x=(lane if lane is not None else rng.randrange(3))*150, y=rng.randrange(8)*10)
            units.append(u)
        actual = observe(current, units)[0]
        baseline = observe(old, units)[0]
        by_id = {u.unit_id: u for u in units}
        expected = tuple(r for r in baseline if by_id[r["from_unit_ids"][0]].kind == by_id[r["to_unit_ids"][0]].kind)
        assert actual == expected, mode
        kind_fix_cases += actual != baseline
        positive_cases += bool(actual)
        cases += 1

cross_kind = [unit(0, lang="en", kind="heading", x=0),
              unit(1, lang="zh", kind="paragraph", x=200)]
assert observe(current, cross_kind)[0] == ()
for _ in range(250):
    units = [unit(i, lane=rng.choice([None, 0, 1]), lang=rng.choice(["en", "zh"]),
                  source=rng.choice(["original-a", "original-b", None]),
                  dom=f"0.1.{i}", x=rng.choice([0, 200])) for i in range(20)]
    by_id = {u.unit_id: u for u in units}
    for r in observe(current, units)[0]:
        assert by_id[r["from_unit_ids"][0]].source_id == by_id[r["to_unit_ids"][0]].source_id

with tempfile.TemporaryDirectory(prefix="owned-probe-", dir=Path(__file__).parent) as name:
    temp_root = Path(name)
    first, second = temp_root / "a", temp_root / "b"
    first.mkdir()
    second.mkdir()
    (first / "__init__.py").write_bytes(b"# root\r\n")
    (second / "__init__.py").write_bytes(b"# root\n")
    for folder in (first, second):
        (folder / "nested").mkdir()
        (folder / "nested" / "rule.py").write_bytes(b"# child\n")
    assert decision_inventory._structure_algorithm_hashes(first) == decision_inventory._structure_algorithm_hashes(second)
    before = decision_inventory._structure_algorithm_hashes(second)
    (second / "nested" / "rule.py").unlink()
    assert decision_inventory._structure_algorithm_hashes(second) != before
assert not temp_root.exists()
result = {"binding": bindings, "baseline": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
          "single_source_differential_cases": cases, "positive_differential_cases": positive_cases,
          "expected_kind_fix_cases": kind_fix_cases, "cross_source_cases": 250,
          "portable_lf_crlf_nested_and_deletion_closure": "PASS", "temporary_root_restored_absent": True,
          "cross_kind_geometry_current": observe(current, cross_kind)[0],
          "cross_kind_geometry_baseline": observe(old, cross_kind)[0]}
out = Path(__file__).with_name("probe-results.json")
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
