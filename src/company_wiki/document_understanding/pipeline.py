"""End-to-end document understanding: one call from parsed units to reading plan.

This is the integration surface ROOT owns (``implementation.md`` steps 4-5). It composes
the three lanes without any of them importing another:

    existing parser units
        -> build_observation        (ROOT adapter)      du-input/1
        -> route_document           (profiles lane)     du-route/1
        -> get_profile              (profiles lane)     profile
        -> build_structure          (structure lane)    du-structure/1
        -> build_dependency_packages(ROOT bridge)       du-packages/1

Two properties this module exists to guarantee, both of which are easy to lose when the
stages are called by hand:

* **Routing informs reading.** ``get_profile`` is resolved from the route and passed to
  the package builder, so a document's own section priorities actually order its packages.
  (Reading ``section_priorities`` off the *route* looks correct and silently does nothing,
  because that key lives on the profile.)
* **Nothing is deleted.** Routing only prioritises. Every stage keeps its own honest
  coverage/diagnostic record so a gap stays visible as a gap.

This module does not call a model, read the disk, or raise a paid budget. It produces a
plan; the existing selector and budget still decide what is actually sent.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .observation_adapter import build_observation, selectable_unit_ids
from .orchestration import build_dependency_packages
from .strategy_binding import bind_reading_plan

PIPELINE_SCHEMA_VERSION = "du-pipeline/1"

#: Families whose documents carry business narrative worth reading closely. A document that
#: routes to ``administrative`` is *readable* but is not expected to yield narrative, so the
#: plan records that expectation instead of pretending the absence is a coverage failure.
NARRATIVE_FAMILIES = frozenset(
    {
        "annual",
        "interim",
        "quarterly",
        "prospectus",
        "offering",
        "results_release",
        "presentation",
        "investor_qa",
        "earnings_call",
    }
)


def understand_units(
    units: Sequence[Any],
    *,
    source_id: str,
    source_sha256: str,
    title: str = "",
    declared_kind: str = "unknown",
    mime_type: str = "application/pdf",
    language: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    native_scan: str = "complete",
    opaque_pages: Sequence[int] = (),
    deferred_pages: Sequence[int] = (),
    limits: Mapping[str, Any] | None = None,
    max_packages: int | None = None,
) -> dict[str, Any]:
    """Run the full document-understanding chain over already-parsed units.

    Returns a ``du-pipeline/1`` mapping holding each stage's own output plus a small plan
    summary. Each stage keeps its own schema version, so a consumer can use one stage's
    output without depending on the rest.
    """
    # Imported here rather than at module import time: the parent package must stay usable
    # when a lane is absent (for example a partial deployment), and a missing lane should
    # surface as a clear error at the call site rather than at import.
    from .profiles import get_profile, route_document
    from .structure import build_structure

    observation = build_observation(
        units,
        source_id=source_id,
        source_sha256=source_sha256,
        title=title,
        declared_kind=declared_kind,
        mime_type=mime_type,
        language=language,
        metadata=metadata,
        native_scan=native_scan,
        opaque_pages=opaque_pages,
        deferred_pages=deferred_pages,
    )

    route = route_document(observation, limits=limits)
    profile = get_profile(route["profile_id"])
    structure = build_structure(observation, limits=limits)
    child_profiles = {}
    for child in route.get("child_routes", ()):
        pid = child.get("profile_id")
        try:
            child_profiles[pid] = get_profile(pid)
        except (KeyError, TypeError, ValueError):
            continue
    reading_plan = bind_reading_plan(observation, structure, route=route,
                                     profile=profile, child_profiles=child_profiles)
    structure = reading_plan["structure"]
    # Carry the observation's non-selectable units into the packages, so the decision made
    # in the adapter actually reaches the consumers that add and send evidence. A marking
    # that nothing reads is the same no-op this layer exists to remove.
    selectable = set(selectable_unit_ids(observation))
    non_selectable = [
        unit["unit_id"]
        for unit in observation["units"]
        if unit["unit_id"] not in selectable
    ]
    packages = build_dependency_packages(
        structure,
        route=route,
        profile=profile,
        max_packages=max_packages,
        unit_order={
            unit["unit_id"]: unit["ordinal"] for unit in observation["units"]
        },
        non_selectable_unit_ids=non_selectable,
        unit_reading_plan=reading_plan["unit_profiles"],
    )

    return {
        "schema_version": PIPELINE_SCHEMA_VERSION,
        "source_ref": observation["source_ref"],
        "observation": observation,
        "route": route,
        "profile": profile,
        "structure": structure,
        "packages": packages,
        "reading_plan": reading_plan,
        "non_selectable_unit_ids": non_selectable,
        "plan": _plan(route, profile, structure, packages),
        "diagnostics": _pipeline_diagnostics(route, structure, packages) + reading_plan["diagnostics"],
    }


def _plan(
    route: Mapping[str, Any],
    profile: Mapping[str, Any],
    structure: Mapping[str, Any],
    packages: Mapping[str, Any],
) -> dict[str, Any]:
    """A small, decision-ready summary of what the reader intends to do."""
    return {
        "profile_id": route["profile_id"],
        "profile_version": route["profile_version"],
        "family": route["family"],
        "regime": route["regime"],
        "confidence": route["confidence"],
        "disposition_hint": route["disposition_hint"],
        "expects_business_narrative": route["family"] in NARRATIVE_FAMILIES,
        "read_first_roles": [
            entry["section_role"]
            for entry in profile.get("section_priorities", ())
            if entry.get("priority") == 1
        ],
        "section_count": len(structure.get("sections", ())),
        "semantic_unit_count": len(structure.get("semantic_units", ())),
        "package_count": packages.get("package_count", 0),
    }


def _pipeline_diagnostics(
    route: Mapping[str, Any],
    structure: Mapping[str, Any],
    packages: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Carry each stage's diagnostics forward instead of collapsing them.

    The important one is the honest empty result: a document that *should* carry business
    narrative but produced no package is a real gap to report, whereas an administrative
    document producing none is expected. Conflating the two is how "we read nothing" turns
    into "there was nothing to read".
    """
    diagnostics: list[dict[str, Any]] = []
    expects_narrative = route["family"] in NARRATIVE_FAMILIES
    package_count = packages.get("package_count", 0)

    if expects_narrative and not package_count:
        diagnostics.append(
            {
                "code": "NO_NARRATIVE_PACKAGES",
                "detail": (
                    "the document routes to a business-narrative family but no "
                    "dependency package was produced; treat as a coverage gap, not as "
                    "an absence of business content"
                ),
            }
        )
    if not expects_narrative:
        diagnostics.append(
            {
                "code": "NO_NARRATIVE_EXPECTED",
                "detail": (
                    f"{route['family']} family; narrative packages are not expected"
                    + (f" (none produced, {package_count} present)" if not package_count else "")
                ),
            }
        )
    if route["confidence"] in {"low", "unknown"}:
        diagnostics.append(
            {
                "code": "ROUTE_LOW_CONFIDENCE",
                "detail": f"route confidence is {route['confidence']}; reading order is a best effort",
            }
        )
    for item in structure.get("diagnostics", ()) or ():
        if isinstance(item, Mapping) and item.get("code"):
            diagnostics.append({"code": str(item["code"]), "detail": "from structure lane"})
    return diagnostics


__all__ = ["NARRATIVE_FAMILIES", "PIPELINE_SCHEMA_VERSION", "understand_units"]
