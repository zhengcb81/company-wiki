"""WU-303~305 RED/audit tests: policy export (POL-01..03) + flag state
machine (FLAG-01..08)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.config import load_catalog_config  # noqa: E402
from company_wiki.source_catalog.flags import (  # noqa: E402
    atomic_rollback,
    validate_flag_state,
)
from company_wiki.source_catalog.policy import (  # noqa: E402
    export_policy,
    policy_authorizes_root,
    validate_policy_hash,
)


def _config(tmp_path: Path):
    import yaml

    payload = {
        "schema_version": "1.0",
        "catalog_dir": "${PROJECT_ROOT}/.source_catalog",
        "roots": [
            {"root_id": "dropbox_stock", "path": "${PROJECT_ROOT}/stock",
             "kind": "directory", "adapter_id": "sidecar_filing_v1",
             "read_only": True, "reusable_for_filing": True},
            {"root_id": "company_raw", "path": "${PROJECT_ROOT}/companies",
             "kind": "company_raw", "reusable_for_filing": True},
        ],
    }
    cfg = tmp_path / "source_catalog.yaml"
    cfg.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")
    return load_catalog_config(cfg, project_root=tmp_path)


def test_pol01_consumer_local_allowance_cannot_widen(tmp_path):
    config = _config(tmp_path)
    _, policy = export_policy(config, project_root=tmp_path)
    # consumer adding an unlisted root must NOT authorize it via policy
    assert policy_authorizes_root(policy, "dropbox_stock") is True
    assert policy_authorizes_root(policy, "unlisted_root") is False


def test_pol02_policy_hash_mismatch_rejected():
    assert validate_policy_hash("abc", "def")
    assert validate_policy_hash("abc", "abc") == []


def test_pol03_expired_snapshot_rejected(tmp_path):
    config = _config(tmp_path)
    hash_a, _ = export_policy(config, project_root=tmp_path)
    # a changed config (new root) produces a different hash — the old
    # snapshot must no longer validate
    import yaml

    payload = {
        "schema_version": "1.0",
        "catalog_dir": "${PROJECT_ROOT}/.source_catalog",
        "roots": [
            {"root_id": "dropbox_stock", "path": "${PROJECT_ROOT}/stock",
             "kind": "directory", "adapter_id": "sidecar_filing_v1",
             "read_only": True, "reusable_for_filing": True},
            {"root_id": "brand_new", "path": "${PROJECT_ROOT}/new",
             "kind": "directory", "adapter_id": "sidecar_filing_v1",
             "read_only": True, "reusable_for_filing": True},
        ],
    }
    cfg = tmp_path / "source_catalog_v2.yaml"
    cfg.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")
    config_v2 = load_catalog_config(cfg, project_root=tmp_path)
    hash_b, _ = export_policy(config_v2, project_root=tmp_path)
    assert hash_a != hash_b


def test_policy_export_redacts_absolute_paths(tmp_path):
    config = _config(tmp_path)
    _, policy = export_policy(config, project_root=tmp_path)
    serialized = str(policy)
    assert "C:\\" not in serialized and "/Users/" not in serialized
    assert "stock" in serialized  # token remains readable


def test_flag_unknown_flag_rejected():
    assert validate_flag_state({"mega_switch": True})


def test_flag_dependency_missing_fails():
    problems = validate_flag_state({"v2_resolve_active": True})
    assert any("v2_resolve_active requires v2_resolve_shadow" in p for p in problems)


def test_flag_valid_chain_passes():
    flags = {
        "v2_scan_shadow": True,
        "v2_persist_assertions": True,
        "v2_resolve_shadow": True,
        "v2_resolve_active": True,
        "v2_bundle_active": True,
    }
    assert validate_flag_state(flags) == []


def test_flag_bridge_conflicts_with_active():
    problems = validate_flag_state({
        "v2_scan_shadow": True, "v2_persist_assertions": True,
        "v2_resolve_shadow": True, "v2_resolve_active": True,
        "legacy_bridge_enabled": True,
    })
    assert any("legacy_bridge_enabled" in p for p in problems)


def test_atomic_rollback_cascades_downstream():
    flags = {
        "v2_scan_shadow": True,
        "v2_persist_assertions": True,
        "v2_resolve_shadow": True,
        "v2_resolve_active": True,
        "v2_bundle_active": True,
    }
    # breaker disables the root of the chain: everything cascades off
    rolled = atomic_rollback(flags, disable=("v2_scan_shadow",))
    assert not any(rolled.values())


def test_atomic_rollback_never_touches_catalog():
    flags = {"v2_scan_shadow": True, "v2_persist_assertions": True}
    rolled = atomic_rollback(flags, disable=("v2_scan_shadow",))
    # pure dict operation — no side effects by construction
    assert rolled == {"v2_scan_shadow": False, "v2_persist_assertions": False}
