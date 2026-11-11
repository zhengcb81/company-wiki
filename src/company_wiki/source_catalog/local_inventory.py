"""Bounded registered originals, including inactive inventory (never consumer eligibility)."""

from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import time
from typing import Any, NoReturn
from company_wiki.source_contract.source_version import SourceReadError, SourceRef

from .read_budget import ReadBudget
from .location_read_contract import RegisteredLocationBinding
from .resolver import SourceResolver
from .source_location import is_hydration_required, resolve_source_location
from company_wiki.source_catalog.filesystem_discovery import SKIP_DIRS


@dataclass(frozen=True)
class LocalPrepareLimits:
    max_candidates: int = 16
    max_bytes: int = 268435456
    timeout_seconds: float = 30.0
    max_discovery_groups: int = 256
    max_discovery_entries: int = 4096

    def __post_init__(self):
        if type(self.max_candidates) is not int or self.max_candidates <= 0:
            raise ValueError("invalid local candidate limit")
        if type(self.max_discovery_groups) is not int or self.max_discovery_groups <= 0:
            raise ValueError("invalid local discovery group limit")
        if type(self.max_discovery_entries) is not int or self.max_discovery_entries <= 0:
            raise ValueError("invalid local discovery entry limit")
        if type(self.max_bytes) is not int or self.max_bytes <= 0:
            raise ValueError("invalid local byte limit")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or not math.isfinite(self.timeout_seconds)
            or self.timeout_seconds <= 0
        ):
            raise ValueError("invalid local deadline")


class LocalReadBudget(ReadBudget):
    def __init__(self, limits: LocalPrepareLimits):
        super().__init__(
            max_candidates=limits.max_candidates, max_bytes=limits.max_bytes
        )
        self.limits = limits
        self.started_at = time.monotonic()
        self.deadline = self.started_at + limits.timeout_seconds
        self.phase = "preparation"
        self.triggered_bound: str | None = None
        self.observed_charge_bytes = 0
        self.max_discovery_groups = limits.max_discovery_groups
        self.max_discovery_entries = limits.max_discovery_entries
        self.discovery_groups = 0
        self.discovery_entries = 0

    def begin_request(self):
        """Keep this parent operation's account across nested Resolver calls."""
        self.check()

    def _stop(self, reason: str, bound: str) -> NoReturn:
        self.triggered_bound = bound
        raise SourceReadError("unavailable", reason)

    def check(self):
        if time.monotonic() >= self.deadline:
            self._stop("local_prepare_deadline", "timeout_seconds")
        if self.cancelled:
            self._stop("cancelled", "cancelled")

    def observation(self, *, reason: str) -> dict[str, Any]:
        """Read-only owner measurements, not network usage or a fee ledger.

        A rejected tail can already have been read when charge() is called.
        Keep it separate from bytes accepted into the existing budget. A
        generic refusal from another owner leaves triggered_bound unknown.
        """
        return {
            "schema_version": "local-read-budget/1",
            "operation": "local_read_budget",
            "usage_scope": "local_original_verification",
            "phase": self.phase,
            "reason": reason,
            "limits": asdict(self.limits),
            "consumed": {
                "candidates": self.candidates,
                "charged_read_bytes": self.bytes_read,
                "observed_charge_bytes": self.observed_charge_bytes,
                "discovery_groups": self.discovery_groups,
                "discovery_entries": self.discovery_entries,
                "elapsed_seconds": round(max(0.0, time.monotonic() - self.started_at), 6),
            },
            "triggered_bound": self.triggered_bound,
        }

    def observe_group(self):
        self.phase = "source_group_discovery"
        self.check()
        self.discovery_groups += 1
        if self.discovery_groups > self.max_discovery_groups:
            self._stop("local_source_group_limit", "max_discovery_groups")

    def observe_entry(self):
        self.phase = "source_entry_discovery"
        self.check()
        self.discovery_entries += 1
        if self.discovery_entries > self.max_discovery_entries:
            self._stop("local_discovery_entry_limit", "max_discovery_entries")

    def read_metadata_observation(self, path, *, root):
        """Read one small JSON under the current aggregate byte/deadline ceiling."""
        self.phase = "metadata_read"
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
        if is_hydration_required(before):
            raise SourceReadError("unavailable", "placeholder_not_hydrated")
        if not resolved.is_file():
            raise SourceReadError("blocked", "local_metadata_unreadable")
        if before.st_size > self.max_bytes - self.bytes_read:
            self._stop("budget_exceeded", "max_bytes")
        chunks = []
        with resolved.open("rb") as stream:
            while True:
                self.check()
                # Chunk size is an IO implementation detail, not a document cap.
                chunk = stream.read(min(65536, self.max_bytes - self.bytes_read + 1))
                if not chunk:
                    break
                stop = self.charge(len(chunk))
                if stop:
                    raise SourceReadError("unavailable", stop)
                chunks.append(chunk)
        data = b"".join(chunks)
        after = resolved.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
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
                    if is_hydration_required(status):
                        raise SourceReadError("unavailable", "placeholder_not_hydrated")
                    path = Path(entry.path)
                    if entry.is_dir(follow_symlinks=False):
                        if entry.name not in SKIP_DIRS:
                            stack.append(path)
                    elif path.suffix.lower() in DOCUMENT_EXTENSIONS:
                        yield path

    def hash_file(self, path, *, root, original=True):
        """Stream a registration SHA under the same remaining read budget."""
        self.phase = "original_read" if original else "auxiliary_read"
        self.check()
        resolved = Path(os.path.realpath(path))
        try:
            resolved.relative_to(root.resolve())
        except ValueError:
            raise SourceReadError("blocked", "artifact_path_outside_allowed_root") from None
        before = resolved.stat()
        if is_hydration_required(before):
            raise SourceReadError("unavailable", "placeholder_not_hydrated")
        if path.is_symlink() or getattr(path.lstat(), "st_file_attributes", 0) & 0x400:
            raise SourceReadError("blocked", "artifact_path_outside_allowed_root")
        if before.st_size > self.max_bytes - self.bytes_read:
            self._stop("budget_exceeded", "max_bytes")
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
        self.phase = "original_read"
        self.check()
        stop = super().take_candidate()
        if stop:
            self.triggered_bound = "cancelled" if stop == "cancelled" else "max_candidates"
        return stop

    def charge(self, size):
        # Local storage calls this after reading a chunk. Observe even a chunk
        # rejected by deadline/cancellation/bytes without changing old decisions.
        if type(size) is int and size >= 0:
            self.observed_charge_bytes += size
        self.check()
        stop = super().charge(size)
        if stop:
            self.triggered_bound = "cancelled" if stop == "cancelled" else "max_bytes"
        return stop


