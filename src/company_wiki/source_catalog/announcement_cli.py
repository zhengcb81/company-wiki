"""CLI for one explicit, create-once official announcement collection."""

from __future__ import annotations

from company_wiki import runtime_feedback
from company_wiki.diagnostic_redaction import redact_text

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
    parser = runtime_feedback.ArgumentParser(
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


@runtime_feedback.command("collect-announcement")
def main(argv: Sequence[str] | None = None) -> int:
    _configure_utf8_streams()
    args = build_parser().parse_args(argv)
    try:
        runtime_feedback.checkpoint("collect-original", input_path=args.root)
        receipt = collect_announcement(
            root=args.root,
            company_name=args.company,
            entity_ids=tuple(args.entity_id),
            source_url=args.url,
            title=args.title,
            published_date=args.published_date,
        )
    except (OSError, TypeError, ValueError) as exc:
        runtime_feedback.record("collect-announcement", "failed", reason=type(exc).__name__, error=exc)
        print(redact_text(f"announcement collection failed: {exc}"), file=sys.stderr)
        return 2
    sys.stdout.write(receipt.canonical_json() + "\n")
    return 0


__all__ = ["build_parser", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
