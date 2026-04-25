"""
图数据加载器
负责从 YAML 文件加载和保存图数据
"""
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from .graph_data import GraphData

logger = logging.getLogger(__name__)


class GraphLoader:
    """图数据加载器（支持 graph.yaml + sectors.yaml + companies.yaml 拆分存储）"""

    def __init__(self, graph_path: Optional[Path] = None):
        """
        初始化加载器

        Args:
            graph_path: graph.yaml 文件路径，默认为 ../graph.yaml
        """
        if graph_path is None:
            graph_path = Path(__file__).parent.parent.parent / "graph.yaml"
        self._path = Path(graph_path)
        self._companies_path = self._path.parent / "companies.yaml"
        self._sectors_path = self._path.parent / "sectors.yaml"
        self._data: Optional[GraphData] = None

    def load(self) -> GraphData:
        """
        加载图数据（从 graph.yaml + sectors.yaml + companies.yaml 合并加载）

        Returns:
            GraphData 对象
        """
        dump_kwargs = dict(allow_unicode=True, default_flow_style=False,
                           sort_keys=False, width=120)

        # 主 graph.yaml（edges, questions, settings）
        merged = {}
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    merged = yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                logger.error(f"YAML 解析错误 {self._path}: {e}")
                raise

        # 合并 sectors.yaml（nodes）
        merged.setdefault("nodes", {})
        if self._sectors_path.exists():
            with open(self._sectors_path, "r", encoding="utf-8") as f:
                sectors_data = yaml.safe_load(f) or {}
            merged["nodes"] = sectors_data.get("nodes", {})

        # 合并 companies.yaml（companies）
        merged.setdefault("companies", {})
        if self._companies_path.exists():
            with open(self._companies_path, "r", encoding="utf-8") as f:
                companies_data = yaml.safe_load(f) or {}
            merged["companies"] = companies_data.get("companies", {})

        self._data = GraphData(
            nodes=merged.get("nodes", {}),
            companies=merged.get("companies", {}),
            edges=merged.get("edges", []),
            questions=merged.get("questions", {}),
            settings=merged.get("settings", {}),
        )

        logger.info(f"加载图数据: {len(self._data.nodes)} 节点, {len(self._data.companies)} 公司, {len(self._data.edges)} 边")

        return self._data

    def save(self, data: Optional[GraphData] = None) -> None:
        """
        保存图数据到文件（按类型拆分存储）

        Args:
            data: 要保存的数据，默认为已加载的数据
        """
        if data is None:
            data = self._data

        if data is None:
            raise ValueError("没有数据可保存")

        dump_kwargs = dict(allow_unicode=True, default_flow_style=False,
                           sort_keys=False, width=120)

        # sectors.yaml: nodes
        if data.nodes:
            self._sectors_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._sectors_path, "w", encoding="utf-8") as f:
                yaml.dump({"nodes": data.nodes}, f, **dump_kwargs)

        # companies.yaml: companies
        if data.companies:
            self._companies_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._companies_path, "w", encoding="utf-8") as f:
                yaml.dump({"companies": data.companies}, f, **dump_kwargs)

        # graph.yaml: 完整合并版（兼容旧脚本的直接读取）
        graph_out = {}
        if data.nodes:
            graph_out["nodes"] = data.nodes
        if data.companies:
            graph_out["companies"] = data.companies
        if data.edges:
            graph_out["edges"] = data.edges
        if data.questions:
            graph_out["questions"] = data.questions
        if data.settings:
            graph_out["settings"] = data.settings
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            yaml.dump(graph_out, f, **dump_kwargs)

        logger.info(f"保存图数据到: {self._path} + sectors.yaml + companies.yaml")
    
    def get_path(self) -> Path:
        """获取文件路径"""
        return self._path
    
    def exists(self) -> bool:
        """检查文件是否存在"""
        return self._path.exists()
    
    def backup(self, backup_path: Optional[Path] = None) -> Path:
        """
        创建备份
        
        Args:
            backup_path: 备份文件路径，默认为原文件加上 .bak 后缀
            
        Returns:
            备份文件路径
        """
        if backup_path is None:
            backup_path = self._path.with_suffix(".yaml.bak")
        
        if self._data is None:
            self.load()
        
        # 保存备份
        with open(backup_path, "w", encoding="utf-8") as f:
            yaml.dump(
                self._data.to_dict(),
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
                width=120
            )
        
        logger.info(f"创建备份: {backup_path}")
        return backup_path
    
    def restore(self, backup_path: Optional[Path] = None) -> GraphData:
        """
        从备份恢复
        
        Args:
            backup_path: 备份文件路径，默认为原文件加上 .bak 后缀
            
        Returns:
            恢复的 GraphData 对象
        """
        if backup_path is None:
            backup_path = self._path.with_suffix(".yaml.bak")
        
        if not backup_path.exists():
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")
        
        # 从备份加载
        with open(backup_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        
        self._data = GraphData(
            nodes=raw.get("nodes", {}),
            companies=raw.get("companies", {}),
            edges=raw.get("edges", []),
            questions=raw.get("questions", {}),
            settings=raw.get("settings", {}),
        )
        
        # 保存到原文件
        self.save()
        
        logger.info(f"从备份恢复: {backup_path}")
        return self._data