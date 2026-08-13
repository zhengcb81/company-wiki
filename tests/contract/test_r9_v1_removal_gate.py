"""R9 execution-packet gate: v1/legacy machinery must be gone (RED now).

These assertions are RED until the R9 wave executes (the v1 scanner, the
legacy bridge machinery, and the R9-backlog tools are still present while
the close gate's observation windows accumulate).  The gate turns GREEN
only after the deletions in ``assurance/fc/Phase-14/01_r9_packet.md`` land
— the same dead-helper gate pattern as FC-1203.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC))

# The gate is RED until the R9 wave executes (the observation windows are
# still accumulating).  It skips in daily suites and runs for real only
# with R9_GATE=1 — the R9 execution protocol flips it RED->GREEN.
pytestmark = pytest.mark.skipif(
    os.environ.get("R9_GATE") != "1",
    reason="R9 wave not executed yet (observation windows accumulating); "
           "run with R9_GATE=1 during the R9 execution protocol",
)


DELETED_MODULES = (
    "company_wiki.source_catalog.backfill_v2",
    "company_wiki.source_catalog.portfolio_promoter",
    "company_wiki.source_catalog.visibility_bridge",
    "company_wiki.source_catalog.legacy_close_gate",
)

DELETED_ATTRIBUTES = (
    ("company_wiki.source_catalog.scanner", "_scan_root_v1"),
)


def test_deleted_modules_are_unimportable():
    for name in DELETED_MODULES:
        assert name not in sys.modules
        try:
            importlib.import_module(name)
        except ModuleNotFoundError:
            continue
        raise AssertionError(f"R9 module {name} still importable")


def test_v1_scanner_function_is_absent():
    module = importlib.import_module("company_wiki.source_catalog.scanner")
    assert not hasattr(module, "_scan_root_v1"), "v1 scanner still present"


def test_bridge_flag_removed_from_flags():
    from company_wiki.source_catalog.flags import FLAGS

    assert "legacy_bridge_enabled" not in FLAGS, (
        "the legacy bridge flag must be gone after R9"
    )


def test_allowlist_shrinks_after_scanner_cleanup():
    from company_wiki.source_catalog.architecture_gate import (
        _ROOT_HARDCODE_ALLOWED_FILES,
    )

    assert "scanner.py" not in _ROOT_HARDCODE_ALLOWED_FILES, (
        "scanner.py must leave the frozen allowlist once the v1 root branches "
        "are deleted (real shrink, FC-1201 ratchet only moves down)"
    )
