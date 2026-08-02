"""Fail-closed launch policy for legacy production writers.

This module deliberately uses only the Python standard library so it can run
before project configuration, dotenv loading, network clients, or writer
modules are imported.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping


BLOCKED_EXIT_CODE = 78
SCRIPTS_DIR = Path(__file__).resolve().parent

# These tools write only isolated receipts/manifests or inspect the repository.
# Production-data writers, test frameworks, cleanup tools, and migration tools
# are intentionally absent.
CONTROL_TOOL_ALLOWLIST = frozenset(
    {
        "architecture_gate.py",
        "clean_env_gate.py",
        "deletion_manifest.py",
        "gate_runner.py",
        "gate_state.py",
        "recovery_baseline.py",
        "reviewer_gate.py",
        "secret_audit.py",
        "semantic_gate.py",
        "snapshot_manifest.py",
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


def legacy_writer_authorized(environment: Mapping[str, str] | None = None) -> bool:
    """Require two explicit factors; either one alone must fail closed."""
    environment = os.environ if environment is None else environment
    return (
        environment.get("COMPANY_WIKI_WRITE_MODE", "").casefold() == "legacy"
        and environment.get("COMPANY_WIKI_LEGACY_WRITERS", "").casefold() == "allow"
    )


def _script_name(script_path: str | os.PathLike[str]) -> str:
    try:
        return Path(script_path).name
    except (OSError, TypeError, ValueError):
        return ""


def legacy_script_execution_allowed(
    script_path: str | os.PathLike[str],
    environment: Mapping[str, str] | None = None,
) -> bool:
    """Return whether an explicitly requested legacy script may execute.

    Research/Wiki orchestration and destructive/reset entries are permanently
    retired.  Other compatibility scripts retain the existing two-factor
    authorization until a later caller-class audit routes or retires them.
    """
    if _script_name(script_path) in PERMANENTLY_RETIRED_SCRIPTS:
        return False
    return legacy_writer_authorized(environment)


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
        and path.name not in {"sitecustomize.py", "writer_policy.py"}
    )


def blocked_message(script_name: str) -> str:
    script_name = _script_name(script_name)
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
        + "  Compatibility scripts are frozen before config, LLM, network, or writes.\n"
        + "  Explicit compatibility execution requires BOTH settings:\n"
        + "    COMPANY_WIKI_WRITE_MODE=legacy\n"
        + "    COMPANY_WIKI_LEGACY_WRITERS=allow\n"
        + "  Gate environments forcibly override both settings to deny.\n"
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
