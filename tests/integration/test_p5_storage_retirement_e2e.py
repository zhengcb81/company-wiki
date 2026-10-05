"""P5-STORAGE integration E2E on real bytes (opt-in via -m slow).

Copies (read-only) the AMEC FY2025 annual report from the MAIN checkout and a
local transcript TXT sample into an isolated short root, builds a REAL-schema
mixed catalog with old derived artifacts + old full-volume spans AND a new
final narrative bundle, then runs inventory / retire-derived / prune-spans /
vacuum and proves the public SourceRef raw read and the narrative transport
read/replay still work before and after.  Network/model/download calls: 0.
"""

from __future__ import annotations

from contextlib import ExitStack, closing
import hashlib
import shutil
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from company_wiki.source_catalog.normalizer import normalize_catalog
from company_wiki.source_catalog.section_extractor import extract_sections_catalog
from company_wiki.source_catalog.store import CatalogStore
from company_wiki.source_catalog.summarizer import summarize_catalog

pytestmark = pytest.mark.slow

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
TOOLS_DIR = REPO_ROOT / "tools"
ANNUAL_SHA = "d64c410832f22f5127277bad6dc357c664aede523561af99150c494857fd3aa5"
PDF_PARSER = "pdf_page_aware_core"
TRANSCRIPT_SHA = "4ac3b4f0fa1be928b56b4ef9775cac694a1712d46785bb1fa28d2a6a68d7852a"


def _main_repo_annual_report() -> Path:
    """Resolve the real annual report from the MAIN checkout (host-neutral).

    The main worktree is derived from this lane worktree's git common dir, so
    no host absolute path is asserted here; the caller skips when absent.
    """
    import subprocess

    common_dir = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True, cwd=str(REPO_ROOT), timeout=60,
    )
    main_root = Path(common_dir.stdout.decode("utf-8").strip()).parent
    return (
        main_root
        / "companies"
        / "中微公司"
        / "raw"
        / "financial_reports"
        / ("中微公司：2025年年度报告.pdf")
    )



def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture(scope="module")
def mixed_fixture(tmp_path_factory) -> dict:
    pytest.importorskip("fitz")
    annual_path = _main_repo_annual_report()
    transcript_path = (annual_path.parents[4].parent / "earnings-transcripts" /
                       "earnings-transcripts/transcripts/MSFT/MSFT_Q4_2026_earnings_call.txt")
    if not annual_path.is_file() or not transcript_path.is_file():
        pytest.skip("real annual report and transcript samples unavailable on this host")
    assert _sha(annual_path.read_bytes()) == ANNUAL_SHA
    assert _sha(transcript_path.read_bytes()) == TRANSCRIPT_SHA
    tmp = tmp_path_factory.mktemp("p5-e2e")
    try:
        with ExitStack() as resources:
            yield _build_mixed_fixture(tmp, annual_path, transcript_path, resources)
    finally:
        shutil.rmtree(tmp)
        assert not tmp.exists()
        assert _sha(annual_path.read_bytes()) == ANNUAL_SHA
        assert _sha(transcript_path.read_bytes()) == TRANSCRIPT_SHA


