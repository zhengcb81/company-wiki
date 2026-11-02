"""ZR-806 acceptance tests: real T2 three-root samples (stage G finale).

Runs on the REAL production catalog and source roots, READ-ONLY (T2 tier),
pinning the sample discipline the completion plan demands:

  C1  样本唯一/新鲜 — a fixed sample list (companies Zijin FY2025/FY2024,
      dayu 1548 HK FY2021, Dropbox StarLake FY2024 + one broker research
      PDF) with unique content hashes and filing dates not in the future;
      a missing sample FAILS the suite (AUD2-05: blocked, never silently
      swapped for an easier sample).
  C2  三 root resolve 只读旅程 — companies → REUSED_EXACT (no download);
      dayu → REUSED_EXACT (dayu-only content); Dropbox → MISSING
      fail-closed (http URLs are never faked into handles).  Root shallow
      fingerprints and catalog row counts are unchanged by the journeys.
  C3  artifact/mine/forecast 样本消费 — the Zijin FY2025/FY2024 raw
      `.source.json` contract (fiscal_year / entity / security_id /
      provider_document_id / content_sha256 == measured file hash /
      byte_size) is consumable by the revenue F2 chain (FY semantics,
      entity naming); the Dropbox StarLake FY2024 sidecar binds the same
      way; the broker PDF has no sidecar and stays a raw sample (honest).

Zero product code changes; zero downloads; zero writes to any production
root or the catalog (resolve-only + fingerprints).
"""

from __future__ import annotations

import datetime
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

from _rf_system_paths import RF_CODE_ROOT  # noqa: E402
ROOT = RF_CODE_ROOT
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

WIKI_ROOT = Path(r"C:\Users\郑曾波\Projects\company-wiki")
DAYU_ROOT = Path(r"C:\Users\郑曾波\Projects\dayu-agent\workspace\portfolio")
DROPBOX_ROOT = Path.home() / "Dropbox" / "Stock"

CATALOG_DB = WIKI_ROOT / ".source_catalog" / "catalog.sqlite3"
CATALOG_CONFIG = WIKI_ROOT / "config" / "source_catalog.yaml"

ZIJIN_FY2025 = WIKI_ROOT / "companies" / "紫金矿业" / "raw" / "financial_reports" / "annual" / (
    "2026-03-20_cninfo_1225023658_紫金矿业集团股份有限公司2025年年度报告.pdf"
)
ZIJIN_FY2024 = WIKI_ROOT / "companies" / "紫金矿业" / "raw" / "financial_reports" / "annual" / (
    "2025-03-21_cninfo_1222870413_紫金矿业集团股份有限公司2024年年报报告.pdf"
)
DAYU_1548_FY2021 = (
    DAYU_ROOT / "1548" / "filings"
    / "fil_cn_573daaffd805c1586f66b51e111bd15fce4406eb"
    / "fil_cn_573daaffd805c1586f66b51e111bd15fce4406eb.pdf"
)
STAR_2024_PDF = (
    DROPBOX_ROOT / "工业与信息化" / "软件与自动化控制" / "星环科技" / "星环科技：2024年年度报告.pdf"
)
STAR_2024_SOURCE = DROPBOX_ROOT / "工业与信息化" / "软件与自动化控制" / "星环科技" / (
    "星环科技：2024年年度报告.pdf.source.json"
)
BROKER_PDF = (
    DROPBOX_ROOT / "工业与信息化" / "软件与自动化控制" / "星环科技"
    / "20260109-东吴证券-计算机行业：NV Rubin新架构&Agent存储最强方向，GPU Native数据库【星环科技】.pdf"
)

# (label, path, sidecar/meta filing_date or None, declared sha or None)
SAMPLES = [
    ("companies-zijin-fy2025", ZIJIN_FY2025, "2026-03-20", "01819e1c7daad939d1779a8aa729f50f02151192e609cb28c2c405634a8f343d"),
    ("companies-zijin-fy2024", ZIJIN_FY2024, "2025-03-21", "004f733e709beea878229ae02b80a952c543129037fc940aaf01b77dfa977a89"),
    ("dayu-1548-fy2021", DAYU_1548_FY2021, "2022-04-25", None),
    ("dropbox-starlake-fy2024", STAR_2024_PDF, "2025-04-26", "eb965857b1e95a9cd6ccdaa3c1e324d4d8558c924d61e9300a12b8e222676124"),
    ("dropbox-broker-research", BROKER_PDF, "2026-01-09", None),
]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _shallow_fingerprint(directory: Path) -> str:
    digest = hashlib.sha256()
    for child in sorted(directory.iterdir()):
        digest.update(child.name.encode("utf-8"))
        try:
            stat = child.stat()
            digest.update(str(stat.st_size).encode())
            digest.update(str(stat.st_mtime_ns).encode())
        except OSError:
            digest.update(b"inaccessible")
    return digest.hexdigest()


def _catalog_row_counts() -> dict[str, int]:
    con = sqlite3.connect(f"file:{CATALOG_DB}?mode=ro", uri=True, timeout=30)
    try:
        counts = {}
        for table in ("documents", "sources", "locations"):
            counts[table] = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        return counts
    finally:
        con.close()


# ---------------------------------------------------------------------------
# C1 — samples unique & fresh (AUD2-05: missing sample = blocked)
# ---------------------------------------------------------------------------


def test_c1_samples_exist_and_unique_hashes():
    hashes = []
    for label, path, _filing, _declared in SAMPLES:
        assert path.is_file(), f"T2 sample missing ({label}) — blocked, never swap samples: {path}"
        hashes.append(_sha256_file(path))
    assert len(set(hashes)) == len(SAMPLES), "sample content hashes must be unique across roots"


