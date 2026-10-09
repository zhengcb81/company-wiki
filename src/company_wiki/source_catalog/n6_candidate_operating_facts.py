"""Generic operating-fact recall rules for narrative candidates (N6-CANDIDATE).

Plain-language patterns only: operating object plus action/status, quantified
structure, industry demand/supply change, corporate development, fundraising
project use, and demand exceeding capacity. No company-name allowlists, no
semantic truth claims: forecasts, plans and negations keep their source wording.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from .n6_scope_changes import SCOPE_CHANGE_JOIN, scope_change_reasons


@dataclass(frozen=True)
class OperatingFact:
    """One conservative operating-fact assessment of a text span."""

    eligible: bool = False
    topics: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    score: int = 0
    financial_exempt: bool = False


_NONE = OperatingFact()

_OBJECT = (
    r"(?:设备|产线|生产线|车间|基地|装置|系统|平台|产品|工厂|园区|试剂|"
    r"型号|机型|客户|产线)"
)
_STRUCTURE_SUBJECT = (
    r"(?:境内|境外|海外|内销|出口|一口价|克重|黄金|高端|产品|机型|型号|系列|"
    r"品类|客户|销量|订单|业务|产线|服务|用户|收入结构|主营)"
)

_APPLIED = re.compile(
    rf"(?:{_OBJECT}).{{0,32}}(?:已[^，。；、]{{0,16}}?)?"
    r"(?:应用(?:于|在)?|投入使用|投用|交付使用|投入运行|稳定运行|批量销售|"
    r"规模化应用|通过验证|完成验证|客户验证|量产|实现销售)"
    r"|(?:已[^，。；、]{0,16}?)?(?:应用|投入使用|投用|交付使用|稳定运行)"
    rf".{{0,32}}(?:{_OBJECT})",
    re.IGNORECASE,
)

_PRODUCTION_STATUS = re.compile(
    r"(?:产销量|产能利用率|产销率|产能|产量|良率|稼动率).{0,30}"
    r"(?:提升|增长|上升|达到|超过|释放|爬坡|保持|处于|加快|再创新高).{0,16}\d"
    r"|(?:产销量|产能|产量).{0,16}(?:大幅提升|显著增长|释放明显|再创新高)",
    re.IGNORECASE,
)

_QUANTIFIED_STRUCTURE = re.compile(
    rf"(?:{_STRUCTURE_SUBJECT}).{{0,30}}(?:占比|比例|构成|结构).{{0,24}}\d",
    re.IGNORECASE,
)

_GROWTH_DRIVER = re.compile(
    r"(?:实现|量产|销售|增长|同比|贡献|成为|占比|放量).{0,40}"
    r"(?:第二增长曲线|第二曲线|新增长极|新增长点|增长引擎|重要新引擎|新引擎)"
    r"|(?:第二增长曲线|第二曲线|新增长极|新增长点|增长引擎|重要新引擎|新引擎)"
    r".{0,40}(?:实现|量产|销售|增长|同比|贡献|成为|占比|放量)",
    re.IGNORECASE,
)

_MA_DONE = re.compile(
    r"(?:已完成|已经完成|完成对|已取得|已签署|已通过)[^，。；]{0,24}?"
    r"(?:收购|并购|控股权|标的股权|资产过户)"
    r"|(?:收购|并购)[^，。；]{0,24}?(?:已完成|已经完成|交割|过户完成)",
    re.IGNORECASE,
)

_MA_PLANNED = re.compile(
    r"(?:拟|计划|将要)\s*(?:通过|以|采用)?[^，。；]{0,40}?"
    r"(?:收购|并购|参股|购买[^，。；]{0,24}控股权|受让[^，。；]{0,16}股权)"
    r"|(?:收购|并购|参股).{0,20}(?:计划|草案|预案)",
    re.IGNORECASE,
)
_CONCRETE_MA_PLANNED = re.compile(
    r"(?:拟|计划|将要)(?:通过|以|采用)?[^，。；]{0,65}?"
    r"(?:收购|并购|参股|购买|受让)(?:\s*对)?[^，。；、]{1,40}?"
    r"(?:公司|企业|控股权|股权|资产)"
    r"|(?:收购|并购|参股)[^，。；、]{1,30}(?:公司|企业|控股权|股权|资产)"
    r"[^，。；]{0,12}(?:草案|预案)",
    re.IGNORECASE,
)

_INDUSTRY_CHANGE = re.compile(
    r"(?:进口|出口|对外依存度).{0,60}从\s*[\d.]+\s*%.{0,12}"
    r"(?:下降|降低|上升|提高|增长)至\s*[\d.]+\s*%"
    r"|(?:市场规模|市场需求|行业需求|行业规模|全球市场|销售额|装机量|渗透率|出货量)"
    r".{0,24}(?:(?:有望|预计|将|进一步|持续|不断|逐年|逐步)\s*)*"
    r"(?:达到|提高至|增长至|增长|提高|扩大|上升|超过|突破)"
    r"|(?:自给(?:率|能力)|进口替代|替代(?:速度|进程)|国产化率).{0,20}"
    r"(?:增强|提高|提升|加快|加速)"
    r"|市场空间.{0,16}(?:广阔|巨大|较大)"
    r"|(?:市场|行业|产业).{0,24}(?:不断扩大|日益扩大|持续扩大|持续景气)"
    r"|(?:下游|终端|应用)?需求.{0,24}(?:持续|不断|日益|进一步|显著)?\s*"
    r"(?:扩张|扩大|增长|旺盛|上升|释放|强劲|走高)",
    re.IGNORECASE,
)

_FUNDRAISING_USE = re.compile(
    r"(?:募集资金|募投项目|本次发行)[\s\S]{0,80}?(?:投资于|拟用于|用于|投向)"
    r"[\s\S]{0,60}?(?:项目|生产线|建设)"
    r"|募投项目.{0,40}(?:达产|投产)[\s\S]{0,60}?(?:新增|预计|释放)",
    re.IGNORECASE,
)

_PROJECT_STARTED = re.compile(
    r"(?:启动|开工|新开工|启动建设|开建)[^，。；]{0,28}?(?:建设项目|项目)"
    r"[\s\S]{0,60}?(?:产能|产量|包含|预计|达产|投产)",
    re.IGNORECASE,
)

_DEMAND_EXCEEDS = re.compile(
    r"demand[\s\S]{0,80}?(?:continue[sd]? to|continuing to|still|kept to)\s+"
    r"(?:exceed|outstrip)\w*[\s\S]{0,40}?(?:available\s+)?(?:supply|capacity)"
    r"|demand[\s\S]{0,60}?(?:exceeds|outstrips)[\s\S]{0,40}?"
    r"(?:available\s+)?(?:supply|capacity)"
    r"|(?:供不应求|需求[\s\S]{0,30}?(?:超过|超出|大于|高于)[\s\S]{0,24}?"
    r"(?:产能|供给|产量))",
    re.IGNORECASE,
)

_PROJECT_TIMELINE = re.compile(
    r"(?:项目|基地|产线|生产线)[^。；]{0,60}(?:开工|启动建设|在建)"
    r"[^。；]{0,80}(?:预计|计划|拟|将)[^。；]{0,40}(?:建成|投产|达产)"
    r"|(?:开工|启动建设)[^。；]{0,30}(?:项目|基地|产线|生产线)"
    r"[^。；]{0,80}(?:预计|计划|拟|将)[^。；]{0,40}(?:建成|投产|达产)",
    re.IGNORECASE,
)

_ADOPTION_MILESTONE = re.compile(
    rf"{_OBJECT}[^。；]{{0,32}}(?:已|已经)[^。；]{{0,12}}"
    r"(?:应用于|应用在|批量销售|投入使用|交付使用|稳定运行)"
    rf"|{_OBJECT}[^。；]{{0,32}}(?:实现了|实现|完成)(?:批量销售|交付使用)",
    re.IGNORECASE,
)
_CUSTOMER_ADOPTION = re.compile(
    r"(?:设备|产品|平台|系统|技术)[^。；，]{0,32}(?:已|已经)[^。；，]{0,12}"
    r"(?:应用于|应用在)[^。；，]{0,40}(?:客户|生产线|产线|终端)"
    r"|(?:设备|产品|平台|系统|技术)[^。；，]{0,32}(?:实现了|实现)批量销售",
    re.IGNORECASE,
)
_INDUSTRY_OUTLOOK = re.compile(
    r"(?:行业|产业|市场|全球|国际)[^。；]{0,100}(?:规模|销售额|出货量|装机量)"
    r"[^。；]{0,30}(?:预计|有望|将|预测)[^。；]{0,20}"
    r"(?:达(?:到)?|提高至|增长至|增加至)[^。；]{0,10}\d",
    re.IGNORECASE,
)
_QUANTIFIED_INDUSTRY_CHANGE = re.compile(
    r"(?:进口|出口|对外依存度)[^。；]{0,60}从\s*[\d.]+\s*%[^。；]{0,12}"
    r"(?:下降|降低|上升|提高|增长)至\s*[\d.]+\s*%",
    re.IGNORECASE,
)
_CONCRETE_PROJECT_USE = re.compile(
    r"(?:募集资金|募投项目|本次发行)[^。；]{0,100}"
    r"(?:投资于|拟用于|用于|投向)[^。；]{0,70}"
    r"[\u3400-\u9fffA-Za-z0-9]{2,30}"
    r"(?:生产线|研发中心|建设项目|扩产升级项目|建设升级项目)",
    re.IGNORECASE,
)
_INCREMENTAL_CAPACITY = re.compile(
    r"(?:募投项目|建设项目|生产线项目)[^。；]{0,50}(?:达产|投产|建成)"
    r"[^。；]{0,60}(?:新增|增加)[^。；]{0,65}\d[\d., ]*"
    r"(?:万|千|亿)?(?:件|支|台|吨|套|片|立方米|千瓦)",
    re.IGNORECASE,
)

_COMMERCIAL_METRIC_CHANGE = re.compile(
    r"(?:^|[，、；。！？!?;,.]\s*|(?:以及|其中|而|但|并|且)\s*)"
    r"(?:(?:本年度|报告期内|报告期|本期|目前|当期|本季度|公司|本土市场|国内|海外|国际市场|"
    r"游戏|广告|的|日|月|年|平均|期间|我们|现有|新增|总|营销服务)\s*){0,8}"
    r"(?:活跃用户|付费用户|付费率|留存率|广告曝光|曝光次数|广告价格|客单价|订阅用户|"
    r"用户时长|付费频次|转化率|广告库存|平均售价)"
    r"(?:(?:次数|同比|环比|持续|显著|分别|进一步|出现|有所|均)\s*){0,4}"
    r"(?:增长|增加|上升|提升|下降|减少|下滑|提高|改善)",
    re.IGNORECASE,
)
_ENGLISH_OPERATING_CHANGE = re.compile(
    r"(?:^|[,.!?;]\s*|\b(?:and|while|whereas)\s+)"
    r"(?:(?:our|the|production|customer|average|daily|monthly|global|international|total)\s+){0,3}"
    r"(?:active users|paying users|paid users|retention rate|advertising impressions|ad impressions|"
    r"ad pric(?:e|ing)|average selling price|capacity(?: utilization)?|production volumes|"
    r"output|orders|order intake|backlog|yield)\s+"
    r"(?:(?:has|have|had|been|was|were|year.over.year|year.on.year|significantly|materially|"
    r"unexpectedly|slightly|steadily|continued to|continues to)\s+){0,3}"
    r"(?:increas\w*|decreas\w*|grew|grow\w*|rose|fell|improv\w*|declin\w*)\b",
    re.IGNORECASE,
)
_ENGLISH_SUPPLY_DELIVERY_RISK = re.compile(
    r"(?:supply|component|material|capacity)[^.!?;。；！？]{0,40}"
    r"(?:constraints?|shortages?|disruptions?|restrictions?)[^.!?;。；！？]{0,40}"
    r"(?:delayed|disrupted|reduced|limited|constrained)[^.!?;。；！？]{0,40}"
    r"(?:deliver(?:y|ies)|production|output|shipments|capacity|customers)",
    re.IGNORECASE,
)
_REVENUE_CAUSE = re.compile(
    r"(?:revenue|sales)[^.;!?。；！？]{0,40}(?:grew|increas\w*|decreas\w*|declin\w*)"
    r"[^.;!?。；！？]{0,55}(?:driven by|due to|because of)[^.;!?。；！？]{0,70}"
    r"(?:customer|adoption|platform|product|volume|pricing|usage|subscription|demand)",
    re.IGNORECASE,
)
_SUPPLY_DELIVERY_RISK = re.compile(
    r"(?:上游|供应链|关键零部件|关键原材料)[^。；]{0,80}(?:紧张|短缺|限制|中断)"
    r"[^。；]{0,65}(?:交期|交付|生产|产能|客户)[^。；]{0,30}(?:影响|延迟|延误|受限|减少)",
    re.IGNORECASE,
)

_DETECTOR_SIGNALS: tuple[
    tuple[re.Pattern[str], tuple[str, ...], tuple[str, ...], int], ...
] = (
    (_PROJECT_TIMELINE, ("capacity_projects",), ("project_execution_timeline", "project_plan_or_status"), 4),
    (_ADOPTION_MILESTONE, ("core_business",), ("applied_operating_milestone",), 3),
    # Classification only: one adoption action must not gain duplicate score.
    (_CUSTOMER_ADOPTION, ("core_business",), ("customer_adoption_milestone",), 0),
    (_INDUSTRY_OUTLOOK, ("industry_dynamics",), ("quantified_industry_outlook", "current_industry_context"), 3),
    (_QUANTIFIED_INDUSTRY_CHANGE, ("industry_dynamics",), ("quantified_industry_change", "current_industry_context"), 3),
    (_CONCRETE_PROJECT_USE, ("capacity_projects",), ("concrete_fundraising_project", "project_plan_or_status"), 3),
    (_INCREMENTAL_CAPACITY, ("capacity_projects",), ("incremental_project_capacity", "project_plan_or_status"), 3),
    (_APPLIED, ("core_business",), ("specific_business_event",), 3),
    (_PRODUCTION_STATUS, ("core_business",), ("quantified_operating_status",), 2),
    (_QUANTIFIED_STRUCTURE, ("core_business",), ("quantified_operating_status",), 2),
    (_GROWTH_DRIVER, ("new_business",), ("quantified_operating_status",), 3),
    (_MA_DONE, ("new_business",), ("corporate_development", "specific_business_event"), 3),
    (_CONCRETE_MA_PLANNED, ("new_business",), ("corporate_development", "project_plan_or_status"), 2),
    (_MA_PLANNED, ("new_business",), ("project_plan_or_status",), 2),
    (_INDUSTRY_CHANGE, ("industry_dynamics",), ("current_industry_context",), 2),
    (_FUNDRAISING_USE, ("capacity_projects",), ("project_plan_or_status",), 3),
    (
        _PROJECT_STARTED,
        ("capacity_projects",),
        ("specific_business_event", "project_plan_or_status"),
        3,
    ),
    (_DEMAND_EXCEEDS, ("industry_dynamics",), ("direct_capacity_constraint",), 2),
    (_COMMERCIAL_METRIC_CHANGE, ("core_business",), ("quantified_operating_status",), 3),
    (_ENGLISH_OPERATING_CHANGE, ("core_business",), ("quantified_operating_status",), 3),
    (_ENGLISH_SUPPLY_DELIVERY_RISK, ("capacity_projects",), ("business_risk_or_constraint",), 3),
    (_REVENUE_CAUSE, ("core_business",), ("specific_business_event",), 3),
    (_SUPPLY_DELIVERY_RISK, ("capacity_projects",), ("business_risk_or_constraint",), 3),
)

# Union used to find minimal unit windows whose joined text carries a fact that
# no single unit expresses (a sentence split across PDF blocks).
OPERATING_FACT_JOIN = re.compile(
    "|".join([*(pattern.pattern for pattern, _, _, _ in _DETECTOR_SIGNALS), SCOPE_CHANGE_JOIN.pattern]),
    re.IGNORECASE,
)


def detect_operating_fact(text: str) -> OperatingFact:
    """Return the accumulated generic operating-fact signal for one text span."""
    reasons: list[str] = []
    topics: list[str] = []
    score = 0
    matched = False
    for pattern, fact_topics, fact_reasons, fact_score in _DETECTOR_SIGNALS:
        if pattern.search(text) is None:
            continue
        matched = True
        score += fact_score
        for reason in fact_reasons:
            if reason not in reasons:
                reasons.append(reason)
        for topic in fact_topics:
            if topic not in topics:
                topics.append(topic)
    scope_reasons = scope_change_reasons(text)
    legacy_matched = matched
    if scope_reasons:
        matched = True
        score += 3
        reasons.extend(reason for reason in scope_reasons if reason not in reasons)
        if "core_business" not in topics:
            topics.append("core_business")
    if not matched:
        return _NONE
    return OperatingFact(
        eligible=True,
        topics=tuple(topics),
        reasons=tuple(reasons),
        score=score,
        financial_exempt=legacy_matched and re.search(r"\d", text) is not None,
    )


__all__ = ["OPERATING_FACT_JOIN", "OperatingFact", "detect_operating_fact"]
