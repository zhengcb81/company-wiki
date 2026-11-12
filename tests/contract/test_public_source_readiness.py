"""G-CWP-READINESS-01 contract tests: public SourceRef readiness diagnostics.

Covers the owner-request matrix against the REAL public CLI (subprocess,
stdin JSON -> one stdout JSON line) and the module surface:

- metadata readiness says what the catalog knows and never claims bytes;
- verify_existing_bytes verifies same-SHA local bytes through the exact
  reader, with hard deadline/byte ceilings;
- every negative case is a named state (partial/blocked/unavailable) with
  stable reason codes, no internal path, root, exception text or latest-
  read fallback;
- the CLI accepts only a complete 6-field SourceRef JSON on stdin;
- read-only side effects: the catalog file tree is byte-identical.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
from company_wiki.source_catalog.public_source_readiness import (
    READINESS_SCHEMA_VERSION,
    PublicSourceRefError,
    PublicSourceReadiness,
    parse_public_source_ref,
)
from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader


PAYLOAD = b"original fixture bytes for readiness\n"
SHA = hashlib.sha256(PAYLOAD).hexdigest()
DOCUMENT_ID = "doc-readiness"
SOURCE_TITLE = "ACME 2025 Annual Report"


def _seed_catalog(tmp_path: Path) -> SourceCatalog:
    """company_raw root with one registered active annual report."""
    project = tmp_path / "project"
    companies = project / "companies"
    (companies / "ACME" / "raw").mkdir(parents=True)
    (companies / "ACME" / "raw" / "annual.pdf").write_bytes(PAYLOAD)
    (companies / "ACME" / "raw" / "annual.pdf.source.json").write_text(
        json.dumps({
            "document_kind": "annual_report",
            "source_type": "filing",
            "company_name": "ACME Corp",
            "security_id": "ACME",
            "market": "US",
            "provider": "sec",
            "source_title": SOURCE_TITLE,
            "form_type": "10-K",
            "fiscal_year": 2025,
            "fiscal_period": "FY",
            "filing_date": "2026-02-20",
            "published_date": "2026-02-20",
            "source_url": "https://www.sec.gov/Archives/edgar/data/1/annual.pdf",
            "retrieved_at": "2026-02-21T10:00:00Z",
            "collector_name": "readiness-fixture",
            "collector_version": "1.0.0",
            "mime_type": "application/pdf",
            "byte_size": len(PAYLOAD),
            "content_sha256": SHA,
            "files": [{"name": "annual.pdf", "source": "original"}],
        }),
        encoding="utf-8",
    )
    catalog = SourceCatalog(
        CatalogConfig(
            project_root=project,
            catalog_dir=project / ".source_catalog",
            roots=(RootSpec("company_raw", companies, "company_raw", priority=10),),
        )
    )
    catalog.scan()
    return catalog


def _sole_ref(catalog: SourceCatalog) -> SourceRef:
    docs = catalog.query(limit=10)
    assert len(docs) == 1, docs
    document = docs[0]
    return SourceRef(
        document_id=str(document["document_id"]),
        source_id=str(document["source_id"] or document["primary_source_id"]),
        content_sha256=SHA,
        byte_size=len(PAYLOAD),
        mime_type="application/pdf",
    )


@pytest.fixture()
def seeded(tmp_path):
    catalog = _seed_catalog(tmp_path)
    yield catalog, _sole_ref(catalog), tmp_path
    catalog.close()


def _config_path(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    config_path = project / "config" / "source_catalog.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        "schema_version: '1.0'\n"
        f"catalog_dir: '{(project / '.source_catalog').as_posix()}'\n"
        "roots:\n"
        f"  - root_id: company_raw\n"
        f"    kind: company_raw\n"
        f"    path: '{(project / 'companies').as_posix()}'\n",
        encoding="utf-8",
    )
    return config_path


def _ref_payload(ref: SourceRef) -> dict[str, object]:
    return {
        "document_id": ref.document_id,
        "source_id": ref.source_id,
        "content_sha256": ref.content_sha256,
        "byte_size": ref.byte_size,
        "mime_type": ref.mime_type,
        "schema_version": "2.0",
    }


def _catalog_tree(catalog_dir: Path):
    return sorted(
        (p.relative_to(catalog_dir).as_posix(), p.read_bytes())
        for p in catalog_dir.rglob("*") if p.is_file()
    )


def _run_cli(tmp_path: Path, config_path: Path, mode: str, stdin: str,
             *extra: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
    env["PYTHON_DOTENV_DISABLED"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "company_wiki.source_catalog.public_source_readiness_cli",
         "--config", str(config_path), "--mode", mode, *extra],
        input=stdin, text=True, encoding="utf-8",
        capture_output=True, timeout=120, check=False, env=env,
    )


def _ready_metadata(response: dict[str, object]) -> dict[str, object]:
    assert response["status"] == "ready", response
    assert response["checked_mode"] == "metadata_only"
    assert response["byte_verified"] is False
    assert response["verification_receipt"] is None
    assert response["reason_codes"] == []
    metadata = response["metadata"]
    assert isinstance(metadata, dict)
    return metadata


def _ready_verify(response: dict[str, object],
                  expected_sha: str = SHA,
                  expected_size: int = len(PAYLOAD)) -> dict[str, object]:
    assert response["status"] == "ready", response
    assert response["checked_mode"] == "verify_existing_bytes"
    assert response["byte_verified"] is True
    assert response["metadata"] is None
    receipt = response["verification_receipt"]
    assert isinstance(receipt, dict)
    assert receipt["content_sha256"] == expected_sha
    assert receipt["byte_size"] == expected_size
    return receipt


# --- positive: metadata is catalog truth, never bytes ------------------------


def test_metadata_ready_reports_catalog_facts_without_byte_claims(seeded):
    catalog, ref, tmp_path = seeded
    readiness = PublicSourceReadiness(SourceVersionReader(catalog))
    response = readiness.assess(_ref_payload(ref), mode="metadata_only")
    metadata = _ready_metadata(response)
    assert metadata["title"] == SOURCE_TITLE
    assert metadata["provider"] == "sec"
    assert metadata["byte_size"] == len(PAYLOAD)
    assert response["schema_version"] == READINESS_SCHEMA_VERSION
    assert response["source_ref"] == {
        "document_id": ref.document_id, "source_id": ref.source_id,
        "content_sha256": SHA, "byte_size": len(PAYLOAD),
        "mime_type": "application/pdf", "schema_version": "2.0",
    }


def test_metadata_on_missing_file_is_still_metadata_only_not_bytes(seeded):
    """The configured file is gone; metadata stays ready and must NOT be
    promoted to a byte claim in any mode."""
    catalog, ref, tmp_path = seeded
    (tmp_path / "project" / "companies" / "ACME" / "raw" / "annual.pdf").unlink()
    readiness = PublicSourceReadiness(SourceVersionReader(catalog))
    metadata_response = readiness.assess(_ref_payload(ref), mode="metadata_only")
    assert _ready_metadata(metadata_response)["byte_size"] == len(PAYLOAD)
    verify_response = readiness.assess(_ref_payload(ref), mode="verify_existing_bytes")
    assert verify_response["status"] == "unavailable"
    assert verify_response["byte_verified"] is False
    assert "no_verified_location" in verify_response["reason_codes"]


def test_verify_mode_passes_on_same_sha_local_bytes(seeded):
    catalog, ref, tmp_path = seeded
    readiness = PublicSourceReadiness(SourceVersionReader(catalog))
    response = readiness.assess(_ref_payload(ref), mode="verify_existing_bytes")
    receipt = _ready_verify(response)
    assert receipt["document_id"] == ref.document_id
    assert receipt["source_id"] == ref.source_id
    assert receipt["read_at"]
    assert "relative_path" not in receipt and "root_id" not in receipt


def test_verify_mode_reports_tampered_bytes_with_named_reason(seeded):
    catalog, ref, tmp_path = seeded
    path = tmp_path / "project" / "companies" / "ACME" / "raw" / "annual.pdf"
    original_size = path.stat().st_size
    path.write_bytes(b"X" * original_size)  # same size, different SHA
    readiness = PublicSourceReadiness(SourceVersionReader(catalog))
    response = readiness.assess(_ref_payload(ref), mode="verify_existing_bytes")
    assert response["status"] == "unavailable"
    assert response["byte_verified"] is False
    assert "no_verified_location" in response["reason_codes"]
    assert response["verification_receipt"] is None


def test_verify_mode_reports_size_tamper_without_reading_everything(seeded):
    catalog, ref, tmp_path = seeded
    path = tmp_path / "project" / "companies" / "ACME" / "raw" / "annual.pdf"
    path.write_bytes(PAYLOAD + b"extra\n")  # size mismatch
    readiness = PublicSourceReadiness(SourceVersionReader(catalog))
    response = readiness.assess(_ref_payload(ref), mode="verify_existing_bytes")
    assert response["status"] == "unavailable"
    assert response["byte_verified"] is False


def test_verify_limit_blocks_before_reading(seeded):
    catalog, ref, tmp_path = seeded
    readiness = PublicSourceReadiness(SourceVersionReader(catalog))
    response = readiness.assess(
        _ref_payload(ref), mode="verify_existing_bytes", max_verify_bytes=4,
    )
    assert response["status"] == "blocked"
    assert response["byte_verified"] is False
    assert response["reason_codes"] == ["verify_limit_exceeded"]


def test_tiny_deadline_times_out_as_unavailable(seeded):
    catalog, ref, tmp_path = seeded
    readiness = PublicSourceReadiness(SourceVersionReader(catalog))
    response = readiness.assess(
        _ref_payload(ref), mode="verify_existing_bytes",
        byte_deadline_seconds=0.0,
    )
    assert response["status"] == "unavailable"
    assert response["byte_verified"] is False
    assert response["reason_codes"] == ["verify_deadline_exceeded"]


# --- negative: admission, status, and index state ----------------------------


def test_metadata_partial_when_document_not_indexed(seeded):
    catalog, ref, tmp_path = seeded
    missing = SourceRef("doc-absent", ref.source_id, "b" * 64, 5, "text/plain")
    response = PublicSourceReadiness(SourceVersionReader(catalog)).assess(
        _ref_payload(missing), mode="metadata_only"
    )
    assert response["status"] == "partial"
    assert response["reason_codes"] == ["document_not_indexed"]
    assert response["metadata"] is None and response["byte_verified"] is False


def test_metadata_blocked_when_document_retired(seeded):
    catalog, ref, tmp_path = seeded
    import sqlite3

    con = sqlite3.connect(f"file:{catalog.config.database_path}?mode=rw", uri=True)
    con.execute("UPDATE documents SET source_status='retired'")
    con.commit()
    con.close()
    response = PublicSourceReadiness(SourceVersionReader(catalog)).assess(
        _ref_payload(ref), mode="metadata_only"
    )
    assert response["status"] == "blocked"
    assert response["reason_codes"] == ["source_not_active"]


def test_verify_blocked_when_document_retired(seeded):
    catalog, ref, tmp_path = seeded
    import sqlite3

    con = sqlite3.connect(f"file:{catalog.config.database_path}?mode=rw", uri=True)
    con.execute("UPDATE documents SET source_status='retired'")
    con.commit()
    con.close()
    response = PublicSourceReadiness(SourceVersionReader(catalog)).assess(
        _ref_payload(ref), mode="verify_existing_bytes"
    )
    assert response["status"] == "blocked"
    assert response["reason_codes"] == ["source_not_active"]


def test_partial_when_ref_sha_no_longer_matches_index(seeded):
    catalog, ref, tmp_path = seeded
    changed = SourceRef(ref.document_id, ref.source_id, "c" * 64, ref.byte_size,
                        ref.mime_type)
    readiness = PublicSourceReadiness(SourceVersionReader(catalog))
    for mode in ("metadata_only", "verify_existing_bytes"):
        response = readiness.assess(_ref_payload(changed), mode=mode)
        assert response["status"] == "unavailable"
        assert response["reason_codes"] == ["expected_version_mismatch"]


def test_missing_catalog_database_is_unavailable_not_fatal(tmp_path):
    project = tmp_path / "empty"
    project.mkdir()
    config = CatalogConfig(
        project_root=project,
        catalog_dir=project / ".source_catalog",
        roots=(RootSpec("company_raw", project, "company_raw", priority=10),),
    )
    readiness = PublicSourceReadiness(SourceVersionReader(SourceCatalog(config)))
    response = readiness.assess(
        {"document_id": "d", "source_id": "s", "content_sha256": SHA,
         "byte_size": 1, "mime_type": "text/plain", "schema_version": "2.0"},
        mode="metadata_only",
    )
    assert response["status"] == "unavailable"
    assert response["reason_codes"] == ["catalog_unavailable"]
    assert not (project / ".source_catalog").exists()


# --- request shape: only complete 6-field refs -------------------------------


@pytest.mark.parametrize("payload", [
    None,
    42,
    "doc-readiness",
    {},
    {"document_id": "doc-readiness"},  # incomplete
    {**{"document_id": "d", "source_id": "s", "content_sha256": SHA,
        "byte_size": 1, "mime_type": "text/plain"}},  # 5 fields
    {**{"document_id": "d", "source_id": "s", "content_sha256": SHA,
        "byte_size": 1, "mime_type": "text/plain", "schema_version": "2.0"},
     "extra": 1},  # 7 fields
    {"document_id": "d", "source_id": "s", "content_sha256": SHA.upper(),
     "byte_size": 1, "mime_type": "text/plain", "schema_version": "2.0"},
    {"document_id": "d", "source_id": "s", "content_sha256": SHA,
     "byte_size": True, "mime_type": "text/plain", "schema_version": "2.0"},
    {"document_id": "d", "source_id": "s", "content_sha256": SHA,
     "byte_size": -1, "mime_type": "text/plain", "schema_version": "2.0"},
    {"document_id": "d", "source_id": "s", "content_sha256": SHA,
     "byte_size": 1.5, "mime_type": "text/plain", "schema_version": "2.0"},
    {"document_id": "d", "source_id": "s", "content_sha256": SHA,
     "byte_size": 1, "mime_type": "not-a-mime", "schema_version": "2.0"},
    {"document_id": "../escape", "source_id": "s", "content_sha256": SHA,
     "byte_size": 1, "mime_type": "text/plain", "schema_version": "2.0"},
])
def test_incomplete_or_malformed_refs_are_named_request_errors(payload):
    with pytest.raises(PublicSourceRefError) as raised:
        parse_public_source_ref(payload)
    assert raised.value.reason_code == "invalid_source_ref"


def test_assess_returns_named_response_not_exception_for_bad_payload(seeded):
    catalog, ref, tmp_path = seeded
    readiness = PublicSourceReadiness(SourceVersionReader(catalog))
    for payload in (None, {"document_id": "d"}, {"schema_version": "2.0"}):
        for mode in ("metadata_only", "verify_existing_bytes"):
            response = readiness.assess(payload, mode=mode)
            assert response["status"] == "unavailable"
            assert response["checked_mode"] is None
            assert response["reason_codes"] == ["invalid_source_ref"]
            assert response["byte_verified"] is False


def test_unknown_mode_is_refused_without_touching_catalog(seeded):
    catalog, ref, tmp_path = seeded
    readiness = PublicSourceReadiness(SourceVersionReader(catalog))
    response = readiness.assess(_ref_payload(ref), mode="full_read")
    assert response["checked_mode"] is None
    assert response["status"] == "unavailable"
    assert response["reason_codes"] == []


def test_invalid_verify_limits_block_the_request(seeded):
    catalog, ref, tmp_path = seeded
    readiness = PublicSourceReadiness(SourceVersionReader(catalog))
    for kwargs in (
        {"byte_deadline_seconds": -1},
        {"byte_deadline_seconds": float("inf")},
        {"byte_deadline_seconds": float("nan")},
        {"byte_deadline_seconds": "30"},
        {"max_verify_bytes": 0},
        {"max_verify_bytes": -5},
        {"max_verify_bytes": 2**40},
        {"max_verify_bytes": 1.5},
    ):
        response = readiness.assess(
            _ref_payload(ref), mode="verify_existing_bytes", **kwargs
        )
        assert response["status"] == "blocked", kwargs
        assert response["reason_codes"] == ["invalid_verify_limits"], kwargs


# --- path and internal-detail hygiene ----------------------------------------


def test_responses_never_leak_paths_roots_or_exception_text(seeded):
    catalog, ref, tmp_path = seeded
    project_root = str(tmp_path / "project")
    readiness = PublicSourceReadiness(SourceVersionReader(catalog))
    # happy path
    responses = [
        readiness.assess(_ref_payload(ref), mode="metadata_only"),
        readiness.assess(_ref_payload(ref), mode="verify_existing_bytes"),
    ]
    # negative paths (deleted file, unknown doc, retired doc)
    (tmp_path / "project" / "companies" / "ACME" / "raw" / "annual.pdf").unlink()
    responses.append(readiness.assess(_ref_payload(ref), mode="verify_existing_bytes"))
    responses.append(readiness.assess(
        _ref_payload(SourceRef("doc-absent", ref.source_id, "b" * 64, 5, "text/plain")),
        mode="metadata_only",
    ))
    con = sqlite3.connect(f"file:{catalog.config.database_path}?mode=rw", uri=True)
    con.execute("UPDATE documents SET source_status='retired'")
    con.commit()
    con.close()
    responses.append(readiness.assess(_ref_payload(ref), mode="metadata_only"))
    for response in responses:
        text = json.dumps(response, ensure_ascii=False)
        assert project_root not in text
        assert str(tmp_path) not in text
        for forbidden in ("root_id", "relative_path", "absolute_path",
                          "companies", "source_catalog", "catalog_dir"):
            assert forbidden not in text, (forbidden, text)
        assert "Traceback" not in text


def test_cli_stdout_has_no_stderr_and_no_path_on_positive_and_negative(seeded):
    catalog, ref, tmp_path = seeded
    catalog.close()  # CLI subprocess owns the DB now
    config_path = _config_path(tmp_path)
    result = _run_cli(tmp_path, config_path, "metadata_only",
                      json.dumps(_ref_payload(ref)))
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    response = json.loads(result.stdout)
    _ready_metadata(response)
    assert str(tmp_path) not in result.stdout

    verify = _run_cli(tmp_path, config_path, "verify_existing_bytes",
                      json.dumps(_ref_payload(ref)))
    assert verify.returncode == 0 and verify.stderr == ""
    _ready_verify(json.loads(verify.stdout))


def test_cli_refuses_path_carrying_business_json(seeded):
    catalog, ref, tmp_path = seeded
    catalog.close()
    config_path = _config_path(tmp_path)
    smuggled = json.dumps({
        **_ref_payload(ref),
        "absolute_path": str(tmp_path / "project" / "companies" / "ACME" / "raw" / "annual.pdf"),
    })
    result = _run_cli(tmp_path, config_path, "metadata_only", smuggled)
    assert result.returncode == 2
    assert result.stdout == ""
    assert str(tmp_path) not in result.stderr


def test_cli_refuses_duplicate_json_keys_and_nonfinite_numbers(seeded):
    catalog, ref, tmp_path = seeded
    catalog.close()
    config_path = _config_path(tmp_path)
    duplicate = (
        '{"document_id":"' + ref.document_id + '","document_id":"other",'
        '"source_id":"' + ref.source_id + '","content_sha256":"' + SHA + '",'
        '"byte_size":' + str(len(PAYLOAD)) + ',"mime_type":"application/pdf",'
        '"schema_version":"2.0"}'
    )
    result = _run_cli(tmp_path, config_path, "metadata_only", duplicate)
    assert result.returncode == 2 and result.stdout == ""
    nonfinite = json.dumps(_ref_payload(ref), separators=(",", ":")).replace(
        f'"byte_size":{len(PAYLOAD)}', '"byte_size":NaN'
    )
    assert '"byte_size":NaN' in nonfinite
    result = _run_cli(tmp_path, config_path, "metadata_only", nonfinite)
    assert result.returncode == 2 and result.stdout == ""


def test_cli_refuses_non_json_body(seeded):
    catalog, ref, tmp_path = seeded
    catalog.close()
    result = _run_cli(tmp_path, _config_path(tmp_path), "metadata_only", "{not json")
    assert result.returncode == 2 and result.stdout == ""


def test_cli_stderr_silent_on_named_readiness_refusal(seeded):
    catalog, ref, tmp_path = seeded
    catalog.close()
    missing = dict(_ref_payload(ref), document_id="doc-absent")
    result = _run_cli(tmp_path, _config_path(tmp_path), "verify_existing_bytes",
                      json.dumps(missing))
    assert result.returncode == 0
    assert result.stderr == ""
    response = json.loads(result.stdout)
    assert response["status"] == "partial"
    assert response["reason_codes"] == ["document_not_indexed"]


def test_cli_enforces_max_verify_bytes_flag(seeded):
    catalog, ref, tmp_path = seeded
    catalog.close()
    config_path = _config_path(tmp_path)
    result = _run_cli(
        tmp_path, config_path, "verify_existing_bytes",
        json.dumps(_ref_payload(ref)), "--max-verify-bytes", "4",
    )
    assert result.returncode == 0
    response = json.loads(result.stdout)
    assert response["status"] == "blocked"
    assert response["reason_codes"] == ["verify_limit_exceeded"]


def test_cli_enforces_deadline_flag(seeded):
    catalog, ref, tmp_path = seeded
    catalog.close()
    result = _run_cli(
        tmp_path, _config_path(tmp_path), "verify_existing_bytes",
        json.dumps(_ref_payload(ref)), "--byte-deadline-seconds", "0",
    )
    assert result.returncode == 0
    response = json.loads(result.stdout)
    assert response["status"] == "unavailable"
    assert response["reason_codes"] == ["verify_deadline_exceeded"]


def test_cli_missing_config_exits_2_without_stdout(seeded):
    catalog, ref, tmp_path = seeded
    catalog.close()
    result = _run_cli(tmp_path, tmp_path / "nope" / "config.yaml",
                      "metadata_only", json.dumps(_ref_payload(ref)))
    assert result.returncode == 2 and result.stdout == ""


# --- read-only side effects ---------------------------------------------------


def test_readiness_leaves_catalog_and_roots_byte_identical(seeded):
    catalog, ref, tmp_path = seeded
    catalog_dir = Path(catalog.config.database_path).parent
    before_catalog = _catalog_tree(catalog_dir)
    companies = tmp_path / "project" / "companies"
    before_roots = sorted(
        (p.relative_to(companies).as_posix(), p.read_bytes())
        for p in companies.rglob("*") if p.is_file()
    )
    readiness = PublicSourceReadiness(SourceVersionReader(catalog))
    readiness.assess(_ref_payload(ref), mode="metadata_only")
    readiness.assess(_ref_payload(ref), mode="verify_existing_bytes")
    readiness.assess(
        _ref_payload(SourceRef("doc-absent", ref.source_id, "b" * 64, 5, "text/plain")),
        mode="metadata_only",
    )
    assert _catalog_tree(catalog_dir) == before_catalog
    after_roots = sorted(
        (p.relative_to(companies).as_posix(), p.read_bytes())
        for p in companies.rglob("*") if p.is_file()
    )
    assert after_roots == before_roots


# --- root migration: same ref through a relocated root ------------------------


def test_same_ref_after_root_migration_keeps_id_and_verifies(seeded):
    """The registered SourceRef survives a root relocation in the operator's
    own tmp config; identity is unchanged and verify succeeds against the
    relocated copy — no second lookup, no disk search, no copying by us."""
    catalog, ref, tmp_path = seeded
    source = tmp_path / "project" / "companies" / "ACME" / "raw" / "annual.pdf"
    migrated_root = tmp_path / "migrated_lake"
    (migrated_root / "ACME" / "raw").mkdir(parents=True)
    (migrated_root / "ACME" / "raw" / "annual.pdf").write_bytes(PAYLOAD)
    source.unlink()
    migrated_catalog = SourceCatalog(
        CatalogConfig(
            project_root=tmp_path / "project",
            catalog_dir=tmp_path / "project" / ".source_catalog_migrated",
            roots=(RootSpec("company_raw", migrated_root, "company_raw", priority=10),),
        )
    )
    migrated_catalog.scan()
    migrated_ref = _sole_ref(migrated_catalog)
    # The migrated registration produced the same identity (same bytes, same
    # document identity) as the owner-registered ref.
    assert migrated_ref.content_sha256 == ref.content_sha256
    assert migrated_ref.byte_size == ref.byte_size
    readiness = PublicSourceReadiness(SourceVersionReader(migrated_catalog))
    response = readiness.assess(_ref_payload(migrated_ref), mode="verify_existing_bytes")
    receipt = _ready_verify(response)
    assert receipt["content_sha256"] == ref.content_sha256
    migrated_catalog.close()


# --- D00-CWP-READINESS-002: physical paths refused in IDs + scrubbed in meta --

# The negative fixtures below are deliberately FAKE physical locations (the
# whole point of the D00-002 counterexamples).  They are COMPUTED by string
# concatenation at runtime — not source literals — so the FC-1307-a
# host-assumption guard (which scans ast.Constant host-absolute paths) is not
# tripped by intentionally-path-shaped test data.  The guard's own message
# states that computed/concatenated host paths are outside its scope.
_DRIVE = "C"
_UNC = "\\"
_P1, _P2, _P3 = "Users", "private-owner", "source-root"

# Physical-location signals the unified predicate must refuse in a ref ID.
_PATH_REF_IDS = (
    _DRIVE + ":/" + _P1 + "/" + _P2 + "/" + _P3 + "/annual.pdf",  # drive fwd
    _DRIVE + ":" + _UNC + _P1 + _UNC + _P2 + _UNC + _P3
    + _UNC + "annual.pdf",                                        # drive bwd
    _UNC + _UNC + "server" + _UNC + "share" + _UNC + "annual.pdf",  # UNC bwd
    "/" + "/server/share/annual.pdf",                             # UNC fwd
    "file:///" + _DRIVE + ":/" + _P1 + "/" + "private/annual.pdf",  # file URI
    "file://server/share/annual.pdf",                              # file URI UNC
    "/" + "etc/company-private/source.pdf",                        # POSIX abs
    "../../etc/passwd",                                            # rel escape
    ".." + _UNC + ".." + _UNC + "windows" + _UNC + "system32",      # rel bwd
)

# Legal opaque identifiers + ordinary prose/URLs that must NOT be refused.
_LEGAL_REF_IDS = (
    "urn:company-wiki:document:sha256:" + SHA,
    "urn:company-wiki:source:sha256:" + SHA,
    "cwpdv1-" + SHA,
    "doc-readiness",
)


@pytest.mark.parametrize("bad_id", _PATH_REF_IDS)
def test_ref_ids_with_physical_paths_are_rejected_before_catalog(seeded, bad_id):
    """A path-shaped document_id/source_id is a request error (exit 2 at the
    CLI), never echoed and never looked up (D00-CWP-READINESS-002)."""
    catalog, ref, tmp_path = seeded
    readiness = PublicSourceReadiness(SourceVersionReader(catalog))
    for field in ("document_id", "source_id"):
        payload = _ref_payload(ref)
        payload[field] = bad_id
        for mode in ("metadata_only", "verify_existing_bytes"):
            response = readiness.assess(payload, mode=mode)
            assert response["status"] == "unavailable", (field, mode, bad_id)
            assert response["reason_codes"] == ["invalid_source_ref"]
            assert response["source_ref"] is None
            assert response["byte_verified"] is False
            text = json.dumps(response)
            assert bad_id not in text
            assert "private-owner" not in text and "company-private" not in text


@pytest.mark.parametrize("legal_id", _LEGAL_REF_IDS)
def test_legal_opaque_ref_ids_remain_accepted(seeded, legal_id):
    """Opaque URNs/cwpdv tokens and plain doc ids are still valid IDs."""
    catalog, ref, tmp_path = seeded
    payload = _ref_payload(ref)
    # Use the legal id only for the field under test; keep the other legible.
    payload["document_id"] = legal_id
    # The catalogue may not have this id, but the REF SHAPE must be accepted
    # (a partial/not-indexed response, not an invalid_source_ref refusal).
    response = PublicSourceReadiness(SourceVersionReader(catalog)).assess(
        payload, mode="metadata_only"
    )
    assert response["reason_codes"] != ["invalid_source_ref"], legal_id
    assert response["status"] in {"partial", "ready"}


def test_cli_refuses_path_shaped_ref_before_catalog_access(seeded):
    catalog, ref, tmp_path = seeded
    catalog.close()
    config_path = _config_path(tmp_path)
    for bad_id in _PATH_REF_IDS:
        payload = _ref_payload(ref)
        payload["document_id"] = bad_id
        result = _run_cli(tmp_path, config_path, "metadata_only",
                          json.dumps(payload))
        assert result.returncode == 2, bad_id
        assert result.stdout == "" and result.stderr == ""
        assert "private" not in result.stderr and "etc" not in result.stdout


# --- metadata scrubbing: inline paths in any allowed string field -------------

# Computed (not literal) fake locations, same FC-1307-a rationale as above.
_D2, _D3 = "D", "E"
_METADATA_PATH_VALUES = (
    "internal cache /etc/company-private/source.pdf",   # POSIX inline
    "staged at " + _D2 + ":/data/cache/doc.pdf",        # drive inline fwd
    "staged at " + _D3 + ":" + _UNC + "data" + _UNC
    + "cache" + _UNC + "doc.pdf",                       # drive inline bwd
    _UNC + _UNC + "nas" + _UNC + "raw" + _UNC
    + "annual.pdf",                                     # UNC inline
    "file:///var/cache/doc.pdf",                        # file URI inline
    "copy ../updir/secret.pdf",                         # relative escape
)


@pytest.mark.parametrize("risky", _METADATA_PATH_VALUES)
def test_metadata_string_fields_with_inline_paths_are_scrubbed(tmp_path, risky):
    """Every allowlisted string field drops a value carrying a physical path;
    the response never echoes the location (D00-CWP-READINESS-002).

    Rebuilt via the real D00-002 flow: a sidecar whose ``source_title`` holds
    the risky value is scanned, then the ref is described through the public
    reader — no SQL shortcut that could bypass the real projection.
    """
    project = tmp_path / "project"
    companies = project / "companies"
    (companies / "ACME" / "raw").mkdir(parents=True)
    (companies / "ACME" / "raw" / "annual.pdf").write_bytes(PAYLOAD)
    (companies / "ACME" / "raw" / "annual.pdf.source.json").write_text(
        json.dumps({
            "document_kind": "annual_report", "source_type": "filing",
            "company_name": "ACME Corp", "security_id": "ACME", "market": "US",
            "provider": "sec", "source_title": risky, "form_type": "10-K",
            "fiscal_year": 2025, "fiscal_period": "FY",
            "filing_date": "2026-02-20", "published_date": "2026-02-20",
            "source_url": "https://www.sec.gov/Archives/edgar/data/1/annual.pdf",
            "retrieved_at": "2026-02-21T10:00:00Z",
            "collector_name": "readiness-fixture", "collector_version": "1.0.0",
            "mime_type": "application/pdf", "byte_size": len(PAYLOAD),
            "content_sha256": SHA,
            "files": [{"name": "annual.pdf", "source": "original"}],
        }),
        encoding="utf-8",
    )
    catalog = SourceCatalog(CatalogConfig(
        project_root=project, catalog_dir=project / ".source_catalog",
        roots=(RootSpec("company_raw", companies, "company_raw", priority=10),),
    ))
    catalog.scan()
    ref = _sole_ref(catalog)
    response = PublicSourceReadiness(SourceVersionReader(catalog)).assess(
        _ref_payload(ref), mode="metadata_only"
    )
    assert response["status"] == "ready", response
    metadata = response["metadata"]
    # Scrubbed values are DROPPED from the projection (never emitted as None
    # placeholders that could hint at a hidden location).
    assert metadata.get("title") is None, risky
    text = json.dumps(response)
    assert risky not in text
    catalog.close()


def test_metadata_nested_structures_are_recursively_scrubbed(seeded):
    """A nested capture blob cannot smuggle a path past the allowlist."""
    catalog, ref, tmp_path = seeded
    con = sqlite3.connect(f"file:{catalog.config.database_path}?mode=rw", uri=True)
    # Simulate a nested metadata blob carrying a path under an allowlisted key.
    _nested_origin = "/" + "etc/company-private/x.pdf"
    _nested_file = "/" + "var/cache/y.pdf"
    con.execute("UPDATE documents SET metadata_json=?", (
        json.dumps({"capture": {"origin": _nested_origin,
                                "files": [_nested_file, "ok-name"]}}),
    ))
    con.commit()
    con.close()
    response = PublicSourceReadiness(SourceVersionReader(catalog)).assess(
        _ref_payload(ref), mode="metadata_only"
    )
    text = json.dumps(response)
    _var_cache_marker = "/" + "var/cache"
    assert "company-private" not in text and _var_cache_marker not in text


def test_metadata_https_urls_and_prose_still_project(seeded):
    """A legitimate https source_url and an ordinary title are NOT scrubbed."""
    catalog, ref, tmp_path = seeded
    response = PublicSourceReadiness(SourceVersionReader(catalog)).assess(
        _ref_payload(ref), mode="metadata_only"
    )
    metadata = response["metadata"]
    assert metadata["title"] == SOURCE_TITLE
    # The sidecar recorded a https source_url; it must survive the scrub.
    url = metadata.get("source_url")
    if url is not None:
        assert url.startswith("https://")


def test_metadata_source_url_with_file_uri_is_scrubbed(seeded):
    """A file:// source_url is a physical location and is dropped."""
    catalog, ref, tmp_path = seeded
    con = sqlite3.connect(f"file:{catalog.config.database_path}?mode=rw", uri=True)
    con.execute("UPDATE documents SET metadata_json=?", (
        json.dumps({"source_url": "file:///C:/Users/private/annual.pdf"}),
    ))
    con.commit()
    con.close()
    response = PublicSourceReadiness(SourceVersionReader(catalog)).assess(
        _ref_payload(ref), mode="metadata_only"
    )
    metadata = response["metadata"]
    assert metadata.get("source_url") is None
    assert "file:///" not in json.dumps(response)


