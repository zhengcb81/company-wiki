"""Shared builders for the document-understanding profile fixtures.

These helpers only assemble ``du-input/1`` observations. They intentionally carry no
expectations, so the A-node tests can state the expected route independently.

The text fragments are bounded excerpts taken from the plan's own
``sample_observations.json.gz`` (``docs/plans/document-understanding-2026-10-13/``).
They are short heading/cover/TOC fragments, not document bodies, and no company is
special-cased anywhere in the package: fragments are used as generic section-vocabulary
evidence (``第三节 管理层讨论与分析``, ``ITEM 4. INFORMATION``, ``業務回顧及展望`` ...).
"""

from __future__ import annotations

from typing import Any, Iterable

SCHEMA_VERSION = "du-input/1"


def unit(
    unit_id: str,
    ordinal: int,
    text: str,
    *,
    kind: str = "paragraph",
    page: int | None = None,
    language: str | None = None,
    role: str | None = None,
    heading_level: int | None = None,
) -> dict[str, Any]:
    """One ``du-input/1`` unit with optional layout/hint fields."""
    item: dict[str, Any] = {
        "unit_id": unit_id,
        "ordinal": ordinal,
        "locator": f"opaque-locator-{ordinal + 1}",
        "page": page,
        "text": text,
        "kind": kind,
        "language": language,
        "role": role,
    }
    if heading_level is not None:
        item["hints"] = {"heading_level": heading_level}
    return item


def observation(
    units: Iterable[dict[str, Any]],
    *,
    title: str | None = None,
    declared_kind: str = "unknown",
    regime: str = "unknown",
    form_type: str | None = None,
    mime_type: str = "application/pdf",
    language: str | None = None,
    native_scan: str = "complete",
    published_at: str | None = None,
    period_end: str | None = None,
    revision: str | None = None,
    source_id: str = "opaque-source-id",
    source_sha256: str = "opaque-passed-through-digest",
    opaque_pages: Iterable[int] = (),
    deferred_pages: Iterable[int] = (),
) -> dict[str, Any]:
    """Assemble a ``du-input/1`` mapping. Missing optionals stay ``None``."""
    return {
        "schema_version": SCHEMA_VERSION,
        "source_ref": {"source_id": source_id, "source_sha256": source_sha256},
        "metadata": {
            "title": title,
            "declared_kind": declared_kind,
            "regime": regime,
            "form_type": form_type,
            "mime_type": mime_type,
            "language": language,
            "published_at": published_at,
            "period_end": period_end,
            "revision": revision,
        },
        "coverage": {
            "native_scan": native_scan,
            "opaque_pages": list(opaque_pages),
            "deferred_pages": list(deferred_pages),
        },
        "units": list(units),
    }


def plain_text_observation(text: str, **kwargs: Any) -> dict[str, Any]:
    """Split a blob into one unit per non-empty line; for TXT/HTML-ish fixtures."""
    lines = [line for line in text.split("\n")]
    units = [
        unit(f"u{index + 1}", index, line, kind="paragraph", language=None)
        for index, line in enumerate(lines)
        if line.strip()
    ]
    kwargs.setdefault("mime_type", "text/plain")
    return observation(units, **kwargs)


# --- bounded real-fragment building blocks -------------------------------------------

CN_ANNUAL_COVER = [
    "公司代码：688012",
    "公司简称：中微公司",
    "2025 年年度报告",
    "1 / 259",
]

CN_ANNUAL_TOC = [
    "目录",
    "第一节 释义",
    "第二节 公司简介和主要财务指标",
    "第三节 管理层讨论与分析",
    "第四节 公司治理、环境和社会",
    "第五节 重要事项",
    "第六节 股份变动及股东情况",
    "第十节 财务报告",
]

CN_ANNUAL_BODY = [
    "第三节 管理层讨论与分析",
    "报告期内重点任务完成情况",
    "1、产品研发及客户拓展方面",
    "公司主营产品等离子体刻蚀设备作为半导体前道核心设备之一，市场空间广阔。",
]

CN_DIRECTOR_REPORT = [
    "2025 年度独立董事述职报告",
    "本人作为公司独立董事，现就 2025 年度履职情况报告如下。",
    "一、出席会议情况",
    "二、发表独立意见情况",
]

CN_QUARTERLY = [
    "证券代码：688012",
    "2026 年第一季度报告",
    "重要内容提示",
    "一、主要财务数据",
    "(一)主要会计数据和财务指标",
    "三、其他提醒事项",
    "四、季度财务报表",
]

CN_QUARTERLY_BODY = [
    "公司以行业领先的研发速度，在短时间内成功开发出十多种薄膜设备。",
    "公司持续保持国际氮化镓基MOCVD 设备市场领先地位。",
]

CN_IPO_COVER = [
    "首次公开发行股票并在科创板上市",
    "招股说明书",
]

CN_IPO_TOC = [
    "目录",
    "第一节 释义",
    "第六节 业务与技术",
    "第八节 财务会计信息与管理层分析",
    "第九节 募集资金运用与未来发展规划",
    "第十节 投资者保护",
]

CN_CONFIRMATION_LETTER = [
    "控股股东、实际控制人对《湖北鼎龙化学股份有限公司首次公开发行股票并在创业板上市招股说明书》的确认意见",
]

CN_OFFERING_COVER = [
    "证券代码：300488",
    "2020 年向特定对象发行A 股股票",
    "募集说明书",
    "（注册稿）",
]

CN_OFFERING_BODY = [
    "第三节 董事会关于本次募集资金使用的可行性分析",
    "本次向特定对象发行A 股股票拟募集资金总额为不超过35,978.71 万元。",
    "（二）项目投资计划",
    "（三）项目建设用地",
    "（四）项目建设周期",
    "项目建设期两期，新建厂房为一期，老厂区改建为二期。",
]

