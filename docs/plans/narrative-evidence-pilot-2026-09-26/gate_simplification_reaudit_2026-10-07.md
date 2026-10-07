# G2：门禁与权限全面补漏及优先实施单

**状态：审计完成；实施 in_progress。优先级：P0，先于 R2 生产来源准备、R3 摘要运行和 R4 可选去重。**

这是 2026-10-07 用户“全面审查、查缺补漏、加到 PWF 并提高优先级”的实际施工入口。G1 的已发布成果继续有效，但其“约定范围完成”不能代表所有遗留机制已清空。目标服务最新实读active，当前顺序仍为G2→R2→R3→R4→R5，不增加角色、人工签收、授权文件或逐小节点检查。

用户现要求独立并行施工包，已拆出[G2三个新包](harness_lanes/g2_parallel_packages_2026-10-07.md)：SW06/StockQA10各P0-B，RF05为可并行P1。三卡用户已分派，待交接；独占工作树/写集/测试/交接各自完整，MAIN仍独占CWP13/01b/12和总PWF/生产/并线。不是重派旧完成卡。

## 1. 审计范围和证据

已检查八个来源链仓库的当前主线/工作树、当前公开入口、运行配置、错误分类、维护命令、提交规则及 CI；另读两份已安装 filing-fetch 技能。结构问题用 CodeGraph caller/context，字符串与实际配置用文件读取；不以搜索到多少个 gate/review 单词作为结论。

| 仓库 | 实读 HEAD | 本轮重点 | 归属 |
|---|---|---|---|
| company-wiki | 2cad90d | live runtime policy、SourceReader pin、AUTO、CLI、冻结 Pipeline、hook/CI | MAIN |
| filing-fetch | 758e8f4 | v2 单下载意图、v1 兼容、安装技能 | MAIN 集成，改动前核最新状态 |
| earnings-transcripts/earnings-transcripts | 2b9fb84 | provider 配置、单网络意图、旧 TXT 复用 | MAIN 集成 |
| revenue-forecast | e241389 | 可选 release_readiness、coverage 工具、来源消费 | 隔离修改；三份 owner 日志不动 |
| StockWiki | 9f552a6 | check_all、AGENTS、覆盖率/体量硬门 | 隔离修改；投资研究状态不改 |
| StockInfoDLSimple/v2-clean-rewrite | 8ed5fdd | 当前 CWP adapter、Git 工作树 | 有 11 个 tracked 修改和未跟踪文件，保留 owner 改动 |
| MeetingConverter | 8a33a7f | 已交付 CI 精简、运行入口 | 未发现需恢复人工审批的新问题 |
| StockQAbyLLM | 原审计34493d5；后续实读6a9ff138 | CI/本地/hook/默认pytest配置一致性、指标门、重复 job | 最新staged/unstaged均0、untracked7；实施前再核，工程工具仅隔离目录清理 |

HEAD/文件 SHA/工作树/现场 policy 原文见[只读审计收据](harness_lanes/results/g2_gate_reaudit_2026-10-07.json)。这是入口和机制审计，**不声称逐行读完全部历史 worktree**。Dayu 是纯外部项目，零代码变更；IQS 有独立项目，不介入。沙箱/操作系统/供应商套餐限制不是项目内人工权限，不能通过修改项目声称取消了它们。

再次追链的14组、scoped pin边界、StockQA最新HEAD、具体同步写集/能力保护与核心本地证据见[补充审计收据](harness_lanes/results/g2_gate_reaudit_followup_2026-10-07.json)。原收据保持原时点，不回写成新状态。

## 2. 已完成项继续保留，不重复施工

- private/public 外发权限、prompt-injection/not_reviewed/待修复提案的人工阻断已退出当前约定入口；历史审查记录只诊断，不恢复签收。
- AUTO Approval CRUD、独立 reviewer、gold/shadow/Work Unit 人工链已退出；历史表不为本次清理整库重写。
- FF v2 以一次 `filing_intent` 驱动下载，ET 为原语言 TXT；两份已安装 FF 技能都以 v2 为推荐入口，不能误报“还在默认 v1”。
- RF 人工 release_authorization 已退出；来源公开日而非下载日的跨仓合同已并线、正式六 CLI 已验收。
- CWP commit 已不跑 pytest；当前单 Python 快 CI 已绿。2cad90d 的 202 项责任节点/64.81 秒与[精确 CI 37582474369](harness_lanes/results/r2_systemic_exact_ci_2026-10-07.json)复用，不因补计划再次跑全部长测。
- 全根发现、有限登记、适配器重复 SHA、AUTO 范围 SQL、同版本终态恢复零子进程的系统性修复已发布。现场steady迁移本次已完成，不能将此等同新版读取pin/handler的发布或生产摘要完成。

## 3. 漏项清单：按实际影响排序

### G2-00 / P0：现场 canary 与默认读取路径（现场已迁移；核心93ac5a5已推）

**原审计确实生效；现已迁移。** `.source_catalog/runtime_policy.json` 原为2026-08 canary，六flag/epoch/cohort/关闭legacy bridge隐藏capture，是G1漏项。现在以已发布2cad90d代码、现有锁/CAS切为264B schema2 steady；16条有效断言保持、17张事实表/222408704B数据库/原件及owner配置不变，同payload重复CAS零写。[现场收据](harness_lanes/results/g2_steady_production_migration_2026-10-07.json)明确旧视图是迁移后用原小snapshot及同一只读DB重建，没有伪造迁移前采样或完整备份。

