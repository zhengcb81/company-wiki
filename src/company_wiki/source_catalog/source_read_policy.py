"""Versioned effective read identity for path-independent consumers.

Schema 2 pins the current read location, selection and admission rules.
Schema 3 pins one exact source's facts and relevant read rules, excluding
physical paths and unrelated roots. It is used by new finite batch bindings;
schema 2 remains an explicit selection/legacy compatibility interpretation.
Compatibility/privacy labels, discovery-only settings and write targets do
not govern an already registered read and cannot invalidate it. RootPolicy
remains a separate wire export; its broad diagnostic hash is not another
permission inside this fingerprint.

The schema change deliberately produces new pins. Existing runs carrying a
schema 1 digest are refused by the reader's ordinary read_policy_mismatch;
their persisted payloads, artifacts and usage are never silently re-signed.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .models import CatalogConfig, RootSpec
from .policy import _effective_reusable
from .runtime_policy import resolver_visibility_projection


READ_POLICY_FINGERPRINT_SCHEMA_VERSION = "2.0"
EXACT_READ_POLICY_FINGERPRINT_SCHEMA_VERSION = "3.0"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _path_identity(value: Path) -> str:
    return str(value.resolve(strict=False))


def _root_read_policy(root: RootSpec, config: CatalogConfig) -> dict[str, Any]:
    """Project rules used by the reader/resolver, not unexecuted declarations.

    Path/ranking/kind/reusability select registered locations; kinds, status and
    size are enforced again during open. Adapter/routes configure discovery,
    not reads of an indexed version. Format/ownership declarations without
    current reader consumers stay in config but do not manufacture permission.
    Real path containment, byte SHA, source role/version, metadata and locator
    validation remain enforced in their existing responsible layers.
    """
    return {
        "root_id": root.root_id,
        "path": _path_identity(root.path),
        "kind": root.kind,
        "priority": root.priority,
        "reusable_for_filing": _effective_reusable(root, config),
        "allowed_document_kinds": sorted(set(root.allowed_document_kinds)),
        "allowed_statuses": sorted(set(root.allowed_statuses)),
        "max_file_size": root.max_file_size,
    }


def _runtime_read_policy(snapshot: Mapping[str, Any] | None) -> dict[str, Any]:
    if snapshot is None:
        return {"reader": "steady", "current_epoch": None, "active_cohorts": (),
                "legacy_bridge_allowed": True}
    snapshot_digest = snapshot.get("snapshot_sha256")
    if not isinstance(snapshot_digest, str) or not _SHA256.fullmatch(snapshot_digest):
        raise ValueError("runtime snapshot must carry a valid SHA-256")
    visibility = resolver_visibility_projection(dict(snapshot))
    # Only the historical v2 reader filters assertions by epoch/cohort.
    # The steady reader and v1 legacy reader do not use those rollout labels.
    if visibility["reader"] != "v2":
        visibility["current_epoch"] = None
        visibility["active_cohorts"] = ()
    else:
        visibility["active_cohorts"] = tuple(sorted(set(visibility["active_cohorts"])))
    return visibility


def source_read_policy_sha256(
    config: CatalogConfig, runtime_snapshot: Mapping[str, Any] | None
) -> str:
    """Hash effective read rules, excluding compatibility and write labels."""
    if not isinstance(config, CatalogConfig):
        raise TypeError("config must be CatalogConfig")
    payload = {
        "schema_version": READ_POLICY_FINGERPRINT_SCHEMA_VERSION,
        "catalog": _path_identity(config.database_path),
        "roots": [_root_read_policy(root, config)
                  for root in sorted(config.roots, key=lambda root: root.root_id)],
        "runtime_read_visibility": _runtime_read_policy(runtime_snapshot),
    }
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def exact_source_read_policy_sha256(
    config: CatalogConfig, runtime_snapshot: Mapping[str, Any] | None, *,
    source_ref: Mapping[str, Any], source_facts: Mapping[str, Any],
    registered_root_ids: Iterable[str],
) -> str:
    """Bind one indexed source to effective rules, independently of storage paths.

    Candidate discovery still uses the global schema-2 pin. This projection is
    for an already chosen version; current containment/admission/byte checks
    remain the reader's responsibility on every open, including after a move.
    """
    root_ids = frozenset(registered_root_ids)
    roots = []
    for root in sorted(config.roots, key=lambda root: root.root_id):
        if root.root_id in root_ids:
            effective = _root_read_policy(root, config)
            effective.pop("path")
            roots.append(effective)
    payload = {
        "schema_version": EXACT_READ_POLICY_FINGERPRINT_SCHEMA_VERSION,
        "source_ref": dict(source_ref), "source_facts": dict(source_facts),
        "roots": roots, "runtime_read_visibility": _runtime_read_policy(runtime_snapshot),
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "READ_POLICY_FINGERPRINT_SCHEMA_VERSION",
    "EXACT_READ_POLICY_FINGERPRINT_SCHEMA_VERSION",
    "exact_source_read_policy_sha256",
    "source_read_policy_sha256",
]
