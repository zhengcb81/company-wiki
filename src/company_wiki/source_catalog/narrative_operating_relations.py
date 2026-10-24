"""Call-scoped operating facts over final source-owned material units.

No parsing, IO, registry or extra work balance. The source owner fixes native
carriers and structural context first; consumers share the resulting facts.
"""
from collections.abc import Mapping
from dataclasses import replace
from bisect import bisect_right
from itertools import chain
import re
from typing import Any

from company_wiki.document_understanding.layout_hints.contract import WorkBudget, WorkBudgetExceeded
from company_wiki.document_understanding.operating_states.relations import OperatingRelationSession
from company_wiki.document_understanding.operating_states.product_reference import (
    find_product_deictic, head_class, product_head_spans,
)
from company_wiki.document_understanding.operating_states.text_view import strip_connector

from .n6_candidate_operating_facts import OperatingFact
from .narrative_business_disclosures import is_backward_plan_qualification
from .narrative_revenue_guidance import (
    is_explicit_backward_revenue_guidance_premise,
    revenue_guidance_premise,
)
from .narrative_business_policy import (
    READING_BUSINESS_SCAN_PASSES, assess_reading_business_fact, project_reading_business_fact,
)

_MAX_EXPLICIT_GUIDANCE_SKIP_PARAGRAPHS = 1


class _ObservedUnits(Mapping):
    """Final material, analysis owners and a read-only original fallback."""

    def __init__(self, units, analysis, originals=None):
        self.units = units
        self.analysis = analysis
        self.originals = originals or {}

    def __len__(self):
        return len(self.units) + len(self.analysis) + len(self.originals)

    def __iter__(self):
        return chain(self.units, self.analysis, self.originals)

    def __getitem__(self, uid):
        if uid in self.analysis:
            return self.analysis[uid]
        unit = self.units.get(uid) if self.originals else self.units[uid]
        if unit is None:
            unit = self.originals[uid]
        return {"text": unit.raw_text, "parent_id": unit.source_id,
                "role": unit.source_role, "kind": unit.unit_kind, "locator": unit.coordinates}


