"""Reception regressions: composition, bounded coverage, purpose and source ranges."""
from __future__ import annotations

import copy

import pytest
from fixtures.document_understanding_profiles import builders as b

from company_wiki.document_understanding.profiles import get_profile, route_document
from company_wiki.document_understanding.profiles.model import SectionPriority, combine
from company_wiki.document_understanding.profiles.observation import parse_observation


def _obs(form, texts, **kw):
    return b.observation(
        [b.unit(f"u{i}", i, text, kind="heading" if i in (0, 2, 3, 4, 6) else "paragraph")
         for i, text in enumerate(texts)], form_type=form, mime_type="text/html", **kw)


def test_composed_aliases_retain_all_markets_and_last_priority_is_explicit():
    merged = combine(
        (SectionPriority("business", ("业务", "Business"), 3),),
        (SectionPriority("risk", ("风险",), 2), SectionPriority("business", ("業務", " business ".strip(), "Ｂｕｓｉｎｅｓｓ"), 1)),
    )
    assert [s.section_role for s in merged] == ["business", "risk"]
    assert merged[0].aliases == ("业务", "Business", "業務")
    assert merged[0].priority == 1


@pytest.mark.parametrize("profile_id", ["prospectus", "offering"])
def test_offering_profiles_retain_combined_english_and_traditional_aliases(profile_id):
    roles = {row["section_role"]: row for row in get_profile(profile_id)["section_priorities"]}
    assert {"所得款項用途", "future plans and use of proceeds"} <= set(roles["fundraising"]["aliases"])
    assert {"業務", "our business"} <= set(roles["business"]["aliases"])
    assert {"行業概覽", "industry overview"} <= set(roles["industry"]["aliases"])


def test_front_heavy_headings_cannot_starve_tail_or_plain_body():
    units = [b.unit(f"h{i}", i, f"目录项目 {i}", kind="heading") for i in range(300)]
    units += [b.unit(f"p{i}", 300+i, f"正文 {i}") for i in range(400)]
    units += [b.unit("tail", 700, "FORM F-1", kind="heading")]
    parsed = parse_observation(b.observation(units), {"max_probe_units": 12})
    ids = {u.unit_id for u in parsed.probes}
    assert "h0" in ids and "tail" in ids
    assert any(u.unit_id.startswith("p") for u in parsed.probes)
    assert len(parsed.probes) <= 12
    assert parsed.probe_limited


def test_character_budget_keeps_span_opportunity_and_never_reads_over_limit():
    observation = b.observation([b.unit("cover", 0, "C"*24, kind="heading"),
        b.unit("middle", 1, "经营情况"), b.unit("tail", 2, "FORM F-1", kind="heading")])
    before = copy.deepcopy(observation)
    parsed = parse_observation(observation, {"max_probe_chars": 30})
    assert "tail" in {u.unit_id for u in parsed.probes}
    assert sum(len(u.text) for u in parsed.probes) == parsed.probed_chars <= 30
    assert parsed.probe_limited and parsed.char_limited
    assert observation == before


@pytest.mark.parametrize("form", ["S-1", "F-1", "S-1/A", "F-1/A"])
def test_registration_form_keeps_issuer_business_and_offering_reading(form):
    route = route_document(_obs(form, [f"FORM {form}", "Registration Statement under the Securities Act of 1933",
        "PROSPECTUS", "Business", "Use of Proceeds", "We provide cloud software services."]))
    assert route["regime"] == "sec"
    assert route["family"] == "prospectus" and route["profile_id"] == "prospectus"
    assert route["disposition_hint"] == "read"
    assert "ipo" not in (route["subtype"] or "").casefold(), "A registration can be for resale; do not assert IPO"


