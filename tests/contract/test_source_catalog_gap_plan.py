"""WU-4.2: metadata-only discovery alignment and GapPlan (RED first).

The GapPlan builder is a pure function: given the local reusable candidates
(already resolved handles) and the remote provider metadata (discovered
DownloadCandidates, NEVER downloaded), it produces the gap plan:

- reuse: local candidate that is already the latest for its period;
- missing: periods the provider has published (by as_of) that local lacks;
- newer_revision: same period, provider accession newer than local;
- not_published: provider has nothing newer than the latest local;
- provider_unavailable: discovery failed/rate-limited → incomplete, keep
  local, never claim up-to-date;
- future: provider metadata published after as_of is excluded.

RED phase: the module does not exist (ImportError → RED).
"""

from __future__ import annotations

import sys
from pathlib import Path


WIKI_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WIKI_ROOT / "src"))

from company_wiki.source_catalog.gap_plan import build_gap_plan  # noqa: E402


class _Local:
    """Minimal stand-in for a resolved SourceHandle (fiscal_year/published)."""

    def __init__(self, fiscal_year: int, published_date: str, accession: str = ""):
        self.fiscal_year = fiscal_year
        self.published_date = published_date
        self.provider_document_id = accession or f"acc-{fiscal_year}"

    def to_dict(self):
        return {
            "fiscal_year": self.fiscal_year,
            "published_date": self.published_date,
            "provider_document_id": self.provider_document_id,
        }


class _Remote:
    """Minimal stand-in for a DownloadCandidate (metadata only)."""

    def __init__(
        self,
        fiscal_year: int,
        filing_date: str,
        accession: str,
        amended: bool = False,
    ):
        self.fiscal_year = fiscal_year
        self.filing_date = filing_date
        self.provider_document_id = accession
        self.amended = amended

    def to_dict(self):
        return {
            "fiscal_year": self.fiscal_year,
            "filing_date": self.filing_date,
            "provider_document_id": self.provider_document_id,
            "amended": self.amended,
        }


def _plan(local, remote, provider_error=None):
    return build_gap_plan(
        request_id="req-1",
        as_of_date="2026-07-31",
        document_kind="annual_report",
        entity="ACME",
        market="US",
        local_handles=local,
        remote_candidates=remote,
        provider_error=provider_error,
    )


def test_local_old_gap_new_period(tmp_path):
    """Local has 2024; provider published 2025 (by as_of): gap = 2025 only."""
    plan = _plan(
        [_Local(2024, "2025-04-15")],
        [_Remote(2025, "2026-04-15", "acc-2025")],
    )
    assert plan.not_published is False
    assert [c.fiscal_year for c in plan.reuse] == [2024]
    assert [c.fiscal_year for c in plan.missing] == [2025]
    assert plan.newer_revision == ()


def test_local_up_to_date_zero_gap(tmp_path):
    """Local has the latest the provider knows: download=0, reuse kept."""
    plan = _plan(
        [_Local(2025, "2026-04-15")],
        [_Remote(2025, "2026-04-15", "acc-2025")],
    )
    assert plan.not_published is True
    assert plan.missing == ()
    assert plan.newer_revision == ()
    assert [c.fiscal_year for c in plan.reuse] == [2025]


def test_new_period_not_yet_published(tmp_path):
    """Provider has nothing beyond local latest: gap=0, not_published."""
    plan = _plan(
        [_Local(2025, "2026-04-15")],
        [_Remote(2025, "2026-04-15", "acc-2025")],
    )
    assert plan.not_published is True
    assert plan.missing == ()


def test_older_revision_listed_not_downloaded(tmp_path):
    """Same period, provider accession newer than local: only the newer
    revision is listed as a gap; old revision stays in provenance."""
    plan = _plan(
        [_Local(2025, "2026-04-15", accession="acc-old")],
        [_Remote(2025, "2026-04-15", "acc-new")],
    )
    assert [c.provider_document_id for c in plan.newer_revision] == ["acc-new"]
    assert plan.missing == ()


