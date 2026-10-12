"""ROOT one-shot preparation: independent sparse worktrees and fixed small inputs."""
import hashlib
import json
from pathlib import Path
import subprocess

PREP = Path(__file__).resolve().parent
CWP = PREP.parents[1]
PROJECTS = CWP.parent
MOTHER = CWP/'docs/plans/cross-market-rf-e2e-2026-10-08'
TOTAL = MOTHER/'phase6/w08_parallel_completion_2026-10-12'
INVENTORY = json.loads((PREP/'inventory.json').read_text(encoding='utf-8'))

def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding='utf-8',newline='\n')

def git(repo,*args):
    return subprocess.check_output(['git','-C',str(repo),*args],encoding='utf-8').strip()

def sha(path):
    assert not any(x in path.name.lower() for x in ['api_key','secret','credential'])
    return hashlib.sha256(path.read_bytes()).hexdigest()

LANES = [
    {'id':'W08-RF-COMBOS','repo':'revenue-forecast','slug':'rf-combinations',
     'plan':'w08-rf-combinations','base':INVENTORY['revenue-forecast']['head'],
     'sparse':['.githooks','.github','agents','config','references','scripts','tests','tools','docs/handoffs/w08-rf-combinations'],
     'title':'RF 原生模型剩余五组组合覆盖',
     'writes':['tools/model_generalization_matrix/**','tools/tests/test_w08_model_combinations.py','docs/handoffs/w08-rf-combinations/**','.planning/w08-rf-combinations/**'],
     'read_roots':['scripts','tests','config','references'],
     'details':'''## 已确认的缺口，不重复原 W07

W07工具已ROOT修复并发布8dc26710；原16向量及36工具测试通过，但整卡PARTIAL。必须读取input/remaining-coverage.md；它是详细设计依据，不是新许可。保持原16 CaseSpec和原36断言，扩独立COMBINATION_CASES；全清单/报告的required manifest来自同一权威清单，不只检查数量。

| 组合组 | 至少需要的实际原生路径 | 有意义的错/未知向量 |
|---|---|---|
| C01 货币单位 | 原生convert_input_quantity；CNY亿元、HKD百万元、USD millions同币种缩放及量×价 | 100/1000倍错误、自动换币、缺币种；不猜汇率或造单位名 |
| C02 并购/跨FY | 实际draft年度收入及dated contribution ancestry；非12-31年结、控制窗口 | 错年度、非控制期间、缺Q零补、全年+H1双计；不是仅测月份helper |
| C03 联合量价 | 原生unit_sales/联合情景，冻结同一shock的量价路径 | 只变一项、重复shock、偷偷重排scenario；不强迫Low≤Base≤High |
| C04 目标/净额 | 原生累计目标比较、gross/net、cannibalization/防双计 | 累计/期末当年度、混毛净额、新业务重复加到已含收入 |
| C05 actual/WAPE | 实际draft与既有历史误差接口，scope精确到segment/year/scenario | future assumption当actual、缺actual补0、无样本WAPE=0、校准跨scope |

每组至少一个合法向量和反例/未知向量，至少10个有不同机制的补充案例；必要的分支再加，不用十个同义数值凑数。独立期望在运行前固定，来自手算量纲/净额恒等式/期间，不从actual反推。一个场景需同时检验实际入参及真实结果，不能参数改了却运行旧input。

## 实施细则

1. 读tools/model_generalization_matrix的native/cases/oracle/runner/report/run，以及原tests/test_lifecycle_forecasts.py、test_research_evidence_roles.py、research数量/历史误差接口。已有测试helper可能修改参数和claim，逐例deepcopy；只读scripts与旧测试。
2. A先固定每个新case的native_entry、真实调用参数、expected推导、结果JSON pointer、哪些情况确实不支持。先写“错误实际结果必须被检出”的行为测试取得RED。
3. B扩现有工具，不另建引擎、不复制forecast计算代码；mode=draft。拒绝必须为真实合同拒绝，未知不算PASS；NOT_SUPPORTED列未关闭组及实际异常。保留原native异常分类、request/result SHA、readonly/cleanup及完整清单。
4. C实际原生全清单一次E2E，现有公开run.py --e2e实际合法/拒绝/support三个CLI。全清单至少原16+补10，不删原case。CLI与引擎差异单列，不mock本节点。
5. 如发现core缺陷，输出最小原生复现和先红测试建议，由ROOT修scripts；本包继续可做部分，不越界或改期望求绿。

## 测试包与交付

B一次集中：python -B -m pytest -q tools/tests/test_w07_model_generalization.py tools/tests/test_w08_model_combinations.py。
C公开入口：python -B tools/model_generalization_matrix/run.py --owned-root ABS_NEW --out-root ABS_NEW --e2e；先--help确认已有参数，不创造不存在的开关。至少一次absent恢复和一次existing empty dir/sentinel失败恢复。没有平台实测就记NOT_RUN。

输出保持model-generalization-matrix/1兼容或明确有依据的additive字段；source_truth_verified=false、economic_reasonableness=not_evaluated。每组交case/native入口/指针/推导/status映射；缺组或未知不能升级整卡COMPLETE。原生payload一份ZIP与小摘要，禁止PWF、handoff再各复制完整JSON。零API/LLM。
'''},
    {'id':'W08-AUDIT-EVIDENCE','repo':'revenue-forecast-audit','slug':'audit-evidence',
     'plan':'w08-audit-evidence','base':INVENTORY['revenue-forecast-audit']['head'],
     'sparse':['skills','tests','tools','docs/handoffs/w08-audit-evidence'],
     'title':'四路审查的执行证据实读与覆盖核对',
     'writes':['skills/revenue-forecast-audit/scripts/review_protocol.py','skills/revenue-forecast-audit/scripts/review_evidence*.py','skills/revenue-forecast-audit/references/review-evidence-reconciliation.md','tests/test_w08_review_evidence.py','tests/fixtures/w08_review_evidence/**','tools/run_review_evidence_e2e.py','docs/handoffs/w08-audit-evidence/**','.planning/w08-audit-evidence/**'],
     'read_roots':['skills/revenue-forecast-audit/references','tests/fixtures/forward_bundle'],
     'details':'''## 当前接口和真正待补的部分

已有review_protocol.py已经检查四审checkpoint、N/A、FAIL→finding、完整issue key、numeric denominator、crosscheck和declared/observed scope；不要重新实现这些检查。其check_coverage(payload)是声明核对，没有实读每项evidence。document_status_join已有请求/调用/逐文档状态与一次费用语义，audit_run已有event/capture/check；复用结果，不再造执行库或审查器。

本包新增**报告型、可选的实际文件/执行记录核对**，用于G4/G5发现“报告齐了却没跑/没读/用旧attempt”的可观察缺口。不是重新验证公司身份、raw字节和来源资格；这些由CWP/RF责任层负责。不能凭日志证明隐藏思维、真实agent独立性或来源真值。

## 实施细则

1. 先读SKILL、references/artifact-contract.md、workflow.md、四review卡，以及audit_run/audit_contracts/review_protocol/document_status_join；固定真实run/event/report字段，未知字段原样兼容。输入由显式execution root和coverage JSON指定，不能扫描本机所有runs/原件/会话或环境密钥。
2. 增加可选CLI coverage --execution-root ABS，保留旧check_coverage(payload)和旧CLI无该参数的行为/断言。新增pure helper及reference明示路径、pointer/行locator、事件/产物引用分类、限额和输出。
3. 实读JSON/有界UTF-8文本evidence，存在文件不等于locator可解析；明确json pointer与行范围，未知PDF locator/source_id/tool-call为UNVERIFIABLE，不在本包调用SourceReader/provider/OCR。相对路径依据显式root，允许用户显式列出的外部只读artifact，禁止隐式全盘扫描。链接/逃逸路径诊断，不打开未知目标。
4. supplied hash才比较；缺hash只记录observed SHA/未签hash状态，**不要求补人工签名、不因缺hash阻断**。SHA是当前读取字节观察，不能冒称历史时点未篡改；有freeze/capture历史可据其显式引用对比。
5. 核对run/review_attempt/role实际已知字段、current报告和真实事件call IDs/输出引用；同公司旧run或旧attempt不作为本轮凭据。opaque公司id当引用、不加身份解析。command_started不等于finished，exit0不等于业务成功，output_complete=false不能称全程可复查；无真实事件列未核查而不是臆造已调用/偷懒结论。
6. numeric verified条目按value_id去重/发现重复，实读明确recompute artifact locator；相同引用重复不能增加分母覆盖。跨role同issue_id按既有完整key保留，不改W05pool状态或预算账。counter/support或数值来源真伪仅引用已有诊断，不重算预测。
7. 输出保持review-coverage/1兼容，additive evidence_reconciliation节点，逐条OBSERVED/UNAVAILABLE/UNVERIFIABLE/MISMATCH和具体refs/reasons。records_complete仍只是记录完整，quality_status=not_evaluated；四审无finding不自动经济PASS。失败范围不中断其他可检查行。
8. 用audit_contracts.write_attempt/Redactor；显式max总文件数、单件/总读取字节、时间上限（建议128件/1MiB单件/8MiB合计/30秒），超限记未核查不伪造完整。不得全套复制执行包/PDF，不读dotenv或真实key。超限是资源诊断，不是新许可。

## A/B/C测试

A先固定有真实文件/真实调用event的合法小包与反例；不能只有手填PASS四份报告。行为RED：文件存在但坏pointer、旧attempt、缺完成事件、坏hash、重复numeric证据、tool-call无可验证响应、截断stdout、opaque引用/缺hash合法保留、文件过大/输出冲突/错误恢复。
B一次集中：python -B -m pytest -q tests/test_review_protocol.py tests/test_w08_review_evidence.py；同时明确旧结构CLI回归。
C新tools/run_review_evidence_e2e.py实际调用audit_run init/event/capture、当前coverage CLI与新可选入口（先--help核参数），生成一份合法包与上述有限反例。child仅本地合成文本程序，保留真实exit/捕获日志；不启动RF/其他agent，不称它四路真实公司审查。每份新attempt输出互不覆盖，临时根absent/sentinel都恢复，固定input与原包SHA保持。

交reference/输出schema/真实CLI日志、固定反例expected→actual、缺支持locator清单和ROOT的四审接线建议。Audit没有remote，仅正常本地commit。SKILL/旧review卡/安装/loop/status_join/财务审查器/核心audit_run不写；ROOT收后接线安装。零模型/provider。
'''},
    {'id':'W08-CWP-G2-REPLAY','repo':'company-wiki','slug':'cwp-g2-replay',
     'plan':'w08-cwp-g2-replay','base':INVENTORY['company-wiki']['head'],
     'sparse':['.githooks','.github','src','scripts','tests','tools','config','docs/handoffs/w08-cwp-g2-replay'],
     'title':'G2摘要—公开读取—RF消费的可复现离线联调包',
     'writes':['tools/narrative_g2_replay/**','tests/unit/test_w08_narrative_g2_replay.py','tests/fixtures/w08_narrative_g2/**','docs/handoffs/w08-cwp-g2-replay/**','.planning/w08-cwp-g2-replay/**'],
     'read_roots':['src','tests/support','tests/fixtures/narrative_real_transcript','config'],
     'details':'''## 当前上下文与排他边界

ROOT正在修W04核心selector的18既有边界FAIL；src/scripts/旧tests归ROOT，此包**只写新工具、新测试、新小fixture**。现在能开发联调框架与冻结基线；不等W04，不把当前已知失败改成期望或最终质量通过。交工后ROOT用已修W04重跑同CaseSpec、再实际配置LLM的G2。无需等RF/Audit新包。

已有tools/g2_acquisition_chain_e2e.py只覆盖采集；本包不重写它/FF矩阵。参考tests/integration/test_narrative_batch_cli_e2e.py、test_narrative_generation_reuse.py、test_narrative_batch_cross_run_e2e.py、test_narrative_runtime_e2e.py与tests/support/narrative_batch_fixtures.py；已有有限AUTO Store/lease/generation/outbox/子进程Worker就是唯一运行机制。不得再搭任务库/摘要引擎。

## 实施细则

1. A固定真实公开命令和native DTO：当前source_catalog CLI、finite narrative batch CLI、narrative read/rationale、RF scripts/company_wiki_narrative_reader.py与narrative_source_preparation.py。先逐个--help、读原integration fixture确认参数，不按记忆造CLI。记录module实际路径/固定code SHA；源码输入是本工区和input/runtime/rf固定快照，不读canonical WIP。
2. 建最小一组公司fixture；内容明确synthetic、业务事实和表格/套话对照。类型覆盖年报、半年报、季报、招股、增发/可转债、IR、原语言TXT电话会。可把增发/可转债合为同一CaseSpec组但各自typed请求要实跑。PDF/HTML/TXT由真实现有parser处理；不把所有类型改成txt冒签PDF。正文小到足够检验来源→span→summary绑定，不声称真实召回率。
3. 通过实际canonical import/scan或当前公共source接口登记，仅生成隔离catalog/AUTO/配置/companies。不能手填已验SourceRef、直接写DB假装公共入库成功。目录路径仅在storage/bootstrap处理，消费者使用SourceRef/公开reader。
4. 用现有loopback model fixture/配置式HTTP模拟模型边界；真实finite worker/摘要选择/verify/publish/read链必须运行。不mock整层；stub只回确定性原语言draft。请求不带真实key，环境最小白名单，禁止公网，translation calls=0。此节点不验证供应商模型质量。
5. CaseSpec至少：业务内容可定位并实际进入summary；财务纯表格/格式套话无有价值经营信息时明确skip/无summary；招股/融资document_kind保持；TXT原文SHA/语言不变且没有PDF转换；低质量/错误locator/坏summary证据不算verified。
6. 真实第二run复用：相同版本/spec没有重复model POST，仍fresh公开read/locator验真；换有效source版本或选取策略应失效，不能缓存复用错版本。用少量现有场景，不在每份文档重复全41采集矩阵。
7. 真实RF只读消费固定代码快照，使用公开narrative reader/source preparation入口；只验证有效证据读入、缺口/语言/period保留，不建正式预测、不写RF/StockWiki、不编economic claim。明确read成功、draft有无支持、是否真实model调用三个不同事实。
8. 既有W04已知失败要按case/status/root_cause/真实复现记录；产品不能修时交PARTIAL。工具oracle要能拒绝空case、删必需组、自报PASS无原始receipt、坏SHA/locator、第二run有新POST、未恢复scratch。expected独立固定，不根据输出重写。

## 测试与公开交付入口

B集中：python -B -m pytest -q tests/unit/test_w08_narrative_g2_replay.py。先oracle行为RED，再实现。只mock工具错误边界；不每个case跑全仓。
C实现公开python -B tools/narrative_g2_replay/run.py --rf-project ABS_FIXED --owned-root ABS_NEW --out-root ABS_NEW，参数/README一次定义并实际启动。同批次至少两种格式和上述类型typed矩阵，第二run零模型POST，实际RF消费与失败恢复；batch采用单一绝对deadline，建议180秒、单子命令30秒，超限真实PARTIAL/NOT_RUN。不用提时限掩盖重复初始化；重型E2E手动大节点，不改CI/hooks。

产物schema=narrative-g2-replay/1：scope/code_binding/case_specs/cases及request/result/关键artifact SHA/locator/actual model calls、原始与派生字节、cleanup/remaining。supplier_fixture=true、llm_semantic_quality=not_evaluated、source_truth_verified仅说明本地实际原件验证范围，不能把synthetic身份等同真实公司。原始报告一份压缩小bundle＋摘要（≤8MiB），临时派生和自建原件恢复成原样；不复制生产数据湖。报告不可用out目录已存在文件覆盖。

ROOT收后提供--rf-project指向当前已验固定RF，以及已修CWP再验；若需profile配置或core修复，列接口建议不越界。后续真实MiMo/DeepSeek/MiniMax配置调用、累计预算、真实公司G2/G4/G5由ROOT执行。本包0收费调用，不修改production config、不同步安装、不原地rebase ROOT。
'''},
]

