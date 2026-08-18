"""ZR-407: no-download exact ``ensure`` must remain a true read path."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from company_wiki.source_catalog import cli
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.store import CatalogStore


def _write_config(project: Path) -> Path:
    config_dir = project / "config"
    config_dir.mkdir(parents=True)
    (project / "companies").mkdir()
    config = config_dir / "source_catalog.yaml"
    config.write_text(
        "schema_version: '1.0'\n"
        "catalog_dir: '${PROJECT_ROOT}/.source_catalog'\n"
        "roots:\n"
        "  - root_id: company_raw\n"
        "    kind: company_raw\n"
        "    path: '${PROJECT_ROOT}/companies'\n"
        "    priority: 10\n",
        encoding="utf-8",
    )
    return config


def _ensure_args(config: Path) -> list[str]:
    return [
        "--config",
        str(config),
        "ensure",
        "--entity",
        "Acme",
        "--market",
        "US",
        "--security-id",
        "ACME",
        "--document-kind",
        "annual_report",
        "--fiscal-year",
        "2025",
        "--as-of-date",
        "2026-08-01",
    ]


def test_no_download_exact_ensure_uses_reader_without_journal(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """The public CLI must return a structured missing response even when
    the database rejects writer initialization.  No journal is appended
    because no acquisition attempt was permitted."""
    config = _write_config(tmp_path / "project")
    database = config.parent.parent / ".source_catalog" / "catalog.sqlite3"
    CatalogStore(database)
    os.chmod(database, stat.S_IREAD)

    def _writer_forbidden(_self: SourceCatalog):
        raise AssertionError("no-download ensure must not initialize CatalogStore")

    monkeypatch.setattr(SourceCatalog, "store", property(_writer_forbidden))
    try:
        exit_code = cli.main(_ensure_args(config))
    finally:
        os.chmod(database, stat.S_IWRITE)

    captured = capsys.readouterr()
    assert exit_code == 0, captured.err
    payload = json.loads(captured.out)
    assert payload["schema_version"] == "1.0"
    assert payload["status"] == "missing"
    assert payload["resolution"]["status"] == "missing"
    assert payload["attempt"] is None
    assert not (database.parent / "acquisition_journal.jsonl").exists()
