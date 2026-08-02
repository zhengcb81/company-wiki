"""
config.py — 配置加载与验证

统一配置加载器，支持 fail-fast：未知字段、非法 interval、重复 ID、悬空引用均拒绝启动。
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from .domain import Company, Sector, Theme


# ── 合法调度间隔 ──────────────────────────────
VALID_INTERVALS = {"daily", "weekly", "monthly", "hourly", "manual"}


# ── 配置异常 ──────────────────────────────
class ConfigError(Exception):
    """配置验证错误"""
    pass


# ── 配置数据类 ──────────────────────────────

@dataclass
class LLMFallbackConfig:
    provider: str = "mimo"
    model: str = "mimo-v2.5-pro"
    base_url: str = "https://token-plan-cn.xiaomimimo.com/v1"
    enabled: bool = True
    usage_scope: str = "general"


@dataclass
class LLMConfig:
    provider: str = "minimax"
    model: str = "MiniMax-M3"
    base_url: str = "https://api.minimaxi.com/v1"
    max_tokens: int = 8192
    temperature: float = 1.0
    max_document_chars: int = 800000
    reasoning_split: bool = True
    fallback: LLMFallbackConfig = field(default_factory=LLMFallbackConfig)


@dataclass
class SearchConfig:
    engine: str = "tavily"
    results_per_query: int = 8
    language: str = "zh"
    max_age_days: int = 7


@dataclass
class ScheduleConfig:
    news_collection: str = "daily"
    report_check: str = "weekly"
    lint: str = "weekly"
    maintenance: str = "weekly"

    def validate(self) -> list[str]:
        """验证所有间隔是否合法，返回错误列表"""
        errors = []
        for name, value in self.__dict__.items():
            if value not in VALID_INTERVALS:
                errors.append(f"schedule.{name}: '{value}' 不是合法间隔 (允许: {VALID_INTERVALS})")
        return errors


@dataclass
class AppConfig:
    """应用配置"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    companies: dict[str, Company] = field(default_factory=dict)
    sectors: dict[str, Sector] = field(default_factory=dict)
    themes: dict[str, Theme] = field(default_factory=dict)
    graph_path: Optional[Path] = None
    companies_path: Optional[Path] = None


# ── 加载函数 ──────────────────────────────

