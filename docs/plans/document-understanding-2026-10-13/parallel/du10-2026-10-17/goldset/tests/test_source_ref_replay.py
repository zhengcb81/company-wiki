"""Real temporary-catalog controls for corpus replay; no production roots."""
from copy import deepcopy
from dataclasses import asdict
import hashlib

import fitz
import pytest

from company_wiki.source_catalog import SourceCatalog
from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.source_reader import SourceVersionReader
from verify_anchors import verify_case


@pytest.fixture
def registered_pdf(tmp_path):
    root = tmp_path / "originals"
    original = root / "Acme" / "annual_report_2025.pdf"
    original.parent.mkdir(parents=True)
    with fitz.open() as doc:
        doc.new_page().insert_text((72, 72), "Acme opened three new service centers.")
        original.write_bytes(doc.tobytes())
    data = original.read_bytes()
    before = (hashlib.sha256(data).hexdigest(), original.stat().st_mtime_ns)
    catalog = SourceCatalog(CatalogConfig(tmp_path, tmp_path / "catalog",
                            (RootSpec("fixture", root, "company_raw"),)))
    try:
        registered = catalog.register_sources(root_id="fixture",
                         relative_paths=["Acme/annual_report_2025.pdf"])
        assert registered.errors == 0
        reader = SourceVersionReader(catalog)
        sha = before[0]
        ref = reader.query_ref("urn:company-wiki:document:sha256:" + sha,
                               "urn:company-wiki:source:sha256:" + sha, sha)
        case = {"case_id": "fixture", "carrier": ".pdf", "source_ref": asdict(ref),
                "facts": [{"id": "centers", "any_support_sets": [[{
                    "page": 1, "location_kind": "page",
                    "exact_quote": "opened three new service centers"}]]}],
                "misread_traps": []}
        yield case, reader
    finally:
        catalog.close()
        assert (hashlib.sha256(original.read_bytes()).hexdigest(),
                original.stat().st_mtime_ns) == before


def test_real_source_ref_and_page_quote_pass(registered_pdf):
    case, reader = registered_pdf
    assert verify_case(case, reader)["status"] == "PASS"


@pytest.mark.parametrize("mutation", ["sha", "size", "page", "quote"])
def test_stale_ref_or_false_locator_never_passes(registered_pdf, mutation):
    original, reader = registered_pdf
    case = deepcopy(original)
    if mutation == "sha":
        case["source_ref"]["content_sha256"] = "0" * 64
    elif mutation == "size":
        case["source_ref"]["byte_size"] += 1
    elif mutation == "page":
        case["facts"][0]["any_support_sets"][0][0]["page"] = 2
    else:
        case["facts"][0]["any_support_sets"][0][0]["exact_quote"] = "invented revenue"
    assert verify_case(case, reader)["status"] == "FAIL"
