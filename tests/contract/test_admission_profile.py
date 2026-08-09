"""WU-503 RED/audit tests: admission profile conformance (ADM-01..10).

Same candidate + different root_id => identical decision.  Only RootPolicy
permission flags change the outcome.  No "Dropbox relaxes / company_raw
privilege" path may exist.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.admission import evaluate_candidate  # noqa: E402


def _candidate(**overrides) -> dict:
    base = {
        "canonical_entity_id": "ent-1",
        "security_id": "US123",
        "document_kind": "annual_report",
        "fiscal_year": "2025",
        "period_end": "2025-12-31",
        "content_sha256": "c" * 64,
    }
    base.update(overrides)
    return base


def _admit(**kwargs):
    return evaluate_candidate(_candidate(), policy_allows_filing=True,
                              profile_allows_filing=True, content_hash_matches=True,
                              **kwargs)


def test_adm01_same_candidate_different_root_same_decision():
    # the decision function never receives a root_id at all
    assert _admit().admitted is True


def test_adm02_policy_denied():
    decision = evaluate_candidate(
        _candidate(), policy_allows_filing=False, profile_allows_filing=True,
        content_hash_matches=True,
    )
    assert not decision.admitted
    assert "policy_denied" in decision.reason


def test_adm03_profile_denied_generic():
    decision = evaluate_candidate(
        _candidate(), policy_allows_filing=True, profile_allows_filing=False,
        content_hash_matches=True,
    )
    assert not decision.admitted
    assert "non_filing_kind" in decision.reason


def test_adm04_hash_mismatch_rejected():
    decision = evaluate_candidate(
        _candidate(), policy_allows_filing=True, profile_allows_filing=True,
        content_hash_matches=False,
    )
    assert not decision.admitted
    assert "content_hash_mismatch" in decision.reason


def test_adm05_identity_missing_rejected():
    decision = evaluate_candidate(
        {k: v for k, v in _candidate().items() if k != "security_id"},
        policy_allows_filing=True, profile_allows_filing=True,
        content_hash_matches=True,
    )
    assert not decision.admitted
    assert "identity_missing" in decision.reason


def test_adm06_status_not_active_rejected():
    assert not _admit(status="retired").admitted
    assert not _admit(status="quarantined").admitted


def test_adm07_period_missing_rejected():
    decision = evaluate_candidate(
        {k: v for k, v in _candidate().items() if k != "period_end"},
        policy_allows_filing=True, profile_allows_filing=True,
        content_hash_matches=True,
    )
    assert not decision.admitted
    assert "period_missing" in decision.reason


def test_adm08_no_root_privilege_path():
    """The decision function signature has no root_id parameter at all."""
    import inspect

    signature = inspect.signature(evaluate_candidate)
    assert "root_id" not in signature.parameters


def test_adm09_rejected_reason_machine_readable():
    decision = evaluate_candidate(
        _candidate(), policy_allows_filing=False, profile_allows_filing=False,
        content_hash_matches=False,
    )
    reasons = decision.reason.split("|")
    assert "policy_denied" in reasons and "non_filing_kind" in reasons
    assert "content_hash_mismatch" in reasons


def test_adm10_deterministic():
    a = _admit()
    b = _admit()
    assert (a.admitted, a.reason) == (b.admitted, b.reason)
