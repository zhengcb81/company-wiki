#!/usr/bin/env python3
"""Retired architecture rule gate (G5-CWP-CHECKS).

Direct invocation — legacy arguments, ``--help``, ``python -S`` — and
``main()`` report ``LEGACY_ENGINEERING_TOOL_RETIRED`` and exit 78.  Importing
this module initialises nothing: no candidate tree is copied, no receipt is
written and no model/Store/downloader is constructed.
"""

from __future__ import annotations

import sys
from pathlib import Path

EXIT_CODE = 78
MARKER = "LEGACY_ENGINEERING_TOOL_RETIRED"
SCRIPT_NAME = Path(__file__).name


def retired_message() -> str:
    """Return the retirement banner printed on direct invocation and by main()."""
    return (
        "=" * 60
        + f"\n  LEGACY ENGINEERING TOOL RETIRED: {SCRIPT_NAME}\n"
        + f"  {MARKER}\n\n"
        + "  This old engineering gate / batch shell is retired.  It no longer\n"
        + "  evaluates rules, copies candidate trees, writes receipts or starts\n"
        + "  any pipeline.  Current checks live in .pre-commit-config.yaml,\n"
        + "  .githooks/pre-push, tools/pre_push_gate.py and\n"
        + "  .github/workflows/ci.yml; see control/README.md for the history.\n"
        + "  Environment overrides cannot re-enable this entry.\n"
        + "=" * 60
    )


def main(argv: list[str] | None = None) -> int:
    """Report retirement.  ``argv`` is accepted and deliberately ignored."""
    del argv
    print(retired_message(), flush=True)
    return EXIT_CODE


if __name__ == "__main__":
    raise SystemExit(main())