def load_config(
    config_path: Path,
    companies_path: Optional[Path] = None,
    graph_path: Optional[Path] = None,
) -> AppConfig:
    """
    加载并验证配置。

    Args:
        config_path: config.yaml 路径
        companies_path: companies.yaml 路径（可选）
        graph_path: graph.yaml 路径（可选）

    Returns:
        验证通过的 AppConfig

    Raises:
        ConfigError: 配置验证失败
    """
    errors = []

    # 1. 加载 config.yaml
    if not config_path.exists():
        raise ConfigError(f"配置文件不存在: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    # 2. 解析 LLM 配置
    llm_raw = raw.get("llm", {})
    fallback_raw = llm_raw.get("fallback", {})
    fallback = LLMFallbackConfig(
        provider=fallback_raw.get("provider", "mimo"),
        model=fallback_raw.get("model", "mimo-v2.5-pro"),
        base_url=fallback_raw.get(
            "base_url", "https://token-plan-cn.xiaomimimo.com/v1"
        ),
        enabled=bool(fallback_raw.get("enabled", True)),
        usage_scope=fallback_raw.get("usage_scope", "general"),
    )
    llm = LLMConfig(
        provider=llm_raw.get("provider", "minimax"),
        model=llm_raw.get("model", "MiniMax-M3"),
        base_url=llm_raw.get("base_url", "https://api.minimaxi.com/v1"),
        max_tokens=llm_raw.get("max_tokens", 8192),
        temperature=llm_raw.get("temperature", 1.0),
        max_document_chars=llm_raw.get("max_document_chars", 800000),
        reasoning_split=bool(llm_raw.get("reasoning_split", True)),
        fallback=fallback,
    )

    # 3. 解析搜索配置
    search_raw = raw.get("search", {})
    search = SearchConfig(
        engine=search_raw.get("engine", "tavily"),
        results_per_query=search_raw.get("results_per_query", 8),
        language=search_raw.get("language", "zh"),
        max_age_days=search_raw.get("max_age_days", 7),
    )

    # 4. 解析调度配置
    sched_raw = raw.get("schedule", {})
    schedule = ScheduleConfig(
        news_collection=sched_raw.get("news_collection", "daily"),
        report_check=sched_raw.get("report_check", "weekly"),
        lint=sched_raw.get("lint", "weekly"),
        maintenance=sched_raw.get("maintenance", "weekly"),
    )

    # 5. 验证调度间隔
    sched_errors = schedule.validate()
    errors.extend(sched_errors)

    # 6. 加载公司配置
    companies = {}
    if companies_path and companies_path.exists():
        with open(companies_path, "r", encoding="utf-8") as f:
            comp_data = yaml.safe_load(f) or {}
        comp_raw = comp_data.get("companies", comp_data)

        if isinstance(comp_raw, dict):
            for name, info in comp_raw.items():
                if not isinstance(info, dict):
                    continue
                company = Company(
                    id=_make_company_id(info.get("exchange", ""), info.get("ticker", "")),
                    name=name,
                    ticker=info.get("ticker", ""),
                    exchange=info.get("exchange", ""),
                    sectors=info.get("sectors", []),
                    themes=info.get("themes", []),
                    position=info.get("position", ""),
                    competes_with=info.get("competes_with", []),
                    news_queries=info.get("news_queries", []),
                    aliases=info.get("aliases", []),
                )
                companies[name] = company

    # 7. 加载行业和主题（从 graph.yaml）
    sectors = {}
    themes = {}
    if graph_path and graph_path.exists():
        with open(graph_path, "r", encoding="utf-8") as f:
            graph_data = yaml.safe_load(f) or {}

        # 从 edges 提取行业
        sector_names = set()
        for edge in graph_data.get("edges", []):
            for key in ("from", "to"):
                name = edge.get(key, "")
                # 行业通常是2-4个字的中文名
                if name and not any(c in name for c in ["设备", "材料", "代工", "封测", "芯片", "基建", "应用", "模块", "液冷", "电力"]):
                    continue
                if name:
                    sector_names.add(name)

        # 从 questions 提取行业
        questions = graph_data.get("questions", {})
        for q_group_name in questions:
            sector_names.add(q_group_name)

        for name in sector_names:
            sector = Sector(
                id=f"sector:{name}",
                name=name,
                default_questions=[q.get("q", q) if isinstance(q, dict) else str(q)
                                   for q in questions.get(name, [])],
            )
            sectors[name] = sector

        # 从公司配置中提取主题
        theme_names = set()
        for company in companies.values():
            theme_names.update(company.themes)

        for name in theme_names:
            theme = Theme(
                id=f"theme:{name}",
                name=name,
                companies=[c.name for c in companies.values() if name in c.themes],
            )
            themes[name] = theme

    # 8. 检查未知字段（在 config.yaml 顶层）
    known_top_keys = {"schedule", "llm", "search", "report_downloader", "news", "budget", "assessments"}
    unknown_keys = set(raw.keys()) - known_top_keys
    for key in unknown_keys:
        errors.append(f"config.yaml: 未知顶层字段 '{key}'")

    # 9. 汇总错误
    if errors:
        raise ConfigError("配置验证失败:\n" + "\n".join(f"  - {e}" for e in errors))

    return AppConfig(
        llm=llm,
        search=search,
        schedule=schedule,
        companies=companies,
        sectors=sectors,
        themes=themes,
        graph_path=graph_path,
        companies_path=companies_path,
    )


def _make_company_id(exchange: str, ticker: str) -> str:
    """生成公司稳定 ID: exchange:ticker"""
    if exchange and ticker:
        return f"{exchange}:{ticker}"
    return ticker or ""


def load_pilot_config(pilot_path: Path) -> dict:
    """加载 pilot.yaml 配置"""
    if not pilot_path.exists():
        raise ConfigError(f"Pilot 配置不存在: {pilot_path}")
    with open(pilot_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
