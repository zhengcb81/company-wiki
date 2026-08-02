import subprocess
from pathlib import Path

import pytest

from clean_env_gate import is_candidate_path, materialize_candidate, sanitized_environment


def init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "--quiet"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "gate@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Gate Test"], cwd=path, check=True)


def test_candidate_path_excludes_production_and_runtime_data():
    assert is_candidate_path("src/company_wiki/domain.py")
    assert is_candidate_path("tests/fixtures/sample.md")
    assert not is_candidate_path("companies/北方华创/raw/report.pdf")
    assert not is_candidate_path("sectors/半导体设备/wiki/行业概览.md")
    assert not is_candidate_path(".state/state.db")
    assert not is_candidate_path(".env")


def test_materialize_candidate_copies_code_but_not_production_data(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "candidate"
    source.mkdir()
    init_repo(source)
    (source / "src").mkdir()
    (source / "src" / "module.py").write_text("VALUE = 1", encoding="utf-8")
    production = source / "companies" / "A" / "raw"
    production.mkdir(parents=True)
    (production / "secret.pdf").write_bytes(b"raw")
    subprocess.run(["git", "add", "."], cwd=source, check=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "baseline"], cwd=source, check=True)

    manifest = materialize_candidate(source, destination)

    assert (destination / "src" / "module.py").is_file()
    assert not (destination / "companies").exists()
    assert manifest["copied_files"] == 1


def test_materialize_rejects_destination_inside_source(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    init_repo(source)
    with pytest.raises(ValueError, match="outside the source tree"):
        materialize_candidate(source, source / "candidate")


def test_sanitized_environment_removes_api_keys(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret")
    monkeypatch.setenv("CUSTOM_API_KEY", "secret")
    environment = sanitized_environment()
    assert "DEEPSEEK_API_KEY" not in environment
    assert "CUSTOM_API_KEY" not in environment
    assert environment["PIP_NO_INDEX"] == "1"
    assert environment["COMPANY_WIKI_WRITE_MODE"] == "off"
