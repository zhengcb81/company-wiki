"""A recorded assessment retains its versioned meaning across runtime upgrades."""

from dataclasses import replace
import json

import pytest

from company_wiki.automation.models import HandlerOutcome
from company_wiki.automation.narrative_contracts import SourceRevisionEventPayload
from company_wiki.automation.narrative_select import NarrativeSelectHandler
from company_wiki.automation.narrative_summary_execution import (
    parse_summary_job_result, wrap_summary,
)
from company_wiki.automation.narrative_verify import NarrativeVerifyHandler
from company_wiki.source_catalog import narrative_summary_protocols as protocols
from company_wiki.source_catalog.narrative_contracts import NarrativeBundle, NarrativeContractError
from unit.test_atomic_summary_artifacts import VERSION, materials
from unit import test_narrative_select_handler as select_fixture
from unit import test_narrative_verify_handler as verify_fixture


def _frozen_result(monkeypatch, assessor_version, *, source=None, **claim):
    """Create a coherent old wire through the actual summary and verification paths."""
    old = replace(protocols.ATOMIC_SCOPED, assessor_version=assessor_version)
    with monkeypatch.context() as historical:
        for name in ("_BY_PROJECTION", "_BY_REQUEST", "_BY_PROMPT"):
            index = getattr(protocols, name)
            historical.setattr(protocols, name, {
                key: old if protocol == protocols.ATOMIC_SCOPED else protocol
                for key, protocol in index.items()
            })
        source, summary, report = materials(source, **claim)
        assert report["validator"]["version"] == assessor_version
        bundle = NarrativeVerifyHandler._bundle(
            source, summary, source.prompt_review, reading_projection_version=VERSION,
        )
        assert bundle.to_dict()["summary_assessment"]["validator"]["version"] == assessor_version
        return source, summary, bundle.to_dict(), wrap_summary(summary, report)


@pytest.mark.parametrize("surface", ["bundle", "summary-job"])
def test_frozen_atomic_1_1_artifact_survives_current_1_2_production(monkeypatch, surface):
    source, summary, bundle, result = _frozen_result(monkeypatch, "source-summary-assessment/1.1.0")
    assert protocols.scoped_protocol_for_projection(VERSION).assessor_version == "source-summary-assessment/1.2.0"
    if surface == "bundle":
        assert NarrativeBundle.from_dict(json.loads(json.dumps(bundle))).to_dict() == bundle
    else:
        assert parse_summary_job_result(json.loads(json.dumps(result)), selected=source) == summary


@pytest.mark.parametrize("surface", ["bundle", "summary-job"])
def test_atomic_protocol_rejects_coherent_assessment_from_incompatible_family(monkeypatch, surface):
    source, _, bundle, result = _frozen_result(monkeypatch, "source-summary-assessment/1.0.0")
    with pytest.raises(NarrativeContractError):
        if surface == "bundle":
            NarrativeBundle.from_dict(bundle)
        else:
            parse_summary_job_result(result, selected=source)


def test_pending_verify_replays_source_and_publishes_the_original_assessment(monkeypatch):
    statement = "We launched a new product and expanded overseas capacity."
    data = f"Full Conference Call Transcript\nCEO: {statement}\n".encode("utf-8")
    payload = select_fixture._payload(data, title="Company earnings call", document_kind="earnings_call_transcript",
                                      language="en", mime_type="text/plain")
    source = NarrativeSelectHandler(
        reader=select_fixture.FakeReader(payload, data), selector_version="0.9.0",
    ).select_source(SourceRevisionEventPayload.from_dict(payload), checkpoint=lambda: None)
    _, summary, historical_bundle, wrapped = _frozen_result(
        monkeypatch, "source-summary-assessment/1.1.0", source=source, claim_text=statement, modality="uncertain",
    )
    context = verify_fixture._context(source, summary)
    context = replace(context, dependency_results={
        **context.dependency_results,
        "source.narrative_summarize": verify_fixture._dependency(wrapped),
    })

    verified = NarrativeVerifyHandler(
        reader=verify_fixture.FakeReader(source, data), selector_version=source.selector.version,
        reading_model_projection=lambda _: VERSION,
    )(context)
    assert verified.outcome is HandlerOutcome.SUCCEEDED, verified.error
    assert len(verified.effects) == 1
    assert NarrativeBundle.from_dict(verified.result).to_dict() == historical_bundle
