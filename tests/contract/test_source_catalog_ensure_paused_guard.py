"""One explicit source download is independent of the retired background worker."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from company_wiki.source_catalog import cli


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
    # Keep accepting the old path while the FF harness merges its call-site change.
    (config_dir / "source_catalog_worker.yaml").write_text(
        "schema_version: '1.0'\n", encoding="utf-8"
    )
    return catalog_config


def _ensure_args(config: Path, *extra: str) -> list[str]:
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


@pytest.mark.parametrize("legacy_flag", [(), ("--allow-acquisition-while-paused",)])
def test_explicit_ensure_download_does_not_consult_legacy_worker_state(
    tmp_path, capsys, monkeypatch, legacy_flag
):
    config = _write_configs(tmp_path / "project")
    controller_calls: list[dict] = []

    def unexpected_worker_controller(**kwargs):
        controller_calls.append(kwargs)
        return object()

    monkeypatch.setattr(cli, "WorkerController", unexpected_worker_controller)

    code = cli.main(_ensure_args(config, *legacy_flag))
    err = capsys.readouterr().err

    # The isolated fixture intentionally lacks acquisition configuration, so reaching
    # that ordinary configuration error proves the legacy paused gate was bypassed.
    assert code == 1
    assert json.loads(err)["error_type"] == "fatal"
    assert "source acquisition is paused" not in err
    assert controller_calls == []


def test_close_gap_does_not_consult_legacy_worker_state(tmp_path, capsys, monkeypatch):
    config = _write_configs(tmp_path / "project")
    binding = tmp_path / "binding.json"
    binding.write_text(
        json.dumps(
            {
                "request_id": "test-request",
                "gap_plan_hash": "a" * 64,
                "policy_hash": "b" * 64,
                "provider": "fixture",
                "allowed_accessions": ["fixture-accession"],
                "max_items": 1,
                "max_bytes": 1024,
                "expires_at": "2099-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    controller_calls: list[dict] = []

    def unexpected_worker_controller(**kwargs):
        controller_calls.append(kwargs)
        return object()

    monkeypatch.setattr(cli, "WorkerController", unexpected_worker_controller)

    code = cli.main(
        [
            "--config",
            str(config),
            "close-gap",
            "--entity",
            "Acme",
            "--binding-file",
            str(binding),
            "--document-kind",
            "annual_report",
            "--as-of-date",
            "2026-08-04",
        ]
    )
    err = capsys.readouterr().err

    assert code == 1
    assert json.loads(err)["error_type"] == "fatal"
    assert "source acquisition is paused" not in err
    assert controller_calls == []
