"""DU4-TABLE unit-test bootstrap (lane-owned test directory only).

The editable ``company_wiki`` install points at whichever checkout performed
``pip install -e``; it may be a different worktree.  This conftest puts *this*
worktree's ``src`` ahead of any installed copy before test modules import the
package, so the lane's tests always exercise the local sources.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_SRC = _ROOT / "src"

if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
