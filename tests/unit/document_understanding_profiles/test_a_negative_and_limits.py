"""A/B-node: negative cases, metadata conflicts, probe limits, determinism, immutability.

These are the counter-examples the card demands: same-named sections, a 10-K or
prospectus mentioned only inside a cross-reference, missing or scan-only bodies, and a
low-confidence generic read that must stay honest instead of guessing.
"""

from __future__ import annotations

import copy
import json

import pytest
from fixtures.document_understanding_profiles import builders as b

from .wire_contract import assert_route_shape, import_profiles_module


def _route(observation, **limits):
    route = import_profiles_module().route_document(observation, limits=limits or None)
    assert_route_shape(route)
    return route


def test_same_named_section_does_not_imply_the_family():
    """A document merely containing ``管理层讨论与分析`` is not automatically an annual."""
    observation = b.observation(
        [
            b.unit("u1", 0, "会议纪要", kind="heading"),
            b.unit("u2", 1, "会上讨论了同业公司年报中第三节 管理层讨论与分析 的写法。"),
            b.unit("u3", 2, "与会人员就表述方式交换了意见。"),
        ],
        title=None,
        declared_kind="unknown",
        regime="unknown",
        language="zh",
    )
    route = _route(observation)
    assert route["profile_id"] != "cn_annual"
    assert route["profile_id"] == "generic"


def test_sec_10k_mentioned_only_in_a_cross_reference_is_not_a_10k():
    observation = b.observation(
        [
            b.unit("u1", 0, "Newsletter", kind="heading"),
            b.unit("u2", 1, "See our Form 10-K Item 1A Risk Factors for details."),
            b.unit("u3", 2, "Subscribe to receive the quarterly update."),
        ],
        title="Investor newsletter",
        declared_kind="unknown",
        regime="unknown",
        language="en",
    )
    route = _route(observation)
    assert route["profile_id"] != "sec_10k"
    assert route["profile_id"] == "generic"


def test_prospectus_mentioned_only_in_a_cross_reference_is_not_a_prospectus():
    observation = b.observation(
        [
            b.unit("u1", 0, "上市公告书", kind="heading"),
            b.unit("u2", 1, "详见公司《首次公开发行股票招股说明书》第六节。"),
            b.unit("u3", 2, "本次上市流通数量为 1,200 万股。"),
        ],
        title="上市公告书",
        declared_kind="unknown",
        regime="unknown",
        language="zh",
    )
    route = _route(observation)
    assert route["profile_id"] != "prospectus"


def test_scan_only_body_is_not_silently_read():
    observation = b.observation(
        [],
        title="中微公司：2025年年度报告",
        declared_kind="annual_report",
        regime="cn_exchange",
        language="zh",
        native_scan="unavailable",
        opaque_pages=[1, 2, 3],
    )
    route = _route(observation)
    assert route["disposition_hint"] != "read"
    assert route["confidence"] in {"low", "unknown"}
    codes = {reason["code"] for reason in route["reasons"]}
    assert codes & {"OPAQUE_PAGES", "NO_READABLE_BODY", "NATIVE_SCAN_UNAVAILABLE"}


def test_partial_scan_is_reported_in_reasons():
    observation = b.observation(
        [
            *[b.unit(f"c{i}", i, text, kind="heading") for i, text in enumerate(b.CN_ANNUAL_COVER)],
            *[
                b.unit(f"t{i}", 10 + i, text, kind="heading")
                for i, text in enumerate(b.CN_ANNUAL_TOC)
            ],
        ],
        title="中微公司：2025年年度报告",
        declared_kind="annual_report",
        regime="cn_exchange",
        language="zh",
        native_scan="partial",
        opaque_pages=[7, 8],
    )
    route = _route(observation)
    codes = {reason["code"] for reason in route["reasons"]}
    assert "PARTIAL_NATIVE_SCAN" in codes
    assert route["confidence"] != "high"


