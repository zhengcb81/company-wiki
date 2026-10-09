"""The requirements-based CI install must include every direct runtime dependency."""

from pathlib import Path

from tools.check_dependencies import missing_dependencies


def test_ci_requirements_include_declared_runtime_dependencies():
    root = Path(__file__).resolve().parents[2]
    missing = missing_dependencies(root)
    assert missing == [], f"CI requirements omit direct runtime dependencies: {missing}"
