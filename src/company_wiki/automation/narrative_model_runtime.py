"""Finite model-protocol dispatch; legacy implementations retain their identity."""
from __future__ import annotations

from . import narrative_model as legacy
from . import narrative_model_scoped as scoped


def resolve_model_boundary(version, *, projected=False):
    if version == scoped.SCOPED_MODEL_PROJECTION_VERSION:
        if type(projected) is not bool:
            raise legacy.ModelResponseError('MODEL_BOUNDARY_PROJECTED_INVALID')
        return legacy.ModelBoundary(version, scoped.SCOPED_PROMPT_VERSION,
            scoped.SCOPED_REQUEST_SCHEMA, 'reading-scoped-task-decoder/4', True)
    return legacy.resolve_model_boundary(version, projected=projected)


def reading_model_boundary_identity(version, *, projected=False):
    if version == scoped.SCOPED_MODEL_PROJECTION_VERSION:
        boundary = resolve_model_boundary(version, projected=projected)
        return scoped.scoped_boundary_identity(boundary)
    return legacy.reading_model_boundary_identity(version, projected=projected)


def build_model_request(selected, *, reading_projection_version=None):
    if reading_projection_version == scoped.SCOPED_MODEL_PROJECTION_VERSION:
        return scoped.build_scoped_request(selected)
    return legacy.NarrativeModelRequest.from_selection(
        selected, reading_projection_version=reading_projection_version)


def decode_model_draft(response, *, selected, reading_projection_version=None):
    if reading_projection_version == scoped.SCOPED_MODEL_PROJECTION_VERSION:
        return scoped.decode_scoped_draft(response, selected=selected)
    return legacy.decode_model_draft(response, selected=selected,
                                     reading_projection_version=reading_projection_version)
