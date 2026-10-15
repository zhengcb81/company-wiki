"""DU4-STATE unit-test bootstrap (lane-owned test directory only).

The editable ``company_wiki`` install may point at another worktree. The
lane's exact test command runs with this worktree's ``src`` on PYTHONPATH,
but this conftest also puts *this* worktree's ``src`` and the lane's own test
directory ahead of any installed copy before test modules import anything.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_HERE = Path(__file__).resolve().parent

for _path in (_ROOT / "src", _HERE):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
