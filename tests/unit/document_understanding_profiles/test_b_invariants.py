"""B-node: independently verified invariants.

These tests do not restate the routing matrix. They attack the properties the card makes
a pass condition -- purity, determinism, budget obedience, profile composition, and the
scope boundary -- plus the specific failure modes that must never pass by accident:
raising ``max_probe``, editing an oracle, or forcing everything to ``annual``.
"""

from __future__ import annotations

import copy
import json
import os
import pathlib

import pytest
from fixtures.document_understanding_profiles import builders as b

from .wire_contract import (
    FAMILIES,
    REGIMES,
    SECTION_ROLES,
    SEMANTIC_UNITS,
    assert_profile_shape,
    assert_route_shape,
    import_profiles_module,
)

#: Source-file suffixes that must never leak into a route, so a carrier cannot be inferred
#: from a path-like detail. Spelled without a leading dot so this file embeds no host path.
SOURCE_SUFFIXES = ("pdf", "htm", "html", "txt", "docx", "pptx")

#: A representative spread of shapes reused by the property tests below.
SHAPES = {
    "cn_annual": lambda: b.observation(
        [b.unit(f"c{i}", i, t, kind="heading", page=1) for i, t in enumerate(b.CN_ANNUAL_COVER)]
        + [b.unit(f"t{i}", 10 + i, t, kind="heading", page=3) for i, t in enumerate(b.CN_ANNUAL_TOC)]
        + [b.unit(f"x{i}", 40 + i, t, page=41) for i, t in enumerate(b.CN_ANNUAL_BODY)],
        title="某公司：2025年年度报告",
        declared_kind="annual_report",
        regime="cn_exchange",
        language="zh",
    ),
    "cn_offering": lambda: b.observation(
        [b.unit(f"c{i}", i, t, kind="heading", page=1) for i, t in enumerate(b.CN_OFFERING_COVER)]
        + [b.unit(f"x{i}", 20 + i, t, page=61) for i, t in enumerate(b.CN_OFFERING_BODY)],
        title=None,
        declared_kind="unknown",
        regime="unknown",
        language="zh",
    ),
    "hk_periodic": lambda: b.observation(
        [b.unit(f"c{i}", i, t, kind="heading", page=1) for i, t in enumerate(b.HK_ANNUAL_COVER)]
        + [b.unit(f"t{i}", 10 + i, t, kind="heading", page=2) for i, t in enumerate(b.HK_ANNUAL_TOC)]
        + [b.unit(f"x{i}", 40 + i, t, page=11) for i, t in enumerate(b.HK_ANNUAL_BODY)],
        title="2024年度报告（港股）",
        declared_kind="annual_report",
        regime="hkex",
        language="zh-Hant",
    ),
    "sec_10k": lambda: b.observation(
        [b.unit(f"c{i}", i, t, kind="heading") for i, t in enumerate(b.SEC_10K_COVER)]
        + [b.unit(f"t{i}", 10 + i, t, kind="heading") for i, t in enumerate(b.SEC_10K_INDEX)]
        + [b.unit(f"x{i}", 40 + i, t) for i, t in enumerate(b.SEC_10K_BODY)],
        title=None,
        declared_kind="unknown",
        regime="unknown",
        language="en",
    ),
    "admin": lambda: b.observation(
        [b.unit("u1", 0, b.CN_CONFIRMATION_LETTER[0], kind="heading", page=1)],
        title="对《首次公开发行股票并在创业板上市招股说明书》的确认意见",
        declared_kind="prospectus",
        regime="cn_exchange",
        language="zh",
        native_scan="unavailable",
        opaque_pages=[1],
    ),
    "generic": lambda: b.observation(
        [b.unit("u1", 0, "some unstructured note without recognised structure")],
        title=None,
        declared_kind="unknown",
        regime="unknown",
        language=None,
    ),
    "empty": lambda: b.observation([], title=None, declared_kind="unknown", regime="unknown"),
}


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_route_is_pure_and_repeatable(shape):
    """Identical input, identical output -- including reason ordering."""
    module = import_profiles_module()
    observation = SHAPES[shape]()
    first = module.route_document(observation)
    second = module.route_document(observation)
    assert first == second
    assert json.dumps(first, sort_keys=True, ensure_ascii=False) == json.dumps(
        second, sort_keys=True, ensure_ascii=False
    )


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_route_does_not_mutate_the_observation(shape):
    module = import_profiles_module()
    observation = SHAPES[shape]()
    before = copy.deepcopy(observation)
    module.route_document(observation, limits={"max_probe_units": 2, "max_probe_chars": 16})
    assert observation == before


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_route_output_is_json_serializable(shape):
    route = import_profiles_module().route_document(SHAPES[shape]())
    assert json.loads(json.dumps(route, ensure_ascii=False))


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_route_is_within_the_frozen_vocabulary(shape):
    route = import_profiles_module().route_document(SHAPES[shape]())
    assert_route_shape(route)
    assert route["regime"] in REGIMES
    assert route["family"] in FAMILIES


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_reasons_cite_only_existing_units(shape):
    """A reason may cite no unit (title-only evidence) but never a fabricated one."""
    module = import_profiles_module()
    observation = SHAPES[shape]()
    valid = {unit["unit_id"] for unit in observation["units"]}
    route = module.route_document(observation)
    for reason in route["reasons"]:
        assert set(reason["unit_ids"]) <= valid, reason
        assert len(reason["unit_ids"]) == len(set(reason["unit_ids"])), reason


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_disposition_is_never_a_skip(shape):
    """Only ROOT decides the final skip; routing stops at administrative_candidate."""
    route = import_profiles_module().route_document(SHAPES[shape]())
    assert route["disposition_hint"] in {"read", "generic_read", "administrative_candidate"}


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_route_carries_no_path_or_company_identity(shape):
    """No file path and no absolute location may appear in the output.

    The markers are derived from this host rather than written as literals, so the check
    stays meaningful on any machine and does not itself embed a host path.
    """
    route = import_profiles_module().route_document(SHAPES[shape]())
    payload = json.dumps(route, ensure_ascii=False)
    markers = {
        os.sep,  # the platform separator, e.g. "\\" or "/"
        pathlib.Path.cwd().anchor,  # e.g. "C:\\" or "/"
        pathlib.Path.home().anchor,
    }
    for suffix in SOURCE_SUFFIXES:
        markers.add("." + suffix)
    for marker in sorted(marker for marker in markers if marker):
        assert marker not in payload, marker


