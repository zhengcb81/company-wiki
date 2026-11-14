"""Prepare bounded native source materials, before admission and selection.

This phase owns source containers and dependency closure. It never selects a
budget winner, writes an artifact, or calls a model. The orchestration facade
supplies its continuity backend explicitly for historical replay/testing.
"""
from __future__ import annotations
from bisect import bisect_right
from collections.abc import Mapping
from hashlib import sha256
import re
from typing import Any
from company_wiki.document_understanding.layout_hints.contract import WorkBudget, DEFAULT_LIMITS
from company_wiki.document_understanding.narrative_continuity import (
    NativeSourceContext, SourcePageFlow, build_native_continuity, native_section_key,
)
from company_wiki.document_understanding.operating_states.relations import (
    independent_statement_start, DEPENDENT_STATEMENT,
)
from company_wiki.document_understanding.text_boundaries import ends_complete_sentence
from .narrative_document import DocumentStructure

def prepare_native_materials(parsed: DocumentStructure, pipeline: Mapping[str, Any], classify=None, *,
                           work_budget: WorkBudget | None = None,
                           _native_contexts: Mapping[str, NativeSourceContext] | None = None,
                           continuity_builder=build_native_continuity):
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
    from .narrative_native_dependencies import collect_native_dependencies
    structure = pipeline.get("structure", {})
    furniture_ids = frozenset(uid for diagnostic in structure.get("diagnostics", ())
        if diagnostic.get("code") == "REPEATED_RUNNING_HEADER"
        for uid in diagnostic.get("unit_ids", ()))
    native_dependencies = collect_native_dependencies(structure.get("semantic_units", ()),
        originals=units, furniture_ids=furniture_ids, work_budget=work_budget)
    # Package semantics cannot exempt original prose from physical continuity.
    # Tables and attributed Q&A retain their separate structural owners.
    prose_kinds = {"background", "paragraph_event", "risk", "project"}
    audited_kinds = prose_kinds
    owners: dict[str, list[Mapping[str, Any]]] = {}
    owner_external_context = {}
    table_owners: set[int] = set()
    atomic_projects: set[int] = set()
    context_blocked: set[str] = set(native_dependencies.blocked)
    # Structure owns exact unresolved scope targets; material compilation must
    # not turn an omitted local introduction into smaller complete evidence.
    for diagnostic in structure.get("diagnostics", ()):
        if diagnostic.get("code") not in {"SOURCE_SCOPE_UNPROVEN", "SOURCE_SCOPE_LIMIT_REACHED"}:
            continue
        targets = diagnostic.get("unit_ids", ())
        work_budget.charge(1 + len(targets))
        context_blocked.update(uid for uid in targets
                               if uid in units and units[uid].source_id == parsed.source_id)
    other_members: set[str] = set()
    table_furniture = {unit["unit_id"] for unit in observation
                       if unit.get("kind") in {"table_row", "table_header", "table_caption"}}
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
        # Project row/header/note dependencies are affirmative structural
        # proof. A plain project heading with prose has no such required IDs;
        # it must not become the sole eligibility gate for all its body.
        if package["kind"] == "project" and (required or any(uid in table_furniture for uid in members)):
            atomic_projects.add(id(package))
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

    # Retain the entire source hierarchy, but distinguish generic navigation
    # from mandatory semantic prose. Source-native list heads (business/period/
    # service) positively establish their own ancestry; only policy-exact outer
    # navigation titles can be omitted. Specific regions/units/qualifiers and
    # independent table/deictic/qualification edges are never removed here.
    from company_wiki.document_understanding.profiles.registry import is_generic_navigation_heading
    work_budget.charge(1 + len(sections))
    native_heads, navigation_heads = set(), set()
    for section in sections:
        ids = section.get("heading_unit_ids", ())
        work_budget.charge(1 + len(ids))
        if "native_numbered_list" in section.get("basis", ()):
            from .narrative_business_policy import detect_reading_business_fact
            # Structural numbering alone does not supply a subject. Observe
            # each native head once, never once per descendant or candidate.
            for uid in ids:
                if uid in units:
                    work_budget.charge()
                    if detect_reading_business_fact(units[uid].raw_text, work_budget=work_budget).eligible:
                        native_heads.add(uid)
        else:
            for uid in ids:
                if uid in units:
                    work_budget.charge(8 * len(units[uid].raw_text) + 64)
                    if is_generic_navigation_heading(units[uid].raw_text):
                        navigation_heads.add(uid)

    def context(member_ids):
        result: set[str] = set()
        for uid in member_ids:
            own_heads = headings.get(uid, set())
            native_context_ids = native_dependencies.context_for(uid)
            work_budget.charge(1 + len(own_heads) + len(native_context_ids))
            if own_heads.intersection(native_heads):
                own_heads = own_heads - navigation_heads
            own = set(own_heads) | set(native_context_ids)
            for owner in owners.get(uid, ()):
                # ParagraphDraft's first anchor is container bookkeeping,
                # not a dependency on every later fact.
                own.update(owner_external_context[id(owner)])
            result.update(own)
        work_budget.charge(len(result) * max(1, len(result).bit_length()))
        return sorted(result - set(member_ids))

    def native_fields(member_ids):
        work_budget.charge(1 + len(member_ids))
        physical: set[str] = set()
        affected = []
        proof_rows = {}
        proof_targets: set[str] = set()
        for uid in member_ids:
            references = native_dependencies.source_for(uid)
            work_budget.charge(1 + len(references))
            physical.update(references)
            proofs = native_dependencies.proofs_for(uid)
            work_budget.charge(len(proofs))
            proof_rows.update({(row["left"], row["right"]): row for row in proofs})
            nested_proof_targets = native_dependencies.proof_targets_for(uid)
            work_budget.charge(len(nested_proof_targets))
            proof_targets.update(nested_proof_targets)
            if references or native_dependencies.context_for(uid):
                affected.append(uid)
        return {"_native_source_original_ids": sorted(physical),
                "_native_dependency_targets": affected,
                "_native_source_proof_targets": sorted(proof_targets),
                "_native_source_proofs": tuple(proof_rows.values())} if affected else {}

    exclusions = other_members | excluded | context_blocked
    work_budget.charge(len(observation))
    observed_kinds = {}
    views = []
    for unit in observation:
        uid = unit["unit_id"]
        observed_kinds[uid] = unit.get("kind")
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
        "observed_kind": observed_kinds.get(unit.unit_id),
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
    continuity = continuity_builder(views, provenance=provenance,
        sections=sections, unit_profiles=profiles, work_budget=work_budget, source_page_flow=page_flow,
        source_contexts=_native_contexts)
    if native_dependencies.diagnostics:
        continuity["native_dependency_diagnostics"] = native_dependencies.diagnostics
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
    dependent_statement = DEPENDENT_STATEMENT
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

    def source_statement_closed(uid: str) -> bool:
        return ends_complete_sentence(units[uid].raw_text)

    def statement_members(member_ids):
        # The continuity owner has already proven the native frame/scope and
        # closed the window. A terminator alone cannot detach a forward or
        # negative qualifier. Split only before an independently asserted,
        # complete issuer statement; keep all original units and their costs.
        statements = []
        pending = []
        for uid in member_ids:
            pending.append(uid)
            if ends_complete_sentence(units[uid].raw_text):
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
        members = list(window["member_unit_ids"])
        if not set(members) <= units.keys():
            continue
        withheld_members = [index for index, uid in enumerate(members) if uid in blocked]
        if withheld_members:
            prefix_end = next((index for index, uid in enumerate(members) if uid not in blocked),
                              len(members))
            # A deferred prefix remains withheld. A later source-complete
            # statement may still stand on its own when an observed terminal
            # boundary separates it from that prefix and native continuity
            # proves the suffix members. Structural/context failures are not
            # recoverable through this path.
            if (prefix_end == 0
                    or withheld_members != list(range(prefix_end))
                    or not source_statement_closed(members[prefix_end - 1])):
                continue
            suffix = members[prefix_end:]
            if (not suffix or any(uid in context_blocked for uid in suffix)
                    or not source_statement_closed(suffix[-1])
                    or dependent_statement.search(linguistic_text([suffix[0]]))):
                continue
            members = suffix
        # Actual row/header/note projects retain their existing atomic
        # source semantics; plain project prose uses independent statements.
        if any(id(owner) in atomic_projects for uid in members for owner in owners.get(uid, ())):
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
                "_paragraph_membership_only": any(edge.get("basis") == "source_exact_paragraph_membership"
                    for edge in window.get("proof", ())),
                "required_context_unit_ids": context(piece), **native_fields(piece)})
            grouped.update(piece)
    expanded = []
    seen: set[str] = set()
    window_for_member = {uid: window for window in continuity["windows"]
                         for uid in window["member_unit_ids"]}
    for package in packages:
        if id(package) in atomic_projects:
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
                "required_context_unit_ids": context([uid]), **native_fields([uid])})
    return [*expanded, *generated], joint_facts, continuity, blocked | set(native_dependencies.blocked)
