"""Neutral local Git E2E for the actual hook/selector/pytest executor.

Only the business test bodies are synthetic stubs. No hook/runner is stubbed;
all remotes are local bare repositories below this review's owned scratch.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent


def run(source, label):
    fixture = source / f'.e2e-{label}'
    assert not fixture.exists()
    fixture.mkdir()
    (fixture / 'sentinel.txt').write_text('owner sentinel unchanged\n', encoding='utf-8')
    sentinel_sha = hashlib.sha256((fixture / 'sentinel.txt').read_bytes()).hexdigest()
    work = fixture / 'work'
    work.mkdir()
    spec = importlib.util.spec_from_file_location('review_gate_cases', source/'tools/pre_push_gate.py')
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    for name in ['.githooks/pre-push', 'tools/pre_push_gate.py', 'tools/changed_unit_tests.py']:
        path = work/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((source/name).read_bytes())
    by_path = {}
    for case in gate.FAST_CONTRACT_CASES:
        path, _, name = case.partition('::')
        by_path.setdefault(path, []).append(name)
    for path, names in by_path.items():
        target = work/path
        target.parent.mkdir(parents=True, exist_ok=True)
        lines = ['import pytest']
        for name in names:
            name = name or 'test_independent_neutral_smoke'
            if '[' in name:
                fn, parameter = name.split('[', 1)
                lines += [f"@pytest.mark.parametrize('case', [{parameter[:-1]!r}])", f'def {fn}(case): pass']
            else:
                lines += [f'def {name}(): pass']
        target.write_text('\n'.join(lines)+'\n', encoding='utf-8')
    (work/'.gitignore').write_text('__pycache__/\n', encoding='utf-8')
    commands = []
    def call(args, cwd=work):
        start = time.monotonic()
        p = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=120)
        commands.append(dict(command=args, cwd=str(cwd), exit_code=p.returncode,
                             seconds=round(time.monotonic()-start,3), stdout=p.stdout, stderr=p.stderr))
        return p
    def git(*args, cwd=work):
        p=call(['git',*args],cwd)
        assert p.returncode==0, p.stdout+p.stderr
        return p.stdout.strip()
    git('init','-q','-b','master')
    git('config','user.email','independent-review@example.invalid')
    git('config','user.name','W13 independent reviewer')
    git('config','core.hooksPath','.githooks')
    git('init','--bare','-q',str(fixture/'remote.git'),cwd=fixture)
    git('remote','add','origin',str(fixture/'remote.git'))
    git('add','-A')
    git('commit','-qm','neutral baseline')
    baseline = call(['git','push','origin','master'])
    assert baseline.returncode==0, baseline.stdout+baseline.stderr
    for i in range(33):
        target=work/f'tests/unit/test_review_new_{i:02}.py'
        target.write_text(f"def test_changed(): {'assert False, '+repr('hidden-wide-red') if i==0 else 'pass'}\n", encoding='utf-8')
    git('add','tests/unit')
    git('commit','-qm','thirty-three closed affected files include hidden failure')
    wide_head=git('rev-parse','HEAD')
    wide=call(['git','push','origin','master'])
    wide_output=wide.stdout+wide.stderr
    wide_ok = wide.returncode==0 and 'full_validation_pending' in wide_output
    checks=[dict(name='real_new_branch_push',passed=True),
            dict(name='real_33_file_closed_range_defers_whole_set', passed=wide_ok,
                 actual_exit_code=wide.returncode)]
    if wide_ok:
        assert git('ls-remote','origin','refs/heads/master').split()[0]==wide_head
    full=call([sys.executable,'-m','pytest','-q','-p','no:cacheprovider','tests/unit'])
    checks.append(dict(name='real_full_unit_command_finds_hidden_failure',
                       passed=full.returncode!=0 and 'hidden-wide-red' in full.stdout))
    first = gate.FAST_CONTRACT_CASES[0]
    path,_,name=first.partition('::')
    (work/path).write_text(f"def {name}(): assert False, 'real-ran-scope-red'\n",encoding='utf-8')
    git('add',path)
    git('commit','-qm','ran-scope smoke fails')
    red=call(['git','push','origin','master'])
    red_out=red.stdout+red.stderr
    checks.append(dict(name='real_ran_scope_red_blocks_push',
                       passed=red.returncode!=0 and 'real-ran-scope-red' in red_out and 'PUSH CHECKS RED' in red_out))
    (work/'tools/pre_push_gate.py').unlink()
    git('add','tools/pre_push_gate.py')
    git('commit','-qm','runner missing')
    missing=call(['git','push','origin','master'])
    checks.append(dict(name='real_missing_runner_blocks_push',
                       passed=missing.returncode!=0 and 'missing' in (missing.stdout+missing.stderr).lower()))
    assert hashlib.sha256((fixture/'sentinel.txt').read_bytes()).hexdigest()==sentinel_sha
    result=dict(label=label, scope='real local Git refs with actual reviewed hook/selector/executor and synthetic business bodies',
                source_sha256=hashlib.sha256((source/'tools/pre_push_gate.py').read_bytes()).hexdigest(),
                checks=checks, commands=commands, external_network_calls=0, model_calls=0,
                sentinel_preserved=True)
    result['fixture_restored_absent'] = False
    receipt=HERE/f'{label}-real-ref.json'
    receipt.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # Each target is resolved and contained before deleting only owned children.
    def clear_owned_readonly(function, path, exception):
        assert Path(path).resolve().is_relative_to(fixture.resolve())
        os.chmod(path, stat.S_IWRITE)
        function(path)
    for child in [work,fixture/'remote.git']:
        assert child.resolve().is_relative_to(fixture.resolve())
        shutil.rmtree(child,onexc=clear_owned_readonly)
    (fixture/'sentinel.txt').unlink()
    fixture.rmdir()
    result['fixture_restored_absent']=not fixture.exists()
    receipt.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'label':label,'checks':checks,'fixture_restored_absent':result['fixture_restored_absent']},ensure_ascii=False,indent=2))
    return any(not x['passed'] for x in checks)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',required=True,type=Path);parser.add_argument('--label',required=True)
    args=parser.parse_args();raise SystemExit(run(args.source.resolve(),args.label))