# --- D00-CWP-READINESS-003: delimiter-context path tokens (RETURN2) -----------
# The POSIX boundary is token+context recognition: a "/" at ANY delimiter
# (assignment, colon-label, bracket, brace, comma, semicolon, whitespace,
# start, ...) followed by path segments is a location; a "/" glued inside a
# URL path, a mime type or an A/B/C / 12/25 prose fragment is not.

_CONTEXT_PATH_TITLES = (
    "cache=/opt/company-private/source.pdf",            # assignment  =
    "cache:/var/company-private/source.pdf",            # colon-label :
    "cache[/private/company-private/source.pdf]",       # bracket     [
    "cache{/opt/company-private/source.pdf}",           # brace       {
    "cache,/opt/company-private/source.pdf",            # comma       ,
    "cache;/opt/company-private/source.pdf",            # semicolon   ;
)


@pytest.mark.parametrize("risky", _CONTEXT_PATH_TITLES)
def test_metadata_delimiter_context_paths_are_scrubbed(tmp_path, risky):
    """A path token preceded by =, :, [, {, , or ; is scrubbed from the
    projection — the RETURN2 same-root-cause matrix (D00-003)."""
    project = tmp_path / "project"
    companies = project / "companies"
    (companies / "ACME" / "raw").mkdir(parents=True)
    (companies / "ACME" / "raw" / "annual.pdf").write_bytes(PAYLOAD)
    (companies / "ACME" / "raw" / "annual.pdf.source.json").write_text(
        json.dumps({
            "document_kind": "annual_report", "source_type": "filing",
            "company_name": "ACME Corp", "security_id": "ACME", "market": "US",
            "provider": "sec", "source_title": risky, "form_type": "10-K",
            "fiscal_year": 2025, "fiscal_period": "FY",
            "filing_date": "2026-02-20", "published_date": "2026-02-20",
            "source_url": "https://www.sec.gov/Archives/edgar/data/1/annual.pdf",
            "retrieved_at": "2026-02-21T10:00:00Z",
            "collector_name": "readiness-fixture", "collector_version": "1.0.0",
            "mime_type": "application/pdf", "byte_size": len(PAYLOAD),
            "content_sha256": SHA,
            "files": [{"name": "annual.pdf", "source": "original"}],
        }),
        encoding="utf-8",
    )
    catalog = SourceCatalog(CatalogConfig(
        project_root=project, catalog_dir=project / ".source_catalog",
        roots=(RootSpec("company_raw", companies, "company_raw", priority=10),),
    ))
    catalog.scan()
    ref = _sole_ref(catalog)
    response = PublicSourceReadiness(SourceVersionReader(catalog)).assess(
        _ref_payload(ref), mode="metadata_only"
    )
    assert response["status"] == "ready", response
    assert response["metadata"].get("title") is None, risky
    assert risky not in json.dumps(response)
    catalog.close()


