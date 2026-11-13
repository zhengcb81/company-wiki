"""Bounded streaming transport over the current stream_version owner port.

The regular :mod:`source_reader_cli` reads the whole verified file into memory
before one stdout write.  This CLI is the large-original companion: stdout
carries only source chunks, and stderr carries two JSON lines -

1. a ``locked`` receipt immediately before the first byte of the admitted
   candidate crosses stdout (and before ``ok`` for an empty original).  It
   pins the exact catalog identity (SHA-256, byte size, MIME) of what is
   about to move; a refusal that produced no bytes carries no lock line,
   because a consumer reads the first receipt as the transfer gate;
2. a final ``ok`` receipt after the owner verified every streamed byte and
   this transport re-digested what actually crossed the pipe.  ``ok`` — not
   ``locked`` — is the complete-stream verification claim.

Every admission, verification, same-SHA fallback, budget and cancellation
decision belongs to the current ``SourceVersionPort.stream_version`` owner;
this transport adds none.  Success requires exit code 0, the locked receipt,
the final ``ok`` receipt, and the caller's own digest check over the received
bytes.  Any failure after bytes started moving is a refusal with no ``ok``
receipt: the transfer stays incomplete by construction, and consumers keep
the last chunk held back until the receipt confirms it.

``filing_reuse`` is refused here: that purpose must verify scope against
whole retained bytes and belongs to the regular reader CLI.  A stdout pipe
cannot express a mid-stream switch between same-SHA copies, so a second
staged candidate is a named refusal rather than concatenated bytes.  The
caller never receives a filesystem path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import NoReturn, Sequence

from company_wiki.source_contract import (
    SourceChunkSink,
    SourceChunkSinkError,
    SourceReadError,
    SourceRef,
)

from .config import CatalogConfigError, load_catalog_config
from .read_budget import ReadBudget
from .reader import CatalogReaderUnavailable
from .service import SourceCatalog
from .source_reader import SourceVersionReader

#: Stream receipts are their own additive protocol.  The 2.1 schema of the
#: whole-buffer reader stays untouched; refusals keep its five-value statuses.
STREAM_RECEIPT_SCHEMA_VERSION = "2.2"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_STREAMABLE_PURPOSES = frozenset({"preview", "source_export", "narrative_derivation"})


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


class _StdoutVerifiedStream(SourceChunkSink):
    """stdout is the provisional staging area; the receipts are the transaction.

    One lock receipt precedes the first chunk of the one admitted candidate.
    The owner may discard a failing copy, but a pipe cannot unsend its bytes,
    so a second staged candidate refuses the whole transfer instead of
    emitting concatenated copies.
    """

    def __init__(self, ref: SourceRef) -> None:
        self._ref = ref
        self._digest = hashlib.sha256()
        self._total = 0
        self._locked = False
        self._lock_emitted = False

    def begin_candidate(self) -> None:
        # The candidate is admitted here, but the lock receipt is emitted
        # lazily: a refusal before the first byte (missing file, denied
        # root, unreadable copy) must carry no lock line, because a
        # consumer reads the first receipt as the transfer gate.
        if self._locked:
            raise SourceChunkSinkError(
                "a stdout stream carries one candidate; retry is a refusal"
            )
        self._locked = True

    def _emit_lock(self) -> None:
        if self._lock_emitted:
            return
        self._lock_emitted = True
        _emit_receipt(
            {
                "schema_version": STREAM_RECEIPT_SCHEMA_VERSION,
                "status": "locked",
                "document_id": self._ref.document_id,
                "source_id": self._ref.source_id,
                "content_sha256": self._ref.content_sha256,
                "mime_type": self._ref.mime_type,
                "byte_size": self._ref.byte_size,
            }
        )

    def write_chunk(self, chunk: bytes) -> None:
        # The receipt precedes the first stdout byte of the admitted
        # candidate; verification of the complete stream stays with the
        # owner and is reported by the final ok receipt.
        self._emit_lock()
        sys.stdout.buffer.write(chunk)
        self._digest.update(chunk)
        self._total += len(chunk)

    def discard_candidate(self) -> None:
        # Bytes already piped cannot be recalled; no ok receipt follows, so
        # the transfer stays incomplete by construction.
        return None

    def commit_verified(self, receipt) -> None:
        if self._digest.hexdigest() != self._ref.content_sha256 or self._total != self._ref.byte_size:
            raise SourceChunkSinkError("streamed bytes differ from the locked identity")
        assert receipt.byte_size == self._ref.byte_size
        # An empty original streams no chunk: the lock still precedes ok.
        self._emit_lock()


def _digest_argument(value: str) -> str:
    """Validate wire syntax before initializing a catalog or reader."""
    if re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise argparse.ArgumentTypeError("digest must be lowercase SHA-256")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = _JsonArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--content-sha256", required=True, type=_digest_argument)
    parser.add_argument("--purpose", default="preview")
    parser.add_argument(
        "--exact-pair", action="store_true",
        help="Resolve the exact registered pair, including non-primary history versions.",
    )
    catalog: SourceCatalog | None = None
    try:
        args = parser.parse_args(argv)
        if args.purpose not in _STREAMABLE_PURPOSES:
            raise SourceReadError("blocked", "purpose_not_streamable")
        config = load_catalog_config(args.config)
        catalog = SourceCatalog(config)
        reader = SourceVersionReader(catalog)
        # Preserve the primary-only default for existing consumers. A history
        # browser explicitly opts into the exact registered document/source pair.
        query = reader.query_exact_pair_ref if args.exact_pair else reader.query_ref
        ref = query(args.document_id, args.source_id, args.content_sha256)
        budget = ReadBudget()
        budget.begin_request()
        sink = _StdoutVerifiedStream(ref)
        receipt = reader.stream_version(
            ref, sink=sink, purpose=args.purpose, budget=budget,
        )
        sys.stdout.buffer.flush()
        _emit_receipt(
            {
                "schema_version": STREAM_RECEIPT_SCHEMA_VERSION,
                "status": "ok",
                "document_id": receipt.document_id,
                "source_id": receipt.source_id,
                "content_sha256": receipt.content_sha256,
                "byte_size": receipt.byte_size,
                "read_at": receipt.read_at,
                "policy_sha256": receipt.policy_sha256,
                "source_read_policy_sha256": receipt.source_read_policy_sha256,
            }
        )
        return 0
    except SourceChunkSinkError:
        # Includes the consumer-disappeared case: bytes cannot be piped on.
        _refuse("unavailable", "stream_consumer_gone")
    except SourceReadError as exc:
        _refuse(exc.status, exc.reason)
    except (CatalogConfigError, CatalogReaderUnavailable):
        _refuse("unavailable", "catalog_unavailable")
    except (OSError, ValueError):
        _refuse("blocked", "invalid_request")
    finally:
        if catalog is not None:
            catalog.close()


if __name__ == "__main__":
    raise SystemExit(main())
