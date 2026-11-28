"""Temporary filesystem policy shared by the pytest hook and its CI parent."""

import os
from pathlib import Path
import tempfile


FALLBACK_ROOT_ENV = "CW_BASETEMP_FALLBACK_ROOT"
PARENT_BASETEMP_ENV = "CW_PARENT_OWNS_BASETEMP"


def short_scratch_root(checkout: Path) -> Path:
    override = os.environ.get(FALLBACK_ROOT_ENV)
    if override:
        root = Path(override).resolve()
    else:
        system_temp = Path(tempfile.gettempdir()).resolve()
        root = min((checkout, system_temp), key=lambda path: len(str(path)))
    root.mkdir(parents=True, exist_ok=True)
    return root
