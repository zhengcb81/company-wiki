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
