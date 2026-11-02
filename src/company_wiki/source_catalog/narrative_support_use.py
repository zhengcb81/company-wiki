"""Source-owned summary support capability, separate from readable originals.

The caller supplies one exact closed support scope and its source assessment.
No IO, source selection, ranking, numeric conversion or context donation.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .n6_candidate_operating_facts import OperatingFact
from .narrative_business_disclosures import UNRESOLVED_READING_REASONS
from .narrative_source_purpose import NON_OPERATING_PURPOSES, descriptive_operating_relation
from company_wiki.document_understanding.operating_states.assertion_roles import SourceAssertionRoles, prepare_source_assertions
from .narrative_source_passage import SourcePassageCapability

SUPPORT_USE_SCAN_PASSES = 8


def source_narrative_relevance(*, fact: OperatingFact,
                               source_roles: SourceAssertionRoles | None,
                               table_qualified: bool = False,
                               passage: SourcePassageCapability | None = None) -> bool:
    """Independent offer relevance from already observed source evidence.

    Readability and numeric uncertainty alone confer no operating relevance.
    This consumes the shared assessment; it never scans or classifies text.
    """
    if passage is not None:
        return table_qualified or passage.relevant
    if fact.purpose in NON_OPERATING_PURPOSES or fact.purpose == 'unassessed':
        return False
    if source_roles is not None and source_roles.independent_payload is False:
        return table_qualified
    if source_roles is not None:
        return (table_qualified or source_roles.independent_payload is True or source_roles.source_scope
                or source_roles.bound_operating or source_roles.numeric_role == 'operating')
    return table_qualified or bool(fact.eligible and set(fact.reasons) - UNRESOLVED_READING_REASONS)


def source_support_use(text: str, *, fact: OperatingFact, financial_only: bool | None,
                       table_qualified: bool = False, context_role: bool = False,
                       source_relations: Mapping[str, Any] | None = None,
                       support_unit_ids: Sequence[str] = (),
                       source_roles: SourceAssertionRoles | None = None,
                       numeric_ambiguous: bool | None = None,
                       passage: SourcePassageCapability | None = None) -> tuple[str, str]:
    """Describe one source scope; neither score nor unknown purpose is a gate."""
    if context_role:
        return "context_only", "attribution_context"
    if table_qualified:
        return "support", "qualified_operating_table"
    if passage is not None:
        if passage.use == 'support' and numeric_ambiguous is True:
            # The exact scope's structural observation takes precedence over
            # general prose readability. Keep its relevance for source offer;
            # do not manufacture numerical support or call it finance-only.
            return 'unresolved', 'source_numeric_scope_unresolved'
        return passage.use, passage.reason
    if financial_only is None or fact.purpose == "unassessed":
        return "unresolved", "source_assessment_incomplete"
    if not text.strip():
        return "unresolved", "source_support_empty"
    if fact.purpose in NON_OPERATING_PURPOSES:
        return "context_only", "non_operating_purpose"
    if financial_only:
        return "context_only", "financial_only"
    source_roles = source_roles if source_roles is not None else prepare_source_assertions(text)
    ambiguous=numeric_ambiguous if numeric_ambiguous is not None else source_roles.numeric_ambiguous
    operating_cells=(source_roles.numeric_cells_observed and source_roles.numeric_role=='operating'
                     and not source_roles.operating)
    if ambiguous or operating_cells:
        if source_roles.numeric_role == "account" and not source_roles.operating:
            return "context_only", "financial_numeric_scope"
        return "unresolved", "source_numeric_scope_unresolved"
    if source_roles.independent_payload is False:
        return "context_only", "source_generic_objective"
    if source_roles.independent_payload is True:
        return ("support", "source_business_relation" if fact.eligible
                and set(fact.reasons) - UNRESOLVED_READING_REASONS else "source_operating_description")
    if source_roles.source_scope:
        return 'support', 'source_declared_scope'
    # Refs only locate characters. Completeness is the source owner's prepared
    # role proof, not a second vote from an unknown stage or arbitrary NP refs.
    # Optional relation/ref arguments remain read-compatible with earlier
    # callers; they cannot bypass the semantic assessment.
    if descriptive_operating_relation(text, prepared=source_roles):
        return "unresolved", "source_payload_unresolved"
    return "context_only", "no_independent_business_support"
