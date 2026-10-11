"""Real full TXT and owned source-parser/projection/replay, with zero model calls."""
from contextlib import contextmanager
from functools import partial
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import fitz
import pytest

from company_wiki.automation.narrative_contracts import NarrativeSelectResult
from company_wiki.automation.narrative_official_json import open_verified_projection, select_verified_projection
from company_wiki.automation.narrative_replay import replay_verified_projection
from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.narrative_evidence import (
    parse_pdf, parse_transcript_text, select_narrative_evidence,
    verify_pdf_evidence_spans, verify_transcript_evidence_spans,
)
from company_wiki.source_catalog.official_json_import import import_official_json_source
from company_wiki.source_catalog.official_json_projection import build_projection_from_refs, persist_projection
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader
from company_wiki.source_contract import source_id_for_sha256

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "narrative_real_transcript" / "MSFT_Q4_2026_earnings_call.txt"
FIXTURE_SHA = "4ac3b4f0fa1be928b56b4ef9775cac694a1712d46785bb1fa28d2a6a68d7852a"


def test_full_msft_true_business_anchors_qualifiers_roles_and_replay():
    raw = FIXTURE.read_bytes()
    parsed = parse_transcript_text(raw.decode(), source_id=source_id_for_sha256(FIXTURE_SHA),
        source_sha256=FIXTURE_SHA, language="en", parser_version="0.3.1")
    legacy = select_narrative_evidence(parsed, title=FIXTURE.name, selector_version="0.6.0")
    new = select_narrative_evidence(parsed, title=FIXTURE.name, selector_version="0.7.0")
    anchors = ["what we launched with Perception", "50% less cost", "90% of the tasks",
        "if a given model goes away", "still continue your cyber operations",
        "my math has changed", "price performance on silicon", "token usage",
        "mix of the portfolio"]
    business = [span for span in new.evidence_spans
        if span.structured_value["source_role"] == "management"]
    for anchor in anchors:
        assert any(anchor in (span.raw_text or "") for span in business), anchor
    assert not any("90% of the tasks" in (span.raw_text or "") for span in legacy.evidence_spans)
    assert len(new.evidence_spans) <= new.selection_limit == 96
    verified, failed = verify_transcript_evidence_spans(raw.decode(),
        source_id=source_id_for_sha256(FIXTURE_SHA), source_sha256=FIXTURE_SHA,
        evidence_spans=new.evidence_spans, language="en")
    assert failed == () and len(verified) == len(new.evidence_spans)
    groups = new.summary_input()["evidence"]
    for group in groups:
        if group.get("context_group_id"):
            assert group["context_member_count"] <= 8
            assert len(group["raw_text"]) <= 1200
            assert group["source_role"] == "management"
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == FIXTURE_SHA
    assert parsed.units and len(parsed.units) == 489


