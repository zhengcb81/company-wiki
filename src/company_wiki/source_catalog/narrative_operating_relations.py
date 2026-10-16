"""Call-scoped operating facts over final source-owned material units.

No parsing, IO, registry or extra work balance. The source owner fixes native
carriers and structural context first; consumers share the resulting facts.
"""
from collections.abc import Mapping
from bisect import bisect_right
from itertools import chain
import re
from typing import Any

from company_wiki.document_understanding.layout_hints.contract import WorkBudget, WorkBudgetExceeded
from company_wiki.document_understanding.operating_states.relations import OperatingRelationSession

from .n6_candidate_operating_facts import OperatingFact
from .narrative_business_policy import project_reading_business_fact


class _ObservedUnits(Mapping):
    def __init__(self, units, analysis):
        self.units = units
        self.analysis = analysis

    def __len__(self):
        return len(self.units) + len(self.analysis)

    def __iter__(self):
        return chain(self.units, self.analysis)

    def __getitem__(self, uid):
        if uid in self.analysis:
            return self.analysis[uid]
        unit = self.units[uid]
        return {"text": unit.raw_text, "parent_id": unit.source_id,
                "role": unit.source_role, "kind": unit.unit_kind, "locator": unit.coordinates}


class SourceOperatingSession:
    def __init__(self, units: Mapping[str, Any], *, work_budget: WorkBudget,
                 contexts: Mapping[str, tuple[str, ...]] | None = None,
                 groups: Mapping[str, tuple[str, ...]] | None = None):
        self.units = units
        self.work_budget = work_budget
        self.contexts = contexts or {}
        self.groups = groups or {}
        self.owners = {uid: gid for gid, members in self.groups.items() for uid in members}
        self.analysis: dict[str, Any] = {}
        self.maps: dict[str, list[tuple[int, int, str, int]]] = {}
        self.engine = OperatingRelationSession(_ObservedUnits(units, self.analysis), work_budget=work_budget)
        self.results: dict[str, dict[str, Any]] = {}
        self.facts: dict[str, OperatingFact] = {}
        self.complete = True

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
            self.work_budget.charge(4 * len(text))
            fact = project_reading_business_fact(text, result, ref_text=ref_text)
        except WorkBudgetExceeded:
            self.complete = False
            # Closed relations retain their exact qualifiers and states without
            # restarting the text recognizer or scanning an unexamined tail.
            fact = project_reading_business_fact(text, result,
                include_description=False, ref_text=ref_text) if result["relations"] else OperatingFact()
        self.facts[owner] = fact
        return fact
