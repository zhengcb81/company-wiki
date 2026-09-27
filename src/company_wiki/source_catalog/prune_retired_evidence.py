"""Prune retired documents' evidence spans after the retention window (Phase 2.3).

Repaired for the five DW15-REPAIR defects (owner ruling A-1, 2026-09-22; the
proposal this implements is I-15-A decision.md / W15-R1..R5).  Repaired
behaviour:

* **D1 (空目录也删)** — deletion is authorised *only* by at least one verified
  archive manifest: manifest exists and declares ``ok``, its declared sha256
  matches the archive bytes, and the per-row digests match the rows re-read from
  that archive.  An empty directory, a bare snapshot without a manifest, a
  manifest whose snapshot is missing/corrupt, and "the directory is old"
  authorise nothing: dry-run reports ``due=false`` and apply deletes 0 rows.
  When a verified *due* manifest exists, apply deletes exactly the
  manifest-authorised, still-retired, digest-matching rows.
* **D2 (同日覆写)** — receipts are uniquely named
  (``prune-retired-<token>.json``): two runs in the same second each keep their
  own receipt; a receipt is only ever replaced by its own run's atomic update.
* **D3 (时钟取目录名)** — no system clock is read anywhere in this module.  The
  caller injects ``now`` (required, timezone-aware); the retention window is
  ``now - manifest.verified_completed_at``, never a directory/file name and
  never the machine clock.
* **D4 (TOCTOU)** — apply freezes an exact plan (span ids + row digests +
  archive sha256s + plan hash).  Inside ``CatalogOperationLock`` it re-verifies
  every archive byte against its sha256 and every planned row's digest/status
  *before the first delete*; each batch then re-reads and re-verifies its rows
  **inside the same transaction** that deletes them.  Any mismatch raises
  ``PruneRefused`` and the whole apply aborts with 0 rows deleted — silently
  narrowing the set is forbidden.
* **D5 (崩溃后不可恢复)** — a *pending* receipt naming the full plan is
  published atomically **before the first delete**, updated atomically after
  every committed batch, and finalized to ``complete`` at the end.  A kill at
  any point leaves the snapshot complete and every deleted id recoverable as a
  subset of (receipt plan ∩ verified snapshot), so the exact deleted set is a
  durable fact rather than a directory listing.

Dry-run by default; ``apply=True`` is explicit and runs under
``CatalogOperationLock``.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .lock import CatalogOperationLock
from .models import CatalogConfig
from .store import CatalogStore

RETENTION_DAYS = 90
BATCH_SIZE = 100_000
MANIFEST_SCHEMA = "archive-verified-manifest-1.0"
PLAN_SCHEMA = "exact-prune-plan-dw15.1"
RECEIPT_SCHEMA = "prune-retired-receipt-1.0"

# every column of evidence_spans plus the document status; ``__source_status``
# is excluded from digests so live rows hash exactly like archived rows.
_SPAN_STATE = """SELECT e.span_id, e.document_id, e.source_id, e.locator,
                        e.page_number, e.paragraph_index, e.table_index,
                        e.raw_text, e.span_json, e.parser_name,
                        e.parser_version, e.parse_status,
                        d.source_status AS __source_status
                 FROM evidence_spans e
                 JOIN documents d ON d.document_id = e.document_id
                 WHERE e.span_id IN ({placeholders})"""


class PruneRefused(RuntimeError):
    """Business refusal: the frozen plan no longer matches the state the delete
    would act on (or the plan object itself is inconsistent).  The whole apply
    aborts; nothing is deleted."""


@dataclass(frozen=True)
class VerifiedArchive:
    manifest_path: str
    archive_path: str
    archive_sha256: str
    verified_completed_at: str
    row_digests: Mapping[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_path": self.manifest_path,
            "archive_path": self.archive_path,
            "archive_sha256": self.archive_sha256,
            "verified_completed_at": self.verified_completed_at,
            "row_digests": dict(self.row_digests),
        }


@dataclass(frozen=True)
class PrunePlan:
    span_ids: tuple[str, ...]
    row_digests: Mapping[str, str]
    archives: tuple[VerifiedArchive, ...]
    retention_days: int
    plan_hash: str

    @staticmethod
    def compute_hash(span_ids: Iterable[str], row_digests: Mapping[str, str],
                     archives: Sequence[VerifiedArchive],
                     retention_days: int) -> str:
        ids = sorted(span_ids)
        payload = {
            "schema_version": PLAN_SCHEMA,
            "retention_days": retention_days,
            "span_ids": ids,
            "row_digests": {sid: row_digests[sid] for sid in ids},
            "archives": sorted(
                ({"archive_path": va.archive_path,
                  "archive_sha256": va.archive_sha256,
                  "verified_completed_at": va.verified_completed_at}
                 for va in archives),
                key=lambda item: item["archive_path"]),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PLAN_SCHEMA,
            "span_ids": list(self.span_ids),
            "row_digests": dict(self.row_digests),
            "archives": [va.to_dict() for va in self.archives],
            "retention_days": self.retention_days,
            "plan_hash": self.plan_hash,
        }


@dataclass(frozen=True)
class PruneReport:
    dry_run: bool
    retired_documents: int
    span_rows: int
    oldest_archive: str | None
    retention_days: int
    due: bool
    deleted_rows: int = 0
    receipt_path: str | None = None
    plan_hash: str | None = None
    plan_span_ids: tuple[str, ...] = ()
    already_absent: tuple[str, ...] = ()
    verified_archives: int = 0
    manifest_problems: tuple[str, ...] = ()
    plan: PrunePlan | None = None

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        d.pop("plan", None)
        if self.receipt_path is None:
            d.pop("receipt_path", None)
        d["plan_span_ids"] = list(self.plan_span_ids)
        d["already_absent"] = list(self.already_absent)
        d["manifest_problems"] = list(self.manifest_problems)
        return d


# ---------------------------------------------------------------------------
# D1/D3 helpers: verified manifests, digests, retention clock
# ---------------------------------------------------------------------------


def _row_digest(row: Mapping[str, Any]) -> str:
    payload = json.dumps(dict(row), sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_snapshot(path: Path) -> tuple[list[str], dict[str, str]]:
    ids: list[str] = []
    digests: dict[str, str] = {}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            span_id = row["span_id"]
            if span_id in digests:
                raise ValueError(f"duplicate span_id {span_id} in {path}")
            ids.append(span_id)
            digests[span_id] = _row_digest(row)
    return ids, digests


def _resolve_archive_path(manifest: Mapping[str, Any],
                          manifest_path: Path) -> Path | None:
    raw = manifest.get("archive_path")
    if not isinstance(raw, str) or not raw:
        return None
    candidate = Path(raw)
    if candidate.is_file():
        return candidate
    sibling = manifest_path.parent / Path(raw).name
    if sibling.is_file():
        return sibling
    return None


# ---------------------------------------------------------------------------
# Complexity ratchet (FC-1204, owner §四十二 裁定一, 2026-09-27): split only;
# behaviour unchanged.
#   * _load_verified_archives 16 -> 4 (frozen 12): the verification ladder
#     became one top-level function per concern — same check order, same
#     problem strings, nothing dropped.
#   * prune_retired_evidence 27 -> 6 (frozen 12): plan selection, due/oldest
#     and the locked apply (pre-delete re-verify, pending receipt, batch
#     delete) each moved into their own top-level function; the entry point
#     only dispatches.
# ---------------------------------------------------------------------------


def _verify_one_manifest(
        manifest_path: Path) -> tuple[VerifiedArchive | None, str | None]:
    """Verify one manifest end to end (W15-R1/D1).

    Returns ``(archive, None)`` when every check passes, else
    ``(None, problem)`` with the exact problem string the ladder used to
    append — in the exact order it used to run the checks.
    """
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"{manifest_path}: unreadable manifest ({exc})"
    problem = _manifest_decl_problem(manifest_path, data)
    if problem is not None:
        return None, problem
    archive_path = _resolve_archive_path(data, manifest_path)
    if archive_path is None:
        return None, f"{manifest_path}: archive file missing"
    actual_sha, problem = _archive_bytes_problem(manifest_path, archive_path, data)
    if problem is not None:
        return None, problem
    return _verified_archive(manifest_path, archive_path, data, actual_sha)


def _manifest_decl_problem(manifest_path: Path, data: Any) -> str | None:
    """Declaration checks: the manifest's schema and ok flag (D1)."""
    if data.get("schema_version") != MANIFEST_SCHEMA:
        return f"{manifest_path}: unsupported schema_version"
    if data.get("ok") is not True:
        return f"{manifest_path}: manifest not ok"
    return None


