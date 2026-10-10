"""Projection evidence views keep real parent refs and one verified read."""

import json
import pytest
from company_wiki.automation.narrative_transport import NarrativeTransportReader
from company_wiki.automation.narrative_evidence_view import (
    NarrativeEvidenceViewReader,
    NarrativeEvidenceViewQuery,
)
from company_wiki.source_catalog.source_reader import SourceVersionReader
from integration.test_official_json_transport_subject import (
    owned_state,
    publish,
    loader_for,
    request,
)


@pytest.mark.parametrize(
    "operation", ["evidence-list", "evidence-search", "evidence-lookup"]
)
def test_projection_views_use_explicit_subject_and_each_true_parent(
    tmp_path, operation
):
    with owned_state(tmp_path) as state:
        subject = state.subjects[0]
        _version, generation, _bytes = publish(state, subject, "view-" + operation)
        calls = []
        transport = NarrativeTransportReader(
            state.artifacts,
            SourceVersionReader(state.catalog),
            projection_loader=loader_for(state, calls),
        )
        ref = transport.reference_subject(subject, generation_sha256=generation)
        query = (
            NarrativeEvidenceViewQuery(operation, query="overseas")
            if operation == "evidence-search"
            else NarrativeEvidenceViewQuery(
                operation, span_id=json.loads(_bytes)["evidence_spans"][0]["span_id"]
            )
            if operation == "evidence-lookup"
            else NarrativeEvidenceViewQuery(operation)
        )
        result = NarrativeEvidenceViewReader(transport).read(request(ref), query)
        value = json.loads(result.data)
        assert value["schema_version"] == "narrative-evidence-view/2"
        assert value["subject_binding"] == subject.to_dict()
        assert value["parent_source_refs"] == list(subject.parent_source_refs)
        assert (
            "manifest" not in value
            and "source_read_policy_sha256" not in result.receipt
        )
        assert result.receipt["schema_version"] == "narrative-evidence-read-receipt/2"
        assert calls == [subject] and value["items"]
        if operation == "evidence-search":
            assert {item["source_id"] for item in value["items"]} == {
                ref["source_id"] for ref in state.refs
            }
            assert {item["source_sha256"] for item in value["items"]} == {
                ref["content_sha256"] for ref in state.refs
            }
        else:
            assert {item["source_id"] for item in value["items"]} <= {
                ref["source_id"] for ref in state.refs
            }
