"""
question_model.py — 问题驱动语义模型

QuestionAnswer: complete/partial/supported/contradicted/stale
Materiality: 重要性评级
Falsification: 证伪条件
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class AnswerState(str, Enum):
    """回答状态 — 不以关键词或是否有文字代替回答程度"""
    UNANSWERED = "unanswered"        # 无任何证据
    PARTIAL = "partial"              # 部分证据，不完整
    SUPPORTED = "supported"          # 有支持证据
    CONTRADICTED = "contradicted"    # 存在矛盾证据
    STALE = "stale"                  # 证据过期


class Materiality(str, Enum):
    """重要性评级"""
    CRITICAL = "critical"      # 关键决策影响
    HIGH = "high"              # 重要信息
    MEDIUM = "medium"          # 一般信息
    LOW = "low"                # 次要信息


class SourceTier(str, Enum):
    """来源认识论分层 — 按可靠性排序"""
    REGULATORY = "regulatory"              # 监管/定期报告（最可靠）
    COMPANY_ANNOUNCEMENT = "company_announcement"  # 公司公告
    IR = "ir"                              # 投资者关系
    BROKER_RESEARCH = "broker_research"    # 券商研报
    ORIGINAL_NEWS = "original_news"        # 原创新闻
    AGGREGATED_NEWS = "aggregated_news"    # 转载/聚合
    MODEL_INFERENCE = "model_inference"    # 模型推断（最不可靠）


@dataclass
class FalsificationCondition:
    """证伪条件"""
    condition: str           # 证伪描述
    evidence_type: str       # 需要的证据类型
    source_tier: SourceTier  # 最低可靠来源等级


@dataclass
class TemporalInfo:
    """四类时间"""
    published_at: Optional[datetime] = None      # 发布时间
    fetched_at: Optional[datetime] = None        # 采集/观察时间
    effective_period: Optional[str] = None       # 有效期间（如 "2025Q1", "2025年"）
    valid_from: Optional[datetime] = None        # 生效开始
    valid_to: Optional[datetime] = None          # 生效结束（None = 仍有效）

    @property
    def is_current(self) -> bool:
        """是否当前有效"""
        now = datetime.now()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_to and now > self.valid_to:
            return False
        return True


@dataclass
class NumericValue:
    """数值结构化"""
    metric: str              # 指标名称
    value: float             # 数值
    unit: str                # 单位
    currency: str = "CNY"    # 货币
    period: Optional[str] = None    # 期间
    scope: Optional[str] = None     # 范围（合并/母公司）
    restatement: bool = False       # 是否更正
    evidence: Optional[str] = None  # 证据来源

    def __str__(self) -> str:
        parts = [f"{self.metric}: {self.value} {self.unit}"]
        if self.period:
            parts.append(f"({self.period})")
        return " ".join(parts)


@dataclass
class Question:
    """研究问题"""
    question_id: str
    text: str
    entity_id: str
    topic: Optional[str] = None
    answer_state: AnswerState = AnswerState.UNANSWERED
    materiality: Materiality = Materiality.MEDIUM
    refresh_sla_days: int = 30
    falsification_conditions: list[FalsificationCondition] = field(default_factory=list)
    required_evidence_types: list[str] = field(default_factory=list)
    answer_claims: list[str] = field(default_factory=list)  # supporting claim IDs
    contradicting_claims: list[str] = field(default_factory=list)
    last_updated: Optional[datetime] = None
    stale_since: Optional[datetime] = None

    @property
    def is_stale(self) -> bool:
        """是否过期（超过刷新 SLA）"""
        if not self.last_updated:
            return True
        stale_threshold = datetime.now() - timedelta(days=self.refresh_sla_days)
        return self.last_updated < stale_threshold

    def update_answer_state(self, new_state: AnswerState, claim_id: Optional[str] = None):
        """更新回答状态"""
        self.answer_state = new_state
        self.last_updated = datetime.now()

        if claim_id:
            if new_state in (AnswerState.SUPPORTED, AnswerState.PARTIAL):
                if claim_id not in self.answer_claims:
                    self.answer_claims.append(claim_id)
            elif new_state == AnswerState.CONTRADICTED:
                if claim_id not in self.contradicting_claims:
                    self.contradicting_claims.append(claim_id)

        if new_state == AnswerState.STALE:
            self.stale_since = datetime.now()
        else:
            self.stale_since = None


@dataclass
class Assessment:
    """评估 — 只消费 verified active claims"""
    assessment_id: str
    entity_id: str
    topic: str
    claims: list[str] = field(default_factory=list)  # 依赖的 claim IDs
    claim_versions: dict[str, str] = field(default_factory=dict)  # claim_id → version
    interpretation: str = ""
    uncertainty: str = ""
    counter_evidence: str = ""
    prediction: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def dependency_count(self) -> int:
        return len(self.claims)

    def mark_stale_if_dependency_changed(self, claim_id: str, new_version: str) -> bool:
        """如果依赖的 claim 版本变化，标记为 stale"""
        if claim_id in self.claim_versions:
            if self.claim_versions[claim_id] != new_version:
                return True
        return False
