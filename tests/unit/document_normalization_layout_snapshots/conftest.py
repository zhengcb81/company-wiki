"""DU3-GEOMETRY unit-test bootstrap (lane-owned test directory only).

The editable ``company_wiki`` install points at whichever checkout performed
``pip install -e``; it may be a different worktree.  This conftest puts *this*
worktree's ``src`` and its own fixtures dir ahead of any installed copy before
test modules import the package.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_SRC = _ROOT / "src"
_FIXTURES = _ROOT / "tests" / "fixtures" / "document_normalization_layout_snapshots"

for _path in (_SRC, _FIXTURES):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