def _archive_bytes_problem(manifest_path: Path, archive_path: Path,
                           data: Any) -> tuple[str | None, str | None]:
    """Byte checks: declared size, then sha256 of the archive bytes (D1).

    Returns ``(actual_sha256, None)`` on success, ``(None, problem)`` on the
    first mismatch.
    """
    if archive_path.stat().st_size != data.get("archive_bytes"):
        return None, f"{manifest_path}: archive size mismatch"
    try:
        actual_sha = _sha256_file(archive_path)
    except OSError as exc:
        return None, f"{manifest_path}: archive unreadable ({exc})"
    if actual_sha != data.get("archive_sha256"):
        return None, f"{manifest_path}: archive sha256 mismatch"
    return actual_sha, None


def _verified_archive(manifest_path: Path, archive_path: Path, data: Any,
                      actual_sha: str) -> tuple[VerifiedArchive | None,
                                                str | None]:
    """Snapshot checks: row count, per-row digests, verified clock (D1/D3)."""
    try:
        ids, digests = _read_snapshot(archive_path)
    except (OSError, EOFError, ValueError, json.JSONDecodeError) as exc:
        return None, f"{manifest_path}: archive corrupt ({exc})"
    if len(ids) != data.get("rows_in_archive"):
        return None, f"{manifest_path}: row count mismatch"
    if dict(digests) != dict(data.get("row_digests") or {}):
        return None, f"{manifest_path}: row digest mismatch"
    completed_at = data.get("verified_completed_at")
    try:
        _parse_utc(completed_at)
    except (TypeError, ValueError):
        return None, f"{manifest_path}: bad verified_completed_at"
    return VerifiedArchive(
        manifest_path=str(manifest_path),
        archive_path=str(archive_path),
        archive_sha256=actual_sha,
        verified_completed_at=completed_at,
        row_digests=dict(digests),
    ), None


