"""Source discourse/complement roles, distinct from matrix syntax and facts.

This is a closed grammar of reporting and rhetorical roles, not a vocabulary
of companies, industries or approved business verbs. Unknown content stays
unresolved; it is not evidence of an operation or of a financial-only source.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from company_wiki.document_understanding.operating_states.assertion_roles import (
    AssertionRole, abstract_source_argument,
)
from company_wiki.document_understanding.operating_states.patterns import COURTESY, ISSUER_WORD
from company_wiki.document_understanding.statement_grammar import StatementObservation

from .narrative_reporting_rules import arithmetic_presentation


# Conservative upper envelope of regex visits, not a wall-clock multiplier:
# bounded arithmetic/name/meta guards, objective/principle/abstract/courtesy,
# then the cached matrix's nominal complement. Mutually exclusive branches
# return early; no source clause is sent to this preparation twice.
SOURCE_CONTEXT_SCAN_PASSES = 12


@dataclass(frozen=True)
class SourceClauseContext:
    status: str = 'candidate'
    reason: str = ''
    objective_operator: bool = False


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


def source_clause_context(value: str, role: AssertionRole) -> SourceClauseContext:
    """Observe a prepared clause's discourse purpose once, before fallbacks.

    Typed independent content retains its own authority. A generic effort is
    not negative by itself: only a closed principle/courtesy envelope can be
    settled without the matrix/complement observation.
    """
    if role.independent_payload is True:
        return SourceClauseContext()
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
    objective = _OBJECTIVE.search(value)
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
    return SourceClauseContext(objective_operator=objective is not None)


def statement_complement_context(value: str, role: AssertionRole,
                                 observation: StatementObservation, *,
                                 prepared: SourceClauseContext) -> SourceClauseContext:
    """Consume one charged syntax observation; never run the tagger again."""
    if role.independent_payload is True:
        return SourceClauseContext()
    if prepared.objective_operator and observation.argument_nominals:
        if all(abstract_source_argument(part) for part in observation.argument_nominals):
            return SourceClauseContext('context', 'source_abstract_objective')
    # Membership alone describes a relationship, not its economic relevance.
    # A prepared business head/function is a relevance observation even when
    # its unfamiliar members are not independent typed event proof. Otherwise
    # preserve the unresolved original without claiming a summary anchor.
    if observation.weak_relation and not role.operating:
        return SourceClauseContext('unresolved', 'source_membership_relevance_unproved')
    return SourceClauseContext()
