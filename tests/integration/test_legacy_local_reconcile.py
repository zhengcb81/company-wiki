"""Local bytes and audited metadata repair; no supplier success fixtures."""

from dataclasses import asdict
import hashlib
import json
import pytest
from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.official_source_flow import import_official_source
from company_wiki.source_catalog.resolver import SourceRequest
from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader
from company_wiki.source_catalog.store import retire_document
from company_wiki.source_catalog.security_identity import (
    SecurityMasterStore,
    SecurityRecord,
)

DATA = b"""<html><body><ix:nonNumeric name="dei:EntityCentralIndexKey">12345</ix:nonNumeric><ix:nonNumeric name="dei:DocumentFiscalYearFocus">2026</ix:nonNumeric><ix:nonNumeric name="dei:DocumentFiscalPeriodFocus">Q2</ix:nonNumeric><ix:nonNumeric name="dei:DocumentPeriodEndDate">2025-12-31</ix:nonNumeric><ix:nonNumeric name="dei:DocumentType">10-Q</ix:nonNumeric><p>Acme actual original.</p></body></html>"""


@pytest.fixture
def lake(tmp_path):
    (tmp_path / "companies").mkdir()
    cat = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / "catalog",
            roots=(RootSpec("company_raw", tmp_path / "companies", "company_raw"),),
        )
    )
    master = SecurityMasterStore(cat.config.catalog_dir / "security_master")
    master.write_market(
        "US",
        (
            SecurityRecord(
                "Acme",
                "US",
                "NASDAQ",
                "ACME",
                "ACME",
                ("Acme Corp",),
                True,
                "sec",
                "https://www.sec.gov/files/company_tickers.json",
                "12345",
                {"cik": "12345"},
            ),
        ),
        retrieved_at="2026-10-09T00:00:00Z",
        sources=("sec",),
    )
    try:
        yield cat
    finally:
        cat.close()


