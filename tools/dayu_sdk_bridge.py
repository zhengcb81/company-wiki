"""Boot CWP's bridge from Dayu's interpreter without changing Dayu's code."""

from pathlib import Path
import sys

# The adapter's cwd is its explicitly selected external SDK checkout (or
# isolated HEAD export); override any editable-install path in its venv.
sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from company_wiki.source_catalog.dayu_sdk_cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
