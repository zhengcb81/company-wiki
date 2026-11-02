"""Contract for the versioned transcript import wire and its owner projection.

The public request is ``company-wiki-transcript-import-request/2``.  Its shape is
frozen by the static fixtures under ``tests/fixtures/transcript_import/``, which
are literal copies of what the producing side emits; this file never builds an
expected envelope from ``dataclasses.asdict``/``to_dict`` of the company-wiki
owner models.  That separation is the point: an internal default field added to
``SourceRequest``/``DownloadCandidate`` must not change what an already released
producer is allowed to send.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, fields
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from company_wiki.source_catalog import transcript_import_cli
from company_wiki.source_catalog.acquisition import DownloadCandidate
from company_wiki.source_catalog.resolver import SourceRequest
from company_wiki.source_catalog.transcript_import_cli import TranscriptImportCliError
from company_wiki.source_catalog.transcript_material import extract_transcript_material


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "transcript_import"
FF_WIRE = FIXTURE_ROOT / "ff_import_request_v2.json"
GENERIC_WIRE = FIXTURE_ROOT / "generic_html_import_request_v2.json"
ET_GOLDEN = REPO_ROOT / "tests" / "fixtures" / "transcript_fmp" / "fmp_v2.fetched.json"


@dataclass(frozen=True)
class _EvolvedSourceRequest(SourceRequest):
    """Test double: the owner model grew one internal defaulted field.

    It is never part of the wire; the decoder must keep accepting the released
    fixture without the producer learning about this attribute.
    """

    _internal_projection_hint: str | None = None


@dataclass(frozen=True)
class _EvolvedDownloadCandidate(DownloadCandidate):
    """Test double: the owner model grew one internal defaulted field."""

    _internal_retry_hint: int = 0


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _wire_bytes(path: Path) -> bytes:
    """The literal producer bytes, unchanged and read fresh from disk."""
    return path.read_bytes()


def _wire(path: Path) -> dict[str, object]:
    """A mutable copy of the literal producer envelope (shape untouched)."""
    return json.loads(_wire_bytes(path))


def _payload(envelope: dict[str, object]) -> bytes:
    result = envelope["transcript_result"]
    assert isinstance(result, dict)
    return base64.b64decode(result["provider_payload_base64"], validate=True)


def _scratch_root(tmp_path: Path, name: str = "company-wiki-fixture") -> Path:
    root = tmp_path / name
    (root / "companies").mkdir(parents=True)
    config = root / "config"
    config.mkdir()
    (config / "source_catalog.yaml").write_text(
        "schema_version: '1.0'\n"
        "catalog_dir: .source_catalog\n"
        "roots:\n"
        "  - root_id: company_raw\n"
        "    path: companies\n"
        "    kind: company_raw\n"
        "    priority: 10\n"
        "    adapter_id: company_raw_v1\n"
        "    read_only: false\n",
        encoding="utf-8",
    )
    return root


def _run_bytes(
    root: Path, payload: bytes, *extra: str
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(SRC_ROOT) + os.pathsep + environment.get("PYTHONPATH", "")
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "company_wiki.source_catalog.transcript_import_cli",
            "--wiki-root",
            str(root),
            *extra,
        ],
        input=payload,
        capture_output=True,
        cwd=REPO_ROOT,
        env=environment,
        check=False,
    )


def _run(root: Path, envelope: dict[str, object]) -> subprocess.CompletedProcess[str]:
    return _run_bytes(root, json.dumps(envelope, ensure_ascii=False).encode("utf-8"))


def _run_transcript_lookup(
    root: Path, source_request: dict[str, object]
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(SRC_ROOT) + os.pathsep + environment.get("PYTHONPATH", "")
    payload = {
        "schema_version": "company-wiki-transcript-import-lookup-request/1",
        "source_request": source_request,
    }
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "company_wiki.source_catalog.source_query_cli",
            "--config",
            str(root / "config" / "source_catalog.yaml"),
        ],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
        env=environment,
        check=False,
    )


def _stored_files(root: Path) -> list[Path]:
    return [
        path
        for path in (root / "companies").rglob("*")
        if path.is_file() and not path.name.endswith(".source.json")
    ]


def _strings(value: object) -> list[str]:
    """Every string inside a decoded public response, for path-leak checks."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for item in value.values() for text in _strings(item)]
    if isinstance(value, list):
        return [text for item in value for text in _strings(item)]
    return []


