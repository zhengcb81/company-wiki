"""FC-905-a RED/acceptance tests: trusted capture/safety evidence on the
SCENARIO: SAFE-04 SAFE-05 SAFE-06
resolution envelope.

The envelope must NEVER fabricate capture/safety counts:

- `prompt_injection_status` comes from the document's review receipt
  (documents.metadata_json['prompt_injection_review']); absent receipt ->
  the explicit `not_reviewed`, never a faked status.
- `parser_calls`/`llm_calls` come from the producer_events journal (a SQLite
  trigger journals every artifact INSERT); without a store they are None —
  absent evidence is never reported as 0.

RED phase: the journal table/trigger, the review receipt helpers, and the
envelope fields do not exist yet.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog.models import RootSpec  # noqa: E402


def _seed_company(tmp_path: Path, company: str = "Acme",
                  pdoc: str = "doc-a", kind: str = "annual_report") -> Path:
    raw = tmp_path / "companies" / company / "raw" / "financial_reports" / "annual"
    raw.mkdir(parents=True, exist_ok=True)
    (raw / f"{pdoc}.pdf").write_bytes(
        b"%PDF-1.4 " + company.encode("utf-8") + pdoc.encode("utf-8"))
    (raw / f"{pdoc}.pdf.source.json").write_text(json.dumps({
        "market": "CN", "security_id": "601899",
        "source_title": f"{company} 2024", "fiscal_year": 2024,
        "filing_date": "2025-03-20", "form_type": kind,
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


def _resolve(catalog):
    from company_wiki.source_catalog import SourceRequest, SourceResolver

    return SourceResolver(catalog).resolve(SourceRequest(
        entity="Acme", market="CN", security_id="601899",
        document_kind="annual_report", form_type="annual_report",
        fiscal_year=2024, provider="cninfo", as_of_date="2026-08-11",
        mode="exact",
    ))


def _doc_id(catalog) -> str:
    con = sqlite3.connect(catalog.config.database_path)
    try:
        return con.execute(
            "SELECT document_id FROM documents WHERE source_status='active'"
            " LIMIT 1").fetchone()[0]
    finally:
        con.close()


def _add_artifact(catalog, tree, *, doc_id: str, role: str,
                  generator_name: str, generator_version: str,
                  body: bytes | None = b"# body") -> None:
    art_dir = tree / "Acme" / "processed"
    art_dir.mkdir(parents=True, exist_ok=True)
    path = art_dir / f"{role}.md"
    if body is not None:
        path.write_bytes(body)
    content_sha = hashlib.sha256(body).hexdigest() if body is not None else "0" * 64
    con = sqlite3.connect(catalog.config.database_path)
    src = con.execute(
        "SELECT primary_source_id FROM documents WHERE document_id=?",
        (doc_id,)).fetchone()[0]
    con.execute(
        """INSERT OR REPLACE INTO artifacts
        (artifact_id, document_id, source_id, artifact_role, path,
         content_sha256, byte_size, mime_type, generator_name,
         generator_version, status, error, metadata_json, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (f"art-{role}", doc_id, src, role, str(path), content_sha,
         len(body) if body is not None else 0, "text/markdown",
         generator_name, generator_version, "completed", None,
         json.dumps({"schema_version": "1.0"}), "2026-08-01T00:00:00Z"),
    )
    con.commit()
    con.close()


def _record_review(catalog, doc_id: str, *, status: str,
                   reviewer: str = "reviewer-a",
                   evidence: str | None = None) -> None:
    from company_wiki.source_catalog.prompt_injection import (
        record_prompt_injection_review,
    )

    con = sqlite3.connect(catalog.config.database_path)
    try:
        record_prompt_injection_review(
            con, doc_id, status=status, reviewer=reviewer,
            evidence_sha256=evidence or ("e" * 64),
            now="2026-08-11T00:00:00Z")
        con.commit()
    finally:
        con.close()


def _envelope(catalog, resolution, *, store=None):
    from company_wiki.source_catalog.resolver import build_resolution_envelope

    return build_resolution_envelope(resolution, store=store)


# --- PI-01/02: review receipt drives prompt_injection_status -----------------


def test_pi01_reviewed_not_detected_forwarded(tmp_path):
    tree = _seed_company(tmp_path)
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    doc_id = _doc_id(catalog)
    _record_review(catalog, doc_id, status="not_detected")
    envelope = _envelope(catalog, _resolve(catalog), store=catalog.store)
    assert envelope.prompt_injection_status == "not_detected"


def test_pi02_reviewed_detected_and_ignored_forwarded(tmp_path):
    tree = _seed_company(tmp_path)
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    doc_id = _doc_id(catalog)
    _record_review(catalog, doc_id, status="detected_and_ignored")
    envelope = _envelope(catalog, _resolve(catalog), store=catalog.store)
    assert envelope.prompt_injection_status == "detected_and_ignored"


