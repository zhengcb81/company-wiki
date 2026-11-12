"""Real isolated owner transactions for exact metadata-only recovery."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json

import pymupdf
import pytest

from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
from company_wiki.source_catalog.assertion_service import get_verified_assertion
from company_wiki.source_catalog.cn_primary_issuer import read_cn_primary_issuer
from company_wiki.source_catalog.local_inventory import observe_document
from company_wiki.source_catalog.public_legacy_source_link import legacy_source_key
from company_wiki.source_catalog.public_legacy_source_recovery import (
    REQUEST_SCHEMA,
    recover_legacy_source,
)
from company_wiki.source_catalog.security_identity import (
    CNINFO_STOCK_URL,
    SecurityMasterStore,
    SecurityRecord,
)
from company_wiki.source_catalog.source_reader import (
    SourceReadError,
    SourceRef,
    SourceVersionReader,
)
from company_wiki.source_catalog.store import retire_document

NAME = "受控半导体设备（上海）股份有限公司"
USCC = "913101157626272806"
REASON = "legacy sidecar lacks source_url; batch governance Phase 15.6 (F13)"


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def build(tmp_path, *, retirement_reason=REASON, body_extra=""):
    root = tmp_path / "originals"
    root.mkdir()
    registration = (
        NAME
        + "(以下简称本公司)的前身为"
        + NAME.removesuffix("股份有限公司")
        + "有限公司"
        "(以下简称原公司)由ControlledInc.Asia(以下简称受控亚洲)于2004年5月31日在中华人民共和国上海市成立。"
        "根据原公司全体股东于2018年12月20日签署的《"
        + NAME
        + "创立大会暨2018年第一次临时股东大会决议》，本公司整体改制变更为股份有限公司。"
        "于2018年12月21日取得新营业执照，统一社会信用代码为" + USCC + body_extra
    )
    pages = [
        "公司基本情况公司的中文名称"
        + NAME
        + "公司的中文简称受控公司公司的外文名称Controlled",
        "公司股票简况股票代码变更前股票简称A股上海证券交易所科创板受控公司688012不适用",
        registration,
    ]
    document = pymupdf.open()
    for text in pages:
        page = document.new_page()
        page.insert_textbox(
            (30, 20, 570, 65),
            NAME + " 2024年半年度报告",
            fontsize=9,
            fontname="china-s",
        )
        page.insert_textbox((30, 90, 570, 780), text, fontsize=11, fontname="china-s")
    data = document.tobytes()
    document.close()
    original = root / "controlled.pdf"
    original.write_bytes(data)
    (root / "unrelated.txt").write_text(
        "Unrelated original remains exact", encoding="utf-8"
    )
    sidecar = {
        "schema_version": "1.0",
        "canonical_entity_id": "company-name:受控公司",
        "display_name": "受控公司",
        "market": "CN",
        "security_id": "688012",
        "document_kind": "semi_annual_report",
        "filing_date": "2024-08-01",
        "fiscal_year": 2024,
        "period_end": "2024-06-30",
        "language": "zh",
        "provider": "controlled",
        "provider_document_id": "controlled-h124",
    }
    (root / "controlled.pdf.source.json").write_text(
        json.dumps(sidecar, ensure_ascii=False), encoding="utf-8"
    )
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / "catalog",
            roots=(RootSpec("originals", root, "directory", reusable_for_filing=True),),
            reusable_root_kinds=("directory",),
        )
    )
    catalog.scan()
    sha = hashlib.sha256(data).hexdigest()
    ref = SourceRef(
        document_id="urn:company-wiki:document:sha256:" + sha,
        source_id="urn:company-wiki:source:sha256:" + sha,
        content_sha256=sha,
        byte_size=len(data),
        mime_type="application/pdf",
        schema_version="2.0",
    )
    record = SecurityRecord(
        canonical_name="受控公司",
        market="CN",
        exchange="SSE",
        ticker="688012",
        security_id="688012",
        aliases=(),
        active=True,
        source_name="cninfo",
        source_url=CNINFO_STOCK_URL,
        source_record_id="controlled-official-record",
        identifiers={"org_id": "controlled"},
    )
    SecurityMasterStore(catalog.config.catalog_dir / "security_master").write_market(
        "CN", [record], retrieved_at="2026-01-01T00:00:00Z", sources=(CNINFO_STOCK_URL,)
    )
    retire_document(
        catalog.store,
        document_id=ref.document_id,
        reason=retirement_reason,
        created_by="phase-15.6-governance",
    )
    observation = observe_document(catalog, ref.document_id)
    request = {
        "schema_version": REQUEST_SCHEMA,
        "legacy_source_id": legacy_source_key(str(original.resolve())),
        "expected_source_sha256": sha,
        "expected_retirement_observation_sha256": digest(observation),
        "expected_retirement_audit_ids": [
            item["audit_id"] for item in observation["retire_audit"]
        ],
        "source_request": {
            "entity": "受控公司",
            "document_kind": "semi_annual_report",
            "as_of_date": "2026-11-01",
            "market": "CN",
            "security_id": "688012",
            "fiscal_year": 2024,
            "fiscal_period": "H1",
            "mode": "exact",
            "allow_download": False,
        },
    }
    return catalog, original, ref, request


def business_snapshot(catalog):
    return {
        table: [
            dict(row)
            for row in catalog.reader.fetchall(
                "SELECT * FROM " + table + " ORDER BY rowid"
            )
        ]
        for table in (
            "documents",
            "locations",
            "sources",
            "source_metadata_assertions",
            "document_retire_audit",
            "document_restore_audit",
        )
    }


def test_preview_is_zero_business_writes_then_exact_atomic_apply(tmp_path):
    catalog, original, ref, request = build(tmp_path)
    before = business_snapshot(catalog)
    original_bytes = original.read_bytes()
    preview = recover_legacy_source(catalog, request, operation="preview")
    assert preview["status"] == "ready_to_restore", preview
    assert preview["assertion_id"] is None and preview["restore_audit_id"] is None
    assert (
        preview["native_original_issuer_proof"]["state"]
        == "original_verified_pending_source_facts"
    )
    assert business_snapshot(catalog) == before
    result = recover_legacy_source(catalog, request, operation="apply")
    assert result["status"] == "restored" and result["restore_audit_id"]
    assert result["source_ref"] == asdict(ref)
    assert original.read_bytes() == original_bytes
    after = business_snapshot(catalog)
    assert [
        row for row in after["documents"] if row["document_id"] != ref.document_id
    ] == [row for row in before["documents"] if row["document_id"] != ref.document_id]
    assert after["sources"] == before["sources"]
    assert after["document_retire_audit"] == before["document_retire_audit"]
    assert (
        len(after["source_metadata_assertions"])
        == len(before["source_metadata_assertions"]) + 1
    )
    assert (
        len(after["document_restore_audit"])
        == len(before["document_restore_audit"]) + 1
    )
    assert (
        get_verified_assertion(
            catalog.reader, ref.source_id, ref.content_sha256, reader="steady"
        )["assertion_id"]
        == result["assertion_id"]
    )
    assert (
        SourceVersionReader(catalog).verify_version(ref).content_sha256
        == ref.content_sha256
    )
    assert read_cn_primary_issuer(catalog, ref)["key"] == {
        "namespace": "cn.uscc",
        "value": USCC,
    }
    catalog.close()


@pytest.mark.parametrize(
    "field,value",
    [
        ("expected_source_sha256", "0" * 64),
        ("expected_retirement_observation_sha256", "0" * 64),
        ("expected_retirement_audit_ids", ["retire-" + "0" * 32]),
        ("legacy_source_id", "src_" + "0" * 16),
    ],
)
def test_exact_pins_refuse_without_mutation(tmp_path, field, value):
    catalog, original, ref, request = build(tmp_path)
    before = business_snapshot(catalog)
    request[field] = value
    with pytest.raises(SourceReadError):
        recover_legacy_source(catalog, request, operation="apply")
    assert business_snapshot(catalog) == before
    catalog.close()


def test_wrong_native_period_cannot_write_other_period(tmp_path):
    catalog, original, ref, request = build(tmp_path)
    before = business_snapshot(catalog)
    request["source_request"]["fiscal_year"] = 2023
    with pytest.raises(SourceReadError, match="native_scope_conflict"):
        recover_legacy_source(catalog, request, operation="apply")
    assert business_snapshot(catalog) == before
    catalog.close()


def test_nonmetadata_retirement_stale_and_changed_bytes_refuse(tmp_path):
    catalog, original, ref, request = build(
        tmp_path, retirement_reason="source revoked for incorrect issuer"
    )
    before = business_snapshot(catalog)
    with pytest.raises(SourceReadError, match="retirement_not_metadata_only"):
        recover_legacy_source(catalog, request, operation="apply")
    assert business_snapshot(catalog) == before
    catalog.close()


def test_source_changed_after_preview_refuses_and_keeps_retired(tmp_path):
    catalog, original, ref, request = build(tmp_path)
    recover_legacy_source(catalog, request, operation="preview")
    before = business_snapshot(catalog)
    original.write_bytes(original.read_bytes() + b"changed")
    with pytest.raises(SourceReadError):
        recover_legacy_source(catalog, request, operation="apply")
    assert business_snapshot(catalog) == before
    catalog.close()
