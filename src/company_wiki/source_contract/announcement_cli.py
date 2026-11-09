"""Compatibility entry point for the former announcement CLI module."""

from __future__ import annotations

from argparse import ArgumentParser
from collections.abc import Sequence


def build_parser() -> ArgumentParser:
    from company_wiki.source_catalog.announcement_cli import build_parser as active_parser

    return active_parser()


def main(argv: Sequence[str] | None = None) -> int:
    from company_wiki.source_catalog.announcement_cli import main as active_main

    return active_main(argv)


__all__ = ["build_parser", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
