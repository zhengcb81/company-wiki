"""Shared reading plan into the established candidate/budget/finalize path.

Format adapters have already read the original. This module owns admission and
selection, not IO, research conclusions, model calls or another task store.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from importlib import import_module
import json
import re
from typing import Any

from company_wiki.document_understanding.pipeline import understand_units
from company_wiki.document_understanding.selection_bridge import build_context_graph
from company_wiki.document_understanding.summary_input import _sent_policies, _unread, _SHARED_CONSTRAINTS

from .narrative_budget import READING_BUDGET_POLICY
from .narrative_business_policy import detect_reading_business_fact, reject_finance_only_text
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
_ACCOUNTING = re.compile(r"营业收入|营业成本|净利润|资产负债|每股收益|现金流量|货币资金|应收账款|"
                         r"\b(?:revenue|net income|earnings per share|cash flow|balance sheet)\b", re.IGNORECASE)


def _financial_only(text: str, fact: Any = None) -> bool:
    fact = fact or detect_reading_business_fact(text)
    # A source-bound billing/scope/operating-driver/contract-conversion relation
    # can contain revenue words. It is not a routine accounting total; the
    # legacy rejector knows none of these opt-in relations.
    if fact.financial_exempt:
        return False
    return reject_finance_only_text(text) or bool(
        _ACCOUNTING.search(text) and not fact.eligible)


def _admitted(unit: Any, reading: Mapping[str, Any], kind: str, *, fact: Any = None,
              is_heading: bool = False) -> tuple[bool, Any]:
    fact = fact or detect_reading_business_fact(unit.raw_text)
    if unit.source_role in _CONTEXT_ROLES or (kind != "operating_table" and _financial_only(unit.raw_text, fact)):
        return False, fact
    # Glyphs/page counters are observed text, not operating descriptions. A
    # numeric cell of an already qualified operating table is different: its
    # original headers, units and period travel in the complete dependency graph.
    alphanumeric = "".join(character for character in unit.raw_text if character.isalnum())
    numeric_marker = bool(alphanumeric) and all(character.isnumeric() for character in alphanumeric)
    roman_marker = bool(re.fullmatch(r"[IVXLCDM]+", alphanumeric, re.IGNORECASE))
    letter_marker = bool(re.fullmatch(r"\s*[(\[（【]\s*[A-Za-z]\s*[)\]）】]\s*[.、:]?\s*", unit.raw_text))
    if not any(character.isalpha() for character in unit.raw_text) or numeric_marker:
        if kind != "operating_table" or not any(character.isdigit() for character in unit.raw_text):
            return False, fact
    if not fact.eligible and (roman_marker or letter_marker):
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


def _candidates(parsed: DocumentStructure, pipeline: Mapping[str, Any]):
    units = {unit.unit_id: unit for unit in parsed.units}
    reading = pipeline["reading_plan"]["unit_profiles"]
    excluded = set(pipeline.get("non_selectable_unit_ids", ()))
    packages = pipeline["packages"]["packages"]
    texts = {uid: unit.raw_text for uid, unit in units.items()}
    graph = build_context_graph(pipeline["packages"], texts)
    candidates: dict[str, EvidenceCandidate] = {}
    metadata: dict[str, dict[str, Any]] = {}
    eligible_packages = []
    withheld = []
    facts: dict[str, Any] = {}
    headings = {uid for section in pipeline.get("structure", {}).get("sections", ())
                for uid in section.get("heading_unit_ids", ())}

    def classify(text: str):
        if text in facts:
            return facts[text]
        value = detect_reading_business_fact(text)
        # Source-local semantic memoization never deduplicates locators/spans,
        # changes a scope, or retains a document in global worker state.
        if len(facts) < 4096:
            facts[text] = value
        return value
    for index, package in enumerate(packages):
        members = list(dict.fromkeys(package["member_unit_ids"]))
        required = set(graph["groups"][index]["required_unit_ids"]) | set(members)
        # Incomplete closure is not a smaller complete fact. Missing original
        # references stay deferred; shadow duplicates alone may be withheld.
        if package.get("truncated") or not required <= units.keys() or required & excluded:
            withheld.append({"package_id": str(package["package_id"]),
                             "reason": "INCOMPLETE_OR_NONSELECTABLE_CONTEXT",
                             "known_unit_ids": sorted(required & units.keys())})
            continue
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
            admitted, fact = _admitted(unit, view, package["kind"], fact=classify(unit.raw_text),
                                       is_heading=uid in headings)
            if not admitted:
                continue
            anchors.append(uid)
            meaningful = fact.eligible or package["kind"] == "operating_table"
            role = view.get("section_role")
            scope_topics = (role,) if not meaningful and role in _BUSINESS_ROLES else ()
            topics = tuple(dict.fromkeys((*fact.topics, *scope_topics)))
            candidates[uid] = EvidenceCandidate(unit, topics,
                ("reading_plan", *fact.reasons), fact.score)
            previous = metadata.get(uid, {})
            metadata[uid] = {"priority": max(1, int(view.get("priority", 2))),
                             "topics": topics, "context_only": False,
                             "value_band": "meaningful_fact" if meaningful else "description",
                             "required": tuple(sorted(set(previous.get("required", ())) | (required - {uid})))}
        if not anchors:
            continue
        eligible_packages.append(package)
        for uid in required:
            if uid not in candidates:
                candidates[uid] = EvidenceCandidate(units[uid], (), ("reading_context",), 0)
                metadata[uid] = {"priority": 2, "topics": (), "context_only": True, "required": ()}
    # Stable source order, never text-only identity deduplication.
    ordered = tuple(candidates[unit.unit_id] for unit in parsed.units if unit.unit_id in candidates)
    return ordered, metadata, eligible_packages, graph["complete"], withheld


def _native_layout_summary(parsed: DocumentStructure) -> dict[str, Any] | None:
    """Persist bounded coverage, never transient words/cells or another inventory."""
    coverage = parsed.layout_coverage
    if coverage is None:
        return None
    result = {key: coverage[key] for key in (
        "feature_version", "complete", "processed_unit_count", "processed_page_count",
        "deferred_unit_count", "fine_element_count", "work_units") if key in coverage}
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
        ids = [pipeline["selected_span_ids"][uid] for uid in original if uid in required]
        digest = sha256(json.dumps(ids, separators=(",", ":")).encode()).hexdigest()
        groups.append({"group_id": "urn:company-wiki:reading-group:sha256:" + digest,
                       "kind": str(entry["kind"]), "section_role": str(entry.get("section_role") or "unknown"),
                       "evidence_ids": ids})
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
    return {"schema_version": "du-production-reading/1", "reading_policy_version": version,
            "reading_policies": policies, "business_facets": facets,
            "constraints": list(_SHARED_CONSTRAINTS),
            "groups": groups, "unread": unread,
            "deferred": deferred, "layout_coverage": layout_coverage}


def _understand(parsed: DocumentStructure, *, title: str, kind: str, mime_type: str):
    """Each immutable parent has its own structure; selection stays global.

    A captured API projection may contain several genuine original parents.
    Their adjacent fields must never manufacture cross-parent Q&A or tables.
    """
    parents: dict[str, list[Any]] = {}
    for unit in parsed.units:
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
            opaque_pages=parsed.opaque_pages, deferred_pages=parsed.deferred_table_pages)
        if native_frontend is not None:
            part["native_layout_frontend"] = native_frontend
            part["observation"]["metadata"]["native_layout_frontend_version"] = native_frontend.get("feature_version")
        parts.append(part)
    if len(parts) == 1:
        return parts[0]
    combined = deepcopy(parts[0])
    combined["observation"]["units"] = []
    combined["reading_plan"]["unit_profiles"] = {}
    combined["reading_plan"]["used_profiles"] = []
    combined["child_profiles"] = {}
    combined["packages"]["packages"] = []
    combined["non_selectable_unit_ids"] = []
    combined["diagnostics"] = []
    for source_id, part in zip(parents, parts):
        def scope_key(key: Any = None) -> str:
            return source_id + "|" + str(key or "root")
        combined["observation"]["units"].extend(part["observation"]["units"])
        combined["reading_plan"]["unit_profiles"].update({
            uid: {**view, "reading_profile_key": scope_key(view.get("reading_profile_key"))}
            for uid, view in part["reading_plan"]["unit_profiles"].items()})
        # Namespace actual parent and child decisions together. A compatibility
        # profile ID can denote more than one family (e.g. HK annual/interim);
        # neither policy assembly nor dependency tracing may guess it later.
        combined["child_profiles"][scope_key()] = part["profile"]
        combined["child_profiles"].update({scope_key(key): profile
                                          for key, profile in part.get("child_profiles", {}).items()})
        combined["reading_plan"]["used_profiles"].extend({**used,
            "reading_profile_key": scope_key(used.get("reading_profile_key"))}
            for used in part["reading_plan"].get("used_profiles", ()))
        combined["packages"]["packages"].extend({**entry,
            "package_id": source_id + ":" + str(entry["package_id"])} for entry in part["packages"]["packages"])
        combined["non_selectable_unit_ids"].extend(part.get("non_selectable_unit_ids", ()))
        combined["diagnostics"].extend(part.get("diagnostics", ()))
    combined["packages"]["non_selectable_unit_ids"] = combined["non_selectable_unit_ids"]
    coverage = combined["structure"]["coverage"]
    for key in ("deferred_unit_ids", "unassigned_unit_ids"):
        coverage[key] = [uid for part in parts for uid in part["structure"]["coverage"].get(key, ())]
    coverage["complete"] = all(part["structure"]["coverage"].get("complete") for part in parts)
    return combined


def select_reading_evidence(parsed: DocumentStructure, *, title: str,
                            existing_kind: str = "unknown", max_selected: int | None = None,
                            max_chars: int = MAX_READING_CHARS) -> NarrativeEvidencePackage:
    route = route_document(title, existing_kind=existing_kind, max_selected=max_selected)
    mime_type = parsed.mime_type or ("text/plain" if route.document_kind == "investor_call_transcript" else
                                    "application/pdf" if parsed.page_count else "text/html")
    pipeline = _understand(parsed, title=title, kind=route.document_kind, mime_type=mime_type)
    candidates, reading, eligible, graph_complete, withheld = _candidates(parsed, pipeline)
    dropped = sum(_financial_only(unit.raw_text) for unit in parsed.units)
    # Semantic 'unassigned' is not an unread page. It must not defeat a fully
    # read and positively classified finance-only document's zero-model result.
    processing_complete = graph_complete and not withheld and not any(
        "BUDGET" in str(entry.get("code", "")) or "LIMIT_REACHED" in str(entry.get("code", ""))
        for entry in pipeline.get("diagnostics", ()))
    empty_may_skip = (not candidates and parsed.coverage_complete and processing_complete
                      and (dropped == len(parsed.units) or pipeline["route"].get("family") == "administrative"))
    effective_route = DocumentRoute(route.document_kind, route.selection_limit,
                                    route.empty_result_may_skip or empty_may_skip)
    result = finalize_selection(parsed, effective_route, candidates, group_ids={},
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
    spans = {(span.source_id, span.coordinates, span.raw_text): span.span_id for span in result.evidence_spans}
    pipeline["selected_span_ids"] = {unit.unit_id: spans[(unit.source_id, unit.coordinates, unit.raw_text)]
        for unit in parsed.units if (unit.source_id, unit.coordinates, unit.raw_text) in spans}
    context = _context(pipeline, result, eligible)
    context["deferred"].extend({"package_id": item["package_id"], "reason": item["reason"]} for item in withheld)
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
            pipeline, used_facet_ids=[facet["id"] for facet in context["business_facets"]]))
    return replace(result, reading_context=context, reading_dependencies=dependencies)


__all__ = ["select_reading_evidence", "READING_SELECTOR_VERSION"]
