"""The requirements-based CI install must include every direct runtime dependency."""

from pathlib import Path

import pytest


def test_ci_requirements_include_declared_runtime_dependencies():
    tomllib = pytest.importorskip("tomllib")
    root = Path(__file__).resolve().parents[2]
    declared = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    required = {
        line.split("#", 1)[0].replace(" ", "").lower()
        for line in (root / "requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    missing = [
        dependency for dependency in declared["project"]["dependencies"]
        if dependency.replace(" ", "").lower() not in required
    ]
    assert missing == [], f"CI requirements omit direct runtime dependencies: {missing}"
