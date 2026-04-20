#!/usr/bin/env python3
"""
llm_client.py — 统一 LLM 客户端模块

为整个知识库系统提供统一的 LLM 调用接口:
- 支持多 provider (DeepSeek/OpenAI/Anthropic)
- 统一的重试/限流/错误处理
- 封装常用业务 prompt (分析/摘要/矛盾检测/wikilink/评估/查询/lint)
- 始终有 fallback
- 兼容已有调用方 (generate/summarize/judge_relevance/detect_contradiction)

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

import json
import os
import re
import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str = ""
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
    ):
        """
        初始化 LLM 客户端

        优先级: 显式参数 > config 对象 > config.yaml > 环境变量 > 默认值

        Args:
            provider: LLM 提供商 (deepseek/openai/claude)
            api_key: API Key
            model: 模型名称
            base_url: API 基础 URL
            config: Config 对象 (from config.py)
        """
        self._sdk_client = None
        self._last_call_time = 0.0
        self._call_count = 0

        # 尝试从 config 对象加载
        if config is None and provider is None:
            try:
                from config import Config
                config = Config.load()
            except Exception:
                config = None

        # 从 config 对象提取参数
        if config and hasattr(config, 'llm'):
            self.provider = provider or config.llm.provider
            self.api_key = api_key or config.llm.api_key
            self.model = model or config.llm.model
            self.base_url = base_url or config.llm.base_url
            self._max_tokens = config.llm.max_tokens
            self._temperature = config.llm.temperature
        else:
            self.provider = provider or self._detect_provider()
            self.api_key = api_key or self._get_api_key(self.provider)
            self.model = model or self._get_default_model(self.provider)
            self.base_url = base_url or self._get_base_url(self.provider)
            self._max_tokens = 1024
            self._temperature = 0.3

        # 限流和重试配置
        self._min_interval = 1.0
        self._max_retries = 3
        self._timeout = 60
        self._backoff_base = 2

        # 初始化底层客户端
        self._init_sdk_client()

    def _detect_provider(self) -> str:
        """根据环境变量检测 provider"""
        if os.getenv("DEEPSEEK_API_KEY"):
            return "deepseek"
        if os.getenv("OPENAI_API_KEY"):
            return "openai"
        if os.getenv("ANTHROPIC_API_KEY"):
            return "claude"
        return "deepseek"

    def _get_api_key(self, provider: str) -> str:
        """获取 API Key"""
        env_vars = {
            "deepseek": "DEEPSEEK_API_KEY",
            "openai": "OPENAI_API_KEY",
            "claude": "ANTHROPIC_API_KEY",
        }
        return os.getenv(env_vars.get(provider, ""), "")

    def _get_default_model(self, provider: str) -> str:
        """获取默认模型"""
        models = {
            "deepseek": "deepseek-reasoner",
            "openai": "gpt-4",
            "claude": "claude-3-opus-20240229",
        }
        return models.get(provider, "deepseek-reasoner")

    def _get_base_url(self, provider: str) -> str:
        """获取基础 URL"""
        urls = {
            "deepseek": "https://api.deepseek.com",
            "openai": "https://api.openai.com/v1",
            "claude": "https://api.anthropic.com",
        }
        return urls.get(provider, "https://api.deepseek.com")

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

    def chat(self, user: str, system: str = "", json_mode: bool = False) -> LLMResponse:
        """
        基础聊天调用

        Args:
            user: 用户消息
            system: 系统消息
            json_mode: 是否要求 JSON 格式响应

        Returns:
            LLMResponse 对象
        """
        if not self.available:
            return LLMResponse(success=False, error="LLM API Key 未配置")

        self._rate_limit()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})

        if self.provider == "claude":
            return self._call_claude(messages, json_mode)

        # DeepSeek / OpenAI 都用 OpenAI 兼容 API
        if self._sdk_client is not None:
            return self._call_with_sdk(messages, json_mode)
        else:
            return self._call_with_urllib(messages, json_mode)

    def chat_with_retry(self, user: str, system: str = "", max_retries: int = None) -> LLMResponse:
        """带重试的聊天调用"""
        if max_retries is None:
            max_retries = self._max_retries

        last_error = ""
        for attempt in range(max_retries):
            response = self.chat(user, system)
            if response.success:
                return response

            last_error = response.error
            if attempt < max_retries - 1:
                wait = self._backoff_base ** attempt
                logger.warning(f"LLM 失败 ({attempt+1}/{max_retries}), {wait}s 后重试: {last_error}")
                time.sleep(wait)

        return LLMResponse(success=False, error=f"重试 {max_retries} 次后仍失败: {last_error}")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = None,
        temperature: float = None,
    ) -> LLMResponse:
        """
        生成文本 (向后兼容接口)

        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            max_tokens: 最大 token 数 (覆盖默认值)
            temperature: 温度 (覆盖默认值)

        Returns:
            LLMResponse 对象
        """
        # 临时覆盖参数
        orig_max_tokens = self._max_tokens
        orig_temperature = self._temperature

        if max_tokens is not None:
            self._max_tokens = max_tokens
        if temperature is not None:
            self._temperature = temperature

        try:
            return self.chat_with_retry(prompt, system_prompt or "")
        finally:
            self._max_tokens = orig_max_tokens
            self._temperature = orig_temperature

    # ── 底层调用实现 ──────────────────────────

    def _call_with_sdk(self, messages: list, json_mode: bool) -> LLMResponse:
        """使用 OpenAI SDK 调用"""
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self._max_tokens,
                "temperature": self._temperature,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = self._sdk_client.chat.completions.create(**kwargs)

            choice = response.choices[0]
            content = choice.message.content or ""
            reasoning = getattr(choice.message, 'reasoning_content', '') or ""

            usage = {}
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            self._call_count += 1
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

    def _call_with_urllib(self, messages: list, json_mode: bool) -> LLMResponse:
        """使用 urllib 直接调用"""
        import urllib.request
        import urllib.error

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
        }
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

    def _call_claude(self, messages: list, json_mode: bool) -> LLMResponse:
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
            "max_tokens": self._max_tokens,
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

    # ── 业务方法: 内容分析 ──────────────────────

    def analyze_content(self, content: str, entity_name: str = "") -> Dict[str, Any]:
        """
        分析内容, 提取关键信息

        Returns:
            {"key_points", "entities_mentioned", "topics_affected",
             "sentiment", "importance", "suggested_questions"}
        """
        content_preview = content[:3000] if len(content) > 3000 else content

        system = "你是一个专业的上市公司研究分析助手。请准确提取关键信息, 以 JSON 格式返回。"
        user = f"""请分析以下文档内容，提取关键信息。