def test_c1_filing_dates_not_in_future():
    today = datetime.date.today()
    for label, _path, filing, _declared in SAMPLES:
        parsed = datetime.date.fromisoformat(filing)
        assert parsed <= today, f"sample {label} filing date {filing} is in the future (stale policy)"


def test_c1_declared_hashes_match_files():
    for label, path, _filing, declared in SAMPLES:
        if declared is None:
            continue
        assert _sha256_file(path) == declared, f"sample {label} content hash drift"


# ---------------------------------------------------------------------------
# C2 — three-root resolve journeys, read-only, zero download, zero write
# ---------------------------------------------------------------------------


def _make_resolver():
    from company_wiki.source_catalog import SourceCatalog, SourceResolver
    from company_wiki.source_catalog.config import load_catalog_config

    config = load_catalog_config(CATALOG_CONFIG, project_root=WIKI_ROOT)
    return SourceResolver(SourceCatalog(config))


def test_c2_companies_zijin_journeys_reused_exact():
    from company_wiki.source_catalog import SourceRequest
    from company_wiki.source_catalog.resolver import ResolutionStatus

    resolver = _make_resolver()
    for fy, pdoc in ((2025, "1225023658"), (2024, "1222870413")):
        result = resolver.resolve(
            SourceRequest(
                entity="紫金矿业", market="CN", security_id="601899",
                document_kind="annual_report", fiscal_year=fy,
                provider="cninfo", provider_document_id=pdoc,
                as_of_date="2026-08-22", mode="exact",
            )
        )
        assert result.status is ResolutionStatus.REUSED_EXACT, result.debug_trace


def test_c2_dayu_journey_reused_exact():
    from company_wiki.source_catalog import SourceRequest
    from company_wiki.source_catalog.resolver import ResolutionStatus

    resolver = _make_resolver()
    result = resolver.resolve(
        SourceRequest(
            entity="金斯瑞生物科技", market="HK", security_id="1548",
            document_kind="annual_report", fiscal_year=2021,
            provider="hkexnews", provider_document_id="10225111",
            as_of_date="2026-08-22", mode="exact",
        )
    )
    assert result.status is ResolutionStatus.REUSED_EXACT, result.debug_trace


def test_c2_dropbox_fails_closed_no_fake_handle():
    from company_wiki.source_catalog import SourceRequest
    from company_wiki.source_catalog.resolver import ResolutionStatus

    resolver = _make_resolver()
    result = resolver.resolve(
        SourceRequest(
            entity="星环科技", market="CN", security_id="688031",
            document_kind="annual_report", fiscal_year=2024,
            provider="cninfo", provider_document_id="1223325316",
            as_of_date="2026-08-22", mode="exact",
        )
    )
    assert result.status is ResolutionStatus.MISSING, "http-only source must not be faked into a handle"


def test_c2_journeys_leave_roots_and_catalog_untouched():
    before_roots = {
        "companies": _shallow_fingerprint(WIKI_ROOT / "companies"),
        "dayu": _shallow_fingerprint(DAYU_ROOT),
        "dropbox": _shallow_fingerprint(DROPBOX_ROOT),
    }
    before_rows = _catalog_row_counts()
    test_c2_companies_zijin_journeys_reused_exact()
    test_c2_dayu_journey_reused_exact()
    test_c2_dropbox_fails_closed_no_fake_handle()
    assert _shallow_fingerprint(WIKI_ROOT / "companies") == before_roots["companies"]
    assert _shallow_fingerprint(DAYU_ROOT) == before_roots["dayu"]
    assert _shallow_fingerprint(DROPBOX_ROOT) == before_roots["dropbox"]
    assert _catalog_row_counts() == before_rows


# ---------------------------------------------------------------------------
# C3 — artifact/mine/forecast sample consumption
# ---------------------------------------------------------------------------


def _read_sidecar(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_c3_zijin_sidecar_contract_and_binding():
    for path, expected in (
        (ZIJIN_FY2025, {"fiscal_year": 2025, "entity": "紫金矿业", "pdoc": "1225023658", "sha": "01819e1c7daad939d1779a8aa729f50f02151192e609cb28c2c405634a8f343d", "size": 79925886}),
        (ZIJIN_FY2024, {"fiscal_year": 2024, "entity": "紫金矿业", "pdoc": "1222870413", "sha": "004f733e709beea878229ae02b80a952c543129037fc940aaf01b77dfa977a89", "size": 32100114}),
    ):
        sidecar = _read_sidecar(Path(str(path) + ".source.json"))
        assert sidecar["fiscal_year"] == expected["fiscal_year"]
        assert sidecar["company_name"] == expected["entity"]
        assert sidecar["security_id"] == "601899"
        assert sidecar["provider_document_id"] == expected["pdoc"]
        assert sidecar["content_sha256"] == _sha256_file(path) == expected["sha"]
        assert sidecar["byte_size"] == path.stat().st_size == expected["size"]
        # FY semantics: annual_report + fiscal_year N ⇒ period FY{N} consumable
        assert sidecar["fiscal_period"] == "FY"
        assert sidecar["document_kind"] == "annual_report"


def test_c3_starlake_sidecar_binds_dropbox_sample():
    sidecar = _read_sidecar(STAR_2024_SOURCE)
    assert sidecar["fiscal_year"] == 2024
    assert sidecar["security_id"] == "688031"
    assert sidecar["provider_document_id"] == "1223325316"
    assert sidecar["content_sha256"] == _sha256_file(STAR_2024_PDF)


def test_c3_broker_pdf_is_raw_sample_without_fake_sidecar():
    assert BROKER_PDF.is_file()
    assert not Path(str(BROKER_PDF) + ".source.json").is_file()
    assert BROKER_PDF.stat().st_size > 1_000_000
