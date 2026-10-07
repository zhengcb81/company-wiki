"""Permanent source policy has no rollout switches or canary membership."""

import pytest

from company_wiki.source_catalog.runtime_policy import (
    RuntimePolicyError, build_snapshot, load_runtime_policy,
    resolver_visibility_projection, save_runtime_policy_cas,
)


def _payload():
    return {"schema_version": "2.0", "mode": "steady", "policy_hash": "a" * 64,
            "updated_at": "2026-10-07T12:00:00Z"}


def test_steady_snapshot_has_no_rollout_controls_and_keeps_cas(tmp_path):
    snapshot = build_snapshot(_payload())
    assert set(snapshot) == {"schema_version", "mode", "policy_hash", "updated_at", "snapshot_sha256"}
    assert resolver_visibility_projection(snapshot) == {
        "reader": "steady", "current_epoch": None, "active_cohorts": (), "legacy_bridge_allowed": True,
    }
    path = tmp_path / "policy.json"
    digest = save_runtime_policy_cas(path, snapshot, expected_hash=None)
    assert load_runtime_policy(path) == snapshot
    before = path.read_bytes()
    with pytest.raises(RuntimePolicyError, match="CAS conflict"):
        save_runtime_policy_cas(path, snapshot, expected_hash="b" * 64)
    assert path.read_bytes() == before
    assert save_runtime_policy_cas(path, snapshot, expected_hash=digest) == digest


@pytest.mark.parametrize("extra", [{"flags": {}}, {"current_epoch": "canary"},
                                  {"active_cohorts": ["canary"]}, {"mode": "canary"}])
def test_steady_snapshot_cannot_reintroduce_canary_controls(extra):
    with pytest.raises(RuntimePolicyError):
        build_snapshot({**_payload(), **extra})