{f'相关实体: {entity_name}' if entity_name else ''}

内容:
{content_preview}

请以 JSON 格式返回:
{{
    "key_points": ["要点1", "要点2", "要点3"],
    "entities_mentioned": ["提及的公司/行业/主题"],
    "topics_affected": ["影响的主题"],
    "sentiment": "positive/negative/neutral",
    "importance": 0.0到1.0之间的数值,
    "suggested_questions": ["这份文档可能回答的研究问题"]
}}

只返回 JSON，不要其他内容。"""

        response = self.chat_with_retry(user, system)
        if response.success:
            parsed = self._parse_json_response(response.content)
            if parsed:
                return parsed

        return self._fallback_analyze(content)

    # ── 业务方法: 摘要生成 ──────────────────────

    def generate_summary(self, content: str, topic: str = "", entity: str = "") -> str:
        """
        生成精炼摘要 (返回 "- 要点" 格式)
        """
        content_truncated = content[:2000] if len(content) > 2000 else content

        system = (
            "你是一个专业的金融分析师助手，负责将新闻内容提炼为简洁的要点摘要。\n"
            "要求：\n"
            "1. 输出 2-5 个关键要点，每条一行\n"
            "2. 每条要点以动词或名词开头\n"
            "3. 包含具体数字、日期、金额等关键数据\n"
            "4. 指出事件的意义或影响\n"
            "5. 直接输出要点列表，不要输出标题或解释"
        )

        user_parts = []
        if entity:
            user_parts.append(f"公司/实体：{entity}")
        if topic:
            user_parts.append(f"所属主题：{topic}")
        user_parts.append(f"\n原始内容：\n{content_truncated}")
        user_parts.append("\n请输出 2-5 个关键要点：")
        user = "\n".join(user_parts)

        response = self.chat_with_retry(user, system)
        if response.success and response.content.strip():
            lines = response.content.strip().split('\n')
            clean_lines = []
            for line in lines:
                line = line.strip()
                line = re.sub(r'^\d+[\.\)、]\s*', '', line)
                line = re.sub(r'^[-*•]\s*', '- ', line)
                if line and not line.startswith('- '):
                    line = f"- {line}"
                if line:
                    clean_lines.append(line)
            return '\n'.join(clean_lines)

        # Fallback
        sentences = re.split(r'(?<=[。！？；])\s*', content_truncated)
        fallback = [f"- {s.strip()}" for s in sentences[:3] if len(s.strip()) > 10]
        return '\n'.join(fallback) if fallback else "- 内容已处理"

    def summarize(self, text: str, max_points: int = 5) -> List[str]:
        """向后兼容: 使用 LLM 生成摘要 (返回字符串列表)"""
        content = self.generate_summary(text)
        # 去掉 "- " 前缀返回纯文本列表
        return [l[2:].strip() for l in content.split('\n') if l.strip().startswith('- ')][:max_points]

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

    def synthesize_assessment(self, timeline_entries: List[str],
                              topic: str = "", entity: str = "",
                              core_questions: List[str] = None) -> str:
        """
        基于时间线条目生成综合评估
        """
        combined = '\n'.join(timeline_entries[:20])
        if len(combined) > 4000:
            combined = combined[:4000]

        questions_text = ""
        if core_questions:
            questions_text = "\n\n核心追踪问题:\n" + "\n".join(f"- {q}" for q in core_questions)

        system = "你是一个资深上市公司研究分析师，擅长从多条信息中提炼趋势、判断方向、发现风险。"

        user = f"""请基于以下时间线条目，为 {entity} 的「{topic}」主题生成一段综合评估。

