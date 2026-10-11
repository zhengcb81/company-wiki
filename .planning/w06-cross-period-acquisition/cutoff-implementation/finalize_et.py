"""Freeze the authorized ET narrow delivery and its PWF without publishing."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
TREE = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/et-cutoff-root')
EVIDENCE = Path(__file__).resolve().parent / 'et'
PLAN = TREE / '.planning/w06-cutoff-result'
HANDOFF = TREE / 'docs/handoffs/w06-cutoff-result'
before = json.loads((EVIDENCE / 'before.json').read_text(encoding='utf-8'))
products = ('transcript_api.py', 'tests/test_transcript_api.py', 'tests/test_retrieval_cli_e2e.py')
goldens = [entry for entry in before['files'] if entry['path'].replace('\\', '/').startswith('tests/golden/')]
for entry in goldens:
    if hashlib.sha256((TREE / entry['path']).read_bytes()).hexdigest() != entry['sha256']:
        raise RuntimeError('Existing golden changed')
commands = {'head': ['rev-parse', 'HEAD'], 'status': ['status', '--short'], 'diff-stat': ['diff', '--stat'], 'diff-check': ['diff', '--check'], 'product': ['diff', '--', *products]}
git = {}
for name, arguments in commands.items():
    result = subprocess.run(['git', '-C', str(TREE), *arguments], capture_output=True, text=True, encoding='utf-8')
    (EVIDENCE / f'git-{name}.txt').write_text(result.stdout + result.stderr, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(f'Git read failed: {name}')
    git[name] = result.stdout.strip()
if git['head'] != before['base_head']:
    raise RuntimeError('Unauthorized ET commit')
freeze_files = []
for relative in products:
    payload = (TREE / relative).read_bytes()
    freeze_files.append({'repository': 'et', 'path': relative, 'sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload)})
freeze = {'schema_version': 'root-w06-et-cutoff-freeze/1', 'root': str(TREE), 'head_before': before['base_head'], 'head_after': git['head'], 'files': freeze_files, 'old_goldens': goldens, 'old_goldens_unchanged': True, 'concentrated_tests': '56 PASS / 40.37s', 'golden_check': '10 matched', 'lint': 'PASS', 'commit_merge_push_install': False}
(EVIDENCE / 'product-freeze.json').write_text(json.dumps(freeze, ensure_ascii=False, indent=2), encoding='utf-8')
plan = (PLAN / 'task_plan.md').read_text(encoding='utf-8')
plan = plan.replace('Next Step：A业务RED，封存后直接B，无小节点签收。', 'A业务RED、B共用实现/集中责任节点、C作者冻结均完成；仅ROOT原41矩阵/非作者验收/发布未执行。Next Step：ROOT使用中央统一product-freeze.json的ET/FF树，原CaseSpec/fixture/期待不变做一次41/180s回放，再正常发布；本作者STOP。')
(PLAN / 'task_plan.md').write_text(plan, encoding='utf-8', newline='\n')
with (PLAN / 'findings.md').open('a', encoding='utf-8') as stream:
    stream.write('\n最终实现把actual身份和期间证明留在原source层，仅新增两值诊断。_listing_candidate_selection返回eligible+真实日期排除标记，exact fetch/discover共享；batch _listing_candidates保留dict接口。FMP多候选在原歧义判断后才处理唯一日期，不放宽原判断；call_date不替publication。真实worker诊断和请求/响应512等用量由既有serializer透明保留，不增body字段。\n')
with (PLAN / 'progress.md').open('a', encoding='utf-8') as stream:
    stream.write('\nB集中节点：全部API/CLI+3受影响batch元数据控制 **56PASS/40.37s**；两个provider真实worker证明error_code、usage1次/实际字节、未载translator、worker临时根清空。旧**10goldens matched**，相关Ruff与git diff --check通过；12golden目录文件SHA保持。合成HOME/TEMP、假key、socket拒绝；0真实HTTP/LLM/费用/keys读取。4个ec-* owned短scratch均恢复不存在。\nC作者冻结：central et/product-freeze.json包含3个产品/测试SHA，head前后c91f5f54不变。ROOT要求的ET+FF统一freeze由总作者生成；本作者不重复41、不commit/merge/push/install，不改canonical ET杂物/原件/config或CWP12。\nNext Step：ROOT原41大节点、一次独立验收并正常发布；本线作者STOP。\n')
HANDOFF.mkdir(parents=True, exist_ok=True)
handoff = '''# W06 ET cutoff 共用修复交付（作者冻结）

TREE：C:/Users/郑曾波/Projects/_harness_worktrees/w06/et-cutoff-root；HEAD前后c91f5f54bc2a24e7b5d6e648dba3f9d578f5fa52不变。未commit/merge/push/install。

## 行为与接口

只有 transcript_api.py 和两个责任测试改动。FMP已验证唯一晚call → not_found/candidate_count0/error_code=call_after_as_of；Motley已验证目标期晚published → publication_after_as_of。普通空列表、别期未来候选不冒cutoff。消息/结果版本和10个goldens不变；FMP publication_date=null/as_of_cutoff_verified=false不变。无公司/年份/fixture特判、无额外HTTP、正文/翻译/许可或身份库。

## TDD和证据

正规RED **5FAIL6PASS**，每项失败都是API/CLI真实not_found缺error_code，无import错误。集中 **56PASS40.37s**，10goldens matched，Ruff/diff clean；新worker测试两个provider、真实supervisor/worker/API，只有HTTP seam为fake，来源诊断和实际usage均到wire，无translator，scratch恢复。

中央证据：company-wiki/.planning/w06-cross-period-acquisition/cutoff-implementation/et/；before.json、red.*、green.*、golden.*、lint.*、git-*、product-freeze.json。3产品SHA与12个旧golden目录文件保存。资源：合成HOME/TEMP/fake key/socket deny，0真实网络/LLM/费用，0真实keys/config/raw读取。

## ROOT Next Step

使用父目录统一 product-freeze.json 的ET+FF树与ROOT已验CWP树，原41矩阵/CaseSpec/期待不变在180s内只回放一次；之后独立验收、正常并线发布。工具205冻结、CWP12、其它工作树零写。本作者冻结STOP；不把56unit/integration PASS说成41完整产品认证或真实FMP权益。
'''
(HANDOFF / 'handoff.md').write_text(handoff, encoding='utf-8', newline='\n')
(HANDOFF / 'handoff.json').write_text(json.dumps({'schema_version': 'w06-cutoff-handoff/1', 'verdict': 'AUTHOR_COMPLETE_PENDING_ROOT_MATRIX', 'root': str(TREE), 'base_head': before['base_head'], 'files': freeze_files, 'tests': {'red': {'failed': 5, 'passed': 6}, 'concentrated': {'passed': 56, 'seconds': 40.37}, 'goldens': 10, 'lint': 'PASS'}, 'next_step': 'ROOT original41 matrix, independent acceptance and publishing', 'stop': True}, ensure_ascii=False, indent=2), encoding='utf-8')
manifest_files = []
for path in sorted(EVIDENCE.rglob('*')):
    if path.is_file() and path.name != 'manifest.json':
        data = path.read_bytes()
        manifest_files.append({'path': str(path.relative_to(EVIDENCE)), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
for path in (*sorted(PLAN.glob('*.md')), *sorted(HANDOFF.glob('*'))):
    if path.is_file():
        data = path.read_bytes()
        manifest_files.append({'path': str(path), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
(EVIDENCE / 'manifest.json').write_text(json.dumps({'schema_version': 'root-w06-et-cutoff-manifest/1', 'files': manifest_files, 'old_goldens_unchanged': True, 'scratch_restored_absent': True, 'product_files': 3, 'verdict': 'AUTHOR_COMPLETE_PENDING_ROOT_MATRIX'}, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'product_files': 3, 'old_golden_files_unchanged': len(goldens), 'head': git['head'], 'handoff': str(HANDOFF)}, ensure_ascii=False))
