"""Refresh only current PWF summaries; preserve historical bodies/CRLF bytes."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'docs/plans/cross-market-rf-e2e-2026-10-08'
W06 = BASE / 'phase6/w06_parallel_verification_2026-10-11'
old = 'OCR/RF/Audit已并线发布；Portability正常并线发布且精确CI绿；FF权威案例工具修复与CWP跨期生产修复并行。母W04/G2/G4/G5未完成。目标active，不增加小节点许可；原FAIL/原件/配置/WIP保留。'
new = 'OCR/RF/Audit/Portability已并线发布；FF手动矩阵工具已并main4167dac4且精确CI38148263309成功。CWP跨期修复191+14独审通过，原41联调40/1，正在修ET→FF截止日诊断。W04真实6原件旧指纹保持但3项业务召回FAIL，按共用质量排序修；G2/G4/G5开放。目标active，不增加小节点许可；原FAIL/原件/配置/WIP保留。'
for group in [BASE, ROOT / 'docs/plans/narrative-evidence-pilot-2026-09-26',
              BASE / 'phase6/w05_parallel_common_roots_2026-10-11', W06]:
    for name in ('task_plan.md', 'findings.md', 'progress.md'):
        path = group / name
        raw = path.read_bytes()
        assert raw.count(old.encode()) == 1, path
        path.write_bytes(raw.replace(old.encode(), new.encode(), 1))
path = W06 / 'ROOT-reception-status.md'
raw = path.read_bytes()
old_row = next(line for line in raw.splitlines() if line.startswith(b'| W06-FF-MATRIX |'))
new_row = '| W06-FF-MATRIX | 固定CaseSpec/RunSpec 195PASS，非作者28/28；已并FF main4167dac4、精确CI38148263309成功，正常push645PASS/7host或显式环境SKIP。CWP来源修复191PASS+13/1独审通过；原41从19/21/1升到40/1、164.62秒 | 剩余call_past_cutoff仅ET→FF原因丢失；TDD共用结构化诊断，原期望不改。整个矩阵C仍开放；手动工具不在每commit跑41场景 |'
raw = raw.replace(old_row, new_row.encode(), 1)
old_order = b'1. '
start = raw.index(old_order, raw.index('## 执行顺序'.encode()))
end = raw.index('本批次0真实provider'.encode(), start)
nl = b'\r\n' if b'\r\n' in raw else b'\n'
text = '''1. FF工具已正常并线推送且CI绿；CWP来源12文件静态hook发现单处空dict annotation，补类型后正常并线发布。旧freeze与失败保留。
2. 独立ET/FF工区实施来源cutoff原因及闭集投影；非作者一个大节点，原41按原期望/180秒新attempt回放，再正常发布/必要定点安装。
3. 母W04工程365与非作者范围绿；真实六原件77.681秒、旧6指纹/raw/cap保持但LPCVD数量、钨验证量产订单、PRISMO PD5新事实3项FAIL。soft quota抢先于质量的共因已确认，Phase2质量带/同带公平TDD修复，不抬cap、不特判。
4. G2真实有界摘要及RF消费 → G4原三公司执行/四路独审 → G5另三公司和指定公司循环。W04/G2/G4/G5仍开放，不能声称整个PWF完成。

'''
raw = raw[:start] + text.replace('\n', nl.decode()).encode() + raw[end:]
path.write_bytes(raw)
pub = W06 / 'evidence/root-ff-matrix-acceptance/tool-publication/publication.json'
record = json.loads(pub.read_text(encoding='utf-8'))
record['ci'] = {'id': 38148263309, 'conclusion': 'success', 'head_sha':record['main_commit'],
                'url':'https://github.com/zhengcb81/filing-fetch/actions/runs/38148263309'}
pub.write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
print('12 shared summaries + current overview + exact FF CI updated; history unchanged')
