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
from typing import Any, Literal, cast
import unicodedata

from company_wiki.source_contract import EvidenceCoordinates, EvidenceSpan

from .narrative_candidates import CandidateRules, EvidenceCandidate, assess_unit
from .narrative_context import ContextRules, build_section_context
from .narrative_document import (
    NarrativeEvidencePackage,
    NarrativeParseResult,
    NarrativeUnit,
)
from .narrative_group_candidates import (
    GroupCandidateRules,
    enrich_context_groups,
)
from .narrative_finalize import finalize_selection
from .narrative_matching import matching_document, matching_text, original_candidates
from .narrative_neighbors import NeighborRules, enrich_neighbor_context
from .narrative_ocr_groups import build_ocr_context_groups
from .narrative_pdf_groups import PdfGroupRules, build_pdf_context_groups
from .narrative_pdf_qa import QA_FRAGMENT_VERSION, pdf_qa_parts, question_markers
from .narrative_project_context import enrich_fundraising_table_context
from .narrative_replay import (
    prepare_pdf_replay,
    prepare_pdf_replay_bytes,
    span_roundtrip_key as _span_roundtrip_key,
    unit_roundtrip_key as _unit_roundtrip_key,
    verify_replayed_pdf_spans,
)
from .narrative_routing import (
    classify_document_kind as _classify_document_kind,
    route_document,
)


