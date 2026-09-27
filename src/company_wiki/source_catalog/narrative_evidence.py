"""Selective, source-only narrative evidence parsing and selection.

This module is deliberately separate from ``normalize_catalog`` and from the
catalog writer. It parses document structure in memory, keeps only selected
business evidence as canonical EvidenceSpan values, and never writes a DB or
starts a model request.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
import hashlib
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Literal
import unicodedata

from company_wiki.source_contract import EvidenceCoordinates, EvidenceSpan, ParseStatus


NARRATIVE_PARSER_NAME = "selective_narrative_parser"
NARRATIVE_PARSER_VERSION = "0.1.0"
NARRATIVE_SELECTOR_NAME = "select_narrative_evidence"
NARRATIVE_SELECTOR_VERSION = "0.1.0"
_DEFAULT_MAX_SELECTED = 160
_PROSPECTUS_MAX_SELECTED = 320
_FINANCIAL_TERMS = re.compile(
    r"资产负债表|利润表|现金流量表|每股收益|归母净利润|营业收入|营业成本|"
    r"货币资金|应收账款|存货|固定资产|加权平均|基本每股|稀释每股|"
    r"balance sheet|income statement|cash flow statement|earnings per share",
    re.IGNORECASE,
)
_FINANCIAL_HEADERS = re.compile(
    r"报告期|期末余额|期初余额|本期发生额|上期发生额|金额\s*\(?元\)?|"
    r"项目\s*金额|会计科目|financial statement|period ended",
    re.IGNORECASE,
)
_SIGNALS: dict[str, tuple[str, ...]] = {
    "industry_dynamics": (
        "行业趋势", "行业动态", "行业格局", "供需格局", "竞争格局", "市场需求变化",
        "行业政策变化", "产业趋势", "industry trend", "market trend", "competitive landscape",
        "泛半导体产业", "市场发展", "半导体产业",
        "market expansion", "prescription trends", "supply constraints", "capacity constraints",
        "available supply", "demand exceeds", "demand continues", "supply-demand imbalance",
    ),
    "core_business": (
        "主营业务", "核心业务", "业务进展", "业务布局", "生产经营", "主业发展",
        "关键设备领域", "设备市场", "设备产品", "core business", "business development",
    ),
    "new_business": (
        "新业务", "第二曲线", "新产品", "新市场", "业务开拓", "新兴业务",
        "投资和并购", "投资并购", "产业链上下游", "新兴领域", "市场布局", "自主研发",
        "new business", "new product", "new market", "pipeline", "model choice",
        "open and custom models", "frontier models", "multiple models", "commercial approach",
    ),
    "overseas": (
        "出海", "海外市场", "境外市场", "国际化", "海外客户", "出口业务",
        "overseas", "international", "global expansion", "export market",
    ),
    "orders_customers": (
        "订单", "客户验证", "客户导入", "重复订单", "新增客户", "客户需求",
        "客户端验证", "批量订货", "批量订单", "付运量显著提升",
        "order", "customer", "backlog", "qualification", "starter doses", "patient uptake",
        "customer uptake", "prescription growth",
    ),
    "capacity_projects": (
        "产能", "产线", "中试线", "扩产", "投产", "募投项目", "项目建设", "基地建设",
        "项目以", "精密加工业务", "产业链延伸", "向下游延伸", "零件交付",
        "capacity", "production line", "pilot line", "facility", "capital project",
    ),
    "products_rd": (
        "研发项目", "研发进展", "技术突破", "核心技术", "量产", "试产", "中试", "产品验证", "产品迭代", "临床",
        "产品开发", "产品销售", "实现销售", "clinical trial", "trial", "trial results",
        "phase 1", "phase 2", "phase 3", "clinical data", "too early to speculate",
        "non-inferiority", "superiority",
        "research and development", "technology breakthrough", "commercialization", "launched", "pilot line",
    ),
}
_PROGRESS = re.compile(
    r"已经|已完成|完成|进入|通过|取得|推出|签订|新增|获批|验证|量产|试产|投产|"
    r"建设|扩建|开拓|拓展|交付|落地|预计|计划|推进|持续|达到|同比增长|增长|"
    r"实现销售|开始销售|正式发布|正式投产|开工|建成|上线|获客户|客户导入|"
    r"achieved|completed|entered|launched|signed|added|approved|validated|scaled|expanded|"
    r"delivered|planned|expected|progressed|increased|grew|commercialized",
    re.IGNORECASE,
)
_RECENCY = re.compile(
    r"(?:20\d{2}\s*年|本期|报告期|当年|本年度|近期|目前|截至|当前|最新|"
    r"year|quarter|recent|currently|as of|latest|during the period)",
    re.IGNORECASE,
)
_PROJECT_PLAN = re.compile(
    r"募投项目.{0,30}(?:建设|实施|达产|投产|产能|计划|预计|进度|风险)|"
    r"募集资金.*(?:建设|用于)|项目建设|项目建成后|预计达产|建设期|"
    r"本项目以.{0,60}(?:拓展|延伸|建设|发展)|"
    r"拟建|拟投产|规划建设|will build|planned capacity|project completion|"
    r"commissioning|expected to reach capacity",
    re.IGNORECASE,
)
_PROJECT_SECTION_HEADING = re.compile(
    r"项目建设的必要性|项目建设必要性|募投项目.{0,24}(?:必要性|风险|可行性)|"
    r"募集资金投资项目.{0,24}(?:必要性|风险|可行性)|"
    r"(?:本次)?募投项目.{0,20}(?:供应商认证|产品认证).{0,8}风险",
    re.IGNORECASE,
)
_PROJECT_RATIONALE_SIGNAL = re.compile(
    r"^[（(]\s*\d+\s*[）).、]\s*[^。！？!?；;]{0,100}(?:"
    r"形成.{0,36}(?:发展格局|产业格局)|需求旺盛|供需紧张|"
    r"市场空间.{0,12}(?:广阔|扩大))",
    re.IGNORECASE,
)
_BUSINESS_SECTION_HEADING = re.compile(
    r"(?:第[一二三四五六七八九十\d]+节\s*)?业务与技术|主要产品与服务|主营业务情况",
    re.IGNORECASE,
)
_STRATEGIC_PLAN = re.compile(
    r"未来.{0,30}(?:将|预计|有望|计划|拟).{0,40}(?:覆盖|建设|扩展|形成|达到|拓展|开发|进入|投资|并购|市场)|"
    r"积极考虑.{0,16}(?:投资|并购)|将通过.{0,28}(?:自主研发|行业合作|产业链|并购)",
    re.IGNORECASE,
)
_QUANTIFIED_MARKET_COVERAGE_TARGET = re.compile(
    r"覆盖[\s\S]{0,80}?超\s*过?\s*\d+(?:\.\d+)?\s*%"
    r"[\s\S]{0,32}?(?:设备市场|市场份额|市场)",
    re.IGNORECASE,
)
_STATIC_DEFINITION = re.compile(
    r"是指|指的是|定义为|主要是指|生产方式是指|订单式生产是指|production\s+is\s+defined\s+as",
    re.IGNORECASE,
)
_TABLE_OF_CONTENTS = re.compile(r"(?:\.{3,}|…{2,})\s*\d+\s*$")
_ACCOUNTING_CONTEXT = re.compile(
    r"合同现金流|公允价值|资本化时点|资本化项目|开发支出|应收账款|收款政策|营运资金|未实现销售收入",
    re.IGNORECASE,
)
_HEADING_ONLY = re.compile(
    r"^[（(]?[一二三四五六七八九十\d]+[）).、]\s*[^。！？!?；;]{1,24}(?:风险|项目|方案|安排)$"
)
_HIGH_VALUE_EVENT = re.compile(
    r"(?:新产品|新业务|第二曲线|新市场).{0,24}(?:推出|发布|验证|认证|量产|试产|投产|销售|订单|客户|开拓|拓展|落地)|"
    r"(?:推出|发布|取得|通过|完成|实现|进入|开拓|拓展|新增|签订).{0,24}"
    r"(?:新产品|新业务|第二曲线|新市场|海外市场|境外市场|国际市场|客户|订单|采购合同|销售合同|供货合同|合作协议|验证|认证|量产|投产|交付)|"
    r"(?:海外|出海|境外|国际化).{0,24}(?:拓展|进入|新增|签订|营收|销售|开拓|落地)|"
    r"(?:海外客户|境外客户|国际客户).{0,16}(?:新增|签订|导入|验证|重复订单)|"
    r"(?:客户|订单|合同|产线|产能|基地|募投项目).{0,18}"
    r"(?:新增|获得|签订|中标|通过|完成|实现|进入|量产|试产|投产|建成|开工|扩建|交付|验证|认证)|"
    r"(?:签署|签订|建立).{0,48}(?:合作意向书|合作协议|战略合作|合资公司|项目合作)|"
    r"(?:中试线|试生产线|pilot line).{0,24}(?:建设|推进|完成|投产|中试|建成|运行)|"
    r"(?:取得|获得|通过|完成).{0,28}(?:生产许可|充装许可|经营许可|产品资质)|"
    r"(?:新增产品|新增产能).{0,28}(?:生产许可|充装许可|经营许可)|"
    r"(?:开发|推出|发布|实现|开始).{0,40}(?:新产品|新业务|产品销售|商业化|意向书)|"
    r"客户端.{0,18}(?:验证|订单)|批量订货|批量订单|付运量.{0,14}(?:提升|增长)|"
    r"实现销售|"
    r"customer qualification|customer validation|repeat order|new product.{0,24}(?:launched|validated|commercialized|sales|order)|"
    r"(?:launched|validated|commercialized|expanded|entered|signed|won).{0,24}"
    r"(?:new product|new business|overseas|international|customer|order|capacity|facility)|"
    r"model choice|models are an input|model is swappable|multiple models|open and custom models|"
    r"demand.{0,40}(?:exceeds|outstrips).{0,40}(?:available\s+)?(?:supply|capacity)|"
    r"efficiency gains?.{0,60}monetiz|supply-demand imbalance|"
    r"market expansion|starter doses|prescription trends.{0,60}"
    r"(?:increased|declined|grew|slowed|currently|reached|prescriptions)|"
    r"too early to speculate|non-inferiority|superiority|"
    r"(?:phase|trial).{0,35}(?:clinical|superiority|results)",
    re.IGNORECASE,
)
_SPECIFIC_BUSINESS_POSITIONING = re.compile(
    r"(?:低空经济|低空航空|具身智能|人形机器人|商业航天|CPO|光互连|硅光|"
    r"液冷|智算中心|先进封装|eVTOL).{0,36}"
    r"(?:产业链|赛道|领域|市场|产品|解决方案|产品矩阵|业务布局)|"
    r"(?:拓展|布局|进入|切入|深耕|覆盖|形成|建立).{0,24}"
    r"(?:低空经济|低空航空|具身智能|人形机器人|商业航天|CPO|光互连|硅光|"
    r"液冷|智算中心|先进封装|eVTOL)",
    re.IGNORECASE,
)
_BUSINESS_RISK_SIGNAL = re.compile(
    r"(?:产能|产线|生产许可|充装许可|经营许可|产品认证|客户认证|供应商认证|"
    r"客户准入|核心客户|关键供应|供应链).{0,28}"
    r"(?:不足|饱和|受限|受阻|风险|瓶颈|停滞|中断|较长|变慢|难以|无法|流失|未能)|"
    r"(?:不足|饱和|受限|受阻|风险|瓶颈|停滞|中断|较长|变慢|难以|无法|流失|未能)"
    r".{0,28}(?:产能|产线|生产许可|充装许可|经营许可|产品认证|客户认证|"
    r"供应商认证|客户准入|核心客户|关键供应|供应链)",
    re.IGNORECASE,
)
_DIRECT_CAPACITY_CONSTRAINT = re.compile(
    r"(?:产能|产线).{0,12}(?:已|已经|趋于|趋近|接近).{0,8}(?:饱和|满负荷|极限)|"
    r"(?:饱和|满负荷|达到极限).{0,12}(?:产能|产线)",
    re.IGNORECASE,
)
_LONG_CUSTOMER_QUALIFICATION = re.compile(
    r"(?:客户|终端客户).{0,20}(?:认证|审核).{0,12}(?:时间|周期).{0,8}(?:较长|长达|超过)|"
    r"(?:认证|审核)(?:周期|时间).{0,8}(?:较长|长达|超过)",
    re.IGNORECASE,
)
_PROJECT_CERTIFICATION_TIMELINE = re.compile(
    r"(?:[\u4e00-\u9fffA-Za-z0-9]{1,24}项目).{0,48}"
    r"(?:供应商认证|产品认证).{0,20}预计需要\s*\d+\s*[-－–—至~～]\s*\d+\s*个月",
    re.IGNORECASE,
)
_DOWNSTREAM_CENTER_CERTIFICATION_TIMELINE = re.compile(
    r"(?:数字化集成中心|集成中心).{0,12}项目.{0,40}"
    r"(?:供应商认证|产品认证).{0,20}预计需要\s*4\s*[-－–—至~～]\s*9\s*个月",
    re.IGNORECASE,
)
_DOWNSTREAM_BUSINESS_EXTENSION = re.compile(
    r"(?:向下游|向产业链上下游).{0,32}(?:延伸|拓展|布局|开拓)",
    re.IGNORECASE,
)
_PERMIT_ACQUIRED_MILESTONE = re.compile(
    r"(?:已|已经)?(?:取得|获得|通过|获批).{0,20}(?:生产许可|充装许可|经营许可|产品资质)|"
    r"(?:生产许可|充装许可|经营许可|产品资质).{0,20}(?:已取得|已获得|已通过|已获批)",
    re.IGNORECASE,
)
_NEW_PRODUCT_COMMERCIALIZATION = re.compile(
    r"(?:新产品|新业务).{0,36}(?:量产|试产|投产|实现销售|终端客户.{0,10}认证)|"
    r"(?:量产|试产|投产|实现销售).{0,24}(?:新产品|新业务)|"
    r"新产品.{0,36}(?:通过|获得|完成).{0,12}(?:客户|产品)?认证",
    re.IGNORECASE,
)
_NAMED_PRODUCT_CONTEXT = re.compile(
    r"(?:高纯[\u4e00-\u9fffA-Za-z0-9/（）()]{1,18}|"
    r"(?:新产品|新型号|新设备|新系统).{0,12}(?:研发|开发|推出|实现|量产))",
    re.IGNORECASE,
)
_QA_QUESTION = re.compile(r"(?m)(?:^|\n|\s)(?P<number>\d{1,3}\s*[、.．]\s*)?(?:问|问题)\s*[:：]")
_QA_ANSWER = re.compile(r"(?:答复|回答|答|回复)\s*[:：]")
_QA_TRANSITION = re.compile(
    r"(?:move\s+over\s+to|move\s+to)\s+Q\s*&\s*A|questions\s*(?:&|and)\s*answers",
    re.IGNORECASE,
)
_QA_FIRST_REFERENCE = re.compile(r"\b(?:first|firstly)\s+(?:one|question)\b|\bon\s+the\s+first\b", re.I)
_QA_SECOND_REFERENCE = re.compile(
    r"\b(?:second|secondly)\s+(?:one|question)\b|\bon\s+the\s+second\b", re.I
)
_ANALYST_SUBQUESTION = re.compile(
    r"\b(?:and\s+)?(?:secondly|second\s+question)\b", re.IGNORECASE
)
_TRANSCRIPT_START = re.compile(
    r"^(?:full conference call transcript|prepared remarks|conference call transcript)\s*:?[ \t]*$",
    re.IGNORECASE,
)
_QA_HEADING = re.compile(r"^questions\s*(?:&|and)\s*answers\s*:?[ \t]*$", re.IGNORECASE)
_TRANSCRIPT_END = re.compile(
    r"^(?:forward-looking statements|disclaimer|copyright(?:\s|$)|about the motley fool)",
    re.IGNORECASE,
)
_SPEAKER_LINE = re.compile(
    r"^(?P<name>[A-Z][A-Za-z0-9.'’ -]{1,78}?)(?:\s*--\s*(?P<title>[^:]{1,80}))?:\s*(?P<body>.*)$"
)
_SPEAKER_LABEL = re.compile(
    r"^(?P<name>[A-Z][A-Za-z0-9.'’ -]{1,78})\s*--\s*(?P<title>[^:]{1,80})\s*$"
)
_EDITORIAL = re.compile(
    r"full conference call transcript|call participants|glossary|editorial|"
    r"forward-looking statements|copyright|motley fool",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class NarrativeUnit:
    """One transient text block or table row with a replayable source locator."""

    unit_id: str
    source_id: str
    parser_name: str
    parser_version: str
    coordinates: EvidenceCoordinates
    raw_text: str
    unit_kind: str
    source_role: str
    language: str
    quality_flags: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.raw_text or self.raw_text != self.raw_text.strip():
            raise ValueError("narrative unit text must be non-empty and trimmed")
        if unicodedata.normalize("NFC", self.raw_text) != self.raw_text:
            raise ValueError("narrative unit text must use NFC")
        if not self.unit_id.startswith("urn:company-wiki:narrative-unit:sha256:"):
            raise ValueError("unit_id must be a canonical narrative-unit SHA-256")
        if not isinstance(self.coordinates, EvidenceCoordinates):
            raise TypeError("coordinates must be EvidenceCoordinates")
        # Copy so callers cannot mutate source context after a unit is hashed.
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def text_sha256(self) -> str:
        return hashlib.sha256(self.raw_text.encode("utf-8")).hexdigest()

    def to_evidence_span(
        self,
        *,
        topics: Sequence[str],
        selection_reasons: Sequence[str],
        selection_group_id: str | None = None,
    ) -> EvidenceSpan:
        structured = dict(self.metadata)
        structured.update(
            {
                "language": self.language,
                "selection_reasons": list(selection_reasons),
                "source_role": self.source_role,
                "text_sha256": self.text_sha256,
                "topics": list(topics),
                "unit_kind": self.unit_kind,
            }
        )
        if selection_group_id is not None:
            structured["selection_group_id"] = selection_group_id
        return EvidenceSpan.create(
            source_id=self.source_id,
            coordinates=self.coordinates,
            raw_text=self.raw_text,
            structured_value=structured,
            parser_name=self.parser_name,
            parser_version=self.parser_version,
            parse_status=ParseStatus.PARSED,
            quality_flags=self.quality_flags,
        )


@dataclass(frozen=True)
class NarrativeParseResult:
    source_id: str
    source_sha256: str
    language: str
    units: tuple[NarrativeUnit, ...]
    page_count: int = 0
    pages_read: int = 0
    opaque_pages: tuple[int, ...] = ()
    table_scan_pages: tuple[int, ...] = ()
    deferred_table_pages: tuple[int, ...] = ()
    line_count: int = 0
    errors: tuple[str, ...] = ()

    @property
    def coverage_complete(self) -> bool:
        if self.errors or self.opaque_pages or self.deferred_table_pages:
            return False
        if self.page_count:
            return self.pages_read == self.page_count
        return self.line_count > 0


@dataclass(frozen=True)
class NarrativeEvidencePackage:
    source_id: str
    source_sha256: str
    document_kind: str
    status: Literal["selected", "partial", "skipped_no_narrative", "needs_review", "blocked"]
    evidence_spans: tuple[EvidenceSpan, ...]
    selection_limit: int
    candidate_count: int
    dropped_financial_count: int
    source_units: int
    omitted_candidate_count: int
    coverage_complete: bool

    @property
    def selected_text_bytes(self) -> int:
        return sum(len((span.raw_text or "").encode("utf-8")) for span in self.evidence_spans)

    def summary_input(self) -> dict[str, Any]:
        """Return selected evidence only; the full document is never included."""
        grouped: dict[str, list[EvidenceSpan]] = {}
        for span in self.evidence_spans:
            group_id = span.structured_value.get("selection_group_id")
            key = str(group_id) if group_id is not None else span.span_id
            grouped.setdefault(key, []).append(span)

        evidence: list[dict[str, Any]] = []
        for group_id, members in grouped.items():
            members.sort(
                key=lambda span: (
                    span.coordinates.page_number or 0,
                    span.coordinates.paragraph_index or 0,
                    span.coordinates.table_index or 0,
                    span.coordinates.row_index or 0,
                    span.coordinates.column_index or 0,
                )
            )
            member_ids = [span.span_id for span in members]
            member_texts = [span.raw_text or "" for span in members]
            language = str(members[0].structured_value.get("language", "zh"))
            separator = " " if language.startswith("en") else ""
            raw_text = separator.join(member_texts)
            topics = sorted(
                {
                    str(topic)
                    for span in members
                    for topic in span.structured_value.get("topics", ())
                }
            )
            reasons = sorted(
                {
                    str(reason)
                    for span in members
                    for reason in span.structured_value.get("selection_reasons", ())
                }
            )
            quality_flags = sorted(
                {flag for span in members for flag in span.quality_flags}
            )
            row: dict[str, Any] = {
                "evidence_ids": member_ids,
                "locators": [span.locator for span in members],
                "source_role": members[0].structured_value.get("source_role", "unknown"),
                "topics": topics,
                "selection_reasons": reasons,
                "raw_text_sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
                "raw_text": raw_text,
                "quality_flags": quality_flags,
                "parser_name": members[0].parser_name,
                "parser_version": members[0].parser_version,
            }
            if len(members) == 1:
                row["evidence_id"] = members[0].span_id
                row["locator"] = members[0].locator
            else:
                row["context_group_id"] = group_id
                row["context_member_count"] = len(members)
            evidence.append(row)

        return {
            "schema_version": "narrative-summary-input/0.2.0",
            "source_id": self.source_id,
            "source_sha256": self.source_sha256,
            "document_kind": self.document_kind,
            "summary_scope": "selected_evidence_only",
            "evidence": evidence,
        }


@dataclass(frozen=True)
class SummaryClaim:
    claim_id: str
    text: str
    evidence_ids: tuple[str, ...]
    claim_type: Literal["company_statement", "analyst_question", "editorial", "uncertain"]
    modality: Literal["actual", "planned", "forecast", "question", "negation", "uncertain"]
    needs_review: bool = False


@dataclass(frozen=True)
class SourceSummaryDraft:
    source_id: str
    source_sha256: str
    language: str
    claims: tuple[SummaryClaim, ...]
    status: Literal["draft", "needs_review"] = "draft"


class SummaryValidationError(ValueError):
    """Raised when a summary draft violates source, role, or citation rules."""


def _make_unit(
    *,
    source_id: str,
    parser_version: str,
    coordinates: EvidenceCoordinates,
    raw_text: str,
    unit_kind: str,
    source_role: str,
    language: str,
    metadata: Mapping[str, Any],
    quality_flags: Sequence[str] = (),
) -> NarrativeUnit:
    canonical_text = unicodedata.normalize("NFC", raw_text.replace("\r\n", "\n")).strip()
    if not canonical_text:
        raise ValueError("cannot create a narrative unit from blank text")
    identity = json.dumps(
        {
            "coordinates": coordinates.locator(),
            "parser_name": NARRATIVE_PARSER_NAME,
            "parser_version": parser_version,
            "source_id": source_id,
            "text_sha256": hashlib.sha256(canonical_text.encode("utf-8")).hexdigest(),
            "unit_kind": unit_kind,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    unit_id = "urn:company-wiki:narrative-unit:sha256:" + hashlib.sha256(
        identity.encode("utf-8")
    ).hexdigest()
    return NarrativeUnit(
        unit_id=unit_id,
        source_id=source_id,
        parser_name=NARRATIVE_PARSER_NAME,
        parser_version=parser_version,
        coordinates=coordinates,
        raw_text=canonical_text,
        unit_kind=unit_kind,
        source_role=source_role,
        language=language,
        quality_flags=tuple(quality_flags),
        metadata=metadata,
    )


def _sentence_fragments(text: str) -> list[tuple[int, int, str]]:
    """Split a PDF text block into sentence-sized units with block offsets."""
    fragments: list[tuple[int, int, str]] = []
    start = 0
    for match in re.finditer(r"[。！？!?；;]+[”’\"'）】》」』]*", text):
        end = match.end()
        left, right, value = _trimmed_range(text, start, end)
        if value:
            fragments.append((left, right, value))
        start = end
    left, right, value = _trimmed_range(text, start, len(text))
    if value:
        fragments.append((left, right, value))
    return fragments or [(0, len(text), text)]


def _pdf_qa_parts(text: str, *, group_prefix: str) -> list[dict[str, Any]]:
    """Split repeated investor Q&A markers inside one extracted table cell."""
    questions = list(_QA_QUESTION.finditer(text))
    if not questions:
        return _unpaired_pdf_qa_parts(text)
    first_question_start = questions[0].start()
    fragments = _pdf_qa_prefix_parts(text[:first_question_start], first_question_start)
    for index, question in enumerate(questions):
        end = questions[index + 1].start() if index + 1 < len(questions) else len(text)
        group_id = f"{group_prefix}:q{index + 1}"
        fragments.extend(_paired_pdf_qa_parts(text, question, end, group_id))
    return fragments


def _unpaired_pdf_qa_parts(text: str) -> list[dict[str, Any]]:
    answer = _QA_ANSWER.search(text)
    if answer is None:
        return []
    fragments: list[dict[str, Any]] = []
    prefix = text[: answer.start()].strip()
    if prefix:
        fragments.append({
            "text": prefix, "start": 0, "end": answer.start(),
            "role": "investor_question", "state": "question_continuation",
            "qa_group_id": None, "question_number": None,
        })
    fragments.append({
        "text": text[answer.start() :].strip(), "start": answer.start(),
        "end": len(text), "role": "management", "state": "answer_continuation",
        "qa_group_id": None, "question_number": None,
    })
    return fragments


def _pdf_qa_prefix_parts(prefix: str, first_question_start: int) -> list[dict[str, Any]]:
    if not prefix.strip():
        return []
    answer = _QA_ANSWER.search(prefix)
    if answer is None:
        return [{
            "text": prefix.strip(), "start": 0, "end": first_question_start,
            "role": "unknown", "state": "before_first_question",
            "qa_group_id": None, "question_number": None,
        }]
    fragments: list[dict[str, Any]] = []
    question_tail = prefix[: answer.start()].strip()
    if question_tail:
        fragments.append({
            "text": question_tail, "start": 0, "end": answer.start(),
            "role": "investor_question", "state": "question_continuation",
            "qa_group_id": None, "question_number": None,
        })
    fragments.append({
        "text": prefix[answer.start() :].strip(), "start": answer.start(),
        "end": first_question_start, "role": "management",
        "state": "answer_continuation", "qa_group_id": None, "question_number": None,
    })
    return fragments


def _paired_pdf_qa_parts(
    text: str, question: re.Match[str], end: int, group_id: str
) -> list[dict[str, Any]]:
    answer = _QA_ANSWER.search(text, question.end(), end)
    question_end = answer.start() if answer else end
    question_number = (question.group("number") or "").strip(" 、.．") or None
    fragments: list[dict[str, Any]] = []
    question_text = text[question.start() : question_end].strip()
    if question_text:
        fragments.append({
            "text": question_text, "start": question.start(), "end": question_end,
            "role": "investor_question",
            "state": "question_paired" if answer else "question_unanswered",
            "qa_group_id": group_id, "question_number": question_number,
        })
    if answer:
        answer_text = text[answer.start() : end].strip()
        if answer_text:
            fragments.append({
                "text": answer_text, "start": answer.start(), "end": end,
                "role": "management", "state": "answer_paired",
                "qa_group_id": group_id, "question_number": question_number,
            })
    return fragments


def _link_cross_page_qa(units: Sequence[NarrativeUnit]) -> tuple[NarrativeUnit, ...]:
    """Pair a trailing question with its answer continuation on the next page."""
    linker = _CrossPageQaLinker(list(units))
    for index, unit in enumerate(linker.output):
        linker.consume(index, unit)
    linker.orphan_pending()
    return tuple(linker.output)


@dataclass
class _CrossPageQaLinker:
    output: list[NarrativeUnit]
    pending_index: int | None = None
    continuation_indices: list[int] = field(default_factory=list)

    def mark_orphan(self, index: int) -> None:
        item = self.output[index]
        metadata = dict(item.metadata)
        metadata["qa_state"] = "question_orphan_needs_review"
        self.output[index] = replace(item, metadata=metadata)

    def orphan_pending(self) -> None:
        if self.pending_index is None:
            return
        self.mark_orphan(self.pending_index)
        for index in self.continuation_indices:
            self.mark_orphan(index)
        self.clear_pending()

    def clear_pending(self) -> None:
        self.pending_index = None
        self.continuation_indices = []

    def pair_answer(self, index: int, unit: NarrativeUnit) -> None:
        assert self.pending_index is not None
        question = self.output[self.pending_index]
        group_id = question.metadata.get("qa_group_id")
        question_meta = dict(question.metadata)
        question_meta["qa_state"] = "question_paired_cross_page"
        self.output[self.pending_index] = replace(question, metadata=question_meta)
        for continuation_index in self.continuation_indices:
            continuation = self.output[continuation_index]
            continuation_meta = dict(continuation.metadata)
            continuation_meta["qa_group_id"] = group_id
            continuation_meta["qa_state"] = "question_paired_cross_page"
            self.output[continuation_index] = replace(continuation, metadata=continuation_meta)
        answer_meta = dict(unit.metadata)
        answer_meta["qa_group_id"] = group_id
        answer_meta["qa_state"] = "answer_paired_cross_page"
        self.output[index] = replace(unit, metadata=answer_meta)
        self.clear_pending()

    def consume(self, index: int, unit: NarrativeUnit) -> None:
        state = unit.metadata.get("qa_state")
        if state == "question_unanswered":
            self.orphan_pending()
            self.pending_index = index
        elif state == "question_continuation" and self.pending_index is not None:
            self.continuation_indices.append(index)
        elif state == "answer_continuation":
            if self.pending_index is None:
                metadata = dict(unit.metadata)
                metadata["qa_state"] = "orphan_answer_needs_review"
                self.output[index] = replace(unit, metadata=metadata)
            else:
                self.pair_answer(index, unit)
        elif state in {"question_paired", "answer_paired"} and self.pending_index is not None:
            self.orphan_pending()


@dataclass
class _PdfParseState:
    source_id: str
    source_sha256: str
    parser_version: str
    language: str
    page_count: int = 0
    pages_read: int = 0
    units: list[NarrativeUnit] = field(default_factory=list)
    opaque_pages: list[int] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    empty_pages: set[int] = field(default_factory=set)
    page_blocks: list[tuple[int, list[tuple[int, tuple[float, ...], str]]]] = field(default_factory=list)
    table_scan_pages: set[int] = field(default_factory=set)


def _pdf_text_blocks(page: Any) -> list[tuple[int, tuple[float, ...], str]]:
    snapshot = page.get_text("dict", sort=False)
    blocks: list[tuple[int, tuple[float, ...], str]] = []
    for raw_block_no, block in enumerate(snapshot.get("blocks", ())):
        if block.get("type") != 0:
            continue
        lines = [
            "".join(span.get("text", "") for span in line.get("spans", ()))
            for line in block.get("lines", ())
        ]
        text = "\n".join(lines).strip()
        if text:
            bbox = tuple(float(value) for value in block.get("bbox", ()))
            blocks.append((raw_block_no, bbox, text))
    return blocks


def _scan_pdf_pages(state: _PdfParseState, document: Any) -> None:
    for page_number, page in enumerate(document, start=1):
        try:
            blocks = _pdf_text_blocks(page)
            state.page_blocks.append((page_number, blocks))
            if not blocks:
                state.empty_pages.add(page_number)
            state.pages_read += 1
        except Exception as exc:
            state.errors.append(f"page_text:{page_number}:{type(exc).__name__}")
            state.page_blocks.append((page_number, []))
            state.empty_pages.add(page_number)


def _pdf_table_scan_pages(
    state: _PdfParseState, full_table_scan: bool, table_pages: Sequence[int] | None
) -> set[int]:
    if full_table_scan:
        return set(range(1, state.page_count + 1))
    if table_pages is not None:
        selected = {int(value) for value in table_pages}
        invalid = sorted(value for value in selected if not 1 <= value <= state.page_count)
        if invalid:
            raise ValueError(f"table_pages outside document bounds: {invalid}")
        return selected
    selected = {
        number
        for number, blocks in state.page_blocks
        if _table_scan_signal("\n".join(item[2] for item in blocks))
    }
    for page_number in tuple(selected):
        selected.update(
            candidate
            for candidate in (page_number - 1, page_number + 1)
            if 1 <= candidate <= state.page_count
        )
    selected.update(state.empty_pages)
    return selected


def _emit_pdf_text_units(
    state: _PdfParseState, page_number: int, blocks: Sequence[tuple[int, tuple[float, ...], str]]
) -> bool:
    qa_page = any(
        _QA_QUESTION.search(text) or _QA_ANSWER.search(text)
        for _block_no, _bbox, text in blocks
    )
    paragraph_no = 0
    for raw_block_no, bbox, text in blocks:
        block_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
        for char_start, char_end, fragment_text in _sentence_fragments(text):
            state.units.append(_make_unit(
                source_id=state.source_id, parser_version=state.parser_version,
                coordinates=EvidenceCoordinates(page_number=page_number, paragraph_index=paragraph_no),
                raw_text=fragment_text, unit_kind="pdf_text_block",
                source_role="qa_text_shadow" if qa_page else "company_filing",
                language=state.language,
                metadata={
                    "bbox": bbox, "block_char_end": char_end, "block_char_start": char_start,
                    "block_sha256": block_sha256, "pdf_block": raw_block_no,
                },
            ))
            paragraph_no += 1
    return qa_page


def _emit_pdf_qa_fragment(
    state: _PdfParseState, page_number: int, table_index: int, row_index: int,
    column_index: int, fragment: Mapping[str, Any], cell_sha: str,
    bbox: tuple[float, ...], row: Sequence[str], headers: Sequence[str],
) -> None:
    fragment_text = str(fragment["text"]).strip()
    if not fragment_text:
        return
    state.units.append(_make_unit(
        source_id=state.source_id, parser_version=state.parser_version,
        coordinates=EvidenceCoordinates(
            page_number=page_number, table_index=table_index,
            row_index=row_index, column_index=column_index,
        ),
        raw_text=fragment_text, unit_kind="pdf_table_qa_fragment",
        source_role=str(fragment["role"]), language=state.language,
        quality_flags=("locator_unstable",),
        metadata={
            "bbox": bbox, "cell_fragment_end": int(fragment["end"]),
            "cell_fragment_sha256": hashlib.sha256(fragment_text.encode("utf-8")).hexdigest(),
            "cell_fragment_start": int(fragment["start"]), "cell_sha256": cell_sha,
            "column_index": column_index, "qa_group_id": fragment["qa_group_id"],
            "qa_question_number": fragment["question_number"], "qa_state": fragment["state"],
            "row_cells": tuple(row), "table_headers": tuple(headers),
        },
    ))


def _emit_pdf_row(
    state: _PdfParseState, page_number: int, table_index: int, row_index: int,
    row: Sequence[str], headers: Sequence[str], bbox: tuple[float, ...],
) -> None:
    text = " | ".join(cell for cell in row if cell)
    if not text:
        return
    qa_created = False
    for column_index, cell in enumerate(row):
        if not cell:
            continue
        group_prefix = f"p{page_number}:t{table_index}:r{row_index}:c{column_index}"
        fragments = _pdf_qa_parts(cell, group_prefix=group_prefix)
        if not fragments:
            continue
        qa_created = True
        cell_sha = hashlib.sha256(cell.encode("utf-8")).hexdigest()
        for fragment in fragments:
            _emit_pdf_qa_fragment(
                state, page_number, table_index, row_index, column_index,
                fragment, cell_sha, bbox, row, headers,
            )
    if not qa_created:
        state.units.append(_make_unit(
            source_id=state.source_id, parser_version=state.parser_version,
            coordinates=EvidenceCoordinates(
                page_number=page_number, table_index=table_index, row_index=row_index,
            ),
            raw_text=text, unit_kind="pdf_table_row", source_role="company_filing",
            language=state.language,
            metadata={"bbox": bbox, "row_cells": tuple(row), "table_headers": tuple(headers)},
        ))


def _emit_pdf_table(state: _PdfParseState, page_number: int, table_index: int, table: Any) -> None:
    normalized_rows = [
        ["" if cell is None else str(cell).strip() for cell in row]
        for row in (table.extract() or [])
    ]
    headers = next((row for row in normalized_rows if any(cell for cell in row)), [])
    bbox = tuple(float(value) for value in table.bbox)
    for row_index, row in enumerate(normalized_rows):
        _emit_pdf_row(state, page_number, table_index, row_index, row, headers, bbox)


def _emit_pdf_tables(state: _PdfParseState, document: Any, page_number: int) -> None:
    try:
        finder = document.load_page(page_number - 1).find_tables()
        for table_index, table in enumerate(finder.tables):
            _emit_pdf_table(state, page_number, table_index, table)
    except Exception as exc:
        state.errors.append(f"page_table:{page_number}:{type(exc).__name__}")


def _emit_pdf_page(
    state: _PdfParseState, document: Any, page_number: int,
    blocks: Sequence[tuple[int, tuple[float, ...], str]],
) -> None:
    page_unit_count = len(state.units)
    qa_page = _emit_pdf_text_units(state, page_number, blocks)
    if page_number in state.table_scan_pages:
        qa_unit_start = len(state.units)
        _emit_pdf_tables(state, document, page_number)
        if qa_page and not any(
            unit.unit_kind == "pdf_table_qa_fragment" for unit in state.units[qa_unit_start:]
        ):
            state.opaque_pages.append(page_number)
    if len(state.units) == page_unit_count and page_number not in state.opaque_pages:
        state.opaque_pages.append(page_number)


def parse_pdf(
    path: Path,
    *,
    source_id: str,
    source_sha256: str,
    parser_version: str = NARRATIVE_PARSER_VERSION,
    language: str = "zh",
    full_table_scan: bool = False,
    table_pages: Sequence[int] | None = None,
) -> NarrativeParseResult:
    """Scan every page cheaply, then detect tables only on candidate pages.

    Set ``full_table_scan`` only for bounded negative-control documents or a
    review run that needs complete table coverage. Unscanned table pages are
    reported as deferred, so the selector cannot auto-skip that document.
    """
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise RuntimeError("PDF parsing requires the optional PyMuPDF dependency") from exc

    state = _PdfParseState(source_id, source_sha256, parser_version, language)
    with fitz.open(path) as document:
        state.page_count = len(document)
        _scan_pdf_pages(state, document)
        state.table_scan_pages = _pdf_table_scan_pages(state, full_table_scan, table_pages)
        for page_number, blocks in state.page_blocks:
            _emit_pdf_page(state, document, page_number, blocks)
    return NarrativeParseResult(
        source_id=source_id, source_sha256=source_sha256, language=language,
        units=_link_cross_page_qa(state.units), page_count=state.page_count,
        pages_read=state.pages_read, opaque_pages=tuple(state.opaque_pages),
        table_scan_pages=tuple(sorted(state.table_scan_pages)),
        deferred_table_pages=tuple(sorted(
            set(range(1, state.page_count + 1)) - state.table_scan_pages
        )),
        errors=tuple(state.errors),
    )


def _speaker_role(name: str, title: str, *, qa_mode: bool, management_speakers: set[str]) -> str:
    lowered = f"{name} {title}".casefold()
    if "operator" in lowered or "conference operator" in lowered:
        return "operator"
    if re.search(r"analyst|j\.p\. morgan|ubs|goldman|morgan stanley|barclays", lowered):
        return "analyst"
    if name in management_speakers or re.search(
        r"ceo|cfo|chief|president|executive|officer|investor relations|management", lowered
    ):
        return "management"
    return "analyst" if qa_mode else "management"


def _trimmed_range(text: str, start: int, end: int) -> tuple[int, int, str]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end, text[start:end]


def _transcript_sentence_fragments(text: str) -> list[tuple[int, int, str]]:
    """Split a speaker turn into replayable sentence fragments."""
    fragments: list[tuple[int, int, str]] = []
    start = 0
    for match in re.finditer(r"[.!?][\"')\]]*\s+(?=[A-Z0-9])", text):
        if _abbreviation_before_boundary(text, match.start()):
            continue
        boundary_end = match.start() + 1
        while boundary_end < match.end() and text[boundary_end] in "\"')]”’":
            boundary_end += 1
        left, right, value = _trimmed_range(text, start, boundary_end)
        if value:
            fragments.append((left, right, value))
        start = match.end()
    left, right, value = _trimmed_range(text, start, len(text))
    if value:
        fragments.append((left, right, value))
    return fragments or [(0, len(text), text)]


def _abbreviation_before_boundary(text: str, boundary: int) -> bool:
    if text[boundary] != ".":
        return False
    prior_token = re.search(r"([A-Za-z](?:[A-Za-z.]*)?)$", text[:boundary])
    if prior_token is None:
        return False
    token = prior_token.group(1)
    abbreviations = {"mr", "mrs", "ms", "dr", "prof", "inc", "ltd", "e.g", "i.e"}
    return token.casefold().strip(".") in abbreviations or len(token.replace(".", "")) == 1


@dataclass
class _TranscriptParseState:
    qa_mode: bool = False
    management_speakers: set[str] = field(default_factory=set)
    blocks: list[dict[str, Any]] = field(default_factory=list)
    active: dict[str, Any] | None = None
    active_qa: int | str | None = None
    current_qa_parent: int | None = None
    qa_counter: int = 0


def _transcript_speaker_fields(stripped: str) -> tuple[str | None, str | None, str | None]:
    label = _SPEAKER_LABEL.match(stripped)
    if label:
        return label.group("name").strip(), label.group("title").strip(), ""
    inline = _SPEAKER_LINE.match(stripped)
    if inline:
        return (
            inline.group("name").strip(),
            (inline.group("title") or "").strip(),
            inline.group("body").strip(),
        )
    return None, None, None


def _transcript_answer_group(
    state: _TranscriptParseState, name: str, title: str, body: str
) -> None:
    if state.current_qa_parent is None:
        return
    cue_text = f"{name} {title} {body}"
    if _QA_FIRST_REFERENCE.search(cue_text):
        state.active_qa = f"{state.current_qa_parent}:q1"
    elif _QA_SECOND_REFERENCE.search(cue_text):
        state.active_qa = f"{state.current_qa_parent}:q2"
    elif state.active_qa is None:
        state.active_qa = state.current_qa_parent


def _begin_transcript_speaker(
    state: _TranscriptParseState, line_number: int,
    name: str, title: str, body: str,
) -> None:
    role = _speaker_role(
        name, title, qa_mode=state.qa_mode,
        management_speakers=state.management_speakers,
    )
    if not state.qa_mode and role == "management":
        state.management_speakers.add(name)
    if state.qa_mode and role == "analyst":
        state.qa_counter += 1
        state.current_qa_parent = state.qa_counter
        state.active_qa = state.current_qa_parent
    if state.qa_mode and role == "management":
        _transcript_answer_group(state, name, title, body)
    state.active = {
        "line_start": line_number, "line_end": line_number,
        "name": name, "title": title, "role": role,
        "qa_group_id": state.active_qa if state.qa_mode else None,
        "section": "qa" if state.qa_mode else "prepared_remarks",
        "lines": [body] if body else [],
    }
    state.blocks.append(state.active)


def _consume_transcript_line(
    state: _TranscriptParseState, line_number: int, line: str
) -> None:
    stripped = line.strip()
    if not stripped:
        if state.active is not None:
            state.active["lines"].append("")
        return
    if _QA_HEADING.match(stripped):
        state.qa_mode = True
        state.active = None
        return
    transition_after_line = bool(_QA_TRANSITION.search(stripped))
    name, title, body = _transcript_speaker_fields(stripped)
    if _is_transcript_speaker(name):
        _begin_transcript_speaker(state, line_number, name, title or "", body or "")
        if transition_after_line:
            state.qa_mode = True
        return
    if _append_transcript_unattributed(state, line_number, line, stripped) and transition_after_line:
        state.qa_mode = True


def _is_transcript_speaker(name: str | None) -> bool:
    return bool(name and name.casefold() not in {"prepared remarks", "questions & answers"})


def _append_transcript_unattributed(
    state: _TranscriptParseState, line_number: int, line: str, stripped: str
) -> bool:
    if state.active is None:
        if _EDITORIAL.search(stripped):
            return False
        # Keep unattributed text visible for review, but not as management evidence.
        state.active = {
            "line_start": line_number, "line_end": line_number,
            "name": "", "title": "", "role": "unknown",
            "qa_group_id": state.active_qa if state.qa_mode else None,
            "section": "qa" if state.qa_mode else "prepared_remarks", "lines": [],
        }
        state.blocks.append(state.active)
    state.active["lines"].append(line)
    state.active["line_end"] = line_number
    return True


def _analyst_question_pieces(
    body: str, role: str
) -> list[tuple[int, int, str]]:
    pieces = [(0, len(body), body)]
    if role != "analyst":
        return pieces
    split_points = list(_ANALYST_SUBQUESTION.finditer(body))
    if not split_points:
        return pieces
    pieces = []
    piece_start = 0
    for match in split_points:
        if match.start() > piece_start:
            pieces.append(_trimmed_range(body, piece_start, match.start()))
            piece_start = match.start()
    if piece_start < len(body):
        pieces.append(_trimmed_range(body, piece_start, len(body)))
    return [piece for piece in pieces if piece[2]]


def _transcript_piece_group(
    block: Mapping[str, Any], pieces: Sequence[tuple[int, int, str]], question_index: int
) -> int | str | None:
    parent_group = block["qa_group_id"]
    if block["role"] == "analyst" and len(pieces) > 1 and parent_group is not None:
        return f"{parent_group}:q{question_index}"
    return parent_group


def _transcript_piece_units(
    block: Mapping[str, Any], piece: tuple[int, int, str], group_id: int | str | None,
    source_id: str, parser_version: str, language: str,
) -> list[NarrativeUnit]:
    question_start, _question_end, question_text = piece
    start_line = int(block["line_start"])
    end_line = int(block["line_end"])
    units: list[NarrativeUnit] = []
    for local_start, local_end, piece_text in _transcript_sentence_fragments(question_text):
        char_start = question_start + local_start
        char_end = question_start + local_end
        coords = EvidenceCoordinates(
            paragraph_index=start_line - 1, char_start=char_start, char_end=char_end,
        )
        units.append(_make_unit(
            source_id=source_id, parser_version=parser_version,
            coordinates=coords, raw_text=piece_text,
            unit_kind="transcript_speaker_block", source_role=block["role"],
            language=language,
            metadata={
                "line_end": end_line, "line_start": start_line,
                "text_char_end": char_end, "text_char_start": char_start,
                "qa_group_id": group_id, "qa_parent_id": block["qa_group_id"],
                "section": block["section"], "speaker": block["name"] or None,
                "speaker_title": block["title"] or None,
            },
        ))
    return units


def _transcript_block_units(
    block: Mapping[str, Any], source_id: str, parser_version: str, language: str
) -> list[NarrativeUnit]:
    body = "\n".join(block["lines"]).strip()
    if not body:
        return []
    pieces = _analyst_question_pieces(body, str(block["role"]))
    units: list[NarrativeUnit] = []
    for question_index, piece in enumerate(pieces, start=1):
        group_id = _transcript_piece_group(block, pieces, question_index)
        units.extend(_transcript_piece_units(
            block, piece, group_id, source_id, parser_version, language,
        ))
    return units


def parse_transcript_text(
    text: str,
    *,
    source_id: str,
    source_sha256: str,
    parser_version: str = NARRATIVE_PARSER_VERSION,
    language: str = "en",
) -> NarrativeParseResult:
    """Split known transcript layouts by speaker while preserving source lines."""
    if not isinstance(text, str):
        raise TypeError("transcript text must be a string")
    raw_lines = text.splitlines()
    start_index = next(
        (index for index, line in enumerate(raw_lines) if _TRANSCRIPT_START.match(line.strip())),
        None,
    )
    if start_index is None:
        return NarrativeParseResult(
            source_id=source_id, source_sha256=source_sha256, language=language,
            units=(), line_count=len(raw_lines), errors=("transcript_start_missing",),
        )
    state = _TranscriptParseState()
    for line_number, line in enumerate(raw_lines[start_index + 1 :], start=start_index + 2):
        if _TRANSCRIPT_END.match(line.strip()):
            break
        _consume_transcript_line(state, line_number, line)
    units = [
        unit for block in state.blocks
        for unit in _transcript_block_units(block, source_id, parser_version, language)
    ]
    return NarrativeParseResult(
        source_id=source_id, source_sha256=source_sha256, language=language,
        units=tuple(units), line_count=len(raw_lines),
    )


def _roundtrip_key(
    *, locator: str, raw_text: str, role: str, unit_kind: str
) -> tuple[str, str, str, str]:
    return (
        locator,
        hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
        role,
        unit_kind,
    )


def _unit_roundtrip_key(unit: NarrativeUnit) -> tuple[str, str, str, str]:
    return _roundtrip_key(
        locator=unit.coordinates.locator(),
        raw_text=unit.raw_text,
        role=unit.source_role,
        unit_kind=unit.unit_kind,
    )


def _span_roundtrip_key(span: EvidenceSpan) -> tuple[str, str, str, str]:
    return _roundtrip_key(
        locator=span.coordinates.locator(),
        raw_text=span.raw_text or "",
        role=str(span.structured_value.get("source_role", "unknown")),
        unit_kind=str(span.structured_value.get("unit_kind", "")),
    )


def verify_pdf_evidence_spans(
    path: Path,
    *,
    source_id: str,
    source_sha256: str,
    evidence_spans: Sequence[EvidenceSpan],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Re-read the hashed PDF and verify selected page/table snippets exactly."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != source_sha256:
        raise ValueError("PDF changed before evidence locator round-trip")
    if any(span.source_id != source_id for span in evidence_spans):
        raise ValueError("evidence source_id does not match the requested PDF")
    versions = {span.parser_version for span in evidence_spans}
    if len(versions) > 1:
        raise ValueError("round-trip verification requires one parser version")
    parser_version = next(iter(versions), NARRATIVE_PARSER_VERSION)
    table_pages = sorted(
        {
            span.coordinates.page_number
            for span in evidence_spans
            if span.coordinates.table_index is not None
            and span.coordinates.page_number is not None
        }
    )
    replay = parse_pdf(
        path,
        source_id=source_id,
        source_sha256=source_sha256,
        parser_version=parser_version,
        table_pages=table_pages,
    )
    available: dict[tuple[str, str, str, str], list[NarrativeUnit]] = {}
    for unit in replay.units:
        available.setdefault(_unit_roundtrip_key(unit), []).append(unit)

    verified: list[str] = []
    failed: list[str] = []
    for span in evidence_spans:
        matches = available.get(_span_roundtrip_key(span), [])
        if not matches:
            failed.append(span.span_id)
            continue
        if span.structured_value.get("unit_kind") == "pdf_table_qa_fragment":
            expected = span.structured_value
            if not any(
                unit.metadata.get("cell_sha256") == expected.get("cell_sha256")
                and unit.metadata.get("cell_fragment_start")
                == expected.get("cell_fragment_start")
                and unit.metadata.get("cell_fragment_end") == expected.get("cell_fragment_end")
                for unit in matches
            ):
                failed.append(span.span_id)
                continue
        verified.append(span.span_id)
    return tuple(verified), tuple(failed)


def verify_transcript_evidence_spans(
    text: str,
    *,
    source_id: str,
    source_sha256: str,
    evidence_spans: Sequence[EvidenceSpan],
    language: str = "en",
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Replay TXT line parsing and verify selected speaker blocks exactly."""
    if any(span.source_id != source_id for span in evidence_spans):
        raise ValueError("evidence source_id does not match the requested transcript")
    versions = {span.parser_version for span in evidence_spans}
    if len(versions) > 1:
        raise ValueError("round-trip verification requires one parser version")
    parser_version = next(iter(versions), NARRATIVE_PARSER_VERSION)
    replay = parse_transcript_text(
        text,
        source_id=source_id,
        source_sha256=source_sha256,
        parser_version=parser_version,
        language=language,
    )
    available = {_unit_roundtrip_key(unit) for unit in replay.units}
    verified = tuple(
        span.span_id for span in evidence_spans if _span_roundtrip_key(span) in available
    )
    failed = tuple(
        span.span_id for span in evidence_spans if _span_roundtrip_key(span) not in available
    )
    return verified, failed


