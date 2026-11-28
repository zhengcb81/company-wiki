"""Versioned control and bound filing commands for owner-isolated T3 workspaces."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

from company_wiki import runtime_feedback
from company_wiki.file_mutex import FileMutexLockedError, os_file_mutex

from .cli import main as catalog_main
from .local_prepare_cli import main as local_prepare_main
from .source_query_cli import main as query_main
from .source_reader_cli import main as open_main
from .t3_workspace import CASE_MARKETS, CaseBinding, WorkspaceError, WorkspaceService

_REQUEST_SCHEMA = "cwp-t3-workspace-request/1"
_RESPONSE_SCHEMA = "cwp-t3-workspace/1"
_OPERATIONS = {"open", "observe", "close"}
_BOUND_ID = re.compile(r"t3-[0-9a-f]{32}")
_OWNER_CONFIG_OVERRIDES = {"--config", "--acquisition-config", "--worker-config", "--identity-cache-dir", "--refresh"}
_BOUND_HANDLERS = {
    "catalog": catalog_main,
    "query": query_main,
    "local_prepare": local_prepare_main,
    "open": open_main,
}


def _connection(workspaces: Path, case: Path) -> dict[str, object]:
    command = [sys.executable, "-B", "-m", "company_wiki.source_catalog.t3_workspace_cli",
               "--workspace-root", str(workspaces.resolve()), "--binding", case.name]
    return {"cwd": str(case), "commands": {
        operation: [*command, "--catalog-operation", operation, "--"] for operation in _BOUND_HANDLERS
    }}


def _bound_command(args: argparse.Namespace, tail: list[str]) -> int:
    handler = _BOUND_HANDLERS.get(args.catalog_operation)
    if handler is None or not _BOUND_ID.fullmatch(args.binding):
        raise WorkspaceError("invalid_bound_command")
    root = args.workspace_root.resolve()
    if not root.is_dir():
        raise WorkspaceError("workspace_unavailable")
    with os_file_mutex(root / (args.binding + ".lock"), timeout_seconds=5.0):
        case = root / args.binding
        if case.resolve() != case or not (case / "binding.json").is_file():
            raise WorkspaceError("workspace_unavailable")
        if (root / (args.binding + ".closed")).exists():
            raise WorkspaceError("workspace_closed")
        if any(flag.startswith(value.split("=", 1)[0])
               for value in tail if value.startswith("--") for flag in _OWNER_CONFIG_OVERRIDES):
            raise WorkspaceError("workspace_config_override")
        if args.catalog_operation == "catalog" and (not tail or tail[0] not in {"identify", "resolve", "ensure"}):
            raise WorkspaceError("workspace_operation_unavailable")
        runtime = case / "runtime"
        os.environ.update(LOCALAPPDATA=str(runtime), XDG_STATE_HOME=str(runtime),
                          RESEARCH_FEEDBACK_DIR=str(runtime / "observations"))
        os.environ.pop("RESEARCH_FEEDBACK_OUT", None)
        return int(handler(["--config", str(case / "config/source_catalog.yaml"), *tail]))


def _workspace_response(args: argparse.Namespace, request: Any, response: dict[str, Any]) -> None:
    if not isinstance(request, dict) or request.get("schema_version") != _REQUEST_SCHEMA:
        raise WorkspaceError("invalid_request")
    operation, run, case = (request.get(key) for key in ("operation", "run_id", "case_id"))
    response.update(operation=operation, run_id=run, case_id=case)
    if (not isinstance(operation, str) or operation not in _OPERATIONS
            or not isinstance(run, str) or not run
            or not isinstance(case, str) or case not in CASE_MARKETS):
        raise WorkspaceError("invalid_request")
    binding = CaseBinding(run, case)
    response["workspace_id"] = binding.workspace_id
    provided = request.get("workspace_id")
    permitted = operation == "open" or provided == binding.workspace_id or (operation == "close" and provided is None)
    if not permitted:
        raise WorkspaceError("workspace_binding_mismatch")
    if args.owner_root is None or args.acquisition_config is None or args.identity_cache is None:
        raise WorkspaceError("workspace_not_configured")
    service = WorkspaceService(args.workspace_root, args.owner_root, args.acquisition_config, args.identity_cache)
    if operation == "open":
        location = service.open(binding)
        response.update(status="opened", connection=_connection(args.workspace_root, location))
    elif operation == "close":
        service.close(binding)
        response["status"] = "closed"
    else:
        checkpoint = request.get("checkpoint")
        expected = ("corrupt",) if case == "corrupt_original" else ("first", "reused")
        if not isinstance(checkpoint, str) or checkpoint not in expected:
            raise WorkspaceError("invalid_checkpoint")
        response.update(status="observed", checkpoint=checkpoint, facts=service.observe(binding, checkpoint))


@runtime_feedback.entry("t3-workspace")
def main(argv: list[str] | None = None) -> int:
    parser = runtime_feedback.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--workspace-root", required=True, type=Path)
    parser.add_argument("--owner-root", type=Path)
    parser.add_argument("--acquisition-config", type=Path)
    parser.add_argument("--identity-cache", type=Path)
    parser.add_argument("--binding")
    parser.add_argument("--catalog-operation", choices=list(_BOUND_HANDLERS))
    args, tail = parser.parse_known_args(argv)
    response: dict[str, Any] = {"schema_version": _RESPONSE_SCHEMA}
    try:
        if args.binding:
            return _bound_command(args, tail[1:] if tail and tail[0] == "--" else tail)
        if tail:
            raise WorkspaceError("invalid_request")
        _workspace_response(args, json.load(sys.stdin), response)
    except WorkspaceError as error:
        runtime_feedback.refusal("failed", str(error))
        response.update(status="failed", error_code=str(error))
    except (FileMutexLockedError, OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
        runtime_feedback.refusal("failed", "workspace_operation_failed")
        response.update(status="failed", error_code="workspace_operation_failed",
                        error_type=type(error).__name__)
    print(json.dumps(response, ensure_ascii=True, separators=(",", ":")))
    return 2 if response["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(runtime_feedback.run_cli(main))
