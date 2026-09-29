from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
from typing import Callable

import pytest

from company_wiki.automation.models import (
    Event,
    HandlerOutcome,
    HandlerResult,
    JobStatus,
    RuntimeState,
    canonical_json,
)
from company_wiki.automation.narrative_contracts import (
    NarrativeBundle,
    SourceRevisionEventPayload,
)
from company_wiki.automation.narrative_model import (
    ModelRateLimitError,
    ModelTimeoutError,
    NarrativeModelRequest,
    NarrativeModelResponse,
)
from company_wiki.automation.narrative_runtime import (
    NarrativeRuntimeDependencies,
    register_narrative_handlers,
)
from company_wiki.automation.policy import PolicyConfig
from company_wiki.automation.registry import create_default_registry
from company_wiki.automation.scheduler import AutomationScheduler
from company_wiki.automation.store import AutomationStore
from company_wiki.automation.worker import HandlerExecutor, Worker
from company_wiki.source_catalog import CatalogConfig, RootSpec, SourceCatalog
from company_wiki.source_catalog.source_reader import SourceVersionReader
from support.narrative_model_fixture import ReplayNarrativeModel


T0 = "2026-09-28T22:00:00Z"
T1 = "2026-09-28T22:01:00Z"


def _sha(value: bytes | str) -> str:
    data = value if isinstance(value, bytes) else value.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _pdf_bytes(text: str) -> bytes:
    fitz = pytest.importorskip("fitz")
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    data = document.tobytes()
    document.close()
    return data


def _sidecar(
    data: bytes,
    *,
    title: str,
    document_kind: str,
    provider_document_id: str,
    language: str = "en",
) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "canonical_entity_id": "ent-acme",
        "display_name": "Acme",
        "market": "US",
        "security_id": "ACME",
        "document_kind": document_kind,
        "fiscal_year": 2026,
        "period_end": "2026-06-30",
        "filing_date": "2026-08-01",
        "provider": "fixture",
        "provider_document_id": provider_document_id,
        "content_sha256": _sha(data),
        "source_url": f"https://fixtures.invalid/sources/{provider_document_id}",
        "source_title": title,
        "language": language,
        "retrieved_at": "2026-08-02T00:00:00Z",
        "collector_name": "narrative_runtime_fixture",
        "collector_version": "1.0.0",
    }


