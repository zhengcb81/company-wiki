"""Selective install using RF's existing installer; retain unrelated metadata."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT.parent / 'revenue-forecast'
E = ROOT / 'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11/evidence/root-rf-flow-acceptance'
HEAD = '30ddae8ed2a457c418e63b182e7d8c9230fbf3ff'
FILES = ['CHANGELOG.md', 'SKILL.md', 'references/dated-contribution.md',
         'references/input-construction.md', 'references/input-schema.md',
         'references/output-schema.md', 'scripts/contracts/annual_consumption.py',
         'scripts/contracts/constants.py', 'scripts/contracts/document.py',
         'scripts/contracts/period_flow.py', 'scripts/contracts/recognition.py',
         'scripts/forecast/segments.py', 'scripts/generate_input_template.py',
         'scripts/research/drivers.py', 'scripts/revenue_core.py',
         'scripts/revenue_report.py', 'scripts/schema_compatibility.py']

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

def call(*extra):
    command = [sys.executable, '-X', 'utf8', '-B', str(MAIN/'tools/sync_installations.py'),
               '--canonical', str(MAIN)]
    for name in FILES:
        command.extend(['--file', name])
    result = subprocess.run(command + list(extra), cwd=MAIN, capture_output=True,
                            text=True, encoding='utf-8', check=True)
    assert not result.stderr.strip(), result.stderr
    return json.loads(result.stdout)

def unselected_metadata(target):
    # No contents read, including user config, output and credentials.
    return {p.relative_to(target).as_posix(): [p.stat().st_size, p.stat().st_mtime_ns]
            for p in target.rglob('*') if p.is_file()
            and p.relative_to(target).as_posix() not in FILES}

mode = argparse.ArgumentParser()
mode.add_argument('mode', choices=('plan', 'apply'))
args = mode.parse_args()
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=MAIN, text=True).strip() == HEAD
plan_path = E/'canonical-install-plan.json'
before_path = E/'canonical-install-unselected-before.json'
receipt_path = E/'installation.json'
if args.mode == 'plan':
    assert not plan_path.exists() and not before_path.exists()
    plan = call('--plan')
    assert plan['selected'] == sorted(FILES) and len(plan['targets']) == 2
    before = {str(Path(row['target']).resolve()): unselected_metadata(Path(row['target']))
              for row in plan['targets']}
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    before_path.write_text(json.dumps(before, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'main': HEAD, 'selected': len(FILES), 'targets': [
        {k: row[k] for k in ('target', 'selected_drift', 'unselected_drift')}
        for row in plan['targets']]}, ensure_ascii=False))
else:
    assert not receipt_path.exists()
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    before = json.loads(before_path.read_text(encoding='utf-8'))
    for row in plan['targets']:
        target = Path(row['target'])
        assert unselected_metadata(target) == before[str(target.resolve())]
        for file in row['files']:
            assert sha(target/file['path']) == file['before_sha256'], file['path']
            assert sha(MAIN/file['path']) == file['source_sha256'], file['path']
    applied = call('--apply', '--json')
    (E/'canonical-install-apply.json').write_text(json.dumps(applied, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    assert applied['status'] == 'completed'
    checked = call('--json')
    (E/'canonical-install-check.json').write_text(json.dumps(checked, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    assert checked['status'] == 'completed'
    for row in plan['targets']:
        target = Path(row['target'])
        assert unselected_metadata(target) == before[str(target.resolve())]
        for file in row['files']:
            assert sha(target/file['path']) == file['source_sha256'], file['path']
    receipt_path.write_text(json.dumps({'schema': 'root-rf-selective-install/1',
        'canonical_head': HEAD, 'selected_per_copy': 17, 'physical_copies': 2,
        'selected_sha_match': 34, 'unselected_metadata_unchanged': True,
        'preexisting_unselected_drift_per_copy': [row['unselected_drift'] for row in plan['targets']],
        'apply': applied, 'check': checked, 'whole_directory_replaced': False,
        'provider_calls': 0, 'llm_calls': 0, 'cost_micro_usd': 0},
        ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Installed17 selected files x2physicalcopies; all34SHA match; unrelated files unchanged')
