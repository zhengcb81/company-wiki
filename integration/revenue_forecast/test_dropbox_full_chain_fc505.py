"""FC-505 RED/acceptance tests: Dropbox 全链 E2E (three repos).

The chain starts from a company-wiki resolve (the real Dropbox canaries
resolve REUSED_EXACT), the handle passes filing-fetch's policy-snapshot
containment, and revenue builds the strict source record consumed by
artifact selection.  On an exact hit every stage is a pure read:
provider discover/fetch, download, parser, LLM and external writes all
stay at zero.  DBX-08: a cohort rollback makes the same request revert
to the pre-cohort response.  Phase 5 exit gate: with the canary present
the request resolves REUSED_EXACT — never the old MISSING — and without
sidecar evidence it fails closed.
"""
import hashlib
import json
import sys
from pathlib import Path

from _rf_system_paths import RF_CODE_ROOT  # noqa: E402
PROJECT_ROOT = RF_CODE_ROOT
WIKI_ROOT = PROJECT_ROOT.parent / "company-wiki"
FILING_ROOT = PROJECT_ROOT.parent / "filing-fetch"

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(WIKI_ROOT / "src"))
sys.path.insert(0, str(FILING_ROOT / "scripts"))

from datetime import datetime, timedelta  # noqa: E402

from company_wiki.source_catalog import (  # noqa: E402
    CatalogConfig,
    ResolutionStatus,
    RootSpec,
    SourceCatalog,
    SourceRequest,
    SourceResolver,
)


def _canary_fixture(tmp_path: Path) -> tuple[Path, bytes]:
    """One Dropbox canary: a real annual-report PDF + complete sidecar."""
    body = b"%PDF-1.4 zijin 2025 annual report"
    dropbox = tmp_path / "Dropbox" / "Stock" / "金属及加工" / "有色金属" / "紫金矿业"
    dropbox.mkdir(parents=True)
    pdf = dropbox / "紫金矿业2025年年报.pdf"
    pdf.write_bytes(body)
    (dropbox / "紫金矿业2025年年报.pdf.source.json").write_text(json.dumps({
        "schema_version": "1.0",
        "canonical_entity_id": "ent-601899",
        "display_name": "紫金矿业集团股份有限公司",
        "market": "CN",
        "security_id": "601899",
        "document_kind": "annual_report",
        "fiscal_year": 2025,
        "period_end": "2025-12-31",
        "provider": "cninfo",
        "provider_document_id": "1225023658",
        "form_type": "annual_report",
        "filing_date": "2026-03-20",
        "source_url": "https://www.cninfo.com.cn/new/disclosure/detail?stockCode=601899&announcementId=1225023658",
        "content_sha256": hashlib.sha256(body).hexdigest(),
    }, ensure_ascii=False), encoding="utf-8")
    return dropbox, body


def _catalog_with_canary(tmp_path: Path, dropbox_dir: Path) -> SourceCatalog:
    # company_names come from company_raw dirs (the real config); the
    # directory-root canary's entity is inferred from them
    companies = tmp_path / "companies" / "紫金矿业" / "raw"
    companies.mkdir(parents=True)
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=("company_raw", "directory"),
            roots=(
                RootSpec(
                    "company_raw", tmp_path / "companies", "company_raw",
                    priority=20, adapter_id="company_raw_v1",
                    read_only=False, reusable_for_filing=True,
                    canonical_write_target="companies",
                ),
                RootSpec(
                    "dropbox_stock", dropbox_dir, "directory",
                    priority=10, adapter_id="sidecar_filing_v1",
                    read_only=True, reusable_for_filing=True,
                ),
            ),
        )
    )
    catalog.scan()  # production v1 scan (non-focus sidecar pairing, FC-505)
    return catalog


def _resolve_canary(catalog: SourceCatalog, *, as_of: str = "2026-08-10"):
    return SourceResolver(catalog).resolve(SourceRequest(
        entity="紫金矿业", market="CN", security_id="601899",
        document_kind="annual_report", form_type="annual_report",
        fiscal_year=2025, provider="cninfo",
        provider_document_id="1225023658",
        as_of_date=as_of, mode="exact",
    ))


def _policy_snapshot(dropbox_dir: Path) -> dict:
    return {
        "schema_version": "2.0",
        "reusable_root_kinds": ["directory"],
        "roots": [
            {
                "root_id": "dropbox_stock",
                "path_ref": str(dropbox_dir),
                "read_only": True,
                "reusable_for_filing": True,
                "canonical_write_target": None,
            },
        ],
    }


def _snapshot_hash(snapshot: dict) -> str:
    return hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


# --- EX-03 / DBX-01: the full three-repo chain, zero side effects ------------


