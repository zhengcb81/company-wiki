"""Refresh current plans, retaining immutable failed evidence and shared history."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'docs/plans/cross-market-rf-e2e-2026-10-08'
W06 = BASE / 'phase6/w06_parallel_verification_2026-10-11'

port = {
 'task_plan.md': '''# ROOT W06-CWP-PORTABILITY 接收计划

状态：工程与独立验收通过，已正常并入本地主线；远端发布待记录。仅合成 Windows 存储/Reader/CLI 及工具判定范围。

- [x] A：原交付范围、22产品及6输入核对；原始失败封存 intake/。
- [x] B：目录归属、最小子进程环境、完整 SourceRef 实读、真实 CLI 输出、typed oracle 共因修复。69PASS/1宿主symlink SKIP/9.07s，七场景4.051s。
- [x] C本地：非作者53案例全部符合预期，原4错误输入SHA不变且正确FAIL；ROOT接收5f10af0b，正常merge master e2e19ea2。
- [ ] C发布：提交接收证据与PWF，正常push，记录精确远端HEAD及对应CI；清理ROOT干净工作树，保留branch/worker/evidence。

证据位于母W06/evidence/root-cwp-portability-acceptance/。最终产品freeze见 fix/verdict-aggregation/product-freeze.json，独审见 independent-verdict-final/report.json，本地主线见 local-main-integration.json，发布后见 publication.json。

这是显式手动工程工具，不复制到技能、不自动每commit跑七场景。原FAIL及原件保持；本包零provider/LLM/费用。生产许可和配置没有新增。母W04/G2/G4/G5仍开放。
''',
 'findings.md': '''# ROOT W06-CWP-PORTABILITY 当前发现

已关闭两组工具共因：初始化/清理只处理本次创建物；保留CLI原始结果，直接实读完整输入SourceRef，typed判定覆盖必需场景。后来独审发现“检测到expectation_unmet却汇总PASS”；现用显式Finding outcome、默认FAIL、None诊断和单调severity聚合，判定不依赖code前缀。

最终69PASS/1SKIP；七场景实际Reader/CLI成功；非作者53案0意外，原4反例输入SHA一致。11产品、8producer、旧FAIL及scratch均保持。仅Windows合成接口验收，不能认证POSIX、真实云、OCR、LLM或投资研究质量。

原FAILED报告完整保留于 intake/、independent-final/；其pending只代表当时状态。当前依据 independent-verdict-final/ 和 local-main-integration.json。正常commit前的额外diff-check曾因原pytest日志尾空格退出；原日志未改，正常仓库hooks通过。
''',
 'progress.md': '''# ROOT W06-CWP-PORTABILITY 接收进度

2026-10-11：原worker f8d5e0f4正常接入ROOT5f10af0b；master正常merge e2e19ea2。A/B/本地C完成，11产品canonical LF一致。最终69工程测试、七场景真实合成执行、53非作者案例及恢复检查已完成，没有重复跑逐小节点全链。

当前下一步：接收资料正常commit/push，记录exact remote/CI，再正常移除干净ROOT checkout。历史FAIL保留；worker与分支保留。没有技能安装，零真实外网/费用。母计划未完成。
'''
}
ff = {
 'task_plan.md': '''# ROOT W06-FF-MATRIX 接收计划

状态：原交付接收中；测试工具权威案例集合缺口修复中，生产跨期来源共因另由ROOT负责。不能把工具绿或worker交付当全链通过。

- [x] A：Git/PWF/25项范围核对；原12绿与独立10FAIL/1正控保留。初始化HOME错误、未验scan侧车及fixture同SHA碰撞已正确区分。
- [x] B1：环境、目录归属、绝对deadline、typed结果及真实byte/period/routing证明修复；34集中测试绿。实际原41矩阵19PASS/21FAIL/1PARTIAL，132.54s，完整旧证据保持。
- [ ] B2：CaseSpec/RunSpec唯一权威驱动runner和oracle，不能相信自报required_cases/expected/request。正式3反例RED后共用修复，全41删1/duplicate/extra和合法正控一次集中测试；非作者审查冻结输入与产品。
- [ ] C：工具验收后，等CWP共用跨期修复，原41向量/期望/180s上限在新独立attempt回放。再正常commit/并线/push及必要同步；零真实外网和费用。

排他接口：作者只写FF tools/offline_contract_matrix、本卡测试/fixtures/自身PWF/handoff；ROOT维护本接收计划、共享PWF、Git发布与CWP生产修复。ET/Dayu/IQS不写，FMP密钥只stat、不得读/hash/继承。现ROOT FF tree基于main08ec85b并已正常接c5527f1待提交。

当前写集与问题依据：母W06/evidence/root-ff-matrix-acceptance/independent-final/；活跃修复 fix/case-authority/，旧 fix/freeze-manifest.json、root_report.md和offline-evidence.zip不可覆盖。生产共因依据 root-cause-review/ 与 .planning/w06-cross-period-acquisition/，不是由工具特判换绿。
''',
 'findings.md': '''# ROOT W06-FF-MATRIX 当前发现

真实联调41case为19PASS/21FAIL/1PARTIAL。九份三市场2024财报由真实CWP公共ensure入库，同期复用正确；缺2025/2026时供应商未启动，多数ET场景受primary失败前置影响，不能判为ET内部错误。

已独立确认CWP共因：resolver排除旧期后，local_reconcile把同实体同类型来源重新纳入；canonical已验入库事实没有steady correction assertion，缺patch被无条件当目标缺口，阻断新下载。需在所属来源层统一可信事实和相关性，保留目标字节/身份/期间/as-of及预算；不增加人工签收或许可。

工具最终独审另发现3反例：删22失败案例并同步自报集合、删cutoff expected、把CN请求改HK并重算请求SHA，均可假PASS。ROOT要求单一CaseSpec权威、完整请求和覆盖核对，不能只加3字段特判或仅数41条。旧报告、ZIP、freeze及输入SHA保持。

完整证据：intake/初始错误；fix/冻结34测试与真实矩阵；independent-final/权威缺口；root-cause-review/生产根因；新修复 fix/case-authority/ 与 producer-scope-fix/分别归属不同目录。
''',
 'progress.md': '''# ROOT W06-FF-MATRIX 接收进度

2026-10-11：范围intake完成；34工程测试绿；实际41矩阵132.54s留证，8秒生产复现已封存。尚未commit/并主线/安装/发布本卡。当前最终独审为TOOL_BLOCKER_CASE_CONTRACT_AUTHORITY_P1，不是整体通过。

FF作者正对CaseSpec共因做TDD并冻结；CWP作者在独立cwp-acquisition-scope-root执行真实writer行为RED与共用scope修复。两个工区及证据目录排他。ROOT负责最后原矩阵一次联调与非作者大节点验收，不能先删失败或重复跑旧41CLI。

下一步：接收工具新freeze→非作者复核；接收生产新freeze→原41向量新attempt回放→正常发布。原件/生产配置/密钥/他人WIP保持，零真实provider/LLM/费用；母W04/G2/G4/G5仍开放。
'''
}
for dirname, docs in [('w06-cwp-portability-reception', port), ('w06-ff-matrix-reception', ff)]:
    for name, body in docs.items():
        (ROOT/'.planning'/dirname/name).write_text(body, encoding='utf-8')

oldline = 'OCR/RF/Audit已并线发布；Portability最终独审发现汇总缺口待修；FF最终离线矩阵在跑。母W04/G2/G4/G5未完成。目标active，不增加小节点许可；原FAIL/原件/配置/WIP保留。'.encode()
newline = 'OCR/RF/Audit已并线发布；Portability工程与独审通过并入本地主线、远端发布跟进；FF权威案例工具修复与CWP跨期生产修复并行。母W04/G2/G4/G5未完成。目标active，不增加小节点许可；原FAIL/原件/配置/WIP保留。'.encode()
for group in [BASE, ROOT/'docs/plans/narrative-evidence-pilot-2026-09-26', BASE/'phase6/w05_parallel_common_roots_2026-10-11', W06]:
    for name in ['task_plan.md', 'findings.md', 'progress.md']:
        path = group/name
        content = path.read_bytes()
        if oldline in content:
            assert content.count(oldline) == 1
            path.write_bytes(content.replace(oldline, newline, 1))
        else:
            assert newline in content

path = W06/'ROOT-reception-status.md'
content = path.read_text(encoding='utf-8')
content = content.replace('工具非作者范围验收中；ROOT独立生产施工计划', '最终独审发现CaseSpec权威缺口，正式RED后统一工具修复；ROOT独立生产施工计划')
content = content.replace('关闭 Portability 工具汇总缺口，接收 FF 矩阵的真实范围', '发布已验收并线的 Portability；关闭 FF CaseSpec 权威缺口，接收矩阵的真实范围')
content = content.replace('ROOT 修 FF 矩阵实证的生产共因（若确认）', 'ROOT 独立工区修复已确认的 CWP 跨期来源共因')
path.write_text(content, encoding='utf-8')

path = ROOT/'.planning/w06-cross-period-acquisition/task_plan.md'
content = path.read_text(encoding='utf-8').replace('起点CWP master057f2f8d（代码与8862372f相同）', '起点CWP mastere2e19ea2（生产来源代码与8862372f相同）')
content = content.replace('- [ ] 独立根因报告收尾，选择最小共用责任层方案；实现前记录具体函数写集。', '- [x] 独立根因报告已冻结于 root-cause-review/；新工区/函数写集已授权，来源资格设计与真实RED由专属作者执行。')
content = content.replace('Next Step：接收独立根因报告，写固定行为RED并冻结失败，然后实施共用scope责任层。', 'Next Step：专属作者在 cwp-acquisition-scope-root 写公共writer行为RED并冻结，再实施共用scope责任层；ROOT接收后重放原矩阵。')
path.write_text(content, encoding='utf-8')
print('current reception plans and 12 shared summary lines refreshed; immutable evidence untouched')
