"""
图数据模型定义
使用 dataclass 定义清晰的数据结构
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class EntityType(str, Enum):
    """实体类型枚举"""
    COMPANY = "company"
    SECTOR = "sector"
    SUBSECTOR = "subsector"
    THEME = "theme"


class EdgeType(str, Enum):
    """边类型枚举"""
    UPSTREAM_OF = "upstream_of"
    BELONGS_TO = "belongs_to"
    COMPETES_WITH = "competes_with"


@dataclass
class Company:
    """公司数据模型"""
    name: str
    ticker: str
    exchange: str
    sectors: List[str] = field(default_factory=list)
    themes: List[str] = field(default_factory=list)
    position: str = ""
    news_queries: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    competes_with: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "ticker": self.ticker,
            "exchange": self.exchange,
            "sectors": self.sectors,
            "themes": self.themes,
            "position": self.position,
            "news_queries": self.news_queries,
            "aliases": self.aliases,
        }
        if self.competes_with:
            result["competes_with"] = self.competes_with
        return result
    
    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> 'Company':
        """从字典创建"""
        return cls(
            name=name,
            ticker=data.get("ticker", ""),
            exchange=data.get("exchange", ""),
            sectors=data.get("sectors", []),
            themes=data.get("themes", []),
            position=data.get("position", ""),
            news_queries=data.get("news_queries", []),
            aliases=data.get("aliases", []),
            competes_with=data.get("competes_with", []),
        )


@dataclass
class Sector:
    """行业数据模型"""
    name: str
    type: str = "sector"  # sector or subsector
    description: str = ""
    tier: Optional[int] = None
    keywords: List[str] = field(default_factory=list)
    parent_theme: List[str] = field(default_factory=list)
    parent_sector: List[str] = field(default_factory=list)
    questions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "type": self.type,
            "description": self.description,
            "keywords": self.keywords,
        }
        if self.tier is not None:
            result["tier"] = self.tier
        if self.parent_theme:
            result["parent_theme"] = self.parent_theme
        if self.parent_sector:
            result["parent_sector"] = self.parent_sector
        return result
    
    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> 'Sector':
        """从字典创建"""
        return cls(
            name=name,
            type=data.get("type", "sector"),
            description=data.get("description", ""),
            tier=data.get("tier"),
            keywords=data.get("keywords", []),
            parent_theme=data.get("parent_theme", []),
            parent_sector=data.get("parent_sector", []),
        )


@dataclass
class Theme:
    """主题数据模型"""
    name: str
    description: str = ""
    keywords: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "type": "theme",
            "description": self.description,
            "keywords": self.keywords,
        }
    
    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> 'Theme':
        """从字典创建"""
        return cls(
            name=name,
            description=data.get("description", ""),
            keywords=data.get("keywords", []),
        )


@dataclass
class Edge:
    """边数据模型"""
    from_entity: str
    to_entity: str
    edge_type: EdgeType
    label: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "from": self.from_entity,
            "to": self.to_entity,
            "type": self.edge_type.value,
        }
        if self.label:
            result["label"] = self.label
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Edge':
        """从字典创建"""
        return cls(
            from_entity=data["from"],
            to_entity=data["to"],
            edge_type=EdgeType(data["type"]),
            label=data.get("label", ""),
        )


@dataclass
class GraphData:
    """图数据容器"""
    nodes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    companies: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    questions: Dict[str, List[str]] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)
    
    def get_company(self, name: str) -> Optional[Company]:
        """获取公司对象"""
        if name not in self.companies:
            return None
        return Company.from_dict(name, self.companies[name])
    
    def get_sector(self, name: str) -> Optional[Sector]:
        """获取行业对象"""
        if name not in self.nodes:
            return None
        node = self.nodes[name]
        if node.get("type") not in ("sector", "subsector"):
            return None
        return Sector.from_dict(name, node)
    
    def get_theme(self, name: str) -> Optional[Theme]:
        """获取主题对象"""
        if name not in self.nodes:
            return None
        node = self.nodes[name]
        if node.get("type") != "theme":
            return None
        return Theme.from_dict(name, node)
    
    def get_all_companies(self) -> List[Company]:
        """获取所有公司"""
        return [Company.from_dict(name, data) for name, data in self.companies.items()]
    
    def get_all_sectors(self) -> List[Sector]:
        """获取所有行业"""
        sectors = []
        for name, node in self.nodes.items():
            if node.get("type") in ("sector", "subsector"):
                sectors.append(Sector.from_dict(name, node))
        return sectors
    
    def get_all_themes(self) -> List[Theme]:
        """获取所有主题"""
        themes = []
        for name, node in self.nodes.items():
            if node.get("type") == "theme":
                themes.append(Theme.from_dict(name, node))
        return themes
    
    def get_edges(self) -> List[Edge]:
        """获取所有边"""
        return [Edge.from_dict(edge) for edge in self.edges]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "nodes": self.nodes,
            "companies": self.companies,
            "edges": self.edges,
            "questions": self.questions,
            "settings": self.settings,
        }