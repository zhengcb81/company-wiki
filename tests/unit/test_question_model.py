"""
tests/unit/test_question_model.py — 问题模型和路由测试
"""

from datetime import datetime, timedelta


from company_wiki.graph_adapter import GraphAdapter
from company_wiki.question_model import (
    AnswerState,
    Assessment,
    FalsificationCondition,
    Materiality,
    NumericValue,
    Question,
    SourceTier,
    TemporalInfo,
)
from company_wiki.routing import ClaimRouter, RoutingConfidence, ROUTING_GOLD_CASES


# ── Question 测试 ──────────────────────────────

class TestQuestion:
    def test_question_creation(self):
        """测试问题创建"""
        q = Question(
            question_id="Q001",
            text="北方华创2025年营收增速是多少？",
            entity_id="北方华创",
            topic="财务表现",
            materiality=Materiality.HIGH,
            refresh_sla_days=30,
        )
        assert q.question_id == "Q001"
        assert q.answer_state == AnswerState.UNANSWERED
        assert q.materiality == Materiality.HIGH

    def test_question_stale_detection(self):
        """测试过期检测"""
        q = Question(
            question_id="Q001",
            text="测试问题",
            entity_id="测试公司",
            refresh_sla_days=30,
        )

        # 从未更新 -> stale
        assert q.is_stale is True

        # 刚刚更新 -> not stale
        q.last_updated = datetime.now()
        assert q.is_stale is False

        # 31天前更新 -> stale
        q.last_updated = datetime.now() - timedelta(days=31)
        assert q.is_stale is True

    def test_update_answer_state_supported(self):
        """测试更新为 supported 状态"""
        q = Question(
            question_id="Q001",
            text="测试问题",
            entity_id="测试公司",
        )

        q.update_answer_state(AnswerState.SUPPORTED, claim_id="claim-001")

        assert q.answer_state == AnswerState.SUPPORTED
        assert "claim-001" in q.answer_claims
        assert q.last_updated is not None

    def test_update_answer_state_contradicted(self):
        """测试更新为 contradicted 状态"""
        q = Question(
            question_id="Q001",
            text="测试问题",
            entity_id="测试公司",
        )

        q.update_answer_state(AnswerState.CONTRADICTED, claim_id="claim-002")

        assert q.answer_state == AnswerState.CONTRADICTED
        assert "claim-002" in q.contradicting_claims

    def test_update_answer_state_stale(self):
        """测试更新为 stale 状态"""
        q = Question(
            question_id="Q001",
            text="测试问题",
            entity_id="测试公司",
        )

        q.update_answer_state(AnswerState.STALE)

        assert q.answer_state == AnswerState.STALE
        assert q.stale_since is not None

    def test_falsification_conditions(self):
        """测试证伪条件"""
        fc = FalsificationCondition(
            condition="营收增速低于10%",
            evidence_type="financial_report",
            source_tier=SourceTier.REGULATORY,
        )

        q = Question(
            question_id="Q001",
            text="测试问题",
            entity_id="测试公司",
            falsification_conditions=[fc],
        )

        assert len(q.falsification_conditions) == 1
        assert q.falsification_conditions[0].source_tier == SourceTier.REGULATORY


# ── TemporalInfo 测试 ──────────────────────────────

class TestTemporalInfo:
    def test_temporal_creation(self):
        """测试时间信息创建"""
        now = datetime.now()
        t = TemporalInfo(
            published_at=now,
            fetched_at=now + timedelta(hours=1),
            effective_period="2025Q1",
            valid_from=now,
            valid_to=now + timedelta(days=365),
        )
        assert t.published_at == now
        assert t.effective_period == "2025Q1"

    def test_is_current(self):
        """测试有效性判断"""
        now = datetime.now()

        # 有效期内
        t1 = TemporalInfo(valid_from=now - timedelta(days=1), valid_to=now + timedelta(days=1))
        assert t1.is_current is True

        # 已过期
        t2 = TemporalInfo(valid_from=now - timedelta(days=2), valid_to=now - timedelta(days=1))
        assert t2.is_current is False

        # 未开始
        t3 = TemporalInfo(valid_from=now + timedelta(days=1), valid_to=now + timedelta(days=2))
        assert t3.is_current is False

        # 无限制 -> 有效
        t4 = TemporalInfo()
        assert t4.is_current is True


# ── NumericValue 测试 ──────────────────────────────

class TestNumericValue:
    def test_numeric_creation(self):
        """测试数值创建"""
        nv = NumericValue(
            metric="营收",
            value=150.5,
            unit="亿元",
            currency="CNY",
            period="2025Q1",
            scope="合并",
        )
        assert nv.metric == "营收"
        assert nv.value == 150.5
        assert str(nv) == "营收: 150.5 亿元 (2025Q1)"

    def test_numeric_with_restatement(self):
        """测试更正值"""
        nv = NumericValue(
            metric="净利润",
            value=50.0,
            unit="亿元",
            restatement=True,
            evidence="年报更正公告",
        )
        assert nv.restatement is True


# ── SourceTier 测试 ──────────────────────────────

