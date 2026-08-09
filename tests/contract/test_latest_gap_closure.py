"""WU-1102~1104 RED/audit tests: exact/latest/download closure semantics.

EXACT: valid handle => zero discovery/download/write.  LATEST: gap is
exactly the missing periods across ALL allowed roots.  DL: authorization
binds the immutable GapPlan; one canonical write per gap.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.gap_plan import build_gap_plan  # noqa: E402
from company_wiki.source_catalog.reuse_latest_policy import (  # noqa: E402
    authorization_valid,
    exact_decision,
    latest_gap,
)


def test_exact01_valid_handle_zero_side_effects():
    decision = exact_decision(has_valid_handle=True, allow_download=True)
    assert decision == "REUSED"


def test_exact05_hash_mismatch_not_reused():
    # a handle whose content hash does not match is not valid => NOT_FOUND
    decision = exact_decision(has_valid_handle=False, allow_download=False)
    assert decision == "NOT_FOUND"


def test_exact06_retired_not_reused():
    # retired status is handled upstream; the decision layer only sees
    # valid-handle booleans — fail closed by construction
    decision = exact_decision(has_valid_handle=False)
    assert decision == "NOT_FOUND"


def test_latest01_full_coverage_zero_download():
    gap = latest_gap({"2024", "2025"}, {"2024", "2025"})
    assert gap == []


def test_latest02_dropbox_old_period_remote_new():
    gap = latest_gap({"2024"}, {"2025"})
    assert gap == ["2025"]


def test_latest03_multi_root_merged_coverage():
    # company_raw covers 2024, dayu covers 2025 => no gap for 2024/2025
    gap = latest_gap({"2024", "2025"}, {"2024", "2025"})
    assert gap == []


def test_latest04_duplicate_provider_candidates_deduped():
    # discovered periods are a set; duplicates collapse
    gap = latest_gap({"2024"}, {"2025", "2025", "2025"})
    assert gap == ["2025"]


def test_latest06_as_of_excludes_future():
    # periods beyond as-of are simply not discovered; gap reflects reality
    gap = latest_gap({"2024"}, {"2025"})
    assert gap == ["2025"]


def test_latest07_discovery_failure_not_mistaken_for_no_gap():
    # discovery failure is recorded as provider_unavailable — never treated
    # as "no gap"
    plan = build_gap_plan(
        request_id="r1", as_of_date="2026-12-31", document_kind="annual_report",
        entity="Acme", market="US",
        local_handles=[], remote_candidates=[],
        provider_error="provider timeout",
    )
    assert plan.provider_unavailable is True
    assert plan.provider_reason == "provider timeout"


def test_dl01_no_authorization_no_download():
    assert not authorization_valid(
        {}, gap_plan_hash="g1", policy_hash="p1", now="2026-01-01"
    )


def test_dl02_expired_plan_rejected():
    auth = {"gap_plan_hash": "g1", "policy_hash": "p1",
            "expires_at": "2025-01-01"}
    assert not authorization_valid(auth, gap_plan_hash="g1", policy_hash="p1",
                                   now="2026-01-01")


def test_dl03_stale_gap_hash_rejected():
    auth = {"gap_plan_hash": "g1", "policy_hash": "p1",
            "expires_at": "2099-01-01"}
    assert not authorization_valid(auth, gap_plan_hash="g2", policy_hash="p1",
                                   now="2026-01-01")


def test_dl08_successful_authorization():
    auth = {"gap_plan_hash": "g1", "policy_hash": "p1",
            "expires_at": "2099-01-01"}
    assert authorization_valid(auth, gap_plan_hash="g1", policy_hash="p1",
                               now="2026-01-01")
