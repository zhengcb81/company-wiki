"""Caller contract for the pathless SourceExport v2 publishing CLI.

All catalog files and sidecars are synthetic and confined to tmp_path.
The CLI is invoked from another cwd with a production-shaped config path.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path
import subprocess
import sys

from company_wiki.source_catalog import SourceCatalog
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.source_reader import SourceVersionReader
from company_wiki.source_contract import (
    EvidenceCoordinates,
    EvidenceSpan,
    ParseStatus,
    SourceExportBundleV2,
)


ROOT = Path(__file__).resolve().parents[2]
CLI_MODULE = "company_wiki.source_catalog.source_export_v2_cli"
TEXT_PREFIX = "正文🙂 "
TEXT_QUOTE = "Revenue increased."
BODY = (
    TEXT_PREFIX + TEXT_QUOTE + " EXPORT-V2-RAW-BYTES-SENTINEL End"
).encode("utf-8")
PDF_BODY = b"%PDF-1.4\nEXPORT-V2-RAW-BYTES-SENTINEL\n"
SHA = hashlib.sha256(BODY).hexdigest()
BUNDLE_FIELDS = {
    "schema_version", "source_manifest_schema_version",
    "evidence_span_schema_version", "counts", "manifests",
    "evidence_spans", "bundle_sha256", "export_id",
}


def _snapshot(root: Path) -> dict[str, tuple]:
    result: dict[str, tuple] = {}
    for path in sorted(root.rglob("*")):
        info = path.stat()
        name = path.relative_to(root).as_posix()
        if path.is_file():
            # SQLite WAL readers may refresh the -shm mtime while taking a
            # read lock. Its bytes and size must still remain unchanged.
            observed_mtime = (
                None if path.name.endswith("-shm") else info.st_mtime_ns
            )
            result[name] = (
                "file", info.st_size, observed_mtime,
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        else:
            result[name] = ("directory", info.st_mtime_ns)
    return result


def _fixture(
    tmp_path: Path, *, text_mode: bool = True
) -> tuple[Path, Path, Path, dict, dict]:
    body = BODY if text_mode else PDF_BODY
    digest = hashlib.sha256(body).hexdigest()
    file_name = "2025.txt" if text_mode else "2025.pdf"
    project = tmp_path / "project"
    raw_root = project / "lake"
    raw_root.mkdir(parents=True)
    raw = raw_root / file_name
    raw.write_bytes(body)
    sidecar = {
        "schema_version": "1.0",
        "canonical_entity_id": "ent-acme",
        "display_name": "Acme",
        "market": "US",
        "security_id": "ACME",
        "document_kind": "annual_report",
        "source_title": "Acme 2025 annual report",
        "fiscal_year": 2025,
        "period_end": "2025-12-31",
        "filing_date": "2026-02-20",
        "form_type": "10-K",
        "provider": "sec",
        "provider_document_id": "doc-v2-cli-1",
        "source_url": "https://sec.gov/x/2025",
        "content_sha256": digest,
        "retrieved_at": "2026-02-21T00:00:00Z",
        "collector_name": "sec_edgar",
        "collector_version": "1.0",
    }
    (raw_root / f"{file_name}.source.json").write_text(
        json.dumps(sidecar), encoding="utf-8"
    )
    config_dir = project / "config"
    config_dir.mkdir()
    config_path = config_dir / "source_catalog.yaml"
    config_path.write_text(
        json.dumps({
            "schema_version": "1.0",
            "catalog_dir": "${PROJECT_ROOT}/state/catalog",
            "reusable_root_kinds": ["directory"],
            "roots": [{
                "root_id": "future_lake",
                "kind": "directory",
                "path": "${PROJECT_ROOT}/lake",
                "priority": 10,
                "adapter_id": "sidecar_filing_v1",
                "read_only": True,
                "reusable_for_filing": True,
            }],
        }),
        encoding="utf-8",
    )
    config = load_catalog_config(config_path)
    assert config.project_root == project
    assert config.catalog_dir.is_relative_to(project)
    assert all(root.path.is_relative_to(project) for root in config.roots)
    catalog = SourceCatalog(config)
    try:
        catalog.scan()
        row = catalog.reader.fetchone(
            """SELECT d.document_id, d.primary_source_id AS source_id,
                      s.content_sha256
               FROM documents d JOIN sources s
                 ON s.source_id=d.primary_source_id
               WHERE d.source_status='active' AND s.content_sha256=?""",
            (digest,),
        )
        assert row is not None
        ref = SourceVersionReader(catalog).query_ref(
            row["document_id"], row["source_id"], digest
        )
    finally:
        catalog.close()
    span = EvidenceSpan.create(
        source_id=ref.source_id,
        coordinates=(
            EvidenceCoordinates(
                char_start=len(TEXT_PREFIX),
                char_end=len(TEXT_PREFIX) + len(TEXT_QUOTE),
            )
            if text_mode else EvidenceCoordinates(page_number=1)
        ),
        raw_text=TEXT_QUOTE,
        structured_value=None,
        parser_name="fixture-parser",
        parser_version="1.0.0",
        parse_status=ParseStatus.PARSED,
        quality_flags=(),
    )
    caller_cwd = tmp_path / "caller"
    caller_cwd.mkdir()
    guard_dir = tmp_path / "guard"
    guard_dir.mkdir()
    (guard_dir / "sitecustomize.py").write_text(
        "import socket, subprocess\n"
        "def forbidden(*args, **kwargs):\n"
        "    raise RuntimeError('network or child process forbidden in export CLI')\n"
        "socket.socket.connect = forbidden\n"
        "socket.socket.connect_ex = forbidden\n"
        "socket.create_connection = forbidden\n"
        "subprocess.Popen = forbidden\n",
        encoding="utf-8",
    )
    return config_path, raw, guard_dir, asdict(ref), span.to_dict()


def _run_cli(
    config_path: Path, guard_dir: Path, ref: dict, span: dict | None, cwd: Path
) -> subprocess.CompletedProcess[bytes]:
    env = os.environ.copy()
    env["PYTHONPATH"] = (
        str(guard_dir) + os.pathsep + str(ROOT / "src")
        + os.pathsep + env.get("PYTHONPATH", "")
    )
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    request = {
        "schema_version": "2.0",
        "source_refs": [ref],
        "evidence_spans": [span] if span is not None else [],
    }
    assert not any(
        token in key.lower()
        for key in request
        for token in ("path", "root", "location")
    )
    return subprocess.run(
        [
            sys.executable, "-B", "-m", CLI_MODULE,
            "--config", str(config_path),
        ],
        input=json.dumps(request, ensure_ascii=False).encode("utf-8"),
        cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False, timeout=30,
    )


def _one_json_error(proc: subprocess.CompletedProcess[bytes], tmp_path: Path) -> dict:
    assert proc.returncode != 0
    assert proc.stdout == b""
    assert proc.stderr.endswith(b"\n"), proc.stderr
    lines = proc.stderr.decode("utf-8").splitlines()
    assert len(lines) == 1, proc.stderr
    error = json.loads(lines[0])
    assert isinstance(error, dict)
    assert error["schema_version"] == "2.0"
    assert error["status"] in {
        "not_found", "not_indexed", "unavailable", "blocked", "ambiguous"
    }
    assert isinstance(error["reason"], str) and error["reason"]
    assert not any(
        token in key.lower()
        for key in error
        for token in ("path", "root", "location")
    )
    assert str(tmp_path) not in lines[0]
    return error


def test_cli_publishes_one_strict_pathless_v2_bundle_without_scanning(
    tmp_path: Path,
) -> None:
    config_path, _raw, guard_dir, ref, span = _fixture(tmp_path)
    before = _snapshot(tmp_path)
    proc = _run_cli(config_path, guard_dir, ref, span, tmp_path / "caller")
    assert proc.returncode == 0, proc.stderr
    assert proc.stderr == b""
    assert proc.stdout.endswith(b"\n")
    assert len(proc.stdout.splitlines()) == 1
    wire = json.loads(proc.stdout)
    assert set(wire) == BUNDLE_FIELDS
    assert SourceExportBundleV2.from_json(proc.stdout).to_dict() == wire
    assert wire["schema_version"] == "2.0.0"
    assert wire["counts"] == {"source_manifests": 1, "evidence_spans": 1}
    manifest = wire["manifests"][0]
    assert manifest["document_id"] == ref["document_id"]
    assert manifest["source_id"] == ref["source_id"]
    assert manifest["content_sha256"] == SHA
    assert manifest["title"] == "Acme 2025 annual report"
    assert wire["evidence_spans"] == [span]
    assert str(tmp_path) not in proc.stdout.decode("utf-8")
    assert b"EXPORT-V2-RAW-BYTES-SENTINEL" not in proc.stdout
    assert _snapshot(tmp_path) == before


def test_cli_rejects_unverified_pdf_span_and_publishes_pdf_manifest_only(
    tmp_path: Path,
) -> None:
    config_path, _raw, guard_dir, ref, forged_span = _fixture(
        tmp_path, text_mode=False
    )
    before = _snapshot(tmp_path)
    rejected = _run_cli(
        config_path, guard_dir, ref, forged_span, tmp_path / "caller"
    )
    error = _one_json_error(rejected, tmp_path)
    assert error["status"] == "blocked"
    assert error["reason"] == "invalid_request"

    allowed = _run_cli(config_path, guard_dir, ref, None, tmp_path / "caller")
    assert allowed.returncode == 0, allowed.stderr
    wire = SourceExportBundleV2.from_json(allowed.stdout).to_dict()
    assert wire["counts"] == {"source_manifests": 1, "evidence_spans": 0}
    assert wire["manifests"][0]["mime_type"] == "application/pdf"
    assert _snapshot(tmp_path) == before


def test_cli_rejects_bad_source_ref_hash_with_empty_stdout(
    tmp_path: Path,
) -> None:
    config_path, _raw, guard_dir, ref, span = _fixture(tmp_path)
    ref["content_sha256"] = "0" * 64
    before = _snapshot(tmp_path)
    proc = _run_cli(config_path, guard_dir, ref, span, tmp_path / "caller")
    _one_json_error(proc, tmp_path)
    assert _snapshot(tmp_path) == before


def test_cli_rejects_same_size_raw_byte_drift_with_empty_stdout(
    tmp_path: Path,
) -> None:
    config_path, raw, guard_dir, ref, span = _fixture(tmp_path)
    raw.write_bytes(BODY[:-1] + b"X")
    assert raw.stat().st_size == len(BODY)
    before = _snapshot(tmp_path)
    proc = _run_cli(config_path, guard_dir, ref, span, tmp_path / "caller")
    _one_json_error(proc, tmp_path)
    assert _snapshot(tmp_path) == before


def test_cli_matches_frozen_source_v2_golden(tmp_path: Path) -> None:
    """Freeze actual CLI bytes for pathless cross-repo consumers."""
    config_path, _raw, guard_dir, ref, span = _fixture(tmp_path)
    goldens = ROOT / "tests" / "golden" / "source_v2"
    ref_wire = (
        json.dumps(ref, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    assert ref_wire == (goldens / "source_ref.json").read_bytes()
    span_wire = (
        json.dumps(span, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    assert span_wire == (goldens / "evidence_span.json").read_bytes()
    process = _run_cli(config_path, guard_dir, ref, span, tmp_path / "caller")
    assert process.returncode == 0, process.stderr
    assert process.stderr == b""
    assert process.stdout == (goldens / "source_export_bundle.json").read_bytes()
    bad_ref = json.loads((goldens / "source_ref_bad_sha.json").read_bytes())
    assert set(bad_ref) == set(ref)
    assert bad_ref["content_sha256"] != ref["content_sha256"]
    rejected = _run_cli(config_path, guard_dir, bad_ref, span, tmp_path / "caller")
    assert rejected.returncode == 2
    assert rejected.stdout == b""
    assert json.loads(rejected.stderr)["status"] in {"not_found", "unavailable"}
