"""Shared real-schema fixtures for the P5 storage-retirement tool tests.

Builds catalogs with the production CatalogStore DDL and frozen fixture
producers (normalizer / extractive summary / section extractor).  No tests
live here; every test module in this package imports the helpers by name.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[2] / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from company_wiki.source_catalog.config import CatalogConfig  # noqa: E402
from company_wiki.source_catalog.models import RootSpec  # noqa: E402
from company_wiki.source_catalog.narrative_artifact_store import (  # noqa: E402
    LocalNarrativeObjectStore,
    NarrativeArtifactDraft,
    NarrativeArtifactStore,
)
from support.legacy_catalog.normalizer import normalize_catalog  # noqa: E402
from support.legacy_catalog.section_extractor import extract_sections_catalog  # noqa: E402
from company_wiki.source_catalog.store import CatalogStore  # noqa: E402
from support.legacy_catalog.summarizer import summarize_catalog  # noqa: E402
from company_wiki.source_contract.source_manifest import source_id_for_sha256  # noqa: E402

NOW = "2026-01-01T00:00:00Z"
ROOT_ID = "urn:company-wiki:root:sha256:" + "r" * 64

ANNUAL_BODY = "\n\n".join(
    [
        "# 年度报告",
        "第一节 业务概要",
        "公司主营业务为半导体设备研发制造。报告期内收入稳步增长，产能利用率提升。",
        "第二节 管理层讨论与分析",
        "公司研发投入占比提升，关键技术取得突破，新产品进展顺利。",
        "第三节 风险因素",
        "行业周期波动带来不确定性风险，竞争加剧可能影响毛利。",
    ]
)
NEWS_BODY = "# 新闻快讯\n\n公司发布新产品，市场反应积极。\n\n后续将披露更多细节。\n"


def _insert(connection: sqlite3.Connection, table: str, values: dict) -> None:
    have = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    use = {key: value for key, value in values.items() if key in have}
    connection.execute(
        f"INSERT INTO {table} ({','.join(use)}) VALUES ({','.join('?' * len(use))})",
        tuple(use.values()),
    )


def _write_source(
    root_dir: Path,
    relative: str,
    body: bytes,
    *,
    mime: str = "text/markdown",
) -> tuple[str, str, str]:
    """Write one raw file and return (sha256, source_id, document_id)."""
    path = root_dir / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    sha = hashlib.sha256(body).hexdigest()
    source_id = source_id_for_sha256(sha)
    document_id = "urn:company-wiki:document:sha256:" + sha
    return sha, source_id, document_id


def _seed_document(
    store: CatalogStore,
    root_dir: Path,
    relative: str,
    body: bytes,
    *,
    document_kind: str,
) -> tuple[str, str]:
    sha, source_id, document_id = _write_source(root_dir, relative, body)
    with store.transaction() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO roots (root_id,path,kind,priority) VALUES (?,?,?,?)",
            (ROOT_ID, str(root_dir), "company_raw", 1),
        )
        _insert(
            connection,
            "sources",
            {
                "source_id": source_id,
                "content_sha256": sha,
                "byte_size": len(body),
                "mime_type": "text/markdown",
                "first_seen_at": NOW,
            },
        )
        _insert(
            connection,
            "documents",
            {
                "document_id": document_id,
                "primary_source_id": source_id,
                "title": Path(relative).stem,
                "source_type": "regulatory_filing",
                "document_kind": document_kind,
                "published_date": "2025-04-30",
                "source_status": "active",
                "metadata_priority": 1,
                "metadata_json": json.dumps(
                    {
                        "canonical_entity_id": "AMEC",
                        "market": "CN",
                        "security_id": "688012",
                        "fiscal_year": 2025,
                        "fiscal_period": "FY",
                    }
                ),
                "first_seen_at": NOW,
                "last_seen_at": NOW,
            },
        )
        _insert(
            connection,
            "locations",
            {
                "location_id": f"loc-{sha[:12]}",
                "root_id": ROOT_ID,
                "relative_path": relative,
                "absolute_path": str(root_dir / relative),
                "source_id": source_id,
                "document_id": document_id,
                "role": "original_primary",
                "location_status": "active",
                "observed_size": len(body),
                "last_seen_run": "run-1",
                "manifest_json": json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "source_id": source_id,
                        "entity_ids": ["AMEC"],
                        "original_path": relative,
                        "content_sha256": sha,
                        "source_type": "regulatory_filing",
                        "published_date": "2025-04-30",
                        "retrieved_at": "2025-05-01T00:00:00Z",
                        "collector_name": "probe",
                        "collector_version": "1.0.0",
                        "mime_type": "text/markdown",
                        "byte_size": len(body),
                        "immutable_status": "verified",
                    }
                ),
                "metadata_json": "{}",
            },
        )
    return source_id, document_id


def _prepare_narrative(
    config: CatalogConfig,
    store: CatalogStore,
    document_id: str,
    source_id: str,
    source_sha256: str,
) -> str:
    objects = LocalNarrativeObjectStore(config.catalog_dir)
    store_ = NarrativeArtifactStore(store, objects)
    content = b'{"schema_version":"narrative-bundle/2.0","version":1}'
    sha = hashlib.sha256(content).hexdigest()
    draft = NarrativeArtifactDraft(
        effect_id=f"effect-{source_sha256[:12]}",
        work_key=sha,
        document_id=document_id,
        source_id=source_id,
        source_sha256=source_sha256,
        producer_name="company_wiki.narrative_bundle",
        producer_version="2.0",
        policy_sha256="b" * 64,
        selection_status="selected",
        quality_status="verified",
        metadata_json='{"environment":"fixture"}',
        created_at=NOW,
    )
    prepared = store_.prepare(draft, content)
    store_.activate(prepared.effect_id, verified_after_hash=sha, activated_at=NOW)
    return prepared.artifact_version_id


def build_catalog(tmp: Path) -> tuple[CatalogConfig, CatalogStore, dict]:
    """Real-schema catalog with old derived artifacts, spans and one new final."""
    root_dir = tmp / "raw"
    config = CatalogConfig(
        project_root=tmp,
        catalog_dir=tmp / "catalog",
        roots=(
            RootSpec(root_id=ROOT_ID, path=root_dir, kind="company_raw", priority=1),
        ),
    )
    store = CatalogStore(config.database_path)
    annual_source, annual_doc = _seed_document(
        store,
        root_dir,
        "reports/annual_probe.md",
        ANNUAL_BODY.encode("utf-8"),
        document_kind="annual_report",
    )
    news_source, news_doc = _seed_document(
        store,
        root_dir,
        "news/news_probe.md",
        NEWS_BODY.encode("utf-8"),
        document_kind="original_news",
    )
    normalize_catalog(config, store, force=True, retry_limit=1)
    summarize_catalog(config, store, force=True)
    extract_sections_catalog(config, store, force=True, document_id=annual_doc)
    _prepare_narrative(
        config, store, annual_doc, annual_source, annual_doc.rsplit(":", 1)[1]
    )
    facts = {
        "annual": {
            "sha": annual_doc.rsplit(":", 1)[1],
            "source_id": annual_source,
            "document_id": annual_doc,
        },
        "news": {
            "sha": news_doc.rsplit(":", 1)[1],
            "source_id": news_source,
            "document_id": news_doc,
        },
    }
    return config, store, facts


def derived_marker(config: CatalogConfig) -> Path:
    return config.derived_dir


def table_names(database_path: Path) -> list[str]:
    conn = sqlite3.connect(f"file:{database_path.as_posix()}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        return [row[0] for row in rows]
    finally:
        conn.close()


def count_rows(database_path: Path, table: str) -> int:
    conn = sqlite3.connect(f"file:{database_path.as_posix()}?mode=ro", uri=True)
    try:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    finally:
        conn.close()


def tree_digest(root: Path) -> dict[str, int]:
    digest: dict[str, int] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            key = path.relative_to(root).as_posix()
            digest[key] = path.stat().st_size
    return digest
