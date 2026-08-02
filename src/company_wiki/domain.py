"""
domain.py — 核心领域模型

定义系统中的核心实体：Company, Sector, Theme, Question, SourceRecord, Claim 等。
所有 ID 均为稳定 ID，不随标题/名称变更。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


# ── 实体类型 ──────────────────────────────

class EntityType(str, Enum):
    COMPANY = "company"
    SECTOR = "sector"
    THEME = "theme"


class SourceKind(str, Enum):
    """来源类型 — 区分事实来源的认识论层次"""
    REGULATORY = "regulatory"          # 监管/定期报告（年报、半年报、季报）
    COMPANY_ANNOUNCEMENT = "company_announcement"  # 公司公告
    IR = "ir"                          # 投资者关系活动
    BROKER_RESEARCH = "broker_research"  # 券商研报
    ORIGINAL_NEWS = "original_news"    # 原创新闻
    AGGREGATED_NEWS = "aggregated_news"  # 转载/聚合新闻
    MODEL_INFERENCE = "model_inference"  # 模型推断


class ClaimType(str, Enum):
    """知识声明类型"""
    FACT = "fact"          # 可验证的事实
    OPINION = "opinion"    # 观点/判断
    PREDICTION = "prediction"  # 预测
    ASSESSMENT = "assessment"  # 综合评估


class AnswerState(str, Enum):
    """问题回答状态"""
    UNANSWERED = "unanswered"
    PARTIAL = "partial"
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    STALE = "stale"


# ── 核心实体 ──────────────────────────────

@dataclass
class Entity:
    """三类一等实体的基类"""
    id: str                    # 稳定 ID（如 "SZSE:002371" 或 "sector:半导体设备"）
    name: str                  # 显示名称
    entity_type: EntityType = EntityType.COMPANY  # 子类在 __post_init__ 中覆盖
    aliases: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class Company(Entity):
    """公司实体"""
    ticker: str = ""
    exchange: str = ""
    sectors: list[str] = field(default_factory=list)   # sector IDs
    themes: list[str] = field(default_factory=list)     # theme IDs
    position: str = ""
    competes_with: list[str] = field(default_factory=list)  # competitor entity IDs
    news_queries: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.entity_type = EntityType.COMPANY


@dataclass
class Sector(Entity):
    """行业实体"""
    companies: list[str] = field(default_factory=list)  # company IDs
    default_questions: list[str] = field(default_factory=list)  # question IDs

    def __post_init__(self):
        self.entity_type = EntityType.SECTOR


@dataclass
class Theme(Entity):
    """主题实体"""
    companies: list[str] = field(default_factory=list)  # company IDs
    related_sectors: list[str] = field(default_factory=list)  # sector IDs

    def __post_init__(self):
        self.entity_type = EntityType.THEME


# ── 问题 ──────────────────────────────

@dataclass
class Question:
    """研究问题"""
    id: str                    # 稳定 ID（如 "Q001"）
    text: str                  # 问题文本
    owner: Optional[str] = None  # entity ID（公司/行业/主题），None 表示跨实体
    priority: str = "medium"   # high / medium / low
    status: str = "active"     # active / archived / superseded
    answer_state: AnswerState = AnswerState.UNANSWERED
    evidence_type: str = "news"  # 所需证据类型
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    last_answered_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    supersedes: Optional[str] = None  # 被替代的问题 ID


# ── 来源 ──────────────────────────────

@dataclass
class SourceRecord:
    """不可变来源记录"""
    source_id: str             # SHA-256 of content
    path: str                  # 文件路径（location，非身份）
    source_kind: SourceKind
    publisher: str = ""
    published_at: Optional[datetime] = None
    fetched_at: datetime = field(default_factory=datetime.now)
    entity_hints: list[str] = field(default_factory=list)  # entity IDs
    content_hash: str = ""     # 内容哈希
    size: int = 0
    url: str = ""
    license: str = ""
    quality_score: float = 0.0


# ── 证据与声明 ──────────────────────────────

@dataclass
class EvidenceSpan:
    """来源中的证据片段"""
    source_id: str
    page: Optional[int] = None
    paragraph: Optional[int] = None
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None
    summary_hash: str = ""     # 证据摘要的哈希


@dataclass
class Claim:
    """知识声明"""
    claim_id: str
    claim_type: ClaimType
    text: str
    entity_id: str             # 关联实体
    question_id: Optional[str] = None  # 关联问题
    evidence: list[EvidenceSpan] = field(default_factory=list)

    # 四类时间
    event_time: Optional[datetime] = None       # 事实发生时间
    published_at: Optional[datetime] = None     # 来源发布时间
    observed_at: Optional[datetime] = None      # 系统采集时间
    effective_from: Optional[datetime] = None   # 知识生效时间

    # 数值
    metric: str = ""
    value: str = ""
    unit: str = ""
    currency: str = ""
    accounting_period: str = ""

    # 关系
    confidence: float = 0.5
    supersedes: Optional[str] = None   # 被替代的 claim ID
    corrects: Optional[str] = None     # 被纠正的 claim ID
    contradicts: Optional[str] = None  # 矛盾的 claim ID
    source_kind: SourceKind = SourceKind.ORIGINAL_NEWS


@dataclass
class KnowledgePatch:
    """知识提案 — 来源→知识的结构化提案"""
    patch_id: str
    source_id: str
    claims: list[Claim] = field(default_factory=list)
    targets: list[str] = field(default_factory=list)  # 目标页面 entity IDs
    routing_reason: str = ""
    risk_level: str = "medium"   # low / medium / high
    validation_result: str = ""  # passed / failed / pending
    model_version: str = ""
    prompt_version: str = ""
    schema_version: str = ""
    created_at: datetime = field(default_factory=datetime.now)
