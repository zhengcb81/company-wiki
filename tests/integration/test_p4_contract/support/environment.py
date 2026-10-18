"""Environment resolution and the production-config guard (P4 card 5.1).

The only permitted hard failure in this lane is ``CWP_P4_CATALOG_CONFIG``
pointing at production configuration or outside both permitted fixture roots.
"""

from __future__ import annotations

import os
from pathlib import Path

from . import constants as C


class ProductionConfigRefused(AssertionError):
    """Raised when the catalog switch targets production or an unapproved path."""


def _clean(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None:
        return None
    stripped = value.strip().strip('"').strip("'")
    return stripped or None


def require_flag() -> bool:
    """``CWP_P4_REQUIRE == "1"`` turns every skip into a failure."""
    return _clean(C.ENV_REQUIRE) == "1"


def catalog_config_path() -> Path | None:
    raw = _clean(C.ENV_CATALOG)
    return Path(raw) if raw is not None else None


def consumer_commands_path() -> Path | None:
    raw = _clean(C.ENV_CONSUMER_COMMANDS)
    return Path(raw) if raw is not None else None


def consumer_root(consumer: str) -> Path | None:
    name = C.ENV_FF_ROOT if consumer == "ff" else C.ENV_RF_ROOT
    raw = _clean(name)
    return Path(raw) if raw is not None else None


def permitted_catalog_roots(tmp_path: Path | None = None) -> tuple[Path, ...]:
    roots = [C.FIXTURES_DIR.resolve()]
    if tmp_path is not None:
        roots.append(Path(tmp_path).resolve())
    return tuple(roots)


def assert_catalog_config_allowed(path: Path, *, tmp_path: Path | None = None) -> Path:
    """Resolve ``path`` and prove it is an approved test catalog.

    ``CWP_P4_CATALOG_CONFIG`` must be an absolute path below ``tmp_path`` or this
    card's ``fixtures/``; anything else - production config included - hard-fails
    rather than silently skipping.

    The existence check runs *before* ``samefile``: ``Path.samefile`` raises a
    bare ``FileNotFoundError`` when the given path does not exist, which would
    escape this function as an unhandled OS error instead of the refusal this
    guard promises (review finding P4-R1).
    """
    resolved = path.resolve()
    if not resolved.is_file():
        raise ProductionConfigRefused(
            f"{C.ENV_CATALOG} does not exist: {resolved}"
        )
    production = C.PRODUCTION_CATALOG_CONFIG.resolve()
    if resolved == production or (
        production.exists() and resolved.samefile(production)
    ):
        raise ProductionConfigRefused(
            f"{C.ENV_CATALOG} must not point at production config "
            f"config/source_catalog.yaml (got {resolved})"
        )
    roots = permitted_catalog_roots(tmp_path)
    if not any(resolved.is_relative_to(root) for root in roots):
        raise ProductionConfigRefused(
            f"{C.ENV_CATALOG} must be an absolute path under tmp_path or "
            f"{C.FIXTURES_DIR}; got {resolved}"
        )
    return resolved
