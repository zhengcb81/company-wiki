"""company_raw-internal duplicate accounting from an existing RAW-DUP report.

Only groups whose members all live under the configured ``company_raw`` root are
considered; outside roots, same-path references, hard links / shared physical
files, similar-size-different-content, unresolved and unread groups never become
savings. Unknown stays unknown: allocation and release fields are ``None`` until
the report actually proves them, and ``deleted_bytes`` is always 0.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

INTERNAL_ROOT_ID = "company_raw"
SCOPE = "company_raw"
RECOMMENDATION_MIN_BENEFIT_BYTES = 256 * 1024 * 1024

_VERIFICATION_OK = frozenset({"verified", "verified_identical"})
_CLASSIFICATION_CATEGORIES = (
    "same_path_references",
    "shared_physical_file",
    "distinct_physical_copies",
    "uncertain_physical_identity",
    "similar_size_different_content",
    "unresolved",
)


def _groups(report: dict[str, Any]) -> list[dict[str, Any]]:
    value = report.get("duplicate_groups")
    return list(value) if isinstance(value, list) else []


def internal_groups(
    report: dict[str, Any], root_id: str = INTERNAL_ROOT_ID
) -> list[dict[str, Any]]:
    """Groups whose every registered locator belongs to the internal root."""
    out = []
    for group in _groups(report):
        locators = group.get("locators") or []
        if not locators:
            continue
        if all(locator.get("root_id") == root_id for locator in locators):
            out.append(group)
    return out


def _is_verified(group: dict[str, Any]) -> bool:
    verification = group.get("verification") or {}
    files = verification.get("files") or []
    unread = verification.get("unread_members") or []
    if not verification.get("attempted") or unread:
        return False
    if verification.get("status") not in _VERIFICATION_OK:
        return False
    if len(files) < len(group.get("locators") or []):
        return False
    return all(f.get("status") in _VERIFICATION_OK for f in files)


def _logical_bytes(group: dict[str, Any]) -> int:
    members = len(group.get("locators") or [])
    size = int(group.get("byte_size") or 0)
    return max(0, members - 1) * size


def _verified_bytes(group: dict[str, Any]) -> int:
    files = (group.get("verification") or {}).get("files") or []
    size = int(group.get("byte_size") or 0)
    return max(0, len(files) - 1) * size


def _category_counts(report: dict[str, Any]) -> dict[str, Any]:
    counts: dict[str, Any] = {name: 0 for name in _CLASSIFICATION_CATEGORIES}
    counts.update(
        {
            "missing": 0,
            "cloud_placeholder": 0,
            "status_unknown": 0,
            "internal_groups": 0,
            "outside_root_groups": 0,
        }
    )
    for group in _groups(report):
        classification = str(group.get("classification") or "unresolved")
        if classification in counts:
            counts[classification] += 1
        locators = group.get("locators") or []
        if locators and all(loc.get("root_id") == INTERNAL_ROOT_ID for loc in locators):
            counts["internal_groups"] += 1
        else:
            counts["outside_root_groups"] += 1
        verification = group.get("verification") or {}
        statuses = [
            str(f.get("status") or "") for f in (verification.get("files") or [])
        ] + [
            str(m.get("status") or "")
            for m in (verification.get("unread_members") or [])
        ]
        for status in statuses:
            if status == "missing" or status in {"missing", "acl_denied", "open_error"}:
                counts["missing"] += 1
            elif status == "skipped_cloud_placeholder":
                counts["cloud_placeholder"] += 1
            elif status in {
                "unread_path",
                "not_attempted",
                "not_attempted_scan_mode",
                "not_attempted_uncertain_or_unresolved",
            }:
                counts["status_unknown"] += 1
        for locator in locators:
            if locator.get("location_status") == "missing":
                counts["missing"] += 1
    return counts


def _allocated_for(counted: Sequence[dict[str, Any]]) -> int | None:
    total = 0
    for group in counted:
        value = group.get("physical_allocated_bytes")
        if value is None:
            return None
        total += int(value)
    return total if counted else None


def _references_allow_release(group: dict[str, Any]) -> bool:
    refs = group.get("reference_counts")
    if not isinstance(refs, dict):
        return False
    return int(refs.get("documents") or 0) <= 1 and int(refs.get("versions") or 0) == 0


def build_raw_space_decision(
    report: dict[str, Any],
    *,
    command: str,
    input_version: str,
    limits_hit: Sequence[str] | None = None,
    actual_command: str | None = None,
    followup: str | None = None,
    registered_internal_upper_bound_bytes: int | None = None,
    registered_internal_groups: int | None = None,
    registered_bound_source: str | None = None,
    metadata: dict[str, Any] | None = None,
    input_report_sha256: str | None = None,
) -> dict[str, Any]:
    limits = report.get("limits") or {}
    hit = sorted(
        {str(item) for item in (report.get("limits_hit") or [])}
        | {str(item) for item in (limits_hit or [])}
    )
    status = str(report.get("status") or "unknown")
    truncation = report.get("truncated") or {}
    groups = internal_groups(report)

    counted = [
        g for g in groups if g.get("classification") == "distinct_physical_copies"
    ]
    verified = [g for g in counted if _is_verified(g)]
    incomplete = [g for g in counted if not _is_verified(g)]
    not_attempted = [
        g for g in counted if not ((g.get("verification") or {}).get("attempted"))
    ]

    listed_bound = sum(_logical_bytes(g) for g in counted)
    if registered_internal_upper_bound_bytes is not None:
        bound = int(registered_internal_upper_bound_bytes)
        bound_source = registered_bound_source or "catalog_metadata"
        registered_groups = (
            int(registered_internal_groups)
            if registered_internal_groups is not None
            else len(counted)
        )
    else:
        bound = listed_bound
        bound_source = "report_listed_groups"
        registered_groups = len(counted)

    verified_bytes = sum(_verified_bytes(g) for g in verified)
    allocated = _allocated_for(counted)
    releasable = (
        allocated
        if allocated is not None
        and verified
        and not incomplete
        and all(_references_allow_release(g) for g in verified)
        else None
    )

    dropped_rows = int(truncation.get("dropped_groups_by_row_cap") or 0)
    stopping = bool({"read_bytes", "deadline"} & set(hit)) or status == "partial"
    if bound_source == "report_listed_groups":
        bound_complete = status == "succeeded" and not stopping and dropped_rows == 0
        incomplete_groups = len(incomplete)
    else:
        bound_complete = True
        incomplete_groups = max(0, registered_groups - len(verified))

    unknowns: list[str] = []
    if status != "succeeded":
        unknowns.append(f"scan_status_{status}")
    if hit:
        unknowns.append("limits_hit:" + ",".join(hit))
    if dropped_rows:
        unknowns.append(
            f"detail_row_cap_dropped_groups={dropped_rows}"
            " (report lists a subset; registered bound comes from catalog metadata)"
        )
    if incomplete_groups:
        unknowns.append(f"registered_groups_not_fully_verified={incomplete_groups}")
    if allocated is None:
        unknowns.append("allocated_bytes_unproven")
    if releasable is None:
        unknowns.append("releasable_bytes_unproven")

    if bound_source == "report_listed_groups" and not bound_complete:
        decision = "not_enough_evidence"
        reason = (
            "the registered bound is only available from a truncated/incomplete report "
            "listing, so no company_raw space claim can be made"
        )
    elif bound < RECOMMENDATION_MIN_BENEFIT_BYTES:
        decision = "no_migration_recommended"
        reason = (
            f"the registered company_raw-internal logical upper bound ({bound} bytes) "
            f"already stays below the {RECOMMENDATION_MIN_BENEFIT_BYTES}-byte benefit "
            f"threshold; {verified_bytes} bytes were read-confirmed, allocation stays "
            "unproven on this platform and deleted_bytes is 0"
        )
    elif (
        verified_bytes >= RECOMMENDATION_MIN_BENEFIT_BYTES
        and allocated is not None
        and releasable is not None
    ):
        decision = "prepare_followup"
        reason = (
            f"verified internal redundant copies reach {verified_bytes} bytes with a "
            "proven allocation and no blocking references"
        )
    elif incomplete_groups:
        decision = "not_enough_evidence"
        reason = (
            "candidate groups exist above the benefit threshold but the internal "
            "evidence is not fully verified, so the benefit stays unknown rather "
            "than zero"
        )
    else:
        decision = "no_migration_recommended"
        reason = (
            f"verified company_raw-internal redundant bytes ({verified_bytes}) stay "
            f"below the {RECOMMENDATION_MIN_BENEFIT_BYTES}-byte benefit threshold and "
            "the allocation/release gain cannot be proven in this lane"
        )

    counts = report.get("counts") or {}
    payload: dict[str, Any] = {
        "schema_version": "g3-raw-space-decision/1",
        "scope": SCOPE,
        "command": command,
        "actual_command": actual_command or command,
        "input_version": input_version,
        "input_report_sha256": input_report_sha256,
        "registered_bound_source": bound_source,
        "registered_bound_complete": bound_complete,
        "report_status": status,
        "limits": limits,
        "limits_hit": hit,
        "read_bytes": report.get("read_bytes"),
        "deadline_seconds": limits.get("deadline_seconds"),
        "candidate_groups": registered_groups,
        "listed_candidate_groups": len(counted),
        "verified_groups": len(verified),
        "incomplete_groups": incomplete_groups,
        "groups_not_attempted": len(not_attempted),
        "counted_groups": [g.get("group_id") for g in counted],
        "registered_upper_bound_bytes": bound,
        "listed_groups_upper_bound_bytes": listed_bound,
        "verified_distinct_copy_bytes": verified_bytes,
        "allocated_bytes": allocated,
        "releasable_bytes": releasable,
        "deleted_bytes": 0,
        "coverage": {
            "registered_groups": registered_groups,
            "groups_read": len(verified),
            "registered_upper_bound_bytes": bound,
            "verified_distinct_copy_bytes": verified_bytes,
            "read_fraction_of_bound": (
                round(verified_bytes / bound, 4) if bound else None
            ),
        },
        "categories": _category_counts(report),
        "metadata": metadata,
        "global_registered_totals": {
            "scope": "whole_database",
            "registered_sources": counts.get("registered_sources"),
            "registered_bytes": counts.get("registered_bytes"),
            "note": "diagnostic only; never a company_raw figure",
        },
        "unknowns": unknowns,
        "decision": decision,
        "reason": reason,
        "followup": followup
        or (
            "MAIN to re-run the bounded company_raw scan after any catalog change; "
            "no delete/move/hardlink/object migration is proposed by this card"
        ),
    }
    return payload


__all__ = [
    "INTERNAL_ROOT_ID",
    "RECOMMENDATION_MIN_BENEFIT_BYTES",
    "SCOPE",
    "build_raw_space_decision",
    "internal_groups",
]
