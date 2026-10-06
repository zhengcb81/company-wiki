"""Bounded, streaming byte verification for candidate duplicate groups."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from .classify import (
    STATE_ACL_DENIED,
    STATE_MISSING,
    Group,
    Member,
)
from .core import (Budget, BudgetExceeded, FILE_ATTRIBUTE_REPARSE_POINT,
                   error_label, hash_file, hydrate_risk, normalized)

STATUS_VERIFIED = "verified"
STATUS_VERIFIED_GROUP = "verified_identical"
STATUS_NOT_ATTEMPTED = "not_attempted"
STATUS_METADATA_MISMATCH = "metadata_sha_mismatch"
STATUS_CHANGED = "changed"
STATUS_ACL = "acl_denied"
STATUS_MISSING = "missing"
STATUS_OPEN_ERROR = "open_error"
STATUS_HYDRATE = "skipped_cloud_placeholder"
STATUS_UNREAD_PATH = "unread_path"

GROUP_STATUS_ORDER = (
    STATUS_METADATA_MISMATCH,
    STATUS_CHANGED,
    STATUS_ACL,
    STATUS_MISSING,
    STATUS_OPEN_ERROR,
    STATUS_HYDRATE,
    STATUS_UNREAD_PATH,
    STATUS_NOT_ATTEMPTED,
)

_UNREAD_STATE_STATUS = {
    STATE_MISSING: STATUS_MISSING,
    STATE_ACL_DENIED: STATUS_ACL,
}


def _unread_status(member: Member) -> str:
    return _UNREAD_STATE_STATUS.get(member.path_state, STATUS_UNREAD_PATH)


def read_targets(group: Group) -> list[list[Member]]:
    """One representative per distinct physical identity (aliases grouped)."""
    targets: dict[tuple[int, int], list[Member]] = {}
    ordered: list[Member] = []
    for member in sorted(
        group.members,
        key=lambda item: (item.root_priority, item.normalized_path or ""),
    ):
        if not member.visible or member.identity is None:
            continue
        bucket = targets.setdefault(member.identity, [])
        if not bucket:
            ordered.append(member)
        bucket.append(member)
    return [
        targets[member.identity] for member in ordered if member.identity is not None
    ]


def _read_one(bucket: list[Member], budget: Budget) -> dict:
    member = bucket[0]
    path = Path(member.path)  # type: ignore[arg-type]
    budget.consume_deadline()
    if member.hydrate_risk or hydrate_risk(path):
        return {
            "root_id": member.record.root_id,
            "relative_path": member.record.relative_path,
            "location_ids": [item.record.location_id for item in bucket],
            "status": STATUS_HYDRATE,
            "registered_sha256": member.record.content_sha256,
            "actual_sha256": None,
            "bytes_read": 0,
            "detail": "cloud placeholder not opened (hydrate risk)",
        }
    entry = {
        "root_id": member.record.root_id,
        "relative_path": member.record.relative_path,
        "location_ids": [item.record.location_id for item in bucket],
        "status": STATUS_NOT_ATTEMPTED,
        "registered_sha256": member.record.content_sha256,
        "actual_sha256": None,
        "bytes_read": 0,
        "detail": "",
    }
    try:
        pre = os.lstat(path)
    except OSError as exc:
        entry["status"] = (
            STATUS_ACL if getattr(exc, "errno", None) in (13, 1) else STATUS_MISSING
        )
        entry["detail"] = error_label(exc)
        return entry
    if (not stat.S_ISREG(pre.st_mode)
        or getattr(pre, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT
        or (pre.st_dev, pre.st_ino) != member.identity
        or str(normalized(path)) != member.normalized_path):
        entry["status"] = STATUS_CHANGED
        entry["detail"] = "path_or_physical_identity_changed_since_scan"
        return entry
    if member.size is not None and (
        pre.st_size != member.size or pre.st_mtime_ns != member.observed_mtime_ns
    ):
        entry["status"] = STATUS_CHANGED
        entry["detail"] = "size_or_mtime_changed_since_scan"
        return entry
    before = budget.read_bytes
    try:
        actual = hash_file(path, budget)
    except OSError as exc:
        entry["bytes_read"] = budget.read_bytes - before
        entry["status"] = (
            STATUS_ACL if getattr(exc, "errno", None) in (13, 1) else STATUS_OPEN_ERROR
        )
        entry["detail"] = error_label(exc)
        return entry
    entry["bytes_read"] = budget.read_bytes - before
    try:
        post = os.stat(path)
    except OSError as exc:
        entry["status"] = STATUS_CHANGED
        entry["detail"] = f"stat_after_read_failed: {error_label(exc)}"
        return entry
    if (post.st_size != pre.st_size or post.st_mtime_ns != pre.st_mtime_ns
        or (post.st_dev, post.st_ino) != (pre.st_dev, pre.st_ino)
        or str(normalized(path)) != member.normalized_path):
        entry["status"] = STATUS_CHANGED
        entry["detail"] = "size_or_mtime_changed_during_read"
        return entry
    entry["actual_sha256"] = actual
    if actual != member.record.content_sha256:
        entry["status"] = STATUS_METADATA_MISMATCH
        entry["detail"] = "registered digest does not match file bytes"
    else:
        entry["status"] = STATUS_VERIFIED
    return entry


def _group_status(files: list[dict], unread: list[dict]) -> str:
    statuses = [item["status"] for item in files] + [item["status"] for item in unread]
    if statuses and all(status == STATUS_VERIFIED for status in statuses):
        return STATUS_VERIFIED_GROUP
    for candidate in GROUP_STATUS_ORDER:
        if candidate in statuses:
            return candidate
    return STATUS_NOT_ATTEMPTED


def _unread_members(group: Group) -> list[dict]:
    unread: list[dict] = []
    for member in group.members:
        if member.visible and member.identity is not None:
            continue
        unread.append(
            {
                "location_id": member.record.location_id,
                "root_id": member.record.root_id,
                "relative_path": member.record.relative_path,
                "status": STATUS_UNREAD_PATH
                if member.visible
                else _unread_status(member),
                "detail": member.error or member.path_state,
            }
        )
    return unread


def verify_group(group: Group, budget: Budget) -> str | None:
    """Verify one group.  Returns the budget reason when the run was aborted."""
    unread = _unread_members(group)
    files: list[dict] = []
    aborted: str | None = None
    for bucket in read_targets(group):
        before = budget.read_bytes
        try:
            files.append(_read_one(bucket, budget))
        except BudgetExceeded as exc:
            aborted = exc.reason
            files.append(
                {
                    "root_id": bucket[0].record.root_id,
                    "relative_path": bucket[0].record.relative_path,
                    "location_ids": [item.record.location_id for item in bucket],
                    "status": STATUS_NOT_ATTEMPTED,
                    "registered_sha256": bucket[0].record.content_sha256,
                    "actual_sha256": None,
                    "bytes_read": budget.read_bytes - before,
                    "detail": f"stopped by {exc.reason} limit",
                }
            )
            break
    group.verification = {
        "attempted": True,
        "status": _group_status(files, unread),
        "files": files,
        "unread_members": unread,
        "bytes_read": sum(int(item["bytes_read"]) for item in files),
        "aborted_by": aborted,
    }
    return aborted


def init_verifications(groups: list[Group], *, scan_mode: bool) -> None:
    """Default every group to an explicit, non-claimed verification status."""
    for group in groups:
        group.verification = {
            "attempted": False,
            "status": STATUS_NOT_ATTEMPTED,
            "files": [],
            "unread_members": [],
            "bytes_read": 0,
            "aborted_by": None,
        }
        value = group.account.get("logical_duplicate_bytes")
        if value is None:
            group.verification["status"] = "not_attempted_uncertain_or_unresolved"
        elif int(value) == 0:
            group.verification["status"] = "not_applicable_zero_logical_bytes"
        elif scan_mode:
            group.verification["status"] = "not_attempted_scan_mode"


def verify_groups(groups: list[Group], budget: Budget, *, max_groups: int) -> int:
    """Verify up to ``max_groups`` groups that can actually save bytes."""
    init_verifications(groups, scan_mode=False)
    candidates = [
        group
        for group in groups
        if isinstance(group.account.get("logical_duplicate_bytes"), int)
        and int(group.account["logical_duplicate_bytes"]) > 0
    ]
    candidates.sort(
        key=lambda group: (
            -int(group.account["logical_duplicate_bytes"]),
            group.group_id,
        )
    )
    attempted = 0
    for group in candidates:
        if attempted >= max_groups:
            budget.mark_hit("max_groups")
            break
        aborted = verify_group(group, budget)
        attempted += 1
        if aborted:
            break
    return attempted
