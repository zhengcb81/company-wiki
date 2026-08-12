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

def test_e2e_f03_filing_allowance_smuggled_fails(tmp_path, monkeypatch):
    """E2E-F03 / FC-501 (CONFIG-DBX-03): a filing-fetch config smuggling
    back an independent allowed_handle_roots is a contract violation —
    the policy snapshot is the single source; the doctor must fail when
    given the filing config explicitly (FC-1202)."""
    from config_doctor import diagnose

    filing = tmp_path / "filing-fetch" / "config"
    filing.mkdir(parents=True)
    filing_config = filing / "company_wiki.json"
    filing_config.write_text(
        '{"schema_version": "1.0", "allowed_handle_roots": ["/Dropbox/Stock"]}',
        encoding="utf-8",
    )
    config = tmp_path / "source_catalog.yaml"
    config.write_text('schema_version: "1.0"\ncatalog_dir: "${PROJECT_ROOT}/.source_catalog"\nreusable_root_kinds: [company_raw, dayu_portfolio, directory]\nroots:\n  - root_id: company_raw\n    kind: company_raw\n    path: "${PROJECT_ROOT}/companies"\n    priority: 10\n  - root_id: dropbox_stock\n    kind: directory\n    path: "${USER_PROFILE}/Dropbox/Stock"\n    priority: 30\n', encoding='utf-8')
    project = tmp_path / "project"
    (project / ".source_catalog" / "security_master").mkdir(parents=True)
    (project / ".source_catalog" / "security_master" / "us.json").write_text("{}", encoding="utf-8")
    problems = diagnose(
        config, project_root=project, filing_fetch_config=filing_config
    )
    assert any("allowed_handle_roots" in p for p in problems), problems


def test_no_implicit_sibling_lookup_without_arg(tmp_path, monkeypatch):
    """FC-1202: without an explicit --filing-fetch-config the doctor must
    NOT look up a sibling filing-fetch directory — even a smuggled sibling
    config is out of this doctor's sight (the three-repo check lives in
    filing-fetch's CI doctor)."""
    from config_doctor import diagnose

    filing = tmp_path / "filing-fetch" / "config"
    filing.mkdir(parents=True)
    (filing / "company_wiki.json").write_text(
        '{"schema_version": "1.0", "allowed_handle_roots": ["/Dropbox/Stock"]}',
        encoding="utf-8",
    )
    config = tmp_path / "source_catalog.yaml"
    config.write_text('schema_version: "1.0"\ncatalog_dir: "${PROJECT_ROOT}/.source_catalog"\nreusable_root_kinds: [company_raw]\nroots:\n  - root_id: company_raw\n    kind: company_raw\n    path: "${PROJECT_ROOT}/companies"\n    priority: 10\n', encoding='utf-8')
    project = tmp_path / "project"
    (project / ".source_catalog" / "security_master").mkdir(parents=True)
    (project / ".source_catalog" / "security_master" / "us.json").write_text("{}", encoding="utf-8")
    problems = diagnose(config, project_root=project)
    assert problems == [], problems


def test_explicit_missing_filing_config_is_reported(tmp_path, monkeypatch):
    """FC-1202: an explicit --filing-fetch-config that does not exist is a
    problem (fail closed), not a silent skip."""
    from config_doctor import diagnose

    config = tmp_path / "source_catalog.yaml"
    config.write_text('schema_version: "1.0"\ncatalog_dir: "${PROJECT_ROOT}/.source_catalog"\nreusable_root_kinds: [company_raw]\nroots:\n  - root_id: company_raw\n    kind: company_raw\n    path: "${PROJECT_ROOT}/companies"\n    priority: 10\n', encoding='utf-8')
    project = tmp_path / "project"
    (project / ".source_catalog" / "security_master").mkdir(parents=True)
    (project / ".source_catalog" / "security_master" / "us.json").write_text("{}", encoding="utf-8")
    problems = diagnose(
        config,
        project_root=project,
        filing_fetch_config=tmp_path / "nope" / "company_wiki.json",
    )
    assert any("does not exist" in p for p in problems), problems


def test_e2e_f03_dropbox_path_not_stock_fails(tmp_path, monkeypatch):
    """E2E-F03 / FC-501 (CONFIG-DBX-04): the Dropbox root's single source
    of truth is source_catalog.yaml — a path that does not point at
    Dropbox/Stock fails the doctor."""
    from config_doctor import diagnose

    config = tmp_path / "source_catalog.yaml"
    config.write_text(
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
        '    path: "${USER_PROFILE}/Dropbox/Other"\n'
        "    priority: 30\n",
        encoding="utf-8",
    )
    project = tmp_path / "project"
    (project / ".source_catalog" / "security_master").mkdir(parents=True)
    (project / ".source_catalog" / "security_master" / "us.json").write_text("{}", encoding="utf-8")
    problems = diagnose(config, project_root=project)
    assert any("Dropbox/Stock" in p for p in problems), problems


