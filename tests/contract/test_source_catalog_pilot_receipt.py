"""Contracts for machine-decidable Source Catalog pilot receipts."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


def _pilot_module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "source_catalog_pilot_check.py"
    spec = importlib.util.spec_from_file_location("source_catalog_pilot_check", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sample(**overrides):
    value = {
        "runtime_state": "running",
        "pid": 123,
        "heartbeat_age": 30,
        "worker_status": "normalizing",
        "progress_current": 1,
        "progress_total": 3,
        "progress_detail": "extracting Markdown",
        "production_workers": 1,
        "foreign_workers": 0,
        "pytest_temp_workers": 0,
        "production_supervisors": 0,
        "production_supervisor_pids": [],
        "foreign_supervisors": 0,
        "pytest_temp_supervisors": 0,
        "markdown_pending": 10,
        "markdown_completed": 5,
        "artifact_rows": 5,
        "current_path_elapsed_seconds": 30,
        "parser_pid": None,
        "parser_elapsed_seconds": None,
        "parser_timeout_seconds": None,
        "parser_ownership": None,
        "parse_timeout_total": 0,
        "last_parse_timeout_path": None,
        "loaded_code_fingerprint": "a" * 64,
        "current_code_fingerprint": "a" * 64,
        "code_match": True,
        "scan_interrupted_count": 2,
        "last_scan_run_id": "scan-baseline",
        "last_scan_new_errors": 0,
        "last_scan_known_quarantined": 1,
        "latest_running_scan": None,
        "operation_lock": "live",
        "last_export_progress_total": None,
        "last_export_duration_seconds": None,
        "last_cycle_at": None,
        "last_cycle_status": None,
        "last_cycle_error": None,
    }
    value.update(overrides)
    return value


def _summarize(
    samples,
    *,
    raw_changed=False,
    stockwiki_changed=False,
    database_check="ok",
    require_progress=False,
    required_export_progress_total=None,
    require_visible_scan_enumeration=False,
    require_supervisor=False,
    require_code_match=False,
):
    module = _pilot_module()
    before = {"samples": ["companies/a.pdf"], "hashes": ["a" * 64]}
    after = (
        {"samples": ["companies/a.pdf"], "hashes": ["b" * 64]}
        if raw_changed
        else before
    )
    stockwiki_before = {
        "available": True,
        "root": "StockWiki",
        "files": 10,
        "digest": "c" * 64,
    }
    stockwiki_after = (
        {**stockwiki_before, "digest": "d" * 64}
        if stockwiki_changed
        else stockwiki_before
    )
    return module.summarize_pilot(
        samples=samples,
        start_time=0,
        end_time=300,
        raw_baseline=before,
        raw_final=after,
        database_check={"quick_check": database_check, "elapsed_seconds": 1.0},
        stockwiki_baseline=stockwiki_before,
        stockwiki_final=stockwiki_after,
        require_progress=require_progress,
        required_export_progress_total=required_export_progress_total,
        require_visible_scan_enumeration=require_visible_scan_enumeration,
        require_supervisor=require_supervisor,
        require_code_match=require_code_match,
    )


def test_pilot_pass_requires_one_stable_worker_and_unchanged_raw_samples():
    receipt = _summarize(
        [
            _sample(markdown_pending=10, artifact_rows=5),
            _sample(
                markdown_pending=8,
                markdown_completed=7,
                artifact_rows=7,
                heartbeat_age=179,
            ),
        ]
    )

    assert receipt["pilot_pass"] is True
    assert receipt["production_worker_pids"] == [123]
    assert receipt["pending_delta"] == 2
    assert receipt["normalized_delta"] == 2
    assert receipt["artifact_delta"] == 2
    assert receipt["raw_sample_unchanged"] is True


def test_pilot_fails_after_heartbeat_exceeds_180_seconds():
    receipt = _summarize([_sample(), _sample(heartbeat_age=181)])

    assert receipt["pilot_pass"] is False
    assert receipt["raw_heartbeat_stale_count"] == 1
    assert receipt["heartbeat_stale_count"] == 1


def test_pilot_treats_bounded_active_path_as_soft_heartbeat_stale():
    receipt = _summarize(
        [
            _sample(),
            _sample(
                heartbeat_age=181,
                current_path="companies/slow.pdf",
                current_path_elapsed_seconds=181,
            ),
        ]
    )

    assert receipt["pilot_pass"] is True
    assert receipt["raw_heartbeat_stale_count"] == 1
    assert receipt["heartbeat_stale_count"] == 0
    assert receipt["same_path_max_seconds"] == 181
    assert receipt["last_good_sample"]["current_path"] == "companies/slow.pdf"


def test_pilot_fails_for_temp_worker_or_pid_change():
    temp = _summarize([_sample(), _sample(pytest_temp_workers=1)])
    changed_pid = _summarize([_sample(), _sample(pid=456)])

    assert temp["pilot_pass"] is False
    assert changed_pid["pilot_pass"] is False


def test_pilot_fails_when_raw_sample_hash_changes():
    receipt = _summarize([_sample(), _sample()], raw_changed=True)

    assert receipt["pilot_pass"] is False
    assert receipt["raw_sample_unchanged"] is False


def test_pilot_fails_when_any_sample_loses_the_production_worker():
    receipt = _summarize([_sample(), _sample(production_workers=0)])

    assert receipt["pilot_pass"] is False
    assert receipt["production_worker_min"] == 0


def test_pilot_fails_when_database_or_stockwiki_boundary_check_fails():
    database = _summarize(
        [_sample(), _sample(markdown_completed=6)],
        database_check="database disk image is malformed",
    )
    stockwiki = _summarize(
        [_sample(), _sample(markdown_completed=6)],
        stockwiki_changed=True,
    )

    assert database["first_failure"] == "database_quick_check_failed"
    assert stockwiki["first_failure"] == "stockwiki_changed_or_unavailable"
    assert database["pilot_pass"] is False
    assert stockwiki["pilot_pass"] is False


def test_pilot_fails_only_for_new_scan_errors_created_inside_the_window():
    known_before_window = _summarize([_sample(), _sample()])
    new_error = _summarize(
        [
            _sample(),
            _sample(
                last_scan_run_id="scan-new",
                last_scan_new_errors=1,
                last_scan_known_quarantined=1,
            ),
        ]
    )

    assert known_before_window["pilot_pass"] is True
    assert known_before_window["new_scan_error_count"] == 0
    assert new_error["pilot_pass"] is False
    assert new_error["first_failure"] == "scan_new_errors_nonzero"
    assert new_error["new_scan_error_count"] == 1


def test_pilot_can_require_progress_and_enforces_same_path_limit():
    no_progress = _summarize([_sample(), _sample()], require_progress=True)
    timed_out = _summarize(
        [_sample(), _sample(current_path_elapsed_seconds=900)]
    )
    isolated_slow = _summarize(
        [
            _sample(),
            _sample(
                current_path="companies/slow.pdf",
                current_path_elapsed_seconds=1200,
                parser_pid=4321,
                parser_elapsed_seconds=1200,
                parser_timeout_seconds=3600,
                parser_ownership="windows_job",
            ),
        ]
    )
    parser_restarted = _summarize(
        [
            _sample(current_path="companies/retry.pdf", parser_pid=100),
            _sample(current_path="companies/retry.pdf", parser_pid=200),
        ]
    )
    timeout_increased = _summarize(
        [_sample(parse_timeout_total=0), _sample(parse_timeout_total=1)]
    )

    assert no_progress["first_failure"] == "throughput_below_required_threshold"
    assert no_progress["pilot_pass"] is False
    assert timed_out["first_failure"] == "same_path_timeout"
    assert timed_out["pilot_pass"] is False
    assert isolated_slow["pilot_pass"] is True
    assert parser_restarted["first_failure"] == "same_path_parser_restarted"
    assert timeout_increased["first_failure"] == "normalization_timeout_delta_nonzero"


def test_pilot_can_require_the_worker_to_have_loaded_current_code():
    matched = _summarize([_sample(), _sample()], require_code_match=True)
    mismatched = _summarize(
        [
            _sample(),
            _sample(
                current_code_fingerprint="b" * 64,
                code_match=False,
            ),
        ],
        require_code_match=True,
    )

    assert matched["pilot_pass"] is True
    assert matched["loaded_code_fingerprints"] == ["a" * 64]
    assert matched["current_code_fingerprints"] == ["a" * 64]
    assert mismatched["first_failure"] == "worker_code_mismatch_or_unknown"


def test_dry_run_arguments_are_order_independent(monkeypatch, capsys):
    module = _pilot_module()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "source_catalog_pilot_check.py",
            "--dry-run",
            "--duration-minutes",
            "5",
            "--interval-seconds",
            "30",
        ],
    )

    assert module.main() == 0
    assert "5 minutes at 30s intervals" in capsys.readouterr().out


def test_pilot_cli_help_exits_without_starting_default_pilot():
    script = Path("scripts/source_catalog_pilot_check.py").resolve()
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=5,
        check=False,
    )
    assert result.returncode == 0
    assert "--require-supervisor" in result.stdout


def test_pilot_cli_rejects_unknown_arguments():
    script = Path("scripts/source_catalog_pilot_check.py").resolve()
    result = subprocess.run(
        [sys.executable, str(script), "--not-a-real-option"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=5,
        check=False,
    )
    assert result.returncode == 2
    assert "unrecognized arguments" in result.stderr


def test_sample_status_decodes_worker_json_as_utf8_sig(monkeypatch, tmp_path):
    module = _pilot_module()
    captured = {}

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=json.dumps({"current_path": "companies/中文.pdf"}),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    status = module.sample_status(tmp_path)

    assert status["current_path"] == "companies/中文.pdf"
    assert captured["encoding"] == "utf-8-sig"
    assert captured["errors"] == "replace"


def test_pilot_can_require_new_export_and_visible_scan_enumeration_contracts():
    valid = _summarize(
        [
            _sample(
                worker_status="exporting",
                progress_total=12,
                progress_detail="building semantic duplicate groups",
            ),
            _sample(
                worker_status="scanning",
                progress_total=237,
                progress_detail="enumerating root company_raw",
                latest_running_scan="present",
                markdown_completed=6,
            ),
        ],
        required_export_progress_total=12,
        require_visible_scan_enumeration=True,
    )
    missing_export = _summarize(
        [_sample(), _sample(markdown_completed=6)],
        required_export_progress_total=12,
    )
    hidden_scan = _summarize(
        [
            _sample(worker_status="exporting", progress_total=12),
            _sample(
                worker_status="scanning",
                progress_detail="enumerating root company_raw",
                latest_running_scan=None,
                markdown_completed=6,
            ),
        ],
        required_export_progress_total=12,
        require_visible_scan_enumeration=True,
    )

    assert valid["pilot_pass"] is True
    assert valid["export_progress_contract_observed"] is True
    assert valid["scan_enumeration_running_visible"] is True
    assert missing_export["first_failure"] == (
        "required_export_progress_contract_not_observed"
    )
    assert hidden_scan["first_failure"] == (
        "scan_enumeration_running_record_not_visible"
    )


def test_pilot_accepts_persisted_export_contract_when_fast_export_is_missed():
    receipt = _summarize(
        [
            _sample(),
            _sample(
                markdown_completed=6,
                last_export_progress_total=12,
                last_export_duration_seconds=0.5,
            ),
        ],
        required_export_progress_total=12,
    )

    assert receipt["pilot_pass"] is True
    assert receipt["export_progress_totals_observed"] == [12]


def test_pilot_can_require_one_stable_production_supervisor():
    valid = _summarize(
        [
            _sample(production_supervisors=1, production_supervisor_pids=[100]),
            _sample(
                production_supervisors=1,
                production_supervisor_pids=[100],
                markdown_completed=6,
            ),
        ],
        require_supervisor=True,
    )
    missing = _summarize(
        [
            _sample(production_supervisors=1, production_supervisor_pids=[100]),
            _sample(production_supervisors=0, markdown_completed=6),
        ],
        require_supervisor=True,
    )
    foreign = _summarize(
        [
            _sample(production_supervisors=1, production_supervisor_pids=[100]),
            _sample(
                production_supervisors=1,
                production_supervisor_pids=[100],
                foreign_supervisors=1,
                markdown_completed=6,
            ),
        ],
        require_supervisor=True,
    )

    assert valid["pilot_pass"] is True
    assert valid["production_supervisor_min"] == 1
    assert valid["production_supervisor_max"] == 1
    assert missing["first_failure"] == "production_supervisor_count_not_one"
    assert missing["recommended_next_phase"] == "WR-10"
    assert foreign["first_failure"] == "foreign_supervisor_present"


def test_pilot_fails_if_supervisor_pid_changes_while_count_remains_one():
    receipt = _summarize(
        [
            _sample(production_supervisors=1, production_supervisor_pids=[100]),
            _sample(
                production_supervisors=1,
                production_supervisor_pids=[200],
                markdown_completed=6,
            ),
        ],
        require_supervisor=True,
    )

    assert receipt["first_failure"] == "production_supervisor_pid_changed"
    assert receipt["recommended_next_phase"] == "WR-10"


def test_pilot_reports_repeated_cycle_failure_before_generic_zero_throughput():
    error = "CatalogOperationLockedError: catalog operation already running: pid=1784"
    receipt = _summarize(
        [
            _sample(
                last_cycle_at=1_000.0,
                last_cycle_status="failed",
                last_cycle_error=error,
            ),
            _sample(
                last_cycle_at=1_030.0,
                last_cycle_status="failed",
                last_cycle_error=error,
            ),
            _sample(
                last_cycle_at=1_060.0,
                last_cycle_status="failed",
                last_cycle_error=error,
            ),
        ],
        require_progress=True,
    )

    assert receipt["first_failure"] == "repeated_cycle_failure"
    assert receipt["repeated_cycle_failure_count"] == 3
    assert receipt["repeated_cycle_error"] == error
