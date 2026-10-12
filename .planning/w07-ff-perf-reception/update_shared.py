"""ROOT-owned current PWF only; historical frozen worker reports stay intact."""
import json
from pathlib import Path
import subprocess

PLAN = Path(__file__).resolve().parent
CWP = PLAN.parents[1]
MOTHER = CWP/'docs/plans/cross-market-rf-e2e-2026-10-08'
W07 = MOTHER/'phase6/w07_parallel_quality_2026-10-11'
FF_HEAD = '64b4d294a1e61e595e330b4a7d4075c289f9fdc3'
ET_HEAD = 'd0ac42c60dcca992db78860b8469cfed3dd527e5'
summary = json.loads((PLAN/'acceptance.json').read_text(encoding='utf-8'))
ci = json.loads((PLAN/'ci.json').read_text(encoding='utf-8'))
assert ci and ci[0]['head_sha'] == FF_HEAD
installed = json.loads((PLAN/'installation.json').read_text(encoding='utf-8'))
assert installed['unselected_metadata_preserved']
publication = {'schema':'root-w07-ff-publication/1','ff_main':FF_HEAD,'et_main':ET_HEAD,
    'ff_ci':ci[0],'et_ci':'no workflow configured in accepted tree',
    'normal_push':True,'hooks_bypassed':False,
    'pre_push':{'passed':708,'skipped':7,'subtests':78,'seconds':78.85,
        'isolated_default_config_doctor':'no RF sibling; skipped',
        'actual_canonical_three_repo_config_doctor':'OK: three-repo configs healthy'},
    'focused_tests':225,'et_tests':53,'full_original_matrix':summary['counts'],
    'seconds':summary['scope']['batch_elapsed_seconds'],
    'installed_physical_copies':2,'installed_runtime_files_per_copy':2,
    'installed_synthetic_checks_per_copy':5,'canonical_wip_metadata_preserved':True,
    'cwp_remote_publication':'blocked by existing W04 18 failures; not retried or bypassed',
    'mother_goal_tool_status':'paused','paid_calls':0}
for name,head,root in [('ff',FF_HEAD,Path('C:/Users/郑曾波/Projects/filing-fetch')),
                       ('et',ET_HEAD,Path('C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts'))]:
    assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()==head
    assert subprocess.check_output(['git','-C',str(root),'ls-remote','origin','refs/heads/main'],text=True).split()[0]==head
