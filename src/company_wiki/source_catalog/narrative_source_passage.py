"""Prepared source-quote capability, never an issuer/event/measurement proof.

Unknown names and business vocabularies need not match an operating predicate
inventory to remain readable narration. This uses generic declaration syntax
and existing source-purpose/abstract/accounting observations. Original text,
attribution, stage, numeric meaning and priority remain with their owners.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
import re

from company_wiki.document_understanding.operating_states.assertion_roles import (
    AssertionRole, SourceAssertionRoles, abstract_source_argument, STATE_HEAD_PATTERN,
)
from company_wiki.document_understanding.structure.table_purpose import accounting_field
from company_wiki.document_understanding.source_turn_markers import (
    explicit_qa_marker, ROLE_INVESTOR, SOURCE_TURN_MARKER_PREFIX_CHARS,
)
from company_wiki.document_model.text_matching import matching_reading_text
from company_wiki.document_understanding.statement_grammar import (
    StatementObservation, observe_english_statement_boundary, observe_statement,
)

from .narrative_causal_links import CAUSAL_LINK
from .narrative_business_meaning import _OBJECT
from .narrative_reporting_rules import arithmetic_presentation
from .narrative_source_context import (
    SOURCE_CONTEXT_SCAN_PASSES, SourceClauseContext, source_clause_context, statement_complement_context,
)


SOURCE_PASSAGE_POLICY_VERSION = 'source-passage/10'
# Preparation reuses normalized clauses from the already charged assessment.
# Includes generic grammar, negative envelopes, account and cause scans, plus
# the measurement callback's normalized clause view. Metric proofs themselves
# share the assessment cache with causal and business consumers.
SOURCE_PASSAGE_SCAN_PASSES = 24 + SOURCE_CONTEXT_SCAN_PASSES


@dataclass(frozen=True)
class SourcePassageCapability:
    use: str
    reason: str
    role: str
    relevant: bool
    financial_only: bool = False
    # Language ambiguity is a completed unresolved observation. Missing
    # capability/scope work is deferred and cannot prove narrative absence.
    assessment_complete: bool = True


@dataclass(frozen=True)
class SourceStatementScope:
    """Transient classification view; original refs never index normalized text."""
    text: str
    roles: SourceAssertionRoles
    suppressed: bool = False
    assertion_keys: frozenset[str] = frozenset()
    business_causal_keys: frozenset[str] = frozenset()
    grammar_results: tuple[tuple[str, StatementObservation], ...] = ()
    context_results: tuple[tuple[str, SourceClauseContext], ...] = ()
    # Source observations and fact eligibility are different views. A known
    # generic or unresolved argument remains an observed grammatical role.
    fact_roles: SourceAssertionRoles | None = None
    financial_context_keys: frozenset[str] = frozenset()


_CN_QUESTION = re.compile(r'\s*(?:请问|請問|是否|会不会|會不會)')
_NON_ASSERTION = re.compile(
    r'^\s*(?:the\s+)?(?:模板|示例|填报|流程|程序|规则|指南|template|example|procedure|manual|'
    r'instructions?|guidelines?)\b|'
    r'^\s*(?:模板|示例|填报|流程|程序|规则|指南)(?:示例|说明|要求|规定|[:：])', re.I)
_REFERENCE_METADATA = re.compile(r'\b(?:glossary|contents|index)\b|术语表|词汇表|目录|'
                                 r'^(?:单位|币种)\s*[:：为是]|'
                                 r'^\s*(?:all\s+)?amounts?\s+in\b', re.I)
_DEPENDENT_SUBJECT = re.compile(r'^\s*(?:the\s+other|other|this|that|such|these|those)\b', re.I)
_COURTESY = re.compile(r'\s*(?:thank you|thanks|good morning|good afternoon|'
                         r'谢谢|謝謝|感谢|感謝|各位好)', re.I)
_SENTENCE_END = re.compile(r'[。！？;；]|[.!?](?=\s|$)')
_QUESTION_END = re.compile(r'[?？]')
_CONFIRMATION_QUESTION = re.compile(
    r'\s*(?:(?:is|was)\s+(?:that|this|it)\s+(?:correct|true|accurate)\b|'
    r'(?:please\s+)?confirm\b[^?？]{0,80}\b(?:that|this|statement)\b|'
    r'(?:请|請)?确认(?:上述|这一|该|這一|該)[^?？]{0,30}(?:属实|屬實|正确|正確))', re.I)
_METADATA_STATEMENT = re.compile(
    r'\b(?:is|are|was|were|be|been)\s+(?:[a-z-]+\s+){0,2}'
    r'(?:described|discussed|mentioned|listed|referenced)\b'
    r'[^。.!?;]{0,80}\b(?:sections?|chapters?|elsewhere|appendi\w*|glossar\w*)\b|'
    r'\b(?:is|are)\s+defined\s+as\b|'
    r'\b(?:is|are)\s+(?:a\s+)?(?:(?:generic|general|billing)\s+){0,3}definition\b', re.I)
# A causal action must bind a typed operating argument in the same clause.
# Word morphology alone (e.g. an arbitrary -ing noun) proves neither role.
_CAUSAL_PROCESS = re.compile(
    r'\b(?:change[sd]?|shift(?:ed|s)?|adjust\w*|mix|higher|lower|greater|fewer|'
    r'increas\w*|decreas\w*|improv\w*|reduc\w*|manufactur\w*|assembl\w*|'
    r'process\w*|produc(?:e|es|ed|ing|tion)|complet\w*|expand\w*)\b|'
    r'调整|調整|改变|改變|转向|轉向|推进|推進|提高|提升|下降|上升|增长|增長|减少|減少|优化|優化', re.I)
_FINANCIAL_CAUSAL_ARGUMENT = re.compile(
    r'\bfinancial\s+(?:performance|results?|condition)\b|财务(?:表现|业绩|状况)|財務(?:表現|業績|狀況)', re.I)


def statement_assertion_key(text: str) -> str:
    return matching_reading_text(text).strip(' \t\r\n.。!?？！;；')


def prepare_source_statement_scope(text: str, roles: SourceAssertionRoles, *,
        accounting_text: Callable[[str], bool] = accounting_field,
        causal_relation: Callable[[str], bool] | None = None,
        measurement_relation: Callable[[str], bool] | None = None,
        quantified_argument: Callable[[str], bool] | None = None,
        business_relation: Callable[[str], bool] | None = None,
        scope_relation: Callable[[str], bool] | None = None,
        grammar_work_budget=None) -> SourceStatementScope:
    """Observe every sentence once; suppress question/courtesy proof anywhere.

    The masked classification string has exactly the original length. One
    monotonic alignment filters the already prepared role proofs; normalization
    is transient and never supplies source offsets. Policy and passage share
    this observation instead of scanning/preparing assertions again.
    """
    start = 0
    segments: list[tuple[int, int, bool]] = []
    suppressed = False
    source_allowed_segments: dict[int, bool] = {}
    grammar_results = []
    context_results_list = []
    prepared_grammar = {}
    argument_roles: dict[str, bool] = {}

    def quantified_role(value: str) -> bool:
        if value not in argument_roles:
            argument_roles[value] = bool(quantified_argument and quantified_argument(value))
        return argument_roles[value]

    for clause in roles.clauses:
        key = statement_assertion_key(clause.text)
        context = source_clause_context(clause.text, clause)
        typed_business = bool(context.status == 'candidate' and not context.objective_operator
                              and business_relation and business_relation(clause.text))
        scope_description = bool(context.status == 'candidate' and not context.objective_operator
                                 and (clause.source_scope or scope_relation and scope_relation(clause.text)))
        if scope_description and not typed_business and clause.independent_payload is not True:
            context = replace(context, source_scope=True)
        if (context.status == 'candidate' and not context.objective_operator and clause.operating
                and clause.independent_payload is None and not typed_business and not scope_description):
            context = replace(context, status='unresolved', reason='source_payload_unresolved')
        if context.status == 'candidate' and (context.objective_operator or
                clause.operating and clause.independent_payload is not True and not typed_business and not scope_description):
            observation = observe_statement(clause.text, work_budget=grammar_work_budget,
                lexical_boundaries=(context.objective_end,) if context.objective_end is not None else ())
            prepared_grammar[key] = observation
            grammar_results.append((key, observation))
            context = statement_complement_context(clause.text, clause, observation, prepared=context,
                                                  quantified_argument=quantified_role,
                                                  work_budget=grammar_work_budget)
        context_results_list.append((key, context))
    context_results = tuple(context_results_list)
    contexts = dict(context_results)
    while start < len(text):
        end = _SENTENCE_END.search(text, start)
        stop = end.end() if end else len(text)
        key = statement_assertion_key(text[start:stop])
        prepared = prepared_grammar.get(key)
        boundary = observe_english_statement_boundary(text[start:stop], work_budget=grammar_work_budget,
                                                       prepared=prepared)
        if boundary is None and key in contexts and contexts[key].objective_operator:
            boundary = prepared
        if boundary is not None and key not in prepared_grammar:
            grammar_results.append((key, boundary))
        question = (bool(end and end.group() in {'?', '？'})
                    or bool(boundary and boundary.reason == 'interrogative_scope')
                    or explicit_qa_marker(text[start:start + SOURCE_TURN_MARKER_PREFIX_CHARS]) == ROLE_INVESTOR
                    or bool(_CN_QUESTION.match(text, start)))
        if question:
            end = _QUESTION_END.search(text, start)
        stop = end.end() if end else len(text)
        if question and _CONFIRMATION_QUESTION.match(text, start) and segments:
            previous_start, previous_stop, _allowed = segments[-1]
            # Explicit backward verification governs only its immediately
            # preceding proposition, not every earlier independent statement.
            segments[-1] = (previous_start, previous_stop, False)
            source_allowed_segments[previous_start] = False
        grammar_unknown = bool(boundary and boundary.status == 'unknown')
        source_allowed = not (question or _COURTESY.match(text, start)
                              or _METADATA_STATEMENT.search(text, start, stop)
                              or bool(boundary and boundary.status == 'fragment'))
        source_allowed_segments[start] = source_allowed
        allowed = source_allowed and not (grammar_unknown or bool(boundary and boundary.status == 'fragment'))
        segments.append((start, stop, allowed))
        suppressed |= not allowed
        start = stop
    if (not suppressed and CAUSAL_LINK.search(text) is None
            and all(context.status == 'candidate' for _, context in context_results)
            and all(observation.status != 'unknown' for observation in prepared_grammar.values())):
        return SourceStatementScope(text, roles, grammar_results=tuple(grammar_results),
                                    context_results=context_results, fact_roles=roles)
    normalized = []
    segment_ranges = []
    offset = 0
    for start, stop, allowed in segments:
        raw = text[start:stop]
        segment = matching_reading_text(raw)
        normalized.append(segment)
        segment_ranges.append((offset, offset + len(segment)))
        offset += len(segment)
    value = ''.join(normalized)
    memberships: list[list] = [[] for _ in segments]
    cursor = 0
    statement_index = 0
    for clause in roles.clauses:
        position = value.find(clause.text, cursor)
        if position < 0:
            # The supplied prepared view cannot prove a safe suffix alignment.
            return SourceStatementScope(' ' * len(text), replace(roles, clauses=(),
                bound_operating=False, bound_payload=False), True,
                grammar_results=tuple(grammar_results), context_results=context_results)
        cursor = position + len(clause.text)
        while (statement_index < len(segment_ranges)
               and segment_ranges[statement_index][1] <= position):
            statement_index += 1
        if (statement_index < len(segment_ranges)
                and segment_ranges[statement_index][0] <= position
                and cursor <= segment_ranges[statement_index][1]):
            memberships[statement_index].append(clause)
    masked = []
    clauses = []
    source_clauses = []
    assertion_keys = set()
    causal_keys: set[str] = set()
    financial_keys: set[str] = set()
    for (start, stop, allowed), segment, members in zip(segments, normalized, memberships):
        if source_allowed_segments[start]:
            source_clauses.extend(members)
        members = [clause for clause in members
                   if contexts[statement_assertion_key(clause.text)].status == 'candidate'
                   and (statement_assertion_key(clause.text) not in prepared_grammar
                        or prepared_grammar[statement_assertion_key(clause.text)].status != 'unknown')]
        if not members:
            allowed = False
        cause = CAUSAL_LINK.search(segment)
        if allowed and cause and accounting_text(segment):
            tail = (cause.group('embedded_cause') or segment[cause.end():]).strip()
            # Existing source-owned quantity/direction/action proof has higher
            # authority than generic quote grammar. It owns the cause's full
            # assertion/modality and must not be vetoed by a weaker noun test.
            source_cause = bool(causal_relation and causal_relation(segment))
            business_cause = source_cause or bool(tail and not accounting_text(tail)
                and not _FINANCIAL_CAUSAL_ARGUMENT.search(tail)
                and not abstract_source_argument(tail)
                and (_OBJECT.search(tail) or STATE_HEAD_PATTERN.search(tail))
                and _CAUSAL_PROCESS.search(tail))
            independent = any(clause.independent_payload is True for clause in members)
            # A separately observed business measurement remains readable even
            # when its causal prelude is unproved. Keep this proof independent:
            # an amount is not evidence that the stated cause is true.
            allowed = independent or business_cause or bool(
                measurement_relation and measurement_relation(segment))
            if not allowed:
                financial_keys.update(statement_assertion_key(clause.text) for clause in members)
            if business_cause:
                causal_keys.update(clause.text.strip(' \t\r\n.。!?？！;；') for clause in members)
        suppressed |= not allowed
        masked.append(text[start:stop] if allowed else ' ' * (stop-start))
        if allowed:
            clauses.extend(members)
            assertion_keys.add(segment.strip(' \t\r\n.。!?？！;；'))
            assertion_keys.update(clause.text.strip(' \t\r\n.。!?？！;；') for clause in members)
    fact_roles = (replace(roles, clauses=tuple(clauses), bound_operating=False,
                          bound_payload=False) if suppressed else roles)
    source_view = tuple(replace(clause, source_scope=True)
                        if contexts[statement_assertion_key(clause.text)].source_scope else clause
                        for clause in source_clauses)
    source_roles = (roles if source_view == roles.clauses else
                    replace(roles, clauses=source_view, bound_operating=False, bound_payload=False))
    return SourceStatementScope(''.join(masked), source_roles, suppressed,
                                frozenset(assertion_keys), frozenset(causal_keys),
                                tuple(grammar_results), context_results, fact_roles, frozenset(financial_keys))


def _declarative(text: str, *, grammar_observations: list[StatementObservation] | None = None,
                 grammar_results: dict[str, StatementObservation] | None = None,
                 source_role: AssertionRole | None = None,
                 semantic_contexts: list[SourceClauseContext] | None = None,
                 semantic_results: dict[str, SourceClauseContext] | None = None,
                 clause_contexts: dict[str, SourceClauseContext] | None = None,
                 bound_causal_description: bool = False,
                 grammar_work_budget=None) -> bool:
    """Observe a source statement, not its economic truth or event eligibility."""
    if not any(character.isalpha() for character in text):
        return False
    if (text.rstrip().endswith(('?', '？'))
            or explicit_qa_marker(text) == ROLE_INVESTOR
            or text.lstrip().startswith(('请问', '請問', '是否', '会不会'))
            or _NON_ASSERTION.search(text) or _COURTESY.match(text)
            or _DEPENDENT_SUBJECT.match(text)
            or abstract_source_argument(text)):
        return False
    # A lexical auxiliary or causal cue can occur inside a relative nominal.
    # Only the statement owner observes a matrix predicate here. Established
    # independent source proofs are consumed separately by the caller above.
    key = statement_assertion_key(text)
    observation = grammar_results.get(key) if grammar_results is not None else None
    prepared = clause_contexts.get(key) if clause_contexts is not None else None
    if prepared is None and source_role is not None:
        prepared = source_clause_context(text, source_role)
        if clause_contexts is not None:
            clause_contexts[key] = prepared
    if prepared is not None and prepared.status != 'candidate':
        if semantic_contexts is not None:
            semantic_contexts.append(prepared)
        return False
    if observation is None:
        observation = observe_statement(text, work_budget=grammar_work_budget,
            lexical_boundaries=(prepared.objective_end,) if prepared and prepared.objective_end is not None else ())
        if grammar_results is not None:
            grammar_results[key] = observation
    if source_role is not None and not bound_causal_description:
        context = semantic_results.get(key) if semantic_results is not None else None
        if context is None:
            assert prepared is not None
            context = (statement_complement_context(text, source_role, observation, prepared=prepared,
                                                    work_budget=grammar_work_budget)
                       if prepared.status == 'candidate' else prepared)
            if semantic_results is not None:
                semantic_results[key] = context
        if context.status != 'candidate':
            if semantic_contexts is not None:
                semantic_contexts.append(context)
            return False
    if grammar_observations is not None:
        grammar_observations.append(observation)
    return observation.independent


def _grammar_uncertainty(observations: list[StatementObservation]) -> SourcePassageCapability | None:
    reasons = {item.reason for item in observations if item.status == 'unknown'}
    if not reasons:
        return None
    if 'statement_grammar_scope_limit' in reasons:
        return SourcePassageCapability('unresolved', 'source_grammar_scope_limit', 'unknown', False,
                                       assessment_complete=False)
    if 'statement_grammar_unavailable' in reasons:
        return SourcePassageCapability('unresolved', 'source_grammar_unavailable', 'unknown', False,
                                       assessment_complete=False)
    # Language ambiguity keeps concrete original words readable as unresolved;
    # it is never independent event, measurement or issuer proof. Capability
    # failure above cannot donate this relevance to unprocessed source text.
    if reasons == {'statement_grammar_ambiguous'}:
        return SourcePassageCapability('unresolved', 'source_grammar_ambiguous', 'source_narrative', True)
    return SourcePassageCapability('unresolved', 'source_grammar_unavailable', 'unknown', False,
                                   assessment_complete=False)


def prepare_source_passage(
    text: str, roles: SourceAssertionRoles, *, purpose: str, financial_only: bool,
    accounting_text: Callable[[str], bool], non_operating_purposes: frozenset[str],
    existing_use: tuple[str, str], existing_relevant: bool,
    statement_scope: SourceStatementScope | None = None,
    existing_fact_proof: bool = False,
    grammar_work_budget=None,
) -> SourcePassageCapability:
    """Prepare once; two consumers share the same capability without rescanning.

    A mixed original scope stays verbatim when an independent narrative clause
    is readable. An account-result clause or an account-only causal explanation
    cannot make itself useful just by being grammatical. This never upgrades
    the existing roles, OperatingFact, numeric or issuer-state proof.
    """
    def context(reason: str, *, finance: bool = False):
        return SourcePassageCapability('context_only', reason,
            'financial_context' if finance else 'source_context', False, finance)

    if purpose == 'unassessed':
        return SourcePassageCapability('unresolved', 'source_assessment_incomplete', 'unknown', False,
                                       assessment_complete=False)
    # A known accounting clause cannot erase already observed unavailable
    # work in another statement of the same original support scope.
    if statement_scope is not None:
        resolved_context = {key for key, value in statement_scope.context_results
                            if value.status != 'candidate'}
        scoped_uncertainty = _grammar_uncertainty([item for key, item in statement_scope.grammar_results
                                                 if key not in resolved_context])
        if scoped_uncertainty is not None and not scoped_uncertainty.assessment_complete:
            # Unexamined clauses remain deferred. A different independently
            # prepared source assertion in this unchanged quote remains usable;
            # the partial flag never becomes issuer/event/numeric proof.
            if (statement_scope.assertion_keys and existing_use[0] == 'support'
                    and existing_relevant and existing_fact_proof
                    and purpose not in non_operating_purposes):
                return replace(scoped_uncertainty, use='support', relevant=True,
                               role='mixed_narrative_context')
            return scoped_uncertainty
    if purpose in non_operating_purposes:
        return context('non_operating_purpose')
    if _NON_ASSERTION.search(text):
        return context('source_non_assertion')
    prepared_use = statement_scope is not None
    statement_scope = (statement_scope if statement_scope is not None else
                       prepare_source_statement_scope(text, roles, grammar_work_budget=grammar_work_budget))
    clauses, has_prefix = statement_scope.roles.clauses, statement_scope.suppressed
    clause_contexts = dict(statement_scope.context_results)
    grammar_results = {key: observation for key, observation in statement_scope.grammar_results
                       if key not in clause_contexts or clause_contexts[key].status == 'candidate'}
    grammar_observations = list(grammar_results.values())
    active_clauses = [clause for clause in clauses if
        statement_assertion_key(clause.text) not in clause_contexts
        or clause_contexts[statement_assertion_key(clause.text)].status == 'candidate']
    if clauses and not active_clauses:
        semantic = [clause_contexts[statement_assertion_key(clause.text)] for clause in clauses]
        unresolved = next((value for value in semantic if value.status == 'unresolved'), None)
        if unresolved is not None:
            return SourcePassageCapability('unresolved', unresolved.reason, 'source_context', unresolved.relevant)
        return context(semantic[0].reason)
    if has_prefix and not clauses:
        uncertainty = _grammar_uncertainty(grammar_observations)
        if uncertainty is not None:
            return uncertainty
        semantic = [context for _, context in statement_scope.context_results
                    if context.status != 'candidate']
        if semantic:
            unresolved = next((context for context in semantic if context.status == 'unresolved'), None)
            if unresolved is not None:
                return SourcePassageCapability('unresolved', unresolved.reason, 'source_context', unresolved.relevant)
            return context(semantic[0].reason)
        return context('source_non_assertion')
    if not has_prefix and roles.independent_payload is False:
        return context('source_generic_objective')
    if any(clause_contexts.get(statement_assertion_key(clause.text), SourceClauseContext()).source_scope
           for clause in active_clauses):
        return SourcePassageCapability('support', 'source_declared_scope', 'source_narrative', True)
    # Preserve the established prepared capability before considering a more
    # general source-quote fallback. It may be proved by a bound relation or a
    # resource/quantity owner rather than a single local clause witness.
    if ((prepared_use or not has_prefix) and existing_use[0] == 'support'
            and (any(clause.independent_payload is True for clause in clauses)
                 or roles.bound_payload or existing_fact_proof)):
        return SourcePassageCapability('support', existing_use[1], 'source_narrative', True)
    if clauses and all(abstract_source_argument(clause.text)
                             for clause in clauses):
        return context('source_generic_objective')
    if (prepared_use or not has_prefix) and existing_use[0] == 'unresolved' and existing_relevant:
        return SourcePassageCapability('unresolved', existing_use[1], 'source_narrative', True)
    readable = False
    finance_seen = financial_only
    semantic_contexts: list[SourceClauseContext] = []
    semantic_results: dict[str, SourceClauseContext] = {}
    for clause in clauses:
        text = clause.text
        if statement_assertion_key(text) in statement_scope.financial_context_keys:
            finance_seen = True
            continue
        if (clause.rule_purpose or clause.independent_payload is False
                or _NON_ASSERTION.search(text)
                or _REFERENCE_METADATA.search(text)):
            continue
        # Presentation belongs to this clause. A different readable operation
        # in the unchanged quote still supplies its own support below.
        account = accounting_text(text) or arithmetic_presentation(text)
        finance_seen |= account
        # Positive role evidence already prepared by the source owner remains
        # valid. Generic readable narration below confers no such proof.
        if clause.independent_payload is True:
            readable = True
        elif not account and _declarative(text, grammar_observations=grammar_observations,
                                         grammar_results=grammar_results,
                                         source_role=clause, semantic_contexts=semantic_contexts,
                                         semantic_results=semantic_results,
                                         clause_contexts=clause_contexts,
                                         grammar_work_budget=grammar_work_budget):
            readable = True
        elif account:
            if text.strip(' \t\r\n.。!?？！;；') in statement_scope.business_causal_keys:
                readable |= _declarative(text, grammar_observations=grammar_observations,
                                         grammar_results=grammar_results,
                                         source_role=clause, semantic_contexts=semantic_contexts,
                                         semantic_results=semantic_results,
                                         clause_contexts=clause_contexts,
                                         bound_causal_description=True,
                                         grammar_work_budget=grammar_work_budget)
            # A comma can separate a complete operating description from its
            # financial consequence. Classify those local scopes separately,
            # while preserving the verbatim quote and all its qualifications.
            # This does not prove the claimed cause or the revenue amount.
            readable |= any(not accounting_text(part) and _declarative(
                                part.strip(), grammar_observations=grammar_observations,
                                grammar_results=grammar_results,
                                source_role=clause, semantic_contexts=semantic_contexts,
                                semantic_results=semantic_results,
                                clause_contexts=clause_contexts,
                                grammar_work_budget=grammar_work_budget)
                            for part in re.split(r'[,，]', text)
                            if part.strip() and part != text)
    uncertainty = _grammar_uncertainty(grammar_observations)
    if uncertainty is not None and not uncertainty.assessment_complete:
        return uncertainty
    if readable:
        if roles.numeric_ambiguous and not roles.operating:
            return SourcePassageCapability('unresolved', 'source_numeric_scope_unresolved',
                                           'source_narrative', True)
        return SourcePassageCapability('support', 'source_readable_narrative',
            'mixed_narrative_context' if finance_seen else 'source_narrative', True)
    if uncertainty is not None:
        return uncertainty
    if semantic_contexts:
        unresolved = next((item for item in semantic_contexts if item.status == 'unresolved'), None)
        if unresolved is not None:
            return SourcePassageCapability('unresolved', unresolved.reason, 'source_context', unresolved.relevant)
        return context(semantic_contexts[0].reason)
    if finance_seen:
        return context('financial_only', finance=True)
    return SourcePassageCapability('unresolved', 'source_passage_incomplete', 'unknown', False)
