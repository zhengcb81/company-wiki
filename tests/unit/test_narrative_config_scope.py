"""Narrative configuration validates the component actually being executed."""
from __future__ import annotations

import json

import pytest
import yaml

from config import Config
import narrative_batch_configured as wrapper


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    for name in ("PYTEST_CURRENT_TEST", "WIKI_ROOT", "TAVILY_API_KEY", "MINIMAX_API_KEY",
                 "MIMO_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "scope-fixture-no-real-key")
    path = tmp_path / "llm.yaml"
    raw = {"llm": {"provider": "deepseek", "model": "configured-flash", "base_url": "https://configured.example/v1",
                   "temperature": 1, "max_tokens": 8192,
                   "generation_policy": {"deepseek": {"narrative": {"thinking": "disabled"}}}},
           "paths": {"wiki_root": str(tmp_path / "deliberately-absent-legacy-wiki")}}

    def write(value=None):
        path.write_text(yaml.safe_dump(raw if value is None else value), encoding="utf8")
        return path

    write()
    return path, raw, write


@pytest.mark.parametrize("test_environment", [False, True])
def test_llm_only_does_not_require_search_or_legacy_wiki(isolated_config, monkeypatch, test_environment):
    path, _, _ = isolated_config
    before = path.read_bytes()
    if test_environment:
        monkeypatch.setenv("PYTEST_CURRENT_TEST", "explicit-determinism-control")
    else:
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    config = Config.load(path, validation_scope="llm")
    assert config.llm.model == "configured-flash"
    assert config.llm.generation_options("narrative") == {"thinking": {"type": "disabled"}}
    assert path.read_bytes() == before


@pytest.mark.parametrize("section,value", [("search", None), ("search", ["unrelated"]),
    ("schedule", 42), ("report_downloader", "unrelated"), ("paths", ["unrelated"])])
def test_llm_only_does_not_construct_unconsumed_sections(isolated_config, section, value):
    path, raw, write = isolated_config
    raw[section] = value
    write()
    assert Config.load(path, validation_scope="llm").llm.model == "configured-flash"


@pytest.mark.parametrize("environment,section", [("TAVILY_API_KEY", "search"), ("WIKI_ROOT", "paths")])
def test_unconsumed_environment_cannot_force_unrelated_section_construction(
    isolated_config, monkeypatch, environment, section,
):
    path, raw, write = isolated_config
    raw[section] = None
    write()
    monkeypatch.setenv(environment, "unused-component-fixture")
    assert Config.load(path, validation_scope="llm").llm.model == "configured-flash"


@pytest.mark.parametrize("unused", [None, ["unused"], "unused"])
def test_unselected_fallback_is_not_constructed(isolated_config, unused):
    path, raw, write = isolated_config
    raw["llm"]["fallback"] = unused
    write()
    assert Config.load(path, validation_scope="llm").llm.model == "configured-flash"


@pytest.mark.parametrize("enabled", [True, False])
def test_explicit_fallback_keeps_configured_profile_and_enabled_policy(
    isolated_config, monkeypatch, enabled,
):
    path, raw, write = isolated_config
    raw["llm"]["fallback"] = {"provider": "mimo", "model": "configured-fallback-model",
                               "base_url": "https://configured-fallback.example/v1", "enabled": enabled}
    monkeypatch.setenv("MIMO_API_KEY", "fallback-fixture-no-real-key")
    write()
    if not enabled:
        with pytest.raises(ValueError, match="disabled"):
            Config.load(path, llm_provider="mimo", validation_scope="llm")
        return
    selected = Config.load(path, llm_provider="mimo", validation_scope="llm").llm
    assert selected.model == "configured-fallback-model"
    assert selected.base_url == "https://configured-fallback.example/v1"
    assert selected.api_key_env == "MIMO_API_KEY"
    assert selected.api_key == "fallback-fixture-no-real-key"
    assert selected.max_tokens == 8192 and selected.temperature == 1


def test_explicit_independent_provider_does_not_rebuild_full_config(isolated_config, monkeypatch):
    path, _, _ = isolated_config
    monkeypatch.setenv("OPENAI_API_KEY", "independent-profile-fixture")
    scopes = []
    original = Config._build_config

    def build(raw, base_dir, *, llm_only=False, llm_provider=None):
        scopes.append(llm_only)
        return original(raw, base_dir, llm_only=llm_only, llm_provider=llm_provider)

    monkeypatch.setattr(Config, "_build_config", staticmethod(build))
    config = Config.load(path, llm_provider="openai", validation_scope="llm")
    assert config.llm.provider == "openai" and config.llm.api_key_env == "OPENAI_API_KEY"
    assert config.llm.max_tokens == 8192 and config.llm.temperature == 1
    assert scopes == [True]


def test_full_configuration_still_checks_search_and_legacy_path(isolated_config, monkeypatch):
    path, _, _ = isolated_config
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    with pytest.raises(ValueError) as error:
        Config.load(path)
    assert "TAVILY_API_KEY" in str(error.value) and "Wiki" in str(error.value)


@pytest.mark.parametrize("test_environment", [False, True])
def test_llm_only_missing_actual_key_is_not_hidden_by_pytest(isolated_config, monkeypatch, test_environment):
    path, _, _ = isolated_config
    monkeypatch.delenv("DEEPSEEK_API_KEY")
    if test_environment:
        monkeypatch.setenv("PYTEST_CURRENT_TEST", "explicit-determinism-control")
    else:
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        Config.load(path, validation_scope="llm")


@pytest.mark.parametrize("key,value", [("temperature", 3), ("max_tokens", 0),
    ("generation_policy", {"deepseek": {"narrative": {"thinking": "invalid"}}})])
def test_actual_llm_configuration_errors_still_fail(isolated_config, key, value):
    path, raw, write = isolated_config
    raw["llm"][key] = value
    write()
    with pytest.raises(ValueError):
        Config.load(path, validation_scope="llm")


@pytest.mark.parametrize("scope", ["lmm", "", None])
def test_unknown_validation_scope_does_not_silently_skip_validation(isolated_config, scope):
    path, _, _ = isolated_config
    with pytest.raises(ValueError, match="scope"):
        Config.load(path, validation_scope=scope)


def test_configured_narrative_cli_uses_real_llm_scope(isolated_config, monkeypatch):
    path, _, _ = isolated_config
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    calls = []

    def batch(args, *, loaded_model_options):
        calls.append((args, loaded_model_options))
        return 23

    monkeypatch.setattr(wrapper, "batch_main", batch)
    assert wrapper.main(["--llm-config", str(path), "--request", "unused-owned-request.json"]) == 23
    assert len(calls) == 1
    options = calls[0][1]
    assert options["model_id"] == "configured-flash"
    assert options["thinking"] == "disabled"
    assert "scope-fixture-no-real-key" not in json.dumps(options)
