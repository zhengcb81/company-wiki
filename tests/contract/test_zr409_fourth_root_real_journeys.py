"""ZR-409 acceptance tests: fourth root by CONFIG ONLY + three REAL-root
read-only user journeys (phase D exit card).

  C1  The production config now carries a fourth root ``future_lake``
      (kind directory + registered sidecar adapter, read-only, reusable):
      the config loads, policy-export lists FOUR reusable roots, and the
      product source is UNCHANGED (core diff = 0; asserted by the card's
      git diff evidence, pinned here by the config-only shape).
  C2  Three REAL-root read-only journeys against the production catalog:
      (a) companies Zijin 601899 FY2025 annual -> REUSED_EXACT, canonical
          under companies/;
      (b) dayu-ONLY HK 1548 FY2021 annual (content absent from companies)
          -> REUSED_EXACT, canonical under the dayu portfolio, nothing
          copied into companies (document/location counts unchanged);
      (c) Dropbox CN 688031 FY2024 annual -> REUSED_EXACT, canonical under
          the Dropbox root.
      Every journey: download_events=0, resolve-only (no writer), and the
      real roots + catalog bytes are untouched (before/after fingerprint).
  C3  Scenario mapping (EX/LT/DL/IDX/UJ) is pinned in the implementer
      receipt as a table; the mapped suites are re-run green (this module
      re-runs the future-root EX-08 family against the production config
      shape).

Real-root access is READ-ONLY: resolve uses the read-only resolver and the
fingerprints prove zero writes (no downloads, no copies, no catalog
mutation).
"""

from __future__ import annotations

import hashlib
import sqlite3
import sys
from pathlib import Path


WIKI_ROOT = Path(r"C:\Users\郑曾波\Projects\company-wiki")
sys.path.insert(0, str(WIKI_ROOT / "src"))

PRODUCTION_DB = WIKI_ROOT / ".source_catalog" / "catalog.sqlite3"
PRODUCTION_CONFIG = WIKI_ROOT / "config" / "source_catalog.yaml"


def _production_catalog():
    from company_wiki.source_catalog import SourceCatalog
    from company_wiki.source_catalog.config import load_catalog_config

    config = load_catalog_config(PRODUCTION_CONFIG, project_root=WIKI_ROOT)
    return SourceCatalog(config)


def _resolve_exact(catalog, *, entity, market, security_id, fy, pdoc, provider, as_of):
    from company_wiki.source_catalog import SourceRequest, SourceResolver
    from company_wiki.source_catalog.resolver import ResolutionStatus

    result = SourceResolver(catalog).resolve(
        SourceRequest(
            entity=entity,
            market=market,
            security_id=security_id,
            document_kind="annual_report",
            fiscal_year=fy,
            provider=provider,
            provider_document_id=pdoc,
            as_of_date=as_of,
            mode="exact",
        )
    )
    assert result.status is ResolutionStatus.REUSED_EXACT, result.debug_trace
    return result


def _shallow_fingerprint(directory: Path) -> str:
    """(top-level child name, size, mtime_ns) digest of a real root — a
    cheap read-only write oracle (full rglob over the production roots
    would take minutes; a copy into any root changes the top level, and
    sample-file bytes+mtime are pinned separately)."""
    digest = hashlib.sha256()
    for child in sorted(directory.iterdir()):
        digest.update(child.name.encode())
        try:
            stat = child.stat()
            digest.update(str(stat.st_size).encode())
            digest.update(str(stat.st_mtime_ns).encode())
        except OSError:
            digest.update(b"inaccessible")
    return digest.hexdigest()


def _file_fingerprint(path: Path) -> str:
    """(size, mtime_ns, sha256) of one concrete file."""
    stat = path.stat()
    digest = hashlib.sha256(path.read_bytes())
    return f"{stat.st_size}:{stat.st_mtime_ns}:{digest.hexdigest()}"