已核 16 条 active/verified、2 条 legacy/verified、4 条 candidate。直接删除 JSON 会退回 v1 默认并隐藏已生效断言，不能这么做。schema 2 `steady` 已在 2cad90d 发布、CI 绿，排除 shadow/candidate/rejected，断言优先、legacy capture 仅补缺，仍绑定真实来源 SHA。

**实施：**先核实际无活跃 writer/AUTO lease；用现有 `CatalogOperationLock` 和 `save_runtime_policy_cas`，比较旧 snapshot SHA/current root policy，再应用[已生成 steady payload](harness_lanes/results/r2_steady_runtime_policy_payload_2026-10-07.json)。旧小配置已在[预检](harness_lanes/results/r2_canary_retirement_preflight_2026-10-07.json)保存，不备份整个库。保留 activation journal，旧 schema 仅历史解码/迁移兼容；默认新库也应采用 steady，不能迁完旧库后新库又默认 canary/v1 控制面。

**完成条件：**现场部分已满足上述小收据；S07 security_id仍是旧公司名标签，期间/公开日修正属于R2，不能声称metadata全部完备。另用新库真实读反例验证无snapshot默认steady：2个语义RED→89项责任GREEN；显式schema1兼容保留。默认实现及有效readpin核心已在93ac5a5正常提交推送，精确CI37590638806全部步骤绿90秒；01b与13等pending不由本子集替代。

### G2-01 / P0：读取指纹仍绑定整个配置

**审计前实际缺陷；有效字段投影本次已修，01b范围仍pending。** 原`source_read_policy.py`对`asdict(CatalogConfig)`全量hash，旧测试要求privacy_class改变pin；取消权限后兼容标签仍使任务失效。93ac5a5已实现schema2显式有效投影，不再要求模型或用户维持这些标签；全roots/DB位置范围仍在01b处理，不能把本次核心修复等同完全路径解耦。

**实施：**先逐字段追踪 reader/resolver/adapter 的实际使用，形成 `effective_read_policy` 显式投影；只纳入会改变本次读取/来源准入的字段。检查外层 RootPolicy hash、export/read_request/批次 event hash，防止删一层仍间接绑定标签。privacy_class 不再当权限；steady 不再受 cohort 标签影响。旧 v1 下真实影响可见性的 cohort 仅留历史兼容，不能在 steady 内偷偷复活。

只保留已登记读取实际使用的catalog位置、根ID/位置/种类/排序/有效复用、准入kind/status/文件上限和实际metadata可见性；schema2中privacy/cohort/写目标、发现adapter/routes、未被reader执行的encoding/symlink等声明不作读取pin。后者仍由发现/配置/真实路径包含等所属层校验，不能用修改标签开放坏路径。来源字节、身份/期间/公开日/locator另由责任层验证，不把目录细节传给消费者。指纹解释版本明确升2.0，schema1旧pin不可证明等价时明确报错；不改旧费用或伪造旧pin。

**先写测试：**无效标签变化不使当前读取或同 run 恢复失效；真实路由/状态/格式/根或来源字节变化仍可检测；v2 CLI → FF → RF/StockWiki 结果一致。不能仅修改原测试的期望来证明实现正确。

**G2-01b / 后续仍pending：全catalog绑定范围仍过大。** 本次schema2已去掉无效字段，但仍hash全部roots/DB位置；`build_batch_events`及storage baseline将全局pin进入input identity。finished exact SourceRef只读实际注册副本，不做全局候选选择，新增无关root仍可能拒绝恢复。不能声称这一问题已解决。下一施工应区分查询选源的全局identity与单source/batch实际副本/准入identity，共用同一责任层；先写“新增无关根/迁DB后精确读取和终态复用不失效、有关副本/准入/字节变化仍拒绝”的公共反例，再同步reader→batch/storage guard→消费合同。MAIN定义版本与旧pin兼容，不能临时接受任意旧pin或重签旧费用；放在G2内、R2之前，不另设签收节点。

已核公开reader合同明确`reusable_for_filing=false`仍可query_local/preview/精确filing_reuse；该旧标签在legacy resolver选源里有作用，但不能作为已选SourceRef读取权限。实际旧工作目录错误为`BATCH_WORK_DIRECTORY_CONFLICT`。后续query投影也须按实际当前caller字段，不自动恢复旧复用门。

**01b独占范围与版本约定：**MAIN仅改`source_catalog/source_read_policy.py/source_reader.py`及实际reader manifest调用处，`automation/narrative_batch.py/narrative_batch_request.py/narrative_run_store.py`现有绑定/storage guard，既有`test_source_read_policy.py/test_source_version_reader.py/test_narrative_versioned_resume.py`及正式CLI恢复责任包。查询选源pin保持全局语义，exact SourceRef/batch改为独立、版本化的已选来源有效读取投影；源ID/SHA、当前身份/期间/公开日、当前真实准入/路径包含/open验证仍保留，不把物理DB位置/无关root作为精确来源事实。先定义新解释版本与绑定schema，保留schema2查询/旧final读；旧记录无法证明等价时明确解释不可复用，不补签旧final/费用。公开SourceRef/SourceExport v2/NarrativeRef形状不扩权限字段；RF/SW只核既有读pin消费合同，若确需改consumer则各独立checkout、本仓责任测试。不得一律忽略所有pin或复制路径给上层。

### G2-02 / P0：AUTO 普通故障仍转“人工阻塞”

