"""config_doctor (R4.1) — production config integrity checks."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from config_doctor import diagnose  # noqa: E402


def _write_config(directory: Path, payload: object) -> Path:
    path = directory / "source_catalog.yaml"
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.fixture
def sandbox(tmp_path, monkeypatch) -> Path:
    catalog = tmp_path / ".source_catalog"
    master = catalog / "security_master"
    master.mkdir(parents=True)
    for market in ("cn", "hk", "us"):
        (master / f"{market}.json").write_text("{}", encoding="utf-8")
    return tmp_path


def test_healthy_config_passes(sandbox: Path) -> None:
    path = _write_config(
        sandbox,
        (
            'schema_version: "1.0"\n'
            'catalog_dir: "${PROJECT_ROOT}/.source_catalog"\n'
            "roots:\n"
            "  - root_id: company_raw\n"
            "    kind: company_raw\n"
            '    path: "${PROJECT_ROOT}/companies"\n'
            "    priority: 10\n"
        ),
    )
    assert diagnose(path, project_root=sandbox) == []


def test_single_line_json_fixture_is_rejected(sandbox: Path) -> None:
    # N-05: the production file was overwritten by exactly this shape.
    path = _write_config(
        sandbox,
        {
            "schema_version": "1.0",
            "catalog_dir": "config/.source_catalog",
            "roots": [{"root_id": "fake", "path": "/tmp", "kind": "company_raw"}],
        },
    )
    problems = diagnose(path, project_root=sandbox)
    assert any("JSON fixture" in problem for problem in problems)


def test_missing_security_master_is_rejected(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path,
        {
            "schema_version": "1.0",
            "catalog_dir": "${PROJECT_ROOT}/.source_catalog",
            "roots": [],
        },
    )
    problems = diagnose(path, project_root=tmp_path)
    assert any("security_master" in problem for problem in problems)


def test_missing_catalog_dir_is_rejected(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path,
        {
            "schema_version": "1.0",
            "catalog_dir": "${PROJECT_ROOT}/missing-catalog",
            "roots": [],
        },
    )
    problems = diagnose(path, project_root=tmp_path)
    assert any("catalog_dir" in problem for problem in problems)


def test_missing_config_file_is_rejected(tmp_path: Path) -> None:
    problems = diagnose(tmp_path / "nope.yaml", project_root=tmp_path)
    assert any("missing config" in problem for problem in problems)
