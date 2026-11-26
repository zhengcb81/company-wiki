"""Explicit bounded local intake CLI; performs no HTTP/model/download work."""

from __future__ import annotations

from company_wiki import runtime_feedback
import argparse
import json
from pathlib import Path
import sys
from .config import load_catalog_config
from .local_inventory import LocalPrepareLimits
from .local_reconcile import prepare_local_source
from .source_request import SourceRequest
from .service import SourceCatalog
from .source_group_scope import SourceRegistrationScope
from .source_reader import SourceReadError


@runtime_feedback.entry("local-source-prepare")
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--request", required=True, help="bounded JSON file or - for stdin"
    )
    parser.add_argument("--identity-cache-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        runtime_feedback.checkpoint("load-request", input_path=Path(args.request) if args.request != "-" else None)
        if args.request == "-":
            payload = sys.stdin.buffer.read()
        else:
            with Path(args.request).open("rb") as stream:
                payload = stream.read()
        value = json.loads(payload)
        if (
            not isinstance(value, dict)
            or value.get("schema_version") != "local-source-prepare-request/1"
            or not set(value)
            <= {"schema_version", "source_request", "limits", "registrations"}
        ):
            raise ValueError("invalid local prepare request schema")
        request = SourceRequest(**value["source_request"])
        limits = LocalPrepareLimits(**value.get("limits", {}))
        registrations = tuple(
            SourceRegistrationScope(x["root_id"], frozenset(x["relative_paths"]))
            for x in value.get("registrations", [])
        )
        config_path = args.config.resolve(strict=True)
        config = load_catalog_config(config_path, project_root=config_path.parents[1])
        catalog = SourceCatalog(config)
        try:
            runtime_feedback.checkpoint("prepare-original", input_path=config_path, related_run_id=request.request_id)
            result = prepare_local_source(
                catalog,
                request,
                identity_cache_dir=args.identity_cache_dir,
                limits=limits,
                registrations=registrations,
            )
        finally:
            catalog.close()
        runtime_feedback.document_results("local-source-prepare", result)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, KeyError, TypeError, OSError, SourceReadError) as exc:
        runtime_feedback.refusal(getattr(exc, "status", "blocked"),
                                 getattr(exc, "reason", "invalid_local_prepare_request"))
        print(
            json.dumps(
                {
                    "schema_version": "local-source-prepare/1",
                    "status": getattr(exc, "status", "blocked"),
                    "reason": getattr(exc, "reason", "invalid_local_prepare_request"),
                    "source_ref": None,
                    "blocks_download": True,
                    "operations": [],
                    "diagnostics": [],
                    "download_events": 0,
                },
                ensure_ascii=False,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
