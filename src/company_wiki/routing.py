"""
routing.py — 消息路由与 fan-out 逻辑

确定新闻/公告应路由到哪些实体（公司、行业、主题）。
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .domain import EntityType
from .graph_adapter import GraphAdapter


class RoutingConfidence(str, Enum):
    """路由置信度"""
    HIGH = "high"          # 强关系，直接路由
    MEDIUM = "medium"      # 中等关系，可能需要审核
    LOW = "low"            # 弱关系，建议人工审核
    AMBIGUOUS = "ambiguous"  # 歧义（如中微公司 vs 中微半导体）


@dataclass
class RoutingTarget:
    """路由目标"""
    entity_id: str
    entity_type: EntityType
    confidence: RoutingConfidence
    reason: str
    requires_review: bool = False


@dataclass
class RoutingResult:
    """路由结果"""
    targets: list[RoutingTarget]
    has_ambiguity: bool = False
    is_irrelevant: bool = False
    disambiguation_needed: Optional[str] = None


class ClaimRouter:
    """
    声明路由器。

    基于内容分析和图关系确定声明应路由到哪些实体。
    """

    def __init__(self, graph: GraphAdapter):
        self._graph = graph

    def route(
        self,
        source_entity: str,
        content: str,
        mentioned_entities: Optional[list[str]] = None,
        max_targets: int = 5,
    ) -> RoutingResult:
        """
        路由声明到目标实体。

        Args:
            source_entity: 来源实体（如新闻提到的公司）
            content: 内容文本
            mentioned_entities: 内容中明确提到的实体列表
            max_targets: 最大目标数

        Returns:
            RoutingResult
        """
        targets = []
        seen = set()

        # 1. 主实体（来源公司）总是 HIGH
        if source_entity not in seen:
            targets.append(RoutingTarget(
                entity_id=source_entity,
                entity_type=EntityType.COMPANY,
                confidence=RoutingConfidence.HIGH,
                reason="主实体",
            ))
            seen.add(source_entity)

        # 2. 从图中获取相关实体
        related = self._graph.resolve_targets(source_entity, content, max_targets=max_targets)
        for rel in related:
            if rel.name not in seen:
                confidence = self._score_to_confidence(rel.score)
                targets.append(RoutingTarget(
                    entity_id=rel.name,
                    entity_type=EntityType.SECTOR,  # 默认，实际应从图中获取
                    confidence=confidence,
                    reason=f"图关系: {rel.relation_type}",
                    requires_review=confidence in (RoutingConfidence.LOW, RoutingConfidence.AMBIGUOUS),
                ))
                seen.add(rel.name)

        # 3. 明确提到的实体
        if mentioned_entities:
            for entity in mentioned_entities:
                if entity not in seen:
                    targets.append(RoutingTarget(
                        entity_id=entity,
                        entity_type=EntityType.COMPANY,  # 默认
                        confidence=RoutingConfidence.MEDIUM,
                        reason="内容明确提及",
                    ))
                    seen.add(entity)

        # 4. 检查歧义
        has_ambiguity = self._check_ambiguity(source_entity, content)
        disambiguation = None
        if has_ambiguity:
            disambiguation = f"检测到歧义: {source_entity} 可能指多个实体"
            # 降低主实体置信度
            if targets:
                targets[0].confidence = RoutingConfidence.AMBIGUOUS
                targets[0].requires_review = True

        return RoutingResult(
            targets=targets[:max_targets],
            has_ambiguity=has_ambiguity,
            disambiguation_needed=disambiguation,
        )

    def _score_to_confidence(self, score: float) -> RoutingConfidence:
        """将图关系评分转换为路由置信度"""
        if score >= 0.8:
            return RoutingConfidence.HIGH
        elif score >= 0.5:
            return RoutingConfidence.MEDIUM
        else:
            return RoutingConfidence.LOW

    def _check_ambiguity(self, entity_name: str, content: str) -> bool:
        """
        检查内容中是否存在歧义。

        简单实现：检查内容中是否有"中微"等可能指代多个实体的关键词。
        """
        # 常见歧义关键词
        ambiguity_patterns = {
            "中微": ["中微公司", "中微半导体"],
            "华创": ["北方华创", "华创证券"],
        }

        for pattern, candidates in ambiguity_patterns.items():
            if pattern in entity_name or pattern in content:
                # 检查内容中是否同时提到了多个候选
                mentioned = [c for c in candidates if c in content]
                if len(mentioned) > 1:
                    return True

        return False


# ── 黄金路由测试用例 ──────────────────────────────

ROUTING_GOLD_CASES = [
    {
        "name": "汽车公司新闻",
        "source_entity": "比亚迪",
        "content": "比亚迪发布2025年年报，营收增长30%",
        "expected_targets": ["比亚迪"],
        "expected_sector": "汽车",
    },
    {
        "name": "半导体设备新闻",
        "source_entity": "北方华创",
        "content": "北方华创获得大基金投资，国产替代加速",
        "expected_targets": ["北方华创", "半导体设备", "半导体国产替代"],
    },
    {
        "name": "竞争者提及",
        "source_entity": "中微公司",
        "content": "中微公司与北方华创竞争刻蚀设备市场",
        "expected_targets": ["中微公司", "北方华创"],
    },
    {
        "name": "同名歧义",
        "source_entity": "中微",
        "content": "中微公司和中微半导体的业务对比",
        "expected_ambiguity": True,
    },
    {
        "name": "无关新闻",
        "source_entity": "贵州茅台",
        "content": "贵州茅台发布年报",
        "expected_targets": ["贵州茅台"],
        "not_expected": ["北方华创"],
    },
    {
        "name": "财报更正",
        "source_entity": "北方华创",
        "content": "北方华创发布年报更正公告，修正营收数据",
        "expected_targets": ["北方华创"],
        "expected_type": "correction",
    },
]