def classify_document_kind(title: str, existing_kind: str = "unknown") -> str:
    # Order is significant: offering documents outrank a generic prospectus,
    # and a half-year report outranks the broader annual-report expression.
    patterns = (
        (r"可转换公司债券|可转债", "convertible_bond_prospectus"),
        (r"向特定对象发行股票|定向增发|增发新股|非公开发行股票", "equity_offering_prospectus"),
        (r"投资者关系管理办法|投资者关系管理制度", "ir_policy"),
        (r"关于召开.*(?:业绩说明会|投资者说明会)|会议通知", "meeting_notice"),
        (r"招股说明书", "prospectus"),
        (r"半年度报告|半年报", "semi_annual_report"),
        (r"年度报告|年报", "annual_report"),
        (r"季度报告|季报", "quarterly_report"),
        (r"投资者关系|活动记录", "investor_relations"),
        (r"earnings_call|transcript", "investor_call_transcript"),
    )
    for pattern, kind in patterns:
        if re.search(pattern, title.casefold()):
            return kind
    return existing_kind


def _topics(text: str) -> tuple[str, ...]:
    return tuple(
        topic
        for topic, phrases in _SIGNALS.items()
        if any(phrase.casefold() in text.casefold() for phrase in phrases)
    )


def _table_scan_signal(text: str) -> bool:
    """Limit expensive table discovery to pages with specific business events."""
    if _QA_QUESTION.search(text) or _QA_ANSWER.search(text):
        return True
    topics = _topics(text)
    if not topics:
        return False
    if any(pattern.search(text) for pattern in (_HIGH_VALUE_EVENT, _PROJECT_PLAN, _STRATEGIC_PLAN)):
        return True
    return "industry_dynamics" in topics and bool(_RECENCY.search(text))


