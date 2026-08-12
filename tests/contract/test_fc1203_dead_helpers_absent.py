"""FC-1203 gate: dead-helper=0 — deleted symbols must stay deleted.

Each entry below was verified to have ZERO production callers (AST + grep)
before deletion (findings 59).  The gate turns deletion into a machine-
enforced contract: resurrecting any of them (mutation M-revive) must fail
these tests, forcing a review of WHY the symbol came back.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC))

# Modules deleted in FC-1203 — import must fail.
# (restore.py is KEPT: the approved production remediation tool
#  scripts/wu904_remediation_restore.py calls restore_asset gates, FC-403 trail.)
DELETED_MODULES = (
    "company_wiki.source_catalog.entity_resolver",
    "company_wiki.source_catalog.reuse_latest_policy",
)

# Attributes deleted from surviving modules.
# (evaluate_candidate is KEPT: Phase 14 R3/R5 admission policy, sealed
#  FC-502 contract tests call it; production wiring is a release-wave item.)
DELETED_ATTRIBUTES = (
    ("company_wiki.source_catalog.normalized_meta", "validate_normalized_filing"),
    ("company_wiki.source_catalog.flags", "atomic_rollback"),
)

# Files deleted wholesale.
DELETED_FILES = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "wu905_catalog_switch_check.py",
)


def test_deleted_modules_are_unimportable() -> None:
    for name in DELETED_MODULES:
        assert name not in sys.modules
        try:
            importlib.import_module(name)
        except ModuleNotFoundError:
            continue
        raise AssertionError(f"deleted module {name} is importable again")


def test_deleted_attributes_are_absent() -> None:
    for module_name, attr in DELETED_ATTRIBUTES:
        module = importlib.import_module(module_name)
        assert not hasattr(module, attr), f"{module_name}.{attr} resurrected"


def test_deleted_files_are_gone() -> None:
    for path in DELETED_FILES:
        assert not path.exists(), f"deleted file resurrected: {path}"
