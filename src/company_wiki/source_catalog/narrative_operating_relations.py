"""Call-scoped operating facts over final source-owned material units.

No parsing, IO, registry or extra work balance. The source owner fixes native
carriers and structural context first; consumers share the resulting facts.
"""
from collections.abc import Iterable, Mapping
from copy import deepcopy
from dataclasses import dataclass, replace
from bisect import bisect_right
from itertools import chain
from types import MappingProxyType
import re
from typing import Any

from company_wiki.document_understanding.layout_hints.contract import WorkBudget, WorkBudgetExceeded
from company_wiki.document_understanding.operating_states.relations import OperatingRelationSession
from company_wiki.document_understanding.operating_states.relations import independent_statement_start
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
    prepare_reading_business_assessment, project_reading_business_fact,
    source_result_subject,
    SOURCE_COMPARISON_MODIFIER_PATTERN,
    source_comparison_bases,
)
from .narrative_predicate_state import observe_metric_predicate

_MAX_EXPLICIT_GUIDANCE_SKIP_PARAGRAPHS = 1
# Existing prepared source-scope contract, distinct from the bounded
# antecedent search window. Physical fragmentation does not change meaning.
SOURCE_SUPPORT_MAX_MEMBERS = 64
_CJK_CONTEXT_RUN = re.compile(r"[\u3400-\u9fff]{2,}")
_LATIN_CONTEXT_TERM = re.compile(r"\b[a-z][a-z0-9-]{2,}\b", re.IGNORECASE)
_GENERIC_PHASE_CONTEXT_TERM = re.compile(
    r"(?:第)?[一二三四五六七八九十百千万\d]+(?:期|阶段)"
)
# Covers the combined stop-phrase pass, CJK and Latin scans, bigram creation,
# and bounded set materialization with headroom for regex/match bookkeeping.
_LOCAL_CONTEXT_TERM_SCAN_PASSES = 6
_GENERIC_CONTEXT_TERMS = frozenset({
    "公司", "本公司", "集团", "本集团", "企业", "业务", "项目", "建设", "产能", "产线",
    "生产", "制造", "产品", "服务", "技术", "设备", "反应", "反应釜", "总体", "体积",
    "完成", "提前", "提升", "新增", "扩大", "运营", "数量", "同比", "增长", "收入",
    "客户", "市场", "计划", "预计", "未来", "目前", "达到", "超过", "报告", "期间",
    "capacity", "project", "build", "building", "construction", "complete", "completed",
    "company", "business", "production", "manufacturing", "product", "service", "technology",
    "equipment", "reactor", "volume", "increase", "increased", "growth", "revenue", "customer",
    "market", "plan", "planned", "expected", "current", "report", "period", "total", "units",
})
_CJK_GENERIC_CONTEXT_TERMS = tuple(sorted(
    (term for term in _GENERIC_CONTEXT_TERMS if _CJK_CONTEXT_RUN.fullmatch(term)),
    key=len,
    reverse=True,
))
_CJK_GENERIC_CONTEXT_PATTERN = re.compile(
    "|".join(re.escape(term) for term in _CJK_GENERIC_CONTEXT_TERMS)
)
_IGNORED_CONTEXT_PATTERN = re.compile(
    f"(?:{_GENERIC_PHASE_CONTEXT_TERM.pattern})|(?:{_CJK_GENERIC_CONTEXT_PATTERN.pattern})"
)
# Result anaphora are source references, not independent metric assertions.
# A named result ("the increase in service revenue") is self-contained and
# does not match this deliberately narrow bare-result grammar.
_RESULT_REFERENCE = re.compile(
    r"(?:^|[，,;；。.!?])\s*(?P<marker>(?:(?:有[关關]|上述|[该該此])\s*)"
    r"(?:(?:" + SOURCE_COMPARISON_MODIFIER_PATTERN + r")\s*)?"
    r"(?P<cn>增加|增[长長]|上升|下降|減少|减少)|"
    r"(?:this|that|the|such)\s+(?:(?:" + SOURCE_COMPARISON_MODIFIER_PATTERN + r")\s+)?"
    r"(?P<en>increase|growth|rise|decrease|decline|reduction)|"
    r"(?P<neutral>(?:这一|這一|这个|這個|上述)(?:变化|變化|变动|變動)|"
    r"(?:this|that|such)\s+(?:change|movement)))"
    r"(?=\s*(?:主要|[是为為由]|was\b|is\b|arose\b|resulted\b|due\b))", re.I)
_RESULT_CHANGE = re.compile(
    r"(?P<up>增加|增[长長]|上升|\b(?:increased?|increases|grew|rose)\b)|"
    r"(?P<down>下降|[减減]少|\b(?:decreased?|decreases|declined?|declines|fell)\b)", re.I)


def _result_direction(value: str) -> str:
    return "down" if value.casefold() in {"decrease", "decline", "reduction", "下降", "减少", "減少"} else "up"


