"""Versioned YAML configuration for the source catalog."""

from __future__ import annotations

import os
from pathlib import Path
import re
from typing import Any

import yaml

from .adapters.registry import admission_profile, registered_adapter
from .models import CatalogConfig, RootSpec, RouteSpec


_TOKEN_RE = re.compile(r"\$\{([A-Z_]+)\}")


class CatalogConfigError(ValueError):
    """Raised when source-catalog configuration is invalid."""


def _mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CatalogConfigError(f"{field_name} must be an object")
    return value


def _expand_path(value: Any, *, project_root: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise CatalogConfigError("path must be non-empty text")
    tokens = {
        "PROJECT_ROOT": str(project_root),
        "USER_PROFILE": os.environ.get("USERPROFILE", str(Path.home())),
    }

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in tokens:
            raise CatalogConfigError(f"unsupported path token: {name}")
        return tokens[name]

    expanded = _TOKEN_RE.sub(replace, value.strip())
    if _TOKEN_RE.search(expanded):
        raise CatalogConfigError("unresolved path token")
    path = Path(expanded).expanduser()
    if not path.is_absolute():
        path = project_root / path
    return path.resolve(strict=False)


def load_catalog_config(path: Path, *, project_root: Path | None = None) -> CatalogConfig:
    if not isinstance(path, Path):
        raise TypeError("path must be pathlib.Path")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    data = _mapping(payload, "config")
    required = {"schema_version", "catalog_dir", "roots"}
    allowed = required | {"reusable_root_kinds"}
    if not set(data) <= allowed or not required <= set(data):
        raise CatalogConfigError(
            "config must contain schema_version/catalog_dir/roots fields "
            "(optional: reusable_root_kinds)"
        )
    if str(data["schema_version"]) != "1.0":
        raise CatalogConfigError("schema_version must be 1.0")
    resolved_project = (project_root or path.resolve().parents[1]).resolve(strict=False)
    raw_roots = data["roots"]
    if not isinstance(raw_roots, list) or not raw_roots:
        raise CatalogConfigError("roots must be a non-empty list")
    roots: list[RootSpec] = []
    seen_root_ids: set[str] = set()
    for index, raw in enumerate(raw_roots):
        item = _mapping(raw, f"roots[{index}]")
        # WU-301: v2 additive fields; v1 configs (no v2 keys) load unchanged.
        allowed_root_fields = {
            "root_id", "path", "kind", "priority", "adapter_id",
            "adapter_version_range", "admission_profile_id", "read_only",
            "reusable_for_filing", "routes", "allowed_document_kinds",
            "allowed_statuses", "symlink_policy", "max_file_size",
            "sidecar_suffixes", "encoding", "privacy_class",
        }
        unknown = set(item) - allowed_root_fields
        if unknown:
            raise CatalogConfigError(f"roots[{index}] unknown fields: {sorted(unknown)}")
        root_id = str(item.get("root_id", ""))
        if root_id in seen_root_ids:
            raise CatalogConfigError(f"duplicate root_id: {root_id} (CFG-03)")
        seen_root_ids.add(root_id)
        raw_path = item.get("path", "")
        unresolved = _unresolved_variables(raw_path)
        if unresolved:
            raise CatalogConfigError(
                f"roots[{index}] path contains unresolved variable(s) "
                f"{sorted(unresolved)} (CFG-04)"
            )
        adapter_id = item.get("adapter_id")
        if adapter_id is not None and registered_adapter(str(adapter_id)) is None:
            raise CatalogConfigError(
                f"roots[{index}] adapter_id {adapter_id!r} not registered (CFG-01)"
            )
        profile_id = item.get("admission_profile_id")
        if profile_id is not None and admission_profile(str(profile_id)) is None:
            raise CatalogConfigError(
                f"roots[{index}] admission_profile_id {profile_id!r} unknown (CFG-02)"
            )
        read_only = item.get("read_only", True)
        reusable_for_filing = item.get("reusable_for_filing")
        if reusable_for_filing is True and read_only is not True:
            raise CatalogConfigError(
                f"roots[{index}] reusable external root must be read_only (CFG-05)"
            )
        if reusable_for_filing is True and adapter_id is not None:
            adapter = registered_adapter(str(adapter_id))
            if adapter and "filing" not in adapter.get("capabilities", ()):
                raise CatalogConfigError(
                    f"roots[{index}] adapter {adapter_id!r} cannot serve filing "
                    "(CFG-07)"
                )
        routes = tuple(
            _parse_route(raw_route, index, route_index)
            for route_index, raw_route in enumerate(item.get("routes", []) or [])
        )
        _check_route_overlap(routes, index)
        roots.append(
            RootSpec(
                root_id=root_id,
                path=_expand_path(raw_path, project_root=resolved_project),
                kind=str(item.get("kind", "")),
                priority=int(item.get("priority", 100)),
                adapter_id=str(adapter_id) if adapter_id is not None else None,
                adapter_version_range=item.get("adapter_version_range"),
                admission_profile_id=(
                    str(profile_id) if profile_id is not None else None
                ),
                read_only=read_only,
                reusable_for_filing=reusable_for_filing,
                routes=routes,
                allowed_document_kinds=tuple(item.get("allowed_document_kinds", []) or []),
                allowed_statuses=tuple(item.get("allowed_statuses", []) or []),
                symlink_policy=str(item.get("symlink_policy", "reject")),
                max_file_size=item.get("max_file_size"),
                sidecar_suffixes=tuple(item.get("sidecar_suffixes", []) or []),
                encoding=str(item.get("encoding", "utf-8")),
                privacy_class=str(item.get("privacy_class", "public")),
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


_CONTROLLED_PATH_TOKENS = {"PROJECT_ROOT", "USER_PROFILE"}


def _unresolved_variables(raw_path) -> set[str]:
    """Variables inside ${...} that are not controlled tokens (CFG-04)."""
    if not isinstance(raw_path, str):
        return {"<non-string-path>"}
    used = set(re.findall(r"\$\{([^}]+)\}", raw_path))
    return used - _CONTROLLED_PATH_TOKENS


def _parse_route(raw, root_index: int, route_index: int) -> RouteSpec:
    item = _mapping(raw, f"roots[{root_index}].routes[{route_index}]")
    unknown = set(item) - {"include", "exclude", "adapter_id", "admission_profile_id"}
    if unknown:
        raise CatalogConfigError(
            f"roots[{root_index}].routes[{route_index}] unknown fields: {sorted(unknown)}"
        )
    adapter_id = item.get("adapter_id")
    if adapter_id is not None and registered_adapter(str(adapter_id)) is None:
        raise CatalogConfigError(
            f"routes[{route_index}] adapter_id {adapter_id!r} not registered (CFG-01)"
        )
    return RouteSpec(
        include=tuple(item.get("include", []) or []),
        exclude=tuple(item.get("exclude", []) or []),
        adapter_id=str(adapter_id) if adapter_id is not None else None,
        admission_profile_id=item.get("admission_profile_id"),
    )


_OVERLAP_SAMPLES = (
    "x.pdf", "a/b/c.pdf", "annual/2025.pdf", "financial_reports/x.pdf",
    "report.md", "2025.pdf", "dir/x.pdf", "dir/annual/2025.pdf",
    "互联网/哔哩哔哩/2025年报.pdf",
)


def _glob_overlap(a: tuple[str, ...], b: tuple[str, ...]) -> bool:
    """Two route include sets overlap when some plausible relative path is
    matched by both (CFG-06/08).  fnmatch on a fixed sample set keeps the
    check deterministic and testable."""
    import fnmatch

    for sample in _OVERLAP_SAMPLES:
        matches_a = any(fnmatch.fnmatch(sample, pattern) for pattern in a)
        matches_b = any(fnmatch.fnmatch(sample, pattern) for pattern in b)
        if matches_a and matches_b:
            return True
    return False


def _check_route_overlap(routes: tuple[RouteSpec, ...], root_index: int) -> None:
    """CFG-06/08: overlapping routes with no unique order would admit the
    same physical file twice — reject at load time."""
    for i in range(len(routes)):
        for j in range(i + 1, len(routes)):
            if _glob_overlap(routes[i].include, routes[j].include):
                raise CatalogConfigError(
                    f"roots[{root_index}] routes[{i}] and routes[{j}] overlap "
                    f"(CFG-06/08)"
                )


__all__ = ["CatalogConfigError", "load_catalog_config"]