@contextmanager
def owned_state(tmp_path):
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with TemporaryDirectory(prefix="w03-business-", dir=tmp_path) as directory:
        root = Path(directory)
        (root / "companies").mkdir()
        catalog = SourceCatalog(CatalogConfig(project_root=root, catalog_dir=root / "catalog",
            roots=(RootSpec("company_raw", root / "companies", "company_raw"),)))
        try:
            yield root, catalog
        finally:
            catalog.close()
    assert {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before
    assert not any(p.name.startswith("w03-business-") for p in tmp_path.iterdir())


# Controlled miniature PDF business snippets based on frozen excerpts; the
# genuine original page and byte replay is recorded in the owned evidence node.
ANNUAL = [
    "中微公司钨系列薄膜沉积产品：CVD（化学气相沉积）钨设备，HAR（高深宽比）钨设备和ALD（原子层沉积）钨设备，可覆盖存储器件所有钨应用；",
    "该系列设备均已通过关键存储客户端现场验证，满足先进存储应用中所有金属互连应用及三维存储器件字线应用各项性能指标，并获得客户重复量产订单。",
]
IPO = [
    "公司主要采用以销定产的生产模式。本公司的主要生产资料是原材料、人工及检测组装设备。原材料方面，公司的原材料供应渠道较多，公司与合格原材料供应商建立了稳定的合作关系，能够保证原材料的供应和质量的稳定，原材料不会成为公司的产能瓶颈。",
    "公司产能具有一定弹性，能根据订单情况灵活地安排人工、原材料采购进行生产安排。由于半导体产业需求存在波动，下游客户的投资扩产可能会相对集中，导致设备厂商突发的较大订单需求，公司短期配备的人工、组装检测设备在一定程度上会限制公司的生产，同时上游供应商原材料的短期供货能力也会限制应对突发需求的生产，这些因素在一定程度上约束公司的生产能力。",
]


@pytest.mark.parametrize("title,texts", [("2025年度报告.pdf", ANNUAL), ("上市招股说明书.pdf", IPO)])
def test_frozen_business_excerpt_pdf_parse_select_original_byte_replay(tmp_path, title, texts):
    with owned_state(tmp_path) as (root, _catalog):
        path = root / title
        document = fitz.open()
        try:
            for text in texts:
                page = document.new_page(width=600, height=800)
                assert page.insert_textbox(fitz.Rect(50, 50, 550, 700), text,
                    fontname="china-s", fontsize=12) >= 0
            document.save(path)
        finally:
            document.close()
        original = path.read_bytes()
        source_sha = hashlib.sha256(original).hexdigest()
        parsed = parse_pdf(path, source_id=source_id_for_sha256(source_sha),
            source_sha256=source_sha, language="zh")
        package = select_narrative_evidence(parsed, title=title, selector_version="0.7.0")
        joined = "".join(span.raw_text or "" for span in package.evidence_spans)
        assert "设备" in joined and ("现场验证" in joined if texts is ANNUAL else "短期供货" in joined)
        verified, failed = verify_pdf_evidence_spans(path, source_id=source_id_for_sha256(source_sha),
            source_sha256=source_sha, evidence_spans=package.evidence_spans)
        assert failed == () and len(verified) == len(package.evidence_spans)
        assert path.read_bytes() == original
        if texts is IPO:
            assert "以销定产" in joined and "不会成为" in joined and "突发" in joined
            assert {span.coordinates.page_number for span in package.evidence_spans} == {1, 2}
        assert package.selection_limit == (160 if texts is IPO else 96)


def import_page(catalog, page):
    raw = json.dumps(page, ensure_ascii=False, separators=(",", ":")).encode()
    digest = hashlib.sha256(raw).hexdigest()
    result = import_official_json_source(catalog, original=raw, request={
        "schema_version": "official-source-import-request/2", "request_id": "w03-" + digest,
        "max_bytes": 1048576, "content_sha256": digest, "mime_type": "application/json",
        "document_kind": "investor_relations", "source_subject": {
            "kind": "multi_issuer_event", "event_namespace": "w03-fixture", "event_id": "1",
            "issuer_refs": [], "attribution_status": "partial"},
        "capture_receipt": {"capture_method": "local_document", "tool_name": "offline-w03-test",
            "tool_call_id": digest, "captured_at": "2026-10-10T00:00:00Z",
            "response_bytes": len(raw), "content_sha256": digest}})
    return SourceRef(**result["source_ref"]), raw


def test_native_json_business_structure_role_parent_issuer_and_real_replay(tmp_path):
    native = "公司的产品分为控制器与执行器，控制器通过直销供给设备厂，执行器由海外渠道销售；关键部件须完成客户验证。"
    question = "传闻海外项目已经获得20个客户订单，是否属实？"
    records = [{"id": issuer, "companyId": issuer,
        "content": native if issuer == 1 else "Foreign issuer revenue increased by 20%.",
        "contentEn": "Translated content must not enter. " * 30,
        "questionContent": question, "isAnswered": True,
        "crtTime": "2026-09-01 10:00:00", "updTime": "2026-09-02 10:00:00"}
        for issuer in (1, 2)]
    page = {"success": True, "code": 200, "datas": [{"current": 1, "size": 2,
        "pages": 1, "total": 2, "records": records}]}
    with owned_state(tmp_path) as (_root, catalog):
        ref, original = import_page(catalog, page)
        projection = build_projection_from_refs(catalog, refs=[ref], layout_id="official-paged-qa",
            issuer={"provider_company_id": 1}, as_of_date="2026-10-08")
        persist_projection(catalog, projection)
        view = open_verified_projection(catalog, projection_id=projection.projection_id,
            expected_projection_sha256=projection.projection_sha256)
        old = select_verified_projection(view, title="投资者关系活动记录",
            selector=partial(select_narrative_evidence, selector_version="0.6.0"))
        new = select_verified_projection(view, title="投资者关系活动记录",
            selector=partial(select_narrative_evidence, selector_version="0.7.0"))
        package = new
        assert native in {span.raw_text for span in package.evidence_spans}
        # Real typed selected DTO bridges the pure policy package to existing
        # source-verified replay; this does not claim AUTO runtime was switched.
        dto = NarrativeSelectResult.from_dict({
            "schema_version": "narrative-select-result/3.0", "subject_binding": view.subject.to_dict(),
            "source_metadata": {"source_class": "official_json", "title": "投资者关系活动记录",
                "document_kind": "investor_relations", "language": "zh"},
            "parser": {"name": view.evidence_spans[0].parser_name, "version": view.evidence_spans[0].parser_version},
            "selector": {"name": "select_narrative_evidence", "version": "0.7.0"},
            "selection": {"status": package.status, "coverage_complete": package.coverage_complete,
                "source_units": package.source_units, "candidate_count": package.candidate_count,
                "selected_count": len(package.evidence_spans), "omitted_candidate_count": package.omitted_candidate_count,
                "dropped_financial_count": package.dropped_financial_count, "pages_total": 1, "pages_read": 1,
                "lines_total": 0, "tables_total": 0, "tables_scanned": 0},
            "evidence_spans": [span.to_dict() for span in package.evidence_spans],
            "prompt_review": {"status": "not_reviewed", "source_sha256": None,
                "evidence_sha256": None, "policy_hash": None, "reviewed_at": None},
            "summary_scope": "selected_evidence_only"})
        assert replay_verified_projection(view, dto) == len(package.evidence_spans)
        for span in package.evidence_spans:
            meta = span.structured_value
            assert meta["provider_record_id"] == 1
            assert meta["parent_content_sha256"] == ref.content_sha256
            assert meta["language"] == "zh"
            assert "translation" not in meta["role"]
            if span.raw_text == question:
                assert meta["source_role"] == "investor_question"
                assert not meta.get("selection_group_id")
            if span.raw_text == native:
                assert meta["source_role"] == "management"
                assert "business_structure" in meta["selection_reasons"]
        assert SourceVersionReader(catalog).open_version(ref).data == original
        assert old.selection_limit == package.selection_limit == 96
