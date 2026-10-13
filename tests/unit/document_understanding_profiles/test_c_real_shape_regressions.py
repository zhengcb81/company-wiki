"""C-node: regression locks for the defects the real-sample recheck exposed.

Each test below corresponds to a defect found by routing the plan's own real observed
document shapes (titles, TOC lines, heading lines, bounded excerpts) rather than by
inventing another synthetic fixture. Every one of them was a genuine routing bug; the
comment on each test records what actually went wrong in the real sample.

These are regression locks, not new capability: they must stay green as the router evolves.
"""

from __future__ import annotations

from fixtures.document_understanding_profiles import builders as b

from .wire_contract import assert_route_shape, import_profiles_module


def _route(observation, **limits):
    module = import_profiles_module()
    route = module.route_document(observation, limits=limits or None)
    assert_route_shape(route)
    return route


def test_bare_declaration_heading_does_not_make_a_filing_administrative():
    """Real ``cn-annual``/``cn-h1``: every A-share report has a ``声明`` section.

    An annual report whose front matter includes ``声明`` (the board's authenticity
    declaration) was being routed to ``administrative``. A boilerplate disclosure section
    is not an administrative purpose, so ``声明`` must not be an administrative marker.
    """
    observation = b.observation(
        [
            b.unit("u1", 0, "公司代码：688012", kind="heading"),
            b.unit("u2", 1, "2025 年年度报告", kind="heading"),
            b.unit("u3", 2, "一、公司上市时未盈利且尚未实现盈利", kind="heading"),
            b.unit("u4", 3, "五、公司负责人尹志尧声明：保证年度报告中财务报告的真实、准确、完整。"),
            b.unit("u5", 4, "八、前瞻性陈述的风险声明", kind="heading"),
        ],
        title="某公司：2025年年度报告",
        declared_kind="annual_report",
        regime="cn_exchange",
        language="zh",
    )
    route = _route(observation)
    assert route["family"] != "administrative"
    assert route["disposition_hint"] != "administrative_candidate"


def test_issuer_declaration_page_in_an_offering_is_not_administrative():
    """Real ``cn-equity``: the offering document opens with ``发行人声明``/``特别提示``.

    Those are mandatory front matter of the offering document itself, so they must not
    override the offering family.
    """
    observation = b.observation(
        [
            b.unit("u1", 0, "发行人声明", kind="heading"),
            b.unit("u2", 1, "特别提示", kind="heading"),
            b.unit("u3", 2, "目录", kind="heading"),
            b.unit("u4", 3, "第一节 发行人基本情况", kind="heading"),
            b.unit("u5", 4, "本次向特定对象发行A 股股票拟募集资金总额为不超过35,978.71 万元。"),
            b.unit("u6", 5, "（二）项目投资计划", kind="heading"),
        ],
        title=None,
        declared_kind="unknown",
        regime="unknown",
        language="zh",
    )
    route = _route(observation)
    assert route["family"] == "offering"
    assert route["disposition_hint"] == "read"


def test_policy_cited_inside_a_prospectus_does_not_make_it_administrative():
    """Real ``cn-ipo``: the IPO prospectus cites ``《募集资金管理办法》`` in its body.

    A cross-reference to a policy document was being read as the prospectus's own purpose,
    routing a 429-page IPO prospectus to ``administrative``. A pointer is not a purpose.
    """
    observation = b.observation(
        [
            b.unit("u1", 0, "首次公开发行股票并在科创板上市", kind="heading"),
            b.unit("u2", 1, "招股说明书", kind="heading"),
            b.unit("u3", 2, "三、募集资金用于研发投入、科技创新、新产品开发生产的情形", kind="heading"),
            b.unit("u4", 3, "《募集资金管理办法》", kind="heading"),
            b.unit("u5", 4, "《中微半导体设备（上海）股份有限公司募集资金管理办法》", kind="heading"),
            b.unit("u6", 5, "本公司提醒投资者认真阅读本招股说明书的“风险因素”部分。"),
        ],
        title=None,
        declared_kind="unknown",
        regime="unknown",
        language="zh",
    )
    route = _route(observation)
    assert route["family"] == "prospectus"
    assert route["disposition_hint"] == "read"


