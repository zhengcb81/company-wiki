"""Isolated, real handler/projector fixture for the narrative transport boundary."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
from typing import Iterator

from company_wiki.automation.models import Event, canonical_json
from company_wiki.automation.narrative_contracts import SourceRefValue, SourceRevisionEventPayload
from company_wiki.automation.narrative_projection import NarrativeEffectDispatcher
from company_wiki.source_catalog import SourceCatalog
from company_wiki.source_catalog.narrative_artifact_store import (
    LocalNarrativeObjectStore, NarrativeArtifactStore,
)
from company_wiki.source_catalog.source_reader import SourceVersionReader
from integration.test_narrative_runtime_e2e import _drain, _new_catalog, _pdf_bytes, _runtime
from support.narrative_model_fixture import ReplayNarrativeModel


TXT = (
    b"Full Conference Call Transcript\n"
    b"CEO: We launched a new product and expanded overseas capacity.\n"
    b"Questions & Answers\nAnalyst: Is commercial launch on schedule?\n"
)
EXPECTED_KEYS = (
    "canonical_entity_id", "market", "security_id", "document_kind",
    "fiscal_year", "fiscal_period",
)


@dataclass
class TransportFixture:
    root: Path
    config_path: Path
    raw_path: Path
    raw_bytes: bytes
    catalog: SourceCatalog
    reader: SourceVersionReader
    artifacts: NarrativeArtifactStore
    source_ref: SourceRefValue
    payload: bytes
    version: object
    expected_source: dict

    def read_request(self, narrative_ref: object, *, as_of_date: str = "2026-09-01") -> dict:
        return {
            "schema_version": "narrative-read-request/1",
            "narrative_ref": narrative_ref.to_dict(),
            "as_of_date": as_of_date,
            "expected_source": dict(self.expected_source),
        }


@contextmanager
def published_fixture(
    tmp_path: Path, *, kind: str = "txt", published: bool = True,
    source_spec: dict[str, object] | None = None,
) -> Iterator[TransportFixture]:
    """Create only scratch raw/catalog, publish through the real three-job DAG.

    All files, including SQLite side files and CLI-created files, are removed on
    exit. PDF is deliberately labelled synthetic; it is not a filing oracle.
    """
    baseline = tuple(sorted(p.name for p in tmp_path.iterdir()))
    root = tmp_path / "nt"
    assert not root.exists()
    root.mkdir()
    catalog = None
    try:
        transcript = kind in {"txt", "json"}
        if kind == "json":
            data = json.dumps([{
                "symbol": "ACME", "year": 2026, "quarter": 2,
                "date": "2026-08-01 12:00:00",
                "content": TXT.decode("utf-8"),
            }], ensure_ascii=False).encode("utf-8")
        elif kind in {"pdf", "skip"}:
            data = _pdf_bytes(
                "This policy describes meeting administration procedures."
                if kind == "skip" else
                "Company launched a new product and expanded overseas capacity for customers."
            )
        else:
            data = TXT
        suffix = "json" if kind == "json" else "txt" if transcript else "pdf"
        source_kind = "investor_call_transcript" if transcript else (
            "ir_policy" if kind == "skip" else "annual_report"
        )
        title = "投资者关系管理办法（2025年8月）.pdf" if kind == "skip" else "ACME business update"
        spec = {
            "name": f"source.{suffix}", "data": data, "title": title,
            "document_kind": source_kind,
            "sidecar_overrides": {"fiscal_period": "Q2" if transcript else "FY"},
        }
        if source_spec is not None:
            spec.update(source_spec)
            data = spec["data"]
            assert isinstance(data, bytes)
            if "language" in spec:
                spec["sidecar_overrides"] = {
                    **dict(spec.get("sidecar_overrides") or {}), "language": spec["language"],
                }
            transcript = spec["document_kind"] == "investor_call_transcript"
        catalog, reader, indexed = _new_catalog(root, [spec])
        _, source = next(iter(indexed.values()))
        source_ref = SourceRefValue.from_dict({
            "schema_version": source.schema_version,
            "document_id": source.document_id, "source_id": source.source_id,
            "content_sha256": source.content_sha256, "byte_size": source.byte_size,
            "mime_type": source.mime_type,
        })
        metadata = reader.describe_version(source)
        value = {
            "schema_version": "source-revision-event/2.0",
            "source_ref": source_ref.to_dict(),
            "expected_read_policy_sha256": reader.read_policy_sha256(),
            "source_metadata": {
                "source_class": "transcript" if transcript else "filing",
                "title": metadata["title"], "document_kind": metadata["document_kind"],
                "language": metadata["language"],
            },
        }
        parsed = SourceRevisionEventPayload.from_dict(value)
        event = Event(
            event_id="transport-event", event_type="source.revision_registered",
            subject_type="source_revision", subject_id=source.document_id,
            input_hash=parsed.input_hash, payload_json=canonical_json(value),
            policy_version="narrative-v1", occurred_at="2026-09-28T22:00:00Z",
            observed_at="2026-09-28T22:00:00Z",
        )
        automation, scheduler, worker = _runtime(root, reader, ReplayNarrativeModel())
        automation.put_event(event)
        scheduler.materialize_event(event)
        assert _drain(worker, scheduler) == 3, [
            (job.job_type, job.last_error_code, job.last_error_detail)
            for job in automation.list_jobs()
        ]
        artifacts = NarrativeArtifactStore(
            catalog.store, LocalNarrativeObjectStore(catalog.config.catalog_dir),
        )
        dispatcher = NarrativeEffectDispatcher(automation, artifacts)
        receipt = dispatcher.dispatch_next(
            worker_id="transport-projector", now="2026-09-28T22:02:00Z",
            lease_until="2026-09-28T22:03:00Z",
            expected_generation=automation.read_runtime_gate().control_generation,
        )
        assert receipt.artifact_version_id is not None, receipt
        version, payload = artifacts.read_visible(
            document_id=source.document_id, source_id=source.source_id,
            source_sha256=source.content_sha256,
        )
        if not published:
            with catalog.store.transaction() as connection:
                connection.execute(
                    "UPDATE narrative_artifact_versions SET status='prepared' WHERE artifact_version_id=?",
                    (version.artifact_version_id,),
                )
        raw_path = next((root / "companies").rglob(str(spec["name"])))
        config_dir = root / "config"
        config_dir.mkdir()
        config_path = config_dir / "source_catalog.yaml"
        config_path.write_text(json.dumps({
            "schema_version": "1.0", "catalog_dir": str(catalog.config.catalog_dir),
            "roots": [{
                "root_id": "company_raw", "path": str(root / "companies"),
                "kind": "company_raw", "priority": 10, "adapter_id": "company_raw_v1",
                "read_only": True, "reusable_for_filing": True,
            }], "reusable_root_kinds": ["company_raw"],
        }), encoding="utf-8")
        fixture = TransportFixture(
            root, config_path, raw_path, data, catalog, reader, artifacts,
            source_ref, payload, version,
            {key: metadata[key] for key in EXPECTED_KEYS},
        )
        yield fixture
        assert hashlib.sha256(raw_path.read_bytes()).hexdigest() == source.content_sha256
    finally:
        if catalog is not None:
            catalog.close()
        assert root.resolve().parent == tmp_path.resolve()
        shutil.rmtree(root)
        assert tuple(sorted(p.name for p in tmp_path.iterdir())) == baseline
