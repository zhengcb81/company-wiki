"""FC-704 RED/acceptance tests: ResolutionEnvelope + AcquisitionTrace.

The envelope returns handle(s), policy/epoch, the journal-reconciled
outcome, and exclusion trace; download evidence comes from the journal,
never inferred from whether a handle was returned (scenario_matrix §2:
counts must come from events/journal).  resolve stays zero-write: the
journal is read, never appended, by the envelope path.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.models import RootSpec  # noqa: E402


def _seed_company(tmp_path: Path, company: str, pdoc: str, kind: str,
                  *, fy: int = 2024) -> Path:
    raw = tmp_path / "companies" / company / "raw" / "financial_reports" / "annual"
    raw.mkdir(parents=True, exist_ok=True)
    (raw / f"{pdoc}.pdf").write_bytes(
        b"%PDF-1.4 " + company.encode("utf-8") + pdoc.encode("utf-8"))
    (raw / f"{pdoc}.pdf.source.json").write_text(json.dumps({
        "market": "CN", "security_id": "601899",
        "source_title": f"{company} {fy}", "fiscal_year": fy,
        "filing_date": f"{fy + 1}-03-20", "form_type": kind,
        "document_kind": kind, "provider": "cninfo",
        "provider_document_id": pdoc,
        "source_url": f"https://provider.example/{pdoc}",
    }, ensure_ascii=False), encoding="utf-8")
    return tmp_path / "companies"


def _catalog(tmp_path: Path, tree: Path):
    from company_wiki.source_catalog import CatalogConfig, SourceCatalog

    return SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=("company_raw",),
            roots=(RootSpec("company_raw", tree, "company_raw",
                            priority=10, adapter_id="company_raw_v1",
                            read_only=False, reusable_for_filing=True,
                            canonical_write_target="companies"),),
        )
    )


def _resolve(catalog, *, entity="Acme", security="601899", fy=2024,
             kind="annual_report", pdoc=None):
    from company_wiki.source_catalog import SourceRequest, SourceResolver

    return SourceResolver(catalog).resolve(SourceRequest(
        entity=entity, market="CN", security_id=security,
        document_kind=kind, form_type=kind, fiscal_year=fy,
        provider="cninfo", provider_document_id=pdoc,
        as_of_date="2026-08-11", mode="exact",
    ))


def _journal(tmp_path: Path):
    from company_wiki.source_catalog.acquisition_journal import (
        AcquisitionJournal,
    )

    return AcquisitionJournal(tmp_path / ".source_catalog")


def _build(resolution, *, policy_snapshot=None, journal=None):
    from company_wiki.source_catalog.resolver import build_resolution_envelope

    return build_resolution_envelope(
        resolution, policy_snapshot=policy_snapshot, journal=journal)


# --- ENV-01: structural outcome for a read-only resolve ----------------------


def test_env01_reused_existing_structural(tmp_path):
    """REUSED_EXACT with an empty journal -> outcome reused_existing and
    zero download events (nothing was fetched; the journal has no entry)."""
    from company_wiki.source_catalog import ResolutionStatus

    tree = _seed_company(tmp_path, "Acme", "doc-a", "annual_report")
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    result = _resolve(catalog)
    assert result.status in (ResolutionStatus.REUSED_EXACT,
                               ResolutionStatus.REUSED_EQUIVALENT)
    envelope = _build(result, journal=_journal(tmp_path))
    assert envelope.outcome == "reused_existing"
    assert envelope.download_events == 0


def test_env02_structural_status_mapping():
    """MISSING/AMBIGUOUS/IDENTITY_CONFLICT map to missing/ambiguous/
    rejected structurally (no journal entry needed)."""
    from company_wiki.source_catalog.resolver import (
        ResolutionResult,
        ResolutionStatus,
        build_resolution_envelope,
        SOURCE_RESOLVER_SCHEMA_VERSION,
    )

    def result_for(status):
        return ResolutionResult(
            schema_version=SOURCE_RESOLVER_SCHEMA_VERSION,
            request_id="urn:test:" + status.value,
            status=status, reason="r", download_required=False,
            download_allowed=False, matches=(), debug_trace=("x",))

    assert build_resolution_envelope(result_for(
        ResolutionStatus.MISSING)).outcome == "missing"
    assert build_resolution_envelope(result_for(
        ResolutionStatus.AMBIGUOUS)).outcome == "ambiguous"
    assert build_resolution_envelope(result_for(
        ResolutionStatus.IDENTITY_CONFLICT)).outcome == "rejected"


# --- ENV-03/04: journal reconciliation ----------------------------------------


def test_env03_journal_downloaded_new_reconciled(tmp_path):
    """A journal entry for the request_id wins over the structural outcome:
    downloaded_new -> download_events=1 (a fetch happened — the receipt may
    never claim zero for a downloaded document)."""
    from company_wiki.source_catalog import ResolutionStatus

    tree = _seed_company(tmp_path, "Acme", "doc-a", "annual_report")
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    result = _resolve(catalog)
    assert result.status in (ResolutionStatus.REUSED_EXACT,
                               ResolutionStatus.REUSED_EQUIVALENT)
    journal = _journal(tmp_path)
    journal.record(request_id=result.request_id, outcome="downloaded_new",
                    reason="staged_and_imported")
    envelope = _build(result, journal=journal)
    assert envelope.outcome == "downloaded_new"
    assert envelope.download_events == 1


def test_env04_journal_reused_after_discovery(tmp_path):
    """reused_after_discovery from the journal -> outcome forwarded,
    download_events=0 (discovery is not a download)."""
    from company_wiki.source_catalog import ResolutionStatus

    tree = _seed_company(tmp_path, "Acme", "doc-a", "annual_report")
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    result = _resolve(catalog)
    assert result.status in (ResolutionStatus.REUSED_EXACT,
                               ResolutionStatus.REUSED_EQUIVALENT)
    journal = _journal(tmp_path)
    journal.record(request_id=result.request_id,
                   outcome="reused_after_discovery",
                   adapter_name="test-adapter")
    envelope = _build(result, journal=journal)
    assert envelope.outcome == "reused_after_discovery"
    assert envelope.download_events == 0


def test_env04b_gap_and_dedup_mapped(tmp_path):
    """gap_plan maps to gap; deduplicated_after_download still counts a
    download (bytes were fetched) with outcome downloaded_new."""
    tree = _seed_company(tmp_path, "Acme", "doc-a", "annual_report")
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    result = _resolve(catalog)
    journal = _journal(tmp_path)
    journal.record(request_id=result.request_id, outcome="gap_plan",
                   reason="plan_only")
    assert _build(result, journal=journal).outcome == "gap"
    journal.record(request_id=result.request_id,
                   outcome="deduplicated_after_download", reason="dup")
    envelope = _build(result, journal=journal)
    assert envelope.outcome == "downloaded_new"
    assert envelope.download_events == 1


# --- ENV-05: policy/epoch forwarding ------------------------------------------


def test_env05_policy_and_epoch_forwarded(tmp_path):
    """policy_hash + activation_epoch come from the RuntimePolicySnapshot;
    without a snapshot they are null — never fabricated."""
    tree = _seed_company(tmp_path, "Acme", "doc-a", "annual_report")
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    result = _resolve(catalog)
    envelope = _build(result, policy_snapshot={
        "policy_hash": "a" * 64, "current_epoch": "epoch-7",
        "flags": {}, "roots": [], "active_cohorts": [],
    })
    assert envelope.policy_hash == "a" * 64
    assert envelope.activation_epoch == "epoch-7"
    bare = _build(result)
    assert bare.policy_hash is None
    assert bare.activation_epoch is None


# --- ENV-06: bundle status explicit -------------------------------------------


def test_env06_bundle_status_explicit_unavailable(tmp_path):
    """bundle_status is explicitly 'unavailable' until FC-901 ships real
    bundles — never a faked empty-green 'available'."""
    tree = _seed_company(tmp_path, "Acme", "doc-a", "annual_report")
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    envelope = _build(_resolve(catalog))
    assert envelope.bundle_status == "unavailable"


# --- ENV-07: serialization determinism ----------------------------------------


def test_env07_to_dict_deterministic(tmp_path):
    """to_dict carries the envelope schema version and round-trips
    deterministically."""
    tree = _seed_company(tmp_path, "Acme", "doc-a", "annual_report")
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    result = _resolve(catalog)
    envelope = _build(result, policy_snapshot={
        "policy_hash": "b" * 64, "current_epoch": "epoch-9"})
    payload = envelope.to_dict()
    assert payload["envelope_schema_version"] == "1.0"
    assert json.dumps(payload, sort_keys=True) == json.dumps(
        envelope.to_dict(), sort_keys=True)


# --- ENV-08: resolve stays zero-write -----------------------------------------


def test_env08_envelope_reads_journal_never_writes(tmp_path):
    """Building the envelope must not append to the journal (resolve is a
    read-only command; scenario_matrix §2 evidence comes from events, and
    read-only resolve performs none)."""
    tree = _seed_company(tmp_path, "Acme", "doc-a", "annual_report")
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    result = _resolve(catalog)
    journal = _journal(tmp_path)
    assert not journal.path.exists()
    _build(result, journal=journal)
    assert not journal.path.exists(), "envelope build wrote to the journal"
