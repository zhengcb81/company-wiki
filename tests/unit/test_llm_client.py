"""
LLMClient 测试
测试 llm_client.py 的核心功能: 初始化、chat 调用、业务方法
所有 LLM API 调用使用 mock，不依赖外部服务。
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from llm_client import LLMClient, LLMResponse


def _make_response(content="测试回复", model="test-model", success=True):
    """创建测试用 LLMResponse"""
    return LLMResponse(
        content=content,
        model=model,
        usage={"prompt_tokens": 10, "completion_tokens": 5},
        success=success,
    )


@pytest.mark.unit
class TestLLMClientInit:

    def test_init_with_explicit_params(self):
        """测试显式参数初始化"""
        client = LLMClient(
            provider="deepseek",
            api_key="sk-test",
            model="test-model",
            base_url="https://api.test.com"
        )
        assert client.provider == "deepseek"
        assert client.api_key == "sk-test"
        assert client.model == "test-model"
        assert client.base_url == "https://api.test.com"

    def test_init_with_openai_provider(self):
        """测试 OpenAI provider 初始化"""
        client = LLMClient(
            provider="openai",
            api_key="sk-openai-test",
            model="gpt-4",
            base_url="https://api.openai.com/v1"
        )
        assert client.provider == "openai"
        assert client.model == "gpt-4"

    def test_init_default_values(self):
        """测试默认参数"""
        client = LLMClient(
            provider="deepseek",
            api_key="sk-test",
        )
        assert client._max_tokens > 0
        assert 0 <= client._temperature <= 1
        assert client._max_retries > 0

    def test_available_with_api_key(self):
        """测试有 API key 时 available 为 True"""
        client = LLMClient(provider="deepseek", api_key="sk-test")
        assert client.available

    def test_unavailable_without_api_key(self):
        """测试无 API key 时 available 为 False"""
        client = LLMClient(provider="deepseek", api_key="")
        assert not client.available


@pytest.mark.unit
class TestLLMClientChat:

    @patch.object(LLMClient, '_call_with_urllib')
    def test_chat_returns_response(self, mock_call):
        """测试 chat 返回 LLMResponse"""
        mock_call.return_value = _make_response("你好世界")
        client = LLMClient(provider="deepseek", api_key="sk-test")
        # 不初始化 SDK，走 urllib 路径
        client._sdk_client = None
        result = client.chat("你好")
        assert isinstance(result, LLMResponse)
        assert result.content == "你好世界"

    @patch.object(LLMClient, '_call_with_urllib')
    def test_chat_with_system_prompt(self, mock_call):
        """测试带 system prompt 的调用"""
        mock_call.return_value = _make_response("ok")
        client = LLMClient(provider="deepseek", api_key="sk-test")
        client._sdk_client = None
        result = client.chat("分析文本", system="你是分析师")
        assert result.content == "ok"

    @patch.object(LLMClient, 'chat')
    def test_chat_with_retry_success(self, mock_chat):
        """测试重试成功"""
        mock_chat.return_value = _make_response("ok")
        client = LLMClient(provider="deepseek", api_key="sk-test")
        result = client.chat_with_retry("测试")
        assert result.success

    @patch.object(LLMClient, 'chat')
    def test_generate_backward_compat(self, mock_chat):
        """测试 generate() 返回 LLMResponse"""
        mock_chat.return_value = _make_response("分析结果")
        client = LLMClient(provider="deepseek", api_key="sk-test")
        result = client.generate("分析这段文本")
        assert isinstance(result, LLMResponse)
        assert result.content == "分析结果"

    def test_chat_unavailable_returns_error(self):
        """测试无 API key 时返回错误"""
        client = LLMClient(provider="deepseek", api_key="")
        result = client.chat("test")
        assert not result.success
        assert "API Key" in result.error


@pytest.mark.unit
class TestLLMClientBusinessMethods:

    @patch.object(LLMClient, 'chat')
    def test_analyze_content(self, mock_chat):
        """测试内容分析"""
        mock_chat.return_value = _make_response(
            '{"key_points": ["要点1"], "entities_mentioned": ["中微公司"], '
            '"topics_affected": ["刻蚀"], "sentiment": "positive", '
            '"importance": 7, "suggested_questions": []}'
        )
        client = LLMClient(provider="deepseek", api_key="sk-test")
        result = client.analyze_content("测试内容", entity_name="测试公司")
        assert isinstance(result, dict)

    @patch.object(LLMClient, 'chat')
    def test_generate_summary(self, mock_chat):
        """测试摘要生成"""
        mock_chat.return_value = _make_response("这是摘要")
        client = LLMClient(provider="deepseek", api_key="sk-test")
        result = client.generate_summary("测试内容", topic="公司动态")
        assert isinstance(result, str)
        assert len(result) > 0

    @patch.object(LLMClient, 'chat')
    def test_generate_wikilinks(self, mock_chat):
        """测试 wikilinks 生成"""
        mock_chat.return_value = _make_response('["中微公司", "半导体设备"]')
        client = LLMClient(provider="deepseek", api_key="sk-test")
        result = client.generate_wikilinks("测试内容", available_pages=["中微公司", "北方华创"])
        assert isinstance(result, list)

    @patch.object(LLMClient, 'chat')
    def test_judge_relevance(self, mock_chat):
        """测试相关性判断"""
        mock_chat.return_value = _make_response(
            '[{"question": "刻蚀", "relevance": 0.8, "answer": "相关"}]'
        )
        client = LLMClient(provider="deepseek", api_key="sk-test")
        result = client.judge_relevance("中微公司刻蚀设备突破", ["刻蚀"])
        assert isinstance(result, list)


@pytest.mark.unit
class TestLLMResponse:

    def test_response_creation(self):
        """测试 LLMResponse 创建"""
        resp = LLMResponse(
            content="测试",
            model="test-model",
            usage={"prompt_tokens": 10, "completion_tokens": 5}
        )
        assert resp.content == "测试"
        assert resp.model == "test-model"
        assert resp.success

    def test_response_default_content(self):
        """测试 LLMResponse 默认值"""
        resp = LLMResponse()
        assert resp.content == ""
        assert resp.model == ""
        assert resp.success

    def test_response_tokens_used(self):
        """测试 tokens_used 属性"""
        resp = LLMResponse(usage={"total_tokens": 42})
        assert resp.tokens_used == 42

    def test_response_no_usage(self):
        """测试无 usage 时 tokens_used 为 0"""
        resp = LLMResponse()
        assert resp.tokens_used == 0