@pytest.mark.parametrize("form", ["8-K", "6-K"])
def test_sec_current_report_container_has_complete_inline_attachment_ranges(form):
    observation = _obs(form, [f"FORM {form}", "Current report",
        "Item 2.02 Results of Operations and Financial Condition", "Exhibit 99.1",
        "Second Quarter Results", "Business Highlights", "We announced a new product offering.",
        "Exhibit 99.2", "Investor Presentation", "We expect the new site to open next year."])
    observation["units"][3]["kind"] = "attachment"
    observation["units"][7]["kind"] = "heading"
    route = route_document(observation)
    assert route["regime"] == "sec" and route["family"] == "unknown"
    assert route["profile_id"] == "generic" and "current_report" in route["subtype"]
    assert any(c["profile_id"] == "results_release" and c["unit_ids"] == ["u3", "u4", "u5", "u6"]
               for c in route["child_routes"])
    assert any(c["profile_id"] == "presentation" and c["unit_ids"] == ["u7", "u8", "u9"]
               for c in route["child_routes"])
    assert not any(c["reason"] == "EXTERNAL_ATTACHMENT_NOT_READ" for c in route["child_routes"])


def test_external_exhibit_link_does_not_claim_read_business_attachment():
    observation = _obs("8-K", ["FORM 8-K", "Current report", "Exhibit 99.1 https://example.invalid/results.html"])
    observation["units"][2]["kind"] = "external_link"
    route = route_document(observation)
    assert route["regime"] == "sec" and route["family"] == "unknown"
    assert route["child_routes"] == [{"unit_ids": ["u2"], "profile_id": "generic", "reason": "EXTERNAL_ATTACHMENT_NOT_READ"}]


def test_exhibit_mentioned_in_running_prose_creates_no_child_range():
    route = route_document(_obs("8-K", ["FORM 8-K", "Current report",
        "See Exhibit 99.1 for additional details on our business."]))
    assert not route["child_routes"]


def test_probe_gap_in_inline_attachment_is_not_reported_complete():
    texts = ["FORM 8-K", "Current report", "Exhibit 99.1", "Business Highlights"] + ["Business update" for _ in range(30)]
    route = route_document(_obs("8-K", texts), limits={"max_probe_units": 5})
    assert not any(c["reason"] == "IN_DOCUMENT_ATTACHMENT_RANGE" for c in route["child_routes"])
    assert any(r["code"] == "CHILD_RANGE_NOT_READ" for r in route["reasons"])


@pytest.mark.parametrize("title,revision,extent,expected_revision", [
    ("2025 年年度报告摘要（修订版）", None, "summary", "amended"),
    ("2025 年年度报告", "original", "full", "original"),
    ("2025 年年度报告", "supplement", "full", "supplement"),
    ("2025 年年度报告", None, "full", "unknown"),
])
def test_extent_and_revision_are_separate_additive_axes(title, revision, extent, expected_revision):
    route = route_document(b.observation([b.unit("cover", 0, title, kind="heading"),
        b.unit("body", 1, "第三节 管理层讨论与分析", kind="heading")], title=title, revision=revision))
    assert route["modifiers"] == {"extent": extent, "revision": expected_revision}
    assert route["family"] == "annual"


def test_body_summary_and_referred_amendment_do_not_modify_whole_document():
    route = route_document(_obs("10-K", ["FORM 10-K", "For the fiscal year ended 2025", "Item 1. Business",
        "Summary", "Item 7. Management's Discussion and Analysis", "Refer to the amended registration statement."]))
    assert route["modifiers"] == {"extent": "full", "revision": "unknown"}


def test_limited_probe_retains_strong_type_reason_and_distinct_coverage_diagnostic():
    observation = _obs("F-1", ["FORM F-1", "Registration Statement", "Business", "Use of Proceeds"] + ["x" for _ in range(50)])
    route = route_document(observation, limits={"max_probe_units": 4})
    assert route["profile_id"] == "prospectus" and route["confidence"] in {"low", "unknown"}
    assert any(r["code"] == "COVER_HEADING" and "F-1" in r["detail"] for r in route["reasons"])
    assert any(r["code"] == "ROUTE_PROBE_LIMIT" for r in route["reasons"])


