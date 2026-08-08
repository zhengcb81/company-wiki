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


def test_e2e_f03_second_directory_root_fails_fast(tmp_path, monkeypatch):
    """E2E-F03: a second kind=directory root must fail the doctor."""
    from config_doctor import diagnose

    config = tmp_path / "source_catalog.yaml"
    config.write_text('schema_version: "1.0"\ncatalog_dir: "${PROJECT_ROOT}/.source_catalog"\nreusable_root_kinds: [company_raw, dayu_portfolio, directory]\nroots:\n  - root_id: company_raw\n    kind: company_raw\n    path: "${PROJECT_ROOT}/companies"\n    priority: 10\n  - root_id: dropbox_stock\n    kind: directory\n    path: "${USER_PROFILE}/Dropbox/Stock"\n    priority: 30\n  - root_id: other_dir\n    kind: directory\n    path: "${USER_PROFILE}/somewhere"\n    priority: 40\n', encoding='utf-8')
    project = tmp_path / "project"
    (project / ".source_catalog" / "security_master").mkdir(parents=True)
    (project / ".source_catalog" / "security_master" / "us.json").write_text("{}", encoding="utf-8")
    problems = diagnose(config, project_root=project)
    assert any("directory roots must be exactly" in p for p in problems), problems

def test_e2e_f03_filing_allowance_missing_dropbox_fails(tmp_path, monkeypatch):
    """E2E-F03: filing-fetch allowance missing Dropbox/Stock → doctor fails."""
    from config_doctor import diagnose

    filing = tmp_path / "filing-fetch" / "config"
    filing.mkdir(parents=True)
    (filing / "company_wiki.json").write_text(
        '{"schema_version": "1.0", "allowed_handle_roots": ["/companies"]}',
        encoding="utf-8",
    )
    config = tmp_path / "source_catalog.yaml"
    config.write_text('schema_version: "1.0"\ncatalog_dir: "${PROJECT_ROOT}/.source_catalog"\nreusable_root_kinds: [company_raw, dayu_portfolio, directory]\nroots:\n  - root_id: company_raw\n    kind: company_raw\n    path: "${PROJECT_ROOT}/companies"\n    priority: 10\n  - root_id: dropbox_stock\n    kind: directory\n    path: "${USER_PROFILE}/Dropbox/Stock"\n    priority: 30\n', encoding='utf-8')
    project = tmp_path / "project"
    (project / ".source_catalog" / "security_master").mkdir(parents=True)
    (project / ".source_catalog" / "security_master" / "us.json").write_text("{}", encoding="utf-8")
    problems = diagnose(config, project_root=project)
    assert any("missing Dropbox/Stock" in p for p in problems), problems



def test_e2e_f03_dropbox_realpath_drift_fails(tmp_path, monkeypatch):
    """E2E-F03: wiki and filing resolve the Dropbox path to different
    realpaths → doctor fails (double-config drift fail-fast)."""
    from config_doctor import diagnose

    filing = tmp_path / "filing-fetch" / "config"
    filing.mkdir(parents=True)
    # filing allowance points at a DIFFERENT Dropbox path
    (filing / "company_wiki.json").write_text(
        '{"schema_version": "1.0", "allowed_handle_roots": ["${USER_PROFILE}/Dropbox/Stock", "/other"]}',
        encoding="utf-8",
    )
    yaml = (
        'schema_version: "1.0"\n'
        'catalog_dir: "${PROJECT_ROOT}/.source_catalog"\n'
        "reusable_root_kinds: [company_raw, dayu_portfolio, directory]\n"
        "roots:\n"
        '  - root_id: company_raw\n'
        "    kind: company_raw\n"
        '    path: "${PROJECT_ROOT}/companies"\n'
        "    priority: 10\n"
        '  - root_id: dropbox_stock\n'
        "    kind: directory\n"
        '    path: "${USER_PROFILE}/Dropbox/Other"\n'  # different realpath
        "    priority: 30\n"
    )
    config = tmp_path / "source_catalog.yaml"
    config.write_text(yaml, encoding="utf-8")
    project = tmp_path / "project"
    (project / ".source_catalog" / "security_master").mkdir(parents=True)
    (project / ".source_catalog" / "security_master" / "us.json").write_text("{}", encoding="utf-8")
    problems = diagnose(config, project_root=project)
    assert any("realpath drift" in p for p in problems), problems
