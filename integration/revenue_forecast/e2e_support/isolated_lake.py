"""FC-1001: unified isolated-lake fixture for the three-root E2E matrix.

One temp directory that looks like the REAL three-root production layout
(companies + dayu portfolio + Dropbox) with sidecars, identity snapshots,
v2 processed artifacts (schema_version COLUMN + metadata, per FC-906-d),
producer_events journal rows, and corruption variants.  Everything is
relative to ``tmp_path`` — no real paths leak into the manifest, no network,
no external writes; Windows/Linux reproducible (pathlib only).

Consumers (company-wiki resolver tests, filing-fetch, revenue E2E) reach the
same layout via sys.path — the pattern test_dropbox_full_chain_fc505.py uses.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

ARTIFACT_SCHEMA_VERSION = "1.0"

# --- deterministic fixture content (same seed -> same bytes) ---


def _body(seed: str) -> bytes:
    return b"%PDF-1.4 fake filing " + seed.encode() + b"\n"


def _sidecar(
    seed: str,
    *,
    market: str,
    security: str,
    pdoc: str,
    fy: int,
    kind: str,
    body_sha: str,
    provider: str = "cninfo",
    title: str | None = None,
) -> dict:
    return {
        "schema_version": "1.0",
        "canonical_entity_id": f"ent-{security}",
        "display_name": title or f"Acme {security}",
        "market": market,
        "security_id": security,
        "document_kind": kind,
        "fiscal_year": fy,
        "period_end": f"{fy}-12-31",
        "filing_date": f"{fy + 1}-02-20",
        "published_date": f"{fy + 1}-02-20",
        "retrieved_at": f"{fy + 1}-02-20T00:00:00Z",
        "form_type": kind,
        "provider": provider,
        "provider_document_id": pdoc,
        "source_url": (f"https://offline-cdn.fixtures.invalid/{security}/{fy}"),
        "content_sha256": body_sha,
        "source_title": title or f"Acme {security} {fy} {kind}",
        "_seed": seed,
    }


@dataclass
class LakeEntry:
    """One document in the lake: root-relative files + catalog identity."""

    rel_path: str  # root-relative pdf path (POSIX)
    sidecar_rel: str | None
    body_sha: str
    market: str
    security: str
    pdoc: str
    fy: int
    kind: str
    root_id: str
    role: str = "original_primary"
    location_status: str = "active"


@dataclass
class IsolatedLakeManifest:
    entries: list[LakeEntry] = field(default_factory=list)
    catalog_path: Path | None = None
    derived_root: Path | None = None

    def manifest_hash(self) -> str:
        """Deterministic hash over relative paths + content shas (sorted)."""
        payload = "\n".join(
            sorted(f"{e.root_id}|{e.rel_path}|{e.body_sha}" for e in self.entries)
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def relative_manifest(self) -> list[str]:
        """All paths, root-relative only (never absolute)."""
        out = []
        for e in self.entries:
            out.append(f"{e.root_id}:{e.rel_path}")
            if e.sidecar_rel:
                out.append(f"{e.root_id}:{e.sidecar_rel}")
        return sorted(out)


class IsolatedLake:
    """Builds the three-root fixture and returns a manifest + catalog."""

    def __init__(self, tmp_path: Path, *, seed: str = "fc1001"):
        self.tmp = tmp_path
        self.seed = seed
        self.lake = tmp_path / "lake"
        self.wiki_root = self.lake / "project"
        self.companies = self.wiki_root / "companies"
        self.portfolio = self.lake / "portfolio"
        self.dropbox = self.lake / "Dropbox" / "Stock"
        self.entries: list[LakeEntry] = []

    # --- layout ---

    def _add_companies(self) -> None:
        seed = self.seed + ":zijin"
        body = _body(seed)
        raw = self.companies / "紫金矿业" / "raw" / "financial_reports" / "annual"
        raw.mkdir(parents=True)
        pdf = raw / "紫金矿业2025年年报.pdf"
        pdf.write_bytes(body)
        side = raw / "紫金矿业2025年年报.pdf.source.json"
        side.write_text(
            json.dumps(
                _sidecar(
                    seed,
                    market="CN",
                    security="601899",
                    pdoc="1225023658",
                    fy=2025,
                    kind="annual_report",
                    body_sha=hashlib.sha256(body).hexdigest(),
                    title="紫金矿业集团股份有限公司",
                ),
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self.entries.append(
            LakeEntry(
                rel_path="紫金矿业/raw/financial_reports/annual/紫金矿业2025年年报.pdf",
                sidecar_rel="紫金矿业/raw/financial_reports/annual/紫金矿业2025年年报.pdf.source.json",
                body_sha=hashlib.sha256(body).hexdigest(),
                market="CN",
                security="601899",
                pdoc="1225023658",
                fy=2025,
                kind="annual_report",
                root_id="company_raw",
            )
        )

    def _add_dayu(self) -> None:
        seed = self.seed + ":dayu"
        body = _body(seed)
        group = self.portfolio / "601899" / "filings" / "fil_cn_fc1001"
        group.mkdir(parents=True)
        (group / "fil_cn_fc1001.pdf").write_bytes(body)
        (group / "meta.json").write_text(
            json.dumps(
                {
                    "document_id": "fil_cn_fc1001",
                    "ticker": "601899",
                    "form_type": "annual_report",
                    "fiscal_year": 2024,
                    "fiscal_period": "FY",
                    "filing_date": "2025-02-20",
                    "source_provider": "cninfo",
                    "source_id": "1224023657",
                    "source_url": "https://provider.example/601899/2024",
                    "source_language": "zh",
                    "source_title": "紫金矿业 2024",
                    "amended": False,
                    "ingest_complete": True,
                    "primary_document": "fil_cn_fc1001.pdf",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (self.portfolio / "601899" / "meta.json").write_text(
            json.dumps({"ticker": "601899", "market": "CN"}, ensure_ascii=False),
            encoding="utf-8",
        )
        self.entries.append(
            LakeEntry(
                rel_path="601899/filings/fil_cn_fc1001/fil_cn_fc1001.pdf",
                sidecar_rel="601899/filings/fil_cn_fc1001/meta.json",
                body_sha=hashlib.sha256(body).hexdigest(),
                market="CN",
                security="601899",
                pdoc="1224023657",
                fy=2024,
                kind="annual_report",
                root_id="dayu_portfolio",
            )
        )

    def _add_dropbox(self) -> None:
        seed = self.seed + ":pingan"
        body = _body(seed)
        raw = self.dropbox / "金融" / "保险" / "中国平安"
        raw.mkdir(parents=True)
        pdf = raw / "中国平安2020年中期报告.PDF"
        pdf.write_bytes(body)
        side = raw / "中国平安2020年中期报告.PDF.source.json"
        side.write_text(
            json.dumps(
                _sidecar(
                    seed,
                    market="CN",
                    security="601318",
                    pdoc="1223023656",
                    fy=2020,
                    kind="semi_annual_report",
                    body_sha=hashlib.sha256(body).hexdigest(),
                    title="中国平安",
                ),
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self.entries.append(
            LakeEntry(
                rel_path="金融/保险/中国平安/中国平安2020年中期报告.PDF",
                sidecar_rel="金融/保险/中国平安/中国平安2020年中期报告.PDF.source.json",
                body_sha=hashlib.sha256(body).hexdigest(),
                market="CN",
                security="601318",
                pdoc="1223023656",
                fy=2020,
                kind="semi_annual_report",
                root_id="dropbox_stock",
            )
        )

    # --- catalog + v2 artifacts ---

    def _catalog(self) -> "object":
        from company_wiki.source_catalog import CatalogConfig, SourceCatalog

        project = self.lake / "project"
        catalog = SourceCatalog(
            CatalogConfig(
                project_root=project,
                catalog_dir=project / ".source_catalog",
                reusable_root_kinds=("company_raw", "dayu_portfolio", "directory"),
                roots=(
                    RootSpecFactory.company(self.companies),
                    RootSpecFactory.dayu(self.portfolio),
                    RootSpecFactory.dropbox(self.dropbox),
                ),
            )
        )
        return catalog

    def build(self) -> IsolatedLakeManifest:
        """Create layout + scan + preset v2 artifacts; return manifest."""
        self._add_companies()
        self._add_dayu()
        self._add_dropbox()
        self._write_wiki_config()
        catalog = self._catalog()
        self._write_security_master(catalog)
        catalog.scan()
        self._write_runtime_policy(catalog)
        self._preset_v2_artifacts(catalog)
        manifest = IsolatedLakeManifest(
            entries=list(self.entries),
            catalog_path=catalog.config.database_path,
            derived_root=catalog.config.derived_dir,
        )
        return manifest

    def _write_security_master(self, catalog: "object") -> None:
        """Identity registry snapshot (filing-fetch identify depends on it):
        cn.json with the lake's issuers."""
        sm = catalog.config.catalog_dir / "security_master"
        sm.mkdir(parents=True, exist_ok=True)
        (sm / "cn.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "market": "CN",
                    "record_count": 2,
                    "retrieved_at": "2026-08-12T00:00:00Z",
                    "sources": ["cninfo"],
                    "records": [
                        {
                            "active": True,
                            "aliases": ["ZIJIN"],
                            "canonical_name": "紫金矿业",
                            "exchange": "SSE",
                            "ticker": "601899",
                            "identifiers": {"cninfo_category": "A股"},
                            "market": "CN",
                            "schema_version": "1.0",
                            "security_id": "601899",
                            "source_name": "cninfo",
                            "source_record_id": "1225023658",
                            "source_url": "https://provider.example/601899",
                        },
                        {
                            "active": True,
                            "aliases": ["PINGAN"],
                            "canonical_name": "中国平安",
                            "exchange": "SSE",
                            "ticker": "601318",
                            "identifiers": {"cninfo_category": "A股"},
                            "market": "CN",
                            "schema_version": "1.0",
                            "security_id": "601318",
                            "source_name": "cninfo",
                            "source_record_id": "1223023656",
                            "source_url": "https://provider.example/601318",
                        },
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def _write_wiki_config(self) -> None:
        """Production-shaped config/source_catalog.yaml under the lake project
        (filing-fetch validates its existence; the CLI reads roots from it)."""
        cfg_dir = self.lake / "project" / "config"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "source_catalog.yaml").write_text(
            'schema_version: "1.0"\n'
            'catalog_dir: "${PROJECT_ROOT}/.source_catalog"\n'
            "reusable_root_kinds: [company_raw, dayu_portfolio, directory]\n"
            "roots:\n"
            f'  - root_id: company_raw\n    kind: company_raw\n    path: "{self.companies.as_posix()}"\n    priority: 10\n'
            f'  - root_id: dayu_portfolio\n    kind: dayu_portfolio\n    path: "{self.portfolio.as_posix()}"\n    priority: 20\n'
            f'  - root_id: dropbox_stock\n    kind: directory\n    path: "{(self.lake / "Dropbox" / "Stock").as_posix()}"\n    priority: 30\n',
            encoding="utf-8",
        )

    def _write_runtime_policy(self, catalog: "object") -> None:
        """P5-RF: write a CWP-valid RuntimePolicySnapshot whose policy_hash
        matches export_policy_2x(config) at read time (the old handwritten
        legacy snapshot is rejected as runtime_policy_invalid by the current
        reader).  Flags: legal all-off baseline.  The hash is pinned from the
        REAL YAML-loaded config (the reader CLI loads its config from that
        same file), not from the programmatic fixture config."""
        from company_wiki.source_catalog.config import load_catalog_config
        from company_wiki.source_catalog.flags import FLAGS
        from company_wiki.source_catalog.policy_2x import export_policy_2x
        from company_wiki.source_catalog.runtime_policy import build_snapshot

        conf = load_catalog_config(
            self.lake / "project" / "config" / "source_catalog.yaml"
        )
        policy_hash, _ = export_policy_2x(conf)
        snapshot = build_snapshot(
            {
                "schema_version": "1.0",
                "current_epoch": "epoch-fixture",
                "active_cohorts": ["fixture-cohort"],
                "flags": {name: False for name in FLAGS}
                | {"legacy_bridge_enabled": True},
                "policy_hash": policy_hash,
                "updated_at": "2026-08-10T00:00:00Z",
            }
        )
        (catalog.config.catalog_dir / "runtime_policy.json").write_text(
            json.dumps(snapshot, ensure_ascii=False, sort_keys=True), encoding="utf-8"
        )

    def _preset_v2_artifacts(self, catalog: "object") -> None:
        """INSERT v2 artifact rows (schema_version column + metadata) +
        derived files + producer_events — isomorphic to the production canary."""
        # RF-E2E-ADAPT: the receipt is written through CW's fail-closed writer
        # (state_domain stamping + payload/dual binding are validated AT WRITE
        # time) — same call shape as CW tests/unit/test_prompt_injection_guard.
        from company_wiki.source_catalog.prompt_injection import (
            record_prompt_injection_review,
        )
        from company_wiki.source_catalog.prompt_injection_guard import RULESET_HASH

        con = sqlite3.connect(catalog.config.database_path)
        con.row_factory = sqlite3.Row
        derived = catalog.config.derived_dir
        # map root_id -> entry list
        by_root: dict[str, list[LakeEntry]] = {}
        for e in self.entries:
            by_root.setdefault(e.root_id, []).append(e)
        for root_id, entries in by_root.items():
            for e in entries:
                doc = con.execute(
                    "SELECT document_id, primary_source_id FROM documents "
                    "WHERE title LIKE ? OR document_id IN "
                    "(SELECT document_id FROM locations WHERE root_id=? AND relative_path=?)",
                    (f"%{e.security}%", root_id, e.rel_path),
                ).fetchone()
                if doc is None:
                    continue
                digest = hashlib.sha256(
                    (
                        doc["document_id"] + "\0normalized\0source_catalog_normalizer\0"
                        "1.0.0"
                    ).encode()
                ).hexdigest()
                art_id = "urn:company-wiki:artifact:sha256:" + digest
                sub = derived / digest[:2] / digest
                sub.mkdir(parents=True)
                body = f"normalized markdown for {e.rel_path} (v2)\n".encode()
                (sub / "normalized.md").write_bytes(body)
                content_sha = hashlib.sha256(body).hexdigest()
                con.execute(
                    """INSERT OR REPLACE INTO artifacts
                    (artifact_id,document_id,source_id,artifact_role,path,content_sha256,
                     byte_size,mime_type,generator_name,generator_version,status,error,
                     schema_version,source_sha256,metadata_json,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,strftime('%Y-%m-%dT%H:%M:%SZ','now'))""",
                    (
                        art_id,
                        doc["document_id"],
                        doc["primary_source_id"],
                        "normalized",
                        str(sub / "normalized.md"),
                        content_sha,
                        len(body),
                        "text/markdown",
                        "source_catalog_normalizer",
                        "1.0.0",
                        "completed",
                        None,
                        ARTIFACT_SCHEMA_VERSION,
                        con.execute(
                            "SELECT content_sha256 FROM sources WHERE source_id=?",
                            (doc["primary_source_id"],),
                        ).fetchone()[0],
                        json.dumps(
                            {
                                "schema_version": ARTIFACT_SCHEMA_VERSION,
                                "parser_name": "plain_text",
                                "parser_version": "1.0.0",
                                "quality_flags": [],
                                "span_count": 0,
                            },
                            ensure_ascii=False,
                        ),
                    ),
                )
                con.execute(
                    """INSERT OR IGNORE INTO producer_events
                    (event_id,document_id,artifact_role,producer_name,producer_version,
                     event_type,created_at)
                    VALUES(?,?,?,?,?,?,datetime('now'))""",
                    (
                        f"pe-{art_id}-fc1001",
                        doc["document_id"],
                        "normalized",
                        "source_catalog_normalizer",
                        "1.0.0",
                        "parser",
                    ),
                )
                # FC-905-b policy gate: consumption blocks on not_reviewed —
                # the lake's documents carry a deterministic-policy review
                # receipt (same contract as the FC-906-c production canary).
                # RF-E2E-ADAPT: written through the CW receipt WRITER (the
                # promoted GUARD-MERGE/OPEN-6 contract: state_domain + payload
                # binding + source/policy dual binding, mirrored from CW's
                # tests/unit/test_prompt_injection_guard.py).  A hand-shaped
                # pre-5d72529 dict fails the reader's C7 state_domain
                # fail-closed as not_reviewed and the chain blocks upstream.
                source_sha = con.execute(
                    "SELECT content_sha256 FROM sources WHERE source_id=?",
                    (doc["primary_source_id"],),
                ).fetchone()[0]
                record_prompt_injection_review(
                    con,
                    doc["document_id"],
                    status="not_detected",
                    reviewer="policy-reviewer-fc1001",
                    evidence_sha256=content_sha,
                    now="2026-08-12T00:00:00Z",
                    source_sha256=source_sha,
                    policy_hash=RULESET_HASH,
                    evidence_payload=body,
                )
                # dayu docs carry the company-name entity too (production dayu
                # metadata infers it from source_title) — the resolver matches
                # by canonical name via the security-master issuer index
                con.execute(
                    "INSERT OR IGNORE INTO document_entities(document_id, entity_id, confidence, method)"
                    " VALUES(?,?,?,?)",
                    (doc["document_id"], f"company-name:{e.security}", 1.0, "sidecar"),
                )
        con.commit()
        con.close()

    # --- corruption variants (each must fail closed) ---

    def corrupt(self, variant: str, manifest: IsolatedLakeManifest) -> None:
        assert manifest.catalog_path is not None
        con = sqlite3.connect(manifest.catalog_path)
        companies_entry = next(
            e for e in manifest.entries if e.root_id == "company_raw"
        )
        dropbox_entry = next(
            e for e in manifest.entries if e.root_id == "dropbox_stock"
        )
        if variant == "hash_mismatch":
            # derived file bytes diverge from content_sha256
            for f in (manifest.derived_root or Path()).rglob("normalized.md"):
                f.write_bytes(b"tampered bytes")
        elif variant == "truncated_source":
            # source bytes diverge from sources.content_sha256
            p = self.companies / companies_entry.rel_path
            p.write_bytes(b"%PDF truncated")
            con.execute(
                "UPDATE sources SET content_sha256=? WHERE source_id IN "
                "(SELECT primary_source_id FROM documents d JOIN locations l "
                "ON l.document_id=d.document_id WHERE l.root_id=?)",
                ("0" * 64, "company_raw"),
            )
        elif variant == "sidecar_missing":
            # Dropbox root depends on the sidecar for identity — removing it
            # must make the document unresolvable (company_raw tolerates
            # sidecar-less files by design; Dropbox does not, FC-501).
            side = self.dropbox / (dropbox_entry.sidecar_rel or "")
            side.unlink()
        elif variant == "location_inactive":
            con.execute(
                "UPDATE locations SET location_status='quarantined' "
                "WHERE root_id='dropbox_stock'"
            )
        elif variant == "column_drop":
            con.execute("UPDATE artifacts SET schema_version=NULL")
        else:
            raise ValueError(f"unknown corruption variant {variant!r}")
        con.commit()
        con.close()


class RootSpecFactory:
    """FC-604-derived RootSpec builders (imported lazily to keep this module
    importable without company-wiki on sys.path for pure manifest tests)."""

    @staticmethod
    def company(path: Path):
        from company_wiki.source_catalog.models import RootSpec

        return RootSpec(
            "company_raw",
            path,
            "company_raw",
            priority=10,
            adapter_id="company_raw_v1",
            read_only=False,
            reusable_for_filing=True,
            canonical_write_target="companies",
        )

    @staticmethod
    def dayu(path: Path):
        from company_wiki.source_catalog.models import RootSpec

        return RootSpec(
            "dayu_portfolio",
            path,
            "dayu_portfolio",
            priority=20,
            adapter_id="dayu_filing_v1",
            read_only=True,
            reusable_for_filing=True,
        )

    @staticmethod
    def dropbox(path: Path):
        from company_wiki.source_catalog.models import RootSpec

        return RootSpec(
            "dropbox_stock",
            path,
            "directory",
            priority=30,
            adapter_id="sidecar_filing_v1",
            read_only=True,
            reusable_for_filing=True,
        )
