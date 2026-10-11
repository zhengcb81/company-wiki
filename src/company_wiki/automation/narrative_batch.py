"""One finite, scoped application over the existing AUTO task system."""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import stat
import time
from typing import Any

from company_wiki._file_mutex import FileMutexLockedError, os_file_mutex

from company_wiki.source_catalog import SourceCatalog
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.lock import CatalogOperationLock
from company_wiki.source_catalog.narrative_artifact_store import (
    LocalNarrativeObjectStore, NarrativeArtifactNotVisibleError, NarrativeArtifactReader, NarrativeArtifactStore,
)
from company_wiki.source_catalog.narrative_language import detect_narrative_language, narrative_language_family
from company_wiki.source_catalog.narrative_normalization import NarrativeNormalization, PPTX_MIME
from company_wiki.source_catalog.source_reader import SourceVersionReader, SourceRef
from company_wiki.source_catalog.source_read_policy import (
    EXACT_READ_POLICY_FINGERPRINT_SCHEMA_VERSION, READ_POLICY_FINGERPRINT_SCHEMA_VERSION,
)

from .models import EffectStatus, Event, HandlerResult, Job, JobStatus, RuntimeGate, RuntimeState, canonical_json, canonical_json_hash
from .narrative_batch_request import NarrativeBatchRequest
from .narrative_contracts import (
    BUNDLE_MAX_BYTES, SELECT_RESULT_MAX_BYTES, SUMMARY_RESULT_MAX_BYTES,
    SourceRevisionEventPayload,
)
from .narrative_model import FailedFinalDiagnostic, NARRATIVE_PROMPT_VERSION
from .narrative_generation import generation_manifest, projection_generation_manifest, generation_sha256, find_reuse_pin, read_reuse_pin
from .narrative_official_json import open_verified_projection
from .narrative_verify import BUNDLE_PRODUCER_VERSION
from .narrative_formats import source_class_for
from .narrative_projection import NarrativeEffectDispatcher
from .narrative_run_store import NarrativeRunError, NarrativeRunStore, RunConflictError
from .narrative_source_guard import (
    NarrativeSourceGuardError,
    source_ref,
    validate_opened_source,
)
from .narrative_verify import EFFECT_TYPE
from .policy import PolicyConfig
from .registry import create_default_registry
from .scheduler import AutomationScheduler
from .store import AutomationStore
from .supervisor import AutomationSupervisor, SupervisorConfig, profile_slots
from .terminal_receipt_contracts import FinalArtifactPin
from .terminal_receipts import compact_terminal_narrative_jobs


@dataclass(frozen=True)
class BatchEvents:
    input_hash: str
    events: tuple[Event, ...]
    source_facts: tuple[dict[str, Any], ...] = ()
    generation_manifests: dict = field(default_factory=dict)
    reused_artifact_pins: dict = field(default_factory=dict)
    normalization_config: dict | None = None


_NARRATIVE_JOB_TYPES = ("source.narrative_select", "source.narrative_summarize", "source.narrative_verify")
_TERMINAL = {JobStatus.SUCCEEDED, JobStatus.DEAD_LETTER, JobStatus.BLOCKED_HUMAN, JobStatus.CANCELLED}
_SOURCE_FACT_FIELDS = ("canonical_entity_id", "market", "security_id", "fiscal_year", "fiscal_period",
                       "period_end", "published_date", "form_type")


class BatchResumeError(ValueError):
    """A stable machine refusal; no provider body, physical path or secret detail."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class BatchPreparationDeadlineExceeded(TimeoutError):
    """The existing request time budget was spent before workers started."""


def _check_preparation_deadline(deadline: float | None) -> None:
    if deadline is not None and time.monotonic() >= deadline:
        raise BatchPreparationDeadlineExceeded("BATCH_PREPARATION_DEADLINE_EXCEEDED")


def _current_sources(
    request, reader, *, deadline=None, normalization=None, projection_catalog=None
):
    """Read current identity/period and exact version admission without writing."""
    _check_preparation_deadline(deadline)
    payloads = []
    source_facts = []
    for item in request.work_items:
        _check_preparation_deadline(deadline)
        if item.kind == "official_json":
            if projection_catalog is None:
                raise ValueError("PROJECTION_SOURCE_PORT_UNAVAILABLE")
            view = open_verified_projection(
                projection_catalog,
                projection_id=item.projection_id,
                expected_projection_sha256=item.projection_sha256,
            )
            _check_preparation_deadline(deadline)
            descriptions = [
                reader.describe_version(SourceRef(**ref))
                for ref in view.subject.parent_source_refs
            ]
            kinds = {
                m.get("document_kind") for m in descriptions if m.get("document_kind")
            }
            titles = {m.get("title") for m in descriptions if m.get("title")}
            metadata = {
                "source_class": "official_json",
                "title": next(iter(titles))
                if len(titles) == 1
                else "Official JSON records",
                "document_kind": next(iter(kinds))
                if len(kinds) == 1
                else "official_json_disclosure",
                "language": view.language or "unknown",
            }
            payloads.append(
                SourceRevisionEventPayload.from_dict(
                    {
                        "schema_version": "source-revision-event/3.0",
                        "subject_binding": view.subject.to_dict(),
                        "source_metadata": metadata,
                    }
                )
            )
            source_facts.append(
                {
                    "item_key": view.subject.item_key,
                    "subject_binding": view.subject.to_dict(),
                    "document_kind": metadata["document_kind"],
                }
            )
            continue
        ref = item.source_ref
        assert ref is not None
        current = reader.query_ref(ref.document_id, ref.source_id, ref.content_sha256)
        if asdict(current) != ref.to_dict():
            raise ValueError("SOURCE_REF_CHANGED")
        policy = reader.read_policy_sha256(current)
        metadata = reader.describe_version(current)
        _check_preparation_deadline(deadline)
        kind = metadata["document_kind"] or "unknown"
        language = metadata.get("language")
        declared_language = language
        if language in {None, "unknown"}:
            opened = reader.open_version(
                current,
                purpose="narrative_derivation",
                expected_read_policy_sha256=policy,
            )
            _check_preparation_deadline(deadline)
            try:
                validate_opened_source(
                    current,
                    opened,
                    expected_read_policy_sha256=policy,
                )
            except NarrativeSourceGuardError as exc:
                if exc.code == "SOURCE_HASH_MISMATCH":
                    raise ValueError("SOURCE_LANGUAGE_SOURCE_MISMATCH") from exc
                raise
            language = detect_narrative_language(
                opened.data, current.mime_type, normalization=normalization
            )
            _check_preparation_deadline(deadline)
        else:
            language = narrative_language_family(language)
        payloads.append(
            SourceRevisionEventPayload.from_dict(
                {
                    "schema_version": "source-revision-event/2.0",
                    "source_ref": ref.to_dict(),
                    "expected_read_policy_sha256": policy,
                    "source_metadata": {
                        "source_class": source_class_for(current.mime_type, kind),
                        "title": metadata["title"],
                        "document_kind": kind,
                        "language": language,
                        **(
                            {"declared_language": declared_language}
                            if declared_language not in {None, "unknown", language}
                            else {}
                        ),
                    },
                }
            )
        )
        source_facts.append(
            {
                "document_id": ref.document_id,
                "document_kind": kind,
                **{field: metadata.get(field) for field in _SOURCE_FACT_FIELDS},
            }
        )
    _check_preparation_deadline(deadline)
    return payloads, tuple(source_facts)


def build_batch_events(
    request: NarrativeBatchRequest,
    reader: SourceVersionReader,
    *,
    now: str,
    deadline: float | None = None,
    projection_catalog=None,
) -> BatchEvents:
    """Bind current source facts and execution settings before materializing jobs."""
    payloads, facts = _current_sources(
        request, reader, deadline=deadline, projection_catalog=projection_catalog
    )
    return _events_from_sources(request, payloads, facts, now=now)


def _events_from_sources(request, payloads, facts, *, now):
    """Pure event construction over the source facts already checked once."""
    input_hash = canonical_json_hash(
        {
            "request_sha256": request.input_hash,
            "source_payloads": [payload.to_dict() for payload in payloads],
        }
    )
    return BatchEvents(
        input_hash,
        tuple(
            Event(
                "narrative-batch-"
                + canonical_json_hash({"run": input_hash, "source": payload.item_key}),
                "source.revision_registered",
                "narrative_subject"
                if payload.subject.kind == "official_json"
                else "source_revision",
                payload.item_key,
                payload.input_hash,
                canonical_json(payload.to_dict()),
                "narrative-batch/1:" + input_hash,
                now,
                now,
            )
            for payload in payloads
        ),
        facts,
    )


def _execution_versions(request):
    registry = create_default_registry()
    return {**request.execution_versions,
            "handlers": {kind: registry.get(kind).handler_version for kind in _NARRATIVE_JOB_TYPES}}


def _job_prompt_versions(jobs, manifests):
    """Freeze each model job's actual prompt without moving source logic to the ledger."""
    return {
        job.job_id: manifests[job.subject_id]["execution_versions"]["prompt"]
        for job in jobs if job.job_type == "source.narrative_summarize"
    }


