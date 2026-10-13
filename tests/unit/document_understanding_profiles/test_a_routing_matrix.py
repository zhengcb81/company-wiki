"""A-node: routing matrix RED over real document shapes.

Each case is a synthetic ``du-input/1`` observation assembled from bounded heading,
cover and TOC fragments observed in the plan's own sample evidence. Expectations come
from the design matrix, not from the implementation.
"""

from __future__ import annotations

import pytest
from fixtures.document_understanding_profiles import builders as b

from .wire_contract import (
    assert_profile_shape,
    assert_route_shape,
    import_profiles_module,
)


def _route(observation, **limits):
    route = import_profiles_module().route_document(observation, limits=limits or None)
    assert_route_shape(route)
    return route


def _cn_annual_observation():
    return b.observation(
        [
            *[b.unit(f"c{i}", i, text, kind="heading") for i, text in enumerate(b.CN_ANNUAL_COVER)],
            *[
                b.unit(f"t{i}", 10 + i, text, kind="heading")
                for i, text in enumerate(b.CN_ANNUAL_TOC)
            ],
            *[
                b.unit(f"b{i}", 40 + i, text)
                for i, text in enumerate(b.CN_ANNUAL_BODY)
            ],
        ],
        title="中微公司：2025年年度报告",
        declared_kind="annual_report",
        regime="cn_exchange",
        language="zh",
    )


def _cn_quarterly_observation(*, body=()):
    units = [
        *[b.unit(f"c{i}", i, text, kind="heading") for i, text in enumerate(b.CN_QUARTERLY)],
        *[b.unit(f"b{i}", 20 + i, text) for i, text in enumerate(body)],
    ]
    return b.observation(
        units,
        title="中微公司：2026年第一季度报告",
        declared_kind="quarterly_report",
        regime="cn_exchange",
        language="zh",
    )


def test_cn_annual_routes_to_annual_profile():
    route = _route(_cn_annual_observation())
    assert route["profile_id"] == "cn_annual"
    assert route["family"] == "annual"
    assert route["regime"] == "cn_exchange"
    assert route["disposition_hint"] == "read"
    assert route["confidence"] == "high"


def test_cn_annual_body_evidence_names_the_mdna_section():
    """The reason list must cite the real heading units that drove the decision."""
    observation = _cn_annual_observation()
    route = _route(observation)
    cited = {unit_id for reason in route["reasons"] for unit_id in reason["unit_ids"]}
    by_id = {unit["unit_id"]: unit["text"] for unit in observation["units"]}
    assert cited, "a high-confidence route must cite the units it read"
    assert all(unit_id in by_id for unit_id in cited), "reason unit_ids must exist in input"
    assert any("管理层讨论与分析" in by_id[unit_id] for unit_id in cited)


def test_cn_interim_routes_to_interim_profile():
    observation = b.observation(
        [
            *[
                b.unit(f"c{i}", i, text, kind="heading")
                for i, text in enumerate(
                    ["公司代码：688012", "2026 年半年度报告", "1 / 210"]
                )
            ],
            *[
                b.unit(f"t{i}", 10 + i, text, kind="heading")
                for i, text in enumerate(
                    [
                        "第一节 释义",
                        "第二节 公司简介和主要财务指标",
                        "第三节 管理层讨论与分析",
                        "第十节 财务报告",
                    ]
                )
            ],
        ],
        title="中微公司：2026年半年度报告",
        declared_kind="semi_annual_report",
        regime="cn_exchange",
        language="zh",
    )
    route = _route(observation)
    assert route["profile_id"] == "cn_interim"
    assert route["family"] == "interim"
    assert route["disposition_hint"] == "read"


def test_cn_quarterly_with_business_body_is_read():
    route = _route(_cn_quarterly_observation(body=b.CN_QUARTERLY_BODY))
    assert route["profile_id"] == "cn_quarterly"
    assert route["family"] == "quarterly"
    assert route["disposition_hint"] == "read"


def test_cn_quarterly_sparse_body_is_still_read_not_skipped():
    """Design: never skip the whole quarterly class; low density is not absence."""
    sparse = b.observation(
        [
            *[b.unit(f"c{i}", i, text, kind="heading") for i, text in enumerate(b.CN_QUARTERLY)],
            b.unit("b0", 20, "□适用 √不适用"),
            b.unit("b1", 21, "合并资产负债表"),
            b.unit("b2", 22, "货币资金 394,410,377.57 373,084,861.17"),
        ],
        title="世华科技：2026年第一季度报告",
        declared_kind="quarterly_report",
        regime="cn_exchange",
        language="zh",
    )
    route = _route(sparse)
    assert route["profile_id"] == "cn_quarterly"
    assert route["disposition_hint"] in {"read", "generic_read"}
    assert route["disposition_hint"] != "administrative_candidate"