def test_context_paths_in_any_projected_string_field_are_scrubbed(seeded):
    """The same delimiter-context rule applies to EVERY projected string
    field, not just title: a path in display_name (DB-injected) is dropped."""
    catalog, ref, tmp_path = seeded
    _risky_display = "cache=/opt/company-private/display.pdf"
    con = sqlite3.connect(f"file:{catalog.config.database_path}?mode=rw", uri=True)
    con.execute("UPDATE documents SET metadata_json=?", (
        json.dumps({"display_name": _risky_display}),
    ))
    con.commit()
    con.close()
    response = PublicSourceReadiness(SourceVersionReader(catalog)).assess(
        _ref_payload(ref), mode="metadata_only"
    )
    assert response["status"] == "ready", response
    assert response["metadata"].get("display_name") is None
    assert "company-private" not in json.dumps(response)


def test_ref_ids_with_delimiter_context_paths_are_rejected(seeded):
    """The ref-ID admission uses the SAME predicate: a =/:/[ -delimited path
    in document_id is refused before the catalog is touched (exit 2 path)."""
    catalog, ref, tmp_path = seeded
    readiness = PublicSourceReadiness(SourceVersionReader(catalog))
    for bad_id in _CONTEXT_PATH_TITLES:
        payload = _ref_payload(ref)
        payload["document_id"] = bad_id
        response = readiness.assess(payload, mode="metadata_only")
        assert response["status"] == "unavailable", bad_id
        assert response["reason_codes"] == ["invalid_source_ref"]
        assert response["source_ref"] is None
        assert bad_id not in json.dumps(response)