@pytest.mark.parametrize("profile_id", ["prospectus", "offering"])
def test_issuer_business_profiles_cover_plain_sec_registration_section_names(profile_id):
    sections = {s["section_role"]: s for s in get_profile(profile_id)["section_priorities"]}
    assert "Business" in sections["business"]["aliases"]
    assert "Use of Proceeds" in sections["fundraising"]["aliases"]


def test_container_outer_form_wins_before_an_actual_form_inside_attachment():
    observation = _obs("8-K", ["FORM 8-K", "Current report", "Exhibit 99.1", "FORM 10-K",
        "Item 1. Business", "Operating update.", "Item 7. Management's Discussion and Analysis"])
    route = route_document(observation)
    assert route["regime"] == "sec" and "current_report_8k" == route["subtype"].removeprefix("sec_")
    assert route["family"] == "unknown"
    assert route["child_routes"][0]["profile_id"] == "sec_10k"


def test_metadata_current_container_is_not_erased_by_attachment_interim_period():
    route = route_document(_obs("8-K", ["Current report", "Exhibit 99.1", "Business Highlights",
        "For the three months ended June 30, 2026.", "See our annual report on Form 10-K for prior-year data."]))
    assert route["regime"] == "sec" and route["subtype"] == "sec_current_report_8k"
    assert route["family"] == "unknown"


def test_missing_native_page_inside_attachment_leaves_gap_instead_of_typed_complete_range():
    observation = _obs("8-K", ["FORM 8-K", "Current report", "Exhibit 99.1", "Business Highlights", "Operating update."])
    observation["units"][4]["kind"] = "paragraph"
    for unit, page in zip(observation["units"], [1, 1, 2, 2, 4]):
        unit["page"] = page
    observation["coverage"] = {"native_scan": "partial", "opaque_pages": [3], "deferred_pages": []}
    route = route_document(observation)
    assert not any(c["reason"] == "IN_DOCUMENT_ATTACHMENT_RANGE" for c in route["child_routes"])
    assert any(r["code"] == "CHILD_RANGE_NOT_READ" for r in route["reasons"])


def test_reference_cannot_masquerade_as_inline_attachment_boundary():
    observation = _obs("8-K", ["FORM 8-K", "Current report", "Exhibit 99.1", "Business Highlights", "Operating update."])
    observation["units"][4]["kind"] = "paragraph"
    observation["units"][2]["kind"] = "reference"
    route = route_document(observation)
    assert not any(c["reason"] == "IN_DOCUMENT_ATTACHMENT_RANGE" for c in route["child_routes"])


@pytest.mark.parametrize("title", ["首次公开发行股票招股说明书摘要（修订稿）", "招股章程摘要（修訂稿）"])
def test_prospectus_summary_and_revision_survive_independently(title):
    route = route_document(b.observation([b.unit("cover", 0, title, kind="heading")], title=title))
    assert route["modifiers"] == {"extent": "summary", "revision": "amended"}


def test_amended_form_token_in_title_and_metadata_has_same_lifecycle_axis():
    for form in ("10-K/A", "F-1/A"):
        route = route_document(_obs(form, [f"FORM {form}", "Business", "Operating update."]))
        assert route["modifiers"] == {"extent": "full", "revision": "amended"}



def test_character_clipping_does_not_turn_prose_into_a_self_identifying_form_label():
    observation = b.observation([b.unit("paragraph", 0,
        "FORM F-1 is one form discussed in the training notes, and this passage compares several instruments. " * 3)])
    route = route_document(observation, limits={"max_probe_chars": 18})
    assert route["profile_id"] == "generic" and route["family"] == "unknown"
    assert any(r["code"] == "ROUTE_PROBE_LIMIT" for r in route["reasons"])
