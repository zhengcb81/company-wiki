"""Commit accepted runtime leaves and prepare three isolated code worktrees."""
from pathlib import Path
import hashlib
import json
import subprocess
import tarfile
import io

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'prepared-roots.json'
assert not OUT.exists(), 'Do not recreate or overwrite assigned worktrees'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
freeze_path = ROOT / '.planning/w06-cross-period-acquisition/cutoff-implementation/product-freeze-v2.json'
freeze = json.loads(freeze_path.read_text(encoding='utf-8'))
old = {'ff': ROOT.parent / '_harness_worktrees/w06/ff-contract-matrix-root',
       'et': ROOT.parent / '_harness_worktrees/w06/et-cutoff-root'}

def git(root, *args):
    result = subprocess.run(['git', *args], cwd=root, capture_output=True, check=True)
    return result.stdout.decode('utf-8', errors='replace').strip()

for row in freeze['files']:
    assert sha(old[row['repository']] / row['path']) == row['sha256'], row['path']
heads = {}
for repo, tree in old.items():
    assert git(tree, 'branch', '--show-current').startswith('codex/root-w06-')
    assert not git(tree, 'diff', '--cached', '--name-only')
    selected = [row['path'] for row in freeze['files'] if row['repository'] == repo]
    for name in ('.planning/w06-cutoff-result', 'docs/handoffs/w06-cutoff-result'):
        selected += [p.relative_to(tree).as_posix() for p in (tree / name).rglob('*') if p.is_file()]
    subprocess.run(['git', 'add', '--pathspec-from-file=-', '--pathspec-file-nul'], cwd=tree,
                   input=b''.join(p.encode('utf-8') + b'\0' for p in sorted(set(selected))), check=True)
    subprocess.run(['git', 'commit', '-m', 'fix: preserve transcript cutoff diagnostics and measured usage'], cwd=tree, check=True)
    heads[repo] = git(tree, 'rev-parse', 'HEAD')
    print('FROZEN_BRANCH_COMMIT', repo, heads[repo], flush=True)
for row in freeze['files']:
    assert sha(old[row['repository']] / row['path']) == row['sha256'], row['path']

specs = {
 'W07-RF-MODEL': {'repo': ROOT.parent / 'revenue-forecast', 'ref': '30ddae8ed2a457c418e63b182e7d8c9230fbf3ff',
   'directory': 'rf-model-quality', 'branch': 'codex/w07-rf-model-quality',
   'sparse': ['scripts', 'references', 'tests', 'tools', 'agents', 'config', 'compatibility', '.githooks']},
 'W07-AUDIT-ANALYST': {'repo': ROOT.parent / 'revenue-forecast-audit', 'ref': '9cd5ff8a2c8f9c1726c4047785164e3263673614',
   'directory': 'audit-analyst-quality', 'branch': 'codex/w07-audit-analyst-quality'},
 'W07-FF-PERF': {'repo': ROOT.parent / 'filing-fetch', 'ref': heads['ff'],
   'directory': 'ff-matrix-efficiency', 'branch': 'codex/w07-ff-matrix-efficiency'},
}
record = {'schema': 'root-w07-prepared-roots/1', 'cutoff_product_freeze_sha256': sha(freeze_path),
          'runtime_branch_commits': heads, 'runtime_release': 'not merged to main; complete matrix pending', 'lanes': {}}
for lane, spec in specs.items():
    directory = ROOT.parent / '_harness_worktrees/w07' / spec['directory']
    assert not directory.exists(), str(directory)
    directory.parent.mkdir(parents=True, exist_ok=True)
    command = ['git', 'worktree', 'add']
    if spec.get('sparse'):
        command += ['--no-checkout']
    command += ['-b', spec['branch'], str(directory), spec['ref']]
    subprocess.run(command, cwd=spec['repo'], check=True)
    if spec.get('sparse'):
        subprocess.run(['git', 'sparse-checkout', 'set', '--cone', *spec['sparse']], cwd=directory, check=True)
        subprocess.run(['git', 'read-tree', '-mu', 'HEAD'], cwd=directory, check=True)
    record['lanes'][lane] = {'repository': str(spec['repo']), 'workdir': str(directory),
        'branch': spec['branch'], 'base_commit': git(directory, 'rev-parse', 'HEAD'),
        'sparse_paths': spec.get('sparse'), 'working_tree_status': git(directory, 'status', '--short')}
    print('READY', lane, directory, flush=True)

# Fixed code-only dependencies: no original documents, production configs, keys,
# or existing research outputs. Git archive reads exact committed bytes.
ff_tree = Path(record['lanes']['W07-FF-PERF']['workdir'])
dep_root = ff_tree / '.planning/w07-ff-matrix-efficiency/input/runtime'
deps = {}
for name, repo, ref, paths in (
    ('et', old['et'], heads['et'], None),
    ('cwp', ROOT, git(ROOT, 'rev-parse', 'HEAD'), ['src', 'pyproject.toml'])):
    if paths is None:
        names = git(repo, 'ls-tree', '--name-only', ref).splitlines()
        paths = [p for p in names if p.endswith('.py') or p in ('requirements.txt', 'pyproject.toml')]
    archive = subprocess.run(['git', 'archive', '--format=tar', ref, *paths], cwd=repo,
                             capture_output=True, check=True).stdout
    destination = dep_root / name
    destination.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:') as tar:
        for member in tar.getmembers():
            target = (destination / member.name).resolve()
            assert target.is_relative_to(destination.resolve())
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(tar.extractfile(member).read())
            else:
                raise ValueError('Runtime dependency must contain only regular files and directories')
    files = {p.relative_to(destination).as_posix(): {'sha256': sha(p), 'bytes': p.stat().st_size}
             for p in destination.rglob('*') if p.is_file()}
    deps[name] = {'repository': str(repo), 'commit': ref, 'root': str(destination), 'files': files,
                  'bytes': sum(row['bytes'] for row in files.values())}
manifest = dep_root.parent / 'dependency-manifest.json'
manifest.write_text(json.dumps({'schema': 'w07-fixed-code-dependencies/1', 'dependencies': deps},
    ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
record['lanes']['W07-FF-PERF']['dependencies'] = {'manifest': str(manifest),
    'manifest_sha256': sha(manifest), 'et_root': deps['et']['root'], 'cwp_root': deps['cwp']['root']}
OUT.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('PREPARED', OUT, flush=True)
