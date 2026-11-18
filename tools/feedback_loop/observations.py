"""Read optional owner sidecars without accepting a partial or ambiguous occurrence."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Iterable


IDENTITY = ("owner", "origin_owner", "run_id", "attempt_id", "step_id", "check_id")
REQUIRED = ("owner", "run_id", "attempt_id", "step_id", "check_id", "expected", "actual")
OPTIONAL = ("origin_owner", "issue_key", "version", "evidence_ref", "details_ref", "parent_step_id", "disposition",
            "original_occurrence_id", "terminal_check_id")

# Legacy producers shipped before starts could name their matching result.
_LEGACY_TERMINALS = {
    "earnings-transcripts": frozenset({"outcome-naming"}),
    "stockinfo-dl-simple": frozenset({"candidate-listing-identity", "staged-fetch-receipt"}),
}


def _step_identity(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(row[field] for field in IDENTITY[:-1])


def digest(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()


def unique_fields(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _observation(raw: bytes) -> dict[str, str]:
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_fields)
    if not isinstance(value, dict) or value.get("schema_version") != "feedback-observation/1":
        raise ValueError("unsupported_observation")
    row = {"schema_version": value["schema_version"]}
    for key in (*REQUIRED, *OPTIONAL):
        item = value.get(key)
        if key in OPTIONAL and item is None:
            continue
        if not isinstance(item, str) or not item.strip():
            raise ValueError("invalid_observation_field")
        row[key] = item
    row.setdefault("origin_owner", row["owner"])
    if "disposition" not in row:
        row["disposition"] = ("unknown" if "unknown" in (row["expected"], row["actual"]) else
                              "expected" if row["expected"] == row["actual"] else "deviation")
    if row["disposition"] not in {"expected", "unknown", "deviation"}:
        raise ValueError("invalid_disposition")
    return row


@dataclass
class Batch:
    observations: dict[str, dict[str, str]]
    diagnostics: list[dict]

    def plan(self) -> dict:
        return {"observations": [{"occurrence_id": key, **row} for key, row in self.observations.items()],
                "diagnostics": self.diagnostics}

    def unfinished_starts(self) -> set[str]:
        matching_checks: dict[tuple[str, ...], set[str]] = {}
        for row in self.observations.values():
            if row["check_id"] != "action-started":
                matching_checks.setdefault(_step_identity(row), set()).add(row["check_id"])
        return {
            key for key, row in self.observations.items()
            if row["check_id"] == "action-started" and row["actual"] == "started"
            and not matching_checks.get(_step_identity(row), set()).intersection(
                {row["terminal_check_id"]} if "terminal_check_id" in row
                else _LEGACY_TERMINALS.get(row["owner"], ()))
        }


def read_batch(paths: Iterable[Path]) -> Batch:
    rows: dict[str, dict[str, str]] = {}
    conflicts: set[str] = set()
    diagnostics = []
    for index, path in enumerate(paths):
        try:
            with path.open("rb") as stream:
                for number, line in enumerate(stream, start=1):
                    if not line.strip():
                        continue
                    try:
                        row = _observation(line)
                    except (ValueError, RecursionError):
                        diagnostics.append({"input": index, "line": number, "code": "unreadable_observation"})
                        continue
                    key = digest([row[field] for field in IDENTITY])
                    if key in conflicts:
                        continue
                    if key in rows and rows[key] != row:
                        del rows[key]
                        conflicts.add(key)
                        diagnostics.append({"input": index, "line": number, "code": "conflicting_observation",
                                            "occurrence_id": key})
                    else:
                        rows[key] = row
        except OSError as exc:
            diagnostics.append({"input": index, "code": "sidecar_read_failed", "error_type": type(exc).__name__})
    return Batch(rows, diagnostics)