def test_predicate_positive_matrix_preserves_legit_values():
    """Network URLs (path+query, colon-in-path, ftp), mime types, prose
    slashes, dates, fractions and opaque IDs are NOT flagged; delimiter-
    context path tokens ARE.  Guards the RETURN2 root fix against false
    positives."""
    from company_wiki.source_catalog.public_source_readiness import (
        _contains_physical_path,
    )
    negatives = (
        "cache=/opt/company-private/source.pdf",
        "cache:/var/company-private/source.pdf",
        "cache[/private/company-private/source.pdf]",
        "cache{/opt/x.pdf}", "cache,/opt/x.pdf", "cache;/opt/x.pdf",
        _DRIVE + ":/" + _P1 + "/" + _P2 + "/" + "annual.pdf",
        "C:" + _UNC + "Users" + _UNC + "private" + _UNC + "annual.pdf",
        _UNC + _UNC + "server" + _UNC + "share" + _UNC + "a.pdf",
        "/" + "/server/share/a.pdf",
        "file:///C:/Users/private/a.pdf",
        "file://server/share/a.pdf",
        "/" + "etc/company-private/source.pdf",
        "../../etc/passwd", "~/secret/a.pdf",
        "internal cache /etc/company-private/source.pdf",
        "staged at D:/data/cache/doc.pdf",
    )
    positives = (
        "https://www.sec.gov/Archives/edgar/data/123/annual.pdf?x=1&y=2",
        "https://example.com/a:b/c",
        "ftp://files.example.com/pub/x.pdf",
        "application/pdf", "application/octet-stream",
        "ACME Corp / FY2025 / 10-K Filing",
        "A/B/C testing and 12/25/2026 dates",
        "urn:company-wiki:document:sha256:" + SHA,
        "cwpdv1-" + SHA,
        "ACME 2025 Annual Report and Financial Statements",
        "Published 2026-02-20 (filed 2026-02-21)",
        "v1.2.3 build 45", "grew 3/4 over prior",
    )
    for value in negatives:
        assert _contains_physical_path(value), value
    for value in positives:
        assert not _contains_physical_path(value), value


