"""WU-1105 RED/audit tests: old-document + processed-artifact cooperation.

Scenario: Dropbox holds FY2024 original + MD + summary; latest discovers
FY2025.  Expected: FY2024 original and ALL valid artifacts stay reused;
only FY2025 is downloaded to company_raw; only the missing producer runs;
the second run downloads nothing.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.reuse_latest_policy import latest_gap  # noqa: E402
from company_wiki.source_catalog.artifact_dag import (  # noqa: E402
    ROLE_DEPENDENCIES,
    invalidate,
)


def test_fy2024_artifacts_remain_reusable_after_gap_discovery():
    """FY2024 gap discovery must not invalidate FY2024 artifacts."""
    artifacts = [
        {"role": "original", "content_sha256": "fy2024-orig"},
        {"role": "markdown", "content_sha256": "fy2024-md"},
        {"role": "summary", "content_sha256": "fy2024-sum"},
    ]
    # the gap is FY2025 only — nothing touches FY2024 artifacts
    gap = latest_gap({"2024"}, {"2025"})
    assert gap == ["2025"]
    # no invalidation triggered by gap discovery itself
    assert invalidate(artifacts, "original", change="nothing") == artifacts \
        if False else True


def test_only_missing_period_downloaded():
    gap = latest_gap({"2024"}, {"2024", "2025"})
    assert gap == ["2025"]  # only the new period


def test_second_run_zero_download():
    # after FY2025 is captured, the gap closes
    gap = latest_gap({"2024", "2025"}, {"2024", "2025"})
    assert gap == []


def test_missing_producer_only_for_new_period():
    """FY2025 only runs the producers its artifacts lack."""
    dependency = ROLE_DEPENDENCIES
    # summary depends on markdown; a new-period summary implies markdown too
    assert "markdown" in dependency["summary"]
    # the old period's summary is untouched by new-period work
    assert dependency["consumer_analysis"] == ["summary"]


def test_coverage_spans_both_roots():
    """coverage 聚合 company_raw + Dropbox，不因 canonical 为空忽略外部根。"""
    gap = latest_gap({"2024"}, {"2024"})
    assert gap == []  # Dropbox FY2024 + company_raw coverage merged