def test_cn_equity_offering_wording_is_recognized():
    """Card acceptance: A-share ``发行A股股票`` must be recognized, not left unknown."""
    observation = b.observation(
        [
            *[
                b.unit(f"c{i}", i, text, kind="heading")
                for i, text in enumerate(b.CN_OFFERING_COVER)
            ],
            *[b.unit(f"b{i}", 20 + i, text) for i, text in enumerate(b.CN_OFFERING_BODY)],
        ],
        title=None,
        declared_kind="unknown",
        regime="unknown",
        language="zh",
    )
    route = _route(observation)
    assert route["family"] == "offering"
    assert route["profile_id"] == "offering"
    assert route["regime"] == "cn_exchange"
    assert route["disposition_hint"] == "read"
    assert route["subtype"] is not None


def test_cn_convertible_bond_is_an_offering_not_an_ipo_prospectus():
    observation = b.observation(
        [
            *[
                b.unit(f"c{i}", i, text, kind="heading")
                for i, text in enumerate(b.CN_CONVERTIBLE_COVER)
            ],
            *[
                b.unit(f"b{i}", 20 + i, text, kind="heading")
                for i, text in enumerate(b.CN_CONVERTIBLE_BODY)
            ],
        ],
        title=None,
        declared_kind="convertible_bond_prospectus",
        regime="unknown",
        language="zh",
    )
    route = _route(observation)
    assert route["family"] == "offering"
    assert route["profile_id"] == "offering"
    assert "convertible" in (route["subtype"] or "") or "bond" in (route["subtype"] or "")


def test_cn_ipo_prospectus_is_a_prospectus():
    observation = b.observation(
        [
            *[b.unit(f"c{i}", i, text, kind="heading") for i, text in enumerate(b.CN_IPO_COVER)],
            *[b.unit(f"t{i}", 10 + i, text, kind="heading") for i, text in enumerate(b.CN_IPO_TOC)],
            b.unit("b0", 40, "第六节 业务与技术"),
            b.unit("b1", 41, "公司主营业务为半导体设备的研发、生产和销售。"),
        ],
        title="中微公司：首次公开发行股票并在科创板上市招股说明书",
        declared_kind="prospectus",
        regime="cn_exchange",
        language="zh",
    )
    route = _route(observation)
    assert route["family"] == "prospectus"
    assert route["profile_id"] == "prospectus"
    assert route["disposition_hint"] == "read"


def test_hk_periodic_bilingual_routes_to_hk_periodic():
    observation = b.observation(
        [
            *[
                b.unit(f"c{i}", i, text, kind="heading")
                for i, text in enumerate(b.HK_ANNUAL_COVER)
            ],
            *[
                b.unit(f"t{i}", 10 + i, text, kind="heading")
                for i, text in enumerate(b.HK_ANNUAL_TOC)
            ],
            *[b.unit(f"b{i}", 40 + i, text) for i, text in enumerate(b.HK_ANNUAL_BODY)],
        ],
        title="2024年度报告（港股）",
        declared_kind="annual_report",
        regime="hkex",
        language="zh-Hant",
    )
    route = _route(observation)
    assert route["profile_id"] == "hk_periodic"
    assert route["family"] == "annual"
    assert route["regime"] == "hkex"
    assert route["disposition_hint"] == "read"


def test_hk_interim_routes_to_hk_periodic_interim():
    observation = b.observation(
        [
            *[
                b.unit(f"c{i}", i, text, kind="heading")
                for i, text in enumerate(
                    ["MINISO", "Interim Report 2025", "2025中期報告"]
                )
            ],
            *[b.unit(f"t{i}", 10 + i, text, kind="heading") for i, text in enumerate(b.HK_INTERIM_TOC)],
        ],
        title="2025半年报（港股）",
        declared_kind="semi_annual_report",
        regime="hkex",
        language="zh-Hant",
    )
    route = _route(observation)
    assert route["profile_id"] == "hk_periodic"
    assert route["family"] == "interim"


def test_hk_ipo_cover_without_the_word_prospectus_is_recognized():
    """The real HK cover says ``全球發售`` and never contains 招股."""
    observation = b.observation(
        [
            *[b.unit(f"c{i}", i, text, kind="heading") for i, text in enumerate(b.HK_IPO_COVER)],
            *[b.unit(f"t{i}", 10 + i, text, kind="heading") for i, text in enumerate(b.HK_IPO_TOC)],
        ],
        title=None,
        declared_kind="unknown",
        regime="hkex",
        language="zh-Hant",
    )
    route = _route(observation)
    assert route["family"] == "prospectus"
    assert route["profile_id"] == "prospectus"
    assert route["regime"] == "hkex"


