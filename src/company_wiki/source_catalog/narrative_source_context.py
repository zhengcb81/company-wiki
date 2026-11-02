"""Source discourse/complement roles, distinct from matrix syntax and facts.

This is a closed grammar of reporting and rhetorical roles, not a vocabulary
of companies, industries or approved business verbs. Unknown content stays
unresolved; it is not evidence of an operation or of a financial-only source.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from collections.abc import Callable
import re

from company_wiki.document_understanding.operating_states.assertion_roles import (
    AssertionRole, abstract_source_argument, source_offering_head,
)
from company_wiki.resource_budget import WorkBudget
from company_wiki.document_understanding.operating_states.patterns import COURTESY, ISSUER_WORD
from company_wiki.document_understanding.statement_grammar import StatementObservation

from .narrative_reporting_rules import arithmetic_presentation


# Conservative upper envelope of regex visits, not a wall-clock multiplier:
# bounded arithmetic/name/meta guards, objective/principle/abstract/courtesy,
# then the cached matrix's nominal complement. Mutually exclusive branches
# return early; no source clause is sent to this preparation twice.
SOURCE_CONTEXT_SCAN_PASSES = 12
# Existing prepared argument strings may overlap. Charge their actual total
# length, not merely one full-clause pass, before relevance scans consume them.
SOURCE_TARGET_SCAN_PASSES = 8


@dataclass(frozen=True)
class SourceClauseContext:
    status: str = 'candidate'
    reason: str = ''
    objective_operator: bool = False
    objective_end: int | None = None
    complement_observed: bool = False
    relevant: bool = False


_PAGE_NAME = re.compile(r'^\s*\d{1,4}\s+[^。.!?;；\n]{1,80}'
                        r'(?:有限公司|有限责任公司|股份公司|控股公司|集团公司)\s*$')
_METATEXT_SUBJECT = re.compile(r'^\s*(?:(?:the|these|those)\s+)?'
    r'(?:words?|terms?|names?|labels?)\b|^\s*[^,，。;!?]{0,30}(?:名称|术语|字词)', re.I)
_METATEXT_PREDICATE = re.compile(r'\b(?:appear\w*|list\w*|mention\w*|refer\w*)\b|列于|列在|载于', re.I)
_METATEXT_OBJECT = re.compile(r'\b(?:glossar\w*|index|lists?|terms?)\b|索引|词汇表|术语表', re.I)
# An effort/commitment operator does not turn its abstract purpose into a
# business action. Concrete unfamiliar complements remain candidates below.
_OBJECTIVE = re.compile(r'\b(?:striv\w*|aspir\w*|aim(?:s|ed|ing)?|committed\s+to|'
                         r'efforts?\s+to)\b|努力|争取|坚持', re.I)
_PRINCIPLE = re.compile(r'^(?P<content>.+?)的(?:原则|理念|愿景)$')
# These are the pre-existing promotional/goal roles, scoped to an NP. Their
# presence is an unresolved relevance observation, never a new negative
# independent-payload proof in the source assertion owner.
_TENTATIVE_HEAD = re.compile(r'^(?:goals?|visions?|aspirations?|愿景|原则|理念)$', re.I)
_PROMOTIONAL = re.compile(r'^(?:(?:outstanding|strategic|best-in-class)\s*|(?:宏伟|远大|美好)(?:的)?)'
                          r'(?:(?:goals?|aspirations?|products?|services?|solutions?|visions?)|愿景|目标|未来)?$', re.I)
_DEGREE = re.compile(r'^(?:more|most|less|least|fewer|fewest|(?:更|最)?(?:大|小|多|少|高|低))$', re.I)


def _argument_relevance(value: str) -> str:
    value = value.strip(' \t\r\n.。!?？！;；')
    if abstract_source_argument(value) or _DEGREE.fullmatch(value):
        return 'abstract'
    if _TENTATIVE_HEAD.fullmatch(value) or _PROMOTIONAL.fullmatch(value):
        return 'unresolved'
    return 'specific'


def _nominal_relevance(nominals: tuple[str, ...], modifiers: tuple[str, ...]) -> str:
    """A modifier cannot turn a generic NP head into a specific argument.

    Unknown nominal compounds can carry real operating content. A tentative
    governing head (a goal/vision) remains tentative regardless of adjective;
    promotional modifiers of otherwise abstract heads supply uncertainty,
    never independent descriptive proof.
    """
    if not nominals:
        return 'unresolved'
    head = _argument_relevance(nominals[-1])
    if head == 'unresolved':
        return head
    values = tuple(_argument_relevance(value) for value in nominals)
    if 'specific' in values:
        return 'specific'
    modifier_values = tuple(_argument_relevance(value) for value in modifiers)
    if 'unresolved' in values or 'unresolved' in modifier_values:
        return 'unresolved'
    if 'specific' in modifier_values:
        # A modified source offering (e.g. unfamiliar technical software) can
        # remain readable without creating a payload proof. A generic benefit
        # or tentative goal cannot borrow that offering-head responsibility.
        return 'specific' if source_offering_head(nominals[-1]) else 'unresolved'
    return 'abstract'


def source_clause_context(value: str, role: AssertionRole, *,
                          work_budget: WorkBudget | None = None) -> SourceClauseContext:
    """Observe a prepared clause's discourse purpose once, before fallbacks.

    Typed independent content retains its own authority. A generic effort is
    not negative by itself: only a closed principle/courtesy envelope can be
    settled without the matrix/complement observation.
    """
    objective = _OBJECTIVE.search(value)
    if role.independent_payload is False:
        return SourceClauseContext('context', 'source_generic_objective')
    if role.independent_payload is True and not objective:
        return SourceClauseContext()
    if role.argument_targets and not objective:
        # Reuse exact arguments already matched by the function-role owner.
        # In particular a generic POS dictionary may split a compound noun
        # into a verb and noun. That retokenization cannot override a fully
        # observed tentative/promotional argument. Unknown targets continue
        # to the shared matrix/complement observer below.
        if work_budget is not None:
            work_budget.charge(SOURCE_TARGET_SCAN_PASSES * sum(map(len, role.argument_targets)))
        targets = tuple(_argument_relevance(target) for target in role.argument_targets)
        if all(value != 'specific' for value in targets):
            return SourceClauseContext('unresolved', 'source_payload_unresolved') if 'unresolved' in targets else (
                SourceClauseContext('context', 'source_abstract_objective'))
    if arithmetic_presentation(value):
        return SourceClauseContext('context', 'source_arithmetic_presentation')
    if _PAGE_NAME.fullmatch(value):
        return SourceClauseContext('context', 'source_page_name')
    subject = _METATEXT_SUBJECT.search(value)
    if subject and (predicate := _METATEXT_PREDICATE.search(value, subject.end())):
        if _METATEXT_OBJECT.search(value, predicate.end()):
            return SourceClauseContext('context', 'source_metatext')
    courtesy = COURTESY.search(value)
    if courtesy:
        prefix = value[:courtesy.start()].strip()
        if (not prefix or ISSUER_WORD.fullmatch(prefix)) and not value[courtesy.end():].strip(' .。!?！?;；'):
            return SourceClauseContext('context', 'source_courtesy')
    if objective:
        target = value[objective.end():].strip(' .。!?！?;；')
        principle = _PRINCIPLE.fullmatch(target)
        if principle:
            content = ''.join(re.sub(r'^(?:可|能|会|将)', '', part.strip())
                              for part in re.split('[、,，]', principle['content']))
            if abstract_source_argument(content):
                return SourceClauseContext('context', 'source_generic_principle')
        if courtesy and courtesy.start() < objective.start():
            # A concrete independently observed operation was handled above;
            # a courtesy followed only by an unproved effort is not its proof.
            return SourceClauseContext('unresolved', 'source_courtesy_objective_unproved')
    return SourceClauseContext(objective_operator=objective is not None,
                               objective_end=objective.end() if objective else None)


def statement_complement_context(value: str, role: AssertionRole,
                                 observation: StatementObservation, *,
                                 prepared: SourceClauseContext,
                                 quantified_argument: Callable[[str], bool] | None = None) -> SourceClauseContext:
    """Consume one charged syntax observation; never run the tagger again."""
    if prepared.complement_observed:
        return prepared
    prepared = replace(prepared, complement_observed=True)
    if role.independent_payload is True and not prepared.objective_operator:
        return prepared
    arguments = observation.argument_scopes
    relevance = (tuple(_nominal_relevance(scope.argument_nominals, scope.argument_modifiers) for scope in arguments)
                 if arguments else ((_nominal_relevance(observation.argument_nominals, ()),)
                                    if observation.argument_nominals else ()))
    if (prepared.objective_operator or role.operating) and relevance:
        if all(value != 'specific' for value in relevance):
            if quantified_argument is not None and any(scope.argument_quantifiers
                    and quantified_argument(' '.join(scope.argument_nominals))
                    for scope in observation.argument_scopes):
                # This is a bound direct-argument role, not a number/unit
                # interpretation or achieved/planned metric proof. Its source
                # words remain unresolved until the original metric owner
                # independently supplies that proof.
                return replace(prepared, status='unresolved', reason='source_goal_quantity_unresolved', relevant=True)
            if 'unresolved' in relevance:
                return replace(prepared, status='unresolved', reason='source_payload_unresolved')
            return replace(prepared, status='context', reason='source_abstract_objective')
    # Membership alone describes a relationship, not its economic relevance.
    # A prepared business head/function is a relevance observation even when
    # its unfamiliar members are not independent typed event proof. Otherwise
    # preserve the unresolved original without claiming a summary anchor.
    if observation.weak_relation and not role.operating:
        return replace(prepared, status='unresolved', reason='source_membership_relevance_unproved')
    return prepared
