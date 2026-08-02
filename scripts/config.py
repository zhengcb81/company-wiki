"""
统一配置管理模块
所有配置从这里加载，支持环境变量覆盖和验证

用法：
    from config import Config
    config = Config.load()
    print(config.llm.api_key)
"""

import os
import copy
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

from common import WIKI_ROOT

logger = logging.getLogger(__name__)

_PROJECT_DOTENV_AUTHORITATIVE_KEYS = frozenset(
    {"MINIMAX_API_KEY", "MIMO_API_KEY", "DEEPSEEK_API_KEY"}
)


def _load_dotenv():
    """Load project .env; its managed LLM keys override stale inherited values."""
    if os.environ.get("PYTHON_DOTENV_DISABLED", "").casefold() in {"1", "true", "yes"}:
        return
    # 查找 .env: 先看项目根目录，再看当前工作目录
    candidates = [
        WIKI_ROOT / ".env",
        Path.cwd() / ".env",
    ]
    for env_path in candidates:
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    if key and (
                        key in _PROJECT_DOTENV_AUTHORITATIVE_KEYS
                        or key not in os.environ
                    ):
                        os.environ[key] = value
            logger.debug(f"已加载 .env: {env_path}")
            return


# 延迟加载标记
_dotenv_loaded = False


def _ensure_dotenv():
    """确保 .env 已加载（首次调用 Config.load 时执行）"""
    global _dotenv_loaded
    if not _dotenv_loaded and not os.getenv("PYTEST_CURRENT_TEST"):
        _load_dotenv()
        _dotenv_loaded = True


@dataclass
class LLMFallbackConfig:
    """Secondary provider profile with an explicit workload policy."""

    provider: str = "mimo"
    api_key: str = ""
    api_key_env: str = "MIMO_API_KEY"
    model: str = "mimo-v2.5-pro"
    base_url: str = "https://token-plan-cn.xiaomimimo.com/v1"
    enabled: bool = True
    usage_scope: str = "general"


@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: str = "minimax"
    api_key: str = ""
    api_key_env: str = "MINIMAX_API_KEY"
    model: str = "MiniMax-M3"
    base_url: str = "https://api.minimaxi.com/v1"
    max_tokens: int = 8192
    max_document_chars: int = 800000  # ~1M tokens 的 80%，用于整篇文档分析
    temperature: float = 1.0
    reasoning_split: bool = True
    fallback: LLMFallbackConfig = field(default_factory=LLMFallbackConfig)


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
    windows_downloads: Path = Path.home() / "StockInfoDownloader" / "downloads"


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
        
        优先级: 项目 .env 中受管 LLM Key > 环境变量 > config.yaml > 默认值
        
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
            config_path = WIKI_ROOT / "config.yaml"
            # 仅在使用默认路径时自动加载 .env（测试传入自定义路径时跳过）
            _ensure_dotenv()
        
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
        """Apply non-secret overrides and remove repository-stored LLM keys."""
        raw = copy.deepcopy(raw)
        llm_raw = raw.get("llm")
        if isinstance(llm_raw, dict):
            # LLM secrets are runtime-only. Do not retain YAML values in _raw,
            # and never copy environment secrets into the serializable mapping.
            llm_raw.pop("api_key", None)
            fallback_raw = llm_raw.get("fallback")
            if isinstance(fallback_raw, dict):
                fallback_raw.pop("api_key", None)
        
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
        provider_defaults = {
            "minimax": ("MINIMAX_API_KEY", "MiniMax-M3", "https://api.minimaxi.com/v1"),
            "mimo": ("MIMO_API_KEY", "mimo-v2.5-pro", "https://token-plan-cn.xiaomimimo.com/v1"),
            "deepseek": ("DEEPSEEK_API_KEY", "deepseek-v4-flash", "https://api.deepseek.com"),
            "openai": ("OPENAI_API_KEY", "gpt-4", "https://api.openai.com/v1"),
            "claude": ("ANTHROPIC_API_KEY", "claude-3-opus-20240229", "https://api.anthropic.com"),
        }
        provider = llm_raw.get("provider", "minimax")
        api_key_env, default_model, default_base_url = provider_defaults.get(
            provider, provider_defaults["minimax"]
        )
        fallback_raw = llm_raw.get("fallback", {})
        fallback_provider = fallback_raw.get("provider", "mimo")
        fallback_env, fallback_model, fallback_base_url = provider_defaults.get(
            fallback_provider, provider_defaults["mimo"]
        )
        fallback = LLMFallbackConfig(
            provider=fallback_provider,
            api_key=os.getenv(fallback_env, ""),
            api_key_env=fallback_env,
            model=fallback_raw.get("model", fallback_model),
            base_url=fallback_raw.get("base_url", fallback_base_url),
            enabled=bool(fallback_raw.get("enabled", True)),
            usage_scope=fallback_raw.get("usage_scope", "general"),
        )
        llm = LLMConfig(
            provider=provider,
            api_key=os.getenv(api_key_env, ""),
            api_key_env=api_key_env,
            model=llm_raw.get("model", default_model),
            base_url=llm_raw.get("base_url", default_base_url),
            max_tokens=llm_raw.get("max_tokens", 8192),
            max_document_chars=llm_raw.get("max_document_chars", 800000),
            temperature=llm_raw.get("temperature", 1.0),
            reasoning_split=bool(llm_raw.get("reasoning_split", True)),
            fallback=fallback,
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
            windows_downloads=Path(os.path.expanduser("~/StockInfoDownloader/downloads")),
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
            errors.append(f"缺少 LLM API Key (设置 {self.llm.api_key_env} 环境变量)")

        # LLM provider 白名单
        valid_providers = {"minimax", "mimo", "deepseek", "openai", "claude"}
        if self.llm.provider and self.llm.provider not in valid_providers:
            errors.append(f"不支持的 LLM provider: {self.llm.provider} (支持: {valid_providers})")
        if self.llm.fallback.provider not in valid_providers:
            errors.append(f"不支持的备用 LLM provider: {self.llm.fallback.provider}")
        if self.llm.fallback.usage_scope != "general":
            errors.append(
                f"不支持的备用 LLM usage_scope: {self.llm.fallback.usage_scope}"
            )

        # 数值范围验证
        if self.llm.temperature is not None and not (0 <= self.llm.temperature <= 2):
            errors.append(f"temperature 超出范围 [0, 2]: {self.llm.temperature}")
        if self.llm.max_tokens is not None and self.llm.max_tokens < 1:
            errors.append(f"max_tokens 必须为正数: {self.llm.max_tokens}")

        # 验证搜索配置
        if strict and not self.search.api_key:
            errors.append("缺少搜索 API Key (设置 TAVILY_API_KEY 环境变量)")

        # 验证调度配置白名单
        valid_intervals = {"hourly", "daily", "weekly", "monthly"}
        if hasattr(self, '_raw'):
            schedule = self._raw.get("schedule", {})
            for task, interval in schedule.items():
                if isinstance(interval, str) and interval not in valid_intervals:
                    errors.append(f"不支持的调度间隔: {task}={interval} (支持: {valid_intervals})")

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
            print("  LLM API Key: 已配置")
        else:
            print("  ⚠️ LLM API Key 为空")

        if config.search.api_key:
            print("  搜索 API Key: 已配置")
        else:
            print("  ⚠️ 搜索 API Key 为空")
        
        sys.exit(0)
    except Exception as e:
        print(f"❌ 配置加载失败: {e}", file=sys.stderr)
        sys.exit(1)
