"""Evidence-fenced metadata proposal rules (G3-SOURCE-FACTS card section 4/5).

The rules are refusals first: weak evidence can only ever produce
``unverified``/``unknown``/``conflict`` states, a digest mismatch or a
sample-id-as-production-id blocks any ready action, an unknown retirement
reason can never suggest an active state, and two disagreeing official
records stay a conflict instead of being averaged into a value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Iterable, Sequence

ACTIONS = (
    "no_change",
    "update_metadata",
    "register_new",
    "do_not_reactivate",
    "unresolved",
)
EVIDENCE_STATUSES = ("verified", "unverified", "unknown", "conflict")

_URN_ID = re.compile(
    r"^urn:company-wiki:(source|document|location|source_version):sha256:[0-9a-f]{64}$"
)
_SAMPLE_ID = re.compile(
    r"^(?:S\d{2}|P\d{2}|T\d{2}|G-S\d{2}-\d{2}|fixture.*)$", re.IGNORECASE
)

_LOCATOR_BASIS = (
    ("filename:", "filename"),
    ("title:", "filename"),
    ("activity:", "activity_date"),
    ("mtime:", "filesystem"),
    ("download:", "filesystem"),
    ("sidecar:", "acquisition_record"),
    ("catalog:", "catalog"),
    ("security_master:", "official_record"),
    ("cninfo:", "official_record"),
    ("sse:", "official_record"),
    ("szse:", "official_record"),
    ("bse:", "official_record"),
    ("sec:", "official_record"),
    ("hkex:", "official_record"),
    ("ir:", "official_record"),
    ("announcement:", "official_record"),
    ("press_release:", "official_record"),
    ("body:", "original_document"),
    ("page:", "original_document"),
    ("loc:", "original_document"),
    ("txt:", "original_document"),
    ("cover:", "original_document"),
)

_WEAK_PUBLISHED_BASES = frozenset(
    {
        "filename",
        "activity_date",
        "filesystem",
        "title",
        "acquisition_record",
        "catalog",
        "unknown",
        "original_document",
    }
)

_IDENTITY_PROBLEM_CODES = frozenset(
    {"sample_id_used_as_production_id", "invalid_production_id"}
)
_IDENTITY_CONFLICT_CODES = frozenset({"content_sha256_mismatch"})
_DATA_BLOCK_PROBLEM_CODES = frozenset(
    {
        "published_date_lacks_verified_evidence",
        "activity_date_cannot_be_published_date",
        "verified_evidence_missing_url",
    }
)


def basis_of(locator: str | None) -> str:
    """Derive the evidence basis from the locator prefix (never from a value)."""
    text = (locator or "").strip()
    lowered = text.casefold()
    for prefix, basis in _LOCATOR_BASIS:
        if lowered.startswith(prefix):
            return basis
    return "unknown"


def _activity_dates(locator: str | None, observed: str | None) -> list[str]:
    dates: list[str] = []
    text = locator or ""
    if text.casefold().startswith("activity:"):
        payload = text.split(":", 1)[1]
        for chunk in payload.split("/"):
            chunk = chunk.strip()
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", chunk):
                dates.append(chunk)
    if observed and re.fullmatch(r"\d{4}-\d{2}-\d{2}", observed.strip()):
        dates.append(observed.strip())
    return dates


@dataclass(frozen=True)
class Evidence:
    field: str
    url: str | None
    locator: str
    observed_value: str | None
    status: str

    def to_record(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "url": self.url,
            "locator": self.locator,
            "observed_value": self.observed_value,
            "status": self.status,
        }


@dataclass
class ProposalItem:
    sample_id: str = ""
    source_id: str | None = None
    document_id: str | None = None
    source_version_id: str | None = None
    location_id: str | None = None
    registered: bool = True
    content_sha256: str | None = None
    registered_content_sha256: str | None = None
    retired: bool = False
    retired_reason: str | None = None
    restore_record: bool = False
    superseded: bool = False
    current: dict[str, Any] = field(default_factory=dict)
    proposed: dict[str, Any] = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)
    main_request: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProposalItem":
        evidence = [
            Evidence(
                field=str(entry.get("field", "")),
                url=entry.get("url"),
                locator=str(entry.get("locator", "")),
                observed_value=entry.get("observed_value"),
                status=str(entry.get("status", "unknown")),
            )
            for entry in payload.get("evidence", []) or []
        ]
        known = {name for name in cls.__dataclass_fields__}
        data = {
            key: value
            for key, value in payload.items()
            if key in known and key != "evidence"
        }
        data["evidence"] = evidence
        return cls(**data)


@dataclass
class ItemReport:
    sample_id: str
    source_id: str | None
    document_id: str | None
    source_version_id: str | None
    location_id: str | None
    content_sha256: str | None
    current: dict[str, Any]
    proposed: dict[str, Any]
    action: str
    retired_reason: str | None
    evidence: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    problems: list[dict[str, Any]]
    main_request: str | None

    def to_item_dict(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "source_id": self.source_id,
            "document_id": self.document_id,
            "source_version_id": self.source_version_id,
            "location_id": self.location_id,
            "content_sha256": self.content_sha256,
            "current": self.current,
            "proposed": self.proposed,
            "action": self.action,
            "retired_reason": self.retired_reason,
            "evidence": self.evidence,
            "conflicts": self.conflicts,
            "problems": self.problems,
            "main_request": self.main_request,
        }


def _problem(code: str, detail: str, **extra: Any) -> dict[str, Any]:
    payload = {"code": code, "detail": detail}
    payload.update(extra)
    return payload


def _conflict(code: str, detail: str, **extra: Any) -> dict[str, Any]:
    payload = {"code": code, "detail": detail}
    payload.update(extra)
    return payload


def _identity_problems(item: ProposalItem) -> list[dict[str, Any]]:
    problems: list[dict[str, Any]] = []
    for name in ("source_id", "document_id", "source_version_id", "location_id"):
        value = getattr(item, name)
        if value is None or value == "":
            continue
        if not isinstance(value, str) or not _URN_ID.match(value):
            if isinstance(value, str) and _SAMPLE_ID.match(value):
                problems.append(
                    _problem(
                        "sample_id_used_as_production_id",
                        f"{name}={value!r} is a sample/fixture id, not a production id",
                        field=name,
                        observed_value=value,
                    )
                )
            else:
                problems.append(
                    _problem(
                        "invalid_production_id",
                        f"{name} is not a urn:company-wiki production id",
                        field=name,
                        observed_value=value,
                    )
                )
    return problems


def _digest_mismatch(item: ProposalItem) -> bool:
    observed = (item.content_sha256 or "").strip().lower()
    registered = (item.registered_content_sha256 or "").strip().lower()
    if not observed or not registered:
        return False
    return observed != registered


def _normalize_evidence(
    item: ProposalItem,
    *,
    digest_mismatch: bool,
    problems: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for evidence in item.evidence:
        status = evidence.status if evidence.status in EVIDENCE_STATUSES else "unknown"
        basis = basis_of(evidence.locator)
        if digest_mismatch and status == "verified":
            status = "unverified"
        if status == "verified" and basis == "official_record" and not evidence.url:
            status = "unverified"
            problems.append(
                _problem(
                    "verified_evidence_missing_url",
                    f"field {evidence.field} claims verified without a first-hand url",
                    field=evidence.field,
                    locator=evidence.locator,
                )
            )
        if (
            evidence.field == "published_date"
            and status == "verified"
            and basis != "official_record"
        ):
            status = "unverified"
        record = evidence.to_record()
        record["status"] = status
        record["_basis"] = basis
        records.append(record)
    return records


def _official_conflicts(
    records: list[dict[str, Any]], conflicts: list[dict[str, Any]]
) -> None:
    by_field: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        if record["_basis"] == "official_record" and record["status"] == "verified":
            by_field.setdefault(record["field"], []).append(record)
    for field_name, group in by_field.items():
        values = []
        for record in group:
            value = record.get("observed_value")
            if value is not None and value not in values:
                values.append(value)
        if len(values) > 1:
            for record in group:
                record["status"] = "conflict"
            conflicts.append(
                _conflict(
                    "official_records_conflict",
                    f"first-hand records disagree on {field_name}",
                    field=field_name,
                    values=values,
                )
            )


def _has_verified_official(records: Sequence[dict[str, Any]], field_name: str) -> bool:
    return any(
        record["field"] == field_name
        and record["status"] == "verified"
        and record["_basis"] == "official_record"
        for record in records
    )


def _strip_private(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if not key.startswith("_")}


def build_item_report(item: ProposalItem) -> ItemReport:
    problems: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []

    problems.extend(_identity_problems(item))

    digest_mismatch = _digest_mismatch(item)
    if digest_mismatch:
        conflicts.append(
            _conflict(
                "content_sha256_mismatch",
                "observed original digest differs from the registered source digest",
                field="content_sha256",
                values=[item.registered_content_sha256, item.content_sha256],
            )
        )

    records = _normalize_evidence(
        item, digest_mismatch=digest_mismatch, problems=problems
    )
    _official_conflicts(records, conflicts)

    activity_values: list[str] = []
    for record in records:
        if record["field"] == "activity_date":
            activity_values.extend(
                _activity_dates(record.get("locator"), record.get("observed_value"))
            )
    activity_values = sorted(set(activity_values))

    proposed_date = item.proposed.get("published_date")
    current_date = item.current.get("published_date")
    published_changed = proposed_date is not None and proposed_date != current_date
    official_published = _has_verified_official(records, "published_date")

    if activity_values and current_date and not official_published:
        if not any(
            start <= current_date <= end
            for start, end in [(activity_values[0], activity_values[-1])]
        ):
            conflicts.append(
                _conflict(
                    "activity_date_vs_published_date",
                    "registered published_date does not sit inside the observed activity window",
                    field="published_date",
                    values=[current_date, *activity_values],
                )
            )

    if published_changed and not official_published:
        problems.append(
            _problem(
                "published_date_lacks_verified_evidence",
                "published_date may only be proposed from a first-hand official record",
                field="published_date",
                observed_value=proposed_date,
            )
        )
        if proposed_date in activity_values:
            problems.append(
                _problem(
                    "activity_date_cannot_be_published_date",
                    "an activity date is not a public disclosure date",
                    field="published_date",
                    observed_value=proposed_date,
                    activity_values=activity_values,
                )
            )

    retired_reason = item.retired_reason if item.retired else None
    if item.retired and not (retired_reason or "").strip():
        problems.append(
            _problem(
                "retired_reason_unknown",
                "retired without a recorded reason",
                field="source_status",
            )
        )
    if item.retired and not item.restore_record:
        problems.append(
            _problem(
                "retired_without_restore_record",
                "file still exists but no restore/supersession record authorises an active state",
                field="source_status",
            )
        )

    identity_blocked = any(
        p["code"] in _IDENTITY_PROBLEM_CODES for p in problems
    ) or any(c["code"] in _IDENTITY_CONFLICT_CODES for c in conflicts)
    data_blocked = bool(conflicts) or any(
        p["code"] in _DATA_BLOCK_PROBLEM_CODES for p in problems
    )

    if not item.proposed or item.proposed == item.current:
        candidate = "no_change"
    elif not item.registered:
        candidate = "register_new"
    else:
        candidate = "update_metadata"

    if identity_blocked:
        action = "unresolved"
    elif item.retired and not item.restore_record:
        action = "do_not_reactivate"
    elif data_blocked:
        action = "unresolved"
    else:
        action = candidate

    return ItemReport(
        sample_id=item.sample_id,
        source_id=item.source_id,
        document_id=item.document_id,
        source_version_id=item.source_version_id,
        location_id=item.location_id,
        content_sha256=item.content_sha256,
        current=item.current,
        proposed=item.proposed,
        action=action,
        retired_reason=retired_reason,
        evidence=[_strip_private(record) for record in records],
        conflicts=conflicts,
        problems=problems,
        main_request=item.main_request,
    )


def build_report(
    items: Iterable[ProposalItem],
    *,
    catalog_observation: dict[str, Any] | None = None,
    observation_time: str,
    budget_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reports = [build_item_report(item) for item in items]
    payload: dict[str, Any] = {
        "schema_version": "g3-metadata-proposals/1",
        "observation_time": observation_time,
        "catalog_observation": catalog_observation or {},
        "items": [report.to_item_dict() for report in reports],
        "problems": [
            {"sample_id": report.sample_id, **problem}
            for report in reports
            for problem in report.problems
        ],
        "conflicts": [
            {"sample_id": report.sample_id, **conflict}
            for report in reports
            for conflict in report.conflicts
        ],
        "unknowns": [
            {
                "sample_id": report.sample_id,
                "field": record["field"],
                "status": record["status"],
                "locator": record["locator"],
            }
            for report in reports
            for record in report.evidence
            if record["status"] in {"unknown", "unverified"}
        ],
    }
    if budget_summary is not None:
        payload["budget"] = budget_summary
    return payload


__all__ = [
    "ACTIONS",
    "EVIDENCE_STATUSES",
    "Evidence",
    "ItemReport",
    "ProposalItem",
    "basis_of",
    "build_item_report",
    "build_report",
]
