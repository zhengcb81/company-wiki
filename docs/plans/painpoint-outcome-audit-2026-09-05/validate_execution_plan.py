"""Read-only, standard-library plan checks; never import or run product code."""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def order(graph):
    if not isinstance(graph, dict) or not graph:
        raise ValueError("empty gate set")
    visiting, visited, result = set(), set(), []

    def visit(node):
        if not node or node not in graph:
            raise ValueError("unknown/empty gate")
        if node in visiting:
            raise ValueError("cycle")
        if node in visited:
            return
        if not graph[node].get("independent_role"):
            raise ValueError("missing independent reviewer")
        visiting.add(node)
        for parent in graph[node]["requires"]:
            visit(parent)
        visiting.remove(node)
        visited.add(node)
        result.append(node)

    for node in graph:
        visit(node)
    return result


def check():
    data = json.loads((HERE / "gate-dag.json").read_text(encoding="utf-8"))
    graph = data["gates"]
    expected = {f"WP{w:02d}.G{g}" for w in range(15) for g in range(6)}
    expected |= {f"S{w:02d}" for w in (1, 2, 4, 5, 6)}
    errors = []
    if set(graph) != expected:
        errors.append("gate set differs from 90 reviews + 5 safety reviews")
    if data["status"] != "NOT_IMPLEMENTATION_AUTHORIZED":
        errors.append("plan must not claim implementation permission")
    topo = order(graph)
    for w in range(15):
        for g in range(6):
            cell = graph[f"WP{w:02d}.G{g}"]
            if cell["state"] != "pending":
                errors.append("unexecuted product gate marked complete")
            if g and f"WP{w:02d}.G{g-1}" not in cell["requires"]:
                errors.append("missing sequential predecessor")
    if "WP13.G5" not in graph["WP12.G4"]["requires"]:
        errors.append("12b lacks real cohort prerequisite")
    if "WP12.G5" not in graph["WP14.G4"]["requires"]:
        errors.append("final exit lacks natural window")
    for action, prerequisites in data["scope_rules"].items():
        if not prerequisites or any(x not in graph for x in prerequisites):
            errors.append(f"bad scope rule {action}")
    for action, needed in {"llm": "S05", "worker_pipeline": "S06"}.items():
        if needed not in data["scope_rules"][action]:
            errors.append("missing critical safety scope")
    negatives = []
    for label, parent in (("cycle", "WP13.G5"), ("unknown", "WP99.G0"), ("empty", "")):
        bad = copy.deepcopy(graph)
        bad["WP00.G3"]["requires"].append(parent)
        try:
            order(bad)
        except ValueError:
            negatives.append(label)
        else:
            errors.append(f"negative survived: {label}")
    links = 0
    for name in ("execution-handbook.md", "execution-control-plane.md", "execution-data-plane.md", "execution-model-plane.md"):
        path = HERE / name
        if not path.is_file():
            errors.append(f"missing handbook: {name}")
            continue
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if "://" not in target:
                links += 1
                if not (path.parent / target.split("#")[0]).exists():
                    errors.append(f"missing link {name}: {target}")
    return {"scope": "plan structure only; no product test, no permission validation", "passed": not errors,
            "gates": len(graph), "work_packages": 15, "negative_cases_rejected": negatives,
            "links_checked": links, "errors": errors, "topological_order": topo}


if __name__ == "__main__":
    result = check()
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result["passed"] else 1)
