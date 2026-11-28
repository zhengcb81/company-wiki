"""Phase 14 R8 fix: entity-gate normalization must match the identity layer.

The bridge-off equivalence comparison found "Apple Inc." (SEC canonical
name, trailing period) failing the v2 entity gate while "Apple Inc"
passed — every period-terminated US issuer would resolve to missing under
bridge-off.  The gate now uses the identity layer's canonical
normalization (NFKC + casefold + alnum-only).  This is NORMALIZATION, not
soft-matching: company-name-vs-ticker still conflicts (FC-702 intact).
"""

from __future__ import annotations


from contextlib import closing

from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
from company_wiki.source_catalog.resolver import SourceResolver

def test_entity_gate_normalizes_trailing_period(tmp_path):
    """Match a bare issuer name to its punctuated SEC canonical form."""
    sources = tmp_path / "raw"
    sources.mkdir()
    config = CatalogConfig(
        project_root=tmp_path, catalog_dir=tmp_path / "catalog",
        roots=(RootSpec("fixture", sources, "directory"),),
    )
    doc = {
        "entities": [{"entity_id": "AAPL", "name": "Apple Inc."}],
        "metadata_json": {"ticker": "AAPL", "security_id": "AAPL",
                          "company_name": "Apple Inc."},
    }
    # Resolution projects and binds metadata once before applying this predicate.
    metadata = doc["metadata_json"]
    with closing(SourceCatalog(config)) as catalog:
        resolver = SourceResolver(catalog)
        assert resolver._entity_matches("Apple Inc", doc, metadata=metadata)
        assert resolver._entity_matches("Apple Inc.", doc, metadata=metadata)
        assert resolver._entity_matches("apple inc.", doc, metadata=metadata)
        assert not resolver._entity_matches("Apple Computers", doc, metadata=metadata)


def test_normalization_does_not_reintroduce_soft_match():
    """FC-702 stays intact: normalization strips punctuation, it does not
    match words to numbers."""
    from company_wiki.source_catalog.security_identity import _normalize_text

    assert _normalize_text("Apple Inc.") == _normalize_text("Apple Inc")
    assert _normalize_text("中国平安") != _normalize_text("601318")
    assert _normalize_text("apple inc.") == "appleinc"