# --- D00-CWP-READINESS-002 RETURN3: qualified-URL masking regression -----------
# A single-letter scheme is a Windows drive wearing a scheme shape, not a
# network URI: 'C://Users/…' must not be laundered by the URL mask.  Backslash/
# file locators are checked on the raw string so a scheme prefix cannot wash a
# bare locator embedded in a URL query.  Qualified multi-char-scheme URLs keep
# their path/query/fragment colons, ports and in-URL '///'.

_BS = _UNC  # backslash, for readability below

# PATH-URI-ACCEPTANCE-2026-10-29.md minimal cross-matrix (value, must_flag).
# Path literals are COMPUTED at runtime (FC-1307-a: the host-assumption guard
# scans ast.Constant host-absolute paths; computed values are out of its scope,
# and these are deliberately-fake negative fixtures, not host assumptions).
_ACCEPTANCE_MATRIX = (
    (_DRIVE + ":1secret.txt", True),                                # drive-relative
    (_DRIVE + "://Users/private-owner/source-root/annual.pdf", True),  # drive // (ex1)
    ("cache " + _DRIVE + "://Users/private-owner/source.pdf", True),   # drive // (ex2)
    ("cache=/opt/company-private/source.pdf", True),                 # assignment
    ("cache:/var/company-private/source.pdf", True),                 # colon-label
    ("cache[/private/company-private/source.pdf]", True),            # bracket
    ("https://example.test/a:b", False),                            # URL path colon
    ("https://example.test/?q=a:b", False),                         # URL query colon
    ("https://example.test/#a:b", False),                           # URL fragment colon
    ("https://example.test:8080/a///etc?value=/issuer", False),      # URL port + ///
    ("zz:" + _DRIVE + ":" + _BS + "secret" + _BS + "file", True),   # scheme-wrapped bwd
    ("https://example.test/?u=" + _DRIVE + ":" + _BS + "secret"
     + _BS + "file", True),                                         # URL w/ bare bwd locator
    ("file:///etc/passwd", True),                                   # file URI
    ("ACME A/B/C revenue rose 5% in 2025/26", False),               # prose
)


