"""W05 native DOCX original identity, bounded parsing and replay contracts."""

from __future__ import annotations
import hashlib
import io
import zipfile
from dataclasses import replace
import pytest
from company_wiki.document_normalization import (
    normalize_document,
    DOCX_PARSER_VERSION,
    NormalizationLimits,
    replay_units,
)
from company_wiki.document_normalization.errors import (
    NormalizationError,
    NormalizationLimitError,
    ReplayError,
)

MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def package(body, extra=None):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
        )
        z.writestr(
            "word/document.xml",
            f'<w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>',
        )
        for name, data in (extra or {}).items():
            z.writestr(name, data)
    return out.getvalue()


def para(text):
    return f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"


def norm(data, **kw):
    sha = hashlib.sha256(data).hexdigest()
    return normalize_document(
        data,
        source_id="urn:company-wiki:source:sha256:" + sha,
        source_sha256=sha,
        mime_type=MIME,
        **kw,
    )


def test_native_text_table_qa_and_exact_original_replay():
    data = package(
        para("投资者关系活动记录")
        + para("问：新产品海外客户认证有何进展？")
        + para("答：新产品已通过海外客户认证并获得重复订单。")
        + "<w:tbl><w:tr><w:tc>"
        + para("业务")
        + "</w:tc><w:tc>"
        + para("进展")
        + "</w:tc></w:tr><w:tr><w:tc>"
        + para("新业务")
        + "</w:tc><w:tc>"
        + para("新增客户并扩产")
        + "</w:tc></w:tr></w:tbl>"
    )
    before = hashlib.sha256(data).hexdigest()
    doc = norm(data)
    assert doc.format_name == "docx" and doc.parser_version == DOCX_PARSER_VERSION
    assert doc.structure.coverage_complete
    assert [u.raw_text for u in doc.units[:3]] == [
        "投资者关系活动记录",
        "问：新产品海外客户认证有何进展？",
        "答：新产品已通过海外客户认证并获得重复订单。",
    ]
    assert [u.source_role for u in doc.units[:3]] == [
        "company_filing",
        "analyst",
        "management",
    ]
    assert doc.units[1].metadata["qa_group_id"] == doc.units[2].metadata["qa_group_id"]
    cells = doc.units[3:]
    assert len(cells) == 4
    assert [
        (
            u.coordinates.table_index,
            u.coordinates.row_index,
            u.coordinates.column_index,
            u.metadata["cell_paragraph_index"],
        )
        for u in cells
    ] == [(0, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 1, 1, 0)]
    assert len({u.metadata["source_locator"] for u in doc.units}) == 7
    assert replay_units(
        data, source_sha256=before, units=doc.units, limits=NormalizationLimits()
    ) == tuple(u.raw_text for u in doc.units)
    assert hashlib.sha256(data).hexdigest() == before


def test_duplicate_headings_and_blank_paragraph_ordinals_are_stable():
    data = package(para("业务进展") + "<w:p/>" + para("业务进展"))
    a = norm(data)
    b = norm(data)
    assert [u.coordinates.paragraph_index for u in a.units] == [0, 2]
    assert a.units == b.units and a.units[0].unit_id != a.units[1].unit_id


def test_hyperlink_label_retained_external_relationship_never_executed(monkeypatch):
    import socket

    monkeypatch.setattr(
        socket.socket, "connect", lambda *a, **kw: pytest.fail("external fetch")
    )
    data = package(
        '<w:p xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:hyperlink r:id="rId1"><w:r><w:t>海外新产品认证已完成</w:t></w:r></w:hyperlink></w:p>',
        {
            "word/_rels/document.xml.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="https://example.invalid/never" TargetMode="External"/></Relationships>'
        },
    )
    doc = norm(data)
    assert doc.units[0].raw_text == "海外新产品认证已完成"
    assert (
        doc.structure.coverage_complete
        and doc.metadata["external_relationship_count"] == 1
    )
    assert "https://" not in repr(doc.metadata)


