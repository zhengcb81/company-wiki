"""S5 source-quality states without permanent whole-document extraction."""

from __future__ import annotations

from contextlib import closing, contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from company_wiki.automation.models import canonical_json
from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
from company_wiki.source_catalog.extraction_quality import (
    ExtractionQualityIntegrityError, ExtractionQualityService,
)
from company_wiki.source_catalog.narrative_artifact_store import NarrativeArtifactDraft
from support.legacy_source_artifact_fixture import legacy_normalize
from support.narrative_transport_fixture import published_fixture


def _identity(root: Path):
    return tuple(
        (p.relative_to(root).as_posix(), p.stat().st_size,
         p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest())
        for p in sorted(root.rglob("*")) if p.is_file()
    )


@contextmanager
def _unprocessed(tmp_path: Path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "report.txt").write_text("Company launched a new product.", encoding="utf-8")
    catalog = SourceCatalog(CatalogConfig(
        project_root=tmp_path, catalog_dir=tmp_path / "catalog",
        roots=(RootSpec("raw", raw, "directory"),),
    ))
    try:
        catalog.scan()
        row = catalog.store.fetchone("SELECT document_id FROM documents LIMIT 1")
        yield catalog, row["document_id"]
    finally:
        catalog.close()


def _assess(fixture, *, limit=100):
    return ExtractionQualityService(fixture.catalog.config.database_path).assess(
        document_id=fixture.source_ref.document_id, locator_limit=limit,
    ).to_dict()


def _publish_changed(fixture, payload):
    old = fixture.version
    draft = NarrativeArtifactDraft(
        effect_id="quality-second", work_key="d" * 64,
        document_id=old.document_id, source_id=old.source_id,
        source_sha256=old.source_sha256, producer_name=old.producer_name,
        producer_version=old.producer_version, policy_sha256=old.policy_sha256,
        selection_status=payload["selection"]["status"],
        quality_status=payload["quality_status"], metadata_json=old.metadata_json,
        created_at="2026-10-01T00:00:00Z",
    )
    version = fixture.artifacts.prepare(draft, canonical_json(payload).encode("utf-8"))
    return fixture.artifacts.activate(
        draft.effect_id, verified_after_hash=version.content_sha256,
        activated_at="2026-10-01T00:00:01Z",
    )


def test_unrequested_raw_is_metadata_only_without_conversion_or_writes(tmp_path):
    with _unprocessed(tmp_path) as (catalog, document_id):
        before = _identity(tmp_path)
        payload = ExtractionQualityService(catalog.config.database_path).assess(
            document_id=document_id,
        ).to_dict()
        assert payload["schema_version"] == "2.0.0"
        assert payload["quality_state"] == "metadata_only"
        assert payload["reason_codes"] == ["not_processed"]
        assert payload["extraction"]["basis"] == "metadata_only"
        assert payload["extraction"]["raw_bytes_verified"] is False
        assert payload["counts"]["spans"] == 0
        assert not payload["locator_references"]
        assert _identity(tmp_path) == before
        assert not (catalog.config.catalog_dir / "derived").exists()


def test_retired_extraction_ignores_unconsumable_old_spans(tmp_path):
    with _unprocessed(tmp_path) as (catalog, document_id):
        legacy_normalize(catalog)
        with catalog.store.transaction() as connection:
            connection.execute("UPDATE artifacts SET status='retired'")
            connection.execute("UPDATE evidence_spans SET span_json='{}'")
        before = _identity(tmp_path)
        payload = ExtractionQualityService(catalog.config.database_path).assess(
            document_id=document_id,
        ).to_dict()
        assert payload["quality_state"] == "metadata_only"
        assert payload["reason_codes"] == ["legacy_extraction_retired"]
        assert payload["normalization"]["artifact_status"] == "retired"
        assert payload["counts"]["spans"] == 0
        assert _identity(tmp_path) == before


