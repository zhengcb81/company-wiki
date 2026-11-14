"""Stream only the committed snapshot of an exact original.

The source owner verifies registered bytes into a temporary sink. It may retry
another copy of the same version while the sink is private. Before the first
stdout byte, the transport emits one 2.2 ``locked`` identity receipt. After
writing and flushing the verified snapshot it emits the final ``ok`` receipt.
A refusal before verification has no lock and exposes no bytes.

The existing source read budget covers candidate selection and staging.
``filing_reuse`` remains on the whole-buffer source reader CLI for scope
verification. The caller receives the two receipts and the source bytes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import BinaryIO, NoReturn, Sequence, cast

from company_wiki.source_contract import (
    SourceChunkSinkError,
    SourceReadError,
    SourceRef,
    VerifiedVersionReceipt,
)

from .config import CatalogConfigError, load_catalog_config
from .read_budget import ReadBudget
from .reader import CatalogReaderUnavailable
from .service import SourceCatalog
from .source_reader import SourceVersionReader

#: Stream receipts are their own additive protocol.  The 2.1 schema of the
#: whole-buffer reader stays untouched; refusals keep its five-value statuses.
STREAM_RECEIPT_SCHEMA_VERSION = "2.2"
_STREAMABLE_PURPOSES = frozenset({"preview", "source_export", "narrative_derivation"})
_OUTPUT_CHUNK_BYTES = 1024 * 1024


class _JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ValueError(message)


def _emit_receipt(payload: dict[str, object]) -> None:
    line = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
    if sys.stderr.write(line) != len(line):
        raise BrokenPipeError("source receipt was not delivered")
    sys.stderr.flush()


def _refuse(status: str, reason: str) -> NoReturn:
    try:
        _emit_receipt({
            "schema_version": STREAM_RECEIPT_SCHEMA_VERSION,
            "status": status,
            "reason": reason,
        })
    except OSError:
        # A closed receipt pipe still yields a failing process exit.
        pass
    raise SystemExit(2)


class _StagedSourceStream:
    """One request's scratch file, writable only through the transactional sink."""

    __slots__ = ("__file", "__committed")

    def __init__(self, file: BinaryIO) -> None:
        self.__file = file
        self.__committed = False

    def begin_candidate(self) -> None:
        self.discard_candidate()

    def write_chunk(self, chunk: bytes) -> None:
        if self.__file.write(chunk) != len(chunk):
            raise SourceChunkSinkError("source staging did not accept the complete chunk")

    def discard_candidate(self) -> None:
        self.__committed = False
        self.__file.seek(0)
        self.__file.truncate()

    def commit_verified(self, receipt: VerifiedVersionReceipt) -> None:
        if self.__file.tell() != receipt.byte_size:
            raise SourceChunkSinkError("source staging size differs from the verified receipt")
        self.__file.seek(0)
        self.__committed = True

    def copy_to(self, output: BinaryIO) -> None:
        if not self.__committed:
            raise SourceChunkSinkError("source snapshot was not committed")
        while chunk := self.__file.read(_OUTPUT_CHUNK_BYTES):
            remaining = memoryview(chunk)
            while remaining:
                written = output.write(remaining)
                if written is None or not 0 < written <= len(remaining):
                    raise OSError("source output write made no progress")
                remaining = remaining[written:]
        output.flush()


def _emit_lock(ref: SourceRef) -> None:
    _emit_receipt(
        {
            "schema_version": STREAM_RECEIPT_SCHEMA_VERSION,
            "status": "locked",
            "document_id": ref.document_id,
            "source_id": ref.source_id,
            "content_sha256": ref.content_sha256,
            "mime_type": ref.mime_type,
            "byte_size": ref.byte_size,
        }
    )


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
        try:
            with tempfile.TemporaryFile(mode="w+b") as scratch:
                # On Windows TemporaryFile is a wrapper around a binary file.
                sink = _StagedSourceStream(cast(BinaryIO, scratch))
                receipt = reader.stream_version(
                    ref, sink=sink, purpose=args.purpose, budget=budget,
                )
                _emit_lock(ref)
                sink.copy_to(sys.stdout.buffer)
        except BrokenPipeError:
            _refuse("unavailable", "stream_consumer_gone")
        except (OSError, SourceChunkSinkError):
            _refuse("unavailable", "stream_staging_unavailable")
        try:
            _emit_receipt({
                "schema_version": STREAM_RECEIPT_SCHEMA_VERSION,
                "status": "ok",
                "document_id": receipt.document_id,
                "source_id": receipt.source_id,
                "content_sha256": receipt.content_sha256,
                "byte_size": receipt.byte_size,
                "read_at": receipt.read_at,
                "policy_sha256": receipt.policy_sha256,
                "source_read_policy_sha256": receipt.source_read_policy_sha256,
            })
        except OSError:
            raise SystemExit(2) from None
        return 0
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
