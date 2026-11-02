"""Explicit integration deployment, never imported by a consumer runtime."""
import os
from pathlib import Path

CWP_CODE_ROOT = Path(__file__).resolve().parents[2]
RF_CODE_ROOT = Path(os.environ.get("RF_CODE_ROOT", CWP_CODE_ROOT.parent / "revenue-forecast"))