def _write_source(
    root: Path,
    *,
    name: str,
    data: bytes,
    title: str,
    document_kind: str,
) -> Path:
    directory = root / "Acme"
    if document_kind == "investor_call_transcript":
        directory = directory / "raw" / "investor_relations" / "transcripts"
    elif document_kind == "annual_report":
        directory = directory / "raw" / "financial_reports" / "annual"
    else:
        directory = directory / "raw" / "investor_relations"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_bytes(data)
    path.with_name(path.name + ".source.json").write_text(
        json.dumps(
            _sidecar(
                data,
                title=title,
                document_kind=document_kind,
                provider_document_id=name,
            ),
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path


def _new_catalog(run_root: Path, sources: list[dict[str, object]]) -> tuple[
    SourceCatalog,
    SourceVersionReader,
    dict[str, tuple[bytes, object]],
]:
    companies = run_root / "companies"
    by_sha: dict[str, bytes] = {}
    for source in sources:
        data = source["data"]
        assert isinstance(data, bytes)
        path = _write_source(
            companies,
            name=str(source["name"]),
            data=data,
            title=str(source["title"]),
            document_kind=str(source["document_kind"]),
        )
        by_sha[_sha(data)] = path.read_bytes()
    config = CatalogConfig(
        project_root=run_root,
        catalog_dir=run_root / "catalog",
        roots=(
            RootSpec(
                "company_raw",
                companies,
                "company_raw",
                priority=10,
                adapter_id="company_raw_v1",
                read_only=False,
                reusable_for_filing=True,
                canonical_write_target="companies",
            ),
        ),
        reusable_root_kinds=("company_raw",),
    )
    catalog = SourceCatalog(config)
    try:
        catalog.scan()
        reader = SourceVersionReader(catalog)
        result: dict[str, tuple[bytes, object]] = {}
        for digest, data in by_sha.items():
            row = catalog.reader.fetchone(
                """SELECT d.document_id, d.primary_source_id AS source_id
                     FROM documents d JOIN sources s ON s.source_id=d.primary_source_id
                    WHERE d.source_status='active' AND s.content_sha256=?""",
                (digest,),
            )
            assert row is not None
            ref = reader.query_ref(row["document_id"], row["source_id"], digest)
            result[digest] = (data, ref)
        return catalog, reader, result
    except BaseException:
        catalog.close()
        raise


def _event(
    reader: SourceVersionReader,
    ref,
    *,
    event_id: str,
) -> Event:
    metadata = reader.describe_version(ref)
    transcript = metadata["document_kind"] == "investor_call_transcript"
    expected_mime = "text/plain" if transcript else "application/pdf"
    assert ref.mime_type == expected_mime, (
        metadata.get("title"),
        metadata.get("document_kind"),
        ref.mime_type,
        expected_mime,
    )
    payload = {
        "schema_version": "source-revision-event/2.0",
        "source_ref": {
            "schema_version": ref.schema_version,
            "document_id": ref.document_id,
            "source_id": ref.source_id,
            "content_sha256": ref.content_sha256,
            "byte_size": ref.byte_size,
            "mime_type": ref.mime_type,
        },
        "expected_read_policy_sha256": reader.read_policy_sha256(),
        "source_metadata": {
            "source_class": "transcript" if transcript else "filing",
            "title": metadata["title"],
            "document_kind": metadata["document_kind"],
            "language": metadata["language"],
        },
    }
    parsed = SourceRevisionEventPayload.from_dict(payload)
    return Event(
        event_id=event_id,
        event_type="source.revision_registered",
        subject_type="source_revision",
        subject_id=ref.document_id,
        input_hash=parsed.input_hash,
        payload_json=canonical_json(payload),
        policy_version="narrative-v1",
        occurred_at=T0,
        observed_at=T0,
    )


class FixedClock:
    def now(self) -> str:
        return T1


class SequentialIDs:
    def __init__(self) -> None:
        self._value = 0

    def new_id(self) -> str:
        self._value += 1
        return f"runtime-e2e-{self._value:04d}"


class FailingModel:
    def __init__(self, error_factory: Callable[[], Exception]) -> None:
        self.calls: list[NarrativeModelRequest] = []
        self._error_factory = error_factory

    def generate(self, request: NarrativeModelRequest) -> NarrativeModelResponse:
        self.calls.append(request)
        raise self._error_factory()


def _runtime(
    run_root: Path,
    reader: SourceVersionReader,
    model,
) -> tuple[AutomationStore, AutomationScheduler, Worker]:
    state_dir = run_root / "automation"
    state_dir.mkdir()
    store = AutomationStore(state_dir / "automation.db")
    store.set_runtime_gate(RuntimeState.ENABLED, updated_at=T0)
    registry = create_default_registry()
    scheduler = AutomationScheduler(
        store,
        registry,
        PolicyConfig(allow_llm=True, allow_network=True),
    )
    executor = HandlerExecutor()
    register_narrative_handlers(
        executor,
        NarrativeRuntimeDependencies(
            reader=reader,
            model=model,
        ),
    )
    worker = Worker(
        store,
        registry,
        executor,
        clock=FixedClock(),
        id_gen=SequentialIDs(),
        lease_seconds=60,
        worker_id="narrative-runtime-e2e",
        allowed_job_types=(
            "source.narrative_select",
            "source.narrative_summarize",
            "source.narrative_verify",
        ),
    )
    return store, scheduler, worker


def _drain(worker: Worker, scheduler: AutomationScheduler, limit: int = 32) -> int:
    processed = 0
    for _ in range(limit):
        scheduler.refresh_ready(now=T1)
        if not worker.process_one():
            break
        processed += 1
    return processed


def _attempt_result(store: AutomationStore, job_id: str) -> HandlerResult:
    attempts = store.list_attempts(job_id)
    assert attempts and attempts[-1].result_json is not None
    return HandlerResult.from_dict(json.loads(attempts[-1].result_json))


def _run_root(tmp_path: Path, name: str) -> tuple[Path, tuple[str, ...]]:
    baseline = tuple(sorted(path.name for path in tmp_path.iterdir()))
    root = tmp_path / name
    assert root.parent.resolve() == tmp_path.resolve()
    assert root.name.startswith("m3-e4-runtime-")
    root.mkdir()
    return root, baseline


def _cleanup(
    tmp_path: Path,
    run_root: Path,
    baseline: tuple[str, ...],
    catalog: SourceCatalog | None,
) -> None:
    if catalog is not None:
        catalog.close()
    if run_root.exists():
        assert run_root.resolve().parent == tmp_path.resolve()
        assert run_root.name.startswith("m3-e4-runtime-")
        shutil.rmtree(run_root)
    assert tuple(sorted(path.name for path in tmp_path.iterdir())) == baseline


def test_runtime_e2e_three_sources_are_idempotent_and_leave_only_pending_effects(
    tmp_path: Path,
) -> None:
    run_root, baseline = _run_root(tmp_path, "m3-e4-runtime-success")
    catalog = None
    try:
        annual = _pdf_bytes(
            "Company launched a new product and expanded overseas capacity for customers."
        )
        low_value = _pdf_bytes("This policy describes meeting administration procedures.")
        transcript = (
            b"Full Conference Call Transcript\n"
            b"CEO: We launched a new product and expanded overseas capacity.\n"
            b"Questions & Answers\n"
            b"Analyst: Is commercial launch on schedule?\n"
        )
        sources = [
            {
                "name": "annual.pdf",
                "data": annual,
                "title": "ACME annual report",
                "document_kind": "annual_report",
            },
            {
                "name": "ir-policy.pdf",
                "data": low_value,
                "title": "投资者关系管理办法（2025年8月）.pdf",
                "document_kind": "ir_policy",
            },
            {
                "name": "call.txt",
                "data": transcript,
                "title": "ACME Q2 earnings call",
                "document_kind": "investor_call_transcript",
            },
        ]
        catalog, reader, indexed = _new_catalog(run_root, sources)
        raw_hashes = {digest: _sha(data) for digest, (data, _ref) in indexed.items()}
        artifacts_before = catalog.reader.fetchone("SELECT COUNT(*) AS count FROM artifacts")
        assert artifacts_before is not None
        model = ReplayNarrativeModel()
        store, scheduler, worker = _runtime(run_root, reader, model)
        events = [
            _event(
                reader,
                ref,
                event_id=f"event-runtime-{index}",
            )
            for index, (_data, ref) in enumerate(indexed.values(), start=1)
        ]
        for event in events:
            store.put_event(event)
            created = scheduler.materialize_event(event)
            assert (created.jobs_created, created.dependencies_created) == (3, 3)

        processed = _drain(worker, scheduler)
        assert processed == 9, [
            (job.job_type, job.status.value, job.last_error_code, job.last_error_detail)
            for job in store.list_jobs()
        ]
        assert len(model.calls) == 2
        jobs = store.list_jobs()
        assert sum(job.status is JobStatus.SUCCEEDED for job in jobs) == 6
        assert sum(job.status is JobStatus.VERIFYING for job in jobs) == 3
        verify_jobs = [job for job in jobs if job.job_type == "source.narrative_verify"]
        bundles = []
        for job in verify_jobs:
            result = _attempt_result(store, job.job_id)
            assert result.outcome is HandlerOutcome.SUCCEEDED
            bundles.append(NarrativeBundle.from_dict(result.result))
            assert len(store.list_effects(job.job_id)) == 1
        assert {bundle.quality_status for bundle in bundles} == {
            "verified",
            "skipped_no_narrative",
        }
        assert len(store.list_outbox_entries(status="pending")) == 3
        for event in events:
            replayed = scheduler.materialize_event(event)
            assert (replayed.jobs_created, replayed.dependencies_created) == (0, 0)
            assert (replayed.jobs_existing, replayed.dependencies_existing) == (3, 3)
        assert _drain(worker, scheduler) == 0
        assert len(store.list_outbox_entries(status="pending")) == 3
        artifacts_after = catalog.reader.fetchone("SELECT COUNT(*) AS count FROM artifacts")
        assert artifacts_after == artifacts_before
        assert {
            digest: _sha(data) for digest, (data, _ref) in indexed.items()
        } == raw_hashes
    finally:
        _cleanup(tmp_path, run_root, baseline, catalog)


@pytest.mark.parametrize(
    ("error_factory", "expected_code"),
    [
        (lambda: ModelRateLimitError("429"), "MODEL_RATE_LIMIT"),
        (lambda: ModelTimeoutError("timeout"), "MODEL_TIMEOUT"),
    ],
)
def test_runtime_e2e_model_transient_stops_before_verify_effect(
    tmp_path: Path,
    error_factory: Callable[[], Exception],
    expected_code: str,
) -> None:
    run_root, baseline = _run_root(tmp_path, f"m3-e4-runtime-{expected_code.lower()}")
    catalog = None
    try:
        data = _pdf_bytes("Company launched a new product for overseas customers.")
        catalog, reader, indexed = _new_catalog(
            run_root,
            [
                {
                    "name": "annual.pdf",
                    "data": data,
                    "title": "ACME annual report",
                    "document_kind": "annual_report",
                }
            ],
        )
        model = FailingModel(error_factory)
        store, scheduler, worker = _runtime(run_root, reader, model)
        ref = next(iter(indexed.values()))[1]
        event = _event(reader, ref, event_id="event-transient")
        store.put_event(event)
        scheduler.materialize_event(event)

        assert _drain(worker, scheduler) == 2
        jobs = {job.job_type: job for job in store.list_jobs()}
        assert jobs["source.narrative_select"].status is JobStatus.SUCCEEDED
        assert jobs["source.narrative_summarize"].status is JobStatus.RETRY_WAIT
        assert jobs["source.narrative_summarize"].last_error_code == expected_code
        assert jobs["source.narrative_verify"].status is JobStatus.PLANNED
        assert len(model.calls) == 1
        assert store.list_outbox_entries() == ()
    finally:
        _cleanup(tmp_path, run_root, baseline, catalog)


def test_runtime_e2e_read_identity_fails_automatically_and_transcript_needs_no_receipt(
    tmp_path: Path,
) -> None:
    run_root, baseline = _run_root(tmp_path, "m3-e4-runtime-auto-checks")
    catalog = None
    try:
        annual = _pdf_bytes("Company launched a new product for overseas customers.")
        transcript = (
            b"Full Conference Call Transcript\n"
            b"CEO: We launched a new product and expanded overseas capacity.\n"
        )
        catalog, reader, indexed = _new_catalog(
            run_root,
            [
                {
                    "name": "annual.pdf",
                    "data": annual,
                    "title": "ACME annual report",
                    "document_kind": "annual_report",
                },
                {
                    "name": "call.txt",
                    "data": transcript,
                    "title": "ACME earnings call",
                    "document_kind": "investor_call_transcript",
                },
            ],
        )
        model = ReplayNarrativeModel()
        store, scheduler, worker = _runtime(run_root, reader, model)
        refs = {data: ref for data, ref in indexed.values()}
        refused = _event(
            reader,
            refs[annual],
            event_id="event-read-policy-mismatch",
        )
        refused_payload = json.loads(refused.payload_json)
        refused_payload["expected_read_policy_sha256"] = _sha("wrong-read-policy")
        refused_parsed = SourceRevisionEventPayload.from_dict(refused_payload)
        refused = Event(
            **{
                **refused.to_dict(),
                "input_hash": refused_parsed.input_hash,
                "payload_json": canonical_json(refused_payload),
            }
        )
        transcript_event = _event(
            reader,
            refs[transcript],
            event_id="event-transcript-no-review",
        )
        for event in (refused, transcript_event):
            store.put_event(event)
            scheduler.materialize_event(event)

        processed = _drain(worker, scheduler)
        assert processed == 4, [
            (job.job_type, job.status.value, job.last_error_code, job.last_error_detail)
            for job in store.list_jobs()
        ]
        jobs = store.list_jobs()
        refused_select = next(
            job
            for job in jobs
            if job.created_from_event_id == refused.event_id
            and job.job_type == "source.narrative_select"
        )
        transcript_verify = next(
            job
            for job in jobs
            if job.created_from_event_id == transcript_event.event_id
            and job.job_type == "source.narrative_verify"
        )
        assert refused_select.status is JobStatus.DEAD_LETTER
        assert refused_select.last_error_code == "POLICY_DENIED"
        assert transcript_verify.status is JobStatus.VERIFYING
        assert store.list_outbox_entries(status="pending")
        assert len(model.calls) == 1
    finally:
        _cleanup(tmp_path, run_root, baseline, catalog)
