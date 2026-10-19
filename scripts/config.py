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
import re
import yaml
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

from common import WIKI_ROOT

logger = logging.getLogger(__name__)

_DEFAULT_DOWNLOADER_ROOT = (
    Path.home() / "Projects" / "StockInfoDLSimple" / "v2-clean-rewrite"
)

_PROJECT_DOTENV_AUTHORITATIVE_KEYS = frozenset(
    {"MINIMAX_API_KEY", "MIMO_API_KEY"}
)


def _load_dotenv():
    """Load managed keys; DeepSeek's environment key takes precedence.

    MiniMax/MiMo use this project's managed keys. DeepSeek is configured in the
    user's environment; .env supplies it only when that variable is absent.
    """
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


MODEL_CONFIG_SCHEMA = "company-wiki-models/1"


def _load_model_profiles(base_dir: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
    """Read the single provider table (``config/models.yaml``).

    Model ids, endpoints and credential variable names live only in that file;
    this loader never carries provider defaults of its own.
    """
    candidates = []
    if base_dir is not None:
        candidates.append(Path(base_dir) / "config" / "models.yaml")
    candidates.append(Path(__file__).resolve().parents[1] / "config" / "models.yaml")
    for path in candidates:
        if not path.is_file():
            continue
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict) or raw.get("schema_version") != MODEL_CONFIG_SCHEMA:
            raise ValueError(
                f"model config must declare schema_version {MODEL_CONFIG_SCHEMA!r}: {path}"
            )
        providers = raw.get("providers")
        if not isinstance(providers, dict) or not providers:
            raise ValueError(f"model config defines no providers: {path}")
        profiles: Dict[str, Dict[str, str]] = {}
        for provider, row in providers.items():
            if not isinstance(row, dict):
                raise ValueError(f"provider {provider!r} must be a mapping: {path}")
            values = {name: row.get(name) for name in ("api_key_env", "model", "base_url")}
            if not all(isinstance(value, str) and value.strip() for value in values.values()):
                raise ValueError(f"provider {provider!r} is incomplete: {path}")
            profiles[str(provider)] = {
                "api_key_env": values["api_key_env"].strip(),
                "model": values["model"].strip(),
                "base_url": values["base_url"].strip().rstrip("/"),
            }
        return profiles
    raise ValueError("config/models.yaml not found; model configuration is required")


@dataclass
class LLMFallbackConfig:
    """Secondary provider profile with an explicit workload policy."""

    provider: str = "mimo"
    api_key: str = ""
    api_key_env: str = ""
    model: str = ""
    base_url: str = ""
    enabled: bool = True
    usage_scope: str = "general"

    def __post_init__(self) -> None:
        profile = _load_model_profiles().get(self.provider)
        if profile is None:
            raise ValueError(
                f"provider {self.provider!r} is not defined in config/models.yaml"
            )
        if not self.model:
            self.model = profile["model"]
        if not self.base_url:
            self.base_url = profile["base_url"]
        if not self.api_key_env:
            self.api_key_env = profile["api_key_env"]
        if not self.api_key:
            self.api_key = os.getenv(self.api_key_env, "")


