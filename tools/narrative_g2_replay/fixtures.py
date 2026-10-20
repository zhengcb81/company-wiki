"""Synthetic original documents for the W08-CWP-G2-REPLAY package.

Every byte here is synthetic and is generated locally.  Nothing is copied from
the production data lake, and no real company identity is claimed.

The content is deliberately sized so the *binding* is checkable:

- each narrative document carries one explicit, quotable operating fact, so a
  locatable span exists and ``required_span_text`` can be asserted to reach the
  selected evidence;
- each financial document carries a genuine financial table plus format
  boilerplate, so a selector that returns table/boilerplate prose instead of
  operating narrative is visible;
- the IR policy carries *only* boilerplate, so an explicit skip is the correct
  outcome.

These are text-layer PDFs (or plain TXT for transcripts) written through the
project's real parsers.  No format is faked: TXT stays TXT.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------------------------------
# plain-text originals (transcripts) -- must stay TXT, never converted to PDF
# --------------------------------------------------------------------------

CALL_ZH_TEXT = (
    "Full Conference Call Transcript\n"
    "W08 Synthetic Manufacturing Co. 2026 Q1 earnings call\n"
    "CEO: 公司完成海外产能扩张，新产品已完成客户认证并进入量产。\n"
    "CFO: 本季度营业收入为人民币12.4亿元，毛利率为31.2%。\n"
    "Analyst: 请问新产线的爬坡节奏如何？\n"
    "CEO: 新产线预计在下半年达到设计产能。\n"
)

CALL_EN_TEXT = (
    "Full Conference Call Transcript\n"
    "W08 Synthetic Manufacturing Co. 2026 Q1 earnings call\n"
    "CEO: We expanded overseas capacity and the new product completed "
    "customer qualification.\n"
    "CFO: Revenue for the quarter was RMB 1.24 billion with a 31.2% gross "
    "margin.\n"
    "Analyst: How fast will the new line ramp?\n"
    "CEO: The new line should reach designed capacity in the second half.\n"
)

# --------------------------------------------------------------------------
# PDF page text
# --------------------------------------------------------------------------

ANNUAL_REPORT_PAGES = (
    (
        "W08 Synthetic Manufacturing Co. Annual Report 2025\n"
        "第三节 管理层讨论与分析\n"
        "公司新建产线已完成客户认证并进入批量交付，产能利用率环比提升。\n"
        "公司持续投入研发，报告期内新增专利二十项。\n"
    ),
    (
        "第四节 财务数据\n"
        "单位：人民币元\n"
        "营业收入 1,240,000,000\n"
        "营业成本 852,000,000\n"
        "毛利率 31.2%\n"
        "本报告经审计，审计意见为标准无保留意见。\n"
    ),
)

HALF_YEAR_REPORT_PAGES = (
    (
        "W08 Synthetic Manufacturing Co. 2026年半年度报告\n"
        "第二节 经营情况讨论与分析\n"
        "海外子公司新增产能已于本期投产，主要客户订单保持稳定。\n"
    ),
    (
        "第三节 财务数据\n"
        "单位：人民币元\n"
        "营业收入 680,000,000\n"
        "净利润 92,000,000\n"
        "未经审计。\n"
    ),
)

QUARTERLY_REPORT_PAGES = (
    (
        "W08 Synthetic Manufacturing Co. 2026年第一季度报告\n"
        "第一节 主要经营情况\n"
        "新一代产品已通过主要客户验证，预计下半年开始贡献收入。\n"
    ),
    (
        "第二节 主要财务数据\n"
        "单位：人民币元\n"
        "营业收入 310,000,000\n"
        "归属于上市公司股东的净利润 41,000,000\n"
    ),
)

PROSPECTUS_PAGES = (
    (
        "W08 Synthetic Manufacturing Co. 招股说明书\n"
        "重要提示\n"
        "本招股说明书的目的仅为向公众提供有关本次发行的简要情况。\n"
    ),
    (
        "第五节 募集资金运用\n"
        "募集资金将用于扩建生产线及补充流动资金，项目建成后年产能提升。\n"
        "项目建设期为二十四个月。\n"
    ),
    (
        "第六节 财务会计信息\n"
        "单位：人民币元\n"
        "营业收入 1,180,000,000\n"
        "资产负债率 42.5%\n"
    ),
)

PLACEMENT_PAGES = (
    (
        "W08 Synthetic Manufacturing Co. 向特定对象发行股票募集说明书\n"
        "重要提示\n"
        "本次发行尚需取得相关批准。\n"
    ),
    (
        "第二节 发行方案\n"
        "本次向特定对象发行股票数量不超过一亿股，募集资金用于产线建设。\n"
        "单位：人民币元\n"
        "募集资金总额 1,500,000,000\n"
    ),
)

CONVERTIBLE_BOND_PAGES = (
    (
        "W08 Synthetic Manufacturing Co. 可转换公司债券募集说明书\n"
        "重要提示\n"
        "本次发行的可转债不提供担保。\n"
    ),
    (
        "第三节 发行条款\n"
        "本次可转债募集资金用于扩建生产线，债券期限为六年。\n"
        "单位：人民币元\n"
        "发行规模 800,000,000\n"
    ),
)

IR_POLICY_PAGES = (
    (
        "W08 Synthetic Manufacturing Co. 投资者关系管理办法\n"
        "第一章 总则\n"
        "为规范公司投资者关系管理工作，保护投资者合法权益，制定本办法。\n"
        "第二章 职责分工\n"
        "公司董事会秘书负责投资者关系管理的日常事务，证券部负责具体执行。\n"
    ),
    (
        "第三章 投资者说明会\n"
        "公司应当在不晚于年度报告披露后召开业绩说明会，并提前公告。\n"
        "第四章 附则\n"
        "本办法由公司董事会负责解释，自发布之日起施行。\n"
    ),
)


# --------------------------------------------------------------------------
# fixture truth
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class FixtureDoc:
    key: str
    filename: str
    mime_type: str
    document_kind: str
    source_class: str
    language: str
    fiscal_year: int
    fiscal_period: str
    period_end: str
    filing_date: str
    pages: tuple[str, ...] = ()
    text_bytes: bytes | None = None

    @property
    def is_transcript(self) -> bool:
        return self.source_class == "transcript"


def fixture_docs() -> dict[str, FixtureDoc]:
    """Fixed fixture truth, keyed by fixture_key (never rewritten at runtime)."""
    return {
        "annual_report": FixtureDoc(
            "annual_report", "w08-annual-report-2025.pdf", "application/pdf",
            "annual_report", "filing", "zh", 2025, "FY", "2025-12-31", "2026-04-20",
            pages=ANNUAL_REPORT_PAGES,
        ),
        "half_year_report": FixtureDoc(
            "half_year_report", "w08-half-year-report-2026h1.pdf", "application/pdf",
            "semi_annual_report", "filing", "zh", 2026, "H1", "2026-06-30",
            "2026-08-20", pages=HALF_YEAR_REPORT_PAGES,
        ),
        "quarterly_report": FixtureDoc(
            "quarterly_report", "w08-quarterly-report-2026q1.pdf", "application/pdf",
            "quarterly_report", "filing", "zh", 2026, "Q1", "2026-03-31",
            "2026-04-28", pages=QUARTERLY_REPORT_PAGES,
        ),
        "prospectus": FixtureDoc(
            "prospectus", "w08-prospectus.pdf", "application/pdf",
            "prospectus", "filing", "zh", 2026, "FY", "2026-06-30", "2026-07-15",
            pages=PROSPECTUS_PAGES,
        ),
        "placement": FixtureDoc(
            "placement", "w08-placement.pdf", "application/pdf",
            "equity_offering_prospectus", "filing", "zh", 2026, "FY",
            "2026-06-30", "2026-07-20", pages=PLACEMENT_PAGES,
        ),
        "convertible_bond": FixtureDoc(
            "convertible_bond", "w08-convertible-bond.pdf", "application/pdf",
            "convertible_bond_prospectus", "filing", "zh", 2026, "FY",
            "2026-06-30", "2026-07-22", pages=CONVERTIBLE_BOND_PAGES,
        ),
        "ir_policy": FixtureDoc(
            "ir_policy", "投资者关系管理办法（2025年8月）.pdf", "application/pdf",
            "ir_policy", "filing", "zh", 2026, "FY", "2026-06-30", "2026-06-30",
            pages=IR_POLICY_PAGES,
        ),
        "call_zh": FixtureDoc(
            "call_zh", "w08-call-zh.txt", "text/plain",
            "investor_call_transcript", "transcript", "zh", 2026, "Q1",
            "2026-03-31", "2026-05-02",
            text_bytes=CALL_ZH_TEXT.encode("utf-8"),
        ),
        "call_en": FixtureDoc(
            "call_en", "w08-call-en.txt", "text/plain",
            "investor_call_transcript", "transcript", "en", 2026, "Q1",
            "2026-03-31", "2026-05-02",
            text_bytes=CALL_EN_TEXT.encode("utf-8"),
        ),
    }


def pdf_bytes(pages: tuple[str, ...]) -> bytes:
    """Render a real text-layer PDF through PyMuPDF; no format is simulated."""
    import pymupdf as fitz

    document = fitz.open()
    try:
        for text in pages:
            page = document.new_page()
            # CJK needs a font that carries the glyphs; PyMuPDF ships one.
            page.insert_text((72, 72), text, fontname="china-s", fontsize=11)
        return document.tobytes()
    finally:
        document.close()


def write_originals(root: Path) -> dict[str, dict]:
    """Write the synthetic originals + sidecars and return the observed truth.

    ``root`` is the project root of the isolated fixture lake.  Each document
    lands under ``companies/<entity>/raw/...`` exactly like the existing
    production fixtures, so the real scanner registers it.
    """
    import hashlib
    import json

    from tools.narrative_g2_replay import specs

    docs = fixture_docs()
    written: dict[str, dict] = {}
    for key, doc in docs.items():
        if doc.is_transcript:
            directory = root / "companies" / "W08Synthetic" / "raw" / "transcripts"
            data = doc.text_bytes or b""
        else:
            directory = root / "companies" / "W08Synthetic" / "raw" / "filings"
            data = pdf_bytes(doc.pages)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / doc.filename
        path.write_bytes(data)
        digest = hashlib.sha256(data).hexdigest()
        sidecar = {
            "schema_version": "1.0",
            "canonical_entity_id": specs.FIXTURE_ENTITY_ID,
            "display_name": specs.FIXTURE_DISPLAY_NAME,
            "market": "CN",
            "security_id": specs.FIXTURE_SECURITY_ID,
            "document_kind": doc.document_kind,
            "fiscal_year": doc.fiscal_year,
            "fiscal_period": doc.fiscal_period,
            "period_end": doc.period_end,
            "filing_date": doc.filing_date,
            "provider": "w08_synthetic_fixture",
            "provider_document_id": doc.filename,
            "content_sha256": digest,
            "source_url": "https://fixtures.invalid/" + doc.filename,
            "source_title": doc.filename,
            "retrieved_at": "2026-08-01T00:00:00Z",
            "collector_name": "w08_narrative_g2_replay",
            "collector_version": "1.0.0",
            "language": doc.language,
            "synthetic": True,
        }
        path.with_name(doc.filename + ".source.json").write_text(
            json.dumps(sidecar, ensure_ascii=False), encoding="utf-8"
        )
        written[key] = {
            "fixture_key": key,
            "filename": doc.filename,
            "path_ref": f"companies/W08Synthetic/raw/"
                        f"{'transcripts' if doc.is_transcript else 'filings'}/"
                        f"{doc.filename}",
            "content_sha256": digest,
            "byte_size": len(data),
            "mime_type": doc.mime_type,
            "document_kind": doc.document_kind,
            "source_class": doc.source_class,
            "language": doc.language,
            "fiscal_year": doc.fiscal_year,
            "fiscal_period": doc.fiscal_period,
            "period_end": doc.period_end,
            "filing_date": doc.filing_date,
            "synthetic": True,
        }
    return written


__all__ = [
    "CALL_EN_TEXT", "CALL_ZH_TEXT", "FixtureDoc", "fixture_docs", "pdf_bytes",
    "write_originals",
]
