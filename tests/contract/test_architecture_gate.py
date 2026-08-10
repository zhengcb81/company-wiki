"""CW-3 contract tests for the architecture gate."""


def test_source_catalog_does_not_import_prohibited_modules():
    from company_wiki.source_catalog.architecture_gate import (
        source_catalog_does_not_import_prohibited_modules,
    )

    ok, violations = source_catalog_does_not_import_prohibited_modules()
    assert ok, f"prohibited imports found: {violations}"


def test_rejected_stages_covers_all_investment_stages():
    from company_wiki.source_catalog.architecture_gate import (
        rejected_stages_covers_all_investment_stages,
    )

    ok, missing = rejected_stages_covers_all_investment_stages()
    assert ok, f"missing rejected stages: {missing}"


def test_scheduler_policy_blocks_valuation_and_research():
    from company_wiki.source_catalog.scheduler_policy import _FORBIDDEN_DISPATCH_TOKENS

    required = {
        "valuation",
        "research",
        "rating",
        "sell",
        "sotp",
        "stockwiki",
        "target_price",
        "wiki_writer",
    }
    assert required <= set(_FORBIDDEN_DISPATCH_TOKENS), (
        f"missing: {required - set(_FORBIDDEN_DISPATCH_TOKENS)}"
    )


# --- FC-205: control-plane adversarial gate --------------------------------


def test_fc205_production_resolver_reads_runtime_policy_snapshot():
    """The production resolver must consume the RuntimePolicySnapshot —
    no hardcoded flag dicts in the resolver path."""
    from company_wiki.source_catalog.architecture_gate import (
        control_plane_reads_runtime_policy,
    )

    ok, violations = control_plane_reads_runtime_policy()
    assert ok, f"production path missing snapshot reads: {violations}"


def test_fc205_no_hardcoded_flag_dicts_in_production():
    """Flag state must live only in flags.py / runtime_policy.py — no
    production module may hand-roll the six-flag dict."""
    from company_wiki.source_catalog.architecture_gate import (
        no_hardcoded_flag_dicts,
    )

    ok, violations = no_hardcoded_flag_dicts()
    assert ok, f"hardcoded flag dicts: {violations}"


def test_fc205_no_legacy_container_read_outside_resolver():
    """acquisition/dayu_meta containers may only be read inside the
    resolver's gated _source_metadata bridge — no bypass elsewhere."""
    from company_wiki.source_catalog.architecture_gate import (
        no_legacy_container_reads_outside_resolver,
    )

    ok, violations = no_legacy_container_reads_outside_resolver()
    assert ok, f"ungated legacy reads: {violations}"


def test_fc205_t4_minimal_cohort_rollback_changes_response(tmp_path):
    """T4: a minimal cohort rollback must change the real resolver
    response for the same request (CTRL-04), not just a dict."""
    import sys as _sys
    from pathlib import Path as _Path

    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2] / "src"))
    from company_wiki.source_catalog.activation import (
        apply_activation,
        rollback_activation,
    )
    from company_wiki.source_catalog.assertion_service import (
        upsert_verified_assertion,
    )
    from company_wiki.source_catalog.normalized_meta import canonical_hash
    from company_wiki.source_catalog.store import CatalogStore

    store = CatalogStore(tmp_path / "t4.sqlite3")
    with store.transaction() as conn:
        conn.execute(
            "INSERT INTO sources (source_id, content_sha256, byte_size, "
            "mime_type, first_seen_at) VALUES ('s1','h',1,'x','2026-01-01')")
        conn.execute(
            "INSERT INTO documents (document_id, title, source_status, "
            "source_type, document_kind, metadata_priority, metadata_json, "
            "first_seen_at, last_seen_at) VALUES ('d1','t','active','file','k',"
            "10,'{}','2026-01-01','2026-01-01')")
    norm = {
        "schema_version": "2.0", "canonical_entity_id": "e",
        "display_name": "A", "market": "US", "security_id": "US1",
        "document_kind": "k", "fiscal_year": 2025,
        "period_end": "2025-12-31", "provider": "p",
        "provider_document_id": "a1", "content_sha256": "c" * 64,
        "adapter_id": "x", "adapter_version": "1.0.0",
        "normalization_status": "capture_ready",
    }
    norm["metadata_sha256"] = canonical_hash(norm)
    r = upsert_verified_assertion(
        store, source_id="s1", document_id="d1", content_sha256="c" * 64,
        adapter_id="x", adapter_version="1.0.0",
        metadata_hash=canonical_hash(norm), normalized=norm)
    # shadow row (default) -> apply flips to active
    receipt = apply_activation(
        store, epoch="epoch-t4", cohort="cohort-t4",
        assertion_ids=[r["assertion_id"]], policy_hash="a" * 64,
        reviewer="t4", reason="t4 drill")
    # same request BEFORE and AFTER rollback must give different resolver
    # responses (v2 reader sees the row only while activated)
    from company_wiki.source_catalog.resolver import (
        _v2_assertion_metadata,
    )

    active_row = _v2_assertion_metadata(
        store, "s1", reader="v2", current_epoch="epoch-t4",
        active_cohorts=("cohort-t4",))
    assert active_row is not None, "activated row must be visible to v2"
    rollback_activation(
        store, receipt_id=receipt["receipt_id"], reviewer="t4",
        reason="t4 rollback")
    rolled_back = _v2_assertion_metadata(
        store, "s1", reader="v2", current_epoch="epoch-t4",
        active_cohorts=("cohort-t4",))
    assert rolled_back is None, "rolled-back row must be invisible (response changed)"
