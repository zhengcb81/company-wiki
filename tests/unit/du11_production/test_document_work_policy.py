"""Actual PDF ports: changed work cannot reuse an unexamined cached prefix."""
import hashlib
import socket
from types import SimpleNamespace

import pymupdf as fitz
import pytest
import yaml

from company_wiki.automation.narrative_generation import current_reading_decision_matches
from company_wiki.automation.narrative_select import NarrativeSelectHandler, _SelectFailure


@pytest.fixture
def run_pdf(tmp_path, monkeypatch):
    config = tmp_path / "budget.yaml"
    monkeypatch.setenv("COMPANY_WIKI_BUDGET_CONFIG", str(config))

    def blocked(*args, **kwargs):
        raise AssertionError("PDF budget tests cannot use a network")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    with fitz.open() as doc:
        for index in range(3):
            page = doc.new_page()
            lines = (["Annual Report", "Management Discussion and Analysis", "Business Review",
                      "Our company has launched a new production line.",
                      "Our company delivered new equipment to customers."] if index == 0 else
                     ["Products and capacity", "Our company has expanded the factory and increased capacity.",
                      "Our new product has entered customer qualification."])
            for line_index, line in enumerate(lines):
                page.insert_text((50, 50 + line_index * 24), line, fontsize=11)
        doc.set_toc([[1, "Management Discussion and Analysis", 1], [2, "Products and capacity", 2]])
        original = doc.tobytes()
    digest = hashlib.sha256(original).hexdigest()
    payload = SimpleNamespace(source_ref=SimpleNamespace(mime_type="application/pdf",
        source_id="urn:company-wiki:source:sha256:" + digest, content_sha256=digest),
        source_metadata=SimpleNamespace(language="en", title="Annual Report", document_kind="annual_report"))

    def run(work, *, tokens=10_000_000, micro_usd=20_000_000):
        config.write_text(yaml.safe_dump({"schema_version": "company-wiki-budget-policy/1",
            "external_model": {"cumulative_tokens": tokens, "cumulative_micro_usd": micro_usd},
            "company_allocation": {"enforcement": "soft", "target_tokens": 150_000,
                                   "target_micro_usd": 1_000_000},
            "document_processing": {"max_work_units": work}}), encoding="utf-8")
        observed = {}

        class ObservedHandler(NarrativeSelectHandler):
            def _parse_pdf(self, *args, **kwargs):
                observed["budget"] = kwargs["work_budget"]
                parsed = super()._parse_pdf(*args, **kwargs)
                observed["after_parse"] = kwargs["work_budget"].used
                return parsed

            def _run_selector(self, *args, **kwargs):
                assert kwargs["work_budget"] is observed["budget"]
                assert kwargs["work_budget"].used == observed["after_parse"]
                selected = super()._run_selector(*args, **kwargs)
                observed["selection"] = selected
                return selected

        handler = ObservedHandler(reader=object(), selector_version="0.9.0")
        try:
            handler._select_pdf(payload, original, SimpleNamespace(checkpoint=lambda: None))
        except _SelectFailure:
            assert work < 16_000_000
        assert hashlib.sha256(original).hexdigest() == digest
        assert observed["budget"].max_work_units == work
        return observed

    return run


def manifest(package):
    return {"reading_dependencies": package.reading_dependencies,
            "selection_generation": {"decision_digest": package.reading_dependencies["decision_digest"]}}


def test_partial_work_retains_diagnostics_and_is_not_a_complete_cache(run_pdf):
    complete = run_pdf(16_000_000)
    assert not complete["budget"].exhausted and complete["selection"].evidence_spans
    # Derive a real refusal from the current algorithm's work, not a fixed
    # operation count that would make a future efficiency improvement fail.
    partial = None
    for numerator in (99, 95, 90, 80, 70, 60):
        observed = run_pdf(complete["budget"].used * numerator // 100)
        package = observed.get("selection")
        if observed["budget"].exhausted and package is not None and package.evidence_spans:
            partial = observed
            break
    assert partial is not None, "fixture must exercise actual source work exhaustion after useful evidence"
    selected, budget = partial["selection"], partial["budget"]
    row = next(item for item in selected.selection_diagnostics if item.get("dimension") == "document_work")
    assert row["used"] == budget.used and row["limit"] == budget.max_work_units
    assert row["external_model_cost"] is False and not selected.coverage_complete
    assert selected.reading_dependencies["status"] != "complete"
    assert not current_reading_decision_matches(manifest(selected))
    run_pdf(32_000_000)
    assert not current_reading_decision_matches(manifest(selected))


def test_only_work_configuration_changes_source_cache_identity(run_pdf):
    original = run_pdf(16_000_000)["selection"]
    assert original.reading_dependencies["status"] == "complete"
    assert current_reading_decision_matches(manifest(original))
    run_pdf(16_000_000, tokens=0, micro_usd=0)
    assert current_reading_decision_matches(manifest(original)), "money cannot invalidate source interpretation"
    run_pdf(32_000_000)
    assert not current_reading_decision_matches(manifest(original))