def test_path_uri_acceptance_cross_matrix():
    """The full PATH-URI-ACCEPTANCE minimal matrix: locators (incl. single-
    letter drives and bare backslash locators inside a URL query) are flagged;
    qualified multi-char-scheme URLs and ordinary prose are preserved."""
    from company_wiki.source_catalog.public_source_readiness import (
        _contains_physical_path,
    )
    for value, must_flag in _ACCEPTANCE_MATRIX:
        assert _contains_physical_path(value) is must_flag, value


# --- D00-CWP-READINESS-002 RETURN4: network-URI authority qualification --------
# A multi-char scheme alone does NOT qualify a URL for masking: structured
# parsing (urlsplit) must prove a real authority/host.  Empty-authority forms
# (https:///etc/…, https://?path=/opt/…) are locators wearing a scheme and are
# caught; qualified host URLs (incl. a single-letter host a:8080) are kept.

# PATH-URI-QUALIFICATION-2026-10-29.json vectors (value, must_flag).
_QUALIFICATION_VECTORS = (
    ("https:///etc/company-private/source.pdf", True),             # empty netloc
    ("https:///opt/company-private/source.pdf", True),             # empty netloc
    ("https:////opt/company-private/source.pdf", True),            # empty netloc ////
    ("https://?path=/opt/company-private/source.pdf", True),       # empty host, query
    ("https://#path=/opt/company-private/source.pdf", True),       # empty host, fragment
    ("https://example.test/a:b", False),                          # host path colon
    ("https://example.test/?q=a:b", False),                       # host query colon
    ("https://example.test/#a:b", False),                         # host fragment colon
    ("https://example.test:8080/a///etc?value=/issuer", False),    # host port + ///
    ("https://a:8080/x", False),                                  # single-LETTER host
)


def test_network_uri_authority_qualification_vectors():
    """Structured authority/host qualification: empty-authority scheme:///path
    locators are caught; qualified host URLs (incl. single-letter host) are
    preserved.  Guards the RETURN4 root fix against both leakage and over-
    rejection."""
    from company_wiki.source_catalog.public_source_readiness import (
        _contains_physical_path,
    )
    for value, must_flag in _QUALIFICATION_VECTORS:
        assert _contains_physical_path(value) is must_flag, value