@pytest.mark.parametrize("legacy", [False, True])
def test_visible_selected_bundle_is_used_without_legacy_span_reads(
    tmp_path, monkeypatch, legacy,
):
    with published_fixture(tmp_path) as fixture:
        if legacy:
            legacy_normalize(fixture.catalog)
            with fixture.catalog.store.transaction() as connection:
                connection.execute("UPDATE evidence_spans SET span_json='{}'")
        # Complete the fixture writer/read lifecycle before a strict static
        # filesystem snapshot. Active WAL read marks are covered separately.
        fixture.catalog.close()
        with closing(sqlite3.connect(fixture.catalog.config.database_path)) as checkpoint:
            assert checkpoint.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0] == 0
        assert not Path(str(fixture.catalog.config.database_path) + "-wal").exists()
        before = _identity(fixture.root)
        statements = []
        real_connect = sqlite3.connect

        def traced_connect(*args, **kwargs):
            connection = real_connect(*args, **kwargs)
            connection.set_trace_callback(statements.append)
            return connection

        monkeypatch.setattr(sqlite3, "connect", traced_connect)
        payload = _assess(fixture, limit=1)
        bundle = json.loads(fixture.payload)
        assert payload["quality_state"] == "usable"
        assert payload["extraction"]["basis"] == "selected_narrative"
        assert payload["extraction"]["selection_status"] == "selected"
        assert payload["extraction"]["artifact_version_id"] == fixture.version.artifact_version_id
        assert payload["extraction"]["coverage_complete"] is True
        assert payload["extraction"]["raw_bytes_verified"] is False
        assert payload["counts"]["spans"] == len(bundle["evidence_spans"])
        assert len(payload["locator_references"]) == 1
        expected = sorted(bundle["evidence_spans"], key=lambda s: (s["locator"], s["span_id"]))
        assert payload["locator_references"][0]["span_id"] == expected[0]["span_id"]
        assert not any("FROM evidence_spans" in s for s in statements)
        assert not any(s.lstrip().upper().startswith(
            ("INSERT", "UPDATE", "DELETE", "CREATE", "REPLACE", "DROP", "ALTER"),
        ) for s in statements)
        assert _identity(fixture.root) == before
        encoded = json.dumps(payload)
        for forbidden in ('"raw_text"', '"structured_value"', '"absolute_path"', '"summary"'):
            assert forbidden not in encoded


def test_partial_narrative_is_a_coverage_diagnostic_without_manual_gate(tmp_path):
    with published_fixture(tmp_path) as fixture:
        payload = json.loads(fixture.payload)
        payload["selection"]["status"] = "partial"
        payload["selection"]["coverage_complete"] = False
        payload["quality_status"] = "needs_review"
        _publish_changed(fixture, payload)
        result = _assess(fixture)
        assert result["quality_state"] == "review_required"
        assert "narrative_partial" in result["reason_codes"]
        assert "narrative_coverage_incomplete" in result["reason_codes"]
        assert result["counts"]["usable_output_spans"] > 0
        assert result["extraction"]["coverage_complete"] is False
        assert "authorization" not in json.dumps(result)


def test_policy_skip_is_not_unavailable_or_fabricated_parsed_content(tmp_path):
    with published_fixture(tmp_path, kind="skip") as fixture:
        result = _assess(fixture)
        assert result["quality_state"] == "skipped_no_narrative"
        assert result["reason_codes"] == ["skipped_no_narrative"]
        assert result["extraction"]["selection_status"] == "skipped_no_narrative"
        assert result["counts"]["spans"] == 0
        assert result["counts"]["parsed"] == 0
        assert not result["locator_references"]


def test_prepared_bundle_does_not_make_quality_usable(tmp_path):
    with published_fixture(tmp_path, published=False) as fixture:
        result = _assess(fixture)
        assert result["quality_state"] == "metadata_only"
        assert result["extraction"]["artifact_version_id"] is None
        assert result["counts"]["spans"] == 0


@pytest.mark.parametrize("fault", ["object_bytes", "bundle_source", "policy_binding", "selection_binding"])
def test_corrupt_current_final_fails_instead_of_falling_back_to_legacy(tmp_path, fault):
    with published_fixture(tmp_path) as fixture:
        legacy_normalize(fixture.catalog)
        if fault == "object_bytes":
            path = fixture.catalog.config.catalog_dir / fixture.version.object_key
            path.write_bytes(b"X" * len(fixture.payload))
        elif fault == "bundle_source":
            payload = json.loads(fixture.payload)
            payload["source_ref"]["document_id"] = "urn:company-wiki:document:sha256:" + "0" * 64
            _publish_changed(fixture, payload)
        else:
            with fixture.catalog.store.transaction() as connection:
                if fault == "policy_binding":
                    connection.execute("UPDATE narrative_artifact_versions SET policy_sha256=?", ("0" * 64,))
                else:
                    connection.execute("UPDATE narrative_artifact_versions SET selection_status='partial'")
        with pytest.raises(ExtractionQualityIntegrityError, match="narrative"):
            _assess(fixture)


def test_missing_active_raw_is_unavailable_even_when_final_exists(tmp_path):
    with published_fixture(tmp_path) as fixture:
        with fixture.catalog.store.transaction() as connection:
            connection.execute("UPDATE locations SET location_status='missing'")
        result = _assess(fixture)
        assert result["quality_state"] == "unavailable"
        assert "no_active_source_location" in result["reason_codes"]


