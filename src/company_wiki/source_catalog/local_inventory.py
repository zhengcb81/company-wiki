"""Bounded registered originals, including inactive inventory (never consumer eligibility)."""

from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any
from .resolver import _ReadBudget, _inside_configured_roots, _read_verified_bytes
from .policy import _effective_reusable
from .source_reader import SourceReadError, SourceRef, _relative_segments


@dataclass(frozen=True)
class LocalPrepareLimits:
    max_candidates: int = 16
    max_bytes: int = 268435456
    timeout_seconds: float = 30.0
    max_discovery_groups: int = 256
    max_discovery_entries: int = 4096

    def __post_init__(self):
        if type(self.max_candidates) is not int or not 1 <= self.max_candidates <= 256:
            raise ValueError("invalid local candidate limit")
        if type(self.max_discovery_groups) is not int or not 1 <= self.max_discovery_groups <= 4096:
            raise ValueError("invalid local discovery group limit")
        if type(self.max_discovery_entries) is not int or not 1 <= self.max_discovery_entries <= 65536:
            raise ValueError("invalid local discovery entry limit")
        if type(self.max_bytes) is not int or not 1 <= self.max_bytes <= 1073741824:
            raise ValueError("invalid local byte limit")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or not 0 < self.timeout_seconds <= 600
        ):
            raise ValueError("invalid local deadline")


class LocalReadBudget(_ReadBudget):
    def __init__(self, limits: LocalPrepareLimits):
        super().__init__(
            max_candidates=limits.max_candidates, max_bytes=limits.max_bytes
        )
        self.deadline = time.monotonic() + limits.timeout_seconds
        self.max_discovery_groups = limits.max_discovery_groups
        self.max_discovery_entries = limits.max_discovery_entries
        self.discovery_groups = 0
        self.discovery_entries = 0

    def check(self):
        if time.monotonic() >= self.deadline:
            raise SourceReadError("unavailable", "local_prepare_deadline")
        if self.cancelled:
            raise SourceReadError("unavailable", "cancelled")

    def observe_group(self):
        self.check()
        self.discovery_groups += 1
        if self.discovery_groups > self.max_discovery_groups:
            raise SourceReadError("unavailable", "local_source_group_limit")

    def observe_entry(self):
        self.check()
        self.discovery_entries += 1
        if self.discovery_entries > self.max_discovery_entries:
            raise SourceReadError("unavailable", "local_discovery_entry_limit")

    def read_metadata_observation(self, path, *, root):
        """Read one small JSON under the current aggregate byte/deadline ceiling."""
        self.check()
        resolved = Path(os.path.realpath(path))
        try:
            resolved.relative_to(root.resolve())
        except ValueError:
            raise SourceReadError("blocked", "metadata_path_outside_root") from None
        try:
            before = resolved.stat()
        except FileNotFoundError:
            return None
        from .resolver import _needs_hydration
        if _needs_hydration(before):
            raise SourceReadError("unavailable", "placeholder_not_hydrated")
        if not resolved.is_file() or before.st_size > 131072:
            raise SourceReadError("unavailable", "local_metadata_byte_limit")
        if before.st_size > self.max_bytes - self.bytes_read:
            raise SourceReadError("unavailable", "budget_exceeded")
        with resolved.open("rb") as stream:
            data = stream.read(min(131073, self.max_bytes - self.bytes_read + 1))
        stop = self.charge(len(data))
        if stop:
            raise SourceReadError("unavailable", stop)
        after = resolved.stat()
        if len(data) > 131072 or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise SourceReadError("unavailable", "local_metadata_changed")
        try:
            value = json.loads(data)
        except (ValueError, UnicodeError, RecursionError):
            raise SourceReadError("blocked", "local_metadata_unreadable") from None
        if not isinstance(value, dict):
            raise SourceReadError("blocked", "local_metadata_unreadable")
        return value, hashlib.sha256(data).hexdigest()

    def metadata_reader(self, root):
        def read(path):
            observation = self.read_metadata_observation(path, root=root)
            return observation[0] if observation is not None else {}
        return read

    def walk_files(self, root):
        """Only explicit registration groups; bounded recursive file enumeration."""
        from .models import DOCUMENT_EXTENSIONS
        from .resolver import _needs_hydration
        stack = [root]
        while stack:
            directory = stack.pop()
            self.observe_group()
            with os.scandir(directory) as entries:
                for entry in entries:
                    self.observe_entry()
                    if entry.is_symlink():
                        continue
                    status = entry.stat(follow_symlinks=False)
                    if getattr(status, "st_file_attributes", 0) & 0x400:
                        continue
                    if _needs_hydration(status):
                        raise SourceReadError("unavailable", "placeholder_not_hydrated")
                    path = Path(entry.path)
                    if entry.is_dir(follow_symlinks=False):
                        from .adapters.common import _SKIP_DIRS
                        if entry.name not in _SKIP_DIRS:
                            stack.append(path)
                    elif path.suffix.lower() in DOCUMENT_EXTENSIONS:
                        yield path

    def hash_file(self, path, *, root, original=True):
        """Stream a registration SHA under the same remaining read budget."""
        self.check()
        resolved = Path(os.path.realpath(path))
        try:
            resolved.relative_to(root.resolve())
        except ValueError:
            raise SourceReadError("blocked", "artifact_path_outside_allowed_root") from None
        before = resolved.stat()
        from .resolver import _needs_hydration
        if _needs_hydration(before):
            raise SourceReadError("unavailable", "placeholder_not_hydrated")
        if path.is_symlink() or getattr(path.lstat(), "st_file_attributes", 0) & 0x400:
            raise SourceReadError("blocked", "artifact_path_outside_allowed_root")
        if before.st_size > self.max_bytes - self.bytes_read:
            raise SourceReadError("unavailable", "budget_exceeded")
        if original:
            stop = self.take_candidate()
            if stop:
                raise SourceReadError("unavailable", stop)
        digest = hashlib.sha256()
        size = 0
        with resolved.open("rb") as stream:
            while True:
                self.check()
                chunk = stream.read(min(65536, self.max_bytes - self.bytes_read + 1))
                if not chunk:
                    break
                stop = self.charge(len(chunk))
                if stop:
                    raise SourceReadError("unavailable", stop)
                digest.update(chunk)
                size += len(chunk)
        self.check()
        after = resolved.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or size != after.st_size:
            raise SourceReadError("unavailable", "local_source_changed")
        return digest.hexdigest(), size

    def take_candidate(self):
        self.check()
        return super().take_candidate()

    def charge(self, size):
        self.check()
        return super().charge(size)


