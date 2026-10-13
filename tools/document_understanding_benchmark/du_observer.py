"""Observe final DU material, independently of gold or model-generated claims.

This pure adapter does no parsing, selection, IO or model invocation. Byte and
identity verification belong to the source layer. Here we only ensure each
final member is an unchanged unit of the already verified source observation.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .records import validate_observed

_CONCRETE_SCOPES = frozenset({"project", "qa_exchange", "operating_table"})


def observe_pipeline(
    pipeline: Mapping[str, Any], summary: Mapping[str, Any], *, sample_id: str,
) -> dict[str, Any]:
    """Measure actual final evidence; unknown coordinates stay unknown.

    No whole-document/project scope is inferred from wording. Semantic scope
    applies only to concrete source groups with unambiguous membership. The
    result measures request assembly, not the quality of a generated summary.
    """
    source = pipeline["source_ref"]
    if summary.get("source_ref") != source:
        raise ValueError("summary and original observation source differ")
    observation = pipeline["observation"]
    if observation.get("source_ref") != source:
        raise ValueError("pipeline and original observation source differ")
    units = {unit["unit_id"]: unit for unit in observation["units"]}
    packages = summary.get("evidence_packages", ())
    scopes: dict[str, set[str]] = {}
    for package in packages:
        if package.get("kind") in _CONCRETE_SCOPES:
            for member in package["members"]:
                scopes.setdefault(member["unit_id"], set()).add(package["package_id"])
    evidence: dict[str, dict[str, Any]] = {}
    semantic_units = []
    for package in packages:
        locators = []
        for member in package["members"]:
            unit = units.get(member["unit_id"])
            if unit is None or any(member.get(key) != unit.get(key) for key in ("text", "locator", "page")):
                raise ValueError("final member differs from original observation unit")
            if not unit["text"].strip():
                continue
            locator = unit["locator"]
            unit_scopes = scopes.get(unit["unit_id"], set())
            row = {
                "locator": locator, "text": unit["text"], "unit_id": unit["unit_id"],
                "page": unit.get("page"), "source_role": unit.get("role"),
                "language": unit.get("language"),
                "scope_id": next(iter(unit_scopes)) if len(unit_scopes) == 1 else None,
                "period": observation.get("metadata", {}).get("period_end"),
            }
            existing = evidence.get(locator)
            if existing is not None and existing != row:
                raise ValueError("ambiguous original units share one locator")
            evidence[locator] = row
            locators.append(locator)
        semantic_units.append({
            "semantic_id": package["package_id"], "kind": package.get("kind"),
            "locators": list(dict.fromkeys(locators)),
            "required_locators": package.get("required_locators"),
            "dependencies_resolved": package.get("dependencies_resolved"),
            "completeness": package.get("completeness"),
        })
    coverage = dict(pipeline.get("structure", {}).get("coverage", {}))
    unread = summary.get("unread", {})
    coverage["native_scan"] = unread.get("native_scan")
    coverage["opaque_pages"] = unread.get("opaque_pages", [])
    coverage["deferred_unit_ids"] = list(dict.fromkeys(
        list(unread.get("deferred_unit_ids", ())) +
        [member for entry in summary.get("deferred", ()) for member in entry.get("unit_ids", ())]
    ))
    coverage["deferred_pages"] = list(unread.get("deferred_pages", ()))
    unread_pages = set(coverage["opaque_pages"]) | set(coverage["deferred_pages"])
    pages = {unit["page"] for unit in units.values() if type(unit.get("page")) is int and unit["page"] > 0}
    coverage["read_pages"] = sorted(pages - unread_pages) if pages else None
    coverage["complete"] = bool(unread.get("structure_complete")) and not (
        summary.get("deferred") or unread_pages or coverage["deferred_unit_ids"]
        or coverage.get("unassigned_unit_ids") or coverage["native_scan"] != "complete"
    )
    selected_text = "\n".join(row["text"] for row in evidence.values())
    return validate_observed({
        "schema_version": "du-observed/1", "sample_id": sample_id,
        "source_sha256": source["source_sha256"], "route": pipeline.get("route"),
        "selected_locators": list(evidence), "selected_evidence": list(evidence.values()),
        "selected_text": selected_text, "semantic_units": semantic_units,
        "claims": [], "coverage": coverage,
        "metrics": {"source_units": len(units), "selected_spans": len(evidence),
                    "selected_text_bytes": len(selected_text.encode("utf-8")),
                    "assembly_budget": dict(summary.get("budget", {}))},
        "execution": {"entry_point": "understand_units -> build_summary_input",
                      "selector_version": pipeline.get("schema_version"),
                      "mode": "producer-only", "calls": 0},
    })