def _load_verified_archives(
        archive_root: Path) -> tuple[list[VerifiedArchive], list[str]]:
    """Verify every manifest under ``archive_root/archive`` (W15-R1).

    Only manifests that fully verify become ``VerifiedArchive``; anything else
    is recorded as a problem and authorises nothing (D1).
    """
    verified: list[VerifiedArchive] = []
    problems: list[str] = []
    base = archive_root / "archive"
    if not base.exists():
        return verified, problems
    for manifest_path in sorted(base.rglob("*.manifest.json")):
        archive, problem = _verify_one_manifest(manifest_path)
        if problem is not None:
            problems.append(problem)
            continue
        verified.append(archive)
    return verified, problems


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _is_due(archive: VerifiedArchive, now: datetime,
            retention_days: int) -> bool:
    """D3: the retention clock is verified_completed_at vs the injected now —
    never a directory name, never the machine clock (W15-R3)."""
    age = now.astimezone(timezone.utc) - _parse_utc(archive.verified_completed_at)
    return age.days >= retention_days


def _span_states(database_path: Path,
                 span_ids: Sequence[str]) -> dict[str, tuple[str, str]]:
    """{span_id: (row_digest, document status)} for rows that exist now."""
    states: dict[str, tuple[str, str]] = {}
    if not span_ids:
        return states
    conn = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        ids = list(span_ids)
        for start in range(0, len(ids), 400):
            chunk = ids[start:start + 400]
            placeholders = ",".join("?" * len(chunk))
            for row in conn.execute(_SPAN_STATE.format(placeholders=placeholders),
                                    chunk):
                digest_row = {key: row[key] for key in row.keys()
                              if key != "__source_status"}
                states[row["span_id"]] = (_row_digest(digest_row),
                                          row["__source_status"])
    finally:
        conn.close()
    return states


