"""Operator-side feedback coordination over public receipts and owner job ports."""

from pathlib import Path
import sys

# The scheduled entry points run from a source checkout. All feedback
# submodules resolve the owning package without relying on import order.
_SRC = Path(__file__).resolve().parents[2] / "src"
if (_SRC / "company_wiki").is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
