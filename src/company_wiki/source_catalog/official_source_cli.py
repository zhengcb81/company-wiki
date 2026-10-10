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


def _load_projection_argument(catalog, request):
    from company_wiki.source_catalog.official_json_projection import (
        ProjectionError,
        load_projection,
        projection_from_dict,
    )
    if request.get("projection_id") is not None:
        return load_projection(catalog, request["projection_id"])
    if request.get("projection") is not None:
        return projection_from_dict(request["projection"])
    raise ProjectionError("invalid_projection_request")


def _json_projection_operation(catalog, operation, request) -> dict | bytes:
    from company_wiki.source_catalog.official_json_projection import (
        ProjectionError,
        build_projection_export,
        build_projection_from_refs,
        persist_projection,
        replay_projection,
    )
    if operation == "project":
        if request.get("schema_version") != "official-json-projection-request/1":
            raise ProjectionError("invalid_projection_request_schema")
        refs = request.get("parent_source_refs")
        if not isinstance(refs, list) or not refs:
            raise ProjectionError("invalid_projection_request")
        # An explicit producer is passed to the source owner. Omission preserves
        # the historical default and wire; unknown versions cannot be ignored.
        if "projection_version" in request and not isinstance(request["projection_version"], str):
            raise ProjectionError("invalid_projection_version")
        version_options = (
            {"projection_version": request["projection_version"]}
            if "projection_version" in request else {}
        )
        projection = build_projection_from_refs(
            catalog, refs=refs, layout_id=request.get("layout_id"),
            issuer=request.get("issuer") or {},
            as_of_date=request.get("as_of_date"), **version_options)
        if request.get("persist"):
            persist_projection(catalog, projection)
        return {
            "schema_version": "official-json-projection-result/1",
            "projection": projection.to_dict(),
            "selected_records": projection.coverage["issuer_records_selected"],
        }
    if operation == "read":
        if request.get("schema_version") != "official-source-read-request/1":
            raise ValueError("invalid_read_request_schema")
        ref = request.get("source_ref")
        if not isinstance(ref, dict):
            raise ValueError("invalid_read_request")
        from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader
        content = SourceVersionReader(catalog).open_version(
            SourceRef(**ref), purpose="source_export")
        return content.data
    if operation == "replay":
        if request.get("schema_version") != "official-json-replay-request/1":
            raise ProjectionError("invalid_replay_request_schema")
        projection = _load_projection_argument(catalog, request)
        return replay_projection(catalog, projection)
    if operation == "export":
        if request.get("schema_version") != "source-projection-export-request/1":
            raise ProjectionError("invalid_export_request_schema")
        projection = _load_projection_argument(catalog, request)
        return build_projection_export(catalog, projection)
    raise ValueError("unknown_operation")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--operation", choices=(
        "import", "discover", "capture", "recover", "project", "read", "replay", "export"),
        default="import")
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--input-file", type=Path)
    args = parser.parse_args(argv)
    catalog = None
    try:
        request = _read_json(args.request)
        if not isinstance(request, dict):
            raise ValueError("invalid_request")
        result: dict
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
            if request.get("schema_version") == "official-source-import-request/2":
                from .official_json_import import import_official_json_source
                result = import_official_json_source(
                    catalog, original=original, request=request)
            else:
                result = import_official_source(catalog, original=original, request=request)
        elif args.operation in {"project", "read", "replay", "export"}:
            if args.config is None:
                raise ValueError("explicit_config_required")
            root = args.project_root or args.config.resolve().parents[1]
            catalog = SourceCatalog(load_catalog_config(args.config, project_root=root))
            projection_result = _json_projection_operation(
                catalog, args.operation, request)
            if args.operation == "read":
                # The public read contract: stdout carries exactly the
                # original bytes and nothing else.
                if not isinstance(projection_result, bytes):
                    raise ValueError("invalid_read_request")
                sys.stdout.buffer.write(projection_result)
                sys.stdout.buffer.flush()
                return 0
            if not isinstance(projection_result, dict):
                raise ValueError("invalid_projection_result")
            result = projection_result
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
                    result = recover_official_source(catalog, capture_id=request["capture_id"], max_bytes=request.get("max_bytes"))
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
        for field in ("capture_id", "acquisition_usage", "acquisition_usage_complete", "provider_started",
                      "http_observation", "http_wire_bytes", "http_wire_usage_complete"):
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