def _frozen_binding(request, binding, *, jobs=()):
    policies = {
        payload.item_key: payload.expected_read_policy_sha256
        for event in binding.events
        for payload in [
            SourceRevisionEventPayload.from_dict(json.loads(event.payload_json))
        ]
        if payload.subject.kind == "raw"
    }
    reusable = bool(binding.generation_manifests)
    if reusable and set(binding.generation_manifests) != {
        item.item_key for item in request.work_items
    }:
        raise BatchResumeError("BATCH_FROZEN_BINDING_INVALID")
    if binding.reused_artifact_pins and not reusable:
        raise BatchResumeError("BATCH_FROZEN_BINDING_INVALID")
    frozen = {
        "schema_version": "narrative-run-binding/4"
        if request.schema_version == "narrative-batch-request/2"
        else ("narrative-run-binding/3" if reusable else "narrative-run-binding/2"),
        "request_sha256": request.request_sha256,
        "execution_versions": _execution_versions(request),
        "read_policy_schema_version": EXACT_READ_POLICY_FINGERPRINT_SCHEMA_VERSION,
        "read_policy_sha256": canonical_json_hash(policies),
        "source_read_policies": policies,
        "source_facts": list(binding.source_facts),
    }
    if reusable:
        _validate_normalization_binding(
            binding.generation_manifests, binding.normalization_config
        )
        frozen.update(
            **_freeze_generations(binding.generation_manifests),
            reused_artifact_pins=binding.reused_artifact_pins,
            normalization_config=binding.normalization_config,
        )
    if request.schema_version == "narrative-batch-request/2":
        frozen["job_prompt_versions"] = _job_prompt_versions(
            jobs, binding.generation_manifests
        )
    return canonical_json(frozen)


_GENERATION_SOURCE_FIELDS = frozenset({"source_ref", "source_metadata", "parser_component",
                                     "parser_components", "material_extractor", "subject_binding", "source_adapter", "language"})


def _freeze_generations(manifests):
    """Deduplicate settings so 100-source bindings retain the existing byte cap."""
    settings, records = {}, {}
    for document, manifest in manifests.items():
        common = {key: value for key, value in manifest.items() if key not in _GENERATION_SOURCE_FIELDS}
        digest = canonical_json_hash(common)
        settings[digest] = common
        records[document] = {"settings_sha256": digest, "generation_sha256": generation_sha256(manifest),
            "source_inputs": {key: value for key, value in manifest.items() if key in _GENERATION_SOURCE_FIELDS}}
    return {"generation_settings": settings, "generation_manifests": records}


def _thaw_generations(frozen):
    settings, records = frozen["generation_settings"], frozen["generation_manifests"]
    if not isinstance(settings, dict) or not isinstance(records, dict):
        raise BatchResumeError("BATCH_FROZEN_BINDING_INVALID")
    manifests = {}
    for document, record in records.items():
        if not isinstance(record, dict) or set(record) != {
            "settings_sha256",
            "generation_sha256",
            "source_inputs",
        }:
            raise BatchResumeError("BATCH_FROZEN_BINDING_INVALID")
        common = settings[record["settings_sha256"]]
        source = record["source_inputs"]
        if (
            not isinstance(common, dict)
            or canonical_json_hash(common) != record["settings_sha256"]
            or not isinstance(source, dict)
            or not (
                {"subject_binding", "source_adapter", "language", "parser_component"}
                <= source.keys()
                if common.get("schema_version") == "narrative-generation/2"
                else {"source_ref", "source_metadata", "parser_component"}
                <= source.keys()
            )
            or not source.keys() <= _GENERATION_SOURCE_FIELDS
            or source.keys() & common.keys()
        ):
            raise BatchResumeError("BATCH_FROZEN_BINDING_INVALID")
        manifest = {**common, **source}
        if generation_sha256(manifest) != record["generation_sha256"]:
            raise BatchResumeError("BATCH_FROZEN_BINDING_INVALID")
        manifests[document] = manifest
    return manifests


def _validate_normalization_binding(manifests, snapshot):
    """Check frozen causal identity without deployment reads or adapter inference."""
    from .narrative_formats import NORMALIZED_MIME_TYPES

    try:
        for manifest in manifests.values():
            if manifest.get("schema_version") == "narrative-generation/2":
                continue
            mime = manifest["source_ref"]["mime_type"]
            if (
                mime not in NORMALIZED_MIME_TYPES
                or manifest["source_metadata"]["source_class"] != "filing"
            ):
                continue
            component = manifest["parser_component"]
            components = manifest.get("parser_components")
            ocr = mime == PPTX_MIME and component["version"] == "2.0.0"
            if components is None and not ocr:
                continue  # Legal historical pure manifests carry only the parser tuple.
            port = NarrativeNormalization.from_snapshot(snapshot if ocr else None)
            actual = port.identity(mime, parser_version=component["version"])
            if components != actual or component != {
                "name": actual["parser_name"],
                "version": actual["parser_version"],
            }:
                raise BatchResumeError("BATCH_FROZEN_BINDING_INVALID")
    except (KeyError, TypeError, ValueError) as exc:
        raise BatchResumeError("BATCH_FROZEN_BINDING_INVALID") from exc


def _completed_history_generation_matches(expected, manifest, *, completed_history):
    """Compare an old gen1 omission without changing its signed generation.

    Historical producers omitted an explicit HTTP reasoning effort. Only a
    fully settled read may keep that unknown value absent; new generations and
    every other field retain exact equality.
    """
    if expected == manifest:
        return True
    if (
        not completed_history
        or expected.get("schema_version") != "narrative-generation/1"
        or manifest.get("schema_version") != "narrative-generation/1"
        or not isinstance(expected.get("model"), dict)
        or not isinstance(manifest.get("model"), dict)
        or "reasoning_effort" in manifest["model"]
        or expected["model"].get("reasoning_effort") is None
    ):
        return False
    model = dict(expected["model"])
    model.pop("reasoning_effort")
    return {**expected, "model": model} == manifest


def _completed_read_history(reader, store, jobs):
    """Require terminal AUTO work, delivered effects and visible publications.

    A delivered outbox alone can precede catalog activation. Both observations
    are necessary to keep the completed-history branch away from workers.
    """
    from . import migrations

    if any(job.status not in _TERMINAL for job in jobs):
        return False
    if not jobs:
        return True  # Frozen reuse pins are replayed by the existing final read.
    scope = tuple(job.job_id for job in jobs)
    placeholders = ",".join("?" for _ in scope)
    connection = migrations._open_readonly_connection(store.db_path)
    try:
        effects = connection.execute(
            "SELECT e.effect_id,e.job_id,e.effect_type,e.status,o.status AS outbox_status "
            "FROM effects e LEFT JOIN outbox o ON o.effect_id=e.effect_id "
            f"WHERE e.job_id IN ({placeholders})",
            scope,
        ).fetchall()
    finally:
        connection.close()
    if any(
        effect["outbox_status"] != "delivered"
        or effect["status"] not in {"verified", "applied"}
        for effect in effects
    ):
        return False
    published_jobs = {
        effect["job_id"] for effect in effects if effect["effect_type"] == EFFECT_TYPE
    }
    if any(
        job.job_type == "source.narrative_verify"
        and job.status is JobStatus.SUCCEEDED
        and job.job_id not in published_jobs
        for job in jobs
    ):
        return False
    artifacts = NarrativeArtifactReader(
        reader.catalog.config.database_path,
        LocalNarrativeObjectStore(reader.catalog.config.catalog_dir),
    )
    try:
        for effect in effects:
            if effect["effect_type"] == EFFECT_TYPE:
                artifacts.visible_version_for_effect(effect["effect_id"])
    except NarrativeArtifactNotVisibleError:
        return False
    finally:
        artifacts.close()
    return True


