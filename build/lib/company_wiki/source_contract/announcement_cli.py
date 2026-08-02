"""CLI for one explicit, create-once official announcement collection."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys

from .announcement_collector import collect_announcement


def _configure_utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="strict", newline="\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="company-wiki-collect-announcement",
        description=(
            "Create one immutable announcement from an explicit official exchange URL"
        ),
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--entity-id", action="append", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--published-date", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    _configure_utf8_streams()
    args = build_parser().parse_args(argv)
    try:
        receipt = collect_announcement(
            root=args.root,
            company_name=args.company,
            entity_ids=tuple(args.entity_id),
            source_url=args.url,
            title=args.title,
            published_date=args.published_date,
        )
    except (OSError, TypeError, ValueError) as exc:
        print(f"announcement collection failed: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(receipt.canonical_json() + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