def _financial_table(unit: NarrativeUnit, topics: Sequence[str]) -> bool:
    if unit.unit_kind != "pdf_table_row":
        return False
    numeric_cells, financial_label, financial_header, event_signal = _financial_row_signals(unit)
    if numeric_cells >= 2 and not event_signal:
        return True
    if not topics and (financial_label or financial_header):
        return True
    if not financial_label or numeric_cells < 1:
        return False
    return not _has_business_table_topics(topics)


def _financial_row_signals(unit: NarrativeUnit) -> tuple[int, bool, bool, bool]:
    headers = " ".join(str(value) for value in unit.metadata.get("table_headers", ()))
    cells = unit.metadata.get("row_cells", ())
    numeric_cells = _numeric_financial_cells(cells)
    financial_label = bool(_FINANCIAL_TERMS.search(unit.raw_text))
    financial_header = bool(_FINANCIAL_HEADERS.search(headers))
    event_signal = bool(_HIGH_VALUE_EVENT.search(unit.raw_text) or _PROJECT_PLAN.search(unit.raw_text))
    return numeric_cells, financial_label, financial_header, event_signal


def _numeric_financial_cells(cells: Sequence[Any]) -> int:
    return sum(
        1 for cell in cells if re.fullmatch(r"[\d,.%()\-+年月日亿元万股\s]+", str(cell))
    )