**审计前实际缺陷；本次93ac5a5已改机器结果/版本恢复，精确CI37590638806全部步骤绿90秒。** 原registry把PARSER_INCOMPLETE、SOURCE_UNAVAILABLE、MODEL_NOT_CONFIGURED、LOCATOR_REPLAY_FAILED归人工阻塞，普通故障被误导为需放行。新任务不产生BLOCKED_HUMAN，历史enum可读；机器终态/有界真实IO重试、失败父任务收敛、handler1.1.0/AUTO5小binding和终态零writer恢复已集中验证，不要求人工签收。G2-13初始化深检仍独立pending。

**实施：**统一配置/输入缺失、可重试 I/O/限流、永久数据错误三类机器结果。配置/输入问题返回明确 reason 和需要修正的字段；修正后由正常事件/显式 retry 继续，不要求人工签收。可重试故障有界重试，坏 SHA/无效 locator 仍失败。新工作不产生 `blocked_human`；旧 enum/历史记录可读，不为改名字丢掉 usage、lease/outbox 或创建第二任务库。先查 handler 真实 outcome 和 Store 迁移，不能只改 UI 文案。

**完成条件：**选择→摘要→回放公共链中的上述错误均有准确终态与恢复方式；历史 blocked 记录可读，修正后的正常重试不重复扣费，kill/ACK 幂等保持。缺密钥不能因此冒充模型已调用，错误资料不能自动放行。

新 registry/handler 的错误语义变化须同步 handler_version；旧任务按既有 version 解码/明确恢复，不能同一个持久版本悄悄换含义。复用原 error/retry/lease Store，不新增泛化“权限中心”或人工重开任务接口。

**新增漏项与实施边界：**实际helper的catalog_unavailable应为IO_TRANSIENT有界重试；failed/historical blocked父任务的子任务必须进入DEPENDENCY_TERMINAL，不能永久PLANNED。重试同时尊重持久job.max_attempts。三narrative handler升1.1.0，timer保留1.0.0。prompt/handler升级后，旧终态run必须先验证冻结请求身份/真实来源/effective pin，再只读final，零materialize/worker/settle；不能套当前registry导致DAG冲突。只在既有AUTO narrative_runs增加nullable小binding_json，冻结不含密钥的request SHA、执行版本和source facts，旧无绑定或schema1 pin不可证明时明确需new run，原final/费用/未知账保留；非终态旧执行版本不支持时零模型拒绝，不添加人工重开许可。这属于G2A一次恢复责任测试，不另加签收或第二Store。

### G2-03 / P1：冻结 Pipeline 的 gate 家族还在

**冻结历史链，不是现行摘要 worker。** `config/pipeline_rules.yaml` 仍有 Gate0–5、approval_threshold、human_review；`scripts/gate_system/` 和 `full_pipeline.py` 保留旧评审/金融 writer。`writer_policy` 已将 full_pipeline 永久退休，所以不能把这些描述成正在阻断每份新文档。

**实施：**以 CodeGraph/公开 entrypoint/package/test import 为依据退休无当前生产消费者的整条配置/模块/控制面，而非留下“disabled approval”空壳。仅将仍有价值的来源解析反例迁到当前 parser/selector 包。删旧专属测试和 CI/mypy/hook 清单项；不重新启用投资 writer，也不把 writer freeze 当个人权限移除。历史说明用 Git 链接，不新复制大 archive。

已核具体写集：退休`config/pipeline_rules.yaml`和`scripts/gate_system/`旧评审实现/专属unit测试；`scripts/full_pipeline.py`保留仅stdlib退休stub及direct CLI exit78（含-S），不再import金融writer。`tests/integration/test_full_pipeline.py`实际测纯PDF提取，有现行价值，保留对应反例，不能按名字误删。

`deployment.generate_retirement_report`仍推荐旧scheduler/ingest，同步换成当前来源CLI；不把旧部署说明作为重启无限worker的授权。

### G2-04 / P1：公开旧维护命令和特例审查

**可调用工具残留。** CLI 仍提供 `archive-retired-evidence`、`prune-retired-evidence`、`focus-cleanup`、`duplicate-recycle`；后两者有 confirmation-token。旧审计“无生产 caller”没覆盖到公开 CLI，结论过宽。`dropbox_governance.inventory_dropbox` 仍有平安特例“eligible without reviewer-completed evidence”，实 caller 是可选 `tools/dropbox_governance_replay.py` 和旧测试，不是正常 reader。

**实施：**逐项对账 S5/S6 已完成的数据迁移和当前合法消费者。无再用需求的派生清理/archive/prune 整体退出公开 CLI；原件处置先变成只读报告或退休旧破坏入口，不能只去确认 token 后开放随意删 raw。真实维护仍需要的集合版本一致性用 machine CAS，取消人造签收与重复 smoke/强制全量备份。Dropbox 工具取消公司特例人工签收；身份不明仅报告不明，不能靠文件名升级 verified，不写外部 Dropbox。

**完成条件：**help/CLI 不再引导旧审批维护；旧入口给明确退休说明且零写；保留原件、来源版本/location；没有把来源质量错误改成通过。