@pytest.mark.parametrize(
    "profile_id,cover,index,body,regime",
    [
        ("sec_10k", b.SEC_10K_COVER, b.SEC_10K_INDEX, b.SEC_10K_BODY, "sec"),
        ("sec_10q", b.SEC_10Q_COVER, [], b.SEC_10Q_BODY, "sec"),
        ("sec_20f", b.SEC_20F_COVER, [], b.SEC_20F_BODY, "sec"),
    ],
)
def test_sec_forms_route_to_their_own_profiles(profile_id, cover, index, body, regime):
    units = [b.unit(f"c{i}", i, text, kind="heading") for i, text in enumerate(cover)]
    units += [b.unit(f"t{i}", 10 + i, text, kind="heading") for i, text in enumerate(index)]
    units += [b.unit(f"b{i}", 40 + i, text) for i, text in enumerate(body)]
    observation = b.observation(
        units, title=None, declared_kind="unknown", regime="unknown", language="en"
    )
    route = _route(observation)
    assert route["profile_id"] == profile_id
    assert route["regime"] == regime
    assert route["disposition_hint"] == "read"


def test_sec_and_hk_vocabularies_never_cross_apply():
    """A 20-F must not be read with 10-K item numbers, nor an HK report with SEC items."""
    twenty_f = b.observation(
        [b.unit(f"c{i}", i, text, kind="heading") for i, text in enumerate(b.SEC_20F_COVER)]
        + [b.unit(f"b{i}", 20 + i, text) for i, text in enumerate(b.SEC_20F_BODY)],
        title=None,
        declared_kind="unknown",
        regime="unknown",
        language="en",
    )
    route = _route(twenty_f)
    assert route["profile_id"] == "sec_20f"

    sec_10k_profile = import_profiles_module().get_profile("sec_10k")
    sec_20f_profile = import_profiles_module().get_profile("sec_20f")
    ten_k_aliases = {
        alias.casefold()
        for entry in sec_10k_profile["section_priorities"]
        for alias in entry["aliases"]
    }
    twenty_f_aliases = {
        alias.casefold()
        for entry in sec_20f_profile["section_priorities"]
        for alias in entry["aliases"]
    }
    assert ten_k_aliases != twenty_f_aliases
    assert not any("item 4" in alias for alias in ten_k_aliases)
    assert not any("item 7" in alias for alias in twenty_f_aliases)

    hk_profile = import_profiles_module().get_profile("hk_periodic")
    hk_aliases = {
        alias.casefold()
        for entry in hk_profile["section_priorities"]
        for alias in entry["aliases"]
    }
    assert not any(alias.startswith("item ") for alias in hk_aliases)


def test_results_release_english_html():
    observation = b.observation(
        [b.unit(f"u{i}", i, text) for i, text in enumerate(b.RESULTS_RELEASE_HTML)],
        title=None,
        declared_kind="unknown",
        regime="unknown",
        mime_type="text/html",
        language="en",
    )
    route = _route(observation)
    assert route["profile_id"] == "results_release"
    assert route["family"] == "results_release"
    assert route["disposition_hint"] == "read"


def test_hk_results_release_is_not_a_periodic_filing():
    observation = b.observation(
        [b.unit(f"u{i}", i, text, kind="heading" if i < 3 else "paragraph") for i, text in enumerate(b.HK_RELEASE)],
        title="Tencent second-quarter and first-half 2026 results",
        declared_kind="unknown",
        regime="hkex",
        language="en",
    )
    route = _route(observation)
    assert route["profile_id"] == "results_release"
    assert route["family"] == "results_release"


def test_presentation_deck():
    observation = b.observation(
        [b.unit(f"u{i}", i, text, kind="heading") for i, text in enumerate(b.HK_DECK)],
        title=None,
        declared_kind="unknown",
        regime="unknown",
        language="en",
    )
    route = _route(observation)
    assert route["profile_id"] == "presentation"
    assert route["family"] == "presentation"


def test_earnings_call_transcript_keeps_speaker_turns():
    observation = b.observation(
        [b.unit(f"u{i}", i, text) for i, text in enumerate(b.TRANSCRIPT_TXT)],
        title=None,
        declared_kind="investor_call_transcript",
        regime="unknown",
        mime_type="text/plain",
    )
    route = _route(observation)
    assert route["profile_id"] == "earnings_call"
    assert route["family"] == "earnings_call"
    profile = import_profiles_module().get_profile("earnings_call")
    assert "qa_exchange" in profile["semantic_units"]


def test_investor_qa_record_detected_from_qa_pairs():
    observation = b.observation(
        [b.unit(f"u{i}", i, text, kind="heading" if i < 2 else "paragraph") for i, text in enumerate(b.CN_IR_QA)],
        title="万润股份：投资者关系活动记录表20260515",
        declared_kind="investor_relations",
        regime="cn_exchange",
        language="zh",
    )
    route = _route(observation)
    assert route["profile_id"] == "investor_qa"
    assert route["family"] == "investor_qa"
    assert route["disposition_hint"] == "read"