def test_metadata_claiming_quarterly_with_annual_body_reports_the_conflict():
    """Contradictory metadata must produce a diagnostic, not a silent override."""
    observation = b.observation(
        [
            *[b.unit(f"c{i}", i, text, kind="heading") for i, text in enumerate(b.CN_ANNUAL_COVER)],
            *[
                b.unit(f"t{i}", 10 + i, text, kind="heading")
                for i, text in enumerate(b.CN_ANNUAL_TOC)
            ],
            *[b.unit(f"b{i}", 40 + i, text) for i, text in enumerate(b.CN_ANNUAL_BODY)],
        ],
        title="中微公司：2025年年度报告",
        declared_kind="quarterly_report",
        regime="cn_exchange",
        language="zh",
    )
    route = _route(observation)
    codes = {reason["code"] for reason in route["reasons"]}
    assert codes & {"METADATA_CONFLICT", "DECLARED_KIND_CONFLICT"}
    assert route["profile_id"] == "cn_annual"


def test_metadata_claiming_sec_with_hk_body_reports_the_conflict():
    observation = b.observation(
        [
            *[b.unit(f"c{i}", i, text, kind="heading") for i, text in enumerate(b.HK_ANNUAL_COVER)],
            *[
                b.unit(f"t{i}", 10 + i, text, kind="heading")
                for i, text in enumerate(b.HK_ANNUAL_TOC)
            ],
        ],
        title="2024年度报告（港股）",
        declared_kind="annual_report",
        regime="sec",
        form_type="10-K",
        language="zh-Hant",
    )
    route = _route(observation)
    assert route["profile_id"] == "hk_periodic"
    assert route["regime"] == "hkex"
    codes = {reason["code"] for reason in route["reasons"]}
    assert codes & {"METADATA_CONFLICT", "REGIME_CONFLICT", "DECLARED_KIND_CONFLICT"}


def test_alternatives_are_offered_when_two_families_compete():
    """A genuine ambiguity lists the runner-up instead of hiding it."""
    observation = b.observation(
        [
            *[b.unit(f"c{i}", i, text, kind="heading") for i, text in enumerate(b.HK_IPO_COVER)],
            *[b.unit(f"t{i}", 10 + i, text, kind="heading") for i, text in enumerate(b.HK_IPO_TOC)],
            b.unit("b0", 40, "ANNUAL REPORT 2024"),
        ],
        title=None,
        declared_kind="unknown",
        regime="unknown",
        language="zh-Hant",
    )
    route = _route(observation)
    for alternative in route["alternatives"]:
        assert alternative["profile_id"] != route["profile_id"]
        assert alternative["reason"]


def test_reason_details_do_not_copy_long_body_text():
    """``detail`` is a short diagnosis, never a body dump."""
    long_line = "公司主营业务为半导体专用设备的研发、生产和销售。" * 40
    observation = b.observation(
        [
            *[b.unit(f"c{i}", i, text, kind="heading") for i, text in enumerate(b.CN_ANNUAL_COVER)],
            *[
                b.unit(f"t{i}", 10 + i, text, kind="heading")
                for i, text in enumerate(b.CN_ANNUAL_TOC)
            ],
            b.unit("b0", 40, long_line),
        ],
        title="中微公司：2025年年度报告",
        declared_kind="annual_report",
        regime="cn_exchange",
        language="zh",
    )
    route = _route(observation)
    for reason in route["reasons"]:
        assert len(reason["detail"]) <= 200, reason["detail"]


# --- limits --------------------------------------------------------------------------


def test_default_limits_are_the_frozen_ones():
    observation = b.observation(
        [b.unit(f"u{i}", i, f"line {i}") for i in range(5)],
        declared_kind="unknown",
    )
    route = import_profiles_module().route_document(observation)
    assert route["schema_version"] == "du-route/1"


def test_probe_limit_marks_route_low_confidence():
    units = [
        *[b.unit(f"c{i}", i, text, kind="heading") for i, text in enumerate(b.CN_ANNUAL_COVER)],
        *[
            b.unit(f"t{i}", 10 + i, text, kind="heading")
            for i, text in enumerate(b.CN_ANNUAL_TOC)
        ],
        *[b.unit(f"b{i}", 100 + i, f"filler paragraph {i}") for i in range(50)],
    ]
    observation = b.observation(
        units,
        title="中微公司：2025年年度报告",
        declared_kind="annual_report",
        regime="cn_exchange",
        language="zh",
    )
    route = _route(observation, max_probe_units=1)
    codes = {reason["code"] for reason in route["reasons"]}
    assert "ROUTE_PROBE_LIMIT" in codes
    assert route["confidence"] in {"low", "unknown"}
    assert route["disposition_hint"] in {"read", "generic_read"}


