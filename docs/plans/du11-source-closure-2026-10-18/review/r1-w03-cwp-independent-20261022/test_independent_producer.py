"""Non-author review of W03 producer: finite independent controls, no API."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from types import ModuleType

import pytest

REPO = Path(os.environ["W03_CWP_CODE_ROOT"]).resolve()
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tests"))
from company_wiki.automation import narrative_transport as transport  # noqa: E402
from company_wiki.automation.models import canonical_json  # noqa: E402
from company_wiki.automation.narrative_transport_contracts import (  # noqa: E402
    NarrativeReadRequest, NarrativeTransportError,
)
from company_wiki.narrative_subject import NarrativeSubjectRef  # noqa: E402
from company_wiki.source_catalog import source_reader as source_reader_module  # noqa: E402
from company_wiki.source_catalog.source_availability import (  # noqa: E402
    verified_availability_evidence, verified_open_observation,
)
from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader  # noqa: E402
from contract.test_narrative_availability import (  # noqa: E402
    capture, database_bytes, owner_proof, raw_ref, set_facts,
)
from integration.test_official_json_transport_subject import (  # noqa: E402
    owned_state, open_verified_projection, publish,
)
from support.narrative_transport_fixture import published_fixture  # noqa: E402

assert Path(transport.__file__).resolve() == REPO / "src/company_wiki/automation/narrative_transport.py"


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Independent review must stay offline")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


def _request(fixture, reference, as_of="2026-09-01"):
    return NarrativeReadRequest.from_dict({"schema_version": "narrative-read-request/1",
        "narrative_ref": reference.to_dict(), "as_of_date": as_of,
        "expected_source": deepcopy(fixture.expected_source)})


@pytest.mark.parametrize("kind", ["pdf", "json"])
def test_actual_owner_is_called_once_after_one_verified_original_and_cannot_write(tmp_path, monkeypatch, kind):
    before_tree = tuple(tmp_path.iterdir())
    with published_fixture(tmp_path, kind=kind) as fixture:
        proof = owner_proof(fixture, "prior_verified_capture")
        reader = transport.NarrativeTransportReader(fixture.artifacts, fixture.reader)
        reference = reader.reference(fixture.source_ref)
        real_read = source_reader_module._read_verified_bytes
        events = []
        def counted(*args, **kwargs):
            events.append("raw")
            return real_read(*args, **kwargs)
        def lookup(catalog, ref):
            assert catalog is fixture.catalog and ref == raw_ref(fixture)
            events.append("proof")
            assert events == ["raw", "proof"]
            result = verified_availability_evidence(catalog, ref)
            assert result == proof
            return result
        def forbidden(*args, **kwargs):
            raise AssertionError("Reads must not create new proof observations or source facts")
        monkeypatch.setattr(source_reader_module, "_read_verified_bytes", counted)
        monkeypatch.setattr(transport, "verified_availability_evidence", lookup)
        monkeypatch.setattr(fixture.catalog, "record_source_facts", forbidden)
        database_before = database_bytes(fixture)
        result = reader.read(_request(fixture, reference))
        assert events == ["raw", "proof"]
        assert result.data == fixture.payload
        assert result.receipt["manifest"]["published_date"] is None
        assert result.receipt["availability_evidence"] == proof
        assert database_bytes(fixture) == database_before
    assert tuple(tmp_path.iterdir()) == before_tree


def test_old_known_publication_receipt_and_body_are_exactly_unchanged(tmp_path, monkeypatch):
    name = "company_wiki.automation._w03_review_before"
    old = ModuleType(name)
    old.__package__ = "company_wiki.automation"
    old.__file__ = "<reviewed Git parent narrative_transport.py>"
    source = subprocess.check_output(["git", "show", "aff8be80^:src/company_wiki/automation/narrative_transport.py"], cwd=REPO)
    sys.modules[name] = old
    exec(compile(source, old.__file__, "exec"), old.__dict__)
    class FixedClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc).astimezone(tz)
    monkeypatch.setattr(transport, "datetime", FixedClock)
    monkeypatch.setattr(old, "datetime", FixedClock)
    monkeypatch.setattr(source_reader_module, "datetime", FixedClock)
    try:
        with published_fixture(tmp_path, kind="json") as fixture:
            assert verified_availability_evidence(fixture.catalog, raw_ref(fixture)) is None
            current = transport.NarrativeTransportReader(fixture.artifacts, fixture.reader)
            previous = old.NarrativeTransportReader(fixture.artifacts, fixture.reader)
            ref = current.reference(fixture.source_ref)
            request = _request(fixture, ref)
            result, before = current.read(request), previous.read(request)
            assert result.data == before.data == fixture.payload
            assert canonical_json(result.receipt) == canonical_json(before.receipt)
            assert "availability_evidence" not in result.receipt
    finally:
        sys.modules.pop(name, None)


def test_real_current_verified_owner_proof_keeps_null_publication_and_no_artifact_mutation(tmp_path):
    with published_fixture(tmp_path, kind="json") as fixture:
        proof = owner_proof(fixture, "current_verified_open")
        reader = transport.NarrativeTransportReader(fixture.artifacts, fixture.reader)
        reference = reader.reference(fixture.source_ref)
        baseline_db = database_bytes(fixture)
        result = reader.read(_request(fixture, reference, proof["available_by"]))
        assert result.receipt["availability_evidence"] == proof
        assert result.receipt["manifest"]["published_date"] is None
        assert result.data == fixture.payload and reader.reference(fixture.source_ref) == reference
        assert database_bytes(fixture) == baseline_db


def test_owner_metadata_refresh_does_not_change_artifact_or_generation_db_on_read(tmp_path):
    with published_fixture(tmp_path, kind="json") as fixture:
        owner_proof(fixture, "prior_verified_capture")
        reader = transport.NarrativeTransportReader(fixture.artifacts, fixture.reader)
        reference = reader.reference(fixture.source_ref)
        first = reader.read(_request(fixture, reference))
        set_facts(fixture, observation={"availability_capture": capture(raw_ref(fixture), at="2026-08-03T00:00:00Z")})
        after_metadata_write = database_bytes(fixture)
        second = reader.read(_request(fixture, reference))
        assert first.data == second.data == fixture.payload
        assert first.receipt["availability_evidence"]["available_by"] == "2026-08-01"
        assert second.receipt["availability_evidence"]["available_by"] == "2026-08-03"
        assert reader.reference(fixture.source_ref) == reference
        assert database_bytes(fixture) == after_metadata_write
        assert b"availability_evidence" not in fixture.payload


def test_valid_owner_proof_does_not_replace_the_requested_identity(tmp_path):
    with published_fixture(tmp_path, kind="json") as fixture:
        owner_proof(fixture, "prior_verified_capture")
        reader = transport.NarrativeTransportReader(fixture.artifacts, fixture.reader)
        request = {"schema_version": "narrative-read-request/1",
                   "narrative_ref": reader.reference(fixture.source_ref).to_dict(),
                   "as_of_date": "2026-09-01", "expected_source": deepcopy(fixture.expected_source)}
        request["expected_source"]["security_id"] = "OTHER"
        with pytest.raises(NarrativeTransportError, match="source_identity_mismatch"):
            reader.read(NarrativeReadRequest.from_dict(request))


@pytest.mark.parametrize("case,reason", [("wrong_sha", "source_publication_unknown"),
    ("late", "source_publication_unknown"), ("future_publication", "source_after_as_of"),
    ("invalid_publication", "source_publication_invalid")])
def test_published_owner_qualification_rejects_scope_or_time_conflicts(case, reason):
    manifest = {"published_date": None, "content_sha256": "a" * 64}
    proof = {"schema_version": "source-availability-evidence/1", "source_sha256": "a" * 64,
        "available_by": "2026-08-01", "basis": "prior_verified_capture",
        "evidence_ref": "urn:review:verified-capture", "locator": "receipt:review"}
    if case == "wrong_sha": proof["source_sha256"] = "b" * 64
    elif case == "late": proof["available_by"] = "2026-09-02"
    elif case == "future_publication": manifest["published_date"] = "2026-09-02"
    else: manifest["published_date"] = "2026-02-30"
    with pytest.raises(NarrativeTransportError, match=reason):
        transport._require_historical_source(manifest, "2026-09-01", availability_evidence=proof)


def test_current_unknown_no_proof_preserves_legacy_read_without_creating_observation(tmp_path, monkeypatch):
    with published_fixture(tmp_path, kind="txt") as fixture:
        set_facts(fixture)
        reader = transport.NarrativeTransportReader(fixture.artifacts, fixture.reader)
        reference = reader.reference(fixture.source_ref)
        baseline_db = database_bytes(fixture)
        def forbidden(*args, **kwargs):
            raise AssertionError("Current reads must not create a proof")
        monkeypatch.setattr(fixture.catalog, "record_source_facts", forbidden)
        result = reader.read(_request(fixture, reference, None))
        assert result.receipt["manifest"]["published_date"] is None
        assert "availability_evidence" not in result.receipt
        assert result.data == fixture.payload and database_bytes(fixture) == baseline_db


def test_projected_parent_a_proof_cannot_cover_parent_b_tamper_or_extend_receipt(tmp_path, monkeypatch):
    with owned_state(tmp_path) as state:
        subject = state.subjects[0]
        _, generation, payload = publish(state, subject, "independent-w03")
        reader = SourceVersionReader(state.catalog)
        first = SourceRef(**dict(state.refs[0]))
        opened = reader.open_version(first, purpose="source_export")
        observation = verified_open_observation(type("Opened", (), {"ref": first, "data": opened.data})())
        state.catalog.record_source_facts(ref=first, facts={"published_date": None}, evidence={
            "published_date": {"value": None, "locator": "review:source", "verified_open": observation}})
        assert verified_availability_evidence(state.catalog, first) is not None
        def load(ref):
            view = open_verified_projection(state.catalog, projection_id=subject.item_key,
                                            expected_projection_sha256=subject.subject_sha256)
            assert NarrativeSubjectRef.from_subject(view.subject) == ref
            return view
        def forbidden(*args, **kwargs):
            raise AssertionError("Projected reads cannot use a single raw proof")
        monkeypatch.setattr(transport, "verified_availability_evidence", forbidden)
        broker = transport.NarrativeTransportReader(state.artifacts, reader, projection_ref_resolver=load)
        reference = broker.reference_subject_ref(NarrativeSubjectRef.from_subject(subject), generation_sha256=generation)
        wire = {"schema_version": "narrative-read-request/3", "narrative_ref": reference.to_dict(),
                "as_of_date": "2026-10-08", "expected_issuer": {"provider_company_id": 1}}
        request = NarrativeReadRequest.from_dict(wire)
        valid = broker.read(request)
        assert valid.data == payload and valid.receipt["parent_count"] == 2
        assert "availability_evidence" not in valid.receipt
        with pytest.raises(ValueError):
            NarrativeReadRequest.from_dict({**wire, "availability_evidence": None})
        originals = [p for p in (state.root / "companies").rglob("*.json") if not p.name.endswith(".source.json")]
        second = next(p for p in originals if hashlib.sha256(p.read_bytes()).hexdigest() == state.refs[1]["content_sha256"])
        original = second.read_bytes()
        try:
            tampered = bytearray(original)
            tampered[len(tampered) // 2] ^= 1
            second.write_bytes(tampered)
            assert second.stat().st_size == len(original)
            with pytest.raises(ValueError):
                broker.read(request)
        finally:
            second.write_bytes(original)