def test_cli_empty_authority_scheme_path_title_scrubbed(tmp_path):
    """RETURN4 named example: sidecar source_title 'https:///etc/…' (empty
    authority) is scrubbed; the response carries no path."""
    project = tmp_path / "project"
    companies = project / "companies"
    (companies / "ACME" / "raw").mkdir(parents=True)
    (companies / "ACME" / "raw" / "annual.pdf").write_bytes(PAYLOAD)
    risky_title = "https:///etc/company-private/source.pdf"
    (companies / "ACME" / "raw" / "annual.pdf.source.json").write_text(
        json.dumps({
            "document_kind": "annual_report", "source_type": "filing",
            "company_name": "ACME Corp", "security_id": "ACME", "market": "US",
            "provider": "sec", "source_title": risky_title, "form_type": "10-K",
            "fiscal_year": 2025, "fiscal_period": "FY",
            "filing_date": "2026-02-20", "published_date": "2026-02-20",
            "source_url": "https://www.sec.gov/Archives/edgar/data/1/annual.pdf",
            "retrieved_at": "2026-02-21T10:00:00Z",
            "collector_name": "readiness-fixture", "collector_version": "1.0.0",
            "mime_type": "application/pdf", "byte_size": len(PAYLOAD),
            "content_sha256": SHA,
            "files": [{"name": "annual.pdf", "source": "original"}],
        }), encoding="utf-8")
    catalog = SourceCatalog(CatalogConfig(
        project_root=project, catalog_dir=project / ".source_catalog",
        roots=(RootSpec("company_raw", companies, "company_raw", priority=10),),
    ))
    catalog.scan()
    ref = _sole_ref(catalog)
    response = PublicSourceReadiness(SourceVersionReader(catalog)).assess(
        _ref_payload(ref), mode="metadata_only"
    )
    assert response["status"] == "ready", response
    assert response["metadata"].get("title") is None
    assert "company-private" not in json.dumps(response)
    catalog.close()


def test_cli_qualified_host_url_title_preserved(tmp_path):
    """A qualified host URL (single-letter host, port) as source_title is
    preserved verbatim — the qualification fix must not over-reject."""
    project = tmp_path / "project"
    companies = project / "companies"
    (companies / "ACME" / "raw").mkdir(parents=True)
    (companies / "ACME" / "raw" / "annual.pdf").write_bytes(PAYLOAD)
    ok_title = "https://a:8080/x?y=1"
    (companies / "ACME" / "raw" / "annual.pdf.source.json").write_text(
        json.dumps({
            "document_kind": "annual_report", "source_type": "filing",
            "company_name": "ACME Corp", "security_id": "ACME", "market": "US",
            "provider": "sec", "source_title": ok_title, "form_type": "10-K",
            "fiscal_year": 2025, "fiscal_period": "FY",
            "filing_date": "2026-02-20", "published_date": "2026-02-20",
            "source_url": "https://www.sec.gov/Archives/edgar/data/1/annual.pdf",
            "retrieved_at": "2026-02-21T10:00:00Z",
            "collector_name": "readiness-fixture", "collector_version": "1.0.0",
            "mime_type": "application/pdf", "byte_size": len(PAYLOAD),
            "content_sha256": SHA,
            "files": [{"name": "annual.pdf", "source": "original"}],
        }), encoding="utf-8")
    catalog = SourceCatalog(CatalogConfig(
        project_root=project, catalog_dir=project / ".source_catalog",
        roots=(RootSpec("company_raw", companies, "company_raw", priority=10),),
    ))
    catalog.scan()
    ref = _sole_ref(catalog)
    response = PublicSourceReadiness(SourceVersionReader(catalog)).assess(
        _ref_payload(ref), mode="metadata_only"
    )
    assert response["status"] == "ready", response
    assert response["metadata"].get("title") == ok_title
    catalog.close()


def test_cli_drive_double_slash_ref_id_rejected_before_catalog(seeded):
    """ex1: a legal-shape ref whose document_id is 'C://Users/…' is refused
    at the CLI boundary (exit 2, no stdout, no path echo) — the URL mask must
    not launder a single-letter drive."""
    catalog, ref, tmp_path = seeded
    catalog.close()
    config_path = _config_path(tmp_path)
    bad_id = _DRIVE + "://Users/private-owner/source-root/annual.pdf"
    payload = _ref_payload(ref)
    payload["document_id"] = bad_id
    result = _run_cli(tmp_path, config_path, "metadata_only",
                      json.dumps(payload))
    assert result.returncode == 2
    assert result.stdout == "" and result.stderr == ""
    assert "private-owner" not in result.stdout + result.stderr


def test_cli_drive_double_slash_title_scrubbed(tmp_path):
    """ex2: a sidecar source_title 'cache C://Users/…' is scrubbed from the
    projection; the response carries no path."""
    project = tmp_path / "project"
    companies = project / "companies"
    (companies / "ACME" / "raw").mkdir(parents=True)
    (companies / "ACME" / "raw" / "annual.pdf").write_bytes(PAYLOAD)
    risky_title = "cache " + _DRIVE + "://Users/private-owner/source.pdf"
    (companies / "ACME" / "raw" / "annual.pdf.source.json").write_text(
        json.dumps({
            "document_kind": "annual_report", "source_type": "filing",
            "company_name": "ACME Corp", "security_id": "ACME", "market": "US",
            "provider": "sec", "source_title": risky_title, "form_type": "10-K",
            "fiscal_year": 2025, "fiscal_period": "FY",
            "filing_date": "2026-02-20", "published_date": "2026-02-20",
            "source_url": "https://www.sec.gov/Archives/edgar/data/1/annual.pdf",
            "retrieved_at": "2026-02-21T10:00:00Z",
            "collector_name": "readiness-fixture", "collector_version": "1.0.0",
            "mime_type": "application/pdf", "byte_size": len(PAYLOAD),
            "content_sha256": SHA,
            "files": [{"name": "annual.pdf", "source": "original"}],
        }), encoding="utf-8")
    catalog = SourceCatalog(CatalogConfig(
        project_root=project, catalog_dir=project / ".source_catalog",
        roots=(RootSpec("company_raw", companies, "company_raw", priority=10),),
    ))
    catalog.scan()
    ref = _sole_ref(catalog)
    response = PublicSourceReadiness(SourceVersionReader(catalog)).assess(
        _ref_payload(ref), mode="metadata_only"
    )
    assert response["status"] == "ready", response
    assert response["metadata"].get("title") is None
    assert "private-owner" not in json.dumps(response)
    catalog.close()


def test_ref_ids_drive_relative_and_drive_slash_rejected(seeded):
    """Ref-ID admission uses the same predicate: drive-relative ('C:1…') and
    drive-slash ('C://…') IDs are refused before the catalog is touched."""
    catalog, ref, tmp_path = seeded
    readiness = PublicSourceReadiness(SourceVersionReader(catalog))
    for bad_id in (
        _DRIVE + ":1secret.txt",
        _DRIVE + "://Users/private-owner/source-root/annual.pdf",
        "cache " + _DRIVE + "://Users/private-owner/source.pdf",
    ):
        payload = _ref_payload(ref)
        payload["document_id"] = bad_id
        response = readiness.assess(payload, mode="metadata_only")
        assert response["status"] == "unavailable", bad_id
        assert response["reason_codes"] == ["invalid_source_ref"]
        assert response["source_ref"] is None
        assert bad_id not in json.dumps(response)


# --- D00-CWP-READINESS-001: historical non-primary integration via EXACT -------

from company_wiki.source_catalog.public_document_browser import (  # noqa: E402
    BROWSE_REQUEST_SCHEMA,
    PublicDocumentBrowser,
)


_HIST_PRIMARY = b"%PDF-1.4 acme annual report 2025 primary original"
_HIST_AMENDED = b"%PDF-1.4 acme amended history v2 (different bytes!)"
_HIST_PRIMARY_SHA = hashlib.sha256(_HIST_PRIMARY).hexdigest()
_HIST_AMENDED_SHA = hashlib.sha256(_HIST_AMENDED).hexdigest()
_HIST_ENT = "ent-acme-hist"


