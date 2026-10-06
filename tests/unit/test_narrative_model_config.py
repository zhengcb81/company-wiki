"""Configured provider settings must reach the bounded model unchanged."""

import json

import pytest

from config import Config, LLMConfig
from company_wiki.automation.narrative_http_model import (
    NarrativeHTTPModel, model_options_from_config,
)
from support.narrative_model_request_fixture import selection as _selection
from company_wiki.automation.narrative_model import NarrativeModelRequest


@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_configured_batch_help_shows_provider_and_batch_options_without_loading_config(
    monkeypatch, capsys, flag,
):
    import narrative_batch_configured as wrapper

    def no_config(*_args, **_kwargs):
        pytest.fail("help must not load production configuration or credentials")

    monkeypatch.setattr(wrapper.Config, "load", no_config)
    with pytest.raises(SystemExit) as exit_info:
        wrapper.main([flag])
    assert exit_info.value.code == 0
    output = capsys.readouterr().out
    assert "--llm-provider" in output and "--llm-config" in output
    assert "--project-root" in output and "--request" in output


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


def test_configured_composition_preserves_explicit_transport_caps(tmp_path, monkeypatch):
    from company_wiki.automation import narrative_batch_cli as cli
    raw = {"schema_version": "narrative-batch-request/1", "run_id": "transport-fixture",
           "sources": [_selection().source_ref.to_dict()], "profile": "P1",
           "max_seconds": 30, "max_tokens": 60000, "max_cost_usd": "0.10",
           "pricing": {"version": "fixture", "input_micro_usd_per_million_tokens": 1,
                       "output_micro_usd_per_million_tokens": 1},
           "model": {"model_id": "stale", "max_output_tokens": 1, "thinking": "disabled",
                     "timeout_seconds": 4, "max_request_bytes": 3000, "max_response_bytes": 5000}}
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(raw), encoding="utf-8")
    before = request_path.read_bytes()
    captured = []

    def run(request, **_kwargs):
        captured.append(request)
        return {"status": "completed"}

    monkeypatch.setattr(cli, "run_batch", run)
    options = model_options_from_config(LLMConfig())
    args = ["--request", str(request_path)]
    for field in ("project-root", "catalog-config", "automation-db", "work-dir"):
        args += ["--" + field, str(tmp_path / field)]
    assert cli.main(args, loaded_model_options=options) == 0
    actual = captured[0].model_options
    assert all(actual[field] == value for field, value in options.items())
    for field in ("timeout_seconds", "max_request_bytes", "max_response_bytes"):
        assert actual[field] == raw["model"][field]
    assert "thinking" not in actual and request_path.read_bytes() == before


def test_provider_selection_uses_configured_fallback_without_mutating_primary(tmp_path, monkeypatch):
    monkeypatch.setenv("MIMO_API_KEY", "fixture-mimo-key")
    path = tmp_path / "config.yaml"
    path.write_text("llm:\n  provider: minimax\n  max_tokens: 8192\n"
                    "  temperature: 0.7\n  fallback:\n    provider: mimo\n"
                    "    model: configured-mimo\n    base_url: https://fallback.example/v1\n",
                    encoding="utf-8")
    config = Config.load(path)
    selected = config.llm_for_provider("mimo")
    assert (selected.provider, selected.model, selected.base_url) == (
        "mimo", "configured-mimo", "https://fallback.example/v1")
    assert selected.api_key == "fixture-mimo-key" and selected.api_key_env == "MIMO_API_KEY"
    assert (selected.max_tokens, selected.temperature) == (8192, 0.7)
    assert config.llm.provider == "minimax" and config.llm_for_provider(None) is config.llm
    assert "fixture-mimo-key" not in json.dumps(model_options_from_config(selected))


