"""Project a bound native diagnostic into the small facts Codex triage can use."""

from __future__ import annotations

import builtins
from collections.abc import Iterable
from errno import errorcode
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from stat import S_ISREG

from .observations import decode_observation, unique_fields

_NATIVE_DETAILS = re.compile(r"feedback-[0-9a-f]{32}\.diagnostic\.json")
_EXCEPTION_TYPES = {
    name: value for name, value in vars(builtins).items()
    if isinstance(value, type) and issubclass(value, BaseException) and value.__name__ == name
}


def _read_candidate(path: Path) -> bytes | None:
    try:
        original = path.lstat()
    except FileNotFoundError:
        return None
    if not S_ISREG(original.st_mode) or path.resolve(strict=True) != path:
        raise ValueError("native diagnostic must be a regular file directly in the inbox")
    with path.open("rb") as stream:
        if not os.path.samestat(original, os.fstat(stream.fileno())):
            raise ValueError("native diagnostic changed before reading")
        return stream.read()


def _exceptions(value: list) -> list[dict]:
    facts = []
    for exception in value:
        if not isinstance(exception, dict) or not isinstance(name := exception.get("type"), str):
            continue
        exception_type = _EXCEPTION_TYPES.get(name)
        if exception_type is None:
            continue
        fact = {"type": name}
        errno = exception.get("errno")
        if issubclass(exception_type, OSError) and type(errno) is int and errno in errorcode:
            fact["errno"] = errno
        facts.append(fact)
    return facts


def native_diagnostic_facts(observation: dict, origin: str, roots: Iterable[Path]) -> dict:
    """Use only an unambiguous copy owned by the observation's publisher."""
    reference = observation.get("details_ref")
    unavailable = {"status": "unavailable"}
    if not isinstance(reference, str) or not _NATIVE_DETAILS.fullmatch(reference):
        return unavailable
    identity = {"owner": origin, **{key: observation.get(key) for key in ("run_id", "attempt_id", "step_id")}}
    if not all(isinstance(value, str) and value for value in identity.values()):
        return unavailable
    packet_name = reference.removesuffix(".diagnostic.json") + ".jsonl"
    seen = set()
    original = None
    try:
        for root in roots:
            try:
                directory = root.resolve(strict=True)
            except FileNotFoundError:
                continue
            if directory in seen:
                continue
            seen.add(directory)
            raw = _read_candidate(directory / reference)
            if raw is None:
                continue
            # A supervised stream lacks this one-to-one packet. Its diagnostic
            # remains at the owner, available through the existing local route.
            packet = _read_candidate(directory / packet_name)
            if packet is None or decode_observation(packet) != observation:
                return unavailable
            if original is not None and raw != original:
                return unavailable
            original = raw
        if original is None:
            return unavailable
        diagnostic = json.loads(original, object_pairs_hook=unique_fields)
    except (OSError, ValueError, RuntimeError):
        return unavailable
    if not isinstance(diagnostic, dict) or any(diagnostic.get(key) != value for key, value in identity.items()):
        return unavailable
    exceptions = diagnostic.get("exceptions")
    if not isinstance(exceptions, list):
        return unavailable
    return {"status": "available", "sha256": sha256(original).hexdigest(), "exceptions": _exceptions(exceptions)}
