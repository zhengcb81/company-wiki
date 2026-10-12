"""Fixed typed CaseSpecs for the W08-CWP-G2-REPLAY offline package.

The card fixes the required document-type coverage.  These specs are the
*expectation* side of the run: a run record may report what happened, and the
oracle judges it, but a run may never rewrite what the card requires.

Document types covered (card section 2):

- annual report (PDF, narrative prose + financial table + boilerplate)
- half-year report (PDF)
- quarterly report (PDF)
- prospectus / 招股说明书 (PDF, financial prose)
- placement (增发) and convertible bond (可转债) -- one CaseSpec *group*, but
  each typed request is actually executed
- investor relations policy (PDF, no valuable operating information)
- original-language TXT earnings call (transcript bytes; no PDF conversion)

Everything here is synthetic.  ``synthetic``-style identity markers are part of
the fixed truth so that no downstream consumer can mistake these bytes for a
real company filing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# The fixed fixture company.  Deliberately not a real listed company name.
FIXTURE_ENTITY_ID = "ent-w08-synthetic-manufacturing"
FIXTURE_DISPLAY_NAME = "W08 Synthetic Manufacturing Co."
FIXTURE_SECURITY_ID = "W08SYN"

# Expected *outcome class* per case.  This is the card's fixed expectation:
#   narrative  -- business content is locatable and must reach a summary
#   skip       -- pure financial table / boilerplate: explicit skip, no summary
#   typed_only -- the run must preserve document_kind; narrative not asserted
EXPECT_NARRATIVE = "narrative"
EXPECT_SKIP = "skip"
EXPECT_TYPED_ONLY = "typed_only"

STATUS_PASS = "PASS"
STATUS_PARTIAL = "PARTIAL"
STATUS_FAIL = "FAIL"
STATUS_UNKNOWN = "UNKNOWN"
STATUS_NOT_RUN = "NOT_RUN"


@dataclass(frozen=True)
class CaseSpec:
    """One typed case.  ``case_id`` is the stable public identifier."""

    case_id: str
    group_id: str
    document_kind: str
    source_class: str
    language: str
    mime_type: str
    filename: str
    fixture_key: str
    expectation: str
    #: typed batch request must actually execute for this case
    typed_request: bool = True
    #: narrative claim that must be locatable in the synthetic original
    required_span_text: str | None = None
    #: boilerplate/financial text that must NOT become the whole summary
    forbidden_summary_text: tuple[str, ...] = ()
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "group_id": self.group_id,
            "document_kind": self.document_kind,
            "source_class": self.source_class,
            "language": self.language,
            "mime_type": self.mime_type,
            "filename": self.filename,
            "fixture_key": self.fixture_key,
            "expectation": self.expectation,
            "typed_request": self.typed_request,
            "required_span_text": self.required_span_text,
            "forbidden_summary_text": list(self.forbidden_summary_text),
            "notes": self.notes,
        }


# --------------------------------------------------------------------------
# Fixed expectations, straight from the construction card.  Keyed by case_id.
# --------------------------------------------------------------------------

FIXED_EXPECTATIONS: dict[str, dict[str, Any]] = {
    "annual-report": {
        "expectation": EXPECT_NARRATIVE,
        "document_kind_preserved": "annual_report",
        "requires_summary": True,
        "language": "zh",
    },
    "half-year-report": {
        "expectation": EXPECT_NARRATIVE,
        "document_kind_preserved": "semi_annual_report",
        "requires_summary": True,
        "language": "zh",
    },
    "quarterly-report": {
        "expectation": EXPECT_NARRATIVE,
        "document_kind_preserved": "quarterly_report",
        "requires_summary": True,
        "language": "zh",
    },
    "prospectus": {
        "expectation": EXPECT_NARRATIVE,
        "document_kind_preserved": "prospectus",
        "requires_summary": True,
        "language": "zh",
    },
    "placement": {
        "expectation": EXPECT_TYPED_ONLY,
        "document_kind_preserved": "equity_offering_prospectus",
        "requires_summary": False,
        "language": "zh",
    },
    "convertible-bond": {
        "expectation": EXPECT_TYPED_ONLY,
        "document_kind_preserved": "convertible_bond_prospectus",
        "requires_summary": False,
        "language": "zh",
    },
    "ir-policy": {
        "expectation": EXPECT_SKIP,
        # The catalog records the scanner's kind (investor_relations); the
        # selector routes the *title* to ir_policy and skips an empty result.
        # Both are real and distinct, so both are pinned here rather than
        # collapsing them into one field.
        "document_kind_preserved": "investor_relations",
        "routed_kind": "ir_policy",
        "requires_summary": False,
        "skip_expected": "skipped_no_narrative",
        "language": "zh",
    },
    "call-txt-zh": {
        "expectation": EXPECT_NARRATIVE,
        "document_kind_preserved": "investor_call_transcript",
        "requires_summary": True,
        "language": "zh",
        "transcript_must_stay_txt": True,
    },
    "call-txt-en": {
        "expectation": EXPECT_NARRATIVE,
        "document_kind_preserved": "investor_call_transcript",
        "requires_summary": True,
        "language": "en",
        "transcript_must_stay_txt": True,
    },
}

#: CaseSpec groups.  Placement and convertible bond share one group (the card
#: allows that) but each keeps its own typed request and its own case_id.
CASE_GROUPS: dict[str, tuple[str, ...]] = {
    "periodic-filings": ("annual-report", "half-year-report", "quarterly-report"),
    "offering-documents": ("prospectus", "placement", "convertible-bond"),
    "non-narrative": ("ir-policy",),
    "original-language-calls": ("call-txt-zh", "call-txt-en"),
}

#: At least two distinct container formats must appear in one batch (card
#: section C): PDF filings plus plain-text transcripts.
REQUIRED_FORMATS = ("application/pdf", "text/plain")


def case_specs() -> tuple[CaseSpec, ...]:
    """The fixed CaseSpec matrix.  Order is part of the contract."""
    return (
        CaseSpec(
            case_id="annual-report",
            group_id="periodic-filings",
            document_kind="annual_report",
            source_class="filing",
            language="zh",
            mime_type="application/pdf",
            filename="w08-annual-report-2025.pdf",
            fixture_key="annual_report",
            expectation=EXPECT_NARRATIVE,
            required_span_text="公司新建产线已完成客户认证并进入批量交付",
            forbidden_summary_text=("本报告经审计", "单位：人民币元"),
            notes="narrative prose plus a financial table and audit boilerplate",
        ),
        CaseSpec(
            case_id="half-year-report",
            group_id="periodic-filings",
            document_kind="semi_annual_report",
            source_class="filing",
            language="zh",
            mime_type="application/pdf",
            filename="w08-half-year-report-2026h1.pdf",
            fixture_key="half_year_report",
            expectation=EXPECT_NARRATIVE,
            required_span_text="海外子公司新增产能已于本期投产",
            forbidden_summary_text=("未经审计", "单位：人民币元"),
        ),
        CaseSpec(
            case_id="quarterly-report",
            group_id="periodic-filings",
            document_kind="quarterly_report",
            source_class="filing",
            language="zh",
            mime_type="application/pdf",
            filename="w08-quarterly-report-2026q1.pdf",
            fixture_key="quarterly_report",
            expectation=EXPECT_NARRATIVE,
            required_span_text="新一代产品已通过主要客户验证",
            forbidden_summary_text=("单位：人民币元",),
        ),
        CaseSpec(
            case_id="prospectus",
            group_id="offering-documents",
            document_kind="prospectus",
            source_class="filing",
            language="zh",
            mime_type="application/pdf",
            filename="w08-prospectus.pdf",
            fixture_key="prospectus",
            expectation=EXPECT_NARRATIVE,
            required_span_text="募集资金将用于扩建生产线及补充流动资金",
            forbidden_summary_text=("重要提示",),
        ),
        CaseSpec(
            case_id="placement",
            group_id="offering-documents",
            document_kind="equity_offering_prospectus",
            source_class="filing",
            language="zh",
            mime_type="application/pdf",
            filename="w08-placement.pdf",
            fixture_key="placement",
            expectation=EXPECT_TYPED_ONLY,
            forbidden_summary_text=(),
            notes="shares one group with convertible-bond; typed request still runs",
        ),
        CaseSpec(
            case_id="convertible-bond",
            group_id="offering-documents",
            document_kind="convertible_bond_prospectus",
            source_class="filing",
            language="zh",
            mime_type="application/pdf",
            filename="w08-convertible-bond.pdf",
            fixture_key="convertible_bond",
            expectation=EXPECT_TYPED_ONLY,
            forbidden_summary_text=(),
            notes="shares one group with placement; typed request still runs",
        ),
        CaseSpec(
            case_id="ir-policy",
            group_id="non-narrative",
            document_kind="investor_relations",
            source_class="filing",
            language="zh",
            mime_type="application/pdf",
            filename="投资者关系管理办法（2025年8月）.pdf",
            fixture_key="ir_policy",
            expectation=EXPECT_SKIP,
            forbidden_summary_text=(),
            notes="format boilerplate only; must skip with no summary and no model call",
        ),
        CaseSpec(
            case_id="call-txt-zh",
            group_id="original-language-calls",
            document_kind="investor_call_transcript",
            source_class="transcript",
            language="zh",
            mime_type="text/plain",
            filename="w08-call-zh.txt",
            fixture_key="call_zh",
            expectation=EXPECT_NARRATIVE,
            required_span_text="公司完成海外产能扩张",
            forbidden_summary_text=(),
            notes="original-language TXT; SHA and language must not change",
        ),
        CaseSpec(
            case_id="call-txt-en",
            group_id="original-language-calls",
            document_kind="investor_call_transcript",
            source_class="transcript",
            language="en",
            mime_type="text/plain",
            filename="w08-call-en.txt",
            fixture_key="call_en",
            expectation=EXPECT_NARRATIVE,
            required_span_text="We expanded overseas capacity",
            forbidden_summary_text=(),
            notes="original-language TXT; must not be converted to PDF",
        ),
    )


def required_case_ids() -> tuple[str, ...]:
    return tuple(spec.case_id for spec in case_specs())


def spec_by_id(case_id: str) -> CaseSpec:
    for spec in case_specs():
        if spec.case_id == case_id:
            return spec
    raise KeyError(case_id)


def coverage_report(executed_ids: tuple[str, ...]) -> dict[str, Any]:
    """Expected vs actually executed IDs; missing/unknown are never PASS."""
    expected = required_case_ids()
    executed = tuple(dict.fromkeys(executed_ids))
    return {
        "required_case_ids": list(expected),
        "executed_case_ids": list(executed),
        "missing_case_ids": [c for c in expected if c not in executed],
        "unknown_case_ids": [c for c in executed if c not in expected],
        "group_coverage": {
            group: {
                "required": list(ids),
                "missing": [c for c in ids if c not in executed],
            }
            for group, ids in CASE_GROUPS.items()
        },
    }
