"""Test-side exact request preflight; the native store owns all charges."""
from __future__ import annotations

import hashlib
import json

from company_wiki.automation.narrative_http_model import NarrativeHTTPModel
from company_wiki.automation.narrative_model import NarrativeModelRequest


def request_preflight(model: NarrativeHTTPModel, request: NarrativeModelRequest) -> tuple[bytes, dict]:
    """Serialize the same configured wire body without opening a connection.

    The conservative reservation bound is identical to the native caller's
    byte bound, including the configured output budget. It is not token usage.
    """
    body = model.request_bytes(request)
    envelope = json.loads(body)
    material = json.loads(envelope['messages'][1]['content'])
    return body, {
        'http_body_sha256': hashlib.sha256(body).hexdigest(),
        'http_body_bytes': len(body),
        'model_input_sha256': request.input_sha256,
        'model_request_schema': material['schema_version'],
        'prompt_version': request.prompt_version,
        'model_id': envelope['model'],
        'output_token_field': model.output_token_field,
        'max_output_tokens': envelope[model.output_token_field],
        'conservative_token_bound': len(body) + 128 + model.max_output_tokens,
    }


def configured_preview(spec: dict, raw_request: dict) -> tuple[bytes, dict]:
    """Pure production selection/request composition, explicitly non-native.

    The in-memory handler context has no Store, claim, fee or real lease. The
    source reader and production selector still validate the actual original.
    No AUTO database, generation owner, artifact or selected text is persisted.
    """
    from datetime import UTC, datetime
    from pathlib import Path
    import time

    from scripts.config import Config
    from company_wiki.source_catalog import SourceCatalog
    from company_wiki.source_catalog.config import load_catalog_config
    from company_wiki.source_catalog.source_reader import SourceVersionReader
    from company_wiki.source_catalog.narrative_normalization import NarrativeNormalization, PPTX_MIME
    from company_wiki.automation.narrative_batch import build_batch_events
    from company_wiki.automation.narrative_batch_request import NarrativeBatchRequest
    from company_wiki.automation.narrative_http_model import model_options_from_config
    from company_wiki.automation.narrative_select import NarrativeSelectHandler
    from company_wiki.automation.narrative_contracts import NarrativeSelectResult, SourceRevisionEventPayload
    from company_wiki.automation.narrative_model_runtime import build_model_request
    from company_wiki.automation.execution_context import JobExecutionContext
    from company_wiki.automation.models import Attempt, HandlerOutcome
    from company_wiki.automation.planner import plan_jobs
    from company_wiki.automation.policy import PolicyConfig
    from company_wiki.automation.registry import create_default_registry
    from company_wiki.automation.scheduler import materialize_plan

    options = model_options_from_config(Config.load(Path(spec['llm_config']),
        llm_provider=spec['llm_provider'], validation_scope='llm').llm)
    if spec.get('allow_local_model_http'):
        options['allow_local_http'] = True
    request = NarrativeBatchRequest.from_dict({**raw_request, 'model': options})
    deadline = time.monotonic() + request.max_seconds

    def checkpoint():
        if time.monotonic() >= deadline:
            raise ValueError('HOLDOUT_PREFLIGHT_DEADLINE_EXCEEDED')

    project = Path(spec['project_root'])
    normalization = NarrativeNormalization.from_project(project,
        enabled=any(ref.mime_type == PPTX_MIME for ref in request.sources), deadline=deadline)
    catalog = SourceCatalog(load_catalog_config(Path(spec['catalog_config']), project_root=project))
    try:
        reader = SourceVersionReader(catalog)
        now = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
        binding = build_batch_events(request, reader, now=now, deadline=deadline, normalization=normalization)
        if len(binding.events) != 1:
            raise ValueError('HOLDOUT_PREFLIGHT_EXPECTS_ONE_SOURCE')
        event = binding.events[0]
        # materialize_plan is the existing pure DTO builder, not Store
        # materialization: nothing is put, claimed or signed as native work.
        dag = materialize_plan(event, plan_jobs(event, create_default_registry(),
            PolicyConfig(allow_llm=True, allow_network=True)))
        job = next(item for item in dag.jobs if item.job_type == 'source.narrative_select')
        attempt = Attempt(attempt_id='preview-non-native', job_id=job.job_id, attempt_no=1,
            worker_id='preview-non-native', lease_token='preview-not-a-lease', lease_until=now,
            started_at=now, heartbeat_at=now, finished_at=None, outcome=None,
            result_json=None, error_code=None, error_detail=None, runtime_generation=0)
        payload = json.loads(event.payload_json)
        context = JobExecutionContext(job, attempt, event, payload, {},
            SourceRevisionEventPayload.from_dict(payload), checkpoint)
        selected = NarrativeSelectHandler(reader=reader, selector_version=request.selector_version,
            normalization=NarrativeNormalization.from_snapshot(normalization.snapshot(), deadline=deadline),
            projection_catalog=catalog)(context)
        if selected.outcome is not HandlerOutcome.SUCCEEDED:
            raise ValueError('HOLDOUT_PREFLIGHT_SELECT_' + (selected.error.code if selected.error else 'FAILED'))
        model_request = build_model_request(NarrativeSelectResult.from_dict(selected.result),
            reading_projection_version=request.reading_model_projection)
        body, facts = request_preflight(NarrativeHTTPModel(**options), model_request)
        facts.update(preview_kind='non-native', selector_version=request.selector_version,
            reading_model_projection=request.reading_model_projection,
            normalization_snapshot_sha256=hashlib.sha256(json.dumps(normalization.snapshot(),
                sort_keys=True).encode()).hexdigest())
        return body, facts
    finally:
        catalog.close()
