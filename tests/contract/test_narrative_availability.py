"""Real public narrative reads reuse source-owned exact-version availability.

No provider/model/network. Each fixture restores its entire scratch subtree.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

from company_wiki.automation import narrative_transport as transport_module
from company_wiki.automation.narrative_transport import NarrativeTransportReader
from company_wiki.automation.narrative_transport_contracts import (
    MAX_RECEIPT_BYTES, NarrativeReadRequest,
)
from company_wiki.narrative_subject import NarrativeSubjectRef
from company_wiki.source_catalog import source_reader as reader_module
from company_wiki.source_catalog.source_availability import (
    verified_availability_evidence, verified_open_observation,
)
from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader
from contract.test_narrative_transport_cli import _cli, _reference, READ_RECEIPT_KEYS
from integration.test_official_json_transport_subject import (
    owned_state, open_verified_projection, publish,
)
from support.narrative_transport_fixture import published_fixture


def raw_ref(fixture):
    return SourceRef(**fixture.source_ref.to_dict())


def capture(ref, *, at="2026-08-01T12:00:00Z"):
    receipt = {
        "schema_version": "1.0", "candidate_id": "offline-accession",
        "provider": "sec", "provider_document_id": "offline-accession",
        "source_url": "https://www.sec.gov/Archives/offline.txt",
        "staged_path": "staging/offline.txt", "content_sha256": ref.content_sha256,
        "byte_size": ref.byte_size, "mime_type": ref.mime_type,
        "retrieved_at": at, "http_status": 200, "adapter_name": "offline-reader",
        "adapter_version": "1.0.0", "etag": None, "last_modified": None,
    }
    return {
        "schema_version": "1.0", "request_id": "offline-source-request",
        **{key: receipt[key] for key in (
            "provider", "provider_document_id", "source_url", "content_sha256",
            "byte_size", "mime_type", "retrieved_at", "adapter_name", "adapter_version",
        )},
        "candidate": {key: receipt[key] for key in ("provider", "provider_document_id", "source_url")},
        "receipt": receipt,
    }


def set_facts(fixture, *, published=None, observation=None):
    evidence = {"value": published, "locator": "fixture:explicit-publication"}
    if observation is not None:
        evidence.update(observation)
    fixture.catalog.record_source_facts(
        ref=raw_ref(fixture), facts={"published_date": published},
        evidence={"published_date": evidence},
    )


def owner_proof(fixture, basis):
    ref = raw_ref(fixture)
    if basis == "prior_verified_capture":
        set_facts(fixture, observation={"availability_capture": capture(ref)})
    else:
        opened = fixture.reader.open_version(ref, purpose="source_export")
        observation = verified_open_observation(SimpleNamespace(ref=ref, data=opened.data))
        set_facts(fixture, observation={"verified_open": observation})
    proof = verified_availability_evidence(fixture.catalog, ref)
    assert proof is not None and proof["basis"] == basis
    return proof


def request(fixture, reference, cutoff="2026-09-01"):
    return {
        "schema_version": "narrative-read-request/1", "narrative_ref": reference,
        "as_of_date": cutoff, "expected_source": dict(fixture.expected_source),
    }


def raw_cli(fixture):
    ref = raw_ref(fixture)
    return subprocess.run(
        [sys.executable, "-m", "company_wiki.source_catalog.source_reader_cli",
         "--config", str(fixture.config_path), "--document-id", ref.document_id,
         "--source-id", ref.source_id, "--content-sha256", ref.content_sha256,
         "--purpose", "source_export", "--include-availability-evidence"],
        capture_output=True, check=False, timeout=30, cwd=fixture.root, env={
            **os.environ, "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHON_DOTENV_DISABLED": "1", "COMPANY_WIKI_NETWORK": "blocked",
        },
    )


def database_bytes(fixture):
    return {
        path.relative_to(fixture.catalog.config.catalog_dir).as_posix(): path.read_bytes()
        for path in fixture.catalog.config.catalog_dir.rglob("*")
        if path.is_file() and path.suffix in {".db", ".sqlite", ".sqlite3"}
        or path.is_file() and path.name.endswith("-wal")
    }


@pytest.mark.parametrize("kind", ["pdf", "json"])
@pytest.mark.parametrize("basis", ["prior_verified_capture", "current_verified_open"])
def test_actual_cli_null_publication_reuses_the_same_owner_proof_and_bundle(tmp_path, kind, basis):
    baseline = tuple(tmp_path.iterdir())
    with published_fixture(tmp_path, kind=kind) as fixture:
        proof = owner_proof(fixture, basis)
        reference = _reference(fixture)
        frozen_artifact = fixture.payload
        manifest = fixture.reader.describe_version(raw_ref(fixture))
        assert manifest["published_date"] is None
        before = database_bytes(fixture)
        raw = raw_cli(fixture)
        assert raw.returncode == 0, raw.stderr.decode()
        receipt22 = json.loads(raw.stderr)
        assert raw.stdout == fixture.raw_bytes and receipt22["schema_version"] == "2.2"
        assert receipt22["availability_evidence"] == proof
        result = _cli(fixture, "read", request(fixture, reference, proof["available_by"]))
        assert result.returncode == 0, result.stderr.decode()
        receipt = json.loads(result.stderr)
        assert set(receipt) == READ_RECEIPT_KEYS | {"availability_evidence"}
        assert receipt["availability_evidence"] == receipt22["availability_evidence"]
        assert receipt["manifest"]["published_date"] is None
        assert receipt["manifest"]["retrieved_at"] == manifest["retrieved_at"]
        assert result.stdout == frozen_artifact
        assert hashlib.sha256(result.stdout).hexdigest() == reference["artifact_sha256"]
        assert len(result.stderr) <= MAX_RECEIPT_BYTES
        assert b"availability_evidence" not in frozen_artifact
        assert fixture.reader.describe_version(raw_ref(fixture)) == manifest
        assert _reference(fixture) == reference
        assert database_bytes(fixture) == before
    assert tuple(tmp_path.iterdir()) == baseline


@pytest.mark.parametrize("case", [
    "missing", "wrong_sha", "late_capture", "schema", "wrong_type",
    "bare_first_seen", "future_publication", "invalid_publication",
])
def test_real_cli_proof_never_manufactures_historical_eligibility(tmp_path, case):
    with published_fixture(tmp_path, kind="json") as fixture:
        payload = capture(raw_ref(fixture))
        if case == "wrong_sha":
            payload["receipt"]["content_sha256"] = "a" * 64
        elif case == "late_capture":
            payload["receipt"]["retrieved_at"] = payload["retrieved_at"] = "2026-09-02T00:00:00Z"
        elif case == "schema":
            payload["receipt"]["schema_version"] = "999"
        elif case == "wrong_type":
            payload["receipt"]["http_status"] = "200"
        observation = {"availability_capture": payload}
        if case == "missing":
            observation = None
        if case == "bare_first_seen":
            observation = {"first_seen_at": "2026-08-01", "mtime": "2026-08-01"}
        set_facts(fixture, published="2026-09-02" if case == "future_publication" else None,
                  observation=observation)
        if case == "invalid_publication":
            with fixture.catalog.store.transaction() as connection:
                connection.execute("UPDATE documents SET published_date='2026-02-30'")
                connection.execute("UPDATE source_metadata_assertions SET published_at='2026-02-30'")
                rows = connection.execute(
                    "SELECT assertion_id,evidence_json FROM source_metadata_assertions"
                ).fetchall()
                for row in rows:
                    evidence = json.loads(row["evidence_json"])
                    evidence["source_fact_patch"]["published_date"] = "2026-02-30"
                    evidence["source_fact_evidence"]["published_date"]["value"] = "2026-02-30"
                    connection.execute(
                        "UPDATE source_metadata_assertions SET evidence_json=? WHERE assertion_id=?",
                        (json.dumps(evidence), row["assertion_id"]),
                    )
            assert fixture.reader.describe_version(raw_ref(fixture))["published_date"] == "2026-02-30"
        reference = _reference(fixture)
        response = _cli(fixture, "read", request(fixture, reference))
        assert response.returncode == 2 and response.stdout == b""
        reason = json.loads(response.stderr)["reason"]
        expected = {
            "future_publication": "source_after_as_of",
            "invalid_publication": "source_publication_invalid",
        }.get(case, "source_publication_unknown")
        assert reason == expected
        assert fixture.raw_path.read_bytes() == fixture.raw_bytes


def test_known_publication_controls_cutoff_even_when_capture_is_later(tmp_path):
    with published_fixture(tmp_path, kind="pdf") as fixture:
        set_facts(fixture, published="2026-08-01", observation={
            "availability_capture": capture(raw_ref(fixture), at="2026-09-02T00:00:00Z")})
        response = _cli(fixture, "read", request(fixture, _reference(fixture), "2026-08-01"))
        assert response.returncode == 0, response.stderr.decode()
        receipt = json.loads(response.stderr)
        assert receipt["manifest"]["published_date"] == "2026-08-01"
        assert response.stdout == fixture.payload


def test_current_mode_keeps_null_publication_without_inventing_a_proof(tmp_path):
    with published_fixture(tmp_path) as fixture:
        set_facts(fixture)
        response = _cli(fixture, "read", request(fixture, _reference(fixture), None))
        assert response.returncode == 0, response.stderr.decode()
        receipt = json.loads(response.stderr)
        assert receipt["as_of_date"] is None and receipt["manifest"]["published_date"] is None
        assert "availability_evidence" not in receipt


@pytest.mark.parametrize("injected", [
    {"schema_version": "999"},
    {"schema_version": "source-availability-evidence/1", "path": "physical.pdf"},
    {"schema_version": "source-availability-evidence/1", "source_sha256": "a" * 64},
    "first_seen_at",
])
def test_caller_cannot_supply_a_proof_or_extra_path_in_a_read_request(tmp_path, injected):
    with published_fixture(tmp_path) as fixture:
        value = request(fixture, _reference(fixture))
        value["availability_evidence"] = injected
        response = _cli(fixture, "read", value)
        assert response.returncode == 2 and response.stdout == b""
        assert json.loads(response.stderr)["reason"] == "invalid_request"


@pytest.mark.parametrize("kind", ["pdf", "json"])
def test_one_verified_original_buffer_one_owner_lookup_no_new_fact_writer(tmp_path, monkeypatch, kind):
    with published_fixture(tmp_path, kind=kind) as fixture:
        proof = owner_proof(fixture, "prior_verified_capture")
        transport = NarrativeTransportReader(fixture.artifacts, fixture.reader)
        reference = transport.reference(fixture.source_ref)
        real_read = reader_module._read_verified_bytes
        observations = []

        def counted_read(*args, **kwargs):
            observations.append("original")
            return real_read(*args, **kwargs)

        def lookup(catalog, ref):
            observations.append("proof")
            assert observations == ["original", "proof"]
            return verified_availability_evidence(catalog, ref)

        def forbidden(*args, **kwargs):
            pytest.fail("narrative reads must not create observations or source facts")

        monkeypatch.setattr(reader_module, "_read_verified_bytes", counted_read)
        monkeypatch.setattr(transport_module, "verified_availability_evidence", lookup, raising=False)
        monkeypatch.setattr(fixture.catalog, "record_source_facts", forbidden)
        result = transport.read(NarrativeReadRequest.from_dict(
            request(fixture, reference.to_dict(), proof["available_by"])))
        assert result.receipt["availability_evidence"] == proof
        assert observations == ["original", "proof"] and result.data == fixture.payload


def test_new_owner_metadata_changes_only_the_receipt_not_frozen_artifact(tmp_path):
    with published_fixture(tmp_path) as fixture:
        first = owner_proof(fixture, "prior_verified_capture")
        reference = _reference(fixture)
        before = _cli(fixture, "read", request(fixture, reference))
        assert before.returncode == 0, before.stderr.decode()
        set_facts(fixture, observation={
            "availability_capture": capture(raw_ref(fixture), at="2026-08-03T00:00:00Z")})
        after = _cli(fixture, "read", request(fixture, reference))
        assert after.returncode == 0, after.stderr.decode()
        assert before.stdout == after.stdout == fixture.payload
        assert json.loads(before.stderr)["availability_evidence"] == first
        assert json.loads(after.stderr)["availability_evidence"]["available_by"] == "2026-08-03"
        assert _reference(fixture) == reference


def test_projected_two_parents_cannot_borrow_one_raw_proof(tmp_path, monkeypatch):
    with owned_state(tmp_path) as state:
        subject = state.subjects[0]
        _, generation, payload = publish(state, subject, "w03-projected")
        reader = SourceVersionReader(state.catalog)
        first = SourceRef(**dict(state.refs[0]))
        opened = reader.open_version(first, purpose="source_export")
        state.catalog.record_source_facts(ref=first, facts={"published_date": None}, evidence={
            "published_date": {"value": None, "locator": "fixture:source-proof",
                               "verified_open": verified_open_observation(SimpleNamespace(ref=first, data=opened.data))}})
        assert verified_availability_evidence(state.catalog, first) is not None

        def load(ref):
            view = open_verified_projection(state.catalog, projection_id=subject.item_key,
                                            expected_projection_sha256=subject.subject_sha256)
            assert NarrativeSubjectRef.from_subject(view.subject) == ref
            return view

        def forbidden(*args, **kwargs):
            pytest.fail("projected receipts do not accept a root raw availability proof")

        monkeypatch.setattr(transport_module, "verified_availability_evidence", forbidden, raising=False)
        transport = NarrativeTransportReader(state.artifacts, reader, projection_ref_resolver=load)
        compact = NarrativeSubjectRef.from_subject(subject)
        reference = transport.reference_subject_ref(compact, generation_sha256=generation)
        value = {"schema_version": "narrative-read-request/3", "narrative_ref": reference.to_dict(),
                 "as_of_date": "2026-10-08", "expected_issuer": {"provider_company_id": 1}}
        response = transport.read(NarrativeReadRequest.from_dict(value))
        assert response.data == payload and response.receipt["schema_version"] == "narrative-read-receipt/3"
        assert response.receipt["parent_count"] == 2 and "availability_evidence" not in response.receipt
        forged = deepcopy(value)
        forged["availability_evidence"] = {"source_sha256": first.content_sha256}
        with pytest.raises(ValueError):
            NarrativeReadRequest.from_dict(forged)
        originals = [p for p in (state.root / "companies").rglob("*.json")
                     if not p.name.endswith(".source.json")]
        second = next(p for p in originals if hashlib.sha256(p.read_bytes()).hexdigest()
                      == state.refs[1]["content_sha256"])
        before = second.read_bytes()
        try:
            second.write_bytes(opened.data)
            with pytest.raises(ValueError):
                transport.read(NarrativeReadRequest.from_dict(value))
        finally:
            second.write_bytes(before)