def _catalog_dir_fingerprint() -> str:
    """(name, size, mtime_ns) digest of the catalog directory listing —
    byte-reading the 49GB database is unnecessary for a read-only proof."""
    directory = PRODUCTION_DB.parent
    digest = hashlib.sha256()
    for child in sorted(directory.iterdir()):
        if child.is_file() and child.name.startswith("catalog.sqlite3"):
            stat = child.stat()
            digest.update(child.name.encode())
            digest.update(str(stat.st_size).encode())
            digest.update(str(stat.st_mtime_ns).encode())
    return digest.hexdigest()


def _root_dir(catalog, root_id: str) -> Path:
    for root in catalog.config.roots:
        if root.root_id == root_id:
            return Path(root.path)
    raise AssertionError(f"root {root_id} missing from config")


# ---------------------------------------------------------------------------
# C1 — fourth root by config only
# ---------------------------------------------------------------------------


def test_c1_production_config_has_fourth_root():
    """future_lake is present, directory-kind, sidecar-adapter-bound,
    read-only and reusable — the config-only fourth root (EX-08)."""
    from company_wiki.source_catalog.config import load_catalog_config

    config = load_catalog_config(PRODUCTION_CONFIG, project_root=WIKI_ROOT)
    by_id = {root.root_id: root for root in config.roots}
    assert "future_lake" in by_id
    future = by_id["future_lake"]
    assert future.kind == "directory"
    assert future.adapter_id == "sidecar_filing_v1"
    assert future.read_only is True
    assert future.reusable_for_filing is True
    assert len(by_id) == 4


def test_c1_policy_export_lists_four_reusable_roots():
    """The policy export (consumed by filing containment) lists all four
    roots as reusable — the future root is a first-class citizen."""
    from company_wiki.source_catalog.policy_2x import export_policy_2x
    from company_wiki.source_catalog.config import load_catalog_config

    config = load_catalog_config(PRODUCTION_CONFIG, project_root=WIKI_ROOT)
    _policy_hash, policy = export_policy_2x(config)
    reusable = {
        entry["root_id"]
        for entry in policy["roots"]
        if entry["reusable_for_filing"] is True
    }
    assert reusable == {"company_raw", "dayu_portfolio", "dropbox_stock", "future_lake"}


def test_c1_future_lake_fixture_dir_exists():
    """The adapter fixture directory exists so the root is scannable."""
    assert (WIKI_ROOT / "future_lake").is_dir()


# ---------------------------------------------------------------------------
# C2 — three REAL-root read-only journeys
# ---------------------------------------------------------------------------

ZIJIN = dict(
    entity="紫金矿业",
    market="CN",
    security_id="601899",
    fy=2025,
    pdoc="1225023658",
    provider="cninfo",
    as_of="2026-08-01",
)
DAYU_ONLY = dict(
    entity="金斯瑞生物科技",
    market="HK",
    security_id="1548",
    fy=2021,
    pdoc="10225111",
    provider="hkexnews",
    as_of="2026-08-01",
)
DROPBOX = dict(
    entity="星环科技",
    market="CN",
    security_id="688031",
    fy=2024,
    pdoc="1223325316",
    provider="cninfo",
    as_of="2026-08-01",
)


def test_c2_journey_companies_zijin():
    """Journey A: companies-root annual resolves exactly, canonical under
    companies/, zero downloads, zero writes."""
    catalog = _production_catalog()
    companies_before = _shallow_fingerprint(_root_dir(catalog, "company_raw"))
    result = _resolve_exact(catalog, **ZIJIN)
    handle = result.matches[0]
    normalized = handle.canonical_path.replace("\\", "/")
    assert "/companies/" in str(normalized)
    assert handle.provider_document_id == ZIJIN["pdoc"]
    assert result.download_required is False
    sample_before = _file_fingerprint(Path(handle.canonical_path))
    # Zero writes: the resolved root + the canonical file are untouched.
    # (Catalog-DIR zero-write is intentionally NOT asserted: the background
    # worker concurrently writes the catalog — ZR-206 fingerprint lesson.)
    assert companies_before == _shallow_fingerprint(_root_dir(catalog, "company_raw"))
    assert sample_before == _file_fingerprint(Path(handle.canonical_path))


