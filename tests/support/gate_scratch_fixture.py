"""Measured, independently owned roots for nested Windows scratch tests."""
from contextlib import contextmanager
import os
from pathlib import Path
import tempfile

from tools import pre_push_gate as gate


@contextmanager
def short_gate_root(tmp_path_factory):
    """Leave room for real positive candidates, without changing product caps.

    An outer pytest basetemp can fit60 units while its /env-temp child no
    longer fits the nested gate. Only this test fixture is relocated; every
    candidate is measured with the actual allocated name and actually created.
    """
    if os.name != 'nt':
        yield tmp_path_factory.mktemp('g')
        return
    descendants = ('missing-a', 'missing-b', 'env-temp', 'good', 'denied', 'a/x')
    suffix_units = max(gate._scratch_path_units(os.sep + name.replace('/', os.sep))
                       for name in descendants)
    base = tmp_path_factory.getbasetemp()
    parents = [base.parent, Path(tempfile.gettempdir()), Path(__file__).resolve().parents[3]]
    # The checkout's parent is already part of this user's workspace; the
    # OS's normal temp is another actual-write candidate, never an ACL change.
    system_root = os.environ.get('SystemRoot')
    if system_root:
        parents.append(Path(system_root) / 'Temp')
    attempts = []
    for parent in dict.fromkeys(parents):
        if not parent.is_dir():
            continue
        minimum = (gate._scratch_path_units(str(parent) + os.sep + '.w2-')
                   + suffix_units + gate.PYTEST_SCRATCH_NAME_RESERVE)
        if minimum > gate.PYTEST_SCRATCH_MAX_UNITS:
            attempts.append(f'{parent}: even prefix-only nested root requires{minimum} units')
            continue
        failure = gate._probe_writable(str(parent))
        if failure is not None:
            # In particular, do not let mkdtemp retry a Windows deny ACL
            # toward TMP_MAX after a bounded mkdir already proved rejection.
            attempts.append(f'{parent}: {type(failure).__name__}')
            continue
        try:
            owned = tempfile.TemporaryDirectory(prefix='.w2-', dir=parent)
        except OSError as exc:
            attempts.append(f'{parent}: {type(exc).__name__}')
            continue
        root = Path(owned.name)
        required = gate._scratch_path_units(str(root)) + suffix_units + gate.PYTEST_SCRATCH_NAME_RESERVE
        if required > gate.PYTEST_SCRATCH_MAX_UNITS:
            owned.cleanup()
            attempts.append(f'{parent}: actual nested root requires{required} units')
            continue
        try:
            yield root
        finally:
            owned.cleanup()
            assert not root.exists(), 'Only this fixture owned root must be removed'
        return
    raise RuntimeError('No writable measured nested-gate test root: ' + '; '.join(attempts))