class SourceOperatingSession:
    def __init__(self, units: Mapping[str, Any], *, work_budget: WorkBudget,
                 contexts: Mapping[str, tuple[str, ...]] | None = None,
                 groups: Mapping[str, tuple[str, ...]] | None = None,
                 antecedents: Mapping[str, tuple[tuple[str, ...], bool]] | None = None,
                 originals: Mapping[str, Any] | None = None):
        self.units = units
        self.work_budget = work_budget
        self.contexts = contexts or {}
        self.groups = groups or {}
        self.owners = {uid: gid for gid, members in self.groups.items() for uid in members}
        self.antecedents = antecedents or {}
        self.originals = originals or {}
        self.analysis: dict[str, Any] = {}
        self.maps: dict[str, list[tuple[int, int, str, int]]] = {}
        self.engine = OperatingRelationSession(
            _ObservedUnits(units, self.analysis, self.originals), work_budget=work_budget)
        self.results: dict[str, dict[str, Any]] = {}
        self.facts: dict[str, OperatingFact] = {}
        self.financial: dict[str, bool | None] = {}
        self.references: dict[str, dict[str, Any]] = {}
        self.complete = True
        self.qualifications: dict[tuple[int, int, int], tuple[Any, Any, dict[str, tuple[str, ...]]]] = {}

    def owner_for(self, uid: str) -> str:
        return self.owners.get(uid, uid)

    def source_text(self, uid: str) -> str:
        owner = self.owner_for(uid)
        return self.analysis[owner]["text"] if owner in self.analysis else self.units[owner].raw_text

    def _prepare_group(self, owner: str):
        if owner in self.analysis:
            return
        members = self.groups[owner]
        first = self.units[members[0]]
        if any(self.units[uid].source_id != first.source_id for uid in members):
            raise ValueError("operating continuity cannot cross original parents")
        self.work_budget.charge(2 * sum(len(self.units[uid].raw_text) for uid in members) + len(members))
        parts, segments = [], []
        cursor = 0
        previous = ""
        cjk = re.compile(r"[\u3400-\u9fff]")
        punctuation = frozenset("。！？；，、：）》】”’（《【“‘")
        for index, uid in enumerate(members):
            raw = self.units[uid].raw_text
            start = 0 if index == 0 else len(raw) - len(raw.lstrip())
            end = len(raw) if index == len(members) - 1 else len(raw.rstrip())
            text = raw[start:end]
            left, right = previous[-1:], text[:1]
            if previous and text:
                boundary = bool(cjk.fullmatch(left) and (cjk.fullmatch(right) or right in punctuation)
                                or cjk.fullmatch(right) and left in punctuation)
                if not boundary:
                    parts.append(" ")
                    cursor += 1  # Analysis separator has no source position.
            parts.append(text)
            if text:
                segments.append((cursor, cursor + len(text), uid, start))
                cursor += len(text)
                previous = text
        self.maps[owner] = segments
        self.analysis[owner] = {"text": "".join(parts), "parent_id": first.source_id,
            "role": first.source_role, "kind": "closed_native_analysis", "locator": first.coordinates}

    def _original_refs(self, owner: str, refs):
        segments = self.maps[owner]
        ends = [segment[1] for segment in segments]
        mapped = []
        for ref in refs:
            start, end = ref["char_start"], ref["char_end"]
            index = bisect_right(ends, start)
            while index < len(segments) and segments[index][0] < end:
                a, b, uid, local = segments[index]
                left, right = max(start, a), min(end, b)
                if left < right:
                    mapped.append({"unit_id": uid, "char_start": local + left-a,
                                   "char_end": local + right-a})
                index += 1
        return mapped

    def relations(self, uid: str):
        owner = self.owner_for(uid)
        if owner not in self.results:
            used_before = self.work_budget.used
            try:
                if owner in self.groups:
                    self._prepare_group(owner)
                result = self.engine.detect(owner, self.contexts.get(owner, ()))
            except WorkBudgetExceeded:
                result = {"schema_version": "du4-operating-relations/1", "unit_id": owner,
                    "relations": [], "diagnostics": [{"code": "work_budget_exhausted", "unit_id": owner}],
                    "status": "partial", "work_used": 0}
            if owner in self.maps:
                result = {**result, "relations": [{**relation, **{
                    field: self._original_refs(owner, relation[field]) for field in
                    ("assertion_refs", "actor_refs", "object_refs", "predicate_refs", "qualifier_refs")}}
                    for relation in result["relations"]]}
            result = {**result, "work_used": self.work_budget.used - used_before}
            self.results[owner] = result
            if result["status"] != "complete":
                self.complete = False
        return self.results[owner]

    def reference(self, uid: str) -> dict[str, Any]:
        """Bounded product-reference readiness for one original or analysis owner.

        Legacy relations/facts are untouched. Declaration refs stay in the
        original namespace: they are validated against their own source text,
        never re-mapped through the target's offsets.
        """
        # Cache by the requested target, not only by its analysis owner: two
        # anchors of one joined window can carry different predecessor scopes.
        cached = self.references.get(uid)
        if cached is not None:
            return cached
        key = self.owner_for(uid)
        if key in self.groups and key not in self.analysis:
            try:
                self._prepare_group(key)
            except (WorkBudgetExceeded, ValueError):
                result = {"schema_version": "du11-reference-closure/1", "unit_id": key,
                          "status": "partial", "reference_refs": [], "declaration_refs": [],
                          "member_refs": [], "required_original_unit_ids": (),
                          "attribution": "unknown",
                          "diagnostics": [{"code": "unprepared_analysis_owner", "unit_id": uid}],
                          "work_used": 0}
                self.references[uid] = result
                return result
        # An absent window is unknown scope, never a proven absence.
        predecessors, complete = self.antecedents.get(uid, ((), False))
        try:
            result = self.engine.reference_closure(key, tuple(predecessors),
                                                   window_complete=complete)
        except ValueError:
            result = {"schema_version": "du11-reference-closure/1", "unit_id": key,
                      "status": "partial", "reference_refs": [], "declaration_refs": [],
                      "member_refs": [], "required_original_unit_ids": (),
                      "attribution": "unknown",
                      "diagnostics": [{"code": "invalid_antecedent_scope", "unit_id": uid}],
                      "work_used": 0}
        if result["status"] in {"unique", "collective"}:
            declarations = self._validate_original_refs(result["declaration_refs"])
            members = self._validate_original_refs(result["member_refs"])
            if declarations is None or members is None:
                diagnostics = result.get("diagnostics")
                diagnostics = list(diagnostics) if isinstance(diagnostics, list) else []
                result = {**result, "status": "partial", "declaration_refs": [],
                          "member_refs": [], "required_original_unit_ids": (),
                          "diagnostics": [*diagnostics,
                                          {"code": "invalid_original_reference", "unit_id": uid}]}
            else:
                result = {**result, "declaration_refs": declarations, "member_refs": members}
        self.references[uid] = result
        return result

    def _source_material_range(self, original_id: str, material_id: str):
        """Exact original body range in the current relation-ref namespace.

        A native carrier retains the observed page-view member offsets. Use
        those actual offsets, never text search or whole-carrier pronoun counts.
        Non-carried original units already share the relation namespace.
        """
        original = self.originals.get(original_id) or self.units.get(original_id)
        material = self.units.get(material_id)
        self.work_budget.charge()
        if original is None or material is None or original.source_id != material.source_id:
            return None
        if original_id == material_id:
            return original.raw_text, {"unit_id": material_id, "char_start": 0,
                                      "char_end": len(original.raw_text)}
        binding = material.metadata.get("native_range")
        if isinstance(binding, Mapping) and binding.get("schema_version") == "native-pdf-range/1":
            members = binding.get("members", ())
            self.work_budget.charge(len(members))
            for member in members:
                if member.get("unit_id") != original_id:
                    continue
                start, end = member.get("view_char_start"), member.get("view_char_end")
                base = material.coordinates.char_start
                if type(start) is not int or type(end) is not int or type(base) is not int:
                    return None
                start, end = start - base, end - base
                self.work_budget.charge(len(original.raw_text))
                if (0 <= start < end <= len(material.raw_text)
                        and material.raw_text[start:end] == original.raw_text):
                    return original.raw_text, {"unit_id": material_id, "char_start": start,
                                              "char_end": end}
                return None
        # A caller's identity-preserving alias has no joined character space.
        # It is usable only when its complete observed characters are equal.
        if material.raw_text == original.raw_text:
            return original.raw_text, {"unit_id": material_id, "char_start": 0,
                                      "char_end": len(original.raw_text)}
        return None

    def local_qualification_dependencies(self, edges, *, origins=None, section_ids=None) -> dict[str, tuple[str, ...]]:
        """Explicit restrictions on original neighbours, projected to material.

        Geometry owns original IDs, relation extraction owns state and object
        refs, and native bindings own character projection. Carrier admission
        cannot erase source-unit dependencies or invent one shared pronoun.
        Reading still counts the whole transitive original envelope.
        """
        key = (id(edges), id(origins), id(section_ids))
        cached = self.qualifications.get(key)
        if cached is not None:
            return cached[2]
        origins = origins if origins is not None else {}
        dependencies: dict[str, tuple[str, ...]] = {}
        bound_heads: dict[str, str] = {}

        def intersects(ref, marker):
            return (ref["unit_id"] == marker["unit_id"]
                    and ref["char_start"] < marker["char_end"]
                    and marker["char_start"] < ref["char_end"])

        try:
            # Native parsers already own turn identity and reset it at headings,
            # tables and speaker changes. Only neighbouring original units may
            # use that proof; no full-turn merge or inferred affiliation.
            previous = None
            for original_id, unit in (self.originals or self.units).items():
                self.work_budget.charge()
                turn = unit.metadata.get("native_speaker_turn")
                if previous is not None and isinstance(turn, Mapping) and turn.get("turn_id"):
                    prev_id, prev_unit, prev_turn = previous
                    if (isinstance(prev_turn, Mapping) and prev_turn == turn
                            and prev_unit.source_id == unit.source_id
                            and prev_unit.parser_name == unit.parser_name
                            and prev_unit.parser_version == unit.parser_version
                            and prev_unit.source_role == unit.source_role):
                        left = origins.get(prev_id, prev_id)
                        right = origins.get(original_id, original_id)
                        if left != right and left in self.units and right in self.units:
                            left_scope = self._source_material_range(prev_id, left)
                            right_scope = self._source_material_range(original_id, right)
                            if left_scope is not None and right_scope is not None:
                                self.work_budget.charge(2 * len(right_scope[0]))
                                if (is_backward_plan_qualification(right_scope[0])
                                        and "operating_plan" in self.fact(left).reasons):
                                    dependencies[left] = tuple(dict.fromkeys(
                                        (*dependencies.get(left, ()), right)))
                previous = (original_id, unit, turn)
            self.work_budget.charge(1 + len(edges))
            for edge in edges:
                if edge.get("basis") != "source_body_adjacency":
                    continue
                left_original, right_original = edge.get("left"), edge.get("right")
                if (not isinstance(left_original, str) or not isinstance(right_original, str)
                        or left_original == right_original):
                    continue
                left, right = origins.get(left_original, left_original), origins.get(right_original, right_original)
                if left not in self.units or right not in self.units:
                    continue
                a, b = self.units[left], self.units[right]
                if (a.source_id != b.source_id or edge.get("source_id") != a.source_id
                        or a.source_role != b.source_role
                        or a.source_role not in {"company_filing", "management", "management_discussion"}):
                    continue
                left_scope = self._source_material_range(left_original, left)
                right_scope = self._source_material_range(right_original, right)
                if left_scope is None or right_scope is None:
                    continue
                right_text, right_marker = right_scope
                self.work_budget.charge(2 * len(right_text))
                # Revenue outlooks are not product objects. Their explicit
                # local premise uses this same source dependency projection,
                # while the caller owns transitive envelope/budget closure.
                if left != right:
                    self.work_budget.charge(2 * (len(a.raw_text) + len(b.raw_text)))
                    if (revenue_guidance_premise(a.raw_text, b.raw_text, follows=True)
                            or revenue_guidance_premise(b.raw_text, a.raw_text, follows=False)):
                        dependencies[left] = tuple(dict.fromkeys((*dependencies.get(left, ()), right)))
                        continue
                deictics = find_product_deictic(right_text)
                if len(deictics) != 1:
                    continue
                deictic = deictics[0]
                if strip_connector(right_text[:deictic.span[0]])[0].strip(" ,，:："):
                    continue
                marker = {**right_marker,
                          "char_start": right_marker["char_start"] + deictic.span[0],
                          "char_end": right_marker["char_start"] + deictic.span[1]}
                result = self.relations(right)
                if result["status"] != "complete":
                    continue
                restriction = False
                for relation in result["relations"]:
                    self.work_budget.charge(1 + len(relation["object_refs"]))
                    if (relation["attribution"] in {"other", "quoted_related_party"}
                            or relation["modality"] not in {"actual", "conditional"}
                            or not (relation["polarity"] == "negative" or relation["stage"] in {
                                "not_yet", "conditional", "suspended", "discontinued"})):
                        continue
                    if any(intersects(ref, marker) for ref in relation["object_refs"]):
                        restriction = True
                        break
                if not restriction:
                    continue
                previous = self.relations(left)
                if previous["status"] != "complete":
                    continue
                objects: list[tuple[str, int, int]] = []
                left_marker = left_scope[1]
                self.work_budget.charge(len(previous["relations"]))
                for relation in previous["relations"]:
                    inherited = (relation["attribution"] == "unknown"
                                 and bound_heads.get(left_original) == head_class(deictic.head))
                    if ((relation["attribution"] != "issuer" and not inherited)
                            or relation["modality"] not in {"actual", "conditional"}):
                        continue
                    self.work_budget.charge(len(relation["object_refs"]))
                    for ref in relation["object_refs"]:
                        if not intersects(ref, left_marker):
                            continue
                        unit = self.units.get(ref["unit_id"]) or self.originals.get(ref["unit_id"])
                        if unit is None or not 0 <= ref["char_start"] < ref["char_end"] <= len(unit.raw_text):
                            continue
                        text = unit.raw_text[ref["char_start"]:ref["char_end"]]
                        self.work_budget.charge(len(text))
                        objects.extend((ref["unit_id"], ref["char_start"] + start,
                                        ref["char_start"] + end)
                                       for start, end, head in product_head_spans(text)
                                       if head == head_class(deictic.head))
                if len(set(objects)) != 1:
                    continue
                bound_heads[right_original] = head_class(deictic.head)
                # Internal carrier edges still establish the next original's
                # identity. Only the published material graph suppresses self.
                if left != right:
                    dependencies[left] = tuple(dict.fromkeys((*dependencies.get(left, ()), right)))
            # An explicit source-authored outlook reference may point past one
            # same-page paragraph. It still needs the same source, role, and
            # uniquely known section, plus exact paragraph coordinates. This
            # is a semantic reference edge, never a physical adjacency proof.
            if section_ids:
                source_units = self.originals or self.units
                by_position: dict[tuple[str, int, str, int], list[str]] = {}
                self.work_budget.charge(len(source_units))
                for original_id, unit in source_units.items():
                    coordinates = getattr(unit, "coordinates", None)
                    section_id = section_ids.get(original_id)
                    page = getattr(coordinates, "page_number", None)
                    paragraph = getattr(coordinates, "paragraph_index", None)
                    if (not isinstance(section_id, str) or not section_id
                            or type(page) is not int or type(paragraph) is not int
                            or getattr(coordinates, "table_index", None) is not None):
                        continue
                    by_position.setdefault((unit.source_id, page, section_id, paragraph), []).append(original_id)
                self.work_budget.charge(len(source_units))
                for premise_id, premise in source_units.items():
                    coordinates = getattr(premise, "coordinates", None)
                    section_id = section_ids.get(premise_id)
                    page = getattr(coordinates, "page_number", None)
                    paragraph = getattr(coordinates, "paragraph_index", None)
                    if (not isinstance(section_id, str) or not section_id
                            or type(page) is not int or type(paragraph) is not int
                            or getattr(coordinates, "table_index", None) is not None
                            or premise.source_role not in {"company_filing", "management", "management_discussion"}):
                        continue
                    self.work_budget.charge(1 + len(premise.raw_text))
                    if not is_explicit_backward_revenue_guidance_premise(premise.raw_text):
                        continue
                    # Include the immediate predecessor to detect ambiguity,
                    # but only a single explicit reference across one skipped
                    # paragraph may use this semantic path.
                    matches: set[tuple[str, str, int]] = set()
                    for gap in range(1, _MAX_EXPLICIT_GUIDANCE_SKIP_PARAGRAPHS + 2):
                        forecast_paragraph = paragraph - gap
                        intervening_paragraph = paragraph - 1
                        if forecast_paragraph < 0:
                            continue
                        forecast_ids = by_position.get(
                            (premise.source_id, page, section_id, forecast_paragraph), ()
                        )
                        if gap == _MAX_EXPLICIT_GUIDANCE_SKIP_PARAGRAPHS + 1 and not by_position.get(
                            (premise.source_id, page, section_id, intervening_paragraph), ()
                        ):
                            continue
                        for forecast_id in forecast_ids:
                            forecast = source_units[forecast_id]
                            if (forecast.source_role != premise.source_role
                                    or forecast.source_role not in {"company_filing", "management", "management_discussion"}):
                                continue
                            left = origins.get(forecast_id, forecast_id)
                            right = origins.get(premise_id, premise_id)
                            if left == right or left not in self.units or right not in self.units:
                                continue
                            left_scope = self._source_material_range(forecast_id, left)
                            right_scope = self._source_material_range(premise_id, right)
                            if left_scope is None or right_scope is None:
                                continue
                            forecast_text, premise_text = left_scope[0], right_scope[0]
                            self.work_budget.charge(2 * (len(forecast_text) + len(premise_text)))
                            if revenue_guidance_premise(forecast_text, premise_text, follows=True):
                                matches.add((left, right, gap))
                    if len(matches) == 1 and next(iter(matches))[2] > 1:
                        left, right, _ = next(iter(matches))
                        dependencies[left] = tuple(dict.fromkeys((*dependencies.get(left, ()), right)))
        except WorkBudgetExceeded:
            self.complete = False
        self.qualifications[key] = (edges, origins, dependencies)
        return dependencies

    def _validate_original_refs(self, refs) -> list[dict[str, Any]] | None:
        projected: list[dict[str, Any]] = []
        for ref in refs:
            uid = ref.get("unit_id")
            start, end = ref.get("char_start"), ref.get("char_end")
            if (not isinstance(uid, str) or not isinstance(start, int) or isinstance(start, bool)
                    or not isinstance(end, int) or isinstance(end, bool)):
                return None
            unit = self.units.get(uid)
            if unit is None:
                unit = self.originals.get(uid)
            if unit is None:
                return None
            text = getattr(unit, "raw_text", None)
            if text is None:
                text = unit.get("text", "") if isinstance(unit, Mapping) else ""
            if not 0 <= start < end <= len(text):
                return None
            entry = {"unit_id": uid, "char_start": start, "char_end": end}
            if not projected or projected[-1] != entry:
                projected.append(entry)
        return projected

    def fact(self, uid: str) -> OperatingFact:
        owner = self.owner_for(uid)
        if owner in self.facts:
            return self.facts[owner]
        result = self.relations(uid)
        text = self.source_text(uid) if owner in self.analysis or owner not in self.groups else ""
        def ref_text(ref):
            return self.units[ref["unit_id"]].raw_text[ref["char_start"]:ref["char_end"]]
        # The compatibility recognizer also scans text. Reserve its work before
        # running it; exhaustion must not restart through a text-only fallback.
        try:
            if result["status"] == "partial" and self.work_budget.exhausted:
                raise WorkBudgetExceeded("operating relation work exhausted")
            self.work_budget.charge(READING_BUSINESS_SCAN_PASSES * len(text))
            fact, financial = assess_reading_business_fact(text, result, ref_text=ref_text)
        except WorkBudgetExceeded:
            self.complete = False
            # Closed relations retain their exact qualifiers and states without
            # restarting the text recognizer or scanning an unexamined tail.
            fact = project_reading_business_fact(text, result,
                include_description=False, ref_text=ref_text) if result["relations"] else OperatingFact()
            fact = replace(fact, purpose="unassessed")
            financial = False if fact.financial_exempt else None
        self.facts[owner] = fact
        self.financial[owner] = financial
        return fact

    def financial_only(self, uid: str) -> bool | None:
        self.fact(uid)
        return self.financial[self.owner_for(uid)]
