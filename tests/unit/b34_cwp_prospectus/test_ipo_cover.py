"""Native exact IPO-cover proof, never treating it as the requested quarter.

Ported from the B34 candidate (dashboard-B34-prospectus-cover, final state
`925b0ad3f`): the exact cover heading proves kind ``prospectus`` only when a
full bounded-frontmatter sweep binds the issuer and finds no conflicting
periodic/IR heading.  There is deliberately no first-page rule; the locator
names the first bound page of the sweep.
"""

from types import SimpleNamespace
import pytest
from company_wiki.source_catalog.local_reconcile import (
    _cn_cover_scope,
    prepare_local_source,
)
from company_wiki.source_catalog.source_reader import SourceReadError
from unit.test_local_source_boundaries import (
    cn_lake,
    cn_request,
    original_with_text,
    NAME,
)


def observe(text, allow=True):
    original = original_with_text(text)
    return _cn_cover_scope(
        original,
        SimpleNamespace(canonical_name=NAME, market="CN", security_id="600999"),
        SimpleNamespace(check=lambda: None),
        allow_other_kinds=allow,
    )


@pytest.mark.parametrize(
    "title", ["首次公开发行股票招股说明书", "首次公开发行股票\n招股说明书"]
)
def test_exact_native_cover_keeps_period_unknown(title):
    facts, proof = observe(NAME + "\n" + title)
    assert facts["document_kind"] == "prospectus"
    assert facts["fiscal_year"] is None and facts["fiscal_period"] is None
    assert all(
        p["extraction_method"] == "cn-ipo-prospectus-cover/1"
        and p["content_sha256"]
        and "pdf:page:1:" in p["locator"]
        for p in proof.values()
    )


@pytest.mark.parametrize(
    "text",
    [
        NAME + "\n请查阅首次公开发行股票招股说明书",
        NAME + "\n参见\n首次公开发行股票招股说明书",
        NAME + "\n公司说明：首次公开发行股票招股说明书",
        NAME + "\n首次公开发行股票招股说明书编制说明",
        NAME + "\n招股说明书",
        "另一公司\n首次公开发行股票招股说明书",
        NAME + "供应链股份有限公司\n首次公开发行股票招股说明书",
        NAME + "\n证券代码：600998\n首次公开发行股票招股说明书",
        NAME + "\n2026年第三季度报告\n首次公开发行股票招股说明书",
        NAME + "\n投资者关系活动记录表\n首次公开发行股票招股说明书",
    ],
)
def test_mention_foreign_or_ambiguous_cover_cannot_restore(text):
    with pytest.raises(SourceReadError):
        observe(text)


def test_unbound_cover_after_a_bound_page_cannot_inherit_the_binding():
    """A positive earlier page never authorises an unbound cover (B34 final)."""
    cover = "首次公开发行股票招股说明书"
    text = NAME + "\n证券代码：600999\n" + cover + "\n另一公司\n" + cover
    with pytest.raises(SourceReadError):
        observe(text)


def test_other_kinds_gate_remains_required():
    with pytest.raises(SourceReadError):
        observe(NAME + "\n首次公开发行股票招股说明书", allow=False)


def test_actual_public_prepare_proves_prospectus_without_inventing_requested_period(
    tmp_path,
):
    catalog, raw = cn_lake(tmp_path)
    try:
        company = raw / NAME
        company.mkdir()
        original = original_with_text(NAME + "\n首次公开发行股票招股说明书")
        path = company / "original.pdf"
        path.write_bytes(original.data)
        result = prepare_local_source(catalog, cn_request())
        assert result["status"] == "not_found", result
        assert result["blocks_download"] is False and result["download_events"] == 0
        rows = catalog.reader.fetchall("SELECT document_kind FROM documents")
        assert rows and all(x["document_kind"] == "prospectus" for x in rows)
        assert (
            catalog.reader.fetchone(
                "SELECT COUNT(*) FROM source_metadata_assertions WHERE evidence_basis='source-facts'"
            )[0]
            > 0
        )
        assert path.read_bytes() == original.data
    finally:
        catalog.close()