def _has_business_table_topics(topics: Sequence[str]) -> bool:
    return any(topic in topics for topic in ("products_rd", "capacity_projects"))


def _pdf_context_groups(
    units: Sequence[NarrativeUnit],
) -> tuple[tuple[str, tuple[NarrativeUnit, ...], str], ...]:
    """Reassemble visually continuous PDF line fragments for selection only.

    Evidence remains stored as independently replayable source spans. These
    transient groups let the selector recognize a sentence split across PDF
    text blocks without inventing a cross-block locator.
    """
    by_page: dict[int, list[NarrativeUnit]] = {}
    for unit in units:
        if unit.unit_kind != "pdf_text_block" or unit.source_role == "qa_text_shadow":
            continue
        page = unit.coordinates.page_number
        if page is not None:
            by_page.setdefault(page, []).append(unit)

    result: list[tuple[str, tuple[NarrativeUnit, ...], str]] = []
    for page, page_units in sorted(by_page.items()):
        ordered = sorted(
            page_units,
            key=lambda unit: (
                unit.coordinates.paragraph_index or 0,
                unit.coordinates.char_start or 0,
            ),
        )
        clusters: list[list[NarrativeUnit]] = []

        def visual_continuation(previous: NarrativeUnit, current: NarrativeUnit) -> bool:
            if previous.source_role != current.source_role:
                return False
            if (
                _PROJECT_SECTION_HEADING.search(previous.raw_text)
                or _BUSINESS_SECTION_HEADING.search(previous.raw_text)
                or _HEADING_ONLY.search(previous.raw_text)
            ):
                return False
            if (
                _PROJECT_SECTION_HEADING.search(current.raw_text)
                or _BUSINESS_SECTION_HEADING.search(current.raw_text)
                or _HEADING_ONLY.search(current.raw_text)
            ):
                return False
            previous_block = previous.metadata.get("pdf_block")
            current_block = current.metadata.get("pdf_block")
            if previous_block is not None and previous_block == current_block:
                return True
            previous_bbox = previous.metadata.get("bbox")
            current_bbox = current.metadata.get("bbox")
            if not (
                isinstance(previous_bbox, Sequence)
                and isinstance(current_bbox, Sequence)
                and len(previous_bbox) == 4
                and len(current_bbox) == 4
            ):
                return False
            vertical_gap = float(current_bbox[1]) - float(previous_bbox[3])
            if vertical_gap < -1.0 or vertical_gap > 16.0:
                return False
            horizontal_overlap = max(
                0.0,
                min(float(previous_bbox[2]), float(current_bbox[2]))
                - max(float(previous_bbox[0]), float(current_bbox[0])),
            )
            narrower_width = min(
                float(previous_bbox[2]) - float(previous_bbox[0]),
                float(current_bbox[2]) - float(current_bbox[0]),
            )
            return narrower_width > 0 and horizontal_overlap / narrower_width >= 0.60

        for unit in ordered:
            if clusters and visual_continuation(clusters[-1][-1], unit):
                clusters[-1].append(unit)
            else:
                clusters.append([unit])

        for cluster in clusters:
            members = tuple(cluster)
            pieces: list[str] = []
            previous: NarrativeUnit | None = None
            for unit in members:
                if previous is None:
                    pieces.append(unit.raw_text)
                else:
                    same_block = previous.metadata.get("pdf_block") == unit.metadata.get("pdf_block")
                    contiguous = (
                        same_block
                        and previous.metadata.get("block_char_end")
                        == unit.metadata.get("block_char_start")
                    )
                    separator = "" if contiguous or unit.language.startswith("zh") else " "
                    pieces.append(separator + unit.raw_text)
                previous = unit
            text = "".join(pieces)
            member_key = "|".join(unit.unit_id for unit in members)
            identity = hashlib.sha256(
                f"{members[0].source_id}:{page}:{member_key}".encode("utf-8")
            ).hexdigest()
            result.append((f"urn:company-wiki:context-group:sha256:{identity}", members, text))
    return tuple(result)


