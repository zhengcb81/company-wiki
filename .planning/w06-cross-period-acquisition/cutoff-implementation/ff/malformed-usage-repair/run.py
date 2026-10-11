"""One scoped TDD/engineering node with synthetic environment and owned scratch."""
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path('C:/Users/郑曾波/Projects/company-wiki').resolve()
TREE = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root').resolve()
EVIDENCE = Path(__file__).resolve().parent
mode = sys.argv[1]
if mode not in {'red', 'concentrated', 'lint'}:
    raise ValueError('Unsupported responsibility node')
scratch = ROOT / '.tmp' / ('mu-' + uuid.uuid4().hex[:8])
if scratch.exists() or scratch.parent.resolve() != (ROOT / '.tmp').resolve():
    raise RuntimeError('Unsafe/nonunique scratch')
scratch.mkdir()
environment = {name: os.environ[name] for name in ('PATH', 'SystemRoot', 'WINDIR', 'SystemDrive', 'COMSPEC', 'PATHEXT') if name in os.environ}
try:
    for name in ('home', 'tmp', 'profile', 'appdata', 'localappdata'):
        (scratch / name).mkdir()
    (scratch / 'sitecustomize.py').write_text(
        'import socket\n'
        'def _deny(*args, **kwargs):\n'
        '    raise RuntimeError("offline-cutoff-test-network-denied")\n'
        'socket.socket.connect = _deny\n'
        'socket.socket.connect_ex = _deny\n'
        'socket.create_connection = _deny\n', encoding='utf-8')
    environment.update({
        'HOME': str(scratch / 'home'), 'USERPROFILE': str(scratch / 'profile'),
        'TEMP': str(scratch / 'tmp'), 'TMP': str(scratch / 'tmp'),
        'APPDATA': str(scratch / 'appdata'), 'LOCALAPPDATA': str(scratch / 'localappdata'),
        'PYTHONPATH': os.pathsep.join((str(scratch), str(TREE))),
        'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUTF8': '1',
        'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'FMP_API_KEY': 'synthetic-cutoff-key',
    })
    command = [sys.executable, '-B']
    if mode == 'lint':
        command += ['-m', 'ruff', 'check', '--no-cache', 'scripts/transcript_tool_transport.py', 'scripts/et_v2_contract.py',
                    'tests/test_transcript_launch_contract.py', 'tests/test_transcript_companion_transport.py', 'tests/test_et_s0b_contract.py']
    else:
        command += ['-m', 'pytest', '-p', 'no:cacheprovider', '-q',
                    '--basetemp', str(scratch / 'pt'), '--junitxml', str(EVIDENCE / f'{mode}.xml'),
                    'tests/test_transcript_launch_contract.py']
        if mode == 'red':
            command += ['-k', 'malformed_stdout_preserves_independently_verified_usage']
        else:
            command += ['tests/test_transcript_companion_transport.py', 'tests/test_et_s0b_contract.py',
                        'tests/test_transcript_response_budget.py', 'tests/test_transcript_companion.py']
    started = time.monotonic()
    result = subprocess.run(command, cwd=TREE, env=environment, capture_output=True, text=True, encoding='utf-8', timeout=150)
    elapsed = time.monotonic() - started
    (EVIDENCE / f'{mode}.log').write_text(result.stdout + result.stderr, encoding='utf-8')
    record = {'command': command, 'tree': str(TREE), 'exit_code': result.returncode,
              'elapsed_seconds': round(elapsed, 3), 'scratch': str(scratch),
              'environment': 'platform allowlist + synthetic HOME/TEMP/key + socket deny',
              'real_network': 0, 'keys_read': 0, 'llm_calls': 0}
finally:
    resolved = scratch.resolve()
    if resolved.parent != (ROOT / '.tmp').resolve() or not resolved.name.startswith('mu-'):
        raise RuntimeError('Cleanup target escaped owned workspace scratch')
    shutil.rmtree(resolved)
record['scratch_restored_absent'] = not scratch.exists()
(EVIDENCE / f'{mode}.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(record, ensure_ascii=False))
print(result.stdout[-6500:] + result.stderr[-1000:])
sys.exit(result.returncode)
