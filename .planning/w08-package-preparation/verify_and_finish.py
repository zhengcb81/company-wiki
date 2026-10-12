"""One preparation check, no product tests and no gate on each small edit."""
import hashlib
import json
from pathlib import Path
import subprocess

PLAN = Path(__file__).resolve().parent
CWP = PLAN.parents[1]
MOTHER = CWP/'docs/plans/cross-market-rf-e2e-2026-10-08'
TOTAL = MOTHER/'phase6/w08_parallel_completion_2026-10-12'
dispatch_path = TOTAL/'dispatch.json'
dispatch = json.loads(dispatch_path.read_text(encoding='utf-8'))
inventory = json.loads((PLAN/'inventory.json').read_text(encoding='utf-8'))
def sha(path):
    assert not any(x in path.name.lower() for x in ['api_key','secret','credential'])
    return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    previous=path.read_bytes() if path.exists() else b''
    ending='\r\n' if previous.count(b'\r\n') and previous.count(b'\r\n')==previous.count(b'\n') else '\n'
    path.write_text(text,encoding='utf-8',newline=ending)
def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],encoding='utf-8').strip()

interface = {
 'schema':'w08-root-interfaces/1',
 'ownership':{'workers':'one lane branch/write set only; no main/install/paid calls',
              'ROOT':'shared PWF, native core remediation, version inputs, main/install/exact CI, real G2/G4/G5'},
 'handoff_schema':'w08-lane-handoff/1',
 'lanes':[
  {'lane_id':'W08-RF-COMBOS','input':'own pinned native code/helpers; original16 + independent COMBINATION_CASES',
   'entry':'python -B tools/model_generalization_matrix/run.py --owned-root ABS_NEW --out-root ABS_NEW --e2e',
   'report_schema':'model-generalization-matrix/1 (preserve existing compatibility)',
   'must_observe':['required_case_ids','per-case native request/result refs','expected derivation','actual native status',
                   'five group coverage/missing','actual CLI exit/schema','readonly fingerprints','cleanup'],
   'ROOT_consumer':'G4/G5 model boundary verification; close remaining coverage, not economic accuracy',
   'new_dependency_on_other_W08':False},
  {'lane_id':'W08-AUDIT-EVIDENCE','input':'explicit coverage JSON + existing execution/report/event artifacts, old modes compatible',
   'entry':'python -B skills/revenue-forecast-audit/scripts/review_protocol.py coverage --input INPUT --execution-root ABS --out-root ABS',
   'report_schema':'review-coverage/1 + additive evidence_reconciliation',
   'must_observe':['artifact_ref','locator','run/review_attempt/role when known','observed bytes/SHA',
                   'supplied hash comparison only if present','event/call/output binding','status/reasons/unchecked scope'],
   'status_values':['OBSERVED','UNAVAILABLE','UNVERIFIABLE','MISMATCH'],
   'quality_status':'not_evaluated',
   'ROOT_consumer':'four reviewer briefing/closing diagnostics; no new permit or automatic forecast blocking',
   'new_dependency_on_other_W08':False},
  {'lane_id':'W08-CWP-G2-REPLAY','input':'own pinned CWP + code-only RF8dc26710 snapshot + small synthetic documents/model fixture',
   'entry':'python -B tools/narrative_g2_replay/run.py --rf-project ABS_FIXED --owned-root ABS_NEW --out-root ABS_NEW',
   'report_schema':'narrative-g2-replay/1',
   'must_observe':['scope/code_binding','fixed typed CaseSpecs/actual executed IDs','real canonical/finite worker/read/RF entry',
                   'request/result/artifact refs','actual model POST and reuse counters','raw hash/locators',
                   'raw/derived bytes','cleanup/remaining','known W04 baseline failures'],
   'ROOT_consumer':'rerun same package on accepted W04; then separate real configured G2, no fixture semantic-quality claim',
   'new_dependency_on_other_W08':False}
 ]}
write(TOTAL/'INTERFACES.json',json.dumps(interface,ensure_ascii=False,indent=2)+'\n')
rows=[]
for lane in dispatch['lanes']:
    root=Path(lane['workdir'])
    own=root/'.planning'/lane['plan_id']
    assert git(root,'rev-parse','HEAD') == lane['base_head']
    assert git(root,'branch','--show-current') == lane['branch']
    assert sha(Path(lane['card'])) == lane['card_sha256'] == sha(own/'施工卡.md')
    assert sha(own/'INPUTS.json') == lane['input_manifest_sha256']
    inputs=json.loads((own/'INPUTS.json').read_text(encoding='utf-8'))
    for path,row in inputs['files'].items():
        assert sha(root/path)==row['sha256'],path
    for dep in inputs['dependencies'].values():
        for path,row in dep['files'].items():
            assert sha(Path(dep['root'])/path)==row['sha256'],path
    prepared_status=git(root,'status','--porcelain').splitlines()
    assert prepared_status and all(row.startswith('?? .planning/') for row in prepared_status),prepared_status
    write(own/'INTERFACES.json',json.dumps(next(x for x in interface['lanes'] if x['lane_id']==lane['lane_id']),ensure_ascii=False,indent=2)+'\n')
    write(own/'START_HERE.md',(own/'START_HERE.md').read_text(encoding='utf-8')+'\nROOT输入输出接口在本目录INTERFACES.json；同schema兼容性、未知范围和实际CLI行为是交付标准，不增加签收许可。\n')
    lane['prepared_bytes']=sum(p.stat().st_size for p in root.rglob('*') if p.is_file() and p.name!='.git')
    rows.append({'lane':lane['lane_id'],'head_matches':True,'card_matches':True,
                 'readonly_input_matches':True,'status_only_prepared_pwf':True,
                 'prepared_bytes':lane['prepared_bytes']})
