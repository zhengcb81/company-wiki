"""Measure the actual shared engine output; gold never supplies observed text."""
import hashlib
from importlib import import_module

import pytest

from company_wiki.document_normalization import normalize_document
from company_wiki.document_understanding import understand_units, build_summary_input
from tools.document_understanding_benchmark.checkers import check_recall_fact, check_context


def produced():
    original = b"<html><body><h1>FORM 8-K</h1><h2>Exhibit 99.1</h2><h2>Second Quarter Results</h2><h3>Business Highlights</h3><p>We launched a new product in Europe during the quarter.</p></body></html>"
    sha = hashlib.sha256(original).hexdigest()
    source_id = "urn:company-wiki:source:sha256:" + sha
    normalized = normalize_document(original, source_id=source_id, source_sha256=sha, mime_type="text/html")
    pipeline = understand_units(normalized.units, source_id=source_id, source_sha256=sha,
                                mime_type="text/html", metadata={"form_type": "8-K", "regime": "sec"})
    return pipeline, build_summary_input(pipeline)


def test_real_engine_selection_is_mapped_to_original_source_material():
    observe = import_module("tools.document_understanding_benchmark.du_observer").observe_pipeline
    pipeline, request = produced()
    observed = observe(pipeline, request, sample_id="probe")
    fact = {"id": "launch", "importance": "critical", "target_kind": "required_business",
            "any_support_sets": [[{"location_kind": "document", "exact_quote": "launched a new product in Europe"}]],
            "must_preserve": [], "must_not_assert": []}
    assert check_recall_fact(fact, observed)["status"] == "PASS"
    assert observed["claims"] == [] and observed["execution"]["calls"] == 0
    assert observed["coverage"]["read_pages"] is None
    assert all(row["locator"] in observed["selected_locators"] for row in observed["selected_evidence"])
    assert check_context(observed, {})["status"] != "FAIL"


def test_materialisation_cannot_substitute_generated_words_for_originals():
    observe = import_module("tools.document_understanding_benchmark.du_observer").observe_pipeline
    pipeline, request = produced()
    request["evidence_packages"][0]["members"][0]["text"] = "invented overseas orders"
    with pytest.raises(ValueError, match="original"):
        observe(pipeline, request, sample_id="probe")


def test_different_source_request_is_rejected():
    observe = import_module("tools.document_understanding_benchmark.du_observer").observe_pipeline
    pipeline, request = produced()
    request["source_ref"] = {"source_sha256": "0" * 64}
    with pytest.raises(ValueError, match="original"):
        observe(pipeline, request, sample_id="probe")


def test_missing_actual_context_is_measured_as_failure():
    observe = import_module("tools.document_understanding_benchmark.du_observer").observe_pipeline
    pipeline, request = produced()
    request["evidence_packages"][0]["required_locators"] = ["missing-context"]
    observed = observe(pipeline, request, sample_id="probe")
    assert check_context(observed, {})["status"] == "FAIL"



def test_top_level_ref_cannot_relabel_other_source_observation():
    observe = import_module("tools.document_understanding_benchmark.du_observer").observe_pipeline
    pipeline, request = produced()
    pipeline["observation"]["source_ref"] = {"source_sha256": "0" * 64}
    with pytest.raises(ValueError, match="original"):
        observe(pipeline, request, sample_id="probe")