def _assert_no_local_path(payload: object, root: Path) -> None:
    local = str(root)
    leaked = [text for text in _strings(payload) if local in text]
    assert not leaked, f"physical path leaked into public output: {leaked}"


def _assert_nothing_written(root: Path) -> None:
    assert not _stored_files(root)
    staging = root / ".source_catalog" / "staging"
    assert not staging.exists() or list(staging.iterdir()) == []


def _remove_fixture(root: Path, parent: Path) -> None:
    if not root.exists():
        return
    resolved = root.resolve(strict=True)
    if resolved.parent != parent.resolve(strict=True):
        raise AssertionError("refusing to remove a fixture outside tmp_path")
    paths = (root, *root.rglob("*"))
    if any(path.is_symlink() for path in paths):
        raise AssertionError("refusing to remove a fixture containing symlinks")
    shutil.rmtree(root)


def test_literal_generic_html_wire_imports_original_without_policy_files(
    tmp_path: Path,
) -> None:
    root = _scratch_root(tmp_path)
    envelope = _wire(GENERIC_WIRE)
    body = _payload(envelope)
    try:
        first = _run(root, envelope)
        assert first.returncode == 0, first.stderr
        response = json.loads(first.stdout)
        assert response["status"] == "imported"
        assert response["canonical_status"] == "imported_new"
        assert response["provider_payload_sha256"] == _sha(body)

        second = _run(root, envelope)
        assert second.returncode == 0, second.stderr
        replay = json.loads(second.stdout)
        assert replay["canonical_status"] == "deduplicated_after_download"
        assert replay["source_id"] == response["source_id"]

        originals = list((root / "companies").rglob("*.html"))
        assert len(originals) == 1
        assert originals[0].read_bytes() == body
        provenance = json.loads(
            originals[0].with_name(originals[0].name + ".source.json").read_text(
                encoding="utf-8"
            )
        )
        audit = provenance["provenance_extensions"]["transcript_acquisition"]
        assert audit["schema_version"] == "transcript-acquisition-audit/2"
        assert audit["provider_payload_sha256"] == _sha(body)
        assert "rights_policy_sha256" not in audit
        assert "download_authorization_hash" not in audit
        assert not (root / "config" / "provider_use_policy.json").exists()
        staging = root / ".source_catalog" / "staging"
        assert not staging.exists() or list(staging.iterdir()) == []
    finally:
        _remove_fixture(root, tmp_path)
    assert not root.exists()


def test_literal_ff_fixture_tracks_the_producer_golden() -> None:
    """The frozen tool result is still the producer's own bytes.

    ``transcript_result`` is copied from the earnings-transcripts golden; only
    the request id is bound to this wire.  If the producer golden moves, this
    fails so the import fixture is refreshed deliberately instead of drifting.
    """
    golden = json.loads(ET_GOLDEN.read_text(encoding="utf-8"))
    result = _wire(FF_WIRE)["transcript_result"]
    assert isinstance(result, dict)
    assert set(result) == set(golden)
    changed = {key for key in golden if result[key] != golden[key]}
    assert changed == {"request_id"}


