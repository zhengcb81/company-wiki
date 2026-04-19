"""
配置加载兼容层 — 所有功能已合并到 config.py

此文件保持向后兼容，将 config_loader 的 API 映射到 config.py。
使用方应迁移到: from config import Config, load_config, get_config
"""

import sys
from pathlib import Path
from dataclasses import dataclass, field

# 确保 scripts/ 在 sys.path 中
_scripts_dir = str(Path(__file__).resolve().parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from config import (
    Config as _Config,
    LLMConfig,
    SearchConfig,
    ScheduleConfig,
    DownloaderConfig,
    PathsConfig,
    load_config,
    get_config,
)

# 兼容别名
ReportDownloaderConfig = DownloaderConfig


@dataclass
class EvolutionConfig:
    """进化机制配置"""
    auto_discover_topics: bool = True
    suggest_companies: bool = True
    evolve_questions: bool = True


def Config(*args, **kwargs):
    """
    兼容工厂函数 — 支持 config_loader 的旧字段名:
    - report_downloader -> downloader
    - evolution -> 忽略 (config.py 没有)
    - wiki_root -> paths.wiki_root + config.wiki_root 属性
    """
    if args:
        # 如果以位置参数方式调用，直接转发
        return _Config(*args, **kwargs)

    # 字段名映射
    mapped = {}
    if "report_downloader" in kwargs:
        mapped["downloader"] = kwargs.pop("report_downloader")
    if "evolution" in kwargs:
        kwargs.pop("evolution")  # config.py 没有 evolution 字段
    if "wiki_root" in kwargs:
        wiki_root = kwargs.pop("wiki_root")
        mapped["paths"] = PathsConfig(wiki_root=Path(wiki_root))

    mapped.update(kwargs)
    obj = _Config(**mapped)

    # 注入 wiki_root 便捷属性（旧代码用 config.wiki_root 访问）
    if not hasattr(obj, "wiki_root") or obj.wiki_root != obj.paths.wiki_root:
        try:
            object.__setattr__(obj, "wiki_root", obj.paths.wiki_root)
        except (AttributeError, TypeError):
            pass  # frozen dataclass 等

    return obj


# 导出
__all__ = [
    "Config", "LLMConfig", "SearchConfig", "ScheduleConfig",
    "ReportDownloaderConfig", "DownloaderConfig", "EvolutionConfig",
    "PathsConfig", "load_config", "get_config",
]


# 兼容: load_yaml_simple
def load_yaml_simple(path=None):
    """向后兼容，建议使用 Config.load()"""
    return load_config(path).to_dict()
