"""Shared reading plan into the established candidate/budget/finalize path.

Format adapters have already read the original. This module owns admission and
selection, not IO, research conclusions, model calls or another task store.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, replace
from hashlib import sha256
from importlib import import_module
import json
import re
from typing import TYPE_CHECKING, Any

from company_wiki.document_model.table_shapes import has_unbound_numeric_cells
from company_wiki.document_understanding.pipeline import understand_units
from company_wiki.document_understanding.narrative_continuity import (
    NativeSourceContext, build_native_continuity,
)
from company_wiki.document_understanding.reading_context_contract import (
    CURRENT_READING_CONTEXT_SCHEMA, SOURCE_PROCESSING_DIMENSION, SOURCE_PROCESSING_ID_SAMPLE_LIMIT,
)
from company_wiki.document_understanding.selection_bridge import build_context_graph
from company_wiki.document_understanding.summary_input import (
    SHARED_CONSTRAINTS as _SHARED_CONSTRAINTS,
    sent_policies as _sent_policies,
    unread_units as _unread,
)
from company_wiki.document_understanding.layout_hints.contract import WorkBudget, WorkBudgetExceeded, DEFAULT_LIMITS

from .narrative_antecedent import build_antecedent_windows, within_reference_envelope
from .narrative_budget import READING_BUDGET_POLICY
from .narrative_business_policy import (
    reading_material_value,
)
from .narrative_candidates import EvidenceCandidate
from .narrative_document import DocumentStructure, NarrativeEvidencePackage
from .narrative_finalize import finalize_selection
from .narrative_pdf_turns import observe_pdf_transcript_turns, printed_turn_is_context
from .narrative_routing import DocumentRoute, route_document
from .narrative_support_use import SUPPORT_USE_SCAN_PASSES, source_support_use, source_narrative_relevance

from .narrative_reading_admission import (
    CONTEXT_ROLES, is_admitted,
)
from .narrative_business_policy import detect_reading_business_fact as detect_reading_business_fact

if TYPE_CHECKING:
    from .narrative_operating_relations import SourceOperatingSession

READING_SELECTOR_VERSION = "0.9.0"
MAX_READING_CHARS = 48000
_BUSINESS_ROLES = frozenset({"business", "management_discussion", "operating_metrics",
                             "fundraising", "industry", "outlook"})
_NEVER_HEADING = re.compile(r"(?!x)x")
_READING_DIAGNOSTIC_SAMPLE_LIMIT = 32
# Kinds whose anchors are prose statements that may carry a product deictic.
# Tables and attributed Q&A retain their separate structural owners.
_REFERENCE_KINDS = frozenset({"background", "paragraph_event", "risk", "project",
                              "native_continuity"})
_REFERENCE_DEFERRAL_REASONS = frozenset({"REFERENCE_UNRESOLVED", "REFERENCE_ENVELOPE"})


@dataclass(frozen=True, slots=True)
class ReadingUnitObservation:
    unit_id: str
    source_id: str
    locator: str
    source_role: str
    raw_text: str


@dataclass(frozen=True, slots=True)
class ReadingInspection:
    """Detached observations from one selection, for offline replay diagnostics."""

    original_units: tuple[ReadingUnitObservation, ...]
    structure: Mapping[str, Any]
    prepared_units: Mapping[str, dict[str, Any]]
    source_packages: tuple[dict[str, Any], ...]
    selected_span_ids: Mapping[str, str]
    work: Mapping[str, Any]
    pipeline_fields: tuple[str, ...]
    selection_diagnostics: tuple[Mapping[str, Any], ...]


def _inspect_reading(parsed: DocumentStructure, pipeline: Mapping[str, Any],
                     eligible: Sequence[Mapping[str, Any]], budget: WorkBudget,
                     diagnostics: Sequence[Mapping[str, Any]],
                     session: SourceOperatingSession | None = None) -> ReadingInspection:
    origins = pipeline.get("_carrier_origins", {})
    profiles = pipeline.get("reading_plan", {}).get("unit_profiles", {})
    prepared = {}
    if session is not None:
        for unit in parsed.units:
            origin = origins.get(unit.unit_id, unit.unit_id)
            owner = session.owner_for(origin)
            prepared[unit.unit_id] = {
                "owner": owner, "fact": session.facts.get(owner),
                "passage": session.passages.get(owner), "profile": deepcopy(profiles.get(origin)),
            }
    fields = ("package_id", "kind", "anchor_unit_ids", "member_unit_ids", "required_context_unit_ids")
    return ReadingInspection(
        tuple(ReadingUnitObservation(unit.unit_id, unit.source_id, unit.coordinates.locator(),
                                     unit.source_role, unit.raw_text) for unit in parsed.units),
        deepcopy(pipeline.get("structure", {})),
        prepared,
        tuple({key: deepcopy(package[key]) for key in fields if key in package} for package in eligible),
        dict(pipeline.get("selected_span_ids", {})),
        {"used": budget.used, "limit": budget.max_work_units, "exhausted": budget.exhausted,
         "complete": session is not None and session.complete},
        tuple(sorted(pipeline)),
        tuple(deepcopy(diagnostics)),
    )




def _citation_support_views(entry, originals):
    """The same exact native support scopes at admission and projection."""
    views = entry.get("citation_support_views")
    if entry["kind"] == "qa_exchange":
        def role(uid):
            unit = originals[uid]
            return unit.get("role") if isinstance(unit, Mapping) else unit.source_role
        declared = entry.get("anchor_unit_ids")
        answers = {uid for uid in (declared if declared is not None else entry["member_unit_ids"])
                   if uid in originals and role(uid) not in CONTEXT_ROLES
                   and (declared is not None or role(uid) == "management")}
        views = [list(dict.fromkeys(uid for uid in view if uid in answers))
                 for view in views or [list(answers)]]
        views = [view for view in views if view]
        if not views and answers:
            views = [[uid for uid in entry["member_unit_ids"] if uid in answers]]
    return views if views is not None else [list(entry.get("anchor_unit_ids", entry["member_unit_ids"]))]


def _qualified_table(package: Mapping[str, Any], units: Mapping[str, Any]):
    """Use the structure owner's one semantic service over actual table members."""
    from company_wiki.document_understanding.structure.table_purpose import TablePurpose, qualify_package_table

    prepared = package.get('table_purpose')
    if prepared is not None:
        return TablePurpose(prepared['status'], prepared['reason'], tuple(prepared['eligible_row_indices']))
    # Compatibility for callers that supply a package without the shared pipeline.
    return qualify_package_table(package, {uid: {'text': unit.raw_text, 'kind': unit.unit_kind}
        for uid, unit in units.items() if uid in package['member_unit_ids']})


def _prose_reading_packages(parsed: DocumentStructure, pipeline: Mapping[str, Any], classify=None, *,
                           work_budget: WorkBudget | None = None,
                           _native_contexts: Mapping[str, NativeSourceContext] | None = None):
    """Compatibility facade over the source-material preparation phase."""
    from .narrative_native_materials import prepare_native_materials
    return prepare_native_materials(parsed, pipeline, classify, work_budget=work_budget,
        _native_contexts=_native_contexts, continuity_builder=build_native_continuity)