def _resume_binding(
    request, reader, store, runs, run, *, deadline, prepared_sources=None
):
    """Verify the frozen membership against current source facts, never re-sign it."""
    if request.schema_version == "narrative-batch-request/2":
        return _resume_item_binding(
            request,
            reader,
            store,
            runs,
            run,
            deadline=deadline,
            prepared_sources=prepared_sources,
        )
    if run.binding_json is None:
        raise BatchResumeError("BATCH_LEGACY_BINDING_UNVERIFIABLE")
    try:
        frozen = json.loads(run.binding_json)
        if not isinstance(frozen, dict):
            raise BatchResumeError("BATCH_LEGACY_BINDING_UNVERIFIABLE")
        schema_pair = (
            frozen.get("schema_version"),
            frozen.get("read_policy_schema_version"),
        )
        reusable = schema_pair == (
            "narrative-run-binding/3",
            EXACT_READ_POLICY_FINGERPRINT_SCHEMA_VERSION,
        )
        scoped = reusable or schema_pair == (
            "narrative-run-binding/2",
            EXACT_READ_POLICY_FINGERPRINT_SCHEMA_VERSION,
        )
        if not scoped and schema_pair != (
            "narrative-run-binding/1",
            READ_POLICY_FINGERPRINT_SCHEMA_VERSION,
        ):
            raise BatchResumeError("BATCH_LEGACY_BINDING_UNVERIFIABLE")
        if frozen["request_sha256"] != request.request_sha256:
            raise BatchResumeError("BATCH_REQUEST_CHANGED")
        versions = frozen["execution_versions"]
        if (
            not isinstance(versions, dict)
            or set(versions) != set(_execution_versions(request))
            or not isinstance(versions.get("handlers"), dict)
            or set(versions["handlers"]) != set(_NARRATIVE_JOB_TYPES)
            or any(
                not isinstance(v, str) or not v
                for k, v in versions.items()
                if k != "handlers"
            )
            or any(
                not isinstance(v, str) or not v for v in versions["handlers"].values()
            )
        ):
            raise BatchResumeError("BATCH_FROZEN_BINDING_INVALID")
        if (
            run.prompt_version != versions["prompt"]
            or run.model_id != request.model_options["model_id"]
            or (
                run.pricing_version,
                run.input_micro_usd_per_million_tokens,
                run.output_micro_usd_per_million_tokens,
                run.max_tokens,
                run.max_micro_usd,
                run.max_output_bytes,
            )
            != (
                request.pricing_version,
                request.input_micro_usd_per_million_tokens,
                request.output_micro_usd_per_million_tokens,
                request.max_tokens,
                request.max_micro_usd,
                min(
                    len(request.work_items) * request.max_final_bytes,
                    request.max_persistent_bytes,
                ),
            )
        ):
            raise BatchResumeError("BATCH_FROZEN_BINDING_INVALID")
        documents = {item.item_key for item in request.work_items}
        if scoped:
            policies = frozen["source_read_policies"]
            if (
                not isinstance(policies, dict)
                or set(policies) != documents
                or any(
                    not isinstance(pin, str) or not re.fullmatch(r"[0-9a-f]{64}", pin)
                    for pin in policies.values()
                )
                or frozen["read_policy_sha256"] != canonical_json_hash(policies)
            ):
                raise BatchResumeError("BATCH_FROZEN_BINDING_INVALID")
        else:
            # An old digest contains no recoverable per-root rules. Retain its
            # original interpretation and never re-sign events/usage/baseline.
            policies = {
                document: frozen["read_policy_sha256"] for document in documents
            }
        pins = frozen["reused_artifact_pins"] if reusable else {}
        manifests = _thaw_generations(frozen) if reusable else {}
        if reusable:
            _validate_normalization_binding(
                manifests, frozen.get("normalization_config")
            )
        payload_wires = {
            document: {
                "schema_version": "source-revision-event/2.0",
                "source_ref": manifest["source_ref"],
                "source_metadata": manifest["source_metadata"],
                "expected_read_policy_sha256": policies[document],
            }
            for document, manifest in manifests.items()
        }
        if reusable and (
            not isinstance(pins, dict)
            or not set(pins) <= documents
            or not isinstance(manifests, dict)
            or set(manifests) != documents
            or not isinstance(payload_wires, dict)
            or set(payload_wires) != documents
        ):
            raise BatchResumeError("BATCH_FROZEN_BINDING_INVALID")
        jobs = store.list_jobs(job_ids=run.job_ids)
        members = runs.job_bindings(run.run_id)
        if (
            len(jobs)
            != (len(request.work_items) - len(pins)) * len(_NARRATIVE_JOB_TYPES)
            or set(members) != set(run.job_ids)
            or canonical_json_hash(list(sorted(run.job_ids))) != run.scope_sha256
        ):
            raise BatchResumeError("BATCH_FROZEN_MEMBERSHIP_INVALID")
        event_ids = {job.created_from_event_id for job in jobs}
        events = tuple(store.get_event(event_id) for event_id in sorted(event_ids))
        if len(events) != len(request.work_items) - len(pins) or any(
            event is None for event in events
        ):
            raise BatchResumeError("BATCH_FROZEN_MEMBERSHIP_INVALID")
        by_document = {}
        if reusable:
            for document in pins:
                payload = SourceRevisionEventPayload.from_dict(payload_wires[document])
                event = Event(
                    "narrative-batch-"
                    + canonical_json_hash({"run": run.input_hash, "source": document}),
                    "source.revision_registered",
                    "source_revision",
                    document,
                    payload.input_hash,
                    canonical_json(payload.to_dict()),
                    "narrative-batch/1:" + run.input_hash,
                    run.created_at,
                    run.created_at,
                )
                events += (event,)
        for event in events:
            payload = SourceRevisionEventPayload.from_dict(
                json.loads(event.payload_json)
            )
            if (
                event.input_hash != payload.input_hash
                or event.policy_version != "narrative-batch/1:" + run.input_hash
                or event.subject_id != payload.source_ref.document_id
                or payload.expected_read_policy_sha256
                != policies.get(payload.source_ref.document_id)
                or event.event_id
                != "narrative-batch-"
                + canonical_json_hash(
                    {"run": run.input_hash, "source": payload.item_key}
                )
            ):
                raise BatchResumeError("BATCH_FROZEN_MEMBERSHIP_INVALID")
            related = tuple(
                job for job in jobs if job.created_from_event_id == event.event_id
            )
            expected_count = (
                0 if event.subject_id in pins else len(_NARRATIVE_JOB_TYPES)
            )
            if (
                len(related) != expected_count
                or {job.job_type for job in related}
                != (set(_NARRATIVE_JOB_TYPES) if expected_count else set())
                or any(
                    (job.input_hash, job.handler_version) != members[job.job_id]
                    or job.handler_version != versions["handlers"][job.job_type]
                    or job.policy_version != event.policy_version
                    or job.input_hash != event.input_hash
                    or job.subject_id != event.subject_id
                    for job in related
                )
            ):
                raise BatchResumeError("BATCH_FROZEN_MEMBERSHIP_INVALID")
            if reusable and payload.to_dict() != payload_wires.get(event.subject_id):
                raise BatchResumeError("BATCH_FROZEN_MEMBERSHIP_INVALID")
            if reusable:
                manifest = manifests[event.subject_id]
                expected = generation_manifest(
                    request,
                    payload,
                    execution_versions=versions,
                    parser_components=manifest.get("parser_components"),
                )
                # Preserve frozen parser/producer interpretation on completed
                # history. The public reader must explicitly replay that version.
                expected["parser_component"] = manifest["parser_component"]
                expected["bundle_producer"] = manifest["bundle_producer"]
                if "material_extractor" in manifest:
                    expected["material_extractor"] = manifest["material_extractor"]
                if expected != manifest and not (
                    _completed_history_generation_matches(
                        expected, manifest, completed_history=True
                    )
                    and _completed_read_history(reader, store, jobs)
                ):
                    raise BatchResumeError("BATCH_FROZEN_BINDING_INVALID")
            by_document[payload.source_ref.document_id] = (event, payload)
        current_payloads, current_facts = (
            _current_sources(request, reader, deadline=deadline)
            if prepared_sources is None
            else prepared_sources
        )
        if set(by_document) != documents:
            raise BatchResumeError("BATCH_FROZEN_MEMBERSHIP_INVALID")
        ordered_events = []
        for current in current_payloads:
            saved_event, saved = by_document[current.source_ref.document_id]
            saved_wire, current_wire = saved.to_dict(), current.to_dict()
            # Only the pin's interpretation differs when opening a schema-2
            # history under current code. Every source/payload fact must match.
            saved_wire.pop("expected_read_policy_sha256")
            current_wire.pop("expected_read_policy_sha256")
            # Already-created jobs retain their generation descriptions and pins.
            # Same original bytes do not need new model work after a title, issuer
            # declaration or period correction. Current selection/read controls
            # use the current facts separately; no old facts are re-signed here.
            saved_wire.pop("source_metadata")
            current_wire.pop("source_metadata")
            if saved_wire != current_wire:
                raise BatchResumeError("BATCH_SOURCE_FACTS_CHANGED")
            ordered_events.append(saved_event)
        return (
            BatchEvents(
                run.input_hash,
                tuple(ordered_events),
                current_facts,
                manifests,
                pins,
                frozen.get("normalization_config"),
            ),
            versions,
            jobs,
        )
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise BatchResumeError("BATCH_FROZEN_BINDING_INVALID") from exc


def _projection_loader(catalog):
    def load(subject):
        return open_verified_projection(
            catalog,
            projection_id=subject.item_key,
            expected_projection_sha256=subject.subject_sha256,
        )

    return load


def _item_generation(request, payload, *, normalization=None, versions=None):
    versions = versions or _execution_versions(request)
    if payload.subject.kind == "raw":
        raw_versions = {
            k: v
            for k, v in versions.items()
            if k
            not in {
                "projection_prompt",
                "projection_model_request_schema",
                "official_json_adapter",
            }
        }
        return generation_manifest(
            request,
            payload,
            execution_versions=raw_versions,
            parser_components=normalization.identity(payload.source_ref.mime_type)
            if normalization is not None
            and payload.source_ref.mime_type == PPTX_MIME
            and payload.source_metadata.source_class == "filing"
            else None,
        )
    projected_versions = {k: versions[k] for k in ("adapter", "selector", "handlers")}
    projected_versions.update(
        prompt=versions["projection_prompt"],
        model_request_schema=versions["projection_model_request_schema"],
    )
    return projection_generation_manifest(
        request,
        payload.subject,
        language=payload.source_metadata.language,
        execution_versions=projected_versions,
        bundle_producer=BUNDLE_PRODUCER_VERSION,
        narrative_adapter_version=versions["official_json_adapter"],
        source_metadata=payload.source_metadata.to_dict(),
    )


def _manifest_payload(manifest, policies, key):
    if manifest.get("schema_version") == "narrative-generation/2":
        return SourceRevisionEventPayload.from_dict(
            {
                "schema_version": "source-revision-event/3.0",
                "subject_binding": manifest["subject_binding"],
                "source_metadata": manifest["source_metadata"],
            }
        )
    return SourceRevisionEventPayload.from_dict(
        {
            "schema_version": "source-revision-event/2.0",
            "source_ref": manifest["source_ref"],
            "source_metadata": manifest["source_metadata"],
            "expected_read_policy_sha256": policies[key],
        }
    )


