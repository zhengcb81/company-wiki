"""Canonical company_raw source factory (Phase 16.10).

Default: writes a primary file plus a *complete capture-ready sidecar*
(https source_url), so resolver reuse works out of the box.  A test that
exercises the Phase 16.2 contract (capture-incomplete documents are not
reusable) must explicitly pass ``drop_url=True`` — a missing URL is the
explicit exception, never the default.
"""

from __future__ import annotations

import json
from pathlib import Path


def canonical_source(
    tmp_path: Path,
    *,
    company: str = "Acme",
    filename: str = "2026-02-20_Acme_2025_annual_report.txt",
    kind_dir: str = "financial_reports/annual",
    market: str = "CN",
    security_id: str = "600519",
    source_title: str = "Acme 2025 Annual Report",
    url: str | None = "https://www.cninfo.com.cn/new/disclosure/detail?stockCode=600519&announcementId=1",
    drop_url: bool = False,
    extra_sidecar: dict | None = None,
    content: bytes = b"annual report content",
) -> Path:
    """Write a canonical company_raw source and return the primary file path."""
    directory = tmp_path / "project" / "companies" / company / "raw" / kind_dir
    directory.mkdir(parents=True)
    primary = directory / filename
    primary.write_bytes(content)
    sidecar = {"source_title": source_title}
    if market is not None:
        sidecar["market"] = market
    if security_id is not None:
        sidecar["security_id"] = security_id
    if not drop_url and url is not None:
        sidecar["source_url"] = url
    if extra_sidecar:
        sidecar.update(extra_sidecar)
    primary.with_name(filename + ".source.json").write_text(
        json.dumps(sidecar), encoding="utf-8"
    )
    return primary


def company_raw_catalog(tmp_path: Path, *sources):
    """Build a SourceCatalog with one company_raw root containing the given
    source paths (each produced by canonical_source)."""
    from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog

    project = tmp_path / "project"
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("company_raw", project / "companies", "company_raw", priority=10),),
        )
    )
    catalog.scan()
    return catalog
