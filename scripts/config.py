"""
统一配置管理模块
所有配置从这里加载，支持环境变量覆盖和验证

用法：
    from config import Config
    config = Config.load()
    print(config.llm.api_key)
"""

import os
import yaml
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: str = "deepseek"
    api_key: str = ""
    model: str = "deepseek-reasoner"
    base_url: str = "https://api.deepseek.com"
    max_tokens: int = 1024
    temperature: float = 0.3


@dataclass
class SearchConfig:
    """搜索配置"""
    engine: str = "tavily"
    api_key: str = ""
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
class DownloaderConfig:
    """下载器配置"""
    tool_path: str = ""
    save_dir: str = ""
    browser_strategy: str = "playwright"
    pages: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class PathsConfig:
    """路径配置"""
    wiki_root: Path = Path.home() / "company-wiki"
    downloader_dir: Path = Path.home() / "StockInfoDownloader"
    windows_downloads: Path = Path("/mnt/c/Users/郑曾波/Projects/StockInfoDownloader/downloads")


@dataclass
class Config:
    """统一配置类"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    downloader: DownloaderConfig = field(default_factory=DownloaderConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    
    # 原始配置数据
    _raw: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> 'Config':
        """
        加载配置
        
        优先级: 环境变量 > config.yaml > 默认值
        
        Args:
            config_path: 配置文件路径，默认为 ~/company-wiki/config.yaml
            
        Returns:
            Config 对象
            
        Raises:
            FileNotFoundError: 配置文件不存在
            ValueError: 配置验证失败
        """
        # 确定配置文件路径
        if config_path is None:
            config_path = Path.home() / "company-wiki" / "config.yaml"
        
        # 加载 YAML 配置
        raw_config = {}
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                raw_config = yaml.safe_load(f) or {}
        else:
            logger.warning(f"配置文件不存在: {config_path}，使用默认值")
        
        # 应用环境变量覆盖
        raw_config = cls._apply_env_overrides(raw_config)
        
        # 构建配置对象
        config = cls._build_config(raw_config, config_path.parent)
        
        # 验证配置（测试模式下使用宽松验证）
        is_test = os.getenv("PYTEST_CURRENT_TEST") is not None
        config.validate(strict=not is_test)
        
        config._raw = raw_config
        return config
    
    @staticmethod
    def _apply_env_overrides(raw: Dict[str, Any]) -> Dict[str, Any]:
        """应用环境变量覆盖"""
        # LLM API Key
        if os.getenv("DEEPSEEK_API_KEY"):
            raw.setdefault("llm", {})["api_key"] = os.getenv("DEEPSEEK_API_KEY")
        
        # Search API Key
        if os.getenv("TAVILY_API_KEY"):
            raw.setdefault("search", {})["tavily_api_key"] = os.getenv("TAVILY_API_KEY")
        
        # Wiki Root
        if os.getenv("WIKI_ROOT"):
            raw.setdefault("paths", {})["wiki_root"] = os.getenv("WIKI_ROOT")
        
        return raw
    
    @staticmethod
    def _build_config(raw: Dict[str, Any], base_dir: Path) -> 'Config':
        """构建配置对象"""
        # LLM 配置
        llm_raw = raw.get("llm", {})
        llm = LLMConfig(
            provider=llm_raw.get("provider", "deepseek"),
            api_key=llm_raw.get("api_key", ""),
            model=llm_raw.get("model", "deepseek-reasoner"),
            base_url=llm_raw.get("base_url", "https://api.deepseek.com"),
            max_tokens=llm_raw.get("max_tokens", 1024),
            temperature=llm_raw.get("temperature", 0.3),
        )
        
        # 搜索配置
        search_raw = raw.get("search", {})
        search = SearchConfig(
            engine=search_raw.get("engine", "tavily"),
            api_key=search_raw.get("tavily_api_key", search_raw.get("api_key", "")),
            results_per_query=search_raw.get("results_per_query", 8),
            language=search_raw.get("language", "zh"),
            max_age_days=search_raw.get("max_age_days", 7),
        )
        
        # 调度配置
        schedule_raw = raw.get("schedule", {})
        schedule = ScheduleConfig(
            news_collection=schedule_raw.get("news_collection", "daily"),
            report_check=schedule_raw.get("report_check", "weekly"),
            lint=schedule_raw.get("lint", "weekly"),
        )
        
        # 下载器配置
        downloader_raw = raw.get("report_downloader", {})
        downloader = DownloaderConfig(
            tool_path=downloader_raw.get("tool_path", ""),
            save_dir=downloader_raw.get("save_dir", ""),
            browser_strategy=downloader_raw.get("browser_strategy", "playwright"),
            pages=downloader_raw.get("pages", []),
        )
        
        # 路径配置
        paths_raw = raw.get("paths", {})
        wiki_root_str = paths_raw.get("wiki_root", "~/company-wiki")
        wiki_root = Path(os.path.expanduser(wiki_root_str))
        
        paths = PathsConfig(
            wiki_root=wiki_root,
            downloader_dir=Path(os.path.expanduser("~/StockInfoDownloader")),
            windows_downloads=Path("/mnt/c/Users/郑曾波/Projects/StockInfoDownloader/downloads"),
        )
        
        return Config(
            llm=llm,
            search=search,
            schedule=schedule,
            downloader=downloader,
            paths=paths,
        )
    
    def validate(self, strict: bool = True) -> None:
        """
        验证配置
        
        Args:
            strict: 是否严格验证（检查路径是否存在）
            
        Raises:
            ValueError: 配置验证失败
        """
        errors = []
        
        # 验证 LLM 配置
        if strict and not self.llm.api_key:
            errors.append("缺少 LLM API Key (设置 DEEPSEEK_API_KEY 环境变量)")
        
        # 验证搜索配置
        if strict and not self.search.api_key:
            errors.append("缺少搜索 API Key (设置 TAVILY_API_KEY 环境变量)")
        
        # 验证路径（仅在严格模式下检查）
        if strict and not self.paths.wiki_root.exists():
            errors.append(f"Wiki 根目录不存在: {self.paths.wiki_root}")
        
        if errors:
            error_msg = "配置验证失败:\n" + "\n".join(f"  - {e}" for e in errors)
            error_msg += "\n\n请检查 config.yaml 或设置环境变量"
            raise ValueError(error_msg)
    
    def get_llm_api_key(self) -> str:
        """获取 LLM API Key"""
        return self.llm.api_key
    
    def get_search_api_key(self) -> str:
        """获取搜索 API Key"""
        return self.search.api_key
    
    def get_wiki_root(self) -> Path:
        """获取 Wiki 根目录"""
        return self.paths.wiki_root
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self._raw.copy()


# 便捷函数
def load_config(config_path: Optional[Path] = None) -> Config:
    """加载配置的便捷函数"""
    return Config.load(config_path)


# 向后兼容
def get_config() -> Config:
    """获取默认配置"""
    return load_config()


if __name__ == "__main__":
    # 测试配置加载
    import sys
    
    try:
        config = load_config()
        print("✅ 配置加载成功")
        print(f"  Wiki 根目录: {config.paths.wiki_root}")
        print(f"  LLM 提供商: {config.llm.provider}")
        print(f"  LLM 模型: {config.llm.model}")
        print(f"  搜索引擎: {config.search.engine}")
        
        # 验证 API Key
        if config.llm.api_key:
            print(f"  LLM API Key: {config.llm.api_key[:10]}...")
        else:
            print("  ⚠️ LLM API Key 为空")
        
        if config.search.api_key:
            print(f"  搜索 API Key: {config.search.api_key[:10]}...")
        else:
            print("  ⚠️ 搜索 API Key 为空")
        
        sys.exit(0)
    except Exception as e:
        print(f"❌ 配置加载失败: {e}", file=sys.stderr)
        sys.exit(1)