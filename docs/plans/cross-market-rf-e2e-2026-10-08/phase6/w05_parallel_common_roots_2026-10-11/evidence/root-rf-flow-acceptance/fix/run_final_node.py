"""Bounded ROOT acceptance node: existing gate, portable compat, native CLI E2E.

No network/model providers; raw/config/install directories are never written.
Only owned scratch and eight small frozen synthetic artifacts are created.
"""
from __future__ import annotations

import copy
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
SCRATCH = EVIDENCE / 'e2e-scratch'
FROZEN = ROOT / 'docs/handoffs/w05-rf-flow/e2e/frozen'
LOG = EVIDENCE / 'final-engineering.log'
RECORDS = []
ENV = os.environ.copy()
for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR', 'GIT_INDEX_FILE',
             'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES',
             'GIT_PREFIX', 'GIT_NAMESPACE', 'GIT_QUARANTINE_PATH'):
    ENV.pop(name, None)
ENV.update(PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
           FF_V2_CODE_ROOT='C:/Users/郑曾波/Projects/filing-fetch',
           CWP_V2_CODE_ROOT='C:/Users/郑曾波/Projects/company-wiki',
           REVENUE_PUBLICATION_REGISTRY=str(SCRATCH / 'publication-registry.jsonl'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(arguments, label, timeout=60):
    start = time.monotonic()
    process = subprocess.run(arguments, cwd=ROOT, env=ENV, capture_output=True,
                             text=True, encoding='utf-8', errors='replace', timeout=timeout)
    record = {'label': label, 'command': arguments, 'exit_code': process.returncode,
              'seconds': round(time.monotonic() - start, 3)}
    RECORDS.append(record)
    with LOG.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + '\n')
        stream.write(process.stdout + process.stderr + '\n')
    print(label, 'exit=', process.returncode, 'seconds=', record['seconds'], flush=True)
    if process.returncode:
        raise RuntimeError(f'{label} failed; original failure preserved in {LOG}')


def remove_owned(path):
    resolved = path.resolve()
    assert resolved.parent == EVIDENCE.resolve() and resolved.name == 'e2e-scratch'
    for file in resolved.rglob('*'):
        if file.is_file():
            file.chmod(stat.S_IREAD | stat.S_IWRITE)
    shutil.rmtree(resolved)


def main():
    assert not SCRATCH.exists(), 'refuse to overwrite a preexisting scratch'
    assert not FROZEN.exists(), 'refuse to overwrite previously frozen evidence'
    SCRATCH.mkdir()
    LOG.write_text('ROOT final engineering node; 0 provider/LLM calls, 0 fees\n', encoding='utf-8')
    initial = {'scratch_exists': False, 'frozen_exists': False}
    status = 'FAIL'
    try:
        run([sys.executable, '-B', 'tools/pre_push_gate.py'], 'existing shared daily gate', 120)
        run([sys.executable, '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '-q',
             '--basetemp', str(SCRATCH / 'compat-pytest'),
             'tests/test_contract_registry.py', 'tests/test_compatibility_manifest.py',
             'tests/test_m3_period_flow_contract.py', 'tests/test_m3_schema_compatibility.py'],
            'portable legacy compatibility and 3.9 field semantics')
        run([sys.executable, '-B', 'docs/handoffs/w05-rf-flow/e2e/build_inputs.py', str(SCRATCH)],
            'native fixture generator')
        run([sys.executable, '-B', 'scripts/generate_input_template.py', '--name', 'FixtureCo Template (synthetic)',
             '--base-year', '2025', '--forecast-years', '2026', '2027', '--segments', 'Segment A',
             '--schema', '3.10', '--currency', 'CNY', '--output', str(SCRATCH / 'template-3.10.json')],
            'schema3.10 native template generation')
        for case in ('case1_acquisition', 'case2_offset_fy'):
            source = SCRATCH / (case + '.input.json')
            run([sys.executable, '-B', 'scripts/revenue_forecast.py', str(source), '--validate-only', '--verbose'],
                case + ' native validation')
            run([sys.executable, '-B', 'scripts/revenue_forecast.py', str(source),
                 '--output', str(SCRATCH / (case + '.forecast.json')),
                 '--markdown', str(SCRATCH / (case + '.forecast.md'))], case + ' forecast/report')
            for kind in (('window', 'currency') if case == 'case1_acquisition' else ('window',)):
                run([sys.executable, '-B', 'docs/handoffs/w05-rf-flow/e2e/read_and_tamper.py',
                     str(SCRATCH / (case + '.forecast.json')), kind], case + ' native strong reader/rehashed ' + kind)
        run([sys.executable, '-B', 'scripts/revenue_backtest.py', 'create',
             str(SCRATCH / 'case1_acquisition.input.json'), '--version', 'w05-root-cny-v1',
             '--output', str(SCRATCH / 'case1_acquisition.snapshot.json')], 'native immutable snapshot creation')
        run([sys.executable, '-B', 'scripts/revenue_forecast.py', str(SCRATCH / 'case1_acquisition.input.json'),
             '--output', str(SCRATCH / 'repeat.forecast.json')], 'full forecast determinism second native CLI')
        first = json.loads((SCRATCH / 'case1_acquisition.forecast.json').read_text(encoding='utf-8'))
        second = json.loads((SCRATCH / 'repeat.forecast.json').read_text(encoding='utf-8'))
        assert first == second, 'full native forecast was not deterministic'
        sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'compatibility')]
        os.environ['REVENUE_PUBLICATION_REGISTRY'] = ENV['REVENUE_PUBLICATION_REGISTRY']
        from revenue_backtest import validate_snapshot
        from revenue_core import ForecastInputError, canonical_sha256
        from compatibility_manifest import load_manifest, validate_manifest, validate_repository_ancestry
        from contract_registry import load, validate_canonical_documents
        snapshot = json.loads((SCRATCH / 'case1_acquisition.snapshot.json').read_text(encoding='utf-8'))
        validate_snapshot(snapshot)
        forged = copy.deepcopy(snapshot)
        target = next(item for item in forged['forecast_result']['parameter_trace'] if item.get('time_basis') == 'period_flow')
        target['period_end'] = '2026-12-31'
        result = forged['forecast_result']
        result['result_sha256'] = canonical_sha256({key: value for key, value in result.items() if key != 'result_sha256'})
        forged['forecast_result_sha256'] = canonical_sha256(result)
        identity = {key: forged[key] for key in ('company_name', 'as_of_date', 'forecast_version', 'input_sha256',
                                                'forecast_result_sha256', 'engine_version', 'forecast_schema_version',
                                                'snapshot_schema_version')}
        forged['snapshot_id'] = canonical_sha256(identity)
        try:
            validate_snapshot(forged)
        except (ForecastInputError, TypeError) as error:
            snapshot_tamper = str(error)
        else:
            raise AssertionError('rehashed snapshot window forgery accepted')
        case1 = json.loads((SCRATCH / 'case1_acquisition.input.json').read_text(encoding='utf-8'))
        c1 = next(item for item in case1['parameters'] if item['parameter_id'] == 'cmp_post_2026')
        assert case1['currency'] == first['currency'] == 'CNY'
        assert c1['unit'] == 'CNY million' and c1['value'] == 1.29190208
        assert c1['period_start'] == '2026-05-31' and c1['period_end'] == '2026-06-30'
        case2 = json.loads((SCRATCH / 'case2_offset_fy.forecast.json').read_text(encoding='utf-8'))
        total2 = next(item for item in case2['parameter_trace'] if item['parameter_id'] == 'fy26_total')
        assert total2['value'] == 20 and case2['fiscal_year_end'] == '06-30'
        assert total2['period_start'] == '2025-07-01' and total2['period_end'] == '2026-06-30'
        projects = Path('C:/Users/郑曾波/Projects')
        real_roots = {'revenue': ROOT, 'filing': projects / 'filing-fetch', 'wiki': projects / 'company-wiki'}
        real_manifest = load_manifest()
        pure = validate_manifest(real_manifest)
        ancestry = validate_repository_ancestry(real_manifest, real_roots)
        documents = validate_canonical_documents(load(), {'company-wiki': projects / 'company-wiki'})
        assert pure == ancestry == documents == [], (pure, ancestry, documents)
        checks = {'full_forecast_deterministic': True, 'c1_actual_cny_unit_and_window': c1,
                  'c2_offset_fye': total2, 'snapshot_reader': 'PASS', 'rehashed_snapshot_tamper_rejected': snapshot_tamper,
                  'portable_unit_tests': 'explicit temporary repos/docs',
                  'real_integration_roots': {key: str(value) for key, value in real_roots.items()},
                  'real_manifest_structural': pure, 'real_manifest_ancestry': ancestry, 'real_canonical_docs': documents,
                  'provider_calls': 0, 'llm_calls': 0, 'fees_usd': 0}
        (EVIDENCE / 'final-checkpoints.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        FROZEN.mkdir()
        names = ['case1_acquisition.input.json', 'case1_acquisition.forecast.json', 'case1_acquisition.forecast.md',
                 'case1_acquisition.snapshot.json', 'case2_offset_fy.input.json', 'case2_offset_fy.forecast.json',
                 'case2_offset_fy.forecast.md', 'template-3.10.json']
        inventory = []
        for name in names:
            source = SCRATCH / name
            target = FROZEN / name
            shutil.copyfile(source, target)
            inventory.append({'path': target.relative_to(ROOT).as_posix(), 'bytes': target.stat().st_size,
                              'sha256': digest(target)})
        assert sum(item['bytes'] for item in inventory) < 8 * 1024 * 1024
        manifest = {'schema': 'w05-root-frozen-e2e/1', 'artifacts': inventory,
                    'total_bytes': sum(item['bytes'] for item in inventory), 'raw_originals_copied': 0,
                    'provider_calls': 0, 'llm_calls': 0, 'fees_usd': 0,
                    'generator': 'docs/handoffs/w05-rf-flow/e2e/build_inputs.py',
                    'scope': 'synthetic offline engineering, C1 sealed value/window retained in CNY; not economic acceptance'}
        (FROZEN / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        status = 'PASS'
    finally:
        before = [{'path': path.relative_to(SCRATCH).as_posix(), 'bytes': path.stat().st_size}
                  for path in SCRATCH.rglob('*') if path.is_file()]
        remove_owned(SCRATCH)
        result = {'status': status, 'commands': RECORDS, 'initial': initial,
                  'owned_scratch_files_before_cleanup': before, 'scratch_exists_after': SCRATCH.exists(),
                  'original_scratch_state_restored': not SCRATCH.exists(),
                  'product_frozen_exists_after': FROZEN.exists(), 'provider_calls': 0, 'llm_calls': 0, 'fees_usd': 0}
        (EVIDENCE / 'final-node.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('Final node', status, 'scratch restored=', not SCRATCH.exists(), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