def _counts(database_path: Path) -> tuple[int, int]:
    conn = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
    try:
        span_rows = int(conn.execute(
            "SELECT COUNT(*) FROM evidence_spans WHERE document_id IN "
            "(SELECT document_id FROM documents WHERE source_status='retired')"
        ).fetchone()[0])
        retired = int(conn.execute(
            "SELECT COUNT(*) FROM documents WHERE source_status='retired'"
        ).fetchone()[0])
    finally:
        conn.close()
    return retired, span_rows


def _build_plan(config: CatalogConfig, archive_root: Path, now: datetime,
                retention_days: int) -> tuple[PrunePlan, list[VerifiedArchive],
                                              list[str]]:
    verified, problems = _load_verified_archives(archive_root)
    due_archives = [va for va in verified if _is_due(va, now, retention_days)]
    authorised: dict[str, str] = {}
    for archive in due_archives:
        for span_id, digest in archive.row_digests.items():
            if span_id in authorised and authorised[span_id] != digest:
                # ambiguous authorisation: refuse to guess (W15-R2)
                authorised.pop(span_id, None)
                problems.append(
                    f"conflicting verified digests for {span_id}; excluded")
                continue
            authorised.setdefault(span_id, digest)
    states = _span_states(config.database_path, sorted(authorised))
    plan_ids: list[str] = []
    plan_digests: dict[str, str] = {}
    for span_id in sorted(authorised):
        state = states.get(span_id)
        if state is None:
            continue                      # already absent: nothing to delete
        live_digest, status = state
        if status == "retired" and live_digest == authorised[span_id]:
            plan_ids.append(span_id)
            plan_digests[span_id] = live_digest
        # present-but-changed / reactivated rows are simply unauthorised (W15-R2)
    plan = PrunePlan(
        span_ids=tuple(plan_ids),
        row_digests=plan_digests,
        archives=tuple(due_archives),
        retention_days=retention_days,
        plan_hash=PrunePlan.compute_hash(plan_ids, plan_digests,
                                         due_archives, retention_days),
    )
    return plan, verified, problems


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    """D5: temp + fsync + atomic replace (own run's receipt only; names are
    uuid-unique so no other run's receipt can be targeted — D2)."""
    tmp = path.with_name(f"{path.name}.partial-{uuid.uuid4().hex[:8]}")
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def _chunks(items: Sequence[str], size: int) -> Iterable[list[str]]:
    for start in range(0, len(items), size):
        yield list(items[start:start + size])


def _verify_archives_on_disk(plan: PrunePlan) -> None:
    """D4: re-read every archive byte before the first delete."""
    for archive in plan.archives:
        path = Path(archive.archive_path)
        if not path.is_file():
            raise PruneRefused(f"archive vanished after plan: {path}")
        if _sha256_file(path) != archive.archive_sha256:
            raise PruneRefused(f"archive changed after plan: {path}")