def _build_mixed_fixture(tmp, annual_path, transcript_path, resources):
    fixture: dict = {"root": tmp}

    # 1) offline narrative fixture (Replay model) -> a REAL new final bundle
    from support.narrative_transport_fixture import published_fixture
    TXT = transcript_path.read_bytes()
    from integration.test_narrative_runtime_e2e import _new_catalog

    transcript_spec = {
        "name": transcript_path.name, "data": TXT, "title": "Microsoft Q4 2026 earnings call",
        "document_kind": "investor_call_transcript", "language": "en",
        "sidecar_overrides": {"canonical_entity_id": "MICROSOFT", "market": "US",
                              "security_id": "MSFT", "fiscal_year": 2026, "fiscal_period": "Q4"},
    }
    with published_fixture(tmp, kind="txt", source_spec=transcript_spec) as published:
        fixture["source_ref"] = published.source_ref.to_dict()
        fixture["expected_source"] = dict(published.expected_source)
        fixture["bundle"] = json.loads(published.payload.decode("utf-8"))
        fixture["txt_bytes"] = TXT

    # 2) mixed catalog: real annual report PDF + the same TXT bytes
    mx = tmp / "mx"
    annual_spec = {
        "name": "中微公司：2025年年度报告.pdf",
        "data": annual_path.read_bytes(),
        "title": "中微公司：2025年年度报告",
        "document_kind": "annual_report",
        "sidecar_overrides": {
            "fiscal_year": 2025,
            "fiscal_period": "FY",
            "market": "CN",
            "security_id": "688012",
            "canonical_entity_id": "AMEC",
            "display_name": "中微公司",
            "language": "zh",
            "filing_date": "2026-04-12",
            "period_end": "2025-12-31",
        },
    }
    txt_spec = transcript_spec
    catalog, reader, _indexed = _new_catalog(mx, [annual_spec, txt_spec])
    resources.callback(catalog.close)
    config = catalog.config
    fixture["config"] = config
    fixture["reader"] = reader

    store = CatalogStore(config.database_path)
    fixture["store"] = store
    with store.transaction() as connection:
        annual = connection.execute(
            "SELECT s.source_id, d.document_id, s.content_sha256, s.byte_size,"
            " s.mime_type FROM documents d JOIN sources s"
            " ON s.source_id=d.primary_source_id"
            " WHERE d.document_kind='annual_report'").fetchone()
    fixture["annual_ref"] = {
        "source_id": annual[0], "document_id": annual[1],
        "content_sha256": annual[2], "byte_size": annual[3], "mime_type": annual[4],
    }
    normalize_catalog(config, store, force=True, parser_timeout_seconds=3600)
    summarize_catalog(config, store, force=True)
    extract_sections_catalog(config, store, force=True)
    with store.transaction() as connection:
        fixture["pdf_spans"] = connection.execute(
            "SELECT COUNT(*) FROM evidence_spans WHERE parser_name=?", (PDF_PARSER,)
        ).fetchone()[0]
        fixture["txt_spans"] = connection.execute(
            "SELECT COUNT(*) FROM evidence_spans WHERE parser_name='plain_text'"
        ).fetchone()[0]
        fixture["keep_pair"] = tuple(
            connection.execute(
                "SELECT source_id, locator FROM evidence_spans"
                " WHERE parser_name='plain_text' LIMIT 1"
            ).fetchone()
        )

    # 3) graft the new final onto the mixed TXT document via the published
    #    NarrativeArtifactStore (prepare + activate), pinned to the mixed
    #    catalog's read policy
    from company_wiki.automation.models import canonical_json
    from company_wiki.automation.narrative_contracts import NarrativeBundle

    rebuilt = dict(fixture["bundle"])
    rebuilt["expected_read_policy_sha256"] = reader.read_policy_sha256()
    payload = canonical_json(NarrativeBundle.from_dict(rebuilt).to_dict()).encode(
        "utf-8"
    )
    txt_sha = _sha(TXT)
    import uuid

    draft = {
        "effect_id": "p5-e2e-" + uuid.uuid4().hex[:12],
        "work_key": hashlib.sha256(payload).hexdigest(),
        "source_sha256": txt_sha,
        "policy_sha256": "b" * 64,
        "metadata_json": '{"environment":"p5-integration-fixture"}',
        "created_at": "2026-10-05T00:00:00Z",
    }
    from company_wiki.source_catalog.narrative_artifact_store import (
        LocalNarrativeObjectStore,
        NarrativeArtifactDraft,
        NarrativeArtifactStore,
    )

    artifacts = NarrativeArtifactStore(
        store, LocalNarrativeObjectStore(config.catalog_dir)
    )
    with store.transaction() as connection:
        doc_row = connection.execute(
            "SELECT d.document_id, d.primary_source_id FROM documents d"
            " JOIN sources s ON s.source_id=d.primary_source_id"
            " WHERE s.content_sha256=?",
            (txt_sha,),
        ).fetchone()
    document_id, mixed_source_id = doc_row[0], doc_row[1]
    prepared = artifacts.prepare(
        NarrativeArtifactDraft(
            effect_id=draft["effect_id"],
            work_key=draft["work_key"],
            document_id=document_id,
            source_id=mixed_source_id,
            source_sha256=txt_sha,
            producer_name="company_wiki.narrative_bundle",
            producer_version="2.0",
            policy_sha256=draft["policy_sha256"],
            selection_status="selected",
            quality_status="verified",
            metadata_json=draft["metadata_json"],
            created_at=draft["created_at"],
        ),
        payload,
    )
    artifacts.activate(
        prepared.effect_id,
        verified_after_hash=_sha(payload),
        activated_at="2026-10-05T00:00:00Z",
    )
    fixture["artifact_version_id"] = prepared.artifact_version_id
    fixture["payload_sha256"] = _sha(payload)
    fixture["config_path"] = _write_config(fixture)
    return fixture


