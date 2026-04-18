"""
图数据查询接口
提供各种查询方法
"""
from collections import defaultdict
from typing import List, Tuple, Dict, Any, Optional, Set
import logging

from .graph_data import GraphData, Company, Sector, Theme, Edge, EntityType

logger = logging.getLogger(__name__)


class GraphQueries:
    """图数据查询接口"""
    
    def __init__(self, data: GraphData):
        """
        初始化查询接口
        
        Args:
            data: 图数据
        """
        self._data = data
        self._build_indices()
    
    def _build_indices(self) -> None:
        """构建索引以加速查询"""
        # 邻接表
        self._upstream: Dict[str, List[str]] = defaultdict(list)
        self._downstream: Dict[str, List[str]] = defaultdict(list)
        self._belongs_to: Dict[str, List[str]] = defaultdict(list)
        
        for edge in self._data.edges:
            f, t, etype = edge["from"], edge["to"], edge["type"]
            if etype == "upstream_of":
                self._downstream[f].append(t)
                self._upstream[t].append(f)
            elif etype == "belongs_to":
                self._belongs_to[t].append(f)
        
        # 关键词 → 实体 映射
        self._keyword_index: Dict[str, Tuple[str, str]] = {}
        for name, node in self._data.nodes.items():
            keywords = node.get("keywords", [name])
            for kw in keywords:
                self._keyword_index[kw.lower()] = (name, node.get("type", "sector"))
        
        # 公司名 → 公司 映射
        self._company_index: Dict[str, Dict[str, Any]] = {}
        for name, comp in self._data.companies.items():
            self._company_index[name] = comp
            # 也按 ticker 索引
            ticker = comp.get("ticker", "")
            if ticker:
                self._company_index[ticker] = comp
            # 按别名索引
            for alias in comp.get("aliases", []):
                self._company_index[alias] = comp
    
    # ── 公司查询 ──────────────────────────────
    
    def get_all_companies(self) -> List[Company]:
        """返回所有公司列表"""
        return self._data.get_all_companies()
    
    def get_company(self, name: str) -> Optional[Company]:
        """获取单个公司详情"""
        # 尝试直接查找
        comp = self._data.companies.get(name)
        if comp:
            return Company.from_dict(name, comp)
        
        # 尝试按 ticker 或别名查找
        comp_data = self._company_index.get(name)
        if comp_data:
            # 找到公司名
            for cname, cdata in self._data.companies.items():
                if cdata == comp_data:
                    return Company.from_dict(cname, cdata)
        
        return None
    
    def get_companies_by_sector(self, sector_name: str) -> List[Company]:
        """获取属于某个行业的所有公司"""
        companies = []
        for name, comp in self._data.companies.items():
            if sector_name in comp.get("sectors", []):
                companies.append(Company.from_dict(name, comp))
        return companies
    
    def get_companies_by_theme(self, theme_name: str) -> List[Company]:
        """获取属于某个主题的所有公司"""
        companies = []
        for name, comp in self._data.companies.items():
            if theme_name in comp.get("themes", []):
                companies.append(Company.from_dict(name, comp))
        return companies
    
    # ── 行业查询 ──────────────────────────────
    
    def get_all_sectors(self) -> List[Sector]:
        """返回所有行业列表"""
        return self._data.get_all_sectors()
    
    def get_sector(self, name: str) -> Optional[Sector]:
        """获取行业详情"""
        node = self._data.nodes.get(name)
        if not node:
            return None
        
        if node.get("type") not in ("sector", "subsector"):
            return None
        
        sector = Sector.from_dict(name, node)
        
        # 补充问题列表
        sector.questions = self._data.questions.get(name, [])
        
        return sector
    
    def get_sectors_by_theme(self, theme_name: str) -> List[Sector]:
        """获取属于某个主题的所有行业"""
        sectors = []
        for name, node in self._data.nodes.items():
            if node.get("type") in ("sector", "subsector"):
                if theme_name in node.get("parent_theme", []):
                    sectors.append(Sector.from_dict(name, node))
        return sectors
    
    def get_subsectors(self, sector_name: str) -> List[Sector]:
        """获取某个行业的所有子行业"""
        return [self.get_sector(sub) for sub in self._belongs_to.get(sector_name, [])]
    
    # ── 主题查询 ──────────────────────────────
    
    def get_all_themes(self) -> List[Theme]:
        """返回所有主题列表"""
        return self._data.get_all_themes()
    
    def get_theme(self, name: str) -> Optional[Theme]:
        """获取主题详情"""
        node = self._data.nodes.get(name)
        if not node:
            return None
        
        if node.get("type") != "theme":
            return None
        
        return Theme.from_dict(name, node)
    
    # ── 图遍历 ──────────────────────────────
    
    def upstream_of(self, entity: str) -> List[str]:
        """获取 entity 的所有上游"""
        return self._upstream.get(entity, [])
    
    def downstream_of(self, entity: str) -> List[str]:
        """获取 entity 的所有下游"""
        return self._downstream.get(entity, [])
    
    def supply_chain_path(self, entity: str, visited: Optional[Set[str]] = None) -> List[List[str]]:
        """
        获取从 entity 到终端应用的所有路径
        
        Args:
            entity: 起始实体
            visited: 已访问的实体集合（用于避免循环）
            
        Returns:
            路径列表，每个路径是实体名称列表
        """
        if visited is None:
            visited = set()
        if entity in visited:
            return []
        visited.add(entity)
        
        paths = []
        targets = self._downstream.get(entity, [])
        if not targets:
            paths.append([entity])
        else:
            for t in targets:
                for sp in self.supply_chain_path(t, visited.copy()):
                    paths.append([entity] + sp)
        return paths
    
    def find_path(self, from_entity: str, to_entity: str, max_depth: int = 10) -> Optional[List[str]]:
        """
        查找两个实体之间的路径
        
        Args:
            from_entity: 起始实体
            to_entity: 目标实体
            max_depth: 最大搜索深度
            
        Returns:
            路径列表，如果不存在返回 None
        """
        if from_entity == to_entity:
            return [from_entity]
        
        visited = set()
        queue = [(from_entity, [from_entity])]
        
        while queue and max_depth > 0:
            current, path = queue.pop(0)
            
            if current in visited:
                continue
            visited.add(current)
            
            # 检查下游
            for downstream in self._downstream.get(current, []):
                if downstream == to_entity:
                    return path + [downstream]
                if downstream not in visited:
                    queue.append((downstream, path + [downstream]))
            
            max_depth -= 1
        
        return None
    
    # ── 相关性匹配（核心 API）──────────────────
    
    def find_related_entities(self, text: str, company_hint: Optional[str] = None) -> List[Tuple[str, str, str]]:
        """
        给定一段文本，判断它与哪些实体（公司/行业/主题）相关。
        
        Args:
            text: 待分析文本
            company_hint: 公司线索（可选）
            
        Returns:
            [(entity_name, entity_type, topic_name), ...]
        """
        text_lower = text.lower()
        related: Set[Tuple[str, str, str]] = set()
        
        # 1. 如果有公司线索，直接关联该公司及其行业
        if company_hint:
            comp = self.get_company(company_hint)
            if comp:
                related.add((company_hint, "company", "公司动态"))
                for s in comp.sectors:
                    related.update(self._expand_sector_topics(s))
                for t in comp.themes:
                    related.update(self._expand_theme_topics(t))
        
        # 2. 关键词匹配行业/主题
        for keyword, (entity_name, entity_type) in self._keyword_index.items():
            if keyword in text_lower:
                if entity_type in ("sector", "subsector"):
                    related.update(self._expand_sector_topics(entity_name))
                elif entity_type == "theme":
                    related.update(self._expand_theme_topics(entity_name))
        
        # 3. 公司名匹配
        for comp_name in self._data.companies:
            if comp_name in text and comp_name != company_hint:
                related.add((comp_name, "company", "相关动态"))
                # 也关联到该公司的行业
                comp = self.get_company(comp_name)
                if comp:
                    for s in comp.sectors:
                        related.update(self._expand_sector_topics(s))
        
        return list(related)
    
    def _expand_sector_topics(self, sector_name: str) -> Set[Tuple[str, str, str]]:
        """展开行业下的所有 topic"""
        result: Set[Tuple[str, str, str]] = set()
        
        # 每个行业就是一个 topic
        result.add((sector_name, "sector", sector_name))
        
        # 也检查子领域
        for sub in self._belongs_to.get(sector_name, []):
            result.add((sub, "sector", sub))
        
        return result
    
    def _expand_theme_topics(self, theme_name: str) -> Set[Tuple[str, str, str]]:
        """展开主题下的所有 topic"""
        result: Set[Tuple[str, str, str]] = set()
        result.add((theme_name, "theme", theme_name))
        return result
    
    # ── 问题查询 ──────────────────────────────
    
    def get_all_questions(self) -> Dict[str, List[str]]:
        """获取所有行业/主题的问题列表"""
        return dict(self._data.questions)
    
    def get_questions(self, entity_name: str) -> List[str]:
        """获取某个实体的问题列表"""
        return self._data.questions.get(entity_name, [])