def _resume_item_binding(
    request, reader, store, runs, run, *, deadline, prepared_sources
):
    """Decode the versioned item binding while retaining the same AUTO jobs/ledger."""
    if run.binding_json is None or prepared_sources is None:
        raise BatchResumeError("BATCH_FROZEN_BINDING_INVALID")
    try:
        frozen = json.loads(run.binding_json)
        if frozen.get("schema_version") != "narrative-run-binding/4":
            raise BatchResumeError("BATCH_FROZEN_BINDING_INVALID")
        if frozen["request_sha256"] != request.request_sha256:
            raise BatchResumeError("BATCH_REQUEST_CHANGED")
        versions = frozen["execution_versions"]
        if (
            not isinstance(versions, dict)
            or set(versions) != set(_execution_versions(request))
            or not isinstance(versions.get("handlers"), dict)
            or set(versions["handlers"]) != set(_NARRATIVE_JOB_TYPES)
            or any(
                not isinstance(v, str) or not v
                for k, v in versions.items()
                if k != "handlers"
            )
            or any(
                not isinstance(v, str) or not v for v in versions["handlers"].values()
            )
        ):
            raise BatchResumeError("BATCH_FROZEN_BINDING_INVALID")
        if (
            run.prompt_version != versions["prompt"]
            or run.model_id != request.model_options["model_id"]
            or (
                run.pricing_version,
                run.input_micro_usd_per_million_tokens,
                run.output_micro_usd_per_million_tokens,
                run.max_tokens,
                run.max_micro_usd,
                run.max_output_bytes,
            )
            != (
                request.pricing_version,
                request.input_micro_usd_per_million_tokens,
                request.output_micro_usd_per_million_tokens,
                request.max_tokens,
                request.max_micro_usd,
                min(
                    len(request.work_items) * request.max_final_bytes,
                    request.max_persistent_bytes,
                ),
            )
        ):
            raise BatchResumeError("BATCH_FROZEN_BINDING_INVALID")
        policies = frozen["source_read_policies"]
        raw_keys = {item.item_key for item in request.work_items if item.kind == "raw"}
        if (
            not isinstance(policies, dict)
            or set(policies) != raw_keys
            or any(
                not isinstance(pin, str) or not re.fullmatch(r"[0-9a-f]{64}", pin)
                for pin in policies.values()
            )
            or frozen["read_policy_sha256"] != canonical_json_hash(policies)
            or frozen["read_policy_schema_version"]
            != EXACT_READ_POLICY_FINGERPRINT_SCHEMA_VERSION
        ):
            raise BatchResumeError("BATCH_FROZEN_BINDING_INVALID")
        manifests = _thaw_generations(frozen)
        pins = frozen["reused_artifact_pins"]
        keys = {item.item_key for item in request.work_items}
        if (
            set(manifests) != keys
            or not isinstance(pins, dict)
            or not set(pins) <= keys
        ):
            raise BatchResumeError("BATCH_FROZEN_BINDING_INVALID")
        _validate_normalization_binding(manifests, frozen.get("normalization_config"))
        current_payloads, facts = prepared_sources
        current = {payload.item_key: payload for payload in current_payloads}
        if set(current) != keys:
            raise BatchResumeError("BATCH_SOURCE_FACTS_CHANGED")
        jobs = store.list_jobs(job_ids=run.job_ids)
        members = runs.job_bindings(run.run_id)
        if (
            len(jobs) != (len(keys) - len(pins)) * len(_NARRATIVE_JOB_TYPES)
            or set(members) != set(run.job_ids)
            or canonical_json_hash(list(sorted(run.job_ids))) != run.scope_sha256
        ):
            raise BatchResumeError("BATCH_FROZEN_MEMBERSHIP_INVALID")
        if frozen.get("job_prompt_versions") != _job_prompt_versions(jobs, manifests):
            raise BatchResumeError("BATCH_FROZEN_BINDING_INVALID")
        events = []
        for item in request.work_items:
            _check_preparation_deadline(deadline)
            key = item.item_key
            manifest = manifests[key]
            saved = _manifest_payload(manifest, policies, key)
            if saved.item_key != key or saved.subject != current[key].subject:
                raise BatchResumeError("BATCH_SOURCE_FACTS_CHANGED")
            expected = _item_generation(
                request,
                saved,
                normalization=NarrativeNormalization.from_snapshot(
                    frozen.get("normalization_config"), deadline=deadline
                ),
                versions=versions,
            )
            for field in ("parser_component", "bundle_producer", "material_extractor"):
                if field in manifest:
                    expected[field] = manifest[field]
            if expected != manifest and not (
                _completed_history_generation_matches(
                    expected, manifest, completed_history=True
                )
                and _completed_read_history(reader, store, jobs)
            ):
                raise BatchResumeError("BATCH_FROZEN_BINDING_INVALID")
            event = _events_from_sources(
                request, [saved], (), now=run.created_at
            ).events[0]
            event = Event(
                "narrative-batch-"
                + canonical_json_hash({"run": run.input_hash, "source": key}),
                event.event_type,
                event.subject_type,
                key,
                saved.input_hash,
                canonical_json(saved.to_dict()),
                "narrative-batch/1:" + run.input_hash,
                run.created_at,
                run.created_at,
            )
            if key not in pins:
                actual = store.get_event(event.event_id)
                if actual is None or (
                    actual.event_type,
                    actual.subject_type,
                    actual.subject_id,
                    actual.input_hash,
                    actual.payload_json,
                    actual.policy_version,
                ) != (
                    event.event_type,
                    event.subject_type,
                    key,
                    event.input_hash,
                    event.payload_json,
                    event.policy_version,
                ):
                    raise BatchResumeError("BATCH_FROZEN_MEMBERSHIP_INVALID")
                event = actual
            related = [
                job for job in jobs if job.created_from_event_id == event.event_id
            ]
            count = 0 if key in pins else len(_NARRATIVE_JOB_TYPES)
            if (
                len(related) != count
                or {j.job_type for j in related}
                != (set(_NARRATIVE_JOB_TYPES) if count else set())
                or any(
                    (j.input_hash, j.handler_version) != members[j.job_id]
                    or j.handler_version != versions["handlers"][j.job_type]
                    or j.policy_version != event.policy_version
                    or j.input_hash != event.input_hash
                    or j.subject_id != key
                    for j in related
                )
            ):
                raise BatchResumeError("BATCH_FROZEN_MEMBERSHIP_INVALID")
            events.append(event)
        return (
            BatchEvents(
                run.input_hash,
                tuple(events),
                facts,
                manifests,
                pins,
                frozen.get("normalization_config"),
            ),
            versions,
            jobs,
        )
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise BatchResumeError("BATCH_FROZEN_BINDING_INVALID") from exc


def _read_projected_pin(artifacts, reader, payload, pin, manifest, *, catalog):
    from .narrative_transport import NarrativeTransportReader
    from .narrative_transport_contracts import NarrativeReadRequest
    from .narrative_contracts import NarrativeBundle

    if pin.get("subject_binding") != payload.subject.to_dict() or pin.get(
        "generation_sha256"
    ) != generation_sha256(manifest):
        raise ValueError("BATCH_REUSE_PIN_SUBJECT_MISMATCH")
    result = NarrativeTransportReader(
        artifacts, reader, projection_loader=_projection_loader(catalog)
    ).read(
        NarrativeReadRequest.from_dict(
            {
                "schema_version": "narrative-read-request/2",
                "narrative_ref": pin,
                "as_of_date": payload.subject.as_of_date,
                "expected_issuer": None,
            }
        )
    )
    bundle = NarrativeBundle.from_dict(json.loads(result.data))
    if (
        bundle.source_metadata.to_dict() != manifest["source_metadata"]
        or bundle.versions.parser != manifest["parser_component"]["version"]
        or bundle.versions.bundle_producer != manifest["bundle_producer"]
        or bundle.versions.selector != manifest["execution_versions"]["selector"]
        or (
            bundle.summary.model is not None
            and (
                bundle.summary.model.model_id != manifest["model"]["model_id"]
                or bundle.summary.model.adapter_id
                != manifest["execution_versions"]["adapter"]
                or bundle.summary.model.prompt_version
                != manifest["execution_versions"]["prompt"]
            )
        )
    ):
        raise ValueError("BATCH_REUSE_BUNDLE_GENERATION_MISMATCH")
    return (
        bundle.selection.status in {"selected", "partial"}
        and bundle.summary.status == "completed"
        and bool(bundle.evidence_spans)
    ) or (
        bundle.selection.coverage_complete
        and bundle.selection.status == "skipped_no_narrative"
        and bundle.summary.status == "summary_not_needed"
        and not bundle.evidence_spans
        and bundle.selection.selected_count == 0
    )


def _find_item_reuse_pin(
    artifacts, reader, payload, manifest, facts, *, catalog, normalization=None
):
    if payload.subject.kind == "raw":
        return find_reuse_pin(
            artifacts, reader, payload, manifest, facts, normalization=normalization
        )
    versions = artifacts.visible_subject_generation_candidates(
        subject=payload.subject, generation_sha256=generation_sha256(manifest)
    )
    for version in versions:
        metadata = json.loads(version.metadata_json)
        if metadata.get("generation_manifest") != manifest:
            raise ValueError("BATCH_REUSE_MANIFEST_INVALID")
        pin = {
            "schema_version": "narrative-ref/2",
            "artifact_version_id": version.artifact_version_id,
            "artifact_sha256": version.content_sha256,
            "byte_size": version.byte_size,
            "subject_binding": payload.subject.to_dict(),
            "generation_sha256": generation_sha256(manifest),
        }
        if _read_projected_pin(
            artifacts, reader, payload, pin, manifest, catalog=catalog
        ):
            return pin
    return None


