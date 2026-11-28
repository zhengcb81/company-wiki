"""Explicit configuration paths depend only on their declared location."""
from pathlib import Path

import pytest

from company_wiki.source_catalog.config import expand_config_path


@pytest.mark.parametrize("configured", ["absolute", "relative", "project_token", "profile_token"])
def test_explicit_catalog_path_does_not_resolve_home(tmp_path, monkeypatch, configured):
    target = tmp_path / "catalog"
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    def unavailable_home():
        raise RuntimeError("host has no default home directory")

    monkeypatch.setattr(Path, "home", unavailable_home)
    values = {
        "absolute": str(target),
        "relative": "catalog",
        "project_token": "${PROJECT_ROOT}/catalog",
        "profile_token": "${USER_PROFILE}/catalog",
    }
    assert expand_config_path(values[configured], project_root=tmp_path) == target.resolve()


def test_acquisition_with_explicit_paths_does_not_resolve_home(tmp_path, monkeypatch):
    import json
    import sys

    from company_wiki.source_catalog.acquisition_config import load_acquisition_config

    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    def unavailable_home():
        raise RuntimeError("host has no default home directory")

    monkeypatch.setattr(Path, "home", unavailable_home)
    config = tmp_path / "acquisition.yaml"
    config.write_text(json.dumps({
        "schema_version": "1.1",
        "staging_root": "staging",
        "timeout_seconds": 30,
        "adapters": {
            market: {
                "name": "fixture", "version": "1.0.0", "interface": "json_command_v1",
                "project_root": "${PROJECT_ROOT}", "config_root": None,
                "command": ["${PYTHON_EXECUTABLE}", "-B", "${USER_PROFILE}/fixture.py"],
            }
            for market in ("cn", "hk", "us")
        },
    }), encoding="utf-8")
    loaded = load_acquisition_config(config, project_root=tmp_path)
    assert loaded.staging_root == (tmp_path / "staging").resolve()
    command = loaded.cn.command
    assert command[0] == str(Path(sys.executable).resolve())
    assert Path(command[2]) == tmp_path / "fixture.py"
