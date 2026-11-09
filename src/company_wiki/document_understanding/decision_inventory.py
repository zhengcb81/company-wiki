"""Historical import compatibility for the source-owned decision inventory.

New consumers import :mod:`company_wiki.source_catalog.narrative_decision_inventory`.
This module is deliberately only a public re-export for older installed readers.
"""

from company_wiki.source_catalog.narrative_decision_inventory import (
    build_decision_trace as build_decision_trace,
    current_decision_trace as current_decision_trace,
    decision_versions as decision_versions,
)

__all__ = ["build_decision_trace", "current_decision_trace", "decision_versions"]