def _specific_context_terms(text: str) -> frozenset[str]:
    """Return bounded content terms for local context matching, not entity identity."""
    # Remove complete ordinal phases and known generic phrases before generating
    # overlapping bigrams. Filtering bigrams afterward leaves fragments such as
    # ``第一`` from ``第一期`` and artifacts such as ``线建`` across generic words.
    context_text = _IGNORED_CONTEXT_PATTERN.sub(" ", text)
    terms = {
        run[index:index + 2]
        for match in _CJK_CONTEXT_RUN.finditer(context_text)
        for run in (match.group(),)
        for index in range(len(run) - 1)
    }
    terms.update(token.casefold() for token in _LATIN_CONTEXT_TERM.findall(text))
    return frozenset(
        term for term in terms
        if term not in _GENERIC_CONTEXT_TERMS
    )


@dataclass(frozen=True)
class _LocalQualification:
    head: str | None = None
    object_ref: tuple[str, int, int] | None = None


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
    """Own one source's immutable scope bindings, results and work account."""

    __slots__ = (
        "__units", "__work_budget", "__contexts", "__groups", "__owners",
        "__antecedents", "__originals", "__analysis", "__maps", "__engine",
        "__results", "__bindings", "__facts", "__financial", "__assertions",
        "__passages", "__references", "__complete",
        "__support_owners", "__support_contexts", "__citation_groups", "__source_positions",
    )

    def __init__(self, units: Mapping[str, Any], *, work_budget: WorkBudget,
                 contexts: Mapping[str, tuple[str, ...]] | None = None,
                 groups: Mapping[str, tuple[str, ...]] | None = None,
                 antecedents: Mapping[str, tuple[tuple[str, ...], bool]] | None = None,
                 originals: Mapping[str, Any] | None = None):
        self.__units = MappingProxyType(dict(units))
        self.__work_budget = work_budget
        self.__contexts = dict(contexts or {})
        self.__groups = dict(groups or {})
        self.__support_owners: dict[tuple[tuple[str, ...], tuple[str, ...]], str] = {}
        self.__support_contexts: dict[str, tuple[str, ...]] = {}
        self.__citation_groups: dict[tuple[str, ...], str | None] = {}
        self.__owners = {uid: gid for gid, members in self.__groups.items() for uid in members}
        self.__antecedents = dict(antecedents or {})
        self.__originals = MappingProxyType(dict(originals or {}))
        self.__source_positions: dict[str, int] | None = None
        self.__analysis: dict[str, Any] = {}
        self.__maps: dict[str, list[tuple[int, int, str, int]]] = {}
        self.__engine = OperatingRelationSession(
            _ObservedUnits(self.__units, self.__analysis, self.__originals), work_budget=work_budget)
        self.__results: dict[str, dict[str, Any]] = {}
        self.__bindings: dict[str, tuple[bool, ...]] = {}
        self.__facts: dict[str, OperatingFact] = {}
        self.__financial: dict[str, bool | None] = {}
        self.__assertions: dict[str, Any] = {}
        self.__passages: dict[str, Any] = {}
        self.__references: dict[tuple[str, tuple[str, ...], bool], dict[str, Any]] = {}
        self.__complete = True

    @property
    def units(self) -> Mapping[str, Any]:
        return self.__units

    @property
    def work_budget(self) -> WorkBudget:
        return self.__work_budget

    @property
    def complete(self) -> bool:
        return self.__complete

    def mark_incomplete(self) -> None:
        self.__complete = False

    def bind_contexts(self, contexts: Mapping[str, tuple[str, ...]]) -> None:
        """Register the structural context before citation assessment.

        Already prepared scopes keep their original semantic view. Context
        for a genuinely different prepared scope travels with its own ID.
        """
        self.__contexts.update((uid, tuple(ids)) for uid, ids in contexts.items() if uid not in self.__results)

    def prepare_citations(self) -> None:
        self.__work_budget.charge(2 * len(self.__groups) + 1)
        indexed: dict[tuple[str, ...], str | None] = {}
        for owner, members in self.__groups.items():
            if members not in indexed:
                indexed[members] = owner
            elif (previous := indexed[members]) is not None and self.context_for(previous) != self.context_for(owner):
                indexed[members] = None
        self.__citation_groups = indexed

    def members_for(self, owner: str) -> tuple[str, ...]:
        return self.__groups.get(owner, (owner,))

    def citation_owner(self, members: tuple[str, ...], *, prepared_owner: str | None = None) -> str:
        """Resolve one exact support scope, preserving explicit meaning context."""
        if prepared_owner is not None:
            if self.members_for(prepared_owner) == members:
                return prepared_owner
            meaning = tuple(uid for uid in self.context_for(prepared_owner) if uid not in members)
            return self.support_owner(members, meaning_context=meaning)
        if members in self.__citation_groups:
            owner = self.__citation_groups[members]
            return owner if owner is not None else self.support_owner(members)
        if len(members) == 1 and self.owner_for(members[0]) == members[0]:
            return members[0]
        return self.support_owner(members)

    def has_fact(self, uid: str) -> bool:
        return self.owner_for(uid) in self.__facts

    def prepared_observation(self, uid: str) -> dict[str, Any]:
        owner = self.owner_for(uid)
        return {"owner": owner, "fact": self.__facts.get(owner), "passage": self.__passages.get(owner)}

    def prepared_relation_ids(self) -> tuple[str, ...]:
        return tuple(self.__results)

    def relation_bindings(self, uid: str) -> tuple[bool, ...]:
        self.__relations_for(uid)
        return self.__bindings.get(self.owner_for(uid), ())

    def unknown_argument(self, uid: str) -> bool:
        if self.__relations_for(uid)["status"] != "complete":
            return False
        owner = self.owner_for(uid)
        return self.__engine.unknown_argument(owner, self.context_for(owner))

    def owner_for(self, uid: str) -> str:
        return self.__owners.get(uid, uid)

    def support_owner(self, support: tuple[str, ...], *,
                      meaning_context: tuple[str, ...] = ()) -> str:
        """Register one immutable semantic scope without replacing unit owners.

        Questions belong to model context, not this semantic context. Callers
        first establish source closure; this method only owns preparation/cache
        identity and the original-character projection already used by groups.
        """
        if (type(support) is not tuple or type(meaning_context) is not tuple
                or not support or len(support) + len(meaning_context) > SOURCE_SUPPORT_MAX_MEMBERS):
            raise ValueError('invalid source support scope')
        # Bounded canonical-ID cache identity is not another source scan.
        # Reject custom hash/iterator objects before the free prepared lookup.
        if any(type(uid) is not str for uid in (*support, *meaning_context)):
            raise ValueError('invalid source support identity')
        key = (support, meaning_context)
        cached = self.__support_owners.get(key)
        if cached is not None:
            return cached
        self.__work_budget.charge(1 + len(support) + len(meaning_context))
        if (any(type(uid) is not str or uid not in self.__units for uid in (*support, *meaning_context))
                or len(set(support)) != len(support) or set(support) & set(meaning_context)):
            raise ValueError('invalid source support members')
        source = self.__units[support[0]].source_id
        if any(self.__units[uid].source_id != source for uid in (*support, *meaning_context)):
            raise ValueError('source support cannot cross originals')
        owner = 'source-scope:' + str(len(self.__support_owners))
        self.__groups[owner] = support
        self.__support_contexts[owner] = meaning_context
        self.__support_owners[key] = owner
        return owner

    def context_for(self, owner: str) -> tuple[str, ...]:
        return self.__support_contexts.get(owner, self.__contexts.get(owner, ()))

    def source_text(self, uid: str) -> str:
        owner = self.owner_for(uid)
        return self.__analysis[owner]["text"] if owner in self.__analysis else self.__units[owner].raw_text

    def _prepare_group(self, owner: str):
        if owner in self.__analysis:
            return
        members = self.__groups.get(owner, (owner,))
        first = self.__units[members[0]]
        if any(self.__units[uid].source_id != first.source_id for uid in members):
            raise ValueError("operating continuity cannot cross original parents")
        self.__work_budget.charge(2 * sum(len(self.__units[uid].raw_text) for uid in members) + len(members))
        parts, segments = [], []
        cursor = 0
        previous = ""
        cjk = re.compile(r"[\u3400-\u9fff]")
        punctuation = frozenset("。！？；，、：）》】”’（《【“‘")
        for index, uid in enumerate(members):
            unit = self.__units[uid]
            raw = unit.raw_text
            start = 0 if index == 0 else len(raw) - len(raw.lstrip())
            end = len(raw) if index == len(members) - 1 else len(raw.rstrip())
            printed = unit.metadata.get("printed_turn")
            if printed is not None and "body_start" in printed:
                start = max(start, printed["body_start"])
                end = min(end, printed["body_end"])
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
        self.__maps[owner] = segments
        printed = first.metadata.get("printed_turn")
        self.__analysis[owner] = {"text": "".join(parts), "parent_id": first.source_id,
            "role": printed["role"] if printed else first.source_role,
            "kind": "closed_native_analysis", "locator": first.coordinates}

    def _original_refs(self, owner: str, refs):
        segments = self.__maps[owner]
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

    def relations(self, uid: str) -> dict[str, Any]:
        """Return an independent serializable observation of the prepared scope."""
        return deepcopy(self.__relations_for(uid))

    def __relations_for(self, uid: str) -> dict[str, Any]:
        owner = self.owner_for(uid)
        if owner not in self.__results:
            used_before = self.__work_budget.used
            context = self.context_for(owner)
            try:
                if owner in self.__groups or "printed_turn" in self.__units[owner].metadata:
                    self._prepare_group(owner)
                result = self.__engine.detect(owner, context)
                self.__bindings[owner] = self.__engine.relation_bindings(owner, context)
            except WorkBudgetExceeded:
                result = {"schema_version": "du4-operating-relations/1", "unit_id": owner,
                    "relations": [], "diagnostics": [{"code": "work_budget_exhausted", "unit_id": owner}],
                    "status": "partial", "work_used": 0}
            if owner in self.__maps:
                result = {**result, "relations": [{**relation, **{
                    field: self._original_refs(owner, relation[field]) for field in
                    ("assertion_refs", "actor_refs", "object_refs", "predicate_refs", "qualifier_refs")}}
                    for relation in result["relations"]]}
            result = {**result, "work_used": self.__work_budget.used - used_before}
            self.__results[owner] = result
            if result["status"] != "complete":
                self.__complete = False
        return self.__results[owner]

    def reference(self, uid: str, *,
                  window: tuple[tuple[str, ...], bool] | None = None) -> dict[str, Any]:
        """Resolve the explicit predecessor window and detach its receipt."""
        return deepcopy(self.__reference_for(uid, window))

    def __reference_for(self, uid: str, window: tuple[tuple[str, ...], bool] | None) -> dict[str, Any]:
        # Cache by the requested target, not only by its analysis owner: two
        # anchors of one joined window can carry different predecessor scopes.
        # Missing window denotes unknown scope, and a later explicit window
        # may legitimately give the same target a different reference result.
        predecessors, window_complete = self.__antecedents.get(uid, ((), False)) if window is None else window
        cache_key = (uid, predecessors, window_complete)
        cached = self.__references.get(cache_key)
        if cached is not None:
            return cached
        key = self.owner_for(uid)
        if predecessors and not self.__predecessors_are_prior(key, predecessors):
            invalid = {"schema_version": "du11-reference-closure/1", "unit_id": key,
                       "status": "partial", "reference_refs": [], "declaration_refs": [],
                       "member_refs": [], "required_original_unit_ids": (), "attribution": "unknown",
                       "diagnostics": [{"code": "invalid_antecedent_scope", "unit_id": uid}], "work_used": 0}
            self.__references[cache_key] = invalid
            return invalid
        if key not in self.__analysis and (key in self.__groups or "printed_turn" in self.__units[key].metadata):
            try:
                self._prepare_group(key)
            except (WorkBudgetExceeded, ValueError):
                result = {"schema_version": "du11-reference-closure/1", "unit_id": key,
                          "status": "partial", "reference_refs": [], "declaration_refs": [],
                          "member_refs": [], "required_original_unit_ids": (),
                          "attribution": "unknown",
                          "diagnostics": [{"code": "unprepared_analysis_owner", "unit_id": uid}],
                          "work_used": 0}
                self.__references[cache_key] = result
                return result
        result = self._result_reference(key, predecessors, window_complete)
        if result is not None:
            self.__references[cache_key] = result
            return result
        try:
            result = self.__engine.reference_closure(key, predecessors, window_complete=window_complete)
        except ValueError:
            result = {"schema_version": "du11-reference-closure/1", "unit_id": key,
                      "status": "partial", "reference_refs": [], "declaration_refs": [],
                      "member_refs": [], "required_original_unit_ids": (),
                      "attribution": "unknown",
                      "diagnostics": [{"code": "invalid_antecedent_scope", "unit_id": uid}],
                      "work_used": 0}
        if result['status'] == 'not_applicable':
            # Product and causal-result identity keep their existing stronger
            # closure. First-person narration only needs its adjacent source
            # context retained; it must not invent a resolved issuer identity.
            from .narrative_actor_context import actor_context_closure
            self.__work_budget.charge(1 + len(predecessors))
            observed = {entry: self.__units.get(entry, self.__originals.get(entry))
                        for entry in predecessors}
            if key in self.__analysis:
                first = self.__units[self.__groups.get(key, (key,))[0]]
                observed[key] = {**self.__analysis[key], 'metadata': first.metadata}
            else:
                observed[key] = self.__units[key]
            result = actor_context_closure(key, predecessors, units=observed,
                window_complete=window_complete, work_budget=self.__work_budget)
            if key in self.__maps and result['reference_refs']:
                result = {**result, 'reference_refs': self._original_refs(key, result['reference_refs'])}
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
        self.__references[cache_key] = result
        return result

    def __predecessors_are_prior(self, owner: str, predecessors: tuple[str, ...]) -> bool:
        units = self.__originals or self.__units
        if self.__source_positions is None:
            self.__work_budget.charge(len(units))
            self.__source_positions = {uid: i for i, uid in enumerate(units)}
        positions = self.__source_positions
        self.__work_budget.charge(1 + len(predecessors))

        def bounds(uid: str, source_id: str) -> tuple[int, int] | None:
            source = units.get(uid)
            index = positions.get(uid)
            if source is not None and index is not None:
                return (index, index) if source.source_id == source_id else None
            carrier = self.__units.get(uid)
            if carrier is None or carrier.source_id != source_id:
                return None
            native_range = carrier.metadata.get("native_range")
            if not isinstance(native_range, Mapping) or native_range.get("schema_version") != "native-pdf-range/1":
                return None
            members = native_range.get("members", ())
            self.__work_budget.charge(len(members))
            indexes = []
            for member in members:
                member_id = member["unit_id"]
                original = units.get(member_id)
                if original is None or original.source_id != source_id:
                    return None
                indexes.append(positions[member_id])
            return (min(indexes), max(indexes)) if indexes else None

        targets = self.members_for(owner)
        target = self.__units.get(targets[0]) or units.get(targets[0])
        if target is None:
            return False
        target_bounds = [bounds(uid, target.source_id) for uid in targets]
        if any(span is None for span in target_bounds):
            return False
        target_start = min(span[0] for span in target_bounds if span is not None)
        last = -1
        for uid in predecessors:
            span = bounds(uid, target.source_id)
            if span is None or not last < span[0] <= span[1] < target_start:
                return False
            last = span[1]
        return True

    def match_qa_qualification(self, left: str, right: str, *, left_owner: str,
                               right_owner: str, inherited_head: str | None = None) -> _LocalQualification | None:
        """Match an explicitly ordered answer pair using each exact member."""
        left_scope = self.__source_material_range(left, left)
        right_scope = self.__source_material_range(right, right)
        if left_scope is None or right_scope is None:
            raise ValueError("qa_original_range_unavailable")
        return self.__qualification_pair(left, right, left_scope, right_scope, inherited_head=inherited_head,
                                         left_owner=left_owner, right_owner=right_owner, qa_sequence=True)

    def _result_reference(self, owner: str, predecessors: tuple[str, ...], complete: bool):
        """Close one bare result over its proven adjacent source statement.

        The existing antecedent window owns source/section/order boundaries.
        Multiple changes, an unobserved predicate or an incomplete window stay
        unresolved; the model cannot obtain a subject from another output.
        """
        used_before = self.__work_budget.used
        text = self.source_text(owner)
        self.__work_budget.charge(len(text) + 1)
        marker = _RESULT_REFERENCE.search(text)
        if marker is None:
            return None
        # A reference inside one original statement may already have its own
        # named result. Do not force it to find a second statement outside.
        internal = text[:marker.start()]
        self.__work_budget.charge(len(internal) + 1)
        internal_changes = tuple(_RESULT_CHANGE.finditer(internal))
        if len(internal_changes) == 1:
            change = internal_changes[0]
            self.__work_budget.charge(2 * len(internal))
            observation = observe_metric_predicate(internal, change.start(), change.end())
            if (observation.observed
                    and source_result_subject(internal, change.start(), change.end(), work_budget=self.__work_budget)
                    and (marker.group('neutral') or change.lastgroup == _result_direction(marker.group('cn') or marker.group('en')))):
                return {'schema_version':'du11-reference-closure/1','unit_id':owner,
                    'status':'not_applicable','reference_refs':[], 'declaration_refs':[],
                    'member_refs':[],'required_original_unit_ids':(), 'attribution':'unknown',
                    'diagnostics':[],'work_used':self.__work_budget.used-used_before}
        reference = {"unit_id": owner, "char_start": marker.start("marker"),
                     "char_end": marker.end("marker")}
        result: dict[str, Any] = {"schema_version": "du11-reference-closure/1", "unit_id": owner,
            "status": "missing" if complete else "partial", "reference_refs": [reference],
            "declaration_refs": [], "member_refs": [], "required_original_unit_ids": (),
            "support_original_unit_ids": (), "reference_kind": "causal_result",
            "attribution": "unknown", "diagnostics": [], "work_used": 0}
        if owner in self.__maps:
            result["reference_refs"] = self._original_refs(owner, [reference])
        if complete and predecessors:
            previous_id = predecessors[-1]
            previous = self.__units.get(previous_id) or self.__originals.get(previous_id)
            target_id = self.__groups.get(owner, (owner,))[0]
            target = self.__units[target_id]
            if (previous is not None and previous.source_id == target.source_id
                    and previous.source_role == target.source_role):
                self.__work_budget.charge(len(previous.raw_text) + 1)
                changes = tuple(_RESULT_CHANGE.finditer(previous.raw_text))
                if len(changes) > 1:
                    result["status"] = "ambiguous"
                elif len(changes) == 1:
                    change = changes[0]
                    self.__work_budget.charge(4 * len(previous.raw_text) + len(marker.group("marker")))
                    observation = observe_metric_predicate(previous.raw_text, change.start(), change.end())
                    previous_basis = source_comparison_bases(previous.raw_text, change.start(), change.end())
                    reference_basis = source_comparison_bases(marker.group("marker"))
                    compatible_basis = (len(previous_basis) <= 1 and len(reference_basis) <= 1
                        and (not previous_basis or not reference_basis or previous_basis == reference_basis))
                    if (observation.observed and compatible_basis
                            and _RESULT_REFERENCE.search(previous.raw_text) is None
                            and (marker.group('neutral') or change.lastgroup == _result_direction(marker.group("cn") or marker.group("en")))
                            and source_result_subject(previous.raw_text, change.start(), change.end(),
                                                      work_budget=self.__work_budget)):
                        declaration = {"unit_id": previous_id, "char_start": 0,
                                       "char_end": len(previous.raw_text)}
                        result.update(status="unique", declaration_refs=[declaration],
                            member_refs=[declaration], required_original_unit_ids=(previous_id,),
                            support_original_unit_ids=(previous_id,), attribution="unknown")
        if result["status"] != "unique":
            result["diagnostics"] = [{"code": "result_antecedent_unresolved", "unit_id": owner}]
        result["work_used"] = self.__work_budget.used - used_before
        return result

    def __source_material_range(self, original_id: str, material_id: str):
        """Exact original body range in the current relation-ref namespace.

        A native carrier retains the observed page-view member offsets. Use
        those actual offsets, never text search or whole-carrier pronoun counts.
        Non-carried original units already share the relation namespace.
        """
        original = self.__originals.get(original_id) or self.__units.get(original_id)
        material = self.__units.get(material_id)
        self.__work_budget.charge()
        if original is None or material is None or original.source_id != material.source_id:
            return None
        if original_id == material_id:
            return original.raw_text, {"unit_id": material_id, "char_start": 0,
                                      "char_end": len(original.raw_text)}
        binding = material.metadata.get("native_range")
        if isinstance(binding, Mapping) and binding.get("schema_version") == "native-pdf-range/1":
            members = binding.get("members", ())
            self.__work_budget.charge(len(members))
            for member in members:
                if member.get("unit_id") != original_id:
                    continue
                start, end = member.get("view_char_start"), member.get("view_char_end")
                base = material.coordinates.char_start
                if type(start) is not int or type(end) is not int or type(base) is not int:
                    return None
                start, end = start - base, end - base
                self.__work_budget.charge(len(original.raw_text))
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

    def __qualification_pair(self, left, right, left_scope, right_scope, *,
                            inherited_head=None, left_owner=None, right_owner=None,
                            qa_sequence=False):
        """Semantic match only; callers own their physical/QA sequence proof."""
        a, b = self.__units[left], self.__units[right]
        def intersects(ref, marker):
            return (ref["unit_id"] == marker["unit_id"]
                    and ref["char_start"] < marker["char_end"]
                    and marker["char_start"] < ref["char_end"])
        right_text, right_marker = right_scope
        self.__work_budget.charge(2 * len(right_text))
        # Revenue outlooks are not product objects. Their explicit
        # local premise uses this same source dependency projection,
        # while the caller owns transitive envelope/budget closure.
        if left != right:
            self.__work_budget.charge(2 * (len(a.raw_text) + len(b.raw_text)))
            if (revenue_guidance_premise(a.raw_text, b.raw_text, follows=True)
                    or revenue_guidance_premise(b.raw_text, a.raw_text, follows=False)):
                return _LocalQualification()
        deictics = find_product_deictic(right_text)
        if len(deictics) != 1:
            return None
        deictic = deictics[0]
        prefix = strip_connector(right_text[:deictic.span[0]])[0].strip(' ,，:：')
        if prefix and not (qa_sequence and independent_statement_start(prefix)):
            return None
        marker = {**right_marker,
                  "char_start": right_marker["char_start"] + deictic.span[0],
                  "char_end": right_marker["char_start"] + deictic.span[1]}
        result = self.__relations_for(right_owner or right)
        if result["status"] != "complete":
            return None
        restriction = False
        for relation in result["relations"]:
            self.__work_budget.charge(1 + len(relation["object_refs"]))
            if (relation["attribution"] in {"other", "quoted_related_party"}
                    or relation["modality"] not in {"actual", "conditional"}
                    or not (relation["polarity"] == "negative" or relation["stage"] in {
                        "not_yet", "conditional", "suspended", "discontinued"})):
                continue
            if any(intersects(ref, marker) for ref in relation["object_refs"]):
                restriction = True
                break
        if not restriction:
            return None
        previous = self.__relations_for(left_owner or left)
        if previous["status"] != "complete":
            return None
        objects: list[tuple[str, int, int]] = []
        left_marker = left_scope[1]
        self.__work_budget.charge(len(previous["relations"]))
        for relation in previous["relations"]:
            inherited = (relation["attribution"] == "unknown"
                         and inherited_head == head_class(deictic.head))
            if ((relation["attribution"] != "issuer" and not inherited)
                    or relation["modality"] not in {"actual", "conditional"}):
                continue
            self.__work_budget.charge(len(relation["object_refs"]))
            for ref in relation["object_refs"]:
                if not intersects(ref, left_marker):
                    continue
                unit = self.__units.get(ref["unit_id"]) or self.__originals.get(ref["unit_id"])
                if unit is None or not 0 <= ref["char_start"] < ref["char_end"] <= len(unit.raw_text):
                    continue
                text = unit.raw_text[ref["char_start"]:ref["char_end"]]
                self.__work_budget.charge(len(text))
                objects.extend((ref["unit_id"], ref["char_start"] + start,
                                ref["char_start"] + end)
                               for start, end, head in product_head_spans(text)
                               if head == head_class(deictic.head))
        if len(set(objects)) != 1:
            return None
        return _LocalQualification(head_class(deictic.head), next(iter(set(objects))))

    def local_qualification_dependencies(self, edges, *, origins=None, section_ids=None) -> dict[str, tuple[str, ...]]:
        """Explicit restrictions on original neighbours, projected to material.

        Geometry owns original IDs, relation extraction owns state and object
        refs, and native bindings own character projection. Carrier admission
        cannot erase source-unit dependencies or invent one shared pronoun.
        Reading still counts the whole transitive original envelope.
        """
        origins = origins if origins is not None else {}
        dependencies: dict[str, tuple[str, ...]] = {}
        bound_heads: dict[str, str] = {}

        try:
            # Native parsers already own turn identity and reset it at headings,
            # tables and speaker changes. Only neighbouring original units may
            # use that proof; no full-turn merge or inferred affiliation.
            previous = None
            for original_id, unit in (self.__originals or self.__units).items():
                self.__work_budget.charge()
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
                        if left != right and left in self.__units and right in self.__units:
                            left_scope = self.__source_material_range(prev_id, left)
                            right_scope = self.__source_material_range(original_id, right)
                            if left_scope is not None and right_scope is not None:
                                self.__work_budget.charge(2 * len(right_scope[0]))
                                if (is_backward_plan_qualification(right_scope[0])
                                        and "operating_plan" in self.fact(left).reasons):
                                    dependencies[left] = tuple(dict.fromkeys(
                                        (*dependencies.get(left, ()), right)))
                previous = (original_id, unit, turn)
            self.__work_budget.charge(1 + len(edges))
            for edge in edges:
                if edge.get("basis") != "source_body_adjacency":
                    continue
                left_original, right_original = edge.get("left"), edge.get("right")
                if (not isinstance(left_original, str) or not isinstance(right_original, str)
                        or left_original == right_original):
                    continue
                left, right = origins.get(left_original, left_original), origins.get(right_original, right_original)
                if left not in self.__units or right not in self.__units:
                    continue
                a, b = self.__units[left], self.__units[right]
                if (a.source_id != b.source_id or edge.get("source_id") != a.source_id
                        or a.source_role != b.source_role
                        or a.source_role not in {"company_filing", "management", "management_discussion"}):
                    continue
                left_scope = self.__source_material_range(left_original, left)
                right_scope = self.__source_material_range(right_original, right)
                if left_scope is None or right_scope is None:
                    continue
                matched = self.__qualification_pair(left, right, left_scope, right_scope,
                    inherited_head=bound_heads.get(left_original))
                if matched is not None:
                    if matched.head:
                        bound_heads[right_original] = matched.head
                    if left != right:
                        dependencies[left] = tuple(dict.fromkeys((*dependencies.get(left, ()), right)))
            # An explicit source-authored outlook reference may point past one
            # same-page paragraph. It still needs the same source, role, and
            # uniquely known section, plus exact paragraph coordinates. This
            # is a semantic reference edge, never a physical adjacency proof.
            if section_ids:
                source_units = self.__originals or self.__units
                by_position: dict[tuple[str, int, str, int], list[str]] = {}
                self.__work_budget.charge(len(source_units))
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
                self.__work_budget.charge(len(source_units))
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
                    self.__work_budget.charge(1 + len(premise.raw_text))
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
                            if left == right or left not in self.__units or right not in self.__units:
                                continue
                            left_scope = self.__source_material_range(forecast_id, left)
                            right_scope = self.__source_material_range(premise_id, right)
                            if left_scope is None or right_scope is None:
                                continue
                            forecast_text, premise_text = left_scope[0], right_scope[0]
                            self.__work_budget.charge(2 * (len(forecast_text) + len(premise_text)))
                            if revenue_guidance_premise(forecast_text, premise_text, follows=True):
                                matches.add((left, right, gap))
                    if len(matches) == 1 and next(iter(matches))[2] > 1:
                        left, right, _ = next(iter(matches))
                        dependencies[left] = tuple(dict.fromkeys((*dependencies.get(left, ()), right)))
        except WorkBudgetExceeded:
            self.__complete = False
        return dependencies

    def local_operating_context_dependencies(
        self, edges: Iterable[Mapping[str, Any]], *, origins: Mapping[str, str] | None = None,
        section_ids: Mapping[str, str] | None = None,
    ) -> dict[str, tuple[str, ...]]:
        """Pair adjacent milestone/quantity facts as context without asserting causality.

        This is deliberately separate from qualification dependencies: both
        facts keep their own citation support, while the other statement is
        available as local context only when the source, role, page, section,
        physical adjacency, semantic types and a specific shared term agree.
        """
        origins = origins if origins is not None else {}
        section_ids = section_ids if section_ids is not None else {}
        contexts: dict[str, list[str]] = {}
        try:
            for edge in edges:
                self.__work_budget.charge()
                if edge.get("basis") != "source_body_adjacency":
                    continue
                left_original, right_original = edge.get("left"), edge.get("right")
                if (not isinstance(left_original, str) or not isinstance(right_original, str)
                        or left_original == right_original):
                    continue
                left, right = origins.get(left_original, left_original), origins.get(right_original, right_original)
                if left == right or left not in self.__units or right not in self.__units:
                    continue
                a, b = self.__units[left], self.__units[right]
                if (a.source_id != b.source_id or edge.get("source_id") != a.source_id
                        or a.source_role != b.source_role
                        or a.source_role not in {"company_filing", "management", "management_discussion"}):
                    continue
                left_page = getattr(getattr(a, "coordinates", None), "page_number", None)
                right_page = getattr(getattr(b, "coordinates", None), "page_number", None)
                if (type(left_page) is not int or left_page != right_page
                        or edge.get("left_page", left_page) != left_page
                        or edge.get("right_page", right_page) != right_page):
                    continue
                left_section, right_section = section_ids.get(left_original), section_ids.get(right_original)
                if not isinstance(left_section, str) or not left_section or left_section != right_section:
                    continue
                left_scope = self.__source_material_range(left_original, left)
                right_scope = self.__source_material_range(right_original, right)
                if left_scope is None or right_scope is None:
                    continue
                left_text, right_text = left_scope[0], right_scope[0]
                self.__work_budget.charge(
                    _LOCAL_CONTEXT_TERM_SCAN_PASSES * (len(left_text) + len(right_text))
                )
                if not (_specific_context_terms(left_text) & _specific_context_terms(right_text)):
                    continue
                left_fact, right_fact = self.fact(left), self.fact(right)
                milestone_quantity_pair = (
                    "project_execution_timeline" in left_fact.reasons
                    and "operating_quantity" in right_fact.reasons
                ) or (
                    "operating_quantity" in left_fact.reasons
                    and "project_execution_timeline" in right_fact.reasons
                )
                if not milestone_quantity_pair:
                    continue
                contexts.setdefault(left, []).append(right)
                contexts.setdefault(right, []).append(left)
        except WorkBudgetExceeded:
            self.__complete = False
        return {owner: tuple(dict.fromkeys(neighbours)) for owner, neighbours in contexts.items()}

    def _validate_original_refs(self, refs) -> list[dict[str, Any]] | None:
        projected: list[dict[str, Any]] = []
        for ref in refs:
            uid = ref.get("unit_id")
            start, end = ref.get("char_start"), ref.get("char_end")
            if (not isinstance(uid, str) or not isinstance(start, int) or isinstance(start, bool)
                    or not isinstance(end, int) or isinstance(end, bool)):
                return None
            unit = self.__units.get(uid)
            if unit is None:
                unit = self.__originals.get(uid)
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
        if owner in self.__facts:
            return self.__facts[owner]
        result = self.__relations_for(uid)
        text = self.source_text(uid) if owner in self.__analysis or owner not in self.__groups else ""
        def ref_text(ref):
            return self.__units[ref["unit_id"]].raw_text[ref["char_start"]:ref["char_end"]]
        # Each source owner accounts for its own observation on the same
        # budget. Exhaustion must not restart through a text-only fallback.
        financial: bool | None
        try:
            if result["status"] == "partial" and self.__work_budget.exhausted:
                raise WorkBudgetExceeded("operating relation work exhausted")
            from company_wiki.document_understanding.operating_states.assertion_roles import prepare_source_assertions
            roles = replace(prepare_source_assertions(text, work_budget=self.__work_budget),
                bound_operating=(self.__engine.complete_assertion(owner,self.context_for(owner))
                    or self.__engine.unknown_argument(owner,self.context_for(owner))))
            assessment = prepare_reading_business_assessment(text, result, ref_text=ref_text,
                source_roles=roles, relation_bindings=self.__bindings.get(owner, ()),
                grammar_work_budget=self.__work_budget)
            fact, financial = assessment.fact, assessment.financial_only
            self.__assertions[owner] = assessment.source_roles
            self.__passages[owner] = assessment.passage
        except WorkBudgetExceeded:
            self.__complete = False
            # Closed relations retain their exact qualifiers and states without
            # restarting the text recognizer or scanning an unexamined tail.
            fact = project_reading_business_fact(text, result,
                include_description=False, ref_text=ref_text,
                relation_bindings=self.__bindings.get(owner, ())) if result["relations"] else OperatingFact()
            fact = replace(fact, purpose="unassessed")
            financial = False if fact.financial_exempt else None
        self.__facts[owner] = fact
        self.__financial[owner] = financial
        return fact

    def financial_only(self, uid: str) -> bool | None:
        self.fact(uid)
        return self.__financial[self.owner_for(uid)]

    def source_assertions(self, uid: str):
        """The exact owner's already charged role proof, never a second scan."""
        self.fact(uid)
        return self.__assertions.get(self.owner_for(uid))

    def source_passage(self, uid: str):
        """The same charged owner's quote capability, not an event proof."""
        self.fact(uid)
        return self.__passages.get(self.owner_for(uid))