class TestSourceTier:
    def test_tier_ordering(self):
        """测试来源等级排序"""
        tiers = [
            SourceTier.REGULATORY,
            SourceTier.COMPANY_ANNOUNCEMENT,
            SourceTier.IR,
            SourceTier.BROKER_RESEARCH,
            SourceTier.ORIGINAL_NEWS,
            SourceTier.AGGREGATED_NEWS,
            SourceTier.MODEL_INFERENCE,
        ]
        # REGULATORY 应该最可靠
        assert tiers[0] == SourceTier.REGULATORY
        assert tiers[-1] == SourceTier.MODEL_INFERENCE


# ── Assessment 测试 ──────────────────────────────

class TestAssessment:
    def test_assessment_creation(self):
        """测试评估创建"""
        a = Assessment(
            assessment_id="A001",
            entity_id="北方华创",
            topic="财务表现",
            claims=["claim-001", "claim-002"],
            claim_versions={"claim-001": "v1", "claim-002": "v1"},
            interpretation="营收增长强劲",
            uncertainty="Q2数据待确认",
        )
        assert a.dependency_count == 2

    def test_assessment_stale_on_dependency_change(self):
        """测试依赖变化时标记为 stale"""
        a = Assessment(
            assessment_id="A001",
            entity_id="北方华创",
            topic="财务表现",
            claims=["claim-001"],
            claim_versions={"claim-001": "v1"},
        )

        # 版本未变化 -> 不 stale
        assert a.mark_stale_if_dependency_changed("claim-001", "v1") is False

        # 版本变化 -> stale
        assert a.mark_stale_if_dependency_changed("claim-001", "v2") is True

        # 不存在的 claim -> 不 stale
        assert a.mark_stale_if_dependency_changed("claim-999", "v1") is False


# ── ClaimRouter 测试 ──────────────────────────────

class TestClaimRouter:
    def _make_router(self, tmp_path):
        """创建测试用路由器"""
        graph_file = tmp_path / "graph.yaml"
        graph_file.write_text("companies:\n  北方华创:\n    relations:\n      - type: belongs_to\n        target: 半导体设备\n        score: 0.9\n", encoding="utf-8")
        graph = GraphAdapter(graph_file)
        return ClaimRouter(graph)

    def test_route_primary_entity(self, tmp_path):
        """测试主实体路由"""
        router = self._make_router(tmp_path)

        result = router.route("北方华创", "北方华创发布年报")

        assert len(result.targets) >= 1
        assert result.targets[0].entity_id == "北方华创"
        assert result.targets[0].confidence == RoutingConfidence.HIGH

    def test_route_with_mentioned_entities(self, tmp_path):
        """测试明确提及的实体路由"""
        router = self._make_router(tmp_path)

        result = router.route(
            "北方华创",
            "北方华创与中微公司竞争",
            mentioned_entities=["中微公司"],
        )

        entity_ids = [t.entity_id for t in result.targets]
        assert "北方华创" in entity_ids
        assert "中微公司" in entity_ids

    def test_route_ambiguity_detection(self, tmp_path):
        """测试歧义检测"""
        router = self._make_router(tmp_path)

        result = router.route("中微", "中微公司和中微半导体对比")

        assert result.has_ambiguity is True
        assert result.disambiguation_needed is not None

    def test_route_max_targets(self, tmp_path):
        """测试最大目标数限制"""
        router = self._make_router(tmp_path)

        result = router.route(
            "北方华创",
            "测试内容",
            mentioned_entities=["实体1", "实体2", "实体3", "实体4", "实体5"],
            max_targets=3,
        )

        assert len(result.targets) <= 3


# ── 黄金路由测试 ──────────────────────────────

class TestRoutingGold:
    def test_gold_cases_structure(self):
        """测试黄金用例结构"""
        assert len(ROUTING_GOLD_CASES) == 6

        for case in ROUTING_GOLD_CASES:
            assert "name" in case
            assert "source_entity" in case
            assert "content" in case

    def test_gold_case_automotive(self):
        """测试汽车公司路由"""
        case = ROUTING_GOLD_CASES[0]
        assert case["source_entity"] == "比亚迪"
        assert "比亚迪" in case["expected_targets"]

    def test_gold_case_semiconductor_equipment(self):
        """测试半导体设备路由"""
        case = ROUTING_GOLD_CASES[1]
        assert case["source_entity"] == "北方华创"
        assert "半导体设备" in case["expected_targets"]
        assert "半导体国产替代" in case["expected_targets"]

    def test_gold_case_competitor(self):
        """测试竞争者提及"""
        case = ROUTING_GOLD_CASES[2]
        assert "北方华创" in case["expected_targets"]
        assert "中微公司" in case["expected_targets"]

    def test_gold_case_ambiguity(self):
        """测试同名歧义"""
        case = ROUTING_GOLD_CASES[3]
        assert case["expected_ambiguity"] is True

    def test_gold_case_irrelevant(self):
        """测试无关新闻"""
        case = ROUTING_GOLD_CASES[4]
        assert "贵州茅台" in case["expected_targets"]
        assert "北方华创" in case["not_expected"]

    def test_gold_case_correction(self):
        """测试财报更正"""
        case = ROUTING_GOLD_CASES[5]
        assert case["expected_type"] == "correction"
