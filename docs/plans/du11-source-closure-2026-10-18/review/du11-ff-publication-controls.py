"""Independent protocol controls, only synthetic files in an owned snapshot."""
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

@pytest.mark.parametrize('valid', [True, False])
def test_ascii_json_roundtrips_non_gbk_path_and_keeps_failure(tmp_path, valid):
    source = tmp_path / '资料_\U0001f4ca.py'
    source.write_text('def f():\n    return 1\n' if valid else 'def broken(:\n', encoding='utf8')
    before = source.read_bytes(), source.stat().st_mtime_ns
    env = dict(os.environ, PYTHONIOENCODING='gbk', PYTHONUTF8='0')
    proc = subprocess.run([sys.executable, '-B', str(Path(__file__).parents[1]/'tools/complexity_diagnostics.py'), str(source)], env=env, capture_output=True, timeout=15)
    assert proc.returncode == (0 if valid else 1)
    assert proc.stdout.isascii()
    result = json.loads(proc.stdout.decode('utf8'))
    group = result['files' if valid else 'errors']
    assert len(group) == 1
    assert group[0]['path'] == str(source.resolve())
    assert result['diagnostic_only'] is True
    if not valid:
        assert group[0]['error'] == 'SyntaxError'
    assert (source.read_bytes(), source.stat().st_mtime_ns) == before