for left in dispatch['lanes']:
    for right in dispatch['lanes']:
        if left is right:
            continue
        a,b=Path(left['workdir']).resolve(),Path(right['workdir']).resolve()
        assert not a.is_relative_to(b) and not b.is_relative_to(a)
        assert left['repo'] != right['repo']
assert not any(p.startswith(('src/','scripts/')) for p in dispatch['lanes'][2]['write_set'])
write(dispatch_path,json.dumps(dispatch,ensure_ascii=False,indent=2)+'\n')
receipt={'schema':'w08-preparation-check/1','rows':rows,'paths_and_repos_disjoint':True,
         'no_worker_started':True,'no_paid_calls':True,'mother_goal_not_resumed':True,
         'prepared_total_bytes':sum(x['prepared_bytes'] for x in rows)}
write(TOTAL/'preparation-check.json',json.dumps(receipt,indent=2)+'\n')
note='''
## W08 新三包 — 2026-10-12

用户要求新的排他施工包；ROOT已核真实Git/PWF并准备三个固定工区，全部READY_NOT_STARTED，无worker开工。
[总入口与三张施工卡](../w08_parallel_completion_2026-10-12/README.md)：RF补W07五组实际遗漏；Audit在已有coverage上补optional实读执行证据；CWP新tools做有限摘要→read→固定RF消费离线联调，不写ROOT的W04 src。各包不同repo/workdir、固定代码输入、独立PWF、接口/测试/交接合同，只有A/B/C大节点，不增加许可门。
ROOT保留W04核心修复/当前主线/安装及真实G2/G4/G5；CWP工具可先开发并交如实PARTIAL，修W04后ROOT重跑同CaseSpec。三个包不等待彼此，也不运行收费模型/provider。
'''
p=MOTHER/'phase6/w06_parallel_verification_2026-10-11/ROOT-reception-status.md'
text=p.read_text(encoding='utf-8')
# Correct superseded current wording; detailed historical evidence stays below.
text=text.replace('## W07 当前可分发的三包','## W07 已完成分发与接收（三包历史）')
text=text.replace('状态READY_NOT_STARTED，已有独立PWF/固定输入/交接合同，各包A/B/C大节点，无跨包依赖。','W07已交付并接收，RF组合覆盖仍PARTIAL；初始READY是准备历史。已有独立PWF/固定输入/交接接口。')
text=text.replace('当前不并生产修复主线。','此条为前次失败历史；W07验收后已正常并线FF64b4d29/ETd0ac42c6，详最新接收条目。')
write(p,text+note)
for name in ['task_plan.md','progress.md','findings.md']:
    p=MOTHER/name
    summary='\n## W08 独立包准备 — 2026-10-12\n\n[三个新包与实际目录](phase6/w08_parallel_completion_2026-10-12/README.md)已准备，可交三个harness现在独立启动；不同repo/目录/唯一写集，RF补已确认五组遗漏、Audit实读执行证据、CWP新联调工具不碰ROOT W04 core。原W07不重派。ROOT协调接收/主线/安装和真实G2/G4/G5；母目标当前暂停，本请求不自动恢复。0付费调用。\n'
    write(p,p.read_text(encoding='utf-8')+summary)
write(PLAN/'task_plan.md','''# W08 独立施工包准备（ROOT，2026-10-12）

A Git/PWF/实际接口调查 complete；B实际排他工区/固定输入/三独立卡/接口与PWF complete；C路径/基线/输入检查 complete，正常文档提交后交用户。母目标未恢复，没有worker开工。

## Next Step

交用户三张W08卡和对应工作目录。外部harness独立实施，ROOT接收后再做跨包接线/main/安装；W04与真实G2/G4/G5仍开放。CWP远端仍待W04已知18FAIL，不能以发卡为由绕过推送检查。

不重跑一次性prepare_packages.py/verify_and_finish.py；独立工作树已建。状态看母W08 dispatch.json。
''')
for name in ['findings.md','progress.md']:
    p=PLAN/name
    write(p,p.read_text(encoding='utf-8')+'\n2026-10-12三个实际工区、base/branch/card/readonly输入检查通过；总准备空间'+str(receipt['prepared_total_bytes'])+'B，没有全湖/旧规划复制。三包不同repo且目录互不嵌套；CWP只新tool/test，ROOT源写集排他。INTERFACES.json明确实际公开入口、输出与ROOT消费者；全部READY_NOT_STARTED，0收费。\n')
print(json.dumps(receipt))
