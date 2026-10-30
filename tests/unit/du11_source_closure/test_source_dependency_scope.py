"""Source closure must be active on real parser output and causal on its owners."""
from hashlib import sha256
from importlib import import_module

import pytest

from company_wiki.document_understanding import decision_inventory


@pytest.mark.parametrize("name", [
    "company_wiki.document_understanding.operating_states.relations",
    "company_wiki.document_understanding.operating_states.patterns",
    "company_wiki.document_understanding.operating_states.assertion_roles",
    "company_wiki.document_understanding.operating_states.text_view",
    "company_wiki.document_normalization.text_matching",
    "company_wiki.source_catalog.n6_candidate_operating_facts",
])
def test_actual_source_grammar_bytes_invalidate_decision_without_a_version_bump(name, tmp_path, monkeypatch):
    module = import_module(name)
    before = decision_inventory._versions()
    changed = tmp_path / "changed_owner.py"
    changed.write_text("# genuinely changed matching owner\n", encoding="utf-8")
    monkeypatch.setattr(module, "__file__", str(changed))
    after = decision_inventory._versions()
    assert before["business_algorithms"] != after["business_algorithms"]


def test_real_pdf_parser_identifies_its_format_for_source_flow():
    import pymupdf as fitz
    from company_wiki.source_catalog.narrative_evidence import parse_pdf_bytes
    from company_wiki.source_contract import source_id_for_sha256

    with fitz.open() as document:
        page = document.new_page()
        page.insert_text((70, 100), "The company ships new products to its customers.")
        data = document.tobytes()
    digest = sha256(data).hexdigest()
    result = parse_pdf_bytes(data, source_id=source_id_for_sha256(digest),
        source_sha256=digest, language="en", full_table_scan=True)
    assert result.units and result.coverage_complete
    assert result.mime_type == "application/pdf"


@pytest.mark.parametrize("count", [16, 32])
def test_new_subject_scans_only_the_original_subject_not_every_later_predicate(count, monkeypatch):
    from company_wiki.document_understanding.operating_states import patterns, relations

    original = patterns.PRODUCT_SUFFIX
    scanned = []

    class Observed:
        def search(self, text):
            scanned.append(len(text))
            return original.search(text)

    monkeypatch.setattr(patterns, "PRODUCT_SUFFIX", Observed())
    text = "Our " + "customers has " * count + "yet."
    assert not relations.independent_statement_start(text)
    assert sum(scanned) <= 3 * len(text)
