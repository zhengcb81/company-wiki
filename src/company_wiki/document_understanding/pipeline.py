"""End-to-end document understanding: one call from parsed units to reading plan.

This is the integration surface ROOT owns (``implementation.md`` steps 4-5). It composes
the three lanes without any of them importing another:

    existing parser units
        -> build_observation        (ROOT adapter)      du-input/1
        -> apply_layout_hints       (ROOT bridge)       existing geometry
        -> route_document           (profiles lane)     du-route/1
        -> resolve_reading_profile  (single catalog)    scoped policy
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

This module uses the installed policy asset; it does not read original files, call a model,
or raise a paid budget. It produces a
plan; the existing selector and budget still decide what is actually sent.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, TYPE_CHECKING
from hashlib import sha256
from dataclasses import replace

from .observation_adapter import build_observation, selectable_unit_ids
from .orchestration import build_dependency_packages
from .strategy_binding import bind_reading_plan
from .layout_hints.contract import WorkBudget, WorkBudgetExceeded, resolve_limits as layout_limits
from .native_signal_bridge import collect_native_signals

if TYPE_CHECKING:
    from .narrative_continuity import NativeSourceContext

PIPELINE_SCHEMA_VERSION = "du-pipeline/1"
PIPELINE_FEATURE_VERSION = "1.13.0"

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
    work_budget: WorkBudget | None = None,
    _native_contexts: dict[str, NativeSourceContext] | None = None,
) -> dict[str, Any]:
    """Run the full document-understanding chain over already-parsed units.

    Returns a ``du-pipeline/1`` mapping holding each stage's own output plus a small plan
    summary. Each stage keeps its own schema version, so a consumer can use one stage's
    output without depending on the rest. A private sink can retain the borrowed
    source observer for the current selection call; the JSON result never owns it.
    """
    # Imported here rather than at module import time: the parent package must stay usable
    # when a lane is absent (for example a partial deployment), and a missing lane should
    # surface as a clear error at the call site rather than at import.
    from .profiles import get_profile, route_document, resolve_reading_profile
    from .layout_bridge import apply_layout_hints, bind_layout_context
    from .structure import build_structure
    from .profiles.observation import parse_observation, reprobe_observation
    from .profiles.child_ranges import reserve_native_scope

    budget = work_budget if work_budget is not None else WorkBudget(layout_limits(limits)["max_work_units"])
    source_unit_count = len(units)
    try:
        budget.charge()
    except WorkBudgetExceeded:
        return _deferred_pipeline(source_id, source_sha256, source_unit_count, budget)

    observation: Mapping[str, Any] = build_observation(
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

    try:
        native_signals = collect_native_signals(observation, work_budget=budget)
    except WorkBudgetExceeded:
        return _deferred_pipeline(source_id, source_sha256, source_unit_count, budget,
                                  observation=observation)
    observation, layout_hints = apply_layout_hints(observation, limits=limits, work_budget=budget)
    if budget.exhausted:
        return _deferred_pipeline(source_id, source_sha256, source_unit_count, budget,
                                  observation=observation, layout_hints=layout_hints)
    prepared = parse_observation(observation, limits)
    reserved = tuple(native_signals['reserved_unit_ids'])
    if reserved:
        reserved = reserve_native_scope(prepared, reserved)
        prepared = reprobe_observation(prepared, reserved_unit_ids=reserved)
    prepared = replace(prepared, native_source_signals=native_signals)
    route = route_document(prepared, limits=limits)
    profile = resolve_reading_profile(get_profile(route["profile_id"]), prepared,
                                      route, limits=limits)
    route["profile_version"] = profile["profile_version"]
    from .narrative_continuity import NativeSourceContext
    try:
        # Borrow only already parsed provenance. Reserve the projection before
        # a document-sized index is built; the same account pays both clients.
        budget.charge(1 + 3 * source_unit_count)
        native_provenance = {
            unit.unit_id: {
                "paragraph_index": getattr(unit.coordinates, "paragraph_index", None),
                **{key: unit.metadata[key] for key in
                   ("pdf_block", "block_sha256", "block_char_start", "block_char_end")
                   if key in unit.metadata}}
            for unit in units}
        for wire in observation["units"]:
            # Attribution is already normalised by the adapter/source_ref.
            # Generic public parser inputs need no new identity attribute, and
            # unknown paragraph coordinates remain unknown physical evidence.
            native_provenance[wire["unit_id"]]["source_id"] = wire.get("hints", {}).get(
                "source_id", source_id)
        native_context = NativeSourceContext(observation["units"], provenance=native_provenance,
            coverage=observation["coverage"], work_budget=budget)
    except WorkBudgetExceeded:
        return _deferred_pipeline(source_id, source_sha256, source_unit_count, budget,
                                  observation=observation, layout_hints=layout_hints)
    if _native_contexts is not None:
        _native_contexts[source_id] = native_context
    structure = bind_layout_context(build_structure(observation, limits=limits, work_budget=budget,
                                    native_context=native_context), layout_hints,
                                    work_budget=budget)
    if budget.exhausted:
        return _deferred_pipeline(source_id, source_sha256, source_unit_count, budget,
                                  observation=observation, layout_hints=layout_hints,
                                  structure=structure)
    child_profiles = {}
    prepared_by_id = {unit.unit_id: unit for unit in prepared.units}
    for child in route.get("child_routes", ()):
        pid = child.get("profile_id")
        reason = child.get("reason", "")
        code = reason.get("code", "") if isinstance(reason, Mapping) else str(reason)
        scope = set(child.get("unit_ids", ()))
        if "EXTERNAL_ATTACHMENT_NOT_READ" in code or not scope:
            continue
        if not scope <= prepared_by_id.keys():
            continue
        actual_units = tuple(sorted((prepared_by_id[uid] for uid in scope), key=lambda unit: unit.ordinal))
        try:
            child_base = get_profile(pid)
        except (KeyError, TypeError, ValueError):
            continue
        # A child sees only its already-read range, including its own metadata.
        # The parent's title/form cannot certify an attachment's purpose.
        child_observation = replace(reprobe_observation(prepared, units=actual_units),
                                    title=None, declared_kind=None, form_type=None,
                                    regime_claim=None, is_attachment_scope=True)
        child_route = {**route, "profile_id": pid,
                       "family": child.get("family", child_base["family"]),
                       "regime": child.get("regime", child_base.get("regime", "unknown")),
                       "form_type": child.get("form_type"),
                       "subtype": child.get("subtype"), "child_routes": []}
        key = f"{pid}:" + sha256("\0".join(sorted(scope)).encode()).hexdigest()[:16]
        child["reading_profile_key"] = key
        child_profiles[key] = resolve_reading_profile(child_base, child_observation,
                                                     child_route, limits=limits)
        child["profile_version"] = child_profiles[key]["profile_version"]
    try:
        reading_plan = bind_reading_plan(observation, structure, route=route,
                                         profile=profile, child_profiles=child_profiles,
                                         work_budget=budget)
    except WorkBudgetExceeded:
        return _deferred_pipeline(source_id, source_sha256, source_unit_count, budget,
                                  observation=observation, layout_hints=layout_hints,
                                  structure=structure)
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

    from .native_table_bridge import bind_native_tables, close_native_table_dependencies

    try:
        # Purpose is determined once from the real table's own fields, before
        # costly numeric binding. Source selection reuses this transient result.
        from .structure.table_purpose import qualify_package_table
        from dataclasses import asdict

        original_units = {unit['unit_id']: unit for unit in observation['units']}
        eligible_ids: set[str] = set()
        prepared_packages: list[dict[str, Any]] = []
        for package in packages['packages']:
            budget.charge()
            if package['kind'] == 'operating_table':
                members = package['member_unit_ids']
                budget.charge(sum(1 + len(original_units[uid]['text']) // 64
                                  for uid in members if uid in original_units))
                purpose = qualify_package_table(package, original_units)
                package = {**package, 'table_purpose': asdict(purpose)}
                body = [uid for uid in members if uid not in package.get('required_context_unit_ids', ())]
                if purpose.eligible and not package.get('truncated'):
                    eligible_ids.update(body[index] for index in purpose.eligible_row_indices)
            prepared_packages.append(package)
        packages = {**packages, 'packages': prepared_packages}
        table_bindings = bind_native_tables(observation, layout_hints=layout_hints,
                                            eligible_unit_ids=eligible_ids, work_budget=budget)
        packages = close_native_table_dependencies(packages, table_bindings, work_budget=budget)
    except WorkBudgetExceeded:
        return _deferred_pipeline(source_id, source_sha256, source_unit_count, budget,
                                  observation=observation, layout_hints=layout_hints,
                                  structure=structure)

    return {
        "schema_version": PIPELINE_SCHEMA_VERSION,
        "feature_version": PIPELINE_FEATURE_VERSION,
        "analysis_status": "complete",
        "work": _work_observation(budget, source_unit_count),
        "source_ref": observation["source_ref"],
        "observation": observation,
        "route": route,
        "profile": profile,
        "child_profiles": child_profiles,
        "structure": structure,
        "packages": packages,
        "reading_plan": reading_plan,
        "layout_hints": layout_hints,
        "source_signals": native_signals,
        "table_bindings": table_bindings,
        "non_selectable_unit_ids": non_selectable,
        "plan": _plan(route, profile, structure, packages),
        "diagnostics": _pipeline_diagnostics(route, structure, packages) + reading_plan["diagnostics"]
        + list(profile.get("policy_diagnostics", ()))
        + list(layout_hints.get("diagnostics", ())),
    }


def _work_observation(budget: WorkBudget, source_unit_count: int) -> dict[str, Any]:
    # Logical analysis accounting does not claim regex or wall-clock bounds.
    return {"used": budget.used, "limit": budget.max_work_units,
            "exhausted": budget.exhausted, "source_unit_count": source_unit_count,
            "scope": "native_signals_layout_structure_and_strategy",
            "full_pipeline_hard_bound": False}


def _deferred_pipeline(source_id, source_sha256, count, budget, *, observation=None,
                       layout_hints=None, structure=None):
    """No exception-path document scan; already prepared originals stay readable."""
    return {"schema_version": PIPELINE_SCHEMA_VERSION, "feature_version": PIPELINE_FEATURE_VERSION,
            "analysis_status": "deferred", "source_ref": {"source_id": source_id, "source_sha256": source_sha256},
            "observation": observation if observation is not None else {
                "schema_version": "du-input/1", "source_ref": {"source_id": source_id, "source_sha256": source_sha256},
                "units": [], "coverage": {"native_scan": "partial", "unobserved_unit_count": count}},
            "structure": structure if structure is not None else {"coverage": {"complete": False}},
            "layout_hints": layout_hints,
            "work": _work_observation(budget, count),
            "diagnostics": [{"code": "WORK_BUDGET_EXCEEDED", "unit_ids": [],
                             "detail": "enhancement deferred; unexamined material is unknown, not absent"}]}



def _narrative_expectation(route: Mapping[str, Any], packages: Mapping[str, Any]) -> bool | None:
    if route["family"] in NARRATIVE_FAMILIES or any(
        entry.get("reading_family") in NARRATIVE_FAMILIES for entry in packages.get("packages", ())
    ):
        return True
    return False if route["family"] == "administrative" else None

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
        "expects_business_narrative": _narrative_expectation(route, packages),
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
    expects_narrative = _narrative_expectation(route, packages)
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
    if expects_narrative is False:
        diagnostics.append(
            {
                "code": "NO_NARRATIVE_EXPECTED",
                "detail": (
                    f"{route['family']} family; narrative packages are not expected"
                    + (f" (none produced, {package_count} present)" if not package_count else "")
                ),
            }
        )
    if expects_narrative is None:
        diagnostics.append({"code": "NARRATIVE_EXPECTATION_UNKNOWN",
                            "detail": "unclassified purpose; absence of business content has not been established"})
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
