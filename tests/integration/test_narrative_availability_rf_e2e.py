"""ROOT integration: real CWP producer and RF public CLI, no fake wire/provider."""

from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import os
import subprocess
import sys

import pytest

from support.narrative_transport_fixture import published_fixture
from company_wiki.source_catalog.source_reader import SourceRef
from company_wiki.source_catalog.source_availability import (
    verified_availability_evidence,
    verified_open_observation,
)

CWP = Path(__file__).resolve().parents[2]
RF = Path(
    os.environ.get("RF_NARRATIVE_CODE_ROOT", str(CWP.parent / "revenue-forecast"))
).resolve()
pytestmark = pytest.mark.skipif(
    "RF_NARRATIVE_CODE_ROOT" not in os.environ
    and not (RF / "scripts/narrative_source_preparation.py").is_file(),
    reason="cross-repository E2E requires RF_NARRATIVE_CODE_ROOT or sibling revenue-forecast",
)


def source_ref(fixture):
    return SourceRef(**fixture.source_ref.to_dict())


def source_facts(
    fixture,
    *,
    basis="prior_verified_capture",
    published=None,
    captured="2026-08-01T12:00:00Z",
    wrong_sha=False,
):
    ref = source_ref(fixture)
    evidence = {"value": published, "locator": "fixture:root-independent-source-clock"}
    if basis == "current_verified_open":
        opened = fixture.reader.open_version(ref, purpose="source_export")
        evidence["verified_open"] = verified_open_observation(
            SimpleNamespace(ref=ref, data=opened.data)
        )
    elif basis == "prior_verified_capture":
        receipt = {
            "schema_version": "1.0",
            "candidate_id": "root-independent",
            "provider": "sec",
            "provider_document_id": "root-independent",
            "source_url": "https://www.sec.gov/Archives/root-independent.txt",
            "staged_path": "staging/root-independent.txt",
            "content_sha256": ref.content_sha256,
            "byte_size": ref.byte_size,
            "mime_type": ref.mime_type,
            "retrieved_at": captured,
            "http_status": 200,
            "adapter_name": "offline-root",
            "adapter_version": "1.0.0",
            "etag": None,
            "last_modified": None,
        }
        capture = {
            "schema_version": "1.0",
            "request_id": "root-independent",
            **{
                key: receipt[key]
                for key in (
                    "provider",
                    "provider_document_id",
                    "source_url",
                    "content_sha256",
                    "byte_size",
                    "mime_type",
                    "retrieved_at",
                    "adapter_name",
                    "adapter_version",
                )
            },
            "candidate": {
                key: receipt[key]
                for key in ("provider", "provider_document_id", "source_url")
            },
            "receipt": receipt,
        }
        if wrong_sha:
            receipt["content_sha256"] = "0" * 64
        evidence["availability_capture"] = capture
    fixture.catalog.record_source_facts(
        ref=ref,
        facts={"published_date": published},
        evidence={"published_date": evidence},
    )
    return verified_availability_evidence(fixture.catalog, ref)


def rf_cli(fixture, value, operation):
    env = dict(
        os.environ,
        PYTHONPATH=str(CWP / "src"),
        PYTHONUTF8="1",
        PYTHONDONTWRITEBYTECODE="1",
        PYTHON_DOTENV_DISABLED="1",
        COMPANY_WIKI_NETWORK="blocked",
    )
    return subprocess.run(
        [
            sys.executable,
            "-B",
            str(RF / "scripts/narrative_source_preparation.py"),
            "--company-wiki-catalog-config",
            str(fixture.config_path),
            "--operation",
            operation,
        ],
        input=json.dumps(value).encode(),
        cwd=fixture.root,
        env=env,
        capture_output=True,
        timeout=45,
    )


def request(fixture, cutoff):
    result = rf_cli(
        fixture,
        {
            "schema_version": "narrative-reference-request/1",
            "source_ref": fixture.source_ref.to_dict(),
        },
        "reference",
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    return {
        "schema_version": "narrative-read-request/1",
        "narrative_ref": json.loads(result.stdout),
        "as_of_date": cutoff,
        "expected_source": dict(fixture.expected_source),
    }


def db_state(fixture):
    return {
        str(p.relative_to(fixture.catalog.config.catalog_dir)): hashlib.sha256(
            p.read_bytes()
        ).hexdigest()
        for p in fixture.catalog.config.catalog_dir.rglob("*")
        if p.is_file()
        and (p.suffix in {".db", ".sqlite", ".sqlite3"} or p.name.endswith("-wal"))
    }


@pytest.mark.parametrize("kind", ["pdf", "json"])
@pytest.mark.parametrize("basis", ["prior_verified_capture", "current_verified_open"])
def test_actual_public_pair_preserves_source_clock_and_frozen_artifact(
    tmp_path, kind, basis
):
    before = set(tmp_path.iterdir())
    with published_fixture(tmp_path, kind=kind) as f:
        proof = source_facts(f, basis=basis)
        assert proof is not None
        manifest = f.reader.describe_version(source_ref(f))
        assert manifest["published_date"] is None
        payload = f.payload
        before_db = db_state(f)
        req = request(f, proof["available_by"])
        result = rf_cli(f, req, "read")
        assert result.returncode == 0, result.stderr.decode(errors="replace")
        assert result.stderr == b""
        context = json.loads(result.stdout)
        receipt = context["read_receipt"]
        assert receipt["availability_evidence"] == proof
        assert receipt["manifest"] == manifest
        assert receipt["manifest"]["published_date"] is None
        assert receipt["narrative_ref"] == req["narrative_ref"]
        assert context["source_ref"] == f.source_ref.to_dict()
        assert context["summary"]["translate"] is False
        assert len(json.dumps(receipt, ensure_ascii=False).encode()) < 16384
        assert str(f.root) not in json.dumps(context)
        assert context["evidence_spans"]
        assert f.raw_path.read_bytes() == f.raw_bytes
        assert f.payload == payload and b"availability_evidence" not in payload
        assert (
            hashlib.sha256(payload).hexdigest()
            == req["narrative_ref"]["artifact_sha256"]
        )
        assert db_state(f) == before_db
    assert set(tmp_path.iterdir()) == before


@pytest.mark.parametrize(
    "case",
    ["missing", "future_pub", "late_capture", "wrong_sha", "current_for_old_cutoff"],
)
def test_public_pair_cannot_turn_bad_or_late_proof_into_historical_material(
    tmp_path, case
):
    before = set(tmp_path.iterdir())
    with published_fixture(tmp_path, kind="json") as f:
        source_facts(
            f,
            basis=None
            if case == "missing"
            else "current_verified_open"
            if case == "current_for_old_cutoff"
            else "prior_verified_capture",
            published="2026-09-02" if case == "future_pub" else None,
            captured="2026-09-02T00:00:00Z"
            if case == "late_capture"
            else "2026-08-01T12:00:00Z",
            wrong_sha=case == "wrong_sha",
        )
        response = rf_cli(f, request(f, "2026-09-01"), "read")
        assert response.returncode == 2
        assert response.stdout == b""
        refusal = json.loads(response.stderr)
        assert refusal["reason"] in {"source_after_as_of", "source_publication_unknown"}
        assert len(response.stderr) < 512 and b"Traceback" not in response.stderr
        assert f.raw_path.read_bytes() == f.raw_bytes
    assert set(tmp_path.iterdir()) == before
