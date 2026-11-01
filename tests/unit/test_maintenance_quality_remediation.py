"""Owner-boundary regressions for legacy retirement and current source CLI."""
from contextlib import nullcontext
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

from company_wiki.source_catalog import architecture_gate as gate

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("source", [
    "from scripts.auto_synthesis import run_synthesis",
    "from ..auto_synthesis import main",
    "import scripts.auto_synthesis as hidden",
    "__import__('auto_synthesis')",
    "import importlib as loader; loader.import_module('scripts.auto_synthesis')",
    "from importlib import import_module as load; load('auto_synthesis')",
])
def test_dependency_check_catches_import_forms_in_package_initializer(tmp_path, source):
    (tmp_path / "__init__.py").write_text(source, encoding="utf-8")
    assert gate.source_catalog_does_not_import_prohibited_modules(tmp_path)[0] is False


def test_dependency_check_ignores_quotes_and_comments(tmp_path):
    (tmp_path / "adapter.py").write_text(
        "# never import auto_synthesis\nmessage = 'from auto_synthesis import main'\n",
        encoding="utf-8",
    )
    assert gate.source_catalog_does_not_import_prohibited_modules(tmp_path) == (True, [])


def test_root_check_ignores_documentation(tmp_path):
    (tmp_path / "adapter.py").write_text("# Dropbox is configured externally\n", encoding="utf-8")
    assert gate.no_root_specific_hardcode(tmp_path) == (True, [])


def test_nested_config_basename_cannot_exempt_root_conditional(tmp_path):
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested/config.py").write_text('if root_id == "company_raw":\n    pass\n', encoding="utf-8")
    assert gate.no_root_specific_hardcode(tmp_path)[0] is False


def test_current_source_catalog_has_no_research_imports():
    assert gate.source_catalog_does_not_import_prohibited_modules() == (True, [])


@pytest.mark.parametrize("script", ["copy_docs.py", "clean_watermarks.py"])
def test_obsolete_copy_and_cleanup_cli_retired_before_arguments(tmp_path, script):
    result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts" / script), "--help"],
                            cwd=tmp_path, capture_output=True, text=True, timeout=10)
    assert result.returncode == 78
    assert "RETIRED" in result.stdout
    assert not list(tmp_path.iterdir())


def test_completed_span_prune_never_opens_current_catalog(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "tools"))
    path = ROOT / "tools/legacy_storage/spans.py"
    spec = importlib.util.spec_from_file_location("retired_span_tool", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class NoCatalogIO:
        def __getattr__(self, name):
            raise AssertionError(f"retired tool must not access {name}")

    result = module.run_prune_spans(NoCatalogIO(), {
        "schema_version": "cwp-span-selection/1", "parser_name": "future_parser_9",
    }, dry_run=False)
    assert result["status"] == "retired"
    assert result["deleted"] == 0


def test_explicit_v2_preview_needs_no_rollout_rounds(monkeypatch):
    from company_wiki.source_catalog import scanner
    sentinel = object()
    monkeypatch.setattr(scanner, "_scan_catalog_impl", lambda *a, **kw: sentinel)
    assert scanner.scan_catalog(object(), None, dry_run=True, v2_scan_shadow=True) is sentinel


@pytest.mark.parametrize("dry_run", [False, True])
def test_current_scan_does_not_load_rollout_snapshot(tmp_path, monkeypatch, dry_run):
    from company_wiki.source_catalog import service
    from company_wiki.source_catalog import scanner
    from company_wiki.source_catalog.models import CatalogConfig, RootSpec
    catalog = service.SourceCatalog(CatalogConfig(project_root=tmp_path, catalog_dir=tmp_path / "catalog",
        roots=(RootSpec("lake", tmp_path / "raw", "company_raw"),)))
    catalog._store = object()
    seen = []
    monkeypatch.setattr(service, "scan_catalog", lambda *a, **kw: seen.append(kw))
    monkeypatch.setattr(service, "CatalogOperationLock", lambda *a, **kw: nullcontext())
    monkeypatch.setattr(scanner, "v2_scan_shadow_from_snapshot",
                        lambda *a: pytest.fail("current scan must not read rollout state"))
    catalog.scan(dry_run=dry_run)
    assert seen[0]["v2_scan_shadow"] is False


def test_reader_bad_arguments_are_invalid_request(capsys):
    from company_wiki.source_catalog.source_reader_cli import main
    assert main([]) == 2
    result = capsys.readouterr()
    assert not result.out
    assert json.loads(result.err)["reason"] == "invalid_request"


def test_reader_bad_digest_is_invalid_before_database_access(tmp_path, capsys, monkeypatch):
    from company_wiki.source_catalog import source_reader_cli as cli
    from company_wiki.source_catalog.models import CatalogConfig, RootSpec
    config = CatalogConfig(project_root=tmp_path, catalog_dir=tmp_path / "catalog",
                           roots=(RootSpec("lake", tmp_path / "raw", "company_raw"),))
    monkeypatch.setattr(cli, "load_catalog_config", lambda path: config)
    assert cli.main(["--config", "not-opened", "--document-id", "d", "--source-id", "s",
                     "--content-sha256", "bad"]) == 2
    result = capsys.readouterr()
    assert not result.out
    assert json.loads(result.err)["reason"] == "invalid_request"
    assert not list(tmp_path.iterdir())


def test_reader_missing_configuration_remains_unavailable(tmp_path, capsys):
    from company_wiki.source_catalog.source_reader_cli import main
    assert main(["--config", str(tmp_path / "absent.yaml"), "--document-id", "d", "--source-id", "s",
                 "--content-sha256", "a" * 64]) == 2
    result = capsys.readouterr()
    assert not result.out
    assert json.loads(result.err)["reason"] == "reader_unavailable"


@pytest.mark.parametrize("operation", ["activation", "runtime-policy"])
def test_historical_rollout_cli_retires_before_configuration(tmp_path, capsys, operation):
    from company_wiki.source_catalog.cli import main
    assert main(["--config", str(tmp_path / "missing.yaml"), operation, "apply"]) == 1
    result = capsys.readouterr()
    assert not result.out
    assert json.loads(result.err)["error_code"] == "MAINTENANCE_OPERATION_RETIRED"
    assert not list(tmp_path.iterdir())


def test_completed_prune_cli_never_loads_config(tmp_path, monkeypatch, capsys):
    monkeypatch.syspath_prepend(str(ROOT / "tools"))
    import legacy_storage_retirement as tool
    monkeypatch.setattr(tool, "_load_config", lambda *a: pytest.fail("retired operation must not load config"))
    assert tool.main(["prune-spans", "--config", str(tmp_path / "config"),
                      "--selection", str(tmp_path / "selection"), "--receipt", str(tmp_path / "receipt"),
                      "--apply"]) == 78
    assert json.loads(capsys.readouterr().err)["status"] == "retired"
    assert not list(tmp_path.iterdir())
