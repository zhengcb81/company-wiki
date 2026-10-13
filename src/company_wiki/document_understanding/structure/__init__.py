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

from collections.abc import Mapping
from typing import Any

from .contract import (
    SCHEMA_VERSION,
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
    observation: Mapping[str, Any], *, limits: Mapping[str, Any] | None = None
) -> dict:
    """Return the ``du-structure/1`` view of one ``du-input/1`` observation."""
    resolved = resolve_limits(limits)
    envelope, units = parse_observation(observation)
    diagnostics: list[dict] = []

    if not units:
        return _empty_result(envelope)

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

    section_build = build_sections(units, ordering, limits=resolved)
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

    paragraph_start = 0
    if qa_available(ordering.ordered):
        qa_drafts, qa_diagnostics = build_qa_exchanges(
            units,
            ordering,
            section_build.unit_section,
            limits=resolved,
            consumed=consumed,
        )
        diagnostics.extend(qa_diagnostics)
        for draft in qa_drafts:
            semantic_units.append(draft.as_wire())
            for unit_id in draft.member_ids:
                member_of.setdefault(unit_id, draft.semantic_id)

    project_drafts, project_diagnostics = build_projects(
        units,
        ordering,
        section_build.unit_section,
        limits=resolved,
        consumed=consumed,
    )
    diagnostics.extend(project_diagnostics)
    projects = list(project_drafts)

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

    for draft in projects:
        semantic_units.append(draft.as_wire())
        for unit_id in draft.member_ids:
            member_of.setdefault(unit_id, draft.semantic_id)
    for draft in table_drafts:
        semantic_units.append(draft.as_wire())
        for unit_id in draft.member_ids:
            member_of.setdefault(unit_id, draft.semantic_id)

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
    for draft in paragraph_drafts:
        semantic_units.append(draft.as_wire())
        for unit_id in draft.member_ids:
            member_of.setdefault(unit_id, draft.semantic_id)

    semantic_units = _stabilise_semantic_ids(
        semantic_units, {unit.unit_id: unit.ordinal for unit in units}
    )

    builder = RelationBuilder(
        {unit.unit_id for unit in units}, max_relations=resolved["max_relations"]
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

    coverage = _coverage(envelope, units, ordering, semantic_units, over_budget, resolved)
    coverage["complete"] = bool(
        coverage["complete"]
        and not over_budget
        and not any(
            item["code"] in {"WORK_BUDGET_EXCEEDED", "RELATION_BUDGET_EXCEEDED"}
            for item in diagnostics
        )
    )

    diagnostics.extend(_coverage_diagnostics(envelope, coverage, units))

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
        members = list(wire.get("member_unit_ids", ()))
        anchors = list(wire.get("anchor_unit_ids", ()))
        self.question_ids = anchors or members[:1]
        self.answer_ids = [unit for unit in members if unit not in set(self.question_ids)]


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
                "unit_ids": [
                    unit.unit_id for unit in units if unit.page == page
                ],
                "detail": f"page {page} produced no native text and is not covered",
            }
        )
    for page in coverage.get("deferred_pages", []):
        diagnostics.append(
            {
                "code": "DEFERRED_PAGE",
                "unit_ids": [
                    unit.unit_id for unit in units if unit.page == page
                ],
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
        key=lambda item: (item["code"], tuple(item.get("unit_ids", ())), item.get("detail", "")),
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
