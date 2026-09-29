"""Production-config doctor (R4.1, roadmap RC-4 / N-05).

Validates ``config/source_catalog.yaml`` so a polluted or broken production
configuration is detected at test/session time instead of silently breaking
the live filing chain (N-05: the config had been overwritten by a single-line
JSON fixture and every filing-fetch live test failed).

Exit code 0 = healthy, 1 = problems found.  Run it from the repo root or from
anywhere; the config path and project root resolve relative to this file.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "source_catalog.yaml"


def diagnose(
    config_path: Path | None = None,
    project_root: Path | None = None,
    filing_fetch_config: Path | None = None,
    check_catalog_data: bool = True,
) -> list[str]:
    """Return a list of config problems (empty = healthy).

    ``filing_fetch_config``: optional explicit path to filing-fetch's
    ``config/company_wiki.json`` for the cross-repo check.  When omitted the
    cross-repo check is skipped (FC-1202: no implicit sibling-directory
    lookup); the three-repo doctor lives in filing-fetch's CI
    (``filing-fetch/tools/config_doctor.py``).
    """
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
        # Code-only worktrees and CI runners have no production catalog.
        # Explicit structure-only mode still checks YAML and root shape.
        if check_catalog_data and os.environ.get("CI") != "true":
            problems.append(f"catalog_dir is not a directory: {config.catalog_dir}")
    elif check_catalog_data:
        master = config.catalog_dir / "security_master"
        files = sorted(master.glob("*.json")) if master.is_dir() else []
        if not files:
            problems.append(
                f"no security_master/*.json under {config.catalog_dir} "
                "(filing-fetch identity lookups will fail)"
            )
    _cross_repo_checks(config, problems, filing_fetch_config)
    return problems


def _cross_repo_checks(
    config,
    problems: list[str],
    filing_fetch_config: Path | None,
) -> None:
    """Check root path shape and the optional filing-fetch config contract.

    Root IDs and physical locations are configuration, not an allowlist in
    Python.  The config loader already rejects duplicate IDs and invalid path
    tokens; an existing path that is a file cannot serve as a scan root.
    """
    for configured_root in config.roots:
        try:
            if configured_root.path.exists() and not configured_root.path.is_dir():
                problems.append(
                    f"root {configured_root.root_id} path is not a directory: "
                    f"{configured_root.path}"
                )
        except OSError as exc:
            problems.append(f"root {configured_root.root_id} path check failed: {exc}")
    if filing_fetch_config is None:
        # FC-1202: no implicit sibling-directory lookup — the cross-repo
        # check runs only when the caller passes an explicit path (the
        # three-repo doctor lives in filing-fetch's CI).
        return
    filing_config = Path(filing_fetch_config)
    if not filing_config.is_file():
        problems.append(
            f"filing-fetch config does not exist: {filing_config}"
        )
        return
    try:
        import json

        payload = json.loads(filing_config.read_text(encoding="utf-8"))
        # FC-501: a filing-fetch config smuggling back an independent root
        # allowlist is a contract violation (CONFIG-DBX-03).
        if payload.get("allowed_handle_roots"):
            problems.append(
                "filing-fetch config must NOT carry allowed_handle_roots "
                "(FC-501: the policy snapshot is the single source; the "
                "config schema rejects it)"
            )
    except Exception as exc:  # noqa: BLE001 - report every failure mode
        problems.append(f"cross-repo config check failed: {exc}")


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Production-config doctor (R4.1, roadmap RC-4 / N-05)."
    )
    parser.add_argument(
        "--structure-only", action="store_true",
        help="validate config structure without requiring a local production catalog",
    )
    parser.add_argument(
        "--filing-fetch-config",
        type=Path,
        default=None,
        help="explicit path to filing-fetch's config/company_wiki.json for "
        "the cross-repo check (FC-1202: skipped when omitted)",
    )
    args = parser.parse_args(argv)
    problems = diagnose(
        filing_fetch_config=args.filing_fetch_config,
        check_catalog_data=not args.structure_only,
    )
    for problem in problems:
        print(f"CONFIG-PROBLEM: {problem}")
    if not problems:
        print(f"OK: {CONFIG_PATH} healthy")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
