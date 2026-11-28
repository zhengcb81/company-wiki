"""Project a bound native diagnostic into the small facts Codex triage can use."""

from __future__ import annotations

import builtins
from collections.abc import Iterable
from errno import errorcode
from hashlib import sha256
from http import client
import json
import os
from pathlib import Path
import re
import sqlite3
from stat import S_ISREG
import subprocess
from urllib import error as url_error

from company_wiki.diagnostic_redaction import redact_text

from .observations import decode_observation, unique_fields

_NATIVE_DETAILS = re.compile(r"feedback-[0-9a-f]{32}\.diagnostic\.json")
_CLASS_LABEL = re.compile(r"[A-Z][A-Za-z0-9]{0,79}")
_EXCEPTION_TYPES = {
    name: value
    for module in (builtins, sqlite3, json, subprocess, client, url_error)
    for name, value in vars(module).items()
    if isinstance(value, type) and issubclass(value, BaseException) and value.__name__ == name
}
_PUBLISHED_CWP_ERRORS = {"CatalogConfigError", "CatalogReaderUnavailable", "SourceReadError"}


def _class_label(value: object, module: object, origin: str) -> str | None:
    if not isinstance(value, str):
        return None
    parts = value.split(".")
    if not all(part.isascii() and part.isidentifier() for part in parts):
        return None
    name = parts[-1]
    if name in _EXCEPTION_TYPES or name in _PUBLISHED_CWP_ERRORS:
        return name
    if _CLASS_LABEL.fullmatch(name) and not name.isupper():
        owner_package = origin.replace("-", "_")
        if (isinstance(module, str) and module.partition(".")[0] == owner_package
                and all(part.isascii() and part.isidentifier() for part in module.split("."))
                and redact_text(name) == name):
            return name
        return "OwnerException"
    return None


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


def _exceptions(value: list, origin: str) -> list[dict]:
    facts = []
    for exception in value:
        if not isinstance(exception, dict):
            continue
        name = _class_label(exception.get("type"), exception.get("module"), origin)
        if name is None:
            continue
        exception_type = _EXCEPTION_TYPES.get(name)
        fact = {"type": name}
        errno = exception.get("errno")
        if (type(errno) is int and errno in errorcode
                and (exception_type is None or issubclass(exception_type, OSError))):
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
    return {"status": "available", "sha256": sha256(original).hexdigest(), "exceptions": _exceptions(exceptions, origin)}
