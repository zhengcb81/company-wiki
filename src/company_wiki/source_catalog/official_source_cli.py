"""Public thin original-import/discovery entry. Canonical paths stay in storage."""

from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import httpx

from .bounded_http import ProviderBudgetStop
from .config import load_catalog_config
from .service import SourceCatalog
from .official_source_flow import (
    import_official_source, OfficialSourceError, capture_official_source,
    recover_official_source, list_retained_official_captures,
)
from .official_discovery import discover_official_documents, fetch_official_indexes

_MAX_REQUEST_BYTES = 65536


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate_request_key")
        result[key] = value
    return result


def _nonfinite(_):
    raise ValueError("nonfinite_request_value")


def _read_json(path):
    with path.open("rb") as handle:
        raw = handle.read(_MAX_REQUEST_BYTES + 1)
    if len(raw) > _MAX_REQUEST_BYTES:
        raise ValueError("request_byte_limit")
    return json.loads(
        raw.decode("utf-8-sig"), object_pairs_hook=_pairs, parse_constant=_nonfinite
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--operation", choices=("import", "discover", "capture", "recover"), default="import")
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--input-file", type=Path)
    args = parser.parse_args(argv)
    catalog = None
    try:
        request = _read_json(args.request)
        if not isinstance(request, dict):
            raise ValueError("invalid_request")
        if args.operation == "import":
            if (
                args.config is None
                or args.input_file is None
                or not args.input_file.is_absolute()
            ):
                raise ValueError("explicit_config_and_absolute_input_file_required")
            cap = request.get("max_bytes")
            if type(cap) is not int or not 0 < cap <= 128 * 1024 * 1024:
                raise ValueError("invalid_byte_cap")
            with args.input_file.open("rb") as handle:
                original = handle.read(cap + 1)
            root = args.project_root or args.config.resolve().parents[1]
            catalog = SourceCatalog(load_catalog_config(args.config, project_root=root))
            result = import_official_source(catalog, original=original, request=request)
        elif args.operation in {"capture", "recover"}:
            if args.config is None:
                raise ValueError("explicit_config_required")
            root = args.project_root or args.config.resolve().parents[1]
            catalog = SourceCatalog(load_catalog_config(args.config, project_root=root))
            if args.operation == "capture":
                result = capture_official_source(catalog, request=request)
            else:
                if request.get("schema_version") != "official-source-recovery-request/1":
                    raise OfficialSourceError("invalid_recovery_request_schema")
                if request.get("capture_id") is None:
                    result = {"schema_version": "official-source-recovery-inventory/1",
                              "captures": list_retained_official_captures(catalog)}
                else:
                    result = recover_official_source(catalog, capture_id=request["capture_id"])
        else:
            if request.get("schema_version") != "official-discovery-request/1":
                raise ValueError("invalid_discovery_schema")
            pages = []
            local_truncated = False
            if ("urls" in request) == ("pages" in request):
                raise ValueError("exactly_one_discovery_input_required")
            if "urls" in request:
                pages, fetch_receipts = fetch_official_indexes(
                    request["urls"],
                    max_bytes=request.get("max_bytes", 8388608),
                    max_seconds=request.get("max_seconds", 120),
                )
            else:
                fetch_receipts = []
                local_pages = request.get("pages", [])
                cap = request.get("max_bytes", 8388608)
                if (
                    not isinstance(local_pages, list)
                    or not 1 <= len(local_pages) <= 6
                    or type(cap) is not int
                    or not 0 < cap <= 8388608
                ):
                    raise ValueError("invalid_local_index_limits")
                remaining = cap
                for index, row in enumerate(local_pages):
                    path = Path(row["input_file"])
                    if not path.is_absolute():
                        raise ValueError("absolute_index_input_required")
                    with path.open("rb") as handle:
                        original = handle.read(remaining + 1)
                    remaining = max(0, remaining - len(original))
                    pages.append(
                        {
                            "url": row["url"],
                            "original": original,
                            "mime_type": row["mime_type"],
                            "capture_id": row["capture_id"],
                        }
                    )
                    if remaining == 0:
                        local_truncated = (
                            index + 1 < len(local_pages) or len(original) > cap
                        )
                        break
            result = discover_official_documents(
                pages,
                entity=request["entity"],
                as_of_date=request["as_of_date"],
                start_date=request["start_date"],
                max_items=request.get("max_items", 30),
                max_bytes=request.get("max_bytes", 8388608),
            )
            result["fetch_receipts"] = fetch_receipts
            if local_truncated:
                result["coverage_status"] = "partial"
                result["limitations"].append("byte_limit_reached")
            if any(row.get("status") != "opened" for row in fetch_receipts):
                result["coverage_status"] = "partial"
                result["limitations"].append("index_fetch_incomplete")
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return 0
    except (OSError, ValueError, RuntimeError, ProviderBudgetStop, httpx.HTTPError) as exc:
        # Do not expose input paths, credentials or source bodies on a refusal.
        code = (
            str(exc)
            if isinstance(exc, OfficialSourceError)
            else "official_source_" + type(exc).__name__
        )
        failure = {"schema_version": "official-source-failure/1", "status": "failed",
                   "error_code": getattr(exc, "error_code", code)}
        for field in ("capture_id", "acquisition_usage", "acquisition_usage_complete", "provider_started"):
            value = getattr(exc, field, None)
            if value is not None:
                failure[field] = value
        print(json.dumps(failure), file=sys.stderr)
        return 2
    finally:
        if catalog is not None:
            catalog.close()


if __name__ == "__main__":
    raise SystemExit(main())
