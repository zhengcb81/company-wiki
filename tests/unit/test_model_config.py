"""The single model table in config/models.yaml drives every provider."""

from pathlib import Path

import pytest

from company_wiki.model_config import (
    MODEL_CONFIG_SCHEMA,
    ModelConfigError,
    load_model_profiles,
    models_path_for,
    repository_models_path,
)


def test_repository_model_config_is_the_single_valid_source():
    profiles = load_model_profiles()
    assert set(profiles) >= {"minimax", "mimo", "deepseek"}
    minimax = profiles["minimax"]
    assert minimax.model == "MiniMax-M3.1-Flash"
    assert minimax.base_url == "https://api.minimaxi.com/v1"
    assert minimax.api_key_env == "MINIMAX_API_KEY"
    for profile in profiles.values():
        assert profile.model and profile.model == profile.model.strip()
        assert profile.base_url.startswith(("https://", "http://"))
        assert profile.api_key_env.isupper()


def test_models_path_prefers_a_sibling_models_file(tmp_path: Path):
    sibling = tmp_path / "config" / "models.yaml"
    sibling.parent.mkdir()
    sibling.write_text(f"schema_version: {MODEL_CONFIG_SCHEMA}\nproviders: {{}}\n", encoding="utf-8")
    assert models_path_for(tmp_path / "config.yaml") == sibling
    other = tmp_path / "other"
    other.mkdir()
    assert models_path_for(other / "config.yaml") == repository_models_path()


def test_invalid_model_config_is_rejected(tmp_path: Path):
    path = tmp_path / "config" / "models.yaml"
    path.parent.mkdir()
    path.write_text("schema_version: wrong\nproviders: {}\n", encoding="utf-8")
    with pytest.raises(ModelConfigError):
        load_model_profiles(tmp_path / "config.yaml")