def _candidates(parsed: DocumentStructure, pipeline: Mapping[str, Any], *,
                work_budget: WorkBudget | None = None,
                _session_state: dict[str, Any] | None = None,
                _native_contexts: Mapping[str, NativeSourceContext] | None = None):
    from typing import cast

    from .narrative_native_ranges import native_range_unit
    from .narrative_operating_relations import SourceOperatingSession

    mutable_pipeline = cast(dict[str, Any], pipeline)
    mutable_pipeline.pop("_material_units", None)
    mutable_pipeline.pop("_carrier_origins", None)
    work_budget = work_budget if work_budget is not None else WorkBudget(DEFAULT_LIMITS["max_work_units"])
    admission_trace: dict[str, Any] = {"counts": {}, "rejection_counts": {}, "samples": {}}
    try:
        # Reserve source closure indexes before constructing them. Geometry
        # below tightens its own ceiling on this same account, never a clone.
        work_budget.charge(2 * len(parsed.units) + len(pipeline.get("non_selectable_unit_ids", ())) + 1)
    except WorkBudgetExceeded:
        if _session_state is not None:
            _session_state["admission_trace"] = admission_trace
        return [], {}, [], False, [{"package_id": "source-closure",
            "reason": "OPERATING_WORK_BUDGET", "known_unit_ids": [], "unexamined_from_index": 0}]
    units = {unit.unit_id: unit for unit in parsed.units}
    reading = pipeline["reading_plan"]["unit_profiles"]
    excluded = set(pipeline.get("non_selectable_unit_ids", ()))
    candidates: dict[str, EvidenceCandidate] = {}
    metadata: dict[str, dict[str, Any]] = {}
    eligible_packages = []
    withheld = []
    quality_checked: set[str] = set()
    numeric_shape_uncertain: set[str] = set()
    try:
        packages, _joint_facts, continuity, blocked = _prose_reading_packages(parsed, pipeline,
            work_budget=work_budget, _native_contexts=_native_contexts)
        withheld.extend(continuity.get("native_dependency_diagnostics", ()))
        sections = pipeline.get("structure", {}).get("sections", ())
        work_budget.charge(sum(1 + len(section.get("heading_unit_ids", ()))
                               + len(section.get("body_unit_ids", ())) for section in sections))
        headings = {uid for section in sections for uid in section.get("heading_unit_ids", ())}
        section_memberships: dict[str, set[str | None]] = {}
        for section in sections:
            section_id = section.get("section_id")
            for uid in section.get("body_unit_ids", ()):
                section_memberships.setdefault(uid, set()).add(section_id)
    except WorkBudgetExceeded:
        if _session_state is not None:
            _session_state["admission_trace"] = admission_trace
        return [], {}, [], False, [{"package_id": "source-closure",
            "reason": "OPERATING_WORK_BUDGET", "known_unit_ids": [], "unexamined_from_index": 0}]
    # Qualify actual table rows before the context graph establishes cost and
    # closure. Rejected account rows are neither facts nor borrowed context.
    scoped_packages = []
    for package in packages:
        try:
            work_budget.charge(1 + len(package.get("member_unit_ids", ())))
        except WorkBudgetExceeded:
            withheld.append({"package_id": str(package["package_id"]),
                             "reason": "OPERATING_WORK_BUDGET", "known_unit_ids": []})
            break
        # A table is a physical source container, not a discourse purpose.
        # The structure owner has already bound Q/A members and roles; requiring
        # operating-table headers here loses actual answers, while qualifying
        # the whole cell lets a question donate business relevance to a purely
        # financial or boilerplate answer. Q/A keeps its exact citation views
        # and passes the ordinary answer-level source assessment below.
        if package["kind"] == "qa_exchange":
            if package.get("completeness") == "partial" and package.get("anchor_unit_ids"):
                # A self-contained answer remains readable, but missing Q/A
                # context reported by the structure owner cannot become a
                # complete exchange merely because its text can be selected.
                withheld.append({"package_id": str(package["package_id"]),
                    "reason": "QA_CONTEXT_PARTIAL",
                    "known_unit_ids": [uid for uid in package.get("member_unit_ids", ()) if uid in units]})
            scoped_packages.append(package)
            continue
        table_members = [units[uid] for uid in package.get("member_unit_ids", ()) if uid in units]
        native_tables = {(unit.source_id, unit.coordinates.page_number, unit.coordinates.table_index)
                         for unit in table_members if unit.coordinates.table_index is not None}
        native_table = (len(native_tables) == 1 and bool(table_members)
                        and all(unit.coordinates.table_index is not None for unit in table_members))
        if package["kind"] != "operating_table" and not native_table:
            scoped_packages.append(package)
            continue
        members = list(dict.fromkeys(package.get("member_unit_ids", ())))
        required = set(package.get("required_context_unit_ids", ()))
        all_ids = set(members) | required
        if package.get("truncated") or not all_ids <= units.keys() or all_ids & excluded:
            withheld.append({"package_id": str(package["package_id"]),
                             "reason": "INCOMPLETE_OR_NONSELECTABLE_CONTEXT",
                             "known_unit_ids": sorted(all_ids & units.keys())})
            continue
        try:
            if package.get("table_purpose") is None:
                work_budget.charge(12 * sum(len(units[uid].raw_text) for uid in all_ids))
            purpose = _qualified_table(package, units)
        except WorkBudgetExceeded:
            withheld.append({"package_id": str(package["package_id"]),
                             "reason": "OPERATING_WORK_BUDGET", "known_unit_ids": sorted(all_ids)})
            continue
        if not purpose.eligible:
            if purpose.status == "incomplete":
                withheld.append({"package_id": str(package["package_id"]),
                                 "reason": purpose.reason, "known_unit_ids": sorted(all_ids)})
            continue
        body = [uid for uid in members if uid not in required]
        admitted_rows = {body[index] for index in purpose.eligible_row_indices}
        scoped_packages.append({**package,
            "_qualified_operating_table": True,
            "member_unit_ids": [uid for uid in members if uid in required or uid in admitted_rows],
            "anchor_unit_ids": [uid for uid in body if uid in admitted_rows]})
    packages = scoped_packages
    # Geometry/scope closure and meaning were established on the originals.
    # Only the source owner may now replace that body with one exact native
    # view range. The budget still charges every character, including native
    # line breaks; no guessed join, second classifier, or discounted fragment.
    origins: dict[str, str] = {}
    carriers = {}
    carrier_views = {}
    ownership: dict[str, int] = {}
    for package in packages:
        if package["kind"] == "native_continuity":
            for uid in dict.fromkeys(package["member_unit_ids"]):
                ownership[uid] = ownership.get(uid, 0) + 1
    for package in packages:
        if package["kind"] != "native_continuity" or package.get("_paragraph_membership_only"):
            continue
        members = list(dict.fromkeys(package["member_unit_ids"]))
        required = set(members) | set(package.get("required_context_unit_ids", ()))
        if (package.get("truncated") or not required <= units.keys() or required & excluded
                or any(ownership[uid] != 1 for uid in members)):
            continue
        carrier = native_range_unit([units[uid] for uid in members])
        if carrier is None:
            continue
        carriers[carrier.unit_id] = carrier
        anchor = next(iter(package.get("anchor_unit_ids", ())), members[0])
        carrier_views[carrier.unit_id] = reading.get(anchor, {})
        origins.update({uid: carrier.unit_id for uid in members})
    material_units = parsed.units
    budget_packages = packages
    if origins:
        material = []
        emitted: set[str] = set()
        for unit in parsed.units:
            target = origins.get(unit.unit_id)
            if target is None:
                material.append(unit)
            elif target not in emitted:
                material.append(carriers[target])
                emitted.add(target)
        material_units = tuple(material)
        units = {unit.unit_id: unit for unit in material_units}
        reading = {**reading, **carrier_views}
        budget_packages = [{**package, **{key: list(dict.fromkeys(
            origins.get(uid, uid) for uid in package.get(key, ())))
            for key in ("member_unit_ids", "anchor_unit_ids", "required_context_unit_ids") if key in package}}
            for package in packages]
        # This private source view never enters a wire bundle or the Store.
        # Original packages remain authoritative for sent reading policies.
        mutable_pipeline["_material_units"] = material_units
        mutable_pipeline["_carrier_origins"] = origins
    texts = {uid: unit.raw_text for uid, unit in units.items()}
    original_units = {unit.unit_id: unit for unit in parsed.units}
    inverse_origins: dict[str, list[str]] = {}
    for origin_uid, carrier_uid in origins.items():
        inverse_origins.setdefault(carrier_uid, []).append(origin_uid)

    def original_members(uid: str) -> tuple[str, ...]:
        # A final carrier stands for every original it replaced; never just [0].
        return tuple(inverse_origins.get(uid, (uid,)))

    prose_ids = {uid for package in packages
                 if package["kind"] in _REFERENCE_KINDS
                 for uid in package.get("member_unit_ids", ())}
    project_for: dict[str, tuple[str, ...]] = {}
    for package in packages:
        if package["kind"] != "project":
            continue
        owner = str(package["package_id"])
        for uid in package.get("member_unit_ids", ()):
            project_for[uid] = (*project_for.get(uid, ()), owner)
    diagnostics = pipeline.get("structure", {}).get("diagnostics", ())
    furniture = frozenset(uid for entry in diagnostics
                          if entry.get("code") == "REPEATED_RUNNING_HEADER"
                          for uid in entry.get("unit_ids", ()))
    carries: set[tuple[str, str]] = set()
    for window in continuity.get("windows", ()):
        members = window.get("member_unit_ids", ())
        for left, right in zip(members, members[1:]):
            if (original_units[left].coordinates.page_number
                    != original_units[right].coordinates.page_number):
                carries.add((left, right))
    list_edges = {}
    for package in packages:
        for proof in package.get("_native_source_proofs", ()):
            work_budget.charge()
            list_edges[(proof["left"], proof["right"])] = proof
    if list_edges:
        work_budget.charge(len(continuity.get("adjacency_edges", ())) + len(list_edges))
        known_edges = {(edge["left"], edge["right"]) for edge in continuity.get("adjacency_edges", ())}
        native_edges = [{**proof, "source_id": original_units[proof["left"]].source_id,
            "basis": "source_body_adjacency", "physical_basis": proof["basis"]}
            for pair, proof in list_edges.items() if pair not in known_edges]
        continuity = {**continuity, "adjacency_edges": [*continuity.get("adjacency_edges", ()), *native_edges]}
        carries.update(list_edges)
    try:
        windows = build_antecedent_windows(parsed, pipeline, prose_unit_ids=prose_ids,
            blocked=frozenset(blocked), excluded=frozenset(excluded),
            furniture=furniture, page_carries=frozenset(carries), project_for=project_for,
            require_adjacency_proof=parsed.mime_type == "application/pdf",
            work_budget=work_budget)
    except WorkBudgetExceeded:
        windows = {}
    antecedents: dict[str, tuple[tuple[str, ...], bool]] = {}
    for package in budget_packages:
        for uid in package.get("member_unit_ids", ()):
            member_ids = original_members(uid)
            window = windows.get(member_ids[0])
            if window is None:
                # No proven window is unknown scope, never a proven absence.
                antecedents[uid] = ((), False)
                continue
            antecedents[uid] = (tuple(entry for entry in window["predecessor_unit_ids"]
                                      if entry not in set(member_ids)), window["complete"])
    analysis_groups: dict[str, tuple[str, ...]] = {}
    for package in budget_packages:
        if package["kind"] == "native_continuity" and len(package["member_unit_ids"]) > 1:
            analysis_groups["analysis:" + package["package_id"]] = tuple(package["member_unit_ids"])
        for index, view in enumerate(package.get("native_analysis_views", ())):
            if len(view) > 1:
                analysis_groups["analysis:" + package["package_id"] + ":" + str(index)] = tuple(view)
    explicit_reference_sections: dict[str, str] = {}
    for uid, memberships in section_memberships.items():
        if len(memberships) == 1:
            section_id = next(iter(memberships))
            if isinstance(section_id, str) and section_id:
                explicit_reference_sections[uid] = section_id
    session = SourceOperatingSession(units, work_budget=work_budget, contexts={},
        groups=analysis_groups, antecedents=antecedents, originals=original_units)
    from .narrative_qa_scopes import close_qa_packages
    packages, budget_packages, qa_withheld = close_qa_packages(packages, budget_packages, session)
    withheld.extend(qa_withheld)
    # Readiness precedes both the graph and any fact/cache work: a product
    # deictic whose declaration is missing, ambiguous, truncated or outside
    # the combined original envelope defers only its own card.
    deferred_packages: set[int] = set()
    extra_context: dict[int, set[str]] = {}
    original_extra: dict[int, set[str]] = {}
    reference_support: dict[int, set[str]] = {}
    for index, package in enumerate(budget_packages):
        if package["kind"] not in _REFERENCE_KINDS:
            continue
        anchors = (list(package.get("anchor_unit_ids", ()))
                   or list(package.get("member_unit_ids", ()))[:1])
        needed_originals: set[str] = set()
        failure = None
        for uid in anchors:
            try:
                closure = session.reference(uid)
            except (ValueError, WorkBudgetExceeded):
                failure = "partial"
                break
            status = closure["status"]
            if status in {"ambiguous", "missing", "partial"}:
                failure = status
                break
            if status in {"unique", "collective"}:
                needed_originals.update(closure["required_original_unit_ids"])
                if closure.get("reference_kind") == "causal_result":
                    reference_support.setdefault(index, set()).update(closure["support_original_unit_ids"])
        if failure is not None:
            deferred_packages.add(index)
            withheld.append({"package_id": str(package["package_id"]),
                "reason": "REFERENCE_UNRESOLVED", "status": failure,
                "known_unit_ids": sorted(set(package.get("member_unit_ids", ())))})
            continue
        if not needed_originals:
            continue
        # The envelope is counted in original coordinates; carriers expand to
        # every member they replaced. A carrier id is never looked up as an
        # original unit.
        original_extra[index] = needed_originals
        extra_context[index] = {origins.get(entry, entry) for entry in needed_originals}
    # Separate complete source statements can still explicitly qualify one
    # another. Native adjacency is only physical proof; the same operating
    # session proves object identity and restrictive state before adding edges.
    local_dependencies = session.local_qualification_dependencies(
        continuity.get("adjacency_edges", ()), origins=origins,
        section_ids=explicit_reference_sections)
    local_context: dict[str, set[str]] = {}
    support_context: dict[str, set[str]] = {}
    for anchor, qualifiers in local_dependencies.items():
        for qualifier in qualifiers:
            local_context.setdefault(anchor, set()).add(qualifier)
            support_context.setdefault(anchor, set()).add(qualifier)
            # A bare restrictive deictic also needs its actual source subject.
            local_context.setdefault(qualifier, set()).add(anchor)
            support_context.setdefault(qualifier, set()).add(anchor)
    project_context = session.local_operating_context_dependencies(
        continuity.get("adjacency_edges", ()), origins=origins,
        section_ids=explicit_reference_sections)
    # Qualification edges may use bounded closure; project context is direct
    # only and must not spread to an unrelated third fact.
    local_components: dict[str, set[str]] = {}
    support_components: dict[str, set[str]] = {}
    intrinsic_support: dict[int, set[str]] = reference_support
    local_unexamined: set[str] = set()
    try:
        def collect_components(adjacency, target):
            for start in adjacency:
                if start in target:
                    continue
                component = {start}
                pending = [start]
                while pending:
                    member = pending.pop()
                    neighbours = adjacency[member]
                    work_budget.charge(1 + len(neighbours))
                    for neighbour in neighbours:
                        if neighbour not in component:
                            component.add(neighbour)
                            pending.append(neighbour)
                work_budget.charge(2 * len(component))
                for member in component:
                    target[member] = component

        collect_components(local_context, local_components)
        collect_components(support_context, support_components)
    except WorkBudgetExceeded:
        session.complete = False
        local_unexamined.update(local_context)
    for index, package in enumerate(budget_packages):
        if index in deferred_packages:
            continue
        if work_budget.exhausted or any(uid in local_unexamined for uid in package.get("member_unit_ids", ())):
            deferred_packages.add(index)
            withheld.append({"package_id": str(package["package_id"]),
                             "reason": "OPERATING_WORK_BUDGET",
                             "known_unit_ids": list(package.get("member_unit_ids", ()))})
            continue
        try:
            member_ids = package.get("member_unit_ids", ())
            work_budget.charge(len(member_ids) + sum(
                len(local_components.get(member, ())) + len(project_context.get(member, ()))
                for member in member_ids))
        except WorkBudgetExceeded:
            session.complete = False
            deferred_packages.add(index)
            withheld.append({"package_id": str(package["package_id"]),
                             "reason": "OPERATING_WORK_BUDGET",
                             "known_unit_ids": list(package.get("member_unit_ids", ()))})
            continue
        needed_material = _package_local_context_members(
            package.get("member_unit_ids", ()), local_components, project_context)
        if not needed_material:
            continue
        try:
            work_budget.charge(1 + sum(len(original_members(uid)) for uid in needed_material)
                               + len(package.get("member_unit_ids", ()))
                               + len(package.get("required_context_unit_ids", ())))
        except WorkBudgetExceeded:
            session.complete = False
            deferred_packages.add(index)
            withheld.append({"package_id": str(package["package_id"]),
                             "reason": "OPERATING_WORK_BUDGET",
                             "known_unit_ids": list(package.get("member_unit_ids", ()))})
            continue
        needed_originals = {member for uid in needed_material for member in original_members(uid)}
        support_material = {uid for member in package.get("member_unit_ids", ())
                            for uid in support_components.get(member, ()) if uid != member}
        support_originals = {member for uid in support_material for member in original_members(uid)}
        if support_originals:
            intrinsic_support.setdefault(index, set()).update(support_originals)
        needed_originals.update(original_extra.get(index, ()))
        extra_context.setdefault(index, set()).update(needed_material)
        original_extra.setdefault(index, set()).update(needed_originals)
    if extra_context:
        budget_packages = [{**package, "required_context_unit_ids": sorted(
            set(package.get("required_context_unit_ids", ())) | extra_context.get(index, set()))}
            for index, package in enumerate(budget_packages)]
    if original_extra:
        # _context and source cards read the original packages; the declaration
        # must be their required context, not only a budget-side carrier.
        packages = [{**package, "required_context_unit_ids": sorted(
            set(package.get("required_context_unit_ids", ())) | original_extra.get(index, set()))}
            for index, package in enumerate(packages)]
    if intrinsic_support:
        # An intrinsic restriction belongs to the quote itself. A context-only
        # link would still let extractive cards publish a naked plan. Ordinary
        # questions, headings and antecedents retain their separate context role.
        try:
            work_budget.charge(len(original_units))
            original_order = {uid: position for position, uid in enumerate(original_units)}
            for index, extra in intrinsic_support.items():
                package = packages[index]
                views = package.get("citation_support_views", [list(
                    package.get("anchor_unit_ids", package["member_unit_ids"]))])
                work_budget.charge(sum(len(view) + len(extra) for view in views))
                packages[index] = {**package, "citation_support_views": [
                    sorted(set(view) | extra, key=original_order.__getitem__) for view in views]}
        except WorkBudgetExceeded:
            session.complete = False
            deferred_packages.update(intrinsic_support)
    contexts: dict[str, set[str]] = {}
    for package in budget_packages:
        context_ids = set(package.get("required_context_unit_ids", ()))
        anchors = package.get("anchor_unit_ids", ())
        for uid in anchors:
            contexts.setdefault(uid, set()).update(context_ids - {uid})
        if package["kind"] == "native_continuity" and len(package["member_unit_ids"]) > 1:
            owner = "analysis:" + package["package_id"]
            owner_members = tuple(package["member_unit_ids"])
            analysis_groups[owner] = owner_members
            contexts[owner] = context_ids - set(owner_members)
        for index, view in enumerate(package.get("native_analysis_views", ())):
            if len(view) > 1:
                owner = "analysis:" + package["package_id"] + ":" + str(index)
                analysis_groups[owner] = tuple(view)
                contexts[owner] = context_ids - set(view)
    session.contexts = {**session.contexts, **{uid: tuple(sorted(ids)) for uid, ids in contexts.items()}}
    graph = build_context_graph({**pipeline["packages"], "packages": budget_packages}, texts)
    # One union of readable native ancestry, product deictics and restrictions.
    # Proven running furniture pays source work, never a new model-material fee.
    for index, package in enumerate(budget_packages):
        if index in deferred_packages or not (
                package.get("_native_dependency_targets") or original_extra.get(index)):
            continue
        try:
            member_ids = package.get("member_unit_ids", ())
            context_ids = graph["groups"][index]["required_unit_ids"]
            work_budget.charge(1 + len(member_ids) + len(context_ids)
                + sum(len(inverse_origins.get(uid, (uid,))) for uid in (*member_ids, *context_ids))
                + len(original_extra.get(index, ())))
            target_originals = [member for uid in member_ids for member in original_members(uid)]
            context_originals = [member for uid in context_ids for member in original_members(uid)]
            needed = sorted(original_extra.get(index, ()))
            valid = within_reference_envelope(target_originals, context_originals,
                                              needed, original_units, expand=original_members)
        except WorkBudgetExceeded:
            valid = False
            session.complete = False
        if not valid:
            deferred_packages.add(index)
            withheld.append({"package_id": str(package["package_id"]),
                "reason": "OPERATING_WORK_BUDGET" if work_budget.exhausted else "REFERENCE_ENVELOPE",
                "known_unit_ids": list(package.get("_native_dependency_targets") or
                                       package.get("member_unit_ids", ()))})

    if _session_state is not None:
        _session_state["session"] = session
    if not continuity["complete"]:
        withheld.append({"package_id": "native-continuity",
            "reason": "INCOMPLETE_NATIVE_CONTINUITY", "known_unit_ids": sorted(blocked)})
    def package_priority(entry):
        index, package = entry
        anchors = package.get("anchor_unit_ids", ()) or package.get("member_unit_ids", ())[:1]
        return (min((int(reading.get(uid, {}).get("priority", 2)) for uid in anchors), default=2), index)

    try:
        work_budget.charge(2 * len(session.groups) + 1)
    except WorkBudgetExceeded:
        scope_ready = False
        session.complete = False
        support_groups = {}
    else:
        scope_ready = True
        support_groups = dict(session.groups)
        session.groups = support_groups
    scope_owners = {tuple(members): owner for owner, members in support_groups.items()}
    scope_uses: dict[tuple[Any, ...], tuple[str, str, bool, str, bool]] = {}

    def scope_use(native_support, *, table_qualified=False, prepared_owner=None):
        # A carrier stands for all original characters in its native range.
        # This key is exactly the scope later projected to canonical spans.
        if not scope_ready:
            return "unresolved", "source_assessment_incomplete", False, "description", False
        members = tuple(dict.fromkeys(origins.get(uid, uid) for uid in native_support))
        key = (members, table_qualified, prepared_owner)
        if key in scope_uses:
            return scope_uses[key]
        try:
            work_budget.charge(len(members) + 1)
            if any(printed_turn_is_context(units[uid]) for uid in members):
                assessed = ("context_only", "attribution_context", False, "description", False)
                scope_uses[key] = assessed
                return assessed
            if prepared_owner is not None and session.groups.get(prepared_owner) != members:
                # Generic source qualification may enlarge a closed QA quote.
                # Prepare the actual final support, not the smaller proof.
                context = tuple(uid for uid in session.context_for(prepared_owner) if uid not in members)
                prepared_owner = session.support_owner(members, meaning_context=context)
            owner = prepared_owner or scope_owners.get(members)
            if owner is None:
                if len(members) == 1 and session.owner_for(members[0]) == members[0]:
                    owner = members[0]
                else:
                    # Add an analysis owner, never override any unit's owner.
                    # Its contexts are empty: context cannot donate a predicate.
                    owner = "source-support:" + str(len(scope_owners))
                    support_groups[owner] = members
                scope_owners[members] = owner
            fact = session.fact(owner)
            text = session.source_text(owner)
            source_roles=session.source_assertions(owner)
            passage = session.source_passage(owner)
            # The closed scope's capability was prepared once in the session.
            # Do not charge a second full text scan for consuming that cache.
            work_budget.charge(SUPPORT_USE_SCAN_PASSES * len(text) if passage is None else len(members) + 1)
            context_role = all(units[uid].source_role in CONTEXT_ROLES for uid in members)
            use = source_support_use(text, fact=fact, financial_only=session.financial_only(owner),
                table_qualified=table_qualified,
                context_role=context_role,
                source_relations=session.relations(owner), support_unit_ids=members,
                source_roles=source_roles, passage=passage,
                numeric_ambiguous=any(uid in numeric_shape_uncertain for uid in members)
                    or bool(source_roles and source_roles.numeric_ambiguous))
            relevance=source_narrative_relevance(fact=fact,source_roles=source_roles, passage=passage,
                                                 table_qualified=table_qualified)
            value = ("meaningful_fact" if table_qualified else
                     reading_material_value(fact, source_roles=source_roles))
            source_deferred = bool(passage is not None and not passage.assessment_complete
                                   and not context_role and not table_qualified)
            assessed=(*use,relevance,value,source_deferred)
        except (WorkBudgetExceeded, ValueError):
            session.complete = False
            assessed = ("unresolved", "source_assessment_incomplete", False, "description", False)
        scope_uses[key] = assessed
        return assessed

    # Spend scarce source-state work on known reading priorities first. This
    # changes analysis order, not material order, ownership or selected costs.
    for index, package in sorted(enumerate(budget_packages), key=package_priority):
        if index in deferred_packages:
            continue
        members = list(dict.fromkeys(package["member_unit_ids"]))
        required = set(graph["groups"][index]["required_unit_ids"]) | set(members)
        # Incomplete closure is not a smaller complete fact. Missing original
        # references stay deferred; shadow duplicates alone may be withheld.
        if package.get("truncated") or not required <= units.keys() or required & (excluded | blocked):
            withheld.append({"package_id": str(package["package_id"]),
                             "reason": "INCOMPLETE_OR_NONSELECTABLE_CONTEXT",
                             "known_unit_ids": sorted(required & units.keys())})
            continue
        # Assess literal numeric quality once, in the same source-priority
        # order as meaning. A later low-priority budget stop cannot invalidate
        # already checked important facts by charging them again at export.
        unexamined_quality = required - quality_checked
        if unexamined_quality:
            try:
                work_budget.charge(len(unexamined_quality))
                work_budget.charge(4 * sum(len(units[uid].raw_text) for uid in unexamined_quality))
            except WorkBudgetExceeded:
                session.complete = False
                withheld.append({"package_id": str(package["package_id"]),
                                 "reason": "OPERATING_WORK_BUDGET", "known_unit_ids": sorted(required)})
                continue
            numeric_shape_uncertain.update(uid for uid in unexamined_quality
                                           if has_unbound_numeric_cells(units[uid].raw_text))
            quality_checked.update(unexamined_quality)
        table_qualified = package["kind"] == "operating_table" or package.get("_qualified_operating_table", False)
        original_package = packages[index]
        use_views = []
        anchor_uses: dict[str, tuple[str, str]] = {}
        anchor_relevance: dict[str, bool] = {}
        anchor_values: dict[str, str] = {}
        anchor_complete: dict[str, bool] = {}
        for native_support in _citation_support_views(original_package, original_units):
            if not native_support:
                continue
            use, reason, relevant, value, source_deferred = scope_use(native_support, table_qualified=table_qualified,
                prepared_owner=original_package.get('_source_scope_owner'))
            if source_deferred:
                withheld.append({"package_id": str(package["package_id"]), "reason": reason,
                    "status": "deferred", "phase": "source_readability",
                    "known_unit_ids": list(dict.fromkeys(native_support))})
            if original_package.get('_qa_scope_complete') is False and use == 'support':
                use, reason = 'unresolved', 'source_scope_partial'
            use_views.append({"support_unit_ids": list(native_support),
                              "reading_support_use": use, "reading_support_reason": reason})
            for uid in native_support:
                material_uid = origins.get(uid, uid)
                # The offer follows one proved view and its closed costs. It
                # never changes another view's generation-use annotation.
                if (material_uid not in anchor_uses or use == "support"
                        or relevant and not anchor_relevance.get(material_uid,False)):
                    anchor_uses[material_uid] = (use, reason)
                    anchor_relevance[material_uid] = relevant
                    anchor_values[material_uid] = value
                    anchor_complete[material_uid] = not source_deferred
        packages[index] = {**original_package, "_reading_support_use_views": use_views}
        declared_anchors = list(package.get("anchor_unit_ids", ()))
        if package["kind"] == "qa_exchange":
            # The shared structure owner identifies actual answers even when a
            # format's neutral source role is company_filing. Questions remain
            # context, including an unanswered exchange; never fall back to Q.
            if "anchor_unit_ids" not in package:
                declared_anchors = [uid for uid in members if units[uid].source_role == "management"]
            if not declared_anchors:
                withheld.append({"package_id": str(package["package_id"]),
                                 "reason": "ANSWER_MISSING", "known_unit_ids": members})
                continue
        elif table_qualified:
            declared_anchors = [uid for uid in members
                                if uid not in set(package.get("required_context_unit_ids", ()))
                                and units[uid].unit_kind not in {"footnote", "table_caption", "table_header"}]
        anchors = []
        for uid in declared_anchors or members[:1]:
            if uid not in members:
                continue
            unit = units[uid]
            view = reading.get(uid, {})
            if session.work_budget.exhausted and session.owner_for(uid) not in session.facts:
                session.complete = False
                withheld.append({"package_id": str(package["package_id"]),
                    "reason": "OPERATING_WORK_BUDGET", "known_unit_ids": sorted(required)})
                continue
            fact = session.fact(uid)
            if session.work_budget.exhausted and not fact.eligible:
                withheld.append({"package_id": str(package["package_id"]),
                    "reason": "OPERATING_WORK_BUDGET", "known_unit_ids": sorted(required)})
                continue
            admitted, fact = is_admitted(unit, view, package["kind"],
                                       fact=fact,
                                       financial_only=session.financial_only(uid),
                                       is_heading=uid in headings, table_qualified=table_qualified,
                                       trace=admission_trace, package_id=str(package["package_id"]),
                                       required_unit_ids=tuple(sorted(required - {uid})),
                                       support_use=anchor_uses.get(uid, ("unresolved", "source_use_unassessed")),
                                       offer_relevant=anchor_relevance.get(uid,False),
                                       assessment_complete=anchor_complete.get(uid,True))
            if not admitted:
                continue
            anchors.append(uid)
            # Value follows the same closed citation view as its support/use;
            # an anchor's larger analysis owner cannot donate another fact.
            meaningful = anchor_values.get(uid) == "meaningful_fact"
            role = view.get("section_role")
            scope_topics = (role,) if not meaningful and role in _BUSINESS_ROLES else ()
            topics = tuple(dict.fromkeys((*fact.topics, *scope_topics)))
            previous = metadata.get(uid, {})
            previous_anchor = bool(previous) and not previous.get("context_only", True)
            previous_meaningful = previous_anchor and previous.get("value_band") == "meaningful_fact"
            old = candidates.get(uid) if previous_anchor else None
            if old is not None:
                # Multiple source packages may share one original anchor. A
                # weaker description cannot erase proven meaning or add its
                # section label as a factual topic. Do not sum duplicate scores.
                previous_topics = old.topics if previous_meaningful or not meaningful else ()
                current_topics = topics if meaningful or not previous_meaningful else ()
                topics = tuple(dict.fromkeys((*previous_topics, *current_topics)))
            reasons = tuple(dict.fromkeys((*(old.reasons if old is not None else ()),
                                            "reading_plan", *fact.reasons)))
            candidates[uid] = EvidenceCandidate(unit, topics, reasons,
                max(old.score if old is not None else 0, fact.score))
            priority = max(1, int(view.get("priority", 2)))
            metadata[uid] = {"priority": min(priority, int(previous["priority"])) if previous_anchor else priority,
                             "topics": topics, "context_only": False,
                             "value_band": "meaningful_fact" if meaningful or previous_meaningful else "description",
                             "required": tuple(sorted(set(previous.get("required", ())) | (required - {uid}))),
                             "fact_purpose": fact.purpose,
                             "fact_reasons": tuple(fact.reasons[:4]),
                             "support_use": "support" if previous.get("support_use") == "support"
                                 else anchor_uses.get(uid, ("unresolved", "source_use_unassessed"))[0],
                             "package_ids": tuple(dict.fromkeys((*previous.get("package_ids", ()),
                                                                  str(package["package_id"]))))}
        if not anchors:
            continue
        eligible_packages.append(packages[index])
        for uid in required:
            if uid not in candidates:
                candidates[uid] = EvidenceCandidate(units[uid], (), ("reading_context",), 0)
                metadata[uid] = {"priority": 2, "topics": (), "context_only": True, "required": ()}
    if _session_state is not None:
        _session_state["numeric_shape_uncertain_ids"] = {
            unit.unit_id for unit in parsed.units
            if origins.get(unit.unit_id, unit.unit_id) in numeric_shape_uncertain}
        _session_state["admission_trace"] = admission_trace
    # Stable source order, never text-only identity deduplication.
    ordered = tuple(candidates[unit.unit_id] for unit in material_units if unit.unit_id in candidates)
    source_order = {package["package_id"]: index for index, package in enumerate(packages)}
    eligible_packages.sort(key=lambda package: source_order[package["package_id"]])
    return ordered, metadata, eligible_packages, graph["complete"] and continuity["complete"] and session.complete, withheld


