"""Normal RF integration after frozen independent type/period acceptance."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
TREE = ROOT.parent / '_harness_worktrees/w05/rf-flow-root'
MAIN = ROOT.parent / 'revenue-forecast'
E = ROOT / 'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11/evidence/root-rf-flow-acceptance'
inventory = json.loads((E/'fix/price-correlation/root-product-inventory.json').read_text(encoding='utf-8'))
review = json.loads((E/'independent-price-final/final-review.json').read_text(encoding='utf-8'))
assert review['verdict'] == 'PASS_WITH_SCOPE' and review['all_frozen_shas_match'] and review['scratch_restored']
for row in inventory['files']:
    assert hashlib.sha256((TREE/row['path']).read_bytes()).hexdigest() == row['sha256'], row['path']

def output(cwd, *args):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()

def run(cwd, *args):
    return subprocess.run(args, cwd=cwd, check=True)

assert output(MAIN, 'git', 'rev-parse', 'HEAD') == inventory['base']
assert output(MAIN, 'git', 'branch', '--show-current') == 'main'
assert output(TREE, 'git', 'rev-parse', 'MERGE_HEAD') == inventory['original_delivery']
preserved = {n: hashlib.sha256((MAIN/n).read_bytes()).hexdigest() for n in
             ('assurance/runs/daily_alert.jsonl', 'assurance/runs/weekly_alert.jsonl',
              'assurance/runs/weekly_manifest.json')}
before_status = output(MAIN, 'git', 'status', '--porcelain')
target = TREE/'docs/handoffs/w05-rf-flow/ROOT-acceptance-final.json'
assert not target.exists()
target.write_text(json.dumps({
    'schema_version': 'root-w05-rf-flow-acceptance/1', 'status': 'PASS_WITH_SCOPE',
    'original_delivery': inventory['original_delivery'],
    'product_sha256': {row['path']: row['sha256'] for row in inventory['files']},
    'final_existing_gate': {'passed': 390, 'subtests': 36, 'pytest_seconds': 42,
                            'whole_entry_seconds': 46.311, 'ruff': 'PASS', 'mypy_public_11': 'PASS'},
    'independent': review,
    'prior_failures_preserved': True, 'native_frozen_outputs_byte_equal': 5,
    'canonical_wip_preserved_before': preserved,
    'scope': 'Shared period/type/source-provenance arithmetic, native CLI and strong readers; no source truth/economic certification',
    'publication': 'Normal local merge follows; install/push/precise remote CI are subsequent recorded steps',
}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
md = target.with_suffix('.md')
md.write_text('''# ROOT final RF flow acceptance

Accepted within the mathematical and runtime scope. Normal merge preserves the original delivery.
One shared period ancestry owns interval contributions, true non-zero dependencies and overlap;
recognition is ordered before causal driver evaluation. Stocks/rates/scalars cannot become annual
income through labels or aliases. Price interpretation remains correlated through shared symbols,
equivalent formulas and derived ancestry; cancelling equal price units supplies no annual duration.
Native annual ARPU/turnover/fee/yield and true flow-derived prices remain usable. Same-dimension
mixed raw price roles must use native roles or a true flow-derived price, rather than ambiguous labels.

Final existing engineering node:390 tests+36subtests, ruff and public mypy11 PASS. Non-author31 cases
and16 original P1 boundary checks pass;5 frozen native outputs are byte-identical. 3.9 compatibility
was previously verified and its scope is preserved. No schema permission, identity review, receipt,
or extra routine gate was introduced. Canonical assurance/output WIP is preserved, scratch restored,
provider/LLM/network/fees zero. Original failures are immutable evidence in the CWP W05 acceptance
directory. This does not certify real source qualifications, numeric source truth or economic forecasts.
Install is a subsequent17-file selective update to2 physical existing copies; no configuration/output
or entire skill directory replacement. Remote exact-SHA CI follows normal push.
''', encoding='utf-8')
run(TREE, 'git', 'add', '--', *(row['path'] for row in inventory['files']),
    str(target.relative_to(TREE)), str(md.relative_to(TREE)))
run(TREE, 'git', 'commit', '-m', 'fix(flow): preserve period ancestry and correlated price roles through native contracts')
head = output(TREE, 'git', 'rev-parse', 'HEAD')
run(MAIN, 'git', 'merge', '--ff-only', head)
after_status = output(MAIN, 'git', 'status', '--porcelain')
after = {n: hashlib.sha256((MAIN/n).read_bytes()).hexdigest() for n in preserved}
assert after == preserved and after_status == before_status
for row in inventory['files']:
    assert (MAIN/row['path']).read_bytes().replace(b'\r\n', b'\n') == (TREE/row['path']).read_bytes().replace(b'\r\n', b'\n'), row['path']
p = E/'local-main-integration.json'
assert not p.exists()
p.write_text(json.dumps({'integration_commit': head, 'main_head': output(MAIN,'git','rev-parse','HEAD'),
    'normal_hooks': True, 'canonical_wip_sha_before': preserved, 'canonical_wip_sha_after': after,
    'canonical_porcelain_before': before_status, 'canonical_porcelain_after': after_status,
    'product_LF_equal': 30, 'install_pending': True, 'remote_push_pending': True},
    ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('RF local normal integration', head, 'WIP preserved; selective installation/push next')