CN_CONVERTIBLE_COVER = [
    "股票代码：002597",
    "公开发行可转换公司债券募集说明书",
]

CN_CONVERTIBLE_BODY = [
    "第八章 本次募集资金运用",
    "本次募集资金投资项目的可行性与必要性",
    "单位：万元",
]

CN_IR_QA = [
    "中节能万润股份有限公司投资者关系活动记录表",
    "投资者关系活动类别",
    "1、问：公司目前账面价值17 个亿的库存，有没有减值风险？",
    "答：您好，公司存货主要包括原材料、在产品及自制半成品。",
    "2、问：有没有能推动与宁德时代等行业龙头达成电池电解液添加剂VC 的带量采购等具体业务？",
    "答：您好，公司现无生产VC（碳酸亚乙烯酯）的情况。",
]

CN_IR_POLICY = [
    "投资者关系管理制度",
    "第一章 总则",
    "第一条 为规范公司投资者关系管理工作，制定本制度。",
    "第二章 投资者关系管理的内容和方式",
]

CN_MEETING_NOTICE = [
    "关于召开 2025 年度业绩说明会的公告",
    "会议召开时间：2026 年 5 月 15 日 15:00-16:30",
    "会议召开方式：网络远程",
]

HK_ANNUAL_COVER = [
    "MINISO",
    "Stock Code 股份代號 : 9896",
    "ANNUAL REPORT 2024",
    "年度報告",
]

HK_ANNUAL_TOC = [
    "Contents 目錄",
    "Financial Performance Highlights 財務表現摘要",
    "Business Review and Outlook 業務回顧及展望",
    "Management Discussion and Analysis 管理層討論與分析",
    "Directors' Report 董事會報告",
    "Independent Auditor's Report 獨立核數師報告",
]

HK_ANNUAL_BODY = [
    "Business Review and Outlook",
    "業務回顧及展望",
    "BUSINESS REVIEW FOR THE REPORTING PERIOD",
    "Store Network",
]

HK_INTERIM_TOC = [
    "Contents 目錄",
    "Financial Performance Highlights 財務表現摘要",
    "Business Review and Outlook 業務回顧及展望",
    "Independent Review Report 獨立審閱報告",
    "Unaudited Consolidated Statement of Profit or Loss",
]

HK_IPO_COVER = [
    "股份代號 : 9896",
    "全球發售",
    "聯席保薦人、聯席全球協調人、聯席賬簿管理人",
]

HK_IPO_TOC = [
    "目 錄",
    "有關本文件及全球發售的資料",
    "行業概覽",
    "法規",
    "歷史及公司架構",
    "業務",
    "未來計劃及所得款項用途",
]

HK_RELEASE = [
    "For Immediate Release",
    "TENCENT ANNOUNCES 2026 SECOND QUARTER RESULTS",
    "Hong Kong, 12 August 2026",
    "CONDENSED CONSOLIDATED STATEMENT OF COMPREHENSIVE INCOME",
]

HK_DECK = [
    "2026 Second Quarter",
    "Results Presentation",
    "Aug 12, 2026",
    "In billion RMB",
]

SEC_10K_COVER = [
    "UNITED STATES SECURITIES AND EXCHANGE COMMISSION",
    "FORM 10-K",
    "For the Fiscal Year Ended June 30, 2025",
]

SEC_10K_INDEX = [
    "INDEX",
    "PART I",
    "Item 1. Business",
    "Item 1A. Risk Factors",
    "Item 1B. Unresolved Staff Comments",
    "Item 2. Properties",
    "PART II",
    "Item 7. Management's Discussion and Analysis of Financial Condition and Results of Operations",
    "Item 7A. Quantitative and Qualitative Disclosures About Market Risk",
    "Item 8. Financial Statements and Supplementary Data",
]

SEC_10K_BODY = [
    "PART I",
    "Item 1. Business",
    "Our segments",
    "Azure revenue is mainly affected by infrastructure-as-a-service and platform-as-a-service consumption-based services.",
]

SEC_10Q_COVER = [
    "UNITED STATES SECURITIES AND EXCHANGE COMMISSION",
    "FORM 10-Q",
    "For the quarterly period ended March 31, 2025",
]

SEC_10Q_BODY = [
    "PART I — FINANCIAL INFORMATION",
    "Item 2. Management's Discussion and Analysis of Financial Condition and Results of Operations",
    "Our Business",
    "We have determined that we have one operating segment and one reportable segment, Insurance.",
]

SEC_20F_COVER = [
    "UNITED STATES SECURITIES AND EXCHANGE COMMISSION",
    "FORM 20-F",
    "For the fiscal year ended February 29, 2024",
]

SEC_20F_BODY = [
    "ITEM 4. INFORMATION ON THE COMPANY",
    "B. Business Overview",
    "ITEM 5. OPERATING AND FINANCIAL REVIEW AND PROSPECTS",
    "ITEM 3. KEY INFORMATION",
    "D. Risk Factors",
]

TRANSCRIPT_TXT = [
    "CALL PARTICIPANTS",
    "Chairman and Chief Executive Officer - Satya Nadella",
    "Chief Financial Officer - Amy Hood",
    "Operator:Greetings, and welcome to the Microsoft Fiscal Year 2026 Fourth Quarter Earnings Conference Call.",
    "Jonathan Neilson:Good afternoon, and thank you for joining us today.",
    "Questions and Answers",
]

RESULTS_RELEASE_HTML = [
    "Business Highlights",
    "Microsoft Cloud revenue was $59.3 billion and increased 27%.",
    "Microsoft returned $10.2 billion to shareholders in the form of dividends and share repurchases.",
]
