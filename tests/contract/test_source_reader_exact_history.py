"""G-CWP-EXACT-01: exact reads of non-primary/history versions of ONE document.

The public browser (G-CWP-01) lists every frozen byte version of one logical
document — same ``document_id`` with several ``source_id``/hash pairs — and
gives each its own opaque ``document_version_id`` that reopens to a complete
SourceRef v2.  The exact reader contract claims to reopen exactly that
SourceRef.  These tests prove, through public entry points only, whether the
``SourceVersionReader``/``source_reader_cli`` actually honor a NON-primary
(history) version of the same document, or silently select the current
primary row instead.

Owner card requirements proven here:

- RED probe: browser lists two versions of one document → exact reopen →
  actual CLI reads bytes (stdout hash + structured stderr receipt) for the
  non-primary version.  Expected: verified bytes of THAT version.  Before the
  fix the pre-``open_described_version`` lookup selects the primary row and
  refuses with ``document_source_mismatch`` — a wrong primary selection, not
  a legitimate policy/as-of refusal.
- Policy gates stay closed: an inactive/retired history version, an
  unconfigured root and a root-admission rejection must keep refusing with
  their own named reasons even after the lookup is pair-precise.
- Cross-document confusion must stay impossible: the same source_id/hash
  pair registered under a DIFFERENT document never satisfies this document's
  request; byte_size/mime_type always come from the requested version row.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog  # noqa: E402
from company_wiki.source_catalog.public_document_browser import (  # noqa: E402
    BROWSE_REQUEST_SCHEMA,
    REOPEN_REQUEST_SCHEMA,
    PublicDocumentBrowser,
)
from company_wiki.source_catalog.source_reader import (  # noqa: E402
    SourceRef,
    SourceReadError,
    SourceVersionReader,
)


ENT = "ent-acme"

PRIMARY = b"%PDF-1.4 acme annual report 2025 primary original"
AMENDED = b"%PDF-1.4 acme annual report 2025 amended history v2"

PRIMARY_SHA = hashlib.sha256(PRIMARY).hexdigest()
AMENDED_SHA = hashlib.sha256(AMENDED).hexdigest()

OTHER_DOC = b"%PDF-1.4 a different document sharing nothing"


def _sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _write_tree(tmp_path: Path) -> None:
    """dayu portfolio group: ONE logical filing, TWO byte versions."""
    filing_dir = tmp_path / "portfolio" / "ACME" / "filings" / "fil_x"
    filing_dir.mkdir(parents=True)
    (filing_dir / "fil_x.pdf").write_bytes(PRIMARY)
    (filing_dir / "fil_x_amended.pdf").write_bytes(AMENDED)
    (filing_dir / "meta.json").write_text(json.dumps({
        "document_id": "fil_x", "ticker": "ACME", "form_type": "FY",
        "canonical_entity_id": ENT, "display_name": "Acme", "market": "CN",
        "document_kind": "annual_report",
        "fiscal_year": 2024, "filing_date": "2025-03-30",
        "source_provider": "dayu", "source_id": "fil_x",
        "source_language": "en",
        "ingest_complete": True, "primary_document": "fil_x.pdf",
    }, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "portfolio" / "ACME" / "meta.json").write_text(
        json.dumps({"ticker": "ACME", "market": "CN"}), encoding="utf-8",
    )


def _roots(tmp_path: Path) -> tuple[RootSpec, ...]:
    return (
        RootSpec("dayu_portfolio", tmp_path / "portfolio", "dayu_portfolio",
                 priority=20, adapter_id="dayu_filing_v1", read_only=True,
                 reusable_for_filing=True),
    )


def _config(tmp_path: Path, roots: tuple[RootSpec, ...]) -> CatalogConfig:
    return CatalogConfig(
        project_root=tmp_path,
        catalog_dir=tmp_path / ".source_catalog",
        roots=roots,
        reusable_root_kinds=("dayu_portfolio",),
    )


def _build(tmp_path: Path) -> SourceCatalog:
    _write_tree(tmp_path)
    catalog = SourceCatalog(_config(tmp_path, _roots(tmp_path)))
    catalog.scan()
    return catalog


def _browse(browser: PublicDocumentBrowser, **overrides) -> dict:
    request = {
        "schema_version": BROWSE_REQUEST_SCHEMA,
        "canonical_entity_id": ENT,
        "market": None,
        "document_kinds": None,
        "fiscal_years": None,
        "language": None,
        "source_statuses": None,
        "limit": None,
        "cursor": None,
        "snapshot_id": None,
    }
    request.update(overrides)
    return browser.browse(request)


def _history_items(tmp_path: Path):
    """Public flow: browse → both versions of one document → reopen each.

    Returns (catalog, browser, primary_item, history_item) where the history
    item has is_current_version False.  Fails the fixture (not the probe) if
    the cabinet does not expose the two-version document at all.
    """
    catalog = _build(tmp_path)
    browser = PublicDocumentBrowser(catalog)
    result = _browse(browser, document_kinds=["annual_report"],
                     fiscal_years=[2024])
    assert result["state"] in {"available", "partial"}, result
    items = result["items"]
    assert len(items) == 2, items
    assert {i["is_current_version"] for i in items} == {True, False}
    primary = next(i for i in items if i["is_current_version"])
    history = next(i for i in items if not i["is_current_version"])
    assert primary["source_ref"]["content_sha256"] == PRIMARY_SHA
    assert history["source_ref"]["content_sha256"] == AMENDED_SHA
    assert primary["source_ref"]["document_id"] == \
        history["source_ref"]["document_id"]
    # exact reopen through the public seam returns each own complete ref
    for item in (primary, history):
        reopened = browser.reopen_document_version({
            "schema_version": REOPEN_REQUEST_SCHEMA,
            "document_version_id": item["document_version_id"],
        })
        assert reopened["state"] == "available", reopened
        assert reopened["document"]["source_ref"] == item["source_ref"]
    return catalog, browser, primary, history


def _run_cli(config_path: Path, document_id: str, source_id: str,
             sha256: str, tmp_path: Path,
             extra: list[str] | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
    return subprocess.run(
        [sys.executable, "-B",
         "-m", "company_wiki.source_catalog.source_reader_cli",
         "--config", str(config_path),
         "--document-id", document_id,
         "--source-id", source_id,
         "--content-sha256", sha256,
         *(extra or [])],
        capture_output=True, cwd=str(tmp_path), env=env,
    )


def _run_stream_cli(config_path: Path, document_id: str, source_id: str,
                    sha256: str, tmp_path: Path,
                    extra: list[str] | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
    env["PYTHONUTF8"] = "1"
    return subprocess.run(
        [sys.executable, "-B", "-m", "company_wiki.source_catalog.source_stream_cli",
         "--config", str(config_path),
         "--document-id", document_id,
         "--source-id", source_id,
         "--content-sha256", sha256,
         *(extra or [])],
        capture_output=True, cwd=str(tmp_path), env=env, timeout=60,
    )


# --- RED probe: the full public chain must read the requested version --------


def test_cli_reads_nonprimary_history_version_of_same_document(tmp_path):
    catalog, browser, primary, history = _history_items(tmp_path)
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
    catalog.close()

    ref = history["source_ref"]
    # Existing consumers retain primary-only behavior unless they opt into an
    # exact historical pair read through the additive CLI flag.
    default_read = _run_cli(config_path, ref["document_id"], ref["source_id"],
                            ref["content_sha256"], tmp_path)
    assert default_read.returncode == 2
    assert default_read.stdout == b""
    default_receipt = json.loads(default_read.stderr.decode("utf-8").splitlines()[-1])
    assert (default_receipt["status"], default_receipt["reason"]) == (
        "not_found", "document_source_mismatch"
    )

    proc = _run_cli(config_path, ref["document_id"], ref["source_id"],
                    ref["content_sha256"], tmp_path, extra=["--exact-pair"])
    # stdout is the requested version's bytes, nothing else
    assert proc.stdout == AMENDED, (
        "CLI stdout is not the requested history version bytes; "
        f"stderr={proc.stderr!r}"
    )
    assert hashlib.sha256(proc.stdout).hexdigest() == AMENDED_SHA
    receipt = json.loads(proc.stderr.decode("utf-8").splitlines()[-1])
    assert receipt["status"] == "ok", receipt
    assert receipt["schema_version"] == "2.1"
    assert receipt["document_id"] == ref["document_id"]
    assert receipt["source_id"] == ref["source_id"]
    assert receipt["content_sha256"] == AMENDED_SHA
    assert receipt["byte_size"] == len(AMENDED)
    # the manifest describes the REQUESTED version, not the primary
    manifest = receipt["manifest"]
    assert manifest["document_id"] == ref["document_id"]
    assert manifest["source_id"] == ref["source_id"]
    assert manifest["content_sha256"] == AMENDED_SHA
    assert manifest["byte_size"] == len(AMENDED)

    default_stream = _run_stream_cli(
        config_path, ref["document_id"], ref["source_id"], ref["content_sha256"],
        tmp_path,
    )
    assert default_stream.returncode == 2
    assert default_stream.stdout == b""
    stream_refusal = json.loads(
        default_stream.stderr.decode("utf-8").splitlines()[-1]
    )
    assert (stream_refusal["status"], stream_refusal["reason"]) == (
        "not_found", "document_source_mismatch"
    )

    exact_stream = _run_stream_cli(
        config_path, ref["document_id"], ref["source_id"], ref["content_sha256"],
        tmp_path, extra=["--exact-pair"],
    )
    assert exact_stream.returncode == 0, exact_stream.stderr.decode("utf-8")
    assert exact_stream.stdout == AMENDED
    streamed_receipts = [
        json.loads(line) for line in exact_stream.stderr.decode("utf-8").splitlines()
    ]
    assert [item["status"] for item in streamed_receipts] == ["locked", "ok"]
    assert streamed_receipts[-1]["content_sha256"] == AMENDED_SHA

    # primary read still works and returns primary bytes
    proc = _run_cli(config_path, primary["source_ref"]["document_id"],
                    primary["source_ref"]["source_id"],
                    primary["source_ref"]["content_sha256"], tmp_path)
    assert proc.stdout == PRIMARY, proc.stderr
    receipt = json.loads(proc.stderr.decode("utf-8").splitlines()[-1])
    assert receipt["status"] == "ok" and receipt["byte_size"] == len(PRIMARY)


def test_reader_module_reads_nonprimary_version_and_reports_exact_facts(tmp_path):
    catalog, browser, primary, history = _history_items(tmp_path)
    reader = SourceVersionReader(catalog)
    ref = SourceRef(**history["source_ref"])
    # The compatibility query remains primary-only. Exact historical reads
    # use a separately named public operation so callers cannot widen the
    # old query contract by accident.
    with pytest.raises(SourceReadError) as error:
        reader.query_ref(ref.document_id, ref.source_id, ref.content_sha256)
    assert (error.value.status, error.value.reason) == (
        "not_found", "document_source_mismatch"
    )
    resolved = reader.query_exact_pair_ref(
        ref.document_id, ref.source_id, ref.content_sha256
    )
    assert resolved == ref
    opened, manifest = reader.open_described_version(ref, purpose="preview")
    assert opened.data == AMENDED
    assert opened.content_sha256 == AMENDED_SHA
    assert opened.byte_size == len(AMENDED)
    assert manifest["source_id"] == ref.source_id
    assert manifest["content_sha256"] == AMENDED_SHA
    # streaming verify gives the same identity without bytes
    receipt = reader.verify_version(ref, purpose="source_export")
    assert receipt.content_sha256 == AMENDED_SHA
    assert receipt.byte_size == len(AMENDED)
    # The primary pair remains available through the established query.
    primary_ref = SourceRef(**primary["source_ref"])
    assert reader.query_ref(primary_ref.document_id, primary_ref.source_id,
                            primary_ref.content_sha256) == primary_ref
    catalog.close()


def test_describe_version_of_history_version_reflects_requested_bytes(tmp_path):
    catalog, browser, primary, history = _history_items(tmp_path)
    reader = SourceVersionReader(catalog)
    history_ref = SourceRef(**history["source_ref"])
    manifest = reader.describe_version(history_ref)
    assert manifest["document_id"] == history_ref.document_id
    assert manifest["source_id"] == history_ref.source_id
    assert manifest["content_sha256"] == AMENDED_SHA
    assert manifest["byte_size"] == len(AMENDED)
    assert manifest["mime_type"] == history_ref.mime_type
    catalog.close()


# --- gates that must STAY closed after pair-precise lookup --------------------


def test_inactive_history_version_stays_blocked(tmp_path):
    catalog, browser, primary, history = _history_items(tmp_path)
    reader = SourceVersionReader(catalog)
    history_ref = SourceRef(**history["source_ref"])
    # retire the DOCUMENT row (the shared status carrier) via a direct,
    # test-only SQL write in the isolated tmp catalog
    import sqlite3
    connection = sqlite3.connect(catalog.config.database_path)
    connection.execute(
        "UPDATE documents SET source_status='retired' WHERE document_id=?",
        (history_ref.document_id,),
    )
    connection.commit()
    connection.close()
    with pytest.raises(SourceReadError) as error:
        reader.open_version(history_ref, purpose="preview")
    assert error.value.status == "blocked"
    assert error.value.reason == "source_not_active"
    catalog.close()


def test_unconfigured_root_stays_unavailable(tmp_path):
    catalog, browser, primary, history = _history_items(tmp_path)
    history_ref = SourceRef(**history["source_ref"])
    # a config without the version's root_id at all: no indexed location can
    # map into the current roots (the honest pre-byte refusal)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    reduced = SourceCatalog(CatalogConfig(
        project_root=tmp_path,
        catalog_dir=tmp_path / ".source_catalog",
        roots=(RootSpec("other_root", elsewhere, "dayu_portfolio",
                        priority=20, adapter_id="dayu_filing_v1",
                        read_only=True, reusable_for_filing=True),),
        reusable_root_kinds=("dayu_portfolio",),
    ))
    with pytest.raises(SourceReadError) as error:
        SourceVersionReader(reduced).open_version(history_ref,
                                                  purpose="preview")
    assert error.value.status == "unavailable"
    assert error.value.reason == "no_indexed_location"
    catalog.close()


def test_root_admission_denial_stays_blocked(tmp_path):
    catalog, browser, primary, history = _history_items(tmp_path)
    history_ref = SourceRef(**history["source_ref"])
    from dataclasses import replace
    tiny = SourceCatalog(CatalogConfig(
        project_root=tmp_path,
        catalog_dir=tmp_path / ".source_catalog",
        roots=(replace(_roots(tmp_path)[0], max_file_size=len(AMENDED) - 1),),
        reusable_root_kinds=("dayu_portfolio",),
    ))
    with pytest.raises(SourceReadError) as error:
        SourceVersionReader(tiny).open_version(history_ref, purpose="preview")
    assert error.value.status == "blocked"
    assert error.value.reason == "root_admission_denied"
    catalog.close()


def test_hash_mismatch_of_history_version_stays_unavailable(tmp_path):
    catalog, browser, primary, history = _history_items(tmp_path)
    reader = SourceVersionReader(catalog)
    history_ref = SourceRef(**history["source_ref"])
    corrupted = SourceRef(
        document_id=history_ref.document_id,
        source_id=history_ref.source_id,
        content_sha256="f" * 64,
        byte_size=history_ref.byte_size,
        mime_type=history_ref.mime_type,
    )
    with pytest.raises(SourceReadError) as error:
        reader.query_exact_pair_ref(corrupted.document_id, corrupted.source_id,
                                    corrupted.content_sha256)
    assert error.value.status == "unavailable"
    assert error.value.reason == "expected_version_mismatch"
    # a source_id this document never registered must not resolve either
    with pytest.raises(SourceReadError) as error:
        reader.query_exact_pair_ref(
            history_ref.document_id,
            "urn:company-wiki:source:sha256:" + "0" * 64,
            "0" * 64,
        )
    assert error.value.status == "not_found"
    assert error.value.reason == "document_source_mismatch"
    catalog.close()


def test_cross_document_same_pair_confusion_impossible(tmp_path):
    """A different logical document must never satisfy this document's ref."""
    catalog, browser, primary, history = _history_items(tmp_path)
    reader = SourceVersionReader(catalog)
    # a second, unrelated document in a separate group
    other_dir = tmp_path / "portfolio" / "ACME" / "filings" / "fil_other"
    other_dir.mkdir(parents=True)
    (other_dir / "fil_other.pdf").write_bytes(OTHER_DOC)
    (other_dir / "meta.json").write_text(json.dumps({
        "document_id": "fil_other", "ticker": "ACME", "form_type": "FY",
        "canonical_entity_id": ENT, "display_name": "Acme", "market": "CN",
        "document_kind": "annual_report",
        "fiscal_year": 2023, "filing_date": "2024-03-30",
        "source_provider": "dayu", "source_id": "fil_other",
        "source_language": "en",
        "ingest_complete": True, "primary_document": "fil_other.pdf",
    }, ensure_ascii=False), encoding="utf-8")
    catalog.scan()
    ref = SourceRef(**history["source_ref"])
    # the history ref must still resolve, and bytes must remain AMENDED
    opened, _ = reader.open_described_version(ref, purpose="preview")
    assert opened.data == AMENDED
    # the other document's own primary still opens to ITS bytes
    other_sha = _sha(OTHER_DOC)
    other_doc_id = "urn:company-wiki:document:sha256:" + other_sha
    other_source_id = "urn:company-wiki:source:sha256:" + other_sha
    other_ref = reader.query_ref(other_doc_id, other_source_id, other_sha)
    opened, _ = reader.open_described_version(other_ref, purpose="preview")
    assert opened.data == OTHER_DOC
    catalog.close()


def test_cli_rejects_bad_arguments_and_reports_pathless_errors(tmp_path):
    catalog, browser, primary, history = _history_items(tmp_path)
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
    catalog.close()
    ref = history["source_ref"]
    # duplicate/illegal argument: argparse-level failure, no traceback noise
    proc = subprocess.run(
        [sys.executable, "-B",
         "-m", "company_wiki.source_catalog.source_reader_cli",
         "--config", str(config_path),
         "--document-id", ref["document_id"],
         "--source-id", ref["source_id"],
         "--content-sha256", "NOTASHA"],
        capture_output=True, cwd=str(tmp_path),
        env={**os.environ,
             "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")},
    )
    assert proc.returncode == 2, proc.stderr
    receipt = json.loads(proc.stderr.decode("utf-8").splitlines()[-1])
    assert receipt["status"] in {"blocked", "unavailable"}, receipt
    # error envelope stays pathless
    stderr_text = proc.stderr.decode("utf-8")
    assert str(tmp_path) not in stderr_text
    assert "portfolio" not in stderr_text
