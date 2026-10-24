"""Pure structure builder for the document-understanding upgrade.

``build_structure`` organises the locator-bearing units of one already
normalised source into sections, semantic units and relations.  It is a pure
function of its input mapping: it opens no file, reads no configuration, calls
no model, and consults no clock, so the same observation always yields the same
mapping.

The output deliberately carries unit *references*, not text.  A consumer that
needs the original text replays the source locator through the existing read
path, which keeps this layer free of a second copy of the document.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..layout_hints.contract import WorkBudget, WorkBudgetExceeded
from ..narrative_continuity import NativeSourceContext
from ._work import WorkPlan, reserve

from .contract import (
    SCHEMA_VERSION,
    StructureInputError,
    parse_observation,
    resolve_limits,
)
from . import layout as layout_mod
from .paragraphs import build_paragraph_units
from .projects import build_projects
from .qa import build_qa_exchanges, qa_available
from .relations import (
    RelationBuilder,
    continuation_relations,
    header_and_footnote_relations,
    language_lane_relations,
    question_answer_relations,
)
from .sections import build_sections
from .tables import build_operating_tables

# The lane exposes exactly one public function.  Everything else in this module
# is an implementation detail that ROOT must not depend on.
__all__ = ["build_structure"]

_LANGUAGE_FAMILY_MAP = {"zh": "zh", "en": "en"}


def build_structure(
    observation: Mapping[str, Any],
    *,
    limits: Mapping[str, Any] | None = None,
    work_budget: WorkBudget | None = None,
    native_context: NativeSourceContext | None = None,
) -> dict:
    """Return the ``du-structure/1`` view of one ``du-input/1`` observation."""
    if work_budget is None:
        return _build_structure(observation, limits=limits, native_context=native_context)
    # Limits remain the old positive input contract, independent of remaining
    # shared work. Validate only this constant-size envelope before charging.
    resolve_limits(limits)
    if (
        not isinstance(observation, Mapping)
        or observation.get("schema_version") != "du-input/1"
    ):
        raise StructureInputError("schema_version must be 'du-input/1'")
    source = observation.get("source_ref")
    if (
        not isinstance(source, Mapping)
        or not isinstance(source.get("source_id"), str)
        or not source.get("source_id")
    ):
        raise StructureInputError("source_ref.source_id is required")
    raw_units = observation.get("units")
    if isinstance(raw_units, (str, bytes)) or not isinstance(raw_units, Sequence):
        raise StructureInputError("units must be a sequence")
    state: dict[str, Any] = {
        "sections": [],
        "semantic_units": [],
        "relations": [],
        "diagnostics": [],
        "completed_stage": "none",
    }
    try:
        work_budget.charge()
        return _build_structure(
            observation, limits=limits, work_budget=work_budget, state=state,
            native_context=native_context
        )
    except WorkBudgetExceeded:
        return _partial_structure(observation, state, work_budget)


def _partial_structure(observation, state, budget):
    """Constant-size failure projection over already committed stage results."""
    source = observation["source_ref"]
    coverage = observation.get("coverage")
    coverage = coverage if isinstance(coverage, Mapping) else {}
    native = coverage.get("native_scan", "unavailable")
    if native not in {"complete", "partial", "unavailable"}:
        native = "unavailable"
    raw_units = observation.get("units", ())
    return {
        "schema_version": SCHEMA_VERSION,
        "source_ref": {
            "source_id": source["source_id"],
            "source_sha256": source.get("source_sha256"),
        },
        "sections": state["sections"],
        "semantic_units": state["semantic_units"],
        "relations": state["relations"],
        "coverage": {
            "native_scan": native,
            "complete": False,
            "source_unit_count": len(raw_units),
            "structured_unit_count": len(state["semantic_units"]),
            "unassigned_unit_ids": [],
            "deferred_unit_ids": [],
            "excluded_furniture_unit_ids": [],
            "opaque_pages": [],
            "deferred_pages": [],
            "unobserved_ids_limited": True,
            "source_opaque_page_count": len(coverage["opaque_pages"])
            if isinstance(coverage.get("opaque_pages"), (list, tuple))
            else None,
            "source_deferred_page_count": len(coverage["deferred_pages"])
            if isinstance(coverage.get("deferred_pages"), (list, tuple))
            else None,
            "completed_stage": state["completed_stage"],
            "work_used": budget.used,
        },
        "diagnostics": [
            {
                "code": "WORK_BUDGET_EXCEEDED",
                "unit_ids": [],
                "detail": "structure work stopped; only closed committed stages are published",
            }
        ],
    }


def _build_structure(observation, *, limits=None, work_budget=None, state=None, native_context=None):
    resolved = resolve_limits(limits)
    work = WorkPlan(work_budget) if work_budget is not None else None
    envelope, units = parse_observation(observation, work=work)
    from .table_purpose import attach_native_row_headers
    attach_native_row_headers(envelope.get('native_tables', ()), units, work_budget=work_budget)
    diagnostics: list[dict] = []

    if not units:
        return _empty_result(envelope)

    if work is not None:
        work.stage(passes=6, sorts=2)  # layout indexes, furniture/text, page ordering
    ordering = layout_mod.order_units(units)
    if "ordinal_only" in ordering.evidence:
        diagnostics.append(
            {
                "code": "NO_LAYOUT_EVIDENCE",
                "unit_ids": [unit.unit_id for unit in units[:5]],
                "detail": "no bbox, column, heading level or DOM path was available",
            }
        )

    over_budget = len(units) > resolved["max_units"]
    work_units = len(units) * max(1, len(ordering.evidence))
    if work_units > resolved["max_work_units"]:
        diagnostics.append(
            {
                "code": "WORK_BUDGET_EXCEEDED",
                "unit_ids": [],
                "detail": (
                    f"estimated {work_units} work units exceed "
                    f"max_work_units={resolved['max_work_units']}"
                ),
            }
        )

    if ordering.toc_ids:
        diagnostics.append(
            {
                "code": "TOC_ENTRIES_DETECTED",
                "unit_ids": sorted(ordering.toc_ids),
                "detail": "table-of-contents entries are excluded from body sections",
            }
        )
    if ordering.running_header_ids:
        diagnostics.append(
            {
                "code": "REPEATED_RUNNING_HEADER",
                "unit_ids": sorted(ordering.running_header_ids),
                "detail": "text repeating at a page edge is page furniture, not body",
            }
        )

    if work is not None:
        work.stage(passes=4, sorts=1)  # section membership, roles and layout checks
    section_build = build_sections(units, ordering, limits=resolved, native_context=native_context)
    if state is not None:
        state["sections"] = [
            _section_wire(section) for section in section_build.sections
        ]
        state["completed_stage"] = "sections"
    diagnostics.extend(section_build.diagnostics)

    if not any(section.heading_ids for section in section_build.sections):
        diagnostics.append(
            {
                "code": "NO_SECTION_HEADINGS",
                "unit_ids": [],
                "detail": "no heading evidence produced a real section",
            }
        )

    consumed: set[str] = set(ordering.toc_ids) | set(ordering.running_header_ids)
    semantic_units: list[dict] = []
    member_of: dict[str, str] = {}

    ordinal_of = {unit.unit_id: unit.ordinal for unit in units}

    def commit_semantics(stage):
        if state is not None:
            # Independent shells: final ID stabilisation must not mutate a
            # previously committed stage. Open questions stay unpublished.
            reserve(
                work_budget,
                len(units)
                + len(semantic_units) * (1 + len(semantic_units).bit_length()),
            )
            closed = [
                dict(unit)
                for unit in semantic_units
                if unit["completeness"] == "complete"
            ]
            state["semantic_units"] = _stabilise_semantic_ids(closed, ordinal_of)
            state["completed_stage"] = stage

    paragraph_start = 0
    if work is not None:
        work.stage(passes=3)  # QA discovery and closed exchange members
    if qa_available(ordering.ordered):
        qa_drafts, qa_diagnostics = build_qa_exchanges(
            units,
            ordering,
            section_build.unit_section,
            limits=resolved,
            consumed=consumed,
        )
        diagnostics.extend(qa_diagnostics)
        for qa_draft in qa_drafts:
            semantic_units.append(qa_draft.as_wire())
            for unit_id in qa_draft.member_ids:
                member_of.setdefault(unit_id, qa_draft.semantic_id)

    commit_semantics("qa")
    if work is not None:
        work.stage(passes=4)  # project headers, bounded carry and membership
    project_drafts, project_diagnostics = build_projects(
        units,
        ordering,
        section_build.unit_section,
        limits=resolved,
        consumed=consumed,
    )
    diagnostics.extend(project_diagnostics)
    projects = list(project_drafts)

    if work is not None:
        work.stage(passes=5, sorts=1)  # scoped table rows, labels and qualification
    table_drafts, table_diagnostics = build_operating_tables(
        units,
        ordering,
        section_build.unit_section,
        limits=resolved,
        consumed=consumed,
    )
    diagnostics.extend(table_diagnostics)

    if len(projects) > 1:
        projects = _resolve_project_overlap(projects, diagnostics)

    for project_draft in projects:
        semantic_units.append(project_draft.as_wire())
        for unit_id in project_draft.member_ids:
            member_of.setdefault(unit_id, project_draft.semantic_id)
    for table_draft in table_drafts:
        semantic_units.append(table_draft.as_wire())
        for unit_id in table_draft.member_ids:
            member_of.setdefault(unit_id, table_draft.semantic_id)

    commit_semantics("projects_and_tables")
    if work is not None:
        work.stage(passes=3)  # paragraph classification and packages
    section_roles = {
        section.section_id: section.section_role for section in section_build.sections
    }
    paragraph_drafts, paragraph_diagnostics = build_paragraph_units(
        units,
        ordering,
        section_build.unit_section,
        section_roles,
        limits=resolved,
        consumed=consumed,
        start_index=paragraph_start,
    )
    diagnostics.extend(paragraph_diagnostics)
    for paragraph_draft in paragraph_drafts:
        semantic_units.append(paragraph_draft.as_wire())
        for unit_id in paragraph_draft.member_ids:
            member_of.setdefault(unit_id, paragraph_draft.semantic_id)

    commit_semantics("semantics")
    if work is not None:
        work.stage(passes=2, sorts=1)  # final IDs and member/anchor references
    semantic_units = _stabilise_semantic_ids(semantic_units, ordinal_of)

    if work is not None:
        work.stage(passes=7, sorts=2)  # relation indexes, bounded adjacent checks
    builder = RelationBuilder(
        {unit.unit_id for unit in units},
        max_relations=resolved["max_relations"],
        work_budget=work_budget,
    )
    continuation_relations(builder, units, ordering, _member_map(semantic_units))
    header_and_footnote_relations(builder, units, ordering)
    question_answer_relations(
        builder,
        [
            _ExchangeView(unit)
            for unit in semantic_units
            if unit["kind"] == "qa_exchange"
        ],
    )
    language_lane_relations(builder, units, ordering)
    builder.check_acyclic()
    diagnostics.extend(builder.diagnostics)
    if state is not None:
        state["relations"] = [dict(item) for item in builder.relations()]
        state["completed_stage"] = "relations"
    if work is not None:
        work.stage(passes=4, sorts=3)  # coverage, diagnostics and output ordering
        pages = envelope["coverage"]
        reserve(
            work_budget,
            (len(pages.get("opaque_pages", [])) + len(pages.get("deferred_pages", [])))
            * (1 + len(units)),
        )

    coverage = _coverage(
        envelope, units, ordering, semantic_units, over_budget, resolved
    )
    coverage["complete"] = bool(
        coverage["complete"]
        and not over_budget
        and not any(
            item["code"] in {"WORK_BUDGET_EXCEEDED", "RELATION_BUDGET_EXCEEDED"}
            for item in diagnostics
        )
    )

    diagnostics.extend(_coverage_diagnostics(envelope, coverage, units))

    for semantic in semantic_units:
        members = semantic.get("member_unit_ids", ())
        reserve(work_budget, 1 + len(members))
        context_by_unit: dict[str, list[str]] = {}
        source_by_unit: dict[str, list[str]] = {}
        proofs_by_unit: dict[str, list[dict[str, Any]]] = {}
        for uid in members:
            required = section_build.required_context_by_unit_id.get(uid, ())
            source_required = section_build.required_source_by_unit_id.get(uid, ())
            proofs = section_build.source_proofs_by_unit_id.get(uid, ())
            reserve(work_budget, len(required) + len(source_required)
                    + sum(1 + len(proof) + len(proof["furniture_unit_ids"]) for proof in proofs))
            if required:
                context_by_unit[uid] = list(required)
            if source_required:
                source_by_unit[uid] = list(source_required)
            if proofs:
                proofs_by_unit[uid] = [dict(proof, furniture_unit_ids=list(proof["furniture_unit_ids"]))
                                      for proof in proofs]
        if context_by_unit:
            semantic["required_context_by_unit_id"] = context_by_unit
        if source_by_unit:
            semantic["required_source_unit_ids_by_unit_id"] = source_by_unit
        if proofs_by_unit:
            semantic["native_source_proofs_by_unit_id"] = proofs_by_unit

    return {
        "schema_version": SCHEMA_VERSION,
        "source_ref": envelope["source_ref"],
        "sections": [_section_wire(section) for section in section_build.sections],
        "semantic_units": semantic_units,
        "relations": [dict(relation) for relation in builder.relations()],
        "coverage": coverage,
        "diagnostics": _sorted_diagnostics(diagnostics),
    }


class _ExchangeView:
    """Adapter so relation building can read question/answer ids uniformly."""

    __slots__ = ("question_ids", "answer_ids")

    def __init__(self, wire: Mapping[str, Any]) -> None:
        # QaDraft's anchors are the actual answer evidence; every question
        # fragment is required context. Do not infer roles from member order:
        # native record fields can be emitted answer-first.
        self.question_ids = list(wire.get("required_context_unit_ids", ()))
        self.answer_ids = list(wire.get("anchor_unit_ids", ()))


def _member_map(semantic_units) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for unit in semantic_units:
        for unit_id in unit["member_unit_ids"]:
            mapping.setdefault(unit_id, unit["semantic_id"])
    return mapping


def _resolve_project_overlap(projects, diagnostics: list[dict]):
    """Keep the earlier package when two projects claim the same anchor."""
    seen: dict[str, dict] = {}
    kept = []
    for draft in projects:
        anchor = draft.anchor_ids[0] if draft.anchor_ids else None
        if anchor is not None and anchor in seen:
            diagnostics.append(
                {
                    "code": "PROJECT_ANCHOR_CONFLICT",
                    "unit_ids": [anchor],
                    "detail": "two project packages claimed the same anchor unit",
                }
            )
            continue
        if anchor is not None:
            seen[anchor] = draft
        kept.append(draft)
    return kept


def _stabilise_semantic_ids(
    semantic_units: list[dict], ordinal_of: Mapping[str, int] | None = None
) -> list[dict]:
    """Renumber ids deterministically, ordered by document position.

    The ordering key is the input ordinal of the package's first member.  It
    must not be the ``unit_id`` string: unit ids are content hashes, so sorting
    on them orders packages by hash value, which is indistinguishable from
    random.  That ordering is what a consumer sees when it reads packages in
    order, so a hash order would make "read the important chapters first"
    silently mean "read them in hash order".
    """
    ordinal_of = ordinal_of or {}

    def position(unit: dict) -> tuple[int, str, str]:
        members = unit.get("member_unit_ids") or []
        first = min(
            (ordinal_of.get(member, 1 << 30) for member in members),
            default=1 << 30,
        )
        return (first, unit["kind"], unit["semantic_id"])

    ordered = sorted(semantic_units, key=position)
    for index, unit in enumerate(ordered, start=1):
        unit["semantic_id"] = f"m{index}"
        for key in ("member_unit_ids", "anchor_unit_ids", "required_context_unit_ids"):
            unit[key] = list(dict.fromkeys(unit.get(key, ())))
    return ordered


def _section_wire(section) -> dict:
    return {
        "section_id": section.section_id,
        "parent_id": section.parent_id,
        "heading_unit_ids": list(section.heading_ids),
        "body_unit_ids": list(section.body_ids),
        "section_role": section.section_role,
        "language": section.language,
        "confidence": section.confidence,
        "basis": list(section.basis),
    }


def _coverage(
    envelope: Mapping[str, Any],
    units,
    ordering: layout_mod.Ordering,
    semantic_units,
    over_budget: bool,
    resolved: Mapping[str, int],
) -> dict:
    assigned = {
        unit_id for unit in semantic_units for unit_id in unit["member_unit_ids"]
    }
    known = {unit.unit_id for unit in units}
    unassigned = sorted(unit_id for unit_id in known if unit_id not in assigned)
    deferred = sorted(set(ordering.toc_ids) | set(ordering.running_header_ids))

    raw_coverage = envelope["coverage"]
    native_scan = raw_coverage.get("native_scan")
    if native_scan not in {"complete", "partial", "unavailable"}:
        native_scan = "unavailable"
    opaque_pages = [
        page for page in raw_coverage.get("opaque_pages", []) if isinstance(page, int)
    ]
    deferred_pages = [
        page for page in raw_coverage.get("deferred_pages", []) if isinstance(page, int)
    ]

    complete = not over_budget and not deferred_pages
    if native_scan == "unavailable":
        complete = False

    return {
        "native_scan": native_scan,
        "structured_unit_count": len(semantic_units),
        "unassigned_unit_ids": unassigned,
        "deferred_unit_ids": deferred,
        "opaque_pages": opaque_pages,
        "deferred_pages": deferred_pages,
        "excluded_furniture_unit_ids": sorted(
            set(ordering.toc_ids) | set(ordering.running_header_ids)
        ),
        "complete": complete,
        "limits": dict(resolved),
    }


def _coverage_diagnostics(
    envelope: Mapping[str, Any], coverage: Mapping[str, Any], units
) -> list[dict]:
    diagnostics: list[dict] = []
    for page in coverage["opaque_pages"]:
        diagnostics.append(
            {
                "code": "OPAQUE_PAGE",
                "unit_ids": [unit.unit_id for unit in units if unit.page == page],
                "detail": f"page {page} produced no native text and is not covered",
            }
        )
    for page in coverage.get("deferred_pages", []):
        diagnostics.append(
            {
                "code": "DEFERRED_PAGE",
                "unit_ids": [unit.unit_id for unit in units if unit.page == page],
                "detail": f"page {page} is deferred by the caller's read budget",
            }
        )
    if coverage["native_scan"] != "complete":
        diagnostics.append(
            {
                "code": "NATIVE_SCAN_INCOMPLETE",
                "unit_ids": [],
                "detail": f"native_scan={coverage['native_scan']}",
            }
        )
    return diagnostics


def _sorted_diagnostics(diagnostics: list[dict]) -> list[dict]:
    deduped: dict[tuple, dict] = {}
    for item in diagnostics:
        key = (item["code"], tuple(item.get("unit_ids", ())), item.get("detail", ""))
        deduped.setdefault(key, item)
    return sorted(
        deduped.values(),
        key=lambda item: (
            item["code"],
            tuple(item.get("unit_ids", ())),
            item.get("detail", ""),
        ),
    )


def _empty_result(envelope: Mapping[str, Any]) -> dict:
    raw_coverage = envelope["coverage"]
    native_scan = raw_coverage.get("native_scan")
    if native_scan not in {"complete", "partial", "unavailable"}:
        native_scan = "unavailable"
    return {
        "schema_version": SCHEMA_VERSION,
        "source_ref": envelope["source_ref"],
        "sections": [],
        "semantic_units": [],
        "relations": [],
        "coverage": {
            "native_scan": native_scan,
            "structured_unit_count": 0,
            "unassigned_unit_ids": [],
            "deferred_unit_ids": [],
            "opaque_pages": list(raw_coverage.get("opaque_pages", [])),
            "deferred_pages": list(raw_coverage.get("deferred_pages", [])),
            "excluded_furniture_unit_ids": [],
            "complete": False,
            "limits": dict(resolve_limits(None)),
        },
        "diagnostics": [
            {
                "code": "NO_UNITS",
                "unit_ids": [],
                "detail": "the observation carried no narrative units",
            }
        ],
    }


__all__ = ["build_structure"]