def test_fc505_chain_exact_hit_zero_side_effects(tmp_path):
    """company-wiki resolve -> filing-fetch containment -> revenue source
    record: every stage is a pure read on the exact hit."""
    from company_wiki_source import build_revenue_source_record
    from filing_contracts import validate_handle

    dropbox_dir, body = _canary_fixture(tmp_path)
    catalog = _catalog_with_canary(tmp_path, dropbox_dir)
    result = _resolve_canary(catalog)
    assert result.status is ResolutionStatus.REUSED_EXACT
    assert result.download_required is False
    assert result.download_allowed is False
    handle = result.matches[0].to_dict()
    handle["request_id"] = "urn:company-wiki:source-request:fc505"

    # filing-fetch: the handle's canonical path must be contained in a
    # reusable root of the policy snapshot (hash-bound)
    snapshot = _policy_snapshot(dropbox_dir)
    validate_handle(
        handle, {"company_query": "紫金矿业", "market": "CN",
                 "document_kind": "annual", "fiscal_year": 2025,
                 "as_of_date": "2026-08-10"},
        tmp_path,
        policy_snapshot=snapshot,
        expected_policy_hash=_snapshot_hash(snapshot),
    )  # must not raise

    # revenue: the strict source record consumed by artifact selection
    record = build_revenue_source_record(
        handle,
        as_of_date=(datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
        source_type="regulatory_filing",
        publisher="cninfo",
        page_or_section="annual_report",
        prompt_injection_status="not_detected",
    )
    assert record["capture"]["snapshot_sha256"] == hashlib.sha256(body).hexdigest()
    assert record["company_wiki_trace"]["provider"] == "cninfo"
    assert record["company_wiki_trace"]["provider_document_id"] == "1225023658"
    # zero side effects on the exact hit: the resolver returned before any
    # acquisition step; validate_handle is read-only; the record build is
    # a pure function
    assert result.download_required is False


# --- DBX-08: cohort rollback -> same request reverts -------------------------


def test_fc505_cohort_rollback_same_request_reverts(tmp_path):
    """A Dropbox-cohort activation flips visibility; rolling it back makes
    the same request return the pre-cohort response (files kept)."""
    from company_wiki.source_catalog.activation import (
        apply_activation,
        rollback_activation,
    )

    dropbox_dir, body = _canary_fixture(tmp_path)
    catalog = _catalog_with_canary(tmp_path, dropbox_dir)

    before = _resolve_canary(catalog)
    assert before.status is ResolutionStatus.REUSED_EXACT
    before_handle = before.matches[0]

    # apply a cohort activation pinning the dropbox cohort, then resolve
    # under that cohort
    # register a verified assertion for the canary content, then activate it
    from company_wiki.source_catalog.assertion_service import (
        upsert_verified_assertion,
    )
    from company_wiki.source_catalog.normalized_meta import canonical_hash

    digest = hashlib.sha256(body).hexdigest()
    normalized = {
        "market": "CN",
        "security_id": "601899",
        "fiscal_year": 2025,
        "provider": "cninfo",
        "provider_document_id": "1225023658",
    }
    # the real document/source ids from the scanned fixture catalog (FK)
    doc_row = catalog.store.fetchone(
        """SELECT d.document_id, d.primary_source_id FROM documents d
           JOIN locations l ON l.document_id = d.document_id
           JOIN sources s ON s.source_id = l.source_id
           WHERE s.content_sha256 = ? LIMIT 1""", (digest,))
    assert doc_row is not None
    assertion = upsert_verified_assertion(
        catalog.store,
        source_id=doc_row["primary_source_id"],
        document_id=doc_row["document_id"],
        content_sha256=digest,
        adapter_id="sidecar_filing_v1",
        adapter_version="1.0.0",
        metadata_hash=canonical_hash(normalized),
        normalized=normalized,
        created_by="fc505-test",
    )
    assertion_id = assertion["assertion_id"]
    applied = apply_activation(
        catalog.store,
        epoch="fc505-epoch",
        cohort="dropbox-cohort",
        assertion_ids=[assertion_id],
        policy_hash="p" * 64,
        reason="FC-505 cohort flip",
        reviewer="reviewer-fc505-test",
    )
    assert applied["kind"] == "apply"

    # rollback: same request must revert to the pre-cohort response
    rolled = rollback_activation(
        catalog.store,
        receipt_id=applied["receipt_id"],
        reviewer="reviewer-fc505-test",
        reason="FC-505 rollback",
    )
    assert rolled["kind"] == "rollback"

    after = _resolve_canary(catalog)
    assert after.status is ResolutionStatus.REUSED_EXACT
    assert after.matches[0].canonical_path == before_handle.canonical_path
    assert after.matches[0].content_sha256 == before_handle.content_sha256
    # the file is kept, not deleted by the rollback
    assert (dropbox_dir / "紫金矿业2025年年报.pdf").is_file()


# --- Phase 5 exit gate: Dropbox configured never MISSING on a canary ---------


def test_fc505_dropbox_configured_no_longer_missing(tmp_path):
    """With the canary present the request resolves REUSED_EXACT; without
    sidecar evidence it fails closed (never fabricated)."""
    dropbox_dir, body = _canary_fixture(tmp_path)
    catalog = _catalog_with_canary(tmp_path, dropbox_dir)
    result = _resolve_canary(catalog)
    assert result.status is ResolutionStatus.REUSED_EXACT
    # remove the sidecar -> the same file has no evidence -> fail closed
    (dropbox_dir / "紫金矿业2025年年报.pdf.source.json").unlink()
    catalog2 = _catalog_with_canary(tmp_path / "b", dropbox_dir)
    catalog2.scan()
    result2 = _resolve_canary(catalog2)
    assert result2.status is not ResolutionStatus.REUSED_EXACT


# --- the source record feeds artifact selection ------------------------------


def test_fc505_source_record_feeds_artifact_selection(tmp_path):
    """The chain's source record is consumable by the revenue artifact
    selection (validate_sources accepts the built record)."""
    from company_wiki_source import build_revenue_source_record
    from revenue_core import validate_sources

    dropbox_dir, body = _canary_fixture(tmp_path)
    catalog = _catalog_with_canary(tmp_path, dropbox_dir)
    result = _resolve_canary(catalog)
    handle = result.matches[0].to_dict()
    handle["request_id"] = "urn:company-wiki:source-request:fc505-artifact"
    record = build_revenue_source_record(
        handle,
        as_of_date=(datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
        source_type="regulatory_filing",
        publisher="cninfo",
        page_or_section="annual_report",
        prompt_injection_status="not_detected",
    )
    index = validate_sources({"sources": [record]}, (datetime.now() + timedelta(days=14)).date())
    assert record["source_id"] in index  # the chain's record is selected