要求:
1. 100-300 字的段落
2. 总结关键趋势和变化
3. 给出核心判断和前瞻
4. 如有风险要点也要提及
5. 用引用块格式 (>) 输出

实体: {entity}
主题: {topic}{questions_text}

时间线条目:
{combined}

请直接输出综合评估 (以 > 开头的引用块格式):"""

        response = self.chat_with_retry(user, system)
        if response.success and response.content.strip():
            text = response.content.strip()
            if not text.startswith('>'):
                text = '> ' + text.replace('\n', '\n> ')
            return text

        return "> 待积累数据后补充。"

    def generate_core_questions(self, entity: str, sector: str = "",
                                 position: str = "", existing_data: str = "",
                                 question_templates: List[str] = None) -> List[str]:
        """
        为实体生成核心追踪问题。

        Args:
            question_templates: 行业级问题模板（从 graph.yaml 加载），
                               用于锚定 LLM 的研究方向，避免产出通用废话。
        """
        system = "你是一个上市公司研究框架设计专家。"

        # 构建问题模板锚定段
        template_section = ""
        if question_templates:
            template_section = f"""
研究框架参考（请基于以下行业级问题框架，针对{entity}的具体情况做个性化适配）:
{chr(10).join(f'- {t}' for t in question_templates)}
"""

        user = f"""请为以下实体设计 3-5 个核心研究追踪问题。

实体: {entity}
{f'所属行业: {sector}' if sector else ''}
{f'定位: {position}' if position else ''}
{template_section}
{f'已有数据概况: {existing_data[:500]}' if existing_data else ''}

要求:
1. 问题要具体、可追踪、有信息增量
2. 必须结合{entity}的实际情况，不要产出适用于任何公司的通用问题
3. 不要出现"核心竞争优势是什么""主要增长驱动力在哪里"这类泛泛的问题
4. 每个问题一行, 不要编号

请直接输出问题列表:"""

        response = self.chat_with_retry(user, system)
        if response.success and response.content.strip():
            lines = [l.strip().lstrip('- •').strip() for l in response.content.strip().split('\n')]
            return [l for l in lines if l and len(l) > 5][:5]

        # LLM 不可用时，如果有模板就使用模板，否则返回空
        if question_templates:
            return question_templates[:5]
        return []

    # ── 业务方法: 查询 ──────────────────────────

    def answer_query(self, query: str, relevant_pages: List[Dict[str, str]]) -> str:
        """
        基于多个 wiki 页面内容综合回答查询
        """
        context_parts = []
        for i, page in enumerate(relevant_pages[:5]):
            context_parts.append(
                f"### 资料 {i+1}: {page.get('title', '')} ({page.get('entity', '')})\n"
                f"{page.get('content', '')[:2000]}"
            )

        context = '\n\n'.join(context_parts)
        if len(context) > 6000:
            context = context[:6000]

        system = "你是一个上市公司研究知识库的智能助手。基于提供的知识库内容准确回答问题。"
        user = f"""请基于以下知识库内容回答问题。

