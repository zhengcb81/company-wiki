"""CLI for the read-only identity audit.

Contract (card section 5.1): exactly one JSON line on stdout, logs only on
stderr, ``--out`` written through a temp file + ``os.replace``, and exit codes
0 (clean), 2 (at least one ``fail``) and 3 (``blocked``/``unavailable``).
Argument errors are reported as a ``blocked`` receipt, never as usage text on
stdout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, NoReturn

from .core import audit
from .receipt import (
    DEPENDENCY_UNAVAILABLE,
    INVALID_ARGUMENT,
    INVALID_JSON,
    LIMIT_EXCEEDED,
    MAX_REQUEST_BYTES,
    TOP_BLOCKED,
    canonical_json,
    utc_now,
)

_EXIT_OK = 0
_EXIT_FAIL = 2
_EXIT_REFUSED = 3

_ZERO_COUNTS = {
    "checked": 0,
    "passed": 0,
    "failed": 0,
    "not_applicable": 0,
    "not_evaluated": 0,
}


class _JsonArgumentParser(argparse.ArgumentParser):
    """argparse that surfaces parse errors as values, never as usage text."""

    def error(self, message: str) -> NoReturn:
        raise ValueError(message)


def _build_parser() -> argparse.ArgumentParser:
    parser = _JsonArgumentParser(
        prog="python -m tools.identity_audit",
        add_help=False,
        description=(
            "Read-only audit of source identity, period, availability, spans and units."
        ),
    )
    parser.add_argument("--config", required=True, metavar="PATH")
    parser.add_argument("--request", required=True, metavar="PATH")
    parser.add_argument("--out", default=None, metavar="PATH")
    parser.add_argument("--pretty", action="store_true")
    return parser


def _log(message: str) -> None:
    print(f"[identity-audit] {message}", file=sys.stderr)


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(name: str) -> None:
    raise ValueError(f"non-finite JSON constant: {name}")


def _blocked(generated_at: str, reason: str, inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "identity-audit-receipt/1",
        "status": TOP_BLOCKED,
        "generated_at": generated_at,
        "reason": reason,
        "inputs": inputs,
        "counts": dict(_ZERO_COUNTS),
        "limitations": [],
        "sources": [],
    }


def _exit_code(receipt: dict[str, Any]) -> int:
    status = receipt["status"]
    if status in {"blocked", "unavailable"}:
        return _EXIT_REFUSED
    if status == "fail":
        return _EXIT_FAIL
    return _EXIT_OK


def _publish(out_path: Path, file_body: str) -> None:
    """Write ``--out`` through a temp file so readers never see a partial file."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        dir=str(out_path.parent),
        prefix=out_path.name + ".",
        suffix=".tmp",
        delete=False,
    )
    temp_name = handle.name
    try:
        handle.write(file_body.encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        os.replace(temp_name, out_path)
    except BaseException:
        handle.close()
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def _emit(
    receipt: dict[str, Any],
    out_path: Path | None,
    *,
    pretty: bool,
    generated_at: str,
    inputs: dict[str, Any],
) -> int:
    """Print one canonical JSON line and optionally publish the ``--out`` file."""
    if out_path is not None and out_path.is_dir():
        _log(f"--out points at a directory: {out_path}")
        receipt = _blocked(generated_at, INVALID_ARGUMENT, inputs)
    if out_path is not None and receipt["status"] != TOP_BLOCKED:
        body = canonical_json(receipt)
        file_body = (
            json.dumps(receipt, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
            if pretty
            else body + "\n"
        )
        try:
            _publish(out_path, file_body)
        except OSError as exc:
            _log(f"could not write --out {out_path}: {exc}")
            receipt = _blocked(generated_at, DEPENDENCY_UNAVAILABLE, inputs)
    line = (canonical_json(receipt) + "\n").encode("utf-8")
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is None:  # pragma: no cover - text-only stdout
        sys.stdout.write(canonical_json(receipt) + "\n")
        sys.stdout.flush()
    else:
        # Byte-level write keeps the receipt a single LF-terminated line even
        # where text mode would translate the newline to CRLF.
        buffer.write(line)
        buffer.flush()
    return _exit_code(receipt)


def _refused_out_path(out_path: Path) -> bool:
    """Reject parent traversal and symlink targets before any bytes move."""
    return ".." in out_path.parts or out_path.is_symlink()


def _refused_exit(
    generated_at: str,
    reason: str,
    args: argparse.Namespace,
    inputs: dict[str, Any],
) -> int:
    out_path = Path(args.out) if args.out else None
    return _emit(
        _blocked(generated_at, reason, inputs),
        out_path,
        pretty=args.pretty,
        generated_at=generated_at,
        inputs=inputs,
    )


def main(argv: list[str] | None = None) -> int:
    generated_at = utc_now()
    try:
        args = _build_parser().parse_args(sys.argv[1:] if argv is None else list(argv))
    except ValueError as exc:
        _log(f"argument error: {exc}")
        return _emit(
            _blocked(generated_at, INVALID_ARGUMENT, {}),
            None,
            pretty=False,
            generated_at=generated_at,
            inputs={},
        )

    config_path = Path(args.config)
    request_path = Path(args.request)
    inputs: dict[str, Any] = {}
    config_binding = _file_binding(config_path)
    if config_binding is not None:
        inputs[str(config_path)] = config_binding
    out_path = Path(args.out) if args.out else None
    if out_path is not None and _refused_out_path(out_path):
        _log(f"--out path refused (parent traversal or symlink): {out_path}")
        return _refused_exit(generated_at, INVALID_ARGUMENT, args, inputs)
    request_binding = _file_binding(request_path)
    if request_binding is None:
        _log(f"request file is not readable: {request_path}")
        return _refused_exit(generated_at, INVALID_ARGUMENT, args, inputs)
    if request_binding["bytes"] > MAX_REQUEST_BYTES:
        _log("request exceeds the frozen byte limit")
        return _refused_exit(generated_at, LIMIT_EXCEEDED, args, inputs)
    try:
        raw = request_path.read_bytes()
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_no_duplicates,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        _log(f"request is not valid JSON: {exc}")
        return _refused_exit(generated_at, INVALID_JSON, args, inputs)
    if not isinstance(payload, dict):
        _log("request must be a JSON object")
        return _refused_exit(generated_at, INVALID_JSON, args, inputs)

    receipt = audit(config_path=config_path, request=payload)
    merged_inputs = dict(receipt.get("inputs") or {})
    merged_inputs[str(request_path)] = request_binding
    receipt["inputs"] = merged_inputs
    return _emit(
        receipt,
        out_path,
        pretty=args.pretty,
        generated_at=generated_at,
        inputs=merged_inputs,
    )


def _file_binding(path: Path) -> dict[str, Any] | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
