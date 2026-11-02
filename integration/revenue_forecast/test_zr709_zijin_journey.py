"""ZR-709 acceptance tests: Zijin five-year forecast user journey (F2 confluence).

Runs the FULL user journey as one fixture chain, on real production entry
points, hermetic (T1 — temp roots only, no catalog writes, no network):

  J1  自动复用财报/研报，补齐依据可解释 — the REAL source_preparation
      subprocess chain reuses an annual report and a research communication
      from a fixture company-wiki root (zero downloads, explainable
      reuse_receipt); a missing document kind fails closed and becomes a
      tracked ProcessingDemand (never fabricated data).
  J2  mine/product 贡献与分部勾稽或诚实 gap — a five-year (FY2026-FY2030)
      mining forecast built FROM the F2 contract modules (MineYearOperation
      → commercial terms → ownership → elimination → reconciliation), with
      mine contributions reconciled to resource-model segment revenue; a
      business line without operating data is reported as an honest gap;
      schema 3.8 opt-in (operating_units embedded) runs the same engine
      path with zero numeric drift.
  J3  draft 可渲染、结果可重放 — prepare_forecast(draft) renders to
      Markdown without any publication registration; formal runs replay
      bit-identically and the snapshot round-trip validates.

Zero product code changes; zero company/mine hardcoding in production.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from _rf_system_paths import RF_CODE_ROOT  # noqa: E402
ROOT = RF_CODE_ROOT
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from asset_ownership import apply_ownership_share  # noqa: E402
from commercial_terms import calculate_net_revenue, validate_commercial_terms  # noqa: E402
from contracts.document import validate_document  # noqa: E402
from contracts.evidence import canonical_sha256  # noqa: E402
from internal_flow import eliminate_internal_revenue, validate_internal_flow  # noqa: E402
from mine_year_operation import (  # noqa: E402
    derive_saleable_volume,
    validate_mine_year_operation,
)
from reconciliation import fallback_segment_listing, gap_report, reconcile_layer  # noqa: E402
from revenue_backtest import create_snapshot, validate_snapshot  # noqa: E402
from revenue_forecast import prepare_forecast  # noqa: E402
from revenue_report import render_markdown  # noqa: E402
from schema_optin import convert_3_8_to_3_7  # noqa: E402
from test_data_contract import (  # noqa: E402
    apply_parameter_contract,
    finalize_contract,
    research_coverage,
)

YEARS = [2026, 2027, 2028, 2029, 2030]
PRICE_MULT = {"low": 0.85, "base": 1.0, "high": 1.2}
VOLUME_MULT = {"low": 0.9, "base": 1.0, "high": 1.08}
RAMP = [1.00, 1.05, 1.10, 1.12, 1.15]  # ramp-up across the five years

# Synthetic Zijin-shaped structure (test-only names; zero product hardcoding)
KAMOA_CHAIN = [
    [{"effective_date": "2015-05-01", "ownership_fraction": 0.6}],
    [{"effective_date": "2015-05-01", "ownership_fraction": 0.66}],
]  # effective group share 0.6 × 0.66 = 0.396
KAMOA_SHARE = 0.396
JULONG_SHARE = 1.0
ZIJINSHAN_SHARE = 1.0
BYPRODUCT_CREDIT = 350.0


def _operation(mine: str, scenario: str, year: int) -> dict:
    index = YEARS.index(year)
    shapes = {
        # mine: (volume, grade, recovery, payable, product)
        "kamoa_copper": (450.0, 2.8, 0.86, 0.965, "copper concentrate"),
        "julong_copper": (200.0, 0.55, 0.84, 0.95, "copper concentrate"),
        "zijinshan_gold": (8000.0, 0.9, 0.78, 0.99, "gold doré"),
    }
    volume, grade, recovery, payable, product = shapes[mine]
    return {
        "volume": volume * VOLUME_MULT[scenario] * RAMP[index],
        "grade": grade,
        "recovery": recovery,
        "payable": payable,
        "product": product,
        "period": f"FY{year}",
        "scenario": scenario,
    }


def _terms(mine: str, scenario: str, year: int) -> dict:
    prices = {
        "kamoa_copper": (9800.0, 0.035),
        "julong_copper": (71000.0, 0.03),
        "zijinshan_gold": (620.0, 0.02),
    }
    price, royalty = prices[mine]
    terms = {
        "price": {
            "value": price * PRICE_MULT[scenario],
            "source": "fixture price curve",
            "assumption": "analyst",
            "period": f"FY{year}",
        },
        "royalty_rate": {
            "value": royalty,
            "source": "fixture mining code",
            "assumption": "contract",
            "period": f"FY{year}",
        },
    }
    if mine == "zijinshan_gold":
        terms["byproduct_credit"] = {
            "value": BYPRODUCT_CREDIT,
            "source": "fixture silver credit",
            "assumption": "analyst",
            "period": f"FY{year}",
        }
    return terms


def _mine_contribution(
    mine: str, share: float, scenario: str, year: int
) -> tuple[float, float]:
    """(ownership-weighted saleable volume, weighted net revenue)."""
    operation = validate_mine_year_operation(_operation(mine, scenario, year))
    saleable = derive_saleable_volume(operation)
    net = calculate_net_revenue(
        saleable, validate_commercial_terms(_terms(mine, scenario, year))
    )
    return saleable * share, net["net"] * share


SEGMENT_MINES = {
    "copper": (("kamoa_copper", KAMOA_SHARE), ("julong_copper", JULONG_SHARE)),
    "gold": (("zijinshan_gold", ZIJINSHAN_SHARE),),
}


def _segment_volume_and_net(
    segment: str, scenario: str, year: int
) -> tuple[float, float]:
    volumes = []
    nets = []
    for mine, share in SEGMENT_MINES[segment]:
        saleable, net = _mine_contribution(mine, share, scenario, year)
        volumes.append(saleable)
        nets.append(net)
    return sum(volumes), sum(nets)


def _trading_value(scenario: str, year: int) -> float:
    base = {"low": 18.0, "base": 20.0, "high": 23.0}[scenario]
    growth = {"low": 1.04, "base": 1.06, "high": 1.09}[scenario]
    return base * growth ** (year - 2025)


def _add_driver(
    data: dict,
    parameter_id: str,
    value: float,
    dimension: str,
    scenario: str,
    year: int,
    definition: str,
) -> None:
    parameter = {
        "parameter_id": parameter_id,
        "kind": "analyst_assumption",
        "value": value,
        "unit": dimension,
        "period": f"FY{year}",
        "definition": definition,
        "scenario": scenario,
        "rationale": "Derived from validated operating units and commercial terms",
        "source_ids": ["filing"],
    }
    data["parameters"].append(parameter)
    apply_parameter_contract(data, parameter, dimension)


def _zijin_document() -> dict:
    """Five-year mining forecast document derived from the F2 contracts."""
    data = {
        "company_name": "Synthetic Zijin-Shaped Copper-Gold Group",
        "as_of_date": "2026-07-12",
        "currency": "USD",
        "unit": "million",
        "fiscal_year_end": "12-31",
        "base_year": 2025,
        "forecast_years": YEARS,
        "sources": [
            {
                "source_id": "filing",
                "source_type": "exchange_filing",
                "title": "FY2025 annual report",
                "publisher": "Test Exchange",
                "url": "https://www.example-filing.com/acme/2025",
                "published_date": "2026-03-01",
                "accessed_date": "2026-07-01",
                "page_or_section": "Revenue note",
            },
            {
                "source_id": "research",
                "source_type": "company_release",
                "title": "Q2 operations research communication",
                "publisher": "Company IR",
                "url": "https://www.example-filing.com/acme/q2-research",
                "published_date": "2026-06-15",
                "accessed_date": "2026-07-01",
                "page_or_section": "Operating outlook",
            },
        ],
        "parameters": [
            {
                "parameter_id": "reported_total",
                "kind": "reported_fact",
                "value": 320,
                "unit": "USD million",
                "period": "FY2025",
                "definition": "reported total revenue",
                "source_ids": ["filing"],
            },
            {
                "parameter_id": "copper_base",
                "kind": "reported_fact",
                "value": 210,
                "unit": "USD million",
                "period": "FY2025",
                "definition": "copper segment external revenue",
                "source_ids": ["filing"],
            },
            {
                "parameter_id": "gold_base",
                "kind": "reported_fact",
                "value": 90,
                "unit": "USD million",
                "period": "FY2025",
                "definition": "gold segment external revenue",
                "source_ids": ["filing"],
            },
            {
                "parameter_id": "trading_base",
                "kind": "reported_fact",
                "value": 20,
                "unit": "USD million",
                "period": "FY2025",
                "definition": "trading and other external revenue",
                "source_ids": ["filing"],
            },
        ],
        "segments": [
            {"name": "copper", "base_revenue_parameter_id": "copper_base"},
            {"name": "gold", "base_revenue_parameter_id": "gold_base"},
            {"name": "trading_and_other", "base_revenue_parameter_id": "trading_base"},
        ],
        "reported_total_revenue_parameter_id": "reported_total",
        "base_adjustment_parameter_ids": [],
        "historical_revenue": [
            {"year": 2024, "value": 300, "source_ids": ["filing"]},
            {"year": 2025, "value": 320, "source_ids": ["filing"]},
        ],
        "research_coverage": research_coverage(
            ["reported_total", "copper_base", "gold_base", "trading_base"]
        ),
    }
    for parameter in data["parameters"]:
        apply_parameter_contract(data, parameter, "revenue")

    driver_ids: dict[str, dict[str, list[str]]] = {}
    for segment in ("copper", "gold"):
        driver_ids[segment] = {}
        for scenario in ("low", "base", "high"):
            volume_ids = []
            price_ids = []
            for year in YEARS:
                seg_volume, seg_net = _segment_volume_and_net(segment, scenario, year)
                other = BYPRODUCT_CREDIT if segment == "gold" else 0.0
                realized_price = (seg_net - other) / seg_volume
                volume_id = f"{segment}_{scenario}_{year}_saleable"
                price_id = f"{segment}_{scenario}_{year}_price"
                _add_driver(
                    data,
                    volume_id,
                    seg_volume,
                    "quantity",
                    scenario,
                    year,
                    f"{segment} ownership-weighted saleable volume",
                )
                _add_driver(
                    data,
                    price_id,
                    realized_price,
                    "revenue_per_unit",
                    scenario,
                    year,
                    f"{segment} blended realized net price per unit",
                )
                volume_ids.append(volume_id)
                price_ids.append(price_id)
            drivers = {
                "saleable_volume": volume_ids,
                "realized_price": price_ids,
            }
            if segment == "gold":
                other_ids = []
                for year in YEARS:
                    other_id = f"gold_{scenario}_{year}_byproduct"
                    _add_driver(
                        data,
                        other_id,
                        BYPRODUCT_CREDIT,
                        "revenue",
                        scenario,
                        year,
                        "silver byproduct credit (flat, never double counted)",
                    )
                    other_ids.append(other_id)
                drivers["other_revenue"] = other_ids
            driver_ids[segment][scenario] = drivers

    trading_ids: dict[str, list[str]] = {}
    for scenario in ("low", "base", "high"):
        ids = []
        for year in YEARS:
            parameter_id = f"trading_{scenario}_{year}_rev"
            _add_driver(
                data,
                parameter_id,
                _trading_value(scenario, year),
                "revenue",
                scenario,
                year,
                "trading and other modeled revenue",
            )
            ids.append(parameter_id)
        trading_ids[scenario] = ids

    for segment in data["segments"]:
        segment["recognition"] = {
            "mode": "modeled_as_recognized",
            "timing": "point_in_time",
            "trigger": "shipment/delivery",
            "presentation": "gross",
        }
        segment["scenarios"] = {}
        for scenario in ("low", "base", "high"):
            if segment["name"] == "trading_and_other":
                model = "direct_revenue"
                drivers = {"revenue": trading_ids[scenario]}
            else:
                model = "resource"
                drivers = driver_ids[segment["name"]][scenario]
            segment["scenarios"][scenario] = {
                "model": model,
                "driver_parameter_ids": drivers,
                "rationale": f"{scenario} mining resource path from F2 contracts",
            }

    base_driver_ids = [
        parameter_id
        for segment in data["segments"]
        for ids in segment["scenarios"]["base"]["driver_parameter_ids"].values()
        for parameter_id in ids
    ]
    growth_record = next(
        item
        for item in data["research_coverage"]
        if item["dimension"] == "growth_curve"
    )
    growth_record.update(
        {
            "status": "modeled_driver",
            "conclusion": "Resource-model paths generate the five-year synthetic forecast",
            "revenue_mechanism": "operating units × commercial terms aggregate by segment",
            "parameter_ids": base_driver_ids,
            "source_ids": ["filing", "research"],
        }
    )
    growth_record.pop("rationale", None)
    return finalize_contract(data)


def _all_operating_units() -> list[dict]:
    return [
        _operation(mine, scenario, year)
        for scenario in ("low", "base", "high")
        for year in YEARS
        for mine in ("kamoa_copper", "julong_copper", "zijinshan_gold")
    ]


# ---------------------------------------------------------------------------
# J1 — 自动复用财报/研报，补齐依据可解释
# ---------------------------------------------------------------------------


def _document_row(
    doc_id: str,
    source_id: str,
    kind: str,
    title: str,
    published: str,
    pdf_path: Path,
    pdf_sha: str,
    size: int,
) -> tuple:
    meta = json.dumps(
        {
            "acquisition": {
                "form_type": kind,
                "fiscal_year": 2025,
                "source_url": f"https://example-filing.com/acme/{kind}",
                "provider": "example-filing",
                "market": "US",
                "security_id": "SEC-US",
                # P5-RF: the v2 manifest requires explicit tz-aware capture
                # fields (same contract as tests/e2e_support/isolated_lake)
                "source_title": title,
                "published_date": published,
                "retrieved_at": published + "T00:00:00Z",
            },
            # RF-E2E-ADAPT: the review receipt is NOT hand-shaped here —
            # _journey_wiki_root writes it through CW's fail-closed writer
            # (state_domain + payload/dual binding; the promoted 5d72529
            # contract), so the chain's reader accepts it.
        }
    )
    location_meta = json.dumps({"acquisition": {}})
    manifest = json.dumps(
        {
            "content_sha256": pdf_sha,
            "retrieved_at": published + "T00:00:00Z",
            "collector_name": "fixture",
            "collector_version": "1.0.0",
            "mime_type": "application/pdf",
            "byte_size": size,
        }
    )
    return (
        (
            doc_id,
            source_id,
            title,
            "active",
            "file",
            kind,
            published,
            10,
            meta,
            "2026-01-01",
            "2026-01-01",
        ),
        (
            "l" + doc_id[1:],
            "company_raw",
            # P5-RF: the v2 reader resolves root/relative_path — the row must
            # carry the path RELATIVE to the companies root, not a bare name
            str(pdf_path.relative_to(pdf_path.parents[4])).replace("\\", "/"),
            str(pdf_path),
            source_id,
            doc_id,
            "original_primary",
            "active",
            size,
            0,
            "2026-01-01",
            manifest,
            location_meta,
            None,
        ),
    )


def _journey_wiki_root(tmp: Path) -> Path:
    """Fixture company-wiki root with TWO active documents: the FY2025
    annual report and a research communication (both reusable, reviewed)."""
    # RF-E2E-ADAPT: receipts go through CW's fail-closed writer (state_domain
    # + payload/dual binding — the promoted 5d72529 contract), same call shape
    # as CW tests/unit/test_prompt_injection_guard.py; the chain's reader
    # fail-closes a hand-shaped pre-contract dict as not_reviewed.
    sys.path.insert(0, str(ROOT.parent / "company-wiki" / "src"))
    from company_wiki.source_catalog.prompt_injection import (
        record_prompt_injection_review,
    )
    from company_wiki.source_catalog.prompt_injection_guard import RULESET_HASH

    catalog = tmp / ".source_catalog" / "catalog.sqlite3"
    catalog.parent.mkdir(parents=True)
    companies = tmp / "companies" / "Acme" / "raw" / "financial_reports"
    companies.mkdir(parents=True)

    bodies = {}
    for name, body in (
        ("annual/2025_Acme_annual.pdf", b"%PDF-1.4 acme-annual" * 10),
        ("research/2026_Acme_q2_research.pdf", b"%PDF-1.4 acme-research" * 10),
    ):
        path = companies / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        bodies[str(path)] = (hashlib.sha256(body).hexdigest(), len(body))

    con = sqlite3.connect(catalog)
    con.execute(
        "CREATE TABLE roots (root_id TEXT, path TEXT, kind TEXT, "
        "priority INTEGER, last_scan_run TEXT, last_scanned_at TEXT)"
    )
    con.execute(
        "INSERT INTO roots VALUES ('company_raw', ?, 'company_raw', 10, '', '')",
        (str(tmp / "companies"),),
    )
    con.execute(
        "CREATE TABLE sources (source_id TEXT PRIMARY KEY, "
        "content_sha256 TEXT, byte_size INTEGER, mime_type TEXT, "
        "first_seen_at TEXT)"
    )
    con.execute(
        "CREATE TABLE documents (document_id TEXT PRIMARY KEY, "
        "primary_source_id TEXT, title TEXT, source_status TEXT, "
        "source_type TEXT, document_kind TEXT, published_date TEXT, "
        "metadata_priority INTEGER, metadata_json TEXT, "
        "first_seen_at TEXT, last_seen_at TEXT)"
    )
    con.execute(
        "CREATE TABLE locations (location_id TEXT PRIMARY KEY, "
        "root_id TEXT, relative_path TEXT, absolute_path TEXT, "
        "source_id TEXT, document_id TEXT, role TEXT, "
        "location_status TEXT, observed_size INTEGER, "
        "observed_mtime_ns INTEGER, last_seen_run TEXT, "
        "manifest_json TEXT, metadata_json TEXT, error TEXT)"
    )
    con.execute(
        "CREATE TABLE artifacts (artifact_id TEXT, document_id TEXT, "
        "artifact_role TEXT, source_id TEXT, path TEXT, "
        "content_sha256 TEXT, byte_size INTEGER, mime_type TEXT, "
        "generator_name TEXT, generator_version TEXT, status TEXT, "
        "error TEXT, schema_version TEXT, source_sha256 TEXT, "
        "created_at TEXT)"
    )
    con.execute(
        "CREATE TABLE entities (entity_id TEXT PRIMARY KEY, name TEXT, entity_kind TEXT)"
    )
    con.execute(
        "CREATE TABLE document_entities (document_id TEXT, entity_id TEXT, "
        "confidence REAL, method TEXT)"
    )
    con.execute("INSERT INTO entities VALUES ('ent-acme', 'Acme', 'company')")
    con.execute("CREATE TABLE catalog_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    con.execute("INSERT INTO catalog_meta VALUES ('schema_version', '1.2.0')")
    con.execute(
        "CREATE TABLE remediation_proposals (proposal_id TEXT PRIMARY KEY, "
        "source_id TEXT, status TEXT, proposed_by TEXT, created_at TEXT)"
    )
    con.execute(
        "CREATE TABLE producer_events (event_id TEXT PRIMARY KEY, "
        "document_id TEXT, artifact_role TEXT, producer_name TEXT, "
        "producer_version TEXT, event_type TEXT, created_at TEXT)"
    )
    con.execute(
        "CREATE TABLE source_metadata_assertions (assertion_id TEXT PRIMARY KEY, "
        "source_id TEXT, document_id TEXT, content_sha256 TEXT, evidence_basis TEXT, "
        "evidence_json TEXT, decision TEXT, created_at TEXT, created_by TEXT, "
        "schema_version TEXT, adapter_id TEXT, adapter_version TEXT, "
        "normalization_status TEXT, visibility_state TEXT, fiscal_year INTEGER, "
        "fiscal_period TEXT, document_kind TEXT, form_type TEXT, provider TEXT, "
        "provider_document_id TEXT, source_url TEXT, security_id TEXT, market TEXT)"
    )

    specs = [
        (
            "d1",
            "s1",
            "annual_report",
            "Acme FY2025 annual report",
            "2026-04-15",
            "annual/2025_Acme_annual.pdf",
        ),
        (
            "d2",
            "s2",
            "company_release",
            "Acme Q2 research communication",
            "2026-06-15",
            "research/2026_Acme_q2_research.pdf",
        ),
    ]
    for doc_id, source_id, kind, title, published, rel in specs:
        pdf_path = companies / rel
        pdf_sha, size = bodies[str(pdf_path)]
        con.execute(
            "INSERT INTO sources VALUES (?, ?, ?, 'application/pdf', '2026-01-01')",
            (source_id, pdf_sha, size),
        )
        doc_row, loc_row = _document_row(
            doc_id, source_id, kind, title, published, pdf_path, pdf_sha, size
        )
        con.execute(
            "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", doc_row
        )
        # FC-905 policy gate: reviewed fixture document via the CW writer —
        # evidence payload bound to the reviewed source bytes (RF-E2E-ADAPT).
        record_prompt_injection_review(
            con, doc_id, status="not_detected", reviewer="fixture-reviewer",
            evidence_sha256=pdf_sha, now="2026-01-01T00:00:00Z",
            source_sha256=pdf_sha, policy_hash=RULESET_HASH,
            evidence_payload=pdf_path.read_bytes(),
        )
        con.execute(
            "INSERT INTO locations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            loc_row,
        )
        con.execute(
            "INSERT INTO document_entities VALUES (?, 'ent-acme', 1.0, 'fixture')",
            (doc_id,),
        )
    con.commit()
    con.close()

    master = tmp / ".source_catalog" / "security_master"
    master.mkdir(parents=True)
    for market in ("CN", "US", "HK"):
        (master / f"{market.lower()}.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "market": market,
                    "retrieved_at": "2026-01-01",
                    "sources": ["fixture"],
                    "record_count": 1,
                    "records": [
                        {
                            "schema_version": "1.0",
                            "canonical_name": "Acme Corp",
                            "market": market,
                            "exchange": "TEST",
                            "ticker": "ACME",
                            "security_id": f"SEC-{market}",
                            "aliases": [],
                            "active": True,
                            "source_name": "fixture",
                            "source_url": "https://x",
                            "source_record_id": f"rec-{market}",
                            "identifiers": {},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
    (tmp / "config").mkdir()
    (tmp / "config" / "source_catalog.yaml").write_text(
        "\n".join(
            [
                "schema_version: '1.0'",
                "catalog_dir: " + str(tmp / ".source_catalog"),
                "roots:",
                "  - root_id: company_raw",
                "    path: " + str(tmp / "companies"),
                "    kind: company_raw",
            ]
        ),
        encoding="utf-8",
    )
    return tmp


def _prepare(tmp_path: Path, wiki: Path, document_kind: str):
    filing_config = wiki / "filing_config.json"
    filing_config.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "company_wiki_root": str(wiki),
            }
        ),
        encoding="utf-8",
    )
    request = {
        "schema_version": "1.2",
        "company_query": "Acme",
        "market": "US",
        "document_kind": document_kind,
        "as_of_date": "2026-12-31",
        "fiscal_year": 2025,
    }
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "source_preparation.py"),
            "--company-wiki-config",
            str(filing_config),
            "--company-wiki-catalog-config",
            str(wiki / "config" / "source_catalog.yaml"),
        ],
        input=json.dumps(request),
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=300,
        check=False,
    )


def test_j1_reuses_filing_and_research_with_explainable_receipt(tmp_path):
    wiki = _journey_wiki_root(tmp_path)
    kinds = {"annual_report": "regulatory_filing", "company_release": "company_release"}
    seen_sources = set()
    for document_kind, expected_type in kinds.items():
        proc = _prepare(tmp_path, wiki, document_kind)
        assert proc.returncode == 0, f"{document_kind}: {proc.stderr}"
        record = json.loads(proc.stdout)
        assert record["source_type"] == expected_type
        seen_sources.add(record["source_id"])
        receipt = record["reuse_receipt"]
        # 补齐依据可解释：reuse provenance is fully explicit, zero downloads
        assert receipt["download_calls"] == 0
        # P5-RF: the v2 route schedules no derived recompute and never reads
        # derived bodies; parser/LLM stay honest-None without real usage
        assert receipt["parser_calls"] is None
        assert receipt["llm_calls"] is None
        assert receipt["outcome"] == "reused_existing"
        # upstream-published policy identity is passed through verbatim —
        # a fixture root without a policy document honestly reports None
        # (never fabricated); production roots embed the exported hash.
        assert "policy_hash" in receipt
        assert receipt["artifact_read"] == [], receipt
        assert receipt["producer_events"] == [], receipt
        assert record["capture"]["prompt_injection_status"] == "not_detected"
    assert len(seen_sources) == 2  # two distinct reused sources, no fabrication


def test_j1_missing_document_fails_closed_into_tracked_demand(tmp_path):
    wiki = _journey_wiki_root(tmp_path)
    proc = _prepare(tmp_path, wiki, "earnings_transcript")
    # fail closed: no handle, no fabricated record (CLI maps RuntimeError → 3)
    assert proc.returncode == 3, proc.stdout + proc.stderr
    payload = json.loads(proc.stderr.strip().splitlines()[-1])
    assert payload["error_code"] == "upstream"

    # 补齐路径 = 显式 ProcessingDemand（claim → heartbeat → complete），
    # 缺口被跟踪而不是用编造数据填补。历史队列 fixture（不再由 prepare_source 生产创建）
    # 的提交接线已由 ZR-701 C4 钉住；这里用全新本地队列验证租约语义，
    # 不触碰进程级共享队列（保持测试顺序无关）。
    from tools.legacy import processing_demand  # noqa: PLC0415

    queue = processing_demand.DemandQueue(
        lease_seconds=10.0, max_attempts=2, backoff_base=5.0
    )
    demand = queue.enqueue(
        key="acme-fy2025-earnings_transcript", kind="source_preparation", now=0.0
    )
    claimed = queue.claim(owner="journey-worker", now=1.0)
    assert claimed.demand_id == demand.demand_id
    assert claimed.key == "acme-fy2025-earnings_transcript"
    heartbeated = queue.heartbeat(
        demand_id=claimed.demand_id, owner="journey-worker", now=5.0
    )
    assert heartbeated.status == "running"
    completed = queue.complete(
        demand_id=heartbeated.demand_id, owner="journey-worker", now=6.0
    )
    assert completed.status == "completed"


# ---------------------------------------------------------------------------
# J2 — mine/product 贡献与分部勾稽或诚实 gap（五年）
# ---------------------------------------------------------------------------


@pytest.fixture(name="registry")
def _registry(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "REVENUE_PUBLICATION_REGISTRY", str(tmp_path / "pub" / "publications.jsonl")
    )
    return tmp_path / "pub" / "publications.jsonl"


def test_j2_five_year_mine_contributions_reconcile_to_segments(registry):
    document = _zijin_document()
    result = prepare_forecast(document, mode="formal")
    segments = {segment["name"]: segment for segment in result["segments"]}
    for segment_name in SEGMENT_MINES:
        recognized = segments[segment_name]["scenarios"]["base"]["recognized_revenue"]
        for year in YEARS:
            _, expected_net = _segment_volume_and_net(segment_name, "base", year)
            verdict = reconcile_layer(expected_net, recognized[str(year)])
            assert verdict["status"] == "reconciled_modeled", (
                f"{segment_name}/{year}: {verdict}"
            )
    # company level closes across all three segments
    consolidated = result["consolidated_forecast"]["base"]["annual_revenue"]
    for year in YEARS:
        parts = sum(
            segments[name]["scenarios"]["base"]["recognized_revenue"][str(year)]
            for name in ("copper", "gold", "trading_and_other")
        )
        assert (
            reconcile_layer(parts, consolidated[str(year)])["status"]
            == "reconciled_modeled"
        )


def test_j2_kamoa_equity_chain_and_internal_flow_never_double_count():
    document = _zijin_document()
    result = prepare_forecast(document, mode="formal")
    copper = next(s for s in result["segments"] if s["name"] == "copper")
    base_2026 = copper["scenarios"]["base"]["recognized_revenue"]["2026"]

    # equity chain: group keeps only its effective share of Kamoa…
    share = apply_ownership_share(
        {"FY2026": 100.0},
        "one_hundred_percent",
        KAMOA_CHAIN,
        {"FY2026": ("2026-01-01", "2026-12-31")},
    )["FY2026"]
    assert share == pytest.approx(39.6)

    # …and internal smelter flows are eliminated once, never double counted.
    flow = validate_internal_flow(
        {
            "flow_id": "concentrate-to-internal-smelter",
            "source": "upstream_mines",
            "destination": "internal_smelter",
            "product": "copper concentrate",
            "volume": 50.0,
            "transfer_price": 9000.0,
            "period": "FY2026",
            "scenario": "base",
        }
    )
    eliminated = eliminate_internal_revenue(base_2026, [flow])
    assert eliminated["net"] == pytest.approx(base_2026)


def test_j2_uncovered_business_is_honest_gap_not_fabricated_revenue(registry):
    document = _zijin_document()
    result = prepare_forecast(document, mode="formal")
    segments = {segment["name"]: segment for segment in result["segments"]}
    consolidated_2026 = result["consolidated_forecast"]["base"]["annual_revenue"][
        "2026"
    ]

    contributions = {}
    for segment_name in SEGMENT_MINES:
        _, net = _segment_volume_and_net(segment_name, "base", 2026)
        contributions[segment_name] = net
    contributions["trading_and_other"] = segments["trading_and_other"]["scenarios"][
        "base"
    ]["recognized_revenue"]["2026"]

    # disclosed group total includes an unmodeled silver business (+120):
    # the difference MUST surface as an explicit gap, never as revenue.
    disclosed_with_silver = consolidated_2026 + 120.0
    report = gap_report(contributions, disclosed_with_silver)
    assert report["status"] == "gap"
    assert report["difference"] == pytest.approx(-120.0)

    listing = fallback_segment_listing(contributions, disclosed_with_silver)
    assert listing["closed"] is False
    assert listing["gap"] == pytest.approx(120.0)
    # without the silver residual everything closes
    closed = fallback_segment_listing(contributions, consolidated_2026)
    assert closed["closed"] is True


def test_j2_schema_38_operating_units_embedded_zero_numeric_drift(registry):
    document = _zijin_document()
    baseline = prepare_forecast(document, mode="formal")

    optin = copy.deepcopy(document)
    optin["schema_version"] = "3.8"
    optin["operating_units"] = _all_operating_units()
    validate_document(optin)  # seven-field contract enforced on every unit

    result38 = prepare_forecast(optin, mode="formal")
    assert result38["schema_version"] == "3.8"
    for segment37, segment38 in zip(baseline["segments"], result38["segments"]):
        for scenario in ("low", "base", "high"):
            expected = segment37["scenarios"][scenario]["recognized_revenue"]
            actual = segment38["scenarios"][scenario]["recognized_revenue"]
            for year in YEARS:
                assert actual[str(year)] == pytest.approx(
                    expected[str(year)], rel=1e-12
                )

    # converter round-trip: 3.8 → 3.7 strips only the opt-in vocabulary
    stripped = convert_3_8_to_3_7(optin)
    assert canonical_sha256(stripped) == canonical_sha256(document)


# ---------------------------------------------------------------------------
# J3 — draft 可渲染、结果可重放
# ---------------------------------------------------------------------------


def test_j3_draft_is_renderable_and_registers_nothing(registry):
    document = _zijin_document()
    draft = prepare_forecast(document, mode="draft")
    markdown = render_markdown(draft)
    assert "Synthetic Zijin-Shaped Copper-Gold Group" in markdown
    assert len(markdown) > 500
    assert draft["publication_receipt"]["formal_output_mode"] == "draft"
    assert draft["publication_receipt"]["gate_ids"] == []
    # draft never touches the publication registry
    assert not registry.exists()


def test_j3_formal_results_replay_bit_identically(registry):
    first = prepare_forecast(_zijin_document(), mode="formal")
    second = prepare_forecast(_zijin_document(), mode="formal")
    assert first == second
    assert first["result_sha256"] == second["result_sha256"]

    import publication_registry  # noqa: PLC0415

    entries = publication_registry._read_entries()
    journey = [e for e in entries if e.get("input_sha256") == first["input_sha256"]]
    assert len(journey) >= 2
    assert {e["result_sha256"] for e in journey} == {first["result_sha256"]}
    assert all(e["validation_status"] == "validated" for e in journey)


def test_j3_snapshot_round_trip_replays(registry):
    document = _zijin_document()
    snapshot = create_snapshot(copy.deepcopy(document), "zr709-journey-v1")
    validate_snapshot(snapshot)  # embedded input re-validates strongly
    replayed = create_snapshot(copy.deepcopy(document), "zr709-journey-v1")
    assert snapshot["snapshot_id"] == replayed["snapshot_id"]


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
