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
    """图数据加载器"""
    
    def __init__(self, graph_path: Optional[Path] = None):
        """
        初始化加载器
        
        Args:
            graph_path: graph.yaml 文件路径，默认为 ../graph.yaml
        """
        if graph_path is None:
            graph_path = Path(__file__).parent.parent.parent / "graph.yaml"
        self._path = Path(graph_path)
        self._data: Optional[GraphData] = None
    
    def load(self) -> GraphData:
        """
        加载图数据
        
        Returns:
            GraphData 对象
            
        Raises:
            FileNotFoundError: 文件不存在
            yaml.YAMLError: YAML 格式错误
        """
        if not self._path.exists():
            raise FileNotFoundError(f"图数据文件不存在: {self._path}")
        
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)
        except yaml.YAMLError as e:
            logger.error(f"YAML 解析错误: {e}")
            raise
        
        if not raw:
            logger.warning(f"图数据文件为空: {self._path}")
            raw = {}
        
        self._data = GraphData(
            nodes=raw.get("nodes", {}),
            companies=raw.get("companies", {}),
            edges=raw.get("edges", []),
            questions=raw.get("questions", {}),
            settings=raw.get("settings", {}),
        )
        
        logger.info(f"加载图数据: {len(self._data.nodes)} 节点, {len(self._data.companies)} 公司, {len(self._data.edges)} 边")
        
        return self._data
    
    def save(self, data: Optional[GraphData] = None) -> None:
        """
        保存图数据到文件
        
        Args:
            data: 要保存的数据，默认为已加载的数据
        """
        if data is None:
            data = self._data
        
        if data is None:
            raise ValueError("没有数据可保存")
        
        # 确保目录存在
        self._path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存到文件
        with open(self._path, "w", encoding="utf-8") as f:
            yaml.dump(
                data.to_dict(),
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
                width=120
            )
        
        logger.info(f"保存图数据到: {self._path}")
    
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