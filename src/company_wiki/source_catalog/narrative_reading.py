"""Shared reading plan into the established candidate/budget/finalize path.

Format adapters have already read the original. This module owns admission and
selection, not IO, research conclusions, model calls or another task store.
"""
from __future__ import annotations

from bisect import bisect_right
from collections.abc import Mapping
from dataclasses import replace
from hashlib import sha256
from importlib import import_module
import json
import re
from typing import Any

from company_wiki.document_understanding.pipeline import understand_units
from company_wiki.document_understanding.narrative_continuity import (
    SourcePageFlow, build_native_continuity, native_section_key,
)
from company_wiki.document_understanding.operating_states.relations import independent_statement_start
from company_wiki.document_understanding.selection_bridge import build_context_graph
from company_wiki.document_understanding.summary_input import _sent_policies, _unread, _SHARED_CONSTRAINTS
from company_wiki.document_understanding.layout_hints.contract import WorkBudget, WorkBudgetExceeded, DEFAULT_LIMITS

from .narrative_antecedent import build_antecedent_windows, within_reference_envelope
from .narrative_budget import READING_BUDGET_POLICY
from .narrative_business_policy import detect_reading_business_fact, reading_financial_only
from .narrative_source_purpose import NON_OPERATING_PURPOSES
from .narrative_candidates import EvidenceCandidate
from .narrative_document import DocumentStructure, NarrativeEvidencePackage
from .narrative_finalize import finalize_selection
from .narrative_routing import DocumentRoute, route_document

READING_SELECTOR_VERSION = "0.9.0"
MAX_READING_CHARS = 48000
_BUSINESS_ROLES = frozenset({"business", "management_discussion", "operating_metrics",
                             "fundraising", "industry", "outlook"})
_CONTEXT_ROLES = frozenset({"operator", "analyst", "investor_question", "qa_text_shadow"})
_NEVER_HEADING = re.compile(r"(?!x)x")
# Kinds whose anchors are prose statements that may carry a product deictic.
# Tables and attributed Q&A retain their separate structural owners.
_REFERENCE_KINDS = frozenset({"background", "paragraph_event", "risk", "project",
                              "native_continuity"})
_REFERENCE_DEFERRAL_REASONS = frozenset({"REFERENCE_UNRESOLVED", "REFERENCE_ENVELOPE"})


def _financial_only(text: str, fact: Any = None) -> bool:
    fact = fact or detect_reading_business_fact(text)
    # A source-bound billing/scope/operating-driver/contract-conversion relation
    # can contain revenue words. It is not a routine accounting total; the
    # legacy rejector knows none of these opt-in relations.
    return reading_financial_only(text, fact)


