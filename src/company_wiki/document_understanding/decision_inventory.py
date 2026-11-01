"""Historical import compatibility for the source-owner inventory adapter.

Current selection/cache entry points import source_catalog's composition owner.
The pure decision_dependencies package remains independent of source/automation.
"""
from company_wiki.source_catalog.narrative_decision_inventory import (
    build_decision_trace as build_decision_trace,
    current_decision_trace as current_decision_trace,
    _inventory as _inventory,
    _versions as _versions,
)

__all__ = ["build_decision_trace", "current_decision_trace"]