def _native_layout_summary(parsed: DocumentStructure) -> dict[str, Any] | None:
    """Persist bounded coverage, never transient words/cells or another inventory."""
    coverage = parsed.layout_coverage
    if coverage is None:
        return None
    result = {key: coverage[key] for key in (
        "feature_version", "complete", "processed_unit_count", "processed_page_count",
        "deferred_unit_count", "fine_element_count", "work_units") if key in coverage}
    execution = coverage.get("reading_execution")
    if isinstance(execution, Mapping):
        # Opaque logical execution observation, already bounded by its source
        # reading owner; this layer neither selects nor configures a backend.
        result["reading_execution"] = dict(execution)
    native_ranges = coverage.get("native_ranges")
    if isinstance(native_ranges, Mapping):
        result["native_ranges"] = {key: native_ranges[key] for key in (
            "feature_version", "complete", "captured_chars", "deferred_page_count", "deferred_pages")
            if key in native_ranges}
    capture = coverage.get("capture")
    if isinstance(capture, Mapping):
        result['capture'] = {key: capture[key] for key in (
            'schema_version', 'strategy', 'mode', 'request_sha256', 'complete',
            'not_requested_page_count') if key in capture}
        for phase in ('requested', 'captured', 'projected', 'deferred'):
            pages = capture.get(phase + '_pages', ())
            result['capture'][phase + '_pages'] = list(pages[:128])
            result['capture'][phase + '_page_count'] = capture.get(phase + '_page_count', len(pages))
            result['capture'][phase + '_pages_limited'] = bool(
                capture.get(phase + '_pages_limited') or len(pages) > 128)
    planning = coverage.get('planning')
    if isinstance(planning, Mapping):
        result['planning'] = {key: planning[key] for key in (
            'feature_version', 'request_digest', 'policy_digest', 'plan_digest',
            'profile_id', 'profile_scope', 'complete', 'navigation_missing',
            'window_count', 'deferred_page_count', 'unresolved_navigation_count') if key in planning}
        result['planning']['reason_counts'] = dict(list(planning.get('reason_counts', {}).items())[:32])
        result['planning']['deferred_pages'] = list(planning.get('deferred_pages', ())[:128])
        result['planning']['exploration_pages'] = list(planning.get('exploration_pages', ())[:64])
        admission = planning.get('admission', {})
        result['planning']['spent'] = dict(admission.get('spent', {}))
    identifiers = coverage.get("deferred_unit_ids", ())
    result["deferred_unit_ids"] = list(identifiers[:128])
    result["deferred_limited"] = bool(coverage.get("deferred_limited") or len(identifiers) > 128)
    counts: dict[str, dict[str, Any]] = {}
    for entry in parsed.layout_diagnostics:
        code = str(entry.get("code", "UNKNOWN"))
        # Native producers already bound diagnostic codes; cap a malformed
        # caller's distinct labels as well without dropping the total count.
        if code not in counts and len(counts) >= 128:
            code = "OTHER_DIAGNOSTICS"
        row = counts.setdefault(code, {"code": code, "count": 0, "unit_count": 0})
        row["count"] += 1
        row["unit_count"] += int(entry.get("unit_count", len(entry.get("unit_ids", ()))))
    result["diagnostics"] = list(counts.values())
    return result