def test_tracked_deleted_text_excluded_and_current_insertions_diagnosed():
    data = package(
        "<w:p><w:r><w:t>新产品</w:t></w:r><w:del><w:r><w:delText>已经投产</w:delText></w:r></w:del><w:ins><w:r><w:t>仍在客户认证中</w:t></w:r></w:ins></w:p>"
    )
    doc = norm(data)
    assert doc.units[0].raw_text == "新产品仍在客户认证中"
    assert (
        "tracked_changes_present" in doc.structure.errors
        and not doc.structure.coverage_complete
    )


@pytest.mark.parametrize("name", ["../escape.xml", "word/../../escape.xml"])
def test_archive_traversal_refused(name):
    with pytest.raises(NormalizationError, match="archive"):
        norm(package(para("content"), {name: b"bad"}))


def test_corrupt_archive_refused_with_named_error():
    with pytest.raises(NormalizationError, match="DOCX|docx|archive"):
        norm(b"PK" + b"bad archive")


def test_duplicate_zip_member_refused():
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as z:
        z.writestr("word/document.xml", "a")
        z.writestr("word/document.xml", "b")
    with pytest.raises(NormalizationError, match="duplicate"):
        norm(data.getvalue())


def test_missing_body_and_doctype_refused():
    for body in [
        '<w:document xmlns:w="' + W + '"/>',
        '<!DOCTYPE x [<!ENTITY evil "leaked">]><w:document xmlns:w="'
        + W
        + '"><w:body><w:p><w:r><w:t>&evil;</w:t></w:r></w:p></w:body></w:document>',
    ]:
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w") as z:
            z.writestr("word/document.xml", body)
        with pytest.raises(NormalizationError):
            norm(out.getvalue())


def test_zip_expansion_text_units_and_deadline_are_finite():
    data = package(para("x" * 50000))
    with pytest.raises(NormalizationLimitError, match="max_total_uncompressed_bytes"):
        norm(data, limits=NormalizationLimits(max_total_uncompressed_bytes=1000))
    with pytest.raises(NormalizationLimitError, match="max_text_output_bytes"):
        norm(data, limits=NormalizationLimits(max_text_output_bytes=100))
    with pytest.raises(NormalizationLimitError, match="max_units"):
        norm(
            package(para("first") + para("second")),
            limits=NormalizationLimits(max_units=1),
        )
    with pytest.raises(NormalizationLimitError, match="deadline"):
        norm(data, limits=NormalizationLimits(deadline=0))


def test_replay_rejects_changed_source_and_forged_coordinates():
    data = package(para("Company launched a new product overseas."))
    doc = norm(data)
    with pytest.raises(ReplayError):
        replay_units(
            data + b"changed",
            source_sha256=doc.source_sha256,
            units=doc.units,
            limits=NormalizationLimits(),
        )
    u = doc.units[0]
    with pytest.raises(ReplayError):
        replay_units(
            data,
            source_sha256=doc.source_sha256,
            units=(replace(u, coordinates=replace(u.coordinates, paragraph_index=9)),),
            limits=NormalizationLimits(),
        )


def test_native_language_sampling_and_generation_dispatch():
    from company_wiki.source_catalog.narrative_language import detect_narrative_language
    from company_wiki.automation.narrative_formats import (
        parser_component,
        source_class_for,
    )

    data = package(
        para("公司新产品已通过海外客户认证并获得重复订单，主营业务取得持续进展。")
    )
    assert detect_narrative_language(data, MIME) == "zh"
    assert source_class_for(MIME, "investor_relations") == "filing"
    assert parser_component(MIME) == ("cwp_document_normalization", DOCX_PARSER_VERSION)