@dataclass(frozen=True)
class LocalOriginal:
    ref: SourceRef
    data: bytes
    locations: tuple[tuple[str, Path, Any], ...]
    failures: tuple[str, ...]


def observe_document(catalog, document_id: str) -> dict[str, Any]:
    row = catalog.reader.exact_source_version(document_id)
    if row is None:
        raise SourceReadError("not_indexed", "document_not_indexed")
    audits = [
        dict(x)
        for x in catalog.reader.fetchall(
            "SELECT * FROM document_retire_audit WHERE document_id=? ORDER BY rowid LIMIT 65",
            (document_id,),
        )
    ]
    if len(audits) > 64:
        raise SourceReadError("blocked", "retirement_history_limit")
    locations = [
        dict(x)
        for x in catalog.reader.exact_source_locations(document_id, row["source_id"])
    ]
    if len(locations) > 256:
        raise SourceReadError("unavailable", "local_location_limit")
    assertions = [
        dict(x)
        for x in catalog.reader.fetchall(
            "SELECT assertion_id,created_at FROM source_metadata_assertions WHERE document_id=? ORDER BY rowid DESC LIMIT 1",
            (document_id,),
        )
    ]
    return {
        "version": dict(row),
        "retire_audit": audits,
        "locations": locations,
        "latest_assertion": assertions,
    }


def metadata_retirement(observation: dict[str, Any]) -> bool:
    """Closed known-producer history, never a substring or issuer/hash whitelist."""
    audits = observation["retire_audit"]
    if not audits:
        return False
    proven = False
    for audit in audits:
        pair = (audit["reason"], audit["created_by"])
        if pair == (
            "legacy sidecar lacks source_url; batch governance Phase 15.6 (F13)",
            "phase-15.6-governance",
        ):
            proven = True
        elif (
            pair
            == (
                "phase-15.6 audit reconciliation (reconcile-retire)",
                "reconcile-retire-20260806",
            )
            and proven
        ):
            pass
        elif pair == ("source_metadata_insufficient", "automated-source-metadata"):
            proven = True
        else:
            return False
    return proven


def verify_registered_original(
    catalog, ref: SourceRef, *, budget: LocalReadBudget
) -> LocalOriginal:
    """Verify actual registered inactive bytes without inventing an active handle."""
    row = catalog.reader.exact_source_version(ref.document_id)
    if row is None or (
        row["source_id"],
        row["content_sha256"],
        row["byte_size"],
        row["mime_type"],
    ) != (ref.source_id, ref.content_sha256, ref.byte_size, ref.mime_type):
        raise SourceReadError("unavailable", "source_ref_changed")
    roots = {x.root_id: x for x in catalog.config.roots}
    rows = catalog.reader.exact_source_locations(ref.document_id, ref.source_id)
    if len(rows) > 256:
        raise SourceReadError("unavailable", "local_location_limit")
    valid = []
    failures = []
    first = None
    for loc in sorted(
        rows,
        key=lambda x: (
            roots[x["root_id"]].priority if x["root_id"] in roots else 999999,
            x["root_id"],
            x["relative_path"],
        ),
    ):
        budget.check()
        root = roots.get(loc["root_id"])
        if (
            root is None
            or not _effective_reusable(root, catalog.config)
            or (root.allowed_statuses and "active" not in root.allowed_statuses)
        ):
            failures.append("root_admission_denied")
            continue
        if (
            root.allowed_document_kinds
            and row["document_kind"] not in root.allowed_document_kinds
        ) or (root.max_file_size is not None and ref.byte_size > root.max_file_size):
            failures.append("root_admission_denied")
            continue
        segments = _relative_segments(str(loc["relative_path"]))
        if (
            loc["role"] != "original_primary"
            or loc["location_status"] not in {"active", "retired"}
            or segments is None
            or ".rejections" in segments
        ):
            failures.append("location_ineligible")
            continue
        resolved = Path(os.path.realpath(root.path.joinpath(*segments)))
        if not _inside_configured_roots(resolved, (root,)):
            failures.append("artifact_path_outside_allowed_root")
            continue
        data, status, reason, detail = _read_verified_bytes(
            resolved,
            expected_sha256=ref.content_sha256,
            expected_byte_size=ref.byte_size,
            budget=budget,
            retain_bytes=first is None,
        )
        if status:
            failures.append(reason or status)
            if reason in {"cancelled", "budget_exceeded"}:
                break
            continue
        if first is None:
            first = data
        valid.append((loc["location_id"], resolved, root))
    if first is None:
        raise SourceReadError(
            "unavailable", "no_verified_location", ",".join(sorted(set(failures)))
        )
    return LocalOriginal(ref, first, tuple(valid), tuple(failures))