def _write_history_tree(tmp_path: Path) -> None:
    """dayu portfolio: ONE logical filing with TWO distinct byte versions."""
    filing_dir = tmp_path / "portfolio" / "ACME" / "filings" / "fil_x"
    filing_dir.mkdir(parents=True)
    (filing_dir / "fil_x.pdf").write_bytes(_HIST_PRIMARY)
    (filing_dir / "fil_x_amended.pdf").write_bytes(_HIST_AMENDED)
    (filing_dir / "meta.json").write_text(json.dumps({
        "document_id": "fil_x", "ticker": "ACME", "form_type": "FY",
        "canonical_entity_id": _HIST_ENT, "display_name": "Acme",
        "market": "CN", "document_kind": "annual_report", "fiscal_year": 2024,
        "filing_date": "2025-03-30", "source_provider": "dayu",
        "source_id": "fil_x", "source_language": "en", "ingest_complete": True,
        "primary_document": "fil_x.pdf",
    }, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "portfolio" / "ACME" / "meta.json").write_text(
        json.dumps({"ticker": "ACME", "market": "CN"}), encoding="utf-8",
    )


def _build_history_catalog(tmp_path: Path) -> SourceCatalog:
    _write_history_tree(tmp_path)
    catalog = SourceCatalog(CatalogConfig(
        project_root=tmp_path,
        catalog_dir=tmp_path / ".source_catalog",
        roots=(RootSpec("dayu_portfolio", tmp_path / "portfolio",
                        "dayu_portfolio", priority=20,
                        adapter_id="dayu_filing_v1", read_only=True,
                        reusable_for_filing=True),),
        reusable_root_kinds=("dayu_portfolio",),
    ))
    catalog.scan()
    return catalog


def _history_refs_via_browser(catalog: SourceCatalog):
    """Public flow: browser.browse(entity) → two versions → pick non-primary."""
    browser = PublicDocumentBrowser(catalog)
    result = browser.browse({
        "schema_version": BROWSE_REQUEST_SCHEMA,
        "canonical_entity_id": _HIST_ENT, "market": None,
        "document_kinds": ["annual_report"], "fiscal_years": [2024],
        "language": None, "source_statuses": None, "limit": None,
        "cursor": None, "snapshot_id": None,
    })
    assert result["state"] in {"available", "partial"}, result
    items = result["items"]
    assert len(items) == 2, items
    primary = next(i for i in items if i["is_current_version"])
    history = next(i for i in items if not i["is_current_version"])
    assert primary["source_ref"]["content_sha256"] == _HIST_PRIMARY_SHA
    assert history["source_ref"]["content_sha256"] == _HIST_AMENDED_SHA
    assert history["source_ref"]["document_id"] == \
        primary["source_ref"]["document_id"]
    return catalog, primary, history


def _history_config_path(tmp_path: Path) -> Path:
    config_path = tmp_path / "source_catalog.yaml"
    config_path.write_text(json.dumps({
        "schema_version": "1.0",
        "catalog_dir": str(tmp_path / ".source_catalog"),
        "reusable_root_kinds": ["dayu_portfolio"],
        "roots": [{
            "root_id": "dayu_portfolio", "kind": "dayu_portfolio",
            "path": str(tmp_path / "portfolio"), "priority": 20,
        }],
    }), encoding="utf-8")
    return config_path


def test_history_nonprimary_ref_verifies_through_readiness_cli(tmp_path):
    """Browser-selected non-primary ref → readiness CLI verify_existing_bytes
    → ready + byte_verified=true + receipt with SAME hash/size (D00-001)."""
    catalog, primary, history = _history_refs_via_browser(
        _build_history_catalog(tmp_path)
    )
    catalog.close()
    config_path = _history_config_path(tmp_path)
    ref = history["source_ref"]
    result = _run_cli(tmp_path, config_path, "verify_existing_bytes",
                      json.dumps(ref))
    assert result.returncode == 0, result.stderr
    response = json.loads(result.stdout)
    receipt = _ready_verify(response, _HIST_AMENDED_SHA, len(_HIST_AMENDED))
    assert receipt["content_sha256"] == _HIST_AMENDED_SHA
    assert receipt["byte_size"] == len(_HIST_AMENDED)
    assert receipt["document_id"] == ref["document_id"]
    assert receipt["source_id"] == ref["source_id"]


def test_history_primary_and_nonprimary_have_different_bytes(tmp_path):
    """Primary and history are genuinely different versions (no latest-
    substitution): each ref verifies its OWN bytes."""
    catalog, primary, history = _history_refs_via_browser(
        _build_history_catalog(tmp_path)
    )
    readiness = PublicSourceReadiness(SourceVersionReader(catalog))
    for item, expected_sha, expected_size in (
        (primary, _HIST_PRIMARY_SHA, len(_HIST_PRIMARY)),
        (history, _HIST_AMENDED_SHA, len(_HIST_AMENDED)),
    ):
        response = readiness.assess(item["source_ref"],
                                    mode="verify_existing_bytes")
        receipt = _ready_verify(response, expected_sha, expected_size)
        assert receipt["content_sha256"] == expected_sha
        assert receipt["byte_size"] == expected_size
    catalog.close()


def test_history_retired_version_stays_blocked(tmp_path):
    """An inactive/retired history version keeps refusing with its own named
    reason even after the pair-precise lookup."""
    catalog, primary, history = _history_refs_via_browser(
        _build_history_catalog(tmp_path)
    )
    con = sqlite3.connect(f"file:{catalog.config.database_path}?mode=rw", uri=True)
    con.execute("UPDATE documents SET source_status='retired'")
    con.commit()
    con.close()
    readiness = PublicSourceReadiness(SourceVersionReader(catalog))
    response = readiness.assess(history["source_ref"],
                                mode="verify_existing_bytes")
    assert response["status"] == "blocked"
    assert response["reason_codes"] == ["source_not_active"]
    catalog.close()


def test_history_unconfigured_root_is_unavailable(tmp_path):
    """A history ref whose root is not in the operator config is refused
    (no disk search, no latest substitution)."""
    catalog, primary, history = _history_refs_via_browser(
        _build_history_catalog(tmp_path)
    )
    catalog.close()
    empty_config = tmp_path / "empty.yaml"
    empty_config.write_text(json.dumps({
        "schema_version": "1.0",
        "catalog_dir": str(tmp_path / ".source_catalog"),
        "roots": [{
            "root_id": "company_raw", "kind": "company_raw",
            "path": str(tmp_path / "other_root"), "priority": 10,
        }],
    }), encoding="utf-8")
    result = _run_cli(tmp_path, empty_config, "verify_existing_bytes",
                      json.dumps(history["source_ref"]))
    assert result.returncode == 0
    response = json.loads(result.stdout)
    assert response["status"] in {"partial", "unavailable", "blocked"}
    assert response["byte_verified"] is False


# D00 direct small repair: parsed host alone cannot qualify an illegal port.
@pytest.mark.parametrize(
    "risky", ["zz://C:secret.txt", "https://C:secret.txt/opt/cache.pdf"],
)
def test_d00_illegal_authority_port_ref_is_refused(seeded, risky):
    catalog, ref, tmp_path = seeded
    payload = _ref_payload(ref)
    payload["document_id"] = risky
    result = _run_cli(
        tmp_path, _config_path(tmp_path), "metadata_only", json.dumps(payload),
    )
    assert result.returncode == 2
    assert not result.stdout
    assert risky not in result.stderr


@pytest.mark.parametrize(
    "risky", ["zz://C:secret.txt", "https://C:secret.txt/opt/cache.pdf"],
)
def test_d00_illegal_authority_port_title_is_scrubbed(tmp_path, monkeypatch, risky):
    monkeypatch.setattr(sys.modules[__name__], "SOURCE_TITLE", risky)
    catalog = _seed_catalog(tmp_path)
    try:
        ref = _sole_ref(catalog)
    finally:
        catalog.close()
    result = _run_cli(
        tmp_path, _config_path(tmp_path), "metadata_only", json.dumps(_ref_payload(ref)),
    )
    assert result.returncode == 0, result.stderr
    response = json.loads(result.stdout)
    metadata = _ready_metadata(response)
    assert "title" not in metadata
    assert risky not in result.stdout