COMMON = '''# W08 共用交接接口（工程记录，不是许可门）

仅A设计/TDD、B集中回归、C一次实际E2E三个大节点。平时可跑必要小测试，不增加逐文件人工审查。正常commit后STOP交ROOT；不push main、不合并其他线、不安装技能、不改CI/hooks/生产配置。正常hook失败记录原因，不用--no-verify，不删旧断言。ROOT最后收集三个交付并串行接线、修core、并主线、安装和精确CI。

## 文件

自己docs/handoffs/<plan_id>/handoff.md与handoff.json；JSON schema=w08-lane-handoff/1。包含lane_id、plan_id、repo/workdir/base_head/branch/implementation_commits/handoff_commit、scope_status=COMPLETE|PARTIAL、changed_files(path/sha256)、readonly_input_manifest_sha256、A/B/C记录（UTC/真实命令/exit/elapsed/结果/证据ref）、case_coverage(expected IDs/实际运行IDs/missing/unknown)、actual_code_binding、cleanup(before/after/remaining)、resource_usage（未测用null）、provider_calls/llm_calls/cost（本包都0）、known_baseline_failures、新缺陷最小复现、remaining、ROOTintegration建议。

实施SHA可取提交代码时的HEAD，handoff_commit若自引用不可填则交工消息补精确SHA，不猜自身hash。记录完整changed_files含计划/测试/工具，但不用复制整仓hash。初始input不可改，准备的START_HERE/施工卡/INPUTS是独立上下文；自己PWF写进度即可。旧本仓AGENTS职责边界适用。

每个产品/工具问题按issue→机制→最小反例→所属责任层→修复建议→测试记录映射；未执行/未知/外部限制不能PASS。只检查本层职责，不叠新身份、hash必填、授权JSON、人工签收、canary、第二budget/state库。

## 测试恢复

首次记录absent或已有文件/空目录/sentinel；只清理该次新建且确定归属的scratch。保留初始文件与报告；不global kill，不删除其他agent数据；失败/timeout也恢复，无法恢复交准确残留路径。保留少量关键失败与一个最终压缩证据，实际payload不重复复制。Code-only快照不是全湖备份；累计所有报告建议≤8MiB，峰值未测填null。

## 独立运行

不能读另一W08工区或等待另一包交付；所有必需输入已在本工区/固定input可得。ROOT主线升级不会进入本包代码，固定base保持。需要其他层新增API时给ROOT建议；本包不得偷偷改邻仓。只有ROOT批准的新版本输入才另建新的证据attempt，不倒改初始manifest。
'''

