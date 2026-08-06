"""`ensure --allow-download` paused-guard contract.

The guard refuses downloads while the background worker is paused (desired_state
== "paused"). `--allow-acquisition-while-paused` is an explicit opt-in for
orchestrators (filing-fetch) that deliberately paused the worker to release the
global catalog lock and will resume it afterwards. The default guard behavior
must be preserved for everyone else.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from company_wiki.source_catalog import cli


class _FakeWorkerController:
    """Stub controller whose status always reports the given desired_state."""

    def __init__(self, desired_state: str) -> None:
        self._desired = desired_state

    def status(self) -> dict:
        return {"desired_state": self._desired}


def _write_configs(project: Path) -> Path:
    config_dir = project / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (project / "companies").mkdir(parents=True, exist_ok=True)
    catalog_config = config_dir / "source_catalog.yaml"
    catalog_config.write_text(
        "schema_version: '1.0'\n"
        "catalog_dir: '${PROJECT_ROOT}/.source_catalog'\n"
        "roots:\n"
        "  - root_id: company_raw\n"
        "    kind: company_raw\n"
        "    path: '${PROJECT_ROOT}/companies'\n"
        "    priority: 10\n",
        encoding="utf-8",
    )
    # worker_config_path() resolves this strictly inside the worker_controller()
    # closure, so it must exist even though the controller itself is stubbed.
    (config_dir / "source_catalog_worker.yaml").write_text(
        "schema_version: '1.0'\n", encoding="utf-8"
    )
    return catalog_config


@pytest.fixture
def paused_controller(monkeypatch):
    monkeypatch.setattr(
        cli, "WorkerController", lambda **kwargs: _FakeWorkerController("paused")
    )


def _ensure_args(config: Path, *extra: str) -> list[str]:
    # --entity (not --company-query) keeps the test off the security-master
    # identity path; the paused guard sits before any acquisition work.
    return [
        "--config",
        str(config),
        "ensure",
        "--entity",
        "Acme",
        "--document-kind",
        "annual_report",
        "--as-of-date",
        "2026-08-04",
        "--allow-download",
        *extra,
    ]


def test_ensure_download_refused_when_paused_without_flag(tmp_path, capsys, paused_controller):
    config = _write_configs(tmp_path / "project")
    code = cli.main(_ensure_args(config))
    err = capsys.readouterr().err
    assert code == 1
    assert "source acquisition is paused" in err


def test_ensure_download_allowed_when_paused_with_flag(tmp_path, capsys, paused_controller):
    config = _write_configs(tmp_path / "project")
    code = cli.main(_ensure_args(config, "--allow-acquisition-while-paused"))
    err = capsys.readouterr().err
    assert code == 1
    # The guard passed: the failure is downstream (missing acquisition config),
    # not the paused guard.
    assert "source acquisition is paused" not in err
    assert "FileNotFoundError" in err


def test_ensure_download_allowed_when_worker_enabled_without_flag(
    tmp_path, capsys, monkeypatch
):
    monkeypatch.setattr(
        cli, "WorkerController", lambda **kwargs: _FakeWorkerController("enabled")
    )
    config = _write_configs(tmp_path / "project")
    code = cli.main(_ensure_args(config))
    err = capsys.readouterr().err
    assert code == 1
    assert "source acquisition is paused" not in err
    assert "FileNotFoundError" in err
