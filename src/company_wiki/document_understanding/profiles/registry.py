"""Static profile registry.

``design.md`` section 9 asks for a static registry, not a plugin framework. The registry
is built once at import time from the shared blocks in :mod:`model`, so adding a family
means composing existing blocks rather than copying a pipeline.

Lookup is by exact ``profile_id``. An unknown id is a real data error and raises, because
inventing a profile on demand would hide the mistake ROOT needs to see.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Iterator, Mapping

from .model import (
    ADMINISTRATIVE_SECTIONS,
    CN_BUSINESS_SECTIONS,
    CN_COMMON_SECTIONS,
    CN_FUNDRAISING_SECTIONS,
    GENERIC_SECTIONS,
    HK_BILINGUAL_SECTIONS,
    HK_OFFERING_SECTIONS,
    NEGATIVE_HINTS_BILINGUAL,
    NEGATIVE_HINTS_COMMON,
    NEGATIVE_HINTS_HTML,
    NEGATIVE_HINTS_PAGINATED,
    SEC_10K_SECTIONS,
    SEC_10Q_SECTIONS,
    SEC_20F_SECTIONS,
    SEC_REGISTRATION_SECTIONS,
    SHARED_FOCUS,
    Profile,
    SectionPriority,
    combine,
)


def _periodic_focus(scope: str) -> str:
    return f"{SHARED_FOCUS.business_and_risk} {scope}{SHARED_FOCUS.periodic_change}"


def _build_profiles() -> tuple[Profile, ...]:
    """Compose the fifteen required profiles from the shared blocks."""
    cn_periodic_negatives = NEGATIVE_HINTS_COMMON + NEGATIVE_HINTS_PAGINATED
    sec_negatives = NEGATIVE_HINTS_COMMON + NEGATIVE_HINTS_PAGINATED + NEGATIVE_HINTS_HTML
    hk_negatives = (
        NEGATIVE_HINTS_COMMON + NEGATIVE_HINTS_PAGINATED + NEGATIVE_HINTS_BILINGUAL
    )
    return (
        Profile(
            profile_id="cn_annual",
            family="annual",
            regime="cn_exchange",
            section_priorities=combine(CN_COMMON_SECTIONS, CN_BUSINESS_SECTIONS),
            semantic_units=("paragraph_event", "project", "operating_table", "risk", "background"),
            summary_focus=_periodic_focus(
                "年度报告重点覆盖管理层讨论、业务概要、行业、研发、经营变化与未来计划，"
                "并补读与业务相关的财务附注。"
            ),
            negative_hints=cn_periodic_negatives + ("年度报告摘要与独立董事述职报告不是完整年报",),
        ),
        Profile(
            profile_id="cn_interim",
            family="interim",
            regime="cn_exchange",
            section_priorities=combine(CN_COMMON_SECTIONS, CN_BUSINESS_SECTIONS),
            semantic_units=("paragraph_event", "project", "operating_table", "risk", "background"),
            summary_focus=_periodic_focus(
                "半年度报告聚焦上半年变化、项目进度与下半年安排；未披露不等于停止。"
            ),
            negative_hints=cn_periodic_negatives + ("半年累计数不得写成单季度，也不得直接复用年报摘要",),
        ),
        Profile(
            profile_id="cn_quarterly",
            family="quarterly",
            regime="cn_exchange",
            section_priorities=combine(
                CN_COMMON_SECTIONS,
                (
                    SectionPriority(
                        "management_discussion",
                        ("重要内容提示", "其他提醒事项", "经营情况说明", "变动原因"),
                        1,
                    ),
                    SectionPriority("business", ("主营业务", "经营情况", "产品进展"), 2),
                    SectionPriority("risk", ("风险提示", "重大风险提示"), 2),
                    SectionPriority(
                        "financial_notes",
                        ("主要财务数据", "季度财务报表", "合并资产负债表", "合并利润表"),
                        3,
                    ),
                ),
            ),
            semantic_units=("paragraph_event", "operating_table", "risk", "background"),
            summary_focus=_periodic_focus(
                "季度报告先稀疏扫描全部事实，再按价值选择；逐项核对后仍可判低业务密度并减少模型调用，"
                "但不得整类跳过，也不得把归母利润变动原因当作产品进展。"
            ),
            negative_hints=cn_periodic_negatives
            + ("其他提醒事项标注不适用时按无内容处理，不代表公司无经营",),
        ),
        Profile(
            profile_id="hk_periodic",
            family="annual",
            regime="hkex",
            section_priorities=combine(HK_BILINGUAL_SECTIONS, CN_COMMON_SECTIONS),
            semantic_units=("paragraph_event", "project", "operating_table", "risk", "background"),
            summary_focus=_periodic_focus(
                "港股定期报告按真实语言分栏恢复阅读顺序，双语选一份原语言输出并保留另一语言对应关系；"
                "门店数、用户数、订单表属于经营驱动而非财务三表。"
            ),
            negative_hints=hk_negatives
            + ("期后事项与报告期内事实必须分开表述",),
        ),
        Profile(
            profile_id="sec_10k",
            family="annual",
            regime="sec",
            section_priorities=SEC_10K_SECTIONS,
            semantic_units=("paragraph_event", "operating_table", "risk", "background"),
            summary_focus=_periodic_focus(
                "10-K 优先 Item 1 Business、Item 1A 风险与 Item 7 MD&A，并选择性补读分部、"
                "合同与并购附注；业务分部、商业机制与消费/订阅 KPI 单独成包。"
            ),
            negative_hints=sec_negatives
            + ("目录与交叉引用不是正文；不得套用 20-F 编号；有业务意义的 notes 不得省略",),
        ),
        Profile(
            profile_id="sec_10q",
            family="quarterly",
            regime="sec",
            section_priorities=SEC_10Q_SECTIONS,
            semantic_units=("paragraph_event", "operating_table", "risk", "background"),
            summary_focus=_periodic_focus(
                "10-Q 先 Part I Item 2 MD&A 与业务附注，再补 Part II 风险更新；"
                "本季度与年初至今必须分开，同环比与 GAAP/non-GAAP 不得混淆。"
            ),
            negative_hints=sec_negatives
            + ("不得当成 A 股常见短季报；承接 10-K 背景但不复制其全文",),
        ),
        Profile(
            profile_id="sec_20f",
            family="annual",
            regime="sec",
            section_priorities=SEC_20F_SECTIONS,
            semantic_units=("paragraph_event", "operating_table", "risk", "background"),
            summary_focus=_periodic_focus(
                "20-F 优先 Item 4 公司/业务、Item 5 经营回顾与 Item 3D 风险，"
                "关注监管与公司结构对业务的事实约束。"
            ),
            negative_hints=sec_negatives
            + ("不得使用 10-K 章节编号；不得按上市市场推断注册地或币种",),
        ),
        Profile(
            profile_id="prospectus",
            family="prospectus",
            regime="cn_exchange",
            section_priorities=combine(CN_FUNDRAISING_SECTIONS, HK_OFFERING_SECTIONS, SEC_REGISTRATION_SECTIONS),
            semantic_units=("paragraph_event", "project", "operating_table", "risk", "background"),
            summary_focus=(
                "招股书建立业务基础知识与发行当时事实包：产品与收入机制、行业与市场口径、"
                "客户与供应商依赖、竞争格局、扩产逻辑与募集资金用途；"
                "外部行业统计不得表述为公司实际业绩，历史计划必须带原日期。"
            ),
            negative_hints=NEGATIVE_HINTS_COMMON
            + NEGATIVE_HINTS_PAGINATED
            + ("不得只抓最新事件，也不得把发行时点的历史事实写成当前现状",),
        ),
        Profile(
            profile_id="offering",
            family="offering",
            regime="cn_exchange",
            section_priorities=combine(CN_FUNDRAISING_SECTIONS, HK_OFFERING_SECTIONS, SEC_REGISTRATION_SECTIONS),
            semantic_units=("project", "operating_table", "risk", "paragraph_event", "background"),
            summary_focus=(
                "再融资与募投按项目绑定产品、实施主体、地点、投入金额、新增与总产能、"
                "建设与爬坡期、备案与环评前提；投资额与项目测算收入不是实际收入，"
                "补充流动资金单列。"
            ),
            negative_hints=NEGATIVE_HINTS_COMMON
            + NEGATIVE_HINTS_PAGINATED
            + ("不得把债券条款当作业务信息耗尽预算，也不得只读标题含招股的章节",),
        ),
        Profile(
            profile_id="investor_qa",
            family="investor_qa",
            regime="cn_exchange",
            section_priorities=(
                SectionPriority("questions", ("交流内容及具体问答记录", "问：", "问答", "互动易"), 1),
                SectionPriority(
                    "administrative",
                    ("投资者关系活动类别", "活动参与人员", "时间", "地点", "形式", "编号"),
                    3,
                ),
                SectionPriority("business", ("主营业务", "经营情况"), 2),
            ),
            semantic_units=("qa_exchange", "paragraph_event", "background"),
            summary_focus=(
                "问答记录把提问与答复连同追问组成一个语义单元，区分提问中的推测、"
                "答复中的事实与避而不答；答复里的否定与限定条件必须保留。"
            ),
            negative_hints=NEGATIVE_HINTS_COMMON
            + ("提问中假设的客户合作不得写成已发生事实；套话可以降权但不能删掉答复的否定",),
        ),
        Profile(
            profile_id="earnings_call",
            family="earnings_call",
            regime="unknown",
            section_priorities=(
                SectionPriority(
                    "management_discussion",
                    ("prepared remarks", "management remarks", "call participants", "operator"),
                    1,
                ),
                SectionPriority("questions", ("questions and answers", "question-and-answer", "q&a"), 1),
                SectionPriority("outlook", ("guidance", "outlook"), 2),
                SectionPriority("operating_metrics", ("revenue", "eps", "margin"), 2),
            ),
            semantic_units=("qa_exchange", "paragraph_event", "background"),
            summary_focus=(
                "电话会按发言轮次与角色组织，保留原语言；管理层 prepared remarks、"
                "分析师提问与网站要点摘要必须分开，不得把提问或第三方要点写成管理层原话。"
            ),
            negative_hints=NEGATIVE_HINTS_COMMON
            + ("编辑摘要与真实发言分开；不经角色识别不得重复摘要",),
        ),
        Profile(
            profile_id="results_release",
            family="results_release",
            regime="unknown",
            section_priorities=(
                SectionPriority("operating_metrics", ("highlights", "business highlights", "financial highlights"), 1),
                SectionPriority("business", ("segment", "business overview", "about"), 2),
                SectionPriority("management_discussion", ("commentary", "ceo", "chairman"), 2),
                SectionPriority("financial_notes", ("condensed consolidated", "statement of", "balance sheet"), 3),
            ),
            semantic_units=("paragraph_event", "operating_table", "background"),
            summary_focus=(
                "业绩发布按 highlights、业务分部与经营指标组织，每个指标说明连同单位、"
                "期间与同比口径一起成包；公告期的数字不等于审计后年度数。"
            ),
            negative_hints=NEGATIVE_HINTS_COMMON
            + NEGATIVE_HINTS_HTML
            + ("业绩发布不是定期报告，不得按年报章节结构解读",),
        ),
        Profile(
            profile_id="presentation",
            family="presentation",
            regime="unknown",
            section_priorities=(
                SectionPriority("operating_metrics", ("in billion", "total revenue", "yoy", "qoq"), 1),
                SectionPriority("business", ("business review", "strategy", "product"), 2),
                SectionPriority("outlook", ("outlook", "roadmap", "plan"), 2),
                SectionPriority("unknown", ("appendix", "notes"), 3),
            ),
            semantic_units=("operating_table", "paragraph_event", "background"),
            summary_focus=(
                "演示稿一个 slide、一张图或一个指标说明构成一个语义包，单位与时间口径随包；"
                "图表失读必须标为未读，不能宣称完整。"
            ),
            negative_hints=NEGATIVE_HINTS_COMMON
            + ("空白提取不等于无内容；图表脚注属于该指标",),
        ),
        Profile(
            profile_id="administrative",
            family="administrative",
            regime="unknown",
            section_priorities=ADMINISTRATIVE_SECTIONS,
            semantic_units=("background",),
            summary_focus=(
                "行政材料先由封面与正文确认用途；确认无业务内容后可作为跳过派生的候选，"
                "但原件与来源记录必须保留。"
            ),
            negative_hints=NEGATIVE_HINTS_COMMON
            + ("仅凭标题不得跳过；财报正文中混入的行政附件不得连带丢弃整份财报",),
        ),
        Profile(
            profile_id="generic",
            family="unknown",
            regime="unknown",
            section_priorities=GENERIC_SECTIONS,
            semantic_units=("paragraph_event", "background"),
            summary_focus=(
                "类型未知时按通用来源策略保守阅读：保留第三方作者/事实/观点属性，"
                "只记录有原文支持的内容，不推断因果也不生成投资结论。"
            ),
            negative_hints=NEGATIVE_HINTS_COMMON + NEGATIVE_HINTS_HTML,
        ),
    )


_PROFILES: tuple[Profile, ...] = _build_profiles()

_PROFILE_INDEX: Mapping[str, Profile] = MappingProxyType(
    {profile.profile_id: profile for profile in _PROFILES}
)

if len(_PROFILE_INDEX) != len(_PROFILES):  # pragma: no cover - construction guard
    raise RuntimeError("duplicate profile_id in the static registry")


def profile_by_id(profile_id: str) -> Profile:
    """Return a registry profile; an unknown or malformed id is a real error."""
    if not isinstance(profile_id, str):
        raise TypeError(f"profile_id must be a string, got {type(profile_id)!r}")
    if not profile_id:
        raise ValueError("profile_id must be non-empty")
    try:
        return _PROFILE_INDEX[profile_id]
    except KeyError:
        raise KeyError(f"unknown profile_id: {profile_id!r}") from None


def iter_profiles() -> Iterator[Profile]:
    """Iterate the registry in a stable order (declaration order, which is stable)."""
    return iter(_PROFILES)


def listed_profiles() -> list[dict]:
    """Wire view of the whole registry."""
    return [profile.to_wire() for profile in _PROFILES]


def profile_wire(profile_id: str) -> dict:
    """Wire view of one profile."""
    return profile_by_id(profile_id).to_wire()


__all__ = [
    "iter_profiles",
    "listed_profiles",
    "profile_by_id",
    "profile_wire",
]