@dataclass(frozen=True)
class StorageSnapshot:
    persistent_added_bytes: int
    scratch_bytes: int
    scratch_peak_bytes: int


def _tree_bytes(path: Path) -> int:
    try:
        info = path.stat()
    except FileNotFoundError:
        return 0
    if stat.S_ISREG(info.st_mode):
        return info.st_size
    total = 0
    for item in path.rglob("*"):
        try:
            info = item.stat()
        except FileNotFoundError:
            # SQLite sidecars and atomic object files may be reclaimed while
            # sampling. Their disappearance releases storage, not a run error.
            continue
        if stat.S_ISREG(info.st_mode):
            total += info.st_size
    return total


class BatchStorageBudget:
    """Measure only application-owned storage, never a raw document tree."""

    def __init__(self, *, files: tuple[Path, ...], persistent_dirs: tuple[Path, ...],
                 scratch_dirs: tuple[Path, ...], max_persistent_bytes: int, max_scratch_bytes: int,
                 baseline: tuple[int, ...] | None = None):
        self.paths = files + persistent_dirs
        self.baseline = baseline if baseline is not None else tuple(_tree_bytes(path) for path in self.paths)
        if len(self.baseline) != len(self.paths) or any(type(size) is not int or size < 0 for size in self.baseline):
            raise ValueError("BATCH_STORAGE_BASELINE_INVALID")
        self.scratch_dirs = scratch_dirs
        self.max_persistent_bytes = max_persistent_bytes
        self.max_scratch_bytes = max_scratch_bytes
        self.peak = 0

    def snapshot(self) -> StorageSnapshot:
        added = sum(max(0, _tree_bytes(path) - size) for path, size in zip(self.paths, self.baseline))
        scratch = sum(_tree_bytes(path) for path in self.scratch_dirs)
        self.peak = max(self.peak, scratch)
        return StorageSnapshot(added, scratch, self.peak)

    def check(self) -> StorageSnapshot:
        result = self.snapshot()
        if result.persistent_added_bytes > self.max_persistent_bytes:
            raise ValueError("PERSISTENT_BYTES_EXCEEDED")
        if result.scratch_bytes > self.max_scratch_bytes:
            raise ValueError("SCRATCH_BYTES_EXCEEDED")
        return result


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _storage_guard(request, catalog, db_path, work_dir, input_hash, *, read_only=False):
    database_paths = (db_path, catalog.config.database_path)
    files = tuple(path for database in database_paths for path in (
        database, Path(str(database) + "-wal"), Path(str(database) + "-shm")))
    baseline_path = work_dir / "storage-baseline.json"
    baseline = None
    if read_only and not baseline_path.is_file():
        raise BatchResumeError("BATCH_WORK_BASELINE_MISSING")
    if baseline_path.exists():
        saved = json.loads(baseline_path.read_text(encoding="utf-8"))
        if saved.get("input_hash") != input_hash:
            raise ValueError("BATCH_WORK_DIRECTORY_CONFLICT")
        baseline = tuple(saved["sizes"])
    persistent_dirs: tuple[Path, ...] = (catalog.config.catalog_dir / "objects", work_dir)
    # Legacy baseline vectors keep their original interpretation and bytes.
    # New vectors also measure this application's small recovery locators.
    if baseline is None or len(baseline) == len(files) + len(persistent_dirs) + 1:
        persistent_dirs += (catalog.config.catalog_dir / "narrative-generations",)
    guard = BatchStorageBudget(files=files, persistent_dirs=persistent_dirs,
        scratch_dirs=(), max_persistent_bytes=request.max_persistent_bytes,
        max_scratch_bytes=request.max_scratch_bytes, baseline=baseline)
    if baseline is None and not read_only:
        baseline_path.write_text(canonical_json({"input_hash": input_hash, "sizes": list(guard.baseline)}), encoding="utf-8")
    return guard


class _BudgetedObjects(LocalNarrativeObjectStore):
    def __init__(self, root, guard, max_final_bytes):
        super().__init__(root)
        self.guard = guard
        self.max_final_bytes = max_final_bytes

    def put(self, data):
        if len(data) > self.max_final_bytes:
            raise ValueError("FINAL_BYTES_EXCEEDED")
        if len(data) > self.guard.max_scratch_bytes:
            raise ValueError("SCRATCH_BYTES_EXCEEDED")
        self.guard.check()
        # The object writer creates one temporary file containing exactly these
        # bytes and removes it in finally. PDF/text parsing uses memory only.
        self.guard.peak = max(self.guard.peak, len(data))
        return super().put(data)


def _preflight_storage(request, *, source_count=None):
    # All contracts are byte-bounded. Admit their worst case plus SQLite/WAL/log
    # overhead before any worker or HTTP starts; measured growth is checked too.
    per_source = (
        SELECT_RESULT_MAX_BYTES
        + SUMMARY_RESULT_MAX_BYTES
        + 2 * BUNDLE_MAX_BYTES
        + 1024**2
    )
    reserve = (
        (len(request.work_items) if source_count is None else source_count) * per_source
        + len(profile_slots(request.profile)) * 262144
        + 8 * 1024**2
    )
    if reserve > request.max_persistent_bytes:
        raise ValueError("PERSISTENT_BYTES_EXCEEDED")
    if request.max_final_bytes > request.max_scratch_bytes:
        raise ValueError("SCRATCH_BYTES_EXCEEDED")


def run_batch(request: NarrativeBatchRequest, *, project_root: Path, catalog_config_path: Path,
              db_path: Path, work_dir: Path) -> dict[str, Any]:
    """Run or resume this exact finite request; paid uncertainty stays reserved."""
    deadline = time.monotonic() + request.max_seconds
    project_root, catalog_config_path, db_path, work_dir = (
        path.resolve() for path in (project_root, catalog_config_path, db_path, work_dir))
    if not db_path.parent.is_dir():
        raise ValueError("AUTOMATION_DATABASE_PARENT_MISSING")
    _check_preparation_deadline(deadline)
    with os_file_mutex(db_path.with_name(db_path.name + ".batch-owner.lock"), timeout_seconds=0.2):
        _check_preparation_deadline(deadline)
        config = load_catalog_config(catalog_config_path, project_root=project_root)
        _check_preparation_deadline(deadline)
        catalog = SourceCatalog(config)
        try:
            return _run_owned(request, catalog, project_root, catalog_config_path, db_path, work_dir,
                              deadline=deadline)
        finally:
            catalog.close()


def _run_owned(
    request, catalog, project_root, config_path, db_path, work_dir, *, deadline
):
    _check_preparation_deadline(deadline)
    reader = SourceVersionReader(catalog)
    # This directory is dedicated to batch records/logs. It must not contain or
    # be an ancestor of raw/config/catalog/database paths being measured.
    protected = (
        project_root,
        catalog.config.catalog_dir,
        db_path,
        config_path,
    ) + tuple(root.path for root in catalog.config.roots)
    if any(
        path.resolve() == work_dir or work_dir in path.resolve().parents
        for path in protected
    ):
        raise ValueError("BATCH_WORK_DIRECTORY_OVERLAPS_STORAGE")
    if (
        work_dir.exists()
        and any(work_dir.iterdir())
        and not (work_dir / "storage-baseline.json").exists()
    ):
        raise ValueError("BATCH_WORK_DIRECTORY_NOT_EMPTY")
    # Complete pure source preparation before AUTO can initialize or migrate.
    # Reuse these facts on resume; code upgrades never re-sign persisted jobs.
    previous = (
        NarrativeRunStore(db_path).get_run(request.run_id)
        if db_path.is_file()
        else None
    )
    if previous is not None and previous.binding_json is not None:
        frozen = json.loads(previous.binding_json)
        normalization = NarrativeNormalization.from_snapshot(
            frozen.get("normalization_config"), deadline=deadline
        )
    else:
        normalization = NarrativeNormalization.from_project(
            project_root,
            enabled=any(ref.mime_type == PPTX_MIME for ref in request.sources),
            deadline=deadline,
        )
    prepared_sources = _current_sources(
        request,
        reader,
        deadline=deadline,
        normalization=normalization,
        projection_catalog=catalog,
    )
    for payload in prepared_sources[0]:
        _check_preparation_deadline(deadline)
        if payload.subject.kind == "official_json":
            continue  # The source port already verified every current parent exactly once.
        opened = reader.open_version(
            source_ref(payload),
            purpose="narrative_derivation",
            expected_read_policy_sha256=payload.expected_read_policy_sha256,
        )
        _check_preparation_deadline(deadline)
        validate_opened_source(
            source_ref(payload),
            opened,
            expected_read_policy_sha256=payload.expected_read_policy_sha256,
        )
        _check_preparation_deadline(deadline)
    _check_preparation_deadline(deadline)
    manifests = {
        payload.item_key: _item_generation(
            request, payload, normalization=normalization
        )
        for payload in prepared_sources[0]
    }
    lock_dir = catalog.config.catalog_dir / "narrative-generations"
    lock_dir.mkdir(parents=True, exist_ok=True)
    with ExitStack() as locks:
        for digest in sorted(
            {generation_sha256(value) for value in manifests.values()}
        ):
            _check_preparation_deadline(deadline)
            try:
                locks.enter_context(
                    os_file_mutex(
                        lock_dir / (digest + ".lock"),
                        timeout_seconds=max(0.001, deadline - time.monotonic()),
                    )
                )
            except FileMutexLockedError as exc:
                raise BatchResumeError("BATCH_GENERATION_BUSY") from exc
        return _run_prepared(
            request,
            catalog,
            project_root,
            config_path,
            db_path,
            work_dir,
            deadline=deadline,
            prepared_sources=prepared_sources,
            manifests=manifests,
            normalization=normalization,
        )