def _context(pipeline: Mapping[str, Any], package: NarrativeEvidencePackage,
             eligible: list[Mapping[str, Any]]) -> dict[str, Any]:
    # Mapping original units to canonical spans retains parser/locator identity.
    observation = pipeline["observation"]
    sent_ids = {span.span_id for span in package.evidence_spans}
    original = {unit["unit_id"]: unit for unit in observation["units"]}
    selected = {}
    # Observation coordinates are wire locators; locate by original ID metadata
    # through a caller-owned table installed below, not fuzzy text matching.
    for uid, span_id in pipeline["selected_span_ids"].items():
        if span_id in sent_ids:
            selected[uid] = original[uid]
    entries = [{"members": list(selected.values())}]
    policies, facets, version = _sent_policies(pipeline, entries)
    groups = []
    group_ids: set[str] = set()
    deferred = []
    for entry in eligible:
        required = set(entry["member_unit_ids"]) | set(entry.get("required_context_unit_ids", ()))
        if not required <= selected.keys():
            deferred.append({"package_id": str(entry["package_id"]), "reason": "SELECTION_BUDGET"})
            continue
        ids = list(dict.fromkeys(pipeline["selected_span_ids"][uid]
                                 for uid in original if uid in required))
        citation_views = []
        seen_support = set()
        support_uses = {tuple(row["support_unit_ids"]): row for row in entry.get("_reading_support_use_views", ())}
        for native_support in _citation_support_views(entry, original):
            if not native_support or not set(native_support) <= required:
                raise ValueError("native citation support must belong to its complete source package")
            support_set = {pipeline["selected_span_ids"][uid] for uid in native_support}
            support = [sid for sid in ids if sid in support_set]
            support_key = tuple(support)
            if support_key in seen_support:
                continue
            seen_support.add(support_key)
            use = support_uses.get(tuple(native_support), {})
            citation_views.append({"support_evidence_ids": support,
                "context_evidence_ids": [sid for sid in ids if sid not in support_set],
                "reading_support_use": use.get("reading_support_use", "unresolved"),
                "reading_support_reason": use.get("reading_support_reason", "source_use_unassessed")})
        proof_rows = tuple(entry.get("_native_source_proofs", ()))
        physical_proof_ids = set(entry.get("_native_source_original_ids", ()))
        proof_endpoints = {str(uid) for proof in proof_rows for uid in (proof["left"], proof["right"])}
        required_proof_targets = sorted(
            proof_endpoints & set(entry.get("_native_source_proof_targets", ())) - physical_proof_ids
        )
        group = {"kind": str(entry["kind"]), "section_role": str(entry.get("section_role") or "unknown"),
                 "evidence_ids": ids, "citation_views": citation_views,
                 **({"source_proof_unit_ids": sorted(physical_proof_ids),
                    "source_proof_target_unit_ids": required_proof_targets,
                    "source_proofs": list(proof_rows)} if proof_rows else {})}
        group_id = _reading_group_id(group)
        group["group_id"] = group_id
        if group_id not in group_ids:
            groups.append(group)
            group_ids.add(group_id)
    unread = _unread(pipeline["structure"], observation)
    # Coverage lists are diagnostic examples, not a second all-unit inventory.
    # Preserve full counts and mark truncation rather than persisting huge IDs.
    list_keys = ("opaque_pages", "deferred_pages", "deferred_unit_ids", "unassigned_unit_ids")
    unread["counts"] = {key: len(unread[key]) for key in list_keys}
    unread["limited"] = any(
        unread["counts"][key] > _READING_DIAGNOSTIC_SAMPLE_LIMIT for key in list_keys
    )
    for key in list_keys:
        if len(unread[key]) > _READING_DIAGNOSTIC_SAMPLE_LIMIT:
            unread[key] = unread[key][:_READING_DIAGNOSTIC_SAMPLE_LIMIT]
    layout_coverage = dict(pipeline.get("layout_hints", {}).get("coverage", {}))
    if pipeline.get("native_layout_frontend") is not None:
        layout_coverage["native_frontend"] = pipeline["native_layout_frontend"]
    constraints = list(_SHARED_CONSTRAINTS)
    if any("table_structure_ambiguous" in span.quality_flags for span in package.evidence_spans):
        constraints.append("Fragments flagged table_structure_ambiguous do not prove column, period, "
                           "row-label or unit attribution. Use independently supported business prose; "
                           "leave unproven numeric interpretations unknown.")
    return {"schema_version": CURRENT_READING_CONTEXT_SCHEMA, "reading_policy_version": version,
            "reading_policies": policies, "business_facets": facets,
            "constraints": constraints,
            "groups": groups, "unread": unread,
            "deferred": deferred, "layout_coverage": layout_coverage}


