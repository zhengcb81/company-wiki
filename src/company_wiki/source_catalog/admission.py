"""Path-scoped admission and deterministic source processing priority."""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Any

from company_wiki.source_contract import SourceType


FOCUS_ROOT_ID = "dropbox_stock"
FOCUS_RELATIVE_PREFIX = "重点关注"

_PRIORITIES = {
    "prospectus": 10,
    "annual_report": 20,
    "semi_annual_report": 21,
    "regulatory_filing": 22,
    "investor_relations": 30,
    "investor_call_transcript": 40,
    "broker_research": 50,
    "quarterly_report": 60,
}

_SOURCE_TYPES = {
    "prospectus": SourceType.PROSPECTUS,
    "annual_report": SourceType.REGULATORY_FILING,
    "semi_annual_report": SourceType.REGULATORY_FILING,
    "quarterly_report": SourceType.REGULATORY_FILING,
    "regulatory_filing": SourceType.REGULATORY_FILING,
    "investor_relations": SourceType.INVESTOR_RELATIONS,
    "investor_call_transcript": SourceType.INVESTOR_RELATIONS,
    "broker_research": SourceType.BROKER_RESEARCH,
}

_PROSPECTUS_RE = re.compile(r"招股(?:说明书|书)|prospectus|ipo\s+filing", re.I)
_ANNUAL_RE = re.compile(
    r"年度报告|(?<!半)年报|annual\s+report|\b(?:10-k|20-f|40-f|10k|20f|40f)\b",
    re.I,
)
_SEMI_RE = re.compile(
    r"半年度报告|半年报|中期报告|interim\s+report|half[- ]year\s+report",
    re.I,
)
_QUARTERLY_RE = re.compile(
    r"季度报告|[一二三四]季报|第[一二三四]季度|quarterly\s+report|\b10-q\b",
    re.I,
)
_FINANCIAL_RE = re.compile(r"财务报告|financial\s+(?:report|statements)", re.I)
_ANNOUNCEMENT_RE = re.compile(
    r"公告|问询函|监管函|权益变动|减持公告|质押公告|处罚决定|立案调查",
    re.I,
)
_COMMENTARY_RE = re.compile(
    r"年报点评|半年报点评|季报点评|财报点评|年报解读|半年报解读|季报解读|"
    r"财报解读|季报复盘|财报复盘|财报摘要|年报摘要|半年报摘要|季报摘要|"
    r"annual\s+report\s+(?:review|commentary)|earnings\s+(?:review|commentary|recap)",
    re.I,
)
_CALL_RE = re.compile(
    r"电话会议(?:纪要|记录|实录)|业绩电话会|业绩会纪要|"
    r"earnings\s+call\s+(?:transcript|minutes)|conference\s+call\s+(?:transcript|minutes)",
    re.I,
)
_IR_RE = re.compile(
    r"投资者关系|投资者调研|机构调研|调研纪要|路演|业绩说明会|"
    r"investor\s+relations?|investor\s+(?:presentation|day)",
    re.I,
)
_BROKER_INSTITUTION_RE = re.compile(
    r"证券(?:股份|有限责任|有限公司)?|证券研究所|研究院|研究部|"
    r"中信建投|中金公司|国泰君安|国泰海通|申万宏源|"
    r"(?:中信|华泰|海通|广发|招商|天风|国信|中泰|浙商|兴业|长江|"
    r"光大|东吴|国金|方正|民生|财通|开源|德邦|华创|首创|银河)(?:证券)?|"
    r"goldman\s+sachs|morgan\s+stanley|j\.?p\.?\s*morgan|ubs|"
    r"bank\s+of\s+america|citigroup|securities|capital\s+markets",
    re.I,
)
_BROKER_REPORT_RE = re.compile(
    r"深度报告|公司研究|行业研究|首次覆盖|跟踪报告|点评报告|年报点评|"
    r"半年报点评|季报点评|研究报告|研报|投资评级|目标价|"
    r"equity\s+research|research\s+report|initiat(?:e|ing)\s+coverage",
    re.I,
)


@dataclass(frozen=True)
class AdmissionDecision:
    admitted: bool
    document_kind: str | None
    source_type: SourceType | None
    priority: int
    reason: str
    evidence: tuple[str, ...] = ()


def processing_priority(document_kind: str) -> int:
    return _PRIORITIES.get(str(document_kind).strip().casefold(), 1000)


def processing_priority_sql(alias: str = "d") -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", alias):
        raise ValueError("SQL alias must be a simple identifier")
    column = f"{alias}.document_kind"
    clauses = " ".join(
        f"WHEN '{kind}' THEN {priority}" for kind, priority in _PRIORITIES.items()
    )
    return f"CASE {column} {clauses} ELSE 1000 END"


def _normalized_relative_path(value: str) -> str:
    normalized = unicodedata.normalize("NFC", str(value).replace("\\", "/"))
    return "/".join(part for part in normalized.split("/") if part not in ("", "."))


def _decision(kind: str, reason: str, *evidence: str) -> AdmissionDecision:
    return AdmissionDecision(
        admitted=True,
        document_kind=kind,
        source_type=_SOURCE_TYPES[kind],
        priority=processing_priority(kind),
        reason=reason,
        evidence=tuple(evidence),
    )


def _rejected(reason: str, *evidence: str) -> AdmissionDecision:
    return AdmissionDecision(False, None, None, 1000, reason, tuple(evidence))