def _admitted(unit: Any, reading: Mapping[str, Any], kind: str, *, fact: Any = None,
              is_heading: bool = False, table_qualified: bool = False,
              financial_only: bool | None = None) -> tuple[bool, Any]:
    fact = fact or detect_reading_business_fact(unit.raw_text)
    if fact.purpose in NON_OPERATING_PURPOSES or fact.purpose == "unassessed":
        return False, fact
    if kind == "operating_table" and not table_qualified:
        return False, fact
    if unit.source_role in _CONTEXT_ROLES or (kind != "operating_table" and
            (financial_only if financial_only is not None else _financial_only(unit.raw_text, fact))):
        return False, fact
    # Glyphs/page counters are observed text, not operating descriptions. A
    # numeric cell of an already qualified operating table is different: its
    # original headers, units and period travel in the complete dependency graph.
    if not fact.eligible:
        alphanumeric = "".join(character for character in unit.raw_text if character.isalnum())
        numeric_marker = bool(alphanumeric) and all(character.isnumeric() for character in alphanumeric)
        roman_marker = bool(re.fullmatch(r"[IVXLCDM]+", alphanumeric, re.IGNORECASE))
        letter_marker = bool(re.fullmatch(r"\s*[(\[（【]\s*[A-Za-z]\s*[)\]）】]\s*[.、:]?\s*", unit.raw_text))
        if not any(character.isalpha() for character in unit.raw_text) or numeric_marker:
            if kind != "operating_table" or not any(character.isdigit() for character in unit.raw_text):
                return False, fact
        if roman_marker or letter_marker:
            return False, fact
    if (is_heading or unit.unit_kind.endswith("_heading")) and not fact.eligible:
        return False, fact
    # Family/role are observed reading intent, not proof of any specific fact.
    # They permit descriptive business material without requiring a number or a
    # particular project duration. Unknown prose still needs an operating signal.
    scoped = reading.get("section_role") in _BUSINESS_ROLES
    descriptive = reading.get("family") in {"prospectus", "offering"}
    return bool(fact.eligible or scoped or kind == "operating_table" or
                (descriptive and kind in {"project", "operating_table"})), fact


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
                           work_budget: WorkBudget | None = None):
    """Container membership is not a claim that all prose is one atomic fact.

    Audit every source-owned prose member. Only the shared native continuity
    engine can group independent members into a bounded original-ID window.
    The final material owner is established before source-state recognition;
    the optional text callback is retained only for private diagnostic replay.
    """
    work_budget = work_budget if work_budget is not None else WorkBudget(DEFAULT_LIMITS["max_work_units"])
    observation = pipeline.get("observation", {}).get("units", ())
    work_budget.charge(2 * len(parsed.units) + len(observation)
                       + len(pipeline.get("non_selectable_unit_ids", ())) + 1)
    units = {unit.unit_id: unit for unit in parsed.units}
    profiles = pipeline["reading_plan"]["unit_profiles"]
    packages = pipeline["packages"]["packages"]
    # Package semantics cannot exempt original prose from physical continuity.
    # Tables and attributed Q&A retain their separate structural owners.
    prose_kinds = {"background", "paragraph_event", "risk"}
    audited_kinds = prose_kinds | {"project"}
    owners: dict[str, list[Mapping[str, Any]]] = {}
    owner_external_context = {}
    table_owners: set[int] = set()
    context_blocked: set[str] = set()
    other_members: set[str] = set()
    for package in packages:
        members = package.get("member_unit_ids", ())
        required = package.get("required_context_unit_ids", ())
        work_budget.charge(3 * len(members) + 2 * len(required)
                           + len(package.get("anchor_unit_ids", ())) + 1)
        external = set(required) - set(members)
        # Each source member can consume this external dependency only once.
        # Reserve actual edges before expanding, not only container count.
        work_budget.charge(len(members) * len(external))
        # A prose label does not erase a source-declared typed table. Preserve
        # its original header/note edges and anchors as one package. Local table
        # indices on another page/parent cannot certify the same table.
        table_members = [units[uid] for uid in members if uid in units
                         and units[uid].coordinates.table_index is not None]
        work_budget.charge(len(table_members))
        if package["kind"] in audited_kinds and table_members:
            table_keys = {(unit.source_id, unit.coordinates.page_number,
                           unit.coordinates.table_index) for unit in table_members}
            if len(table_keys) == 1:
                table_owners.add(id(package))
            else:
                context_blocked.update(members)
        owner_external_context[id(package)] = external
        if (package["kind"] in audited_kinds and id(package) not in table_owners
                and not package.get("truncated")):
            for uid in members:
                owners.setdefault(uid, []).append(package)
        else:
            other_members.update(members)
    excluded = set(pipeline.get("non_selectable_unit_ids", ()))
    headings: dict[str, set[str]] = {}
    section_for_unit = {}
    sections = pipeline.get("structure", {}).get("sections", ())
    section_index = {}
    duplicate_sections = set()
    for section in sections:
        sid = section.get("section_id")
        work_budget.charge(1 + len(section.get("heading_unit_ids", ())))
        # Older callers may declare one local section without an ID. Its
        # explicit headings are usable locally; it cannot become a named
        # ancestor or collide with a different anonymous section.
        if sid is not None:
            if sid in section_index:
                duplicate_sections.add(sid)
            section_index[sid] = section
    inherited: dict[str, tuple[frozenset[str], bool]] = {}
    for section in sections:
        sid = section.get("section_id")
        path, visiting = [], set()
        cursor = sid if sid is not None else section.get("parent_id")
        while cursor is not None and cursor not in inherited:
            work_budget.charge()
            if cursor in visiting or cursor not in section_index or cursor in duplicate_sections:
                inherited[cursor] = (frozenset(), False)
                break
            visiting.add(cursor)
            path.append(cursor)
            cursor = section_index[cursor].get("parent_id")
        actual_heads, valid = inherited.get(cursor, (frozenset(), True))
        for parent in reversed(path):
            own_heads = section_index[parent].get("heading_unit_ids", ())
            # Debit each real inherited edge before materialising its closure;
            # missing/cyclic parents cannot become a smaller complete context.
            work_budget.charge(len(actual_heads) + len(own_heads) + 1)
            actual_heads = actual_heads.union(own_heads)
            inherited[parent] = (actual_heads, valid)
        if sid is not None:
            actual_heads, valid = inherited[sid]
        else:
            own_heads = section.get("heading_unit_ids", ())
            work_budget.charge(len(actual_heads) + len(own_heads) + 1)
            actual_heads = actual_heads.union(own_heads)
        heads, body = section.get("heading_unit_ids", ()), section.get("body_unit_ids", ())
        work_budget.charge(1 + len(heads) + len(body) * (len(actual_heads) + 1))
        for uid in (*heads, *body):
            section_for_unit[uid] = sid
        for uid in body:
            if (not valid or uid not in units or any(
                    head not in units or units[head].source_id != units[uid].source_id
                    for head in actual_heads)):
                context_blocked.add(uid)
                continue
            headings.setdefault(uid, set()).update(actual_heads)

    def context(member_ids):
        result: set[str] = set()
        for uid in member_ids:
            result.update(headings.get(uid, ()))
            for owner in owners.get(uid, ()):
                # ParagraphDraft's first anchor is also marked required. This
                # is container bookkeeping, not a dependency on every later
                # fact. Preserve actual external headings/context only.
                result.update(owner_external_context[id(owner)])
        work_budget.charge(len(result) * max(1, len(result).bit_length()))
        return sorted(result - set(member_ids))

    exclusions = other_members | excluded | context_blocked
    views = []
    for unit in observation:
        uid = unit["unit_id"]
        if uid not in owners or uid in exclusions:
            views.append({**unit, "kind": "continuity_boundary"})
            continue
        projects = tuple(sorted(str(owner["package_id"]) for owner in owners[uid]
                                if owner["kind"] == "project"))
        if projects:
            # A physical line cannot silently bridge two independently named
            # projects just because they share a source section and font.
            hints = unit.get("hints", {})
            unit = {**unit, "hints": {**hints,
                "section_key": (native_section_key(hints, section_for_unit.get(uid)), projects)}}
        views.append(unit)
    provenance = {unit.unit_id: {"source_id": unit.source_id,
        "paragraph_index": unit.coordinates.paragraph_index,
        **{key: unit.metadata.get(key) for key in (
            "pdf_block", "block_sha256", "block_char_start", "block_char_end")}}
        for unit in parsed.units if unit.unit_kind == "pdf_text_block"}
    page_flow = None
    if parsed.mime_type == "application/pdf":
        diagnostics = pipeline.get("structure", {}).get("diagnostics", ())
        work_budget.charge(sum(1 + len(entry.get("unit_ids", ())) for entry in diagnostics)
                           + len(parsed.opaque_pages) + len(parsed.deferred_table_pages))
        furniture = frozenset(uid for entry in diagnostics if entry.get("code") == "REPEATED_RUNNING_HEADER"
                              for uid in entry.get("unit_ids", ()) if uid in units)
        page_flow = SourcePageFlow(furniture, independent_statement_start,
            coarse_complete=bool(parsed.page_count and parsed.pages_read == parsed.page_count and not parsed.errors),
            unproven_pages=frozenset((*parsed.opaque_pages, *parsed.deferred_table_pages)))
    continuity = build_native_continuity(views, provenance=provenance,
        sections=sections, unit_profiles=profiles, work_budget=work_budget, source_page_flow=page_flow)
    ranges: dict[tuple[str, int], list[tuple[int, int]]] = {}
    for entry in continuity["deferred_unit_ranges"]:
        ranges.setdefault((entry["source_id"], entry["page"]), []).append(
            (entry["first_ordinal"], entry["last_ordinal"]))
    ranges = {key: sorted(values) for key, values in ranges.items()}
    starts = {key: [a for a, _b in values] for key, values in ranges.items()}
    blocked: set[str] = set(context_blocked)
    if context_blocked:
        continuity = {**continuity, "complete": False}
    for index, wire in enumerate(observation):
        key = (wire.get("hints", {}).get("source_id"), wire.get("page"))
        intervals = ranges.get(key, ())
        point = bisect_right(starts.get(key, ()), wire.get("ordinal", -1)) - 1
        unexamined = continuity["unexamined_from_index"]
        if ((point >= 0 and wire["ordinal"] <= intervals[point][1])
                or (unexamined is not None and index >= unexamined)):
            if wire["unit_id"] in owners:
                blocked.add(wire["unit_id"])
    grouped: set[str] = set()
    generated = []
    joint_facts: dict[Any, Any] = {}
    dependent_statement = re.compile(
        r"该|上述|这一|此项|这些|其|尚未|未能|未经|并未|不代表|不意味着|"
        r"然而|但是|但|仍需|须|需先|如果|除非|未来|下半年|预计|预期|计划|将|拟|可能|"
        r"\b(?:this|these|that|those|it|however|but|not|never|unless|if|before|"
        r"still|required|requires|subject to|will|would|could|may|expect\w*|plan\w*)\b",
        re.IGNORECASE)
    cjk_character = re.compile(r"[\u3400-\u9fff]")
    cjk_punctuation = frozenset("。！？；，、：）》】”’（《【“‘")

    def linguistic_text(member_ids) -> str:
        # Declared language is a source category, not native token alignment.
        # Remove only our temporary separator at an actual CJK boundary. Latin
        # words, decimal quantities and unit tokens keep a whitespace boundary,
        # even if an English fragment was categorised as zh. Raw is untouched.
        result = ""
        for uid in member_ids:
            text = units[uid].raw_text
            if not result:
                result = text
                continue
            left, right = result.rstrip()[-1:], text.lstrip()[:1]
            cjk_boundary = bool(
                cjk_character.fullmatch(left) and (cjk_character.fullmatch(right) or right in cjk_punctuation)
                or cjk_character.fullmatch(right) and left in cjk_punctuation)
            result = result.rstrip() + ("" if cjk_boundary else " ") + text.lstrip()
        return result

    def statement_members(member_ids):
        # The continuity owner has already proven the native frame/scope and
        # closed the window. A terminator alone cannot detach a forward or
        # negative qualifier. Split only before an independently asserted,
        # complete issuer statement; keep all original units and their costs.
        statements = []
        pending = []
        for uid in member_ids:
            pending.append(uid)
            text = units[uid].raw_text.rstrip().rstrip("\"'”’）)]》")
            if text.endswith(("。", "！", "？", ".", "!", "?", ";", "；")):
                statements.append(pending)
                pending = []
        if pending:
            # The native owner cannot currently emit an open window, but keep
            # any future additive shape whole rather than guessing completion.
            return [member_ids]
        result = []
        current: list[str] = []
        for statement in statements:
            text = linguistic_text(statement)
            preceding = linguistic_text(current)
            work_budget.charge(8 * len(text))
            separate = (current and independent_statement_start(text)
                        and not dependent_statement.search(text)
                        and not dependent_statement.search(preceding))
            if separate:
                result.append(current)
                current = []
            current.extend(statement)
        if current:
            result.append(current)
        return result

    for window in continuity["windows"]:
        members = window["member_unit_ids"]
        if not set(members) <= units.keys() or set(members) & blocked:
            continue
        # A structured project's row, qualification note and original context
        # remain one semantic package. Physical prose audit must not flatten
        # that package into independently selectable rows or drop its notes.
        if any(owner["kind"] == "project" for uid in members for owner in owners.get(uid, ())):
            continue
        pieces = statement_members(members)
        for piece in pieces:
            # Structural closure establishes the material owner before meaning.
            # A linguistic join has no original coordinate system and cannot
            # supply operating states or refs on behalf of its first fragment.
            # Retain the old private diagnostic callback for replay tests. The
            # production owner never supplies it; its join never supplies refs
            # or source-state facts to the selection session.
            if classify is not None:
                diagnostic_fact = classify(linguistic_text(piece))
                if not diagnostic_fact.eligible:
                    continue
            pid = window["window_id"]
            if len(pieces) > 1:
                pid += ":statement:" + sha256("\0".join(piece).encode()).hexdigest()
            generated.append({"package_id": pid, "kind": "native_continuity",
                "member_unit_ids": piece, "anchor_unit_ids": list(piece),
                "required_context_unit_ids": context(piece)})
            grouped.update(piece)
    expanded = []
    seen: set[str] = set()
    window_for_member = {uid: window for window in continuity["windows"]
                         for uid in window["member_unit_ids"]}
    for package in packages:
        if package["kind"] == "project":
            members = set(package.get("member_unit_ids", ()))
            anchors = package.get("anchor_unit_ids", ())
            window_ids = set()
            windows = []
            for uid in package.get("anchor_unit_ids", ()):
                window = window_for_member.get(uid)
                if (window is not None and window["window_id"] not in window_ids
                        and set(window["member_unit_ids"]) <= members):
                    window_ids.add(window["window_id"])
                    windows.append(window["member_unit_ids"])
            support = set(anchors)
            for anchor in anchors:
                window = window_for_member.get(anchor)
                if window is not None and window["window_id"] in window_ids:
                    support.update(window["member_unit_ids"])
            # The existing public task contract has finite citation views. A
            # physical window expands original anchors inside the same project,
            # not into one new task/view for every anchor.
            ordered_support = list(dict.fromkeys(uid for uid in package.get("member_unit_ids", ())
                                                if uid in support))
            expanded.append({**package, **({"citation_support_views": [ordered_support],
                "native_analysis_views": windows} if windows and support <= members else {})})
            continue
        if (package["kind"] not in prose_kinds or package.get("truncated")
                or id(package) in table_owners):
            expanded.append(package)
            continue
        for uid in package.get("member_unit_ids", ()):
            if uid in seen or uid in grouped or uid in blocked:
                continue
            seen.add(uid)
            expanded.append({**package, "package_id": str(package["package_id"]) + ":" + uid,
                "member_unit_ids": [uid], "anchor_unit_ids": [uid],
                "required_context_unit_ids": context([uid])})
    return [*expanded, *generated], joint_facts, continuity, blocked


