#!/usr/bin/env python3
"""full_pipeline.py — retired unified pipeline entry (G4-CWP-PIPELINE).

The legacy Gate0-5 / financial-writer pipeline has been removed from this
repository.  This file is now a stdlib-thin retirement stub: importing it is
silent, and direct execution always retires with exit 78 before any
configuration, model, network, directory, or subprocess initialization.
"""

from __future__ import annotations

import sys

import writer_policy


RETIRED_EXIT_CODE = writer_policy.BLOCKED_EXIT_CODE
RETIRED_ENTRY = "full_pipeline.py"
RETIRED_MARKER = "LEGACY_PIPELINE_RETIRED"


def retirement_notice() -> str:
    """Build the full retirement notice for the retired pipeline entry."""
    header = "\n".join(
        (
            "=" * 60,
            f"  {RETIRED_MARKER}: scripts/{RETIRED_ENTRY}",
            "  Legacy unified pipeline (Gate0-5 checks + financial/research",
            "  writers) is retired as a whole family.",
            "  Current source CLI: company-wiki-source-catalog,",
            "  company-wiki-source-read, company-wiki-source-query,",
            "  company-wiki-source-export-v2; limited narrative runs use",
            "  scripts/narrative_evidence_pilot.py --help.",
            "  Direct execution, --help, --stage, --no-gates, --dry-run,",
            "  --gate-log, and unknown flags all exit 78.  There is no",
            "  authorization, review, or writer-restore path.",
            "=" * 60,
        )
    )
    return header + "\n" + writer_policy.blocked_message(RETIRED_ENTRY)


def main(argv=None) -> int:
    """Print the retirement notice and return the retired exit code."""
    del argv
    print(retirement_notice(), flush=True)
    return RETIRED_EXIT_CODE


if __name__ == "__main__":
    print(
        f"  {RETIRED_MARKER}: scripts/{RETIRED_ENTRY} "
        "legacy unified pipeline is retired as a whole family.",
        flush=True,
    )
    writer_policy.enforce_direct_cli(__name__, __file__)
    sys.exit(main(sys.argv[1:]))
