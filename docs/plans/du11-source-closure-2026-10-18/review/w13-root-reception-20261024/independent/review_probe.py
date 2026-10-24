"""Independent scheduling probes; never runs a company's documents or models."""
from __future__ import annotations

import argparse
import ast
import contextlib
import hashlib
import importlib.util
import inspect
import io
import json
from pathlib import Path
import sys
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(source, label):
    sys.path.insert(0, str(source))
    gate = load(source / 'tools/pre_push_gate.py', 'independent_gate')
    assert Path(inspect.getfile(gate.select_unit_tests)).resolve() == source / 'tools/changed_unit_tests.py'
    results = []

    def check(name, fn):
        try:
            fn()
            results.append(dict(name=name, status='PASS'))
        except AssertionError as exc:
            results.append(dict(name=name, status='FAIL', detail=str(exc)))

    def wide(count):
        selected = [f'tests/unit/test_independent_{i}.py' for i in range(count)]
        targets, reason = gate._push_targets(selected)
        assert targets == list(gate.FAST_CONTRACT_CASES), f'{count} closed files became {len(targets)} ran targets'
        assert 'defer' in reason

    for count in [33, 65, 333]:
        check(f'wide_closed_{count}_wholly_deferred', lambda count=count: wide(count))

    def small():
        files = [f'tests/unit/test_independent_{i}.py' for i in range(32)]
        targets, _ = gate._push_targets([*files, *files])
        assert targets[:32] == files
        assert len(targets) == len(set(targets))
    check('small_boundary_complete_and_deduplicated', small)

    def directory(path):
        assert gate._push_targets([path])[0] == list(gate.FAST_CONTRACT_CASES)
    for path in ['tests/unit', 'tests/unit/source_catalog', 'tests/contract']:
        check(f'directory_not_one_small_file:{path}', lambda path=path: directory(path))

    def dispatch(code):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch.object(gate.sys, 'stdin', io.StringIO('ref input')), \
                patch.object(gate, 'changed_paths', return_value={'source.py'}), \
                patch.object(gate, 'select_unit_tests', return_value=(['tests/unit'], 'unknown range')):
            before = []
            def child(cmd, _label):
                before.append(output.getvalue())
                assert 'local_fast_pass' not in before[-1], 'PASS token printed before child ran'
                for target in gate.FAST_CONTRACT_CASES:
                    assert target in before[-1], 'actual target omitted from CLI output: ' + target
                return code
            with patch.object(gate, '_run_pytest_gate', side_effect=child):
                actual = gate.main(['--push-checks'])
        assert actual == code
        assert ('local_fast_pass' in output.getvalue()) == (code == 0)
        assert 'full_validation_pending' in output.getvalue()
    for code in [0, 7, 124]:
        check(f'honest_output_and_exact_exit:{code}', lambda code=code: dispatch(code))

    def exceptions(exc):
        with contextlib.redirect_stdout(io.StringIO()), patch.object(gate.sys, 'stdin', io.StringIO('refs')), \
                patch.object(gate, 'changed_paths', return_value=None), \
                patch.object(gate, '_run_pytest_gate', side_effect=exc):
            assert gate.main(['--push-checks']) != 0
    for exc in [OSError('no executable'), TimeoutError('runner timeout'), ValueError('runner malformed')]:
        check('exception_blocks:' + type(exc).__name__, lambda exc=exc: exceptions(exc))

    baseline = load(source / '.baseline_pre_push_gate.py', 'independent_baseline_gate')
    def unchanged_constants_and_executors():
        assert gate.FAST_CONTRACT_CASES == baseline.FAST_CONTRACT_CASES
        assert gate.CURRENT_CI_REGRESSION_CASES == baseline.CURRENT_CI_REGRESSION_CASES
        for name in ['_run', '_run_pytest_gate', '_explicit_test_paths']:
            assert ast.dump(ast.parse(inspect.getsource(getattr(gate, name)))) == ast.dump(ast.parse(inspect.getsource(getattr(baseline, name)))), name
    check('all_fast_members_and_full_executors_unchanged_from_base', unchanged_constants_and_executors)

    def capture(module, args):
        commands = []
        def child(cmd, label, **kwargs):
            commands.append(dict(command=cmd, label=label, extra=kwargs))
            return 0
        with contextlib.redirect_stdout(io.StringIO()), patch.object(module, '_run', side_effect=child), \
                patch.object(module, '_run_pytest_gate', side_effect=child):
            assert module.main(args) == 0
        return commands
    for args in [[], ['--skip-contract'], ['--fast-contracts-only'], ['--fast-contracts-only', '--junitxml', 'report.xml']]:
        def same(args=args):
            assert capture(gate, args) == capture(baseline, args), args
        check('full_and_ci_actual_command_contract:' + repr(args), same)

    result = dict(scope='independent offline execution-policy controls, not business testing',
                  label=label, source_root=str(source),
                  gate_sha256=hashlib.sha256((source/'tools/pre_push_gate.py').read_bytes()).hexdigest(),
                  helper_sha256=hashlib.sha256((source/'tools/changed_unit_tests.py').read_bytes()).hexdigest(),
                  results=results, passed=sum(r['status']=='PASS' for r in results),
                  failed=sum(r['status']=='FAIL' for r in results))
    (HERE / f'{label}-probes.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return bool(result['failed'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.source.resolve(), args.label))