def prune_retired_evidence(
    config: CatalogConfig,
    archive_root: Path,
    *,
    apply: bool = False,
    retention_days: int = RETENTION_DAYS,
    now: datetime,
    plan: PrunePlan | None = None,
) -> PruneReport:
    """Plan (dry-run by default) or apply a prune of verified retired spans.

    ``now`` (timezone-aware) is REQUIRED — the machine clock is never read (D3).
    Pass the ``plan`` returned by a previous dry-run to apply *that exact set*;
    apply re-verifies it under the operation lock and refuses on any drift (D4).
    """
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise TypeError(
            "now: a timezone-aware datetime is required (no system-clock fallback)")
    archive_root = Path(archive_root)
    retired, span_rows = _counts(config.database_path)
    active_plan, verified, manifest_problems = _select_plan(
        config, archive_root, now, retention_days, plan)

    due, oldest = _due_and_oldest(active_plan, verified, now)

    base_report = dict(
        retired_documents=retired,
        span_rows=span_rows,
        oldest_archive=oldest,
        retention_days=active_plan.retention_days,
        due=due,
        plan_hash=active_plan.plan_hash,
        plan_span_ids=active_plan.span_ids,
        verified_archives=len(verified),
        manifest_problems=tuple(manifest_problems),
        plan=active_plan,
    )

    if not apply:
        return PruneReport(dry_run=True, **base_report)
    if not due:
        return PruneReport(dry_run=False, deleted_rows=0, **base_report)
    return _apply_prune(config, now, active_plan, base_report)


def _select_plan(config: CatalogConfig, archive_root: Path, now: datetime,
                 retention_days: int,
                 plan: PrunePlan | None,
                 ) -> tuple[PrunePlan, list[VerifiedArchive], list[str]]:
    """Freeze this run's plan: build it from verified due archives, or verify
    the caller-supplied frozen plan against its own hash and use it as-is.
    The verified archives (and manifest problems) are loaded either way.
    """
    if plan is None:
        built_plan, verified, problems = _build_plan(
            config, archive_root, now, retention_days)
        return built_plan, verified, problems
    if PrunePlan.compute_hash(plan.span_ids, plan.row_digests,
                              plan.archives, plan.retention_days
                              ) != plan.plan_hash:
        raise PruneRefused("frozen plan hash does not match its contents")
    verified, problems = _load_verified_archives(archive_root)
    return plan, verified, problems


def _due_and_oldest(active_plan: PrunePlan,
                    verified: Sequence[VerifiedArchive],
                    now: datetime) -> tuple[bool, str | None]:
    """Is any planned archive past retention, and which verified archive is
    the oldest one (for the report)?"""
    due = bool(active_plan.archives) and any(
        _is_due(va, now, active_plan.retention_days)
        for va in active_plan.archives)
    oldest: str | None = None
    if verified:
        oldest = min(verified, key=lambda va: (
            _parse_utc(va.verified_completed_at), va.archive_path)).archive_path
    return due, oldest


def _apply_prune(config: CatalogConfig, now: datetime,
                 active_plan: PrunePlan,
                 base_report: dict[str, Any]) -> PruneReport:
    """Apply side of ``prune_retired_evidence``: take the operation lock,
    re-verify the frozen plan against the live state before the first delete
    (D4), publish the pending receipt naming the FULL plan (D5), delete in
    batches (each re-verified inside its own transaction), finalize.
    """
    receipt_path: str | None = None
    deleted = 0
    already_absent: tuple[str, ...] = ()
    with CatalogOperationLock(config.catalog_dir,
                              operation="prune_retired_evidence"):
        # ---- D4: re-verify plan vs. current state before the first delete ----
        _verify_archives_on_disk(active_plan)
        states, absent = _pre_delete_check(config, active_plan)
        already_absent = tuple(absent)

        # ---- D5: pending receipt naming the FULL plan, before any delete ----
        receipt = _pending_receipt(now, active_plan, already_absent)
        receipt_file = config.catalog_dir / "artifacts" / "gates" / (
            f"prune-retired-{uuid.uuid4().hex[:16]}.json")
        receipt_file.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(receipt_file, receipt)
        receipt_path = str(receipt_file.resolve())

        store = CatalogStore(config.database_path)
        todo = _plan_todo(active_plan, states, absent)
        for batch in _chunks(todo, BATCH_SIZE):
            deleted += _delete_batch(store, active_plan, batch)
            receipt["committed_ids"] = list(
                dict.fromkeys(receipt["committed_ids"] + batch))
            receipt["deleted_rows"] = deleted
            _atomic_write_json(receipt_file, receipt)     # after every commit

        receipt["status"] = "complete"
        _atomic_write_json(receipt_file, receipt)

    return PruneReport(
        dry_run=False,
        deleted_rows=deleted,
        receipt_path=receipt_path,
        already_absent=already_absent,
        **{k: v for k, v in base_report.items() if k != "plan"},
        plan=active_plan,
    )