def test_provider_unavailable_keeps_local_and_incomplete(tmp_path):
    """Provider offline/rate-limited: keep local, return incomplete, never
    claim up-to-date."""
    plan = _plan(
        [_Local(2024, "2025-04-15")],
        [],
        provider_error="rate_limit_exceeded",
    )
    assert plan.provider_unavailable is True
    assert plan.provider_reason == "rate_limit_exceeded"
    assert plan.not_published is False  # must not claim up-to-date
    assert [c.fiscal_year for c in plan.reuse] == [2024]


def test_remote_after_as_of_excluded(tmp_path):
    """Provider metadata published after as_of is excluded from the gap."""
    plan = _plan(
        [_Local(2024, "2025-04-15")],
        [_Remote(2025, "2026-08-15", "acc-2025")],  # after as_of 2026-07-31
    )
    assert [c.fiscal_year for c in plan.future] == [2025]
    assert plan.missing == ()
    assert plan.not_published is True  # nothing eligible to download


def test_gap_hash_deterministic(tmp_path):
    plan1 = _plan(
        [_Local(2024, "2025-04-15")],
        [_Remote(2025, "2026-04-15", "acc-2025")],
    )
    plan2 = _plan(
        [_Local(2024, "2025-04-15")],
        [_Remote(2025, "2026-04-15", "acc-2025")],
    )
    assert plan1.gap_hash == plan2.gap_hash
    assert len(plan1.gap_hash) == 64


def test_gap_hash_order_independent_same_period_multi_accession(tmp_path):
    """Reviewer finding: two local handles sharing a period with different
    accessions must hash identically regardless of input order."""
    a = _Local(2025, "2026-04-15", accession="acc-old")
    b = _Local(2025, "2026-04-15", accession="acc-new")
    remote = [_Remote(2025, "2026-04-15", "acc-new")]
    p1 = _plan([a, b], remote)
    p2 = _plan([b, a], remote)
    assert p1.gap_hash == p2.gap_hash


