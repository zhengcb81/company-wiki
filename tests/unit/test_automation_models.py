"""AUTO-1 contract tests for the isolated automation control-plane models."""

from dataclasses import FrozenInstanceError
import hashlib
import importlib
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MODELS_PATH = ROOT / "src" / "company_wiki" / "automation" / "models.py"


def load_models():
    assert MODELS_PATH.is_file(), "AUTO-1 requires an isolated automation/models.py"
    return importlib.import_module("company_wiki.automation.models")


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def event_data() -> dict:
    return {
        "event_id": "evt-001",
        "event_type": "source.revision_registered",
        "subject_type": "source_revision",
        "subject_id": "rev-001",
        "input_hash": digest("source-input"),
        "payload_json": '{"entity":"北方华创","revision":1}',
        "policy_version": "automation-policy.v1",
        "occurred_at": "2026-07-12T06:00:00Z",
        "observed_at": "2026-07-12T06:00:01Z",
    }


def job_data() -> dict:
    m = load_models()
    data = {
        "job_id": "job-001",
        "job_type": "source.normalize",
        "subject_type": "source_revision",
        "subject_id": "rev-001",
        "input_hash": digest("source-input"),
        "policy_version": "automation-policy.v1",
        "handler_version": "1.0.0",
        "risk_class": "low",
        "status": "detected",
        "priority": 0,
        "not_before": "2026-07-12T06:00:00Z",
        "max_attempts": 3,
        "created_from_event_id": "evt-001",
        "created_at": "2026-07-12T06:00:00Z",
        "updated_at": "2026-07-12T06:00:00Z",
        "last_error_code": None,
        "last_error_detail": None,
    }
    data["job_key"] = m.make_job_key(
        data["job_type"], data["subject_type"], data["subject_id"],
        data["input_hash"], data["policy_version"], data["handler_version"],
    )
    return data


def test_models_file_exists_before_contract_import():
    assert MODELS_PATH.is_file(), "expected red: automation models are not implemented"


def test_canonical_json_is_unicode_preserving_and_order_stable():
    m = load_models()
    left = m.canonical_json({"z": [3, 2], "公司": "北方华创", "a": {"b": True}})
    right = m.canonical_json({"a": {"b": True}, "公司": "北方华创", "z": [3, 2]})
    assert left == right
    assert left == '{"a":{"b":true},"z":[3,2],"公司":"北方华创"}'
    assert m.canonical_json_hash(json.loads(left)) == digest(left)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), {1: "non-string-key"}, {"x": object()}])
def test_canonical_json_rejects_non_json_or_ambiguous_values(value):
    m = load_models()
    with pytest.raises((TypeError, ValueError)):
        m.canonical_json(value)


def test_canonical_json_text_must_already_be_canonical():
    m = load_models()
    with pytest.raises(ValueError, match="canonical"):
        m.require_canonical_json('{"b": 2, "a": 1}')
    assert m.require_canonical_json('{"a":1,"b":2}') == '{"a":1,"b":2}'


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-07-12 06:00:00Z",
        "2026-07-12T06:00:00+00:00",
        "2026-07-12T06:00:00.123Z",
        "2026-02-30T06:00:00Z",
        "2026-07-12T06:00Z",
    ],
)
def test_utc_timestamp_rejects_offsets_fractional_seconds_and_invalid_dates(timestamp):
    m = load_models()
    with pytest.raises(ValueError, match="UTC"):
        m.require_utc_timestamp(timestamp)


def test_utc_timestamp_accepts_exact_schema_format():
    m = load_models()
    assert m.require_utc_timestamp("2026-07-12T06:00:00Z") == "2026-07-12T06:00:00Z"


def test_job_key_is_stable_and_matches_frozen_formula():
    m = load_models()
    parts = ("gold.validate_receipt", "review_receipt", "receipt-1", digest("input"), "p1", "1.0.0")
    expected = digest("|".join(parts))
    assert m.make_job_key(*parts) == expected
    assert m.make_job_key(*parts) == m.make_job_key(*parts)
    for index in range(len(parts)):
        changed = list(parts)
        changed[index] += "-changed"
        assert m.make_job_key(*changed) != expected


def test_effect_key_is_stable_and_matches_frozen_formula():
    m = load_models()
    parts = ("artifact.write", "artifacts/gates/receipt.json", digest("action"), "projector.v1")
    assert m.make_effect_key(*parts) == digest("|".join(parts))
    assert m.make_effect_key(*parts) == m.make_effect_key(*parts)


def test_key_components_reject_empty_or_delimiter_ambiguity():
    m = load_models()
    with pytest.raises(ValueError):
        m.make_job_key("", "subject", "id", digest("x"), "p1", "h1")
    with pytest.raises(ValueError):
        m.make_effect_key("artifact|write", "target", digest("x"), "v1")


