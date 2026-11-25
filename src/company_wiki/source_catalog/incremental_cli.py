"""Compatibility entry for the original incremental-reading module."""

from collections.abc import Sequence

from .incremental_command import run_incremental as run_incremental

__all__ = ["main", "run_incremental"]


def main(argv: Sequence[str] | None = None) -> int:
    from company_wiki.scheduled_reading import main as scheduled_main

    return scheduled_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