def test_active_wal_quality_sees_committed_facts_without_data_writes(tmp_path):
    with _unprocessed(tmp_path) as (catalog, document_id):
        with closing(sqlite3.connect(catalog.config.database_path)) as writer:
            writer.execute("UPDATE documents SET source_status='incomplete'")
            writer.commit()
            before = {item[0]: item[1:] for item in _identity(tmp_path)}
            assert "catalog/catalog.sqlite3-wal" in before
            result = ExtractionQualityService(catalog.config.database_path).assess(
                document_id=document_id,
            ).to_dict()
            assert result["source"]["source_status"] == "incomplete"
            assert result["quality_state"] == "metadata_only"
            assert "source_incomplete" in result["reason_codes"]
            after = {item[0]: item[1:] for item in _identity(tmp_path)}
            assert before.keys() == after.keys()
            # SQLite's shared-memory read marks coordinate live readers. Raw,
            # the database, WAL and every other persistent file are unchanged.
            before.pop("catalog/catalog.sqlite3-shm")
            after.pop("catalog/catalog.sqlite3-shm")
            assert before == after


def test_oversized_final_is_rejected_before_object_bytes_are_read(tmp_path, monkeypatch):
    from company_wiki.automation.narrative_contracts import BUNDLE_MAX_BYTES
    from company_wiki.source_catalog.narrative_artifact_store import LocalNarrativeObjectStore

    with published_fixture(tmp_path) as fixture:
        with fixture.catalog.store.transaction() as connection:
            connection.execute("UPDATE narrative_artifact_versions SET byte_size=?", (BUNDLE_MAX_BYTES + 1,))

        def forbidden_read(*args, **kwargs):
            pytest.fail("oversized object bytes must not be opened")

        monkeypatch.setattr(LocalNarrativeObjectStore, "read", forbidden_read)
        with pytest.raises(ExtractionQualityIntegrityError, match="narrative"):
            _assess(fixture)


def test_real_transcript_quality_cli_and_transport_restore_test_directory(tmp_path):
    original = (
        Path(__file__).resolve().parents[3] / "earnings-transcripts" / "earnings-transcripts"
        / "transcripts" / "MSFT" / "MSFT_Q4_2026_earnings_call.txt"
    )
    data = original.read_bytes()
    digest = "4ac3b4f0fa1be928b56b4ef9775cac694a1712d46785bb1fa28d2a6a68d7852a"
    assert hashlib.sha256(data).hexdigest() == digest
    baseline = _identity(tmp_path)
    with published_fixture(tmp_path, source_spec={
        "data": data, "title": "MSFT Q4 2026 earnings call",
    }) as fixture:
        cli = subprocess.run([
            sys.executable, "-m", "company_wiki.source_catalog.cli",
            "--config", str(fixture.config_path), "extraction-quality",
            "--source-id", fixture.source_ref.source_id, "--locator-limit", "2",
        ], capture_output=True, timeout=60, check=False)
        assert cli.returncode == 0, cli.stderr.decode("utf-8")
        result = json.loads(cli.stdout)
        assert result["quality_state"] in {"usable", "review_required"}
        assert result["extraction"]["basis"] == "selected_narrative"
        assert result["counts"]["spans"] == len(json.loads(fixture.payload)["evidence_spans"])
        assert len(result["locator_references"]) == 2

        transport = [sys.executable, "-m", "company_wiki.source_catalog.narrative_transport_cli",
                     "--config", str(fixture.config_path)]
        reference = subprocess.run(
            [*transport, "--operation", "reference"],
            input=canonical_json({
                "schema_version": "narrative-reference-request/1",
                "source_ref": fixture.source_ref.to_dict(),
            }).encode("utf-8"), capture_output=True, timeout=60, check=False,
        )
        assert reference.returncode == 0, reference.stderr.decode("utf-8")
        request = {
            "schema_version": "narrative-read-request/1",
            "narrative_ref": json.loads(reference.stdout),
            "as_of_date": "2026-10-05", "expected_source": fixture.expected_source,
        }
        replay = subprocess.run(
            transport, input=canonical_json(request).encode("utf-8"),
            capture_output=True, timeout=60, check=False,
        )
        assert replay.returncode == 0, replay.stderr.decode("utf-8")
        assert replay.stdout == fixture.payload
        assert json.loads(replay.stderr)["replay_status"] == "verified"
        assert hashlib.sha256(fixture.raw_path.read_bytes()).hexdigest() == digest
    assert _identity(tmp_path) == baseline
    assert hashlib.sha256(original.read_bytes()).hexdigest() == digest
