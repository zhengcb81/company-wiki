"""Install detached diagnostics before importing the target entry point."""

import runpy
import sys

from .diagnostics import run_background


def _run() -> None:
    sys.argv = sys.argv[1:]
    runpy.run_module(sys.argv[0], run_name="__main__", alter_sys=True)


if __name__ == "__main__":
    run_background(_run)
