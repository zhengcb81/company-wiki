"""
graph_adapter.py — Graph 适配器

保留现有 graph.py 的关系匹配能力，新增统一接口。
旧 scripts/graph.py 的薄包装，签名固定，返回值类型化。
"""

from dataclasses import dataclass
from pathlib import Path

from .domain import EntityType


@dataclass
class RelatedTarget:
    """关系匹配结果"""
    entity_name: str
    entity_type: EntityType
    relation_type: str   # belongs_to, upstream_of, competes_with, etc.
    relevance_score: float
    label: str = ""


class GraphAdapter:
    """
    Graph 关系适配器。

    封装 scripts/graph.py，提供类型化接口。
    旧代码通过此适配器访问关系匹配，不再直接操作 graph.yaml。
    """

    def __init__(self, graph_path: Path, companies: dict = None):
        """
        Args:
            graph_path: graph.yaml 路径
            companies: 公司配置字典（从 companies.yaml 加载）
        """
        self._graph_path = graph_path
        self._companies = companies or {}
        self._edges = []
        self._questions = {}
        self._load()

    def _load(self):
        """加载 graph.yaml"""
        import yaml
        if not self._graph_path.exists():
            return
        with open(self._graph_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        self._edges = data.get("edges", [])
        self._questions = data.get("questions", {})

    def resolve_targets(
        self,
        source_entity: str,
        content: str = "",
        max_targets: int = 10,
    ) -> list[RelatedTarget]:
        """
        根据来源实体和内容，解析相关目标实体。

        Args:
            source_entity: 来源实体名称（公司名/行业名/主题名）
            content: 内容文本（用于相关性评分）
            max_targets: 最大返回数

        Returns:
            相关目标列表，按相关性降序
        """
        targets = []

        # 1. 从 edges 找直接关系
        for edge in self._edges:
            from_name = edge.get("from", "")
            to_name = edge.get("to", "")
            rel_type = edge.get("type", "related")
            label = edge.get("label", "")

            if from_name == source_entity:
                entity_type = self._infer_entity_type(to_name)
                score = self._score_relation(rel_type, content, to_name)
                targets.append(RelatedTarget(
                    entity_name=to_name,
                    entity_type=entity_type,
                    relation_type=rel_type,
                    relevance_score=score,
                    label=label,
                ))
            elif to_name == source_entity:
                entity_type = self._infer_entity_type(from_name)
                score = self._score_relation(rel_type, content, from_name)
                targets.append(RelatedTarget(
                    entity_name=from_name,
                    entity_type=entity_type,
                    relation_type=rel_type,
                    relevance_score=score,
                    label=label,
                ))

        # 2. 从公司配置找竞争关系
        company = self._companies.get(source_entity)
        if company:
            for competitor in company.competes_with:
                targets.append(RelatedTarget(
                    entity_name=competitor,
                    entity_type=EntityType.COMPANY,
                    relation_type="competes_with",
                    relevance_score=0.7,
                    label=f"{source_entity} 的竞争对手",
                ))
            # 所属行业
            for sector in company.sectors:
                targets.append(RelatedTarget(
                    entity_name=sector,
                    entity_type=EntityType.SECTOR,
                    relation_type="belongs_to",
                    relevance_score=0.9,
                    label=f"{source_entity} 所属行业",
                ))
            # 关联主题
            for theme in company.themes:
                targets.append(RelatedTarget(
                    entity_name=theme,
                    entity_type=EntityType.THEME,
                    relation_type="related_to",
                    relevance_score=0.8,
                    label=f"{source_entity} 关联主题",
                ))

        # 3. 去重并排序
        seen = set()
        unique = []
        for t in targets:
            key = (t.entity_name, t.relation_type)
            if key not in seen:
                seen.add(key)
                unique.append(t)

        unique.sort(key=lambda t: t.relevance_score, reverse=True)
        return unique[:max_targets]

    def get_questions(self, entity_name: str) -> list[str]:
        """获取实体关联的问题列表"""
        return self._questions.get(entity_name, [])

    def _infer_entity_type(self, name: str) -> EntityType:
        """从名称推断实体类型"""
        if name in self._companies:
            return EntityType.COMPANY
        # 简单启发：如果在 questions 中有同名 key，认为是行业
        if name in self._questions:
            return EntityType.SECTOR
        return EntityType.THEME

    def _score_relation(self, rel_type: str, content: str, target_name: str) -> float:
        """评分关系相关性"""
        base_scores = {
            "belongs_to": 0.9,
            "upstream_of": 0.7,
            "competes_with": 0.6,
            "related_to": 0.5,
        }
        score = base_scores.get(rel_type, 0.5)

        # 如果内容中提及目标，加分
        if content and target_name in content:
            score = min(1.0, score + 0.2)

        return score
