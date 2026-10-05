"""P5-STORAGE red tests: prune-spans selection / protection / idempotence."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from support.p5_storage_catalog_fixture import build_catalog

from legacy_storage.spans import run_prune_spans
from legacy_storage.inventory import run_inventory


def _now() -> datetime:
    return datetime(2026, 10, 5, 0, 0, 0, tzinfo=UTC)


_SPAN_PARSER = "plain_text"


def _selection(parser_version: str = "1.0.0") -> dict:
    return {
        "schema_version": "cwp-span-selection/1",
        "parser_name": _SPAN_PARSER,
        "parser_version": parser_version,
        "source_ids": [],
        "document_ids": [],
    }


def test_empty_selection_is_refused(tmp_path: Path) -> None:
    config, _, _ = build_catalog(tmp_path)
    report = run_prune_spans(
        config,
        {"schema_version": "cwp-span-selection/1"},
        keep_refs=[],
        now=_now(),
        dry_run=True,
    )
    assert report["status"] == "refused"
    assert report["error_code"] == "empty_selection"


def test_dry_run_deletes_nothing(tmp_path: Path) -> None:
    config, store, _ = build_catalog(tmp_path)
    before = store.fetchone("SELECT COUNT(*) AS n FROM evidence_spans")["n"]
    report = run_prune_spans(config, _selection(), keep_refs=[], now=_now())
    assert report["dry_run"] is True
    assert report["deleted"] == 0
    after = store.fetchone("SELECT COUNT(*) AS n FROM evidence_spans")["n"]
    assert before == after


def test_prune_respects_parser_and_keep_refs(tmp_path: Path) -> None:
    config, store, facts = build_catalog(tmp_path)
    with store.transaction() as connection:
        keep_pair = connection.execute(
            "SELECT source_id, locator FROM evidence_spans LIMIT 1"
        ).fetchone()
        keep_source, keep_locator = keep_pair[0], keep_pair[1]
    inventory_report = run_inventory(config, now=_now())
    count_before = inventory_report.report["source_facts_before"]
    report = run_prune_spans(
        config,
        _selection(),
        keep_refs=[{"source_id": keep_source, "locator": keep_locator}],
        now=_now(),
        dry_run=False,
    )
    assert report["status"] == "succeeded"
    assert report["deleted"] > 0
    with store.transaction() as connection:
        remaining = connection.execute(
            "SELECT parser_name, COUNT(*) FROM evidence_spans GROUP BY parser_name"
        ).fetchall()
        # keep ref survived
        hit = connection.execute(
            "SELECT COUNT(*) FROM evidence_spans WHERE source_id=? AND locator=?",
            (keep_source, keep_locator),
        ).fetchone()[0]
        assert hit == 1
    assert {row[0] for row in remaining} == {_SPAN_PARSER}
    # source facts did not move
    assert (
        report["source_facts_after"]["sources"]["count"]
        == count_before["sources"]["count"]
    )


def test_prune_is_idempotent_and_rerunnable(tmp_path: Path) -> None:
    config, _, _ = build_catalog(tmp_path)
    selection = _selection()
    first = run_prune_spans(config, selection, keep_refs=[], now=_now(), dry_run=False)
    snapshot_deleted = first["deleted"]
    second = run_prune_spans(config, selection, keep_refs=[], now=_now(), dry_run=False)
    assert second["deleted"] == 0
    assert second["already_absent"] == snapshot_deleted or second["already_absent"] == 0
    assert second["status"] == "succeeded"


def test_prune_keeps_unknown_parser(tmp_path: Path) -> None:
    config, store, _ = build_catalog(tmp_path)
    with store.transaction() as connection:
        connection.execute(
            "INSERT INTO evidence_spans (span_id, document_id, source_id, locator,"
            " raw_text, span_json, parser_name, parser_version, parse_status)"
            " SELECT span_id||'-new', document_id, source_id, locator||'-x', raw_text,"
            " span_json, 'future_parser_9', '1.0.0', parse_status"
            " FROM evidence_spans LIMIT 1"
        )
    report = run_prune_spans(
        config, _selection(), keep_refs=[], now=_now(), dry_run=False
    )
    assert report["status"] == "succeeded"
    with store.transaction() as connection:
        rows = connection.execute(
            "SELECT COUNT(*) FROM evidence_spans WHERE parser_name='future_parser_9'"
        ).fetchone()[0]
    assert rows == 1


def test_keep_ref_that_does_not_exist_is_an_error(tmp_path: Path) -> None:
    config, _, _ = build_catalog(tmp_path)
    report = run_prune_spans(
        config,
        _selection(),
        keep_refs=[
            {
                "source_id": "urn:company-wiki:source:sha256:" + "9" * 64,
                "locator": "loc:v1/paragraph:9999/chars:0-1",
            }
        ],
        now=_now(),
        dry_run=False,
    )
    assert report["status"] == "refused"
    assert report["error_code"] == "keep_ref_unknown"


def test_prune_reports_integrity_and_fk(tmp_path: Path) -> None:
    config, _, _ = build_catalog(tmp_path)
    report = run_prune_spans(
        config, _selection(), keep_refs=[], now=_now(), dry_run=False
    )
    assert report["foreign_key_check"] == []
    assert report["integrity_check"] == "ok"


def test_span_selection_supports_document_scope(tmp_path: Path) -> None:
    from support.p5_storage_catalog_fixture import count_rows

    config, store, facts = build_catalog(tmp_path)
    annual_docs = store.fetchall(
        "SELECT document_id FROM documents WHERE document_kind='annual_report'"
    )
    target = annual_docs[0]["document_id"]
    selection = _selection()
    selection["document_ids"] = [target]
    before_total = count_rows(config.database_path, "evidence_spans")
    report = run_prune_spans(config, selection, keep_refs=[], now=_now(), dry_run=False)
    assert report["deleted"] > 0
    after_total = count_rows(config.database_path, "evidence_spans")
    assert after_total < before_total
