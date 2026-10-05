"""Runtime retirement and raw-only fingerprint responsibilities."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
from company_wiki.source_catalog import normalizer


@pytest.mark.parametrize(
    "module", ["summarizer", "llm_summarizer", "section_extractor", "normalized_artifact_reader"]
)
def test_whole_document_generators_are_not_runtime_modules(module):
    assert importlib.util.find_spec(f"company_wiki.source_catalog.{module}") is None


def test_raw_parser_does_not_offer_a_persistent_whole_document_writer():
    assert not hasattr(normalizer, "normalize_catalog")
    assert not hasattr(normalizer, "_frontmatter")


def test_public_import_does_not_load_historical_generators(tmp_path):
    source_root = Path(__file__).resolve().parents[2] / "src"
    environment = dict(os.environ, PYTHONPATH=str(source_root), PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run(
        [sys.executable, "-B", "-c", "import json,sys; import company_wiki.source_catalog as c; "
         "print(json.dumps({'historical': [m for m in sys.modules if m.startswith('support.') "
         "or m.rsplit('.',1)[-1] in ('llm_summarizer','summarizer','section_extractor',"
         "'normalized_artifact_reader')], 'exports': c.__all__}))"],
        env=environment, cwd=tmp_path, capture_output=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["historical"] == []
    assert "LLMSummaryError" not in payload["exports"]
    assert "SectionSlice" not in payload["exports"]
    assert list(tmp_path.iterdir()) == []


@pytest.fixture
def catalog(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "healthy.txt").write_text("New business entered the overseas market.", encoding="utf-8")
    (raw / "changed.txt").write_text("Business expansion is under way.", encoding="utf-8")
    instance = SourceCatalog(CatalogConfig(
        project_root=tmp_path, catalog_dir=tmp_path / "catalog",
        roots=(RootSpec("fixture", raw, "directory"),),
    ))
    instance.scan()
    try:
        yield instance, raw
    finally:
        instance.close()


def _assert_no_whole_document_storage(catalog):
    assert catalog.store.fetchone("SELECT COUNT(*) AS n FROM artifacts")["n"] == 0
    assert catalog.store.fetchone("SELECT COUNT(*) AS n FROM evidence_spans")["n"] == 0
    assert not catalog.config.derived_dir.exists()
    parser_tmp = catalog.config.catalog_dir / "parser_tmp"
    assert not parser_tmp.exists() or list(parser_tmp.iterdir()) == []


def _assert_one_source_failed(catalog):
    rows = catalog.store.fetchall(
        "SELECT status,last_error_code FROM document_fingerprint_state ORDER BY status"
    )
    assert [row["status"] for row in rows] == ["completed", "retryable_failed"]
    assert rows[1]["last_error_code"] == "SourceManifestMismatchError"
    assert catalog.store.fetchone(
        "SELECT COUNT(*) AS n FROM documents WHERE text_fingerprint IS NOT NULL"
    )["n"] == 1
    _assert_no_whole_document_storage(catalog)


def test_fingerprints_use_raw_without_recreating_derived_storage(catalog):
    instance, raw = catalog
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in raw.iterdir()}
    report = instance.backfill_text_fingerprints()
    assert (report.completed, report.failed) == (2, 0)
    assert instance.backfill_text_fingerprints().completed == 0
    rows = instance.store.fetchall("SELECT text_fingerprint FROM documents")
    assert all(len(row["text_fingerprint"]) == 64 for row in rows)
    assert before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in raw.iterdir()}
    _assert_no_whole_document_storage(instance)


def test_changed_raw_is_not_fingerprinted_under_an_old_source(catalog):
    instance, raw = catalog
    path = raw / "changed.txt"
    # Same-size replacement must be detected by the bytes SHA, not only stat.
    original = path.read_bytes()
    path.write_bytes(b"X" * len(original))
    report = instance.backfill_text_fingerprints()
    assert (report.completed, report.failed) == (1, 1)
    _assert_one_source_failed(instance)


def test_parser_time_replacement_cannot_commit_a_stale_fingerprint(catalog, monkeypatch):
    instance, _raw = catalog

    def replaced_during_parse(path, manifest, sidecar, **_options):
        parsed = normalizer._normalize_source(path, manifest, sidecar)
        if path.name == "changed.txt":
            path.write_bytes(b"X" * len(path.read_bytes()))
        return parsed

    monkeypatch.setattr(normalizer, "_run_parser_isolated", replaced_during_parse)
    report = instance.backfill_text_fingerprints()
    assert (report.completed, report.failed) == (1, 1)
    _assert_one_source_failed(instance)


def test_manifest_from_another_source_cannot_supply_a_fingerprint(catalog, monkeypatch):
    instance, _raw = catalog
    healthy_manifest = instance.store.fetchone(
        "SELECT manifest_json FROM locations WHERE relative_path='healthy.txt'"
    )["manifest_json"]
    # Keep the changed file's path so location/size checks alone cannot validate identity.
    changed_manifest = json.loads(instance.store.fetchone(
        "SELECT manifest_json FROM locations WHERE relative_path='changed.txt'"
    )["manifest_json"])
    wrong = json.loads(healthy_manifest)
    wrong["original_path"] = changed_manifest["original_path"]
    with instance.store.transaction() as connection:
        connection.execute(
            "UPDATE locations SET manifest_json=? WHERE relative_path='changed.txt'",
            (json.dumps(wrong),),
        )
    called = []

    def parser(path, manifest, sidecar, **_options):
        called.append(path.name)
        return normalizer._normalize_source(path, manifest, sidecar)

    monkeypatch.setattr(normalizer, "_run_parser_isolated", parser)
    report = instance.backfill_text_fingerprints()
    assert (report.completed, report.failed) == (1, 1)
    assert called == ["healthy.txt"]
    _assert_one_source_failed(instance)
