"""One final existing daily gate + bounded frozen native replay; zero providers."""
from __future__ import annotations
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root')
EVIDENCE = Path(__file__).resolve().parent
SCRATCH = EVIDENCE / 'typed-boundary-scratch'
FROZEN = ROOT / 'docs/handoffs/w05-rf-flow/e2e/frozen'
LOG = EVIDENCE / 'typed-boundary-final-node.log'
environment = os.environ.copy()
for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR', 'GIT_INDEX_FILE', 'GIT_PREFIX',
            'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES', 'GIT_NAMESPACE', 'GIT_QUARANTINE_PATH'):
    environment.pop(key, None)
environment.update(PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
                   FF_V2_CODE_ROOT='C:/Users/郑曾波/Projects/filing-fetch',
                   CWP_V2_CODE_ROOT='C:/Users/郑曾波/Projects/company-wiki',
                   REVENUE_PUBLICATION_REGISTRY=str(SCRATCH / 'publication-registry.jsonl'))
commands = []

def run(arguments, label, timeout=60):
    start = time.monotonic()
    result = subprocess.run(arguments, cwd=ROOT, env=environment, capture_output=True,
                            text=True, encoding='utf-8', timeout=timeout)
    item = {'label': label, 'command': arguments, 'exit_code': result.returncode,
            'seconds': round(time.monotonic() - start, 3)}
    commands.append(item)
    with LOG.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(item, ensure_ascii=False) + '\n' + result.stdout + result.stderr + '\n')
    print(label, result.returncode, item['seconds'], flush=True)
    if result.returncode:
        raise RuntimeError(label + ' failed; original output preserved')


def main():
    assert not SCRATCH.exists()
    SCRATCH.mkdir()
    LOG.write_text('One post-P1 existing gate and frozen native replay; 0 provider/LLM calls, $0\n', encoding='utf-8')
    status = 'FAIL'
    comparisons = []
    try:
        run([sys.executable, '-B', 'tools/pre_push_gate.py'], 'existing single daily gate', 120)
        frozen_manifest = json.loads((FROZEN / 'manifest.json').read_text(encoding='utf-8'))
        for item in frozen_manifest['artifacts']:
            path = ROOT / item['path']
            assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'] and path.stat().st_size == item['bytes']
        for case in ('case1_acquisition', 'case2_offset_fy'):
            run([sys.executable, '-B', 'scripts/revenue_forecast.py', str(FROZEN / (case + '.input.json')),
                 '--output', str(SCRATCH / (case + '.forecast.json')), '--markdown', str(SCRATCH / (case + '.forecast.md'))],
                case + ' native frozen-input replay')
            for suffix in ('forecast.json', 'forecast.md'):
                generated, frozen = SCRATCH / (case + '.' + suffix), FROZEN / (case + '.' + suffix)
                assert generated.read_bytes() == frozen.read_bytes(), case + ' differs from pre-P1 frozen ' + suffix
                comparisons.append({'path': frozen.name, 'full_bytes_identical': True,
                                    'sha256': hashlib.sha256(generated.read_bytes()).hexdigest()})
            run([sys.executable, '-B', 'docs/handoffs/w05-rf-flow/e2e/read_and_tamper.py',
                 str(SCRATCH / (case + '.forecast.json')), 'window'], case + ' strong reader/rehashed date reject')
        run([sys.executable, '-B', 'docs/handoffs/w05-rf-flow/e2e/read_and_tamper.py',
             str(SCRATCH / 'case1_acquisition.forecast.json'), 'currency'], 'C1 strong reader/rehashed currency reject')
        run([sys.executable, '-B', 'scripts/revenue_backtest.py', 'create',
             str(FROZEN / 'case1_acquisition.input.json'), '--version', 'w05-root-cny-v1',
             '--output', str(SCRATCH / 'case1_acquisition.snapshot.json')], 'native frozen C1 snapshot replay')
        assert (SCRATCH / 'case1_acquisition.snapshot.json').read_bytes() == (FROZEN / 'case1_acquisition.snapshot.json').read_bytes()
        comparisons.append({'path': 'case1_acquisition.snapshot.json', 'full_bytes_identical': True})
        status = 'PASS'
    finally:
        files = [{'path': path.relative_to(SCRATCH).as_posix(), 'bytes': path.stat().st_size}
                 for path in SCRATCH.rglob('*') if path.is_file()]
        assert SCRATCH.resolve().parent == EVIDENCE.resolve() and SCRATCH.name == 'typed-boundary-scratch'
        for path in SCRATCH.rglob('*'):
            if path.is_file():
                path.chmod(stat.S_IREAD | stat.S_IWRITE)
        shutil.rmtree(SCRATCH)
        (EVIDENCE / 'typed-boundary-final-node.json').write_text(json.dumps({
            'status': status, 'commands': commands, 'frozen_comparisons': comparisons,
            'scratch_initial_exists': False, 'files_before_cleanup': files, 'scratch_final_exists': SCRATCH.exists(),
            'scratch_restored': not SCRATCH.exists(), 'provider_calls': 0, 'llm_calls': 0, 'fees_usd': 0},
            ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(status, 'scratch_restored=', not SCRATCH.exists(), flush=True)


if __name__ == '__main__':
    main()
