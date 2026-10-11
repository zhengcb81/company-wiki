"""Record exact successful publication and remove only the clean accepted checkout."""
from pathlib import Path
import hashlib
import json
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
TREE = ROOT.parent/'_harness_worktrees/w06/cwp-portability-root'
W06 = ROOT/'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w06_parallel_verification_2026-10-11'
E = W06/'evidence/root-cwp-portability-acceptance'
HEAD = '6dd7a1197f480c05ced36c6865b89f7f23d49ba6'

def out(cwd, *args):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()

assert not (E/'publication.json').exists(), 'publication receipt already written'
assert out(ROOT, 'git', 'rev-parse', 'HEAD') == HEAD
assert out(ROOT, 'git', 'ls-remote', 'origin', 'refs/heads/master').split()[0] == HEAD
request = urllib.request.Request('https://api.github.com/repos/zhengcb81/company-wiki/actions/runs/38145427297',
                                 headers={'User-Agent': 'Codex-W06-reception'})
with urllib.request.urlopen(request, timeout=30) as response:
    ci = json.load(response)
assert ci['head_sha'] == HEAD and ci['status'] == 'completed' and ci['conclusion'] == 'success'
assert TREE.resolve().parent == (ROOT.parent/'_harness_worktrees/w06').resolve()
assert TREE.name == 'cwp-portability-root' and TREE.is_dir()
assert out(TREE, 'git', 'rev-parse', 'HEAD') == '5f10af0bafafb1c13d26d1afd9821e83dd8b7168'
assert not out(TREE, 'git', 'status', '--porcelain')
ignored = out(TREE, 'git', 'status', '--ignored', '--short').splitlines()
assert set(ignored) <= {'!! .pytest_cache/', '!! .ruff_cache/'}
subprocess.run(['git', 'merge-base', '--is-ancestor', '5f10af0b', HEAD], cwd=ROOT, check=True)
freeze = json.loads((E/'fix/verdict-aggregation/product-freeze.json').read_text(encoding='utf-8'))
for row in freeze['files']:
    original = (TREE/row['path']).read_bytes()
    assert hashlib.sha256(original).hexdigest() == row['sha256']
    assert (ROOT/row['path']).read_bytes().replace(b'\r\n', b'\n') == original.replace(b'\r\n', b'\n')
files = [p for p in TREE.rglob('*') if p.is_file()]
bytes_removed = sum(p.stat().st_size for p in files)
subprocess.run(['git', 'worktree', 'remove', str(TREE.resolve())], cwd=ROOT, check=True)
assert not TREE.exists()
receipt = {'schema': 'root-w06-portability-publication/1', 'status': 'PUBLISHED_WITH_SCOPE',
           'acceptance_commit': '5f10af0bafafb1c13d26d1afd9821e83dd8b7168',
           'main_merge': 'e2e19ea200bf87b13dd41d6389897ea5f2711d93', 'published_head': HEAD,
           'remote_exact': True, 'normal_commit_push_hooks': True,
           'prepush': {'passed': 3305, 'seconds': 212.82},
           'ci': {k: ci[k] for k in ['id', 'head_sha', 'status', 'conclusion', 'html_url']},
           'engineering': {'passed': 69, 'host_symlink_skipped': 1},
           'actual_synthetic_reader_cli_scenarios': 7, 'independent_cases': 53,
           'product_LF_match_files': len(freeze['files']),
           'cleanup': {'removed_checkout': str(TREE), 'file_count': len(files), 'bytes': bytes_removed,
                       'force': False, 'ignored_only': ignored, 'branch_worker_evidence_kept': True},
           'installation': 'Repository-only manual tools; no skill installation required',
           'scope': 'Windows synthetic roots/Reader/full SourceRef/CLI/oracle; not real cloud or POSIX or model quality',
           'provider_calls': 0, 'llm_calls': 0, 'fee_micro_usd': 0}
(E/'publication.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
for name in ['task_plan.md', 'findings.md', 'progress.md']:
    path = ROOT/'.planning/w06-cwp-portability-reception'/name
    body = path.read_text(encoding='utf-8')
    body = body.replace('远端发布待记录', '远端发布完成，6dd7a119/CI38145427297 success')
    body = body.replace('- [ ] C发布：', '- [x] C发布：')
    body += '\n发布完成：main/origin/master6dd7a119；精确CI38145427297 success，正常push3305PASS212.82s。干净ROOT checkout正常移除，branch/worker/历史FAIL保留；详细事实见 publication.json。\n'
    path.write_text(body, encoding='utf-8')
path = W06/'ROOT-reception-status.md'
body = path.read_text(encoding='utf-8').replace(
    '已正常接worker并ROOT5f10af0b、并入本地主线；收尾证据与正常远端push/CI跟进。未增加生产许可或技能安装',
    '正常ROOT5f10af0b并线发布master6dd7a119，精确CI38145427297成功/正常push3305PASS；ROOT干净checkout已移除。手动工具无需技能安装')
path.write_text(body, encoding='utf-8')
print(json.dumps({'published_head': HEAD, 'ci': ci['id'], 'checkout_bytes_released': bytes_removed}))