@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: str = "minimax"
    api_key: str = ""
    api_key_env: str = ""
    model: str = ""
    base_url: str = ""
    max_tokens: int = 8192
    max_document_chars: int = 800000  # ~1M tokens 的 80%，用于整篇文档分析
    temperature: float = 1.0
    reasoning_split: bool = True
    fallback: LLMFallbackConfig = field(default_factory=LLMFallbackConfig)
    generation_policy: Dict[str, Dict[str, Dict[str, str]]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        profile = _load_model_profiles().get(self.provider)
        if profile is None:
            raise ValueError(
                f"provider {self.provider!r} is not defined in config/models.yaml"
            )
        if not self.model:
            self.model = profile["model"]
        if not self.base_url:
            self.base_url = profile["base_url"]
        if not self.api_key_env:
            self.api_key_env = profile["api_key_env"]
        if not self.api_key:
            self.api_key = os.getenv(self.api_key_env, "")

    def generation_options(self, purpose: str = "general") -> Dict[str, Any]:
        """Resolve explicit provider/purpose options without credentials or defaults."""
        policy = self.generation_policy
        if not isinstance(policy, dict):
            raise ValueError("generation_policy must be a provider mapping")
        if not isinstance(purpose, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", purpose):
            raise ValueError("generation_policy purpose must be a named workload")
        for provider, purposes in policy.items():
            if provider not in {"minimax", "mimo", "deepseek", "openai", "claude"}:
                raise ValueError("generation_policy contains an unknown provider")
            if not isinstance(purposes, dict):
                raise ValueError("generation_policy provider must contain purpose mappings")
            for name, options in purposes.items():
                if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", name):
                    raise ValueError("generation_policy purpose must be a named workload")
                if not isinstance(options, dict) or not options.keys() <= {"thinking", "reasoning_effort"}:
                    raise ValueError("generation_policy contains unsupported options")
                thinking_values = {"enabled", "disabled"}
                if provider != "deepseek":
                    thinking_values.add("adaptive")
                for key, values in (("thinking", thinking_values),
                                    ("reasoning_effort", {"low", "high", "max"})):
                    if key in options and (not isinstance(options[key], str) or options[key] not in values):
                        raise ValueError("generation_policy contains an invalid " + key)
        purposes = policy.get(self.provider, {})
        selected = {**purposes.get("general", {}), **purposes.get(purpose, {})}
        wire: Dict[str, Any] = {}
        if "thinking" in selected:
            wire["thinking"] = {"type": selected["thinking"]}
        if "reasoning_effort" in selected:
            wire["reasoning_effort"] = selected["reasoning_effort"]
        return wire


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
    downloader_dir: Path = _DEFAULT_DOWNLOADER_ROOT
    windows_downloads: Path = _DEFAULT_DOWNLOADER_ROOT / "downloads"


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
    def load(cls, config_path: Optional[Path] = None, *,
             llm_provider: Optional[str] = None,
             validation_scope: str = "all") -> 'Config':
        """
        加载配置
        
        优先级: MiniMax/MiMo 项目受管 Key；DeepSeek 环境变量优先、.env 补缺。
        模型参数来自 config/models.yaml（单一模型源），config.yaml 只选择 provider 并可逐项覆盖。
        
        Args:
            config_path: 配置文件路径，默认为 ~/company-wiki/config.yaml
            
        Returns:
            Config 对象
            
        Raises:
            FileNotFoundError: 配置文件不存在
            ValueError: 配置验证失败
        """
        if validation_scope not in ("all", "llm"):
            raise ValueError("unsupported configuration validation scope")
        llm_only = validation_scope == "llm"

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
        raw_config = cls._apply_env_overrides(raw_config, llm_only=llm_only)
        
        # 构建配置对象
        config = cls._build_config(raw_config, config_path.parent, llm_only=llm_only,
                                   llm_provider=llm_provider if llm_only else None)
        config.llm = config.llm_for_provider(llm_provider)
        
        # 验证配置（测试模式下使用宽松验证）
        is_test = os.getenv("PYTEST_CURRENT_TEST") is not None
        config.validate(strict=llm_only or not is_test, llm_only=llm_only)
        
        config._raw = raw_config
        return config

    def llm_for_provider(self, provider: Optional[str] = None) -> LLMConfig:
        """Select an existing provider profile without changing persisted config.

        Primary and configured fallback retain their exact model/endpoint. Other
        providers use this loader's defaults with the shared generation settings.
        Credentials stay runtime-only. Selection is explicit; this does not retry.
        """
        if provider is None or provider == self.llm.provider:
            return self.llm
        fallback = self.llm.fallback
        if provider == fallback.provider:
            if not fallback.enabled:
                raise ValueError("configured fallback is disabled")
            return replace(self.llm, provider=fallback.provider, api_key=fallback.api_key,
                           api_key_env=fallback.api_key_env, model=fallback.model,
                           base_url=fallback.base_url)
        generation = {name: getattr(self.llm, name) for name in (
            "max_tokens", "max_document_chars", "temperature", "reasoning_split", "generation_policy")}
        selected = self._build_config({"llm": {"provider": provider, **generation}},
                                      self.paths.wiki_root)
        selected.validate(strict=False)
        return replace(selected.llm, fallback=fallback)
    
    @staticmethod
    def _apply_env_overrides(raw: Dict[str, Any], *, llm_only: bool = False) -> Dict[str, Any]:
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
        if not llm_only and os.getenv("TAVILY_API_KEY"):
            raw.setdefault("search", {})["tavily_api_key"] = os.getenv("TAVILY_API_KEY")
        
        # Wiki Root
        if not llm_only and os.getenv("WIKI_ROOT"):
            raw.setdefault("paths", {})["wiki_root"] = os.getenv("WIKI_ROOT")
        
        return raw
    
    @staticmethod
    def _build_config(raw: Dict[str, Any], base_dir: Path, *, llm_only: bool = False,
                      llm_provider: Optional[str] = None) -> 'Config':
        """构建配置对象"""
        # LLM 配置（provider 选择 + config/models.yaml 单一模型源）
        llm_raw = raw.get("llm", {})
        model_profiles = _load_model_profiles(base_dir)
        provider = llm_raw.get("provider", "minimax")
        if llm_only:
            # Select the actual profile before constructing its credentials or
            # unrelated components. Defaults remain in this one provider table.
            selected_provider = llm_provider or provider
            if selected_provider != provider:
                configured_fallback = llm_raw.get("fallback", {})
                selected = {
                    name: llm_raw[name] for name in (
                        "max_tokens", "max_document_chars", "temperature",
                        "reasoning_split", "generation_policy",
                    ) if name in llm_raw
                }
                if (isinstance(configured_fallback, dict)
                        and configured_fallback.get("provider", "mimo") == selected_provider):
                    if not configured_fallback.get("enabled", True):
                        raise ValueError("configured fallback is disabled")
                    for name in ("model", "base_url"):
                        if name in configured_fallback:
                            selected[name] = configured_fallback[name]
                llm_raw = {**selected, "provider": selected_provider}
                provider = selected_provider
        selected_profile = model_profiles.get(provider) or model_profiles.get("minimax")
        if selected_profile is None:
            raise ValueError("config/models.yaml defines neither the selected provider nor minimax")
        api_key_env = selected_profile["api_key_env"]
        default_model = selected_profile["model"]
        default_base_url = selected_profile["base_url"]
        fallback = LLMFallbackConfig()
        if not llm_only:
            fallback_raw = llm_raw.get("fallback", {})
            fallback_provider = fallback_raw.get("provider", "mimo")
            fallback_profile = model_profiles.get(fallback_provider) or model_profiles.get("mimo")
            if fallback_profile is None:
                raise ValueError("config/models.yaml defines neither the fallback provider nor mimo")
            fallback_env = fallback_profile["api_key_env"]
            fallback_model = fallback_profile["model"]
            fallback_base_url = fallback_profile["base_url"]
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
            generation_policy=copy.deepcopy(llm_raw.get("generation_policy", {})),
        )
        
        if llm_only:
            return Config(llm=llm)

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
            downloader_dir=_DEFAULT_DOWNLOADER_ROOT,
            windows_downloads=_DEFAULT_DOWNLOADER_ROOT / "downloads",
        )
        
        return Config(
            llm=llm,
            search=search,
            schedule=schedule,
            downloader=downloader,
            paths=paths,
        )
    
    def validate(self, strict: bool = True, *, llm_only: bool = False) -> None:
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
        if not llm_only:
            if self.llm.fallback.provider not in valid_providers:
                errors.append(f"不支持的备用 LLM provider: {self.llm.fallback.provider}")
            if self.llm.fallback.usage_scope != "general":
                errors.append(
                    f"不支持的备用 LLM usage_scope: {self.llm.fallback.usage_scope}"
                )

        try:
            self.llm.generation_options()
        except ValueError as exc:
            errors.append(str(exc))

        # 数值范围验证
        if self.llm.temperature is not None and not (0 <= self.llm.temperature <= 2):
            errors.append(f"temperature 超出范围 [0, 2]: {self.llm.temperature}")
        if self.llm.max_tokens is not None and self.llm.max_tokens < 1:
            errors.append(f"max_tokens 必须为正数: {self.llm.max_tokens}")

        if not llm_only:
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