**本次追加的入口/数据层细节：**archive/prune公开分支没传必需now，实际会TypeError，不能因CodeGraph无caller声称已退役。focus文件还在`code_identity.CORE_SOURCE_PATHS`，退休须同步指纹清单。`duplicate_cleanup`不能整模块删除：`list_groups`只读清单与`DuplicateCleanupJournal.read_all`仍被当前CLI/export历史审计消费；仅recycler/preview/token破坏链退出，`list_groups`两处查询改现有`catalog.reader`，避免只读命令初始化写Store。`eligible_for_recycle`改成inventory诊断，不引导raw删除。旧测试要求不存在的`scripts/source_catalog_control.ps1`是过期入口断言，应替换当前只读CLI/退休零写反例，不造回旧脚本。

### G2-05 / P1：RF 可选发布工具仍绑三个仓库和固定样本

**可选，不在当前日常 CI。** `tools/release_readiness.py` 仍要求三 repo HEAD、恰好 197 场景、backup 目录；`backup_readable` 实际写 `.read-probe`，`run_checks` 写 rollback_manifest，检查名称与效果不符。直接定位 sibling CWP SQLite 也违反抽象边界。

**实施：**发布检查只验证实际 RF 代码与本次确实消费的版本化证据；197/邻仓 HEAD 为历史统计诊断，邻仓缺席不阻 RF 独立开发。来源读取走正式接口，不直接查 CWP 内部库。只读检查零输出文件/原目录修改；rollback 文件只在确实执行有状态发布时按需保存，不强制备份目录和全量恢复演练。`run_coverage_gates.py` 的指标阈值改报告，行为错误仍失败。旧人工 release auth 已退出，不能重新添另一签收。

**先写测试：**无 sibling 仓/无 backup、样本数量变化、check-only 无写仍可检查；消费的证据 bytes 不符仍失败。只在 RF 隔离目录实施，三个 owner 日志不动，不跨仓写。

完整同步写集还包括`.coveragerc`、`tools/final_ratchet.py`和`tools/session_checklist.md`：final_ratchet仍驱动全tests/900秒、84% overall和8模块40–80%以及固定mypy错误数69；checklist仍要求每会话全测/真实E2E/安装全MATCH并apply、CWPconfig等HEAD/checkout。全改为相关大节点和owner保护，不因旧文案恢复这些要求。现日常`quality.yml→pre_push_gate.py`单Python/11精选包已合理，保留。用户后续已放松缺hash闭环要求：缺hash仅诊断，提供hash而实际不符仍失败，本卡不能恢复早期强制所有路径有hash规则。

**本次并行复核补漏：**`tools/release_checklist.py`还重复全测/mutation/registry/安装，固定EXPECTED_RED且只匹配FAILED文字，返回2可误绿；一并收敛真退出码。旧质量工具AST读取coverage常量，保留`fail_under=0/PER_MODULE_MINIMUM={}`兼容面；`scan_hardcode/scan_legacy/scan_encoding`有真实caller，不按名字删API。完整实现和集中责任包见[RF单卡](harness_lanes/g2_revenue_forecast_optional_tools.md)，此补漏不扩写assurance/业务或安装目录。

### G2-06 / P0-B：StockWiki 日常全套与数字门仍保留

**现行CI脚本和AGENTS均生效；hook本身没有pytest。** `scripts/check_all.sh`仍被CI调用，全pytest+73% overall/40% ui硬门；AGENTS仍要求Before commit。hook的validate-framework间接执行600/1000行硬门，注释却称warning；`pyproject.toml`另有fail_under=73。必须统一清理，单删check_all参数会漏底层配置。上次外线只消除了重复pytest。

**实施：**commit只运行便宜静态检查，不新增pytest hook；真实行为由短CI/相关大节点验收，全套真实工作区 E2E 只在相关大节点/显式运行一次。覆盖率、体量变成诊断，framework 的实际配置/模块一致性错误继续失败。同步 AGENTS/脚本/文档，不留“脚本精简但接手模型每 commit 必须全测”的冲突。投资研究 accepted/rejected 属 StockWiki 业务状态，本卡不取消投资结论语义。

**验收：**hook/docs 不触发全套、指标低于旧阈值本身不失败；一个真实责任测试故意失败时整体 exit 非零。一次相关来源 CLI/E2E 节点即可，不因小改动重复 935 项。

推荐一份`scripts/checks.py`供CI与sh薄包装共用，默认Ruff/真实framework一致性/identity和SourceExport/NarrativeReader精选行为；全真实工作区和coverage显式大节点。责任复用`test_check_all_script.py`当前shim、framework反例、identity/source/narrative CLI包；`test_e2e_real_workspace.py`保留真实数据行为，体量仅诊断。`test_data_contract.py`是业务成熟度，与投资accepted/rejected一起保留，移到相关大节点，不能当权限删掉。

**具体同步写集：**StockWiki `.github/workflows/ci.yml`、`.pre-commit-config.yaml`、`pyproject.toml`、`AGENTS.md`、`scripts/check_all.sh`及新薄编排，`stockwiki/framework_validators_okf.py`现600/1000体量硬门与`tests/test_framework_validation.py/tests/test_check_all_script.py`；`stockwiki/cli.py`只在现validate-framework返回诊断所需时修改，不改业务研究writer。当前没有远端，本地主线发布需准确表述，不能假造远端CI。

### G2-07 / P1：CWP 工程检查与退休清单同步

**现行小门与可选旧工具混合。** host-assumption regex 曾误拒测试中故意的 `C:/absolute.pdf`；mypy/hook/CI 仍包含旧 canary/维护模块，另有 optional coverage/complexity ratchet 历史测试。

