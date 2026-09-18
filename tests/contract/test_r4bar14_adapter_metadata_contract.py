"""F-BAR-14 regression: the sidecar adapter must not NARROW the declared metadata.

Found while fixing F-BAR-10 (2026-09-18).  The legacy walk wrote the whole `.source.json`
into the document's `acquisition` block; the adapter's first version mapped a fixed subset
and dropped everything else.  Because the adapter path REPLACES the legacy walk for any root
that declares an adapter, that narrowing was a live behaviour change, measured as:

* `form_type` gone      -> the resolver's form gate answered `form_type_mismatch` for a
                            filing that resolves on a legacy-walked root;
* `company_name` gone   -> entity anchoring for external roots lost its only honest anchor
                            (the B08 level 2 lesson);
* `source_title` gone   -> the document title fell back to the file stem, so B05's
                            provenance stopped seeing a declared-title conflict between two
                            captures (B06's `blocked` qualification became `verified_input`);
* older `filing_date` spelling gone -> `published_date_unknown`;
* `fiscal_year` stringified -> the SQL filter `json_extract(...) = <int>` matched nothing.

The rule now: declared keys pass through, the adapter's canonical mapping overlays the keys
it owns.  This test pins the information set in the CONTAINER (the `acquisition` block the
rest of the system reads), not the adapter's internal dict, so it fails if the narrowing
comes back through any refactor.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from company_wiki.source_catalog import CatalogConfig, SourceCatalog
from company_wiki.source_catalog.models import RootSpec

BODY = b"%PDF-1.4\n% r4bar14 declared-metadata passthrough fixture\n"
DIGEST = hashlib.sha256(BODY).hexdigest()
DECLARED = {
    "schema_version": "1.0",
    "canonical_entity_id": "ent-r4bar14",
    "display_name": "R4BAR14 Acme",
    "company_name": "R4BAR14 Acme Holdings",
    "market": "US",
    "security_id": "R4BAR14",
    "document_kind": "annual_report",
    "fiscal_year": 2025,
    "period_end": "2025-12-31",
    "published_at": "2026-02-20",
    "form_type": "10-K",
    "provider": "sec",
    "provider_document_id": "r4bar14-doc-1",
    "source_url": "https://www.sec.gov/Archives/edgar/data/r4bar14/2025.htm",
    "source_title": "R4BAR14 2025 Annual Report",
    "language": "en",
    "content_sha256": DIGEST,
}


def _scan(tmp_path: Path) -> tuple[SourceCatalog, dict]:
    root_dir = tmp_path / "roots" / "declared"
    root_dir.mkdir(parents=True, exist_ok=True)
    (root_dir / "2025-annual.pdf").write_bytes(BODY)
    (root_dir / "2025-annual.pdf.source.json").write_text(
        json.dumps(DECLARED, ensure_ascii=False), encoding="utf-8")
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path,
            catalog_dir=tmp_path / ".source_catalog",
            reusable_root_kinds=("company_raw", "directory"),
            roots=(RootSpec("declared_root", root_dir, "directory", priority=10,
                            adapter_id="sidecar_filing_v1", read_only=True,
                            reusable_for_filing=True),),
        )
    )
    report = catalog.scan()
    assert dict(report.strategy) == {"declared_root": "adapter"}, report.strategy
    connection = sqlite3.connect(f"file:{catalog.config.database_path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        row = dict(connection.execute(
            "SELECT title, published_date, metadata_json FROM documents").fetchone())
    finally:
        connection.close()
    return catalog, row


def test_declared_keys_survive_in_the_acquisition_block(tmp_path: Path) -> None:
    _catalog, row = _scan(tmp_path)
    acquisition = json.loads(row["metadata_json"])["acquisition"]
    for key in ("form_type", "company_name", "source_title", "provider",
                "provider_document_id", "canonical_entity_id", "security_id", "market"):
        assert acquisition.get(key) == DECLARED[key], (key, acquisition.get(key))
    # fiscal_year keeps the CONTAINER type the SQL filter needs (int, not "2025")
    assert acquisition["fiscal_year"] == 2025
    assert isinstance(acquisition["fiscal_year"], int)
    # the adapter's own identity is still declared, and the date aliases are filled from the
    # declared `published_at` (the scanner derives the document's published date from
    # `filing_date`, and the older spelling must keep working too)
    assert acquisition["adapter_id"] == "sidecar_filing_v1"
    assert acquisition["filing_date"] == DECLARED["published_at"]
    assert acquisition["published_at"] == DECLARED["published_at"]
    assert row["published_date"] == DECLARED["published_at"], row["published_date"]
    # the title derivation and the published date now see what the sidecar declared
    assert row["title"] == DECLARED["source_title"], row["title"]


def test_the_sql_fiscal_year_filter_matches_an_adapter_root(tmp_path: Path) -> None:
    """The int is not cosmetic: SQLite compares types strictly, so "2025" matches nothing."""
    catalog, _row = _scan(tmp_path)
    candidates = catalog.query_filing_candidates(
        document_kind="annual_report", source_statuses=("active",), fiscal_year=2025,
    )
    assert len(candidates) == 1, candidates
    assert candidates[0]["metadata"]["acquisition"]["fiscal_year"] == 2025


# ---------------------------------------------------------------------------
# The mapping's own branches (the coverage ratchet requires >= 95 on this module, and every
# arm below is a real input shape a sidecar can have)
# ---------------------------------------------------------------------------


def _adapter():
    from company_wiki.source_catalog.adapters.sidecar import SidecarFilingAdapter

    return SidecarFilingAdapter()


def _payload(tmp_path: Path, **overrides) -> dict:
    directory = tmp_path / "branch"
    directory.mkdir(parents=True, exist_ok=True)
    body = b"%PDF-1.4 branch"
    (directory / "2025.pdf").write_bytes(body)
    payload = {
        "schema_version": "1.0",
        "canonical_entity_id": "ent-branch",
        "display_name": "Branch Co",
        "market": "US",
        "security_id": "BRANCH",
        "document_kind": "annual_report",
        "fiscal_year": 2025,
        "period_end": "2025-12-31",
        "published_at": "2026-02-20",
        "provider": "sec",
        "provider_document_id": "branch-1",
        "content_sha256": hashlib.sha256(body).hexdigest(),
    }
    payload.update(overrides)
    for key in overrides.get("_drop", ()):  # explicit removal support
        payload.pop(key, None)
    payload.pop("_drop", None)
    (directory / "2025.pdf.source.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return {"directory": directory, "payload": payload, "body": body}


def _normalized(tmp_path: Path, **overrides) -> dict:
    fixture = _payload(tmp_path, **overrides)
    candidates = _adapter().enumerate(fixture["directory"])
    # An INCOMPLETE sidecar degrades to `indexed_only` (the adapter's own rule), and the
    # normalized payload is still built - which is exactly what several branch arms below
    # assert, so fall back instead of requiring `original_primary`.
    primary = next((item for item in candidates if item.role == "original_primary"),
                   candidates[0])
    return primary.normalized


def test_fiscal_year_arms(tmp_path: Path) -> None:
    """Every arm of the fiscal-year coercion, including the ones that yield None."""
    assert _normalized(tmp_path / "int")["fiscal_year"] == 2025
    assert _normalized(tmp_path / "digits", fiscal_year="2024")["fiscal_year"] == 2024
    # a non-digit spelling is carried verbatim rather than invented
    assert _normalized(tmp_path / "text", fiscal_year="FY2023")["fiscal_year"] == "FY2023"
    assert _normalized(tmp_path / "empty", fiscal_year="")["fiscal_year"] is None
    assert _normalized(tmp_path / "none", fiscal_year=None)["fiscal_year"] is None
    # bool is an int subclass and is never a year
    assert _normalized(tmp_path / "bool", fiscal_year=True)["fiscal_year"] is None
    assert _normalized(tmp_path / "blank", fiscal_year="   ")["fiscal_year"] is None


def test_date_and_name_alias_arms(tmp_path: Path) -> None:
    """`published_at`/`filing_date` and `company_name`/`display_name` are both accepted."""
    legacy = _normalized(tmp_path / "legacy-date",
                         _drop=("published_at",), filing_date="2025-11-05")
    assert legacy["filing_date"] == "2025-11-05"
    assert legacy["published_at"] == "2025-11-05"
    fallback_name = _normalized(tmp_path / "display-name", _drop=("company_name",))
    assert fallback_name["company_name"] == "Branch Co"
    both = _normalized(tmp_path / "both-names", company_name="Declared Name")
    assert both["company_name"] == "Declared Name"


def test_legacy_containers_are_never_borrowed(tmp_path: Path) -> None:
    """FC-502, restated where the passthrough lives: the denylist must hold."""
    normalized = _normalized(
        tmp_path / "containers",
        acquisition={"fiscal_year": 1999, "provider": "wrong"},
        dayu_meta={"security_id": "000001"},
    )
    assert "acquisition" not in normalized
    assert "dayu_meta" not in normalized
    assert normalized["fiscal_year"] == 2025
    assert normalized["provider"] == "sec"


def test_an_unparseable_sidecar_yields_an_empty_mapping(tmp_path: Path) -> None:
    directory = tmp_path / "broken"
    directory.mkdir(parents=True)
    (directory / "2025.pdf").write_bytes(b"%PDF-1.4 broken")
    (directory / "2025.pdf.source.json").write_text("{not json", encoding="utf-8")
    candidates = _adapter().enumerate(directory)
    primary = next((item for item in candidates if item.role == "original_primary"),
                   candidates[0])
    assert primary.normalized == {}
    assert primary.role == "indexed_only"
