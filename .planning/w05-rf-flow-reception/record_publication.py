"""Record normal publication, exact-SHA CI and selective runtime installation."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT.parent/'revenue-forecast'
E = ROOT/'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w05_parallel_common_roots_2026-10-11/evidence/root-rf-flow-acceptance'
HEAD = '30ddae8ed2a457c418e63b182e7d8c9230fbf3ff'
ci = json.loads((E/'remote-ci.json').read_text(encoding='utf-8-sig'))
install = json.loads((E/'installation.json').read_text(encoding='utf-8'))
integration = json.loads((E/'local-main-integration.json').read_text(encoding='utf-8'))
assert ci['head_sha'] == HEAD and ci['status'] == 'completed' and ci['conclusion'] == 'success'
assert install['canonical_head'] == HEAD and install['selected_sha_match'] == 34
remote = subprocess.check_output(['git', 'ls-remote', 'origin', 'refs/heads/main'], cwd=MAIN, text=True).split()[0]
assert remote == HEAD == subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=MAIN, text=True).strip()
status = subprocess.check_output(['git', 'status', '--porcelain'], cwd=MAIN, text=True).strip()
assert status == integration['canonical_porcelain_before']
preserved = {name: hashlib.sha256((MAIN/name).read_bytes()).hexdigest()
             for name in integration['canonical_wip_sha_before']}
assert preserved == integration['canonical_wip_sha_before']
target = E/'publication.json'
assert not target.exists()
target.write_text(json.dumps({'schema': 'root-rf-publication/1', 'status': 'PASS_WITH_SCOPE',
    'main_head': HEAD, 'remote_main_head': remote, 'normal_push': True,
    'prepush': {'ruff': 'PASS', 'mypy_public_files': 11, 'pytest_passed': 390,
                'subtests_passed': 36, 'pytest_seconds': 33.97},
    'exact_sha_remote_ci': ci, 'selective_runtime_install': install,
    'canonical_wip_preserved': True, 'canonical_wip_sha_after': preserved,
    'canonical_porcelain_after': status, 'provider_calls': 0, 'llm_calls': 0,
    'cost_micro_usd': 0,
    'scope': 'Period/type/source ancestry math and native readers; not source truth or economic certification'},
    ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
prefix = '''## ROOT 当前结论 — W05-RF-FLOW 已并线、安装和发布 — 2026-10-11

A/B/C完成。正式RED与后续独审发现的4类期间/存量/价格关联缺陷均由共用数学责任层修复；最后31个非作者案例、原4P1共16实际入口检查通过，合法ARPU/周转率/费率/收益率保留。最终既有工程节点390PASS+36subtests、ruff/mypy11通过；正常push再次390+36通过33.97秒。

main与origin/main均30ddae8ed2a457c418e63b182e7d8c9230fbf3ff，远端quality CI38142227109 exactSHA成功。17运行文件×2物理安装副本定点更新，34SHA匹配；.claude为.agents同一junction。未选文件元数据保留，安装前未选漂移当前.agents=0/.codex=9，9项不在此次范围；配置/output/assurance WIP原样。原FAIL、冻结及所有历史节点保留，0provider/LLM/费用。

结论是数学与运行接口范围PASS_WITH_SCOPE，不认证真实来源事实或经济预测。发布/安装见母W05 evidence/root-rf-flow-acceptance/publication.json及installation.json；安装后小smoke另行记录，不增加常规门禁。Next Step：返回母W04/G2/G4/G5；这四项仍开放，整个PWF尚未完成。下面未验收状态均为历史。

'''
for name in ('task_plan.md', 'findings.md', 'progress.md'):
    path = ROOT/'.planning/w05-rf-flow-reception'/name
    path.write_text(prefix+path.read_text(encoding='utf-8'), encoding='utf-8')
print('RF selected PWF closed; exact remote/CI/install/WIP receipts recorded')
