"""Run ET responsibility tests with synthetic environment and owned short scratch."""
import hashlib
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
TREE = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/et-cutoff-root').resolve()
EVIDENCE = Path(__file__).resolve().parent / 'et'
mode = sys.argv[1]
if mode not in {'red', 'green', 'golden', 'lint'}:
    raise ValueError('Unsupported responsibility node')
scratch = ROOT / '.tmp' / ('ec-' + uuid.uuid4().hex[:8])
if scratch.exists() or scratch.parent.resolve() != (ROOT / '.tmp').resolve():
    raise RuntimeError('Unsafe/nonunique scratch')
scratch.mkdir()
before = []
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
    if mode in {'red', 'green'}:
        command += ['-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                    'tests/test_transcript_api.py', 'tests/test_retrieval_cli_e2e.py',
                    '--basetemp', str(scratch / 'pt'), '--junitxml', str(EVIDENCE / f'{mode}.xml')]
        if mode == 'red':
            command += ['-k', 'w06 or test_as_of_date_excludes_later_publication_without_fetching_body or test_fmp_excludes_call_after_requested_as_of_date']
        else:
            command += [
                'tests/test_batch_runtime.py::test_fool_recent_quarters_expand_only_from_resolvable_metadata',
                'tests/test_batch_runtime.py::test_fool_recent_quarters_without_resolvable_periods_is_period_unresolved',
                'tests/test_batch_runtime.py::test_list_with_explicit_periods_prints_only_matching_metadata',
            ]
    elif mode == 'golden':
        command += ['tests/generate_transcript_goldens.py', '--check']
    else:
        command += ['-m', 'ruff', 'check', '--no-cache', 'transcript_api.py', 'tests/test_transcript_api.py', 'tests/test_retrieval_cli_e2e.py']
    started = time.monotonic()
    result = subprocess.run(command, cwd=TREE, env=environment, capture_output=True, text=True, encoding='utf-8', timeout=150)
    elapsed = time.monotonic() - started
    (EVIDENCE / f'{mode}.log').write_text(result.stdout + result.stderr, encoding='utf-8')
    record = {'mode': mode, 'command': command, 'tree': str(TREE), 'exit_code': result.returncode,
              'elapsed_seconds': round(elapsed, 3), 'scratch': str(scratch), 'environment': 'platform-allowlist plus synthetic HOME/TEMP/key and network deny',
              'real_network': 0, 'keys_read': 0, 'llm_calls': 0}
finally:
    resolved = scratch.resolve()
    if resolved.parent != (ROOT / '.tmp').resolve() or not resolved.name.startswith('ec-'):
        raise RuntimeError('Cleanup target escaped owned workspace scratch')
    shutil.rmtree(resolved)
if scratch.exists():
    raise RuntimeError('Owned scratch not restored')
record['scratch_restored_absent'] = True
(EVIDENCE / f'{mode}.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(record, ensure_ascii=False))
print(result.stdout[-9000:] + result.stderr[-1000:])
sys.exit(result.returncode)
