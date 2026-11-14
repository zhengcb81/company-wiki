"""Read persistent narrative bundles by logical identity, never raw file paths.

stdin: bounded versioned JSON request. stdout: exact artifact bytes (or reference).
stderr: one JSON receipt/refusal. Consumers require exit 0 and verify stdout SHA.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager, redirect_stderr, redirect_stdout
import json
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any, NoReturn, Sequence

from company_wiki.automation.models import canonical_json
from company_wiki.automation.narrative_contracts import NarrativeContractError
from company_wiki.automation.narrative_evidence_view import (
    EVIDENCE_VIEW_OPERATIONS, NarrativeEvidenceViewQuery, NarrativeEvidenceViewReader,
)
from company_wiki.automation.narrative_transport import NarrativeTransportReader
from company_wiki.automation.narrative_transport_contracts import (
    NARRATIVE_COMPACT_REFERENCE_REQUEST_SCHEMA,
    NARRATIVE_COMPACT_READ_RECEIPT_SCHEMA,
    parse_compact_reference_request,
    NARRATIVE_READ_RECEIPT_SCHEMA,
    NARRATIVE_PROJECTED_READ_RECEIPT_SCHEMA,
    parse_projected_reference_request,
    NarrativeReadRequest,
    NarrativeTransportError,
    parse_reference_request,
)

from company_wiki.source_catalog.config import CatalogConfigError, load_catalog_config
from company_wiki.source_catalog.narrative_artifact_store import NarrativeArtifactReader
from company_wiki.source_catalog.narrative_normalization import NarrativeNormalization
from company_wiki.source_catalog.reader import CatalogReaderUnavailable
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_contract import SourceReadError
from company_wiki.source_catalog.source_reader import SourceVersionReader


__all__ = ["dispatch_transport_request", "main"]


class _JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ValueError(message)


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise ValueError("non-finite JSON number")


def _read_request() -> object:
    raw = sys.stdin.buffer.read()
    return json.loads(
        raw.decode("utf-8", errors="strict"), object_pairs_hook=_unique_pairs,
        parse_constant=_invalid_constant,
    )


def _emit_receipt(receipt: dict[str, Any]) -> None:
    raw = canonical_json(receipt).encode("utf-8") + b"\n"
    binary = getattr(sys.stderr, "buffer", None)
    if binary is None:
        sys.stderr.write(raw.decode("utf-8"))
    else:
        binary.write(raw)
    sys.stderr.flush()


def _refusal(status: str, reason: str) -> int:
    _emit_receipt({
        "schema_version": NARRATIVE_READ_RECEIPT_SCHEMA,
        "status": status, "reason": reason,
    })
    return 2


@contextmanager
def _quiet_transport_operation() -> Iterator[None]:
    """Reserve the CLI protocol streams, including writes by native parsers."""
    sys.stdout.flush()
    sys.stderr.flush()
    with open(os.devnull, "w", encoding="utf-8") as quiet, ExitStack() as descriptors:
        for descriptor in (1, 2):
            inheritable = os.get_inheritable(descriptor)
            saved = os.dup(descriptor)
            descriptors.callback(os.close, saved)
            os.dup2(quiet.fileno(), descriptor, inheritable=inheritable)
            descriptors.callback(os.dup2, saved, descriptor, inheritable=inheritable)
        with redirect_stdout(quiet), redirect_stderr(quiet):
            yield


def dispatch_transport_request(
    operation: str,
    request: object,
    reader: NarrativeTransportReader,
    *,
    view_query: NarrativeEvidenceViewQuery | None = None,
) -> tuple[bytes, dict[str, Any]]:
    if (operation in EVIDENCE_VIEW_OPERATIONS and view_query is None) or (
        view_query is not None and view_query.operation != operation
    ):
        raise ValueError("evidence operation and filters differ")
    if operation == "reference":
        projected = (
            isinstance(request, dict)
            and request.get("schema_version") == "narrative-reference-request/2"
        )
        compact = (isinstance(request, dict)
                   and request.get("schema_version") == NARRATIVE_COMPACT_REFERENCE_REQUEST_SCHEMA)
        if compact:
            subject_ref, generation = parse_compact_reference_request(request)
            ref = reader.reference_subject_ref(subject_ref, generation_sha256=generation)
        elif projected:
            subject, generation = parse_projected_reference_request(request)
            ref = reader.reference_subject(subject, generation_sha256=generation)
        else:
            ref = reader.reference(parse_reference_request(request))
        return canonical_json(ref.to_dict()).encode("utf-8"), {
            "schema_version": NARRATIVE_COMPACT_READ_RECEIPT_SCHEMA if compact
            else NARRATIVE_PROJECTED_READ_RECEIPT_SCHEMA if projected
            else NARRATIVE_READ_RECEIPT_SCHEMA,
            "status": "metadata_only",
            "narrative_ref": ref.to_dict(),
        }
    parsed = NarrativeReadRequest.from_dict(request)
    result = (
        NarrativeEvidenceViewReader(reader).read(parsed, view_query)
        if view_query is not None
        else reader.read(parsed)
    )
    return result.data, result.receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = _JsonArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--operation",
        choices=("reference", "read", *EVIDENCE_VIEW_OPERATIONS),
        default="read",
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument("--offset", type=int)
    parser.add_argument("--span-id")
    parser.add_argument("--locator")
    parser.add_argument("--query")
    catalog: SourceCatalog | None = None
    artifacts: NarrativeArtifactReader | None = None
    try:
        args = parser.parse_args(argv)
        filters = {
            name: getattr(args, name)
            for name in ("limit", "offset", "span_id", "locator", "query")
        }
        view_query = None
        if args.operation in EVIDENCE_VIEW_OPERATIONS:
            view_query = NarrativeEvidenceViewQuery(args.operation, **filters)
        elif any(value is not None for value in filters.values()):
            raise ValueError("filters require an evidence operation")
        request = _read_request()
        config = load_catalog_config(args.config)
        catalog = SourceCatalog(config)
        artifacts = catalog.open_narrative_artifact_reader()
        from company_wiki.source_catalog.narrative_official_json import bind_projection_loader

        # The composition root owns the OCR configuration location.  The
        # transport only consumes the normalization port it is given, so a
        # protocol-only source implementation needs no catalog or project
        # layout of its own.
        normalization = NarrativeNormalization.deferred_from_project(config.project_root)
        if isinstance(request, dict) and request.get("schema_version") in {
            "narrative-reference-request/2", "narrative-read-request/2",
            "narrative-reference-request/3", "narrative-read-request/3",
        }:
            projection_loader = bind_projection_loader(catalog)
            reader = NarrativeTransportReader(
                artifacts, SourceVersionReader(catalog), normalization=normalization,
                projection_loader=projection_loader,
                projection_ref_resolver=projection_loader,
            )
        else:
            reader = NarrativeTransportReader(
                artifacts, SourceVersionReader(catalog), normalization=normalization,
            )
        # Some PDF backends print optional-package notices. The two protocol
        # streams belong exclusively to artifact bytes and the JSON receipt.
        with _quiet_transport_operation():
            data, receipt = dispatch_transport_request(
                args.operation, request, reader, view_query=view_query
            )
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()
        _emit_receipt(receipt)
        return 0
    except (NarrativeTransportError, SourceReadError) as exc:
        return _refusal(exc.status, exc.reason)
    except (CatalogConfigError, CatalogReaderUnavailable, OSError, sqlite3.Error):
        return _refusal("unavailable", "narrative_reader_unavailable")
    except (
        NarrativeContractError,
        TypeError,
        UnicodeError,
        ValueError,
        RecursionError,
    ):
        return _refusal("blocked", "invalid_request")
    finally:
        if artifacts is not None:
            artifacts.close()
        if catalog is not None:
            catalog.close()


if __name__ == "__main__":
    raise SystemExit(main())
