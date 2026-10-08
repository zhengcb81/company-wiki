"""Stage RF regression tests, preserving existing fixture helpers."""
from pathlib import Path
import os

root = Path(os.environ['USERPROFILE']) / 'Projects/revenue-forecast'
stage = Path(__file__).parent / 'rf_fix_stage'
stage.mkdir(exist_ok=True)
additions = {}
additions['test_filing_fetch_client.py'] = '''

def test_schema2_source_candidate_is_unwrapped(tmp_path, monkeypatch):
    import filing_fetch_client as client
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/fetch_filing.py").write_text("", encoding="utf-8")
    filing = {"status": "source_candidate", "source_ref": {"schema_version": "2.0"},
              "document_kind": "annual_report", "fiscal_year": 2025, "fiscal_period": "FY",
              "resolution_outcome": "reused_existing", "download_events": 0,
              "byte_verification": "pending_verified_open"}
    payload = {"schema_version": "2.0", "status": "source_candidate", "filing": filing,
               "transcript": {"status": "not_requested"}, "calls": 2, "downloads": 0}
    monkeypatch.setattr(client.subprocess, "run", lambda *a, **kw:
                        subprocess.CompletedProcess([], 0, json.dumps(payload), ""))
    assert client.resolve_filing({"schema_version": "2.0"}, filing_fetch_root=tmp_path) == filing


def test_schema2_gap_keeps_provider_reason(tmp_path, monkeypatch):
    import filing_fetch_client as client
    import pytest
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/fetch_filing.py").write_text("", encoding="utf-8")
    payload = {"schema_version": "2.0", "status": "gap",
               "filing": {"status": "gap", "reason": "provider_unavailable"}}
    monkeypatch.setattr(client.subprocess, "run", lambda *a, **kw:
                        subprocess.CompletedProcess([], 0, json.dumps(payload), ""))
    with pytest.raises(client._ClientError, match="provider_unavailable"):
        client.resolve_filing({"schema_version": "2.0"}, filing_fetch_root=tmp_path)
'''
additions['test_company_wiki_source_v2.py'] = '''

def test_unknown_retrieval_preserved_and_actual_read_captured():
    ref, receipt, manifest = _inputs()
    manifest["retrieved_at"] = None
    result = _build(ref, receipt, manifest)
    assert result["company_wiki_trace"]["source_manifest"]["retrieved_at"] is None
    assert result["capture"]["captured_date"] == receipt["read_at"][:10]
    assert result["accessed_date"] == receipt["read_at"][:10]
    validate_sources({"sources": [result]}, date.fromisoformat("2026-09-27"), require_capture=True)


def test_minimal_schema2_candidate_uses_verified_manifest():
    ref, receipt, manifest = _inputs()
    minimal = {"status": "source_candidate", "source_ref": ref,
               "byte_verification": "pending_verified_open", "document_kind": "annual_report",
               "fiscal_year": 2025, "fiscal_period": None,
               "resolution_outcome": "reused_existing", "download_events": 0}
    record = _build(ref, receipt, manifest, candidate=minimal)
    assert record["published_date"] == manifest["published_date"]
    assert record["title"] == manifest["title"]
    minimal["fiscal_year"] = 2024
    with pytest.raises(CompanyWikiSourceError, match="fiscal_year"):
        _build(ref, receipt, manifest, candidate=minimal)
'''
additions['test_company_wiki_source_reader_v2.py'] = '''

def test_null_original_retrieval_is_preserved(monkeypatch, tmp_path):
    receipt = _receipt()
    receipt["manifest"]["retrieved_at"] = None
    monkeypatch.setattr("subprocess.run", lambda command, **kw:
                        subprocess.CompletedProcess(command, 0, BODY,
                            (json.dumps(receipt) + "\\n").encode()))
    body, read_receipt, manifest = _open(tmp_path)
    assert body == BODY
    assert manifest["retrieved_at"] is None
    assert read_receipt["read_at"] == receipt["read_at"]
'''
additions['test_source_preparation.py'] = '''

def test_annual_optional_period_defaults_to_canonical_fy():
    import source_preparation as prep
    import pytest
    request = {"document_kind": "annual_report", "fiscal_year": 2025}
    handle = {"source_ref": {}, "document_kind": "annual_report",
              "fiscal_year": 2025, "fiscal_period": "FY"}
    assert prep._validate_v2_candidate(request, handle) == 2025
    request["fiscal_period"] = "H1"
    with pytest.raises(RuntimeError, match="fiscal_period"):
        prep._validate_v2_candidate(request, handle)
'''
for name, extra in additions.items():
    original = root / 'tests' / name
    (stage / name).write_text(original.read_text(encoding='utf-8') + extra, encoding='utf-8')
print(stage)