def test_deepseek_selection_reuses_loader_defaults_and_global_generation(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fixture-deepseek-key")
    path = tmp_path / "config.yaml"
    path.write_text("llm:\n  max_tokens: 8192\n  temperature: 0.6\n", encoding="utf-8")
    config = Config.load(path)
    selected = config.llm_for_provider("deepseek")
    defaults = Config._build_config({"llm": {"provider": "deepseek"}}, tmp_path).llm
    assert (selected.model, selected.base_url, selected.api_key_env) == (
        defaults.model, defaults.base_url, defaults.api_key_env)
    assert selected.api_key == "fixture-deepseek-key"
    assert selected.max_tokens == 8192 and selected.temperature == 0.6
    assert config.llm.provider == "minimax"


def test_provider_selection_respects_disabled_fallback_and_unknown_provider():
    config = Config()
    config.llm.fallback.enabled = False
    with pytest.raises(ValueError, match="disabled"):
        config.llm_for_provider("mimo")
    with pytest.raises(ValueError):
        config.llm_for_provider("misspelled-provider")


def test_explicit_provider_validates_selected_key_instead_of_primary(tmp_path, monkeypatch):
    import config as config_module
    monkeypatch.delenv("PYTEST_CURRENT_TEST")
    monkeypatch.setenv("MIMO_API_KEY", "fixture-mimo-key")
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.setenv("TAVILY_API_KEY", "fixture-search")
    monkeypatch.setenv("WIKI_ROOT", str(tmp_path))
    monkeypatch.setattr(config_module, "_dotenv_loaded", True)
    path = tmp_path / "config.yaml"
    path.write_text("llm:\n  provider: minimax\n", encoding="utf-8")
    before = path.read_bytes()
    config = Config.load(path, llm_provider="mimo")
    assert config.llm.provider == "mimo" and config.llm.api_key == "fixture-mimo-key"
    assert path.read_bytes() == before


@pytest.mark.parametrize("provider", ["mimo", "deepseek"])
def test_configured_entrypoint_selects_provider_through_authoritative_loader(monkeypatch, provider):
    import narrative_batch_configured as entrypoint
    captured = []
    loaded = []

    def load(path, *, llm_provider=None):
        loaded.append((path, llm_provider))
        config = Config()
        config.llm = config.llm_for_provider(llm_provider)
        return config

    def batch(args, *, loaded_model_options):
        captured.append((args, loaded_model_options))
        return 0

    monkeypatch.setattr(entrypoint.Config, "load", load)
    monkeypatch.setattr(entrypoint, "batch_main", batch)
    assert entrypoint.main(["--llm-provider", provider, "--request", "fixture.json"]) == 0
    assert loaded == [(None, provider)]
    assert captured[0][0] == ["--request", "fixture.json"]
    assert captured[0][1]["api_key_env"] == provider.upper() + "_API_KEY"
    assert captured[0][1]["max_output_tokens"] == 8192


@pytest.mark.parametrize("provider,expected", [
    ("mimo", "mimo-v2.6-flash"), ("deepseek", "deepseek-flash"),
])
def test_user_selected_flash_profiles_are_consistent_across_active_defaults(tmp_path, provider, expected):
    from llm_client import LLMClient
    selected = Config().llm_for_provider(provider)
    direct = Config._build_config({"llm": {"provider": provider}}, tmp_path).llm
    legacy_client = object.__new__(LLMClient)  # No SDK, key read or network.
    assert selected.model == direct.model == expected
    assert legacy_client._get_default_model(provider) == expected
    if provider == "mimo":
        from company_wiki.config import LLMFallbackConfig
        assert LLMFallbackConfig().model == expected


def test_production_yaml_requests_user_selected_mimo_flash():
    from pathlib import Path
    import yaml
    path = Path(__file__).resolve().parents[2] / "config.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert raw["llm"]["fallback"]["model"] == "mimo-v2.6-flash"


@pytest.mark.parametrize("environment_present", [True, False])
def test_deepseek_environment_key_wins_dotenv_which_is_only_a_fallback(
    tmp_path, monkeypatch, environment_present,
):
    import config as config_module
    monkeypatch.setattr(config_module, "WIKI_ROOT", tmp_path)
    monkeypatch.setattr(config_module, "_dotenv_loaded", False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST")
    monkeypatch.setenv("TAVILY_API_KEY", "fixture-search")
    monkeypatch.setenv("WIKI_ROOT", str(tmp_path))
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED", raising=False)
    if environment_present:
        monkeypatch.setenv("DEEPSEEK_API_KEY", "environment-fixture-key")
    else:
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    (tmp_path / "config.yaml").write_text("llm:\n  provider: minimax\n", encoding="utf-8")
    (tmp_path / ".env").write_text("DEEPSEEK_API_KEY=dotenv-fixture-key\n", encoding="utf-8")
    config = Config.load(llm_provider="deepseek")
    expected = "environment-fixture-key" if environment_present else "dotenv-fixture-key"
    assert config.llm.api_key == expected
    assert expected not in json.dumps(model_options_from_config(config.llm))