def _pre_delete_check(
        config: CatalogConfig,
        active_plan: PrunePlan) -> tuple[dict[str, tuple[str, str]], list[str]]:
    """D4: re-read every planned row under the lock before the first delete.

    Refuses the WHOLE apply (``PruneRefused``, 0 rows deleted) on any drift;
    ids whose rows are already gone are returned as ``absent`` (idempotent,
    not drift).
    """
    states = _span_states(config.database_path, active_plan.span_ids)
    absent: list[str] = []
    for span_id in active_plan.span_ids:
        state = states.get(span_id)
        if state is None:
            absent.append(span_id)          # already deleted: idempotent, not drift
            continue
        live_digest, status = state
        if status != "retired":
            raise PruneRefused(
                f"document of {span_id} is no longer retired; whole apply refused")
        if live_digest != active_plan.row_digests[span_id]:
            raise PruneRefused(
                f"row {span_id} changed since the plan was frozen; whole apply refused")
    return states, absent


def _delete_batch(store: CatalogStore, active_plan: PrunePlan,
                  batch: list[str]) -> int:
    """Delete one batch: re-read and re-verify every planned row INSIDE the
    same transaction that deletes them (D4); any drift raises ``PruneRefused``
    and aborts the whole apply.  Returns the rows deleted by this batch.
    """
    placeholders = ",".join("?" * len(batch))
    with store.transaction() as connection:
        # atomic re-verification WITH the delete (D4)
        rows = {row["span_id"]: row for row in connection.execute(
            _SPAN_STATE.format(placeholders=placeholders), batch)}
        for span_id in batch:
            row = rows.get(span_id)
            if row is None:
                raise PruneRefused(
                    f"row {span_id} vanished mid-apply; whole apply refused")
            digest_row = {key: row[key] for key in row.keys()
                          if key != "__source_status"}
            if row["__source_status"] != "retired":
                raise PruneRefused(
                    f"document of {span_id} reactivated mid-apply; "
                    "whole apply refused")
            if _row_digest(digest_row) != active_plan.row_digests[span_id]:
                raise PruneRefused(
                    f"row {span_id} changed mid-apply; whole apply refused")
        cursor = connection.execute(
            f"DELETE FROM evidence_spans WHERE span_id IN ({placeholders})",
            batch)
        batch_rows = cursor.rowcount
    return max(batch_rows, 0)


def _pending_receipt(now: datetime, active_plan: PrunePlan,
                     already_absent: Sequence[str]) -> dict[str, Any]:
    """D5: the receipt payload naming the FULL plan, published atomically
    BEFORE the first delete (the caller updates it after every commit and
    finalizes it to ``complete``)."""
    return {
        "schema_version": RECEIPT_SCHEMA,
        "status": "pending",
        "now": now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "retention_days": active_plan.retention_days,
        "plan_hash": active_plan.plan_hash,
        "span_ids": list(active_plan.span_ids),
        "row_digests": dict(active_plan.row_digests),
        "archives": [va.to_dict() for va in active_plan.archives],
        "already_absent": list(already_absent),
        "committed_ids": [],
        "deleted_rows": 0,
    }


def _plan_todo(plan: PrunePlan, states: Mapping[str, tuple[str, str]],
               absent: Sequence[str]) -> list[str]:
    absent_set = set(absent)
    return [span_id for span_id in plan.span_ids
            if span_id not in absent_set and span_id in states]


__all__ = ["PrunePlan", "PruneRefused", "PruneReport", "RETENTION_DAYS",
           "VerifiedArchive", "prune_retired_evidence"]
