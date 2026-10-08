"""Source facts have one byte-verified, atomic and repeatable write boundary."""
from contextlib import contextmanager
from dataclasses import asdict, replace
import json
import hashlib
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest
import yaml

from company_wiki.source_catalog.models import CatalogConfig, RootSpec
from company_wiki.source_catalog.resolver import SourceRequest
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceReadError, SourceVersionReader
from company_wiki.source_catalog.store import retire_document, restore_document


@pytest.fixture
def lake(tmp_path):
    originals = tmp_path / "companies" / "Acme" / "raw"
    originals.mkdir(parents=True)
    selected = originals / "source.pdf"
    selected.write_bytes(b"%PDF-1.4 selected original")
    selected.with_suffix(".pdf.source.json").write_text(json.dumps({
        "company_name": "Acme", "market": "CN", "security_id": "Acme",
        "source_title": "Acme original", "published_date": "2023-12-31",
        "fiscal_year": 2023, "fiscal_period": "FY", "language": "en",
    }), encoding="utf-8")
    (originals / "unselected.pdf").write_bytes(b"%PDF-1.4 unrelated original")
    config = CatalogConfig(project_root=tmp_path, catalog_dir=tmp_path / ".source_catalog",
                           roots=(RootSpec("company_raw", tmp_path / "companies", "company_raw"),))
    catalog = SourceCatalog(config)
    catalog.scan()
    try:
        document = catalog.reader.fetchone("SELECT document_id,primary_source_id FROM documents WHERE title='Acme original'")
        reader = SourceVersionReader(catalog)
        ref = reader.query_ref(document["document_id"], document["primary_source_id"], hashlib.sha256(selected.read_bytes()).hexdigest())
        yield catalog, reader, ref, selected
    finally:
        catalog.close()


def _evidence(facts):
    return {key: {"locator": "test:source-header", "value": value} for key, value in facts.items()}


def _apply(lake, facts, evidence=None):
    catalog, _, ref, _ = lake
    return catalog.record_source_facts(ref=ref, facts=facts,
                                       evidence=_evidence(facts) if evidence is None else evidence)


def _assertions(catalog):
    return [dict(row) for row in catalog.reader.fetchall("SELECT * FROM source_metadata_assertions")]


def test_effective_facts_projection_and_immutable_capture_are_consistent(lake):
    catalog, reader, ref, original = lake
    doc_before = dict(catalog.reader.fetchone("SELECT * FROM documents WHERE document_id=?", (ref.document_id,)))
    others = [dict(x) for x in catalog.reader.fetchall("SELECT * FROM documents WHERE document_id<>?", (ref.document_id,))]
    original_before = original.read_bytes()
    facts = {"entity": "Acme", "market": "CN", "security_id": "300775",
             "document_kind": "equity_offering_prospectus", "published_date": "2022-11-30",
             "source_url": "https://example.org/official.pdf", "language": "zh"}
    result = _apply(lake, facts)
    assert result["status"] == "recorded"
    current = reader.describe_version(ref)
    assert {key: current[key] for key in facts if key != "entity"} == {key: value for key, value in facts.items() if key != "entity"}
    assert current["fiscal_year"] == 2023 and current["fiscal_period"] == "FY"
    doc_after = dict(catalog.reader.fetchone("SELECT * FROM documents WHERE document_id=?", (ref.document_id,)))
    assert doc_after["source_type"] == "prospectus"
    assert doc_after["metadata_json"] == doc_before["metadata_json"]
    assert original.read_bytes() == original_before
    assert [dict(x) for x in catalog.reader.fetchall("SELECT * FROM documents WHERE document_id<>?", (ref.document_id,))] == others
    assert reader.query_ref(ref.document_id, ref.source_id, ref.content_sha256) == ref


def test_identical_repeat_does_not_write_or_add_assertions(lake, monkeypatch):
    catalog = lake[0]
    facts = {"security_id": "002643", "published_date": None}
    first = _apply(lake, facts)
    before = _assertions(catalog)
    def no_transaction():
        raise AssertionError("same request must not begin a write transaction")
    monkeypatch.setattr(catalog.store, "transaction", no_transaction)
    second = _apply(lake, facts)
    assert second["status"] == "unchanged" and second["assertion_id"] == first["assertion_id"]
    assert _assertions(catalog) == before