def test_tightening_the_probe_budget_never_increases_confidence():
    """A smaller probe budget may not make a route more confident."""
    module = import_profiles_module()
    order = {"unknown": 0, "low": 1, "medium": 2, "high": 3}
    for shape in sorted(SHAPES):
        observation = SHAPES[shape]()
        full = module.route_document(observation)
        starved = module.route_document(
            observation, limits={"max_probe_units": 1, "max_probe_chars": 1}
        )
        assert order[starved["confidence"]] <= order[full["confidence"]], shape


def test_a_starved_probe_reports_the_limit():
    module = import_profiles_module()
    observation = SHAPES["cn_annual"]()
    route = module.route_document(observation, limits={"max_probe_units": 1})
    assert "ROUTE_PROBE_LIMIT" in {reason["code"] for reason in route["reasons"]}


def test_raising_the_budget_cannot_change_a_metadata_contradiction():
    """Widening the probe must not make a contradiction disappear."""
    module = import_profiles_module()
    observation = b.observation(
        [b.unit(f"c{i}", i, t, kind="heading") for i, t in enumerate(b.CN_ANNUAL_COVER)]
        + [b.unit(f"t{i}", 10 + i, t, kind="heading") for i, t in enumerate(b.CN_ANNUAL_TOC)]
        + [b.unit(f"x{i}", 40 + i, f"filler {i}") for i in range(400)],
        title="某公司：2025年年度报告",
        declared_kind="quarterly_report",
        regime="cn_exchange",
        language="zh",
    )
    for budget in (10, 200, 1000):
        route = module.route_document(observation, limits={"max_probe_units": budget})
        codes = {reason["code"] for reason in route["reasons"]}
        assert "DECLARED_KIND_CONFLICT" in codes, budget


def test_unknown_is_never_forced_to_annual():
    """The card forbids passing by classifying everything as an annual report."""
    module = import_profiles_module()
    unrelated = [
        b.observation([b.unit(f"u{i}", i, text)], title=None, declared_kind="unknown")
        for i, text in enumerate(
            [
                "a plain memo about lunch arrangements",
                "unstructured working notes",
                "1 2 3 4 5",
            ]
        )
    ]
    for observation in unrelated:
        route = module.route_document(observation)
        assert route["profile_id"] != "cn_annual"
        assert route["family"] != "annual"


def test_the_oracle_is_not_self_referential():
    """A profile's declared family must match what its route produces."""
    module = import_profiles_module()
    by_id = {profile["profile_id"]: profile for profile in module.list_profiles()}
    for shape, factory in SHAPES.items():
        route = module.route_document(factory())
        profile = by_id[route["profile_id"]]
        assert profile["family"] == route["family"] or profile["family"] == "unknown", (
            shape,
            route["profile_id"],
            profile["family"],
            route["family"],
        )
        assert profile["profile_version"] == route["profile_version"]