**实施：**保留真正可移植行为的责任测试，将误伤合法反例/注释的字符串扫描收敛为诊断或语法范围检查，不增加 allowlist 签收表；同一退休模块在 package、tests、hook、CI、pre-push 清单一起移除。覆盖率/复杂度数值报告化，当前快 CI 维持单 Python，不恢复全合同/多平台矩阵。Ruff、实际公开 DTO 类型、相关配置体检和密钥泄露检查保留，不重复全仓无关检查。

**本次实际补漏：**FC701历史snapshot测试误标schema2（现在定义steady），改为真实schema1保留原v2无bridge/错误断言；禁止所有新模块读取acquisition字符串的冻结owner AST门误拒当前合法canonical登记，还在源码目录临时写evil_probe。整条AST所有者名单/两个扫描测试退休，来源身份/SHA/retired/历史可见性行为反例保留；不是加一个允许owner名字凑绿。72项行为绿、2项上述历史失败定位后，剩余FC701五项真实行为全部绿。源码不因capture这个合法字段名被拒绝。

**具体同步写集：**CWP `pyproject.toml`现console入口、`src/company_wiki/source_catalog/cli.py/code_identity.py`、`.pre-commit-config.yaml`、`.github/workflows/ci.yml`、`.githooks/pre-push`、`tools/pre_push_gate.py`及其实际退休模块清单测试；源职责约束/CLI合同只改被退休的入口，不删除真身份/SHA/Locator行为。CI/commit/push各清单同步移除已退休模块，source源码指纹清单同时更新，避免删源码后整个新batch无法执行。保留当前快CI和便宜静态，N4历史A/B/C已验收，不重新跑。

### G2-08 / P1：FF v1 兼容与安装入口最终收敛

**v2 正确；v1 残留需 caller 审计。** 旧 `--allow-download` 与 request authorization 兼容仍在，不能算到 v2 单意图上。两份安装技能已推荐 v2，但 legacy 附录和摘要会让较弱模型反复询问授权。

**实施：**查 RF/其他正式 caller 的 schema；无合法新下载 caller 则退休 v1 下载路由，必要只读复用留薄兼容，不继续支持两套审批协议。库和 CLI 使用同一个 intent，不二次 ask。同步 repo skill 与两个安装副本的实际脚本/文档，仅从对应已发布版本安装；哈希差异先解释，不覆盖用户密钥/配置。当前持续授权作为上下文使用，`reuse_only` 仍零网络；限时/字节/费用不是人工签收。

安装位置为`C:/Users/郑曾波/.agents/skills/filing-fetch`和`C:/Users/郑曾波/.codex/skills/filing-fetch`：仅同步已发布且本次改过的SKILL.md、scripts/fetch_filing.py/filing_contracts.py及直接依赖的reference文件；实际文件清单先核安装入口，未改文件/密钥/用户配置保留。RF安装副本若确有调用本次可选工具的正式caller，同样只同步必要文件，不恢复“全MATCH才可用”的门。

**验收：**正式 FF→ET→CWP 离线链走三个真实 CLI、复用零 provider、语言/SHA/清理正确；相同 intent 的库与 CLI 一致，未来公开和预算拒绝仍明确。使用既有链测试入口，不新增十套 request contract。

### G2-09 / 已核能力边界：ET、provider 和外发文案

ET `ProviderSettings` 仍称 Reviewed runtime availability，但实际是单运行能力配置；没有发现新的人工 receipt。`download_authorized` 是一次请求网络意图。FMP 402、缺凭证、disabled provider 是现实能力，不能为“简化”冒充可以付费下载。只清理误导文案/重复问答；已有 TXT 在 provider 关闭、无翻译 LLM 凭证时也应正常零 HTTP 复用。MiniMax/MiMo/DeepSeek 必须继续遵守已配置模型与预算，持续外发授权不意味着无限预算。

StockInfoDLSimple 的 provider host、include/exclude 是来源发现和过滤，不是个人权限。MeetingConverter 当前快 CI 未见新人工审批门。此两仓无明确问题就不强加施工；StockInfoDLSimple dirty 不由本卡顺手清除。Dayu/IQS 无写。

### G2-10 / P0-B：StockQA CI、本地、hook和pytest默认不一致

**远端正在生效。** CI 两 Python、独立 type/lint/black/bandit/radon/build/report，多次安装同类依赖；coverage 门 87%，本地 run_ci 却 60%。本地 `command | tee` 没有 pipefail，会吞失败退出码；pylint `--exit-zero` 却称“质量通过”。这能解释一类本地绿/远端红，不能假称是此前全部 CI 失败的唯一根因。

**实施：**一份短检查定义供本地/CI 共用；保留实际行为、类型/格式错误，coverage/pylint/radon 分数仅诊断。日常单受支持 Python，额外兼容测试显式大节点；依赖安装一次，不因报告/格式再建六 job。脚本真实失败退出码贯通，成功报告不能来自 tee；报告准确区分检测通过与指标统计。不削弱真实 failed test，不加新的人工质量签收。

**先写测试：**伪 pytest/type/format 返回失败时本地与 CI 共用入口非零，tee 不掩盖；低覆盖率本身成功，实际反例失败；无密钥离线执行短责任包。独立测试目录最终恢复原样。

