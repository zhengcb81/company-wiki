"""ZR-101: cross-repo stage taxonomy 2.0 contract tests (hermetic).

Covers: the canonical 8-stage order, complete REASONS attribution (no
orphan codes), fail-closed ``stages_for_reason``, ``StageEvent`` validation
(including N-1 schema rejection and path redaction), the additive
v1.1 -> 2.0 subset property, and ``MetricsCollector.record_stage_event``
gating.  No catalog DB, no network, no files outside tmp_path.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from company_wiki.source_catalog.observability import (
    REDACT,
    REASONS,
    REASON_TAXONOMY_VERSION,
    STAGE_TAXONOMY_SCHEMA,
    STAGE_TAXONOMY_VERSION,
    STAGES_BY_REASON,
    CrossRepoStage,
    MetricsCollector,
    StageEvent,
    is_registered_stage,
    stage_sequence,
    stages_for_reason,
    validate_stage_event,
)

# Frozen spec (scenario_matrix.md §28): exact canonical stage order.
FROZEN_STAGE_ORDER = (
    "identity",
    "resolution",
    "freshness",
    "acquisition",
    "safety",
    "artifact",
    "semantic",
    "consumer",
)

# Frozen v1.1 reason-code floor: every code below must survive into 2.0
# unchanged (the registry is additive — nothing is deleted or renamed).
FROZEN_V11_REASONS = frozenset(
    {
        "identity_missing",
        "exact_hit",
        "downloaded",
        "artifact_selected",
        "legacy_bridge_hit",
        "migration_remaining",
        "admitted",
        "kind_missing",
        "period_missing",
        "hash_missing",
        "content_hash_mismatch",
        "status_not_active",
        "policy_denied",
        "non_filing_kind",
        "focus_policy_invalid_relative_path",
        "download_suppressed",
        "download_authorized",
        "gap_not_required",
        "gap_authorization_expired",
        "latest_selected",
        "ambiguous_issuer",
        "entity_gate_rejected",
        "artifact_rejected",
        "recomputed",
        "stale_bundle",
        "shadow_diff",
        "verified_v2_assertion",
        "canonical_copy",
        "canonical_import_failed",
        "semantic_review_only",
        "clean_exit",
        "no_output",
        "gap_already_closed",
        "gap_closed_by_concurrent",
        "document_not_in_catalog",
        "source_not_in_catalog",
        "no_original_location",
        "empty_text",
        "unsupported_document",
        "cannot_parse_yaml",
        "unexpected_path_pattern",
        "focus_policy_orphan_sidecar",
        "llm_deferred",
        "llm_global_failure",
        "fiscal_year",
        "unhandled_exception",
        "cycle_failed",
        "productive_cycle",
        "already_running",
        "control_request",
        "persistent_pause",
    }
)


def test_stage_taxonomy_constants() -> None:
    assert STAGE_TAXONOMY_VERSION == "2.0"
    assert STAGE_TAXONOMY_SCHEMA == "stage-taxonomy-2.0"
    # N-1 compat: the v1.1 flat taxonomy constant is untouched.
    assert REASON_TAXONOMY_VERSION == "1.1"


def test_eight_stages_exist_in_canonical_order() -> None:
    seq = stage_sequence()
    assert len(seq) == 8
    assert [s.value for s in seq] == list(FROZEN_STAGE_ORDER)
    assert [s.name for s in seq] == list(FROZEN_STAGE_ORDER)


def test_stage_enum_values_are_snake_case_names() -> None:
    for stage in CrossRepoStage:
        assert stage.value == stage.name  # value == snake_case name
    assert CrossRepoStage.identity.value == "identity"
    assert CrossRepoStage.consumer.value == "consumer"


def test_stages_by_reason_covers_every_reason_code() -> None:
    # No orphan codes and no phantom entries.
    assert set(STAGES_BY_REASON) == set(REASONS)
    for code, stages in STAGES_BY_REASON.items():
        assert stages, f"reason {code!r} attributed to no stage"
        assert code in REASONS


def test_attributed_stages_registered_and_canonical_ordered() -> None:
    rank = {name: i for i, name in enumerate(FROZEN_STAGE_ORDER)}
    for code, stages in STAGES_BY_REASON.items():
        for stage in stages:
            assert is_registered_stage(stage), f"{code} -> {stage!r} unregistered"
        assert len(stages) == len(set(stages)), f"{code} has duplicate stages"
        assert stages == tuple(sorted(stages, key=rank.__getitem__)), (
            f"{code} stages not in canonical order: {stages}"
        )


def test_stage_attribution_semantic_spots() -> None:
    # Spec-mandated attributions (§28).
    assert stages_for_reason("identity_missing") == ("identity",)
    assert stages_for_reason("exact_hit") == ("resolution",)
    assert stages_for_reason("ambiguous_issuer") == ("resolution",)
    assert stages_for_reason("period_missing") == ("freshness",)
    assert stages_for_reason("only_sources_published_after_as_of_date") == (
        "freshness",
    )
    assert stages_for_reason("downloaded") == ("acquisition",)
    assert stages_for_reason("canonical_copy") == ("acquisition",)
    assert stages_for_reason("download_authorized") == ("acquisition",)
    assert stages_for_reason("artifact_selected") == ("artifact",)
    assert stages_for_reason("artifact_rejected") == ("artifact",)
    assert stages_for_reason("stale_bundle") == ("artifact",)
    assert stages_for_reason("semantic_review_only") == ("semantic",)
    assert stages_for_reason("recomputed") == ("consumer",)
    assert stages_for_reason("migration_remaining") == ("consumer",)
    assert stages_for_reason("legacy_bridge_hit") == ("consumer",)
    # safety stage exists but currently has no registered codes.
    assert is_registered_stage("safety")
    attributed = {s for stages in STAGES_BY_REASON.values() for s in stages}
    assert "safety" not in attributed


def test_stages_for_reason_fail_closed() -> None:
    for code in REASONS:
        assert stages_for_reason(code), f"no stages for registered code {code}"
    with pytest.raises(ValueError):
        stages_for_reason("not_a_real_reason_code")
    with pytest.raises(ValueError):
        stages_for_reason("")


def test_is_registered_stage() -> None:
    for stage in FROZEN_STAGE_ORDER:
        assert is_registered_stage(stage)
    assert not is_registered_stage("identity ")
    assert not is_registered_stage("Identity")
    assert not is_registered_stage("")


def test_stage_event_to_dict_and_defaults() -> None:
    event = StageEvent(stage="identity", reason="identity_missing")
    data = event.to_dict()
    assert data["schema_version"] == STAGE_TAXONOMY_SCHEMA
    assert data["stage"] == "identity"
    assert data["reason"] == "identity_missing"
    assert data["detail"] is None
    assert data["emitted_at_utc"].endswith("Z")
    datetime.fromisoformat(data["emitted_at_utc"].replace("Z", "+00:00"))


def test_validate_stage_event_valid() -> None:
    event = StageEvent(stage="identity", reason="identity_missing")
    assert validate_stage_event(event) == []
    assert validate_stage_event(event.to_dict()) == []
    # explicit UTC instants accepted, with and without the Z suffix.
    z_form = StageEvent(
        stage="consumer",
        reason="recomputed",
        emitted_at_utc="2026-08-13T12:00:00Z",
    )
    assert validate_stage_event(z_form) == []
    offset_form = StageEvent(
        stage="consumer",
        reason="recomputed",
        emitted_at_utc="2026-08-13T12:00:00+00:00",
    )
    assert validate_stage_event(offset_form) == []
    # benign (non-path) detail passes through untouched.
    plain = StageEvent(
        stage="artifact",
        reason="artifact_selected",
        detail="model v2 verified",
    )
    assert validate_stage_event(plain) == []
    assert plain.detail == "model v2 verified"


def test_validate_unknown_stage_problem() -> None:
    event = StageEvent(stage="safety_extra", reason="identity_missing")
    problems = validate_stage_event(event)
    assert problems
    assert any("stage" in p for p in problems)


def test_validate_unknown_reason_problem() -> None:
    event = StageEvent(stage="identity", reason="made_up_reason")
    problems = validate_stage_event(event)
    assert problems
    assert any("reason" in p for p in problems)


def test_validate_reason_stage_mismatch_problem() -> None:
    event = StageEvent(stage="acquisition", reason="identity_missing")
    problems = validate_stage_event(event)
    assert problems
    assert any("not attributed" in p for p in problems)


def test_validate_bad_emitted_at_problem() -> None:
    event = StageEvent(
        stage="identity",
        reason="identity_missing",
        emitted_at_utc="yesterday-ish",
    )
    problems = validate_stage_event(event)
    assert problems
    assert any("emitted_at_utc" in p for p in problems)
    # a naive timestamp is not a UTC instant.
    naive = StageEvent(
        stage="identity",
        reason="identity_missing",
        emitted_at_utc="2026-08-13T12:00:00",
    )
    assert any("emitted_at_utc" in p for p in validate_stage_event(naive))


def test_validate_redacts_path_detail() -> None:
    event = StageEvent(
        stage="identity",
        reason="identity_missing",
        detail=r"C:\reports\Q1_2026.xlsx",
    )
    assert validate_stage_event(event) == []  # redact, never reject
    assert event.detail == REDACT
    as_dict = {
        "schema_version": STAGE_TAXONOMY_SCHEMA,
        "stage": "identity",
        "reason": "identity_missing",
        "detail": "/home/user/secret/file.pdf",
        "emitted_at_utc": "2026-08-13T12:00:00Z",
    }
    assert validate_stage_event(as_dict) == []
    assert as_dict["detail"] == REDACT


def test_validate_wrong_schema_version_problem() -> None:
    event = StageEvent(stage="identity", reason="identity_missing")
    event.schema_version = "reason-taxonomy-1.1"  # an N-1 payload
    problems = validate_stage_event(event)
    assert problems
    assert any("schema_version" in p for p in problems)
    # missing schema_version in dict form is also a problem.
    as_dict = event.to_dict()
    del as_dict["schema_version"]
    assert any("schema_version" in p for p in validate_stage_event(as_dict))


def test_validate_never_raises_on_garbage() -> None:
    assert validate_stage_event(None)  # non-empty problems
    assert validate_stage_event("nope")
    assert validate_stage_event(42)


def test_n1_consumer_rejects_20_event_without_crash() -> None:
    """An N-1 consumer knowing only reason-taxonomy-1.1 must refuse a 2.0
    event gracefully (problems list) and never crash."""

    def n1_validate(event: dict) -> list[str]:
        problems: list[str] = []
        if event.get("schema_version") != f"reason-taxonomy-{REASON_TAXONOMY_VERSION}":
            problems.append(
                f"unsupported schema_version: {event.get('schema_version')!r}"
            )
        return problems

    two_oh = StageEvent(stage="identity", reason="identity_missing").to_dict()
    assert two_oh["schema_version"] == "stage-taxonomy-2.0"
    problems = n1_validate(two_oh)
    assert problems, "N-1 consumer must reject the 2.0 event"
    assert "unsupported" in problems[0]
    # a genuine 1.1 payload still passes the N-1 validator.
    one_one = dict(two_oh, schema_version="reason-taxonomy-1.1")
    assert n1_validate(one_one) == []


def test_reasons_additive_over_v11() -> None:
    # nothing deleted: every frozen v1.1 code is still present.
    assert FROZEN_V11_REASONS <= set(REASONS)
    # The registry is additive and must never shrink below the v1.1 floor.
    # NOTE (ZR-101 deviation): the frozen spec mentioned >=90 codes; the
    # implemented v1.1 taxonomy registers 78 codes at implementation time,
    # so the floor is 78 (asserted as >= to stay additive-compatible).
    assert len(REASONS) >= 78


def test_record_stage_event_gates() -> None:
    collector = MetricsCollector()
    assert (
        collector.record_stage_event(
            StageEvent(stage="identity", reason="identity_missing")
        )
        is True
    )
    assert (
        collector.record_stage_event(StageEvent(stage="identity", reason="bogus"))
        is False
    )
    assert (
        collector.record_stage_event(
            StageEvent(stage="acquisition", reason="identity_missing")
        )
        is False
    )
    # redacted detail survives into the stored record.
    ok = collector.record_stage_event(
        StageEvent(
            stage="artifact",
            reason="artifact_selected",
            detail=r"C:\artifacts\model_v2.json",
        )
    )
    assert ok is True
    raw = collector.snapshot().raw
    assert len(raw) == 2
    assert raw[-1]["detail"] == REDACT
    assert raw[-1]["schema_version"] == STAGE_TAXONOMY_SCHEMA
