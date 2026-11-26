"""Read optional owner sidecars without accepting a partial or ambiguous occurrence."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Iterable


IDENTITY = ("owner", "origin_owner", "run_id", "attempt_id", "step_id", "check_id")
REQUIRED = ("owner", "run_id", "attempt_id", "step_id", "check_id", "expected", "actual")
OPTIONAL = ("origin_owner", "issue_key", "version", "evidence_ref", "details_ref", "parent_step_id", "disposition",
            "original_occurrence_id", "terminal_check_id")
_REFUSAL_CODE = re.compile(r"[a-z][a-z0-9_-]{0,80}")
_COST_CHECKS = {"job-usage", "provider-usage", "transcript-provider-usage", "cost-receipt"}

# Legacy producers shipped before starts could name their matching result.
_LEGACY_TERMINALS = {
    "earnings-transcripts": frozenset({"outcome-naming"}),
    "stockinfo-dl-simple": frozenset({"candidate-listing-identity", "staged-fetch-receipt"}),
}


def _step_identity(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(row[field] for field in IDENTITY[:-1])


def _evidence_scope(row: dict[str, str]) -> tuple[str, ...]:
    scope = _step_identity(row)
    return (*scope, row["evidence_ref"]) if "evidence_ref" in row else scope


def has_stage_result(row: dict[str, str]) -> bool:
    return row["check_id"] != "action-started" and row["actual"] not in (
        "started", "pending", "running", "unknown", "unconfirmed", "cost_unknown",
    )


def digest(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()


def _terminal_checks(row: dict[str, str]) -> frozenset[str]:
    declared = row.get("terminal_check_id")
    if declared is None:
        return _LEGACY_TERMINALS.get(row["owner"], frozenset())
    if isinstance(declared, str) and declared.strip() and declared != "action-started":
        return frozenset({declared})
    return frozenset()


def terminal_occurrence_ids(row: dict[str, str]) -> tuple[str, ...]:
    """Locate declared results for an ordinary start using its original stage identity."""
    if (row.get("check_id") != "action-started" or row.get("disposition") != "expected"
            or row.get("expected") != "started" or row.get("actual") != "started" or "refusal_code" in row):
        return ()
    identity = [row.get(field) for field in IDENTITY[:-1]]
    if not all(isinstance(value, str) and value.strip() for value in identity):
        return ()
    return tuple(digest([*identity, check]) for check in sorted(_terminal_checks(row)))


def unique_fields(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def decode_observation(raw: bytes) -> dict[str, str]:
    return normalize_observation(json.loads(raw.decode("utf-8"), object_pairs_hook=unique_fields))


def normalize_observation(value: object) -> dict[str, str]:
    """Validate an observation read from a sidecar or the durable host ledger."""
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
    code = value.get("refusal_code")
    if isinstance(code, str) and _REFUSAL_CODE.fullmatch(code):
        row["refusal_code"] = code
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

    def unfinished_starts(self, *, registered: set[str] | None = None) -> set[str]:
        matching_checks: dict[tuple[str, ...], set[str]] = {}
        for key, row in self.observations.items():
            if (registered is None or key in registered) and has_stage_result(row):
                for scope in {_step_identity(row), _evidence_scope(row)}:
                    matching_checks.setdefault(scope, set()).add(row["check_id"])
        return {
            key for key, row in self.observations.items()
            if row["check_id"] == "action-started" and row["actual"] == "started"
            and not matching_checks.get(_evidence_scope(row), set()).intersection(_terminal_checks(row))
        }

    def unfinished_occurrences(self, *, starts: set[str] | None = None) -> set[str]:
        if starts is None:
            starts = self.unfinished_starts()
        pending_starts = (self.observations[key] for key in starts)
        scopes = {
            _step_identity(row) for row in pending_starts
            if "terminal_check_id" in row or row["owner"] in _LEGACY_TERMINALS
        }
        refusal_scopes = scopes | {
            _step_identity(row) for row in self.observations.values()
            if row["check_id"] in _COST_CHECKS and row["actual"] in ("unknown", "cost_unknown")
        }
        return starts | {
            key for key, row in self.observations.items()
            if (row["disposition"] == "deviation" and _step_identity(row) in scopes)
            or ("refusal_code" in row and _step_identity(row) in refusal_scopes)
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
                        row = decode_observation(line)
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
