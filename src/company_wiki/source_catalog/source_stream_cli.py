"""Bounded streaming transport for an exact, verified source version.

The regular :mod:`source_reader_cli` reads the whole verified file into
memory before one stdout write.  This CLI is the large-original companion:
stdout carries only source chunks, and stderr carries two JSON lines -

1. a ``locked`` receipt after the catalog identity (SHA-256, byte size, MIME)
   and the exact read policy are pinned and the candidate file was fully
   verified, but before any byte is written;
2. a final ``ok`` receipt after every streamed byte was re-digested against
   the locked hash, or one refusal in the reader's five-value error model.

Success requires exit code 0, the locked receipt, the final ``ok`` receipt,
and the caller's own digest check over the received bytes.  Any failure after
bytes started moving is a refusal with no ``ok`` receipt: the transfer stays
incomplete by construction.  ``filing_reuse`` is refused here: that purpose
must verify scope against whole retained bytes and belongs to the regular
reader CLI.  The caller never receives a filesystem path.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn, Sequence

from .config import CatalogConfigError, load_catalog_config
from .policy_2x import export_policy_2x
from .reader import CatalogReaderUnavailable
from .resolver import _ReadBudget
from .security_code import canonical_security_code
from .service import SourceCatalog
from .source_availability import verified_availability_evidence
from .source_byte_lock import (
    REFUSAL_BUDGET,
    REFUSAL_CANCELLED,
    ByteLock,
    ByteLockError,
)
from .source_location import SourceLocationError, resolve_source_location
from .source_reader import (
    _SUPPORTED_READ_PURPOSES,
    SourceReadError,
    SourceVersionReader,
)

#: Stream receipts are their own additive protocol.  The 2.1 schema of the
#: whole-buffer reader stays untouched; refusals keep its five-value statuses.
STREAM_RECEIPT_SCHEMA_VERSION = "2.2"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class _JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ValueError(message)


def _emit_receipt(payload: dict[str, object]) -> None:
    try:
        line = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        sys.stderr.write(line + "\n")
        sys.stderr.flush()
    except OSError:
        # A consumer that is gone cannot be told so either; the non-zero exit
        # below still says no ok receipt exists.
        pass


def _refuse(status: str, reason: str, detail: str = "") -> NoReturn:
    _emit_receipt(
        {
            "schema_version": STREAM_RECEIPT_SCHEMA_VERSION,
            "status": status,
            "reason": reason,
        }
    )
    raise SystemExit(2)


def _elect_verified_candidate(
    catalog: SourceCatalog, ref: Any, version_row: sqlite3.Row, budget: _ReadBudget
) -> ByteLock:
    """Pass 1: bind the candidate to a protected, verified handle.

    Admission is the reader's own shared gate
    (:meth:`SourceVersionReader._admitted_candidates`), so the streaming
    transport elects exactly the candidate the whole-buffer reader elects --
    by construction, not by a mirrored copy of the admission rules.  The
    candidate is opened so that no other process can write or replace it
    while we hold it, and its bytes are digested FROM THAT HANDLE.  The
    stream pass rewinds the same handle, so a path replaced behind our back
    cannot change what we stream.
    """
    reader = SourceVersionReader(catalog)
    roots = {root.root_id: root for root in catalog.config.roots}
    failures: list[str] = []
    candidates = reader._admitted_candidates(ref, version_row, roots=roots)
    for location in sorted(candidates, key=lambda item: item["candidate_rank"]):
        try:
            resolved = resolve_source_location(roots[location["root_id"]],
                                               str(location["relative_path"]))
        except SourceLocationError as exc:
            failures.append(exc.reason)
            continue
        try:
            return ByteLock.open(
                resolved, expected_sha256=ref.content_sha256,
                expected_byte_size=ref.byte_size, budget=budget)
        except ByteLockError as exc:
            failures.append(exc.detail or exc.reason)
            if exc.reason in {REFUSAL_CANCELLED, REFUSAL_BUDGET}:
                break
    raise SourceReadError(
        "unavailable", "no_verified_location", ",".join(sorted(set(failures)))
    )


def _stream_verified_bytes(lock: ByteLock, *, ref: Any, budget: _ReadBudget) -> str:
    """Pass 2: stream the verified bytes from the SAME handle, hashing them.

    The bytes handed to stdout are exactly the bytes digested, read from the
    object the verify pass already proved.  Every refusal exits before an
    ``ok`` receipt exists, so the transfer stays incomplete by construction.
    A broken stdout is the consumer's cancellation, not a read success.
    """

    def write(chunk: bytes) -> None:
        try:
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
        except OSError:
            # On Windows a consumer that stopped reading surfaces as
            # EINVAL/pipe-closed rather than EPIPE: either way the
            # transfer is cancelled, never a success.
            raise ByteLockError(REFUSAL_CANCELLED) from None

    try:
        return lock.stream(write, budget=budget)
    except ByteLockError as exc:
        _refuse("unavailable", exc.reason, exc.detail)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _JsonArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--content-sha256", required=True)
    parser.add_argument("--purpose", default="preview")
    parser.add_argument("--expected-read-policy-sha256")
    parser.add_argument("--include-availability-evidence", action="store_true",
                        help="Return the final receipt with existing historical capture evidence, or null.")
    parser.add_argument("--include-canonical-identity", action="store_true",
                        help="Project market code formatting without changing observed manifest facts.")
    catalog: SourceCatalog | None = None
    try:
        args = parser.parse_args(argv)
        if args.purpose not in _SUPPORTED_READ_PURPOSES or args.purpose == "filing_reuse":
            _refuse("blocked", "unsupported_purpose_for_stream")
        expected_pin = args.expected_read_policy_sha256
        if expected_pin is not None and (
            not isinstance(expected_pin, str) or not _SHA256.fullmatch(expected_pin)
        ):
            raise SourceReadError("blocked", "invalid_read_policy_pin")
        config = load_catalog_config(args.config)
        catalog = SourceCatalog(config)
        reader = SourceVersionReader(catalog)
        ref = reader.query_ref(args.document_id, args.source_id, args.content_sha256)
        manifest = reader.describe_version(ref)
        global_pin = reader.read_policy_sha256()
        if expected_pin is None or expected_pin == global_pin:
            read_policy_sha256 = global_pin
        else:
            read_policy_sha256 = reader.read_policy_sha256(ref)
        try:
            version_row = catalog.reader.exact_source_version(ref.document_id)
        except (CatalogReaderUnavailable, sqlite3.Error):
            raise SourceReadError("unavailable", "catalog_unavailable") from None
        if version_row is None:
            raise SourceReadError("not_indexed", "document_not_indexed")
        policy_sha256, _ = export_policy_2x(config)

        extension: dict[str, Any] = {}
        if args.include_canonical_identity:
            market = manifest.get("market")
            security_id = manifest.get("security_id")
            extension["canonical_identity"] = {
                "schema_version": "source-canonical-identity/1",
                "market": market,
                "security_id": canonical_security_code(
                    security_id if isinstance(security_id, str) else None,
                    market if isinstance(market, str) else None,
                ),
            }
        if args.include_availability_evidence:
            extension["availability_evidence"] = verified_availability_evidence(catalog, ref)

        budget = _ReadBudget()
        budget.begin_request()
        resolved = _elect_verified_candidate(catalog, ref, version_row, budget)

        _emit_receipt(
            {
                "schema_version": STREAM_RECEIPT_SCHEMA_VERSION,
                "status": "locked",
                "document_id": ref.document_id,
                "source_id": ref.source_id,
                "content_sha256": ref.content_sha256,
                "byte_size": ref.byte_size,
                "mime_type": ref.mime_type,
                "policy_sha256": policy_sha256,
                "source_read_policy_sha256": read_policy_sha256,
                "read_at": datetime.now(UTC).isoformat(),
                "manifest": manifest,
                **extension,
            }
        )

        budget.begin_request()
        try:
            computed = _stream_verified_bytes(resolved, ref=ref, budget=budget)
        finally:
            resolved.close()
        sys.stdout.buffer.flush()
        _emit_receipt(
            {
                "schema_version": STREAM_RECEIPT_SCHEMA_VERSION,
                "status": "ok",
                "document_id": ref.document_id,
                "source_id": ref.source_id,
                "content_sha256": computed,
                "byte_size": ref.byte_size,
                "policy_sha256": policy_sha256,
                "source_read_policy_sha256": read_policy_sha256,
                "read_at": datetime.now(UTC).isoformat(),
            }
        )
        return 0
    except SourceReadError as exc:
        _refuse(exc.status, exc.reason, exc.detail)
    except (CatalogConfigError, CatalogReaderUnavailable, OSError, sqlite3.Error, ValueError):
        _refuse("unavailable", "reader_unavailable")
    finally:
        if catalog is not None:
            catalog.close()


if __name__ == "__main__":
    raise SystemExit(main())
