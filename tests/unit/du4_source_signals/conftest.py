"""DU4-FORM unit-test bootstrap (lane-owned test directory only).

The editable ``company_wiki`` install may point at a different worktree, so
this conftest puts *this* worktree's ``src`` ahead of any installed copy
before test modules import the package.  Tests only read the lane's own saved
observation fixtures; no config, production data, API or clock is touched.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
PWF_FIXTURES = ROOT / "docs" / "plans" / "du4-form-2026-10-15" / "fixtures"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
