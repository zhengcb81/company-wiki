"""Fail-closed launch policy for legacy production writers.

This module deliberately uses only the Python standard library so it can run
before project configuration, dotenv loading, network clients, or writer
modules are imported.

Entry classification is static: supported control and source-workflow tools
always run, permanently retired research/Wiki writers never run, the retired
engineering gate/batch shells report ``LEGACY_ENGINEERING_TOOL_RETIRED`` and
exit 78, and every other legacy entry stays frozen until it is normalized or
retired.  The historic ``COMPANY_WIKI_WRITE_MODE`` / ``COMPANY_WIKI_LEGACY_WRITERS``
permission pair no longer changes any result.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping


BLOCKED_EXIT_CODE = 78
SCRIPTS_DIR = Path(__file__).resolve().parent

# These tools write only isolated receipts/manifests or inspect the repository.
# Production-data writers, test frameworks, cleanup tools, and migration tools
# are intentionally absent.  config_doctor is the read-only production-config
# maintenance entry (R4.1/N-05) and must behave the same in every startup mode.
# The retired engineering gates/batch shells left this list in G5-CWP-CHECKS;
# they now belong to RETIRED_ENGINEERING_TOOL_SCRIPTS below.
CONTROL_TOOL_ALLOWLIST = frozenset(
    {
        "config_doctor.py",
        "legacy_observer.py",
        "recovery_baseline.py",
        "secret_audit.py",
        "snapshot_manifest.py",
        "wr109_step6_capture.py",
    }
)

# G5-CWP-CHECKS retirement category: the six old engineering gates and batch
# shells are standard-library-only stubs.  Direct invocation (legacy arguments,
# ``--help``, ``python -S``) prints ``LEGACY_ENGINEERING_TOOL_RETIRED`` and
# exits 78; importing them initialises nothing.  They are not supported control
# tools, they are not research/Wiki writers, and no environment value, flag or
# approval re-enables the old chain.  Current checks live in
# .pre-commit-config.yaml, .githooks/pre-push, tools/pre_push_gate.py and
# .github/workflows/ci.yml.
RETIRED_ENGINEERING_TOOL_SCRIPTS = frozenset(
    {
        "architecture_gate.py",
        "batch_process.py",
        "clean_env_gate.py",
        "gold_gate.py",
        "semantic_gate.py",
        "test_framework.py",
    }
)

# Source narrative workflows belong to the canonical source system.  The
# configured finite batch entry only loads the authoritative LLM configuration
# and composes the bounded source CLI; it is not a legacy research writer.
# These tools retain their own byte/path/transaction checks.  The completed
# one-off catalog retirement, cutover, audit and
# derived-archive deletion tools were removed together with their dedicated
# test chain (see the G1-LEGACY handoff).
SOURCE_WORKFLOW_TOOL_ALLOWLIST = frozenset(
    {
        "narrative_batch_configured.py",
        "narrative_evidence_pilot.py",
        "narrative_summary_review_pilot.py",
    }
)

# These entry points create or orchestrate legacy research semantics, formal
# research output, review/Wiki state, or destructive cleanup/reset operations.
# The source-only and immutable-raw boundaries are permanent: compatibility
# environment variables must never restore them.
PERMANENTLY_RETIRED_SCRIPTS = frozenset(
    {
        "auto_synthesis.py",
        "auto_discover.py",
        "batch_assessment.py",
        "batch_ingest.py",
        "batch_process.py",
        "build_links.py",
        "cleanup_deprecated.py",
        "cleanup_junk.py",
        "cleanup_log.py",
        "consolidate.py",
        "cross_verify.py",
        "enrich_wiki.py",
        "evolve_questions.py",
        "expire_tracker.py",
        "fix_broken_links.py",
        "fix_sources_count.py",
        "full_pipeline.py",
        "generate_dashboard.py",
        "generate_index.py",
        "generate_slides.py",
        "ingest_v2.py",
        "investment_judgment.py",
        "maintenance.py",
        "query.py",
        "question_evolver.py",
        "quality_dashboard.py",
        "refine.py",
        "reprocess.py",
        "reset_ingested.py",
        "review_queue.py",
        "scheduler.py",
        "stage3_analyze.py",
        "stage4_review.py",
        "stage5_ingest.py",
        "stage6_synthesize.py",
        "tag_segments.py",
        "valuation_engine.py",
        "wikilinks.py",
    }
)


def _script_name(script_path: str | os.PathLike[str]) -> str:
    try:
        return Path(script_path).name
    except (OSError, TypeError, ValueError):
        return ""


def _supported_tool(script_name: str) -> bool:
    return (
        script_name in CONTROL_TOOL_ALLOWLIST
        or script_name in SOURCE_WORKFLOW_TOOL_ALLOWLIST
    )


def legacy_script_execution_allowed(
    script_path: str | os.PathLike[str],
    environment: Mapping[str, str] | None = None,
) -> bool:
    """Return whether an explicitly requested legacy script may execute.

    The result is a pure function of the entry classification.  Permanently
    retired research/Wiki writers never run, supported control and
    source-pilot tools always run, and un-normalized mixed legacy entries
    stay frozen.  ``environment`` is accepted so existing callers keep
    working, but permission variables no longer change the outcome.
    """
    del environment
    name = _script_name(script_path)
    if name in RETIRED_ENGINEERING_TOOL_SCRIPTS:
        return False
    if name in PERMANENTLY_RETIRED_SCRIPTS:
        return False
    return _supported_tool(name)


def is_legacy_script_cli(script_path: str | os.PathLike[str]) -> bool:
    """Return whether *script_path* is a directly executed, frozen script."""
    try:
        path = Path(script_path).resolve()
    except (OSError, TypeError, ValueError):
        return False
    return (
        path.parent == SCRIPTS_DIR
        and path.suffix.casefold() == ".py"
        and path.name not in CONTROL_TOOL_ALLOWLIST
        and path.name not in SOURCE_WORKFLOW_TOOL_ALLOWLIST
        and path.name not in {"sitecustomize.py", "writer_policy.py"}
    )


def blocked_message(script_name: str) -> str:
    script_name = _script_name(script_name)
    if script_name in RETIRED_ENGINEERING_TOOL_SCRIPTS:
        # Checked first: batch_process.py is also permanently retired, but both
        # startup paths (sitecustomize here, the stub under `python -S`) must
        # report the same engineering retirement marker.
        return (
            "=" * 60
            + f"\n  LEGACY ENGINEERING TOOL RETIRED: {script_name}\n"
            + "  LEGACY_ENGINEERING_TOOL_RETIRED\n\n"
            + "  This old engineering gate / batch shell is retired.  It no longer\n"
            + "  evaluates rules, copies candidate trees, writes receipts or starts\n"
            + "  any pipeline.  Current checks live in .pre-commit-config.yaml,\n"
            + "  .githooks/pre-push, tools/pre_push_gate.py and\n"
            + "  .github/workflows/ci.yml; see control/README.md for the history.\n"
            + "  Environment overrides cannot re-enable this entry.\n"
            + "=" * 60
        )
    if script_name in PERMANENTLY_RETIRED_SCRIPTS:
        return (
            "=" * 60
            + f"\n  LEGACY WRITER BLOCKED - PERMANENTLY RETIRED: {script_name}\n\n"
            + "  company-wiki is source-only and cannot run research, "
            + "assessment, valuation, review, or Wiki writers.\n"
            + "  Use company-wiki-source-catalog for source scanning, "
            + "normalization, quality, query, and export.\n"
            + "  Investment research and review belong to StockWiki.\n"
            + "  Environment overrides cannot re-enable this entry.\n"
            + "=" * 60
        )
    return (
        "=" * 60
        + f"\n  LEGACY WRITER BLOCKED: {script_name}\n\n"
        + "  This legacy entry is not on the supported control / "
        + "source-pilot list.\n"
        + "  It stays frozen before config, LLM, network, or writes until "
        + "it is normalized\n"
        + "  or retired; environment settings cannot enable it.\n"
        + "  Investment research and review belong to StockWiki.\n"
        + "=" * 60
    )


def enforce_direct_cli(
    module_name: str,
    script_path: str | os.PathLike[str],
    environment: Mapping[str, str] | None = None,
) -> None:
    """Terminate a directly executed legacy script before it can initialize."""
    if module_name != "__main__" or not is_legacy_script_cli(script_path):
        return
    if legacy_script_execution_allowed(script_path, environment):
        return
    print(blocked_message(Path(script_path).name), flush=True)
    raise SystemExit(BLOCKED_EXIT_CODE)
