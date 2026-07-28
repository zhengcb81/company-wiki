"""WR-3 §10.8.4 governance helpers — exported under the package ``tests.helpers``.

Pure read-only; never kills anything. Used by the autouse guard fixture in
``tests/contract/conftest.py`` and by the contract tests in
``test_source_catalog_temp_worker_governance.py``.
"""

from __future__ import annotations

from pathlib import Path


def scan_owned_temp_workers() -> set[int]:
    """Return the set of PIDs whose command line is a real ``worker``
    subcommand that points at a config under ``%TEMP%``/``%TMP%`` or under
    a ``\\pytest-of-`` directory.

    Implemented as a thin wrapper over
    ``company_wiki.source_catalog.control._scan_source_catalog_processes``
    (per WR-1); never terminates anything.
    """
    from company_wiki.source_catalog.control import _scan_source_catalog_processes

    inventory = _scan_source_catalog_processes(Path.cwd())
    return {int(w["pid"]) for w in inventory["pytest_temp_workers"]}
