"""The shared finalizer measures real raw context and charges actual spans."""
import json

from company_wiki.source_catalog import narrative_finalize as finalizer
from company_wiki.source_catalog.narrative_evidence import _HEADING_ONLY
from company_wiki.source_catalog.narrative_routing import route_document
from integration.test_n6_budget_packages import FIXTURE_PATH, _structure, _candidate


def test_semantic_finalizer_measures_original_text_without_rewriting_it(monkeypatch):
    sample = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["samples"][0]
    candidates = tuple(_candidate(rec, sample["source_id"]) for rec in sample["units"])
    groups = {rec["unit_id"]:rec["group_id"] for rec in sample["units"] if rec["group_id"] is not None}
    seen = []
    original = finalizer.select_budget_items
    def observe(items, **kwargs):
        seen.append((items, kwargs))
        return original(items, **kwargs)
    monkeypatch.setattr(finalizer, "select_budget_items", observe)
    route = route_document(sample["title"], existing_kind=sample["existing_kind"])
    package = finalizer.finalize_selection(_structure(sample), route, candidates,
        group_ids=groups, heading_pattern=_HEADING_ONLY, dropped_financial_count=0,
        budget_policy="semantic_coverage/1")
    items, kwargs = seen[0]
    assert kwargs == {"limit":route.selection_limit, "policy":"semantic_coverage/1"}
    assert items and all(item.evidence_chars == len(item.payload.unit.raw_text) for item in items)
    actual = {candidate.unit.coordinates.locator():candidate.unit.raw_text for candidate in candidates}
    assert all(span.raw_text == actual[span.locator] for span in package.evidence_spans)
    assert len(package.evidence_spans) <= route.selection_limit
    assert package.omitted_candidate_count == len(candidates)-len(package.evidence_spans)
