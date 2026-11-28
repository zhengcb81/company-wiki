"""Compose catalog requests with the automation owner's scheduled summary port."""

from collections.abc import Sequence

from company_wiki import runtime_feedback
from company_wiki.source_catalog.incremental_command import run_incremental

__all__ = ["main"]


@runtime_feedback.entry("scheduled-reading")
def main(argv: Sequence[str] | None = None) -> int:
    from company_wiki.automation.scheduled_summary import ConfiguredReadingSummaries

    return run_incremental(argv, summary_owner=ConfiguredReadingSummaries())