@dataclass(frozen=True)
class LocalOriginal:
    ref: SourceRef
    data: bytes
    locations: tuple[RegisteredLocationBinding, ...]
    failures: tuple[str, ...]


@dataclass(frozen=True)
class RegisteredSidecarObservation:
    metadata: dict[str, Any]
    content_sha256: str
    original_name: str
    locator: str


def _inventory_rows(catalog, sql, parameters, *, budget):
    """Page indexed metadata under the existing discovery account.

    Pages are IO granularity, not a maximum row count. SQL metadata is not an
    original-file read; each observed row charges discovery work, not invented
    serialized byte costs. No partial observation escapes a depleted account.
    """
    after = 0
    while True:
        budget.check()
        size = min(128, max(1, budget.max_discovery_entries - budget.discovery_entries + 1))
        rows = catalog.reader.fetchall(sql + " AND rowid>? ORDER BY rowid LIMIT ?", (*parameters, after, size))
        budget.check()
        for row in rows:
            budget.observe_entry()
            observed = dict(row)
            after = observed.pop("_inventory_rowid")
            yield observed
        if len(rows) < size:
            return


def _location_rows(catalog, document_id, source_id, *, budget):
    return _inventory_rows(catalog,
        "SELECT rowid AS _inventory_rowid,location_id,document_id,source_id,root_id,relative_path,role,location_status,manifest_json "
        "FROM locations WHERE document_id=? AND source_id=?",
        (document_id, source_id), budget=budget)


