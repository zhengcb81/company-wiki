"""
tests/unit/test_proposal.py — 提议系统测试
"""


import pytest

from company_wiki.proposal import (
    AutonomyGate,
    AutonomyLevel,
    Proposal,
    ProposalManager,
    ProposalStatus,
    ProposalType,
    RiskLevel,
    RiskMatrix,
)


# ── Proposal 测试 ──────────────────────────────

class TestProposal:
    def test_proposal_creation(self):
        """测试提议创建"""
        proposal = Proposal(
            proposal_id="prop-001",
            proposal_type=ProposalType.NEW_ENTITY,
            risk_level=RiskLevel.MEDIUM,
            title="新增北方华创",
            description="添加北方华创到知识库",
        )
        assert proposal.proposal_id == "prop-001"
        assert proposal.status == ProposalStatus.DETECTED
        assert proposal.risk_level == RiskLevel.MEDIUM

    def test_proposal_to_dict(self):
        """测试提议序列化"""
        proposal = Proposal(
            proposal_id="prop-001",
            proposal_type=ProposalType.NEW_ENTITY,
            risk_level=RiskLevel.MEDIUM,
            title="测试提议",
            description="测试描述",
            evidence=["证据1"],
        )

        d = proposal.to_dict()
        assert d["proposal_id"] == "prop-001"
        assert d["proposal_type"] == "new_entity"
        assert len(d["evidence"]) == 1

    def test_proposal_save_load(self, tmp_path):
        """测试提议保存和加载"""
        proposal = Proposal(
            proposal_id="prop-001",
            proposal_type=ProposalType.NEW_ENTITY,
            risk_level=RiskLevel.MEDIUM,
            title="测试提议",
            description="测试描述",
            evidence=["证据1"],
            evidence_sources=["来源1"],
            impact_scope=["影响1"],
        )

        # 保存
        path = tmp_path / "prop-001.json"
        proposal.save(path)

        # 加载
        loaded = Proposal.load(path)
        assert loaded.proposal_id == "prop-001"
        assert loaded.title == "测试提议"
        assert len(loaded.evidence) == 1


# ── RiskMatrix 测试 ──────────────────────────────

class TestRiskMatrix:
    def test_low_risk(self):
        """测试低风险评估"""
        matrix = RiskMatrix()
        assert matrix.assess_risk("add_alias") == RiskLevel.LOW
        assert matrix.assess_risk("update_metadata") == RiskLevel.LOW

    def test_medium_risk(self):
        """测试中风险评估"""
        matrix = RiskMatrix()
        assert matrix.assess_risk("new_entity") == RiskLevel.MEDIUM
        assert matrix.assess_risk("new_topic") == RiskLevel.MEDIUM

    def test_high_risk(self):
        """测试高风险评估"""
        matrix = RiskMatrix()
        assert matrix.assess_risk("update_schema") == RiskLevel.HIGH
        assert matrix.assess_risk("update_prompt") == RiskLevel.HIGH

    def test_critical_risk(self):
        """测试关键风险评估"""
        matrix = RiskMatrix()
        assert matrix.assess_risk("delete_entity") == RiskLevel.CRITICAL
        assert matrix.assess_risk("archive_stale") == RiskLevel.CRITICAL

    def test_unknown_risk(self):
        """测试未知操作风险评估"""
        matrix = RiskMatrix()
        assert matrix.assess_risk("unknown_action") == RiskLevel.LOW


# ── ProposalManager 测试 ──────────────────────────────