问题: {query}

知识库内容:
{context}

请给出详细、准确的回答:"""

        response = self.chat_with_retry(user, system)
        return response.content if response.success else "无法生成答案 (LLM 不可用)"

    # ── 业务方法: 矛盾检测 ──────────────────────

    def detect_contradictions(self, page1_content: str, page2_content: str,
                               entity: str = "") -> List[str]:
        """
        检测两个页面之间的矛盾
        """
        system = "你是一个数据一致性检查专家。请仔细对比两段文本, 找出矛盾。"

        user = f"""请对比以下两段关于 {entity if entity else '某个实体'} 的文本，找出矛盾。

文本 A:
{page1_content[:2000]}

文本 B:
{page2_content[:2000]}

请列出所有矛盾, 每个矛盾一行。如果没有矛盾, 输出"未发现矛盾"。只输出矛盾列表:"""

        response = self.chat(user, system)
        if response.success:
            text = response.content.strip()
            if "未发现矛盾" in text or "没有矛盾" in text:
                return []
            lines = [l.strip().lstrip('- •').strip() for l in text.split('\n')]
            return [l for l in lines if l and len(l) > 5][:10]

        return []

    def detect_contradiction(self, old_claim: str, new_claim: str) -> Optional[Dict[str, Any]]:
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
        questions_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))

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

    def lint_page(self, page_content: str, all_pages_index: str = "") -> List[Dict[str, str]]:
        """
        LLM 驱动的 wiki 页面质量检查
        """
        system = "你是一个知识库质量审查专家。请检查 wiki 页面质量。"

        user = f"""请检查以下 wiki 页面的质量，找出问题:

1. 过时的结论或数据
2. 提及了但未链接的概念/公司 (应该有 wikilink 的地方)
3. 信息缺失或不够深入的地方
4. 格式问题

页面内容:
{page_content[:3000]}

{f'知识库其他页面: {all_pages_index[:500]}' if all_pages_index else ''}

请以 JSON 格式返回问题列表:
[
    {{"type": "stale", "description": "...", "suggestion": "..."}},
    {{"type": "missing_link", "description": "...", "suggestion": "..."}},
    {{"type": "content_gap", "description": "...", "suggestion": "..."}}
]

如果没有问题, 返回 []。只返回 JSON:"""

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

        # 直接解析
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        # markdown 代码块
        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 裸 JSON
        for pattern in [r'\{.*\}', r'\[.*\]']:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass

        return None

    def _fallback_analyze(self, content: str) -> Dict[str, Any]:
        """规则 fallback"""
        sentences = re.split(r'(?<=[。！？；\n])\s*', content[:2000])

        scored = []
        for s in sentences:
            if len(s) < 15:
                continue
            score = 0
            if re.search(r'\d+\.?\d*\s*(亿|万|%|元)', s):
                score += 3
            for w in ['发布', '推出', '宣布', '获得', '突破', '增长', '下跌', '亏损']:
                if w in s:
                    score += 2
                    break
            if score > 0:
                scored.append((score, s))

        scored.sort(key=lambda x: x[0], reverse=True)

        positive = sum(1 for w in ['增长', '突破', '创新', '领先', '成功'] if w in content)
        negative = sum(1 for w in ['下降', '亏损', '延迟', '失败', '风险'] if w in content)

        return {
            "key_points": [s[1][:100] for s in scored[:3]],
            "entities_mentioned": [],
            "topics_affected": [],
            "sentiment": "positive" if positive > negative else ("negative" if negative > positive else "neutral"),
            "importance": 0.5,
            "suggested_questions": [],
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取调用统计"""
        return {
            "total_calls": self._call_count,
            "provider": self.provider,
            "model": self.model,
            "available": self.available,
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
    import sys

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
        summary = client.summarize("中微公司2025年营收达到90亿元，同比增长25%。其中刻蚀设备收入占比超过60%。公司最新研发的CCP刻蚀设备已通过长存验证。", max_points=3)
        for s in summary:
            print(f"  - {s}")

    print(f"\n统计: {client.get_stats()}")
