"""Read-only deterministic export CLI for company-wiki source contracts."""

import argparse
from collections.abc import Sequence
import json
from pathlib import Path
import sys
from typing import Any

from .evidence_span import EvidenceSpan
from .source_export import SourceExportBundle
from .source_manifest import SourceManifest


def _configure_utf8_streams() -> None:
    """Make CLI bytes stable across Windows and POSIX locale settings."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="strict", newline="\n")


def _read_stable_text(path: Path) -> str:
    if not isinstance(path, Path):
        raise TypeError("input path must be pathlib.Path")
    resolved = path.resolve(strict=True)
    if not resolved.is_file():
        raise ValueError(f"input path is not a regular file: {path}")
    before = resolved.stat()
    content = resolved.read_bytes()
    after = resolved.stat()
    if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
        raise ValueError(f"input changed while reading: {path}")
    return content.decode("utf-8")


def _read_jsonl(path: Path, *, kind: str) -> list[Any]:
    text = _read_stable_text(path)
    records: list[Any] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"{kind} JSONL contains blank line {line_number}: {path}")
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"invalid {kind} JSONL at {path}:{line_number}: {exc.msg}"
            ) from exc
    return records


def _load_manifests(paths: Sequence[Path]) -> tuple[SourceManifest, ...]:
    return tuple(
        SourceManifest.from_dict(record)
        for path in paths
        for record in _read_jsonl(path, kind="manifest")
    )


def _load_spans(paths: Sequence[Path]) -> tuple[EvidenceSpan, ...]:
    return tuple(
        EvidenceSpan.from_dict(record)
        for path in paths
        for record in _read_jsonl(path, kind="evidence span")
    )


def _load_base(path: Path | None) -> SourceExportBundle | None:
    if path is None:
        return None
    try:
        data = json.loads(_read_stable_text(path))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid base export JSON: {path}: {exc.msg}") from exc
    return SourceExportBundle.from_dict(data)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="company-wiki-source-export",
        description="Read-only deterministic source-contract export to stdout",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    child = subparsers.add_parser(
        "export",
        help="verify immutable raw and emit one canonical export bundle",
    )
    child.add_argument(
        "--root",
        type=Path,
        required=True,
        help="immutable source repository root",
    )
    child.add_argument(
        "--manifests",
        type=Path,
        action="append",
        default=[],
        help="Source Manifest JSONL input; repeatable",
    )
    child.add_argument(
        "--spans",
        type=Path,
        action="append",
        default=[],
        help="Evidence Span JSONL input; repeatable",
    )
    child.add_argument(
        "--base",
        type=Path,
        default=None,
        help="previous source export bundle for add-only incremental merge",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    _configure_utf8_streams()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "export":
        return 2
    if args.base is None and not args.manifests:
        parser.error("export requires --base or at least one --manifests input")

    try:
        base = _load_base(args.base)
        manifests = _load_manifests(args.manifests)
        spans = _load_spans(args.spans)
        if not manifests and (base is None or not base.manifests):
            raise ValueError("export requires at least one source manifest")
        bundle = SourceExportBundle.build(
            root=args.root,
            manifests=manifests,
            evidence_spans=spans,
            base=base,
        )
    except (OSError, TypeError, ValueError) as exc:
        print(f"source export failed: {exc}", file=sys.stderr)
        return 2

    sys.stdout.write(bundle.canonical_json() + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
