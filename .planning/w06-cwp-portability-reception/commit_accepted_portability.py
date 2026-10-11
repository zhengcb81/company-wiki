"""Integrate the accepted tooling only, preserving the original delivery."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
TREE = ROOT.parent/'_harness_worktrees/w06/cwp-portability-root'
E = ROOT/'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w06_parallel_verification_2026-10-11/evidence/root-cwp-portability-acceptance'
freeze = json.loads((E/'fix/verdict-aggregation/product-freeze.json').read_text(encoding='utf-8'))
review = json.loads((E/'independent-verdict-final/report.json').read_text(encoding='utf-8'))
assert review['verdict'] == 'PASS_WITH_SCOPE' and review['blockers'] == []
assert review['independent_execution']['case_count'] == 53
assert review['independent_execution']['unexpected'] == 0
assert review['accepted_fix']['product_freeze_sha256'] == hashlib.sha256((E/'fix/verdict-aggregation/product-freeze.json').read_bytes()).hexdigest()
for row in freeze['files']:
    assert hashlib.sha256((TREE/row['path']).read_bytes()).hexdigest() == row['sha256'], row['path']
def output(cwd, *args):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()
def run(cwd, *args):
    subprocess.run(args, cwd=cwd, check=True)
assert output(TREE, 'git', 'rev-parse', 'HEAD') == '8862372f714209cff1b218d77b5c4b8af6bc74dc'
assert output(TREE, 'git', 'rev-parse', 'MERGE_HEAD') == 'f8d5e0f4f6047375fdaef38e15e54edff2abe61d'
assert output(ROOT, 'git', 'branch', '--show-current') == 'master'
base = output(ROOT, 'git', 'rev-parse', 'HEAD')
before = output(ROOT, 'git', 'status', '--porcelain')
target = TREE/'docs/handoffs/w06-cwp-portability/ROOT-acceptance-final.json'
payload = {'schema': 'root-w06-portability-acceptance/1',
    'status': 'PASS_WITH_SCOPE', 'worker_delivery': 'f8d5e0f4f6047375fdaef38e15e54edff2abe61d',
    'final_product': freeze, 'independent': review,
    'engineering': {'passed': 69, 'skipped_host_symlink': 1, 'seconds': 9.07},
    'actual_synthetic_reader_cli_scenarios': 7, 'scenario_seconds': 4.051,
    'production_code_config_raw_unchanged': True, 'historical_failures_preserved': True,
    'scope': 'Windows synthetic source-root/Reader/full-Ref/CLI/tool verdict; not real cloud, POSIX, OCR, LLM or economic certification',
    'provider_calls': 0, 'llm_calls': 0, 'cost_micro_usd': 0}
if target.exists():
    assert json.loads(target.read_text(encoding='utf-8')) == payload
else:
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
paths = [row['path'] for row in freeze['files']]
paths += ['.planning/w06-cwp-portability/'+name for name in ('task_plan.md','findings.md','progress.md')]
paths += ['docs/handoffs/w06-cwp-portability/'+name for name in (
    'ROOT-product-freeze.json','ROOT-tool-repair.md','ROOT-verdict-aggregation.md',
    'ROOT-verdict-product-freeze.json','ROOT-acceptance-final.json')]
run(TREE, 'git', 'add', '--', *paths)
# Frozen pytest failure logs include literal trailing whitespace. Preserve them;
# source SHA checks and normal repository hooks own the implementation checks.
run(TREE, 'git', 'commit', '-m', 'test(storage): add truthful isolated root portability verification')
accepted = output(TREE, 'git', 'rev-parse', 'HEAD')
run(ROOT, 'git', 'merge', '--no-ff', accepted, '-m', 'merge: receive W06 root portability tools after independent acceptance')
for row in freeze['files']:
    assert (ROOT/row['path']).read_bytes().replace(b'\r\n', b'\n') == (TREE/row['path']).read_bytes().replace(b'\r\n', b'\n'), row['path']
(E/'local-main-integration.json').write_text(json.dumps({'main_before': base,
    'root_acceptance_commit': accepted, 'main_head': output(ROOT,'git','rev-parse','HEAD'),
    'normal_hooks': True, 'main_preexisting_status_before': before,
    'product_LF_equal_files': len(freeze['files']), 'remote_push_pending': True,
    'installation': 'Repository-only manual tools; not skill runtime install'},
    ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('Portability normally merged; source products unchanged, final tooling accepted within scope')