def evaluate_admission(
    *, root_id: str, relative_path: str, metadata: dict[str, Any]
) -> AdmissionDecision | None:
    """Return a decision only for the exact Dropbox ``重点关注`` subtree."""
    relative = _normalized_relative_path(relative_path)
    parts = relative.split("/") if relative else []
    if root_id != FOCUS_ROOT_ID or not parts or parts[0] != FOCUS_RELATIVE_PREFIX:
        return None
    if any(part == ".." for part in parts):
        return _rejected("focus_policy_invalid_relative_path", "path_traversal")

    explicit_kind = str(metadata.get("document_kind") or "").strip().casefold()
    if explicit_kind:
        if explicit_kind == "regulatory_filing":
            # Blocker 1: a generic regulatory_filing declaration is NOT enough.
            # Only explicit financial report forms/titles may admit; otherwise
            # fall through to evidence-based analysis below.
            pass
        elif explicit_kind in _SOURCE_TYPES:
            return _decision(
                explicit_kind,
                "focus_policy_explicit_document_kind",
                f"document_kind={explicit_kind}",
            )
        else:
            return _rejected(
                "focus_policy_explicit_kind_not_allowed",
                f"document_kind={explicit_kind}",
            )

    form_type = str(metadata.get("form_type") or "").strip()
    title = str(metadata.get("source_title") or "").strip()
    text = " ".join((relative, title, form_type))
    folded_form = form_type.casefold()

    if _ANNOUNCEMENT_RE.search(text):
        return _rejected(
            "focus_policy_announcement_or_notice",
            "announcement_or_regulatory_notice",
        )
    if _PROSPECTUS_RE.search(text):
        return _decision("prospectus", "focus_policy_prospectus_keyword", "prospectus")
    if _CALL_RE.search(text):
        return _decision(
            "investor_call_transcript",
            "focus_policy_call_transcript_keyword",
            "call_transcript",
        )
    if _BROKER_INSTITUTION_RE.search(text) and _BROKER_REPORT_RE.search(text):
        return _decision(
            "broker_research",
            "focus_policy_strict_broker_evidence",
            "broker_institution",
            "research_report_semantics",
        )
    if _COMMENTARY_RE.search(text):
        # Blocker 2: commentary without strict broker evidence must fail closed
        # instead of falling through to annual/semi/quarterly keywords.
        return _rejected(
            "focus_policy_commentary_without_broker_evidence",
            "commentary_or_recap",
        )
    if folded_form in {"10-k", "20-f", "40-f", "10k", "20f", "40f"}:
        return _decision("annual_report", "focus_policy_regulatory_form", form_type)
    # dayu portfolio form_type codes (FY/H1) — the portfolio meta.json carries
    # these; titles are Traditional Chinese (年報 / 中期報告) which the keyword
    # regexes below do not match (ADR-008 Strategy B).
    if folded_form in {"fy"}:
        return _decision("annual_report", "focus_policy_regulatory_form", form_type)
    if folded_form in {"h1", "h2"}:
        return _decision("semi_annual_report", "focus_policy_regulatory_form", form_type)
    if _SEMI_RE.search(text):
        return _decision(
            "semi_annual_report", "focus_policy_semi_annual_keyword", "semi_annual"
        )
    if folded_form in {"10-q", "q1", "q2", "q3", "q4"} or _QUARTERLY_RE.search(text):
        return _decision(
            "quarterly_report", "focus_policy_quarterly_keyword", "quarterly"
        )
    if _ANNUAL_RE.search(text):
        return _decision("annual_report", "focus_policy_annual_keyword", "annual")
    if _FINANCIAL_RE.search(text):
        return _decision(
            "regulatory_filing",
            "focus_policy_financial_report_keyword",
            "financial_report",
        )
    if _IR_RE.search(text):
        return _decision(
            "investor_relations",
            "focus_policy_investor_relations_keyword",
            "investor_relations",
        )
    return _rejected("focus_policy_no_allowed_category_evidence")


__all__ = [
    "AdmissionDecision",
    "FOCUS_RELATIVE_PREFIX",
    "FOCUS_ROOT_ID",
    "evaluate_admission",
    "processing_priority",
    "processing_priority_sql",
]


# WU-503: root-agnostic admission profile evaluation.  The SAME candidate
# evaluated under different root_ids yields the SAME decision; only RootPolicy
# authorization flags change the outcome (ADM-01..10).  No root name ever
# appears in the decision path.

def evaluate_candidate(
    candidate: dict,
    *,
    policy_allows_filing: bool,
    profile_allows_filing: bool,
    content_hash_matches: bool,
    status: str = "active",
) -> AdmissionDecision:
    """Fail-closed admission over candidate facts + policy/profile flags."""
    reasons: list[str] = []
    if not candidate.get("canonical_entity_id") or not candidate.get("security_id"):
        reasons.append("identity_missing")
    if not candidate.get("document_kind"):
        reasons.append("kind_missing")
    if not candidate.get("fiscal_year") or not candidate.get("period_end"):
        reasons.append("period_missing")
    if not candidate.get("content_sha256"):
        reasons.append("hash_missing")
    if not content_hash_matches:
        reasons.append("content_hash_mismatch")
    if status != "active":
        reasons.append("status_not_active")
    if not policy_allows_filing:
        reasons.append("policy_denied")
    if not profile_allows_filing:
        reasons.append("non_filing_kind")
    if reasons:
        return _rejected("|".join(reasons), *reasons)
    return _decision(
        str(candidate["document_kind"]),
        "v2_profile_admitted",
        "candidate_facts",
    )
