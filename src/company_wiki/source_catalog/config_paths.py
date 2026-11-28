"""Shared path and token semantics for CWP owner configuration."""
from __future__ import annotations

import os
from pathlib import Path
import re
import sys


_TOKEN = re.compile(r"\$\{([A-Z_]+)\}")


class ConfigPathTokenError(ValueError):
    """An explicitly requested configuration token cannot be resolved."""


def expand_tokens(text: str, *, project_root: Path, allow_python_executable: bool = False) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name == "PROJECT_ROOT":
            return str(project_root)
        if name == "USER_PROFILE":
            profile = os.environ.get("USERPROFILE")
            return profile if profile is not None else str(Path.home())
        if name == "PYTHON_EXECUTABLE" and allow_python_executable:
            return str(Path(sys.executable).resolve())
        raise ConfigPathTokenError(f"unsupported path token: {name}")

    expanded = _TOKEN.sub(replace, text.strip())
    if _TOKEN.search(expanded):
        raise ConfigPathTokenError("unresolved path token")
    return expanded


def project_path(text: str, *, project_root: Path) -> Path:
    path = Path(text).expanduser()
    return (path if path.is_absolute() else project_root / path).resolve(strict=False)
