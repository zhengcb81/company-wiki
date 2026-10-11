"""Update current PWF pointers and verify prepared W07 packet boundaries."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
CENTRAL = ROOT / 'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w07_parallel_quality_2026-10-11'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
dispatch = json.loads((HERE / 'dispatch-record.json').read_text(encoding='utf-8'))
assert not (HERE / 'verification.json').exists(), 'Preserve prior verification'
old = 'OCR/RF/Audit/Portability已并线发布；FF工具main4167dac4/CWP来源master8bd23344精确CI均成功。W04质量带375工程绿、固定六原件87.4409秒PASS，四项主体绑定业务事实恢复，待非作者和并线。ET/FF cutoff工程绿；独审发现坏JSON抹去实测用量的共因，正在修。原41历史40/1保留，新attempt因180秒批次截止为2PASS/31PARTIAL/8NOT_RUN，未认证，避免重型并跑后再按原限额验收。G2/G4/G5仍开放；目标active，无新增人工许可，原件/配置/WIP保持。'
new = 'OCR/RF/Audit/Portability已并线发布，精确CI成功。W04质量带375工程绿、同六原件87.4409秒PASS，非作者17/17及四事实见证通过；18文件集成清单READY，ROOT待正常并线。ET/FF坏stdout覆盖已测用量共因已修并提交分支ETd0ac42c6/FF2d380a05，集中独审7PASS，尚未发布；原41最新1PASS/27PARTIAL/13NOT_RUN、184.54秒触及180秒截止，未认证。W07三包已实际准备（READY_NOT_STARTED）：FF固定41提速、RF组合测试、Audit买方风险诊断，ROOT保留W04/G2/G4/G5与主线安装；G2/G4/G5仍开放，目标active，0付费调用，无新增人工许可。'
bases = ['docs/plans/narrative-evidence-pilot-2026-09-26', 'docs/plans/cross-market-rf-e2e-2026-10-08',
         'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/main_auto_official_json',
         'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w06_parallel_verification_2026-10-11']
updated = []
for base in bases:
    for name in ('task_plan.md', 'findings.md', 'progress.md'):
        p = ROOT / base / name
        raw = p.read_bytes()
        old_count = raw.count(old.encode())
        new_count = raw.count(new.encode())
        if base == bases[2]:
            assert old_count <= 1 and new_count <= 1, str(p)
        else:
            assert old_count + new_count == 1, str(p)
        raw = raw.replace(old.encode(), new.encode(), 1)
        rel = {bases[0]: '../cross-market-rf-e2e-2026-10-08/phase6/w07_parallel_quality_2026-10-11/README.md',
               bases[1]: 'phase6/w07_parallel_quality_2026-10-11/README.md',
               bases[2]: '../w07_parallel_quality_2026-10-11/README.md',
               bases[3]: '../w07_parallel_quality_2026-10-11/README.md'}[base]
        addition = f'\nW07：[三包总览及实际工作目录]({rel})。三包可同时启动；各自只有A/B/C三个测试大节点，不增加小节点门禁。\n'
        if base == bases[2] and not raw.startswith('## ROOT 当前入口 — 2026-10-11 / W07'.encode()):
            raw = ('## ROOT 当前入口 — 2026-10-11 / W07 三包已准备\n\n'+new+'\n'+addition+'\n以下较早入口是历史。\n\n').encode() + raw
        elif addition.encode() not in raw:
            needle = new.encode()
            raw = raw.replace(needle, needle + addition.encode(), 1)
        p.write_bytes(raw)
        updated.append(str(p.relative_to(ROOT)))

status = ROOT / bases[3] / 'ROOT-reception-status.md'
s = status.read_text(encoding='utf-8')
s = s.replace('| W06-FF-MATRIX |'+s.split('| W06-FF-MATRIX |', 1)[1].split('\n', 1)[0],
    '| W06-FF-MATRIX | CaseSpec/RunSpec195PASS、非作者28/28；FFmain4167dac4/CWP来源master8bd23344已发布且精确CI绿。cutoff/usage分支修复ETd0ac42c6/FF2d380a05，集中独审7PASS；旧39PASS/3FAIL保留。最新原41为1PASS/27PARTIAL/13NOT_RUN、184.54秒，180秒到期后fresh proofs未完成 | W07-FF-PERF修准备/进程/proof共同超时，原41/30s/180s/期望不减；ROOT接收后并线ET/FF生产修复，当前未认证全链 |')
s = s.replace('| W04业务信息召回 |'+s.split('| W04业务信息召回 |', 1)[1].split('\n', 1)[0],
    '| W04业务信息召回 | 质量带375PASS；同六原件87.4409秒PASS，四主体事实见证、legacy指纹/raw/cap/完整组保持；最终独审17/17＋4/4见证通过 | 18文件集成清单READY（.planning/w04-selector-integration），ROOT下一步正常并线；摘要/研究尚未验收 |')
start = s.index('2. 独立ET/FF工区')
end = s.index('4. G2真实有界摘要', start)
s = s[:start]+'''2. ET/FF单一错误投影已修：集中独审7PASS，正常分支commit ETd0ac42c6/FF2d380a05。旧失败保留；原41第二完整attempt仍因180秒截止1/27/13，W07-FF-PERF负责运行共因，当前不并生产修复主线。
3. W04旧365工程绿与六原件3FAIL保留；新375工程/同六原件87.4409秒/非作者17＋4均绿。ROOT只集成已冻结18文件，不回退新CI/OCR测试，不带G2配置，之后执行一次集中集成测试与正常发布。
'''+s[end:]
s += '''\n## W07 当前可分发的三包\n\n[总览、三个独立卡与实际目录](../w07_parallel_quality_2026-10-11/README.md)：W07-FF-PERF（优先）、W07-RF-MODEL、W07-AUDIT-ANALYST。状态READY_NOT_STARTED，已有独立PWF/固定输入/交接合同，各包A/B/C大节点，无跨包依赖。ROOT并行推进W04→G2，接收后将新工具用于G4/G5，不把工程报告当真值/经济判断。\n'''
status.write_text(s, encoding='utf-8')
updated.append(str(status.relative_to(ROOT)))
diag = ROOT / '.planning/w06-cross-period-acquisition/matrix-deadline-diagnosis.md'
with diag.open('a', encoding='utf-8') as f:
    f.write('\n## 第二次固定原41：2026-10-11\n\nroot-matrix-final-usage-v2 为1PASS/27PARTIAL/13NOT_RUN、184.54秒；仍是180秒deadline导致尾case及最终proof缺失，不签收。此前stdout/usage独审7PASS且已正常分支提交；旧失败不改。W07-FF-PERF明确保持41/30s/180s及权威期望，负责阶段实测与准备/启动共因，避免第三次盲目重复原失败。\n')
updated.append(str(diag.relative_to(ROOT)))

checks = []
roots = []
for lane in dispatch['lanes']:
    work = Path(lane['workdir'])
    plan = work / '.planning' / lane['plan_id']
    data = json.loads((plan / 'INPUTS.json').read_text(encoding='utf-8'))
    assert sha(Path(lane['card'])) == sha(plan / 'START_HERE.md') == lane['card_sha256']
    assert sha(plan / 'INPUTS.json') == lane['input_manifest_sha256']
    assert (plan / 'HANDOFF_CONTRACT.md').read_bytes() == (CENTRAL / 'handoff_contract.md').read_bytes()
    assert subprocess.check_output(['git', '-C', str(work), 'rev-parse', 'HEAD'], text=True).strip() == lane['base']
    assert subprocess.check_output(['git', '-C', str(work), 'branch', '--show-current'], text=True).strip() == lane['branch']
    for row in data['readonly_code']:
        assert sha(work / row['path']) == row['sha256'], row['path']
    for row in data['local_inputs']:
        assert sha(plan / row['path']) == row['sha256'], row['path']
    assert all((plan / name).is_file() for name in ('task_plan.md','findings.md','progress.md'))
    roots.append(work.resolve())
    checks.append({'lane': lane['lane'], 'card_and_copy_identical': True, 'baseline_branch_correct': True,
                   'readonly_code_unchanged': len(data['readonly_code']), 'inputs_match': len(data['local_inputs']),
                   'state': 'READY_NOT_STARTED'})
assert len(set(roots)) == 3 and not any(a in b.parents for a in roots for b in roots if a != b)
links = []
for p in CENTRAL.rglob('*.md'):
    for link in re.findall(r'\]\(([^)]+)\)', p.read_text(encoding='utf-8')):
        if not link.startswith(('http', '#')):
            target = (p.parent / link).resolve()
            assert target.exists(), (p, link)
            links.append({'file': str(p.relative_to(CENTRAL)), 'target': link})
ff = roots[2]
runtime = ff / '.planning/w07-ff-matrix-efficiency/input/runtime'
ignored = subprocess.run(['git', '-C', str(ff), 'check-ignore', str(runtime / 'et/transcript_tool.py')], capture_output=True)
assert ignored.returncode == 0, 'Code-only runtime must not be staged'
record = {'schema':'w07-root-packet-verification/1', 'lanes':checks, 'separate_roots':True,
          'local_links_verified':len(links), 'ff_runtime_ignored':True,
          'mother_pwf_updated':updated, 'provider_llm_calls':0,
          'future_worker_tests':'NOT_RUN', 'paid_budget_unchanged':True}
(HERE / 'verification.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
(CENTRAL / 'preparation-verification.json').write_bytes((HERE / 'verification.json').read_bytes())
p = HERE / 'task_plan.md'
s = p.read_text(encoding='utf-8').replace('2. 进行中：', '2. 已完成：').replace('3. 待完成：', '3. 进行中：')
s = s.replace('生成 RF 原生 draft 工程样本，供 Audit 包只读消费，然后完成三张独立卡。', '准备与边界核对完成；正常提交推送本批PWF/交接证据，再向用户给出三张卡与工作目录。')
p.write_text(s, encoding='utf-8')
with (HERE / 'progress.md').open('a', encoding='utf-8') as f:
    f.write('\n- 三卡及各自本地PWF已准备，固定原生合成三文件177809B，三workdir不重叠/分支基线/全部只读输入/本地链接核对通过；FF runtime忽略，不入commit。worker未开工。母12PWF与ROOT入口/失败诊断已同步。\n')
print(json.dumps({'lanes_verified':len(checks),'local_links':len(links),'mother_files':len(updated),'worker_tests':'NOT_RUN'}))
