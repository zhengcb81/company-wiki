"""DU2-LAYOUT unit-test bootstrap (lane-owned test directory only).

The editable ``company_wiki`` install points at whichever checkout performed
``pip install -e``; it may be a different worktree.  The lane's exact test
command runs without PYTHONPATH, so this conftest puts *this* worktree's
``src`` ahead of any installed copy before test modules import the package.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_SRC = _ROOT / "src"
_FIXTURES = _ROOT / "tests" / "fixtures" / "document_understanding_layout_hints"

for path in (_SRC, _FIXTURES):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
