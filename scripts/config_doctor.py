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
        # CI runners have no production catalog; they still get structure +
        # cross-repo checks. Production machines must have the catalog.
        if os.environ.get("CI") != "true":
            problems.append(f"catalog_dir is not a directory: {config.catalog_dir}")
    else:
        master = config.catalog_dir / "security_master"
        files = sorted(master.glob("*.json")) if master.is_dir() else []
        if not files:
            problems.append(
                f"no security_master/*.json under {config.catalog_dir} "
                "(filing-fetch identity lookups will fail)"
            )
    _cross_repo_checks(config, root, problems)
    return problems


def _cross_repo_checks(config, root: Path, problems: list[str]) -> None:
    """E2E-F03: cross-repo config drift must fail fast at doctor time.

    1. kind=directory roots must be EXACTLY {dropbox_stock} (a second
       directory root would silently gain reuse rights).
    2. FC-501 (CONFIG-DBX-03/04): filing-fetch holds NO independent root
       allowance (allowed_handle_roots is rejected by its config schema);
       the Dropbox root's single source of truth is this
       source_catalog.yaml.  The doctor verifies the wiki side only.
    """
    directory_roots = {
        str(r.root_id) for r in config.roots if r.kind == "directory"
    }
    # Zero directory roots is fine (no Dropbox configured); if any exist they
    # must be EXACTLY {dropbox_stock} (a second directory root would silently
    # gain reuse rights under kind-level authorization).
    if directory_roots and directory_roots != {"dropbox_stock"}:
        problems.append(
            "kind=directory roots must be exactly {dropbox_stock}, "
            f"got {sorted(directory_roots)}"
        )
    filing_config = (
        root.parent / "filing-fetch" / "config" / "company_wiki.json"
    )
    if not filing_config.is_file():
        return  # filing-fetch absent in this workspace — skip
    try:
        import json
        import os

        payload = json.loads(filing_config.read_text(encoding="utf-8"))
        dropbox_wiki = next(
            (r for r in config.roots if r.root_id == "dropbox_stock"), None
        )
        if dropbox_wiki is None:
            problems.append("dropbox_stock root missing from source_catalog.yaml")
            return
        # FC-501: a filing-fetch config smuggling back an independent root
        # allowlist is a contract violation (CONFIG-DBX-03).
        if payload.get("allowed_handle_roots"):
            problems.append(
                "filing-fetch config must NOT carry allowed_handle_roots "
                "(FC-501: the policy snapshot is the single source; the "
                "config schema rejects it)"
            )
        profile = os.environ.get("USERPROFILE") or str(Path.home())
        wiki_path = str(dropbox_wiki.path).replace("${USER_PROFILE}", profile)
        if not Path(wiki_path).resolve().name == "Stock" or "Dropbox" not in str(Path(wiki_path)):
            problems.append(
                f"dropbox_stock path does not point at Dropbox/Stock: {wiki_path}"
            )
    except Exception as exc:  # noqa: BLE001 - report every failure mode
        problems.append(f"cross-repo config check failed: {exc}")


def main() -> int:
    problems = diagnose()
    for problem in problems:
        print(f"CONFIG-PROBLEM: {problem}")
    if not problems:
        print(f"OK: {CONFIG_PATH} healthy")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
