"""Production matching behavior for source-observed market outlines."""

import pytest
from company_wiki.document_understanding.profiles import (
    get_profile,
    resolve_reading_profile,
)
from company_wiki.document_understanding.strategy_binding import _match_rule


def profile(pid, family, regime, form=None):
    metadata = {"regime": regime}
    if form:
        metadata["form_type"] = form
    original = {
        "schema_version": "du-input/1",
        "source_ref": {"source_id": "original", "source_sha256": "a" * 64},
        "metadata": metadata,
        "coverage": {
            "native_scan": "complete",
            "opaque_pages": [],
            "deferred_pages": [],
        },
        "units": [],
    }
    return resolve_reading_profile(
        get_profile(pid),
        original,
        {"family": family, "regime": regime, "form_type": form},
    )


def matched(p, *chain):
    ids = [str(i) for i in range(len(chain))]
    rule = _match_rule(
        ids[-1],
        p,
        {sid: ids[i - 1] if i else None for i, sid in enumerate(ids)},
        dict(zip(ids, chain)),
        [],
    )
    return rule["role"] if rule else None


@pytest.mark.parametrize(
    "parent", ["Item 3. Key Information", "Item 3 Key Information"]
)
def test_20f_real_nested_risk(parent):
    assert (
        matched(profile("sec_20f", "annual", "sec", "20-F"), parent, "D. Risk Factors")
        == "risk"
    )


def test_20f_cannot_borrow_10k_mda_number():
    assert (
        matched(
            profile("sec_20f", "annual", "sec", "20-F"),
            "Item 7. Major Shareholders and Related Party Transactions",
        )
        != "management_discussion"
    )


@pytest.mark.parametrize(
    "heading",
    [
        "RECENT DEVELOPMENTS AFTER THE REPORTING PERIOD",
        "RECENT DEVELOPMENT AFTER THE REPORTING PERIOD",
        "報告期後的近期發展",
    ],
)
def test_hk_interim_postperiod_is_local_outlook(heading):
    assert matched(profile("hk_periodic", "interim", "hkex"), heading) == "outlook"


@pytest.mark.parametrize("parent", ["Item 18. Financial Statements"])
def test_20f_notes_business_mechanism_uses_its_actual_part(parent):
    assert (
        matched(
            profile("sec_20f", "annual", "sec", "20-F"),
            parent,
            "Notes to Financial Statements",
        )
        == "financial_notes"
    )


def test_20f_risk_subsection_d_does_not_escape_parent_scope():
    assert (
        matched(
            profile("sec_20f", "annual", "sec", "20-F"),
            "Item 6. Directors, Senior Management and Employees",
            "D. Risk Factors",
        )
        is None
    )


def test_interim_declared_business_review_can_be_root_heading():
    assert (
        matched(profile("hk_periodic", "interim", "hkex"), "Business Review")
        == "business"
    )


@pytest.mark.parametrize(
    "heading,role",
    [
        ("我們的市場機會", "industry"),
        ("募集資金用途", "fundraising"),
        ("我們的業務", "business"),
    ],
)
def test_hk_prospectus_second_listing_uses_source_chapter_titles(heading, role):
    assert matched(profile("prospectus", "prospectus", "hkex"), heading) == role


def test_cn_prospectus_business_chapter_does_not_require_itself_twice():
    assert (
        matched(profile("prospectus", "prospectus", "cn_exchange"), "第六节 业务与技术")
        == "business"
    )


@pytest.mark.parametrize(
    "form,title,heads,role",
    [
        (
            "20-F",
            "FORM 20-F",
            [("Item 3. Key Information", 1), ("D. Risk Factors", 2)],
            "risk",
        ),
        (
            None,
            "中期報告 INTERIM REPORT",
            [("RECENT DEVELOPMENTS AFTER THE REPORTING PERIOD", 1)],
            "outlook",
        ),
        (None, "中期報告 INTERIM REPORT", [("Business Review", 1)], "business"),
    ],
)
def test_actual_native_headings_bind_the_body_policy(form, title, heads, role):
    from company_wiki.document_understanding import understand_units
    from company_wiki.source_catalog.narrative_evidence import _make_unit
    from company_wiki.source_contract import EvidenceCoordinates, source_id_for_sha256

    sid = source_id_for_sha256("a" * 64)
    texts = [
        (title, 1),
        *heads,
        ("Our platform provides learning services and software subscriptions.", None),
    ]
    units = [
        _make_unit(
            source_id=sid,
            parser_version="1.0.0",
            coordinates=EvidenceCoordinates(paragraph_index=i),
            raw_text=text,
            unit_kind="html_heading" if level else "html_paragraph",
            source_role="company_filing",
            language="en",
            metadata={"heading_level": level, "tag_name": f"h{level}"} if level else {},
        )
        for i, (text, level) in enumerate(texts)
    ]
    result = understand_units(
        units,
        source_id=sid,
        source_sha256="a" * 64,
        declared_kind="unknown",
        mime_type="text/html",
        language="en",
        metadata={"form_type": form, "regime": "sec" if form else "hkex"},
    )
    views = result["reading_plan"]["unit_profiles"]
    body = views[units[-1].unit_id]
    assert body["section_role"] == role
    assert body["matched_section_rule"] is not None
    assert body["family_policy"]["id"] == ("sec_20f" if form else "hk_interim_report")


def test_conditional_currency_policy_reaches_actual_model_request():
    import json
    from company_wiki.automation.narrative_contracts import NarrativeSelectResult
    from company_wiki.automation.narrative_model_scoped import build_scoped_request
    from unit.test_narrative_reading_transport import with_reading

    wire = with_reading().to_dict()
    policy = profile("earnings_call", "earnings_call", "unknown")
    # Feed only the source-to-model wire fields, not the routing resolver's
    # private probe/section diagnostics; the production DTO validates this seam.
    keys = wire["reading_context"]["reading_policies"][0].keys()
    wire["reading_context"]["reading_policies"] = [{key: policy[key] for key in keys}]
    selected = NarrativeSelectResult.from_dict(wire)
    request = build_scoped_request(selected)
    strategy = json.loads(request.data_json)["reading_strategy"]["reading_policies"][0]
    assert any(
        "reported/constant currency" in text and "两者相同时" in text
        for text in strategy["reading_questions"]
    )
    assert selected.to_dict() == wire
