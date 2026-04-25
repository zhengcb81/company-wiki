"""
数据模型模块（已弃用 — 仅供测试和归档脚本使用）

⚠️ 新代码请使用 scripts/graph.py（Graph 类），它提供了相同的功能并返回字典。
    本模块使用 dataclass 类型化对象，但未被任何活动脚本引用。

保留原因：test_graph_models.py 中的 12 个测试仍然通过，且归档脚本依赖此模块。
"""

from .graph_data import GraphData, Company, Sector, Theme, Edge
from .graph_loader import GraphLoader
from .graph_queries import GraphQueries

__all__ = [
    "GraphData",
    "Company",
    "Sector",
    "Theme",
    "Edge",
    "GraphLoader",
    "GraphQueries",
]