"""Configured provider settings must reach the bounded model unchanged."""

import json

import pytest

from config import Config, LLMConfig
from company_wiki.automation.narrative_http_model import (
    NarrativeHTTPModel, model_options_from_config,
)
from support.narrative_model_request_fixture import selection as _selection
from company_wiki.automation.narrative_model import NarrativeModelRequest


@pytest.mark.parametrize("provider,token_field", [
    ("minimax", "max_completion_tokens"), ("mimo", "max_completion_tokens"),
    ("deepseek", "max_tokens"), ("openai", "max_tokens"),
])
def test_existing_loader_settings_reach_exact_http_body(tmp_path, monkeypatch, provider, token_field):
    monkeypatch.setenv("MINIMAX_API_KEY", "fixture-secret-only")
    path = tmp_path / "config.yaml"
    path.write_text(f"llm:\n  provider: {provider}\n  model: configured-model\n"
                    "  base_url: https://configured.example/v1/\n"
                    "  max_tokens: 8192\n  temperature: 0.7\n  reasoning_split: true\n",
                    encoding="utf-8")
    config = Config.load(path)
    options = model_options_from_config(config.llm)
    assert options["model_id"] == "configured-model"
    assert options["endpoint"] == "https://configured.example/v1/chat/completions"
    assert options["api_key_env"] == config.llm.api_key_env
    assert options["max_output_tokens"] == 8192
    assert "fixture-secret-only" not in json.dumps(options)
    assert "thinking" not in options  # Configuration never requested disabling it.
    body = json.loads(NarrativeHTTPModel(**options).request_bytes(
        NarrativeModelRequest.from_selection(_selection())))
    assert body["model"] == config.llm.model and body[token_field] == config.llm.max_tokens
    assert ({"max_tokens", "max_completion_tokens"} & body.keys()) == {token_field}
    assert body["temperature"] == config.llm.temperature
    assert body.get("reasoning_split") is (True if provider == "minimax" else None)


def test_default_loader_keeps_project_dotenv_authoritative(tmp_path, monkeypatch):
    import config as config_module
    monkeypatch.setattr(config_module, "WIKI_ROOT", tmp_path)
    monkeypatch.setattr(config_module, "_dotenv_loaded", False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST")
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED", raising=False)
    monkeypatch.setenv("MINIMAX_API_KEY", "inherited-stale-fixture")
    monkeypatch.setenv("TAVILY_API_KEY", "fixture-search")
    monkeypatch.setenv("WIKI_ROOT", str(tmp_path))
    (tmp_path / "config.yaml").write_text("llm:\n  provider: minimax\n", encoding="utf-8")
    (tmp_path / ".env").write_text("MINIMAX_API_KEY=project-fixture-key\n", encoding="utf-8")
    config = Config.load()
    assert config.llm.api_key == "project-fixture-key"
    options = model_options_from_config(config.llm)
    assert options["endpoint"] == config.llm.base_url.rstrip("/") + "/chat/completions"
    assert options["max_output_tokens"] == config.llm.max_tokens == 8192
    assert "project-fixture-key" not in json.dumps(options)


def test_adapter_does_not_switch_an_incompatible_configured_provider():
    with pytest.raises(ValueError, match="OpenAI-compatible"):
        model_options_from_config(LLMConfig(provider="claude"))


def test_disabled_reasoning_split_keeps_existing_client_omission_policy():
    options = model_options_from_config(LLMConfig(reasoning_split=False))
    body = json.loads(NarrativeHTTPModel(**options).request_bytes(
        NarrativeModelRequest.from_selection(_selection())))
    assert "reasoning_split" not in body
    assert "thinking" not in body


@pytest.mark.parametrize("options", [
    {"temperature": True}, {"temperature": float("nan")}, {"temperature": 3},
    {"reasoning_split": "false"}, {"output_token_field": "unbounded"},
])
def test_invalid_generation_options_are_rejected_before_http(options):
    with pytest.raises(ValueError):
        NarrativeHTTPModel(model_id="fixture", endpoint="https://fixture.invalid/chat/completions",
                           api_key_env="UNUSED", **options)


def test_configuration_identity_includes_real_generation_parameters():
    from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
    raw = {"schema_version": "narrative-batch-request/1", "run_id": "config-fixture",
           "sources": [_selection().source_ref.to_dict()], "profile": "P1",
           "max_seconds": 30, "max_tokens": 60000, "max_cost_usd": "0.10",
           "pricing": {"version": "fixture", "input_micro_usd_per_million_tokens": 1,
                       "output_micro_usd_per_million_tokens": 1}}
    raw["model"] = model_options_from_config(LLMConfig())
    original = NarrativeBatchRequest.from_dict(raw)
    assert NarrativeBatchRequest.from_dict(original.to_dict()).input_hash == original.input_hash
    for field, value in (("temperature", 0.5), ("reasoning_split", False),
                         ("output_token_field", "max_tokens")):
        raw["model"] = {**original.model_options, field: value}
        assert NarrativeBatchRequest.from_dict(raw).input_hash != original.input_hash