def imported(cat, *, published="2026-01-28", wrong=True, url=True):
    sha = hashlib.sha256(DATA).hexdigest()
    source = {
        "entity": "Acme",
        "market": "HK" if wrong else "US",
        "security_id": "ACME",
        "document_kind": "regulatory_filing",
        "title": "Acme original",
        "publisher": "Acme",
        "source_url": "https://www.sec.gov/Archives/edgar/data/12345/000001234526000007/original.htm",
        "published_date": published,
        "filing_date": published,
        "fiscal_year": 2025 if wrong else 2026,
        "fiscal_period": "Q2",
        "period_end": "2025-12-31",
        "language": "en",
    }
    req = {
        "schema_version": "official-source-import-request/1",
        "request_id": "fixture",
        "source": source,
        "content_sha256": sha,
        "mime_type": "text/html",
        "max_bytes": 4096,
        "capture_receipt": {
            "capture_method": "local_document",
            "tool_name": "fixture",
            "tool_call_id": "one",
            "captured_at": "2026-10-09T00:00:00Z",
            "content_sha256": sha,
            "response_bytes": len(DATA),
        },
    }
    result = import_official_source(cat, original=DATA, request=req)
    ref = SourceRef(**result["source_ref"])
    if not url:
        cat.record_source_facts(
            ref=ref,
            facts={"source_url": None},
            evidence={"source_url": {"locator": "fixture:/unknown-url", "value": None}},
        )
    loc = cat.reader.exact_source_locations(ref.document_id, ref.source_id)[0]
    path = cat.config.roots[0].path / loc["relative_path"]
    meta = {
        "company_id": "12345",
        "accession_number": "0000012345-26-000007",
        "primary_document": path.name,
        "form_type": "10-Q",
        "report_date": "2025-12-31",
        "filing_date": published,
        "ingest_complete": True,
        "is_deleted": False,
        "files": [
            {
                "name": path.name,
                "sha256": sha,
                "size": len(DATA),
                "source_url": (
                    "https://www.sec.gov/Archives/edgar/data/12345/000001234526000007/"
                    + path.name
                )
                if url
                else None,
            }
        ],
    }
    path.with_name("meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return ref, path, req


def retire(
    cat,
    ref,
    reason="legacy sidecar lacks source_url; batch governance Phase 15.6 (F13)",
    actor="phase-15.6-governance",
):
    retire_document(
        cat.store, document_id=ref.document_id, reason=reason, created_by=actor
    )
    if actor == "phase-15.6-governance":
        retire_document(
            cat.store,
            document_id=ref.document_id,
            reason="phase-15.6 audit reconciliation (reconcile-retire)",
            created_by="reconcile-retire-20260806",
        )


def business(**kw):
    return SourceRequest(
        entity="Acme",
        market="US",
        security_id="ACME",
        document_kind="regulatory_filing",
        fiscal_year=2026,
        fiscal_period="Q2",
        as_of_date=kw.pop("as_of_date", "2026-10-09"),
        **kw,
    )


def prepare(cat, **kw):
    from company_wiki.source_catalog.local_reconcile import prepare_local_source

    return prepare_local_source(cat, business(**kw))


def counts(cat):
    return [
        cat.store.fetchone("SELECT COUNT(*) FROM " + t)[0]
        for t in (
            "source_metadata_assertions",
            "document_retire_audit",
            "document_restore_audit",
        )
    ]


def test_retired_actual_dei_repairs_identity_same_ref_and_is_idempotent(lake):
    ref, path, _ = imported(lake, url=False)
    retire(lake, ref)
    assert SourceVersionReader(lake).query_local(business()).status == "not_found"
    before = counts(lake)
    result = prepare(lake)
    assert result["status"] == "ready" and result["source_ref"] == asdict(ref)
    assert result["download_events"] == 0 and not result["blocks_download"]
    current = SourceVersionReader(lake).describe_version(ref)
    assert (
        current["market"],
        current["fiscal_year"],
        current["fiscal_period"],
        current["source_url"],
    ) == ("US", 2026, "Q2", None)
    assert (
        SourceVersionReader(lake).open_version(ref, purpose="source_export").data
        == DATA
        == path.read_bytes()
    )
    after = counts(lake)
    assert after == [before[0] + 1, before[1], 1]
    assert prepare(lake)["source_ref"] == asdict(ref) and counts(lake) == after


@pytest.mark.parametrize(
    "reason,actor",
    [
        ("issuer withdrew original", "source-publisher"),
        ("damaged raw", "quality-check"),
        ("metadata gap", "unknown"),
    ],
)
def test_untrusted_or_true_retirement_never_restores(lake, reason, actor):
    ref, path, _ = imported(lake)
    retire(lake, ref, reason, actor)
    before = counts(lake)
    result = prepare(lake)
    assert result["status"] == "blocked" and result["blocks_download"]
    assert (
        lake.reader.exact_source_version(ref.document_id)["source_status"] == "retired"
    )
    assert counts(lake) == before and path.read_bytes() == DATA


@pytest.mark.parametrize(
    "published,asof,reason",
    [
        (None, "2026-10-09", "publication_date_unknown"),
        ("2026-01-28", "2026-01-27", "publication_after_as_of"),
    ],
)
def test_publication_gap_never_becomes_reusable_or_download(
    lake, published, asof, reason
):
    ref, _, _ = imported(lake, published=published)
    retire(lake, ref)
    result = prepare(lake, as_of_date=asof)
    assert result["status"] != "ready" and result["blocks_download"]
    assert reason in json.dumps(result)
    assert (
        SourceVersionReader(lake).query_local(business(as_of_date=asof)).status
        != "found"
    )


def test_official_same_sha_dedup_corrects_facts_without_rewriting_raw(lake):
    ref, path, req = imported(lake)
    original_files = {
        x: x.read_bytes() for x in lake.config.roots[0].path.rglob("*") if x.is_file()
    }
    req["source"].update(market="US", fiscal_year=2026)
    result = import_official_source(lake, original=DATA, request=req)
    assert result["status"] == "deduplicated" and result["source_ref"] == asdict(ref)
    assert (
        result["metadata"]["market"] == "US"
        and result["metadata"]["fiscal_year"] == 2026
    )
    assert SourceVersionReader(lake).query_local(business()).status == "found"
    assert original_files == {
        x: x.read_bytes() for x in lake.config.roots[0].path.rglob("*") if x.is_file()
    }
    after = counts(lake)
    import_official_source(lake, original=DATA, request=req)
    assert counts(lake) == after


def test_local_official_import_does_not_resurrect_withdrawn(lake):
    from company_wiki.source_catalog.official_source_flow import OfficialSourceError

    ref, path, req = imported(lake)
    retire(lake, ref, "issuer withdrew original", "source-publisher")
    before = counts(lake)
    with pytest.raises(OfficialSourceError, match="retirement_not_metadata_only"):
        import_official_source(lake, original=DATA, request=req)
    assert (
        lake.reader.exact_source_version(ref.document_id)["source_status"] == "retired"
    )
    assert counts(lake) == before and path.read_bytes() == DATA


def correct_facts():
    facts = {
        "entity": "Acme",
        "market": "US",
        "security_id": "ACME",
        "document_kind": "regulatory_filing",
        "published_date": "2026-01-28",
        "fiscal_year": 2026,
        "fiscal_period": "Q2",
        "period_end": "2025-12-31",
        "source_url": None,
    }
    return facts, {
        key: {"locator": "test-primary:/" + key, "value": value}
        for key, value in facts.items()
    }


@pytest.mark.parametrize(
    "table,operation,condition",
    [
        ("source_metadata_assertions", "INSERT", ""),
        ("documents", "UPDATE", " OF published_date"),
        ("locations", "UPDATE", ""),
        ("document_restore_audit", "INSERT", ""),
    ],
)
def test_atomic_fault_cannot_leave_half_restored(lake, table, operation, condition):
    from company_wiki.source_catalog.assertion_service import restore_document_facts
    from company_wiki.source_catalog.local_inventory import observe_document
    import sqlite3

    ref, path, _ = imported(lake)
    retire(lake, ref)
    observation = observe_document(lake, ref.document_id)
    before = counts(lake)
    facts, evidence = correct_facts()
    with lake.store.transaction() as conn:
        conn.execute(
            f"CREATE TRIGGER fault BEFORE {operation}{condition} ON {table} BEGIN SELECT RAISE(ABORT,'injected atomic fault'); END"
        )
    with pytest.raises(sqlite3.IntegrityError, match="injected atomic fault"):
        restore_document_facts(
            lake,
            ref=ref,
            facts=facts,
            evidence=evidence,
            retirement_observation=observation,
        )
    assert (
        observe_document(lake, ref.document_id) == observation
        and counts(lake) == before
    )
    assert path.read_bytes() == DATA


def test_stale_audit_observation_refuses_by_name(lake):
    from company_wiki.source_catalog.assertion_service import restore_document_facts
    from company_wiki.source_catalog.local_inventory import observe_document
    from company_wiki.source_catalog.source_reader import SourceReadError

    ref, _, _ = imported(lake)
    retire(lake, ref)
    observation = observe_document(lake, ref.document_id)
    retire_document(
        lake.store,
        document_id=ref.document_id,
        reason="new withdrawal",
        created_by="publisher",
    )
    before = counts(lake)
    facts, evidence = correct_facts()
    with pytest.raises(SourceReadError, match="local_observation_changed"):
        restore_document_facts(
            lake,
            ref=ref,
            facts=facts,
            evidence=evidence,
            retirement_observation=observation,
        )
    assert (
        counts(lake) == before
        and lake.reader.exact_source_version(ref.document_id)["source_status"]
        == "retired"
    )


def test_concurrent_prepare_never_exposes_inflight_and_retry_reuses(lake, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from company_wiki.source_catalog import assertion_service

    ref, _, _ = imported(lake)
    retire(lake, ref)
    entered = Event()
    release = Event()
    original = assertion_service._write_source_fact_projection

    def paused(*args):
        original(*args)
        entered.set()
        assert release.wait(5)

    monkeypatch.setattr(assertion_service, "_write_source_fact_projection", paused)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(prepare, lake)
        assert entered.wait(5)
        try:
            second = prepare(lake)
            assert second["status"] == "unavailable" and second["blocks_download"]
            assert "local_reconcile_busy" in json.dumps(second)
            assert (
                SourceVersionReader(lake).query_local(business()).status == "not_found"
            )
        finally:
            release.set()
        assert first.result(5)["status"] == "ready"
    before = counts(lake)
    assert prepare(lake)["source_ref"] == asdict(ref) and counts(lake) == before
    assert before[-1] == 1


@pytest.mark.parametrize(
    "failure", ["tampered", "outside_root", "placeholder", "byte_cap", "deadline"]
)
def test_local_read_failure_preserves_retirement(lake, monkeypatch, failure):
    from company_wiki.source_catalog.local_reconcile import prepare_local_source
    from company_wiki.source_catalog.local_inventory import LocalPrepareLimits
    from company_wiki.source_catalog import resolver

    ref, path, _ = imported(lake)
    retire(lake, ref)
    before = counts(lake)
    limits = None
    if failure == "tampered":
        path.write_bytes(DATA.replace(b"Acme", b"Fake"))
    elif failure == "outside_root":
        with lake.store.transaction() as conn:
            conn.execute(
                "UPDATE locations SET relative_path='../escaped.htm' WHERE document_id=? AND role='original_primary'",
                (ref.document_id,),
            )
    elif failure == "placeholder":
        monkeypatch.setattr(resolver, "_needs_hydration", lambda _: True)
    elif failure == "byte_cap":
        limits = LocalPrepareLimits(max_bytes=10)
    elif failure == "deadline":
        limits = LocalPrepareLimits(timeout_seconds=0.000001)
    result = prepare_local_source(lake, business(), limits=limits)
    assert result["status"] != "ready" and result["blocks_download"]
    assert (
        counts(lake) == before
        and lake.reader.exact_source_version(ref.document_id)["source_status"]
        == "retired"
    )


class NoSupplier:
    name = "offline-no-supplier"
    version = "1.0.0"

    def __init__(self):
        self.discover_calls = 0
        self.fetch_calls = 0

    def discover(self, request):
        self.discover_calls += 1
        raise AssertionError("local reuse must not discover")

    def fetch(self, candidate, staging_dir):
        self.fetch_calls += 1
        raise AssertionError("local reuse must not fetch")


@pytest.mark.parametrize(
    "published,asof,allow,expected",
    [
        ("2026-01-28", "2026-10-09", True, "reused"),
        ("2026-01-28", "2026-10-09", False, "reused"),
        (None, "2026-10-09", True, "missing"),
        ("2026-01-28", "2026-01-27", True, "missing"),
    ],
)
def test_ensure_composition_reconciles_or_reports_gap_before_adapter(
    lake, published, asof, allow, expected
):
    from company_wiki.source_catalog.acquisition import (
        AcquisitionCoordinator,
        AdapterRegistry,
    )
    from company_wiki.source_catalog.acquisition_service import SourceAcquisitionService
    from company_wiki.source_catalog.acquisition_journal import AcquisitionJournal
    from company_wiki.source_catalog.canonical_writer import CanonicalSourceWriter

    ref, _, _ = imported(lake, published=published)
    retire(lake, ref)
    adapter = NoSupplier()
    service = SourceAcquisitionService(
        coordinator=AcquisitionCoordinator(
            catalog=lake,
            adapters=AdapterRegistry(adapter, adapter, adapter),
            staging_root=lake.config.catalog_dir / "staging",
        ),
        writer=CanonicalSourceWriter(lake),
        journal=AcquisitionJournal(lake.config.catalog_dir),
    )
    result = service.ensure(business(as_of_date=asof, allow_download=allow))
    assert result.status.value == expected and (
        adapter.discover_calls,
        adapter.fetch_calls,
    ) == (0, 0)
    if expected == "reused":
        assert (
            SourceVersionReader(lake).open_version(ref, purpose="source_export").data
            == DATA
        )


@pytest.mark.parametrize("form", ["10- Q", "10-\nQ"])
def test_actual_inline_tag_whitespace_is_canonical_sec_form(form):
    from company_wiki.source_catalog.dayu_fiscal_metadata import extract_sec_primary

    data = DATA.replace(b">10-Q<", (">" + form + "<").encode())
    primary = extract_sec_primary(data)
    assert primary["form_type"] == "10-Q" and primary["fiscal_period"] == "Q2"


def test_public_prepare_receipt_contains_no_physical_field(lake):
    ref, _, _ = imported(lake)
    retire(lake, ref)
    result = prepare(lake)
    assert result["status"] == "ready"

    def physical(value):
        if isinstance(value, dict):
            return any(
                any(
                    token in str(key).lower()
                    for token in ("path", "location", "root", "bundle")
                )
                or physical(child)
                for key, child in value.items()
            )
        return isinstance(value, (list, tuple)) and any(
            physical(child) for child in value
        )

    assert not physical(result)


def test_bounded_dayu_source_group_discovery_registers_existing_raw_without_fetch(lake):
    from dataclasses import replace

    raw_root = lake.config.project_root / "legacy_portfolio"
    group = raw_root / "ACME/filings/fil_0000012345-26-000007"
    group.mkdir(parents=True)
    path = group / "original.htm"
    path.write_bytes(DATA)
    sha = hashlib.sha256(DATA).hexdigest()
    meta = {
        "company_id": "12345",
        "ticker": "ACME",
        "accession_number": "0000012345-26-000007",
        "primary_document": path.name,
        "form_type": "10-Q",
        "fiscal_year": 2025,
        "fiscal_period": "Q2",
        "report_date": "2025-12-31",
        "filing_date": "2026-01-28",
        "ingest_complete": True,
        "is_deleted": False,
        "files": [
            {
                "name": path.name,
                "sha256": sha,
                "size": len(DATA),
                "source_url": "https://www.sec.gov/Archives/edgar/data/12345/000001234526000007/original.htm",
            }
        ],
    }
    group.joinpath("meta.json").write_text(json.dumps(meta), encoding="utf-8")
    lake.config = replace(
        lake.config,
        roots=(*lake.config.roots, RootSpec("legacy", raw_root, "dayu_portfolio")),
        reusable_root_kinds=("company_raw", "dayu_portfolio"),
    )
    _ = lake.store
    original = {p: p.read_bytes() for p in group.iterdir()}
    result = prepare(lake)
    assert result["status"] == "ready" and result["source_ref"]["content_sha256"] == sha
    assert result["download_events"] == 0 and original == {
        p: p.read_bytes() for p in group.iterdir()
    }
    assert not list(lake.config.roots[0].path.rglob("*.html"))
