"""Read-policy pin contracts that are deliberately separate from RootPolicy 2.x."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import re
import sys

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.models import (  # noqa: E402
    CatalogConfig,
    RootSpec,
    RouteSpec,
)
from company_wiki.source_catalog.policy_2x import export_policy_2x  # noqa: E402
from company_wiki.source_catalog.runtime_policy import build_snapshot  # noqa: E402
from company_wiki.source_catalog.source_read_policy import (  # noqa: E402
    source_read_policy_sha256,
)


def _config(tmp_path: Path) -> CatalogConfig:
    root = RootSpec(
        "lake", tmp_path / "lake", "directory", priority=10,
        adapter_id="sidecar_filing_v1", read_only=True,
        reusable_for_filing=True,
    )
    return CatalogConfig(
        project_root=tmp_path, catalog_dir=tmp_path / ".source_catalog",
        roots=(root,), reusable_root_kinds=("directory",),
    )


@pytest.mark.parametrize(
    "change",
    (
        {"privacy_class": "private_user"},
        {"max_file_size": 42},
        {"allowed_statuses": ("quarantined",)},
        {"symlink_policy": "allow_internal"},
        {"routes": (RouteSpec(include=("reports/**",), exclude=("secret/**",)),)},
        {"adapter_version_range": ">=2.0"},
        {"sidecar_suffixes": (".source.json",)},
        {"encoding": "gb18030"},
    ),
)
def test_read_policy_pin_covers_every_admission_dimension(tmp_path, change):
    config = _config(tmp_path)
    first = source_read_policy_sha256(config, None)
    changed = replace(config, roots=(replace(config.roots[0], **change),))
    second = source_read_policy_sha256(changed, None)
    assert re.fullmatch(r"[0-9a-f]{64}", first)
    assert second != first
    if set(change) <= {"privacy_class", "max_file_size", "allowed_statuses"}:
        assert export_policy_2x(config)[0] == export_policy_2x(changed)[0]


def test_read_policy_pin_covers_runtime_activation_snapshot(tmp_path):
    config = _config(tmp_path)
    policy_hash = export_policy_2x(config)[0]
    snapshot = build_snapshot({
        "schema_version": "1.0",
        "flags": {
            "v2_scan_shadow": True,
            "v2_persist_assertions": True,
            "v2_resolve_shadow": True,
            "v2_resolve_active": True,
            "v2_bundle_active": False,
            "legacy_bridge_enabled": False,
        },
        "current_epoch": "epoch-a",
        "active_cohorts": ["cohort-a"],
        "policy_hash": policy_hash,
        "updated_at": "2026-09-27T00:00:00Z",
    })
    assert source_read_policy_sha256(config, None) != source_read_policy_sha256(
        config, snapshot
    )
    changed = build_snapshot({
        key: value for key, value in snapshot.items()
        if key != "snapshot_sha256"
    } | {"current_epoch": "epoch-b"})
    assert source_read_policy_sha256(config, snapshot) != source_read_policy_sha256(
        config, changed
    )


def _runtime_snapshot(
    config: CatalogConfig,
    *,
    updated_at: str = "2026-09-27T00:00:00Z",
    current_epoch: str = "epoch-a",
    active_cohorts: tuple[str, ...] = ("cohort-a",),
    flag_changes: dict[str, bool] | None = None,
) -> dict:
    from company_wiki.source_catalog.runtime_policy import build_snapshot

    flags = {
        "v2_scan_shadow": False,
        "v2_persist_assertions": False,
        "v2_resolve_shadow": False,
        "v2_resolve_active": False,
        "v2_bundle_active": False,
        "legacy_bridge_enabled": False,
    }
    flags.update(flag_changes or {})
    return build_snapshot({
        "schema_version": "1.0",
        "flags": flags,
        "current_epoch": current_epoch,
        "active_cohorts": list(active_cohorts),
        "policy_hash": export_policy_2x(config)[0],
        "updated_at": updated_at,
    })


def test_read_policy_pin_ignores_timestamp_and_unrelated_runtime_flags(tmp_path):
    config = _config(tmp_path)
    baseline = _runtime_snapshot(config)
    changed = _runtime_snapshot(
        config,
        updated_at="2026-09-28T00:00:00Z",
        flag_changes={"v2_scan_shadow": True},
    )

    assert baseline["snapshot_sha256"] != changed["snapshot_sha256"]
    assert source_read_policy_sha256(config, baseline) == source_read_policy_sha256(
        config, changed
    )


@pytest.mark.parametrize(
    "changes",
    (
        {"current_epoch": "epoch-b"},
        {"active_cohorts": ("cohort-b",)},
        {"flag_changes": {
            "v2_scan_shadow": True,
            "v2_persist_assertions": True,
            "v2_resolve_shadow": True,
            "v2_resolve_active": True,
        }},
        {"flag_changes": {"legacy_bridge_enabled": True}},
    ),
)
def test_read_policy_pin_changes_with_effective_reader_visibility(tmp_path, changes):
    config = _config(tmp_path)
    baseline = _runtime_snapshot(config)
    changed = _runtime_snapshot(config, **changes)

    assert source_read_policy_sha256(config, baseline) != source_read_policy_sha256(
        config, changed
    )
