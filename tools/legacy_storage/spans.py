"""Retired one-off full-volume span pruning.

S5 production retirement finished 2026-10-06. The old parser-name DELETE is
intentionally gone: it cannot classify current referenced source evidence.
Historical receipts remain readable; inventory is still supported by its owner.
"""
from __future__ import annotations


def run_prune_spans(config, selection, *, keep_refs=None, now=None, dry_run=True) -> dict:
    """Compatibility result, with no config, filesystem or database access."""
    del config, selection, keep_refs, now
    return {"schema_version": "cwp-storage-retirement/1", "operation": "prune-spans",
            "status": "retired", "error_code": "legacy_span_prune_retired",
            "dry_run": dry_run, "deleted": 0, "already_absent": 0,
            "resume_notes": ["S5 span retirement completed; use read-only inventory for current evidence."]}
