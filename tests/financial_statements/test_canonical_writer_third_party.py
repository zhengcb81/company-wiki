"""Neutral RED: canonical writer entry for third-party multi-period datasets."""

from __future__ import annotations

import hashlib
import json

import pytest

from company_wiki.source_catalog.canonical_writer import (
    CanonicalSourceWriter,
    ThirdPartyDatasetOriginal,
)
from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.service import SourceCatalog

from . import fixtures


@pytest.fixture()
def catalog(tmp_path):
    project = tmp_path / "project"
    companies = project / "companies"
    companies.mkdir(parents=True)
    config = CatalogConfig(
        project_root=project,
        catalog_dir=project / ".source_catalog",
        roots=(
            RootSpec(
                "company_raw", companies, "company_raw", priority=10,
                adapter_id="company_raw_v1",
            ),
        ),
    )
    made = SourceCatalog(config)
    made.scan()
    return made


def _original(url: str = "https://quotes.sina.cn/x?paperCode=sh688012&source=lrb&type=0&page=1&num=10"):
    return ThirdPartyDatasetOriginal(
        entity="中微公司",
        market="CN",
        security_id="688012",
        title="Sina lrb sh688012 page 1",
        source_url=url,
        document_kind="financial_statement_dataset",
        publisher="新浪财经",
        provider="sina_finance",
        provider_document_id="sina:sh688012:lrb:type0:page1",
    )


def _stage(writer: CanonicalSourceWriter, payload: bytes, name: str = "page1.json"):
    staged = writer.staging_root / name
    staged.parent.mkdir(parents=True, exist_ok=True)
    staged.write_bytes(payload)
    return staged


class TestThirdPartyDatasetImport:
    def test_import_commits_json_original_with_provider_identity(self, catalog):
        writer = CanonicalSourceWriter(catalog)
        payload = fixtures.fixture_bytes("sh688012-lrb-type0-page1-num10.json.gz")
        staged = _stage(writer, payload)
        result = writer.import_third_party_dataset_staged(
            request_id="req-w19-1",
            original=_original(),
            staged_path=staged,
            content_sha256=hashlib.sha256(payload).hexdigest(),
            byte_size=len(payload),
            mime_type="application/json",
            retrieved_at="2026-10-25T12:00:00Z",
            capture_receipt={"http_status": 200, "url": _original().source_url},
        )
        assert result.status.value == "imported_new"
        destination = result.canonical_path
        assert destination.endswith(".json")
        relative = destination.replace("\\", "/").split("/")
        assert relative[-3] == "raw"
        assert relative[-2] == "financial_statements"
        assert "中微公司" in destination
        provenance = json.loads(
            open(destination + ".source.json", encoding="utf-8").read()
        )
        assert provenance["provider"] == "sina_finance"
        assert provenance["provider"] != "official"
        assert provenance["publisher"] == "新浪财经"
        assert provenance["fiscal_year"] is None  # no fabricated single year
        assert provenance["document_kind"] == "financial_statement_dataset"
        # registered + classified through the sidecar kind map
        row = catalog.store.fetchone(
            "SELECT document_kind, source_type FROM documents WHERE document_id=?",
            (result.source_ref.document_id,),
        )
        assert row is not None
        assert row["document_kind"] == "financial_statement_dataset"

    def test_reimport_same_bytes_deduplicates(self, catalog):
        writer = CanonicalSourceWriter(catalog)
        payload = fixtures.fixture_bytes("sh688012-fzb-type0-page1-num10.json.gz")
        first = writer.import_third_party_dataset_staged(
            request_id="req-1",
            original=_original("https://quotes.sina.cn/x?fzb=1"),
            staged_path=_stage(writer, payload),
            content_sha256=hashlib.sha256(payload).hexdigest(),
            byte_size=len(payload),
            mime_type="application/json",
            retrieved_at="2026-10-25T12:00:00Z",
            capture_receipt={},
        )
        second = writer.import_third_party_dataset_staged(
            request_id="req-2",
            original=_original("https://quotes.sina.cn/x?fzb=1"),
            staged_path=_stage(writer, payload, "page1-again.json"),
            content_sha256=hashlib.sha256(payload).hexdigest(),
            byte_size=len(payload),
            mime_type="application/json",
            retrieved_at="2026-10-25T13:00:00Z",
            capture_receipt={},
        )
        assert second.status.value == "deduplicated_after_download"
        assert second.source_id == first.source_id

    def test_provider_official_is_refused(self, catalog):
        writer = CanonicalSourceWriter(catalog)
        payload = b"{}"
        original = ThirdPartyDatasetOriginal(
            entity="X", market="CN", security_id="1", title="t",
            source_url="https://example.com/a", document_kind="financial_statement_dataset",
            publisher="p", provider="official", provider_document_id="d",
        )
        with pytest.raises(Exception):
            writer.import_third_party_dataset_staged(
                request_id="req-3",
                original=original,
                staged_path=_stage(writer, payload),
                content_sha256=hashlib.sha256(payload).hexdigest(),
                byte_size=len(payload),
                mime_type="application/json",
                retrieved_at="2026-10-25T12:00:00Z",
                capture_receipt={},
            )

    def test_staged_byte_mismatch_refused(self, catalog):
        writer = CanonicalSourceWriter(catalog)
        payload = b'{"a": 1}'
        with pytest.raises(Exception):
            writer.import_third_party_dataset_staged(
                request_id="req-4",
                original=_original(),
                staged_path=_stage(writer, payload),
                content_sha256="b" * 64,
                byte_size=len(payload),
                mime_type="application/json",
                retrieved_at="2026-10-25T12:00:00Z",
                capture_receipt={},
            )