class TestProposalManager:
    def test_create_proposal(self, tmp_path):
        """测试创建提议"""
        manager = ProposalManager(tmp_path / "proposals")

        proposal = manager.create_proposal(
            proposal_type=ProposalType.NEW_ENTITY,
            title="新增北方华创",
            description="添加北方华创到知识库",
            entity_id="北方华创",
        )

        assert proposal.proposal_id.startswith("prop-")
        assert proposal.status == ProposalStatus.PROPOSED
        assert proposal.risk_level == RiskLevel.MEDIUM  # NEW_ENTITY 是中风险

    def test_attach_evidence(self, tmp_path):
        """测试附加证据"""
        manager = ProposalManager(tmp_path / "proposals")

        proposal = manager.create_proposal(
            proposal_type=ProposalType.NEW_ENTITY,
            title="测试",
            description="测试",
        )

        # 附加证据
        updated = manager.attach_evidence(
            proposal.proposal_id,
            evidence=["证据1", "证据2"],
            sources=["来源1", "来源2"],
        )

        assert updated.status == ProposalStatus.EVIDENCE_ATTACHED
        assert len(updated.evidence) == 2

    def test_simulate_impact(self, tmp_path):
        """测试模拟影响"""
        manager = ProposalManager(tmp_path / "proposals")

        proposal = manager.create_proposal(
            proposal_type=ProposalType.NEW_ENTITY,
            title="测试",
            description="测试",
        )

        updated = manager.simulate_impact(
            proposal.proposal_id,
            impact_scope=["影响1", "影响2"],
        )

        assert updated.status == ProposalStatus.IMPACT_SIMULATED
        assert updated.impact_simulated is True

    def test_validate(self, tmp_path):
        """测试验证"""
        manager = ProposalManager(tmp_path / "proposals")

        proposal = manager.create_proposal(
            proposal_type=ProposalType.NEW_ENTITY,
            title="测试",
            description="测试",
        )

        updated = manager.validate(proposal.proposal_id, notes="验证通过")

        assert updated.status == ProposalStatus.VALIDATED
        assert updated.validated is True

    def test_approve(self, tmp_path):
        """测试批准"""
        manager = ProposalManager(tmp_path / "proposals")

        proposal = manager.create_proposal(
            proposal_type=ProposalType.NEW_ENTITY,
            title="测试",
            description="测试",
        )

        updated = manager.approve(proposal.proposal_id, approved_by="审核人")

        assert updated.status == ProposalStatus.APPROVED
        assert updated.approved_by == "审核人"

    def test_reject(self, tmp_path):
        """测试拒绝"""
        manager = ProposalManager(tmp_path / "proposals")

        proposal = manager.create_proposal(
            proposal_type=ProposalType.NEW_ENTITY,
            title="测试",
            description="测试",
        )

        updated = manager.reject(proposal.proposal_id, reason="不符合要求")

        assert updated.status == ProposalStatus.REJECTED
        assert updated.rejection_reason == "不符合要求"

    def test_mark_canary(self, tmp_path):
        """测试标记为金丝雀"""
        manager = ProposalManager(tmp_path / "proposals")

        proposal = manager.create_proposal(
            proposal_type=ProposalType.NEW_ENTITY,
            title="测试",
            description="测试",
        )

        updated = manager.mark_canary(proposal.proposal_id)

        assert updated.status == ProposalStatus.CANARY
        assert updated.applied_at is not None

    def test_promote(self, tmp_path):
        """测试推广"""
        manager = ProposalManager(tmp_path / "proposals")

        proposal = manager.create_proposal(
            proposal_type=ProposalType.NEW_ENTITY,
            title="测试",
            description="测试",
        )

        updated = manager.promote(proposal.proposal_id)

        assert updated.status == ProposalStatus.PROMOTED
        assert updated.promoted_at is not None

    def test_rollback(self, tmp_path):
        """测试回滚"""
        manager = ProposalManager(tmp_path / "proposals")

        proposal = manager.create_proposal(
            proposal_type=ProposalType.NEW_ENTITY,
            title="测试",
            description="测试",
        )

        updated = manager.rollback(proposal.proposal_id, reason="发现问题")

        assert updated.status == ProposalStatus.ROLLED_BACK

    def test_list_proposals(self, tmp_path):
        """测试列出提议"""
        manager = ProposalManager(tmp_path / "proposals")

        # 创建多个提议
        manager.create_proposal(ProposalType.NEW_ENTITY, "提议1", "描述1")
        manager.create_proposal(ProposalType.NEW_TOPIC, "提议2", "描述2")
        manager.create_proposal(ProposalType.UPDATE_ALIAS, "提议3", "描述3")

        # 列出全部
        all_proposals = manager.list_proposals()
        assert len(all_proposals) == 3

        # 按状态过滤
        proposed = manager.list_proposals(status=ProposalStatus.PROPOSED)
        assert len(proposed) == 3

    def test_full_lifecycle(self, tmp_path):
        """测试完整生命周期"""
        manager = ProposalManager(tmp_path / "proposals")

        # 创建提议
        proposal = manager.create_proposal(
            proposal_type=ProposalType.NEW_ENTITY,
            title="完整生命周期测试",
            description="测试",
        )

        # 附加证据
        proposal = manager.attach_evidence(proposal.proposal_id, ["证据"], ["来源"])
        assert proposal.status == ProposalStatus.EVIDENCE_ATTACHED

        # 模拟影响
        proposal = manager.simulate_impact(proposal.proposal_id, ["影响"])
        assert proposal.status == ProposalStatus.IMPACT_SIMULATED

        # 验证
        proposal = manager.validate(proposal.proposal_id)
        assert proposal.status == ProposalStatus.VALIDATED

        # 批准
        proposal = manager.approve(proposal.proposal_id, "审核人")
        assert proposal.status == ProposalStatus.APPROVED

        # 金丝雀测试
        proposal = manager.mark_canary(proposal.proposal_id)
        assert proposal.status == ProposalStatus.CANARY

        # 推广
        proposal = manager.promote(proposal.proposal_id)
        assert proposal.status == ProposalStatus.PROMOTED