def test_job_status_transition_table_is_exact():
    m = load_models()
    expected = {
        m.JobStatus.DETECTED: {m.JobStatus.PLANNED, m.JobStatus.CANCELLED},
        m.JobStatus.PLANNED: {m.JobStatus.READY, m.JobStatus.BLOCKED_HUMAN, m.JobStatus.CANCELLED},
        m.JobStatus.READY: {m.JobStatus.LEASED, m.JobStatus.CANCELLED},
        m.JobStatus.LEASED: {m.JobStatus.RUNNING, m.JobStatus.READY},
        m.JobStatus.RUNNING: {
            m.JobStatus.VERIFYING, m.JobStatus.RETRY_WAIT,
            m.JobStatus.BLOCKED_HUMAN, m.JobStatus.DEAD_LETTER,
        },
        m.JobStatus.VERIFYING: {
            m.JobStatus.SUCCEEDED, m.JobStatus.RETRY_WAIT,
            m.JobStatus.BLOCKED_HUMAN, m.JobStatus.DEAD_LETTER,
        },
        m.JobStatus.RETRY_WAIT: {m.JobStatus.READY, m.JobStatus.DEAD_LETTER},
        m.JobStatus.BLOCKED_HUMAN: {m.JobStatus.READY, m.JobStatus.CANCELLED},
        m.JobStatus.SUCCEEDED: set(),
        m.JobStatus.DEAD_LETTER: set(),
        m.JobStatus.CANCELLED: set(),
    }
    assert m.JOB_STATUS_TRANSITIONS == expected
    for current, targets in expected.items():
        for target in m.JobStatus:
            if target in targets:
                assert m.validate_job_transition(current, target) is None
            else:
                with pytest.raises(ValueError, match="transition"):
                    m.validate_job_transition(current, target)


@pytest.mark.parametrize(
    "model_name,data_factory",
    [
        ("Event", event_data),
        ("Job", job_data),
    ],
)
def test_models_roundtrip_with_enum_values_and_reject_unknown_fields(model_name, data_factory):
    m = load_models()
    cls = getattr(m, model_name)
    data = data_factory()
    model = cls.from_dict(data)
    assert model.to_dict() == data
    with pytest.raises(ValueError, match="unknown fields"):
        cls.from_dict({**data, "unexpected": "must-fail"})


def test_event_rejects_noncanonical_payload_and_invalid_hash():
    m = load_models()
    with pytest.raises(ValueError, match="canonical"):
        m.Event.from_dict({**event_data(), "payload_json": '{"revision": 1}'})
    with pytest.raises(ValueError, match="SHA-256"):
        m.Event.from_dict({**event_data(), "input_hash": "not-a-hash"})


def test_event_rejects_observation_before_occurrence():
    m = load_models()
    with pytest.raises(ValueError, match="observed_at"):
        m.Event.from_dict({**event_data(), "observed_at": "2026-07-12T05:59:59Z"})


def test_job_requires_its_key_to_match_its_identity_fields():
    m = load_models()
    with pytest.raises(ValueError, match="job_key"):
        m.Job.from_dict({**job_data(), "job_key": digest("wrong")})


def test_job_rejects_boolean_priority_and_nonpositive_attempt_limit():
    m = load_models()
    with pytest.raises(TypeError):
        m.Job.from_dict({**job_data(), "priority": True})
    with pytest.raises(ValueError):
        m.Job.from_dict({**job_data(), "max_attempts": 0})


def test_attempt_approval_effect_and_handler_result_roundtrip():
    m = load_models()
    attempt = m.Attempt.from_dict({
        "attempt_id": "attempt-001", "job_id": "job-001", "attempt_no": 1,
        "worker_id": "worker-1", "lease_token": "lease-token-1",
        "lease_until": "2026-07-12T06:05:00Z", "started_at": "2026-07-12T06:00:00Z",
        "heartbeat_at": "2026-07-12T06:01:00Z", "finished_at": None,
        "outcome": None, "result_json": None, "error_code": None, "error_detail": None,
    })
    approval = m.Approval.from_dict({
        "approval_id": "approval-001", "job_id": "job-001", "action_hash": digest("action"),
        "reviewer_principal": "reviewer-1", "reviewer_session_id": "session-1",
        "role": "primary", "decision": "approved", "decided_at": "2026-07-12T06:10:00Z",
        "receipt_hash": digest("receipt"),
    })
    effect = m.Effect.from_dict({
        "effect_id": "effect-001",
        "effect_key": m.make_effect_key("artifact.write", "artifacts/gates/result.json", digest("action"), "v1"),
        "job_id": "job-001", "effect_type": "artifact.write", "target": "artifacts/gates/result.json",
        "before_hash": None, "intended_after_hash": digest("after"), "actual_after_hash": None,
        "status": "planned", "created_at": "2026-07-12T06:00:00Z", "verified_at": None,
    })
    result = m.HandlerResult.from_dict({
        "outcome": "succeeded", "result": {"valid": True},
        "artifacts": [{"path": "artifacts/gates/result.json", "sha256": digest("after")}],
        "effects": [effect.to_dict()],
        "metrics": {"tokens": 0, "cost_usd": 0.0, "duration_ms": 12},
        "error": None,
    })
    assert attempt.to_dict()["outcome"] is None
    assert approval.to_dict()["decision"] == "approved"
    assert effect.to_dict()["status"] == "planned"
    assert result.to_dict()["artifacts"][0]["sha256"] == digest("after")
    assert result.to_dict()["effects"][0]["effect_id"] == "effect-001"