def test_one_paragraph_qa_splits_roles_with_original_character_locators():
    data = package(
        para("问：新产品海外客户认证完成了吗？答：新产品已完成海外客户认证并进入量产。")
    )
    doc = norm(data)
    assert [u.source_role for u in doc.units] == ["analyst", "management"]
    assert doc.units[0].metadata["qa_group_id"] == doc.units[1].metadata["qa_group_id"]
    assert (
        "".join(u.raw_text for u in doc.units)
        == "问：新产品海外客户认证完成了吗？答：新产品已完成海外客户认证并进入量产。"
    )
    assert all(
        u.coordinates.char_start is not None and "|ch=" in u.metadata["source_locator"]
        for u in doc.units
    )
    assert replay_units(
        data,
        source_sha256=doc.source_sha256,
        units=doc.units,
        limits=NormalizationLimits(),
    ) == tuple(u.raw_text for u in doc.units)


def test_explicit_vanish_false_preserves_current_visible_text():
    doc = norm(
        package(
            '<w:p><w:r><w:rPr><w:vanish w:val="false"/></w:rPr><w:t>新产品已通过客户认证</w:t></w:r></w:p>'
        )
    )
    assert doc.units[0].raw_text == "新产品已通过客户认证"


def test_answer_reply_label_keeps_management_role_in_inline_qa():
    data = package(
        para("问题：新产品是否已投产？答复：新产品已进入量产并交付海外客户。")
    )
    doc = norm(data)
    assert [u.source_role for u in doc.units] == ["analyst", "management"]
    assert doc.units[0].metadata["qa_group_id"] == doc.units[1].metadata["qa_group_id"]


def test_excessive_xml_depth_rejected_with_named_limit():
    body = "<w:customXml>" * 140 + para("业务进展") + "</w:customXml>" * 140
    with pytest.raises(NormalizationLimitError, match="max_xml_depth"):
        norm(package(body))


def test_deleted_only_body_and_embedded_object_have_explicit_diagnostics():
    deleted = norm(
        package(
            "<w:del><w:p><w:r><w:delText>原先预计已量产</w:delText></w:r></w:p></w:del>"
        )
    )
    assert not deleted.units
    assert set(deleted.structure.errors) == {
        "tracked_changes_present",
        "docx_no_visible_text",
    }
    opaque = norm(
        package(para("客户认证取得进展") + "<w:p><w:r><w:object/></w:r></w:p>")
    )
    assert [u.raw_text for u in opaque.units] == ["客户认证取得进展"]
    assert (
        "docx_opaque_content" in opaque.structure.errors
        and not opaque.structure.coverage_complete
    )


def test_macro_package_refused_before_body_use():
    with pytest.raises(NormalizationError, match="macro"):
        norm(package(para("新产品业务进展"), {"word/vbaProject.bin": b"unused"}))


def test_deleted_body_paragraph_and_table_still_reserve_source_ordinals():
    deleted = (
        "<w:del>"
        + para("删除的旧计划")
        + "<w:tbl><w:tr><w:tc>"
        + para("删除的表格")
        + "</w:tc></w:tr></w:tbl></w:del>"
    )
    current = (
        para("当前海外客户认证完成")
        + "<w:tbl><w:tr><w:tc>"
        + para("当前订单已开始交付")
        + "</w:tc></w:tr></w:tbl>"
    )
    doc = norm(package(deleted + current))
    assert doc.units[0].coordinates.paragraph_index == 1
    assert doc.units[1].coordinates.table_index == 1
    assert all("删除" not in u.raw_text for u in doc.units)


def test_unparsed_cell_wrapper_is_explicit_partial_coverage():
    body = (
        "<w:tbl><w:tr><w:tc><w:sdt><w:sdtContent>"
        + para("客户认证完成")
        + "</w:sdtContent></w:sdt></w:tc></w:tr></w:tbl>"
    )
    doc = norm(package(body + para("当前新产品业务进展")))
    assert doc.units
    assert "docx_unsupported_table_element" in doc.structure.errors
    assert not doc.structure.coverage_complete