def _write_config(fixture) -> Path:
    from company_wiki.automation.models import canonical_json

    config = fixture["config"]
    path = Path(fixture["root"]) / "mx" / "catalog.json"
    path.write_text(
        canonical_json(
            {
                "schema_version": "1.0",
                "catalog_dir": str(config.catalog_dir),
                "roots": [
                    {
                        "root_id": r.root_id,
                        "path": str(r.path),
                        "kind": r.kind,
                        "priority": r.priority,
                        "adapter_id": r.adapter_id,
                    }
                    for r in config.roots
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _env() -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC_DIR)
    env["COMPANY_WIKI_NETWORK"] = "blocked"
    return env


TOOL_PY = str(TOOLS_DIR / "legacy_storage_retirement.py")


def _raw_open(fixture, ref=None) -> tuple[int, dict]:
    ref = fixture["annual_ref"] if ref is None else ref
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "company_wiki.source_catalog.source_reader_cli",
            "--config",
            fixture["config_path"],
            "--document-id",
            ref["document_id"],
            "--source-id",
            ref["source_id"],
            "--content-sha256",
            ref["content_sha256"],
            "--purpose",
            "source_export",
        ],
        capture_output=True,
        env=_env(),
        timeout=300,
    )
    stderr = proc.stderr.decode("utf-8")
    receipt = json.loads(stderr.splitlines()[-1]) if stderr else {}
    if proc.returncode == 0:
        assert _sha(proc.stdout) == ref["content_sha256"]
    return proc.returncode, receipt


def _narrative_reference(fixture) -> tuple[int, dict]:
    request = {
        "schema_version": "narrative-reference-request/1",
        "source_ref": fixture["source_ref"],
    }
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "company_wiki.source_catalog.narrative_transport_cli",
            "--config",
            fixture["config_path"],
            "--operation",
            "reference",
        ],
        input=json.dumps(request).encode("utf-8"),
        capture_output=True,
        env=_env(),
        timeout=300,
    )
    return proc.returncode, proc.stdout


def _narrative_read(fixture) -> tuple[int, bytes]:
    code, reference_bytes = _narrative_reference(fixture)
    assert code == 0
    request = {
        "schema_version": "narrative-read-request/1",
        "narrative_ref": json.loads(reference_bytes.decode("utf-8")),
        "as_of_date": "2026-09-01",
        "expected_source": fixture["expected_source"],
    }
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "company_wiki.source_catalog.narrative_transport_cli",
            "--config",
            fixture["config_path"],
            "--operation",
            "read",
        ],
        input=json.dumps(request).encode("utf-8"),
        capture_output=True,
        env=_env(),
        timeout=300,
    )
    return proc.returncode, proc.stdout


