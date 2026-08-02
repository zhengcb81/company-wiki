#!/usr/bin/env python3
"""
llm_client.py — 统一 LLM 客户端模块

为整个知识库系统提供统一的 LLM 调用接口:
- 支持多 provider (DeepSeek/OpenAI/Anthropic)
- 统一的重试/限流/错误处理
- 封装常用业务 prompt (分析/摘要/矛盾检测/wikilink/评估/查询/lint)
- 始终有 fallback
- 兼容已有调用方 (generate/summarize/judge_relevance/detect_contradiction)

模块结构（两大部分）:
  ┌─────────────────────────────────────────────────────────────┐
  │  基础设施 (第 49–508 行)                                     │
  │  LLMClient 初始化、API 调用、限流、成本追踪                    │
  │  ───────────────────────────────────────────────────────── │
  │  业务方法 (第 509–1092 行)                                   │
  │  内容分析、摘要生成、Wikilinks、综合评估、查询、矛盾检测、lint   │
  └─────────────────────────────────────────────────────────────┘

线程约束:
  LLMClient 不是线程安全的。整个系统（scheduler.py 在内）以单线程顺序执行任务。
  如需多线程，须将 LLMClient 改为无状态设计或引入锁机制。

用法:
    from llm_client import LLMClient, get_llm_client

    # 方式 1: 自动从 config.yaml 加载
    client = LLMClient()

    # 方式 2: 手动指定 provider
    client = LLMClient(provider="deepseek")

    # 基础调用
    result = client.chat("分析这段文本", system="你是一个分析师")
    result = client.generate("分析这段文本")  # 向后兼容

    # 业务方法
    info = client.analyze_content(content, entity_name="中微公司")
    summary = client.generate_summary(content, topic="公司动态")
    links = client.generate_wikilinks(content, available_pages=["寒武纪", "GPU与AI芯片"])
    assessment = client.synthesize_assessment(entries, topic="公司动态", entity="中微公司")
    questions = client.generate_core_questions("中微公司", sector="半导体设备")
    answer = client.answer_query("中微公司的竞争优势?", relevant_pages=[...])
    contradictions = client.detect_contradictions(page1, page2, entity="中微公司")
    issues = client.lint_page(page_content, all_pages_index)
"""

import csv
import json
import os
import re
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

from common import WIKI_ROOT

from prompts import (
    CONTENT_ANALYSIS_SYSTEM_PROMPT,
    SUMMARY_GENERATION_SYSTEM_PROMPT,
    ASSESSMENT_SYSTEM_PROMPT,
    CORE_QUESTIONS_SYSTEM_PROMPT,
    QUERY_ANSWER_SYSTEM_PROMPT,
    CONTRADICTION_DETECTION_SYSTEM_PROMPT,
    LINT_PAGE_SYSTEM_PROMPT,
    build_content_analysis_prompt,
    build_summary_generation_prompt,
    build_assessment_client_prompt,
    build_core_questions_prompt,
    build_query_answer_prompt,
    build_contradiction_detection_prompt,
    build_lint_page_prompt,
)

logger = logging.getLogger(__name__)

# ── LLM 成本追踪 ──────────────────────────
_COST_LOG_PATH = WIKI_ROOT / "llm_cost_log.csv"

# 各 provider 每百万 token 价格（USD）
# 参考各厂商官方定价，可按需更新
_PROVIDER_PRICING = {
    "deepseek": {"input": 0.14, "output": 0.28},
    "openai": {"input": 2.50, "output": 10.00},
    "claude": {"input": 3.00, "output": 15.00},
}


@dataclass
class LLMResponse:
    """LLM 响应"""

    content: str = ""
    provider: str = ""
    model: str = ""
    reasoning: str = ""
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: str = ""
    success: bool = True
    error: str = ""

    def __post_init__(self):
        if self.usage is None:
            self.usage = {}

    @property
    def tokens_used(self) -> int:
        return self.usage.get("total_tokens", 0)