def observe_document(catalog, document_id: str, *, budget: LocalReadBudget | None = None) -> dict[str, Any]:
    budget = budget if budget is not None else LocalReadBudget(LocalPrepareLimits())
    budget.check()
    row = catalog.reader.exact_source_version(document_id)
    if row is None:
        raise SourceReadError("not_indexed", "document_not_indexed")
    budget.observe_entry()
    audits = list(_inventory_rows(catalog,
        "SELECT rowid AS _inventory_rowid,* FROM document_retire_audit WHERE document_id=?",
        (document_id,), budget=budget))
    locations = sorted(_location_rows(catalog, document_id, row["source_id"], budget=budget),
                       key=lambda x: (x["root_id"], x["relative_path"], x["location_id"]))
    assertions = [
        dict(x)
        for x in catalog.reader.fetchall(
            "SELECT assertion_id,created_at FROM source_metadata_assertions WHERE document_id=? ORDER BY rowid DESC LIMIT 1",
            (document_id,),
        )
    ]
    for _ in assertions:
        budget.observe_entry()
    budget.check()
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
    resolver = SourceResolver(catalog)
    budget.check()
    rows = list(_location_rows(catalog, ref.document_id, ref.source_id, budget=budget))
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
        if root is None:
            failures.append("root_admission_denied")
            continue
        result = resolver.read_registered_original(
            ref,
            str(loc["location_id"]),
            budget=budget,
            retain_bytes=first is None,
        )
        if not result.ok:
            reason, detail, status = result.reason, result.detail, result.status
            failures.append(
                "local_original_missing"
                if reason == "read_failed" and detail == "FileNotFoundError"
                else (reason or status)
            )
            if reason in {"cancelled", "budget_exceeded"}:
                raise SourceReadError(status, reason, detail)
            continue
        if first is None:
            assert result.observation is not None
            first = result.observation.data
        if result.binding is None:
            raise SourceReadError("unavailable", "location_binding_missing")
        valid.append(result.binding)
    if first is None:
        if failures and set(failures) == {"local_original_missing"}:
            raise SourceReadError("not_found", "local_original_missing")
        raise SourceReadError(
            "unavailable", "no_verified_location", ",".join(sorted(set(failures)))
        )
    return LocalOriginal(ref, first, tuple(valid), tuple(failures))


def read_registered_sidecar(
    catalog,
    ref: SourceRef,
    location: RegisteredLocationBinding,
    *,
    kind: str,
    budget: LocalReadBudget,
) -> RegisteredSidecarObservation | None:
    """Read a known adjacent sidecar without exporting its filesystem path.

    ``location`` is the binding emitted with the verified original. Resolver
    re-reads the catalog mapping before each metadata read and refuses a root or
    relative-locator rebind. The only accepted sidecar forms are the two
    registration conventions already consumed by local reconciliation.
    """
    if kind not in {"sec_provider_meta", "source_sidecar"}:
        raise ValueError("unsupported registered sidecar kind")
    budget.check()
    resolver = SourceResolver(catalog)
    descriptor = resolver.describe_registered_location(
        ref, location, budget=budget
    )
    if not descriptor.ok:
        raise SourceReadError(descriptor.status, descriptor.reason, descriptor.detail)
    roots = {root.root_id: root for root in catalog.config.roots}
    root = roots.get(descriptor.location.root_id)
    if root is None:
        raise SourceReadError("unavailable", "location_root_missing")
    try:
        original_path = resolve_source_location(root, descriptor.location.relative_path)
    except ValueError as exc:
        reason = getattr(exc, "reason", "artifact_path_outside_allowed_root")
        raise SourceReadError("unavailable", reason) from None
    sidecar_path = (
        original_path.with_name("meta.json")
        if kind == "sec_provider_meta"
        else original_path.with_name(original_path.name + ".source.json")
    )
    observation = budget.read_metadata_observation(sidecar_path, root=root.path)
    after_read = resolver.describe_registered_location(
        ref, location, budget=budget
    )
    if not after_read.ok or after_read.binding != location:
        raise SourceReadError(
            after_read.status or "unavailable",
            after_read.reason or "location_binding_changed",
            after_read.detail,
        )
    if observation is None:
        return None
    metadata, digest = observation
    return RegisteredSidecarObservation(
        metadata=metadata,
        content_sha256=digest,
        original_name=original_path.name,
        locator=(
            "registered-provider-cache:/meta.json"
            if kind == "sec_provider_meta"
            else "registered-source-sidecar:/.source.json"
        ),
    )
