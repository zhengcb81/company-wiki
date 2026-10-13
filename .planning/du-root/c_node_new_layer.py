"""ROOT C-node: measure the new document-understanding layer against the benchmark gold.

This driver answers the only question that matters for the upgrade: with the
*same* evidence budget the baseline uses (96 units, or 160 for an offering), does
structure-driven selection recover facts the flat selector never found?

It is a measurement tool, not product code.  It reads the bound originals
read-only, builds a ``du-input/1`` observation, runs the frozen route/structure
packages plus the ROOT packaging bridge, and emits a ``du-observed/1`` record
that the benchmark's own oracle scores.  Nothing here re-implements or relaxes a
checker.

Usage:
    python -X utf8 .planning/du-root/c_node_new_layer.py \
        --bindings <bindings.json> --gold <gold dir> --output <dir>

The budget is honoured deliberately: selecting the whole document would raise
recall without proving anything, so packages are taken in the document profile's
priority order until the unit budget is spent, with required context always
closed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# Same budgets the legacy router uses, so the comparison is like for like.
DEFAULT_BUDGET = 96
OFFERING_BUDGET = 160
_OFFERING_FAMILIES = {"offering", "prospectus"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_original(path: Path, sample_id: str, sha: str):
    """Parse any supported original into narrative units."""
    suffix = path.suffix.casefold()
    if suffix in {".htm", ".html"}:
        from company_wiki.document_normalization import (
            NormalizationLimits,
            normalize_document,
        )

        document = normalize_document(
            path.read_bytes(),
            source_id=sample_id,
            source_sha256=sha,
            mime_type="text/html",
            limits=NormalizationLimits(),
        )
        return list(document.units), "complete", []
    if suffix == ".txt":
        from company_wiki.source_catalog.narrative_evidence import parse_transcript

        parsed = parse_transcript(
            path.read_text(encoding="utf-8", errors="replace"),
            source_id=sample_id,
            source_sha256=sha,
        )
        return list(parsed.units), "complete", []
    from company_wiki.source_catalog.narrative_evidence import parse_pdf

    parsed = parse_pdf(path, source_id=sample_id, source_sha256=sha)
    return list(parsed.units), "partial", sorted(parsed.opaque_pages)


def _budget_for(family: str) -> int:
    return OFFERING_BUDGET if family in _OFFERING_FAMILIES else DEFAULT_BUDGET


def _select_by_structure(observation, structure, packages, profile, *, budget: int):
    """Walk packages in profile priority order until the unit budget is spent.

    Required context is always closed, so a row never travels without its
    caption and header.  A package that would overflow the budget is skipped
    whole rather than half-included, because half a project package is a
    different and usually false claim.
    """
    ordered_roles = [
        entry["section_role"]
        for entry in sorted(
            profile.get("section_priorities", ()) or (),
            key=lambda entry: entry.get("priority", 9),
        )
    ]
    role_rank = {role: index for index, role in enumerate(ordered_roles)}
    kind_band = {
        "project": 0,
        "operating_table": 0,
        "qa_exchange": 0,
        "risk": 1,
        "paragraph_event": 2,
        "background": 3,
    }

    def rank(package):
        # Chapter priority first (the profile says which chapters matter), then
        # dependency-bearing kinds, then completeness, then document order.
        return (
            role_rank.get(package["section_role"], len(role_rank)),
            kind_band.get(package["kind"], 3),
            0 if package["completeness"] == "complete" else 1,
            package["package_id"],
        )

    selected: list[str] = []
    seen: set[str] = set()
    taken_packages: list[str] = []
    for package in sorted(packages.get("packages", ()), key=rank):
        members = list(package["member_unit_ids"])
        required = [
            unit_id
            for unit_id in package.get("required_context_unit_ids", ())
            if unit_id in members
        ]
        new = [unit_id for unit_id in members if unit_id not in seen]
        if not new:
            continue
        if len(selected) + len(new) > budget:
            continue
        selected.extend(new)
        seen.update(new)
        taken_packages.append(package["package_id"])
        # Keep the required context flag visible for the closure bookkeeping.
        del required
    return selected, taken_packages


def build_observed(path: Path, sample_id: str, *, gold: dict | None = None) -> dict:
    """Run the new layer and return a ``du-observed/1`` record."""
    from company_wiki.document_understanding import build_observation
    from company_wiki.document_understanding.orchestration import (
        build_dependency_packages,
    )
    from company_wiki.document_understanding.profiles import (
        get_profile,
        route_document,
    )
    from company_wiki.document_understanding.structure import build_structure

    started = time.perf_counter()
    sha = _sha256(path)
    units, native_scan, opaque_pages = _parse_original(path, sample_id, sha)
    title = sample_id
    if gold:
        title = gold.get("title") or sample_id

    observation = build_observation(
        units,
        source_id=sample_id,
        source_sha256=sha,
        title=title,
        native_scan=native_scan,
        opaque_pages=opaque_pages,
    )
    route = route_document(observation)
    profile = get_profile(route["profile_id"])
    structure = build_structure(observation)
    packages = build_dependency_packages(structure, route=route, profile=profile)

    budget = _budget_for(route["family"])
    selected_ids, taken = _select_by_structure(
        observation, structure, packages, profile, budget=budget
    )

    locator_of = {unit["unit_id"]: unit["locator"] for unit in observation["units"]}
    text_of = {unit["unit_id"]: unit["text"] for unit in observation["units"]}
    ordered = sorted(selected_ids, key=lambda unit_id: _ordinal(observation, unit_id))
    selected_locators = [locator_of[unit_id] for unit_id in ordered if unit_id in locator_of]
    selected_text = "\n".join(
        text_of[unit_id] for unit_id in ordered if unit_id in text_of
    )

    elapsed = time.perf_counter() - started
    return {
        "schema_version": "du-observed/1",
        "sample_id": sample_id,
        "source_sha256": sha,
        "route": route,
        "selected_locators": selected_locators,
        "selected_text": selected_text,
        "semantic_units": [
            {
                "semantic_id": unit["semantic_id"],
                "kind": unit["kind"],
                "locators": [
                    locator_of[member]
                    for member in unit["member_unit_ids"]
                    if member in locator_of
                ],
                "completeness": unit["completeness"],
            }
            for unit in structure["semantic_units"]
            if any(member in set(selected_ids) for member in unit["member_unit_ids"])
        ],
        "claims": [],
        "coverage": {
            "native_scan": native_scan,
            "opaque_pages": opaque_pages,
            "selected_units": len(selected_ids),
            "budget": budget,
            "packages_taken": len(taken),
            "structure_complete": structure.get("coverage", {}).get("complete"),
        },
        "metrics": {
            "selected_unit_count": len(selected_ids),
            "candidate_unit_count": len(observation["units"]),
            "budget": budget,
        },
        "execution": {
            "entry": "company_wiki.document_understanding",
            "route_profile": route["profile_id"],
            "route_confidence": route["confidence"],
            "family": route["family"],
            "regime": route["regime"],
            "elapsed_seconds": round(elapsed, 3),
            "model_calls": 0,
            "network_calls": 0,
        },
    }


def _ordinal(observation, unit_id: str) -> int:
    for unit in observation["units"]:
        if unit["unit_id"] == unit_id:
            return unit["ordinal"]
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bindings", required=True)
    parser.add_argument("--gold", required=True, help="gold directory")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    sys.path.insert(0, str(REPO / "src"))
    sys.path.insert(0, str(REPO))

    from tools.document_understanding_benchmark.evaluate import evaluate
    from tools.document_understanding_benchmark.gold import load_gold

    bindings = json.loads(Path(args.bindings).read_text(encoding="utf-8"))
    gold_dir = Path(args.gold)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for gold_path in sorted(gold_dir.glob("*.json")):
        gold = load_gold(gold_path)
        if not isinstance(gold, dict):
            gold = dict(gold)
        sample_id = str(gold.get("sample_id") or gold_path.stem)
        entry = bindings.get(sample_id)
        # Bindings are ``sample_id -> absolute path`` strings; the expected
        # digest comes from the gold record itself, which is what the benchmark
        # verifies against.
        if isinstance(entry, dict):
            path_value = entry.get("path")
            expected_sha = entry.get("sha256")
        elif isinstance(entry, str):
            path_value = entry
            expected_sha = gold.get("source_sha256")
        else:
            continue
        if not isinstance(path_value, str) or not path_value:
            continue
        path = Path(path_value)
        if not path.is_file():
            results.append(
                {"sample_id": sample_id, "status": "UNAVAILABLE", "reason": "not bound"}
            )
            continue
        actual_sha = _sha256(path)
        if isinstance(expected_sha, str) and expected_sha and actual_sha != expected_sha:
            results.append(
                {
                    "sample_id": sample_id,
                    "status": "UNAVAILABLE",
                    "reason": "sha mismatch against gold",
                }
            )
            continue

        try:
            observed = build_observed(path, sample_id, gold={"title": sample_id})
            outcome = evaluate(observed, gold)
        except Exception as exc:  # pragma: no cover - environment dependent
            results.append(
                {
                    "sample_id": sample_id,
                    "status": "ERROR",
                    "reason": f"{type(exc).__name__}: {exc}",
                }
            )
            continue

        metrics = outcome.get("metrics") or {}
        results.append(
            {
                "sample_id": sample_id,
                "scope": gold.get("scope"),
                "status": outcome.get("status"),
                "critical_fact_recall": metrics.get("critical_fact_recall"),
                "observed_metrics": observed["metrics"],
                "execution": observed["execution"],
            }
        )

    dev = [r for r in results if r.get("scope") == "development"]
    hold = [r for r in results if r.get("scope") == "holdout"]
    report = {
        "schema_version": "du-c-new-layer/1",
        "results": results,
        "by_scope": {
            "development": _aggregate(dev),
            "holdout": _aggregate(hold),
        },
    }
    (output_dir / "new_layer.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report["by_scope"], ensure_ascii=False, indent=2))
    for row in results:
        print(
            f"  {row['sample_id']:<26} {str(row.get('status')):<10} "
            f"recall={row.get('critical_fact_recall')} "
            f"selected={row.get('observed_metrics', {}).get('selected_unit_count')}"
            f"/{row.get('observed_metrics', {}).get('candidate_unit_count')}"
        )
    return 0


def _aggregate(rows: list[dict]) -> dict:
    scored = [row for row in rows if isinstance(row.get("critical_fact_recall"), (int, float))]
    if not scored:
        return {"documents": len(rows), "critical_fact_recall": None}
    return {
        "documents": len(rows),
        "scored": len(scored),
        "critical_fact_recall": round(
            sum(row["critical_fact_recall"] for row in scored) / len(scored), 3
        ),
    }


if __name__ == "__main__":
    raise SystemExit(main())
