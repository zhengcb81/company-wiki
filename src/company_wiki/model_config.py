"""Single model-profile source shared by every config loader.

Model ids, endpoints and credential variable names live in ``config/models.yaml``
(schema ``company-wiki-models/1``). Loaders select a profile by provider; they
never carry provider defaults of their own.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import yaml

MODEL_CONFIG_SCHEMA = "company-wiki-models/1"
_API_KEY_ENV = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class ModelConfigError(ValueError):
    """The model configuration is missing or invalid."""


@dataclass(frozen=True)
class ModelProfile:
    provider: str
    model: str
    base_url: str
    api_key_env: str


def repository_models_path() -> Path:
    """Return the repository copy of ``config/models.yaml``."""
    return Path(__file__).resolve().parents[2] / "config" / "models.yaml"


def models_path_for(config_path: Path | None) -> Path:
    """Prefer ``<config dir>/config/models.yaml``, else the repository copy."""
    if config_path is not None:
        candidate = config_path.resolve().parent / "config" / "models.yaml"
        if candidate.is_file():
            return candidate
    return repository_models_path()


def load_model_profiles(config_path: Path | None = None) -> dict[str, ModelProfile]:
    """Load and validate every provider profile from the single model config."""
    path = models_path_for(config_path)
    if not path.is_file():
        raise ModelConfigError(f"model config not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ModelConfigError(f"model config is not valid YAML: {exc}") from exc
    if not isinstance(raw, dict) or raw.get("schema_version") != MODEL_CONFIG_SCHEMA:
        raise ModelConfigError(
            f"model config must declare schema_version {MODEL_CONFIG_SCHEMA!r}"
        )
    providers = raw.get("providers")
    if not isinstance(providers, dict) or not providers:
        raise ModelConfigError("model config must define at least one provider")
    profiles: dict[str, ModelProfile] = {}
    for provider, row in providers.items():
        if not isinstance(provider, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", provider):
            raise ModelConfigError(f"invalid provider name: {provider!r}")
        if not isinstance(row, dict):
            raise ModelConfigError(f"provider {provider!r} must be a mapping")
        model = row.get("model")
        base_url = row.get("base_url")
        api_key_env = row.get("api_key_env")
        if not isinstance(model, str) or not model.strip():
            raise ModelConfigError(f"provider {provider!r} needs a nonempty model")
        if not isinstance(base_url, str) or not base_url.startswith(("https://", "http://")):
            raise ModelConfigError(f"provider {provider!r} needs an http(s) base_url")
        if not isinstance(api_key_env, str) or not _API_KEY_ENV.fullmatch(api_key_env):
            raise ModelConfigError(f"provider {provider!r} needs an env-style api_key_env")
        profiles[provider] = ModelProfile(
            provider=provider,
            model=model.strip(),
            base_url=base_url.rstrip("/"),
            api_key_env=api_key_env,
        )
    return profiles


__all__ = [
    "MODEL_CONFIG_SCHEMA",
    "ModelConfigError",
    "ModelProfile",
    "load_model_profiles",
    "models_path_for",
    "repository_models_path",
]
