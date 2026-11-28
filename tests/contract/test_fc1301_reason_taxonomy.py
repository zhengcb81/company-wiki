"""Legacy stage/metric readers and owner-specific failure reasons stay distinct."""

from pathlib import Path

from company_wiki.source_catalog import observability
from company_wiki.source_catalog.observability import (
    MetricsCollector,
    REASONS,
    REASON_TAXONOMY_VERSION,
    STAGES_BY_REASON,
    StageEvent,
)
from company_wiki.source_contract.source_version import SourceReadError

# Legacy codes from FC-1301 are still wire values, even though other owner
# contracts use their own typed status and diagnostic vocabulary.
_LEGACY_CODES = {
    "one_verified_exact_identity",
    "multiple_verified_exact_identities",
    "exact_identity_conflicts_with_market_or_exchange_hint",
    "no_verified_identity_candidate",
    "one_unique_strong_fuzzy_identity",
    "fuzzy_candidates_require_user_selection",
    "identity_mismatch_market_or_security_id",
    "one_existing_source_matches_provider_identity",
    "latest_existing_source_matches_provider_identity",
    "multiple_existing_sources_match_provider_identity",
    "one_existing_source_satisfies_semantic_request",
    "latest_existing_source_satisfies_semantic_request",
    "multiple_existing_sources_match_semantic_request",
    "matching_sources_have_unknown_published_date",
    "no_runtime_policy",
    "stale_policy_hash",
}


def test_taxonomy_version_and_released_reason_values_stay_compatible():
    assert REASON_TAXONOMY_VERSION == "1.1"
    assert _LEGACY_CODES <= REASONS.keys()
    assert _LEGACY_CODES <= STAGES_BY_REASON.keys()


def test_stage_collector_accepts_attributed_release_codes():
    collector = MetricsCollector()
    for reason in sorted(_LEGACY_CODES):
        for stage in STAGES_BY_REASON[reason]:
            assert collector.record_stage_event(StageEvent(stage=stage, reason=reason))
    assert {row["reason"] for row in collector.snapshot().raw} == _LEGACY_CODES


def test_owner_reason_does_not_need_a_legacy_metric_assignment():
    error = SourceReadError("unavailable", "verify_deadline_exceeded")
    collector = MetricsCollector()

    assert error.reason == "verify_deadline_exceeded"
    assert not collector.record_reason(error.reason)
    assert not collector.record_stage_event(StageEvent(stage="resolve", reason=error.reason))
    assert not collector.snapshot().raw


def test_real_registry_values_are_documented_and_ship_from_this_owner():
    expected = Path(__file__).resolve().parents[2] / "src/company_wiki/source_catalog/observability.py"
    assert Path(observability.__file__).resolve() == expected.resolve()
    assert all(isinstance(description, str) and description.strip() for description in REASONS.values())