def _run_prepared(
    request,
    catalog,
    project_root,
    config_path,
    db_path,
    work_dir,
    *,
    deadline,
    prepared_sources,
    manifests,
    normalization,
):
    reader = SourceVersionReader(catalog)
    store = AutomationStore(db_path) if db_path.exists() else None
    runs = NarrativeRunStore(db_path) if store is not None else None
    previous = runs.get_run(request.run_id) if runs is not None else None
    versions = None
    current_jobs: tuple[Job, ...] = ()
    if previous is not None:
        binding, versions, current_jobs = _resume_binding(
            request,
            reader,
            store,
            runs,
            previous,
            deadline=deadline,
            prepared_sources=prepared_sources,
        )
        guard = _storage_guard(
            request, catalog, db_path, work_dir, binding.input_hash, read_only=True
        )
    else:
        binding = _events_from_sources(request, *prepared_sources, now=_now())
        pins = {}
        readonly_artifacts = NarrativeArtifactReader(
            catalog.config.database_path,
            LocalNarrativeObjectStore(catalog.config.catalog_dir),
        )
        try:
            facts = {
                item.get("item_key", item.get("document_id")): item
                for item in prepared_sources[1]
            }
            for payload in prepared_sources[0]:
                _check_preparation_deadline(deadline)
                document = payload.item_key
                pointer = _generation_pointer(catalog, manifests[document])
                try:
                    candidate = (
                        _find_item_reuse_pin(
                            readonly_artifacts,
                            reader,
                            payload,
                            manifests[document],
                            facts[document],
                            catalog=catalog,
                            normalization=normalization,
                        )
                        if not request.refresh or pointer.exists()
                        else None
                    )
                except ValueError as exc:
                    raise BatchResumeError("BATCH_REUSE_ARTIFACT_INVALID") from exc
                _check_preparation_deadline(deadline)
                # A visible verified publication completes the recovery locator,
                # including a crash between activate and pointer cleanup. Refresh
                # still creates its own new jobs and usage.
                if candidate is not None:
                    pointer.unlink(missing_ok=True)
                pin = None if request.refresh else candidate
                if pin is not None:
                    pins[document] = pin
                    pointer.unlink(missing_ok=True)
                else:
                    _check_generation_owner(pointer, db_path, request.run_id)
        finally:
            readonly_artifacts.close()
        binding = BatchEvents(
            binding.input_hash,
            binding.events,
            binding.source_facts,
            manifests,
            pins,
            normalization.snapshot(),
        )
        misses = len(request.work_items) - len(pins)
        if misses:
            _preflight_storage(request, source_count=misses)
        _check_preparation_deadline(deadline)
        work_dir.mkdir(parents=True, exist_ok=True)
        # Save the baseline before new AUTO initialization/materialization grows files.
        guard = _storage_guard(request, catalog, db_path, work_dir, binding.input_hash)
        if store is None:
            _check_preparation_deadline(deadline)
            store = AutomationStore(db_path)
            runs = NarrativeRunStore(db_path)
    assert store is not None and runs is not None
    gate = store.read_runtime_gate()
    if gate.desired_state is RuntimeState.ENABLED and previous is None:
        raise ValueError("AUTOMATION_RUNTIME_ALREADY_ENABLED")
    if previous is not None and (
        all(job.status in _TERMINAL for job in current_jobs)
        or (previous.blocked and _blocked_history_is_idle(store, current_jobs, gate))
    ):
        # Completed or blocked idle history is a read, not a new execution.
        # Blocked pending jobs and the original usage remain untouched.
        readonly_artifacts = NarrativeArtifactReader(
            catalog.config.database_path,
            LocalNarrativeObjectStore(catalog.config.catalog_dir),
        )
        try:
            documents = _final_documents(
                request,
                binding,
                store,
                runs,
                readonly_artifacts,
                read_only=True,
                job_ids=previous.job_ids,
                reader=reader,
                normalization=normalization,
                projection_catalog=catalog,
            )
        finally:
            readonly_artifacts.close()
        if all(
            document["status"] not in {"activation_pending", "succeeded"}
            for document in documents
        ):
            status = (
                "completed"
                if all(document["status"] == "completed" for document in documents)
                else "failed"
            )
            if any(
                job.last_error_code == "MODEL_BUDGET_DENIED" for job in current_jobs
            ):
                status = "budget_exhausted"
            if previous.blocked:
                status = _blocked_status(previous)
            return _receipt(previous.run_id, status, documents, runs, guard)
    if previous is not None and versions != _execution_versions(request):
        raise BatchResumeError("BATCH_EXECUTION_VERSION_UNAVAILABLE_NEW_RUN_REQUIRED")
    if previous is not None and store.has_running_jobs_outside_scope(previous.job_ids):
        raise ValueError("AUTOMATION_FOREIGN_WORKER_ACTIVE")
    status = "partial"
    generation = None
    supervisor = None
    try:
        if gate.desired_state is RuntimeState.ENABLED:
            # A surviving enabled gate can only be recovered by the run
            # durably recorded as its owner. Bind and fence it before AUTO
            # events/jobs can be written.
            with CatalogOperationLock(
                catalog.config.catalog_dir, operation="narrative-batch-start"
            ):
                generation = runs.activate_run(
                    request.run_id,
                    expected_generation=gate.control_generation,
                    updated_at=_now(),
                ).control_generation

        if previous is None:
            scheduler = AutomationScheduler(
                store,
                create_default_registry(),
                PolicyConfig(allow_llm=True, allow_network=True),
            )
            event_ids = {
                event.event_id
                for event in binding.events
                if event.subject_id not in binding.reused_artifact_pins
            }
            for event in binding.events:
                if event.subject_id in binding.reused_artifact_pins:
                    continue
                stored = store.get_event(event.event_id)
                if stored is None:
                    stored = store.put_event(event).value
                elif (
                    stored.input_hash,
                    stored.payload_json,
                    stored.policy_version,
                    stored.subject_id,
                ) != (
                    event.input_hash,
                    event.payload_json,
                    event.policy_version,
                    event.subject_id,
                ):
                    raise RunConflictError("batch event changed")
                scheduler.materialize_event(stored)
            scoped_jobs = store.list_jobs(event_ids=tuple(event_ids))
            job_ids = tuple(job.job_id for job in scoped_jobs)
            run = runs.create_run(
                run_id=request.run_id,
                input_hash=binding.input_hash,
                job_ids=job_ids,
                model_id=request.model_options["model_id"],
                prompt_version=NARRATIVE_PROMPT_VERSION,
                pricing_version=request.pricing_version,
                input_micro_usd_per_million_tokens=request.input_micro_usd_per_million_tokens,
                output_micro_usd_per_million_tokens=request.output_micro_usd_per_million_tokens,
                max_tokens=request.max_tokens,
                max_micro_usd=request.max_micro_usd,
                max_output_bytes=min(
                    len(request.work_items) * request.max_final_bytes,
                    request.max_persistent_bytes,
                ),
                created_at=_now(),
                binding_json=_frozen_binding(request, binding, jobs=scoped_jobs),
            )
        else:
            run = previous
        if not run.job_ids:
            readonly_artifacts = NarrativeArtifactReader(
                catalog.config.database_path,
                LocalNarrativeObjectStore(catalog.config.catalog_dir),
            )
            try:
                documents = _final_documents(
                    request,
                    binding,
                    store,
                    runs,
                    readonly_artifacts,
                    read_only=True,
                    job_ids=(),
                    reader=reader,
                    normalization=normalization,
                    projection_catalog=catalog,
                )
                try:
                    guard.check()
                except ValueError as exc:
                    if str(exc) not in {
                        "PERSISTENT_BYTES_EXCEEDED",
                        "SCRATCH_BYTES_EXCEEDED",
                    }:
                        raise
                    runs.block_run(run.run_id, error_code=str(exc), updated_at=_now())
                    return _receipt(
                        run.run_id, "storage_exhausted", documents, runs, guard
                    )
                return _receipt(run.run_id, "completed", documents, runs, guard)
            finally:
                readonly_artifacts.close()
        artifacts = NarrativeArtifactStore(
            catalog.store,
            _BudgetedObjects(
                catalog.config.catalog_dir, guard, request.max_final_bytes
            ),
        )
        for document, manifest in binding.generation_manifests.items():
            if document not in binding.reused_artifact_pins:
                _write_generation_owner(
                    _generation_pointer(catalog, manifest), db_path, run.run_id
                )
        dispatcher = NarrativeEffectDispatcher(
            store,
            artifacts,
            allowed_job_ids=run.job_ids,
            generation_manifests=binding.generation_manifests,
            projection_loader=_projection_loader(catalog),
        )
        supervisor = AutomationSupervisor(
            SupervisorConfig(
                db_path=db_path,
                log_dir=work_dir / "logs",
                profile=request.profile,
                runtime_factory_path="company_wiki.automation.narrative_worker_factory:create_runtime",
                runtime_options_json=canonical_json(
                    {
                        "project_root": str(project_root),
                        "catalog_config_path": str(config_path),
                        "run_id": run.run_id,
                        "expected_run_input_hash": run.input_hash,
                        "model": request.model_options,
                        "max_final_bytes": request.max_final_bytes,
                        "normalization_config": binding.normalization_config,
                        "normalization_parsers": _normalization_parsers(
                            binding, versions or _execution_versions(request)
                        ),
                        "normalization_deadline": deadline,
                    }
                ),
                compute_job_types=(
                    "source.narrative_select",
                    "source.narrative_verify",
                ),
                model_job_types=("source.narrative_summarize",),
                allowed_job_ids=run.job_ids,
                heartbeat_interval_seconds=1,
                lease_seconds=15,
                idle_sleep_seconds=0.05,
                maintenance_interval_seconds=0.05,
                stop_grace_seconds=2,
                child_log_max_bytes=262144,
            )
        )
        if generation is None:
            with CatalogOperationLock(
                catalog.config.catalog_dir, operation="narrative-batch-start"
            ):
                current = store.read_runtime_gate()
                generation = runs.activate_run(
                    request.run_id,
                    expected_generation=current.control_generation,
                    updated_at=_now(),
                ).control_generation
        terminal = _TERMINAL
        current_jobs = store.list_jobs(job_ids=run.job_ids)
        if len(current_jobs) != len(run.job_ids):
            raise RunConflictError("batch run job disappeared")
        needs_workers = any(job.status not in terminal for job in current_jobs)
        if not run.blocked and needs_workers and time.monotonic() < deadline:
            supervisor.start()
        while time.monotonic() < deadline:
            current_gate = store.read_runtime_gate()
            if (
                current_gate.desired_state is not RuntimeState.ENABLED
                or current_gate.control_generation != generation
            ):
                status = "paused"
                break
            guard.check()
            if not run.blocked:
                supervisor.maintain()
                # Finished model attempts with no provider receipt may have
                # reached the provider. Reconcile their reserved bounds as
                # unknown without refunding them; repeat calls are idempotent.
                runs.settle_finished_attempt_reservations(
                    run_id=run.run_id, settled_at=_now()
                )
            # Do not prepare a file larger than the requested final byte cap.
            for effect_id in store.effect_ids_for_jobs(
                run.job_ids, effect_type=EFFECT_TYPE
            ):
                effect = store.get_effect(effect_id)
                if effect is None:
                    raise RunConflictError("batch effect disappeared")
                if effect.status.value in {"planned", "pending"}:
                    if (
                        len(
                            canonical_json(
                                store.result_for_effect(effect_id).to_dict()["result"]
                            ).encode("utf-8")
                        )
                        > request.max_final_bytes
                    ):
                        raise ValueError("FINAL_BYTES_EXCEEDED")
            now = _now()
            dispatcher.dispatch_next(
                worker_id="narrative-batch-projector",
                now=now,
                lease_until=(
                    datetime.now(timezone.utc) + timedelta(seconds=30)
                ).strftime("%Y-%m-%dT%H:%M:%SZ"),
                expected_generation=generation,
            )
            dispatcher.reconcile_prepared(activated_at=now)
            jobs = store.list_jobs(job_ids=run.job_ids)
            if len(jobs) != len(run.job_ids):
                raise RunConflictError("batch run job disappeared")
            current_run = runs.get_run(run.run_id)
            if current_run is None:
                raise RunConflictError("batch run disappeared")
            # The ledger's hard limit is independent of whether maintenance
            # has already terminalized dependent jobs after a model failure.
            if current_run.blocked:
                status = _blocked_status(current_run)
                break
            if all(job.status in terminal for job in jobs):
                status = (
                    "completed"
                    if all(job.status is JobStatus.SUCCEEDED for job in jobs)
                    else "failed"
                )
                if any(job.last_error_code == "MODEL_BUDGET_DENIED" for job in jobs):
                    status = "budget_exhausted"
                break
            time.sleep(0.05)
    except KeyboardInterrupt:
        status = "paused"
    except ValueError as exc:
        if str(exc) not in {
            "PERSISTENT_BYTES_EXCEEDED",
            "SCRATCH_BYTES_EXCEEDED",
            "FINAL_BYTES_EXCEEDED",
        }:
            raise
        runs.block_run(run.run_id, error_code=str(exc), updated_at=_now())
        status = "storage_exhausted"
    finally:
        if supervisor is not None:
            supervisor.stop()
        if generation is not None:
            with CatalogOperationLock(
                catalog.config.catalog_dir, operation="narrative-batch-stop"
            ):
                current = store.read_runtime_gate()
                if current.control_generation == generation:
                    store.set_runtime_gate(
                        RuntimeState.PAUSED,
                        updated_at=_now(),
                        expected_generation=generation,
                    )
    documents = _final_documents(
        request,
        binding,
        store,
        runs,
        artifacts,
        job_ids=run.job_ids,
        reader=reader,
        normalization=normalization,
        projection_catalog=catalog,
    )
    for document in documents:
        manifest = binding.generation_manifests.get(
            document.get("item_key", document.get("document_id"))
        )
        if manifest is not None:
            pointer = _generation_pointer(catalog, manifest)
            if document["status"] == "completed" or _generation_owner_finished(
                db_path, run.run_id
            ):
                pointer.unlink(missing_ok=True)
    if status == "completed" and any(
        document["status"] != "completed" for document in documents
    ):
        status = "partial"
    return _receipt(run.run_id, status, documents, runs, guard)


