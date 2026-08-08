"""Production-config doctor (R4.1, roadmap RC-4 / N-05).

Validates ``config/source_catalog.yaml`` so a polluted or broken production
configuration is detected at test/session time instead of silently breaking
the live filing chain (N-05: the config had been overwritten by a single-line
JSON fixture and every filing-fetch live test failed).

Exit code 0 = healthy, 1 = problems found.  Run it from the repo root or from
anywhere; the config path and project root resolve relative to this file.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "source_catalog.yaml"


def diagnose(
    config_path: Path | None = None, project_root: Path | None = None
) -> list[str]:
    """Return a list of config problems (empty = healthy)."""
    path = config_path or CONFIG_PATH
    root = project_root or ROOT
    problems: list[str] = []
    if not path.is_file():
        return [f"missing config: {path}"]
    raw = path.read_text(encoding="utf-8")
    # N-05 signature: a single-line JSON fixture replaces the YAML file.
    if raw.lstrip().startswith("{") and "\n" not in raw.strip():
        problems.append(
            f"config looks like a single-line JSON fixture, not YAML: {path}"
        )
        return problems
    try:
        from company_wiki.source_catalog.config import load_catalog_config

        config = load_catalog_config(path, project_root=root)
    except Exception as exc:  # noqa: BLE001 - report every failure mode
        problems.append(f"config failed to load: {exc}")
        return problems
    if not config.catalog_dir.is_dir():
        problems.append(f"catalog_dir is not a directory: {config.catalog_dir}")
    else:
        master = config.catalog_dir / "security_master"
        files = sorted(master.glob("*.json")) if master.is_dir() else []
        if not files:
            problems.append(
                f"no security_master/*.json under {config.catalog_dir} "
                "(filing-fetch identity lookups will fail)"
            )
    return problems


def main() -> int:
    problems = diagnose()
    for problem in problems:
        print(f"CONFIG-PROBLEM: {problem}")
    if not problems:
        print(f"OK: {CONFIG_PATH} healthy")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