class LLMClient:
    """统一 LLM 客户端"""

    def __init__(
        self,
        provider: str = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        config=None,
        workload: str = "research",
        enable_fallback: bool = True,
    ):
        """
        初始化 LLM 客户端

        优先级: 显式参数 > config 对象 > config.yaml > 环境变量 > 默认值

        Args:
            provider: LLM 提供商 (minimax/mimo/deepseek/openai/claude)
            api_key: API Key
            model: 模型名称
            base_url: API 基础 URL
            config: Config 对象 (from config.py)
        """
        self._sdk_client = None
        self._last_call_time = 0.0
        self._call_count = 0
        self.workload = workload
        self.fallback_client = None
        self.fallback_status = "not_configured"

        # 尝试从 config 对象加载
        if config is None and provider is None:
            try:
                from config import Config

                config = Config.load()
            except Exception:
                config = None

        # 从 config 对象提取参数
        if config and hasattr(config, "llm"):
            self.provider = provider or config.llm.provider
            self.api_key = api_key or config.llm.api_key
            self.model = model or config.llm.model
            self.base_url = base_url or config.llm.base_url
            self._max_tokens = config.llm.max_tokens
            self._temperature = config.llm.temperature
            self._reasoning_split = bool(
                getattr(config.llm, "reasoning_split", self.provider == "minimax")
            )
        else:
            self.provider = provider or self._detect_provider()
            self.api_key = api_key or self._get_api_key(self.provider)
            self.model = model or self._get_default_model(self.provider)
            self.base_url = base_url or self._get_base_url(self.provider)
            self._max_tokens = 1024
            self._temperature = 1.0 if self.provider == "minimax" else 0.3
            self._reasoning_split = self.provider == "minimax"

        if enable_fallback and config and hasattr(config, "llm"):
            fallback = getattr(config.llm, "fallback", None)
            if fallback is None:
                self.fallback_status = "not_configured"
            elif not fallback.enabled:
                self.fallback_status = "disabled"
            elif not fallback.api_key:
                self.fallback_status = "missing_api_key"
            else:
                self.fallback_client = LLMClient(
                    provider=fallback.provider,
                    api_key=fallback.api_key,
                    model=fallback.model,
                    base_url=fallback.base_url,
                    workload=workload,
                    enable_fallback=False,
                )
                self.fallback_status = "ready"

        # 限流和重试配置
        self._min_interval = 1.0
        self._max_retries = 3
        self._timeout = 60
        self._backoff_base = 2

        # 成本熔断配置
        self._daily_budget_usd = 15.0  # 默认日预算 $15 (~¥100)
        self._circuit_breaker_enabled = True
        self._budget_warning_threshold = 0.8  # 80% 时告警

        # 初始化底层客户端
        self._init_sdk_client()

    def _detect_provider(self) -> str:
        """根据环境变量检测 provider"""
        if os.getenv("MINIMAX_API_KEY"):
            return "minimax"
        if os.getenv("DEEPSEEK_API_KEY"):
            return "deepseek"
        if os.getenv("OPENAI_API_KEY"):
            return "openai"
        if os.getenv("ANTHROPIC_API_KEY"):
            return "claude"
        return "minimax"

    def _get_api_key(self, provider: str) -> str:
        """获取 API Key"""
        env_vars = {
            "minimax": "MINIMAX_API_KEY",
            "mimo": "MIMO_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "openai": "OPENAI_API_KEY",
            "claude": "ANTHROPIC_API_KEY",
        }
        return os.getenv(env_vars.get(provider, ""), "")

    def _get_default_model(self, provider: str) -> str:
        """获取默认模型"""
        models = {
            "minimax": "MiniMax-M3",
            "mimo": "mimo-v2.5-pro",
            "deepseek": "deepseek-v4-flash",
            "openai": "gpt-4",
            "claude": "claude-3-opus-20240229",
        }
        return models.get(provider, "MiniMax-M3")

    def _get_base_url(self, provider: str) -> str:
        """获取基础 URL"""
        urls = {
            "minimax": "https://api.minimaxi.com/v1",
            "mimo": "https://token-plan-cn.xiaomimimo.com/v1",
            "deepseek": "https://api.deepseek.com",
            "openai": "https://api.openai.com/v1",
            "claude": "https://api.anthropic.com",
        }
        return urls.get(provider, "https://api.minimaxi.com/v1")

    def _init_sdk_client(self):
        """初始化 OpenAI SDK 客户端 (兼容 DeepSeek)"""
        if not self.api_key:
            logger.debug("LLM API Key 为空, 将使用 fallback 模式")
            return

        try:
            from openai import OpenAI

            self._sdk_client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            logger.info(f"LLM SDK 客户端初始化成功 ({self.provider}/{self.model})")
        except ImportError:
            logger.debug("openai 包未安装, 将使用 urllib")
            self._sdk_client = None
        except Exception as e:
            logger.warning(f"SDK 初始化失败: {e}, 将使用 urllib")
            self._sdk_client = None

    @property
    def available(self) -> bool:
        """LLM 是否可用"""
        return bool(self.api_key)

    # ── 核心调用方法 ──────────────────────────

    def _get_daily_cost(self) -> float:
        """获取今日已消耗成本（USD）"""
        if not _COST_LOG_PATH.exists():
            return 0.0

        today = datetime.now().strftime("%Y-%m-%d")
        daily_cost = 0.0

        try:
            with open(_COST_LOG_PATH, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ts = row.get("timestamp", "")
                    if ts.startswith(today):
                        daily_cost += float(row.get("estimated_cost_usd", 0))
        except Exception as e:
            # 成本日志读取失败不应静默忽略，否则预算熔断失效
            print(f"[WARN] 成本日志读取失败，预算熔断可能失效: {e}")

        return daily_cost

    def _check_budget(self) -> Tuple[bool, str]:
        """
        检查成本熔断状态

        Returns:
            (是否允许调用, 状态消息)
        """
        if not self._circuit_breaker_enabled:
            return True, ""

        daily_cost = self._get_daily_cost()

        if daily_cost >= self._daily_budget_usd:
            return (
                False,
                f"日预算已耗尽: ${daily_cost:.2f}/${self._daily_budget_usd:.2f}",
            )

        if daily_cost >= self._daily_budget_usd * self._budget_warning_threshold:
            return (
                True,
                f"预算告警: ${daily_cost:.2f}/${self._daily_budget_usd:.2f} ({daily_cost / self._daily_budget_usd * 100:.0f}%)",
            )

        return True, ""

    def get_circuit_status(self) -> Dict[str, Any]:
        """获取熔断器状态"""
        daily_cost = self._get_daily_cost()
        remaining = max(0, self._daily_budget_usd - daily_cost)

        return {
            "enabled": self._circuit_breaker_enabled,
            "daily_budget_usd": self._daily_budget_usd,
            "daily_cost_usd": round(daily_cost, 4),
            "remaining_usd": round(remaining, 4),
            "usage_percent": round(daily_cost / self._daily_budget_usd * 100, 1)
            if self._daily_budget_usd > 0
            else 0,
            "circuit_open": daily_cost >= self._daily_budget_usd,
            "warning": daily_cost
            >= self._daily_budget_usd * self._budget_warning_threshold,
        }

    def chat(
        self,
        user: str,
        system: str = "",
        json_mode: bool = False,
        max_tokens: int = None,
        temperature: float = None,
    ) -> LLMResponse:
        """
        基础聊天调用

        Args:
            user: 用户消息
            system: 系统消息
            json_mode: 是否要求 JSON 格式响应
            max_tokens: 覆盖实例默认值（不修改实例状态）
            temperature: 覆盖实例默认值（不修改实例状态）

        Returns:
            LLMResponse 对象
        """
        if not self.available:
            return LLMResponse(success=False, error="LLM API Key 未配置")

        # 成本熔断检查
        allowed, message = self._check_budget()
        if not allowed:
            logger.warning(f"[Circuit Breaker] {message}")
            return LLMResponse(success=False, error=f"[成本熔断] {message}")
        elif message:
            logger.warning(f"[Circuit Breaker] {message}")

        self._rate_limit()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})

        if self.provider == "claude":
            return self._call_claude(messages, json_mode, max_tokens=max_tokens)

        # DeepSeek / OpenAI 都用 OpenAI 兼容 API
        if self._sdk_client is not None:
            return self._call_with_sdk(
                messages, json_mode, max_tokens=max_tokens, temperature=temperature
            )
        else:
            return self._call_with_urllib(
                messages, json_mode, max_tokens=max_tokens, temperature=temperature
            )

    def chat_with_retry(
        self,
        user: str,
        system: str = "",
        max_retries: int = None,
        max_tokens: int = None,
        temperature: float = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        """带重试的聊天调用"""
        if max_retries is None:
            max_retries = self._max_retries

        last_error = ""
        for attempt in range(max_retries):
            response = self.chat(
                user,
                system,
                json_mode=json_mode,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            if not response.provider:
                response.provider = self.provider
            if not response.model:
                response.model = self.model
            if response.success:
                return response

            last_error = response.error
            if attempt < max_retries - 1:
                wait = self._backoff_base**attempt
                logger.warning(
                    f"LLM 失败 ({attempt + 1}/{max_retries}), {wait}s 后重试: {last_error}"
                )
                time.sleep(wait)

        primary_failure = LLMResponse(
            provider=self.provider,
            model=self.model,
            success=False,
            error=f"重试 {max_retries} 次后仍失败: {last_error}",
        )
        if self.fallback_client is not None:
            logger.warning(
                "Primary LLM exhausted retries; trying policy-approved fallback %s/%s",
                self.fallback_client.provider,
                self.fallback_client.model,
            )
            return self.fallback_client.chat_with_retry(
                user,
                system,
                max_retries=max_retries,
                max_tokens=max_tokens,
                temperature=temperature,
                json_mode=json_mode,
            )
        return primary_failure

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = None,
        temperature: float = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        """
        生成文本 (向后兼容接口)

        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            max_tokens: 最大 token 数 (覆盖默认值)
            temperature: 温度 (覆盖默认值)
            json_mode: 是否要求 provider 返回 JSON 对象

        Returns:
            LLMResponse 对象
        """
        # 通过参数传递到底层调用，不修改实例状态（线程安全）
        return self.chat_with_retry(
            prompt,
            system_prompt or "",
            max_tokens=max_tokens,
            temperature=temperature,
            json_mode=json_mode,
        )

    # ── 底层调用实现 ──────────────────────────

    def _call_with_sdk(
        self,
        messages: list,
        json_mode: bool,
        max_tokens: int = None,
        temperature: float = None,
    ) -> LLMResponse:
        """使用 OpenAI SDK 调用"""
        try:
            token_limit = max_tokens if max_tokens is not None else self._max_tokens
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature
                if temperature is not None
                else self._temperature,
            }
            if self.provider in {"minimax", "mimo"}:
                kwargs["max_completion_tokens"] = token_limit
            else:
                kwargs["max_tokens"] = token_limit
            if self.provider == "minimax" and self._reasoning_split:
                kwargs["extra_body"] = {"reasoning_split": True}
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = self._sdk_client.chat.completions.create(**kwargs)

            choice = response.choices[0]
            content = choice.message.content or ""
            reasoning = getattr(choice.message, "reasoning_content", "") or ""

            usage = {}
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            self._call_count += 1
            self._log_cost(usage)
            return LLMResponse(
                content=content,
                model=self.model,
                reasoning=reasoning,
                usage=usage,
                finish_reason=choice.finish_reason or "",
                success=True,
            )

        except Exception as e:
            return LLMResponse(success=False, error=f"SDK 调用失败: {e}")

    def _call_with_urllib(
        self,
        messages: list,
        json_mode: bool,
        max_tokens: int = None,
        temperature: float = None,
    ) -> LLMResponse:
        """使用 urllib 直接调用"""
        import urllib.request
        import urllib.error

        token_limit = max_tokens if max_tokens is not None else self._max_tokens
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
            if temperature is not None
            else self._temperature,
        }
        if self.provider in {"minimax", "mimo"}:
            payload["max_completion_tokens"] = token_limit
        else:
            payload["max_tokens"] = token_limit
        if self.provider == "minimax" and self._reasoning_split:
            payload["reasoning_split"] = True
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content", "")
            reasoning = message.get("reasoning_content", "")
            usage = data.get("usage", {})

            self._call_count += 1
            self._log_cost(usage)
            return LLMResponse(
                content=content,
                model=data.get("model", self.model),
                reasoning=reasoning,
                usage=usage,
                finish_reason=choice.get("finish_reason", ""),
                success=True,
            )

        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return LLMResponse(success=False, error=f"HTTP {e.code}: {body[:200]}")
        except Exception as e:
            return LLMResponse(success=False, error=f"urllib 调用失败: {e}")

    def _call_claude(
        self, messages: list, json_mode: bool, max_tokens: int = None
    ) -> LLMResponse:
        """调用 Claude API (不同的请求格式)"""
        import urllib.request
        import urllib.error

        # Claude API 格式不同
        system_content = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                user_messages.append(msg)

        payload = {
            "model": self.model,
            "max_tokens": max_tokens if max_tokens is not None else self._max_tokens,
            "messages": user_messages,
        }
        if system_content:
            payload["system"] = system_content

        url = f"{self.base_url}/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            content = data.get("content", [{}])[0].get("text", "")
            usage = data.get("usage", {})

            self._call_count += 1
            self._log_cost(usage)
            return LLMResponse(
                content=content,
                model=data.get("model", self.model),
                usage=usage,
                finish_reason=data.get("stop_reason", ""),
                success=True,
            )
        except Exception as e:
            return LLMResponse(success=False, error=f"Claude 调用失败: {e}")

    def _rate_limit(self):
        """简单限流"""
        elapsed = time.time() - self._last_call_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_call_time = time.time()

    # ── 成本追踪 ────────────────────────────────

    def _log_cost(self, usage: Dict[str, int]):
        """将本次调用记录到成本 CSV"""
        if not usage:
            return
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)

        pricing = _PROVIDER_PRICING.get(self.provider, {"input": 0.27, "output": 1.10})
        input_cost = prompt_tokens / 1_000_000 * pricing["input"]
        output_cost = completion_tokens / 1_000_000 * pricing["output"]
        estimated_cost = input_cost + output_cost

        _COST_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

        try:
            # 检查是否需要写 header（在 open 之前原子判断）
            needs_header = (
                not _COST_LOG_PATH.exists() or _COST_LOG_PATH.stat().st_size == 0
            )
            with open(_COST_LOG_PATH, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if needs_header:
                    writer.writerow(
                        [
                            "timestamp",
                            "provider",
                            "model",
                            "prompt_tokens",
                            "completion_tokens",
                            "total_tokens",
                            "estimated_cost_usd",
                        ]
                    )
                writer.writerow(
                    [
                        datetime.now().isoformat(),
                        self.provider,
                        self.model,
                        prompt_tokens,
                        completion_tokens,
                        total_tokens,
                        round(estimated_cost, 6),
                    ]
                )
        except Exception as e:
            logger.warning(f"成本日志写入失败: {e}")

    def get_cost_stats(self) -> Dict[str, Any]:
        """获取成本统计"""
        if not _COST_LOG_PATH.exists():
            return {"total_calls": 0, "total_tokens": 0, "total_cost_usd": 0.0}

        total_tokens = 0
        total_cost = 0.0
        count = 0

        try:
            with open(_COST_LOG_PATH, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    count += 1
                    total_tokens += int(row.get("total_tokens", 0))
                    total_cost += float(row.get("estimated_cost_usd", 0))
        except Exception as e:
            logger.warning(f"成本统计读取失败: {e}")

        return {
            "total_calls": count,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
            "avg_cost_per_call": round(total_cost / count, 6) if count else 0,
        }

    # ── 业务方法: 内容分析 ──────────────────────

    def analyze_content(self, content: str, entity_name: str = "") -> Dict[str, Any]:
        """
        分析内容, 提取关键信息

        Returns:
            {"key_points", "entities_mentioned", "topics_affected",
             "sentiment", "importance", "suggested_questions"}
        """
        system = CONTENT_ANALYSIS_SYSTEM_PROMPT
        user = build_content_analysis_prompt(content, entity_name)

        response = self.chat_with_retry(user, system)
        if response.success:
            parsed = self._parse_json_response(response.content)
            if parsed:
                return parsed

        return self._fallback_analyze(content)

    def analyze_full_document(
        self,
        content: str,
        entity_name: str = "",
        doc_type: str = "annual_report",
        previous_period_data: str = "",
        published_date: str = "",
    ) -> Dict[str, Any]:
        """
        分析完整文档（利用 1M 上下文，直接传入整篇文档不做截断）。

        适用于：年报/半年报/季报/招股书等大型 PDF 文档。

        Args:
            content: 完整文档文本（可长达数十万字符）
            entity_name: 相关实体名称
            doc_type: 文档类型 (annual_report/quarterly_report/prospectus/announcement)
            previous_period_data: 上一期财务数据（用于环比分析）

        Returns:
            {"key_points", "financial_highlights", "entities_mentioned",
             "topics_affected", "sentiment", "importance", "suggested_questions"}
        """
        # 根据文档类型选择分析角度
        doc_type_prompts = {
            "annual_report": "请从年度经营、财务表现、研发投入、行业地位等角度全面分析。",
            "半年度报告": "请从半年度经营、财务表现、环比变化、行业地位等角度分析。",
            "quarterly_report": "请从季度经营、财务表现、环比同比变化等角度分析。",
            "prospectus": "请从业务模式、竞争优势、募集资金用途、风险因素等角度分析。",
            "announcement": "请从公告内容、影响程度、投资价值等角度快速分析。",
        }
        doc_hint = doc_type_prompts.get(doc_type, "请全面分析此文档的关键信息。")

        # 如果有上一期数据，添加环比分析提示
        prev_section = ""
        if previous_period_data:
            prev_section = f"""
上一期财务数据（用于环比分析）:
{previous_period_data}

请结合上期数据进行环比分析。"""

        # 报告发布日期真相源 — 防止 LLM 自填日期幻觉
        # （根因修复：整篇文档分析时 LLM 看到年报正文里出现多个年份的数字，
        #   会自填 date 字段为正文里提到的年份，导致时间线日期失真。
        #   日期是结构字段不是内容，应由文件名事实层决定。）
        date_section = ""
        if published_date:
            date_section = f"""
报告发布日期: {published_date}
⚠️ 重要：所有 timeline_entries 的 date 字段必须填 "{published_date}"，
不要从文档正文里挑年份自填，不要使用原文中提到的其他历史年份。"""

        system = "你是一个专业的上市公司研究分析助手。请严格按要求的JSON格式输出。"

        user = f"""你是一名资深财务分析师。请深度分析以下{doc_hint}{prev_section}{date_section}

{f"相关实体: {entity_name}" if entity_name else ""}
{f"文档类型: {doc_type}" if doc_type else ""}

## 分析要求
请从以下维度提取关键信息，每维度输出一条时间线条目：

1. **经营亮点**：营收、利润、市场份额等核心指标
2. **研发突破**：关键技术、专利、产品进展
3. **行业动态**：市场竞争、供需变化、政策影响
4. **战略布局**：产能扩张、并购合作、海外布局
5. **风险因素**：竞争风险、政策风险、经营风险
6. **财务健康**：现金流、负债、资产质量

## 输出格式
请以以下JSON格式返回（必须是有效JSON，不要有其他内容）：
{{
    "timeline_entries": [
        {{
            "date": "<YYYY-MM-DD>",
            "source_type": "<来源类型>",
            "title": "<标题，简洁概括>",
            "points": ["<要点1>", "<要点2>", "<要点3>"]
        }}
    ],
    "sentiment": "positive/negative/neutral",
    "importance": 0.0到1.0之间的数值
}}

只返回JSON，不要其他内容。"""

        response = self.chat_with_retry(user, system, max_tokens=8192)
        if response.success:
            parsed = self._parse_json_response(response.content)
            if parsed:
                return parsed

        # Fallback：返回空结构
        return {"timeline_entries": [], "sentiment": "neutral", "importance": 0.0}

    # ── 业务方法: 摘要生成 ──────────────────────

    def generate_summary(self, content: str, topic: str = "", entity: str = "") -> str:
        """
        生成精炼摘要 (返回 "- 要点" 格式)
        """
        system = SUMMARY_GENERATION_SYSTEM_PROMPT
        user = build_summary_generation_prompt(content, topic, entity)

        response = self.chat_with_retry(user, system)
        if response.success and response.content.strip():
            lines = response.content.strip().split("\n")
            clean_lines = []
            for line in lines:
                line = line.strip()
                line = re.sub(r"^\d+[\.\)、]\s*", "", line)
                line = re.sub(r"^[-*•]\s*", "- ", line)
                if line and not line.startswith("- "):
                    line = f"- {line}"
                if line:
                    clean_lines.append(line)
            return "\n".join(clean_lines)

        # Fallback
        content_truncated = content[:2000] if len(content) > 2000 else content
        sentences = re.split(r"(?<=[。！？；])\s*", content_truncated)
        fallback = [f"- {s.strip()}" for s in sentences[:3] if len(s.strip()) > 10]
        return "\n".join(fallback) if fallback else "- 内容已处理"

    def summarize(self, text: str, max_points: int = 5) -> List[str]:
        """向后兼容: 使用 LLM 生成摘要 (返回字符串列表)"""
        content = self.generate_summary(text)
        # 去掉 "- " 前缀返回纯文本列表
        return [
            l[2:].strip() for l in content.split("\n") if l.strip().startswith("- ")
        ][:max_points]

    # ── 业务方法: Wikilinks ─────────────────────

    def generate_wikilinks(self, content: str, available_pages: List[str]) -> List[str]:
        """
        识别内容中可以链接到已有 wiki 页面的实体
        """
        if not available_pages:
            return []

        # 规则匹配优先 (快速, 无 LLM 调用)
        rule_links = []
        for page_name in available_pages:
            if page_name in content and f"[[{page_name}]]" not in content:
                rule_links.append(page_name)

        return rule_links[:10]

    # ── 业务方法: 综合评估 ─────────────────────

    def synthesize_assessment(
        self,
        timeline_entries: List[str],
        topic: str = "",
        entity: str = "",
        core_questions: List[str] = None,
    ) -> str:
        """
        基于时间线条目生成综合评估
        """
        combined = "\n".join(timeline_entries[:20])
        if len(combined) > 4000:
            combined = combined[:4000]

        system = ASSESSMENT_SYSTEM_PROMPT
        user = build_assessment_client_prompt(combined, topic, entity, core_questions)

        response = self.chat_with_retry(user, system)
        if response.success and response.content.strip():
            text = response.content.strip()
            if not text.startswith(">"):
                text = "> " + text.replace("\n", "\n> ")
            return text

        return "> 待积累数据后补充。"

    def generate_core_questions(
        self,
        entity: str,
        sector: str = "",
        position: str = "",
        existing_data: str = "",
        question_templates: List[str] = None,
    ) -> List[str]:
        """
        为实体生成核心追踪问题。

        Args:
            question_templates: 行业级问题模板（从 graph.yaml 加载），
                               用于锚定 LLM 的研究方向，避免产出通用废话。
        """
        system = CORE_QUESTIONS_SYSTEM_PROMPT
        user = build_core_questions_prompt(
            entity, sector, position, existing_data, question_templates
        )

        response = self.chat_with_retry(user, system)
        if response.success and response.content.strip():
            lines = [
                l.strip().lstrip("- •").strip()
                for l in response.content.strip().split("\n")
            ]
            return [l for l in lines if l and len(l) > 5][:5]

        # LLM 不可用时，如果有模板就使用模板，否则返回空
        if question_templates:
            return question_templates[:5]
        return []

    def batch_analyze(
        self, contents: List[Dict[str, str]], entity: str = "", topic: str = "公司动态"
    ) -> List[Dict[str, Any]]:
        """
        批量分析多个文档，生成综合时间线条目。

        利用 1M 上下文，将多个文档一次性发给 LLM 做综合分析，
        比逐个分析能更好地捕捉跨文档的关联和趋势。

        Args:
            contents: 文档列表，每项包含:
                - content: 文档文本
                - title: 文档标题/标签
                - date: 日期（可选）
                - source_type: 来源类型（可选）
            entity: 实体名称
            topic: 主题

        Returns:
            [{"date": "...", "title": "...", "points": [...], "source": "..."}, ...]
        """
        if not contents:
            return []

        # 组合多个文档内容（最多 10 个，总计控制在 80 万字符）
        MAX_DOCS = 10
        MAX_TOTAL_CHARS = 800000

        selected = contents[:MAX_DOCS]
        combined = ""
        for i, doc in enumerate(selected):
            src = doc.get("source_type", "文档")
            title = doc.get("title", f"文档{i + 1}")
            date = doc.get("date", "")
            date_prefix = f"[{date}] " if date else ""
            combined += f"\n\n## {date_prefix}{title} ({src})\n{doc['content'][:80000]}"

        if len(combined) > MAX_TOTAL_CHARS:
            combined = combined[:MAX_TOTAL_CHARS]

        system = "你是一个专业的上市公司研究分析助手。请从多个文档中提取关键信息，以 JSON 格式返回结构化时间线条目。"

        user = f"""请分析以下 {len(selected)} 个文档，提取关键时间线条目。

实体: {entity}
主题: {topic}

要求：
1. 每个文档提取 1-3 条关键时间线条目
2. 条目按时间排序（最新优先）
3. 每条包含：日期、来源类型、标题、2-4 个要点
4. 跨文档的信息（如"Q1营收同比增长25%，与Q2订单增长呼应"）要特别标注

文档内容:
{combined}

请以 JSON 格式返回:
{{
    "timeline_entries": [
        {{
            "date": "<YYYY-MM-DD>",
            "source_type": "<来源类型>",
            "title": "<标题>",
            "points": ["<要点1>", "<要点2>"],
            "cross_doc": true  // 跨文档关联时为 true
        }}
    ]
}}

只返回 JSON，不要其他内容。"""

        response = self.chat_with_retry(user, system, max_tokens=8192)
        if response.success:
            parsed = self._parse_json_response(response.content)
            if parsed:
                return parsed.get("timeline_entries", [])

        return []

    # ── 业务方法: 查询 ──────────────────────────

    def answer_query(
        self, query: str, relevant_pages: List[Dict[str, str]], max_pages: int = 20
    ) -> str:
        """
        基于多个 wiki 页面内容综合回答查询（利用 1M 上下文，支持更多页面）。

        Args:
            query: 查询问题
            relevant_pages: 相关页面列表
            max_pages: 最多使用的页面数（默认 20，利用 1M 上下文）
        """
        context_parts = []
        for i, page in enumerate(relevant_pages[:max_pages]):
            content = page.get("content", "")
            # 每个页面取前 5000 字符（20 个页面约 10 万字符，加上 prompt 仍在 1M 范围内）
            context_parts.append(
                f"### 资料 {i + 1}: {page.get('title', '')} ({page.get('entity', '')})\n"
                f"{content[:5000]}"
            )

        context = "\n\n".join(context_parts)
        if len(context) > 800000:
            context = context[:800000]

        system = QUERY_ANSWER_SYSTEM_PROMPT
        user = build_query_answer_prompt(query, context)

        response = self.chat_with_retry(user, system, max_tokens=8192)
        return response.content if response.success else "无法生成答案 (LLM 不可用)"

    # ── 业务方法: 矛盾检测 ──────────────────────

    def detect_contradictions(
        self, page1_content: str, page2_content: str, entity: str = ""
    ) -> List[str]:
        """
        检测两个页面之间的矛盾
        """
        system = CONTRADICTION_DETECTION_SYSTEM_PROMPT
        user = build_contradiction_detection_prompt(
            page1_content, page2_content, entity
        )

        response = self.chat(user, system)
        if response.success:
            text = response.content.strip()
            if "未发现矛盾" in text or "没有矛盾" in text:
                return []
            lines = [l.strip().lstrip("- •").strip() for l in text.split("\n")]
            return [l for l in lines if l and len(l) > 5][:10]

        return []

    def detect_contradiction(
        self, old_claim: str, new_claim: str
    ) -> Optional[Dict[str, Any]]:
        """向后兼容: 检测两个声明之间的矛盾"""
        system = "你是一个数据一致性检查专家。"
        user = f"""请判断这两个声明是否矛盾。

旧声明: {old_claim}

新声明: {new_claim}

请以 JSON 格式输出:
{{
  "is_contradiction": true/false,
  "confidence": 0.0到1.0,
  "explanation": "解释"
}}"""

        response = self.chat(user, system, json_mode=True)
        if response.success:
            parsed = self._parse_json_response(response.content)
            if parsed:
                return parsed
        return None

    # ── 业务方法: 相关性判断 (向后兼容) ──────────

    def judge_relevance(self, text: str, questions: List[str]) -> List[Dict[str, Any]]:
        """向后兼容: 判断文本与问题的相关性"""
        questions_text = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(questions))

        user = f"""请判断以下文本是否回答了这些问题。

文本:
{text[:2000]}

问题:
{questions_text}

请以 JSON 格式输出:
[
  {{"question": "问题内容", "relevance": 0-1, "answer": "相关答案或null"}}
]"""

        response = self.chat(user, json_mode=True)
        if response.success:
            parsed = self._parse_json_response(response.content)
            if isinstance(parsed, list):
                return parsed
        return []

    # ── 业务方法: Lint ──────────────────────────

    def lint_page(
        self, page_content: str, all_pages_index: str = ""
    ) -> List[Dict[str, str]]:
        """
        LLM 驱动的 wiki 页面质量检查
        """
        system = LINT_PAGE_SYSTEM_PROMPT
        user = build_lint_page_prompt(page_content, all_pages_index)

        response = self.chat(user, system)
        if response.success:
            parsed = self._parse_json_response(response.content)
            if isinstance(parsed, list):
                return parsed
        return []

    # ── 工具方法 ────────────────────────────────

    def _parse_json_response(self, text: str) -> Optional[Any]:
        """从 LLM 响应中提取 JSON"""
        if not text:
            return None

        candidates = [text.strip()]

        # markdown 代码块
        json_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if json_match:
            candidates.append(json_match.group(1))

        # 裸 JSON
        for pattern in [r"\{.*\}", r"\[.*\]"]:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                candidates.append(match.group())

        for candidate in candidates:
            # 尝试直接解析
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

            # 清理乱码（U+FFFD replacement character）后重试
            if "\ufffd" in candidate:
                cleaned = candidate.replace("\ufffd", "?")
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    pass

            # 尝试修复常见的 JSON 格式错误：移除尾部逗号
            try:
                fixed = re.sub(r",(\s*[}\]])", r"\1", candidate)
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass

        return None

    def _fallback_analyze(self, content: str) -> Dict[str, Any]:
        """规则 fallback"""
        sentences = re.split(r"(?<=[。！？；\n])\s*", content[:2000])

        scored = []
        for s in sentences:
            if len(s) < 15:
                continue
            score = 0
            if re.search(r"\d+\.?\d*\s*(亿|万|%|元)", s):
                score += 3
            for w in ["发布", "推出", "宣布", "获得", "突破", "增长", "下跌", "亏损"]:
                if w in s:
                    score += 2
                    break
            if score > 0:
                scored.append((score, s))

        scored.sort(key=lambda x: x[0], reverse=True)

        positive = sum(
            1 for w in ["增长", "突破", "创新", "领先", "成功"] if w in content
        )
        negative = sum(
            1 for w in ["下降", "亏损", "延迟", "失败", "风险"] if w in content
        )

        return {
            "key_points": [s[1][:100] for s in scored[:3]],
            "entities_mentioned": [],
            "topics_affected": [],
            "sentiment": "positive"
            if positive > negative
            else ("negative" if negative > positive else "neutral"),
            "importance": 0.5,
            "suggested_questions": [],
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取调用统计（含成本）"""
        cost_stats = self.get_cost_stats()
        return {
            "total_calls": self._call_count,
            "provider": self.provider,
            "model": self.model,
            "available": self.available,
            "cost": cost_stats,
        }


# ── 便捷函数 ──────────────────────────────────

_default_client: Optional[LLMClient] = None


def get_llm_client(provider: str = None) -> LLMClient:
    """获取全局 LLM 客户端 (单例)"""
    global _default_client
    if _default_client is None or (provider and _default_client.provider != provider):
        _default_client = LLMClient(provider=provider)
    return _default_client


def summarize_text(text: str, max_points: int = 5) -> List[str]:
    """快速摘要"""
    return get_llm_client().summarize(text, max_points)


if __name__ == "__main__":

    print("=" * 50)
    print("  统一 LLM 客户端 — 测试")
    print("=" * 50)

    client = LLMClient()
    print(f"\n状态: {'可用' if client.available else '不可用 (API Key 未设置)'}")
    print(f"Provider: {client.provider}")
    print(f"Model: {client.model}")
    print(f"Base URL: {client.base_url}")

    if client.available:
        print("\n测试 generate()...")
        response = client.generate("请用一句话介绍你自己。", max_tokens=100)
        if response.success:
            print(f"  响应: {response.content[:200]}")
            print(f"  Tokens: {response.usage}")
        else:
            print(f"  失败: {response.error}")

        print("\n测试 summarize()...")
        summary = client.summarize(
            "中微公司2025年营收达到90亿元，同比增长25%。其中刻蚀设备收入占比超过60%。公司最新研发的CCP刻蚀设备已通过长存验证。",
            max_points=3,
        )
        for s in summary:
            print(f"  - {s}")

    print(f"\n统计: {client.get_stats()}")
