"""Versioned YAML configuration for the source catalog."""

from __future__ import annotations

import os
from pathlib import Path
import re
from typing import Any

import yaml

from .models import CatalogConfig, RootSpec


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
    if set(data) != {"schema_version", "catalog_dir", "roots"}:
        raise CatalogConfigError("config must contain exact schema_version/catalog_dir/roots fields")
    if str(data["schema_version"]) != "1.0":
        raise CatalogConfigError("schema_version must be 1.0")
    resolved_project = (project_root or path.resolve().parents[1]).resolve(strict=False)
    raw_roots = data["roots"]
    if not isinstance(raw_roots, list) or not raw_roots:
        raise CatalogConfigError("roots must be a non-empty list")
    roots: list[RootSpec] = []
    for index, raw in enumerate(raw_roots):
        item = _mapping(raw, f"roots[{index}]")
        unknown = set(item) - {"root_id", "path", "kind", "priority"}
        if unknown:
            raise CatalogConfigError(f"roots[{index}] unknown fields: {sorted(unknown)}")
        roots.append(
            RootSpec(
                root_id=str(item.get("root_id", "")),
                path=_expand_path(item.get("path"), project_root=resolved_project),
                kind=str(item.get("kind", "")),
                priority=int(item.get("priority", 100)),
            )
        )
    return CatalogConfig(
        project_root=resolved_project,
        catalog_dir=_expand_path(data["catalog_dir"], project_root=resolved_project),
        roots=tuple(roots),
    )


__all__ = ["CatalogConfigError", "load_catalog_config"]
