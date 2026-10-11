"""Versioned v2 delivery; preserve the original freeze/failures and all ET bytes."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
CENTRAL = HERE.parents[1]
CWP = Path('C:/Users/郑曾波/Projects/company-wiki')
old_path = CENTRAL / 'product-freeze.json'
old_hash = hashlib.sha256(old_path.read_bytes()).hexdigest()
if old_hash != 'e13ee23e64e0ec720edce6e4f5c6847f0dea2ead17a8d112d63874cd0e4cf28a':
    raise RuntimeError('Original freeze changed')
old = json.loads(old_path.read_text(encoding='utf-8'))
roots = {name: Path(value) for name, value in old['roots'].items()}
TREE = roots['ff']
changed = []
files = []
for entry in old['files']:
    data = (roots[entry['repository']] / entry['path']).read_bytes()
    current = {**entry, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
    if current['sha256'] != entry['sha256']:
        if entry['repository'] != 'ff':
            raise RuntimeError('ET freeze changed during FF repair')
        changed.append(entry['path'])
    files.append(current)
if set(changed) != {'scripts/transcript_tool_transport.py', 'tests/test_transcript_launch_contract.py'}:
    raise RuntimeError(f'Unexpected v2 product write set: {changed}')
head_after = {}
for name, root in roots.items():
    result = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True, encoding='utf-8', check=True)
    head_after[name] = result.stdout.strip()
if head_after != old['head_after']:
    raise RuntimeError('Git publishing happened during author repair')
for name, entries in old['old_goldens'].items():
    if name == 'unchanged':
        continue
    for item in entries:
        if hashlib.sha256((roots[name] / item['path']).read_bytes()).hexdigest() != item['sha256']:
            raise RuntimeError('Old golden drift')
protected = json.loads((CENTRAL / 'ff/baseline.json').read_text(encoding='utf-8'))['protected']
for item in protected:
    if hashlib.sha256((TREE / item['path']).read_bytes()).hexdigest() != item['sha256']:
        raise RuntimeError('Original FF protected input drift')
tool_manifest = CWP / 'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w06_parallel_verification_2026-10-11/evidence/root-ff-matrix-acceptance/fix/case-authority/manifest.json'
tools = json.loads(tool_manifest.read_text(encoding='utf-8'))['files']
for item in tools:
    if hashlib.sha256((TREE / item['path']).read_bytes()).hexdigest() != item['sha256']:
        raise RuntimeError('205 original tool files changed')
for name in ('red', 'concentrated', 'lint'):
    record = json.loads((HERE / f'{name}.json').read_text(encoding='utf-8'))
    scratch = Path(record['scratch'])
    if scratch.exists() or scratch.resolve().parent != (CWP / '.tmp').resolve():
        raise RuntimeError('Owned mu scratch not restored')
git = subprocess.run(['git', '-C', str(TREE), 'diff', '--check'], capture_output=True, text=True, encoding='utf-8', check=True)
(HERE / 'diff-check.log').write_text(git.stdout + git.stderr, encoding='utf-8')
patch = subprocess.run(['git', '-C', str(TREE), 'diff', '--', 'scripts/transcript_tool_transport.py', 'scripts/et_v2_contract.py', 'tests/test_transcript_launch_contract.py', 'tests/test_transcript_companion_transport.py', 'tests/test_et_s0b_contract.py'], capture_output=True, text=True, encoding='utf-8', check=True)
(HERE / 'tracked-product-v2.patch').write_text(patch.stdout, encoding='utf-8')
freeze = {
    **old,
    'frozen_at': datetime.now(timezone.utc).isoformat(),
    'delivery_version': 2,
    'verdict': 'AUTHOR_COMPLETE_PENDING_INDEPENDENT_REREVIEW',
    'head_after': head_after,
    'files': files,
    'supersedes': {'path': str(old_path), 'sha256': old_hash, 'preserved': True},
    'ff_malformed_usage_repair': {'changed_files': changed, 'business_red': '3 FAIL / 0.37s',
                                  'concentrated': '137 PASS / 4 SKIP / 2.46s',
                                  'error_projection': 'one validated stderr snapshot for every post-receipt failure',
                                  'usage_snapshot_parsed_once': True, 'et_product_unchanged': True,
                                  'owned_scratch_restored': True},
    'final_responsibility_tests': {
        'et': old['final_responsibility_tests']['et'],
        'ff': {'passed': 137, 'skipped': 4, 'seconds': 2.46, 'record': 'ff/malformed-usage-repair/concentrated.json'},
    },
    'next_step': 'Independent reviewer receives v2 freeze and concentrates on original cutoff probes, including the three malformed usage failures; ROOT owns matrix timing and normal publication',
}
target = CENTRAL / 'product-freeze-v2.json'
if target.exists():
    raise RuntimeError('Refusing to overwrite v2 delivery')
target.write_text(json.dumps(freeze, ensure_ascii=False, indent=2), encoding='utf-8')
freeze_hash = hashlib.sha256(target.read_bytes()).hexdigest()
PLAN = TREE / '.planning/w06-cutoff-result'
plan = (PLAN / 'task_plan.md').read_text(encoding='utf-8')
plan = plan.replace('D complete — final author FROZEN STOP; ROOT responsibility B green, real41 acceptance pending.', 'E complete — v2 malformed-usage common error projection FROZEN STOP; independent concentrated rereview pending.')
plan = plan.replace('ROOT runs unchanged original41 FF→ET→CWP offline matrix and owns publication; author STOP.', 'Independent reviewer concentrates on original cutoff probes using central product-freeze-v2.json; ROOT owns matrix timing and publication. ET/v1 freeze stay unchanged; author STOP.')
plan = plan.replace('## Final reception facts', '## Historical v1 reception facts (superseded by E)')
(PLAN / 'task_plan.md').write_text(plan, encoding='utf-8', newline='\n')
with (PLAN / 'progress.md').open('a', encoding='utf-8') as stream:
    stream.write(f'\nE最终集中节点：**137PASS4SKIP/2.46s**，3RED同一断言转绿；Ruff/diff绿，三个mu owned scratch恢复。旧freeze/独审失败/134PASS等历史记录不覆盖。FF本轮仅transport+launch测试变化；ET3 SHA完全不变。205tools/354protected/30oldgoldens不变；0网络/keys/config/raw/LLM，未commit/install。新中央product-freeze-v2.json SHA {freeze_hash}。\nNext Step：非作者用v2 freeze仅集中复验原cutoff probes；ROOT负责182.86s矩阵host时间调查，原CaseSpec/180s预算与期待不改，本作者STOP。\n')
with (PLAN / 'findings.md').open('a', encoding='utf-8') as stream:
    stream.write('\nE修复不是给三种坏payload单独补usage字段：_et_result共享局部unavailable(reason,calls,retryable)，仅一次解析合格stderr。泄密/JSON解码/非dict/receipt绑定/具名provider失败/nonzeroexit均同一投影，未知或污染receipt仍未知；未触达receipt的transport异常不伪造用量。不因正常失败重设消耗，不追加身份或许可。\n')
HANDOFF = TREE / 'docs/handoffs/w06-cutoff-result'
handoff = f'''# W06 FF cutoff v2 — malformed stdout 与实际用量共用修复

状态：AUTHOR_COMPLETE_PENDING_INDEPENDENT_REREVIEW；作者STOP。旧handoff/v1 freeze不覆盖。
独审3FAIL是完整stderr usage1次987bytes被JSONdecode/non-dict错误分支清空。已先正规3RED（0.37s），再共用实现，集中137PASS4SKIP（2.46s），Ruff/diff绿。SKIP仍旧四项显式跨仓tool/checkout未给，非PASS；ET不重复跑且3产品SHA不变。
产品只transport，测试只launch contract；仍位于原five-file写集。所有post-receipt失败共用一次已验snapshot，真实unknown不伪造complete，无新身份复验/门禁/重试/import。生产配置/key/raw/Git发布零写。
统一中央product-freeze-v2.json SHA {freeze_hash}，8 files +两roots/head，ET3不变，FF5新版本。205工具/354保护文件/ET12+FF18旧goldens全未变；旧v1 e13ee23..及独审失败证据保留，三个mu scratch恢复。
证据：company-wiki/.planning/w06-cross-period-acquisition/cutoff-implementation/ff/malformed-usage-repair/。
Next Step：ROOT将v2 freeze交非作者，仅集中复验原cutoff probes；ROOT调查当前主机41矩阵182.86s的问题，不改CaseSpec/timeout/期待洗绿。本作者不commit/merge/push/install，STOP。
'''
(HANDOFF / 'handoff-v2.md').write_text(handoff, encoding='utf-8', newline='\n')
report = {'schema_version': 'root-w06-ff-malformed-usage-repair/1', 'verdict': freeze['verdict'],
          'root': str(TREE), 'changed_files': changed, 'red': {'failed': 3, 'seconds': 0.37},
          'concentrated': {'passed': 137, 'skipped': 4, 'seconds': 2.46},
          'lint_diff': 'PASS', 'et_products_unchanged': True, 'old_freeze_preserved': True,
          'tools_unchanged': len(tools), 'protected_unchanged': len(protected),
          'new_freeze': str(target), 'new_freeze_sha256': freeze_hash,
          'resources': {'real_network_keys_config_raw_llm': 0, 'scratch_restored': 3, 'git_publish': False},
          'next_step': freeze['next_step'], 'stop': True}
(HERE / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
(HERE / 'report.md').write_text(handoff, encoding='utf-8', newline='\n')
(HANDOFF / 'handoff-v2.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
manifest_files = []
for path in sorted(HERE.rglob('*')):
    if path.is_file() and path.name != 'manifest.json':
        payload = path.read_bytes()
        manifest_files.append({'path': str(path.relative_to(HERE)), 'sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload)})
for path in (target, *sorted(PLAN.glob('*.md')), HANDOFF / 'handoff-v2.md', HANDOFF / 'handoff-v2.json'):
    payload = path.read_bytes()
    manifest_files.append({'path': str(path), 'sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload)})
manifest_path = HERE / 'manifest.json'
manifest_path.write_text(json.dumps({'schema_version': 'root-w06-ff-malformed-usage-manifest/1', 'files': manifest_files, 'verdict': freeze['verdict'], 'et_unchanged': True, 'old_freeze_preserved': True, 'scratch_restored': True}, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'freeze_v2_sha256': freeze_hash, 'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                  'ff_changed': changed, 'et_unchanged': True, 'old_freeze_preserved': True}, ensure_ascii=False))
