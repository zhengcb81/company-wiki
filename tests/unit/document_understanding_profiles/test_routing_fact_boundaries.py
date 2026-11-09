from dataclasses import replace

import pytest

from company_wiki.document_understanding import profiles
from fixtures.document_understanding_profiles import builders as b


@pytest.mark.parametrize("title, lines, profile", [
    (None, ("See our annual report on Form 10-K filed with the Securities and Exchange Commission.",
            "For the three months ended March 31, we reported operating revenue."), "sec_10q"),
    ("半年度报告", ("2026 年半年度报告", "第三节 管理层讨论与分析"), "cn_interim"),
    ("Interim Report", ("中期報告 Interim Report", "業務回顧及展望"), "hk_periodic"),
    ("公开发行可转换公司债券募集说明书", ("可转换公司债券募集说明书", "项目投资计划"), "offering"),
    ("Results", ("Business Highlights", "We expanded production capacity."), "results_release"),
    ("董事会关于召开股东大会的会议通知", ("股东大会会议通知", "会议安排"), "administrative"),
])
def test_route_does_not_depend_on_the_language_of_diagnostic_explanations(monkeypatch, title, lines, profile):
    observation = b.observation([b.unit(str(index), index, line, kind="heading")
                                 for index, line in enumerate(lines)], title=title)
    before = profiles.route_document(observation)
    assert before["profile_id"] == profile
    detect_signals = profiles.detect_signals

    def neutral_wording(parsed):
        observed = detect_signals(parsed)
        for bucket in (observed.signals, observed.cover_signals, observed.toc_signals, observed.body_signals):
            bucket[:] = [replace(signal, detail="Observed source feature") for signal in bucket]
        return observed

    monkeypatch.setattr(profiles, "detect_signals", neutral_wording)
    after = profiles.route_document(observation)
    for key in ("schema_version", "profile_id", "profile_version", "regime", "family", "subtype",
                "form_type", "confidence", "alternatives", "disposition_hint"):
        assert after[key] == before[key]


@pytest.mark.parametrize("form_label", ["管理層討論與分析", "全球發售", "Business Highlights"])
def test_opaque_metadata_label_cannot_become_physical_filing_evidence(form_label):
    units = [b.unit("p1", 0, "FORM S-1", kind="heading"),
             b.unit("p2", 1, "Registration statement under the Securities Act of 1933.")]
    route = profiles.route_document(b.observation(units, form_type=form_label))
    assert (route["profile_id"], route["regime"], route["form_type"]) == ("prospectus", "sec", "S-1")


@pytest.mark.parametrize("mime", ["application/pdf", "text/html", "text/plain"])
def test_observed_cn_periodic_cover_is_independent_of_carrier(mime):
    route = profiles.route_document(b.observation([
        b.unit("cover", 0, "2026 年半年度报告", kind="heading"),
        b.unit("business", 1, "第三节 管理层讨论与分析", kind="heading"),
    ], mime_type=mime))
    assert (route["profile_id"], route["regime"], route["family"]) == ("cn_interim", "cn_exchange", "interim")


@pytest.mark.parametrize("regime", ["hkex", "sec", "cn_exchange", "unknown"])
def test_investor_qa_content_language_does_not_decide_its_market(regime):
    units = [b.unit(str(index), index, line, kind="heading" if index < 2 else "paragraph")
             for index, line in enumerate(b.CN_IR_QA)]
    route = profiles.route_document(b.observation(units, regime=regime, declared_kind="investor_relations",
                                                   mime_type="text/plain"))
    assert (route["profile_id"], route["regime"]) == ("investor_qa", regime)
    assert not any(reason["code"] == "REGIME_CONFLICT" for reason in route["reasons"])