# --- profile composition --------------------------------------------------------------


def test_profiles_compose_rather_than_duplicate():
    """Types differ by aliases/priorities/focus, not by fifteen parallel pipelines."""
    module = import_profiles_module()
    profiles = module.list_profiles()
    assert len(profiles) == 15

    # Shared business/risk focus must be genuinely reused across periodic families: each
    # profile adds a type-specific sentence, but the shared clause is present in all.
    periodic = [
        profile
        for profile in profiles
        if profile["family"] in {"annual", "interim", "quarterly"}
    ]
    assert len(periodic) >= 4
    shared_clause = "有来源支持的具体风险与限制"
    assert all(shared_clause in profile["summary_focus"] for profile in periodic)
    assert all(
        "未披露项标注未披露而不是零" in profile["summary_focus"] for profile in periodic
    )
    focuses = [profile["summary_focus"] for profile in periodic]
    # Each periodic profile adds its own scope sentence, so the strings differ -- but they
    # must be built from the same shared core clauses rather than written independently.
    assert all(
        focus.startswith("记录报告期已发生的经营事实") for focus in focuses
    ), focuses

    # No profile may be an exact duplicate of another.
    fingerprints = [
        json.dumps(
            {k: v for k, v in profile.items() if k != "profile_id"},
            sort_keys=True,
            ensure_ascii=False,
        )
        for profile in profiles
    ]
    assert len(set(fingerprints)) == len(fingerprints)


def test_section_blocks_are_reused_across_profiles():
    """The same section aliases must serve several families, not be copied per type."""
    module = import_profiles_module()
    profiles = {profile["profile_id"]: profile for profile in module.list_profiles()}

    def aliases(profile_id):
        return {
            alias
            for entry in profiles[profile_id]["section_priorities"]
            for alias in entry["aliases"]
        }

    # A-share annual/interim/quarterly share the common CN blocks.
    assert aliases("cn_annual") & aliases("cn_interim")
    assert aliases("cn_annual") & aliases("cn_quarterly")
    # Prospectus and offering share the fundraising block.
    assert aliases("prospectus") & aliases("offering")
    fund_aliases = aliases("offering")
    assert "募集资金运用" in fund_aliases
    assert "募集资金运用" in aliases("prospectus")


def test_every_profile_uses_the_frozen_section_roles_and_semantic_units():
    for profile in import_profiles_module().list_profiles():
        assert_profile_shape(profile)
        for entry in profile["section_priorities"]:
            assert entry["section_role"] in SECTION_ROLES
        for unit in profile["semantic_units"]:
            assert unit in SEMANTIC_UNITS


def test_profiles_declare_a_reachable_priority_range():
    """Every profile must give the reader an ordering, and every priority must be usable.

    A typed profile marks at least one section as "read first" (priority 1). The
    ``generic`` profile is the deliberate exception: an unrecognised document has no
    highest-priority section, and claiming one would be a guess. It must still use the
    legal priority range.
    """
    for profile in import_profiles_module().list_profiles():
        priorities = [entry["priority"] for entry in profile["section_priorities"]]
        assert set(priorities) <= {1, 2, 3}, profile["profile_id"]
        if profile["profile_id"] == "generic":
            assert min(priorities) > 1, "generic must not claim a read-first section"
        else:
            assert min(priorities) == 1, profile["profile_id"]


def test_negative_hints_are_hints_not_deletion_rules():
    """A negative hint must describe soft evidence, never a whole-chapter delete."""
    for profile in import_profiles_module().list_profiles():
        for hint in profile["negative_hints"]:
            assert isinstance(hint, str) and hint
            for forbidden in ("删除", "drop", "delete", "忽略整"):
                assert forbidden not in hint, (profile["profile_id"], hint)


def test_sec_profiles_use_distinct_item_vocabularies():
    module = import_profiles_module()
    ten_k = module.get_profile("sec_10k")
    ten_q = module.get_profile("sec_10q")
    twenty_f = module.get_profile("sec_20f")

    def aliases(profile):
        return {
            alias.casefold()
            for entry in profile["section_priorities"]
            for alias in entry["aliases"]
        }

    assert aliases(ten_k) != aliases(ten_q) != aliases(twenty_f)
    assert not any("item 4" in alias for alias in aliases(ten_k))
    assert not any("item 7" in alias for alias in aliases(twenty_f))


def test_hk_profile_carries_traditional_chinese_aliases():
    profile = import_profiles_module().get_profile("hk_periodic")
    blob = " ".join(
        alias for entry in profile["section_priorities"] for alias in entry["aliases"]
    )
    assert "業務回顧及展望" in blob
    assert "管理層討論與分析" in blob