(PLAN/'publication.json').write_text(json.dumps(publication,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
ci_state = '成功' if ci[0]['conclusion']=='success' else ci[0]['status']
current = ('W07-FF-PERF已完成ROOT接收：原41场景全PASS/99.9624s、零oracle findings、26最终原文证明，'
    '原30/180秒上限与case/期望不减；225集中绿、ET53绿。FF main/origin/main64b4d29、ET main/origin/main d0ac42c6已正常发布，'
    f'FF精确CI38170433893状态{ci_state}；ET没有配置workflow。两运行文件×两物理FF技能副本同步、各5实际安装后边界绿；'
    '三仓配置体检绿，非选文件元数据和原WIP保持。Audit已接收安装；RF工具已发布8dc26710/精确CI成功，'
    '整卡仍缺五组组合覆盖。W04已本地并线7a0b702a但正常push18FAIL，远端仍5c07f47c；'
    'ROOT后续W04共因→G2→G4→G5。目标工具当前paused，本次仅完成用户授权的接收，0付费调用。')
details = ('\n## 2026-10-11 W07-FF-PERF ROOT 最终接收\n\n'+current+
    '\n\n共因修复：Windows长路径重复编译/重复准备与proof饥饿由作者统一解决；ROOT补独占attempt缓存、proof失败不可覆盖/'
    '完整worker证明、子进程reap、异常清理和seed完整序列。ROOT自己的逻辑别名数过约束有反例修复；'
    '首轮28/13记录保持，最终原41重跑全绿。两轮原始证据仅490060-byte ZIP，隔离重放oracle零发现、自动恢复。'
    '长矩阵手动大节点；轻量测试走同一正常push/CI，未新增人工门禁。'
    '\n\n证据入口：company-wiki/.planning/w07-ff-perf-reception/publication.json、acceptance.json、offline-evidence.zip、replay_evidence.py。'
    '工程绿不认证真实供应商可达、来源真值或研究质量。预算母账保持413778tokens/334463µUSD+2764FXhold，累计$20/200万tokens。\n')
for name in ['task_plan.md','progress.md','findings.md']:
    p = MOTHER/name
    lines = p.read_text(encoding='utf-8').splitlines()
    assert lines[0].startswith('## ROOT 当前入口')
    lines[3] = current
    lines[4] = 'W07：[三包当前接收状态](phase6/w07_parallel_quality_2026-10-11/README.md)。仅A/B/C大节点；历史READY记录保留为历史。'
    p.write_text('\n'.join(lines)+'\n'+details,encoding='utf-8',newline='\n')
for name in ['progress.md','findings.md']:
    p = W07/name
    p.write_text(p.read_text(encoding='utf-8')+details,encoding='utf-8',newline='\n')
p = W07/'task_plan.md'
p.write_text('# W07 ROOT 分包总计划\n\n## 当前状态\n\n'+current+
    '\n\n## 大节点\n\nA独立工区/固定输入完成；B三个包均已ROOT接收。Audit和FF范围完成、RF工具接收但组合覆盖PARTIAL。'
    'C Audit main/安装完成，FF及ET主线发布/安装完成，RF主线发布/CI成功；CWP共享PWF远端等待W04修复。'
    '\n\n## Next Step\n\n母目标恢复后先修W04已证实共因并正常发布，再G2真实摘要/RF消费→G4原三公司四独审→G5新三及指定循环。'
    'RF五组缺口按[详细计划](ROOT-rf-remaining-coverage.md)在消费组合结论前补完。'
    '\n\n不增加授权JSON、private/public、逐材料许可或小节点签收；原件、实际资源上限和责任层字节/期间校验保留。\n',encoding='utf-8',newline='\n')
p = W07/'README.md'
text = p.read_text(encoding='utf-8')
text = text.replace('三包工作目录已经准备，均可现在同时开工。','三包均已交付并由ROOT接收；RF整卡组合覆盖仍PARTIAL。原工作目录保留，不重复派施工。')
text = text.replace('FF仍未ROOT接收；不要把准备状态当作实时开工状态。',current)
p.write_text(text,encoding='utf-8',newline='\n')
p = W07/'dispatch.json'
d = json.loads(p.read_text(encoding='utf-8'))
d['state']='ACCEPTED_WITH_RF_COVERAGE_REMAINING'
ff = next(x for x in d['lanes'] if x['lane']=='W07-FF-PERF')
ff.update(status='ACCEPTED_MERGED_PUBLISHED_INSTALLED',accepted_main_head=FF_HEAD,
          et_main_head=ET_HEAD,exact_ci=ci[0]['id'],ci_status=ci[0]['status'],
          ci_conclusion=ci[0]['conclusion'],root_evidence='.planning/w07-ff-perf-reception/publication.json')
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
p = MOTHER/'phase6/w06_parallel_verification_2026-10-11/ROOT-reception-status.md'
text = p.read_text(encoding='utf-8')
rows = text.splitlines()
for index,line in enumerate(rows):
    if line.startswith('| W06-FF-MATRIX |'):
        rows[index] = '| W06-FF-MATRIX / W07-FF-PERF | 原41全PASS/99.9624秒；26fresh原文证明、零oracle、目录恢复。FF64b4d29/ETd0ac42c6本地与远端相同；FF精确CI38170433893 '+ci_state+'。225集中、ET53、正常push708＋78subtests；两文件×两安装/各5边界及三仓配置体检绿 | 接收、并线、同步完成；真实供应商/经济质量仍留G4/G5 |'
text = '\n'.join(rows)+'\n'
text = text.replace('目标工具当前active。','目标工具当前paused；用户授权的独立接收正常推进。')
text = text.replace('另外两包尚未ROOT接收，当前开工状态不推定。','RF与FF最新接收结果见本文后续条目；此句为历史记录。')
text = text.replace('详[后续](ROOT-rf-remaining-coverage.md)','详[后续](../w07_parallel_quality_2026-10-11/ROOT-rf-remaining-coverage.md)')
p.write_text(text+details,encoding='utf-8',newline='\n')
for relative in ['.planning/w06-ff-matrix-reception','.planning/w06-cross-period-acquisition']:
    root = CWP/relative
    for name in ['progress.md','findings.md']:
        p = root/name
        p.write_text(p.read_text(encoding='utf-8')+details,encoding='utf-8',newline='\n')
    p = root/'task_plan.md'
    text = p.read_text(encoding='utf-8')
    # Only final release-phase checkboxes; historical failure evidence untouched.
    if 'ff-matrix-reception' in relative:
        text = text.replace('- [ ] C：','- [x] C：')
    else:
        begin = text.index('### C：')
        end = text.index('## 恢复',begin)
        text = text[:begin]+text[begin:end].replace('- [ ]','- [x]')+text[end:]
    lines = text.splitlines()
    for index,line in enumerate(lines):
        if line.startswith('Next Step：'):
            lines[index] = 'Next Step：本包接收/FF及ET并线发布/安装完成；回母W04共因修复→G2→G4→G5。'+current
    p.write_text('\n'.join(lines)+'\n'+details,encoding='utf-8',newline='\n')
(PLAN/'task_plan.md').write_text((PLAN/'task_plan.md').read_text(encoding='utf-8').replace('| in_progress |','| complete |').replace(
    'Complete normal FF/ET publication and narrow two-file FF installation synchronization; update shared PWF. CWP publication remains behind W04\'s existing 18 failures.',
    'Bounded reception complete; preserve remote CI status in publication.json. Mother work remains W04→G2→G4→G5; CWP records commit locally without bypassing known W04 push failures.'),encoding='utf-8',newline='\n')
for name in ['progress.md','findings.md']:
    p = PLAN/name
    p.write_text(p.read_text(encoding='utf-8')+details,encoding='utf-8',newline='\n')
print(json.dumps({'ff':FF_HEAD,'et':ET_HEAD,'ci':ci[0]['status'],'conclusion':ci[0]['conclusion']}))
