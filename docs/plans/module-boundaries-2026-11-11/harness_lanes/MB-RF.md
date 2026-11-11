# MB-RF — 独立施工卡

## A0：收敛旧release差额与未提交材料（2026-11-11新增）

先读总计划 `reconciliation.md` 和 `review/repo_reconciliation_20261111/research_review.md` §3/7。96个refs并非96项待并；旧Dashboard/B31/B34/B35/B37家族合成一个参考顶点 `28d646d306e8f0b5f90d402e204676cf97d2b5a1`。不要逐祖先重复合并、整树覆盖main或复制旧安装产物。当前main的durable job/concurrency/recovery、RF实际来源端口和报告入册必须保留。

最小候选19个产品路径：4个与main相同；9个同名有变化，逐hunk适配；6个main缺失：`scripts/report_catalog_compare.py`、`report_catalog_compare_cli.py`、`report_catalog_scope_binding.py`、`report_catalog_subject_resolver.py`、`report_catalog_verified_compare.py`、`report_catalog_verified_compare_cli.py`。完整19路径及历史handoff在报告§3.2。写集合相应加入这些目录/身份/compare/scope/publication owner模块、薄CLI和对应测试，不扩成旧release整仓。

1. A先为当前必需公开compare/scope/publication合同建立失败或已满足证据。B用RF自身owner实现，旧CWP SQLite/private layout依赖不能随并线复活；StockWiki仅通过公开DTO/CLI通讯。缺StockWiki实现时用冻结公开fixture推进RF本地，ROOT负责真实组合，RF作者不能改SW。
2. 当前回归入口：`tests/test_report_catalog_rf_job_import.py`、`test_rf_job_concurrency.py`、`test_rf_job_recovery.py`、`test_rf_job_boundary_regression.py`、`test_decoupled_source_port.py`、`test_d4_narrative_consumption_port.py`。参考分支用例：`tests/b37_scope_binding/`、`b37_publication_sources/`、`b34_publication/`、`b35_lineage/` 和相应compare tests。仅迁移仍属当前合同的反例，集中验证，不重跑预测。
3. 旧job-facade大包已由main更新替代，不再整体合。`rf-input-prep-01`的118个研究资料不是runtime改进，旧W04 authoring草稿不能覆盖当前SKILL/可选attestation；这些回父研究计划。
4. ROOT已归档4份assurance生成物原字节并restore，主工区tracked已清。日志内旧canary/bound-stale失败保留，归本卡旧分发/运行入口退役核对，不因清理日志宣称失败修好了。
5. `rf-impl`的238 staged中233与main同blob，余5是独有PWF/审计；先归档5项，后给ROOT精确核销清单。4个含msft原文的Temp工区保留。`3b00b938`原型有codex/revenue-source-reader引用，不建第二reader；先核销合同差额再退役。release路径仍被Dashboard配置引用，ROOT组合前不删除。

A0和本卡原core/report/分发边界由同一RF作者顺序推进；验收后ROOT并main，不增加人工许可。StockWiki C38/B03归ROOT自己的SW工作，不是RF作者写集合。

## 任务定位与唯一工区

- 原仓：`C:/Users/郑曾波/Projects/revenue-forecast`；基线 `b005a179`；目标主线 `main`。
- 新工区：`C:/Users/郑曾波/Projects/mb11-rf`；分支 `codex/mb11-rf`。本卡尚未开工，不把准备好的卡称为已派发。
- 本仓PWF：`docs/plans/mb11-rf-2026-11-11/`。先建立 task_plan.md、findings.md、progress.md，记录真实基线与工作量；本卡及公共接口说明可复制到该目录inputs。
- 总控计划：`C:/Users/郑曾波/Projects/company-wiki/docs/plans/module-boundaries-2026-11-11/`。开工只需读本卡、该目录 interfaces.md、acceptance.md、runtime_verification.md 和本仓AGENTS；无需回放旧聊天/全部历史PWF。

```powershell
git -C 'C:/Users/郑曾波/Projects/revenue-forecast' worktree add -b codex/mb11-rf 'C:/Users/郑曾波/Projects/mb11-rf' b005a179
```

若工区/分支已存在，先只读核归属；不能 reset、清别人的目录或接管未知工作区。可以用新的唯一后缀并记录。用仓库实际可用的Python/离线依赖；不要重新抓取原件或部署到全局技能目录。

## 全卡共用完成规则

