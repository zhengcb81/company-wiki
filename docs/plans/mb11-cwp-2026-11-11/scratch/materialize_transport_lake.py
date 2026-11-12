"""Scratch probe: materialize a persistent narrative-transport lake.

Run inside the worktree test environment.  Leaves the lake, its config, the
exact source_ref and the request JSON in the scratch dir for the installed
wheel to consume from an empty cwd without any source PYTHONPATH.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\郑曾波\Projects\mb11-cwp\src")
sys.path.insert(0, r"C:\Users\郑曾波\Projects\mb11-cwp\tests")

from company_wiki.automation.models import Event, canonical_json
from company_wiki.automation.narrative_contracts import SourceRefValue
from company_wiki.automation.narrative_projection import NarrativeEffectDispatcher
from company_wiki.source_catalog.narrative_artifact_store import (
    LocalNarrativeObjectStore, NarrativeArtifactStore,
)
from integration.test_narrative_runtime_e2e import _drain, _new_catalog, _runtime
from support.narrative_model_fixture import ReplayNarrativeModel

OUT = Path(r"C:/Users/Public/mb11-cwp-scratch/lake")
TXT = (
    b"Full Conference Call Transcript\n"
    b"CEO: We launched a new product and expanded overseas capacity.\n"
    b"Questions & Answers\nAnalyst: Is commercial launch on schedule?\n"
)

if OUT.exists():
    import shutil
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
root = OUT / "nt"
root.mkdir()

spec = {
    "name": "source.txt", "data": TXT, "title": "ACME business update",
    "document_kind": "investor_call_transcript",
    "sidecar_overrides": {"fiscal_period": "Q2"},
}
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
    "expected_read_policy_sha256": reader.read_policy_sha256(None),
    "source_metadata": {
        "source_class": "transcript",
        "title": metadata["title"], "document_kind": metadata["document_kind"],
        "language": metadata["language"],
    },
}
from company_wiki.automation.narrative_contracts import SourceRevisionEventPayload

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
assert _drain(worker, scheduler) == 3
artifacts_store = NarrativeArtifactStore(
    catalog.store, LocalNarrativeObjectStore(catalog.config.catalog_dir),
)
dispatcher = NarrativeEffectDispatcher(automation, artifacts_store)
receipt = dispatcher.dispatch_next(
    worker_id="transport-projector", now="2026-09-28T22:02:00Z",
    lease_until="2026-09-28T22:03:00Z",
    expected_generation=automation.read_runtime_gate().control_generation,
)
assert receipt.artifact_version_id is not None, receipt
version, payload = artifacts_store.read_visible(
    document_id=source.document_id, source_id=source.source_id,
    source_sha256=source.content_sha256,
)
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

manifest = {
    "config": str(config_path),
    "root": str(root),
    "source_ref": source_ref.to_dict(),
    "expected_source": {key: metadata[key] for key in (
        "canonical_entity_id", "market", "security_id", "document_kind",
        "fiscal_year", "fiscal_period",
    )},
    "artifact_sha256": version.content_sha256,
    "artifact_version_id": version.artifact_version_id,
    "byte_size": version.byte_size,
    "payload_sha256": canonical_json(payload).hex() if False else __import__("hashlib").sha256(payload).hexdigest(),
}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
catalog.close()
sys.stdout.write("lake materialized at %s\n" % OUT)
sys.stdout.write(json.dumps(manifest, indent=2))
