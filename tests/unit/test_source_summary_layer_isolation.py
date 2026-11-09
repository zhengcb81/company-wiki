"""Source summary values and assessment consume selected material in isolation."""

from pathlib import Path
import subprocess
import sys


SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src"

PROBE = r'''
from hashlib import sha256
import sys

sys.path.insert(0, sys.argv[1])
blocked = (
    "company_wiki.automation",
    "company_wiki.document_normalization",
    "company_wiki.parser_adapters",
    "company_wiki.source_catalog.acquisition",
    "company_wiki.source_catalog.acquisition_service",
    "company_wiki.source_catalog.canonical_writer",
    "company_wiki.source_catalog.narrative_artifact_store",
    "company_wiki.source_catalog.narrative_evidence",
    "company_wiki.source_catalog.security_identity",
    "company_wiki.source_catalog.service",
    "company_wiki.source_catalog.source_reader",
    "lxml",
    "pymupdf",
    "sqlite3",
    "urllib.request",
)


def is_blocked(name):
    return any(name == prefix or name.startswith(prefix + ".") for prefix in blocked)


class RefuseRuntime:
    def find_spec(self, fullname, path=None, target=None):
        if is_blocked(fullname):
            raise AssertionError("unrelated source runtime: " + fullname)
        return None


sys.meta_path.insert(0, RefuseRuntime())

from company_wiki import source_catalog
from company_wiki.source_catalog import SourceRef as LegacySourceRef
from company_wiki.source_catalog.narrative_claims import validate_summary_claim
from company_wiki.source_catalog.narrative_contracts import (
    NarrativeBundle,
    summary_claim_from_dict,
    summary_claim_to_dict,
)
from company_wiki.source_catalog.narrative_summary_assessment import (
    ASSESSMENT_VERSION,
    QUALIFIED_ASSESSMENT_VERSION,
    assess_summary_material,
    validate_assessment_material,
)
from company_wiki.source_catalog.narrative_summary_material import compile_scoped_material_view
from company_wiki.source_contract import (
    EvidenceCoordinates,
    EvidenceSpan,
    ParseStatus,
    SourceRef,
    source_id_for_sha256,
)

assert "SourceCatalog" in source_catalog.__all__
assert set(source_catalog.__all__) <= set(dir(source_catalog))
assert LegacySourceRef is SourceRef
assert NarrativeBundle.__module__ == "company_wiki.source_catalog.narrative_contracts"
text = "The company opened five overseas stores and signed several new distributors this quarter."
digest = sha256(text.encode()).hexdigest()
span = EvidenceSpan.create(
    source_id=source_id_for_sha256(digest),
    coordinates=EvidenceCoordinates(paragraph_index=0),
    raw_text=text,
    structured_value={"topics": ["core_business"], "source_role": "company_filing",
                      "unit_kind": "pdf_text_block", "selection_reasons": ["specific_operating_fact"]},
    parser_name="fixture-parser", parser_version="1.0.0", parse_status=ParseStatus.PARSED,
    quality_flags=(),
)
claim = {"claim_id": "claim-1", "text": text, "evidence_ids": [span.span_id],
         "claim_type": "company_statement", "modality": "actual", "needs_review": False}
parsed = summary_claim_from_dict(claim)
assert summary_claim_to_dict(parsed) == claim
validate_summary_claim(parsed, {span.span_id: span}, "draft")
view = compile_scoped_material_view([span], None, max_claims=20)
keys = [task.key for task in view.model_tasks]
assert keys == ["t1"]
for version in (ASSESSMENT_VERSION, QUALIFIED_ASSESSMENT_VERSION):
    report = assess_summary_material(
        [span], None, [claim], requested_task_keys=keys, plan_max_claims=20, assessor_version=version,
    )
    assert report["requested_emission_complete"] is True
    assert report["emitted_task_keys"] == keys
    assert report == validate_assessment_material(
        report, [span], None, [claim], plan_max_claims=20, assessor_version=version,
    )
assert not any(is_blocked(name) for name in sys.modules)
'''


def test_summary_wire_and_assessment_need_only_selected_source_material():
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", PROBE, str(SOURCE_ROOT)],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr


def test_legacy_catalog_and_claim_imports_preserve_owner_objects():
    from company_wiki import source_catalog
    from company_wiki.source_catalog import narrative_claims, narrative_evidence
    from company_wiki.source_catalog.service import SourceCatalog

    assert source_catalog.SourceCatalog is SourceCatalog
    assert source_catalog.narrative_evidence is narrative_evidence
    for name in narrative_claims.__all__:
        if name != "summary_claims_sha256":
            assert getattr(narrative_evidence, name) is getattr(narrative_claims, name)
