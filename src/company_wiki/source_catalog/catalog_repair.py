"""FF-1 B2: declaration-driven, one-shot repair of undated catalog groups.

The ensure flow may resolve a request to AMBIGUOUS only because a stored
document row lacks ``published_date`` while its on-disk group sidecar
(dayu portfolio ``meta.json`` / company_raw & directory ``.source.json``)
DECLARED a filing date the catalog never absorbed.  This module plans that
repair read-only, and the acquisition service performs it through the SAME
directed registration the ``catalog register`` subcommand uses
(``registration_scope.register_groups``) plus an append-only journal event.

Red lines honoured here:
  * the planner only READS (sidecar files + the catalog reader);
  * the repair never invents a value: a group is registered only when its
    sidecar declares a filing date (``_DECLARING_KEYS`` semantics);
  * resolve/query never call into this module (ensure-only self-heal).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, UTC, datetime
import json
import os
from pathlib import Path
from typing import Any

from .acquisition_sidecar import (
    ACQUISITION_SIDECAR_SUFFIX,
    read_acquisition_sidecar,
)
from .lock import acquisition_mutex
from .source_group_scope import filing_group_key
from .store import canonical_json


CATALOG_REPAIR_JOURNAL_SCHEMA_VERSION = "catalog-repair/1"

#: Where a repaired group's declaration came from (journal ``data_source``).
DATA_SOURCE_GROUP_SIDECAR_DECLARATION = "group_sidecar_declaration"

_DAYU_GROUP_SIDECAR = "group_meta_json"
_ACQUISITION_GROUP_SIDECAR = "acquisition_sidecar"


@dataclass(frozen=True)
class GroupRepair:
    """One directed registration the self-heal will perform."""

    root_id: str
    relative_path: str
    sidecar_kind: str
    filing_date: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _declared_filing_date(payload: dict[str, Any]) -> str | None:
    """The sidecar's declared publication date, or None when undeclared.

    Mirrors the scanner's ``_DECLARING_KEYS["published_date"]`` order
    (``filing_date`` first, then ``published_date``): only a canonical ISO
    date counts as a declaration — anything else is treated as absent
    rather than guessed into the catalog.
    """
    for key in ("filing_date", "published_date"):
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        candidate = value.strip()
        try:
            parsed = date.fromisoformat(candidate)
        except ValueError:
            continue
        if parsed.isoformat() == candidate:
            return candidate
    return None


def _dayu_group_repair(root: Any, relative: str) -> GroupRepair | None:
    group = filing_group_key(relative)
    meta_path = root.path.joinpath(*Path(group).parts) / "meta.json"
    try:
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    declared = _declared_filing_date(payload)
    if declared is None:
        return None
    return GroupRepair(str(root.root_id), relative, _DAYU_GROUP_SIDECAR, declared)


def _acquisition_sidecar_repair(root: Any, relative: str) -> GroupRepair | None:
    sidecar = root.path.joinpath(*Path(relative).parts).with_name(
        Path(relative).name + ACQUISITION_SIDECAR_SUFFIX
    )
    if not sidecar.is_file():
        return None
    payload = read_acquisition_sidecar(sidecar)
    declared = _declared_filing_date(payload)
    if declared is None:
        return None
    return GroupRepair(str(root.root_id), relative, _ACQUISITION_GROUP_SIDECAR, declared)


def plan_undated_group_repairs(catalog: Any, resolution: Any) -> tuple[GroupRepair, ...]:
    """Read-only plan: which excluded undated candidates' groups DECLARE a date.

    Only candidates the resolver excluded for an unknown published date are
    considered; a repair target is emitted solely when the group's sidecar on
    disk declares a filing date.  The registration relative path is the
    candidate's own active ``original_primary`` location, so the directed
    registration selects exactly that group (``SourceRegistrationScope``).
    """
    roots = {root.root_id: root for root in catalog.config.roots}
    planned: dict[tuple[str, str], GroupRepair] = {}
    for candidate in getattr(resolution, "excluded_candidates", ()) or ():
        if not isinstance(candidate, dict):
            continue
        if candidate.get("publication_status") != "unknown":
            continue
        source_ref = candidate.get("source_ref")
        document_id = candidate.get("document_id") or (
            source_ref.get("document_id") if isinstance(source_ref, dict) else None
        )
        source_id = source_ref.get("source_id") if isinstance(source_ref, dict) else None
        if not document_id or not source_id:
            continue
        try:
            locations = catalog.reader.exact_source_locations(
                str(document_id), str(source_id)
            )
        except Exception:  # noqa: BLE001 - planning is best-effort read-only
            continue
        for location in locations:
            if location["role"] != "original_primary":
                continue
            if location["location_status"] != "active":
                continue
            root = roots.get(str(location["root_id"]))
            relative = str(location["relative_path"])
            if root is None:
                continue
            if root.kind == "dayu_portfolio":
                repair = _dayu_group_repair(root, relative)
            elif root.kind in {"company_raw", "directory"}:
                repair = _acquisition_sidecar_repair(root, relative)
            else:
                continue
            if repair is not None:
                planned.setdefault((repair.root_id, repair.relative_path), repair)
    return tuple(planned.values())


class CatalogRepairJournal:
    """Append-only journal of directed catalog repairs (FF-1 B2).

    A dedicated JSONL file (``catalog_repairs.jsonl``): the acquisition
    attempt journal's outcome vocabulary is a frozen read-model contract, so
    repair events get their own append-only stream with the same per-file
    mutex discipline.  Never written while holding the catalog operation
    lock (ADR-008 ordering: register first, journal after).
    """

    def __init__(self, catalog_dir: Path):
        if not isinstance(catalog_dir, Path):
            raise TypeError("catalog_dir must be pathlib.Path")
        self.catalog_dir = catalog_dir
        self.path = catalog_dir / "catalog_repairs.jsonl"

    def record_repair_applied(
        self, *, request_id: str, resolution_reason: str,
        repairs: tuple[GroupRepair, ...] | list[GroupRepair],
        data_source: str = DATA_SOURCE_GROUP_SIDECAR_DECLARATION,
    ) -> dict[str, Any]:
        if not isinstance(request_id, str) or not request_id.strip():
            raise ValueError("request_id must be non-empty text")
        if not isinstance(resolution_reason, str) or not resolution_reason.strip():
            raise ValueError("resolution_reason must be non-empty text")
        registered = [repair.to_dict() for repair in repairs]
        if not registered:
            raise ValueError("catalog_repair_applied requires registered groups")
        event: dict[str, Any] = {
            "schema_version": CATALOG_REPAIR_JOURNAL_SCHEMA_VERSION,
            "event": "catalog_repair_applied",
            "request_id": request_id,
            "resolution_reason": resolution_reason,
            "data_source": data_source,
            "registered": registered,
            "recorded_at": _utc_now(),
        }
        encoded = (canonical_json(event) + "\n").encode("utf-8")
        with acquisition_mutex(self.path):
            self.catalog_dir.mkdir(parents=True, exist_ok=True)
            with self.path.open("ab") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
        return event

    def read_all(self) -> tuple[dict[str, Any], ...]:
        if not self.path.is_file():
            return ()
        events: list[dict[str, Any]] = []
        with self.path.open(encoding="utf-8") as stream:
            for raw in stream:
                if not raw.strip():
                    continue
                events.append(json.loads(raw))
        return tuple(events)


__all__ = [
    "CATALOG_REPAIR_JOURNAL_SCHEMA_VERSION",
    "CatalogRepairJournal",
    "DATA_SOURCE_GROUP_SIDECAR_DECLARATION",
    "GroupRepair",
    "plan_undated_group_repairs",
]
