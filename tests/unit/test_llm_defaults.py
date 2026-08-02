"""Provider/default/fallback contracts; no test may contact a real endpoint."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from config import Config, LLMConfig, LLMFallbackConfig
from company_wiki.config import LLMConfig as TypedLLMConfig
from llm_client import LLMClient


@pytest.mark.unit
def test_project_dotenv_is_authoritative_for_llm_keys(
    tmp_path: Path, monkeypatch
) -> None:
    import config as config_module

    (tmp_path / ".env").write_text(
        "MINIMAX_API_KEY=file-minimax\n"
        "MIMO_API_KEY=file-mimo\n"
        "DEEPSEEK_API_KEY=file-deepseek\n"
        "TAVILY_API_KEY=file-tavily\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config_module, "WIKI_ROOT", tmp_path)
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED", raising=False)
    monkeypatch.setenv("MINIMAX_API_KEY", "stale-minimax")
    monkeypatch.setenv("MIMO_API_KEY", "stale-mimo")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "stale-deepseek")
    monkeypatch.setenv("TAVILY_API_KEY", "inherited-tavily")

    config_module._load_dotenv()

    assert os.environ["MINIMAX_API_KEY"] == "file-minimax"
    assert os.environ["MIMO_API_KEY"] == "file-mimo"
    assert os.environ["DEEPSEEK_API_KEY"] == "file-deepseek"
    assert os.environ["TAVILY_API_KEY"] == "inherited-tavily"


@pytest.mark.unit
def test_primary_and_secondary_defaults_are_exact() -> None:
    llm = LLMConfig()

    assert llm.provider == "minimax"
    assert llm.model == "MiniMax-M3"
    assert llm.base_url == "https://api.minimaxi.com/v1"
    assert llm.api_key_env == "MINIMAX_API_KEY"
    assert llm.temperature == 1.0

    assert llm.fallback.provider == "mimo"
    assert llm.fallback.model == "mimo-v2.5-pro"
    assert llm.fallback.base_url == "https://token-plan-cn.xiaomimimo.com/v1"
    assert llm.fallback.api_key_env == "MIMO_API_KEY"
    assert llm.fallback.usage_scope == "general"


@pytest.mark.unit
def test_typed_package_config_uses_same_primary_default() -> None:
    llm = TypedLLMConfig()
    assert llm.provider == "minimax"
    assert llm.model == "MiniMax-M3"
    assert llm.base_url == "https://api.minimaxi.com/v1"
    assert llm.temperature == 1.0
    assert llm.fallback.usage_scope == "general"


@pytest.mark.unit
def test_llm_secrets_are_environment_only(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MINIMAX_API_KEY", "env-minimax-test")
    monkeypatch.setenv("MIMO_API_KEY", "env-mimo-test")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
llm:
  provider: minimax
  api_key: must-not-be-loaded
  fallback:
    provider: mimo
    api_key: must-not-be-loaded-either
""",
        encoding="utf-8",
    )

    config = Config.load(config_path)

    assert config.llm.api_key == "env-minimax-test"
    assert config.llm.fallback.api_key == "env-mimo-test"
    serialized = json.dumps(config.to_dict(), ensure_ascii=False)
    assert "env-minimax-test" not in serialized
    assert "env-mimo-test" not in serialized
    assert "must-not-be-loaded" not in serialized


@pytest.mark.unit
def test_mimo_fallback_is_available_for_research_after_owner_override(monkeypatch) -> None:
    monkeypatch.setenv("MINIMAX_API_KEY", "primary-test")
    monkeypatch.setenv("MIMO_API_KEY", "secondary-test")
    config = Config._build_config({}, Path.cwd())

    client = LLMClient(config=config, workload="research")

    assert client.provider == "minimax"
    assert client.fallback_client is not None
    assert client.fallback_client.provider == "mimo"
    assert client.fallback_client.model == "mimo-v2.5-pro"
    assert client.fallback_status == "ready"


@pytest.mark.unit
def test_coding_only_scope_cannot_be_restored_silently() -> None:
    config = Config(
        llm=LLMConfig(fallback=LLMFallbackConfig(usage_scope="coding_only"))
    )

    with pytest.raises(ValueError, match="usage_scope"):
        config.validate(strict=False)


@pytest.mark.unit
def test_mimo_token_plan_can_only_be_selected_for_coding(monkeypatch) -> None:
    monkeypatch.setenv("MINIMAX_API_KEY", "primary-test")
    monkeypatch.setenv("MIMO_API_KEY", "secondary-test")
    config = Config._build_config({}, Path.cwd())

    client = LLMClient(config=config, workload="coding")

    assert client.fallback_client is not None
    assert client.fallback_client.provider == "mimo"
    assert client.fallback_client.model == "mimo-v2.5-pro"


@pytest.mark.unit
@pytest.mark.parametrize("provider", ["minimax", "mimo"])
def test_modern_openai_compatible_providers_use_max_completion_tokens(provider: str) -> None:
    client = LLMClient(provider=provider, api_key="test-only")
    sdk = MagicMock()
    choice = MagicMock()
    choice.message.content = "ok"
    choice.message.reasoning_content = ""
    choice.finish_reason = "stop"
    response = MagicMock(choices=[choice], usage=None)
    sdk.chat.completions.create.return_value = response
    client._sdk_client = sdk

    result = client.chat("test", max_tokens=123)

    assert result.success
    kwargs = sdk.chat.completions.create.call_args.kwargs
    assert kwargs["max_completion_tokens"] == 123
    assert "max_tokens" not in kwargs