**新增完整写集：**`run_ci.bat`、`.pre-commit-config.yaml`、`pyproject.toml`与dev工具版本必须同时收敛。现9个实际runner/8次准备，hook always_run pytest和联网pip-audit，Black24.10对CI26、mypy strict不一致、pylint≥9阻断对本地exit-zero虚称≥8；pytest默认生成XML/HTML/coverage，轻测试也增文件。一份Python短编排供sh/bat/CI共用，默认pytest无覆盖率、提交只便宜静态、网络审计显式大节点；真实失败返回码保留。现build smoke只import空src包，换真实公开CLI/module导入。离线models/config/basic_runner/main行为和quick_scan/Q07预算恢复反例保留，live/收费默认关闭。基线必须从最新6a9ff138再核，不覆盖7个untracked资料。

**本次并行复核补漏：**实际包装路径是`scripts/run_ci.sh/bat`，另security/release/docs三个workflow重复每push巡检/固定70%和8分门/无关代码触发文档部署，必须同步，不能只改ci.yml。现有显式网络审计保留准确报告/真实异常，发布权限不变、本卡不发布tag/文档；真实CLI import因logger造logs，使用自己的TemporaryDirectory/PYTHONPATH隔离，不修改业务logger。完整写集和真退出码E2E见[StockQA单卡](harness_lanes/g2_stockqa_engineering_checks.md)。

### G2-11 / P0：摘要质量标记由模型重复维护并硬校验

**审计前实际状态门；单处程序投影本次93ac5a5已发布，精确CI37590638806全部步骤绿90秒。** 原_validate_claim_review_status要求模型重复维护claim.needs_review/draft.status，矛盾可能丢有效内容。现在由project_summary_quality根据真实引用质量/角色/不确定性/局部恢复诊断推导；旧字段仅兼容，真实SHA/locator/language/未知引用/角色错误仍拒绝。148责任项与配置真实loopback/resume已绿，不重复付费模型。

**实施：**解析后统一根据当前 evidence quality/replay 与保留claims推导质量诊断/草稿状态，保留模型 uncertainty 作为内容诊断；不因可确定的标签不一致拒绝有效内容。schema/来源SHA/原语言/引用ID/发言角色/真实locator仍由自动反例严格验证；locator确实无法回放的内容仍剔除，不靠改成needs_review放过坏引用。质量状态需要对外展示时由单处投影生成，旧字段兼容读，不添加review receipt。

**先写测试：**相同有效claim/evidence只改变模型review标签，保留内容、引用和原语言一致，程序质量投影一致；坏locator、未知evidence、问题冒充公司陈述仍不能入final；同run恢复不再因冗余状态变化重复付费。只用离线合法响应/已有真实响应做回归，不为测试这个状态多调用模型。

公开兼容字段可以保留，最终值由单处投影确定；若实际输出合同/prompt/handler解释变化，同步现有版本字段与消费者契约测试，不能重签历史final、更改旧费用或把整个provider响应重存一份。

### G2-12 / P0-B：CWP latest下载仍分叉到旧gap签收协议

**仍在执行，不能归入仅FF v1历史。** CWP exact `ensure --allow-download`已用单意图和AcquisitionBudget、不要求DownloadAuthorization；但latest_as_of即使允许下载也无条件只回GAP。公开`close-gap`强制binding-file、runtime snapshot/plan/policy hash/expiry/accessions，新默认无snapshot的steady库还会被`no_runtime_policy`拒绝。FF v2明确不走旧close-gap，收到GAP只返回，故latest缺件不能自动补齐。已核真实CLI help与实际类调用，非搜索单词推断。

旧receipt只是无签名的确定性摘要；remote_size只能估计，读取中的AcquisitionBudget才有真正限额。一条旧latest流程可重复四次metadata discovery，TTL还进入事务锁键；这既增加多余门，也浪费查询。`missing_download_authorization`等有些仅是观测字典标签，无当前执行路径，不能只删标签冒称已修。HTTP bearer脱敏继续保留。

**统一接口：**复用SourceRequest一次allow_download/FF filing_intent和现有AcquisitionBudget，不加新授权DTO。reuse_only的exact纯复用、latest有界发现；fetch_if_missing在同一服务最多补齐一个明确目标。latest的GAP仅内部发现结果，按公司/市场/kind/期次/as-of/provider/accession选目标，真正歧义零下载。锁键由规范请求/目标生成、不含签收TTL；锁等待/发现/读取共用剩余deadline/累计bytes/cost，二次subprocess和重试不能重置。保留single-flight、锁内本地再解析、暂存验真、唯一canonical writer/journal/最终真实再解析，不重复四次发现。

**旧入口迁移：**close-gap只薄转发到同一服务；旧binding含明确accession或更低上限时仍约束请求范围，忽略旧expiry/plan/policy“签收”字段，不扩用户范围。authorization.py退休或仅旧输入转换，不再创建receipt/临时binding。FF v1/v2都调用同一ensure，保留v2 pathless SourceRef形状。当前根/config/实际bytes由程序现场核验，不要求用户保存/刷新hash文件。用户持续授权继续适用，限额和供应商能力仍真实。

**完整独占写集：**MAIN的CWP`acquisition.py/acquisition_service.py/close_gap.py/authorization.py/cli.py/observability.py`，必要时`source_operation.py/lock.py`及OPERATIONS/当前合同说明；FF独立checkout仅`scripts/fetch_filing.py/filing_contracts.py`、SKILL/reference ownership和对应测试，发布后再同步安装副本。无Dayu/IQS/生产配置/raw改动，公共SourceRequest request_id算法不必变。