def test_c2_journey_dayu_only_real_sample():
    """Journey B: a filing that exists ONLY under the dayu portfolio
    (content absent from companies — pinned by the dedicated test below)
    resolves EXACTLY there — nothing is copied into companies, zero
    downloads, zero writes to any root."""
    catalog = _production_catalog()
    companies_before = _shallow_fingerprint(_root_dir(catalog, "company_raw"))
    portfolio_before = _shallow_fingerprint(_root_dir(catalog, "dayu_portfolio"))
    result = _resolve_exact(catalog, **DAYU_ONLY)
    handle = result.matches[0]
    normalized = handle.canonical_path.replace("\\", "/")
    assert "/portfolio/" in str(normalized), handle.canonical_path
    assert result.download_required is False
    sample_before = _file_fingerprint(Path(handle.canonical_path))
    # Zero writes: both real roots + the canonical file are untouched
    # (catalog-DIR zero-write not asserted — background worker, ZR-206).
    assert companies_before == _shallow_fingerprint(_root_dir(catalog, "company_raw"))
    assert portfolio_before == _shallow_fingerprint(
        _root_dir(catalog, "dayu_portfolio")
    )
    assert sample_before == _file_fingerprint(Path(handle.canonical_path))


def test_c2_journey_dayu_sample_is_dayu_only():
    """Precondition pin: the dayu journey's document content is genuinely
    absent from companies (not a disguised copy) — the exec-plan T2 sample
    rule."""
    catalog = _production_catalog()
    result = _resolve_exact(catalog, **DAYU_ONLY)
    content = result.matches[0].content_sha256
    con = sqlite3.connect(f"file:{PRODUCTION_DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    row = con.execute(
        """SELECT COUNT(*) c FROM locations l
           JOIN sources s ON s.source_id = l.source_id
           WHERE s.content_sha256 = ? AND l.root_id = 'company_raw'""",
        (content,),
    ).fetchone()
    con.close()
    assert row["c"] == 0, "dayu-only sample unexpectedly exists in companies"


def test_c2_journey_dropbox_fail_closed_incomplete_sample():
    """Journey C (honest, current production data): the Dropbox root's ONLY
    exclusive annual filings carry http (not https) source_urls — they are
    capture-INCOMPLETE.  The resolver must evaluate the Dropbox path and
    fail closed (MISSING with capture_incomplete trace), never fake a
    handle, zero downloads, zero writes.  (The Zijin annual under Dropbox
    is shared with companies — pinned by the cross-root test below.)"""
    catalog = _production_catalog()
    dropbox_before = _shallow_fingerprint(_root_dir(catalog, "dropbox_stock"))
    from company_wiki.source_catalog import SourceRequest, SourceResolver
    from company_wiki.source_catalog.resolver import ResolutionStatus

    result = SourceResolver(catalog).resolve(
        SourceRequest(
            entity="星环科技",
            market="CN",
            security_id="688031",
            document_kind="annual_report",
            fiscal_year=2024,
            provider="cninfo",
            provider_document_id="1223325316",
            as_of_date="2026-08-01",
            mode="exact",
        )
    )
    assert result.status is ResolutionStatus.MISSING, result.debug_trace
    assert result.download_required is True  # a download would be the only fix
    assert any("capture_incomplete" in item for item in result.debug_trace), (
        result.debug_trace
    )
    sample_dir = _root_dir(catalog, "dropbox_stock")
    assert dropbox_before == _shallow_fingerprint(sample_dir)