def _minimal_matching_unit_windows(
    units: Sequence[NarrativeUnit], pattern: re.Pattern[str]
) -> tuple[tuple[int, int], ...]:
    """Return smallest contiguous unit windows whose joined text matches."""
    matches: set[tuple[int, int]] = set()
    for start in range(len(units)):
        pieces: list[str] = []
        for end in range(start, len(units)):
            if pieces and not units[end].language.startswith("zh"):
                pieces.append(" ")
            pieces.append(units[end].raw_text)
            if pattern.search("".join(pieces)):
                matches.add((start, end))
                break
    minimal = [candidate for candidate in matches if _window_is_minimal(candidate, matches)]
    return tuple(sorted(minimal, key=lambda item: (item[0], item[1])))


def _window_is_minimal(
    candidate: tuple[int, int], matches: set[tuple[int, int]]
) -> bool:
    return not any(
        other != candidate
        and candidate[0] <= other[0]
        and other[1] <= candidate[1]
        for other in matches
    )


def select_narrative_evidence(
    parsed: NarrativeParseResult,
    *,
    title: str,
    existing_kind: str = "unknown",
    max_selected: int | None = None,
) -> NarrativeEvidencePackage:
    """Select compact narrative spans; incomplete scans can never auto-skip."""
    document_kind = classify_document_kind(title, existing_kind)
    if max_selected is None:
        max_selected = (
            _PROSPECTUS_MAX_SELECTED
            if document_kind
            in {"prospectus", "convertible_bond_prospectus", "equity_offering_prospectus"}
            else _DEFAULT_MAX_SELECTED
        )
    if max_selected < 1:
        raise ValueError("max_selected must be positive")
    candidates: list[tuple[NarrativeUnit, tuple[str, ...], tuple[str, ...], int]] = []
    selection_group_ids: dict[str, str] = {}
    dropped_financial = 0
    for unit in parsed.units:
        if unit.source_role in {
            "analyst", "investor_question", "operator", "editorial", "qa_text_shadow"
        }:
            continue
        topics = _topics(unit.raw_text)
        if _financial_table(unit, topics):
            dropped_financial += 1
            continue
        unit_event_signal = bool(_HIGH_VALUE_EVENT.search(unit.raw_text))
        unit_project_rationale_signal = bool(_PROJECT_RATIONALE_SIGNAL.search(unit.raw_text))
        unit_project_signal = bool(
            _PROJECT_PLAN.search(unit.raw_text)
            or _STRATEGIC_PLAN.search(unit.raw_text)
            or _DOWNSTREAM_BUSINESS_EXTENSION.search(unit.raw_text)
        )
        unit_positioning_signal = bool(_SPECIFIC_BUSINESS_POSITIONING.search(unit.raw_text))
        unit_risk_signal = bool(_BUSINESS_RISK_SIGNAL.search(unit.raw_text))
        if not topics and not unit_event_signal and not unit_project_signal and not (
            unit_positioning_signal or unit_risk_signal or unit_project_rationale_signal
        ):
            continue
        if not topics:
            topics = (
                ("new_business",)
                if unit_event_signal or unit_positioning_signal
                else ("capacity_projects",)
            )
        if len(unit.raw_text) < 12 or _TABLE_OF_CONTENTS.search(unit.raw_text):
            continue
        if _ACCOUNTING_CONTEXT.search(unit.raw_text) or _HEADING_ONLY.search(unit.raw_text):
            continue
        has_progress = bool(_PROGRESS.search(unit.raw_text))
        has_event = bool(_HIGH_VALUE_EVENT.search(unit.raw_text))
        has_positioning = bool(_SPECIFIC_BUSINESS_POSITIONING.search(unit.raw_text))
        has_business_risk = bool(_BUSINESS_RISK_SIGNAL.search(unit.raw_text))
        has_direct_capacity_constraint = bool(
            _DIRECT_CAPACITY_CONSTRAINT.search(unit.raw_text)
        )
        has_long_customer_qualification = bool(
            _LONG_CUSTOMER_QUALIFICATION.search(unit.raw_text)
        )
        has_project_certification_timeline = bool(
            _PROJECT_CERTIFICATION_TIMELINE.search(unit.raw_text)
        )
        has_permit_milestone = bool(_PERMIT_ACQUIRED_MILESTONE.search(unit.raw_text))
        has_new_product_milestone = bool(
            _NEW_PRODUCT_COMMERCIALIZATION.search(unit.raw_text)
        )
        has_project_rationale = bool(_PROJECT_RATIONALE_SIGNAL.search(unit.raw_text))
        has_downstream_extension = bool(
            _DOWNSTREAM_BUSINESS_EXTENSION.search(unit.raw_text)
        )
        has_current_industry_signal = (
            "industry_dynamics" in topics and bool(_RECENCY.search(unit.raw_text))
        )
        has_project_signal = bool(
            _PROJECT_PLAN.search(unit.raw_text)
            or _STRATEGIC_PLAN.search(unit.raw_text)
            or has_project_certification_timeline
        )
        # Topic words alone are too broad (for example, a static list of
        # products or generic R&D language). Require evidence of a change,
        # project, or current industry development before selecting a unit.
        if not (
            has_event
            or has_project_signal
            or has_positioning
            or has_business_risk
            or has_project_rationale
            or has_project_certification_timeline
            or (has_progress and has_current_industry_signal)
        ):
            continue
        if _STATIC_DEFINITION.search(unit.raw_text):
            continue
        reasons = ["business_narrative_signal"]
        if has_progress:
            reasons.append("progress_or_change_language")
        if has_event:
            reasons.append("specific_business_event")
        if has_positioning:
            reasons.append("specific_emerging_business_positioning")
        if has_business_risk:
            reasons.append("business_risk_or_constraint")
        if has_direct_capacity_constraint:
            reasons.append("direct_capacity_constraint")
        if has_long_customer_qualification:
            reasons.append("long_customer_qualification_cycle")
        if has_project_certification_timeline:
            reasons.append("project_certification_timeline")
        if has_permit_milestone:
            reasons.append("permit_acquired_milestone")
        if has_new_product_milestone:
            reasons.append("new_product_commercialization_milestone")
        if has_project_rationale:
            reasons.append("specific_project_rationale")
        if has_downstream_extension:
            reasons.append("downstream_business_extension")
        if has_project_signal:
            reasons.append("project_plan_or_status")
        if has_current_industry_signal:
            reasons.append("current_industry_context")
        if unit.source_role == "management":
            reasons.append("management_statement")
        score = (
            len(topics)
            + (2 if has_progress else 0)
            + (3 if has_event else 0)
            + (2 if has_positioning else 0)
            + (2 if has_business_risk else 0)
            + (2 if has_direct_capacity_constraint else 0)
            + (2 if has_long_customer_qualification else 0)
            + (4 if has_project_certification_timeline else 0)
            + (2 if has_permit_milestone else 0)
            + (2 if has_new_product_milestone else 0)
            + (4 if has_project_rationale else 0)
            + (3 if has_downstream_extension else 0)
        )
        if unit.unit_kind == "pdf_table_row":
            score += 1
        candidates.append((unit, topics, tuple(reasons), score))

    # PDF layout extraction often separates one logical sentence into several
    # adjacent text blocks. Evaluate those fragments together, then retain the
    # original locators as a grouped set of evidence spans. Prospectus project
    # sections also supply local context for their following body paragraphs.
    pdf_groups = _pdf_context_groups(parsed.units)
    project_context_group_ids: set[str] = set()
    project_context_scores: dict[str, int] = {}
    business_context_group_ids: set[str] = set()
    business_context_scores: dict[str, int] = {}
    if document_kind in {
        "convertible_bond_prospectus",
        "equity_offering_prospectus",
    }:
        groups_by_page: dict[int, list[tuple[str, tuple[NarrativeUnit, ...], str]]] = {}
        for group in pdf_groups:
            page = group[1][0].coordinates.page_number
            if page is not None:
                groups_by_page.setdefault(page, []).append(group)
        for page_groups in groups_by_page.values():
            active_project_context = False
            remaining_context_chars = 0
            active_context_score = 0
            for group_id, _members, group_text in page_groups:
                if _PROJECT_SECTION_HEADING.search(group_text):
                    active_project_context = True
                    remaining_context_chars = 1_600
                    active_context_score = 120 if re.search(
                        r"项目建设.{0,8}必要性|项目建设必要性", group_text
                    ) else 80
                    continue
                if active_project_context and _HEADING_ONLY.search(group_text):
                    active_project_context = False
                    remaining_context_chars = 0
                    active_context_score = 0
                    continue
                if active_project_context:
                    if remaining_context_chars <= 0:
                        active_project_context = False
                        continue
                    project_context_group_ids.add(group_id)
                    project_context_scores[group_id] = active_context_score
                    remaining_context_chars -= len(group_text)

    if document_kind == "prospectus":
        groups_by_page = {}
        for group in pdf_groups:
            page = group[1][0].coordinates.page_number
            if page is not None:
                groups_by_page.setdefault(page, []).append(group)
        for page_groups in groups_by_page.values():
            active_business_context = False
            remaining_context_chars = 0
            for group_id, _members, group_text in page_groups:
                if _BUSINESS_SECTION_HEADING.search(group_text):
                    active_business_context = True
                    remaining_context_chars = 1_200
                    continue
                if active_business_context and _HEADING_ONLY.search(group_text):
                    active_business_context = False
                    remaining_context_chars = 0
                    continue
                if active_business_context:
                    if remaining_context_chars <= 0:
                        active_business_context = False
                        continue
                    business_context_group_ids.add(group_id)
                    business_context_scores[group_id] = 140
                    remaining_context_chars -= len(group_text)

    candidate_unit_ids_before_context = {item[0].unit_id for item in candidates}
    for group_id, members, group_text in pdf_groups:
        topics = _topics(group_text)
        if _PROJECT_SECTION_HEADING.search(group_text) or _BUSINESS_SECTION_HEADING.search(group_text):
            continue
        in_project_context = group_id in project_context_group_ids
        in_business_context = group_id in business_context_group_ids
        in_context = in_project_context or in_business_context
        has_event = bool(_HIGH_VALUE_EVENT.search(group_text))
        has_positioning = bool(_SPECIFIC_BUSINESS_POSITIONING.search(group_text))
        has_business_risk = bool(_BUSINESS_RISK_SIGNAL.search(group_text))
        has_direct_capacity_constraint = bool(
            _DIRECT_CAPACITY_CONSTRAINT.search(group_text)
        )
        has_long_customer_qualification = bool(
            _LONG_CUSTOMER_QUALIFICATION.search(group_text)
        )
        has_project_certification_timeline = bool(
            _PROJECT_CERTIFICATION_TIMELINE.search(group_text)
        )
        has_quantified_market_coverage_target = bool(
            _QUANTIFIED_MARKET_COVERAGE_TARGET.search(group_text)
        )
        has_permit_milestone = bool(_PERMIT_ACQUIRED_MILESTONE.search(group_text))
        has_new_product_milestone = bool(
            _NEW_PRODUCT_COMMERCIALIZATION.search(group_text)
        )
        has_project_rationale = bool(_PROJECT_RATIONALE_SIGNAL.search(group_text))
        timeline_window_unit_ids: set[str] = set()
        if has_project_certification_timeline:
            # A PDF text block can contain a whole risk subsection. Keep only
            # each certification duration sentence and a necessary short name
            # prefix; promoting the whole block can displace specific evidence.
            windows = _minimal_matching_unit_windows(
                members, _PROJECT_CERTIFICATION_TIMELINE
            )
            expanded_windows: list[tuple[int, int]] = []
            for start, end in windows:
                if start > 0:
                    prefix = members[start - 1]
                    prefix_text = prefix.raw_text.strip()
                    if (
                        prefix.source_role == members[start].source_role
                        and len(prefix_text) <= 12
                        and not re.search(r"[。！？!?；;]$", prefix_text)
                    ):
                        start -= 1
                expanded_windows.append((start, end))
            for window_index, (start, end) in enumerate(expanded_windows):
                timeline_group_id = f"{group_id}:certification-timeline:{window_index}"
                window_members = members[start : end + 1]
                window_text = "".join(unit.raw_text for unit in window_members)
                is_downstream_center_timeline = bool(
                    _DOWNSTREAM_CENTER_CERTIFICATION_TIMELINE.search(window_text)
                )
                for unit in window_members:
                    if unit.source_role in {
                        "analyst", "investor_question", "operator", "editorial", "qa_text_shadow"
                    }:
                        continue
                    if _TABLE_OF_CONTENTS.search(unit.raw_text):
                        continue
                    selection_group_ids[unit.unit_id] = timeline_group_id
                    timeline_window_unit_ids.add(unit.unit_id)
                    existing_index = next(
                        (
                            index
                            for index, candidate in enumerate(candidates)
                            if candidate[0].unit_id == unit.unit_id
                        ),
                        None,
                    )
                    if existing_index is not None:
                        if is_downstream_center_timeline:
                            existing = candidates[existing_index]
                            reasons = tuple(
                                dict.fromkeys(
                                    (*existing[2], "downstream_center_certification_timeline")
                                )
                            )
                            candidates[existing_index] = (
                                existing[0],
                                existing[1],
                                reasons,
                                existing[3] + 2,
                            )
                        continue
                    unit_topics = _topics(unit.raw_text) or topics or ("capacity_projects",)
                    unit_reasons = [
                        "business_narrative_signal",
                        "project_certification_timeline",
                        "project_plan_or_status",
                        "pdf_visual_context_group",
                    ]
                    if is_downstream_center_timeline:
                        unit_reasons.append("downstream_center_certification_timeline")
                    if len(unit.raw_text.strip()) <= 12:
                        unit_reasons.append("short_fragment_continuation")
                    if unit.source_role == "management":
                        unit_reasons.append("management_statement")
                    candidates.append(
                        (unit, unit_topics, tuple(unit_reasons), len(unit_topics) + 4)
                    )
        extension_window_unit_ids: set[str] = set()
        has_downstream_extension = bool(
            _DOWNSTREAM_BUSINESS_EXTENSION.search(group_text)
        )
        if has_downstream_extension:
            windows = _minimal_matching_unit_windows(
                members, _DOWNSTREAM_BUSINESS_EXTENSION
            )
            for window_index, (start, end) in enumerate(windows):
                if start > 0:
                    prefix = members[start - 1]
                    prefix_text = prefix.raw_text.strip()
                    if (
                        prefix.source_role == members[start].source_role
                        and len(prefix_text) <= 160
                        and not re.search(r"[。！？!?；;]$", prefix_text)
                    ):
                        start -= 1
                if end + 1 < len(members):
                    final_text = members[end].raw_text.strip()
                    continuation = members[end + 1]
                    continuation_text = continuation.raw_text.strip()
                    if (
                        continuation.source_role == members[end].source_role
                        and len(continuation_text) <= 160
                        and not re.search(r"[。！？!?；;]$", final_text)
                    ):
                        end += 1
                extension_group_id = f"{group_id}:downstream-extension:{window_index}"
                for unit in members[start : end + 1]:
                    if unit.source_role in {
                        "analyst", "investor_question", "operator", "editorial", "qa_text_shadow"
                    }:
                        continue
                    if _TABLE_OF_CONTENTS.search(unit.raw_text):
                        continue
                    selection_group_ids[unit.unit_id] = extension_group_id
                    extension_window_unit_ids.add(unit.unit_id)
                    existing_index = next(
                        (
                            index
                            for index, candidate in enumerate(candidates)
                            if candidate[0].unit_id == unit.unit_id
                        ),
                        None,
                    )
                    if existing_index is not None:
                        existing = candidates[existing_index]
                        reasons = tuple(
                            dict.fromkeys((*existing[2], "downstream_business_extension"))
                        )
                        candidates[existing_index] = (
                            existing[0],
                            existing[1],
                            reasons,
                            existing[3] + 3,
                        )
                        continue
                    unit_topics = _topics(unit.raw_text) or topics or ("capacity_projects",)
                    candidates.append(
                        (
                            unit,
                            unit_topics,
                            (
                                "business_narrative_signal",
                                "downstream_business_extension",
                                "project_plan_or_status",
                                "pdf_visual_context_group",
                            ),
                            len(unit_topics) + 3,
                        )
                    )
        market_coverage_window_unit_ids: set[str] = set()
        if has_quantified_market_coverage_target:
            windows = _minimal_matching_unit_windows(
                members, _QUANTIFIED_MARKET_COVERAGE_TARGET
            )
            for window_index, (start, end) in enumerate(windows):
                coverage_group_id = f"{group_id}:market-coverage-target:{window_index}"
                for unit in members[start : end + 1]:
                    if unit.source_role in {
                        "analyst", "investor_question", "operator", "editorial", "qa_text_shadow"
                    }:
                        continue
                    if _TABLE_OF_CONTENTS.search(unit.raw_text):
                        continue
                    selection_group_ids[unit.unit_id] = coverage_group_id
                    market_coverage_window_unit_ids.add(unit.unit_id)
                    existing_index = next(
                        (
                            index
                            for index, candidate in enumerate(candidates)
                            if candidate[0].unit_id == unit.unit_id
                        ),
                        None,
                    )
                    if existing_index is not None:
                        existing = candidates[existing_index]
                        reasons = tuple(
                            dict.fromkeys((*existing[2], "quantified_market_coverage_target"))
                        )
                        candidates[existing_index] = (
                            existing[0], existing[1], reasons, existing[3] + 4
                        )
                        continue
                    unit_topics = _topics(unit.raw_text) or topics or ("core_business",)
                    unit_reasons = [
                        "business_narrative_signal",
                        "quantified_market_coverage_target",
                        "project_plan_or_status",
                        "pdf_visual_context_group",
                    ]
                    if len(unit.raw_text.strip()) <= 12:
                        unit_reasons.append("short_fragment_continuation")
                    candidates.append(
                        (unit, unit_topics, tuple(unit_reasons), len(unit_topics) + 4)
                    )
        has_project_certification_timeline = False
        has_downstream_extension = False
        has_project_signal = bool(
            _PROJECT_PLAN.search(group_text)
            or _STRATEGIC_PLAN.search(group_text)
        )
        if (
            not topics
            and not in_context
            and not has_event
            and not has_positioning
            and not has_business_risk
            and not has_project_rationale
            and not has_new_product_milestone
            and not has_project_signal
            and not has_project_certification_timeline
            and not has_quantified_market_coverage_target
        ):
            continue
        if len(group_text) < 12 or _TABLE_OF_CONTENTS.search(group_text):
            continue
        if _ACCOUNTING_CONTEXT.search(group_text) or _STATIC_DEFINITION.search(group_text):
            continue
        has_progress = bool(_PROGRESS.search(group_text))
        has_current_industry_signal = (
            "industry_dynamics" in topics and bool(_RECENCY.search(group_text))
        )
        if not (
            has_event
            or has_positioning
            or has_business_risk
            or has_project_rationale
            or has_new_product_milestone
            or has_project_signal
            or has_project_certification_timeline
            or has_quantified_market_coverage_target
            or (has_progress and has_current_industry_signal)
            or in_context
        ):
            continue
        if not topics:
            if (
                in_project_context
                or has_project_signal
                or has_business_risk
                or has_quantified_market_coverage_target
            ):
                topics = ("capacity_projects",)
            elif in_business_context:
                topics = ("core_business",)
            else:
                topics = ("new_business",)
        reasons = ["business_narrative_signal", "pdf_visual_context_group"]
        if has_progress:
            reasons.append("progress_or_change_language")
        if has_event:
            reasons.append("specific_business_event")
        if has_positioning:
            reasons.append("specific_emerging_business_positioning")
        if has_business_risk:
            reasons.append("business_risk_or_constraint")
        if has_direct_capacity_constraint:
            reasons.append("direct_capacity_constraint")
        if has_long_customer_qualification:
            reasons.append("long_customer_qualification_cycle")
        if has_project_certification_timeline:
            reasons.append("project_certification_timeline")
        if has_quantified_market_coverage_target:
            reasons.append("quantified_market_coverage_target")
        if has_permit_milestone:
            reasons.append("permit_acquired_milestone")
        if has_new_product_milestone:
            reasons.append("new_product_commercialization_milestone")
        if has_project_rationale:
            reasons.append("specific_project_rationale")
        if has_project_signal or in_project_context:
            reasons.append("project_plan_or_status")
        if in_project_context:
            reasons.append("project_section_context")
        if in_business_context:
            reasons.append("business_section_context")
        if has_current_industry_signal:
            reasons.append("current_industry_context")
        score = (
            8
            + len(topics)
            + (2 if has_progress else 0)
            + (3 if has_event else 0)
            + (2 if has_positioning else 0)
            + (2 if has_business_risk else 0)
            + (2 if has_direct_capacity_constraint else 0)
            + (2 if has_long_customer_qualification else 0)
            + (4 if has_project_certification_timeline else 0)
            + (2 if has_permit_milestone else 0)
            + (2 if has_new_product_milestone else 0)
            + (4 if has_project_rationale else 0)
            + (4 if has_quantified_market_coverage_target else 0)
        )
        if in_project_context:
            score += project_context_scores.get(group_id, 40)
        if in_business_context:
            score += business_context_scores.get(group_id, 80)
        if not in_context and any(
            unit.unit_id in candidate_unit_ids_before_context for unit in members
        ):
            # Existing sentence-level candidates already carry the signal. Do
            # not expand every such group into all of its line fragments; the
            # context group is expanded only when selection depends on joined
            # text that no individual member exposes.
            continue
        for unit in members:
            if unit.source_role in {
                "analyst", "investor_question", "operator", "editorial", "qa_text_shadow"
            }:
                continue
            if unit.unit_id in timeline_window_unit_ids:
                continue
            if unit.unit_id in extension_window_unit_ids:
                continue
            if unit.unit_id in market_coverage_window_unit_ids:
                continue
            if _TABLE_OF_CONTENTS.search(unit.raw_text):
                continue
            page_y = unit.metadata.get("bbox")
            if (
                isinstance(page_y, Sequence)
                and len(page_y) == 4
                and (float(page_y[1]) < 60.0 or float(page_y[1]) > 750.0)
            ):
                continue
            selection_group_ids[unit.unit_id] = group_id
            member_topics = _topics(unit.raw_text) or topics
            member_reasons = list(reasons)
            if unit.source_role == "management":
                member_reasons.append("management_statement")
            candidates.append((unit, member_topics, tuple(member_reasons), score))

    # Keep an immediately preceding product/new-business phrase when an event
    # sentence starts with a connector such as “and these four products...”.
    unit_by_location = {
        (unit.coordinates.page_number, unit.coordinates.paragraph_index): unit
        for unit in parsed.units
        if unit.unit_kind == "pdf_text_block"
    }
    candidate_unit_ids = {item[0].unit_id for item in candidates}
    for unit, _topics_for_event, _reasons, _score in tuple(candidates):
        if unit.unit_kind != "pdf_text_block" or not _HIGH_VALUE_EVENT.search(unit.raw_text):
            continue
        page = unit.coordinates.page_number
        paragraph = unit.coordinates.paragraph_index
        previous = unit_by_location.get((page, paragraph - 1))
        if (
            previous is None
            or previous.unit_id in candidate_unit_ids
            or previous.source_role != unit.source_role
            or not (
                set(_topics(previous.raw_text)) & {"new_business", "products_rd", "core_business"}
                or _NAMED_PRODUCT_CONTEXT.search(previous.raw_text)
            )
            or len(previous.raw_text) < 12
            or _ACCOUNTING_CONTEXT.search(previous.raw_text)
        ):
            continue
        current_group = selection_group_ids.get(unit.unit_id)
        previous_group = selection_group_ids.get(previous.unit_id)
        if current_group is not None and previous_group is not None and current_group != previous_group:
            continue
        has_named_product_context = bool(_NAMED_PRODUCT_CONTEXT.search(previous.raw_text))
        adjacent_group_id = current_group or previous_group
        if adjacent_group_id is None:
            pair_key = "|".join(sorted((unit.unit_id, previous.unit_id)))
            pair_sha = hashlib.sha256(
                f"{unit.source_id}:adjacent-context:{pair_key}".encode("utf-8")
            ).hexdigest()
            adjacent_group_id = f"urn:company-wiki:context-group:sha256:{pair_sha}"
        selection_group_ids[unit.unit_id] = adjacent_group_id
        selection_group_ids[previous.unit_id] = adjacent_group_id
        if has_named_product_context:
            for index, item in enumerate(candidates):
                if item[0].unit_id == unit.unit_id:
                    reasons = tuple(
                        dict.fromkeys((*item[2], "named_product_milestone_context"))
                    )
                    candidates[index] = (item[0], item[1], reasons, item[3] + 4)
        candidates.append(
            (
                previous,
                _topics(previous.raw_text),
                (
                    ("adjacent_subject_context", "named_product_milestone_context")
                    if has_named_product_context
                    else ("adjacent_subject_context",)
                ),
                0,
            )
        )
        candidate_unit_ids.add(previous.unit_id)

    # Numbered project-rationale headings can be split by the PDF parser so
    # the final few characters land in a tiny next-paragraph unit (for
    # example, “外协需” + “求旺盛”). Preserve that fragment with its heading
    # instead of dropping it under the normal short-unit filter.
    for unit, _topics_for_heading, _reasons, _score in tuple(candidates):
        if (
            unit.unit_kind != "pdf_text_block"
            or not _PROJECT_RATIONALE_SIGNAL.search(unit.raw_text)
        ):
            continue
        page = unit.coordinates.page_number
        paragraph = unit.coordinates.paragraph_index
        continuation = unit_by_location.get((page, paragraph + 1))
        if (
            continuation is None
            or continuation.unit_id in candidate_unit_ids
            or continuation.source_role != unit.source_role
            or not 1 <= len(continuation.raw_text) < 12
            or not re.search(r"[\u3400-\u9fffA-Za-z0-9]", continuation.raw_text)
            or _TABLE_OF_CONTENTS.search(continuation.raw_text)
            or _ACCOUNTING_CONTEXT.search(continuation.raw_text)
        ):
            continue
        current_group = selection_group_ids.get(unit.unit_id)
        continuation_group = selection_group_ids.get(continuation.unit_id)
        if (
            current_group is not None
            and continuation_group is not None
            and current_group != continuation_group
        ):
            continue
        group_id = current_group or continuation_group
        if group_id is None:
            pair_key = "|".join(sorted((unit.unit_id, continuation.unit_id)))
            pair_sha = hashlib.sha256(
                f"{unit.source_id}:heading-continuation:{pair_key}".encode("utf-8")
            ).hexdigest()
            group_id = f"urn:company-wiki:context-group:sha256:{pair_sha}"
        selection_group_ids[unit.unit_id] = group_id
        selection_group_ids[continuation.unit_id] = group_id
        for index, item in enumerate(candidates):
            if item[0].unit_id == unit.unit_id:
                reasons = tuple(
                    dict.fromkeys((*item[2], "short_fragment_continuation"))
                )
                candidates[index] = (item[0], item[1], reasons, item[3])
        candidates.append(
            (
                continuation,
                _topics(continuation.raw_text),
                ("adjacent_subject_context", "short_fragment_continuation"),
                0,
            )
        )
        candidate_unit_ids.add(continuation.unit_id)

    # A selected management answer can carry its linked analyst/investor
    # question as
    # context. Questions remain separately role-tagged and never support facts.
    selected_ids = {item[0].unit_id for item in candidates}
    qa_groups = {
        item[0].metadata.get("qa_group_id")
        for item in candidates
        if item[0].metadata.get("qa_group_id") is not None
    }
    for unit in parsed.units:
        question_group = unit.metadata.get("qa_group_id")
        linked = any(
            question_group == answer_group
            or (
                question_group is not None
                and answer_group is not None
                and str(question_group).startswith(f"{answer_group}:q")
            )
            for answer_group in qa_groups
        )
        if (
            unit.source_role in {"analyst", "investor_question"}
            and linked
            and unit.unit_id not in selected_ids
        ):
            if not (
                _topics(unit.raw_text)
                or _HIGH_VALUE_EVENT.search(unit.raw_text)
                or "?" in unit.raw_text
                or "？" in unit.raw_text
            ):
                continue
            candidates.append((unit, (), ("linked_question_context",), 0))
            selected_ids.add(unit.unit_id)

    # Keep the best locator when the PDF exposes identical text in both views.
    by_text: dict[tuple[str, int | None, str], tuple[NarrativeUnit, tuple[str, ...], tuple[str, ...], int]] = {}
    for item in candidates:
        unit = item[0]
        text_key = hashlib.sha256(" ".join(unit.raw_text.split()).encode("utf-8")).hexdigest()
        # Suppress duplicate text/table views on the same page while retaining
        # repeated statements on different pages or by different speakers.
        key = (text_key, unit.coordinates.page_number, unit.source_role)
        previous = by_text.get(key)
        if previous is None or (unit.unit_kind == "pdf_table_row" and previous[0].unit_kind != "pdf_table_row"):
            by_text[key] = item
    candidates = sorted(
        by_text.values(),
        key=lambda item: (-item[3], item[0].coordinates.locator(), item[0].unit_id),
    )
    if len(candidates) > max_selected:
        # A long document may contain more high-scoring spans than the budget.
        # Treat each visual context group as one indivisible selection unit:
        # selecting only some line fragments can make a sentence misleading,
        # while appending the rest after the budget is reached violates the
        # caller's hard storage limit.
        def budget_priority(
            item: tuple[NarrativeUnit, tuple[str, ...], tuple[str, ...], int]
        ) -> tuple[int, int, tuple[int | str, ...], str]:
            reasons = set(item[2])
            if reasons & {
                "direct_capacity_constraint",
                "long_customer_qualification_cycle",
            }:
                priority = -1
            elif "downstream_business_extension" in reasons:
                priority = -1
            elif "downstream_center_certification_timeline" in reasons:
                priority = -2
            elif "quantified_market_coverage_target" in reasons:
                priority = -1
            elif "project_certification_timeline" in reasons:
                priority = 0
            elif "named_product_milestone_context" in reasons:
                priority = -1
            elif "permit_acquired_milestone" in reasons:
                priority = 0
            elif "new_product_commercialization_milestone" in reasons:
                priority = 0
            elif "business_risk_or_constraint" in reasons:
                priority = 1
            elif "specific_project_rationale" in reasons:
                priority = 2
            elif "specific_business_event" in reasons:
                priority = 3
            elif "specific_emerging_business_positioning" in reasons:
                priority = 4
            elif "project_plan_or_status" in reasons:
                priority = 5
            elif "current_industry_context" in reasons:
                priority = 6
            else:
                priority = 7
            if _HEADING_ONLY.search(item[0].raw_text):
                priority += 2
            return (
                priority,
                -item[3],
                item[0].coordinates.locator(),
                item[0].unit_id,
            )

        category_order = (
            "critical_risk", "business_extension", "market_coverage_target", "milestone", "project_timeline",
            "named_product_milestone", "product_milestone",
            "risk", "rationale", "event", "positioning", "project", "industry", "other"
        )

        def item_category(
            item: tuple[NarrativeUnit, tuple[str, ...], tuple[str, ...], int]
        ) -> str:
            reasons = set(item[2])
            if reasons & {
                "direct_capacity_constraint",
                "long_customer_qualification_cycle",
            }:
                return "critical_risk"
            if "downstream_business_extension" in reasons:
                return "business_extension"
            if "quantified_market_coverage_target" in reasons:
                return "market_coverage_target"
            if "permit_acquired_milestone" in reasons:
                return "milestone"
            if "project_certification_timeline" in reasons:
                return "project_timeline"
            if "named_product_milestone_context" in reasons:
                return "named_product_milestone"
            if "new_product_commercialization_milestone" in reasons:
                return "product_milestone"
            if "business_risk_or_constraint" in reasons:
                return "risk"
            if "specific_project_rationale" in reasons:
                return "rationale"
            if "specific_business_event" in reasons:
                return "event"
            if "specific_emerging_business_positioning" in reasons:
                return "positioning"
            if "project_plan_or_status" in reasons:
                return "project"
            if "current_industry_context" in reasons:
                return "industry"
            return "other"

        # Build atomic bundles after text deduplication so the budget is
        # measured in the exact spans that will be emitted.
        bundles_by_key: dict[str, dict[str, Any]] = {}
        for item in candidates:
            unit = item[0]
            group_id = selection_group_ids.get(unit.unit_id)
            bundle_key = group_id or f"unit:{unit.unit_id}"
            bundle = bundles_by_key.setdefault(bundle_key, {"items": [], "group_id": group_id})
            bundle["items"].append(item)

        bundles: list[dict[str, Any]] = []
        for bundle_key, bundle in bundles_by_key.items():
            bundle_items = sorted(bundle["items"], key=budget_priority)
            first = bundle_items[0]
            page_number = first[0].coordinates.page_number
            page_key = (
                ("page", str(page_number))
                if page_number is not None
                else ("locator", json.dumps(first[0].coordinates.locator(), sort_keys=True))
            )
            categories = {item_category(item) for item in bundle_items}
            category = min(categories, key=category_order.index)
            bundles.append(
                {
                    "key": bundle_key,
                    "items": bundle_items,
                    "group_id": bundle["group_id"],
                    "page_key": page_key,
                    "category": category,
                    "priority": min(budget_priority(item) for item in bundle_items),
                    "score": max(item[3] for item in bundle_items),
                }
            )

        reserved_bundles: list[dict[str, Any]] = []
        reserved_bundle_keys: set[str] = set()
        for required_reason in (
            "downstream_center_certification_timeline",
            "downstream_business_extension",
        ):
            options = [
                bundle
                for bundle in bundles
                if bundle["key"] not in reserved_bundle_keys
                and any(
                    required_reason in item[2]
                    for item in bundle["items"]
                )
            ]
            options.sort(
                key=lambda bundle: (
                    bundle["priority"][0],
                    -bundle["score"],
                    bundle["items"][0][0].coordinates.page_number or 0,
                    bundle["items"][0][0].coordinates.paragraph_index or 0,
                    bundle["items"][0][0].unit_id,
                    bundle["key"],
                )
            )
            if options:
                candidate = options[0]
                if (
                    sum(len(bundle["items"]) for bundle in reserved_bundles)
                    + len(candidate["items"])
                    <= max_selected
                ):
                    reserved_bundles.append(candidate)
                    reserved_bundle_keys.add(candidate["key"])

        by_page: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for bundle in bundles:
            if bundle["key"] not in reserved_bundle_keys:
                by_page.setdefault(bundle["page_key"], []).append(bundle)
        page_order = sorted(
            by_page,
            key=lambda key: (
                min(category_order.index(bundle["category"]) for bundle in by_page[key]),
                -max(bundle["score"] for bundle in by_page[key]),
                0 if key[0] == "page" else 1,
                key[1],
            ),
        )
        page_bundles: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for page_key, page_items in by_page.items():
            # On each page, preserve one span from each available evidence
            # class before spending the remaining slots on another span of a
            # class already represented. A single risk-plus-event passage is
            # treated as risk first; a separate product milestone can then
            # remain available beside it.
            buckets: dict[str, list[dict[str, Any]]] = {name: [] for name in category_order}
            for bundle in page_items:
                buckets[bundle["category"]].append(bundle)
            for values in buckets.values():
                values.sort(
                    key=lambda bundle: (
                        bundle["priority"],
                        len(bundle["items"]),
                        bundle["key"],
                    )
                )
            staged = [
                values[0]
                for values in buckets.values()
                if values
            ]
            staged_keys = {bundle["key"] for bundle in staged}
            remainder = [bundle for bundle in page_items if bundle["key"] not in staged_keys]
            remainder.sort(
                key=lambda bundle: (
                    category_order.index(bundle["category"]),
                    bundle["priority"],
                    len(bundle["items"]),
                    bundle["key"],
                )
            )
            page_bundles[page_key] = [*staged, *remainder]

        kept = [
            item
            for bundle in reserved_bundles
            for item in bundle["items"]
        ]
        if page_bundles:
            for rank in range(max(len(items) for items in page_bundles.values())):
                for page_key in page_order:
                    page_items = page_bundles.get(page_key, [])
                    if rank < len(page_items):
                        bundle = page_items[rank]
                        bundle_cost = len(bundle["items"])
                        if len(kept) + bundle_cost <= max_selected:
                            kept.extend(bundle["items"])
                        # Oversized bundles are skipped whole. Later smaller
                        # bundles can still use the remaining budget.
    else:
        kept = candidates[:max_selected]
    omitted = max(0, len(candidates) - len(kept))
    kept.sort(key=lambda item: (item[0].coordinates.locator(), item[0].unit_id))
    spans = tuple(
        unit.to_evidence_span(
            topics=topics,
            selection_reasons=reasons,
            selection_group_id=selection_group_ids.get(unit.unit_id),
        )
        for unit, topics, reasons, _score in kept
    )

    if spans:
        if any("locator_unstable" in span.quality_flags for span in spans):
            status: Literal["selected", "partial", "skipped_no_narrative", "needs_review", "blocked"] = "needs_review"
        else:
            status = "selected" if parsed.coverage_complete and omitted == 0 else "partial"
    elif parsed.errors:
        status = "blocked"
    elif not parsed.coverage_complete:
        status = "needs_review"
    elif document_kind in {"ir_policy", "meeting_notice"}:
        status = "skipped_no_narrative"
    else:
        status = "needs_review"

    return NarrativeEvidencePackage(
        source_id=parsed.source_id,
        source_sha256=parsed.source_sha256,
        document_kind=document_kind,
        status=status,
        evidence_spans=spans,
        selection_limit=max_selected,
        candidate_count=len(candidates),
        dropped_financial_count=dropped_financial,
        source_units=len(parsed.units),
        omitted_candidate_count=omitted,
        coverage_complete=parsed.coverage_complete,
    )


