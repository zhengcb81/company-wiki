"""Phase 14 R8 fix: entity-gate normalization must match the identity layer.

The bridge-off equivalence comparison found "Apple Inc." (SEC canonical
name, trailing period) failing the v2 entity gate while "Apple Inc"
passed — every period-terminated US issuer would resolve to missing under
bridge-off.  The gate now uses the identity layer's canonical
normalization (NFKC + casefold + alnum-only).  This is NORMALIZATION, not
soft-matching: company-name-vs-ticker still conflicts (FC-702 intact).
"""

from __future__ import annotations


from company_wiki.source_catalog.resolver import SourceResolver

def test_entity_gate_normalizes_trailing_period():
    """Direct gate-level regression: _entity_matches must accept the SEC
    canonical form (trailing period) for the same issuer.  No catalog
    fixture needed — the gate is pure over a document dict."""
    resolver = SourceResolver.__new__(SourceResolver)
    resolver.legacy_bridge_allowed = False
    resolver._issuer_index = lambda: ({}, {})  # no issuer anchoring in this unit
    doc = {
        "entities": [{"entity_id": "AAPL", "name": "Apple Inc."}],
        "metadata_json": {"ticker": "AAPL", "security_id": "AAPL",
                          "company_name": "Apple Inc."},
    }
    assert resolver._entity_matches("Apple Inc", doc)
    assert resolver._entity_matches("Apple Inc.", doc)
    assert resolver._entity_matches("apple inc.", doc)
    assert not resolver._entity_matches("Apple Computers", doc)


def test_normalization_does_not_reintroduce_soft_match():
    """FC-702 stays intact: normalization strips punctuation, it does not
    match words to numbers."""
    from company_wiki.source_catalog.security_identity import _normalize_text

    assert _normalize_text("Apple Inc.") == _normalize_text("Apple Inc")
    assert _normalize_text("中国平安") != _normalize_text("601318")
    assert _normalize_text("apple inc.") == "appleinc"
