"""Caller contract for the pathless processed-document reading CLI.

D5 frozen contract: ``company-wiki-processed-document/1``.  All catalog files
and sidecars are synthetic and confined to tmp_path; fixtures are built with
the same parser libraries the owner uses (python-docx, PyMuPDF, openpyxl) so
the responses exercise the real parse composition.  The CLI is invoked from
another cwd with a production-shaped config path; network is forbidden in the
CLI and its parser child, subprocesses are allowed (PDF/text parse in the
catalog's isolated parser process).
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import docx
import fitz
import openpyxl

from company_wiki.source_catalog import SourceCatalog
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.source_reader import SourceVersionReader


ROOT = Path(__file__).resolve().parents[2]
CLI_MODULE = "company_wiki.source_catalog.processed_document_cli"
SCHEMA = "company-wiki-processed-document/1"

ENVELOPE_FIELDS = {
    "schema_version", "source_ref", "manifest", "parser", "status",
    "units", "continuation", "quality",
}
UNIT_FIELDS = {"unit_id", "kind", "locator", "content"}
QUALITY_FIELDS = {
    "quality_flags", "coverage_complete", "page_count", "errors", "reason",
}
MANIFEST_IDENTITY = {
    "document_id", "source_id", "content_sha256", "byte_size", "mime_type",
}

PARAGRAPH_ONE = "D5 contract paragraph one: revenue increased twelve percent."
PARAGRAPH_TWO = "D5 contract paragraph two: 刻蚀设备收入创新高。"
#: PyMuPDF's default font cannot embed CJK, so the PDF fixture stays ASCII
#: (the DOCX/TXT fixtures carry the CJK coverage instead).
PDF_TEXT_ONE = "D5 contract paragraph one: revenue increased twelve percent."
PDF_TEXT_TWO = "D5 contract paragraph two: etch revenue reached a new high."


def _docx_bytes() -> bytes:
    document = docx.Document()
    document.add_heading("D5 contract heading", level=1)
    document.add_paragraph(PARAGRAPH_ONE)
    document.add_paragraph(PARAGRAPH_TWO)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _pdf_bytes() -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), PDF_TEXT_ONE)
    second = document.new_page()
    second.insert_text((72, 72), PDF_TEXT_TWO)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _xlsx_bytes(*, empty_sheet: bool = False) -> bytes:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Income"
    if not empty_sheet:
        sheet.append(["item", "value"])
        sheet.append(["revenue", 123])
        sheet.append(["cost", None])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


BODIES: dict[str, bytes] = {
    "2025.txt": (PARAGRAPH_ONE + "\n\n" + PARAGRAPH_TWO + "\n").encode("utf-8"),
    "partial-2024.txt": "正文2024🡒 部分文本".encode("gb18030"),
    "2025.docx": _docx_bytes(),
    "2025.pdf": _pdf_bytes(),
    "2025.xlsx": _xlsx_bytes(),
    "empty-2023.xlsx": _xlsx_bytes(empty_sheet=True),
}


def _snapshot(root: Path) -> dict[str, tuple]:
    result: dict[str, tuple] = {}
    for path in sorted(root.rglob("*")):
        info = path.stat()
        name = path.relative_to(root).as_posix()
        if path.is_file():
            result[name] = (
                "file", info.st_size, info.st_mtime_ns,
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        else:
            result[name] = ("directory", info.st_mtime_ns)
    return result


def _fixture(tmp_path: Path) -> dict[str, dict]:
    project = tmp_path / "project"
    raw_root = project / "lake"
    raw_root.mkdir(parents=True)
    for file_name, body in BODIES.items():
        (raw_root / file_name).write_bytes(body)
        sidecar = {
            "schema_version": "1.0",
            "canonical_entity_id": "ent-acme",
            "display_name": "Acme",
            "market": "CN",
            "security_id": "688012",
            "document_kind": "annual_report",
            "source_title": f"Acme contract {file_name}",
            "fiscal_year": 2025,
            "period_end": "2025-12-31",
            "filing_date": "2026-02-20",
            "form_type": "10-K",
            "provider": "sec",
            "provider_document_id": f"doc-{file_name}",
            "source_url": "https://sec.gov/x/2025",
            "content_sha256": hashlib.sha256(body).hexdigest(),
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
    catalog = SourceCatalog(config)
    try:
        catalog.scan()
        reader = SourceVersionReader(catalog)
        refs: dict[str, dict] = {}
        for file_name, body in BODIES.items():
            digest = hashlib.sha256(body).hexdigest()
            row = catalog.reader.fetchone(
                """SELECT d.document_id, d.primary_source_id AS source_id,
                          s.byte_size, s.mime_type
                   FROM documents d JOIN sources s
                     ON s.source_id=d.primary_source_id
                   WHERE d.source_status='active' AND s.content_sha256=?""",
                (digest,),
            )
            assert row is not None, file_name
            ref = reader.query_ref(row["document_id"], row["source_id"], digest)
            refs[file_name] = {
                "ref": dict(
                    schema_version=ref.schema_version,
                    document_id=ref.document_id,
                    source_id=ref.source_id,
                    content_sha256=ref.content_sha256,
                    byte_size=ref.byte_size,
                    mime_type=ref.mime_type,
                ),
                "tmp_project": str(project),
            }
    finally:
        catalog.close()
    return refs


def _guard_dir(tmp_path: Path) -> Path:
    guard_dir = tmp_path / "guard"
    guard_dir.mkdir()
    (guard_dir / "sitecustomize.py").write_text(
        "import socket\n"
        "def forbidden(*args, **kwargs):\n"
        "    raise RuntimeError('network forbidden in processed-document CLI')\n"
        "socket.socket.connect = forbidden\n"
        "socket.socket.connect_ex = forbidden\n"
        "socket.create_connection = forbidden\n",
        encoding="utf-8",
    )
    return guard_dir


def _run_cli(
    config_path: Path,
    guard_dir: Path,
    request: dict,
    cwd: Path,
) -> subprocess.CompletedProcess[bytes]:
    env = os.environ.copy()
    env["PYTHONPATH"] = (
        str(guard_dir) + os.pathsep + str(ROOT / "src")
        + os.pathsep + env.get("PYTHONPATH", "")
    )
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"
    return subprocess.run(
        [sys.executable, "-m", CLI_MODULE, "--config", str(config_path)],
        input=json.dumps(request, ensure_ascii=True).encode("utf-8"),
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=300,
    )


def _parse_envelope(completed: subprocess.CompletedProcess[bytes]) -> dict:
    assert completed.returncode == 0, completed.stderr.decode("utf-8", "replace")
    lines = completed.stdout.decode("utf-8").strip().splitlines()
    assert len(lines) == 1, "the CLI writes exactly one JSON line"
    return json.loads(lines[0])


def _request(ref: dict, **options) -> dict:
    request = {"schema_version": SCHEMA, "source_ref": dict(ref)}
    if options:
        request["options"] = options
    return request


def _assert_envelope_shape(envelope: dict, ref: dict) -> None:
    assert set(envelope) == ENVELOPE_FIELDS
    assert envelope["schema_version"] == SCHEMA
    assert envelope["source_ref"] == ref, "identity must echo the request exactly"
    manifest = envelope["manifest"]
    assert isinstance(manifest, dict)
    assert "original_path" not in manifest
    for key in MANIFEST_IDENTITY:
        assert manifest[key] == ref[key], key
    parser = envelope["parser"]
    assert set(parser) == {"name", "version", "profile"}
    assert isinstance(parser["name"], str) and parser["name"]
    assert isinstance(parser["version"], str) and parser["version"]
    assert envelope["status"] in {"complete", "partial", "unsupported"}
    assert isinstance(envelope["units"], list)
    for unit in envelope["units"]:
        assert set(unit) == UNIT_FIELDS
        assert isinstance(unit["unit_id"], str) and unit["unit_id"]
        assert isinstance(unit["kind"], str) and unit["kind"]
        assert isinstance(unit["locator"], str) and unit["locator"]
    assert envelope["continuation"] is None or (
        isinstance(envelope["continuation"], dict)
        and set(envelope["continuation"]) == {"cursor", "has_more"}
        and envelope["continuation"]["has_more"] is True
        and isinstance(envelope["continuation"]["cursor"], str)
    )
    assert set(envelope["quality"]) == QUALITY_FIELDS


def test_text_source_returns_a_complete_ordered_envelope(tmp_path: Path):
    refs = _fixture(tmp_path)
    config_path = refs["2025.txt"]["tmp_project"] + "/config/source_catalog.yaml"
    ref = refs["2025.txt"]["ref"]
    caller = tmp_path / "caller"
    caller.mkdir()
    completed = _run_cli(
        Path(config_path), _guard_dir(tmp_path), _request(ref), caller,
    )
    envelope = _parse_envelope(completed)
    _assert_envelope_shape(envelope, ref)
    assert envelope["status"] == "complete"
    assert envelope["parser"]["name"] == "plain_text"
    assert len(envelope["units"]) >= 2
    assert envelope["units"][0]["kind"] == "text"
    assert envelope["units"][0]["locator"].startswith("loc:v1/")
    assert envelope["continuation"] is None
    payload = completed.stdout.decode("utf-8")
    assert "original_path" not in payload
    assert refs["2025.txt"]["tmp_project"] not in payload, "no storage path leaks"
    assert "lake" not in payload


def test_unit_ids_are_stable_across_requests(tmp_path: Path):
    refs = _fixture(tmp_path)
    config_path = Path(refs["2025.txt"]["tmp_project"]) / "config/source_catalog.yaml"
    ref = refs["2025.txt"]["ref"]
    caller = tmp_path / "caller"
    caller.mkdir()
    guard = _guard_dir(tmp_path)
    first = _parse_envelope(_run_cli(config_path, guard, _request(ref), caller))
    second = _parse_envelope(_run_cli(config_path, guard, _request(ref), caller))
    assert [unit["unit_id"] for unit in first["units"]] == [
        unit["unit_id"] for unit in second["units"]
    ]
    assert all(unit["unit_id"].startswith("urn:company-wiki:") for unit in first["units"])


def test_docx_returns_normalization_owner_units(tmp_path: Path):
    refs = _fixture(tmp_path)
    config_path = Path(refs["2025.docx"]["tmp_project"]) / "config/source_catalog.yaml"
    ref = refs["2025.docx"]["ref"]
    caller = tmp_path / "caller"
    caller.mkdir()
    envelope = _parse_envelope(
        _run_cli(config_path, _guard_dir(tmp_path), _request(ref), caller)
    )
    _assert_envelope_shape(envelope, ref)
    assert envelope["status"] == "complete"
    assert envelope["parser"]["name"] == "cwp_document_normalization"
    assert envelope["parser"]["version"]
    assert envelope["units"], "the docx produced text units"
    kinds = {unit["kind"] for unit in envelope["units"]}
    assert "docx_heading" in kinds or "docx_paragraph" in kinds
    for unit in envelope["units"]:
        assert unit["unit_id"].startswith("urn:company-wiki:narrative-unit:sha256:")
        assert unit["locator"]
    texts = "\n".join(unit["content"] for unit in envelope["units"])
    assert PARAGRAPH_ONE in texts
    assert PARAGRAPH_TWO in texts


def test_xlsx_returns_structured_sheet_units(tmp_path: Path):
    refs = _fixture(tmp_path)
    config_path = Path(refs["2025.xlsx"]["tmp_project"]) / "config/source_catalog.yaml"
    ref = refs["2025.xlsx"]["ref"]
    caller = tmp_path / "caller"
    caller.mkdir()
    envelope = _parse_envelope(
        _run_cli(config_path, _guard_dir(tmp_path), _request(ref), caller)
    )
    _assert_envelope_shape(envelope, ref)
    assert envelope["status"] == "complete"
    assert envelope["parser"]["name"] == "openpyxl"
    sheets = [unit for unit in envelope["units"] if unit["kind"] == "sheet"]
    assert len(sheets) == 1
    content = sheets[0]["content"]
    assert content["sheet"] == "Income"
    assert content["rows"] == [["item", "value"], ["revenue", "123"], ["cost", None]]


def test_pdf_returns_page_ordered_units(tmp_path: Path):
    refs = _fixture(tmp_path)
    config_path = Path(refs["2025.pdf"]["tmp_project"]) / "config/source_catalog.yaml"
    ref = refs["2025.pdf"]["ref"]
    caller = tmp_path / "caller"
    caller.mkdir()
    envelope = _parse_envelope(
        _run_cli(config_path, _guard_dir(tmp_path), _request(ref), caller)
    )
    _assert_envelope_shape(envelope, ref)
    assert envelope["status"] == "complete"
    assert envelope["parser"]["name"] == "pdf_page_aware_core"
    assert envelope["quality"]["page_count"] == 2
    pages = [
        unit["locator"].split("/page:", 1)[1].split("/", 1)[0]
        for unit in envelope["units"]
        if "/page:" in unit["locator"]
    ]
    assert pages == sorted(pages), "units follow the original page order"
    texts = "\n".join(
        unit["content"] for unit in envelope["units"] if unit["kind"] == "text"
    )
    assert PDF_TEXT_ONE in texts
    assert PDF_TEXT_TWO in texts


def test_encoding_repaired_text_is_an_honest_partial(tmp_path: Path):
    refs = _fixture(tmp_path)
    config_path = (
        Path(refs["partial-2024.txt"]["tmp_project"]) / "config/source_catalog.yaml"
    )
    ref = refs["partial-2024.txt"]["ref"]
    caller = tmp_path / "caller"
    caller.mkdir()
    envelope = _parse_envelope(
        _run_cli(config_path, _guard_dir(tmp_path), _request(ref), caller)
    )
    _assert_envelope_shape(envelope, ref)
    assert envelope["status"] == "partial"
    assert "encoding_repaired" in envelope["quality"]["quality_flags"]


def test_unparseable_format_is_an_honest_unsupported(tmp_path: Path):
    refs = _fixture(tmp_path)
    config_path = (
        Path(refs["empty-2023.xlsx"]["tmp_project"]) / "config/source_catalog.yaml"
    )
    ref = refs["empty-2023.xlsx"]["ref"]
    caller = tmp_path / "caller"
    caller.mkdir()
    envelope = _parse_envelope(
        _run_cli(config_path, _guard_dir(tmp_path), _request(ref), caller)
    )
    _assert_envelope_shape(envelope, ref)
    assert envelope["status"] == "unsupported"
    assert envelope["units"] == []
    assert envelope["quality"]["reason"], "the unsupported reason is carried"


def test_identity_mismatch_is_a_named_refusal(tmp_path: Path):
    refs = _fixture(tmp_path)
    config_path = Path(refs["2025.txt"]["tmp_project"]) / "config/source_catalog.yaml"
    ref = dict(refs["2025.txt"]["ref"])
    digest = hashlib.sha256(b"not the registered bytes").hexdigest()
    ref["content_sha256"] = digest
    ref["source_id"] = "urn:company-wiki:source:sha256:" + digest
    caller = tmp_path / "caller"
    caller.mkdir()
    completed = _run_cli(
        Path(config_path), _guard_dir(tmp_path), _request(ref), caller,
    )
    assert completed.returncode == 2
    lines = completed.stderr.decode("utf-8").strip().splitlines()
    assert len(lines) == 1
    error = json.loads(lines[0])
    # A self-consistent ref that the catalog never registered is named
    # not_found by the existing read contract; stdout stays empty either way.
    assert error["status"] == "not_found"
    assert error["reason"]
    assert completed.stdout == b""


def test_unknown_request_core_version_is_refused(tmp_path: Path):
    refs = _fixture(tmp_path)
    config_path = Path(refs["2025.txt"]["tmp_project"]) / "config/source_catalog.yaml"
    ref = refs["2025.txt"]["ref"]
    caller = tmp_path / "caller"
    caller.mkdir()
    completed = _run_cli(
        Path(config_path),
        _guard_dir(tmp_path),
        {"schema_version": SCHEMA.rsplit("/", 1)[0] + "/2", "source_ref": ref},
        caller,
    )
    assert completed.returncode == 2
    error = json.loads(completed.stderr.decode("utf-8").strip())
    assert error["status"] == "blocked"
    assert error["reason"] == "unsupported_request_version"


def test_broken_request_shape_is_refused(tmp_path: Path):
    refs = _fixture(tmp_path)
    config_path = Path(refs["2025.txt"]["tmp_project"]) / "config/source_catalog.yaml"
    ref = refs["2025.txt"]["ref"]
    caller = tmp_path / "caller"
    caller.mkdir()
    guard = _guard_dir(tmp_path)
    extra = _request(ref)
    extra["surprise"] = True
    completed = _run_cli(config_path, guard, extra, caller)
    assert completed.returncode == 2
    assert json.loads(completed.stderr.decode("utf-8").strip())["status"] == "blocked"

    bad_options = _request(ref, max_units=0)
    completed = _run_cli(config_path, guard, bad_options, caller)
    assert completed.returncode == 2
    assert json.loads(completed.stderr.decode("utf-8").strip())["status"] == "blocked"


def test_pagination_replays_without_dup_or_gap(tmp_path: Path):
    refs = _fixture(tmp_path)
    config_path = Path(refs["2025.txt"]["tmp_project"]) / "config/source_catalog.yaml"
    ref = refs["2025.txt"]["ref"]
    caller = tmp_path / "caller"
    caller.mkdir()
    guard = _guard_dir(tmp_path)
    full = _parse_envelope(_run_cli(config_path, guard, _request(ref), caller))
    all_ids = [unit["unit_id"] for unit in full["units"]]
    assert len(all_ids) >= 2

    first = _parse_envelope(
        _run_cli(config_path, guard, _request(ref, max_units=1), caller)
    )
    assert [unit["unit_id"] for unit in first["units"]] == all_ids[:1]
    assert first["continuation"] is not None
    assert first["continuation"]["has_more"] is True

    second = _parse_envelope(
        _run_cli(
            config_path,
            guard,
            _request(ref, continuation=first["continuation"]["cursor"]),
            caller,
        )
    )
    merged = [unit["unit_id"] for unit in first["units"]] + [
        unit["unit_id"] for unit in second["units"]
    ]
    assert merged == all_ids, "continuation resumes exactly, no dup or gap"
    assert second["continuation"] is None


def test_tampered_continuation_cursor_is_refused(tmp_path: Path):
    refs = _fixture(tmp_path)
    config_path = Path(refs["2025.txt"]["tmp_project"]) / "config/source_catalog.yaml"
    ref = refs["2025.txt"]["ref"]
    caller = tmp_path / "caller"
    caller.mkdir()
    guard = _guard_dir(tmp_path)
    first = _parse_envelope(
        _run_cli(config_path, guard, _request(ref, max_units=1), caller)
    )
    raw = json.loads(
        base64.urlsafe_b64decode(
            first["continuation"]["cursor"] + "=" * (-len(first["continuation"]["cursor"]) % 4)
        ).decode("utf-8")
    )
    raw["after_index"] = 99
    tampered = base64.urlsafe_b64encode(
        json.dumps(raw, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    completed = _run_cli(
        config_path, guard, _request(ref, continuation=tampered), caller,
    )
    assert completed.returncode == 2
    error = json.loads(completed.stderr.decode("utf-8").strip())
    assert error["status"] == "blocked"
    assert error["reason"] == "invalid_continuation"
