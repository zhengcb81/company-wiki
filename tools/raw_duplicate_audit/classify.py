"""Candidate grouping and byte accounting for the raw duplicate audit.

Four shapes are recognised and must never be summed alike:

1. ``same_path_references``           different source/version/location, one path
2. ``shared_physical_file``           different names, one physical file (hardlink/alias)
3. ``distinct_physical_copies``       different physical files with registered-identical content
4. ``similar_size_different_content`` same size, different registered digest

Only shape 3 contributes logical duplicate bytes.  Unknown physical identity is
reported as uncertain and contributes nothing.
"""

from __future__ import annotations

import errno
import os
import stat as stat_module
from dataclasses import dataclass, field
from pathlib import Path

from .catalog import LocationRecord
from .core import (
    FILE_ATTRIBUTE_REPARSE_POINT,
    HYDRATE_RISK_MASK,
    Budget,
    BudgetExceeded,
    allocation_size,
    normalized,
)

STATE_OK = "ok"
STATE_UNKNOWN_ROOT = "unknown_root"
STATE_ROOT_MISSING = "root_missing"
STATE_OUTSIDE_ROOT = "outside_configured_root"
STATE_MISSING = "missing"
STATE_ACL_DENIED = "acl_denied"
STATE_NOT_A_FILE = "not_a_file"
STATE_REPARSE_POINT = "reparse_point"

VISIBLE_STATES = frozenset({STATE_OK, STATE_REPARSE_POINT})

CLASS_UNRESOLVED = "unresolved"
CLASS_SAME_PATH = "same_path_references"
CLASS_SHARED_FILE = "shared_physical_file"
CLASS_DISTINCT_COPIES = "distinct_physical_copies"
CLASS_UNCERTAIN = "uncertain_physical_identity"
CLASS_SIMILAR = "similar_size_different_content"


@dataclass
class Member:
    """One registered location after read-only filesystem observation."""

    record: LocationRecord
    path_state: str
    normalized_path: str | None
    identity: tuple[int, int] | None
    size: int | None
    allocated_bytes: int | None
    hydrate_risk: bool
    observed_mtime_ns: int | None
    path: Path | None = None
    root_priority: int = 0
    error: str | None = None

    @property
    def visible(self) -> bool:
        return self.path_state in VISIBLE_STATES

    @property
    def locator(self) -> dict:
        return {
            "location_id": self.record.location_id,
            "root_id": self.record.root_id,
            "relative_path": self.record.relative_path,
            "location_status": self.record.location_status,
            "role": self.record.role,
        }


@dataclass
class Group:
    """Locations registered under one content digest."""

    group_id: str
    content_sha256: str
    byte_size: int
    members: list[Member]
    similar: bool = False
    account: dict = field(default_factory=dict)
    verification: dict = field(default_factory=dict)

    @property
    def logical_duplicate_bytes(self) -> int | None:
        return self.account.get("logical_duplicate_bytes")


def _lexical_key(path: Path | str) -> Path:
    return Path(os.path.normcase(os.path.abspath(str(path))))


def _is_proper_child(child: Path, root: Path) -> bool:
    if child == root:
        return False
    try:
        child.relative_to(root)
    except ValueError:
        return False
    return True


def _empty_member(
    record: LocationRecord, state: str, *, error: str | None = None
) -> Member:
    return Member(
        record=record,
        path=None,
        path_state=state,
        normalized_path=None,
        identity=None,
        size=None,
        allocated_bytes=None,
        hydrate_risk=False,
        observed_mtime_ns=None,
        error=error,
    )


