"""The retired whole-catalog worker and startup writers are not public CLI paths."""

from __future__ import annotations

import pytest

import importlib.util
import os
from pathlib import Path
import subprocess
import sys

from company_wiki.source_catalog.cli import _parser


@pytest.mark.parametrize(
    "command",
    [
        "normalize",
        "summarize",
        "extract-sections",
        "evidence",
        "evidence-list",
        "sections-list",
        "run",
        "worker",
        "worker-start",
        "worker-resume",
        "worker-pause",
        "install-startup",
    ],
)
def test_retired_background_and_full_catalog_commands_are_not_registered(command):
    with pytest.raises(SystemExit) as raised:
        _parser().parse_args([command])

    assert raised.value.code == 2


@pytest.mark.parametrize(
    "command",
    [
        "scan",
        "status",
        "query",
        "export",
        "worker-status",
        "worker-stop",
        "uninstall-startup",
    ],
)
def test_source_maintenance_and_worker_cleanup_commands_remain(command):
    args = _parser().parse_args([command])

    assert args.command == command


def test_normalized_section_writer_is_not_a_catalog_api(tmp_path):
    from company_wiki.source_catalog.models import CatalogConfig, RootSpec
    from company_wiki.source_catalog.service import SourceCatalog

    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            roots=(RootSpec("fixture", tmp_path / "raw", "directory"),),
        )
    )
    try:
        assert not hasattr(catalog, "extract_sections")
        assert not (tmp_path / ".source_catalog").exists()
    finally:
        catalog.close()


def test_legacy_automatic_worker_and_full_document_writers_are_retired():
    import company_wiki.source_catalog as public
    from company_wiki.source_catalog.service import SourceCatalog

    assert importlib.util.find_spec("company_wiki.source_catalog.worker") is None
    assert (
        importlib.util.find_spec("company_wiki.source_catalog.scheduler_policy") is None
    )
    assert public.SourceCatalog is SourceCatalog
    assert not hasattr(public, "SourceOnlySchedulerPolicy")
    for name in ("normalize", "summarize", "summarize_with_llm", "extract_sections"):
        assert not hasattr(SourceCatalog, name)
    for name in ("scan", "backfill_text_fingerprints", "query_filing_candidates"):
        assert callable(getattr(SourceCatalog, name))


@pytest.mark.parametrize("method", ["normalize", "summarize", "summarize_with_llm"])
def test_retired_writer_cannot_create_storage_or_call_a_model(tmp_path, monkeypatch, method):
    from company_wiki.source_catalog.models import CatalogConfig, RootSpec
    from company_wiki.source_catalog.service import SourceCatalog
    catalog = SourceCatalog(CatalogConfig(
        project_root=tmp_path, catalog_dir=tmp_path / "catalog",
        roots=(RootSpec("fixture", tmp_path / "raw", "directory"),)))
    monkeypatch.setattr("socket.create_connection", lambda *_args, **_kwargs: pytest.fail("network opened"))
    try:
        with pytest.raises(AttributeError):
            getattr(catalog, method)()
        assert not (tmp_path / "catalog").exists()
        assert not (tmp_path / "derived").exists()
    finally:
        catalog.close()


def test_legacy_worker_keeps_cleanup_controls_without_a_session_launcher():
    import company_wiki.source_catalog.control as control

    assert not hasattr(control, "WorkerSession")
    assert "WorkerSession" not in control.__all__
    assert not hasattr(control.WorkerController, "open_session")
    assert not hasattr(control.WorkerController, "read_desired_state")
    for name in (
        "status",
        "stop",
        "persist_pause_intent",
        "persist_automation_interlock",
    ):
        assert callable(getattr(control.WorkerController, name))


@pytest.mark.parametrize("command", ["extract-sections", "evidence", "evidence-list", "sections-list"])
def test_retired_section_cli_refuses_before_opening_any_catalog(tmp_path, command):
    raw = tmp_path / "original.txt"
    original = "公司主营业务进展：本季度新产品完成量产。".encode("utf-8")
    raw.write_bytes(original)
    source_root = Path(__file__).resolve().parents[2] / "src"
    environment = dict(
        os.environ, PYTHONPATH=str(source_root), PYTHONDONTWRITEBYTECODE="1"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "company_wiki.source_catalog.cli",
            "--config",
            str(tmp_path / "missing-config.yaml"),
            command,
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert b"invalid choice" in result.stderr
    assert raw.read_bytes() == original
    assert not (tmp_path / ".source_catalog").exists()
    assert not (tmp_path / "derived").exists()


def test_old_full_catalog_evidence_backend_is_not_a_public_export():
    import company_wiki.source_catalog as public

    for name in ("EvidenceQueryService", "EvidenceQueryResult", "EvidenceQueryPage"):
        assert not hasattr(public, name)
        assert name not in public.__all__
