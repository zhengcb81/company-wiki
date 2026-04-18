"""
配置管理模块
统一加载配置，支持环境变量覆盖
"""
import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: str
    api_key: str
    model: str
    base_url: str
    max_tokens: int = 1024
    temperature: float = 0.3


@dataclass
class SearchConfig:
    """搜索配置"""
    engine: str
    api_key: str
    results_per_query: int = 8
    language: str = "zh"
    max_age_days: int = 7


@dataclass
class ScheduleConfig:
    """调度配置"""
    news_collection: str = "daily"
    report_check: str = "weekly"
    lint: str = "weekly"


@dataclass
class ReportDownloaderConfig:
    """报告下载配置"""
    tool_path: str
    save_dir: str
    browser_strategy: str = "playwright"
    pages: list = field(default_factory=list)


@dataclass
class EvolutionConfig:
    """进化机制配置"""
    auto_discover_topics: bool = True
    suggest_companies: bool = True
    evolve_questions: bool = True


@dataclass
class Config:
    """主配置类"""
    llm: LLMConfig
    search: SearchConfig
    schedule: ScheduleConfig
    report_downloader: ReportDownloaderConfig
    evolution: EvolutionConfig
    wiki_root: Path
    raw_config: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> 'Config':
        """
        加载配置，支持环境变量覆盖
        
        Args:
            config_path: 配置文件路径，默认为 scripts/../config.yaml
            
        Returns:
            Config 对象
            
        Raises:
            FileNotFoundError: 配置文件不存在
            ValueError: 配置格式错误
        """
        # 确定配置文件路径
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        # 加载 YAML
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"配置文件格式错误: {e}")
        
        if not raw:
            raise ValueError("配置文件为空")
        
        # 环境变量覆盖
        raw = cls._apply_env_overrides(raw)
        
        # 验证必需字段
        cls._validate_config(raw)
        
        # 构建配置对象
        try:
            llm = LLMConfig(**raw.get("llm", {}))
            
            # 处理搜索配置：tavily_api_key -> api_key
            search_raw = raw.get("search", {})
            search_data = {
                "engine": search_raw.get("engine", "tavily"),
                "api_key": search_raw.get("tavily_api_key", search_raw.get("api_key", "")),
                "results_per_query": search_raw.get("results_per_query", 8),
                "language": search_raw.get("language", "zh"),
                "max_age_days": search_raw.get("max_age_days", 7)
            }
            search = SearchConfig(**search_data)
            
            schedule = ScheduleConfig(**raw.get("schedule", {}))
            
            report_downloader_raw = raw.get("report_downloader", {})
            report_downloader = ReportDownloaderConfig(
                tool_path=report_downloader_raw.get("tool_path", ""),
                save_dir=report_downloader_raw.get("save_dir", ""),
                browser_strategy=report_downloader_raw.get("browser_strategy", "playwright"),
                pages=report_downloader_raw.get("pages", [])
            )
            
            evolution = EvolutionConfig(**raw.get("evolution", {}))
            
            wiki_root = Path(
                raw.get("paths", {}).get("wiki_root", "~/company-wiki")
            ).expanduser()
            
            return cls(
                llm=llm,
                search=search,
                schedule=schedule,
                report_downloader=report_downloader,
                evolution=evolution,
                wiki_root=wiki_root,
                raw_config=raw
            )
        except (TypeError, KeyError) as e:
            raise ValueError(f"配置数据结构错误: {e}")
    
    @staticmethod
    def _apply_env_overrides(raw: Dict[str, Any]) -> Dict[str, Any]:
        """应用环境变量覆盖"""
        # Tavily API Key
        if os.getenv("TAVILY_API_KEY"):
            if "search" not in raw:
                raw["search"] = {}
            raw["search"]["tavily_api_key"] = os.getenv("TAVILY_API_KEY")
            logger.debug("使用环境变量 TAVILY_API_KEY")
        
        # DeepSeek API Key
        if os.getenv("DEEPSEEK_API_KEY"):
            if "llm" not in raw:
                raw["llm"] = {}
            raw["llm"]["api_key"] = os.getenv("DEEPSEEK_API_KEY")
            logger.debug("使用环境变量 DEEPSEEK_API_KEY")
        
        # Wiki Root
        if os.getenv("WIKI_ROOT"):
            if "paths" not in raw:
                raw["paths"] = {}
            raw["paths"]["wiki_root"] = os.getenv("WIKI_ROOT")
            logger.debug("使用环境变量 WIKI_ROOT")
        
        return raw
    
    @staticmethod
    def _validate_config(raw: Dict[str, Any]) -> None:
        """验证配置必需字段"""
        errors = []
        
        # 检查 LLM 配置
        llm = raw.get("llm", {})
        if not llm.get("api_key"):
            errors.append("缺少 LLM API Key (llm.api_key)")
        if not llm.get("model"):
            errors.append("缺少 LLM 模型 (llm.model)")
        
        # 检查搜索配置
        search = raw.get("search", {})
        if not search.get("tavily_api_key"):
            errors.append("缺少 Tavily API Key (search.tavily_api_key)")
        
        if errors:
            error_msg = "配置验证失败:\n" + "\n".join(f"  - {e}" for e in errors)
            error_msg += "\n\n请检查 config.yaml 或设置环境变量:"
            error_msg += "\n  - TAVILY_API_KEY"
            error_msg += "\n  - DEEPSEEK_API_KEY"
            raise ValueError(error_msg)
    
    def get_llm_api_key(self) -> str:
        """获取 LLM API Key"""
        return self.llm.api_key
    
    def get_search_api_key(self) -> str:
        """获取搜索 API Key"""
        return self.search.api_key
    
    def get_wiki_root(self) -> Path:
        """获取 wiki 根目录"""
        return self.wiki_root
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        return self.raw_config


# 便捷函数
def load_config(config_path: Optional[Path] = None) -> Config:
    """加载配置的便捷函数"""
    return Config.load(config_path)


def get_config() -> Config:
    """获取默认配置"""
    return load_config()


# 向后兼容：保持原有接口
def load_yaml_simple(path: Path) -> Dict[str, Any]:
    """
    向后兼容的 YAML 加载函数
    建议使用 Config.load() 替代
    """
    import warnings
    warnings.warn(
        "load_yaml_simple 已弃用，请使用 Config.load()",
        DeprecationWarning,
        stacklevel=2
    )
    
    config = load_config(path)
    return config.to_dict()


if __name__ == "__main__":
    # 测试配置加载
    import sys
    
    try:
        config = load_config()
        print("✓ 配置加载成功")
        print(f"  Wiki 根目录: {config.wiki_root}")
        print(f"  LLM 提供商: {config.llm.provider}")
        print(f"  LLM 模型: {config.llm.model}")
        print(f"  搜索引擎: {config.search.engine}")
        print(f"  搜索结果数: {config.search.results_per_query}")
        
        # 验证 API Key 不为空
        if config.llm.api_key:
            print(f"  LLM API Key: {config.llm.api_key[:10]}...")
        else:
            print("  ⚠ LLM API Key 为空")
        
        if config.search.api_key:
            print(f"  搜索 API Key: {config.search.api_key[:10]}...")
        else:
            print("  ⚠ 搜索 API Key 为空")
        
        sys.exit(0)
    except Exception as e:
        print(f"✗ 配置加载失败: {e}", file=sys.stderr)
        sys.exit(1)