# ── AutonomyGate 测试 ──────────────────────────────

class TestAutonomyGate:
    def test_initial_level(self):
        """测试初始级别"""
        gate = AutonomyGate()
        assert gate.current_level == AutonomyLevel.OBSERVE_ONLY

    def test_can_advance_observe_to_propose(self):
        """测试从观察到提议的晋级条件"""
        gate = AutonomyGate()
        gate.current_level = AutonomyLevel.OBSERVE_ONLY

        # 不够10个提议
        gate.proposals_created = 5
        assert gate.can_advance() is False

        # 达到10个提议
        gate.proposals_created = 10
        assert gate.can_advance() is True

    def test_can_advance_propose_to_reviewed(self):
        """测试从提议到审核的晋级条件"""
        gate = AutonomyGate()
        gate.current_level = AutonomyLevel.PROPOSE

        # 不够5个批准
        gate.proposals_approved = 3
        assert gate.can_advance() is False

        # 达到5个批准，但批准率不够
        gate.proposals_approved = 5
        gate.proposals_rejected = 5  # 批准率 50%
        assert gate.can_advance() is False

        # 批准率达到80%
        gate.proposals_rejected = 1  # 批准率 83%
        assert gate.can_advance() is True

    def test_can_advance_reviewed_to_sampled(self):
        """测试从审核到采样的晋级条件"""
        gate = AutonomyGate()
        gate.current_level = AutonomyLevel.REVIEWED_APPLY

        # 不够10个自动应用
        gate.auto_applied = 5
        assert gate.can_advance() is False

        # 达到10个自动应用，但回滚率太高
        gate.auto_applied = 10
        gate.auto_rollback = 2  # 回滚率 20%
        assert gate.can_advance() is False

        # 回滚率降到10%以下
        gate.auto_rollback = 1  # 回滚率 10%
        assert gate.can_advance() is True

    def test_advance(self):
        """测试晋级"""
        gate = AutonomyGate()
        gate.current_level = AutonomyLevel.OBSERVE_ONLY
        gate.proposals_created = 10

        assert gate.advance() is True
        assert gate.current_level == AutonomyLevel.PROPOSE

    def test_advance_cannot(self):
        """测试无法晋级"""
        gate = AutonomyGate()
        gate.current_level = AutonomyLevel.OBSERVE_ONLY
        gate.proposals_created = 5

        assert gate.advance() is False
        assert gate.current_level == AutonomyLevel.OBSERVE_ONLY

    def test_demote(self):
        """测试降级"""
        gate = AutonomyGate()
        gate.current_level = AutonomyLevel.PROPOSE

        gate.demote("测试降级")
        assert gate.current_level == AutonomyLevel.OBSERVE_ONLY

    def test_demote_at_initial(self):
        """测试在初始级别降级"""
        gate = AutonomyGate()
        gate.current_level = AutonomyLevel.OBSERVE_ONLY

        gate.demote("测试降级")
        assert gate.current_level == AutonomyLevel.OBSERVE_ONLY  # 保持不变

    def test_approval_rate(self):
        """测试批准率计算"""
        gate = AutonomyGate()
        gate.proposals_approved = 8
        gate.proposals_rejected = 2

        assert gate.approval_rate == pytest.approx(0.8)

    def test_auto_rollback_rate(self):
        """测试自动回滚率计算"""
        gate = AutonomyGate()
        gate.auto_applied = 100
        gate.auto_rollback = 5

        assert gate.auto_rollback_rate == pytest.approx(0.05)