# --- PI-03: absent receipt -> explicit not_reviewed (never faked) -------------


def test_pi03_no_review_is_explicit_not_reviewed(tmp_path):
    tree = _seed_company(tmp_path)
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    envelope = _envelope(catalog, _resolve(catalog), store=catalog.store)
    assert envelope.prompt_injection_status == "not_reviewed"


# --- PI-04: no store -> evidence absent (None), never fabricated 0 ------------


def test_pi04_no_store_means_no_fabricated_counts(tmp_path):
    tree = _seed_company(tmp_path)
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    envelope = _envelope(catalog, _resolve(catalog))  # no store
    assert envelope.prompt_injection_status == "not_reviewed"
    assert envelope.parser_calls is None
    assert envelope.llm_calls is None


# --- PI-05: parser/llm counts come from the producer_events journal ----------


def test_pi05_counts_from_journal_not_output(tmp_path):
    tree = _seed_company(tmp_path)
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    doc_id = _doc_id(catalog)
    # normalized (parser-type) + summary (llm-type) artifact inserts
    _add_artifact(catalog, tree, doc_id=doc_id, role="normalized",
                  generator_name="source_catalog_normalizer",
                  generator_version="1.0.0")
    _add_artifact(catalog, tree, doc_id=doc_id, role="summary",
                  generator_name="source_catalog_llm_summary",
                  generator_version="1.0.0")
    envelope = _envelope(catalog, _resolve(catalog), store=catalog.store)
    assert envelope.parser_calls == 1
    assert envelope.llm_calls == 1


def test_pi06_zero_events_is_honest_zero(tmp_path):
    """No producer events journaled -> counts are 0 (the journal EXISTS and
    says zero — different from PI-04 where the journal is unreachable)."""
    tree = _seed_company(tmp_path)
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    envelope = _envelope(catalog, _resolve(catalog), store=catalog.store)
    assert envelope.parser_calls == 0
    assert envelope.llm_calls == 0


# --- PI-07: the trigger journals every artifact INSERT -----------------------


def test_pi07_trigger_journals_artifact_insert(tmp_path):
    tree = _seed_company(tmp_path)
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    doc_id = _doc_id(catalog)
    _add_artifact(catalog, tree, doc_id=doc_id, role="normalized",
                  generator_name="source_catalog_normalizer",
                  generator_version="1.0.0")
    con = sqlite3.connect(catalog.config.database_path)
    try:
        rows = con.execute(
            "SELECT artifact_role, event_type FROM producer_events").fetchall()
    finally:
        con.close()
    assert rows == [("normalized", "parser")]


# --- PI-08: review receipt write validates fail-closed -----------------------


def test_pi08_review_write_validates(tmp_path):
    from company_wiki.source_catalog.prompt_injection import (
        record_prompt_injection_review,
    )

    tree = _seed_company(tmp_path)
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    doc_id = _doc_id(catalog)
    con = sqlite3.connect(catalog.config.database_path)
    try:
        for bad in ("not_reviewed", "maybe", ""):
            try:
                record_prompt_injection_review(
                    con, doc_id, status=bad, reviewer="r",
                    evidence_sha256="e" * 64, now="2026-08-11T00:00:00Z")
            except ValueError:
                continue
            raise AssertionError(f"status {bad!r} must be rejected")
        try:
            record_prompt_injection_review(
                con, doc_id, status="not_detected", reviewer="",
                evidence_sha256="e" * 64, now="2026-08-11T00:00:00Z")
        except ValueError:
            pass
        else:
            raise AssertionError("empty reviewer must be rejected")
        try:
            record_prompt_injection_review(
                con, doc_id, status="not_detected", reviewer="r",
                evidence_sha256="short", now="2026-08-11T00:00:00Z")
        except ValueError:
            pass
        else:
            raise AssertionError("non-sha256 evidence must be rejected")
    finally:
        con.close()


# --- PI-09: envelope to_dict carries the new fields deterministically --------


def test_pi09_envelope_to_dict_deterministic(tmp_path):
    tree = _seed_company(tmp_path)
    catalog = _catalog(tmp_path, tree)
    catalog.scan()
    doc_id = _doc_id(catalog)
    _record_review(catalog, doc_id, status="not_detected")
    _add_artifact(catalog, tree, doc_id=doc_id, role="normalized",
                  generator_name="source_catalog_normalizer",
                  generator_version="1.0.0")
    resolution = _resolve(catalog)
    e1 = _envelope(catalog, resolution, store=catalog.store)
    e2 = _envelope(catalog, resolution, store=catalog.store)
    payload = e1.to_dict()
    assert payload["prompt_injection_status"] == "not_detected"
    assert payload["parser_calls"] == 1
    assert payload["llm_calls"] == 0
    assert json.dumps(payload, sort_keys=True) == json.dumps(
        e2.to_dict(), sort_keys=True)