def observe(
    records: list[LocationRecord],
    roots,
    *,
    budget: "Budget | None" = None,
    deadline_check_every: int = 256,
) -> tuple[list[Member], list[dict]]:
    """Stat every registered location without following unknown directories."""
    root_map = {root.root_id: root for root in roots}
    root_keys: dict[str, Path] = {}
    for root in roots:
        root_keys[root.root_id] = _lexical_key(root.path)

    members: list[Member] = []
    diagnostics: list[dict] = []
    for index, record in enumerate(records):
        if budget is not None and index % deadline_check_every == 0:
            try:
                budget.consume_deadline()
            except BudgetExceeded:
                diagnostics.append(
                    {
                        "kind": "deadline_stopped_observation_early",
                        "locations_observed": len(members),
                        "locations_total": len(records),
                    }
                )
                break
        root = root_map.get(record.root_id)
        if root is None:
            members.append(_empty_member(record, STATE_UNKNOWN_ROOT))
            continue
        root_path = Path(root.path)
        if not root_path.is_dir():
            members.append(_empty_member(record, STATE_ROOT_MISSING))
            continue
        candidate = root_path / record.relative_path
        lexical = _lexical_key(candidate)
        if not _is_proper_child(lexical, root_keys[record.root_id]):
            members.append(_empty_member(record, STATE_OUTSIDE_ROOT))
            continue
        try:
            stat_result = os.lstat(candidate)
        except OSError as exc:
            if exc.errno in (errno.EACCES, errno.EPERM):
                members.append(_empty_member(record, STATE_ACL_DENIED, error=str(exc)))
            else:
                members.append(_empty_member(record, STATE_MISSING, error=str(exc)))
            continue

        attributes = getattr(stat_result, "st_file_attributes", None)
        risk = bool(attributes is not None and attributes & HYDRATE_RISK_MASK)
        if attributes is not None and attributes & FILE_ATTRIBUTE_REPARSE_POINT:
            members.append(
                Member(
                    record=record,
                    path=candidate,
                    path_state=STATE_REPARSE_POINT,
                    normalized_path=str(lexical),
                    identity=None,
                    size=int(stat_result.st_size),
                    allocated_bytes=None,
                    hydrate_risk=risk,
                    observed_mtime_ns=int(stat_result.st_mtime_ns),
                    root_priority=int(getattr(root, "priority", 0)),
                    error="reparse point not followed",
                )
            )
            continue
        if not stat_module.S_ISREG(stat_result.st_mode):
            members.append(_empty_member(record, STATE_NOT_A_FILE))
            continue
        inode = int(getattr(stat_result, "st_ino", 0) or 0)
        members.append(
            Member(
                record=record,
                path=candidate,
                path_state=STATE_OK,
                normalized_path=str(lexical),
                identity=(int(stat_result.st_dev), inode) if inode else None,
                size=int(stat_result.st_size),
                allocated_bytes=None,
                hydrate_risk=risk,
                observed_mtime_ns=int(stat_result.st_mtime_ns),
                root_priority=int(getattr(root, "priority", 0)),
            )
        )
        if record.absolute_path:
            declared = _lexical_key(record.absolute_path)
            if declared != lexical:
                diagnostics.append(
                    {
                        "kind": "absolute_path_mismatch",
                        "location_id": record.location_id,
                        "root_id": record.root_id,
                    }
                )
    return members, diagnostics


def enforce_containment(groups: list[Group], roots) -> int:
    """Resolve candidate members and drop any that escape the configured roots.

    Realpath resolution is deliberately deferred to this point: only members of
    a multi-reference group are ever resolved, so a junction that leaves a
    configured root is never followed and never read.
    """
    root_real = {root.root_id: normalized(root.path) for root in roots}
    dropped = 0
    for group in groups:
        for member in group.members:
            if not member.visible or member.path is None:
                continue
            if member.path_state == STATE_REPARSE_POINT:
                continue
            real = normalized(member.path)
            if not _is_proper_child(real, root_real[member.record.root_id]):
                member.path_state = STATE_OUTSIDE_ROOT
                member.normalized_path = None
                member.identity = None
                member.error = "resolved outside configured root"
                dropped += 1
            else:
                member.normalized_path = str(real)
    return dropped


def build_groups(members: list[Member]) -> tuple[list[Group], list[dict]]:
    """Group visible members by registered digest; report path conflicts."""
    by_digest: dict[str, list[Member]] = {}
    for member in members:
        digest = member.record.content_sha256
        if not digest:
            continue
        by_digest.setdefault(digest, []).append(member)

    groups: list[Group] = []
    path_owner: dict[str, str] = {}
    conflicts: list[dict] = []
    for digest in sorted(by_digest):
        bucket = by_digest[digest]
        if len(bucket) < 2:
            continue
        group = Group(
            group_id=f"grp:{digest[:16]}",
            content_sha256=digest,
            byte_size=bucket[0].record.registered_size,
            members=bucket,
        )
        groups.append(group)
        for member in bucket:
            key = member.normalized_path or f"loc:{member.record.location_id}"
            owner = path_owner.get(key)
            if owner is None:
                path_owner[key] = group.group_id
            elif owner != group.group_id:
                conflicts.append(
                    {
                        "kind": "path_registered_sha_conflict",
                        "normalized_path_key": _redact(key),
                        "group_ids": sorted({owner, group.group_id}),
                    }
                )
    return groups, conflicts