def _normalization_parsers(binding, versions):
    """Pass every native format's recorded parser to its owning Worker."""
    from .narrative_formats import NORMALIZED_MIME_TYPES

    parsers = {}
    for event in binding.events:
        payload = SourceRevisionEventPayload.from_dict(json.loads(event.payload_json))
        if (
            payload.source_metadata.source_class != "filing"
            or payload.source_ref.mime_type not in NORMALIZED_MIME_TYPES
        ):
            continue
        manifest = binding.generation_manifests.get(event.subject_id)
        parsers[event.subject_id] = (manifest["parser_component"]["version"] if manifest else
            versions.get("document_normalization", "1.0.0"))
    return parsers


def _generation_pointer(catalog, manifest):
    return catalog.config.catalog_dir / "narrative-generations" / (generation_sha256(manifest) + ".json")


def _generation_owner_finished(db_path, run_id):
    """Read existing AUTO facts; only known settled terminal work can be released."""
    from . import migrations
    if not db_path.is_file():
        return False
    runs = NarrativeRunStore(db_path)
    run = runs.get_run(run_id)
    if run is None:
        return False
    if any(item.usage_status != "known" for item in runs.reservations_for_run(run_id)):
        return False
    connection = migrations._open_readonly_connection(db_path)
    try:
        rows = connection.execute("""SELECT j.status FROM jobs j JOIN narrative_run_jobs r
            ON r.job_id=j.job_id WHERE r.run_id=?""", (run_id,)).fetchall()
        if len(rows) != len(run.job_ids) or any(JobStatus(row[0]) not in _TERMINAL for row in rows):
            return False
        pending = connection.execute("""SELECT 1 FROM effects e JOIN narrative_run_jobs r
            ON r.job_id=e.job_id WHERE r.run_id=? AND e.status IN ('planned','pending','verified') LIMIT 1""",
            (run_id,)).fetchone()
        return pending is None
    finally:
        connection.close()


def _check_generation_owner(pointer, db_path, run_id):
    if not pointer.exists():
        return
    try:
        owner = json.loads(pointer.read_text(encoding="utf-8"))
        if set(owner) != {"schema_version", "automation_db", "run_id"} or owner["schema_version"] != "narrative-generation-recovery/1":
            raise ValueError("invalid recovery pointer")
        origin_db = Path(owner["automation_db"])
        if origin_db.resolve() == db_path.resolve() and owner["run_id"] == run_id:
            return
        if _generation_owner_finished(origin_db, owner["run_id"]):
            pointer.unlink()
            return
    except (OSError, KeyError, TypeError, ValueError, NarrativeRunError):
        raise BatchResumeError("BATCH_GENERATION_RECOVERY_REQUIRED") from None
    raise BatchResumeError("BATCH_GENERATION_RECOVERY_REQUIRED")


def _write_generation_owner(pointer, db_path, run_id):
    import os
    temporary = pointer.with_suffix(".partial")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            stream.write(canonical_json({"schema_version": "narrative-generation-recovery/1",
                "automation_db": str(db_path), "run_id": run_id}))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, pointer)
    finally:
        temporary.unlink(missing_ok=True)


def _blocked_status(run) -> str:
    return (
        "storage_exhausted"
        if run.block_reason in {
            "PERSISTENT_BYTES_EXCEEDED", "SCRATCH_BYTES_EXCEEDED", "FINAL_BYTES_EXCEEDED",
        }
        else "budget_exhausted"
    )