def test_latest_as_of_with_allow_download_still_returns_gap(tmp_path):
    """Reviewer finding: latest_as_of + allow_download=True must NOT bypass
    the plan — metadata-only first, nothing fetched."""
    import hashlib
    import json
    import sqlite3

    from company_wiki.source_catalog import (
        AcquisitionCoordinator,
        AcquisitionStatus,
        AdapterRegistry,
        CatalogConfig,
        DownloadCandidate,
        RootSpec,
        SourceCatalog,
        SourceRequest,
    )

    project = tmp_path / "project"
    companies = project / "companies"
    (companies / "ACME" / "raw").mkdir(parents=True)
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("company_raw", companies, "company_raw", priority=10),),
            reusable_root_kinds=("company_raw",),
        )
    )
    catalog.store.status()
    con = sqlite3.connect(catalog.config.database_path)
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS sources (
            source_id TEXT PRIMARY KEY, content_sha256 TEXT NOT NULL UNIQUE,
            byte_size INTEGER NOT NULL, mime_type TEXT NOT NULL, first_seen_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY, primary_source_id TEXT, title TEXT,
            source_type TEXT, document_kind TEXT, published_date TEXT,
            source_status TEXT NOT NULL, metadata_priority INTEGER NOT NULL,
            metadata_json TEXT NOT NULL, text_fingerprint TEXT,
            first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS entities (
            entity_id TEXT PRIMARY KEY, name TEXT NOT NULL, entity_kind TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS document_entities (
            document_id TEXT NOT NULL, entity_id TEXT NOT NULL,
            confidence REAL NOT NULL, method TEXT NOT NULL,
            PRIMARY KEY(document_id, entity_id)
        );
        CREATE TABLE IF NOT EXISTS locations (
            location_id TEXT PRIMARY KEY, root_id TEXT NOT NULL,
            relative_path TEXT NOT NULL, absolute_path TEXT NOT NULL,
            source_id TEXT, document_id TEXT, role TEXT NOT NULL,
            location_status TEXT NOT NULL, observed_size INTEGER,
            observed_mtime_ns INTEGER, last_seen_run TEXT NOT NULL,
            manifest_json TEXT, metadata_json TEXT NOT NULL, error TEXT
        );
        CREATE TABLE IF NOT EXISTS roots (
            root_id TEXT PRIMARY KEY, path TEXT NOT NULL, kind TEXT NOT NULL,
            priority INTEGER NOT NULL, last_scan_run TEXT, last_scanned_at TEXT
        );
        """
    )
    con.execute(
        "INSERT INTO roots VALUES ('company_raw', ?, 'company_raw', 10, NULL, NULL)",
        (str(companies),),
    )
    con.execute("INSERT INTO entities VALUES ('ticker:ACME', 'ACME', 'ticker')")
    did, sid = "doc-0", "src-0"
    body = b"%PDF-2024"
    f = companies / "ACME" / "0.pdf"
    f.write_bytes(body)
    sha = hashlib.sha256(body).hexdigest()
    meta = json.dumps(
        {"acquisition": {"fiscal_year": 2024, "market": "US", "security_id": "ACME",
         "form_type": "10-K", "source_url": "https://x/0.pdf",
         "retrieved_at": "2025-05-01T10:00:00Z", "collector_name": "t",
         "collector_version": "1.0.0"}}
    )
    manifest = json.dumps(
        {"content_sha256": sha, "retrieved_at": "2025-05-01T10:00:00Z",
         "collector_name": "t", "collector_version": "1.0.0",
         "mime_type": "application/pdf", "byte_size": len(body)}
    )
    con.execute("INSERT INTO sources VALUES (?,?,?,?,?)", (sid, sha, len(body), "application/pdf", "2025-01-01"))
    con.execute(
        "INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (did, sid, "ACME 2024 annual", "filing", "annual_report", "2025-04-15",
         "active", 1, meta, None, "2025-01-01", "2026-08-08"),
    )
    con.execute("INSERT INTO document_entities VALUES (?,?,?,?)", (did, "ticker:ACME", 1.0, "path_ticker"))
    con.execute(
        "INSERT INTO locations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("loc-0", "company_raw", "ACME/0.pdf", str(f), sid, did,
         "original_primary", "active", len(body), 1, "scan-x", manifest, "{}", None),
    )
    con.commit()
    con.close()

    fetch_calls = {"n": 0}

    class FakeAdapter:
        name = "fake"
        version = "1.0.0"

        def discover(self, request):
            return (DownloadCandidate(
                candidate_id="c-2025", provider="sec",
                provider_document_id="acc-2025", market="US", entity="ACME",
                title="ACME 2025 annual",
                source_url="https://www.sec.gov/x/2025.pdf",
                document_kind="annual_report", filing_date="2026-04-15",
                fiscal_year=2025,
            ),)

        def fetch(self, candidate, staging_dir):
            fetch_calls["n"] += 1
            raise AssertionError("fetch must not be called")

    coordinator = AcquisitionCoordinator(
        catalog=catalog,
        adapters=AdapterRegistry(cn=FakeAdapter(), hk=FakeAdapter(), us=FakeAdapter()),
        staging_root=tmp_path / "staging",
    )
    request = SourceRequest(
        entity="ACME", market="US", security_id="ACME",
        document_kind="annual_report", mode="latest_as_of",
        as_of_date="2026-07-31", allow_download=True,
    )
    result = coordinator.resolve_or_stage(request)
    assert result.status is AcquisitionStatus.GAP, result
    assert result.gap_plan is not None
    assert fetch_calls["n"] == 0
    assert not (tmp_path / "staging").exists()


def test_coordinator_latest_as_of_returns_gap_without_fetch(tmp_path):
    """End-to-end: latest_as_of + no allow_download → GAP status, discover=1,
    fetch=0, no files written to staging."""
    import hashlib
    import json
    import sqlite3

    from company_wiki.source_catalog import (
        AcquisitionCoordinator,
        AcquisitionStatus,
        CatalogConfig,
        DownloadCandidate,
        RootSpec,
        SourceCatalog,
        SourceRequest,
    )

    project = tmp_path / "project"
    companies = project / "companies"
    (companies / "ACME" / "raw").mkdir(parents=True)
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("company_raw", companies, "company_raw", priority=10),),
            reusable_root_kinds=("company_raw",),
        )
    )
    # local: one ACME FY2024 annual (capture-ready)
    catalog.store.status()
    con = sqlite3.connect(catalog.config.database_path)
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS sources (
            source_id TEXT PRIMARY KEY, content_sha256 TEXT NOT NULL UNIQUE,
            byte_size INTEGER NOT NULL, mime_type TEXT NOT NULL, first_seen_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY, primary_source_id TEXT, title TEXT,
            source_type TEXT, document_kind TEXT, published_date TEXT,
            source_status TEXT NOT NULL, metadata_priority INTEGER NOT NULL,
            metadata_json TEXT NOT NULL, text_fingerprint TEXT,
            first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS entities (
            entity_id TEXT PRIMARY KEY, name TEXT NOT NULL, entity_kind TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS document_entities (
            document_id TEXT NOT NULL, entity_id TEXT NOT NULL,
            confidence REAL NOT NULL, method TEXT NOT NULL,
            PRIMARY KEY(document_id, entity_id)
        );
        CREATE TABLE IF NOT EXISTS locations (
            location_id TEXT PRIMARY KEY, root_id TEXT NOT NULL,
            relative_path TEXT NOT NULL, absolute_path TEXT NOT NULL,
            source_id TEXT, document_id TEXT, role TEXT NOT NULL,
            location_status TEXT NOT NULL, observed_size INTEGER,
            observed_mtime_ns INTEGER, last_seen_run TEXT NOT NULL,
            manifest_json TEXT, metadata_json TEXT NOT NULL, error TEXT
        );
        CREATE TABLE IF NOT EXISTS roots (
            root_id TEXT PRIMARY KEY, path TEXT NOT NULL, kind TEXT NOT NULL,
            priority INTEGER NOT NULL, last_scan_run TEXT, last_scanned_at TEXT
        );
        """
    )
    con.execute(
        "INSERT INTO roots VALUES ('company_raw', ?, 'company_raw', 10, NULL, NULL)",
        (str(companies),),
    )
    con.execute("INSERT INTO entities VALUES ('ticker:ACME', 'ACME', 'ticker')")
    did, sid = "doc-0", "src-0"
    body = b"%PDF-2024"
    f = companies / "ACME" / "0.pdf"
    f.write_bytes(body)
    sha = hashlib.sha256(body).hexdigest()
    meta = json.dumps(
        {
            "acquisition": {
                "fiscal_year": 2024,
                "market": "US",
                "security_id": "ACME",
                "form_type": "10-K",
                "source_url": "https://x/0.pdf",
                "retrieved_at": "2025-05-01T10:00:00Z",
                "collector_name": "t",
                "collector_version": "1.0.0",
            }
        }
    )
    manifest = json.dumps(
        {
            "content_sha256": sha,
            "retrieved_at": "2025-05-01T10:00:00Z",
            "collector_name": "t",
            "collector_version": "1.0.0",
            "mime_type": "application/pdf",
            "byte_size": len(body),
        }
    )
    con.execute("INSERT INTO sources VALUES (?,?,?,?,?)", (sid, sha, len(body), "application/pdf", "2025-01-01"))
    con.execute(
        "INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (did, sid, "ACME 2024 annual", "filing", "annual_report", "2025-04-15",
         "active", 1, meta, None, "2025-01-01", "2026-08-08"),
    )
    con.execute("INSERT INTO document_entities VALUES (?,?,?,?)", (did, "ticker:ACME", 1.0, "path_ticker"))
    con.execute(
        "INSERT INTO locations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ( "loc-0", "company_raw", "ACME/0.pdf", str(f), sid, did,
         "original_primary", "active", len(body), 1, "scan-x", manifest, "{}", None),
    )
    con.commit()
    con.close()

    discover_calls = {"n": 0}
    fetch_calls = {"n": 0}

    class FakeAdapter:
        name = "fake"
        version = "1.0.0"

        def discover(self, request):
            discover_calls["n"] += 1
            return (
                DownloadCandidate(
                    candidate_id="c-2025",
                    provider="sec",
                    provider_document_id="acc-2025",
                    market="US",
                    entity="ACME",
                    title="ACME 2025 annual",
                    source_url="https://www.sec.gov/x/2025.pdf",
                    document_kind="annual_report",
                    filing_date="2026-04-15",
                    fiscal_year=2025,
                ),
            )

        def fetch(self, candidate, staging_dir):
            fetch_calls["n"] += 1
            raise AssertionError("fetch must not be called for metadata-only")

    from company_wiki.source_catalog import AdapterRegistry

    coordinator = AcquisitionCoordinator(
        catalog=catalog,
        adapters=AdapterRegistry(cn=FakeAdapter(), hk=FakeAdapter(), us=FakeAdapter()),
        staging_root=tmp_path / "staging",
    )
    request = SourceRequest(
        entity="ACME",
        market="US",
        security_id="ACME",
        document_kind="annual_report",
        mode="latest_as_of",
        as_of_date="2026-07-31",
    )
    result = coordinator.resolve_or_stage(request)
    assert result.status is AcquisitionStatus.GAP, result
    assert result.gap_plan is not None
    assert [c.fiscal_year for c in result.gap_plan.missing] == [2025]
    assert [c.fiscal_year for c in result.gap_plan.reuse] == [2024]
    assert discover_calls["n"] == 1
    assert fetch_calls["n"] == 0
    assert not (tmp_path / "staging").exists()