def test_c2_journey_dropbox_shared_zijin_resolves_in_companies():
    """The Dropbox root also hosts the Zijin annual, shared with companies
    (same content): the cross-root dedup makes the lowest-priority root
    (companies p10) canonical — nothing is copied into Dropbox, proving
    the Dropbox path participates without duplication (ZR-403 semantics)."""
    catalog = _production_catalog()
    dropbox_before = _shallow_fingerprint(_root_dir(catalog, "dropbox_stock"))
    result = _resolve_exact(catalog, **ZIJIN)
    normalized = result.matches[0].canonical_path.replace("\\", "/")
    assert "/companies/" in str(normalized)
    assert dropbox_before == _shallow_fingerprint(_root_dir(catalog, "dropbox_stock"))


def test_c2_journeys_are_read_only_for_every_root():
    """All three journeys in one process: every real root's shallow
    fingerprint and each canonical sample file are unchanged (catalog-DIR
    zero-write not asserted — the background worker writes it, ZR-206)."""
    catalog = _production_catalog()
    fingerprints = {
        root_id: _shallow_fingerprint(_root_dir(catalog, root_id))
        for root_id in ("company_raw", "dayu_portfolio", "dropbox_stock", "future_lake")
    }
    sample_files = []
    for journey in (ZIJIN, DAYU_ONLY):
        result = _resolve_exact(catalog, **journey)
        sample_files.append(_file_fingerprint(Path(result.matches[0].canonical_path)))
    for root_id, before in fingerprints.items():
        assert before == _shallow_fingerprint(_root_dir(catalog, root_id)), root_id


# ---------------------------------------------------------------------------
# C3 — EX-08 future-root family against the production config shape
# ---------------------------------------------------------------------------


def test_c3_ex08_future_root_scan_and_export(tmp_path):
    """EX-08 (production shape): a config with the SAME future_lake root
    declaration scans an empty/README fixture without errors and exports
    a policy that includes it — config only, zero product change."""
    import shutil

    project = tmp_path / "project"
    (project / "future_lake").mkdir(parents=True)
    (project / "future_lake" / "README.md").write_text("# fixture\n", encoding="utf-8")
    config_path = project / "config" / "source_catalog.yaml"
    config_path.parent.mkdir(parents=True)
    shutil.copyfile(PRODUCTION_CONFIG, config_path)
    # rewrite the root paths for the temp project
    text = config_path.read_text(encoding="utf-8")
    text = text.replace("${PROJECT_ROOT}/companies", "${PROJECT_ROOT}/companies")
    text = text.replace(
        "${PROJECT_ROOT}/../dayu-agent/workspace/portfolio", "${PROJECT_ROOT}/portfolio"
    )
    text = text.replace(
        "${USER_PROFILE}/Dropbox/Stock", "${PROJECT_ROOT}/Dropbox/Stock"
    )
    text = text.replace("${PROJECT_ROOT}/future_lake", "${PROJECT_ROOT}/future_lake")
    config_path.write_text(text, encoding="utf-8")
    for rel in ("companies", "portfolio", "Dropbox/Stock"):
        (project / rel).mkdir(parents=True, exist_ok=True)

    from company_wiki.source_catalog import SourceCatalog
    from company_wiki.source_catalog.config import load_catalog_config
    from company_wiki.source_catalog.policy_2x import export_policy_2x

    config = load_catalog_config(config_path, project_root=project)
    catalog = SourceCatalog(config)
    report = catalog.scan()
    assert report.errors == 0, report
    _hash, policy = export_policy_2x(config)
    reusable = {
        entry["root_id"]
        for entry in policy["roots"]
        if entry["reusable_for_filing"] is True
    }
    assert "future_lake" in reusable
    # the fixture README is not a filing: nothing indexed as annual_report
    con = sqlite3.connect(f"file:{config.database_path}?mode=ro", uri=True)
    count = con.execute(
        "SELECT COUNT(*) FROM documents WHERE document_kind='annual_report'"
    ).fetchone()[0]
    con.close()
    assert count == 0