NARRATIVE_PARSER_NAME = "selective_narrative_parser"
NARRATIVE_PARSER_VERSION = QA_FRAGMENT_VERSION
NARRATIVE_SELECTOR_NAME = "select_narrative_evidence"
# 0.4.2 separates customer adoption and binds visual fundraising project rows.
# 0.4.1 preserves specific operating/industry meaning and atomic fact sentences.
# 0.4.0 completes bounded business facts and preserves discourse boundaries.
# 0.3.3 adds context-safe whole-group dedup and fixed-budget category fairness.
# 0.3.2 adds concrete English operating actions and adoption, without brand rules.
# 0.3.1 recognizes administrative English IR policy titles; 0.3.0 added
# concrete current Chinese operating/new-business/overseas progress
# and keeps unrecognized business documents reviewable. The version also pins
# batch generation identity, so old selection results cannot be silently reused.
# Parsing, source bytes and locator construction remain unchanged.
NARRATIVE_SELECTOR_VERSION = "0.6.0"
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
        "景气度", "景气上行",
        "泛半导体产业", "市场发展", "半导体产业",
        "market expansion", "prescription trends", "supply constraints", "capacity constraints",
        "available supply", "demand exceeds", "demand continues", "supply-demand imbalance",
    ),
    "core_business": (
        "主营业务", "核心业务", "业务进展", "业务布局", "生产经营", "主业发展",
        "关键设备领域", "设备市场", "设备产品", "core business", "business development",
        "生产装置", "装置运行", "产销量", "产销率", "产能利用率", "营业规模",
        "commercial operations", "commercial deployment", "distribution network", "sales office",
        "throughput", "operating efficiency",
    ),
    "new_business": (
        "新业务", "第二曲线", "新产品", "新市场", "业务开拓", "新兴业务",
        "投资和并购", "投资并购", "产业链上下游", "新兴领域", "市场布局", "自主研发",
        "new business", "new product", "new market", "pipeline", "model choice",
        "open and custom models", "frontier models", "multiple models", "commercial approach",
        "new model", "new service", "new platform", "new solution",
    ),
    "overseas": (
        "出海", "海外市场", "境外市场", "国际化", "海外客户", "出口业务",
        "海外业务", "境外业务", "海外收入", "境外收入", "出口订单", "境外基地", "海外基地",
        "overseas", "international", "global expansion", "export market",
    ),
    "orders_customers": (
        "订单", "客户验证", "客户导入", "重复订单", "新增客户", "客户需求",
        "客户端验证", "批量订货", "批量订单", "付运量显著提升",
        "order", "customer", "backlog", "qualification", "starter doses", "patient uptake",
        "customer uptake", "prescription growth",
        "pilot agreement", "supply agreement", "pilot deployment",
    ),
    "capacity_projects": (
        "产能", "产线", "中试线", "扩产", "投产", "募投项目", "项目建设", "基地建设",
        "项目以", "精密加工业务", "产业链延伸", "向下游延伸", "零件交付",
        "capacity", "production line", "pilot line", "facility", "capital project",
        "data center", "data centre", "manufacturing site",
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
_BUSINESS_PROGRESS_ACTION = re.compile(
    r"(?:"
    r"(?:主营业务|核心业务|业务线|第二曲线|新业务|新兴业务|新产品|产品线|产品|"
    r"募投项目|项目|产线|产能|海外市场|境外市场|国际市场|海外客户|境外客户|"
    r"客户|订单|交付效率|交付量|本地化服务|服务能力|服务网络|商业化|建设进度|"
    r"验证周期|研发进展|市场覆盖|渠道|团队|生产装置|装置运行|产销量|产销率|产能利用率|"
    r"营业规模|海外业务|境外业务|海外收入|境外收入|出口订单|境外基地|海外基地)"
    r".{0,20}(?:提升|增长|改善|扩大|加快|缩短|收紧|增强|下降|加速|增加|上升|"
    r"完成|建成|投产|量产|试产|交付|获得|取得|通过|新增|进入|拓展|落地|上线|"
    r"扩建|开拓|实现|签约|签订|获批|导入|验证|认证|扩容)|"
    r"(?:完成|建成|投产|量产|试产|交付|获得|取得|通过|新增|进入|拓展|落地|"
    r"上线|扩建|开拓|实现|签约|签订|获批|导入|验证|认证|扩容)"
    r".{0,20}(?:主营业务|核心业务|业务线|第二曲线|新业务|新兴业务|新产品|产品线|"
    r"产品|募投项目|项目|产线|产能|海外市场|境外市场|国际市场|海外客户|境外客户|"
    r"客户|订单|交付效率|交付量|本地化服务|服务能力|服务网络|商业化|建设进度|"
    r"验证周期|研发进展|市场覆盖|渠道|团队|生产装置|装置运行|产销量|产销率|产能利用率|"
    r"营业规模|海外业务|境外业务|海外收入|境外收入|出口订单|境外基地|海外基地)"
    r")",
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
_EXCLUDED_NARRATIVE_CONTEXT = re.compile(
    _ACCOUNTING_CONTEXT.pattern + r"|\b(?:safe[ -]harbou?r|forward[ -]looking statements?)\b|"
    r"\bactual results (?:may|could) differ materially\b",
    re.IGNORECASE,
)
_HEADING_ONLY = re.compile(
    r"^[（(]?[一二三四五六七八九十\d]+[）).、]\s*[^。！？!?；;]{1,24}(?:风险|项目|方案|安排)$"
)
_ENGLISH_OPERATING_OBJECT = (
    r"(?:data cent(?:er|re)s?|manufacturing sites?|production lines?|"
    r"products?|services?|platforms?|solutions?|models?|agents?|"
    r"customers?|users?|paid seats?|workloads?|throughput|capacity)"
)
# A business noun alone is not a milestone. Keep a nearby operating action or
# explicit current adoption count, and exclude a financial subject in the gap.
_ENGLISH_FINANCIAL_MEASURE = r"(?:revenues?|earnings|income|profits?|margins?|EPS|dividends?)"
_ENGLISH_OPERATING_GAP = r"(?:(?!\b" + _ENGLISH_FINANCIAL_MEASURE + r"\b)[^.!?;\n]){0,80}"
_ENGLISH_OPERATING_EVENT = (
    r"\b(?:added|built|opened|expanded|launched|introduced|announced|released|"
    r"deployed|rolled out|increased|scaled|commissioned)\b"
    + _ENGLISH_OPERATING_GAP + r"\b" + _ENGLISH_OPERATING_OBJECT
    + r"\b(?!\s*(?:'s\s+)?" + _ENGLISH_FINANCIAL_MEASURE + r"\b)|"
    r"(?:^|[.!?;\n])\s*" + _ENGLISH_OPERATING_GAP
    + r"\b(?:customers?|users?|paid seats?|workloads?|throughput|capacity)\b"
    + _ENGLISH_OPERATING_GAP + r"\b(?:increased|expanded|grew|doubled|tripled|scaled)\b|"
    r"\b(?:now|currently)\s+(?:have|serve|support)\s+"
    r"(?:(?:over|more than|approximately|about)\s+)?[\d,]+"
    r"(?:\s+\w+){0,6}\s+(?:customers?|users?|seats?|deployments?)\b|"
    r"(?:^|[.!?;\n])\s*" + _ENGLISH_OPERATING_GAP
    + r"\b(?:customers?|users?|seats?|deployments?)\b"
    + _ENGLISH_OPERATING_GAP
    + r"\b(?:surpassed|reached|crossed|now\s+(?:over|above))\s+[\d,]+\b|"
    r"\b(?:reduced|shortened|decreased)\b"
    + _ENGLISH_OPERATING_GAP
    + r"\b(?:dock[- ]to[- ]live|delivery|deployment|lead|fulfillment)\s+times?\b|"
    r"\b(?:transitioning|evolving|shifting|changed|adopting)\b"
    + _ENGLISH_OPERATING_GAP
    + r"\b(?:business|monetization|pricing|subscription)\s+models?\b|"
    r"\b(?:now|currently)\s+(?:have|use|offer)\b"
    + _ENGLISH_OPERATING_GAP
    + r"\b(?:per\s+seat|usage|consumption|subscription|licensing)\s+"
    r"(?:business\s+)?models?\b"
)
_HIGH_VALUE_EVENT = re.compile(
    r"(?:新产品|新业务|第二曲线|新市场).{0,24}(?:推出|发布|验证|认证|量产|试产|投产|销售|订单|客户|开拓|拓展|落地)|"
    r"(?:设立|成立|启动).{0,28}(?:新业务|新产品|新材料|新装置|事业部|研究院|研究所|研发项目)|"
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
    # Require a completed operational action and a specific business object.
    # Neither market/growth vocabulary alone nor finance-only growth qualifies.
    r"\b(?:entered|penetrated|expanded\s+into)\b[^.!?;\n]{0,48}\b(?:new|overseas|international|export)\s+markets?\b|"
    r"\b(?:signed|secured|won|executed)\b[^.!?;\n]{0,36}\b(?:pilot|supply|distribution|commercial|customer)\s+(?:agreements?|contracts?)\b|"
    r"\b(?:began|started|commenced|completed)\b[^.!?;\n]{0,36}\b(?:commercial\s+(?:operations?|deployments?)|pilot\s+(?:deployments?|programs?|projects?))\b|"
    r"\b(?:expanded|established|opened)\b[^.!?;\n]{0,48}\b(?:distribution\s+networks?|sales\s+offices?|commercial\s+operations?)\b|"
    r"(?:launched|validated|commercialized|expanded|entered|signed|won).{0,24}"
    r"(?:new product|new business|overseas|international|customer|order|capacity|facility)|"
    r"model choice|models are an input|model is swappable|multiple models|open and custom models|"
    r"demand.{0,40}(?:exceeds|outstrips).{0,40}(?:available\s+)?(?:supply|capacity)|"
    r"efficiency gains?.{0,60}monetiz|supply-demand imbalance|"
    r"market expansion|starter doses|prescription trends.{0,60}"
    r"(?:increased|declined|grew|slowed|currently|reached|prescriptions)|"
    r"too early to speculate|non-inferiority|superiority|"
    r"(?:phase|trial).{0,35}(?:clinical|superiority|results)|"
    + _ENGLISH_OPERATING_EVENT,
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
    r"新产品.{0,36}(?:通过|获得|完成).{0,12}(?:客户|产品)?认证|"
    r"(?:设备|产品|型号|机型).{0,24}(?:已|已经)(?:进入|通过|完成|获得)"
    r".{0,16}(?:客户端|客户|量产|试产).{0,8}(?:验证|认证)",
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
    identity_fields: dict[str, Any] = {
            "coordinates": coordinates.locator(),
            "parser_name": NARRATIVE_PARSER_NAME,
            "parser_version": parser_version,
            "source_id": source_id,
            "text_sha256": hashlib.sha256(canonical_text.encode("utf-8")).hexdigest(),
            "unit_kind": unit_kind,
        }
    if parser_version == QA_FRAGMENT_VERSION and unit_kind == "pdf_table_qa_fragment":
        identity_fields["cell_fragment_range"] = (
            metadata.get("cell_fragment_start"), metadata.get("cell_fragment_end")
        )
        identity_fields["source_role"] = source_role
    identity = json.dumps(
        identity_fields,
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


def _pdf_qa_parts(
    text: str, *, group_prefix: str, parser_version: str = NARRATIVE_PARSER_VERSION,
) -> list[dict[str, Any]]:
    """Split repeated investor Q&A markers inside one extracted table cell."""
    if parser_version == QA_FRAGMENT_VERSION:
        return pdf_qa_parts(text, group_prefix=group_prefix)
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
    last_answer_index: int | None = None

    @staticmethod
    def compatible(left: NarrativeUnit, right: NarrativeUnit) -> bool:
        if QA_FRAGMENT_VERSION not in {left.parser_version, right.parser_version}:
            return True  # replay the historical linking policy unchanged
        lp, rp = left.coordinates.page_number, right.coordinates.page_number
        return bool(
            left.source_id == right.source_id and left.language == right.language
            and left.parser_name == right.parser_name and left.parser_version == right.parser_version
            and lp is not None and rp is not None and 0 <= rp - lp <= 1
        )

    def continue_answer(self, index: int, unit: NarrativeUnit) -> bool:
        if self.last_answer_index is None or unit.parser_version != QA_FRAGMENT_VERSION:
            return False
        previous = self.output[self.last_answer_index]
        if not (
            self.compatible(previous, unit) and previous.coordinates == unit.coordinates
            and previous.metadata.get("cell_sha256") == unit.metadata.get("cell_sha256")
            and unit.metadata["cell_fragment_start"] >= previous.metadata["cell_fragment_end"]
        ):
            return False
        metadata = dict(unit.metadata)
        for key in ("qa_group_id", "qa_question_number", "qa_state"):
            metadata[key] = previous.metadata.get(key)
        self.output[index] = replace(unit, metadata=metadata)
        self.last_answer_index = index
        return True

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
        if unit.parser_version == QA_FRAGMENT_VERSION:
            answer_meta["qa_question_number"] = question.metadata.get("qa_question_number")
            self.last_answer_index = index
            for continuation_index in self.continuation_indices:
                continuation = self.output[continuation_index]
                metadata = dict(continuation.metadata)
                metadata["qa_question_number"] = question.metadata.get("qa_question_number")
                self.output[continuation_index] = replace(continuation, metadata=metadata)
        self.output[index] = replace(unit, metadata=answer_meta)
        self.clear_pending()

    def consume(self, index: int, unit: NarrativeUnit) -> None:
        state = unit.metadata.get("qa_state")
        if state != "answer_continuation":
            self.last_answer_index = None
        if self.pending_index is not None and state in {"question_continuation", "answer_continuation"}:
            anchor = self.continuation_indices[-1] if self.continuation_indices else self.pending_index
            if not self.compatible(self.output[anchor], unit):
                self.orphan_pending()
        if state == "question_unanswered":
            self.orphan_pending()
            self.pending_index = index
        elif state == "question_continuation" and self.pending_index is not None:
            self.continuation_indices.append(index)
        elif state == "answer_continuation":
            if self.pending_index is None:
                if self.continue_answer(index, unit):
                    return
                self.last_answer_index = None
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
        if _table_scan_signal("\n".join(item[2] for item in blocks), parser_version=state.parser_version)
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
        _has_pdf_question(text, state.parser_version) or _QA_ANSWER.search(text)
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
        fragments = _pdf_qa_parts(cell, group_prefix=group_prefix, parser_version=state.parser_version)
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


def _fitz_module() -> Any:
    try:
        import fitz  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise RuntimeError(
            "PDF parsing requires the optional PyMuPDF dependency"
        ) from exc
    return fitz


def _parse_pdf_document(
    document: Any,
    *,
    source_id: str,
    source_sha256: str,
    parser_version: str = NARRATIVE_PARSER_VERSION,
    language: str = "zh",
    full_table_scan: bool = False,
    table_pages: Sequence[int] | None = None,
) -> NarrativeParseResult:
    state = _PdfParseState(source_id, source_sha256, parser_version, language)
    state.page_count = len(document)
    _scan_pdf_pages(state, document)
    state.table_scan_pages = _pdf_table_scan_pages(
        state, full_table_scan, table_pages
    )
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
    """Scan a PDF path without materializing a normalized full-text artifact."""
    with _fitz_module().open(path) as document:
        return _parse_pdf_document(
            document,
            source_id=source_id,
            source_sha256=source_sha256,
            parser_version=parser_version,
            language=language,
            full_table_scan=full_table_scan,
            table_pages=table_pages,
        )


def parse_pdf_bytes(
    data: bytes,
    *,
    source_id: str,
    source_sha256: str,
    parser_version: str = NARRATIVE_PARSER_VERSION,
    language: str = "zh",
    full_table_scan: bool = False,
    table_pages: Sequence[int] | None = None,
) -> NarrativeParseResult:
    """Parse verified PDF bytes in memory without a temporary file."""
    if not isinstance(data, bytes):
        raise TypeError("PDF data must be bytes")
    if hashlib.sha256(data).hexdigest() != source_sha256:
        raise ValueError("PDF changed before narrative parsing")
    with _fitz_module().open(stream=data, filetype="pdf") as document:
        return _parse_pdf_document(
            document,
            source_id=source_id,
            source_sha256=source_sha256,
            parser_version=parser_version,
            language=language,
            full_table_scan=full_table_scan,
            table_pages=table_pages,
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
    if _consume_transcript_control_line(state, stripped):
        return
    transition_after_line = bool(_QA_TRANSITION.search(stripped))
    name, title, body = _transcript_speaker_fields(stripped)
    if _is_transcript_speaker(name):
        assert name is not None
        _begin_transcript_speaker(state, line_number, name, title or "", body or "")
        _enable_transcript_qa(state, transition_after_line)
        return
    appended = _append_transcript_unattributed(state, line_number, line, stripped)
    _enable_transcript_qa(state, appended and transition_after_line)


def _consume_transcript_control_line(
    state: _TranscriptParseState, stripped: str
) -> bool:
    if _consume_transcript_blank(state, stripped):
        return True
    return _consume_transcript_qa_heading(state, stripped)


def _consume_transcript_blank(state: _TranscriptParseState, stripped: str) -> bool:
    if stripped:
        return False
    if state.active is not None:
        state.active["lines"].append("")
    return True


def _consume_transcript_qa_heading(
    state: _TranscriptParseState, stripped: str
) -> bool:
    if _QA_HEADING.match(stripped) is None:
        return False
    state.qa_mode = True
    state.active = None
    return True


def _enable_transcript_qa(state: _TranscriptParseState, enabled: bool) -> None:
    if enabled:
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
    raw_group = block["qa_group_id"]
    parent_group = raw_group if isinstance(raw_group, (int, str)) else None
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


def verify_pdf_evidence_spans(
    path: Path,
    *,
    source_id: str,
    source_sha256: str,
    evidence_spans: Sequence[EvidenceSpan],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Re-read the hashed PDF and verify selected page/table snippets exactly."""
    plan = prepare_pdf_replay(
        path,
        source_id=source_id,
        source_sha256=source_sha256,
        evidence_spans=evidence_spans,
        default_parser_version=NARRATIVE_PARSER_VERSION,
    )
    replay = parse_pdf(
        path,
        source_id=source_id,
        source_sha256=source_sha256,
        parser_version=plan.parser_version,
        table_pages=plan.table_pages,
    )
    return verify_replayed_pdf_spans(evidence_spans, replay.units)


def verify_pdf_evidence_spans_bytes(
    data: bytes,
    *,
    source_id: str,
    source_sha256: str,
    evidence_spans: Sequence[EvidenceSpan],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Replay verified PDF bytes and verify selected locators without disk."""
    plan = prepare_pdf_replay_bytes(
        data,
        source_id=source_id,
        source_sha256=source_sha256,
        evidence_spans=evidence_spans,
        default_parser_version=NARRATIVE_PARSER_VERSION,
    )
    replay = parse_pdf_bytes(
        data,
        source_id=source_id,
        source_sha256=source_sha256,
        parser_version=plan.parser_version,
        table_pages=plan.table_pages,
    )
    return verify_replayed_pdf_spans(evidence_spans, replay.units)


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
    """Compatibility facade for the document-routing layer."""
    return cast(str, _classify_document_kind(title, existing_kind))


def _topics(text: str) -> tuple[str, ...]:
    return tuple(
        topic
        for topic, phrases in _SIGNALS.items()
        if any(phrase.casefold() in text.casefold() for phrase in phrases)
    )


def _has_pdf_question(text: str, parser_version: str) -> bool:
    return bool(question_markers(text)) if parser_version == QA_FRAGMENT_VERSION else bool(_QA_QUESTION.search(text))


def _table_scan_signal(text: str, *, parser_version: str = NARRATIVE_PARSER_VERSION) -> bool:
    """Limit expensive table discovery to pages with specific business events."""
    text = matching_text(text)
    if _has_pdf_question(text, parser_version) or _QA_ANSWER.search(text):
        return True
    topics = _topics(text)
    if not topics:
        return False
    if any(pattern.search(text) for pattern in (_HIGH_VALUE_EVENT, _PROJECT_PLAN, _STRATEGIC_PLAN)):
        return True
    return "industry_dynamics" in topics and bool(_RECENCY.search(text))


def _financial_table(unit: NarrativeUnit, topics: Sequence[str]) -> bool:
    if unit.unit_kind in {"html_table_cell", "pptx_table_cell"}:
        return unit.metadata.get("table_class") == "financial" and not _has_business_table_topics(topics)
    if unit.unit_kind != "pdf_table_row":
        return False
    numeric_cells, financial_label, financial_header, event_signal = _financial_row_signals(unit)
    if _numeric_financial_row(numeric_cells, event_signal):
        return True
    if _unclassified_financial_row(topics, financial_label, financial_header):
        return True
    if not financial_label:
        return False
    if numeric_cells < 1:
        return False
    return not _has_business_table_topics(topics)


def _numeric_financial_row(numeric_cells: int, event_signal: bool) -> bool:
    return numeric_cells >= 2 and not event_signal


def _unclassified_financial_row(
    topics: Sequence[str], financial_label: bool, financial_header: bool
) -> bool:
    return not topics and (financial_label or financial_header)


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


def _candidate_rules() -> CandidateRules:
    return CandidateRules(
        topics=_topics,
        financial_table=_financial_table,
        high_value_event=_HIGH_VALUE_EVENT,
        project_plan=_PROJECT_PLAN,
        strategic_plan=_STRATEGIC_PLAN,
        downstream_extension=_DOWNSTREAM_BUSINESS_EXTENSION,
        positioning=_SPECIFIC_BUSINESS_POSITIONING,
        business_risk=_BUSINESS_RISK_SIGNAL,
        project_rationale=_PROJECT_RATIONALE_SIGNAL,
        progress=_PROGRESS,
        business_progress_action=_BUSINESS_PROGRESS_ACTION,
        direct_capacity_constraint=_DIRECT_CAPACITY_CONSTRAINT,
        long_customer_qualification=_LONG_CUSTOMER_QUALIFICATION,
        project_certification_timeline=_PROJECT_CERTIFICATION_TIMELINE,
        permit_milestone=_PERMIT_ACQUIRED_MILESTONE,
        new_product_milestone=_NEW_PRODUCT_COMMERCIALIZATION,
        recency=_RECENCY,
        table_of_contents=_TABLE_OF_CONTENTS,
        accounting_context=_EXCLUDED_NARRATIVE_CONTEXT,
        heading_only=_HEADING_ONLY,
        static_definition=_STATIC_DEFINITION,
    )


def _base_candidates(
    parsed: NarrativeParseResult,
) -> tuple[list[EvidenceCandidate], int]:
    candidates: list[EvidenceCandidate] = []
    dropped_financial = 0
    rules = _candidate_rules()
    for unit in parsed.units:
        assessment = assess_unit(unit, rules)
        if assessment.dropped_financial:
            dropped_financial += 1
        candidate = assessment.candidate
        if candidate is not None:
            candidates.append(candidate)
    return candidates, dropped_financial


def _pdf_context_groups(
    units: Sequence[NarrativeUnit],
) -> tuple[tuple[str, tuple[NarrativeUnit, ...], str], ...]:
    """Compatibility seam; PDF points and OCR image pixels stay separate."""
    rules = PdfGroupRules(
        project_heading=_PROJECT_SECTION_HEADING,
        business_heading=_BUSINESS_SECTION_HEADING,
        heading_only=_HEADING_ONLY,
    )
    return cast(
        tuple[tuple[str, tuple[NarrativeUnit, ...], str], ...],
        build_pdf_context_groups(units, rules) + build_ocr_context_groups(units, rules),
    )


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
    original = parsed
    parsed = matching_document(parsed)
    route = route_document(
        matching_text(title), existing_kind=existing_kind, max_selected=max_selected
    )
    candidates, dropped_financial = _base_candidates(parsed)
    selection_group_ids: dict[str, str] = {}

    # PDF layout extraction often separates one logical sentence into several
    # adjacent text blocks. Evaluate those fragments together, then retain the
    # original locators as a grouped set of evidence spans. Prospectus project
    # sections also supply local context for their following body paragraphs.
    pdf_groups = _pdf_context_groups(parsed.units)
    section_context = build_section_context(
        route.document_kind,
        pdf_groups,
        ContextRules(
            project_heading=_PROJECT_SECTION_HEADING,
            business_heading=_BUSINESS_SECTION_HEADING,
            heading_only=_HEADING_ONLY,
        ),
    )
    project_context_scores = section_context.project_scores
    business_context_scores = section_context.business_scores

    enriched = enrich_context_groups(
        pdf_groups,
        initial_candidates=candidates,
        initial_group_ids=selection_group_ids,
        project_scores=project_context_scores,
        business_scores=business_context_scores,
        rules=GroupCandidateRules(
            topics=_topics,
            window_finder=_minimal_matching_unit_windows,
            project_heading=_PROJECT_SECTION_HEADING,
            business_heading=_BUSINESS_SECTION_HEADING,
            heading_only=_HEADING_ONLY,
            high_value_event=_HIGH_VALUE_EVENT,
            positioning=_SPECIFIC_BUSINESS_POSITIONING,
            business_risk=_BUSINESS_RISK_SIGNAL,
            direct_capacity_constraint=_DIRECT_CAPACITY_CONSTRAINT,
            long_customer_qualification=_LONG_CUSTOMER_QUALIFICATION,
            project_certification_timeline=_PROJECT_CERTIFICATION_TIMELINE,
            quantified_market_coverage_target=_QUANTIFIED_MARKET_COVERAGE_TARGET,
            permit_milestone=_PERMIT_ACQUIRED_MILESTONE,
            new_product_milestone=_NEW_PRODUCT_COMMERCIALIZATION,
            project_rationale=_PROJECT_RATIONALE_SIGNAL,
            downstream_extension=_DOWNSTREAM_BUSINESS_EXTENSION,
            project_plan=_PROJECT_PLAN,
            strategic_plan=_STRATEGIC_PLAN,
            table_of_contents=_TABLE_OF_CONTENTS,
            accounting_context=_EXCLUDED_NARRATIVE_CONTEXT,
            static_definition=_STATIC_DEFINITION,
            progress=_PROGRESS,
            recency=_RECENCY,
            downstream_center_timeline=_DOWNSTREAM_CENTER_CERTIFICATION_TIMELINE,
        ),
    )
    candidates = list(enriched.candidates)
    selection_group_ids = dict(enriched.group_ids)

    neighbors = enrich_neighbor_context(
        parsed.units,
        initial_candidates=candidates,
        initial_group_ids=selection_group_ids,
        rules=NeighborRules(
            topics=_topics,
            high_value_event=_HIGH_VALUE_EVENT,
            named_product_context=_NAMED_PRODUCT_CONTEXT,
            accounting_context=_EXCLUDED_NARRATIVE_CONTEXT,
            project_rationale=_PROJECT_RATIONALE_SIGNAL,
            table_of_contents=_TABLE_OF_CONTENTS,
        ),
    )
    projects = enrich_fundraising_table_context(
        parsed.units, pdf_groups, initial_candidates=neighbors.candidates,
        initial_group_ids=neighbors.group_ids,
    )
    previous_ids = {candidate.unit.unit_id for candidate in neighbors.candidates}
    dropped_financial -= sum(
        assess_unit(candidate.unit, _candidate_rules()).dropped_financial
        for candidate in projects.candidates if candidate.unit.unit_id not in previous_ids
    )
    return finalize_selection(
        original,
        route,
        original_candidates(projects.candidates, original),
        group_ids=projects.group_ids,
        heading_pattern=_HEADING_ONLY,
        dropped_financial_count=dropped_financial,
        excluded_context_unit_ids=enriched.excluded_context_unit_ids,
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
    validate_summary_identity(
        draft, source_id=source_id, source_sha256=source_sha256, language=language,
    )
    known = {span.span_id: span for span in evidence_spans}
    if not draft.claims:
        raise SummaryValidationError("summary draft must contain at least one claim")
    for claim in draft.claims:
        validate_summary_claim(claim, known, draft.status)
    # A citation-valid draft remains a draft. Semantic entailment, contradictory
    # evidence, modality, negation, and speaker accuracy remain quality questions,
    # not permission to publish or read a source-oriented draft.


def validate_summary_identity(
    draft: SourceSummaryDraft, *, source_id: str, source_sha256: str, language: str,
) -> None:
    """Check the whole-draft binding before inspecting recoverable claims."""
    if draft.source_id != source_id or draft.source_sha256 != source_sha256:
        raise SummaryValidationError("summary source identity/hash does not match")
    if draft.language != language:
        raise SummaryValidationError("summary language must match the source language")


def validate_summary_claim(
    claim: SummaryClaim, known: Mapping[str, EvidenceSpan], draft_status: str
) -> None:
    """Validate content binding; the legacy status argument is diagnostic only."""
    if not claim.text.strip():
        raise SummaryValidationError("summary claim text must not be blank")
    if not claim.evidence_ids:
        raise SummaryValidationError("every summary claim requires evidence IDs")
    if set(claim.evidence_ids) - set(known):
        raise SummaryValidationError("summary claim refers to unknown evidence IDs")
    _validate_claim_roles(claim, known)


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
    if claim.claim_type == "analyst_question" and claim.modality != "question":
        raise SummaryValidationError("analyst-question claims must preserve question modality")


def project_summary_quality(
    draft: SourceSummaryDraft, *, evidence_spans: Sequence[EvidenceSpan],
    discarded_claims: bool = False,
) -> SourceSummaryDraft:
    """Compute quality once after claim recovery, without a manual review gate.

    Model uncertainty remains in claim_type/modality. Redundant model status
    labels cannot invalidate grounded content or declare it verified. This is
    a diagnostic projection; publication still requires original-byte replay
    of every selected locator in the verify handler.
    """
    known = {span.span_id: span for span in evidence_spans}
    projected = []
    for claim in draft.claims:
        validate_summary_claim(claim, known, draft.status)
        cited = [known[evidence_id] for evidence_id in claim.evidence_ids]
        needs_review = (
            claim.claim_type == "uncertain" or claim.modality == "uncertain"
            or any(span.quality_flags or span.parse_status != "parsed" for span in cited)
            or any(span.structured_value.get("source_role", "unknown") == "unknown"
                   for span in cited)
        )
        projected.append(replace(claim, needs_review=needs_review))
    # All selected spans remain in the exported bundle and are replayed, even
    # when the compact summary does not repeat each span as a separate claim.
    review_required = (
        discarded_claims or any(claim.needs_review for claim in projected)
        or any(span.quality_flags or span.parse_status != "parsed" for span in evidence_spans)
    )
    return replace(
        draft, claims=tuple(projected),
        status="needs_review" if review_required else "draft",
    )
