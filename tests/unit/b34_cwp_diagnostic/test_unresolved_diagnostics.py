"""B34 bounded logical diagnostics; synthetic owner roots only.

Ported from the B34 candidate with one deliberate deviation: the historical
fixed eight-item cap is NOT revived (card R7 constraint).  Deduplication
keeps the list bounded by distinct unresolved sources; trimming the result
to hit a representation quota would be silent evidence loss.
"""
from dataclasses import asdict, replace
import hashlib
import json

import pytest

from company_wiki.source_catalog import local_reconcile as subject
from company_wiki.source_catalog.source_reader import SourceReadError, SourceRef
from unit.test_local_source_boundaries import cn_lake, cn_request, original_with_text, NAME


def ref_for(index=1):
    digest = hashlib.sha256(str(index).encode()).hexdigest()
    return SourceRef("urn:company-wiki:document:sha256:" + digest,
                     "urn:company-wiki:source:sha256:" + digest,
                     digest, index, "application/pdf")


def test_actual_unresolved_local_original_retains_exact_logical_ref(tmp_path, monkeypatch):
    catalog, raw = cn_lake(tmp_path)
    try:
        company = raw / NAME
        company.mkdir()
        original = original_with_text(NAME + "\n\u62db\u80a1\u8bf4\u660e\u4e66\n\u8bc1\u5238\u4ee3\u7801\uff1a600999")
        path = company / "local.pdf"
        path.write_bytes(original.data)
        result = subject.prepare_local_source(catalog, cn_request())
        assert set(result) == {"schema_version", "status", "reason", "source_ref",
                               "blocks_download", "operations", "diagnostics", "download_events"}
        assert result["status"] == "blocked"
        assert result["reason"] == "local_document_kind_unresolved"
        assert result["blocks_download"] is True and result["download_events"] == 0
        assert result["source_ref"] is None
        candidates = [x for x in result["diagnostics"] if x["reason"] == "local_candidate_scope_unresolved"]
        assert len(candidates) == 1, result
        ref = candidates[0]["source_ref"]
        digest = hashlib.sha256(original.data).hexdigest()
        assert ref == asdict(SourceRef("urn:company-wiki:document:sha256:" + digest,
                                      "urn:company-wiki:source:sha256:" + digest,
                                      digest, len(original.data), "application/pdf"))
        assert candidates[0]["failure_reason"] == result["reason"]
        assert str(tmp_path) not in json.dumps(candidates)
        assert path.read_bytes() == original.data
        # The synthetic raw PDF is registered then proved; compare the unchanged
        # owner budget path rather than assume one operation for both phases.
        consumed = result["operations"][-1]["consumed"].copy()
        consumed.pop("elapsed_seconds")
        comparison_root = tmp_path / "comparison"
        comparison_root.mkdir()
        comparison, comparison_raw = cn_lake(comparison_root)
        try:
            comparison_company = comparison_raw / NAME
            comparison_company.mkdir()
            (comparison_company / "local.pdf").write_bytes(original.data)
            monkeypatch.setattr(subject._PreparationProgress, "record_unresolved", lambda *args: None)
            unchanged = subject.prepare_local_source(comparison, cn_request())
            original_consumed = unchanged["operations"][-1]["consumed"].copy()
            original_consumed.pop("elapsed_seconds")
            assert consumed == original_consumed
            assert unchanged["status"] == result["status"]
            assert unchanged["reason"] == result["reason"]
            assert unchanged["blocks_download"] == result["blocks_download"]
            assert not unchanged["diagnostics"]
        finally:
            comparison.close()
    finally:
        catalog.close()


@pytest.mark.parametrize("change", [
    {"schema_version": "1.0"},
    {"document_id": "not-a-document-urn"},
    {"source_id": "not-a-source-urn"},
    {"content_sha256": "z" * 64},
    {"content_sha256": "b" * 64},
    {"byte_size": True},
    {"byte_size": -1},
    {"byte_size": "1"},
    {"mime_type": "application/pdf\nprivate"},
    {"mime_type": "file:private"},
])
def test_malformed_reference_never_reflects_its_values(change):
    progress = subject._PreparationProgress()
    progress.record_unresolved(replace(ref_for(), **change), "local_document_kind_unresolved")
    assert progress.diagnostics == [{"reason": "unresolved_source_reference_invalid",
                                     "failure_reason": "local_document_kind_unresolved"}]


def test_untyped_reference_cannot_reflect_extra_storage_fields():
    progress = subject._PreparationProgress()
    value = {**asdict(ref_for()), "canonical_path": "private-location"}
    progress.record_unresolved(value, "local_document_kind_unresolved")
    assert "source_ref" not in progress.diagnostics[0]
    assert "private-location" not in json.dumps(progress.diagnostics)


def test_diagnostic_is_in_memory_only_and_retains_unknown_bytes_status(monkeypatch):
    def no_io(*args, **kwargs):
        raise AssertionError("diagnostic projection must not perform I/O")
    monkeypatch.setattr(subject.Path, "open", no_io)
    progress = subject._PreparationProgress()
    progress.record_unresolved(ref_for(), "local_document_kind_unresolved")
    assert progress.diagnostics == [{"reason": "local_candidate_scope_unresolved",
                                    "failure_reason": "local_document_kind_unresolved",
                                    "source_ref": asdict(ref_for())}]
    assert not ({"available", "verified", "byte_verified", "title", "location"}
                & set(progress.diagnostics[0]))


def test_diagnostics_deduplicate_without_an_arbitrary_count_cap():
    """Distinct unresolved sources all survive; duplicates collapse (no R7 cap)."""
    prior = {"reason": "trusted_scope_not_relevant", "document_id": "previous-document"}
    progress = subject._PreparationProgress(diagnostics=[prior])
    for index in range(1, 31):
        progress.record_unresolved(ref_for(index), "local_document_kind_unresolved")
    progress.record_unresolved(ref_for(), "local_document_kind_unresolved")
    assert len(progress.diagnostics) == 31
    assert progress.diagnostics[0] == prior
    assert [x["source_ref"] for x in progress.diagnostics[1:]] == [
        asdict(ref_for(index)) for index in range(1, 31)
    ]


def test_exception_details_and_bad_reason_are_not_exposed():
    progress = subject._PreparationProgress()
    progress.record_unresolved(ref_for(), "private-location/with separators")
    assert progress.diagnostics[0]["failure_reason"] == "local_fact_validation_failed"
    assert "private-location" not in json.dumps(progress.diagnostics)


@pytest.mark.parametrize("reason", ["budget_exceeded", "cancelled", "local_prepare_deadline"])
def test_original_budget_or_cancel_refusal_precedes_diagnostic(tmp_path, monkeypatch, reason):
    catalog, raw = cn_lake(tmp_path)
    try:
        company = raw / NAME
        company.mkdir()
        original = original_with_text(NAME + "\n\u62db\u80a1\u8bf4\u660e\u4e66\n\u8bc1\u5238\u4ee3\u7801\uff1a600999")
        (company / "local.pdf").write_bytes(original.data)
        def stop(*args, **kwargs):
            raise SourceReadError("unavailable", reason, "private diagnostic detail")
        monkeypatch.setattr(subject, "restore_document_facts", stop)
        result = subject.prepare_local_source(catalog, cn_request())
        assert result["reason"] == reason and result["blocks_download"] is True
        assert not result["diagnostics"]
        assert "private diagnostic detail" not in json.dumps(result)
    finally:
        catalog.close()
