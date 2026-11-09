"""Readability admission of an already prepared source scope; no selection or IO."""
from __future__ import annotations
from collections.abc import Mapping, Sequence
import re
from typing import Any
from .n6_candidate_operating_facts import OperatingFact
from .narrative_business_policy import detect_reading_business_fact, reading_financial_only
from .narrative_pdf_turns import printed_turn_is_context
from .narrative_source_purpose import NON_OPERATING_PURPOSES
from .narrative_support_use import source_support_use, source_narrative_relevance

CONTEXT_ROLES = frozenset({"operator", "analyst", "investor_question", "qa_text_shadow"})
def _financial_only(text: str, fact: Any = None) -> bool:
    fact = fact or detect_reading_business_fact(text)
    # A source-bound billing/scope/operating-driver/contract-conversion relation
    # can contain revenue words. It is not a routine accounting total; the
    # legacy rejector knows none of these opt-in relations.
    return reading_financial_only(text, fact)


def _admitted(unit: Any, reading: Mapping[str, Any], kind: str, *, fact: Any = None,
              is_heading: bool = False, table_qualified: bool = False,
              financial_only: bool | None = None,
              trace: dict[str, Any] | None = None, package_id: str | None = None,
              required_unit_ids: Sequence[str] = (),
              support_use: tuple[str, str] | None = None,
              offer_relevant: bool | None = None,
              assessment_complete: bool | None = None) -> tuple[bool, Any]:
    fact = fact if fact is not None else OperatingFact()
    closed_assessment = support_use is not None and offer_relevant is not None

    def decision(admitted: bool, reason: str | None = None) -> tuple[bool, Any]:
        if trace is not None:
            status = "admitted" if admitted else "not_admitted"
            counts = trace.setdefault("counts", {})
            counts[status] = counts.get(status, 0) + 1
            if reason is not None:
                reasons = trace.setdefault("rejection_counts", {})
                reasons[reason] = reasons.get(reason, 0) + 1
            samples = trace.setdefault("samples", {})
            rows = samples.setdefault(reason or status, [])
            if len(rows) < 4:
                rows.append({
                    "target_id": unit.unit_id,
                    "package_id": package_id,
                    "status": status,
                    "reason": reason,
                    "fact_purpose": fact.purpose,
                    "fact_reasons": list(fact.reasons[:4]),
                    "fact_reason_count": len(fact.reasons),
                    "required_unit_ids": list(required_unit_ids[:16]),
                    "required_unit_count": len(required_unit_ids),
                    "priority": max(1, int(reading.get("priority", 2))),
                })
        return admitted, fact

    prepared_roles = None
    prepared_passage = None
    if fact.purpose == "unassessed":
        return decision(False, "unassessed_purpose")
    # Glyphs/page counters are observed text, not operating descriptions. A
    # numeric cell of an already qualified operating table is different: its
    # original headers, units and period travel in the complete dependency graph.
    if not fact.eligible:
        alphanumeric = "".join(character for character in unit.raw_text if character.isalnum())
        numeric_marker = bool(alphanumeric) and all(character.isnumeric() for character in alphanumeric)
        roman_marker = bool(re.fullmatch(r"[IVXLCDM]+", alphanumeric, re.IGNORECASE))
        letter_marker = bool(re.fullmatch(r"\s*[(\[（【]\s*[A-Za-z]\s*[)\]）】]\s*[.、:]?\s*", unit.raw_text))
        if not any(character.isalpha() for character in unit.raw_text) or numeric_marker:
            if not table_qualified or not any(character.isdigit() for character in unit.raw_text):
                return decision(False, "non_narrative_unit" if not any(character.isalpha() for character in unit.raw_text)
                                else "bare_numeric_marker")
        if roman_marker or letter_marker:
            return decision(False, "outline_marker")
    if support_use is None or offer_relevant is None:
        # Standalone compatibility calls use the identical source owner, not
        # an old fact union plus a separate new role preparation. Production
        # always supplies both cached axes and never enters this branch.
        from company_wiki.resource_budget import new_document_work_budget
        from .narrative_operating_relations import SourceOperatingSession
        if getattr(unit, "unit_id", None) is None:
            # Text-only compatibility has no canonical source references. Use
            # the same prepared reading owner without inventing identifiers.
            from .narrative_business_policy import prepare_reading_business_assessment
            assessment = prepare_reading_business_assessment(unit.raw_text, {"relations": []})
            fact, prepared_roles = assessment.fact, assessment.source_roles
            prepared_passage = assessment.passage
            if financial_only is None:
                financial_only = assessment.financial_only
        else:
            source = SourceOperatingSession({unit.unit_id: unit}, work_budget=new_document_work_budget())
            fact = source.fact(unit.unit_id)
            prepared_roles = source.source_assertions(unit.unit_id)
            prepared_passage = source.source_passage(unit.unit_id)
            if financial_only is None:
                financial_only = source.financial_only(unit.unit_id)
        if prepared_passage is not None:
            financial_only = prepared_passage.financial_only
            assessment_complete = prepared_passage.assessment_complete
    if (not closed_assessment and fact.purpose in NON_OPERATING_PURPOSES) or fact.purpose == "unassessed":
        return decision(False, "non_operating_purpose" if fact.purpose in NON_OPERATING_PURPOSES
                        else "unassessed_purpose")
    if kind == "operating_table" and not table_qualified:
        return decision(False, "table_not_qualified")
    if unit.source_role in CONTEXT_ROLES or printed_turn_is_context(unit):
        return decision(False, "source_context_role")
    if not closed_assessment and not table_qualified and (
        financial_only if financial_only is not None else _financial_only(unit.raw_text, fact)
    ):
        return decision(False, "financial_only")
    if (is_heading or unit.unit_kind.endswith("_heading")) and not fact.eligible:
        return decision(False, "heading_without_business_fact")
    # Reading intent is not proof of independent support. Descriptive business
    # material can still qualify without a known stage, number or duration.
    use, reason = support_use or source_support_use(unit.raw_text, fact=fact,
        financial_only=financial_only if financial_only is not None else _financial_only(unit.raw_text, fact),
        table_qualified=table_qualified, source_roles=prepared_roles, passage=prepared_passage)
    if assessment_complete is False and use != 'support':
        return decision(False, reason)
    if offer_relevant is None:
        offer_relevant=source_narrative_relevance(fact=fact,table_qualified=table_qualified,
            source_roles=prepared_roles, passage=prepared_passage)
    readable_business = offer_relevant and use in {"support", "unresolved"}
    if not offer_relevant and use == 'unresolved':
        return decision(False,'unresolved_without_business_relevance')
    return decision(readable_business, None if readable_business else reason)
