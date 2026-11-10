"""LLM-only configuration responsibilities, including unmasked production launch."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from config import Config, LLMConfig
from company_wiki.automation.narrative_http_model import model_options_from_config
from company_wiki.automation.narrative_run_store import NarrativeRunStore
from support import narrative_batch_fixtures as batch_fixtures
from support.narrative_batch_fixtures import KEY, isolated_batch_directory, prepare_source_catalog


ROOT = Path(__file__).resolve().parents[2]
loopback_model_server = batch_fixtures.loopback_model_server


def _config(tmp_path, llm=None, **unrelated):
    path = tmp_path / "llm.yaml"
    raw = {"llm": llm or {"provider": "minimax"}, **unrelated}
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return path


def _environment(cwd, **keys):
    env = dict(os.environ)
    for name in list(env):
        if name.upper().endswith("_API_KEY"):
            env.pop(name)
    env.pop("PYTEST_CURRENT_TEST", None)
    env.pop("TAVILY_API_KEY", None)
    env.update(PYTHONPATH=os.pathsep.join((str(ROOT / "src"), str(ROOT / "scripts"))),
               PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1", PYTHON_DOTENV_DISABLED="1",
               WIKI_ROOT=str(cwd / "missing-wiki-root"), **keys)
    return env


def _python(code, cwd, **keys):
    return subprocess.run([sys.executable, "-B", "-c", code], cwd=cwd,
                          env=_environment(cwd, **keys), capture_output=True,
                          text=True, encoding="utf-8", timeout=20, check=False)


def test_production_llm_only_loader_has_no_search_wiki_or_schedule_dependency(tmp_path):
    path = _config(tmp_path, {"provider": "minimax", "max_tokens": 321},
                   search={}, schedule={"news_collection": "unused-invalid-interval"},
                   paths={"wiki_root": str(tmp_path / "missing")})
    before = path.read_bytes()
    result = _python(
        "from config import Config; import json; "
        f"c=Config.load_llm(__import__('pathlib').Path({str(path)!r})); "
        "print(json.dumps([c.provider,c.model,c.max_tokens]))", tmp_path,
        MINIMAX_API_KEY=KEY,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == ["minimax", "MiniMax-M3", 321]
    assert KEY not in result.stdout + result.stderr
    assert path.read_bytes() == before


def test_unrelated_malformed_sections_are_never_constructed(tmp_path, monkeypatch):
    monkeypatch.setenv("MINIMAX_API_KEY", KEY)
    path = _config(tmp_path, search="not-a-search-mapping", paths=["unused"], schedule=7)
    llm = Config.load_llm(path)
    assert isinstance(llm, LLMConfig)
    assert llm.model == "MiniMax-M3"


@pytest.mark.parametrize("marker", [None, "synthetic pytest marker"])
def test_selected_credentials_are_strict_even_in_pytest(tmp_path, monkeypatch, marker):
    path = _config(tmp_path)
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.setenv("MIMO_API_KEY", KEY)
    if marker is None:
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    else:
        monkeypatch.setenv("PYTEST_CURRENT_TEST", marker)
    with pytest.raises(ValueError, match="MINIMAX_API_KEY") as error:
        Config.load_llm(path)
    assert KEY not in str(error.value)
    # Having the configured secondary credential cannot silently select it.
    selected = Config.load_llm(path, llm_provider="mimo")
    assert selected.provider == "mimo" and selected.api_key == KEY


@pytest.mark.parametrize("provider", ["minimax", "mimo", "deepseek", "openai", "claude"])
def test_full_and_llm_only_loaders_share_exact_profiles(tmp_path, monkeypatch, provider):
    key_env = {"claude": "ANTHROPIC_API_KEY"}.get(provider, provider.upper() + "_API_KEY")
    monkeypatch.setenv(key_env, KEY)
    path = _config(tmp_path, {
        "provider": "minimax", "model": "configured-main", "base_url": "https://main.example/v1",
        "max_tokens": 8192, "temperature": 0.6, "reasoning_split": False,
        "fallback": {"provider": "mimo", "model": "configured-fallback",
                     "base_url": "https://fallback.example/v1"},
        "generation_policy": {"deepseek": {"general": {"thinking": "enabled"},
                                             "narrative": {"thinking": "disabled"}}},
    })
    selected = Config.load_llm(path, llm_provider=provider)
    legacy = Config.load(path, llm_provider=provider).llm
    assert selected == legacy
    assert selected.max_tokens == 8192 and selected.temperature == 0.6
    assert selected.api_key == KEY
    if provider == "minimax":
        assert (selected.model, selected.base_url) == ("configured-main", "https://main.example/v1")
    elif provider == "mimo":
        assert (selected.model, selected.base_url) == ("configured-fallback", "https://fallback.example/v1")
    elif provider == "deepseek":
        assert (selected.model, selected.base_url) == ("deepseek-flash", "https://api.deepseek.com")
        assert selected.generation_options("narrative") == {"thinking": {"type": "disabled"}}
    if provider != "claude":
        assert KEY not in json.dumps(model_options_from_config(selected))


def test_selection_does_not_build_unrelated_config(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", KEY)
    path = _config(tmp_path)

    def unrelated(*args, **kwargs):
        raise AssertionError("LLM selection must not construct full Config")

    monkeypatch.setattr(Config, "_build_config", unrelated)
    assert Config.load_llm(path, llm_provider="deepseek").model == "deepseek-flash"


@pytest.mark.parametrize("provider", ["mimo", "misspelled-provider"])
def test_explicit_selection_rejects_disabled_or_unknown_profile(tmp_path, monkeypatch, provider):
    monkeypatch.setenv("MINIMAX_API_KEY", KEY)
    monkeypatch.setenv("MIMO_API_KEY", KEY)
    path = _config(tmp_path, {"fallback": {"provider": "mimo", "enabled": False}})
    with pytest.raises(ValueError):
        Config.load_llm(path, llm_provider=provider)


@pytest.mark.parametrize("llm", [
    {"max_tokens": 0}, {"max_tokens": True}, {"max_tokens": "8192"},
    {"temperature": float("nan")}, {"temperature": True}, {"temperature": "1"},
    {"reasoning_split": "false"}, {"max_document_chars": 0},
    {"generation_policy": {"deepseek": {"narrative": {"thinking": "adaptive"}}}},
    {"generation_policy": {"minimax": {"narrative": {"reasoning_effort": "medium"}}}},
])
def test_invalid_llm_parameters_fail_through_both_loaders(tmp_path, monkeypatch, llm):
    monkeypatch.setenv("MINIMAX_API_KEY", KEY)
    path = _config(tmp_path, {"provider": "minimax", **llm})
    for load in (Config.load_llm, Config.load):
        with pytest.raises(ValueError) as error:
            load(path)
        assert KEY not in str(error.value)


def test_explicit_config_does_not_search_dotenv_or_accept_yaml_key(tmp_path, monkeypatch):
    import config as module
    monkeypatch.setattr(module, "WIKI_ROOT", tmp_path)
    monkeypatch.setattr(module, "_dotenv_loaded", False)
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.delenv("PYTHON_DOTENV_DISABLED", raising=False)
    (tmp_path / ".env").write_text("MINIMAX_API_KEY=" + KEY + "\n", encoding="utf-8")
    path = _config(tmp_path, {"provider": "minimax", "api_key": "yaml-key-never-usable"})
    with pytest.raises(ValueError, match="MINIMAX_API_KEY"):
        Config.load_llm(path)
    assert "MINIMAX_API_KEY" not in os.environ


@pytest.mark.parametrize("environment_present", [False, True])
def test_default_dotenv_keeps_managed_keys_and_deepseek_env_precedence(tmp_path, environment_present):
    (tmp_path / "config.yaml").write_text("llm:\n  provider: minimax\n", encoding="utf-8")
    (tmp_path / ".env").write_text(
        "MINIMAX_API_KEY=managed-primary-fixture\n"
        "DEEPSEEK_API_KEY=dotenv-deepseek-fixture\n", encoding="utf-8")
    env = _environment(tmp_path, MINIMAX_API_KEY="stale-primary-fixture")
    env["WIKI_ROOT"] = str(tmp_path)
    env.pop("PYTHON_DOTENV_DISABLED")
    if environment_present:
        env["DEEPSEEK_API_KEY"] = "environment-deepseek-fixture"
    process = subprocess.run([sys.executable, "-B", "-c",
        "from config import Config; "
        "a=Config.load_llm();b=Config.load_llm(llm_provider='deepseek'); "
        "assert a.api_key=='managed-primary-fixture'; "
        f"assert b.api_key=={'environment-deepseek-fixture' if environment_present else 'dotenv-deepseek-fixture'!r}; "
        "print('verified')"], cwd=tmp_path, env=env, capture_output=True,
        text=True, encoding="utf-8", timeout=20, check=False)
    assert process.returncode == 0, process.stdout + process.stderr
    assert process.stdout.strip() == "verified"


def test_full_config_keeps_production_search_and_wiki_requirements(tmp_path):
    path = _config(tmp_path)
    process = _python(
        "from config import Config; "
        f"Config.load(__import__('pathlib').Path({str(path)!r}))", tmp_path,
        MINIMAX_API_KEY=KEY,
    )
    assert process.returncode != 0
    assert "TAVILY_API_KEY" in process.stderr and "Wiki 根目录不存在" in process.stderr
    assert KEY not in process.stdout + process.stderr


def test_configured_cli_missing_key_is_static_before_batch_or_network(tmp_path):
    path = _config(tmp_path)
    process = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/narrative_batch_configured.py"),
                              "--llm-config", str(path)], cwd=tmp_path,
                             env=_environment(tmp_path), capture_output=True, text=True,
                             encoding="utf-8", timeout=20, check=False)
    assert process.returncode == 1
    assert json.loads(process.stdout)["error"] == "NARRATIVE_MODEL_CONFIG_INVALID"
    assert KEY not in process.stdout + process.stderr


def test_production_configured_cli_completes_with_only_llm_dependencies(
    tmp_path_factory, loopback_model_server,
):
    with isolated_batch_directory(tmp_path_factory) as root:
        state = prepare_source_catalog(root, one_source=True, include_policy=False)
        try:
            path = _config(root, {
                "provider": "deepseek", "model": "stub-model",
                "base_url": loopback_model_server.endpoint.removesuffix("/chat/completions"),
                "max_tokens": 8192, "temperature": 0.6,
                "generation_policy": {"deepseek": {"narrative": {"thinking": "disabled"}}},
            }, paths={"wiki_root": str(root / "missing")}, search={},
                schedule={"news_collection": "unused-invalid-interval"})
            original_bytes = {p: p.read_bytes() for p in state.raw_paths.values()}
            original_config = path.read_bytes()
            ref, _language, _kind = next(iter(state.indexed.values()))
            request = {
                "schema_version": "narrative-batch-request/1", "run_id": "w04-config-scope",
                "sources": [{"schema_version": ref.schema_version, "document_id": ref.document_id,
                             "source_id": ref.source_id, "content_sha256": ref.content_sha256,
                             "byte_size": ref.byte_size, "mime_type": ref.mime_type}],
                "profile": "P2", "max_seconds": 40, "max_tokens": 100_000, "max_cost_usd": "0.2",
                "model": {"timeout_seconds": 5, "max_request_bytes": 100_000, "max_response_bytes": 100_000},
                "pricing": {"version": "fixture-price/1", "input_micro_usd_per_million_tokens": 1_000_000,
                            "output_micro_usd_per_million_tokens": 2_000_000},
            }
            request_path = root / "request.json"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            command = [sys.executable, "-B", str(ROOT / "scripts/narrative_batch_configured.py"),
                       "--llm-config", str(path), "--allow-local-model-http",
                       "--project-root", str(root), "--catalog-config", str(state.config_path),
                       "--automation-db", str(root / "automation.db"), "--work-dir", str(root / "work"),
                       "--request", str(request_path)]
            process = subprocess.run(command, cwd=root, env=_environment(root, DEEPSEEK_API_KEY=KEY),
                                     capture_output=True, text=True, encoding="utf-8", timeout=55, check=False)
            assert process.returncode == 0, process.stdout + process.stderr
            receipt = json.loads(process.stdout)
            assert receipt["status"] == "completed"
            assert receipt["documents"][0]["artifact_ref"] is not None
            assert receipt["budget"] == {"tokens": 92, "estimated_micro_usd": 111,
                                          "unknown_reservations": 0, "unsettled_reservations": 0}
            assert len(loopback_model_server.requests) == 1 and not loopback_model_server.errors
            body = json.loads(loopback_model_server.requests[0][1])
            assert body["model"] == "stub-model" and body["max_tokens"] == 8192
            assert body["temperature"] == 0.6 and body["thinking"] == {"type": "disabled"}
            reservation, = NarrativeRunStore(root / "automation.db").reservations_for_run("w04-config-scope")
            assert reservation.usage_status == "known"
            assert (reservation.input_tokens, reservation.output_tokens) == (73, 19)
            assert path.read_bytes() == original_config
            assert {p: p.read_bytes() for p in state.raw_paths.values()} == original_bytes
            assert KEY not in process.stdout + process.stderr
        finally:
            state.catalog.close()