def validate_summary_draft(
    draft: SourceSummaryDraft,
    *,
    source_id: str,
    source_sha256: str,
    language: str,
    evidence_spans: Sequence[EvidenceSpan],
) -> None:
    """Validate citations and roles; this is not a semantic truth review."""
    if draft.source_id != source_id or draft.source_sha256 != source_sha256:
        raise SummaryValidationError("summary source identity/hash does not match")
    if draft.language != language:
        raise SummaryValidationError("summary language must match the source language")
    known = {span.span_id: span for span in evidence_spans}
    if not draft.claims:
        raise SummaryValidationError("summary draft must contain at least one claim")
    for claim in draft.claims:
        _validate_summary_claim(claim, known, draft.status)
    # A citation-valid draft remains a draft. Semantic entailment, contradictory
    # evidence, modality, negation, and speaker accuracy require G1 review.


def _validate_summary_claim(
    claim: SummaryClaim, known: Mapping[str, EvidenceSpan], draft_status: str
) -> None:
    if not claim.text.strip():
        raise SummaryValidationError("summary claim text must not be blank")
    if not claim.evidence_ids:
        raise SummaryValidationError("every summary claim requires evidence IDs")
    if set(claim.evidence_ids) - set(known):
        raise SummaryValidationError("summary claim refers to unknown evidence IDs")
    _validate_claim_roles(claim, known)
    _validate_claim_review_status(claim, known, draft_status)


def _validate_claim_roles(claim: SummaryClaim, known: Mapping[str, EvidenceSpan]) -> None:
    roles = {
        known[evidence_id].structured_value.get("source_role", "unknown")
        for evidence_id in claim.evidence_ids
    }
    if claim.claim_type == "company_statement" and not roles <= {"company_filing", "management"}:
        raise SummaryValidationError("non-company evidence cannot support a company statement")
    if claim.claim_type == "analyst_question" and (
        not roles or not roles <= {"analyst", "investor_question"}
    ):
        raise SummaryValidationError("analyst-question claims must cite question evidence only")


def _validate_claim_review_status(
    claim: SummaryClaim, known: Mapping[str, EvidenceSpan], draft_status: str
) -> None:
    cited_spans = [known[evidence_id] for evidence_id in claim.evidence_ids]
    if any("locator_unstable" in span.quality_flags for span in cited_spans):
        if not claim.needs_review or draft_status != "needs_review":
            raise SummaryValidationError("unstable evidence locators require needs_review status")
    if claim.needs_review and draft_status != "needs_review":
        raise SummaryValidationError("review-required claims require a needs_review draft")