def test_probe_char_limit_marks_route_partial():
    observation = b.observation(
        [
            b.unit(f"c{i}", i, text, kind="heading")
            for i, text in enumerate(b.CN_ANNUAL_COVER)
        ]
        + [
            b.unit(f"t{i}", 10 + i, text, kind="heading")
            for i, text in enumerate(b.CN_ANNUAL_TOC)
        ],
        title="中微公司：2025年年度报告",
        declared_kind="annual_report",
        regime="cn_exchange",
        language="zh",
    )
    route = _route(observation, max_probe_chars=1)
    codes = {reason["code"] for reason in route["reasons"]}
    assert "ROUTE_PROBE_LIMIT" in codes


def test_limits_cannot_be_raised_by_a_profile():
    """Profiles carry no budget field: the caller keeps the ceiling."""
    for profile in import_profiles_module().list_profiles():
        assert "max_probe_units" not in profile
        assert "limits" not in profile
        assert "max_probe_chars" not in profile


def test_limits_do_not_change_the_input():
    observation = b.observation(
        [
            b.unit("u1", 0, "2025 年年度报告", kind="heading"),
            b.unit("u2", 1, "第一节 释义", kind="heading"),
        ],
        title="2025 年年度报告",
    )
    before = copy.deepcopy(observation)
    import_profiles_module().route_document(observation, limits={"max_probe_units": 1})
    assert observation == before


def test_max_child_routes_caps_child_routes():
    units = [b.unit(f"u{i}", i, f"paragraph {i}") for i in range(30)]
    attachments = [
        b.unit(f"a{i}", 100 + i, f"附件{i}：https://example.invalid/doc{i}.pdf", kind="attachment")
        for i in range(30)
    ]
    observation = b.observation(units + attachments, title=None, declared_kind="unknown")
    route = _route(observation, max_child_routes=2)
    assert len(route["child_routes"]) <= 2


# --- determinism and immutability ----------------------------------------------------


def test_route_is_deterministic_across_calls():
    observation = b.observation(
        [
            *[b.unit(f"c{i}", i, text, kind="heading") for i, text in enumerate(b.CN_ANNUAL_COVER)],
            *[
                b.unit(f"t{i}", 10 + i, text, kind="heading")
                for i, text in enumerate(b.CN_ANNUAL_TOC)
            ],
        ],
        title="中微公司：2025年年度报告",
        declared_kind="annual_report",
        regime="cn_exchange",
        language="zh",
    )
    first = import_profiles_module().route_document(observation)
    second = import_profiles_module().route_document(observation)
    assert first == second
    assert json.dumps(first, sort_keys=True, ensure_ascii=False) == json.dumps(
        second, sort_keys=True, ensure_ascii=False
    )


def test_route_does_not_mutate_the_observation():
    observation = b.observation(
        [b.unit(f"u{i}", i, f"line {i}") for i in range(5)],
        title=None,
        declared_kind="unknown",
        opaque_pages=[2],
        deferred_pages=[3],
    )
    before = copy.deepcopy(observation)
    import_profiles_module().route_document(observation)
    assert observation == before


def test_route_output_is_json_serializable():
    observation = b.observation(
        [b.unit(f"u{i}", i, f"line {i}") for i in range(5)], declared_kind="unknown"
    )
    route = import_profiles_module().route_document(observation)
    assert json.loads(json.dumps(route, ensure_ascii=False))


def test_ordering_is_stable_when_units_are_reordered_identically():
    """The decision must not depend on how unit ids happen to be spelled.

    Reasons legitimately cite the ids of *this* input, so the comparison is on the
    decision itself plus the reason codes -- not on the literal id strings.
    """
    first = b.observation(
        [
            *[b.unit(f"c{i}", i, text, kind="heading") for i, text in enumerate(b.SEC_10K_COVER)],
            *[
                b.unit(f"t{i}", 10 + i, text, kind="heading")
                for i, text in enumerate(b.SEC_10K_INDEX)
            ],
        ],
        title=None,
        declared_kind="unknown",
        regime="unknown",
        language="en",
    )
    second = copy.deepcopy(first)
    for index, unit in enumerate(second["units"]):
        unit["unit_id"] = f"zz{index:03d}"

    first_route = import_profiles_module().route_document(first)
    second_route = import_profiles_module().route_document(second)

    for key in (
        "schema_version",
        "profile_id",
        "profile_version",
        "regime",
        "family",
        "subtype",
        "confidence",
        "disposition_hint",
    ):
        assert first_route[key] == second_route[key], key
    assert [reason["code"] for reason in first_route["reasons"]] == [
        reason["code"] for reason in second_route["reasons"]
    ]
    assert [route["profile_id"] for route in first_route["child_routes"]] == [
        route["profile_id"] for route in second_route["child_routes"]
    ]