def _candidates(parsed: DocumentStructure, pipeline: Mapping[str, Any], *,
                work_budget: WorkBudget | None = None,
                _session_state: dict[str, Any] | None = None):
    from typing import cast

    from .narrative_native_ranges import native_range_unit
    from .narrative_operating_relations import SourceOperatingSession

    mutable_pipeline = cast(dict[str, Any], pipeline)
    mutable_pipeline.pop("_material_units", None)
    mutable_pipeline.pop("_carrier_origins", None)
    work_budget = work_budget if work_budget is not None else WorkBudget(DEFAULT_LIMITS["max_work_units"])
    try:
        # Reserve source closure indexes before constructing them. Geometry
        # below tightens its own ceiling on this same account, never a clone.
        work_budget.charge(2 * len(parsed.units) + len(pipeline.get("non_selectable_unit_ids", ())) + 1)
    except WorkBudgetExceeded:
        return [], {}, [], False, [{"package_id": "source-closure",
            "reason": "OPERATING_WORK_BUDGET", "known_unit_ids": [], "unexamined_from_index": 0}]
    units = {unit.unit_id: unit for unit in parsed.units}
    reading = pipeline["reading_plan"]["unit_profiles"]
    excluded = set(pipeline.get("non_selectable_unit_ids", ()))
    candidates: dict[str, EvidenceCandidate] = {}
    metadata: dict[str, dict[str, Any]] = {}
    eligible_packages = []
    withheld = []
    try:
        packages, _joint_facts, continuity, blocked = _prose_reading_packages(parsed, pipeline,
            work_budget=work_budget)
        sections = pipeline.get("structure", {}).get("sections", ())
        work_budget.charge(sum(1 + len(section.get("heading_unit_ids", ())) for section in sections))
        headings = {uid for section in sections for uid in section.get("heading_unit_ids", ())}
    except WorkBudgetExceeded:
        return [], {}, [], False, [{"package_id": "source-closure",
            "reason": "OPERATING_WORK_BUDGET", "known_unit_ids": [], "unexamined_from_index": 0}]
    # Qualify actual table rows before the context graph establishes cost and
    # closure. Rejected account rows are neither facts nor borrowed context.
    scoped_packages = []
    for package in packages:
        if package["kind"] != "operating_table":
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
        purpose = _qualified_table(package, units)
        if not purpose.eligible:
            if purpose.status == "incomplete":
                withheld.append({"package_id": str(package["package_id"]),
                                 "reason": purpose.reason, "known_unit_ids": sorted(all_ids)})
            continue
        body = [uid for uid in members if uid not in required]
        admitted_rows = {body[index] for index in purpose.eligible_row_indices}
        scoped_packages.append({**package,
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
        if package["kind"] != "native_continuity":
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
    session = SourceOperatingSession(units, work_budget=work_budget, contexts={},
        groups=analysis_groups, antecedents=antecedents, originals=original_units)
    # Readiness precedes both the graph and any fact/cache work: a product
    # deictic whose declaration is missing, ambiguous, truncated or outside
    # the combined original envelope defers only its own card.
    deferred_packages: set[int] = set()
    extra_context: dict[int, set[str]] = {}
    original_extra: dict[int, set[str]] = {}
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
        target_originals = [member for uid in package.get("member_unit_ids", ())
                            for member in original_members(uid)]
        context_originals = [member for uid in package.get("required_context_unit_ids", ())
                             for member in original_members(uid)]
        if not within_reference_envelope(target_originals, context_originals,
                                         sorted(needed_originals), original_units,
                                         expand=original_members):
            deferred_packages.add(index)
            withheld.append({"package_id": str(package["package_id"]),
                "reason": "REFERENCE_ENVELOPE", "known_unit_ids": sorted(needed_originals)})
            continue
        original_extra[index] = needed_originals
        extra_context[index] = {origins.get(entry, entry) for entry in needed_originals}
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
    session.contexts = {uid: tuple(sorted(ids)) for uid, ids in contexts.items()}
    graph = build_context_graph({**pipeline["packages"], "packages": budget_packages}, texts)
    if _session_state is not None:
        _session_state["session"] = session
    if not continuity["complete"]:
        withheld.append({"package_id": "native-continuity",
            "reason": "INCOMPLETE_NATIVE_CONTINUITY", "known_unit_ids": sorted(blocked)})
    def package_priority(entry):
        index, package = entry
        anchors = package.get("anchor_unit_ids", ()) or package.get("member_unit_ids", ())[:1]
        return (min((int(reading.get(uid, {}).get("priority", 2)) for uid in anchors), default=2), index)

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
        table_qualified = package["kind"] == "operating_table"
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
        elif package["kind"] == "operating_table":
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
            admitted, fact = _admitted(unit, view, package["kind"],
                                       fact=fact,
                                       financial_only=session.financial_only(uid),
                                       is_heading=uid in headings, table_qualified=table_qualified)
            if not admitted:
                continue
            anchors.append(uid)
            meaningful = fact.eligible or package["kind"] == "operating_table"
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
                             "required": tuple(sorted(set(previous.get("required", ())) | (required - {uid})))}
        if not anchors:
            continue
        eligible_packages.append(packages[index])
        for uid in required:
            if uid not in candidates:
                candidates[uid] = EvidenceCandidate(units[uid], (), ("reading_context",), 0)
                metadata[uid] = {"priority": 2, "topics": (), "context_only": True, "required": ()}
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
    deferred = []
    for entry in eligible:
        required = set(entry["member_unit_ids"]) | set(entry.get("required_context_unit_ids", ()))
        if not required <= selected.keys():
            deferred.append({"package_id": str(entry["package_id"]), "reason": "SELECTION_BUDGET"})
            continue
        ids = list(dict.fromkeys(pipeline["selected_span_ids"][uid]
                                 for uid in original if uid in required))
        digest = sha256(json.dumps(ids, separators=(",", ":")).encode()).hexdigest()
        citation_views = []
        seen_support = set()
        native_views = entry.get("citation_support_views")
        if entry["kind"] == "qa_exchange":
            declared = entry.get("anchor_unit_ids")
            answer_ids = {uid for uid in (declared if declared is not None else entry["member_unit_ids"])
                          if uid in original and original[uid].get("role") not in _CONTEXT_ROLES
                          and (declared is not None or original[uid].get("role") == "management")}
            # A question can establish attribution/context, never an answer's
            # factual support. Generic per-member native views may include Q;
            # narrow them to actual source-owned answer anchors, keeping the
            # complete question and all remaining members as dependencies.
            native_views = [list(dict.fromkeys(uid for uid in view if uid in answer_ids))
                            for view in native_views or [list(answer_ids)]]
            native_views = [view for view in native_views if view]
            if not native_views and answer_ids:
                native_views = [[uid for uid in entry["member_unit_ids"] if uid in answer_ids]]
        for native_support in native_views if native_views is not None else [
                list(entry.get("anchor_unit_ids", entry["member_unit_ids"]))]:
            if not native_support or not set(native_support) <= required:
                raise ValueError("native citation support must belong to its complete source package")
            support_set = {pipeline["selected_span_ids"][uid] for uid in native_support}
            support = [sid for sid in ids if sid in support_set]
            support_key = tuple(support)
            if support_key in seen_support:
                continue
            seen_support.add(support_key)
            citation_views.append({"support_evidence_ids": support,
                "context_evidence_ids": [sid for sid in ids if sid not in support_set]})
        groups.append({"group_id": "urn:company-wiki:reading-group:sha256:" + digest,
                       "kind": str(entry["kind"]), "section_role": str(entry.get("section_role") or "unknown"),
                       "evidence_ids": ids, "citation_views": citation_views})
    unread = _unread(pipeline["structure"], observation)
    # Coverage lists are diagnostic examples, not a second all-unit inventory.
    # Preserve full counts and mark truncation rather than persisting huge IDs.
    list_keys = ("opaque_pages", "deferred_pages", "deferred_unit_ids", "unassigned_unit_ids")
    unread["counts"] = {key: len(unread[key]) for key in list_keys}
    unread["limited"] = any(unread["counts"][key] > 128 for key in list_keys)
    for key in list_keys:
        if len(unread[key]) > 128:
            unread[key] = unread[key][:128]
    layout_coverage = dict(pipeline.get("layout_hints", {}).get("coverage", {}))
    if pipeline.get("native_layout_frontend") is not None:
        layout_coverage["native_frontend"] = pipeline["native_layout_frontend"]
    constraints = list(_SHARED_CONSTRAINTS)
    if any("table_structure_ambiguous" in span.quality_flags for span in package.evidence_spans):
        constraints.append("Fragments flagged table_structure_ambiguous do not prove column, period, "
                           "row-label or unit attribution. Use independently supported business prose; "
                           "leave unproven numeric interpretations unknown.")
    return {"schema_version": "du-production-reading/2", "reading_policy_version": version,
            "reading_policies": policies, "business_facets": facets,
            "constraints": constraints,
            "groups": groups, "unread": unread,
            "deferred": deferred, "layout_coverage": layout_coverage}


def _understand(parsed: DocumentStructure, *, title: str, kind: str, mime_type: str,
                work_budget: WorkBudget | None = None):
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
            work_budget=budget)
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


