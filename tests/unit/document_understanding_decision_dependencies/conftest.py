"""Keep the shared tests/fixtures package importable from this lane.

Lane conftests elsewhere insert their own directory (which contains a
``fixtures/`` folder) at ``sys.path[0]``. Under the gate mixed xdist
selection that shadowed ``tests/fixtures`` and this package modules failed
with ModuleNotFoundError while importing ``fixtures.*``. Loading this
conftest runs before the lane test modules, so re-asserting the tests root
here makes the shared fixtures win regardless of collection order.
"""
import sys
from pathlib import Path

_TESTS_ROOT = str(Path(__file__).resolve().parents[2])
if not sys.path or sys.path[0] != _TESTS_ROOT:
    try:
        sys.path.remove(_TESTS_ROOT)
    except ValueError:
        pass
    sys.path.insert(0, _TESTS_ROOT)
