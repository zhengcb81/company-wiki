import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

PLAN = Path(__file__).resolve().parent
MAIN = Path('C:/Users/郑曾波/Projects/revenue-forecast')
ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w07/root-rf-model-reception')
head = json.loads((PLAN/'implementation-commit.json').read_text(encoding='utf-8'))['commit']
freeze = json.loads((PLAN/'freeze.json').read_text(encoding='utf-8'))
def git(*args):
    return subprocess.check_output(['git', '-C', str(MAIN), *args], text=True, encoding='utf-8').strip()
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
assert all(sha(MAIN/p) == h for p, h in freeze['main_wip'].items())
current = git('rev-parse', 'HEAD')
assert current in {freeze['origin_main'], head}
if current != head:
    subprocess.run(['git', '-C', str(MAIN), 'merge', '--ff-only', head], check=True)
assert git('rev-parse', 'HEAD') == head
assert all(sha(MAIN/p) == h for p, h in freeze['main_wip'].items())
remote = git('ls-remote', 'origin', 'refs/heads/main').split()[0]
assert remote == head
record = {'schema': 'w07-root-publication/1', 'repository': str(MAIN), 'main_head': head, 'remote_main_head': remote, 'author_commits_included': all(subprocess.run(['git','-C',str(MAIN),'merge-base','--is-ancestor',c,head],capture_output=True).returncode == 0 for c in ['d282c9d58734d2905d5c8b20aa9ee0db1541a1da', freeze['author_head']]), 'main_wip_preserved_sha_files': len(freeze['main_wip']), 'main_status': git('status','--short'), 'normal_pre_push': '390 passed + 36 subtests / 32.07s; ruff and public types GREEN', 'skill_installation': 'not applicable (engineering tool only)', 'coverage': 'PARTIAL; see ROOT-rf-remaining-coverage.md', 'cost_usd': 0}
url = f'https://api.github.com/repos/zhengcb81/revenue-forecast/actions/runs?head_sha={head}&per_page=10'
try:
    req = urllib.request.Request(url, headers={'Accept':'application/vnd.github+json','User-Agent':'ROOT-W07-reception'})
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.load(response)
    record['ci'] = [{'id': r['id'], 'url': r['html_url'], 'head_sha': r['head_sha'], 'name': r['name'], 'status': r['status'], 'conclusion': r['conclusion']} for r in payload['workflow_runs'] if r['head_sha'] == head]
except Exception as exc:
    record['ci_lookup_error'] = f'{type(exc).__name__}: {exc}'
(PLAN/'publication.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
print(json.dumps(record,ensure_ascii=False,indent=2))