def test_attempt_rejects_noncanonical_result_json_and_bad_attempt_number():
    m = load_models()
    base = {
        "attempt_id": "attempt-001", "job_id": "job-001", "attempt_no": 1,
        "worker_id": "worker-1", "lease_token": "lease-token-1",
        "lease_until": "2026-07-12T06:05:00Z", "started_at": "2026-07-12T06:00:00Z",
        "heartbeat_at": "2026-07-12T06:01:00Z", "finished_at": None,
        "outcome": None, "result_json": None, "error_code": None, "error_detail": None,
    }
    with pytest.raises(ValueError, match="canonical"):
        m.Attempt.from_dict({**base, "result_json": '{"ok": true}'})
    with pytest.raises(ValueError):
        m.Attempt.from_dict({**base, "attempt_no": 0})


def test_lifecycle_models_reject_impossible_timestamp_ordering():
    m = load_models()
    with pytest.raises(ValueError, match="updated_at"):
        m.Job.from_dict({**job_data(), "updated_at": "2026-07-12T05:59:59Z"})
    attempt = {
        "attempt_id": "attempt-001", "job_id": "job-001", "attempt_no": 1,
        "worker_id": "worker-1", "lease_token": "lease-token-1",
        "lease_until": "2026-07-12T06:05:00Z", "started_at": "2026-07-12T06:00:00Z",
        "heartbeat_at": "2026-07-12T05:59:59Z", "finished_at": None,
        "outcome": None, "result_json": None, "error_code": None, "error_detail": None,
    }
    with pytest.raises(ValueError, match="heartbeat_at"):
        m.Attempt.from_dict(attempt)
    effect = {
        "effect_id": "effect-001", "effect_key": digest("effect-key"), "job_id": "job-001",
        "effect_type": "artifact.write", "target": "artifact.json", "before_hash": None,
        "intended_after_hash": digest("after"), "actual_after_hash": digest("after"),
        "status": "verified", "created_at": "2026-07-12T06:00:00Z",
        "verified_at": "2026-07-12T05:59:59Z",
    }
    with pytest.raises(ValueError, match="verified_at"):
        m.Effect.from_dict(effect)


def test_handler_result_error_contract_matches_outcome():
    m = load_models()
    base = {
        "result": {}, "artifacts": [], "effects": [],
        "metrics": {"tokens": 0, "cost_usd": 0.0, "duration_ms": 0},
    }
    with pytest.raises(ValueError, match="error"):
        m.HandlerResult.from_dict({**base, "outcome": "succeeded", "error": {"code": "X", "detail": "bad"}})
    with pytest.raises(ValueError, match="error"):
        m.HandlerResult.from_dict({**base, "outcome": "retryable", "error": None})
    retry = m.HandlerResult.from_dict({
        **base, "outcome": "retryable", "error": {"code": "IO_TRANSIENT", "detail": "try later"},
    })
    assert retry.outcome is m.HandlerOutcome.RETRYABLE


def test_models_are_frozen_value_objects():
    m = load_models()
    event = m.Event.from_dict(event_data())
    with pytest.raises(FrozenInstanceError):
        event.event_id = "changed"


def test_handler_result_is_deeply_immutable_and_serializes_back_to_plain_json():
    m = load_models()
    result = m.HandlerResult.from_dict({
        "outcome": "succeeded",
        "result": {"nested": {"items": [1, 2]}},
        "artifacts": [],
        "effects": [],
        "metrics": {"tokens": 0, "cost_usd": 0.0, "duration_ms": 1},
        "error": None,
    })
    with pytest.raises(TypeError):
        result.result["nested"] = {}
    with pytest.raises(TypeError):
        result.result["nested"]["items"][0] = 9
    assert result.to_dict()["result"] == {"nested": {"items": [1, 2]}}
