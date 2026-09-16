"""R4/B05 follow-up: every READER of the shared ``documents.metadata_json`` column.

Work package b05-read-side-malformed-columns, second disposition round.  The verifier of
the first round found that the same crash class (B-VR05M2-01, P1) still lived in readers
the package had mislabelled as "artifacts column, unverified":

  * ``llm_summarizer.summarize_catalog_with_llm`` - the batch selection filters with
    ``json_extract(d.metadata_json, '$.<receipt>.schema_version')``; without a
    ``json_valid`` guard SQLite raises ``OperationalError: malformed JSON`` from inside
    the query for ``{not json``, deep nesting, the empty string and undecodable TEXT.

Hermetic: a temp catalog built by the product's own ``CatalogStore`` (no production
catalog, no network, no LLM call - the client factory raises if it is ever invoked).
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from company_wiki.source_catalog import CatalogConfig  # noqa: E402
from company_wiki.source_catalog.store import CatalogStore  # noqa: E402

MALFORMED_SHAPES = (
    ("invalid JSON", "{not json"),
    ("deeply nested JSON", "[" * 5000),
    ("empty string", ""),
    ("payload is a JSON array", "[]"),
)


def _seed_catalog(tmp_path: Path) -> tuple[CatalogStore, Path]:
    """A catalog whose document actually reaches the summarizer's WHERE clause.

    Anti-vacuity, second attempt: the first fixture had no ``artifacts`` row, so the
    JOIN produced no candidates and ``json_extract`` was never EVALUATED on the malformed
    value - the cases passed while proving nothing (the mutation harness caught it: the
    mutant that removes the ``json_valid`` guard survived).  With a normalized artifact
    row and an active location the expression is evaluated for real.
    """
    store = CatalogStore(tmp_path / "catalog.sqlite3")
    with store.transaction() as conn:
        conn.execute(
            "INSERT INTO roots (root_id, path, kind, priority) "
            "VALUES ('company_raw','/x','company_raw',10)"
        )
        conn.execute(
            "INSERT INTO sources (source_id, content_sha256, byte_size, mime_type, "
            "first_seen_at) VALUES ('s1','h',1,'x','2026-01-01')"
        )
        conn.execute(
            "INSERT INTO documents (document_id, primary_source_id, title, source_type, "
            "document_kind, source_status, metadata_priority, metadata_json, "
            "first_seen_at, last_seen_at) "
            "VALUES ('d1','s1','t','file','annual_report','active',10,'{}','2026-01-01',"
            "'2026-01-01')"
        )
        conn.execute(
            "INSERT INTO artifacts (artifact_id, document_id, source_id, artifact_role, "
            "path, content_sha256, byte_size, mime_type, generator_name, "
            "generator_version, status, metadata_json, created_at) "
            "VALUES ('a1','d1','s1','normalized','/x/d1.md','h',1,'text/markdown',"
            "'normalizer','1','completed','{}','2026-01-01')"
        )
        conn.execute(
            "INSERT INTO locations (location_id, root_id, relative_path, absolute_path, "
            "source_id, document_id, role, location_status, last_seen_run, metadata_json) "
            "VALUES ('l1','company_raw','a.pdf','/x/a.pdf','s1','d1','original_primary',"
            "'active','run1','{}')"
        )
    return store, tmp_path / "catalog.sqlite3"


def _corrupt(database: Path, raw: str | bytes) -> None:
    con = sqlite3.connect(database)
    try:
        if isinstance(raw, bytes):
            con.execute(
                "UPDATE documents SET metadata_json=CAST(? AS TEXT) WHERE document_id='d1'",
                (raw,),
            )
        else:
            con.execute(
                "UPDATE documents SET metadata_json=? WHERE document_id='d1'", (raw,)
            )
        con.commit()
    finally:
        con.close()


def _config(tmp_path: Path) -> CatalogConfig:
    """A minimal real config: CatalogConfig insists on a non-empty root tuple, and these
    cases only ever exercise the SELECTION query (no scan is run)."""
    from company_wiki.source_catalog.models import RootSpec

    root = tmp_path / "companies"
    root.mkdir(exist_ok=True)
    spec = RootSpec(
        "company_raw",
        root,
        "company_raw",
        priority=10,
        adapter_id="company_raw_v1",
        read_only=False,
        reusable_for_filing=True,
        canonical_write_target="companies",
    )
    # catalog_dir=tmp_path so the config's database_path is the same file the store uses
    return CatalogConfig(
        project_root=tmp_path,
        catalog_dir=tmp_path,
        reusable_root_kinds=("company_raw", "directory"),
        roots=(spec,),
    )


@pytest.mark.parametrize("label,raw", MALFORMED_SHAPES + (("undecodable TEXT", b"\xff\xfe{}"),))
def test_the_summarizer_selection_survives_a_malformed_shared_column(
        tmp_path, monkeypatch, label, raw):
    """B-VR05M2-01 (P1): the batch selection must not raise on any of these - a row whose
    receipt cannot be read is simply not eligible for summarization.

    Anti-vacuity: the case counts the SELECT calls and fails if the query never ran (the
    function returns early when the exit gate has no configured roots, which would make
    "it did not raise" meaningless).  Eligibility itself (a normalized artifact row plus
    gate roots) is NOT seeded here - the positive path is covered by the existing
    summarizer suites."""
    from company_wiki.source_catalog.llm_summarizer import summarize_catalog_with_llm

    store, database = _seed_catalog(tmp_path)
    _corrupt(database, raw)

    selects: list[str] = []
    real_fetchall = store.fetchall

    def counting_fetchall(sql, params=()):  # noqa: ANN001
        selects.append(sql)
        return real_fetchall(sql, params)

    monkeypatch.setattr(store, "fetchall", counting_fetchall)

    def _forbidden_client() -> object:
        raise AssertionError(f"the LLM client was constructed ({label})")

    report = summarize_catalog_with_llm(
        _config(tmp_path),
        store,
        limit=10,
        llm_client_factory=_forbidden_client,
        max_input_chars=4000,
        max_output_tokens=256,
    )
    assert selects, f"the selection query never ran ({label}) - the case is vacuous"
    assert report.completed == 0, (label, report)
    assert report.eligible == 0, (label, report)


def test_the_selection_query_is_the_one_under_test(tmp_path, monkeypatch):
    """Pin the anti-vacuity mechanism itself: the query text the counting wrapper sees is
    the guarded selection (json_valid present), so the resilience cases above cannot pass
    by skipping the SQL."""
    from company_wiki.source_catalog.llm_summarizer import summarize_catalog_with_llm

    store, database = _seed_catalog(tmp_path)
    _corrupt(database, "{not json")

    selects: list[str] = []
    real_fetchall = store.fetchall

    def counting_fetchall(sql, params=()):  # noqa: ANN001
        selects.append(sql)
        return real_fetchall(sql, params)

    monkeypatch.setattr(store, "fetchall", counting_fetchall)
    summarize_catalog_with_llm(
        _config(tmp_path),
        store,
        limit=10,
        llm_client_factory=lambda: object(),
        max_input_chars=4000,
        max_output_tokens=256,
    )
    assert any("json_valid(d.metadata_json)" in sql for sql in selects), selects