def test_only_reobservation_time_does_not_duplicate_source_facts(lake):
    facts = {"security_id": "002643"}
    proof = _evidence(facts)
    proof["security_id"]["observed_at"] = "2026-10-07T00:00:00Z"
    first = _apply(lake, facts, proof)
    proof["security_id"]["observed_at"] = "2026-10-08T00:00:00Z"
    second = _apply(lake, facts, proof)
    assert second["status"] == "unchanged" and second["assertion_id"] == first["assertion_id"]
    assert len(_assertions(lake[0])) == 1


def test_cumulative_provenance_is_bounded(lake):
    facts = {"security_id": "002643"}
    proof = _evidence(facts)
    proof["security_id"]["detail"] = "x" * 40000
    _apply(lake, facts, proof)
    other = {"market": "CN"}
    more = _evidence(other)
    more["market"]["detail"] = "y" * 40000
    with pytest.raises(ValueError, match="byte limit"):
        _apply(lake, other, more)
    assert len(_assertions(lake[0])) == 1


def test_finite_registration_keeps_verified_projection_and_unknown_date(lake):
    catalog, reader, ref, original = lake
    _apply(lake, {"document_kind": "equity_offering_prospectus", "published_date": None})
    before = _assertions(catalog)
    for _ in range(2):
        catalog.register_sources(root_id="company_raw", relative_paths={original.relative_to(catalog.config.roots[0].path).as_posix()})
        described = reader.describe_version(ref)
        assert described["document_kind"] == "equity_offering_prospectus"
        assert described["published_date"] is None
    assert _assertions(catalog) == before


def test_new_conflicting_capture_is_diagnostic_after_source_fact_correction(lake):
    catalog, reader, ref, original = lake
    _apply(lake, {"market": "CN", "security_id": "002643"})
    sidecar = original.with_suffix(".pdf.source.json")
    data = json.loads(sidecar.read_text(encoding="utf-8"))
    data["market"] = "US"
    sidecar.write_text(json.dumps(data), encoding="utf-8")
    catalog.register_sources(root_id="company_raw", relative_paths={original.relative_to(catalog.config.roots[0].path).as_posix()})
    assert reader.describe_version(ref)["market"] == "CN"
    assert reader.metadata_diagnostics(ref)["conflicted_fields"]
    assert reader.open_version(ref).data == original.read_bytes()


def test_corrected_unknown_publication_cannot_match_an_asof_filing(lake):
    _apply(lake, {"entity": "Acme", "security_id": "002643", "market": "CN",
                  "document_kind": "annual_report", "published_date": None})
    request = SourceRequest(entity="Acme", security_id="002643", market="CN",
                            document_kind="annual_report", fiscal_year=2023,
                            as_of_date="2024-01-01")
    assert lake[1].query_local(request).matches == ()


def test_unknown_publication_never_returns_from_capture_after_later_correction(lake):
    catalog, reader, ref, original = lake
    first = _apply(lake, {"published_date": None})
    second = _apply(lake, {"security_id": "002867"})
    assert reader.describe_version(ref)["published_date"] is None
    assert reader.describe_candidate(ref)["capture_ready"] is False
    assertions = _assertions(catalog)
    assert len(assertions) == 2
    latest = next(x for x in assertions if x["assertion_id"] == second["assertion_id"])
    assert latest["supersedes_assertion_id"] == first["assertion_id"]
    assert json.loads(latest["evidence_json"])["source_fact_patch"]["published_date"] is None
    assert reader.open_version(ref, purpose="filing_reuse").data == original.read_bytes()


@pytest.mark.parametrize("facts", [
    {}, {"arbitrary_permission": True}, {"published_date": "2022-02-30"},
    {"fiscal_year": True}, {"security_id": "Acme/display"}, {"market": "OTHER"},
    {"document_kind": "made_up"}, {"source_url": "relative.pdf"},
])
def test_invalid_facts_are_refused_before_any_write(lake, facts):
    with pytest.raises(ValueError):
        _apply(lake, facts)
    assert _assertions(lake[0]) == []


