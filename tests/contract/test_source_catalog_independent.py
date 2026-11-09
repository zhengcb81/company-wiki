"""Catalog contracts and operations run with the job runtime unavailable."""

from pathlib import Path
import subprocess
import sys


SOURCE = Path(__file__).resolve().parents[2] / "src"
NO_AUTOMATION = r"""
import importlib.abc
import sys

sys.path.insert(0, sys.argv[1])

class RefuseAutomation(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "company_wiki.automation" or fullname.startswith("company_wiki.automation."):
            raise AssertionError("catalog imported job runtime: " + fullname)
        return None

sys.meta_path.insert(0, RefuseAutomation())
"""


def run_catalog_in_isolation(code: str, *args: str) -> None:
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", NO_AUTOMATION + code, str(SOURCE), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=45, check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_source_decision_identity_is_available_without_automation():
    run_catalog_in_isolation("""
from company_wiki.source_catalog.narrative_decision_inventory import decision_versions

versions = decision_versions(mime_type="text/plain")
assert len(versions["source_usability"].split("+")[-1]) == 64
""")


def test_catalog_selects_original_transcript_without_automation():
    run_catalog_in_isolation("""
from hashlib import sha256
from company_wiki.source_catalog.narrative_contracts import SourceMetadataValue, SourceRefValue
from company_wiki.source_catalog.narrative_selection import RawNarrativeSelector, verify_selected_material
from company_wiki.source_contract import source_id_for_sha256

original = (b"Full Conference Call Transcript\\n"
            b"CEO: We launched a new product and expanded overseas capacity.\\n"
            b"Questions & Answers\\nAnalyst: Is commercial launch on schedule?\\n")
digest = sha256(original).hexdigest()
ref = SourceRefValue("2.0", "doc", source_id_for_sha256(digest), digest, len(original), "text/plain")
metadata = SourceMetadataValue("transcript", "Company results", "investor_call_transcript", "en")
work = RawNarrativeSelector().select(original, source_ref=ref, source_metadata=metadata, checkpoint=lambda: None)
assert any("expanded overseas capacity" in span.raw_text for span in work.package.evidence_spans)
verify_selected_material(work.parsed, work.package, mime_type=ref.mime_type)
""")


def test_catalog_reads_visible_narrative_quality_without_automation(tmp_path):
    from support.narrative_transport_fixture import published_fixture

    with published_fixture(tmp_path, kind="txt") as fixture:
        database = fixture.catalog.config.database_path
        before = database.read_bytes()
        run_catalog_in_isolation("""
from contextlib import closing
from pathlib import Path
from company_wiki.source_catalog import SourceCatalog, load_catalog_config
from company_wiki.source_catalog.extraction_quality import ExtractionQualityService
from company_wiki.source_catalog.narrative_bundle_reader import NarrativeBundleReader
from company_wiki.source_catalog.narrative_material_replay import replay_narrative_evidence

report = ExtractionQualityService(Path(sys.argv[2])).assess(document_id=sys.argv[3])
assert report.extraction_basis == "selected_narrative"
assert report.span_count > 0
with closing(SourceCatalog(load_catalog_config(Path(sys.argv[4])))) as catalog:
    with closing(catalog.open_narrative_artifact_reader()) as artifacts:
        visible = NarrativeBundleReader(artifacts).read(document_id=sys.argv[3], source_id=sys.argv[6],
                                                        source_sha256=sys.argv[7])
        assert replay_narrative_evidence(Path(sys.argv[5]).read_bytes(), visible.bundle) == report.span_count
""", str(database), fixture.source_ref.document_id, str(fixture.config_path),
                                 str(fixture.raw_path), fixture.source_ref.source_id, fixture.source_ref.content_sha256)
        assert database.read_bytes() == before
