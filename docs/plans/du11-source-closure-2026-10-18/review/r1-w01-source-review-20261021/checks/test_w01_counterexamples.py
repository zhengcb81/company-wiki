"""Independent W01 counterexamples; no original downloads or product writes."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
from types import SimpleNamespace

import pymupdf as fitz
import pytest

from company_wiki.source_catalog.local_inventory import LocalPrepareLimits, LocalReadBudget
from company_wiki.source_catalog.local_reconcile import _cn_cover_scope
from company_wiki.source_catalog.qualification import latest_source_index, qualify_source
from company_wiki.source_catalog.source_availability import _open_evidence, verified_open_observation
from company_wiki.source_catalog.source_reader import SourceRef, SourceReadError

NAME = "\u548c\u5149\u79d1\u6280"
TITLE = "2026\u5e74\u534a\u5e74\u5ea6\u62a5\u544a"


def original_with_text(text):
    with fitz.open() as pdf:
        page = pdf.new_page()
        page.insert_text((40, 50), text, fontname="china-s", fontsize=11)
        data = pdf.tobytes()
    ref = SourceRef("independent-doc", "independent-source", hashlib.sha256(data).hexdigest(), len(data), "application/pdf")
    return SimpleNamespace(data=data, ref=ref)


def identity():
    return SimpleNamespace(canonical_name=NAME, market="CN", security_id="600999")


def test_real_periodic_cover_control_has_expected_scope():
    original = original_with_text(NAME + "\n" + TITLE + "\n\u8bc1\u5238\u4ee3\u7801\uff1a600999")
    facts, evidence = _cn_cover_scope(original, identity(), LocalReadBudget(LocalPrepareLimits()))
    assert facts["document_kind"] == "semi_annual_report"
    assert facts["fiscal_year"] == 2026 and facts["fiscal_period"] == "H1"
    assert evidence["entity"]["content_sha256"] == original.ref.content_sha256


def test_ir_mention_of_periodic_report_is_not_the_periodic_original():
    original = original_with_text(NAME + "\n\u6295\u8d44\u8005\u5173\u7cfb\u6d3b\u52a8\u8bb0\u5f55\u8868\n\u95ee\uff1a" + TITLE + "\u4e2d\u5df2\u62ab\u9732\u7684\u6536\u5165\u600e\u6837\uff1f")
    with pytest.raises(SourceReadError):
        _cn_cover_scope(original, identity(), LocalReadBudget(LocalPrepareLimits()))


def test_cover_explicit_security_code_conflict_cannot_be_ignored_by_name_hit():
    original = original_with_text(NAME + "\n" + TITLE + "\n\u8bc1\u5238\u4ee3\u7801\uff1a600123")
    with pytest.raises(SourceReadError):
        _cn_cover_scope(original, identity(), LocalReadBudget(LocalPrepareLimits()))


def test_same_verified_period_and_publication_day_different_versions_are_ambiguous():
    versions = [{"fiscal_year": 2026, "fiscal_period": "H1", "scope_verified": True,
                 "published_date": "2026-08-01", "provider_document_id": "a", "source_id": "different-bytes-a"},
                {"fiscal_year": 2026, "fiscal_period": "H1", "scope_verified": True,
                 "published_date": "2026-08-01", "provider_document_id": "b", "source_id": "different-bytes-b"}]
    assert latest_source_index(versions) is None


def test_mixed_verified_and_unproved_period_does_not_revert_to_legacy_publication_sort():
    versions = [{"fiscal_year": 2026, "fiscal_period": "H1", "scope_verified": True,
                 "published_date": "2026-08-01", "source_id": "proved"},
                {"scope_verified": False, "published_date": "2026-10-01", "source_id": "unproved"}]
    assert latest_source_index(versions) is None


def test_current_open_byte_binding_clock_and_unknown_publication_controls():
    original = original_with_text(NAME + "\n" + TITLE)
    observation = verified_open_observation(original)
    proof = _open_evidence(observation, original.ref)
    today = datetime.now(timezone.utc).date()
    assert proof["available_by"] == today.isoformat()
    assert proof["basis"] == "current_verified_open"
    qualified = qualify_source(None, as_of_date=today.isoformat(), local_bytes_status="verified",
                               source_sha256=original.ref.content_sha256, availability_evidence=proof)
    assert qualified.publication_status == "unknown" and qualified.historical_reuse_eligible
    assert not qualify_source(None, as_of_date=(today-timedelta(days=1)).isoformat(), local_bytes_status="verified",
                              source_sha256=original.ref.content_sha256, availability_evidence=proof).historical_reuse_eligible
    assert not qualify_source((today+timedelta(days=1)).isoformat(), as_of_date=today.isoformat(), local_bytes_status="verified",
                              source_sha256=original.ref.content_sha256, availability_evidence=proof).historical_reuse_eligible
    assert _open_evidence(observation, replace(original.ref, byte_size=original.ref.byte_size+1)) is None
    assert _open_evidence(observation, replace(original.ref, mime_type="text/plain")) is None
    assert _open_evidence(observation, replace(original.ref, content_sha256="a"*64)) is None
    assert _open_evidence({**observation, "verified_at": (datetime.now(timezone.utc)+timedelta(days=1)).isoformat()}, original.ref) is None
    assert _open_evidence({**observation, "verified_at": "2026-10-21T00:00:00"}, original.ref) is None



def cn_lake(tmp_path):
    from company_wiki.source_catalog.models import CatalogConfig, RootSpec
    from company_wiki.source_catalog.service import SourceCatalog
    from company_wiki.source_catalog.security_identity import SecurityMasterStore, SecurityRecord
    raw = tmp_path / "raw"
    raw.mkdir()
    catalog = SourceCatalog(CatalogConfig(project_root=tmp_path, catalog_dir=tmp_path / "cat",
        roots=(RootSpec("raw", raw, "company_raw"),)))
    SecurityMasterStore(catalog.config.catalog_dir / "security_master").write_market("CN", (
        SecurityRecord(NAME, "CN", "SSE", "600999", "600999", (), True, "official",
            "https://example.org/securities", "600999", {}),),
        retrieved_at="2026-10-21T00:00:00Z", sources=("official",))
    return catalog, raw


def cn_request():
    from company_wiki.source_catalog.resolver import SourceRequest
    return SourceRequest(entity=NAME, market="CN", security_id="600999", document_kind="semi_annual_report",
        fiscal_year=2026, fiscal_period="H1", as_of_date=datetime.now(timezone.utc).date().isoformat())


def test_real_writer_must_not_relabel_ir_reference_as_registered_h1(tmp_path):
    from company_wiki.source_catalog.local_reconcile import prepare_local_source
    catalog, raw = cn_lake(tmp_path)
    try:
        original = original_with_text(NAME + "\n\u6295\u8d44\u8005\u5173\u7cfb\u6d3b\u52a8\u8bb0\u5f55\u8868\n\u95ee\uff1a" + TITLE + "\u4e2d\u5df2\u62ab\u9732\u7684\u6536\u5165\u600e\u6837\uff1f")
        company = raw / NAME
        company.mkdir()
        path = company / "activity.pdf"
        path.write_bytes(original.data)
        before = path.read_bytes()
        result = prepare_local_source(catalog, cn_request())
        assert result["status"] != "ready", result
        assert path.read_bytes() == before
        rows = catalog.reader.fetchall("SELECT document_kind FROM documents")
        assert not any(row["document_kind"] == "semi_annual_report" for row in rows)
        # A genuinely proved IR can be NOT_RELEVANT. An unresolved generic
        # original cannot silently authorize H1 collection as an empty lake.
        if not result["blocks_download"]:
            assert rows and all(row["document_kind"] == "investor_relations" for row in rows)
            assert catalog.reader.fetchone("SELECT COUNT(*) FROM source_metadata_assertions WHERE evidence_basis='source-facts'")[0] > 0
    finally:
        catalog.close()


def test_cn_raw_cover_repairs_wrong_registered_labels_instead_of_declaring_absence(tmp_path, monkeypatch):
    import json
    from company_wiki.source_catalog.local_reconcile import prepare_local_source
    from company_wiki.source_catalog.source_reader import SourceVersionReader
    catalog, raw = cn_lake(tmp_path)
    try:
        original = original_with_text(NAME + "\n" + TITLE + "\n\u8bc1\u5238\u4ee3\u7801\uff1a600999")
        company = raw / NAME
        company.mkdir()
        path = company / "current.pdf"
        path.write_bytes(original.data)
        path.with_name(path.name + ".source.json").write_text(json.dumps({
            "entity": NAME, "market": "HK", "security_id": "OTHER", "document_kind": "semi_annual_report",
            "fiscal_year": 2026, "fiscal_period": "H1", "provider": "legacy", "published_date": None,
            "content_sha256": original.ref.content_sha256}), encoding="utf-8")
        catalog.scan()
        result = prepare_local_source(catalog, cn_request())
        assert result["status"] == "ready", result
        ref = SourceRef(**result["source_ref"])
        observed = SourceVersionReader(catalog).describe_version(ref)
        assert observed["market"] == "CN" and observed["security_id"] == "600999"
        assert ref.content_sha256 == original.ref.content_sha256 and path.read_bytes() == original.data
        assert result["download_events"] == 0
    finally:
        catalog.close()



def test_unknown_generic_registered_original_is_not_proof_of_absent_h1(tmp_path):
    from company_wiki.source_catalog.local_reconcile import prepare_local_source
    catalog, raw = cn_lake(tmp_path)
    try:
        original = original_with_text(NAME + "\nOperating update with unresolved document category")
        company = raw / NAME
        company.mkdir()
        path = company / "unlabeled.pdf"
        path.write_bytes(original.data)
        for _retry in range(3):
            result = prepare_local_source(catalog, cn_request())
            assert result["status"] != "ready", result
            assert result["blocks_download"] is True, result
            assert result["download_events"] == 0
            assert path.read_bytes() == original.data
            assert catalog.reader.fetchone("SELECT COUNT(*) FROM documents")[0] == 1
    finally:
        catalog.close()