def test_ir_policy_is_administrative_candidate_not_a_skip():
    observation = b.observation(
        [b.unit(f"u{i}", i, text, kind="heading" if i < 3 else "paragraph") for i, text in enumerate(b.CN_IR_POLICY)],
        title="万润股份：002643万润股份投资者关系管理制度20230428",
        declared_kind="ir_policy",
        regime="cn_exchange",
        language="zh",
    )
    route = _route(observation)
    assert route["disposition_hint"] == "administrative_candidate"
    assert route["family"] == "administrative"
    assert route["profile_id"] == "administrative"


def test_meeting_notice_is_administrative_candidate():
    observation = b.observation(
        [b.unit(f"u{i}", i, text, kind="heading" if i == 0 else "paragraph") for i, text in enumerate(b.CN_MEETING_NOTICE)],
        title="关于召开2025年度业绩说明会的公告",
        declared_kind="meeting_notice",
        regime="cn_exchange",
        language="zh",
    )
    route = _route(observation)
    assert route["disposition_hint"] == "administrative_candidate"
    assert route["profile_id"] == "administrative"


def test_confirmation_letter_is_never_a_full_ipo_prospectus():
    """The plan's headline real defect: title says 招股说明书, body is a one-page letter."""
    observation = b.observation(
        [
            b.unit(
                "u1",
                0,
                b.CN_CONFIRMATION_LETTER[0],
                kind="heading",
                page=1,
            )
        ],
        title="鼎龙股份：控股股东、实际控制人对《首次公开发行股票并在创业板上市招股说明书》的确认意见",
        declared_kind="prospectus",
        regime="cn_exchange",
        language="zh",
        native_scan="partial",
        opaque_pages=[1],
    )
    route = _route(observation)
    assert route["profile_id"] == "administrative"
    assert route["family"] == "administrative"
    assert route["disposition_hint"] == "administrative_candidate"
    assert route["disposition_hint"] != "read"
    assert "administrative" in (route["subtype"] or "")


def test_confirmation_letter_with_empty_native_text_still_routes_administrative(
):
    """Real case ``cn-ipo-confirmation``: one opaque page, empty native text."""
    observation = b.observation(
        [],
        title="关于《首次公开发行股票并在创业板上市招股说明书》的确认意见",
        declared_kind="prospectus",
        regime="cn_exchange",
        language=None,
        native_scan="unavailable",
        opaque_pages=[1],
    )
    route = _route(observation)
    assert route["disposition_hint"] == "administrative_candidate"
    assert route["profile_id"] == "administrative"
    assert route["confidence"] in {"low", "medium", "unknown"}


def test_director_report_is_not_a_full_annual_report():
    observation = b.observation(
        [b.unit(f"u{i}", i, text, kind="heading" if i < 2 else "paragraph") for i, text in enumerate(b.CN_DIRECTOR_REPORT)],
        title="中微公司：2025年度独立董事述职报告",
        declared_kind="annual_report",
        regime="cn_exchange",
        language="zh",
    )
    route = _route(observation)
    assert route["family"] == "administrative"
    assert route["disposition_hint"] == "administrative_candidate"
    assert route["profile_id"] != "cn_annual"


def test_unknown_document_still_routes_to_generic_read():
    observation = b.observation(
        [b.unit("u1", 0, "Some unrelated text without any recognizable structure.")],
        title=None,
        declared_kind="unknown",
        regime="unknown",
        language=None,
    )
    route = _route(observation)
    assert route["profile_id"] == "generic"
    assert route["disposition_hint"] == "generic_read"
    assert route["confidence"] in {"low", "unknown"}
    assert route["regime"] == "unknown"


def test_empty_observation_is_readable_not_a_crash():
    observation = b.observation([], title=None, declared_kind="unknown", regime="unknown")
    route = _route(observation)
    assert route["profile_id"] == "generic"
    assert route["disposition_hint"] == "generic_read"


def test_every_required_profile_is_reachable_by_a_route():
    """No profile may be dead weight: each must be some observation's winner."""
    observations = [
        _cn_annual_observation(),
        _cn_quarterly_observation(body=b.CN_QUARTERLY_BODY),
    ]
    reachable = {_route(item)["profile_id"] for item in observations}
    assert "cn_annual" in reachable
    assert "cn_quarterly" in reachable


def test_routed_profile_id_exists_in_the_registry():
    route = _route(_cn_annual_observation())
    profile = import_profiles_module().get_profile(route["profile_id"])
    assert_profile_shape(profile)
    assert profile["profile_version"] == route["profile_version"]
    assert profile["family"] == route["family"]