- 先列本仓实际交付runtime的活动入口、逻辑模块、公开面、状态owner和依赖方向；包含兼容/退休分类。确认缺口只是入口，不是允许忽略其他已登记模块。发现同根绕行在本卡owner内归并修复，新增业务需求交父计划。
- 保留现有公开协议；各模块只写自己代码和状态。公开协议真需要改时先把失败例和最小兼容方案交ROOT协调，继续其余独立工作；不擅自改邻仓。
- A写行为/隔离测试 → B修owner根因 → C模块验收。A/B/C是工程步骤，完成A即可继续B/C，不需ROOT或用户逐步批准。
- 接口负例应体现实际能力/依赖错误；fixture/缺依赖/沙箱权限失败不冒作产品RED。已有边界通过就保留，不为凑改动重写。
- 只在模块最终交付前调用独立审查agent，审完整度、架构归属、回归和所有新增测试。修复所有本卡可行动问题并复核，才交付；非本范围新发现明确列给ROOT。
- 测试用新临时目录，恢复初始状态；生产原件/配置/既有WIP不动。只运行受影响测试与必要最终包级CI，不每小步重跑全量，不删断言换绿。
- 提交并推送自己的交付分支（存在remote时）；不自行合并主线、不修改ROOT总PWF。交付本仓PWF下 handoff.md/json、独审报告、测试/恢复证据索引，格式见总计划handoff_contract.md。

## 目标与已确认现状

保留pathless来源准备、native模型、report catalog与jobs的既有公开接口。独立报告 `review/research_architecture.md` 已确认R-01旧canary直读CWP私库且随scripts分发，R-03 report依赖core聚合而core运行时回调report；R-02是历史研究admission对旧执行包/代码布局的表示耦合。

## 写入范围

`scripts/processed_artifact_canary.py`、`installation_manifest.py`、`revenue_core.py`、`revenue_report.py`、`revenue_forecast.py`及其已有leaf module的最小依赖调整；`scripts/report_catalog_research*.py`只做历史profile隔离/公开receipt适配；source_preparation/reader/client模块仅当公开隔离RED证明缺陷才改。相应 `tests/test_single_owner_guard.py`、`test_architecture_dependency_uses.py`、`test_golden_behavior_lock.py`、`test_decoupled_source_port.py`、report catalog/job/installation测试与新增`tests/test_module_boundary_closure.py`；references和本仓PWF可写。

不写4个既有 `assurance/runs/{daily_alert.jsonl,monthly_manifest.json,weekly_alert.jsonl,weekly_manifest.json}`，不改其他owner仓、Dashboard release worktree、生产报告/registry、全局skills。RF内部所有这些任务由同一harness顺序完成，不能再分给两个同时修改core或installation_manifest的作者。

## A/B/C及TDD

1. **交付闭包**：先测试正式runtime包的活动入口无需CWP SQLite/schema/DAG知识。追踪canary调用者，未使用则移出交付/明确退休；实际仍需要的诊断改消费既有public projection。旧审查资料保留。禁止为了旧工具新造CWP SQL代理。
2. **计算/研究/报告职责**：给已有pure model/calculation leaf建立无网络/无写入替身环境；report直接消费现有leaf API，core编排调用report。先锁相同frozen input的数值、schema、错误与receipt语义；保持旧core re-export兼容。formal注册属于runtime，修正文档的pure/zero-IO误称，不搬进计算层。
3. **来源边界**：无CWP/FF Python包和不可读的上游DB时，配置public commands仍能source prepare/read并保持原文引用；失败不会退回扫描邻仓目录。只通过public fixture观察调用次数/错误，不能patch上游私有helper。
4. **历史admission**：旧B34 profile作为显式版本兼容reader保留，仍按它既有retained绝对路径合同读取；不要求旧run整体可搬迁。先检查当前profile分发和实际调用，用旧profile兼容正例、缺失必需证据反例及默认路径无CWP内部布局依赖锁合同。可移动测试仅对当前已声明可移植的公开artifact/新fixture，不改旧审查字节/身份或重签旧数据。若布局要求仅属于显式历史profile，证明默认路径不引用即可关闭；不为本卡新建Audit协议。确需新wire时把最小方案交ROOT协调。
5. **作业/目录**：code root与data root分开；只读不建库，恢复不重新采集/计算已有完成阶段。已有公开hash/数值/单位的owner校验保留；可选日志/registry审计不作许可。
6. **安装和独审**：使用当前RF canonical skill/runtime安装机制，临时目标和空cwd，验证来源/计算/报告/目录/job入口；不直接同步全局技能。最后集中独审、修完并交付。

## 证明库

```powershell
python -B -m pytest tests/test_single_owner_guard.py tests/test_architecture_dependency_uses.py tests/test_decoupled_source_port.py tests/test_golden_behavior_lock.py tests/test_model_registry_contract.py tests/test_rf_job_boundary_regression.py tests/test_rf_job_recovery.py tests/test_report_catalog_rf_job_import.py -q -p no:cacheprovider
python -B -m pytest tests/test_module_boundary_closure.py -q -p no:cacheprovider
```

实际文件名开工核对后记入PWF；不得把文件找不到当产品失败。Dashboard比较功能在本卡A0已明确为RF仓内差额接收范围，按指定19路径逐合同移植，不复制外部owner工区。本卡不重跑公司预测、不改假设/模型算法或给任何公司打补丁。

## 出口

RF模型/研究leaf、runtime副作用、report/catalog/jobs和source adapters边界清楚；已分发越层工具消失或公开委托；历史profile隔离有证据；安装、兼容与公开替代端口通过，独审无未修本卡问题。