**先写反例并并入G2B一次联调：**新steady无snapshot/binding仍可latest明确下载一次，再请求复用零fetch；旧expired/stale签收不影响相同范围有效请求；不同旧TTL并发仍最多一fetch/canonical。无intent/真实歧义/错身份期次/未来公开零fetch；假SHA/PDF、越界、未计量响应、实际超byte/time/cost不入库；provider unavailable/提交或最终再解析失败不能报completed。真实离线subprocess核FF v1/v2→ET/CWP一致、预算不重置、pathless与计数保留。复用close_gap FC801/804、download_authorization/gap_plan/acquisition/canonical_writer/adapter_process/ensure_paused/source_operation_v2及FF FC802/S3/v2责任包；删除签收本身的旧期待，保留资源/身份/SHA/幂等反例。不为此重复paid HTTP。

### G2-13 / P0：构造Store暗含整库深检和全量补种

**当前：b202d07已正常推送；精确CI37597724658全步骤GREEN/79秒。** [实际验收](harness_lanes/results/g2_store_initialization_acceptance_2026-10-07.json)：132初始责任项、54最终责任/两CLI；普通构造0深检、显式/new/升级各一轮，Catalog当前0DDL/seed，真实升级原子回滚；账目按当前run校验，不靠整库体检避免隐式转换。01b仍pending，不代表whole G2A完成。以下为原问题和实施合同。

**实际调用链存在系统性重复扫描；次数是结构审计，不冒称实测生产耗时。** 当前v5库每次`AutomationStore.__init__→migrate_database→_validate_current_readonly→_require_expected_structure`做一轮`PRAGMA integrity_check/foreign_key_check`；`NarrativeRunStore.__init__→validate_database`做两轮，因为后者重复检查。完成run的零worker恢复、每个worker启动/重启均构造两种Store，仍有三轮整库检查；失败CLI新构造RunStore又两轮。同一RunStore的`budget_snapshot`只是按run_id查询，没有每次深检，不能误报。

CatalogStore当前版本每次`_initialize→_apply_additive_migrations→_seed_fingerprint_state`还执行DDL探测与`INSERT…SELECT documents JOIN sources WHERE NOT EXISTS`全库补种。只读SourceReader已避开writer，但正常写Store仍会随全库规模增长。这与已修复WAL争锁时间让步是两个问题，不能拿WAL绿灯声称本项完成。

**实施接口与写集：**同一AUTO/来源库中拆开轻量current-schema验证与显式深检。构造只查版本、必要表/列/键/singleton，不扫描业务数据，不宣称`integrity_ok=true`；新建、真实迁移提交前、显式`validate_database`大节点各执行一次深检，消除内部重复。旧/未来版本和非SQLite、必要结构损坏仍明确拒绝，迁移失败原子回滚；实际业务查询异常和FK执行仍保留。复用`automation/migrations.py`的结构函数、`store.py`及`narrative_run_store.py`构造入口，不增加健康服务、第二Store、缓存许可或签收文件。

CatalogStore已是当前schema时不DDL/全库seed，未知版本在DDL前拒绝；seed仅新建/真实升级一次。现`select_fingerprint_batch`已将无state文档视为pending、`record_fingerprint_outcome`已UPSERT，优先沿用此责任；如新登记需要初始化，只在对应文档事务内做，不补扫全库。独占写集为`source_catalog/store.py`及确有必要的fingerprint责任文件；不能将优化转成全库metadata重写。

**TDD并入同一G2A：**SQL trace证明current库重复构造、预算、终态恢复/worker factory不执行整库PRAGMA/DDL/seed；显式深检一轮，新建/真实迁移一次且损坏/FK孤儿被诊断，失败回滚。轻入口不虚报完整健康；真实选中资料/账目读取异常不得变成零费用/成功。原run scope、lease/generation、未知账、CAS负例保留；无state新文档仍可选择并保存结果。使用已有migrations/store/atomic/run-store责任包及一条实际CLI恢复，不每日全库check，不增加审查节点。

显式深检直接沿用`company_wiki.automation.migrations.validate_database(Path)`公共API及既有迁移测试，不另造doctor服务。当前AUTO CLI doctor只是模块可导入诊断，不能冒称已做DB完整性检查；调用方报告必须区分结构检查与实际深检。

## 4. 实施次序、所有权和接口

MAIN 是唯一集成与生产变更负责人。此表是施工顺序，不是新增逐组签收。

| 顺序 | 工作 | 输出/责任 | 状态 |
|---|---|---|---|
| 1 | G2-00 steady现场迁移/默认新库收敛 | 当前policy、旧小snapshot、真实读和16断言 | 现场complete；默认核心93ac5a5已推，精确CI37590638806全部步骤绿90秒 |
| 2 | G2-01 effective read pin + G2-02 AUTO机器错误/版本恢复 + G2-11派生质量状态 | 版本化读取语义、同AUTO单库恢复、单处质量诊断 | 核心责任/E2E已收口、93ac5a5已推，精确CI37590638806全部步骤绿90秒；不等于完整A |
| 3 | G2-13日常Store轻初始化 → G2-01b精确来源scoped pin | 去除隐含整库检查/补种及无关root对精确批次的阻断 | 13已发布/精确CI绿，01b仍pending/P0；先于R2，沿用同一G2A集中节点 |
| 4 | G2-06 StockWiki/G2-10 StockQA日常工程门 + G2-12 CWP/FF统一latest单请求 | 各仓独占目录，MAIN接线；共享ensure事务/唯一intent、工具/CI/hook/默认配置同步 | P0-B；SW/StockQA用户已分派待交接；MAIN独占12 |
| 5 | G2-03/04/07 CWP旧家族/公开维护/检查清单、G2-05 RF可选工具、G2-08安装/v1、G2-09能力文案 | CLI/import/package/清单/安装及指导同步；不启用raw破坏入口 | P1；RF新卡用户已分派待交接，其余由MAIN按P0/P0-B后续；不恢复旧签收 |
| 大节点 A | CWP最终写集完成后的当前链集中责任/E2E | isolated真实IR PDF/英文TXT；read/有限登记/零模型skip/loopback；现场小对照 | pending；核心子集先收口发布，复用已绿202/历史节点，不等同整个A完成 |
| 大节点 B | 三仓离线链 + 当前消费者 + 发布 | FF→ET→CWP、RF/SW 读取；每仓对应代码 CI；保护/临时根清理 | pending；不重复付费模型 |
| 6 | 回 R2 metadata/有限登记 → R3 → R4 → R5 | 原目标全部待办继续；G2 非缩减目标 | pending |