def test_literal_ff_wire_imports_through_real_catalog_and_verified_read(
    tmp_path: Path,
) -> None:
    """The released FF bytes go in; owner checks and a verified read come out."""
    from company_wiki.source_catalog import SourceCatalog, load_catalog_config
    from company_wiki.source_catalog.source_reader import SourceVersionReader

    root = _scratch_root(tmp_path, "company-wiki-fmp")
    envelope = _wire(FF_WIRE)
    original = _payload(envelope)
    catalog = None
    try:
        first = _run_bytes(root, _wire_bytes(FF_WIRE))
        assert first.returncode == 0, first.stderr
        imported = json.loads(first.stdout)
        assert imported["status"] == "imported"
        assert imported["canonical_status"] == "imported_new"
        assert imported["schema_version"] == "company-wiki-transcript-import-response/3"
        # The id FF echoes back comes from the lookup side of this same wire;
        # it is a literal in the fixture, not recomputed from an owner object.
        assert imported["request_id"] == envelope["transcript_result"]["request_id"]
        assert imported["provider_payload_sha256"] == _sha(original)
        source_ref = imported["source_ref"]
        assert source_ref == {
            "schema_version": "2.0",
            "document_id": source_ref["document_id"],
            "source_id": imported["source_id"],
            "content_sha256": _sha(original),
            "byte_size": len(original),
            "mime_type": "application/json",
        }
        assert isinstance(source_ref["document_id"], str) and source_ref["document_id"]
        assert not any("path" in key.lower() for key in source_ref)
        _assert_no_local_path(imported, root)

        files = _stored_files(root)
        assert len(files) == 1 and files[0].read_bytes() == original
        # Storage owns the physical filename (including Windows path budgets).
        # Provider/publication semantics live in provenance and the reader,
        # rather than in the spelling of the raw file's name.
        assert files[0].suffix == ".json"
        sidecar = json.loads(
            files[0].with_name(files[0].name + ".source.json").read_text(encoding="utf-8")
        )
        assert sidecar["provider"] == "fmp"
        assert sidecar["filing_date"] is None
        audit = sidecar["provenance_extensions"]["transcript_acquisition"]
        assert audit["call_date"] == "2026-07-22"
        assert audit["publication_date"] is None
        assert audit["as_of_cutoff_verified"] is False
        assert (
            audit["provider_canonical_content_sha256"]
            == envelope["transcript_result"]["canonical_content_sha256"]
        )

        config = load_catalog_config(
            root / "config" / "source_catalog.yaml", project_root=root
        )
        catalog = SourceCatalog(config)
        reader = SourceVersionReader(catalog)
        docs = catalog.reader.query(
            text="MSFT 2026 Q3", document_kind="investor_call_transcript"
        )
        assert len(docs) == 1 and docs[0]["published_date"] is None
        ref = reader.query_ref(
            docs[0]["document_id"], imported["source_id"], _sha(original)
        )
        assert ref.document_id == source_ref["document_id"]
        assert ref.source_id == source_ref["source_id"]
        opened = reader.open_version(ref, purpose="preview")
        assert opened.data == original
        material = extract_transcript_material(opened.data, mime_type="application/json")
        material.verify(original)
        assert material.lines

        # An owner-side query built from the wire still misses the exact
        # provider document; the wire itself is not a resolution result.
        owner_request = {
            attribute: envelope["source_request"][field]
            for field, attribute in transcript_import_cli._SOURCE_REQUEST_WIRE
        }
        assert reader.query_local(SourceRequest(**owner_request)).status == "not_found"
        # FF's provider-scoped lookup envelope (`_query`) narrows the same wire
        # to one provider and drops the document id; the released fixture stays
        # the cross-source (`_query_local`) shape, which this CLI refuses.
        dedup_request = dict(envelope["source_request"])
        dedup_request["provider"] = "fmp"
        dedup_request["provider_document_id"] = None
        lookup_process = _run_transcript_lookup(root, dedup_request)
        assert lookup_process.returncode == 0, lookup_process.stderr
        lookup = json.loads(lookup_process.stdout)
        assert lookup["status"] == "unknown_publication"
        assert lookup["reason"] == "publication_date_unknown"
        assert lookup["matches"] == [source_ref]
        assert lookup["candidates"][0]["published_date"] is None
        _assert_no_local_path(lookup, root)

        second = _run_bytes(root, _wire_bytes(FF_WIRE))
        assert second.returncode == 0, second.stderr
        replay = json.loads(second.stdout)
        assert replay["canonical_status"] == "deduplicated_after_download"
        assert replay["source_id"] == imported["source_id"]
        assert replay["source_ref"] == source_ref
        assert len(_stored_files(root)) == 1
        staging = root / ".source_catalog" / "staging"
        assert not staging.exists() or list(staging.iterdir()) == []
    finally:
        if catalog is not None:
            catalog.close()
        _remove_fixture(root, tmp_path)
    assert not root.exists()


def test_literal_ff_wire_keeps_the_owner_original_byte_budget(tmp_path: Path) -> None:
    """The explicit import allocation is still enforced by the CWP owner."""
    root = _scratch_root(tmp_path, "company-wiki-budget")
    original = _payload(_wire(FF_WIRE))
    assert len(original) > 256
    try:
        rejected = _run_bytes(root, _wire_bytes(FF_WIRE), "--max-original-bytes", "256")
        assert rejected.returncode != 0
        assert json.loads(rejected.stdout)["status"] == "rejected"
        _assert_nothing_written(root)
    finally:
        _remove_fixture(root, tmp_path)
    assert not root.exists()