def _redact(path_key: str) -> str:
    """Never leak a machine absolute path into the Git report."""
    text = str(path_key).replace("\\", "/")
    if ":" in text[:3]:
        return "<absolute-path-redacted>"
    return text


def account_group(group: Group) -> dict:
    """Classify one group and derive its byte contribution."""
    members = group.members
    visible = [member for member in members if member.visible]
    paths = sorted(
        {member.normalized_path for member in visible if member.normalized_path}
    )
    identities = [member.identity for member in visible]
    reference_counts = {
        "sources": len({m.record.source_id for m in members if m.record.source_id}),
        "versions": len(
            {m.record.content_sha256 for m in members if m.record.content_sha256}
        ),
        "documents": len(
            {m.record.document_id for m in members if m.record.document_id}
        ),
        "locations": len(members),
    }
    base = {
        "group_id": group.group_id,
        "content_sha256": group.content_sha256,
        "byte_size": group.byte_size,
        "reference_counts": reference_counts,
        "distinct_paths": len(paths),
        "members_total": len(members),
        "unresolved_members": len(members) - len(visible),
        "hydrate_risk_members": sum(1 for member in members if member.hydrate_risk),
    }

    if group.similar:
        copies = _copies(identities)
        base.update(
            {
                "classification": CLASS_SIMILAR,
                "certainty": "known" if copies is not None else "uncertain",
                "distinct_physical_copies": copies,
                "logical_duplicate_bytes": 0,
                "physical_allocated_bytes": 0
                if copies is not None and copies <= 1
                else None,
            }
        )
        return base

    if not visible:
        base.update(
            {
                "classification": CLASS_UNRESOLVED,
                "certainty": "unresolved",
                "distinct_physical_copies": None,
                "logical_duplicate_bytes": None,
                "physical_allocated_bytes": None,
            }
        )
        return base

    if len(paths) <= 1:
        base.update(
            {
                "classification": CLASS_SAME_PATH,
                "certainty": "known",
                "distinct_physical_copies": 1,
                "logical_duplicate_bytes": 0,
                "physical_allocated_bytes": 0,
            }
        )
        return base

    if any(identity is None for identity in identities):
        base.update(
            {
                "classification": CLASS_UNCERTAIN,
                "certainty": "uncertain",
                "distinct_physical_copies": None,
                "logical_duplicate_bytes": None,
                "physical_allocated_bytes": None,
            }
        )
        return base

    copies = _copies(identities)
    if copies is not None and copies <= 1:
        base.update(
            {
                "classification": CLASS_SHARED_FILE,
                "certainty": "known",
                "distinct_physical_copies": 1,
                "logical_duplicate_bytes": 0,
                "physical_allocated_bytes": 0,
            }
        )
        return base

    base.update(
        {
            "classification": CLASS_DISTINCT_COPIES,
            "certainty": "known",
            "distinct_physical_copies": copies,
            "logical_duplicate_bytes": max(0, (copies or 0) - 1) * int(group.byte_size),
            "physical_allocated_bytes": _redundant_allocated_bytes(visible, identities),
        }
    )
    return base


def _copies(identities: list[tuple[int, int] | None]) -> int | None:
    if not identities or any(identity is None for identity in identities):
        return None
    return len(set(identities))


def _redundant_allocated_bytes(
    visible: list[Member], identities: list[tuple[int, int] | None]
) -> int | None:
    if any(identity is None for identity in identities):
        return None
    representatives: dict[tuple[int, int], Member] = {}
    for member in visible:
        if member.identity is None:
            return None
        representatives.setdefault(member.identity, member)
    ordered = sorted(
        representatives.values(),
        key=lambda member: (member.root_priority, member.normalized_path or ""),
    )
    if len(ordered) <= 1:
        return 0
    if any(member.allocated_bytes is None for member in ordered):
        return None
    return int(sum(int(member.allocated_bytes or 0) for member in ordered[1:]))


def fill_allocations(groups: list[Group]) -> int:
    """Query on-disk allocation only for groups that can hold real duplicates."""
    filled = 0
    for group in groups:
        if group.account.get("classification") != CLASS_DISTINCT_COPIES:
            continue
        for member in group.members:
            if (
                not member.visible
                or member.path is None
                or member.allocated_bytes is not None
            ):
                continue
            member.allocated_bytes = allocation_size(member.path)
            filled += 1
    return filled


def upper_bound_bytes(accounts: list[dict]) -> int:
    total = 0
    for account in accounts:
        value = account.get("logical_duplicate_bytes")
        if value is None:
            continue
        total += int(value)
    return total
