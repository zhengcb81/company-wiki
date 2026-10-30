"""Finite model-protocol dispatch; legacy implementations retain their identity."""
from __future__ import annotations

from . import narrative_model as legacy
from . import narrative_model_scoped as scoped
from . import narrative_model_extractive as extractive
from .narrative_summary_protocols import SCOPED_PROTOCOLS, scoped_protocol_for_projection


# Protocols that may use paid model tokens must preserve the complete provider
# response so restart recovery can replay it locally without another POST.
DURABLE_PAID_RESPONSE_PROJECTIONS = frozenset({
    *(protocol.projection for protocol in SCOPED_PROTOCOLS),
    scoped.SCOPED_MODEL_PROJECTION_VERSION,
    extractive.EXTRACTIVE_MODEL_PROJECTION_VERSION,
})


def supports_durable_paid_response(version):
    return version in DURABLE_PAID_RESPONSE_PROJECTIONS


def resolve_model_boundary(version, *, projected=False):
    protocol = scoped_protocol_for_projection(version)
    if protocol is not None:
        if type(projected) is not bool:
            raise legacy.ModelResponseError('MODEL_BOUNDARY_PROJECTED_INVALID')
        return legacy.ModelBoundary(version,protocol.prompt,protocol.request_schema,
                                    protocol.decoder,True)
    if version == extractive.EXTRACTIVE_MODEL_PROJECTION_VERSION:
        if type(projected) is not bool:
            raise legacy.ModelResponseError('MODEL_BOUNDARY_PROJECTED_INVALID')
        return legacy.ModelBoundary(version, extractive.EXTRACTIVE_PROMPT_VERSION,
            extractive.EXTRACTIVE_REQUEST_SCHEMA, 'reading-source-extractive-decoder/5', True)
    return legacy.resolve_model_boundary(version, projected=projected)


def reading_model_boundary_identity(version, *, projected=False):
    protocol = scoped_protocol_for_projection(version)
    if protocol is not None:
        return scoped.scoped_boundary_identity(resolve_model_boundary(version,projected=projected),
                                               protocol=protocol)
    if version == extractive.EXTRACTIVE_MODEL_PROJECTION_VERSION:
        return extractive.extractive_boundary_identity(resolve_model_boundary(version, projected=projected))
    return legacy.reading_model_boundary_identity(version, projected=projected)


def build_model_request(selected, *, reading_projection_version=None,
                        only_tasks=None, target_claims=None):
    protocol = scoped_protocol_for_projection(reading_projection_version)
    if protocol is not None:
        return scoped.build_scoped_request(selected,only_tasks=only_tasks,target_claims=target_claims,
                                           protocol=protocol)
    if reading_projection_version == extractive.EXTRACTIVE_MODEL_PROJECTION_VERSION:
        if only_tasks is not None or target_claims is not None:
            raise legacy.ModelResponseError('MODEL_REQUEST_INVALID')
        return extractive.build_extractive_request(selected)
    if only_tasks is not None or target_claims is not None:
        raise legacy.ModelResponseError('MODEL_REQUEST_INVALID')
    return legacy.NarrativeModelRequest.from_selection(
        selected, reading_projection_version=reading_projection_version)


def decode_model_draft(response, *, selected, reading_projection_version=None):
    protocol = scoped_protocol_for_projection(reading_projection_version)
    if protocol is not None:
        return scoped.decode_scoped_draft(response,selected=selected,protocol=protocol)
    if reading_projection_version == extractive.EXTRACTIVE_MODEL_PROJECTION_VERSION:
        return extractive.decode_extractive_result(response, selected=selected).draft
    return legacy.decode_model_draft(response, selected=selected,
                                     reading_projection_version=reading_projection_version)
