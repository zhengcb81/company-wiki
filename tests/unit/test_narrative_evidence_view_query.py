"""The public query adapter rejects invalid resource limits before transport."""

import pytest

from company_wiki.automation.narrative_evidence_view import (
    NarrativeEvidenceViewQuery, NarrativeEvidenceViewReader,
)


@pytest.mark.parametrize("operation,filters", [
    ("evidence-list", {"limit": True}), ("evidence-list", {"offset": False}),
    ("evidence-search", {"query": 123}),
    ("evidence-search", {"query": "海外" * 1000}),
    ("evidence-lookup", {"span_id": " anchor "}),
    ("evidence-lookup", {"locator": "x" * 1025}),
])
def test_invalid_public_filter_never_reaches_raw_transport(operation, filters):
    class NoRead:
        def read(self, _request):
            pytest.fail("invalid input reached transport")

    reader = NarrativeEvidenceViewReader(NoRead())
    with pytest.raises(ValueError):
        reader.read(None, NarrativeEvidenceViewQuery(operation, **filters))


def test_unvalidated_query_mapping_cannot_trigger_transport():
    class NoRead:
        def read(self, _request):
            pytest.fail("unvalidated mapping reached transport")

    with pytest.raises(ValueError):
        NarrativeEvidenceViewReader(NoRead()).read(None, {"operation": "evidence-list"})
