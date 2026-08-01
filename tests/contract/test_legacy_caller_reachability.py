"""CW-3.1 contracts for retiring legacy research/Wiki orchestrators."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402
import writer_policy  # noqa: E402


EXPECTED_R1 = frozenset(
    {
        "auto_synthesis.py",
        "batch_assessment.py",
        "batch_ingest.py",
        "batch_process.py",
        "consolidate.py",
        "enrich_wiki.py",
        "full_pipeline.py",
        "generate_slides.py",
        "ingest_v2.py",
        "investment_judgment.py",
        "review_queue.py",
        "scheduler.py",
        "stage3_analyze.py",
        "stage4_review.py",
        "stage5_ingest.py",
        "stage6_synthesize.py",
        "valuation_engine.py",
    }
)

EXPECTED_R2 = frozenset(
    {
        "auto_discover.py",
        "evolve_questions.py",
        "expire_tracker.py",
        "maintenance.py",
        "query.py",
        "question_evolver.py",
        "refine.py",
        "reprocess.py",
        "tag_segments.py",
    }
)

EXPECTED_R3 = frozenset(
    {
        "cleanup_deprecated.py",
        "cleanup_junk.py",
        "cleanup_log.py",
        "reset_ingested.py",
    }
)

EXPECTED_R4 = frozenset(
    {
        "build_links.py",
        "fix_broken_links.py",
        "fix_sources_count.py",
        "generate_dashboard.py",
        "generate_index.py",
        "quality_dashboard.py",
        "wikilinks.py",
    }
)

EXPECTED_R5 = frozenset({"cross_verify.py"})

EXPECTED_PERMANENTLY_RETIRED = (
    EXPECTED_R1 | EXPECTED_R2 | EXPECTED_R3 | EXPECTED_R4 | EXPECTED_R5
)


def _legacy_override() -> dict[str, str]:
    environment = {
        key: os.environ[key]
        for key in ("PATH", "PATHEXT", "SYSTEMROOT", "TEMP", "TMP")
        if key in os.environ
    }
    environment.update(
        {
            "PYTHONIOENCODING": "utf-8",
            "PYTHON_DOTENV_DISABLED": "1",
            "COMPANY_WIKI_WRITE_MODE": "legacy",
            "COMPANY_WIKI_LEGACY_WRITERS": "allow",
            "COMPANY_WIKI_REAL_LLM": "0",
            "COMPANY_WIKI_NETWORK": "blocked",
        }
    )
    return environment


def test_permanent_retirement_inventory_is_frozen_in_policy() -> None:
    actual = getattr(writer_policy, "PERMANENTLY_RETIRED_SCRIPTS", frozenset())
    assert actual == EXPECTED_PERMANENTLY_RETIRED


def test_r1_override_is_rejected_by_policy() -> None:
    execution_allowed = getattr(
        writer_policy, "legacy_script_execution_allowed", None
    )
    assert execution_allowed is not None
    environment = _legacy_override()
    for script_name in EXPECTED_R1:
        assert execution_allowed(script_name, environment) is False


def test_r2_override_is_rejected_by_policy() -> None:
    execution_allowed = getattr(
        writer_policy, "legacy_script_execution_allowed", None
    )
    assert execution_allowed is not None
    environment = _legacy_override()
    for script_name in EXPECTED_R2:
        assert execution_allowed(script_name, environment) is False


def test_r3_override_is_rejected_by_policy() -> None:
    execution_allowed = getattr(
        writer_policy, "legacy_script_execution_allowed", None
    )
    assert execution_allowed is not None
    environment = _legacy_override()
    for script_name in EXPECTED_R3:
        assert execution_allowed(script_name, environment) is False


def test_r4_override_is_rejected_by_policy() -> None:
    execution_allowed = getattr(
        writer_policy, "legacy_script_execution_allowed", None
    )
    assert execution_allowed is not None
    environment = _legacy_override()
    for script_name in EXPECTED_R4:
        assert execution_allowed(script_name, environment) is False


def test_r5_override_is_rejected_by_policy() -> None:
    execution_allowed = getattr(
        writer_policy, "legacy_script_execution_allowed", None
    )
    assert execution_allowed is not None
    assert execution_allowed("cross_verify.py", _legacy_override()) is False


def test_non_r1_source_compatibility_keeps_explicit_override_contract() -> None:
    execution_allowed = getattr(
        writer_policy, "legacy_script_execution_allowed", None
    )
    assert execution_allowed is not None
    assert execution_allowed("collect_reports.py", _legacy_override()) is True
    assert execution_allowed("test_framework.py", _legacy_override()) is True


def test_r1_direct_cli_fails_before_argument_or_llm_initialization() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPTS / "scheduler.py"), "--help"],
        cwd=ROOT,
        env=_legacy_override(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
    )
    assert completed.returncode == writer_policy.BLOCKED_EXIT_CODE
    assert "PERMANENTLY RETIRED" in completed.stdout
    assert "source-catalog" in completed.stdout
    assert "StockWiki" in completed.stdout


def test_imported_orchestrator_permission_rejects_r1_override(monkeypatch) -> None:
    monkeypatch.setenv("COMPANY_WIKI_WRITE_MODE", "legacy")
    monkeypatch.setenv("COMPANY_WIKI_LEGACY_WRITERS", "allow")
    assert common.require_legacy_writer_permission("full_pipeline.py") is False
    assert common.require_legacy_writer_permission("batch_process.py") is False


def test_imported_destructive_permission_rejects_r3_override(monkeypatch) -> None:
    monkeypatch.setenv("COMPANY_WIKI_WRITE_MODE", "legacy")
    monkeypatch.setenv("COMPANY_WIKI_LEGACY_WRITERS", "allow")
    assert common.require_legacy_writer_permission("cleanup_junk.py") is False


def test_imported_link_writer_permission_rejects_r4_override(monkeypatch) -> None:
    monkeypatch.setenv("COMPANY_WIKI_WRITE_MODE", "legacy")
    monkeypatch.setenv("COMPANY_WIKI_LEGACY_WRITERS", "allow")
    assert common.require_legacy_writer_permission("fix_broken_links.py") is False


def test_imported_cross_verify_permission_rejects_r5_override(monkeypatch) -> None:
    monkeypatch.setenv("COMPANY_WIKI_WRITE_MODE", "legacy")
    monkeypatch.setenv("COMPANY_WIKI_LEGACY_WRITERS", "allow")
    assert common.require_legacy_writer_permission("cross_verify.py") is False


def test_r2_direct_cli_rejects_override_without_running_writer() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPTS / "query.py"), "--help"],
        cwd=ROOT,
        env=_legacy_override(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
    )
    assert completed.returncode == writer_policy.BLOCKED_EXIT_CODE
    assert "PERMANENTLY RETIRED" in completed.stdout


def test_maintenance_guard_survives_python_no_site_mode() -> None:
    completed = subprocess.run(
        [sys.executable, "-S", str(SCRIPTS / "maintenance.py"), "--help"],
        cwd=ROOT,
        env=_legacy_override(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
    )
    assert completed.returncode == writer_policy.BLOCKED_EXIT_CODE
    assert "PERMANENTLY RETIRED" in completed.stdout


def test_r3_guard_survives_python_no_site_mode() -> None:
    completed = subprocess.run(
        [sys.executable, "-S", str(SCRIPTS / "cleanup_log.py"), "--help"],
        cwd=ROOT,
        env=_legacy_override(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
    )
    assert completed.returncode == writer_policy.BLOCKED_EXIT_CODE
    assert "PERMANENTLY RETIRED" in completed.stdout


def test_r4_guard_survives_python_no_site_mode_without_writing() -> None:
    script = SCRIPTS / "generate_dashboard.py"
    harness = (
        "import pathlib,runpy,sys;"
        f"sys.path.insert(0,{str(SCRIPTS)!r});"
        "pathlib.Path.write_text=lambda *a,**k:"
        "(_ for _ in ()).throw(RuntimeError('WRITE BLOCKED'));"
        f"sys.argv=[{str(script)!r},'--help'];"
        f"runpy.run_path({str(script)!r},run_name='__main__')"
    )
    completed = subprocess.run(
        [sys.executable, "-S", "-c", harness],
        cwd=ROOT,
        env=_legacy_override(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
    )
    assert completed.returncode == writer_policy.BLOCKED_EXIT_CODE
    assert "PERMANENTLY RETIRED" in completed.stdout
    assert "WRITE BLOCKED" not in completed.stdout
    assert "WRITE BLOCKED" not in completed.stderr


def test_r4_module_import_preserves_wikilink_engine() -> None:
    import wikilinks

    assert wikilinks.WikilinkEngine.__name__ == "WikilinkEngine"


def test_r5_guard_survives_python_no_site_mode() -> None:
    completed = subprocess.run(
        [sys.executable, "-S", str(SCRIPTS / "cross_verify.py"), "--help"],
        cwd=ROOT,
        env=_legacy_override(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
    )
    assert completed.returncode == writer_policy.BLOCKED_EXIT_CODE
    assert "PERMANENTLY RETIRED" in completed.stdout


def test_r5_module_import_preserves_historical_event_cluster() -> None:
    import cross_verify

    cluster = cross_verify.EventCluster("example")
    cluster.add_entry({"company": "Example", "source_url": "source.md"})
    assert cluster.source_count == 1


def test_every_retired_script_has_an_explicit_direct_cli_guard() -> None:
    missing = []
    for script_name in sorted(EXPECTED_PERMANENTLY_RETIRED):
        source = (SCRIPTS / script_name).read_text(encoding="utf-8-sig")
        if "enforce_direct_cli" not in source:
            missing.append(script_name)
    assert not missing


def test_maintenance_guard_precedes_project_initialization() -> None:
    source = (SCRIPTS / "maintenance.py").read_text(encoding="utf-8-sig")
    assert source.index("enforce_direct_cli") < source.index("from common import")


def test_deletion_manifest_control_cli_remains_available() -> None:
    assert "deletion_manifest.py" in writer_policy.CONTROL_TOOL_ALLOWLIST
    completed = subprocess.run(
        [sys.executable, str(SCRIPTS / "deletion_manifest.py"), "--help"],
        cwd=ROOT,
        env=_legacy_override(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_canonical_source_export_help_remains_available() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "company_wiki.source_catalog.cli",
            "--config",
            "config/source_catalog.yaml",
            "export",
            "--help",
        ],
        cwd=ROOT,
        env=_legacy_override(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_canonical_extraction_quality_help_remains_available() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "company_wiki.source_catalog.cli",
            "--config",
            "config/source_catalog.yaml",
            "extraction-quality",
            "--help",
        ],
        cwd=ROOT,
        env=_legacy_override(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_canonical_source_entry_points_exclude_legacy_modules() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    entries = pyproject.split("[project.scripts]", 1)[1].split("[", 1)[0]
    assert "company_wiki.source_catalog" in entries
    assert "company_wiki.source_contract" in entries
    for forbidden in (
        "scripts.scheduler",
        "investment_judgment",
        "valuation_engine",
        "batch_assessment",
        "review_queue",
    ):
        assert forbidden not in entries


def test_windows_source_launchers_exclude_legacy_scheduler() -> None:
    launcher_text = "\n".join(
        (SCRIPTS / name).read_text(encoding="utf-8-sig")
        for name in (
            "source_catalog_worker.ps1",
            "source_catalog_worker_at_logon.ps1",
            "source_catalog_control.ps1",
            "source_catalog_control.cmd",
        )
    )
    assert "company_wiki.source_catalog.cli" in launcher_text
    assert "scheduler.py" not in launcher_text
    assert "full_pipeline.py" not in launcher_text
