"""Finite model-protocol dispatch; legacy implementations retain their identity."""
from __future__ import annotations

from . import narrative_model as legacy
from . import narrative_model_scoped as scoped
from . import narrative_model_extractive as extractive


# Protocols that may use paid model tokens must preserve the complete provider
# response so restart recovery can replay it locally without another POST.
DURABLE_PAID_RESPONSE_PROJECTIONS = frozenset({
    scoped.SCOPED_MODEL_PROJECTION_VERSION,
    extractive.EXTRACTIVE_MODEL_PROJECTION_VERSION,
})


def supports_durable_paid_response(version):
    return version in DURABLE_PAID_RESPONSE_PROJECTIONS


def resolve_model_boundary(version, *, projected=False):
    if version == extractive.EXTRACTIVE_MODEL_PROJECTION_VERSION:
        if type(projected) is not bool:
            raise legacy.ModelResponseError('MODEL_BOUNDARY_PROJECTED_INVALID')
        return legacy.ModelBoundary(version, extractive.EXTRACTIVE_PROMPT_VERSION,
            extractive.EXTRACTIVE_REQUEST_SCHEMA, 'reading-source-extractive-decoder/5', True)
    if version == scoped.SCOPED_MODEL_PROJECTION_VERSION:
        if type(projected) is not bool:
            raise legacy.ModelResponseError('MODEL_BOUNDARY_PROJECTED_INVALID')
        return legacy.ModelBoundary(version, scoped.SCOPED_PROMPT_VERSION,
            scoped.SCOPED_REQUEST_SCHEMA, 'reading-scoped-task-decoder/4', True)
    return legacy.resolve_model_boundary(version, projected=projected)


def reading_model_boundary_identity(version, *, projected=False):
    if version == extractive.EXTRACTIVE_MODEL_PROJECTION_VERSION:
        return extractive.extractive_boundary_identity(resolve_model_boundary(version, projected=projected))
    if version == scoped.SCOPED_MODEL_PROJECTION_VERSION:
        boundary = resolve_model_boundary(version, projected=projected)
        return scoped.scoped_boundary_identity(boundary)
    return legacy.reading_model_boundary_identity(version, projected=projected)


def build_model_request(selected, *, reading_projection_version=None,
                        only_tasks=None, target_claims=None):
    if reading_projection_version == extractive.EXTRACTIVE_MODEL_PROJECTION_VERSION:
        if only_tasks is not None or target_claims is not None:
            raise legacy.ModelResponseError('MODEL_REQUEST_INVALID')
        return extractive.build_extractive_request(selected)
    if reading_projection_version == scoped.SCOPED_MODEL_PROJECTION_VERSION:
        return scoped.build_scoped_request(selected, only_tasks=only_tasks,
                                           target_claims=target_claims)
    if only_tasks is not None or target_claims is not None:
        raise legacy.ModelResponseError('MODEL_REQUEST_INVALID')
    return legacy.NarrativeModelRequest.from_selection(
        selected, reading_projection_version=reading_projection_version)


def decode_model_draft(response, *, selected, reading_projection_version=None):
    if reading_projection_version == extractive.EXTRACTIVE_MODEL_PROJECTION_VERSION:
        return extractive.decode_extractive_result(response, selected=selected).draft
    if reading_projection_version == scoped.SCOPED_MODEL_PROJECTION_VERSION:
        return scoped.decode_scoped_draft(response, selected=selected)
    return legacy.decode_model_draft(response, selected=selected,
                                     reading_projection_version=reading_projection_version)
