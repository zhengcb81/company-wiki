"""Selection capacity and local computation are distinct from model charges."""
import re

import pytest

from company_wiki.resource_budget import WorkBudget
from company_wiki.source_contract import EvidenceCoordinates
from company_wiki.source_catalog.narrative_candidates import EvidenceCandidate
from company_wiki.source_catalog.narrative_document import DocumentStructure
from company_wiki.source_catalog.narrative_evidence import _make_unit
from company_wiki.source_catalog.narrative_finalize import finalize_selection
from company_wiki.source_catalog.narrative_budget import READING_BUDGET_POLICY
from company_wiki.source_catalog.narrative_reading import select_reading_evidence
from company_wiki.source_catalog.narrative_routing import DocumentRoute

SOURCE_ID = "urn:company-wiki:source:sha256:" + "a" * 64


def document():
    units = tuple(_make_unit(source_id=SOURCE_ID, parser_version="0.1.0",
        coordinates=EvidenceCoordinates(paragraph_index=index),
        raw_text=text, unit_kind="paragraph", source_role="company_filing", language="en", metadata={})
        for index, text in enumerate(("Our product has entered customer qualification.",
                                     "Our factory has opened a new assembly line.")))
    return DocumentStructure(SOURCE_ID, "a" * 64, "en", units, line_count=2, mime_type="text/plain")


@pytest.mark.parametrize(("spans", "chars", "code", "dimension"), [
    (1, 48000, "budget_full", "selection_spans"),
    (96, 1, "character_budget", "selection_characters"),
])
def test_selection_diagnostic_reports_actual_capacity_dimension(spans, chars, code, dimension):
    parsed = document()
    candidates = tuple(EvidenceCandidate(unit, ("core_business",), ("operating_activity",), 3)
                       for unit in parsed.units)
    result = finalize_selection(parsed, DocumentRoute("annual_report", spans, False), candidates,
        group_ids={}, heading_pattern=re.compile(r"(?!)"), dropped_financial_count=0,
        budget_policy=READING_BUDGET_POLICY, max_chars=chars)
    diagnostic = next(item for item in result.selection_diagnostics if item["code"] == code)
    assert diagnostic["dimension"] == dimension
    assert diagnostic["phase"] == "selection"
    assert diagnostic["limit"] == (spans if dimension == "selection_spans" else chars)
    assert diagnostic["used"] == (len(result.evidence_spans) if dimension == "selection_spans" else
                                   sum(len(span.raw_text) for span in result.evidence_spans))
    assert diagnostic["external_model_cost"] is False


def test_public_selector_reports_document_work_refusal_with_real_counters():
    budget = WorkBudget(0, phase="parse-and-select")
    result = select_reading_evidence(document(), title="Annual Report", work_budget=budget)
    diagnostic = next(item for item in result.selection_diagnostics if item["code"] == "work_budget_exhausted")
    assert diagnostic["dimension"] == "document_work"
    assert diagnostic["phase"] == "parse-and-select"
    assert (diagnostic["used"], diagnostic["requested"], diagnostic["limit"]) == (0, 1, 0)
    assert diagnostic["external_model_cost"] is False
    assert not result.evidence_spans and not result.coverage_complete