def select_reading_evidence(parsed: DocumentStructure, *, title: str,
                            existing_kind: str = "unknown", max_selected: int | None = None,
                            max_chars: int = MAX_READING_CHARS,
                            work_budget: WorkBudget | None = None) -> NarrativeEvidencePackage:
    route = route_document(title, existing_kind=existing_kind, max_selected=max_selected)
    mime_type = parsed.mime_type or ("text/plain" if route.document_kind == "investor_call_transcript" else
                                    "application/pdf" if parsed.page_count else "text/html")
    from company_wiki.resource_budget import new_document_work_budget
    budget = work_budget if work_budget is not None else new_document_work_budget()
    try:
        budget.charge()
        pipeline = _understand(parsed, title=title, kind=route.document_kind, mime_type=mime_type,
                               work_budget=budget)
    except WorkBudgetExceeded:
        return _deferred_selection(parsed, route)
    if pipeline.get("analysis_status") == "deferred":
        return _deferred_selection(parsed, route)
    session_state: dict[str, Any] = {}
    candidates, reading, eligible, graph_complete, withheld = _candidates(
        parsed, pipeline, work_budget=budget, _session_state=session_state)
    session = session_state["session"]
    origins = pipeline.get("_carrier_origins", {})
    dropped = 0
    for unit in parsed.units:
        uid = session.owner_for(origins.get(unit.unit_id, unit.unit_id))
        if budget.exhausted and uid not in session.facts:
            session.complete = False
            break
        financial = session.financial_only(uid)
        if financial is None:
            session.complete = False
            break
        dropped += financial
    # Semantic 'unassigned' is not an unread page. It must not defeat a fully
    # read and positively classified finance-only document's zero-model result.
    # A bounded reference deferral removes one card, not the rest of the
    # document: it is reported separately and does not downgrade coverage.
    blocking_withheld = [entry for entry in withheld
                         if entry.get("reason") not in _REFERENCE_DEFERRAL_REASONS]
    processing_complete = graph_complete and session.complete and not budget.exhausted and not blocking_withheld and not any(
        "BUDGET" in str(entry.get("code", "")) or "LIMIT_REACHED" in str(entry.get("code", ""))
        for entry in pipeline.get("diagnostics", ()))
    empty_may_skip = (not candidates and parsed.coverage_complete and processing_complete
                      and (dropped == len(parsed.units) or pipeline["route"].get("family") == "administrative"))
    effective_route = DocumentRoute(route.document_kind, route.selection_limit,
                                    route.empty_result_may_skip or empty_may_skip)
    material_parsed = replace(parsed, units=tuple(pipeline.get("_material_units", parsed.units)))
    result = finalize_selection(material_parsed, effective_route, candidates, group_ids={},
        heading_pattern=_NEVER_HEADING, dropped_financial_count=dropped,
        budget_policy=READING_BUDGET_POLICY, reading_metadata=reading, max_chars=max_chars)
    if not processing_complete:
        known_candidates = {item.unit.unit_id for item in candidates} | {
            uid for item in withheld for uid in item["known_unit_ids"]}
        count = len(known_candidates)
        result = replace(result, coverage_complete=False,
                         status="partial" if result.evidence_spans else "needs_review",
                         candidate_count=count, omitted_candidate_count=count - len(result.evidence_spans))
    if any(diagnostic["code"] == "work_budget_exhausted" for diagnostic in result.selection_diagnostics):
        result = replace(result, coverage_complete=False,
                         status="partial" if result.evidence_spans else "needs_review")
    pipeline["selected_span_ids"] = _selected_unit_spans(parsed, result, pipeline)
    # Preserve source bytes and IDs. The existing quality vocabulary carries
    # unresolved table attribution into every model view, without an IO gate.
    uncertain = {pipeline["selected_span_ids"][uid]
                 for entry in eligible
                 if entry["kind"] == "operating_table" and entry.get("table_binding_status") != "complete"
                 for uid in set(entry["member_unit_ids"]) - set(entry.get("required_context_unit_ids", ()))
                 if uid in pipeline["selected_span_ids"]}
    if uncertain:
        result = replace(result, evidence_spans=tuple(
            replace(span, quality_flags=tuple(dict.fromkeys((*span.quality_flags, "table_structure_ambiguous"))))
            if span.span_id in uncertain else span for span in result.evidence_spans))
    context = _context(pipeline, result, eligible)
    # Reference deferrals are the newest and the ones a reader must be able to
    # audit; put them at the front of the bounded list so a document dominated
    # by budget deferrals cannot hide them.
    reference_entries = [{"package_id": item["package_id"], "reason": item["reason"]}
                         for item in withheld
                         if item.get("reason") in _REFERENCE_DEFERRAL_REASONS]
    other_entries = [{"package_id": item["package_id"], "reason": item["reason"]}
                     for item in withheld
                     if item.get("reason") not in _REFERENCE_DEFERRAL_REASONS]
    context["deferred"] = reference_entries + context["deferred"] + other_entries
    context["deferred_count"] = len(context["deferred"])
    context["deferred_limited"] = context["deferred_count"] > 128
    context["deferred"] = context["deferred"][:128]
    context["selection_diagnostics"] = list(result.selection_diagnostics)
    dependencies = None
    try:
        dependency_port = import_module("company_wiki.document_understanding.decision_dependencies")
    except ModuleNotFoundError as exc:
        if exc.name != "company_wiki.document_understanding.decision_dependencies":
            raise
        context["selection_diagnostics"].append({"code": "DECISION_DEPENDENCIES_UNAVAILABLE", "count": 1})
    else:
        from company_wiki.document_understanding.decision_inventory import build_decision_trace
        dependencies = dependency_port.freeze_decision_dependencies(build_decision_trace(
            pipeline, used_facet_ids=[facet["id"] for facet in context["business_facets"]],
            source_parser_names=tuple({unit.parser_name for unit in parsed.units})))
    return replace(result, reading_context=context, reading_dependencies=dependencies)


def _deferred_selection(parsed: DocumentStructure, route: DocumentRoute) -> NarrativeEvidencePackage:
    return NarrativeEvidencePackage(source_id=parsed.source_id, source_sha256=parsed.source_sha256,
        document_kind=route.document_kind, status="needs_review", evidence_spans=(),
        selection_limit=route.selection_limit, candidate_count=0, dropped_financial_count=0,
        source_units=len(parsed.units), omitted_candidate_count=0, coverage_complete=False,
        selection_diagnostics=({"code": "work_budget_exhausted", "count": 1,
                               "detail": "unexamined source content remains unknown; original is unchanged"},))


__all__ = ["select_reading_evidence", "READING_SELECTOR_VERSION"]
