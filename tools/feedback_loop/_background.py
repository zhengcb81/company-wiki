"""Install detached diagnostics before importing the target entry point."""

import runpy
import sys

from company_wiki import runtime_feedback


def _run() -> None:
    sys.argv = sys.argv[1:]
    runpy.run_module(sys.argv[0], run_name="__main__", alter_sys=True)


def main() -> int:
    # Bind bootstrap failures before the host's regular diagnostic scope is available.
    try:
        from .diagnostics import run_background
    except Exception as exc:
        runtime_feedback.record("feedback-background", "failed", error=exc, publish_issue=False)
        raise

    run_background(_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(runtime_feedback.run_cli(main))
