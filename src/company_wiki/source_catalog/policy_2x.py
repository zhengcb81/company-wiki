"""FC-301: RootPolicy 2.x loader/doctor (RootPolicySnapshot 2.0).

2.x makes every root's adapter, admission profile, read_only,
reusable_for_filing, allowed kinds, cohort and canonical write target
explicit (no kind-based guessing; ADR-010 / architecture_target section 3).
Loading fails closed on: external roots that are writable, unknown
adapter/profile, widening routes, and duplicate roots.  A 1.x->2.x doctor
reports migration status WITHOUT changing production scan behavior (the
1.x loader in config.py remains the operational loader until FC-305).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from .adapters.registry import admission_profile, registered_adapter
from .config import CatalogConfigError, _expand_path, _unresolved_variables
from .models import ROOT_KINDS, CatalogConfig, RootSpec, RouteSpec

POLICY_2X_SCHEMA_VERSION = "2.0"
ALLOWED_ROOT_FIELDS_2X = {
    "root_id",
    "path",
    "kind",
    "priority",
    "adapter_id",
    "adapter_version_range",
    "admission_profile_id",
    "read_only",
    "reusable_for_filing",
    "routes",
    "allowed_document_kinds",
    "allowed_statuses",
    "symlink_policy",
    "max_file_size",
    "sidecar_suffixes",
    "encoding",
    "privacy_class",
    "cohort",
    "canonical_write_target",
}
# Only the canonical write root may be writable; external roots (directory /
# dayu_portfolio) are read-only reuse sources by contract.
_WRITABLE_KINDS = frozenset({"company_raw"})


def _mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CatalogConfigError(f"{field_name} must be an object")
    return value


def load_root_policy_2x(
    path: Path, *, project_root: Path | None = None, yaml_schema_version: str = "1.0"
) -> CatalogConfig:
    """Load a RootPolicy 2.x config: per-root explicit policy fields,
    fail-closed on external-writable roots, unknown adapter/profile,
    widening routes and duplicate roots.

    ``yaml_schema_version`` is the YAML ``schema_version`` accepted by the
    shared loader (default "1.0" = 2.x semantics; the ZR-401 3.0 loader
    passes "3.0" so the shared surface checks apply unchanged).
    """
    if not isinstance(path, Path):
        raise TypeError("path must be pathlib.Path")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    data = _mapping(payload, "config")
    required = {"schema_version", "catalog_dir", "roots"}
    if not set(data) <= (required | {"reusable_root_kinds"}):
        raise CatalogConfigError(
            "2.x config must contain only schema_version/catalog_dir/roots"
        )
    if str(data["schema_version"]) != yaml_schema_version:
        raise CatalogConfigError(
            f"2.x config YAML schema_version must be {yaml_schema_version} (additive)"
        )
    resolved_project = (project_root or path.resolve().parents[1]).resolve(strict=False)
    raw_roots = data["roots"]
    if not isinstance(raw_roots, list) or not raw_roots:
        raise CatalogConfigError("roots must be a non-empty list")
    roots: list[RootSpec] = []
    seen_root_ids: set[str] = set()
    for index, raw in enumerate(raw_roots):
        item = _mapping(raw, f"roots[{index}]")
        unknown = set(item) - ALLOWED_ROOT_FIELDS_2X
        if unknown:
            raise CatalogConfigError(
                f"roots[{index}] unknown fields: {sorted(unknown)}"
            )
        root_id = str(item.get("root_id", ""))
        if root_id in seen_root_ids:
            raise CatalogConfigError(f"duplicate root_id: {root_id}")
        seen_root_ids.add(root_id)
        raw_path = item.get("path", "")
        unresolved = _unresolved_variables(raw_path)
        if unresolved:
            raise CatalogConfigError(
                f"roots[{index}] path contains unresolved variable(s) "
                f"{sorted(unresolved)}"
            )
        kind = str(item.get("kind", ""))
        if kind not in ROOT_KINDS:
            raise CatalogConfigError(f"roots[{index}] unsupported kind {kind!r}")
        adapter_id = item.get("adapter_id")
        if adapter_id is not None and registered_adapter(str(adapter_id)) is None:
            raise CatalogConfigError(
                f"roots[{index}] adapter_id {adapter_id!r} not registered"
            )
        profile_id = item.get("admission_profile_id")
        if profile_id is not None and admission_profile(str(profile_id)) is None:
            raise CatalogConfigError(
                f"roots[{index}] admission_profile_id {profile_id!r} unknown"
            )
        read_only = item.get("read_only", True)
        reusable_for_filing = item.get("reusable_for_filing")
        write_target = item.get("canonical_write_target")
        if write_target is not None:
            if kind not in _WRITABLE_KINDS:
                raise CatalogConfigError(
                    f"roots[{index}] external root {root_id!r} cannot be a "
                    f"canonical write target (only company_raw may write)"
                )
            if read_only is True:
                raise CatalogConfigError(
                    f"roots[{index}] write target requires read_only=false"
                )
        # A reusable root must be read-only UNLESS it is the canonical
        # write target itself (company_raw is both reusable and writable).
        if (
            reusable_for_filing is True
            and read_only is not True
            and write_target is None
        ):
            raise CatalogConfigError(
                f"roots[{index}] reusable external root must be read_only"
            )
        # routes must be a subset of the root's allowed kinds (no widening)
        allowed_kinds = tuple(item.get("allowed_document_kinds", []) or [])
        routes = tuple(
            _parse_route_2x(raw_route, index, route_index, allowed_kinds)
            for route_index, raw_route in enumerate(item.get("routes", []) or [])
        )
        roots.append(
            RootSpec(
                root_id=root_id,
                path=_expand_path(raw_path, project_root=resolved_project),
                kind=kind,
                priority=int(item.get("priority", 100)),
                adapter_id=str(adapter_id) if adapter_id is not None else None,
                adapter_version_range=item.get("adapter_version_range"),
                admission_profile_id=(
                    str(profile_id) if profile_id is not None else None
                ),
                read_only=read_only,
                reusable_for_filing=reusable_for_filing,
                routes=routes,
                allowed_document_kinds=allowed_kinds,
                allowed_statuses=tuple(item.get("allowed_statuses", []) or []),
                symlink_policy=str(item.get("symlink_policy", "reject")),
                max_file_size=item.get("max_file_size"),
                sidecar_suffixes=tuple(item.get("sidecar_suffixes", []) or []),
                encoding=str(item.get("encoding", "utf-8")),
                privacy_class=str(item.get("privacy_class", "public")),
                cohort=(
                    str(item["cohort"]) if item.get("cohort") is not None else None
                ),
                canonical_write_target=(
                    str(item["canonical_write_target"])
                    if item.get("canonical_write_target") is not None
                    else None
                ),
            )
        )
    raw_kinds = data.get("reusable_root_kinds", ["company_raw"])
    if (
        not isinstance(raw_kinds, list)
        or not raw_kinds
        or not all(isinstance(kind, str) and kind.strip() for kind in raw_kinds)
    ):
        raise CatalogConfigError(
            "reusable_root_kinds must be a non-empty list of non-empty strings"
        )
    return CatalogConfig(
        project_root=resolved_project,
        catalog_dir=_expand_path(data["catalog_dir"], project_root=resolved_project),
        roots=tuple(roots),
        reusable_root_kinds=tuple(raw_kinds),
    )


def _parse_route_2x(
    raw, root_index: int, route_index: int, allowed_kinds: tuple[str, ...]
) -> RouteSpec:
    item = _mapping(raw, f"roots[{root_index}].routes[{route_index}]")
    unknown = set(item) - {
        "include",
        "exclude",
        "adapter_id",
        "admission_profile_id",
        "allowed_document_kinds",
    }
    if unknown:
        raise CatalogConfigError(
            f"roots[{root_index}].routes[{route_index}] unknown fields: "
            f"{sorted(unknown)}"
        )
    route_kinds = tuple(item.get("allowed_document_kinds", []) or [])
    extra = set(route_kinds) - set(allowed_kinds)
    if extra:
        raise CatalogConfigError(
            f"roots[{root_index}].routes[{route_index}] widens allowed kinds "
            f"beyond root policy: {sorted(extra)}"
        )
    adapter_id = item.get("adapter_id")
    if adapter_id is not None and registered_adapter(str(adapter_id)) is None:
        raise CatalogConfigError(
            f"routes[{route_index}] adapter_id {adapter_id!r} not registered"
        )
    return RouteSpec(
        include=tuple(item.get("include", []) or []),
        exclude=tuple(item.get("exclude", []) or []),
        adapter_id=str(adapter_id) if adapter_id is not None else None,
        admission_profile_id=item.get("admission_profile_id"),
    )


# --- 1.x -> 2.x doctor ------------------------------------------------------


_2X_FIELDS = (
    "adapter_id",
    "admission_profile_id",
    "read_only",
    "reusable_for_filing",
    "allowed_document_kinds",
    "cohort",
    "canonical_write_target",
)


def doctor_root_policy(
    path: Path, *, project_root: Path | None = None
) -> dict[str, Any]:
    """Report the config's RootPolicy version and which 2.x fields each root
    is missing.  Read-only; never changes production scan behavior."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    data = _mapping(payload, "config")
    schema = str(data.get("schema_version", "?"))
    raw_roots = data.get("roots", [])
    missing: list[str] = []
    for index, raw in enumerate(raw_roots):
        item = _mapping(raw, f"roots[{index}]")
        for field in _2X_FIELDS:
            if field not in item:
                missing.append(f"roots[{index}].{field}")
    # a config is 2.x when every root carries adapter + profile + write target
    every_root_explicit = all(
        "adapter_id" in _mapping(raw, f"roots[{index}]")
        and "admission_profile_id" in _mapping(raw, f"roots[{index}]")
        for index, raw in enumerate(raw_roots)
    )
    return {
        "schema": schema,
        "policy_version": "2.x" if every_root_explicit and not missing else "1.x",
        "missing_2x_fields": missing,
        "root_count": len(raw_roots),
    }