def test_internal_defaulted_field_does_not_change_the_wire(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Owner-side evolution is invisible to the released producer bytes.

    The decoder must project the pinned wire fields onto the current owner
    types.  Deriving the accepted field set from ``dataclasses.fields`` would
    turn any new internal default into a newly *required* wire field and reject
    a request that FF legitimately sends today.
    """
    assert len(fields(_EvolvedSourceRequest)) == len(fields(SourceRequest)) + 1
    assert len(fields(_EvolvedDownloadCandidate)) == len(fields(DownloadCandidate)) + 1

    monkeypatch.setattr(transcript_import_cli, "SourceRequest", _EvolvedSourceRequest)
    monkeypatch.setattr(
        transcript_import_cli, "DownloadCandidate", _EvolvedDownloadCandidate
    )

    root = _scratch_root(tmp_path, "company-wiki-evolved")
    original = _payload(_wire(FF_WIRE))
    try:
        response = transcript_import_cli.run_import(
            root, io.BytesIO(_wire_bytes(FF_WIRE))
        )
        assert response["status"] == "imported"
        assert response["canonical_status"] == "imported_new"
        assert response["provider_payload_sha256"] == _sha(original)
        files = _stored_files(root)
        assert len(files) == 1 and files[0].read_bytes() == original
    finally:
        _remove_fixture(root, tmp_path)
    assert not root.exists()


@pytest.mark.parametrize(
    ("target", "field", "value"),
    [
        ("transcript_result", "ticker", "OTHER"),
        ("transcript_result", "fiscal_period", "2026-Q4"),
        ("transcript_result", "as_of_date", "2026-09-29"),
        ("transcript_result", "provider_document_id", "fmp:MSFT:2026:Q3:2026-07-23"),
        ("transcript_result", "provider", "other_provider"),
        (
            "transcript_result",
            "source_url",
            "https://financialmodelingprep.com/stable/earning-call-transcript"
            "?symbol=MSFT&year=2026&quarter=4",
        ),
        ("transcript_result", "provider_payload_sha256", "0" * 64),
        ("transcript_result", "canonical_content_sha256", "0" * 64),
        ("candidate", "provider_document_id", "fmp:MSFT:2026:Q3:2026-07-23"),
        ("source_request", "security_id", "OTHER"),
        ("source_request", "fiscal_period", "Q4"),
    ],
)
def test_wire_core_identity_changes_are_still_rejected(
    tmp_path: Path, target: str, field: str, value: object
) -> None:
    root = _scratch_root(tmp_path, "company-wiki-reject")
    envelope = _wire(FF_WIRE)
    section = envelope[target]
    assert isinstance(section, dict)
    section[field] = value
    try:
        process = _run(root, envelope)
        assert process.returncode != 0
        assert json.loads(process.stdout)["status"] == "rejected"
        assert b"rejected" in process.stderr
        _assert_nothing_written(root)
    finally:
        _remove_fixture(root, tmp_path)
    assert not root.exists()


def test_wire_field_set_is_pinned_to_the_request_schema(tmp_path: Path) -> None:
    """Exactly the released wire fields are accepted - no more, no less."""
    root = _scratch_root(tmp_path, "company-wiki-pinned")
    envelope = _wire(FF_WIRE)
    # The pinned protocol table and the literal producer bytes must agree; a
    # change to either side is a REQUEST_SCHEMA change, not a silent drift.
    assert transcript_import_cli.SOURCE_REQUEST_WIRE_FIELDS == set(
        envelope["source_request"]
    )
    assert transcript_import_cli.CANDIDATE_WIRE_FIELDS == set(envelope["candidate"])
    try:
        missing = _wire(FF_WIRE)
        del missing["source_request"]["mode"]  # type: ignore[index]
        with pytest.raises(
            TranscriptImportCliError, match="source_request fields differ from schema"
        ):
            transcript_import_cli.run_import(
                root, io.BytesIO(json.dumps(missing).encode("utf-8"))
            )

        unknown = _wire(FF_WIRE)
        unknown["source_request"]["_internal_projection_hint"] = None  # type: ignore[index]
        with pytest.raises(
            TranscriptImportCliError, match="source_request fields differ from schema"
        ):
            transcript_import_cli.run_import(
                root, io.BytesIO(json.dumps(unknown).encode("utf-8"))
            )

        missing_candidate = _wire(FF_WIRE)
        del missing_candidate["candidate"]["remote_size"]  # type: ignore[index]
        with pytest.raises(
            TranscriptImportCliError, match="candidate fields differ from schema"
        ):
            transcript_import_cli.run_import(
                root, io.BytesIO(json.dumps(missing_candidate).encode("utf-8"))
            )

        unknown_candidate = _wire(FF_WIRE)
        unknown_candidate["candidate"]["_internal_retry_hint"] = 0  # type: ignore[index]
        with pytest.raises(
            TranscriptImportCliError, match="candidate fields differ from schema"
        ):
            transcript_import_cli.run_import(
                root, io.BytesIO(json.dumps(unknown_candidate).encode("utf-8"))
            )

        wrong_owner_schema = _wire(FF_WIRE)
        wrong_owner_schema["source_request"]["schema_version"] = "0.9"  # type: ignore[index]
        with pytest.raises(TranscriptImportCliError, match="source_request is invalid"):
            transcript_import_cli.run_import(
                root, io.BytesIO(json.dumps(wrong_owner_schema).encode("utf-8"))
            )

        wrong_envelope_schema = _wire(FF_WIRE)
        wrong_envelope_schema["schema_version"] = "company-wiki-transcript-import-request/1"
        with pytest.raises(
            TranscriptImportCliError, match="unsupported stdin envelope schema"
        ):
            transcript_import_cli.run_import(
                root, io.BytesIO(json.dumps(wrong_envelope_schema).encode("utf-8"))
            )
        _assert_nothing_written(root)
    finally:
        _remove_fixture(root, tmp_path)
    assert not root.exists()


def test_envelope_json_hardening_is_unchanged(tmp_path: Path) -> None:
    """Duplicate keys, NaN and non-UTF-8 stay real rejections, not leniency."""
    root = _scratch_root(tmp_path, "company-wiki-hardening")
    raw = _wire_bytes(FF_WIRE)
    try:
        duplicate = raw.replace(
            b'"schema_version": "1.0"',
            b'"schema_version": "1.0", "schema_version": "1.0"',
            1,
        )
        assert duplicate != raw
        with pytest.raises(TranscriptImportCliError, match="duplicate JSON object key"):
            transcript_import_cli.run_import(root, io.BytesIO(duplicate))

        nan = raw.replace(b'"fiscal_year": 2026', b'"fiscal_year": NaN', 1)
        assert nan != raw
        with pytest.raises(TranscriptImportCliError, match="invalid JSON constant"):
            transcript_import_cli.run_import(root, io.BytesIO(nan))

        invalid_utf8 = raw.replace(
            b"Microsoft Corporation", b"Microsoft Corporati\xffn", 1
        )
        assert invalid_utf8 != raw
        with pytest.raises(
            TranscriptImportCliError, match="stdin envelope is invalid UTF-8 JSON"
        ):
            transcript_import_cli.run_import(root, io.BytesIO(invalid_utf8))

        oversize = _run_bytes(root, raw, "--max-envelope-bytes", str(len(raw) - 1))
        assert oversize.returncode != 0
        assert json.loads(oversize.stdout)["status"] == "rejected"
        _assert_nothing_written(root)
    finally:
        _remove_fixture(root, tmp_path)
    assert not root.exists()


@pytest.mark.parametrize(
    "bad_field", ["provider_payload_sha256", "canonical_content_sha256"]
)
def test_fmp_cli_rejects_corrupt_original_evidence_without_files(
    tmp_path: Path, bad_field: str,
) -> None:
    root = _scratch_root(tmp_path, "company-wiki-corrupt")
    envelope = _wire(FF_WIRE)
    result = envelope["transcript_result"]
    assert isinstance(result, dict)
    result[bad_field] = "0" * 64
    try:
        process = _run(root, envelope)
        assert process.returncode != 0
        assert json.loads(process.stdout)["status"] == "rejected"
        _assert_nothing_written(root)
    finally:
        _remove_fixture(root, tmp_path)
    assert not root.exists()
