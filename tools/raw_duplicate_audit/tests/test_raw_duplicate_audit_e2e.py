"""E2E against the real production catalog, strictly read-only.

No candidates is a legal outcome; nothing here fabricates a saving.  The two
reports written into ``.planning/n5-raw-duplicate-audit/`` are the small
artefacts the lane keeps; every machine-absolute path goes to a temp side file
that is never committed.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from raw_duplicate_audit.assessment import run_assessment
from raw_duplicate_audit.catalog import load_inputs
from raw_duplicate_audit.core import hydrate_risk, sha256_file
from raw_duplicate_audit.report import report_contains_forbidden_claims

pytestmark = [pytest.mark.slow, pytest.mark.real_data, pytest.mark.e2e]

REPO_ROOT = Path(__file__).resolve().parents[3]
PLANNING_DIR = REPO_ROOT / ".planning" / "n5-raw-duplicate-audit"
SOURCE_REPO = Path(
    os.environ.get("N5_SOURCE_REPO", "C:/Users/郑曾波/Projects/company-wiki")
)
CONFIG_PATH = SOURCE_REPO / "config" / "source_catalog.yaml"
DATABASE_PATH = SOURCE_REPO / ".source_catalog" / "catalog.sqlite3"

SCAN_REPORT_PATH = PLANNING_DIR / "raw_duplicate_report_scan.json"
VERIFY_REPORT_PATH = PLANNING_DIR / "raw_duplicate_report_e2e.json"

MAX_GROUPS = 3
MAX_READ_BYTES = 512 * 1024 * 1024
DEADLINE_SECONDS = 300.0


def _require_production() -> None:
    if not CONFIG_PATH.is_file():
        pytest.skip(f"production config not available: {CONFIG_PATH}")
    if not DATABASE_PATH.is_file():
        pytest.skip(f"production catalog not available: {DATABASE_PATH}")


def _snapshot(paths: list[Path]) -> dict[str, tuple[str, int, int]]:
    snapshot: dict[str, tuple[str, int, int]] = {}
    for path in paths:
        try:
            stat_result = os.stat(path)
        except OSError:
            continue
        snapshot[str(path)] = (
            sha256_file(path),
            int(stat_result.st_size),
            int(stat_result.st_mtime_ns),
        )
    return snapshot


def _targets_from(scan_report: dict, root_paths: dict[str, Path]) -> list[Path]:
    """Every registered path of the groups verify will actually open."""
    targets: list[Path] = []
    seen: set[str] = set()
    for group in scan_report.get("duplicate_groups", [])[:MAX_GROUPS]:
        for locator in group.get("locators", []):
            root = root_paths.get(locator["root_id"])
            if root is None:
                continue
            path = Path(root) / locator["relative_path"]
            if hydrate_risk(path):
                continue
            key = str(path).lower() if os.name == "nt" else str(path)
            if key in seen:
                continue
            seen.add(key)
            targets.append(path)
    return targets


def test_production_catalog_duplicate_assessment_is_read_only_and_bounded():
    _require_production()
    PLANNING_DIR.mkdir(parents=True, exist_ok=True)
    inputs = load_inputs(CONFIG_PATH)
    root_paths = {root.root_id: Path(root.path) for root in inputs.roots}

    config_sha_before = sha256_file(CONFIG_PATH)
    database_sha_before = sha256_file(DATABASE_PATH)
    database_stat_before = (
        DATABASE_PATH.stat().st_size,
        DATABASE_PATH.stat().st_mtime_ns,
    )
    catalog_dir = DATABASE_PATH.parent
    catalog_listing_before = sorted(item.name for item in catalog_dir.iterdir())

    scan_report = run_assessment(
        mode="scan",
        config_path=CONFIG_PATH,
        output_path=SCAN_REPORT_PATH,
        max_groups=MAX_GROUPS,
        max_read_bytes=0,
        deadline_seconds=DEADLINE_SECONDS,
        overwrite=True,
    )
    assert scan_report["status"] in {"succeeded", "partial"}, scan_report["error_code"]
    assert scan_report["read_bytes"] == 0
    assert scan_report["deleted_bytes"] == 0

    targets = _targets_from(scan_report, root_paths)
    before = _snapshot(targets)

    local_output = Path(tempfile.mkdtemp(prefix="n5-raw-dup-")) / "local_paths.json"
    verify_report = run_assessment(
        mode="verify",
        config_path=CONFIG_PATH,
        output_path=VERIFY_REPORT_PATH,
        max_groups=MAX_GROUPS,
        max_read_bytes=MAX_READ_BYTES,
        deadline_seconds=DEADLINE_SECONDS,
        overwrite=True,
        local_output_path=local_output,
    )

    after = _snapshot(targets)

    print(
        "N5-RAW-DUP E2E receipt:"
        f" candidate_groups={verify_report['counts']['candidate_groups']}"
        f" upper_bound={verify_report['logical_duplicate_bytes_upper_bound']}"
        f" verified={verify_report['verified_duplicate_bytes']}"
        f" read_bytes={verify_report['read_bytes']}"
        f" read_files={verify_report['read_files']}"
        f" elapsed={verify_report['elapsed_seconds']}s"
        f" limits_hit={verify_report['limits_hit']}"
        f" status={verify_report['status']}"
    )

    assert verify_report["status"] in {"succeeded", "partial"}
    assert verify_report["deleted_bytes"] == 0
    assert verify_report["protected_unchanged"] is True
    assert verify_report["read_bytes"] <= MAX_READ_BYTES
    assert verify_report["elapsed_seconds"] <= DEADLINE_SECONDS + 60
    assert verify_report["counts"]["candidate_groups"] >= 0
    assert isinstance(verify_report["logical_duplicate_bytes_upper_bound"], int)
    assert report_contains_forbidden_claims(verify_report) == []

    assert sha256_file(CONFIG_PATH) == config_sha_before
    assert sha256_file(DATABASE_PATH) == database_sha_before
    assert (
        DATABASE_PATH.stat().st_size,
        DATABASE_PATH.stat().st_mtime_ns,
    ) == database_stat_before
    assert sorted(item.name for item in catalog_dir.iterdir()) == catalog_listing_before

    assert before == after, "an original changed during the read-only assessment"

    for report_path in (SCAN_REPORT_PATH, VERIFY_REPORT_PATH):
        assert report_path.is_file()
        assert report_path.stat().st_size <= 1024 * 1024
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        assert payload["schema_version"] == "raw-duplicate-assessment/1"
        assert payload["truncated"]["detail_rows"] <= 5000

    assert local_output.is_file()
    local = json.loads(local_output.read_text(encoding="utf-8"))
    assert local["schema_version"] == "raw-duplicate-assessment-local-paths/1"
    assert Path(local["database_path"]) == DATABASE_PATH
    if not targets:
        pytest.skip("no readable duplicate target in production (legal real result)")
    assert any(
        member["absolute_path"]
        for group in local["groups"]
        for member in group["members"]
    )
    assert str(local["database_path"]) not in VERIFY_REPORT_PATH.read_text(
        encoding="utf-8"
    )
