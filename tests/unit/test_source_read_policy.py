"""Effective policy identity excludes inert labels but retains declared read rules."""

from dataclasses import replace
import pytest

from company_wiki.source_catalog.models import CatalogConfig, RootSpec, RouteSpec
from company_wiki.source_catalog.runtime_policy import build_snapshot
from company_wiki.source_catalog.source_read_policy import (
    READ_POLICY_FINGERPRINT_SCHEMA_VERSION,
    source_read_policy_sha256,
)


def _config(tmp_path):
    return CatalogConfig(tmp_path, tmp_path / "catalog", (
        RootSpec("lake", tmp_path / "lake", "directory", adapter_id="sidecar_filing_v1",
                 reusable_for_filing=True),
    ), ("directory",))


def _steady(policy_hash="a" * 64):
    return build_snapshot({"schema_version": "2.0", "mode": "steady",
                           "policy_hash": policy_hash, "updated_at": "2026-10-07T00:00:00Z"})


def test_effective_projection_has_distinct_version():
    assert READ_POLICY_FINGERPRINT_SCHEMA_VERSION == "2.0"


@pytest.mark.parametrize("change", (
    {"privacy_class": "private_user"}, {"cohort": "old-canary"},
    {"canonical_write_target": "new-write-location"},
    {"adapter_id": "company_raw_v1"}, {"adapter_version_range": ">=2.0"},
    {"admission_profile_id": "generic_document_v1"}, {"read_only": False},
    {"routes": (RouteSpec(include=("reports/**",), exclude=("notes/**",)),)},
    {"symlink_policy": "allow_internal"},
    {"sidecar_suffixes": (".metadata.json",)}, {"encoding": "gb18030"},
))
def test_steady_pin_excludes_fields_without_current_read_consumers(tmp_path, change):
    config = _config(tmp_path)
    changed = replace(config, roots=(replace(config.roots[0], **change),))
    assert source_read_policy_sha256(config, _steady()) == source_read_policy_sha256(changed, _steady())


def test_steady_pin_excludes_outer_envelope_hash_and_project_label(tmp_path):
    config = _config(tmp_path)
    changed = replace(config, project_root=tmp_path / "unrelated-display-root")
    assert source_read_policy_sha256(config, _steady()) == source_read_policy_sha256(changed, _steady("b" * 64))


def test_unused_kind_policy_is_normalized_to_effective_root_reusability(tmp_path):
    config = _config(tmp_path)
    changed = replace(config, reusable_root_kinds=("company_raw",))
    assert source_read_policy_sha256(config, None) == source_read_policy_sha256(changed, None)
    inherited = replace(config, roots=(replace(config.roots[0], reusable_for_filing=None),))
    excluded = replace(inherited, reusable_root_kinds=("company_raw",))
    assert source_read_policy_sha256(inherited, None) != source_read_policy_sha256(excluded, None)


@pytest.mark.parametrize("change", (
    {"root_id": "other"}, {"kind": "company_raw"}, {"priority": 1},
    {"reusable_for_filing": False},
    {"allowed_document_kinds": ("annual_report",)}, {"allowed_statuses": ("active",)},
    {"max_file_size": 42},
))
def test_effective_pin_retains_executed_read_rules(tmp_path, change):
    config = _config(tmp_path)
    changed = replace(config, roots=(replace(config.roots[0], **change),))
    assert source_read_policy_sha256(config, None) != source_read_policy_sha256(changed, None)


def test_effective_pin_tracks_root_location_and_catalog_identity(tmp_path):
    config = _config(tmp_path)
    root_moved = replace(config, roots=(replace(config.roots[0], path=tmp_path / "new-lake"),))
    catalog_moved = replace(config, catalog_dir=tmp_path / "new-catalog")
    baseline = source_read_policy_sha256(config, None)
    assert source_read_policy_sha256(root_moved, None) != baseline
    assert source_read_policy_sha256(catalog_moved, None) != baseline
    same_path = replace(config, roots=(replace(config.roots[0], path=config.roots[0].path / "."),))
    assert source_read_policy_sha256(same_path, None) == baseline


def test_missing_snapshot_uses_same_steady_read_identity(tmp_path):
    config = _config(tmp_path)
    assert source_read_policy_sha256(config, None) == source_read_policy_sha256(config, _steady())


def test_effective_pin_ignores_root_order_and_membership_order(tmp_path):
    first = replace(_config(tmp_path).roots[0], allowed_statuses=("active", "quarantined"))
    second = replace(first, root_id="second", path=tmp_path / "second")
    config = CatalogConfig(tmp_path, tmp_path / "catalog", (first, second), ("directory",))
    changed = replace(config, roots=(second, replace(first, allowed_statuses=("quarantined", "active"))))
    assert source_read_policy_sha256(config, None) == source_read_policy_sha256(changed, None)


@pytest.mark.parametrize("change", ({"current_epoch": "old-b"}, {"active_cohorts": ["old-b"]}))
def test_legacy_v2_visibility_remains_pinned(tmp_path, change):
    config = _config(tmp_path)
    payload = {"schema_version": "1.0", "policy_hash": "a" * 64,
               "updated_at": "2026-10-07T00:00:00Z", "current_epoch": "old-a",
               "active_cohorts": ["old-a"], "flags": {
                   "v2_scan_shadow": True, "v2_persist_assertions": True,
                   "v2_resolve_shadow": True, "v2_resolve_active": True,
                   "v2_bundle_active": False, "legacy_bridge_enabled": False,
               }}
    assert source_read_policy_sha256(config, build_snapshot(payload)) != source_read_policy_sha256(
        config, build_snapshot(payload | change),
    )