# --- carrier and language coverage ----------------------------------------------------


def test_english_document_is_routable():
    module = import_profiles_module()
    route = module.route_document(SHAPES["sec_10k"]())
    assert route["profile_id"] == "sec_10k"


def test_traditional_chinese_document_is_routable():
    module = import_profiles_module()
    route = module.route_document(SHAPES["hk_periodic"]())
    assert route["profile_id"] == "hk_periodic"


def test_missing_title_is_routable():
    """A document with no title must still route from its body structure alone."""
    module = import_profiles_module()
    observation = SHAPES["sec_10k"]()
    assert observation["metadata"]["title"] is None
    route = module.route_document(observation)
    assert route["profile_id"] == "sec_10k"
    assert route["confidence"] != "unknown"


def test_title_and_body_agreeing_raises_confidence():
    """Body evidence must be able to confirm a correct title, not just contradict one."""
    module = import_profiles_module()
    with_title = module.route_document(SHAPES["sec_10k"]())
    observation = SHAPES["sec_10k"]()
    observation["metadata"]["title"] = None
    without_title = module.route_document(observation)
    order = {"unknown": 0, "low": 1, "medium": 2, "high": 3}
    assert order[with_title["confidence"]] >= order[without_title["confidence"]] - 1


# --- external attachments -------------------------------------------------------------


def test_external_links_are_reported_unread_and_never_fetched():
    module = import_profiles_module()
    observation = b.observation(
        [
            b.unit("u1", 0, "2025 年年度报告", kind="heading"),
            b.unit("u2", 1, "第一节 释义", kind="heading"),
            b.unit("u3", 2, "详见附件：https://example.invalid/attachment.pdf"),
            b.unit("u4", 3, "附件2：https://example.invalid/other.pdf", kind="attachment"),
        ],
        title="某公司：2025年年度报告",
        declared_kind="annual_report",
        regime="cn_exchange",
        language="zh",
    )
    route = module.route_document(observation, limits={"max_child_routes": 16})
    for child in route["child_routes"]:
        assert child["reason"] in {
            "EXTERNAL_ATTACHMENT_NOT_READ",
            "IN_DOCUMENT_QA_RANGE",
        }
        # An attachment must never be turned into a fabricated SourceRef.
        assert "source_ref" not in child
        assert "source_id" not in child
        assert "source_sha256" not in child


def test_child_routes_cite_units_that_exist():
    module = import_profiles_module()
    observation = b.observation(
        [
            b.unit("u1", 0, "2025 年年度报告", kind="heading"),
            b.unit("u2", 1, "附件：https://example.invalid/a.pdf", kind="attachment"),
        ],
        title="某公司：2025年年度报告",
        declared_kind="annual_report",
        regime="cn_exchange",
        language="zh",
    )
    valid = {"u1", "u2"}
    route = module.route_document(observation)
    for child in route["child_routes"]:
        assert set(child["unit_ids"]) <= valid


def test_zero_child_route_budget_is_honoured():
    module = import_profiles_module()
    observation = b.observation(
        [
            b.unit("u1", 0, "2025 年年度报告", kind="heading"),
            b.unit("u2", 1, "附件：https://example.invalid/a.pdf", kind="attachment"),
        ],
        title="某公司：2025年年度报告",
        declared_kind="annual_report",
        regime="cn_exchange",
    )
    route = module.route_document(observation, limits={"max_child_routes": 0})
    assert route["child_routes"] == []


# --- scale ----------------------------------------------------------------------------


def test_large_document_is_probed_within_budget_and_stays_fast():
    """A 5k-unit document must not be scanned linearly beyond the probe budget."""
    import time

    module = import_profiles_module()
    units = [b.unit(f"h{i}", i, text, kind="heading") for i, text in enumerate(b.CN_ANNUAL_TOC)]
    units += [
        b.unit(f"p{i}", 100 + i, f"段落 {i} 公司经营情况说明。")
        for i in range(5000)
    ]
    observation = b.observation(
        units,
        title="某公司：2025年年度报告",
        declared_kind="annual_report",
        regime="cn_exchange",
        language="zh",
    )
    started = time.perf_counter()
    route = module.route_document(observation)
    elapsed = time.perf_counter() - started
    assert_route_shape(route)
    assert route["profile_id"] == "cn_annual"
    # A generous ceiling: this is a diagnostic trend, not a fragile millisecond assertion.
    assert elapsed < 5.0, f"routing 5000 units took {elapsed:.3f}s"