def test_ten_q_referring_to_its_own_10k_is_not_a_10k():
    """Real ``us-10q``: a 10-Q always says "our annual report on Form 10-K".

    The phrase was matching the 10-K pattern and routing a quarterly report to the annual
    family. A form name inside a pointer to another filing is not this document's form.
    """
    observation = b.observation(
        [
            b.unit(
                "u1",
                0,
                " material changes to our contractual obligations outside the ordinary "
                "course of our business from those reported in our annual report on Form "
                "10-K and filed with the Securities and Exchange Commission on "
                "February 26, 2025.",
            ),
            b.unit(
                "u2",
                1,
                "For the three months ended March 31, 2025 and 2024, we had no material "
                "transactions with related parties.",
            ),
            b.unit(
                "u3",
                2,
                "Revenues We earn revenues through agreements for hosted subscriptions, "
                "advisory/consulting services, and for transactional solutions.",
            ),
        ],
        title=None,
        declared_kind="unknown",
        regime="unknown",
        mime_type="text/html",
        language="en",
    )
    route = _route(observation)
    assert route["profile_id"] != "sec_10k"
    assert route["family"] == "quarterly"


def test_ten_q_interim_period_is_detected_from_narrative_text():
    """The interim-period wording lives in narrative prose, not in a heading line.

    The SEC item header is often outside the probed window, so period wording must be read
    from every probed unit rather than only from heading-like lines.
    """
    observation = b.observation(
        [
            b.unit(
                "u1",
                0,
                "our annual report on Form 10-K dated and filed with the Securities and "
                "Exchange Commission on February 26, 2025.",
            ),
            b.unit(
                "u2",
                1,
                "For the three months ended March 31, 2025 and 2024, approximately 83% and "
                "80% of our insurance revenues were derived from hosted subscriptions.",
            ),
        ],
        title=None,
        declared_kind="unknown",
        regime="unknown",
        mime_type="text/html",
        language="en",
    )
    route = _route(observation)
    assert route["profile_id"] == "sec_10q"
    assert route["family"] == "quarterly"


def test_annual_report_reference_alone_is_not_a_ten_q():
    """The guard must not fire the other way: a 10-K excerpt is not a 10-Q.

    An annual report also says "annual report on Form 10-K", but it does not report a
    quarter, so it must not acquire the interim family.
    """
    observation = b.observation(
        [
            b.unit("u1", 0, "CORPORATION FORM 10-K For the Fiscal Year Ended June 30, 2025"),
            b.unit("u2", 1, "OUR ANNUAL REPORT ON FORM 10-K"),
            b.unit(
                "u3",
                2,
                "Azure revenue is mainly affected by infrastructure-as-a-service and "
                "platform-as-a-service consumption-based services.",
            ),
        ],
        title=None,
        declared_kind="unknown",
        regime="unknown",
        mime_type="text/html",
        language="en",
    )
    route = _route(observation)
    assert route["profile_id"] == "sec_10k"
    assert route["family"] == "annual"


def test_english_annual_report_phrase_does_not_imply_hk():
    """Real ``us-10q``: "annual report" was firing the HK annual signal on a US filing.

    The English phrase alone is not HK evidence; HK signals require HK vocabulary or a
    bilingual heading.
    """
    observation = b.observation(
        [
            b.unit("u1", 0, "See our annual report on Form 10-K for details."),
            b.unit("u2", 1, "This quarterly report covers subscriptions and deferred revenues."),
        ],
        title=None,
        declared_kind="unknown",
        regime="unknown",
        mime_type="text/html",
        language="en",
    )
    route = _route(observation)
    assert route["profile_id"] != "hk_periodic"
    assert route["regime"] != "hkex"


def test_hk_interim_is_distinguished_from_hk_annual():
    """Real ``hk-interim``: the interim report says ``2025中期報告`` / ``Interim Report``.

    Traditional ``報告`` and Simplified ``报告`` are different codepoints and NFKC does not
    convert between them, so both spellings must be listed; the earlier Simplified-only
    check routed a real interim report to the annual family.
    """
    observation = b.observation(
        [
            b.unit("u1", 0, "MINISO", kind="heading"),
            b.unit("u2", 1, "Interim Report 2025", kind="heading"),
            b.unit("u3", 2, "2025中期報告", kind="heading"),
            b.unit("u4", 3, "Business Review and Outlook", kind="heading"),
            b.unit("u5", 4, "業務回顧及展望", kind="heading"),
            b.unit("u6", 5, "Management Discussion and Analysis", kind="heading"),
            b.unit("u7", 6, "管理層討論與分析", kind="heading"),
        ],
        title=None,
        declared_kind="unknown",
        regime="unknown",
        language="zh-Hant",
    )
    route = _route(observation)
    assert route["profile_id"] == "hk_periodic"
    assert route["family"] == "interim"