def _reading_group_id(group: Mapping[str, Any]) -> str:
    """Bind identity to the complete semantic/citation row, not evidence membership alone."""
    identity = json.dumps(group, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = sha256(identity.encode("utf-8")).hexdigest()
    return "urn:company-wiki:reading-group:sha256:" + digest


def _sample_deferred(reference_entries: Sequence[Mapping[str, Any]],
                     selector_entries: Sequence[Mapping[str, Any]],
                     other_entries: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, str]], int, bool]:
    groups = (reference_entries, selector_entries, other_entries)
    count = sum(len(rows) for rows in groups)
    selected: list[tuple[int, int, Mapping[str, Any]]] = []
    selected_positions: set[tuple[int, int]] = set()
    seen_reasons: set[object] = set()
    # Keep one early example of each reason before filling by the established
    # reference, selector, then other priority. Store only bounded row refs.
    for group_index, rows in enumerate(groups):
        for row_index, row in enumerate(rows):
            reason = row.get("reason")
            position = (group_index, row_index)
            if reason not in seen_reasons and len(selected) < _READING_DIAGNOSTIC_SAMPLE_LIMIT:
                selected.append((group_index, row_index, row))
                selected_positions.add(position)
                seen_reasons.add(reason)
    if len(selected) < _READING_DIAGNOSTIC_SAMPLE_LIMIT:
        for group_index, rows in enumerate(groups):
            for row_index, row in enumerate(rows):
                position = (group_index, row_index)
                if position in selected_positions:
                    continue
                selected.append((group_index, row_index, row))
                if len(selected) == _READING_DIAGNOSTIC_SAMPLE_LIMIT:
                    break
            if len(selected) == _READING_DIAGNOSTIC_SAMPLE_LIMIT:
                break
    return ([dict(row) for _, _, row in selected], count, count > len(selected))