def export_policy_2x(config: CatalogConfig) -> tuple[str, dict[str, Any]]:
    """RootPolicySnapshot 2.0 canonical export + sha256.

    Consumers (filing-fetch, revenue) verify only the policy hash; the
    snapshot carries the ten contract fields per root (ADR-010).
    """
    roots = []
    for spec in config.roots:
        roots.append(
            {
                "root_id": spec.root_id,
                "path_ref": str(spec.path),
                "adapter_id": spec.adapter_id,
                "admission_profile_id": spec.admission_profile_id,
                "read_only": spec.read_only,
                # ZR-405: resolver-consistent reusability — an unset per-root
                # flag follows the kind-level reusable_root_kinds allowance.
                "reusable_for_filing": _effective_reusable_2x(spec, config),
                "allowed_document_kinds": list(spec.allowed_document_kinds),
                "canonical_write_target": getattr(spec, "canonical_write_target", None),
                "priority": spec.priority,
                "cohort": getattr(spec, "cohort", None),
            }
        )
    policy = {
        "schema_version": POLICY_2X_SCHEMA_VERSION,
        "reusable_root_kinds": list(config.reusable_root_kinds),
        "roots": roots,
    }
    payload = json.dumps(policy, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest(), policy


def _effective_reusable_2x(spec, config) -> bool:
    """Per-root reusable_for_filing if set, else the kind-level allowance."""
    if spec.reusable_for_filing is not None:
        return bool(spec.reusable_for_filing)
    return spec.kind in config.reusable_root_kinds


__all__ = [
    "POLICY_2X_SCHEMA_VERSION",
    "doctor_root_policy",
    "export_policy_2x",
    "load_root_policy_2x",
]
