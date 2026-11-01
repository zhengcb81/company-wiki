"""FC-201 RED/acceptance tests: persistent versioned RuntimePolicySnapshot.

The snapshot is the single activation authority (ActivationSnapshot 1.0,
ADR-010): request start pins policy_hash + activation_epoch + cohort; flag
off hides active rows even when present; read failure fails closed; writes
are compare-and-swap.  These tests cover CTRL-01/02/05 at the snapshot
seam; resolver SQL wiring lands in FC-202.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
import json  # noqa: E402

import pytest  # noqa: E402

from company_wiki.source_catalog.runtime_policy import (  # noqa: E402
    RuntimePolicyError,
    build_snapshot,
    load_runtime_policy,
    reader_mode,
    save_runtime_policy_cas,
    snapshot_hash,
)
from company_wiki.source_catalog.visibility_bridge import active_assertions  # noqa: E402

_POLICY_HASH = "a" * 64


def _snapshot(**overrides):
    payload = {
        "schema_version": "1.0",
        "flags": {
            "v2_scan_shadow": False,
            "v2_persist_assertions": False,
            "v2_resolve_shadow": False,
            "v2_resolve_active": False,
            "v2_bundle_active": False,
            "legacy_bridge_enabled": True,
        },
        "current_epoch": None,
        "active_cohorts": [],
        "policy_hash": _POLICY_HASH,
        "updated_at": "2026-08-10T00:00:00Z",
    }
    payload.update(overrides)
    return payload


def _write(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "runtime_policy.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


# --- fail-closed reads (CTRL-05 side: load is a stable snapshot) ---------


def test_load_missing_snapshot_fails_closed(tmp_path):
    with pytest.raises(RuntimePolicyError):
        load_runtime_policy(tmp_path / "nope.json")


def test_load_corrupt_json_fails_closed(tmp_path):
    path = tmp_path / "runtime_policy.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(RuntimePolicyError):
        load_runtime_policy(path)


def test_load_unknown_flag_fails_closed(tmp_path):
    path = _write(tmp_path, _snapshot(flags={
        "v2_scan_shadow": False, "made_up_flag": True}))
    with pytest.raises(RuntimePolicyError):
        load_runtime_policy(path)


def test_load_illegal_flag_dependency_fails_closed(tmp_path):
    # v2_resolve_active without v2_resolve_shadow -> FLAG-03 dependency rule
    flags = {
        "v2_scan_shadow": False,
        "v2_persist_assertions": False,
        "v2_resolve_shadow": False,
        "v2_resolve_active": True,
        "v2_bundle_active": False,
        "legacy_bridge_enabled": False,
    }
    path = _write(tmp_path, _snapshot(flags=flags))
    with pytest.raises(RuntimePolicyError):
        load_runtime_policy(path)


def test_load_placeholder_policy_hash_rejected(tmp_path):
    path = _write(tmp_path, _snapshot(policy_hash="placeholder"))
    with pytest.raises(RuntimePolicyError):
        load_runtime_policy(path)


def test_load_short_policy_hash_rejected(tmp_path):
    path = _write(tmp_path, _snapshot(policy_hash="abc123"))
    with pytest.raises(RuntimePolicyError):
        load_runtime_policy(path)


# --- deterministic hashing ------------------------------------------------


def test_snapshot_hash_deterministic_and_excludes_self():
    one = build_snapshot(_snapshot())
    two = build_snapshot(_snapshot())
    assert one["snapshot_sha256"] == two["snapshot_sha256"]
    # hash excludes the hash field itself (no self-reference)
    without_hash = {k: v for k, v in one.items() if k != "snapshot_sha256"}
    assert snapshot_hash(without_hash) == one["snapshot_sha256"]


def test_build_snapshot_injects_canonical_hash():
    built = build_snapshot(_snapshot())
    assert len(built["snapshot_sha256"]) == 64
    assert snapshot_hash(built) == built["snapshot_sha256"]


# --- CTRL-01: flag off hides active rows even when present ---------------


def test_ctrl01_flag_false_hides_active_rows(tmp_path):
    flags = {
        "v2_scan_shadow": False,
        "v2_persist_assertions": False,
        "v2_resolve_shadow": False,
        "v2_resolve_active": False,
        "v2_bundle_active": False,
        "legacy_bridge_enabled": True,
    }
    snapshot = build_snapshot(_snapshot(flags=flags, current_epoch="epoch-2"))
    path = _write(tmp_path, snapshot)
    loaded = load_runtime_policy(path)
    assert reader_mode(loaded) == "v1"
    rows = [
        {"assertion_id": "a-active", "visibility_state": "active",
         "activation_epoch": "epoch-2", "decision": "verified"},
        {"assertion_id": "a-legacy", "visibility_state": "legacy",
         "activation_epoch": None, "decision": "verified"},
    ]
    visible = active_assertions(
        rows, reader=reader_mode(loaded),
        current_epoch=loaded["current_epoch"])
    assert {r["assertion_id"] for r in visible} == {"a-legacy"}


def _V2_ACTIVE_FLAGS():
    return {
        "v2_scan_shadow": True,
        "v2_persist_assertions": True,
        "v2_resolve_shadow": True,
        "v2_resolve_active": True,
        "v2_bundle_active": False,
        "legacy_bridge_enabled": False,
    }


# --- CTRL-02: activation epoch mismatch -> invisible ----------------------


def test_ctrl02_epoch_mismatch_hides_rows(tmp_path):
    flags = _V2_ACTIVE_FLAGS()
    snapshot = build_snapshot(_snapshot(flags=flags, current_epoch="epoch-2"))
    path = _write(tmp_path, snapshot)
    loaded = load_runtime_policy(path)
    assert reader_mode(loaded) == "v2"
    rows = [
        {"assertion_id": "a-epoch1", "visibility_state": "active",
         "activation_epoch": "epoch-1", "decision": "verified"},
        {"assertion_id": "a-epoch2", "visibility_state": "active",
         "activation_epoch": "epoch-2", "decision": "verified"},
    ]
    visible = active_assertions(
        rows, reader=reader_mode(loaded),
        current_epoch=loaded["current_epoch"])
    assert {r["assertion_id"] for r in visible} == {"a-epoch2"}


# --- CTRL-05: request pins a stable snapshot ------------------------------


def test_ctrl05_request_snapshot_stable_when_file_changes(tmp_path):
    first = build_snapshot(_snapshot(current_epoch="epoch-1"))
    path = _write(tmp_path, first)
    loaded = load_runtime_policy(path)  # request start: pinned
    # policy flips while the request is in flight
    second = build_snapshot(_snapshot(
        flags=_V2_ACTIVE_FLAGS(),
        current_epoch="epoch-2"))
    save_runtime_policy_cas(path, second, expected_hash=snapshot_hash(first))
    assert load_runtime_policy(path)["current_epoch"] == "epoch-2"
    # the request snapshot is unchanged
    assert loaded["current_epoch"] == "epoch-1"
    assert loaded["flags"]["v2_resolve_active"] is False


# --- CAS: compare-and-swap writes -----------------------------------------


def test_cas_first_write_succeeds(tmp_path):
    snapshot = build_snapshot(_snapshot())
    path = tmp_path / "runtime_policy.json"
    new_hash = save_runtime_policy_cas(path, snapshot, expected_hash=None)
    assert new_hash == snapshot["snapshot_sha256"]
    assert load_runtime_policy(path)["snapshot_sha256"] == new_hash


def test_cas_stale_expected_hash_conflict(tmp_path):
    first = build_snapshot(_snapshot(current_epoch="epoch-1"))
    second = build_snapshot(_snapshot(current_epoch="epoch-2"))
    third = build_snapshot(_snapshot(current_epoch="epoch-3"))
    path = tmp_path / "runtime_policy.json"
    h1 = save_runtime_policy_cas(path, first, expected_hash=None)
    # concurrent writer flips to epoch-2 first
    save_runtime_policy_cas(path, second, expected_hash=h1)
    # stale expected hash must fail closed
    with pytest.raises(RuntimePolicyError):
        save_runtime_policy_cas(path, third, expected_hash=h1)
    # file still holds the concurrent writer's snapshot
    assert load_runtime_policy(path)["current_epoch"] == "epoch-2"


def test_cas_expected_hash_none_rejects_existing_file(tmp_path):
    snapshot = build_snapshot(_snapshot())
    path = tmp_path / "runtime_policy.json"
    save_runtime_policy_cas(path, snapshot, expected_hash=None)
    with pytest.raises(RuntimePolicyError):
        save_runtime_policy_cas(path, snapshot, expected_hash=None)


# --- CLI seam (show / apply) ----------------------------------------------


def _project(tmp_path: Path):
    project = tmp_path / "project"
    config_path = project / "config" / "source_catalog.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        "\n".join(
            [
                "schema_version: '1.0'",
                "catalog_dir: '" + str(project / ".source_catalog").replace("\\", "/") + "'",
                "roots:",
                "  - root_id: company_raw",
                "    kind: company_raw",
                "    path: '" + str(project / "companies").replace("\\", "/") + "'",
                "    priority: 10",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return project, config_path


def test_cli_runtime_policy_show_fails_closed_when_absent(tmp_path, capsys):
    from company_wiki.source_catalog.cli import main

    project, config_path = _project(tmp_path)
    rc = main(["--config", str(config_path), "runtime-policy", "show"])
    assert rc == 1  # fail closed, not a silent default


def test_cli_runtime_policy_apply_then_show(tmp_path, capsys):
    from company_wiki.source_catalog.cli import main

    project, config_path = _project(tmp_path)
    payload = _snapshot()
    payload_file = tmp_path / "snapshot.json"
    payload_file.write_text(json.dumps(payload), encoding="utf-8")
    rc = main(
        ["--config", str(config_path), "runtime-policy", "apply",
         "--file", str(payload_file)]
    )
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["applied"] is True
    assert len(out["snapshot_sha256"]) == 64

    rc = main(["--config", str(config_path), "runtime-policy", "show"])
    assert rc == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["schema_version"] == "1.0"
    assert shown["snapshot_sha256"] == out["snapshot_sha256"]
    assert shown["flags"]["v2_resolve_active"] is False
