"""WU-904 RED/audit tests: explicit restore (REST-01..06)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.restore import (  # noqa: E402
    restore_asset,
    revert_restore,
)

GATES = {
    "file_hash_matches": True,
    "v2_complete": True,
    "provenance_ok": True,
    "policy_allows": True,
    "reviewer": "reviewer-1",
    "reason": "explicit restore after remediation",
    "original_retire_reason": "retired by 2026 cleanup",
    "policy_hash": "pol-1",
}


def test_rest01_missing_provenance_rejected():
    gates = dict(GATES, provenance_ok=False)
    receipt, rejection = restore_asset(document_id="d1", **gates)
    assert receipt is None
    assert "missing_provenance" in rejection.reasons


def test_rest02_hash_changed_rejected():
    gates = dict(GATES, file_hash_matches=False)
    receipt, rejection = restore_asset(document_id="d1", **gates)
    assert receipt is None
    assert "file_hash_changed" in rejection.reasons


def test_rest03_root_policy_denied():
    gates = dict(GATES, policy_allows=False)
    receipt, rejection = restore_asset(document_id="d1", **gates)
    assert receipt is None
    assert "root_policy_denied" in rejection.reasons


def test_rest04_fuzzy_batch_rejected():
    gates = dict(GATES, allow_fuzzy=True)
    receipt, rejection = restore_asset(document_id="d1", **gates)
    assert receipt is None
    assert "fuzzy_batch_restore_forbidden" in rejection.reasons
    # fuzzy target with comma is also rejected
    receipt, rejection = restore_asset(document_id="d1,d2", **GATES)
    assert receipt is None
    assert "must_target_one_document_id" in rejection.reasons


def test_rest05_retired_auto_scan_never_restores():
    """restore is explicit-only: no code path auto-restores retired assets."""
    receipt, rejection = restore_asset(document_id="d1", **GATES)
    assert receipt is not None  # explicit restore works
    # a scanner-driven path would call with reviewer="" → rejected
    auto = dict(GATES, reviewer="")
    receipt, rejection = restore_asset(document_id="d1", **auto)
    assert receipt is None
    assert "reviewer_required" in rejection.reasons


def test_rest06_receipt_preserves_history_and_can_revert():
    receipt, rejection = restore_asset(document_id="d1", **GATES)
    assert receipt is not None
    assert receipt.original_retire_reason == "retired by 2026 cleanup"
    reverted = revert_restore(receipt)
    assert reverted.reverted is True
    assert reverted.original_retire_reason == receipt.original_retire_reason