def test_raw_read_replay_and_receipts_across_full_chain(mixed_fixture, record_property) -> None:
    raw_before = _raw_open(mixed_fixture)
    assert raw_before[0] == 0, raw_before[1]
    assert raw_before[1]["content_sha256"] == ANNUAL_SHA
    assert _raw_open(mixed_fixture, mixed_fixture["source_ref"])[0] == 0
    final_before = _narrative_read(mixed_fixture)
    assert final_before[0] == 0
    assert _sha(final_before[1]) == mixed_fixture["payload_sha256"]

    manifest_path = mixed_fixture["root"] / "inventory.manifest.json"
    out = mixed_fixture["root"] / "receipts"
    inventory = subprocess.run(
        [
            sys.executable,
            TOOL_PY,
            "inventory",
            "--config",
            mixed_fixture["config_path"],
            "--output",
            str(manifest_path),
        ],
        capture_output=True,
        env=_env(),
        timeout=900,
    )
    assert inventory.returncode == 0, inventory.stderr.decode("utf-8")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "cwp-storage-manifest/1"

    retire = subprocess.run(
        [
            sys.executable,
            TOOL_PY,
            "retire-derived",
            "--config",
            mixed_fixture["config_path"],
            "--manifest",
            str(manifest_path),
            "--receipt",
            str(out / "retire.json"),
            "--apply",
        ],
        capture_output=True,
        env=_env(),
        timeout=900,
    )
    assert retire.returncode == 0, retire.stderr.decode("utf-8")
    retire_report = json.loads((out / "retire.json").read_text(encoding="utf-8"))
    assert retire_report["status"] == "succeeded"
    assert retire_report["deleted"]

    keep_path = mixed_fixture["root"] / "keep.jsonl"
    keep_ref = mixed_fixture["keep_pair"]
    keep_path.write_text(
        json.dumps({"source_id": keep_ref[0], "locator": keep_ref[1]}) + "\n",
        encoding="utf-8",
    )
    selection_path = mixed_fixture["root"] / "selection.json"
    selection_path.write_text(
        json.dumps(
            {
                "schema_version": "cwp-span-selection/1",
                "parser_name": PDF_PARSER,
                "source_ids": [],
                "document_ids": [],
            }
        ),
        encoding="utf-8",
    )
    prune = subprocess.run(
        [
            sys.executable,
            TOOL_PY,
            "prune-spans",
            "--config",
            mixed_fixture["config_path"],
            "--selection",
            str(selection_path),
            "--keep-refs",
            str(keep_path),
            "--receipt",
            str(out / "prune.json"),
            "--apply",
        ],
        capture_output=True,
        env=_env(),
        timeout=900,
    )
    assert prune.returncode == 0, prune.stderr.decode("utf-8")
    prune_report = json.loads((out / "prune.json").read_text(encoding="utf-8"))
    assert prune_report["deleted"] == mixed_fixture["pdf_spans"]

    vacuum = subprocess.run(
        [
            sys.executable,
            TOOL_PY,
            "vacuum",
            "--config",
            mixed_fixture["config_path"],
            "--receipt",
            str(out / "vacuum.json"),
            "--apply",
        ],
        capture_output=True,
        env=_env(),
        timeout=900,
    )
    assert vacuum.returncode == 0, vacuum.stderr.decode("utf-8")
    vacuum_report = json.loads((out / "vacuum.json").read_text(encoding="utf-8"))
    assert vacuum_report["freelist_after"] == 0
    assert vacuum_report["database_file_bytes_released"] > 0
    assert vacuum_report["source_facts_before"] == vacuum_report["source_facts_after"]
    assert vacuum_report["legacy_record_facts_before"] == vacuum_report["legacy_record_facts_after"]
    assert vacuum_report["protected_objects_before"] == vacuum_report["protected_objects_after"]
    assert retire_report["source_facts_before"] == prune_report["source_facts_after"]
    assert retire_report["protected_objects_before"]["new_final_count"] == 1
    assert retire_report["protected_objects_before"]["object_bytes"] > 0

    raw_after = _raw_open(mixed_fixture)
    assert raw_after[0] == 0, raw_after[1]
    assert _raw_open(mixed_fixture, mixed_fixture["source_ref"])[0] == 0
    assert raw_after[1]["content_sha256"] == ANNUAL_SHA
    final_after = _narrative_read(mixed_fixture)
    assert final_after[0] == 0
    assert _sha(final_after[1]) == mixed_fixture["payload_sha256"]

    with closing(sqlite3.connect(mixed_fixture["config"].database_path)) as conn:
        kept = conn.execute(
            "SELECT COUNT(*) FROM evidence_spans WHERE source_id=? AND locator=?",
            keep_ref,
        ).fetchone()[0]
        txt_left = conn.execute(
            "SELECT COUNT(*) FROM evidence_spans WHERE parser_name='plain_text'"
        ).fetchone()[0]
        pdf_left = conn.execute(
            "SELECT COUNT(*) FROM evidence_spans WHERE parser_name=?", (PDF_PARSER,)
        ).fetchone()[0]
        visible = conn.execute(
            "SELECT COUNT(*) FROM narrative_artifact_versions WHERE status='visible'"
        ).fetchone()[0]
        sources = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        legacy_completed = conn.execute(
            "SELECT COUNT(*) FROM artifacts WHERE status='completed'"
            " AND artifact_role IN ('normalized','summary','sections')"
        ).fetchone()[0]
    assert kept == 1
    assert txt_left == mixed_fixture["txt_spans"]
    assert pdf_left == 0
    assert visible == 1
    assert sources >= 2
    assert legacy_completed == 0

    mixed_fixture["receipts"] = {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in out.glob("*.json")
    }

    metrics = {}
    for operation, receipt in mixed_fixture["receipts"].items():
        deleted = receipt["deleted"]
        metrics[operation] = {
            "status": receipt["status"], "error_code": receipt["error_code"],
            "deleted": len(deleted) if isinstance(deleted, list) else deleted,
            "files_before": receipt["files_bytes_before"], "files_after": receipt["files_bytes_after"],
            "db_before": receipt["database_bytes_before"], "db_after": receipt["database_bytes_after"],
            "freelist_before": receipt["freelist_before"], "freelist_after": receipt["freelist_after"],
            "source_facts_equal": receipt["source_facts_before"] == receipt["source_facts_after"],
            "integrity": receipt["integrity_check"],
            "new_final_count": receipt["protected_objects_after"].get("new_final_count"),
            "object_bytes": receipt["protected_objects_after"].get("object_bytes"),
        }
    record_property("storage_metrics", json.dumps(metrics, sort_keys=True))
    record_property("annual_sha256", ANNUAL_SHA)
    record_property("transcript_sha256", TRANSCRIPT_SHA)
    record_property("final_payload_sha256", mixed_fixture["payload_sha256"])
