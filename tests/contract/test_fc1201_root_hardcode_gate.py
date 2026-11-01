"""Executable root-specific behavior belongs to storage/layout owners.

The old duplicate frozen file list and comment-token bans were not behavior
contracts. Unit tests exercise imported spellings, executable conditionals and
positive documentation cases; this is the actual current-tree check.
"""
from company_wiki.source_catalog.architecture_gate import no_root_specific_hardcode


def test_current_root_conditionals_belong_to_layout_owners():
    ok, violations = no_root_specific_hardcode()
    assert ok, violations