def test_service_ensure_latest_as_of_returns_gap(tmp_path):
    """Reviewer finding: SourceAcquisitionService.ensure must surface GAP
    (not raise) for latest_as_of, with a journal record and fetch=0."""
    import hashlib
    import json
    import sqlite3

    from company_wiki.source_catalog import (
        AcquisitionCoordinator,
        AcquisitionJournal,
        AdapterRegistry,
        CanonicalSourceWriter,
        CatalogConfig,
        DownloadCandidate,
        RootSpec,
        SourceAcquisitionService,
        SourceCatalog,
        SourceRequest,
    )

    project = tmp_path / "project"
    companies = project / "companies"
    (companies / "ACME" / "raw").mkdir(parents=True)
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("company_raw", companies, "company_raw", priority=10),),
            reusable_root_kinds=("company_raw",),
        )
    )
    catalog.store.status()
    con = sqlite3.connect(catalog.config.database_path)
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS sources (
            source_id TEXT PRIMARY KEY, content_sha256 TEXT NOT NULL UNIQUE,
            byte_size INTEGER NOT NULL, mime_type TEXT NOT NULL, first_seen_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY, primary_source_id TEXT, title TEXT,
            source_type TEXT, document_kind TEXT, published_date TEXT,
            source_status TEXT NOT NULL, metadata_priority INTEGER NOT NULL,
            metadata_json TEXT NOT NULL, text_fingerprint TEXT,
            first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS entities (
            entity_id TEXT PRIMARY KEY, name TEXT NOT NULL, entity_kind TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS document_entities (
            document_id TEXT NOT NULL, entity_id TEXT NOT NULL,
            confidence REAL NOT NULL, method TEXT NOT NULL,
            PRIMARY KEY(document_id, entity_id)
        );
        CREATE TABLE IF NOT EXISTS locations (
            location_id TEXT PRIMARY KEY, root_id TEXT NOT NULL,
            relative_path TEXT NOT NULL, absolute_path TEXT NOT NULL,
            source_id TEXT, document_id TEXT, role TEXT NOT NULL,
            location_status TEXT NOT NULL, observed_size INTEGER,
            observed_mtime_ns INTEGER, last_seen_run TEXT NOT NULL,
            manifest_json TEXT, metadata_json TEXT NOT NULL, error TEXT
        );
        CREATE TABLE IF NOT EXISTS roots (
            root_id TEXT PRIMARY KEY, path TEXT NOT NULL, kind TEXT NOT NULL,
            priority INTEGER NOT NULL, last_scan_run TEXT, last_scanned_at TEXT
        );
        """
    )
    con.execute(
        "INSERT INTO roots VALUES ('company_raw', ?, 'company_raw', 10, NULL, NULL)",
        (str(companies),),
    )
    con.execute("INSERT INTO entities VALUES ('ticker:ACME', 'ACME', 'ticker')")
    did, sid = "doc-0", "src-0"
    body = b"%PDF-2024"
    f = companies / "ACME" / "0.pdf"
    f.write_bytes(body)
    sha = hashlib.sha256(body).hexdigest()
    meta = json.dumps(
        {"acquisition": {"fiscal_year": 2024, "market": "US", "security_id": "ACME",
         "form_type": "10-K", "source_url": "https://x/0.pdf",
         "retrieved_at": "2025-05-01T10:00:00Z", "collector_name": "t",
         "collector_version": "1.0.0"}}
    )
    manifest = json.dumps(
        {"content_sha256": sha, "retrieved_at": "2025-05-01T10:00:00Z",
         "collector_name": "t", "collector_version": "1.0.0",
         "mime_type": "application/pdf", "byte_size": len(body)}
    )
    con.execute("INSERT INTO sources VALUES (?,?,?,?,?)", (sid, sha, len(body), "application/pdf", "2025-01-01"))
    con.execute(
        "INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (did, sid, "ACME 2024 annual", "filing", "annual_report", "2025-04-15",
         "active", 1, meta, None, "2025-01-01", "2026-08-08"),
    )
    con.execute("INSERT INTO document_entities VALUES (?,?,?,?)", (did, "ticker:ACME", 1.0, "path_ticker"))
    con.execute(
        "INSERT INTO locations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("loc-0", "company_raw", "ACME/0.pdf", str(f), sid, did,
         "original_primary", "active", len(body), 1, "scan-x", manifest, "{}", None),
    )
    con.commit()
    con.close()

    fetch_calls = {"n": 0}

    class FakeAdapter:
        name = "fake"
        version = "1.0.0"

        def discover(self, request):
            return (DownloadCandidate(
                candidate_id="c-2025", provider="sec",
                provider_document_id="acc-2025", market="US", entity="ACME",
                title="ACME 2025 annual",
                source_url="https://www.sec.gov/x/2025.pdf",
                document_kind="annual_report", filing_date="2026-04-15",
                fiscal_year=2025,
            ),)

        def fetch(self, candidate, staging_dir):
            fetch_calls["n"] += 1
            raise AssertionError("fetch must not be called")

    journal_dir = tmp_path / "journal"
    journal_dir.mkdir(parents=True, exist_ok=True)
    journal = AcquisitionJournal(journal_dir)
    coordinator = AcquisitionCoordinator(
        catalog=catalog,
        adapters=AdapterRegistry(cn=FakeAdapter(), hk=FakeAdapter(), us=FakeAdapter()),
        staging_root=tmp_path / "staging",
    )
    service = SourceAcquisitionService(
        coordinator=coordinator,
        journal=journal,
        writer=CanonicalSourceWriter(catalog),
    )
    request = SourceRequest(
        entity="ACME", market="US", security_id="ACME",
        document_kind="annual_report", mode="latest_as_of",
        as_of_date="2026-07-31",
    )
    result = service.ensure(request)
    assert result.status.value == "gap", result
    assert result.acquisition.gap_plan is not None
    assert [c.fiscal_year for c in result.acquisition.gap_plan.missing] == [2025]
    assert fetch_calls["n"] == 0
    records = [
        json.loads(line)
        for line in journal.path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(r.get("outcome") == "gap_plan" for r in records), records
