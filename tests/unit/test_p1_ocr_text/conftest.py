"""P1-OCR-TEXT unit-test bootstrap (lane-owned test directory only).

The editable ``company_wiki`` install may point at another worktree, so this
conftest puts *this* worktree's ``src`` first, and keeps the lane's own helper
modules importable without turning the directory into a package.
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parents[2] / "src"

for _path in (_SRC, _HERE):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