def _trace_ref(value: object, namespace: str) -> str:
    digest = sha256(str(value).encode("utf-8")).hexdigest()
    return f"urn:company-wiki:{namespace}:sha256:{digest}"


def _selection_trace(*, source_unit_count: int, admission: Mapping[str, Any],
                     eligible: Sequence[Mapping[str, Any]], withheld: Sequence[Mapping[str, Any]],
                     selected_span_ids: Mapping[str, str]) -> dict[str, Any]:
    counts = admission.get("counts", {})
    admitted_count = int(counts.get("admitted", 0))
    rejected_count = int(counts.get("not_admitted", 0))
    rejection_counts = dict(admission.get("rejection_counts", {}))
    if len(rejection_counts) > 32:
        kept = dict(sorted(rejection_counts.items())[:31])
        kept["other_rejections"] = sum(
            value for key, value in rejection_counts.items() if key not in kept
        )
        rejection_counts = kept

    admission_samples = []
    for sample_key in sorted(admission.get("samples", {})):
        for row in admission["samples"][sample_key]:
            required = tuple(row.get("required_unit_ids", ()))
            fact_reasons = tuple(row.get("fact_reasons", ()))
            admission_samples.append({
                "unit_id": row["target_id"],
                "package_ref": _trace_ref(row.get("package_id", "unknown"), "reading-package"),
                "status": row["status"],
                "reason": row["reason"],
                "fact_purpose": row["fact_purpose"],
                "fact_reasons": list(fact_reasons[:4]),
                "fact_reason_count": int(row.get("fact_reason_count", len(fact_reasons))),
                "fact_reasons_limited": int(row.get("fact_reason_count", len(fact_reasons))) > len(fact_reasons),
                "required_unit_ids": list(required[:8]),
                "required_unit_count": int(row.get("required_unit_count", len(required))),
                "required_unit_ids_limited": int(row.get("required_unit_count", len(required))) > len(required[:8]),
                "priority": row["priority"],
                "selected_span_id": selected_span_ids.get(row["target_id"]),
            })
    admission_samples = admission_samples[:16]

    eligible_samples = []
    for package in eligible[:12]:
        members = tuple(package.get("member_unit_ids", ()))
        anchors = tuple(package.get("anchor_unit_ids", ()))
        required = tuple(package.get("required_context_unit_ids", ()))
        eligible_samples.append({
            "package_ref": _trace_ref(package.get("package_id", "unknown"), "reading-package"),
            "kind": str(package.get("kind", "unknown")),
            "member_unit_ids": list(members[:8]), "member_count": len(members),
            "member_limited": len(members) > 8,
            "anchor_unit_ids": list(anchors[:8]), "anchor_count": len(anchors),
            "anchor_limited": len(anchors) > 8,
            "required_unit_ids": list(required[:8]), "required_count": len(required),
            "required_limited": len(required) > 8,
        })

    withheld_samples = []
    for row in withheld[:16]:
        known = tuple(dict.fromkeys(row.get("known_unit_ids", ())))
        withheld_samples.append({
            "package_ref": _trace_ref(row.get("package_id", "unknown"), "reading-package"),
            "reason": str(row.get("reason", "unknown")),
            "status": row.get("status"),
            "known_unit_ids": list(known[:8]),
            "known_unit_count": len(known),
            "known_unit_ids_limited": len(known) > 8,
        })

    selected_samples = [
        {"unit_id": unit_id, "span_id": span_id}
        for unit_id, span_id in sorted(selected_span_ids.items())[:16]
    ]
    return {
        "schema_version": "selection-trace/1",
        "source_unit_count": source_unit_count,
        "admission": {
            "count": admitted_count + rejected_count,
            "admitted_count": admitted_count,
            "rejected_count": rejected_count,
            "limited": admitted_count + rejected_count > len(admission_samples),
            "rejection_counts": rejection_counts,
            "samples": admission_samples,
        },
        "eligible_packages": {
            "count": len(eligible), "limited": len(eligible) > len(eligible_samples),
            "samples": eligible_samples,
        },
        "withheld": {
            "count": len(withheld), "limited": len(withheld) > len(withheld_samples),
            "samples": withheld_samples,
        },
        "selected": {
            "count": len(selected_span_ids), "limited": len(selected_span_ids) > len(selected_samples),
            "samples": selected_samples,
        },
    }