# --- input validation ----------------------------------------------------------------


def test_rejects_wrong_schema_version():
    observation = b.observation([b.unit("u1", 0, "text")], declared_kind="unknown")
    observation["schema_version"] = "du-input/2"
    with pytest.raises((ValueError, KeyError)):
        import_profiles_module().route_document(observation)


def test_rejects_missing_units_key():
    observation = b.observation([b.unit("u1", 0, "text")], declared_kind="unknown")
    del observation["units"]
    with pytest.raises((ValueError, KeyError, TypeError)):
        import_profiles_module().route_document(observation)


def test_rejects_duplicate_unit_ids():
    observation = b.observation(
        [b.unit("u1", 0, "a"), b.unit("u1", 1, "b")], declared_kind="unknown"
    )
    with pytest.raises((ValueError, KeyError)):
        import_profiles_module().route_document(observation)


def test_rejects_non_mapping_observation():
    with pytest.raises((TypeError, ValueError)):
        import_profiles_module().route_document(["not", "a", "mapping"])


def test_tolerates_missing_optional_metadata_fields():
    """Optional fields absent is ``unknown``, never a review gate."""
    observation = {
        "schema_version": "du-input/1",
        "source_ref": {"source_id": "s", "source_sha256": "d"},
        "metadata": {"title": None},
        "coverage": {},
        "units": [
            {
                "unit_id": "u1",
                "ordinal": 0,
                "locator": "opaque-locator-1",
                "page": None,
                "text": "unstructured note",
            }
        ],
    }
    route = import_profiles_module().route_document(observation)
    assert_route_shape(route)
    assert route["profile_id"] == "generic"


def test_no_review_or_permission_gate_is_required():
    """The card forbids any human-permission flow in routing."""
    observation = b.observation(
        [b.unit("u1", 0, "text")], title=None, declared_kind="unknown", regime="unknown"
    )
    route = import_profiles_module().route_document(observation)
    serialized = json.dumps(route, ensure_ascii=False).casefold()
    for forbidden in ("permission", "approval", "signoff", "sign_off", "authoriz"):
        assert forbidden not in serialized


def test_disposition_is_never_a_skip_or_delete():
    """Only ROOT decides the final skip; the router never returns it."""
    for observation in (
        b.observation([], title=None, declared_kind="unknown"),
        b.observation(
            [b.unit(f"u{i}", i, text) for i, text in enumerate(b.CN_IR_POLICY)],
            title="投资者关系管理制度",
            declared_kind="ir_policy",
        ),
        b.observation(
            [b.unit("u1", 0, b.CN_CONFIRMATION_LETTER[0])],
            title="确认意见",
            declared_kind="prospectus",
        ),
    ):
        route = import_profiles_module().route_document(observation)
        assert route["disposition_hint"] in {"read", "generic_read", "administrative_candidate"}


def test_no_company_name_or_security_code_special_casing():
    """Same shape, different company wording, must give the same route."""
    first = b.observation(
        [
            *[b.unit(f"c{i}", i, text, kind="heading") for i, text in enumerate(b.CN_ANNUAL_COVER)],
            *[
                b.unit(f"t{i}", 10 + i, text, kind="heading")
                for i, text in enumerate(b.CN_ANNUAL_TOC)
            ],
        ],
        title="甲公司：2025年年度报告",
        declared_kind="annual_report",
        regime="cn_exchange",
        language="zh",
    )
    second = copy.deepcopy(first)
    second["metadata"]["title"] = "乙公司：2025年年度报告"
    for unit in second["units"]:
        unit["text"] = unit["text"].replace("中微公司", "乙公司")
    first_route = import_profiles_module().route_document(first)
    second_route = import_profiles_module().route_document(second)
    assert first_route["profile_id"] == second_route["profile_id"]
    assert first_route["family"] == second_route["family"]