跨仓公共接口继续为SourceRef/SourceExport v2、NarrativeRef、FF单intent和ET TXT，不以reviewer DTO、路径或共享可变DB接线。MAIN独占总PWF/生产/合入；本次三个内部子任务仅在已划分互不重叠的CWP文件实现或外仓只读调查，不代用户新建harness任务。外仓后续只在各自独立checkout施工，集成前复核最新HEAD/status并保留owner资料。

施工优先顺序统一为13→01b→06/10和12→其余P1。A在本仓最终写集完成时集中验收，B在跨仓接线完成时集中验收；这些节点不是每组都跑全套。核心已发布责任包后续按实际影响补反例，不再重跑已绿长包。

## 5. 两个大节点的测试包和验收边界

实施先写行为反例，再改代码；每个 helper 不做独立签收。新测试按职责放置：

- `tests/unit/test_source_read_policy.py`（新计划文件；现有契约包在 `tests/contract/test_source_read_policy.py`）：投影纯函数、无效标签稳定、有效准入变化、版本化 pin。
- `tests/unit/test_automation_worker.py`（含 classify_outcome/retry 现有反例）、`test_automation_models.py`、`test_automation_store_atomic.py`：新故障分类、历史解码、有限重试、不能以成功掩盖无效来源；仅修改影响的责任集合，不猜不存在的 retry 测试文件。
- `tests/contract/test_gate_simplification_current_entrypoints.py`（待新增）：当前 CLI/help、旧 writer 退出、check-only 无写、默认 steady、不再要求人工 receipt。
- `tests/unit/test_narrative_partial_summary.py`（现有）：真实有效内容不因重复review标签矛盾丢弃，程序统一状态；坏locator/未知引用/发言角色错误仍拒绝，保留原R6局部恢复合同。
- `tests/integration/test_gate_simplification_source_chain.py`（待新增）：独立短根用真实 S07 PDF 和 S09 TXT，走实际登记/read/export、零模型 skip、本地 loopback 有界子进程；真实定位/SHA、坏字节/未来公开拒绝，只有选中组改变。跨仓链复用现有正式脚本，不再另造全功能链。
- RF/SW/StockQA 新工程入口测试各放本仓 tests 的独占责任模块；外部返回码用 stub 验证，再在大节点一次实跑相关行为集合。无需逐小模块全 coverage。

测试资料仅在新的独立测试目录；运行前记录 absent/原清单，结束 finally 删除新复制/下载/SQLite/模型工作目录，恢复原状。真实 paid provider POST **0**；不全文恢复备份，不将生产原件/owner 配置当夹具。现场 policy 迁移是正式操作，以小配置 CAS/断言/SHA 对照验收，不在生产造坏记录。

大节点 A 只集中跑修改的责任集合和公共 E2E；已发布融资、budget、kill/ACK 等节点不因本清理全重跑，只有其实际调用合同被修改才加相应反例。大节点 B 对真正变化的仓跑短 CI 和离线集成，纯 PWF/收据提交不触发新代码 CI。失败就定位具体责任，不能扩大门禁或改预期凑绿。

## 6. 应保留的自动正确性（不再包装成权限）

1. 原件不丢、真实 open 字节 SHA、来源版本/撤回事实；不能将任意输入自动标 verified。
2. 公司/证券/期间/公开日和 as-of；晚下载旧公开资料可用，未来公开拒绝。
3. evidence locator 真实回放、原语言和来源支持；上游只供应资料，不写投资结论。
4. 目录包含/写入归属、跨仓只读、外部 Dayu 零改动；同一用户不等于自动跨项目写。
5. 显式有限批次的字节/时间/token/费用和未知账保留；lease/generation/幂等/outbox 单库恢复。
6. 实际 schema/类型/语法/相关配置和密钥泄露检查；数字覆盖率/复杂度不是行为正确性的替代。

不保留人造授权文件、review receipt、签名/信任 TTL、固定样本数、无关 repo HEAD、必须备份目录、每次 commit 全套检查。保留项均需对应真实失败反例；没有实际当前责任的控制直接退休。

## Next Step

**本次审计与核心93ac5a5已正常推送、精确CI37590638806全部步骤绿90秒。** 全G2A还含Store轻初始化/scoped pin/旧家族清理，不能用核心子集代替。目标服务paused；明确恢复后先G2-13/P0轻初始化TDD→01b→P0-B两仓日常门和CWP/FF latest单请求→P1家族/工程清单→集中G2A/B→R2。不重跑已绿核心长包、不自动启动付费批次，不把审计/核心修复冒称全面完成。
