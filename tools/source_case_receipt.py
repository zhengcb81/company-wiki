"""Lossless JSON receipts; diagnostic volume is never execution permission."""
from __future__ import annotations

import json


def _json(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def encode_source_receipt(record: dict) -> bytes:
    """Keep the full observation, or report a genuine serialization failure.

    No byte/count/depth cap and no silent trace or source excerpt removal.
    The source operation's configured resource limits belong to its owner.
    """
    try:
        if not isinstance(record, dict):
            raise TypeError("receipt must be a mapping")
        return _json(record)
    except (TypeError, ValueError, RecursionError, UnicodeError) as error:
        # A malformed diagnostic must not erase the independently serializable
        # checkpoints. Do not stringify arbitrary objects or exception bodies.
        checkpoints, missing = {}, []
        source_status = None
        if isinstance(record, dict):
            for key, value in record.items():
                try:
                    _json({key: value})
                except (TypeError, ValueError, RecursionError, UnicodeError):
                    if isinstance(key, str):
                        missing.append(key.encode("utf-8", "backslashreplace").decode("utf-8"))
                    continue
                checkpoints[key] = value
            source_status = checkpoints.pop("status", None)
        return _json({
            "status": "OBSERVATION_INCOMPLETE", "source_status": source_status,
            "encoding_error": {"code": "encoding_error", "type": type(error).__name__},
            "integrity_checkpoints": checkpoints, "unretained_fields": missing,
        })