@pytest.mark.parametrize("evidence", [{}, {"security_id": {"locator": "", "value": "002643"}},
                                      {"security_id": {"locator": "cover:p1", "value": "002867"}}])
def test_missing_or_disagreeing_field_evidence_is_not_verified(lake, evidence):
    with pytest.raises(ValueError):
        _apply(lake, {"security_id": "002643"}, evidence)
    assert _assertions(lake[0]) == []


def test_changed_original_and_wrong_reference_are_refused(lake):
    catalog, _, ref, original = lake
    with pytest.raises(SourceReadError, match="expected_version_mismatch"):
        catalog.record_source_facts(ref=replace(ref, content_sha256="0" * 64),
                                    facts={"security_id": "002643"}, evidence=_evidence({"security_id": "002643"}))
    original.write_bytes(b"%PDF-1.4 different original")
    with pytest.raises(SourceReadError):
        _apply(lake, {"security_id": "002643"})
    assert _assertions(catalog) == []


def test_retired_source_needs_actual_restore_and_preserves_audit(lake):
    catalog, _, ref, _ = lake
    retire_document(catalog.store, document_id=ref.document_id, reason="legacy lacks URL", created_by="fixture")
    with pytest.raises(SourceReadError, match="source_not_active"):
        _apply(lake, {"security_id": "002643"})
    assert _assertions(catalog) == []
    restore_document(catalog.store, document_id=ref.document_id, reason="actual hash; old URL gate retired", created_by="automated-source-quality")
    _apply(lake, {"security_id": "002643"})
    assert len(catalog.reader.fetchall("SELECT * FROM document_retire_audit")) == 1
    assert len(catalog.reader.fetchall("SELECT * FROM document_restore_audit")) == 1


def test_projection_failure_rolls_back_appended_assertion(lake, monkeypatch):
    catalog, _, ref, _ = lake
    before = dict(catalog.reader.fetchone("SELECT * FROM documents WHERE document_id=?", (ref.document_id,)))
    original = catalog.store.transaction
    class FailingConnection:
        def __init__(self, connection):
            self.connection = connection
        def execute(self, sql, parameters=()):
            if sql.startswith("UPDATE documents"):
                raise sqlite3.OperationalError("projection fault")
            return self.connection.execute(sql, parameters)
    @contextmanager
    def fail_projection():
        with original() as connection:
            yield FailingConnection(connection)
    monkeypatch.setattr(catalog.store, "transaction", fail_projection)
    with pytest.raises(sqlite3.OperationalError, match="projection fault"):
        _apply(lake, {"document_kind": "equity_offering_prospectus"})
    assert _assertions(catalog) == []
    assert dict(catalog.reader.fetchone("SELECT * FROM documents WHERE document_id=?", (ref.document_id,))) == before


def test_literal_cli_records_and_repeats_one_source(lake, tmp_path):
    catalog, reader, ref, _ = lake
    config = tmp_path / "catalog.yaml"
    config.write_text(yaml.safe_dump({"schema_version": "1.0", "catalog_dir": str(catalog.config.catalog_dir),
                                     "roots": [{"root_id": "company_raw", "kind": "company_raw", "path": str(tmp_path / "companies")}] }), encoding="utf-8")
    request = tmp_path / "facts.json"
    facts = {"security_id": "002643", "published_date": None}
    request.write_text(json.dumps({"source_ref": asdict(ref), "facts": facts, "evidence": _evidence(facts)}), encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / "src"))
    command = [sys.executable, "-B", "-m", "company_wiki.source_catalog.cli", "--config", str(config), "source-facts", "--request", str(request)]
    for expected in ("recorded", "unchanged"):
        result = subprocess.run(command, env=env, text=True, capture_output=True, timeout=25)
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["status"] == expected
    assert reader.describe_version(ref)["security_id"] == "002643"
    assert len(_assertions(catalog)) == 1
