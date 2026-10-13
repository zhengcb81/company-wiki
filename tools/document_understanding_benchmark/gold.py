"""Loading, validating and indexing gold records for a benchmark run.

Gold lives as plain JSON per sample plus one bindings file that maps a
``sample_id`` to an absolute original path. The bindings file is a *local,
uncommitted* artifact: originals are never copied, and a missing binding or a
SHA mismatch yields ``UNAVAILABLE`` rather than a substituted or synthetic
sample.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .records import validate_gold
from .schema import BenchmarkSchemaError

GOLD_DIR = Path(__file__).resolve().parent / "gold"
BINDINGS_NAME = "bindings.json"


class GoldError(RuntimeError):
    """Gold or bindings are structurally wrong (a refused run, not a FAIL)."""


def load_gold(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GoldError(f"cannot read gold {path}: {exc}") from exc
    return validate_gold(raw)


def load_gold_dir(directory: Path | None = None) -> list[dict[str, Any]]:
    root = Path(directory) if directory else GOLD_DIR
    if not root.is_dir():
        raise GoldError(f"gold directory missing: {root}")
    records = [load_gold(path) for path in sorted(root.glob("*.json"))]
    if not records:
        raise GoldError(f"no gold records in {root}")
    seen: set[str] = set()
    for record in records:
        sample_id = record["sample_id"]
        if sample_id in seen:
            raise BenchmarkSchemaError(f"duplicate gold sample_id: {sample_id}")
        seen.add(sample_id)
    return records


def load_bindings(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    candidate = Path(path)
    if not candidate.is_file():
        raise GoldError(f"bindings file missing: {candidate}")
    try:
        raw = json.loads(candidate.read_text(encoding="utf8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GoldError(f"cannot read bindings {candidate}: {exc}") from exc
    if not isinstance(raw, Mapping):
        raise GoldError("bindings must be a JSON object")
    # Accept either {sample_id: path} or {"bindings": {sample_id: path}}.
    table = raw.get("bindings") if isinstance(raw.get("bindings"), Mapping) else raw
    bindings: dict[str, str] = {}
    for sample_id, value in table.items():
        if isinstance(value, Mapping):
            located = value.get("path")
        else:
            located = value
        if not isinstance(located, str) or not located:
            raise GoldError(f"binding for {sample_id} must be a path string or {{path}}")
        bindings[str(sample_id)] = located
    return bindings


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_original(sample_id: str, expected_sha: str, bindings: Mapping[str, str]) -> dict[str, Any]:
    """Locate one original by binding + SHA. Never copies and never substitutes."""

    located = bindings.get(sample_id)
    if not located:
        return {
            "status": "UNAVAILABLE",
            "reason": "no local binding for sample",
            "sample_id": sample_id,
            "path": None,
            "expected_sha256": expected_sha,
            "actual_sha256": None,
        }
    path = Path(located)
    if not path.is_file():
        return {
            "status": "UNAVAILABLE",
            "reason": "bound path does not exist",
            "sample_id": sample_id,
            "path": str(path),
            "expected_sha256": expected_sha,
            "actual_sha256": None,
        }
    actual = sha256_file(path)
    if actual != expected_sha:
        return {
            "status": "UNAVAILABLE",
            "reason": "bound original SHA-256 does not match gold",
            "sample_id": sample_id,
            "path": str(path),
            "expected_sha256": expected_sha,
            "actual_sha256": actual,
        }
    return {
        "status": "OK",
        "reason": "",
        "sample_id": sample_id,
        "path": str(path),
        "expected_sha256": expected_sha,
        "actual_sha256": actual,
    }


def unavailable_observed(gold: Mapping[str, Any], reason: str) -> dict[str, Any]:
    """A truthful observation for a source that could not be read.

    It carries no claims and no selected locators, so the oracle reports
    UNAVAILABLE rather than a fabricated FAIL or PASS.
    """

    return {
        "schema_version": "du-observed/1",
        "sample_id": gold["sample_id"],
        "source_sha256": gold["source_sha256"],
        "route": None,
        "selected_locators": [],
        "selected_text": "",
        "semantic_units": [],
        "claims": [],
        "coverage": {
            "native_scan": "unavailable",
            "complete": False,
            "opaque_pages": [],
            "deferred_unit_ids": [],
            "unassigned_unit_ids": [],
        },
        "metrics": {},
        "execution": {
            "entry_point": None,
            "parser_version": None,
            "selector_version": None,
            "calls": 0,
            "elapsed_seconds": None,
            "mode": "unavailable",
            "reason": reason,
        },
    }
