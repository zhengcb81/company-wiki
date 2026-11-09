"""Public bounded subprocess interface used by parser and automation owners."""

from ._bounded_process import (
    MAX_JSON_OUTPUT_BYTES,
    ChildFailed,
    ChildTimeout,
    OutputLimitExceeded,
    TransportError,
    _WINDOWS_BOOTSTRAP,
    run_bounded,
    run_bounded_json,
    run_json_process,
)

WINDOWS_WAIT_BOOTSTRAP = _WINDOWS_BOOTSTRAP

__all__ = [
    "MAX_JSON_OUTPUT_BYTES",
    "ChildFailed",
    "ChildTimeout",
    "OutputLimitExceeded",
    "TransportError",
    "WINDOWS_WAIT_BOOTSTRAP",
    "run_bounded",
    "run_bounded_json",
    "run_json_process",
]
