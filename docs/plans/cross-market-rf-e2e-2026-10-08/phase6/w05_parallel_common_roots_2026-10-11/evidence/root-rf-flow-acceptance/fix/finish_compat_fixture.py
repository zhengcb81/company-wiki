from pathlib import Path
ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root')
path = ROOT / 'compatibility/compatibility_manifest.py'
body = path.read_text(encoding='utf-8')
old = '    if baseline == head:\n        return True\n'
assert old in body
path.write_text(body.replace(old, ''), encoding='utf-8')
path = ROOT / 'tests/test_compatibility_manifest.py'
body = path.read_text(encoding='utf-8')
body = body.replace('Six tiny real commits', 'Nine tiny real commits')
old = '                roots[name], floor[name] = root, fixture_git(root, "rev-parse", "HEAD")\n'
new = (old + '                fixture_git(root, "commit", "--quiet", "--allow-empty", "-m", "current")\n')
assert old in body
body = body.replace(old, new)
body = body.replace('yield {"frozen_baseline_triplet": floor, "current_triplet": dict(floor)}, roots',
                    'yield {"frozen_baseline_triplet": floor, "current_triplet": {name: fixture_git(root, "rev-parse", "HEAD") for name, root in roots.items()}}, roots')
body = body.replace('fixture_git(roots["revenue"], "rev-parse", "HEAD~1")', 'fixture_git(roots["revenue"], "rev-parse", "HEAD~2")')
path.write_text(body, encoding='utf-8')
print('Explicit ancestry now always reads actual Git objects, even equal commits; temp fixture has real descendant and regression')