def _understand(parsed: DocumentStructure, *, title: str, kind: str, mime_type: str,
                work_budget: WorkBudget | None = None,
                _native_contexts: dict[str, NativeSourceContext] | None = None):
    """Each immutable parent has its own structure; selection stays global.

    A captured API projection may contain several genuine original parents.
    Their adjacent fields must never manufacture cross-parent Q&A or tables.
    """
    budget = work_budget if work_budget is not None else WorkBudget(DEFAULT_LIMITS["max_work_units"])
    parents: dict[str, list[Any]] = {}
    for unit in parsed.units:
        budget.charge()
        parents.setdefault(unit.source_id, []).append(unit)
    if not parents:
        parents[parsed.source_id] = []
    parts = []
    native_frontend = _native_layout_summary(parsed)
    for source_id, units in parents.items():
        part = understand_units(units, source_id=source_id,
            source_sha256=source_id.rsplit(":", 1)[-1], title=title, declared_kind=kind,
            mime_type=mime_type, language=parsed.language,
            native_scan="complete" if parsed.coverage_complete else "partial",
            opaque_pages=parsed.opaque_pages, deferred_pages=parsed.deferred_table_pages,
            native_text_coverage=parsed.native_text_coverage,
            work_budget=budget, _native_contexts=_native_contexts)
        if part.get("analysis_status") == "deferred":
            return part
        if native_frontend is not None:
            part["native_layout_frontend"] = native_frontend
            part["observation"]["metadata"]["native_layout_frontend_version"] = native_frontend.get("feature_version")
        parts.append(part)
    if len(parts) == 1:
        return parts[0]
    # Each parent owns its structure and native evidence. Compose graph shells
    # once; copying only the first graph silently loses later parent headings.
    from .narrative_parent_composition import compose_parent_pipelines

    budget.charge(len(parents))
    return compose_parent_pipelines(parts, list(parents), work_budget=budget)


def _selected_unit_spans(parsed: DocumentStructure, result: NarrativeEvidencePackage,
                         pipeline: Mapping[str, Any]) -> dict[str, str]:
    """Bind original policy members to the exact source-owned sent material.

    A proven native range can represent several original fragments. Policies
    still use those originals; the model and planner use the unique range.
    Neither layer creates evidence from a summary or guesses a text match.
    """
    material = pipeline.get("_material_units", parsed.units)
    def key(value: Any):
        return (value.source_id, value.coordinates, value.raw_text,
                value.parser_name, value.parser_version)
    by_key = {key(unit): unit.unit_id for unit in material}
    selected = {}
    for span in result.evidence_spans:
        uid = by_key.get(key(span))
        if uid is None:
            raise ValueError("selected evidence is not source-owned material")
        selected[uid] = span.span_id
    original = {unit.unit_id: unit for unit in parsed.units}
    material_by_id = {unit.unit_id: unit for unit in material}
    origins = pipeline.get("_carrier_origins", {})
    if any(uid not in original or target not in material_by_id
           or original[uid].source_id != material_by_id[target].source_id
           or original[uid].coordinates.page_number != material_by_id[target].coordinates.page_number
           for uid, target in origins.items()):
        raise ValueError("native material origin binding is incomplete")
    return {uid: selected[target] for uid in original
            if (target := origins.get(uid, uid)) in selected}


def _package_local_context_members(
    member_ids: Iterable[str],
    local_components: Mapping[str, set[str]],
    direct_project_context: Mapping[str, Sequence[str]],
) -> set[str]:
    """Return qualification closure plus one-hop project context only."""
    members = tuple(member_ids)
    return {
        uid
        for member in members
        for uid in local_components.get(member, ())
        if uid != member
    } | {
        related
        for member in members
        for related in direct_project_context.get(member, ())
        if related != member
    }