assert not TOTAL.exists(), 'one-shot directory already exists'
dispatch = []
for lane in LANES:
    repo = PROJECTS/lane['repo']
    work = PROJECTS/'_harness_worktrees/w08'/lane['slug']
    branch = 'codex/'+lane['plan']
    assert not work.exists()
    subprocess.run(['git','-C',str(repo),'worktree','add','--no-checkout','-b',branch,str(work),lane['base']],check=True)
    subprocess.run(['git','-C',str(work),'sparse-checkout','init','--cone'],check=True)
    subprocess.run(['git','-C',str(work),'sparse-checkout','set',*lane['sparse']],check=True)
    subprocess.run(['git','-C',str(work),'checkout'],check=True)
    assert git(work,'rev-parse','HEAD') == lane['base']
    assert not git(work,'status','--porcelain')
    own = work/'.planning'/lane['plan']
    read = own/'input'
    read.mkdir(parents=True)
    write(own/'.gitignore','input/\n.runtime/\n')
    preamble = f'''# {lane['id']}：{lane['title']}

## 可以现在独立启动

- 工作目录：`{work.as_posix()}`（已准备，不是原主仓）
- 所属项目：`{lane['repo']}`；固定基线：`{lane['base']}`
- 分支：`{branch}`；PWF：`.planning/{lane['plan']}/`
- 先读本卡、同目录HANDOFF_CONTRACT.md与INPUTS.json；不取消稀疏checkout，不拉入旧大体积.planning/assurance/output。
- 本包预算：外网provider/LLM调用0；不要读取真实凭证或恢复暂停母目标。无需等待另外两个W08包。

## 唯一可写集

'''+'\n'.join('- `'+p+'`' for p in lane['writes'])+'\n\n未列入写集均只读，包括旧断言/初始input/主线/安装及其他包。ROOT专属母PWF、W04 core、G2真实付费、主线/安装/CI。\n\n'
    card = preamble + lane['details'] + '\n## 交工\n\n按本地HANDOFF_CONTRACT.md正常commit并STOP；交给ROOT卡号、实际branch/HEAD和handoff绝对路径。允许如实PARTIAL，不以只测wrapper冒签原生E2E。\n'
    write(TOTAL/'cards'/f"{lane['id']}.md",card)
    write(own/'施工卡.md',card)
    write(own/'HANDOFF_CONTRACT.md',COMMON)
    manifest = {'schema':'w08-inputs/1','lane_id':lane['id'],'base_head':lane['base'],
                'read_only_roots':lane['read_roots'],'files':{},'dependencies':{}}
    paths = git(work,'ls-files',*lane['read_roots']).splitlines()
    for relative in paths:
        p = work/relative
        if p.is_file() and not any(x in p.name.lower() for x in ['api_key','secret','credential']):
            manifest['files'][relative] = {'sha256':sha(p),'bytes':p.stat().st_size}
    if lane['id']=='W08-RF-COMBOS':
        data=(MOTHER/'phase6/w07_parallel_quality_2026-10-11/ROOT-rf-remaining-coverage.md').read_bytes()
        (read/'remaining-coverage.md').write_bytes(data)
        manifest['files']['.planning/'+lane['plan']+'/input/remaining-coverage.md']={'sha256':sha(read/'remaining-coverage.md'),'bytes':len(data)}
    if lane['id']=='W08-CWP-G2-REPLAY':
        rf = PROJECTS/'revenue-forecast'
        rf_head = INVENTORY['revenue-forecast']['head']
        snapshot = read/'runtime/rf'
        dependency = {'commit':rf_head,'root':str(snapshot),'files':{}}
        for relative in git(rf,'ls-tree','-r','--name-only',rf_head,'scripts').splitlines():
            # Fixed runtime source only; no live config/output/key/pyc.
            if not relative.endswith('.py'):
                continue
            raw = subprocess.check_output(['git','-C',str(rf),'show',rf_head+':'+relative])
            target = snapshot/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(raw)
            dependency['files'][relative]={'sha256':sha(target),'bytes':len(raw)}
        manifest['dependencies']['rf']=dependency
    write(own/'INPUTS.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    write(own/'task_plan.md',f"# {lane['id']} 独立实施计划\n\nOwner外部harness；状态READY_NOT_STARTED。固定base {lane['base']}。\n\n## 大节点\n\n- A pending：读施工卡/输入，冻结case与期望，先写行为RED。\n- B pending：实现本包唯一写集，一次集中回归，保留旧断言/输入。\n- C pending：实际原生/公开CLI E2E、恢复、范围/提交/handoff；STOP等ROOT。\n\n## Next Step\n\n读施工卡.md、HANDOFF_CONTRACT.md、INPUTS.json，再调查本层实际接口。不要重复已完成W07。\n")
    write(own/'findings.md',f"# Findings\n\n本包的既有事实和入口均在施工卡.md；代码固定{lane['base']}，不读取浮动canonical WIP。首个任务是把真实支持接口与未知范围记录于此。\n")
    write(own/'progress.md',"# Progress\n\n2026-10-12 ROOT已准备独立worktree、PWF及只读输入；尚未开工/未实施代码/未收费。\n")
    write(own/'START_HERE.md',f"# {lane['id']} 启动入口\n\n工作目录 `{work.as_posix()}`。先读施工卡.md，再HANDOFF_CONTRACT.md、INPUTS.json、三个PWF文件。\n\n这是新W08卡，不重跑W07；初始input固定只读，RF/CWP/Audit其他工区均不写。具体范围/命令/验收在施工卡。正常commit到本分支，STOP交ROOT；不推main/安装/改共享PWF。\n")
    size=sum(p.stat().st_size for p in work.rglob('*') if p.is_file() and p.name!='.git')
    dispatch.append({'lane_id':lane['id'],'repo':lane['repo'],'workdir':str(work),'branch':branch,
       'base_head':lane['base'],'plan_id':lane['plan'],'status':'READY_NOT_STARTED',
       'card':str(TOTAL/'cards'/f"{lane['id']}.md"),'start_here':str(own/'START_HERE.md'),
       'card_sha256':sha(own/'施工卡.md'),'input_manifest_sha256':sha(own/'INPUTS.json'),
       'readonly_files':len(manifest['files']),'prepared_bytes':size,'write_set':lane['writes']})
write(TOTAL/'HANDOFF_CONTRACT.md',COMMON)
write(TOTAL/'dispatch.json',json.dumps({'schema':'w08-root-dispatch/1','state':'READY_NOT_STARTED','lanes':dispatch},ensure_ascii=False,indent=2)+'\n')
write(TOTAL/'README.md','''# W08 三个可以现在独立启动的施工包 — 2026-10-12

本批只发这三张新卡，工作目录已准备；不是前次W07的重复。ROOT负责总接口/共享PWF/最终验收并线安装；workers不推main。

| 卡 | 做什么 | 工作目录 | 施工卡 |
|---|---|---|---|
| W08-RF-COMBOS | 补五组已确认遗漏的原生模型组合；保留原16/36 | C:/Users/郑曾波/Projects/_harness_worktrees/w08/rf-combinations | [卡](cards/W08-RF-COMBOS.md) |
| W08-AUDIT-EVIDENCE | 在已有四审覆盖工具上实读执行证据/locator与当前attempt，报告缺口 | C:/Users/郑曾波/Projects/_harness_worktrees/w08/audit-evidence | [卡](cards/W08-AUDIT-EVIDENCE.md) |
| W08-CWP-G2-REPLAY | 做可复现的摘要→公开read→固定RF消费离线包，不修改W04 core | C:/Users/郑曾波/Projects/_harness_worktrees/w08/cwp-g2-replay | [卡](cards/W08-CWP-G2-REPLAY.md) |

## 为什么能同时跑

三工作目录不重叠、三项目不同，唯一写集见dispatch.json。CWP包新tools/narrative_g2_replay与新测试，ROOT改W04 src，源码写集不重叠；输入仍固定122bbe3b，不读ROOT新WIP。RF包只扩tool，不动scripts；Audit包只改review_protocol/新evidence helper，不动loop/四review主卡。CWP只消费固定RF8dc26710代码快照，不等待新RF组合工具，Audit也不读另外两包。

## ROOT接线顺序

1. ROOT W04已证实共因修复→集中测试→正常发布，母目标仍暂停时不因发卡自动启动。
2. 接收三个分支和handoff，独立大节点检查；RF闭五组覆盖，Audit由ROOT接入四审/安装，CWP使用已修当前核心重跑同CaseSpec。
3. ROOT真正配置的G2有限付费模型/公开read/RF消费；G4原三家公司/12独审；G5新A/H/US三家及后续循环。工具工程绿不等于研究完成。

workers只在A/B/C三大节点审查；测试与下载资料归独立测试根并恢复原样。缺hash不新增签收，未知不PASS。各包0外网provider/LLM调用，ROOT累计预算仍$20/200万tokens。

完成后给ROOT卡号、workdir/branch/HEAD和docs/handoffs/<plan_id>/handoff.json/md绝对路径；一包不需要等另一包。详各卡和[共用交接接口](HANDOFF_CONTRACT.md)。母当前状态见[ROOT入口](../w06_parallel_verification_2026-10-11/ROOT-reception-status.md)。
''')
write(TOTAL/'task_plan.md','''# W08 ROOT 总计划

A准备/核对完成；B外部harness施工pending；C ROOT接收/并线/安装pending。只有三包，初始READY_NOT_STARTED。

## Next Step

用户分别交三个独立harness，使用每张卡上的实际工作目录。ROOT保留共享接口及母W04/G2/G4/G5；不在主仓运行worker，不代其启动。
''')
write(TOTAL/'findings.md','''# Findings

RF五组缺口来自W07 ROOT已公开PARTIAL，不另造需求。Audit现check_coverage只声明核对，新增optional实际读取避免重复其已有checkpoint/issue逻辑。CWP现g2_acquisition_chain只采集，新包接有限摘要/复用/read/固定RF消费；已知W04产品FAIL由ROOT修，worker如实PARTIAL。三包排他写集与固定输入，无新provider/数据库/许可门。
''')
write(TOTAL/'progress.md','''# Progress

2026-10-12 ROOT创建三个新独立稀疏worktree、准确base/branch、本地施工卡/START_HERE/INPUTS/PWF/交接接口。尚未开工。没有model/provider调用，不动原件/其他WIP/安装/生产配置。
''')
print(json.dumps({'cards':3,'lanes':[{k:v for k,v in d.items() if k in ['lane_id','workdir','base_head','prepared_bytes','readonly_files']} for d in dispatch]}))