def test_hk_annual_stays_annual_when_no_interim_marker_is_present():
    observation = b.observation(
        [
            b.unit("u1", 0, "MINISO", kind="heading"),
            b.unit("u2", 1, "ANNUAL REPORT 2024", kind="heading"),
            b.unit("u3", 2, "年度報告", kind="heading"),
            b.unit("u4", 3, "Business Review and Outlook", kind="heading"),
            b.unit("u5", 4, "業務回顧及展望", kind="heading"),
        ],
        title=None,
        declared_kind="unknown",
        regime="unknown",
        language="zh-Hant",
    )
    route = _route(observation)
    assert route["profile_id"] == "hk_periodic"
    assert route["family"] == "annual"


def test_unreadable_document_is_honestly_generic_not_guessed():
    """Real ``cn-ipo-confirmation``: one opaque page, zero readable characters.

    The confirmation wording lives only in the *filename* on that sample, and the router is
    forbidden to derive the country or the document type from a path. With no readable
    evidence and no supplied title, the honest answer is ``generic_read`` -- the route must
    not invent a family from the declared kind alone.
    """
    observation = b.observation(
        [],
        title=None,
        declared_kind="prospectus",
        regime="cn_exchange",
        language=None,
        native_scan="unavailable",
        opaque_pages=[1],
    )
    route = _route(observation)
    assert route["profile_id"] == "generic"
    assert route["disposition_hint"] == "generic_read"
    assert route["confidence"] in {"low", "unknown"}
    codes = {reason["code"] for reason in route["reasons"]}
    assert "NO_READABLE_BODY" in codes
    assert "NATIVE_SCAN_UNAVAILABLE" in codes
    assert "OPAQUE_PAGES" in codes


def test_ir_activity_record_wins_over_a_policy_shaped_filename():
    """Real ``cn-ir-policy``: the file name says 制度 but the body is an activity record.

    ``findings.md`` records this manifest entry as an activity record whose recorded body
    is an ``投资者关系活动记录表``. The body must win, and because the declared kind
    disagrees the route must say so rather than quietly overriding it.
    """
    observation = b.observation(
        [
            b.unit("u1", 0, "中节能万润股份有限公司投资者关系活动记录表", kind="heading"),
            b.unit("u2", 1, "投资者关系活动类别", kind="heading"),
            b.unit("u3", 2, "□特定对象调研  □分析师会议  ☑业绩说明会"),
            b.unit("u4", 3, "1、问：公司沸石系列环保材料目前理论产能近万吨，利用率是多少？"),
            b.unit("u5", 4, "答：您好，公司2022 年功能性材料整体产能利用率64.68%。"),
        ],
        title="某公司：投资者关系管理制度",
        declared_kind="ir_policy",
        regime="cn_exchange",
        language="zh",
    )
    route = _route(observation)
    assert route["profile_id"] == "investor_qa"
    assert route["family"] == "investor_qa"
    codes = {reason["code"] for reason in route["reasons"]}
    assert "DECLARED_KIND_CONFLICT" in codes


def test_real_shapes_are_deterministic_and_immutable():
    """A second pass over the real-shape set must be byte-identical and non-mutating."""
    import copy
    import json

    module = import_profiles_module()
    shapes = [
        b.observation(
            [b.unit(f"c{i}", i, t, kind="heading") for i, t in enumerate(b.SEC_10K_COVER)]
            + [b.unit(f"t{i}", 10 + i, t, kind="heading") for i, t in enumerate(b.SEC_10K_INDEX)]
            + [b.unit(f"x{i}", 40 + i, t) for i, t in enumerate(b.SEC_10K_BODY)],
            title=None,
            declared_kind="unknown",
            regime="unknown",
            language="en",
        ),
        b.observation(
            [b.unit(f"c{i}", i, t, kind="heading") for i, t in enumerate(b.HK_ANNUAL_COVER)]
            + [b.unit(f"t{i}", 10 + i, t, kind="heading") for i, t in enumerate(b.HK_ANNUAL_TOC)],
            title="2024年度报告（港股）",
            declared_kind="annual_report",
            regime="hkex",
            language="zh-Hant",
        ),
    ]
    for observation in shapes:
        before = copy.deepcopy(observation)
        first = module.route_document(observation)
        second = module.route_document(observation)
        assert observation == before
        assert json.dumps(first, sort_keys=True, ensure_ascii=False) == json.dumps(
            second, sort_keys=True, ensure_ascii=False
        )