def select_reading_evidence(parsed: DocumentStructure, *, title: str,
                            existing_kind: str = "unknown", max_selected: int | None = None,
                            max_chars: int = MAX_READING_CHARS,
                            work_budget: WorkBudget | None = None,
                            observe: Callable[[ReadingInspection], None] | None = None,
                            ) -> NarrativeEvidencePackage:
    route = route_document(title, existing_kind=existing_kind, max_selected=max_selected)
    mime_type = parsed.mime_type or ("text/plain" if route.document_kind == "investor_call_transcript" else
                                    "application/pdf" if parsed.page_count else "text/html")
    from company_wiki.resource_budget import new_document_work_budget
    budget = work_budget if work_budget is not None else new_document_work_budget()
    native_contexts: dict[str, NativeSourceContext] = {}
    try:
        budget.charge()
        if mime_type == "application/pdf" and route.document_kind == "investor_call_transcript":
            parsed = observe_pdf_transcript_turns(parsed, work_budget=budget)
        pipeline = _understand(parsed, title=title, kind=route.document_kind, mime_type=mime_type,
                               work_budget=budget, _native_contexts=native_contexts)
    except WorkBudgetExceeded as refusal:
        result = _deferred_selection(parsed, route, budget=budget, refusal=refusal)
        if observe is not None:
            observe(_inspect_reading(parsed, {}, (), budget, result.selection_diagnostics))
        return result
    session_state: dict[str, Any] = {}
    if pipeline.get("analysis_status") != "deferred":
        candidates, reading, eligible, graph_complete, withheld = _candidates(
            parsed, pipeline, work_budget=budget, _session_state=session_state,
            _native_contexts=native_contexts)
    session = session_state.get("session")
    if session is None:
        result = _deferred_selection(parsed, route, budget=budget)
        if observe is not None:
            observe(_inspect_reading(parsed, pipeline, (), budget, result.selection_diagnostics))
        return result
    origins = pipeline.get("_carrier_origins", {})
    dropped = 0
    proved_without_offer = 0
    unexplained_numeric = False
    deferred_source_ids = {uid for row in withheld if row.get("phase") == "source_readability"
                           for uid in row["known_unit_ids"]}
    for unit in parsed.units:
        uid = session.owner_for(origins.get(unit.unit_id, unit.unit_id))
        if budget.exhausted and uid not in session.facts:
            session.complete = False
            break
        financial = session.financial_only(uid)
        if financial is None:
            passage = session.source_passage(uid)
            if passage is not None and not passage.assessment_complete:
                if unit.unit_id not in deferred_source_ids:
                    withheld.append({"package_id": uid, "reason": passage.reason,
                        "status": "deferred", "phase": "source_readability",
                        "known_unit_ids": [unit.unit_id]})
                    deferred_source_ids.add(unit.unit_id)
                # One unavailable/long scope is not a global work stop. Other
                # independent scopes still receive their own prepared use.
                continue
            session.complete = False
            break
        dropped += financial
        source_roles=session.source_assertions(uid)
        mixed_numeric=bool(source_roles and source_roles.numeric_ambiguous
            and not source_roles.raw_structure_complete)
        unexplained_numeric = unexplained_numeric or mixed_numeric
        raw_only=bool(source_roles and source_roles.raw_structure_complete
            and not source_narrative_relevance(fact=session.fact(uid),source_roles=source_roles))
        generic_only = bool(source_roles and source_roles.independent_payload is False)
        proved_without_offer += bool(not mixed_numeric and (financial or raw_only or generic_only))
    # Semantic 'unassigned' is not an unread page. It must not defeat a fully
    # read and positively classified finance-only document's zero-model result.
    # A bounded reference deferral removes one card, not the rest of the
    # document: it is reported separately and does not downgrade coverage.
    blocking_withheld = [entry for entry in withheld
                         if entry.get("reason") not in _REFERENCE_DEFERRAL_REASONS]
    processing_base_complete = graph_complete and session.complete and not budget.exhausted and not any(
        "BUDGET" in str(entry.get("code", "")) or "LIMIT_REACHED" in str(entry.get("code", ""))
        for entry in pipeline.get("diagnostics", ()))
    processing_complete = processing_base_complete and not blocking_withheld
    empty_may_skip = (not candidates and parsed.coverage_complete and processing_complete
                      and not unexplained_numeric
                      and (proved_without_offer == len(parsed.units)
                           or pipeline["route"].get("family") == "administrative"
                           or route.empty_result_may_skip))
    effective_route = DocumentRoute(route.document_kind, route.selection_limit,
                                    empty_may_skip)
    material_parsed = replace(parsed, units=tuple(pipeline.get("_material_units", parsed.units)))
    result = finalize_selection(material_parsed, effective_route, candidates, group_ids={},
        heading_pattern=_NEVER_HEADING, dropped_financial_count=dropped,
        budget_policy=READING_BUDGET_POLICY, reading_metadata=reading, max_chars=max_chars)
    if not processing_complete:
        known_candidates = {item.unit.unit_id for item in candidates} | {
            uid for item in withheld for uid in item["known_unit_ids"]}
        count = len(known_candidates)
        # Readability capability failure is semantic processing deferral, not
        # evidence that already read source pages/geometry became unread.
        coverage_complete = result.coverage_complete if processing_base_complete and not any(
            row.get("phase") != "source_readability" for row in blocking_withheld) else False
        result = replace(result, coverage_complete=coverage_complete,
                         status="partial" if result.evidence_spans else "needs_review",
                         candidate_count=count, omitted_candidate_count=count - len(result.evidence_spans))
    if any(diagnostic["code"] == "work_budget_exhausted" for diagnostic in result.selection_diagnostics):
        result = replace(result, coverage_complete=False,
                         status="partial" if result.evidence_spans else "needs_review")
    if budget.exhausted:
        result = replace(result, selection_diagnostics=(
            *result.selection_diagnostics, _document_work_diagnostic(budget)))
    source_diagnostics = _source_processing_diagnostics(withheld)
    if source_diagnostics:
        result = replace(result, selection_diagnostics=(*result.selection_diagnostics, *source_diagnostics))
    pipeline["selected_span_ids"] = _selected_unit_spans(parsed, result, pipeline)
    # Preserve source bytes and IDs. The existing quality vocabulary carries
    # unresolved table attribution into every model view, without an IO gate.
    uncertain = {pipeline["selected_span_ids"][uid]
                 for entry in eligible
                 if entry["kind"] == "operating_table" and entry.get("table_binding_status") != "complete"
                 for uid in set(entry["member_unit_ids"]) - set(entry.get("required_context_unit_ids", ()))
                 if uid in pipeline["selected_span_ids"]}
    # Only project observed quality. Fully bound tables keep the structure
    # owner's positive proof; no second scan, inference or late resource bill.
    bound = {pipeline["selected_span_ids"][uid]
             for entry in eligible if entry.get("table_binding_status") == "complete"
             for uid in (*entry["member_unit_ids"], *entry.get("required_context_unit_ids", ()))
             if uid in pipeline["selected_span_ids"]}
    uncertain.update(span_id for uid, span_id in pipeline["selected_span_ids"].items()
                     if uid in session_state.get("numeric_shape_uncertain_ids", ()) and span_id not in bound)
    if uncertain:
        result = replace(result, evidence_spans=tuple(
            replace(span, quality_flags=tuple(dict.fromkeys((*span.quality_flags, "table_structure_ambiguous"))))
            if span.span_id in uncertain else span for span in result.evidence_spans))
    context = _context(pipeline, result, eligible)
    context["source_processing_complete"] = processing_complete
    # Reference deferrals are the newest and the ones a reader must be able to
    # audit; put them at the front of the bounded list so a document dominated
    # by budget deferrals cannot hide them.
    reference_entries = [{"package_id": item["package_id"], "reason": item["reason"]}
                         for item in withheld
                         if item.get("reason") in _REFERENCE_DEFERRAL_REASONS]
    other_entries = [{"package_id": item["package_id"], "reason": item["reason"]}
                     for item in withheld
                     if item.get("reason") not in _REFERENCE_DEFERRAL_REASONS]
    context["deferred"], context["deferred_count"], context["deferred_limited"] = _sample_deferred(
        reference_entries, context["deferred"], other_entries
    )
    context["selection_diagnostics"] = list(result.selection_diagnostics)
    context["selection_trace"] = _selection_trace(
        source_unit_count=len(parsed.units), admission=session_state.get("admission_trace", {}),
        eligible=eligible, withheld=withheld, selected_span_ids=pipeline["selected_span_ids"],
    )
    dependencies = None
    try:
        dependency_port = import_module("company_wiki.document_understanding.decision_dependencies")
    except ModuleNotFoundError as exc:
        if exc.name != "company_wiki.document_understanding.decision_dependencies":
            raise
        context["selection_diagnostics"].append({"code": "DECISION_DEPENDENCIES_UNAVAILABLE", "count": 1})
    else:
        from .narrative_decision_inventory import build_decision_trace
        trace = build_decision_trace(
            pipeline, used_facet_ids=[facet["id"] for facet in context["business_facets"]],
            source_parser_names=tuple({unit.parser_name for unit in parsed.units}),
            document_work_limit=budget.max_work_units)
        if not processing_complete or budget.exhausted or any(row["code"] == "work_budget_exhausted"
                                   for row in result.selection_diagnostics):
            trace["inventory_complete"] = False
        dependencies = dependency_port.freeze_decision_dependencies(trace)
    if observe is not None:
        observe(_inspect_reading(parsed, pipeline, eligible, budget, result.selection_diagnostics, session))
    return replace(result, reading_context=context, reading_dependencies=dependencies)


def _source_processing_diagnostics(withheld: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    """Bounded public reasons/IDs from prepared deferrals; never rescan text."""
    counts: dict[str, int] = {}
    members: dict[str, set[str]] = {}
    for row in withheld:
        if row.get("phase") != "source_readability":
            continue
        reason = str(row["reason"])
        counts[reason] = counts.get(reason, 0) + 1
        members.setdefault(reason, set()).update(row["known_unit_ids"])
    return tuple({"code": reason, "count": counts[reason], "phase": SOURCE_PROCESSING_DIMENSION,
                  "dimension": SOURCE_PROCESSING_DIMENSION, "external_model_cost": False,
                  "known_unit_ids": sorted(members[reason])[:SOURCE_PROCESSING_ID_SAMPLE_LIMIT],
                  "known_unit_count": len(members[reason]),
                  "known_unit_ids_limited": len(members[reason]) > SOURCE_PROCESSING_ID_SAMPLE_LIMIT}
                 for reason in sorted(counts))


def _document_work_diagnostic(budget: WorkBudget,
                              refusal: WorkBudgetExceeded | None = None) -> dict[str, Any]:
    return {"code": "work_budget_exhausted", "count": 1,
            "dimension": "document_work", "external_model_cost": False,
            "phase": refusal.phase if refusal is not None else budget.phase,
            "used": refusal.used if refusal is not None else budget.used,
            "requested": refusal.requested if refusal is not None else None,
            "limit": refusal.limit if refusal is not None else budget.max_work_units,
            "detail": "unexamined source content remains unknown; original is unchanged"}


def _deferred_selection(parsed: DocumentStructure, route: DocumentRoute, *,
                        budget: WorkBudget, refusal: WorkBudgetExceeded | None = None) -> NarrativeEvidencePackage:
    return NarrativeEvidencePackage(source_id=parsed.source_id, source_sha256=parsed.source_sha256,
        document_kind=route.document_kind, status="needs_review", evidence_spans=(),
        selection_limit=route.selection_limit, candidate_count=0, dropped_financial_count=0,
        source_units=len(parsed.units), omitted_candidate_count=0, coverage_complete=False,
        selection_diagnostics=(_document_work_diagnostic(budget, refusal),))


__all__ = ["ReadingInspection", "ReadingUnitObservation", "select_reading_evidence", "READING_SELECTOR_VERSION"]
