"""Immutable profile objects and the shared building blocks they compose from.

``design.md`` section 1 and 9 forbid one pipeline (or one skill) per document type. The
model here is therefore *composition*: a small set of shared section blocks, shared
semantic-unit sets and shared summary focus fragments, assembled into fifteen profiles.

Two rules are enforced by construction rather than by convention:

* every profile version is a digest of its own content, so a profile cannot drift
  without the version changing;
* ``get_profile`` output is a frozen mapping view, so a caller cannot mutate the shared
  registry entry by accident.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Iterable
import unicodedata

from . import vocabulary as v


@dataclass(frozen=True)
class SectionPriority:
    """A prioritized section role with the textual aliases that identify it."""

    section_role: str
    aliases: tuple[str, ...]
    priority: int

    def __post_init__(self) -> None:
        if self.section_role not in v.SECTION_ROLES:
            raise ValueError(f"unknown section_role: {self.section_role!r}")
        if self.priority not in (1, 2, 3):
            raise ValueError(f"priority must be 1..3, got {self.priority!r}")
        if not self.aliases:
            raise ValueError(f"{self.section_role} needs at least one alias")
        for alias in self.aliases:
            if not alias or alias != alias.strip():
                raise ValueError(f"alias must be non-empty and trimmed: {alias!r}")

    def to_wire(self) -> dict:
        return {
            "section_role": self.section_role,
            "aliases": list(self.aliases),
            "priority": self.priority,
        }


@dataclass(frozen=True)
class Profile:
    """A composable reading strategy. Content-addressed by ``profile_version``."""

    profile_id: str
    family: str
    section_priorities: tuple[SectionPriority, ...]
    semantic_units: tuple[str, ...]
    summary_focus: str
    negative_hints: tuple[str, ...] = ()
    regime: str = "unknown"
    version: int = 1

    def __post_init__(self) -> None:
        if not self.profile_id:
            raise ValueError("profile_id must be non-empty")
        if self.family not in v.FAMILIES:
            raise ValueError(f"unknown family: {self.family!r}")
        if self.regime not in v.REGIMES:
            raise ValueError(f"unknown regime: {self.regime!r}")
        if not self.section_priorities:
            raise ValueError(f"{self.profile_id} needs at least one section priority")
        for semantic_unit in self.semantic_units:
            if semantic_unit not in v.SEMANTIC_UNITS:
                raise ValueError(f"unknown semantic unit: {semantic_unit!r}")
        if not self.summary_focus:
            raise ValueError(f"{self.profile_id} needs a summary focus")
        roles = [entry.section_role for entry in self.section_priorities]
        duplicates = {role for role in roles if roles.count(role) > 1}
        if duplicates:
            raise ValueError(f"{self.profile_id} repeats section roles: {sorted(duplicates)}")

    @property
    def profile_version(self) -> str:
        """Content digest: identical content means an identical version."""
        payload = json.dumps(
            {
                "profile_id": self.profile_id,
                "family": self.family,
                "regime": self.regime,
                "version": self.version,
                "section_priorities": [entry.to_wire() for entry in self.section_priorities],
                "semantic_units": list(self.semantic_units),
                "summary_focus": self.summary_focus,
                "negative_hints": list(self.negative_hints),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = sha256(payload.encode("utf-8")).hexdigest()
        return f"{self.profile_id}/v{self.version}+{digest[:12]}"

    def to_wire(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "family": self.family,
            "section_priorities": [entry.to_wire() for entry in self.section_priorities],
            "semantic_units": list(self.semantic_units),
            "summary_focus": self.summary_focus,
            "negative_hints": list(self.negative_hints),
        }


# --- shared negative hints ------------------------------------------------------------
# design.md section 5: TOC/headers/signatures/plain-financials are soft hints, never a
# hard delete rule for a whole chapter.

NEGATIVE_HINTS_COMMON: tuple[str, ...] = (
    "目录页与正文标题同名时以正文为准",
    "重复页眉/页脚不构成新章节",
    "签章、确认意见、封面落款不承载业务事实",
    "三张主表与常规账龄表按财务口径处理",
)

NEGATIVE_HINTS_PAGINATED: tuple[str, ...] = (
    "页码页脚（x / N、Page n of m、– n –）不是正文内容",
)

NEGATIVE_HINTS_HTML: tuple[str, ...] = (
    "站点导航与页脚样板文字不是披露内容",
    "交叉引用中提到的表单名称不构成本文档类型",
)

NEGATIVE_HINTS_BILINGUAL: tuple[str, ...] = (
    "中英对照同一事实不得重复计数",
    "不可依赖词形相似推断跨语言对应",
)


# --- shared section blocks ------------------------------------------------------------
# Each block is a reusable, regime-legitimate set of aliases. Profiles combine blocks;
# they never invent a mixed vocabulary that would leak SEC item numbers into HK reports.

CN_COMMON_SECTIONS: tuple[SectionPriority, ...] = (
    SectionPriority(
        "administrative",
        ("第一节 释义", "公司简介", "公司资料", "释义"),
        3,
    ),
    SectionPriority(
        "operating_metrics",
        ("主要财务指标", "主要会计数据和财务指标", "非经常性损益项目", "财务指标"),
        2,
    ),
)

CN_BUSINESS_SECTIONS: tuple[SectionPriority, ...] = (
    SectionPriority(
        "management_discussion",
        ("第三节 管理层讨论与分析", "管理层讨论与分析", "经营情况讨论与分析"),
        1,
    ),
    SectionPriority(
        "business",
        ("主营业务", "公司业务", "业务概要", "经营模式", "研发投入", "技术与研发"),
        1,
    ),
    SectionPriority(
        "industry",
        ("行业情况", "行业格局", "所处行业", "行业发展趋势"),
        2,
    ),
    SectionPriority("outlook", ("未来发展", "未来计划", "经营计划", "展望"), 1),
    SectionPriority("risk", ("风险因素", "重大风险提示", "风险提示"), 1),
    SectionPriority(
        "financial_notes",
        ("财务报告", "财务报表", "重要事项", "公司治理"),
        3,
    ),
)

CN_FUNDRAISING_SECTIONS: tuple[SectionPriority, ...] = (
    SectionPriority(
        "fundraising",
        (
            "募集资金运用",
            "本次募集资金运用",
            "募集资金使用",
            "募集资金投资项目",
            "募集资金使用金额",
            "项目投资计划",
            "项目建设周期",
            "项目建设用地",
            "项目投资回报",
            "项目备案",
            "所得款项用途",
            "募投项目",
        ),
        1,
    ),
    SectionPriority("business", ("业务与技术", "主营业务", "经营模式", "竞争优势"), 1),
    SectionPriority("industry", ("行业概览", "行业情况", "行业发展趋势", "市场规模"), 2),
    SectionPriority("outlook", ("未来发展规划", "发展战略", "未来计划"), 2),
    SectionPriority("risk", ("风险因素", "重大事项提示", "风险提示"), 1),
    SectionPriority(
        "financial_notes",
        ("财务会计信息", "管理层分析", "财务报告", "历史及公司架构", "公司架构"),
        3,
    ),
)

SEC_10K_SECTIONS: tuple[SectionPriority, ...] = (
    SectionPriority("business", ("item 1. business", "item 1 business", "our segments"), 1),
    SectionPriority("risk", ("item 1a. risk factors", "item 1a risk factors"), 1),
    SectionPriority(
        "management_discussion",
        (
            "item 7. management's discussion and analysis",
            "item 7 management's discussion and analysis",
        ),
        1,
    ),
    SectionPriority(
        "operating_metrics",
        ("remaining performance obligations", "azure revenue", "segment revenue"),
        2,
    ),
    SectionPriority("financial_notes", ("item 8. financial statements", "notes to financial statements"), 3),
)

SEC_10Q_SECTIONS: tuple[SectionPriority, ...] = (
    SectionPriority(
        "management_discussion",
        (
            "item 2. management's discussion and analysis",
            "item 2 management's discussion and analysis",
        ),
        1,
    ),
    SectionPriority("business", ("our business", "reportable segment", "one operating segment"), 1),
    SectionPriority("operating_metrics", ("subscriptions", "deferred revenues", "revenues"), 2),
    SectionPriority("risk", ("part ii", "item 1a. risk factors", "risk factors"), 2),
    SectionPriority("financial_notes", ("item 1. financial statements", "condensed consolidated"), 3),
)

SEC_20F_SECTIONS: tuple[SectionPriority, ...] = (
    SectionPriority(
        "business",
        ("item 4. information on the company", "item 4. information", "b. business overview", "business overview"),
        1,
    ),
    SectionPriority(
        "management_discussion",
        ("item 5. operating and financial review", "item 5. operating", "operating and financial review"),
        1,
    ),
    SectionPriority(
        "risk",
        ("item 3. key information", "item 3. key information—d. risk factors", "d. risk factors"),
        1,
    ),
    SectionPriority("operating_metrics", ("organizational structure", "vie subsidiaries"), 2),
    SectionPriority("financial_notes", ("item 18. financial statements", "consolidated financial statements"), 3),
)

HK_BILINGUAL_SECTIONS: tuple[SectionPriority, ...] = (
    SectionPriority(
        "management_discussion",
        ("management discussion and analysis", "管理層討論與分析", "管理层讨论与分析"),
        1,
    ),
    SectionPriority(
        "business",
        ("business review and outlook", "業務回顧及展望", "业务回顾及展望", "business review"),
        1,
    ),
    SectionPriority(
        "outlook",
        ("recent developments after the reporting period", "報告期後事項", "报告期后事项", "business outlook", "展望"),
        1,
    ),
    SectionPriority(
        "operating_metrics",
        ("store network", "門店網絡", "financial performance highlights", "財務表現摘要", "財務表現摘要"),
        2,
    ),
    SectionPriority("risk", ("principal risks", "主要風險", "risk management", "風險管理"), 2),
    SectionPriority(
        "financial_notes",
        ("directors' report", "董事會報告", "corporate governance report", "企業管治報告", "independent auditor's report"),
        3,
    ),
)

HK_OFFERING_SECTIONS: tuple[SectionPriority, ...] = (
    SectionPriority(
        "fundraising",
        (
            "future plans and use of proceeds",
            "未來計劃及所得款項用途",
            "所得款項用途",
            "全球發售",
            "全球发售",
        ),
        1,
    ),
    SectionPriority("business", ("業務", "业务", "our business"), 1),
    SectionPriority("industry", ("行業概覽", "行业概览", "industry overview"), 2),
    SectionPriority("risk", ("風險因素", "风险因素", "risk factors"), 1),
    SectionPriority(
        "financial_notes",
        ("歷史及公司架構", "历史及公司架构", "法規", "法规", "會計師報告", "会计师报告"),
        3,
    ),
)

SEC_REGISTRATION_SECTIONS: tuple[SectionPriority, ...] = (
    SectionPriority("business", ("Business", "Description of Business"), 1),
    SectionPriority("fundraising", ("Use of Proceeds", "Selling Stockholders", "Underwriting"), 1),
    SectionPriority("industry", ("Market and Industry Data",), 2),
    SectionPriority("risk", ("Risk Factors",), 1),
    SectionPriority("management_discussion", ("Management's Discussion and Analysis",), 1),
    SectionPriority("financial_notes", ("Notes to Financial Statements",), 3),
)


GENERIC_SECTIONS: tuple[SectionPriority, ...] = (
    SectionPriority(
        "business",
        ("业务", "主要内容", "背景", "概述", "overview", "summary"),
        2,
    ),
    SectionPriority("management_discussion", ("讨论", "分析", "discussion", "analysis"), 2),
    SectionPriority("risk", ("风险", "risk"), 2),
    SectionPriority("unknown", ("其他", "附录", "other", "appendix"), 3),
)

ADMINISTRATIVE_SECTIONS: tuple[SectionPriority, ...] = (
    SectionPriority(
        "administrative",
        (
            "确认意见",
            "述职报告",
            "管理制度",
            "管理办法",
            "会议通知",
            "公告",
            "承诺",
            "声明",
            "签章",
        ),
        1,
    ),
    SectionPriority("unknown", ("其他",), 3),
)


def combine(*blocks: Iterable[SectionPriority]) -> tuple[SectionPriority, ...]:
    """Compose generic-to-specific blocks without losing aliases.

    Role order and the first spelling of each normalized alias are stable. Later
    blocks explicitly override the role priority; they add aliases rather than
    replacing the vocabulary of an earlier market or purpose block.
    """
    merged: dict[str, SectionPriority] = {}
    for block in blocks:
        for entry in block:
            existing = merged.get(entry.section_role)
            aliases = (*existing.aliases, *entry.aliases) if existing else entry.aliases
            unique: dict[str, str] = {}
            for alias in aliases:
                key = " ".join(unicodedata.normalize("NFKC", alias).casefold().split())
                unique.setdefault(key, alias)
            merged[entry.section_role] = SectionPriority(
                entry.section_role, tuple(unique.values()), entry.priority
            )
    return tuple(merged.values())


@dataclass(frozen=True)
class SharedFocus:
    """Summary focus fragments reused across families, per the card's reuse rule."""

    business_and_risk: str = field(
        default=(
            "记录报告期已发生的经营事实、业务与产品变化、客户与订单、产能与项目进展、"
            "公司计划、以及有来源支持的具体风险与限制；数字保留单位、币种、期间与口径。"
        )
    )
    periodic_change: str = field(
        default=(
            "总结本报告期相较可比期间的变化，区分已发生事实、计划与预测，"
            "未披露项标注未披露而不是零。"
        )
    )


SHARED_FOCUS = SharedFocus()