def _blocked_history_is_idle(
    store: AutomationStore, jobs: tuple[Job, ...], gate: RuntimeGate,
) -> bool:
    """Read blocked history only when execution and delivery are quiescent.

    A paused gate fences new claims. Unfinished attempts (even expired) and
    unpublished effects retain the normal recovery path. Bounded outbox reads
    use the actual effect/job foreign key: another run cannot reactivate this
    blocked history, and opaque outbox identities need no derived naming.
    """
    if gate.desired_state is not RuntimeState.PAUSED:
        return False
    for job in jobs:
        if job.status in {JobStatus.LEASED, JobStatus.RUNNING, JobStatus.VERIFYING}:
            return False
        if any(attempt.finished_at is None for attempt in store.list_attempts(job.job_id)):
            return False
        if any(
            effect.status not in {EffectStatus.VERIFIED, EffectStatus.FAILED, EffectStatus.CANCELLED}
            for effect in store.list_effects(job.job_id)
        ):
            return False
    return not any(
        store.list_outbox_entries(status=status, limit=1, allowed_job_ids=tuple(job.job_id for job in jobs))
        for status in ("pending", "leased", "failed")
    )


def _receipt(run_id, status, documents, runs, guard):
    budget = runs.budget_snapshot(run_id)
    storage = guard.snapshot()
    return {
        "schema_version": "narrative-batch-result/2"
        if any("item_key" in item for item in documents)
        else "narrative-batch-result/1",
        "run_id": run_id,
        "status": status,
        **(
            {"items": documents}
            if any("item_key" in item for item in documents)
            else {"documents": documents}
        ),
        "budget": {
            "tokens": budget.charged_tokens,
            "estimated_micro_usd": budget.charged_micro_usd,
            "unknown_reservations": budget.unknown_reservations,
            "unsettled_reservations": budget.unsettled_reservations,
        },
        "storage": {
            "persistent_added_bytes": storage.persistent_added_bytes,
            "scratch_peak_bytes": storage.scratch_peak_bytes,
        },
    }



def _attempt_model_diagnostics(store, reservations, summary_job):
    """Read optional observed meters; old receipts keep their original shape."""
    observations = []
    for attempt in store.list_attempts(summary_job.job_id):
        raw = attempt.result_json
        if raw is None or not any(field in raw for field in ('"reasoning_tokens":', '"usage_diagnostic":', '"failed_final":')):
            continue
        try:
            parsed = HandlerResult.from_dict(json.loads(raw))
            metrics = parsed.metrics
            failed = parsed.result.get("failed_final")
            diagnostic = FailedFinalDiagnostic.from_dict(failed).to_dict() if failed is not None else None
            if metrics.reasoning_tokens is None and metrics.usage_diagnostic is None and diagnostic is None:
                continue
            reservation = reservations.get(attempt.attempt_id)
            observation: dict[str, Any] = {
                "attempt_id": attempt.attempt_id,
                "usage_status": reservation.usage_status if reservation else "unknown",
                "input_tokens": reservation.input_tokens if reservation else None,
                "output_tokens": reservation.output_tokens if reservation else None,
                "reasoning_tokens": metrics.reasoning_tokens,
                "usage_diagnostic": metrics.usage_diagnostic,
            }
            if diagnostic is not None:
                observation["failed_final"] = diagnostic
            observations.append(observation)
        except (KeyError, TypeError, ValueError):
            # Optional diagnostics never change the original job/fee outcome.
            observations.append({"attempt_id": attempt.attempt_id,
                                 "diagnostic_status": "stored_observation_unreadable"})
    return observations


def _item_result(request, payload, document):
    if request.schema_version == "narrative-batch-request/1":
        return document
    result = {
        k: v
        for k, v in document.items()
        if k not in {"document_id", "item_key", "kind"}
    }
    pin = result.get("artifact_ref")
    if pin is not None and payload.subject.kind == "raw":
        result["artifact_ref"] = {
            "schema_version": "narrative-ref/1",
            "artifact_version_id": pin["artifact_version_id"],
            "artifact_sha256": pin["content_sha256"],
            "byte_size": pin["byte_size"],
            "source_ref": payload.source_ref.to_dict(),
        }
    return {"item_key": payload.item_key, "kind": payload.subject.kind, **result}


def _final_documents(
    request,
    binding,
    store,
    runs,
    artifacts,
    *,
    read_only=False,
    job_ids=None,
    reader=None,
    normalization=None,
    projection_catalog=None,
):
    documents = []
    reservations = {
        item.attempt_id: item for item in runs.reservations_for_run(request.run_id)
    }
    all_jobs = store.list_jobs(
        job_ids=job_ids, event_ids=tuple(event.event_id for event in binding.events)
    )
    facts = {
        item.get("item_key", item.get("document_id")): item
        for item in binding.source_facts
    }
    for event in binding.events:
        payload = SourceRevisionEventPayload.from_dict(json.loads(event.payload_json))
        ref = payload.source_ref
        key = payload.item_key
        projected = payload.subject.kind == "official_json"
        manifest = binding.generation_manifests.get(key)
        pin = binding.reused_artifact_pins.get(key)
        if pin is not None:
            if reader is None:
                raise BatchResumeError("BATCH_REUSE_ARTIFACT_INVALID")
            valid = (
                _read_projected_pin(
                    artifacts,
                    reader,
                    payload,
                    pin,
                    manifest,
                    catalog=projection_catalog,
                )
                if projected
                else read_reuse_pin(
                    artifacts,
                    reader,
                    payload,
                    pin,
                    facts[key],
                    manifest,
                    normalization=normalization,
                )
            )
            if not valid:
                raise BatchResumeError("BATCH_REUSE_ARTIFACT_INVALID")
            documents.append(
                _item_result(
                    request,
                    payload,
                    {
                        "document_id": key,
                        "status": "completed",
                        "artifact_ref": pin,
                        "errors": [],
                        "generation_status": "reused",
                    },
                )
            )
            continue
        jobs = tuple(
            job for job in all_jobs if job.created_from_event_id == event.event_id
        )
        verify = next(job for job in jobs if job.job_type == "source.narrative_verify")
        effect_ids = store.effect_ids_for_jobs(
            (verify.job_id,), effect_type=EFFECT_TYPE
        )
        artifact_ref = None
        document_status = verify.status.value
        if verify.status is JobStatus.SUCCEEDED and effect_ids:
            try:
                version = artifacts.visible_version_for_effect(effect_ids[0])
                if projected:
                    if manifest is None:
                        raise BatchResumeError("BATCH_FROZEN_BINDING_INVALID")
                    digest = generation_sha256(manifest)
                    artifacts.read_current_subject(
                        artifact_version_id=version.artifact_version_id,
                        subject=payload.subject,
                        generation_sha256=digest,
                        expected_sha256=version.content_sha256,
                        expected_size=version.byte_size,
                    )
                    artifact_ref = {
                        "schema_version": "narrative-ref/2",
                        "artifact_version_id": version.artifact_version_id,
                        "artifact_sha256": version.content_sha256,
                        "byte_size": version.byte_size,
                        "subject_binding": payload.subject.to_dict(),
                        "generation_sha256": digest,
                    }
                    if read_only and (
                        reader is None
                        or not _read_projected_pin(
                            artifacts,
                            reader,
                            payload,
                            artifact_ref,
                            manifest,
                            catalog=projection_catalog,
                        )
                    ):
                        raise BatchResumeError("BATCH_REUSE_ARTIFACT_INVALID")
                else:
                    artifacts.read_exact(
                        artifact_version_id=version.artifact_version_id,
                        document_id=ref.document_id,
                        source_id=ref.source_id,
                        source_sha256=ref.content_sha256,
                        expected_sha256=version.content_sha256,
                        expected_size=version.byte_size,
                    )
                    artifact_ref = {
                        "artifact_version_id": version.artifact_version_id,
                        "content_sha256": version.content_sha256,
                        "byte_size": version.byte_size,
                        "document_id": ref.document_id,
                        "source_id": ref.source_id,
                        "source_sha256": ref.content_sha256,
                    }
                document_status = "completed"
                if not read_only:
                    summary = next(
                        job
                        for job in jobs
                        if job.job_type == "source.narrative_summarize"
                    )
                    for reservation in runs.reservations_for_run(request.run_id):
                        if (
                            reservation.job_id == summary.job_id
                            and reservation.error_code is None
                        ):
                            runs.settle_output(
                                run_id=request.run_id,
                                attempt_id=reservation.attempt_id,
                                output_bytes=version.byte_size,
                                output_sha256=version.content_sha256,
                                settled_at=_now(),
                            )
                    final_pin = FinalArtifactPin(
                        version.effect_id,
                        version.artifact_version_id,
                        version.content_sha256,
                        version.byte_size,
                        ref.document_id,
                        ref.source_id,
                        ref.content_sha256,
                        **(
                            {
                                "subject_binding": payload.subject,
                                "generation_sha256": digest,
                            }
                            if projected
                            else {}
                        ),
                    )
                    compact_terminal_narrative_jobs(
                        store,
                        artifacts,
                        job_ids=tuple(job.job_id for job in jobs),
                        final_artifact=final_pin,
                        compacted_at=_now(),
                        **(
                            {
                                "projection_loader": _projection_loader(
                                    projection_catalog
                                )
                            }
                            if projected
                            else {}
                        ),
                    )
            except NarrativeArtifactNotVisibleError:
                document_status = "activation_pending"
        document = {
            "document_id": key,
            "status": document_status,
            "artifact_ref": artifact_ref,
            "errors": [job.last_error_code for job in jobs if job.last_error_code],
        }
        summary_job = next(
            job for job in jobs if job.job_type == "source.narrative_summarize"
        )
        observations = _attempt_model_diagnostics(store, reservations, summary_job)
        if observations:
            document["model_diagnostics"] = observations
        documents.append(_item_result(request, payload, document))
    return documents


__all__ = ["BatchEvents", "BatchStorageBudget", "StorageSnapshot", "build_batch_events", "run_batch"]
