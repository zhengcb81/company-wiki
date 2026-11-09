"""The reading engine can consume parser output without a parser runtime."""

from pathlib import Path
import subprocess
import sys


SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src"

PROBE = r'''
from hashlib import sha256
import json
import sys

sys.path.insert(0, sys.argv[1])
blocked = (
    "company_wiki.automation",
    "company_wiki.document_normalization",
    "company_wiki.parser_adapters",
    "company_wiki.source_catalog",
    "docx",
    "fitz",
    "lxml",
    "onnxruntime",
    "pdfplumber",
    "pptx",
    "pymupdf",
)


def is_blocked(name):
    return any(name == prefix or name.startswith(prefix + ".") for prefix in blocked)


class RefuseParserRuntime:
    def find_spec(self, fullname, path=None, target=None):
        if is_blocked(fullname):
            raise AssertionError("unexpected parser or runtime import: " + fullname)
        return None


isolated = sys.argv[2] == "isolated"
if isolated:
    sys.meta_path.insert(0, RefuseParserRuntime())

from company_wiki.document_model import NarrativeUnit
from company_wiki.document_understanding import understand_units
from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256

heading = "Item 1. Business"
body = "The company opened five overseas stores and plans to expand distribution."
labels = ("Overseas stores", "18")
row_text = " | ".join(labels)
digest = sha256("\n".join((heading, body, row_text)).encode()).hexdigest()
source_id = source_id_for_sha256(digest)


def unit(text, coordinates, kind="pdf_text_block", metadata=None):
    return NarrativeUnit(
        unit_id="urn:company-wiki:narrative-unit:sha256:" + sha256(text.encode()).hexdigest(),
        source_id=source_id,
        parser_name="fixture-parser",
        parser_version="1.0.0",
        coordinates=coordinates,
        raw_text=text,
        unit_kind=kind,
        source_role="company_filing",
        language="en",
        metadata=metadata or {},
    )


cells = []
start = 0
for column, label in enumerate(labels):
    end = start + len(label)
    cells.append({
        "text": label, "table_id": "p1:t0", "row": 1, "column": column, "page": 1,
        "char_start": start, "char_end": end, "char_alignment": "exact",
        "coordinate_frame": "dict",
    })
    start = end + 3

units = (
    unit(heading, EvidenceCoordinates(page_number=1, paragraph_index=0)),
    unit(body, EvidenceCoordinates(page_number=1, paragraph_index=1)),
    unit(row_text, EvidenceCoordinates(page_number=1, table_index=0, row_index=1),
         "pdf_table_row", {"reading_layout": {"upstream_hints": {"cells": cells}}}),
)
output = understand_units(
    units, source_id=source_id, source_sha256=digest, title="2025 Annual Report",
    declared_kind="annual_report", mime_type="application/pdf", metadata={"form_type": "10-K"},
)
assert output["schema_version"] == "du-pipeline/1"
assert output["analysis_status"] == "complete"
assert output["route"]["family"] == "annual"
assert output["plan"]["package_count"] >= 1
observed = {item["unit_id"]: item for item in output["observation"]["units"]}
assert observed[units[1].unit_id]["text"] == body
assert observed[units[1].unit_id]["locator"] == units[1].coordinates.locator()
refs = [measurement["value_ref"] for table in output["table_bindings"]["tables"]
        for measurement in table["measurements"]]
assert any(observed[ref["unit_id"]]["text"][ref["char_start"]:ref["char_end"]] == "18"
           for ref in refs), output["table_bindings"]
if isolated:
    assert not any(is_blocked(name) for name in sys.modules)
canonical = json.dumps(output, sort_keys=True, ensure_ascii=True)
print("DU_RESULT:" + sha256(canonical.encode()).hexdigest())
'''


def _probe(mode: str) -> str:
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", PROBE, str(SOURCE_ROOT), mode],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr
    return next(line for line in completed.stdout.splitlines() if line.startswith("DU_RESULT:"))


def test_understanding_with_fine_table_observations_needs_no_parser_runtime():
    expected = _probe("normal")
    assert _probe("isolated") == expected


def test_existing_observation_imports_forward_to_the_public_owners():
    from company_wiki.document_model import form_fields, table_shapes, text_matching
    from company_wiki.document_model.reading_identity import reading_algorithm_hashes
    from company_wiki.document_normalization import (
        form_fields as previous_fields,
        pdf_table_observations as previous_pdf_tables,
        table_shapes as previous_shapes,
        text_matching as previous_matching,
    )
    from company_wiki.document_normalization.pdf_table_observations import adapter
    from company_wiki.document_normalization.reading_identity import (
        reading_algorithm_hashes as previous_hashes,
    )
    from company_wiki.document_understanding import pdf_table_observations

    shared = (
        (form_fields, previous_fields),
        (table_shapes, previous_shapes),
        (text_matching, previous_matching),
    )
    hashes = reading_algorithm_hashes()
    legacy = previous_hashes(pdf_frontend=False)
    for owner, facade in shared:
        assert facade.__all__ == owner.__all__
        assert all(getattr(facade, name) is getattr(owner, name) for name in owner.__all__)
        assert legacy[facade.__name__] == hashes[owner.__name__]
    active_builder = pdf_table_observations.build_pdf_table_observations
    assert previous_pdf_tables.build_pdf_table_observations is active_builder
    assert adapter.build_pdf_table_observations is active_builder
