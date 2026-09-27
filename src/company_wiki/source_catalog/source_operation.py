"""Facade for validated, pathless acquisition operation results."""

from __future__ import annotations

from typing import Any

from .operation_contract import (
    SourceOperationProjectionError,
    parse_operation_payload,
)
from .operation_projection import (
    OPERATION_SCHEMA_VERSION,
    VersionReader,
    project_source_operation,
)


def project_operation_result(
    payload: dict[str, Any],
    *,
    operation: str,
    reader: VersionReader,
) -> dict[str, Any]:
    """Validate one producer result, then expose the pathless consumer DTO."""
    operation_input = parse_operation_payload(payload, operation=operation)
    return project_source_operation(operation_input, reader=reader)


__all__ = [
    "OPERATION_SCHEMA_VERSION",
    "SourceOperationProjectionError",
    "project_operation_result",
]
