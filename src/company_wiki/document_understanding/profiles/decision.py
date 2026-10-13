"""Turn a signal bag into a ``du-route/1`` decision.

This is the only module that arbitrates between competing families. The order of
arbitration is the card's order:

1. administrative purpose wins before any family, because a confirmation letter can
   mention ``招股说明书`` in its own title and a director's report can mention ``年报``;
2. regime-specific form vocabulary decides the regime (SEC item numbers never decide an
   HK report, and vice versa);
3. document purpose (IPO vs. offering vs. plain periodic) refines the family;
4. when the evidence stays thin, the route degrades to ``generic`` with
   ``generic_read`` rather than guessing a specific family.

Every decision cites unit ids. Nothing here reads company names, security codes, file
paths or the clock.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from . import vocabulary as v
from .observation import Observation
from .signals import SignalBag, normalize


@dataclass
class Candidate:
    """A scored family/regime hypothesis with the evidence behind it."""

    profile_id: str
    family: str
    regime: str
    subtype: str | None
    score: int
    reasons: list[tuple[str, Sequence[str], str]] = field(default_factory=list)

    def to_wire_reasons(self) -> list[dict]:
        return [
            {
                "code": code,
                "unit_ids": list(dict.fromkeys(unit_ids)),
                "detail": detail[: v.MAX_REASON_DETAIL_CHARS],
            }
            for code, unit_ids, detail in self.reasons
        ]


def _has(bag: SignalBag, code: str) -> bool:
    return code in bag.codes()


def _units(bag: SignalBag, code: str) -> tuple[str, ...]:
    return bag.unit_ids_for(code)


def _detail_of(bag: SignalBag, code: str) -> str:
    for signal in bag.all:
        if signal.code == code:
            return signal.detail
    return code


def _any_unit(bag: SignalBag) -> tuple[str, ...]:
    for signal in bag.all:
        if signal.unit_ids:
            return signal.unit_ids
    return ()


def _administrative_candidate(observation: Observation, bag: SignalBag) -> Candidate | None:
    """Administrative purpose, decided before family assignment.

    One exception is deliberate. A *title* naming a policy is weak evidence: a real
    investor-relations activity record was observed whose stored file name says
    ``投资者关系管理制度`` while its body is an ``投资者关系活动记录表``. When the body
    carries observed question/answer structure, that structure is direct evidence about the
    document and outranks a policy-shaped title, so the Q&A family wins and the disagreement
    is still reported as a conflict.
    """
    if not _has(bag, v.REASON_ADMINISTRATIVE_PURPOSE):
        return None
    detail = _detail_of(bag, v.REASON_ADMINISTRATIVE_PURPOSE)
    lowered = detail.casefold()
    is_policy_shaped = "管理制度" in lowered or "管理办法" in lowered
    observed_qa = _has(bag, v.REASON_QA_STRUCTURE)
    if is_policy_shaped and observed_qa:
        return None

    unit_ids = _units(bag, v.REASON_ADMINISTRATIVE_PURPOSE) or _any_unit(bag)
    subtype = "administrative_material"
    if "确认意见" in lowered:
        subtype = "administrative_confirmation"
    elif "述职" in lowered:
        subtype = "administrative_director_report"
    elif is_policy_shaped or "制度" in lowered:
        subtype = "administrative_policy"
    elif "会议通知" in lowered or "关于召开" in lowered:
        subtype = "administrative_meeting_notice"
    return Candidate(
        profile_id="administrative",
        family="administrative",
        regime="unknown",
        subtype=subtype,
        score=100,
        reasons=[
            (v.REASON_ADMINISTRATIVE_PURPOSE, unit_ids, detail),
        ],
    )


def _regime_of(observation: Observation, bag: SignalBag) -> tuple[str, list[tuple[str, Sequence[str], str]]]:
    """Decide the regime from form vocabulary and structure, never from file location.

    Precedence follows ``design.md`` section 4: cover and section evidence outrank the
    metadata claim. An HK bilingual report whose ``form_type`` wrongly says ``10-K`` is
    therefore read as an HK report *and* reported as a metadata conflict, instead of the
    metadata silently winning.
    """
    reasons: list[tuple[str, Sequence[str], str]] = []
    sec_form = None
    hk_signal = False
    cn_signal = False

    details = " ".join(signal.detail for signal in bag.all)
    hk_structure = any(
        "港股" in signal.detail for signal in bag.toc_signals
    ) or _has_hk_structure(details)

    for signal in bag.cover_signals:
        detail = signal.detail
        if detail.startswith("SEC 表单"):
            sec_form = detail.split(":", 1)[-1].strip()
            reasons.append((v.REASON_COVER_HEADING, signal.unit_ids, detail))
        elif "港股" in detail or "全球发售" in detail:
            hk_signal = True
            reasons.append((v.REASON_COVER_HEADING, signal.unit_ids, detail))
        elif "A股" in detail or "再融资" in detail or "首次公开发行" in detail or "可转换" in detail:
            cn_signal = True
            reasons.append((v.REASON_COVER_HEADING, signal.unit_ids, detail))

    for signal in bag.toc_signals:
        if "10-K Item" in signal.detail or "10-Q Part I" in signal.detail or "20-F Item" in signal.detail:
            reasons.append((v.REASON_TOC_STRUCTURE, signal.unit_ids, signal.detail))
            sec_form = sec_form or signal.detail.split()[0]

    # Interim-period reporting language is SEC evidence even when the item header sits
    # outside the probed window.
    if sec_form is None and any(
        "SEC 中期期间报告措辞" in signal.detail for signal in bag.body_signals
    ):
        sec_form = "10-Q"
        reasons.append(
            (
                v.REASON_SECTION_VOCABULARY,
                _units(bag, v.REASON_SECTION_VOCABULARY),
                "SEC 中期期间报告措辞",
            )
        )

    # Structural evidence beats a metadata-only form claim.
    if hk_structure and not _has_sec_structure(details):
        return "hkex", reasons
    if sec_form:
        return "sec", reasons
    if hk_signal:
        return "hkex", reasons
    if cn_signal:
        return "cn_exchange", reasons

    declared = (observation.regime_claim or "unknown").casefold()
    if declared in v.REGIMES and declared != "unknown":
        return declared, reasons
    return "unknown", reasons


#: Section vocabulary that identifies an HK periodic report or offering.
_HK_STRUCTURE_VOCAB = (
    "業務回顧及展望",
    "管理層討論與分析",
    "財務表現摘要",
    "董事會報告",
    "企業管治報告",
    "獨立核數師報告",
    "全球發售",
    "行業概覽",
    "歷史及公司架構",
    "所得款項用途",
)

#: Section vocabulary that identifies an SEC filing's item structure.
_SEC_STRUCTURE_VOCAB = (
    "10-K Item",
    "10-Q Part I",
    "20-F Item",
    "item 1. business",
    "item 4. information on the company",
)


def _has_hk_structure(details: str) -> bool:
    folded = normalize(details)
    return any(normalize(token) in folded for token in _HK_STRUCTURE_VOCAB)


def _has_sec_structure(details: str) -> bool:
    folded = normalize(details)
    return any(normalize(token) in folded for token in _SEC_STRUCTURE_VOCAB)


def _sec_profile(observation: Observation, bag: SignalBag) -> Candidate | None:
    """Map a SEC form to its profile. Falls back to interim-period evidence.

    When the probed window never includes the form's item header, the document can still
    identify itself: a report that covers ``three months ended`` and refers back to its own
    ``annual report on Form 10-K`` is a quarterly report, not an annual one. That
    fallback is only used when no explicit form was found.
    """
    form = None
    for signal in bag.all:
        if signal.detail.startswith("SEC 表单"):
            form = signal.detail.split(":", 1)[-1].strip().casefold()
            break
    structural = " ".join(signal.detail for signal in bag.all)
    if form is None:
        if "20-F Item" in structural:
            form = "20-f"
        elif "10-Q Part I" in structural:
            form = "10-q"
        elif "10-K Item" in structural:
            form = "10-k"
        elif "SEC 中期期间报告措辞" in structural:
            form = "10-q"
    if form in {"s-1", "f-1"}:
        return Candidate(
            profile_id="prospectus", family="prospectus", regime="sec",
            subtype="sec_registration_" + form.replace("-", ""), score=80,
            reasons=[(v.REASON_COVER_HEADING, _units(bag, "COVER_HEADING"),
                      f"SEC 表单: {form.upper()}；注册发行用途，不推断首次上市")],
        )
    if form in {"8-k", "6-k"}:
        return Candidate(
            profile_id="generic", family="unknown", regime="sec",
            subtype="sec_current_report_" + form.replace("-", ""), score=90,
            reasons=[(v.REASON_COVER_HEADING, _units(bag, "COVER_HEADING"),
                      f"SEC 表单: {form.upper()}；保留容器，附件按实际同源范围阅读")],
        )
    mapping = {"10-k": "sec_10k", "10-q": "sec_10q", "20-f": "sec_20f"}
    if form not in mapping:
        return None
    profile_id = mapping[form]
    family = {"sec_10k": "annual", "sec_10q": "quarterly", "sec_20f": "annual"}[profile_id]
    reasons = [
        (v.REASON_COVER_HEADING, _units(bag, "COVER_HEADING"), f"SEC 表单: {form.upper()}"),
        (
            v.REASON_SECTION_VOCABULARY,
            _units(bag, "TOC_STRUCTURE") or _units(bag, v.REASON_SECTION_VOCABULARY),
            "SEC Item/期间结构证据",
        ),
    ]
    return Candidate(
        profile_id=profile_id,
        family=family,
        regime="sec",
        subtype=form,
        score=80 if "SEC 表单" in structural else 66,
        reasons=[reason for reason in reasons if reason[1]],
    )


def _hk_candidate(observation: Observation, bag: SignalBag) -> Candidate | None:
    """HK periodic vs. HK offering, decided from real bilingual vocabulary.

    Interim vs. annual is decided from every piece of evidence, not only the cover: a real
    interim report names itself ``2025中期報告``/``Interim Report`` on the cover OR in the
    TOC/first heading, and a reconstruction may only carry the latter.
    """
    offering = _offering_evidence(bag, hk=True)
    if offering:
        return Candidate(
            profile_id="prospectus",
            family="prospectus",
            regime="hkex",
            subtype="ipo_global_offering",
            score=75,
            reasons=offering,
        )
    periodic: list[tuple[str, Sequence[str], str]] = [
        (v.REASON_COVER_HEADING, _units(bag, "COVER_HEADING"), "港股定期报告措辞"),
        (v.REASON_TOC_STRUCTURE, _units(bag, "TOC_STRUCTURE"), "港股双语章节"),
    ]
    periodic = [reason for reason in periodic if reason[1]]

    evidence = normalize(
        " ".join(
            [observation.title or ""]
            + [signal.detail for signal in bag.all]
            + [unit.text for unit in observation.probes]
        )
    )
    interim_markers = ("interim report", "中期報告", "中期报告", "半年報", "半年报", "中期業績")
    annual_markers = ("annual report", "年報", "年报", "年度報告", "年度报告")

    if any(normalize(marker) in evidence for marker in interim_markers):
        return Candidate(
            profile_id="hk_periodic",
            family="interim",
            regime="hkex",
            subtype="hk_interim",
            score=70,
            reasons=periodic,
        )
    if any(normalize(marker) in evidence for marker in annual_markers):
        return Candidate(
            profile_id="hk_periodic",
            family="annual",
            regime="hkex",
            subtype="hk_annual",
            score=70,
            reasons=periodic,
        )
    return None


def _offering_evidence(bag: SignalBag, *, hk: bool) -> list[tuple[str, Sequence[str], str]]:
    evidence: list[tuple[str, Sequence[str], str]] = []
    offering_units: list[str] = []
    for signal in bag.all:
        detail = signal.detail
        is_hk = "全球发售" in detail or "招股章程" in detail
        is_cn = "再融资" in detail or "可转换" in detail or "首次公开发行" in detail
        if hk and is_hk:
            offering_units.extend(signal.unit_ids)
            evidence.append((v.REASON_COVER_HEADING, signal.unit_ids, detail))
        elif not hk and is_cn:
            offering_units.extend(signal.unit_ids)
            evidence.append((v.REASON_COVER_HEADING, signal.unit_ids, detail))
    for signal in bag.all:
        if signal.code == v.REASON_SECTION_VOCABULARY and "募投" in signal.detail:
            offering_units.extend(signal.unit_ids)
            evidence.append((v.REASON_SECTION_VOCABULARY, signal.unit_ids, signal.detail))
    return evidence


def _cn_candidate(observation: Observation, bag: SignalBag) -> Candidate | None:
    """A-share prospectus vs. offering, from cover wording *or* fundraising structure.

    A real offering document was observed whose first observed units are front matter
    (``发行人声明``/``特别提示``/``目录``/``第一节``) and whose only offering evidence is a
    later fundraising unit with the issue amount. Requiring cover wording alone routed it to
    the periodic family, so the fundraising-section evidence counts too.
    """
    details = " ".join(signal.detail for signal in bag.all)
    cover_units = _units(bag, "COVER_HEADING")
    fundraising_units = tuple(
        unit_id
        for signal in bag.all
        if signal.code == v.REASON_SECTION_VOCABULARY and "募投" in signal.detail
        for unit_id in signal.unit_ids
    )
    offering_reasons: list[tuple[str, Sequence[str], str]] = []
    if fundraising_units:
        offering_reasons.append(
            (v.REASON_SECTION_VOCABULARY, fundraising_units, "募投/所得款项章节")
        )

    if "可转换" in details:
        return Candidate(
            profile_id="offering",
            family="offering",
            regime="cn_exchange",
            subtype="convertible_bond",
            score=78,
            reasons=[
                (v.REASON_COVER_HEADING, cover_units, "可转换公司债券募集说明书"),
                *offering_reasons,
            ],
        )
    if "再融资" in details:
        return Candidate(
            profile_id="offering",
            family="offering",
            regime="cn_exchange",
            subtype="equity_offering",
            score=78,
            reasons=[
                (v.REASON_COVER_HEADING, cover_units, "向特定对象发行A股股票募集说明书"),
                *offering_reasons,
            ],
        )
    if "首次公开发行" in details or "招股" in details:
        return Candidate(
            profile_id="prospectus",
            family="prospectus",
            regime="cn_exchange",
            subtype="ipo",
            score=74,
            reasons=[
                (v.REASON_COVER_HEADING, cover_units, "首次公开发行/招股措辞"),
                *[
                    (v.REASON_TOC_STRUCTURE, signal.unit_ids, signal.detail)
                    for signal in bag.all
                    if signal.code == v.REASON_TOC_STRUCTURE
                ],
            ],
        )
    # Fundraising structure without any issue-type wording: still an offering document
    # rather than a periodic report, but with a lower score so explicit wording wins.
    if fundraising_units and _has(bag, v.REASON_TOC_STRUCTURE):
        return Candidate(
            profile_id="offering",
            family="offering",
            regime="cn_exchange",
            subtype="offering_unspecified",
            score=58,
            reasons=offering_reasons,
        )
    return None


def _cn_periodic_candidate(observation: Observation, bag: SignalBag) -> Candidate | None:
    """A-share periodic reports: annual / interim / quarterly.

    Reasons come from the cover/self-identification wording *and* the section numbering,
    because a real report may carry either without the other: the sampled 2025 annual
    report names itself on the cover, while a body-only excerpt may show only ``第三节``.
    """
    if _has(bag, "TXT_CARRIER") or _has(bag, "HTML_CARRIER"):
        return None
    # Fundraising structure (募集资金运用/募投项目/所得款项用途) marks an offering document,
    # not a periodic report. A real offering whose front matter is ``发行人声明``/``目录`` and
    # whose only offering evidence is a fundraising section must not fall into the periodic
    # family by default.
    if any(
        signal.code == v.REASON_SECTION_VOCABULARY and "募投" in signal.detail
        for signal in bag.all
    ) and not _has_periodic_self_identification(bag):
        return None
    structure: list[tuple[str, Sequence[str], str]] = [
        (v.REASON_COVER_HEADING, _units(bag, "COVER_HEADING"), _cover_detail(bag, "定期报告")),
        (v.REASON_TOC_STRUCTURE, _units(bag, "TOC_STRUCTURE"), "A股第N节章节编号"),
    ]
    cover_details = " ".join(signal.detail for signal in bag.cover_signals)
    body_details = " ".join(signal.detail for signal in bag.body_signals)
    combined = cover_details + " " + body_details
    section_units = _units(bag, v.REASON_SECTION_VOCABULARY)

    def reasons_for(detail: str) -> list[tuple[str, Sequence[str], str]]:
        listed: list[tuple[str, Sequence[str], str]] = [(code, ids, text) for code, ids, text in structure if ids]
        if not listed and section_units:
            listed.append(
                (v.REASON_SECTION_VOCABULARY, section_units, "A股章节结构与业务章节")
            )
        return listed or [
            (v.REASON_DECLARED_KIND_MATCH, _any_unit(bag), detail),
        ]

    if "季度报告" in combined:
        return Candidate(
            profile_id="cn_quarterly",
            family="quarterly",
            regime="cn_exchange",
            subtype="cn_quarterly_report",
            score=72,
            reasons=reasons_for("季度报告封面/标题"),
        )
    if "半年度报告" in combined:
        return Candidate(
            profile_id="cn_interim",
            family="interim",
            regime="cn_exchange",
            subtype="cn_semi_annual",
            score=72,
            reasons=reasons_for("半年度报告封面/标题"),
        )
    if "年度报告" in combined:
        return Candidate(
            profile_id="cn_annual",
            family="annual",
            regime="cn_exchange",
            subtype="cn_annual_report",
            score=72,
            reasons=reasons_for("年度报告封面/标题"),
        )
    if section_units:
        return Candidate(
            profile_id="cn_annual",
            family="annual",
            regime="cn_exchange",
            subtype="cn_periodic_unspecified",
            score=48,
            reasons=[
                (v.REASON_SECTION_VOCABULARY, section_units, "A股章节结构与业务章节"),
            ],
        )
    return None


def _has_periodic_self_identification(bag: SignalBag) -> bool:
    """True when the document names itself a periodic report.

    Used to protect a real A-share annual/interim/quarterly report that happens to include a
    fundraising section from being reclassified as an offering.
    """
    for signal in bag.cover_signals:
        if signal.code != "COVER_HEADING":
            continue
        if "定期报告" in signal.detail or "年度报告" in signal.detail or "半年度报告" in signal.detail or "季度报告" in signal.detail:
            return True
    return False


def _cover_detail(bag: SignalBag, fallback: str) -> str:
    for signal in bag.cover_signals:
        if signal.code == "COVER_HEADING" and "定期报告" not in signal.detail:
            return signal.detail
    return fallback


def _qa_candidate(observation: Observation, bag: SignalBag) -> Candidate | None:
    if not _has(bag, v.REASON_QA_STRUCTURE):
        return None
    ids = _units(bag, v.REASON_QA_STRUCTURE) or _any_unit(bag)
    return Candidate(
        profile_id="investor_qa",
        family="investor_qa",
        regime="cn_exchange" if any("\u4e00" <= ch <= "\u9fff" for ch in " ".join(
            unit.text for unit in observation.probes[:5]
        )) else "unknown",
        subtype="ir_activity_record",
        score=76,
        reasons=[(v.REASON_QA_STRUCTURE, ids, _detail_of(bag, v.REASON_QA_STRUCTURE))],
    )


def _call_candidate(observation: Observation, bag: SignalBag) -> Candidate | None:
    if not _has(bag, v.REASON_SPEAKER_TURNS):
        return None
    return Candidate(
        profile_id="earnings_call",
        family="earnings_call",
        regime="unknown",
        subtype="transcript",
        score=76,
        reasons=[
            (v.REASON_SPEAKER_TURNS, _units(bag, v.REASON_SPEAKER_TURNS), "发言轮次与角色")
        ],
    )


def _deck_candidate(observation: Observation, bag: SignalBag) -> Candidate | None:
    if not _has(bag, v.REASON_SLIDE_STRUCTURE):
        return None
    ids = _units(bag, v.REASON_SLIDE_STRUCTURE)
    return Candidate(
        profile_id="presentation",
        family="presentation",
        regime="unknown",
        subtype="results_deck",
        score=70,
        reasons=[(v.REASON_SLIDE_STRUCTURE, ids, "演示稿封面与指标页")],
    )


def _release_candidate(observation: Observation, bag: SignalBag) -> Candidate | None:
    details = " ".join(signal.detail for signal in bag.all)
    ids = _units(bag, v.REASON_SECTION_VOCABULARY) or _units(bag, "COVER_HEADING")
    if "业绩发布措辞" in details or "Business Highlights" in details:
        return Candidate(
            profile_id="results_release",
            family="results_release",
            regime="unknown",
            subtype="results_announcement",
            score=68,
            reasons=[(v.REASON_SECTION_VOCABULARY, ids, "业绩发布/要点措辞")],
        )
    return None


def _generic_candidate(observation: Observation, bag: SignalBag) -> Candidate:
    ids = _any_unit(bag)
    detail = "无足够类型特征，按通用来源策略保守阅读"
    reasons: list[tuple[str, Sequence[str], str]] = [(v.REASON_LOW_INFORMATION, ids, detail)]
    if observation.declared_kind and observation.declared_kind != "unknown":
        reasons.append(
            (
                v.REASON_DECLARED_KIND_MATCH,
                ids,
                f"declared_kind={observation.declared_kind} 未被正文证据支持",
            )
        )
    return Candidate(
        profile_id="generic",
        family="unknown",
        regime="unknown",
        subtype=None,
        score=10,
        reasons=reasons,
    )


def decide(observation: Observation, bag: SignalBag) -> Candidate:
    """Arbitrate a route. Order: administrative, then regime, then family, then generic."""
    administrative = _administrative_candidate(observation, bag)
    if administrative is not None:
        return administrative

    regime, regime_reasons = _regime_of(observation, bag)

    ordered: list[Candidate] = []
    if regime == "sec":
        sec = _sec_profile(observation, bag)
        if sec is not None:
            ordered.append(sec)
    elif regime == "hkex":
        hk = _hk_candidate(observation, bag)
        if hk is not None:
            ordered.append(hk)
    elif regime == "cn_exchange":
        for factory in (_cn_candidate, _cn_periodic_candidate, _qa_candidate, _call_candidate):
            candidate = factory(observation, bag)
            if candidate is not None:
                ordered.append(candidate)
    else:
        for factory in (
            _call_candidate,
            _deck_candidate,
            _release_candidate,
            _qa_candidate,
            _sec_profile,
            _cn_candidate,
            _cn_periodic_candidate,
        ):
            candidate = factory(observation, bag)
            if candidate is not None:
                ordered.append(candidate)

    # A Q&A / transcript *shape* may compete across regimes only when no regime-specific
    # filing form was actually established. `design.md` section 4 makes the cover and
    # section evidence the primary axis; a document that proves it is an HK report from its
    # bilingual section vocabulary must not lose to an incidental `Name:`-shape match. This
    # is a real observed failure: the 246-page HK annual report in the plan's sample set
    # carries 33 statement-footnote `Notes:` labels, and letting the transcript candidate
    # compete across regimes routed that annual report to `earnings_call`.
    if not _regime_is_structural(observation, bag):
        for factory in (_call_candidate, _qa_candidate, _deck_candidate, _release_candidate):
            candidate = factory(observation, bag)
            if candidate is not None and all(
                item.profile_id != candidate.profile_id for item in ordered
            ):
                ordered.append(candidate)

    if not ordered:
        generic = _generic_candidate(observation, bag)
        generic.reasons.extend(regime_reasons)
        return generic

    ordered.sort(key=lambda item: item.score, reverse=True)
    winner = ordered[0]
    if regime_reasons and not any(
        code == v.REASON_COVER_HEADING for code, _, _ in winner.reasons
    ):
        winner.reasons.extend(regime_reasons)
    return winner


def _regime_is_structural(observation: Observation, bag: SignalBag) -> bool:
    """True when the regime rests on a real filing form, not on an incidental shape.

    A cover/TOC signal that names the regime's own section vocabulary (``港股`` bilingual
    structure, an SEC form id, an A-share periodic cover) is structural evidence. When one
    is present *and it cites a unit that can serve as this document's own cover line*, the
    regime-specific periodic/offering candidate is authoritative and a cross-regime
    Q&A/transcript shape must not displace it.

    The unit check matters: ``See our Form 10-K Item 1A Risk Factors for details.`` inside a
    newsletter raises the same ``SEC 表单`` signal as a real 10-K cover, so the signal text
    alone cannot decide. Only units that pass ``is_title_evidence`` -- heading-like or short
    standalone lines that are not cross-references -- count as structural proof.
    """
    structural_details = " ".join(
        signal.detail for signal in (bag.cover_signals + bag.toc_signals)
    )
    if not structural_details:
        return False
    named_form = (
        any(
            token in structural_details
            for token in ("港股", "全球发售", "A股", "再融资", "首次公开发行", "可转换")
        )
        or "SEC 表单" in structural_details
        or "10-K Item" in structural_details
        or "10-Q Part I" in structural_details
        or "20-F Item" in structural_details
    )
    if not named_form:
        return False
    return _cites_title_evidence(observation, bag)


def _cites_title_evidence(observation: Observation, bag: SignalBag) -> bool:
    """True when a cover/TOC signal cites a unit that really is a cover/heading line."""
    from .signals import is_title_evidence

    by_id = {unit.unit_id: unit for unit in observation.units}
    for signal in bag.cover_signals + bag.toc_signals:
        for unit_id in signal.unit_ids:
            unit = by_id.get(unit_id)
            if unit is not None and is_title_evidence(unit):
                return True
    return False


__all__ = ["Candidate", "decide"]
