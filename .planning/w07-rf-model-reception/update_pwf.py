import json
from pathlib import Path

PLAN = Path(__file__).resolve().parent
REPO = PLAN.parents[1]
MOTHER = REPO/'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w07_parallel_quality_2026-10-11'
publication = json.loads((PLAN/'publication.json').read_text(encoding='utf-8'))
assert publication['ci'][0]['conclusion'] == 'success'

def replace(path, before, after):
    text = path.read_text(encoding='utf-8')
    assert before in text, (str(path), before)
    path.write_text(text.replace(before, after, 1), encoding='utf-8')

replace(PLAN/'task_plan.md', '| C | Normal commit, merge to RF main, push and check exact-head CI; update mother PWF | in_progress |', '| C | Normal commit, merge to RF main, push and check exact-head CI; update mother PWF | complete |')
replace(PLAN/'task_plan.md', 'Finish normal push with existing explicit sibling-root configuration, fast-forward canonical main preserving WIP, check exact-head CI and update mother PWF. Full card boundary coverage remains explicitly OPEN in ROOT-rf-remaining-coverage.md.', 'Reception complete with PARTIAL card coverage. RF main/origin/main8dc26710 and exact CI38168556914 successful. Return to W04→G2; close the five explicit engineering coverage groups in ROOT-rf-remaining-coverage.md before claiming the full card complete.')
for name in ['progress.md','findings.md']:
    p = PLAN/name
    p.write_text(p.read_text(encoding='utf-8')+'\nNormal push and local main fast-forward completed:8dc2671040f4330d3b54d1bea1d17246130f9c2a; author commits included.390PASS+36subtests/32.07s, exact quality CI38168556914 SUCCESS.150 WIP file SHAs unchanged; engineering-only no skill sync. Full card coverage remains PARTIAL.\n', encoding='utf-8')

dispatch_path = MOTHER/'dispatch.json'
dispatch = json.loads(dispatch_path.read_text(encoding='utf-8'))
for lane in dispatch['lanes']:
    if lane['lane'] == 'W07-RF-MODEL':
        lane.update(status='ACCEPTED_TOOL_PARTIAL_COVERAGE_MERGED_PUBLISHED', accepted_main_head=publication['main_head'], exact_ci=38168556914, root_evidence='.planning/w07-rf-model-reception/publication.json', remaining_plan='ROOT-rf-remaining-coverage.md')
dispatch_path.write_text(json.dumps(dispatch,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')

replace(MOTHER/'task_plan.md', 'FF-PERF/RF-MODEL当前未接收，开工状态不据旧准备记录推定。', 'RF-MODEL工具已由ROOT共因修复后并线发布，整卡组合覆盖仍PARTIAL；FF-PERF当前未接收，开工状态不据旧准备记录推定。')
replace(MOTHER/'task_plan.md', 'FF/RF等待各自交接，正常验收并线。Audit无remote/CI。', 'RF工具main/origin/main8dc26710、精确CI38168556914成功；36集中/16原生向量及三CLI绿，5组组合缺口保留详细后续计划。FF仍待交接。Audit无remote/CI。')
replace(MOTHER/'task_plan.md', 'ROOT继续W04共因修复与G2；另外两包交付后按独立范围接收。', 'ROOT继续W04共因修复→G2；FF交付后接收。RF剩余覆盖按[详细计划](ROOT-rf-remaining-coverage.md)在G4/G5引用充分组合证据前完成，不误报整卡完成。')
replace(MOTHER/'README.md', '另两包仍独立，当前未接收；不要把准备状态当作实时开工状态。', 'RF-MODEL工具已正常并线发布8dc26710/CI38168556914成功；组合覆盖PARTIAL，见[ROOT剩余覆盖计划](ROOT-rf-remaining-coverage.md)。FF仍未ROOT接收；不要把准备状态当作实时开工状态。')
entry = '''
## W07-RF-MODEL ROOT 接收结果

工程工具接收、整卡部分覆盖：作者d282c9d/72d0ced保留，ROOT22RED/1PASS暴露误报共因；系统修复异常分类、per-case真实request/result、未知/空比较、完整清单、CLI/readonly/清理状态和原目录恢复。原assertions不变，最终36PASS/4.19s，原16向量11PASS/5REJECT_OK、三实际CLI0/2/0，1.394767s。正常main/origin/main8dc26710，推送前390PASS＋36subtests/32.07s，精确CI38168556914成功；150WIP文件SHA保持，不安装工程工具。

仍缺CNY/HKD、并购控制/跨FY、联合量价、累计/净额/防双计、future actual/WAPE五组覆盖，不能称整卡COMPLETE，详[后续](ROOT-rf-remaining-coverage.md)。ROOT留证只存单份压缩native JSON与摘要，当前约330KB。0provider/LLM/费用；来源真值/买方经济判断仍未认证。CWP母PWF提交可在本地保存，远端发布仍待W04旧18失败修复，不以RF CI代替CWP发布。
'''
for name in ['findings.md','progress.md']:
    p = MOTHER/name
    p.write_text(p.read_text(encoding='utf-8')+entry,encoding='utf-8')
current = MOTHER.parent/'w06_parallel_verification_2026-10-11/ROOT-reception-status.md'
current.write_text(current.read_text(encoding='utf-8')+entry, encoding='utf-8')
print('All ROOT W07/current reception PWF updated; RF exact CI success, wider coverage explicitly open.')
