"""Versioned external adapter command configuration."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any

import yaml

from .acquisition import AdapterRegistry
from .adapter_process import JsonCommandAdapter
from .dayu_cli_adapter import DayuCliDownloadAdapter


_TOKEN_RE = re.compile(r"\$\{([A-Z_]+)\}")


class AcquisitionConfigError(ValueError):
    """Raised when the acquisition command configuration is invalid."""


@dataclass(frozen=True)
class AdapterCommandSpec:
    name: str
    version: str
    interface: str
    project_root: Path
    config_root: Path | None
    command: tuple[str, ...]


@dataclass(frozen=True)
class AcquisitionConfig:
    schema_version: str
    staging_root: Path
    timeout_seconds: float
    cn: AdapterCommandSpec
    hk: AdapterCommandSpec
    us: AdapterCommandSpec

    def build_registry(self) -> AdapterRegistry:
        def build_json(spec: AdapterCommandSpec) -> JsonCommandAdapter:
            return JsonCommandAdapter(
                name=spec.name,
                version=spec.version,
                command=spec.command,
                project_root=spec.project_root,
                timeout_seconds=self.timeout_seconds,
            )

        def build_dayu(spec: AdapterCommandSpec, market: str) -> DayuCliDownloadAdapter:
            if spec.config_root is None:
                raise AcquisitionConfigError("dayu_cli_v1 adapter requires config_root")
            return DayuCliDownloadAdapter(
                name=spec.name,
                version=spec.version,
                market=market,
                command=spec.command,
                project_root=spec.project_root,
                config_root=spec.config_root,
                # Use system temp dir to avoid exceeding Windows MAX_PATH (260 chars)
                # when dayu creates deep nested paths inside the workspace.
                workspace_parent=Path(tempfile.gettempdir()) / "company-wiki-dayu",
                timeout_seconds=self.timeout_seconds,
            )

        if self.cn.interface != "json_command_v1":
            raise AcquisitionConfigError("CN adapter must use json_command_v1")
        if self.hk.interface != "dayu_cli_v1" or self.us.interface != "dayu_cli_v1":
            raise AcquisitionConfigError("HK/US adapters must use dayu_cli_v1")

        return AdapterRegistry(
            cn=build_json(self.cn),
            hk=build_dayu(self.hk, "HK"),
            us=build_dayu(self.us, "US"),
        )


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AcquisitionConfigError(f"{name} must be an object")
    return value


def _expand(value: Any, *, project_root: Path) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AcquisitionConfigError("configured text must be non-empty")
    tokens = {
        "PROJECT_ROOT": str(project_root),
        "USER_PROFILE": os.environ.get("USERPROFILE", str(Path.home())),
        "PYTHON_EXECUTABLE": str(Path(sys.executable).resolve()),
    }

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in tokens:
            raise AcquisitionConfigError(f"unsupported path token: {name}")
        return tokens[name]

    expanded = _TOKEN_RE.sub(replace, value.strip())
    if _TOKEN_RE.search(expanded):
        raise AcquisitionConfigError("unresolved acquisition config token")
    return expanded


def _path(value: Any, *, project_root: Path) -> Path:
    expanded = Path(_expand(value, project_root=project_root)).expanduser()
    if not expanded.is_absolute():
        expanded = project_root / expanded
    return expanded.resolve(strict=False)


def _adapter(value: Any, *, project_root: Path, name: str) -> AdapterCommandSpec:
    data = _mapping(value, name)
    if set(data) != {
        "name",
        "version",
        "interface",
        "project_root",
        "config_root",
        "command",
    }:
        raise AcquisitionConfigError(
            f"{name} must contain exact name/version/interface/project_root/config_root/command fields"
        )
    raw_command = data["command"]
    if not isinstance(raw_command, list) or not raw_command:
        raise AcquisitionConfigError(f"{name}.command must be a non-empty array")
    command = tuple(_expand(item, project_root=project_root) for item in raw_command)
    interface = _expand(data["interface"], project_root=project_root)
    if interface not in {"json_command_v1", "dayu_cli_v1"}:
        raise AcquisitionConfigError(f"{name}.interface is unsupported")
    raw_config_root = data["config_root"]
    if interface == "json_command_v1" and raw_config_root is not None:
        raise AcquisitionConfigError(f"{name}.config_root must be null for json_command_v1")
    if interface == "dayu_cli_v1" and raw_config_root is None:
        raise AcquisitionConfigError(f"{name}.config_root is required for dayu_cli_v1")
    return AdapterCommandSpec(
        name=_expand(data["name"], project_root=project_root),
        version=_expand(data["version"], project_root=project_root),
        interface=interface,
        project_root=_path(data["project_root"], project_root=project_root),
        config_root=(
            _path(raw_config_root, project_root=project_root)
            if raw_config_root is not None
            else None
        ),
        command=command,
    )


def load_acquisition_config(
    path: Path,
    *,
    project_root: Path,
) -> AcquisitionConfig:
    if not isinstance(path, Path) or not isinstance(project_root, Path):
        raise TypeError("path and project_root must be pathlib.Path")
    data = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), "config")
    if set(data) != {"schema_version", "staging_root", "timeout_seconds", "adapters"}:
        raise AcquisitionConfigError(
            "config must contain exact schema_version/staging_root/timeout_seconds/adapters"
        )
    if str(data["schema_version"]) != "1.1":
        raise AcquisitionConfigError("schema_version must be 1.1")
    timeout = data["timeout_seconds"]
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        raise AcquisitionConfigError("timeout_seconds must be positive")
    adapters = _mapping(data["adapters"], "adapters")
    if set(adapters) != {"cn", "hk", "us"}:
        raise AcquisitionConfigError("adapters must contain exact cn/hk/us fields")
    resolved_project = project_root.resolve(strict=True)
    return AcquisitionConfig(
        schema_version="1.1",
        staging_root=_path(data["staging_root"], project_root=resolved_project),
        timeout_seconds=float(timeout),
        cn=_adapter(adapters["cn"], project_root=resolved_project, name="adapters.cn"),
        hk=_adapter(adapters["hk"], project_root=resolved_project, name="adapters.hk"),
        us=_adapter(adapters["us"], project_root=resolved_project, name="adapters.us"),
    )


__all__ = [
    "AcquisitionConfig",
    "AcquisitionConfigError",
    "AdapterCommandSpec",
    "load_acquisition_config",
]
