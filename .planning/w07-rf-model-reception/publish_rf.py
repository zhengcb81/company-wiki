"""Normal commit/push only; pins author/main states and preserves unrelated WIP."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

PLAN = Path(__file__).resolve().parent
ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w07/root-rf-model-reception')
MAIN = Path('C:/Users/郑曾波/Projects/revenue-forecast')

def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True, encoding='utf-8').strip()

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

freeze = json.loads((PLAN/'freeze.json').read_text(encoding='utf-8'))
assert git(ROOT, 'rev-parse', 'HEAD') == freeze['author_head']
assert git(MAIN, 'rev-parse', 'HEAD') == freeze['origin_main']
assert all(sha(MAIN/p) == h for p, h in freeze['main_wip'].items())

# One compressed native report, not several repeated full JSON copies.
folder = PLAN/'native-e2e'
report_path = folder/'model-generalization-matrix.json'
raw = report_path.read_bytes()
rep = json.loads(raw)
assert rep['status'] == 'COMPLETE' and not rep['residuals']
assert rep['cleanup']['owned_root_restored'] and rep['cleanup']['readonly_unchanged']
packed = PLAN/'native-e2e.json.gz'
assert not packed.exists()
packed.write_bytes(gzip.compress(raw, mtime=0))
receipt = {
    'schema': 'w07-root-rf-reception/1',
    'acceptance': 'ACCEPTED_PARTIAL_COVERAGE',
    'repository': str(MAIN), 'author_commits': ['d282c9d58734d2905d5c8b20aa9ee0db1541a1da', freeze['author_head']],
    'regressions': {'root_red': '22 failed / 1 passed', 'final': '36 passed / 4.19 seconds', 'original_assertions_unchanged': True},
    'native_e2e': {k: rep[k] for k in ['status', 'counts', 'class_status', 'combination_coverage', 'wall_seconds', 'cleanup', 'cli_evidence', 'residuals']},
    'payload': {'relative_to_company_wiki': '.planning/w07-rf-model-reception/native-e2e.json.gz', 'sha256_gzip': sha(packed), 'sha256_json': hashlib.sha256(raw).hexdigest(), 'bytes_json': len(raw), 'bytes_gzip': packed.stat().st_size},
    'scope': 'Engineering tool execution accepted; wider card combination coverage remains OPEN, not a source truth or economic conclusion.',
    'installation': 'Not applicable: engineering tools excluded from installed RF skill.',
    'provider_calls': 0, 'llm_calls': 0, 'cost_usd': 0,
    'wip_files_preserved': len(freeze['main_wip']),
    'publication': 'Normal commit/push pending; ROOT records exact-head CI separately.',
}
handoff = ROOT/'docs/handoffs/w07-rf-model-quality'
(handoff/'ROOT-reception.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
(handoff/'ROOT-reception.md').write_text('''# ROOT W07-RF-MODEL reception — 2026-10-11

**ACCEPTED_PARTIAL_COVERAGE**. Author commits are retained in history. The delivered
engineering tool needed shared fixes: exceptions were mistaken for contract
rejections, case references accumulated, missing/empty assertions passed, and
CLI/cleanup failures did not affect success. ROOT added behavior-first tests,
fixed those shared mechanisms, and kept author assertions unchanged.

ROOT RED: 22 failures / 1 pass. Final: 36 passes / 4.19 seconds. Actual 16-vector
native E2E: 11 PASS / 5 REJECT_OK, no failed/unrun vectors; all three shipped CLI
checks passed. New scratch root restored; existing sentinel test passed;
readonly code SHA unchanged. No native scripts, config, installed runtime,
production originals, sibling projects or paid calls changed.

Declared vector execution is COMPLETE; card combination coverage remains PARTIAL.
See README and ROOT-reception.json for explicit remaining CNY/HKD, acquisition /
control, joint volume/price, cumulative/net/cannibalization and future actual/WAPE
items. These are untested, not assertions that the native engine lacks support.
ROOT must extend meaningful inputs and independent expected arithmetic before
marking the whole card complete. No new per-commit/CI gate is introduced.

The author's five stale tool-file hashes and incorrect repository path are
diagnostic metadata errors. Original prepared inputs stayed byte-identical.
Actual commit and ROOT evidence, not extra signatures, establish delivery.
The bounded synthetic native payload is retained once as compressed JSON in
company-wiki/.planning/w07-rf-model-reception; hashes recorded in JSON. This
payload strategy does not authorize retaining complete real-company LLM logs.
''', encoding='utf-8')

# Retain only compressed payload and small receipt; remove our own duplicate files.
assert folder.resolve().parent == PLAN.resolve()
for name in ['model-generalization-matrix.json', 'model-generalization-matrix.md']:
    (folder/name).unlink()
folder.rmdir()
(PLAN/'reception.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

paths = ['tools/model_generalization_matrix/README.md', 'tools/model_generalization_matrix/bootstrap.py', 'tools/model_generalization_matrix/cases.py', 'tools/model_generalization_matrix/native.py', 'tools/model_generalization_matrix/report.py', 'tools/model_generalization_matrix/run.py', 'tools/model_generalization_matrix/runner.py', 'tools/tests/test_root_w07_model_boundaries.py', 'docs/handoffs/w07-rf-model-quality/ROOT-reception.json', 'docs/handoffs/w07-rf-model-quality/ROOT-reception.md']
subprocess.run(['git', '-C', str(ROOT), 'add', '--', *paths], check=True)
subprocess.run(['git', '-C', str(ROOT), 'commit', '-m', 'fix(tools): make model matrix failures attributable and restore scratch'], check=True)
head = git(ROOT, 'rev-parse', 'HEAD')
(PLAN/'implementation-commit.json').write_text(json.dumps({'commit': head, 'root_worktree': str(ROOT), 'author_included': True}, indent=2)+'\n', encoding='utf-8')
print('Committed ROOT corrections normally: '+head)
