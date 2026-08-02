"""
proposal.py — Proposal-first 自我进化系统

提议与执行分离，所有变更通过提议流程。
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class ProposalStatus(str, Enum):
    """提议状态"""
    DETECTED = "detected"                    # 检测到变更需求
    PROPOSED = "proposed"                    # 已生成提议
    EVIDENCE_ATTACHED = "evidence_attached"  # 已附加证据
    IMPACT_SIMULATED = "impact_simulated"    # 已模拟影响
    VALIDATED = "validated"                  # 已验证
    APPROVED = "approved"                    # 已批准
    CANARY = "canary"                        # 金丝雀测试中
    PROMOTED = "promoted"                    # 已推广
    REJECTED = "rejected"                    # 已拒绝
    ROLLED_BACK = "rolled_back"              # 已回滚


class ProposalType(str, Enum):
    """提议类型"""
    NEW_ENTITY = "new_entity"          # 新实体
    NEW_TOPIC = "new_topic"            # 新主题
    UPDATE_ALIAS = "update_alias"      # 更新别名
    UPDATE_PRIORITY = "update_priority"  # 更新优先级
    UPDATE_SCHEMA = "update_schema"    # 更新 schema
    UPDATE_PROMPT = "update_prompt"    # 更新 prompt
    FIX_CONTRADICTION = "fix_contradiction"  # 修复矛盾
    ARCHIVE_STALE = "archive_stale"    # 归档过期内容


class RiskLevel(str, Enum):
    """风险等级"""
    LOW = "low"          # 低风险（可自动应用）
    MEDIUM = "medium"    # 中风险（需要审核）
    HIGH = "high"        # 高风险（需要人工审核）
    CRITICAL = "critical"  # 关键风险（需要多人审核）


@dataclass
class Proposal:
    """变更提议"""
    proposal_id: str
    proposal_type: ProposalType
    risk_level: RiskLevel
    status: ProposalStatus = ProposalStatus.DETECTED
    title: str = ""
    description: str = ""
    entity_id: Optional[str] = None
    topic: Optional[str] = None

    # 证据
    evidence: list[str] = field(default_factory=list)
    evidence_sources: list[str] = field(default_factory=list)

    # 影响分析
    impact_scope: list[str] = field(default_factory=list)
    impact_simulated: bool = False

    # 验证
    validated: bool = False
    validation_notes: str = ""

    # 审核
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    # 执行
    applied_at: Optional[datetime] = None
    promoted_at: Optional[datetime] = None

    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "proposal_type": self.proposal_type.value,
            "risk_level": self.risk_level.value,
            "status": self.status.value,
            "title": self.title,
            "description": self.description,
            "entity_id": self.entity_id,
            "topic": self.topic,
            "evidence": self.evidence,
            "evidence_sources": self.evidence_sources,
            "impact_scope": self.impact_scope,
            "impact_simulated": self.impact_simulated,
            "validated": self.validated,
            "validation_notes": self.validation_notes,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejection_reason": self.rejection_reason,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "promoted_at": self.promoted_at.isoformat() if self.promoted_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def save(self, path: Path):
        """保存提议"""
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Proposal":
        """加载提议"""
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            proposal_id=data["proposal_id"],
            proposal_type=ProposalType(data["proposal_type"]),
            risk_level=RiskLevel(data["risk_level"]),
            status=ProposalStatus(data["status"]),
            title=data.get("title", ""),
            description=data.get("description", ""),
            entity_id=data.get("entity_id"),
            topic=data.get("topic"),
            evidence=data.get("evidence", []),
            evidence_sources=data.get("evidence_sources", []),
            impact_scope=data.get("impact_scope", []),
            impact_simulated=data.get("impact_simulated", False),
            validated=data.get("validated", False),
            validation_notes=data.get("validation_notes", ""),
            approved_by=data.get("approved_by"),
            approved_at=datetime.fromisoformat(data["approved_at"]) if data.get("approved_at") else None,
            rejection_reason=data.get("rejection_reason"),
            applied_at=datetime.fromisoformat(data["applied_at"]) if data.get("applied_at") else None,
            promoted_at=datetime.fromisoformat(data["promoted_at"]) if data.get("promoted_at") else None,
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )


@dataclass
class RiskMatrix:
    """风险矩阵"""
    # 低风险：可自动应用
    low_risk_actions: list[str] = field(default_factory=lambda: [
        "add_alias",
        "update_metadata",
        "fix_formatting",
    ])

    # 中风险：需要审核
    medium_risk_actions: list[str] = field(default_factory=lambda: [
        "new_entity",
        "new_topic",
        "update_priority",
    ])

    # 高风险：需要人工审核
    high_risk_actions: list[str] = field(default_factory=lambda: [
        "update_schema",
        "update_prompt",
        "fix_contradiction",
    ])

    # 关键风险：需要多人审核
    critical_risk_actions: list[str] = field(default_factory=lambda: [
        "delete_entity",
        "archive_stale",
        "update_core_config",
    ])

    def assess_risk(self, action: str) -> RiskLevel:
        """评估风险等级"""
        if action in self.critical_risk_actions:
            return RiskLevel.CRITICAL
        if action in self.high_risk_actions:
            return RiskLevel.HIGH
        if action in self.medium_risk_actions:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW


class ProposalManager:
    """
    提议管理器。

    管理提议的生命周期。
    """

    def __init__(self, proposals_dir: Path):
        self._dir = proposals_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._risk_matrix = RiskMatrix()

    def create_proposal(
        self,
        proposal_type: ProposalType,
        title: str,
        description: str,
        entity_id: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> Proposal:
        """创建提议"""
        proposal_id = f"prop-{proposal_type.value}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        risk_level = self._assess_risk(proposal_type)

        proposal = Proposal(
            proposal_id=proposal_id,
            proposal_type=proposal_type,
            risk_level=risk_level,
            title=title,
            description=description,
            entity_id=entity_id,
            topic=topic,
        )

        proposal.status = ProposalStatus.PROPOSED
        proposal.updated_at = datetime.now()

        # 保存
        proposal.save(self._dir / f"{proposal_id}.json")

        return proposal

    def attach_evidence(self, proposal_id: str, evidence: list[str], sources: list[str]) -> Proposal:
        """附加证据"""
        proposal = self.load_proposal(proposal_id)
        proposal.evidence = evidence
        proposal.evidence_sources = sources
        proposal.status = ProposalStatus.EVIDENCE_ATTACHED
        proposal.updated_at = datetime.now()
        proposal.save(self._dir / f"{proposal_id}.json")
        return proposal

    def simulate_impact(self, proposal_id: str, impact_scope: list[str]) -> Proposal:
        """模拟影响"""
        proposal = self.load_proposal(proposal_id)
        proposal.impact_scope = impact_scope
        proposal.impact_simulated = True
        proposal.status = ProposalStatus.IMPACT_SIMULATED
        proposal.updated_at = datetime.now()
        proposal.save(self._dir / f"{proposal_id}.json")
        return proposal

    def validate(self, proposal_id: str, notes: str = "") -> Proposal:
        """验证提议"""
        proposal = self.load_proposal(proposal_id)
        proposal.validated = True
        proposal.validation_notes = notes
        proposal.status = ProposalStatus.VALIDATED
        proposal.updated_at = datetime.now()
        proposal.save(self._dir / f"{proposal_id}.json")
        return proposal

    def approve(self, proposal_id: str, approved_by: str) -> Proposal:
        """批准提议"""
        proposal = self.load_proposal(proposal_id)

        # 检查风险等级
        if proposal.risk_level == RiskLevel.CRITICAL:
            # 关键风险需要额外审核
            pass  # 实际实现中应该检查审核人列表

        proposal.approved_by = approved_by
        proposal.approved_at = datetime.now()
        proposal.status = ProposalStatus.APPROVED
        proposal.updated_at = datetime.now()
        proposal.save(self._dir / f"{proposal_id}.json")
        return proposal

    def reject(self, proposal_id: str, reason: str) -> Proposal:
        """拒绝提议"""
        proposal = self.load_proposal(proposal_id)
        proposal.status = ProposalStatus.REJECTED
        proposal.rejection_reason = reason
        proposal.updated_at = datetime.now()
        proposal.save(self._dir / f"{proposal_id}.json")
        return proposal

    def mark_canary(self, proposal_id: str) -> Proposal:
        """标记为金丝雀测试"""
        proposal = self.load_proposal(proposal_id)
        proposal.status = ProposalStatus.CANARY
        proposal.applied_at = datetime.now()
        proposal.updated_at = datetime.now()
        proposal.save(self._dir / f"{proposal_id}.json")
        return proposal

    def promote(self, proposal_id: str) -> Proposal:
        """推广提议"""
        proposal = self.load_proposal(proposal_id)
        proposal.status = ProposalStatus.PROMOTED
        proposal.promoted_at = datetime.now()
        proposal.updated_at = datetime.now()
        proposal.save(self._dir / f"{proposal_id}.json")
        return proposal

    def rollback(self, proposal_id: str, reason: str) -> Proposal:
        """回滚提议"""
        proposal = self.load_proposal(proposal_id)
        proposal.status = ProposalStatus.ROLLED_BACK
        proposal.updated_at = datetime.now()
        proposal.save(self._dir / f"{proposal_id}.json")
        return proposal

    def load_proposal(self, proposal_id: str) -> Proposal:
        """加载提议"""
        path = self._dir / f"{proposal_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"提议不存在: {proposal_id}")
        return Proposal.load(path)

    def list_proposals(self, status: Optional[ProposalStatus] = None) -> list[Proposal]:
        """列出提议"""
        proposals = []
        for path in self._dir.glob("*.json"):
            try:
                proposal = Proposal.load(path)
                if status is None or proposal.status == status:
                    proposals.append(proposal)
            except Exception:
                continue
        return sorted(proposals, key=lambda p: p.created_at, reverse=True)

    def _assess_risk(self, proposal_type: ProposalType) -> RiskLevel:
        """评估提议风险"""
        type_to_action = {
            ProposalType.NEW_ENTITY: "new_entity",
            ProposalType.NEW_TOPIC: "new_topic",
            ProposalType.UPDATE_ALIAS: "add_alias",
            ProposalType.UPDATE_PRIORITY: "update_priority",
            ProposalType.UPDATE_SCHEMA: "update_schema",
            ProposalType.UPDATE_PROMPT: "update_prompt",
            ProposalType.FIX_CONTRADICTION: "fix_contradiction",
            ProposalType.ARCHIVE_STALE: "archive_stale",
        }
        action = type_to_action.get(proposal_type, "unknown")
        return self._risk_matrix.assess_risk(action)


# ── 自治晋级 ──────────────────────────────

class AutonomyLevel(str, Enum):
    """自治级别"""
    OBSERVE_ONLY = "observe_only"              # 只观察
    PROPOSE = "propose"                        # 可以提议
    REVIEWED_APPLY = "reviewed_apply"          # 审核后应用
    SAMPLED_LOW_RISK = "sampled_low_risk"      # 低风险自动应用（采样审核）
    SLO_GOVERNED = "slo_governed"              # SLO 管控下的自治


@dataclass
class AutonomyGate:
    """自治晋级门"""
    current_level: AutonomyLevel = AutonomyLevel.OBSERVE_ONLY
    proposals_created: int = 0
    proposals_approved: int = 0
    proposals_rejected: int = 0
    auto_applied: int = 0
    auto_rollback: int = 0

    @property
    def approval_rate(self) -> float:
        """批准率"""
        total = self.proposals_approved + self.proposals_rejected
        if total == 0:
            return 0.0
        return self.proposals_approved / total

    @property
    def auto_rollback_rate(self) -> float:
        """自动回滚率"""
        if self.auto_applied == 0:
            return 0.0
        return self.auto_rollback / self.auto_applied

    def can_advance(self) -> bool:
        """是否可以晋级"""
        if self.current_level == AutonomyLevel.OBSERVE_ONLY:
            return self.proposals_created >= 10
        elif self.current_level == AutonomyLevel.PROPOSE:
            return self.proposals_approved >= 5 and self.approval_rate >= 0.8
        elif self.current_level == AutonomyLevel.REVIEWED_APPLY:
            return self.auto_applied >= 10 and self.auto_rollback_rate <= 0.1
        elif self.current_level == AutonomyLevel.SAMPLED_LOW_RISK:
            return self.auto_applied >= 50 and self.auto_rollback_rate <= 0.05
        return False

    def advance(self) -> bool:
        """晋级"""
        if not self.can_advance():
            return False

        levels = list(AutonomyLevel)
        current_idx = levels.index(self.current_level)
        if current_idx < len(levels) - 1:
            self.current_level = levels[current_idx + 1]
            return True
        return False

    def demote(self, reason: str):
        """降级"""
        levels = list(AutonomyLevel)
        current_idx = levels.index(self.current_level)
        if current_idx > 0:
            self.current_level = levels[current_idx - 1]
