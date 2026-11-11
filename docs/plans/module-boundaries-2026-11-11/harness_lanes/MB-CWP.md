# MB-CWP — 独立施工卡

## A0：先接回历史成果，再完成本卡边界（2026-11-11新增）

用户已授权逐项清理/并线。本卡仍只有一个CWP作者；不另开重叠reader/config工作线。先读总计划 `reconciliation.md` 与 `review/repo_reconciliation_20261111/cwp_review.md` §3/5/6。本卡未开工；下列是有限接收清单，不表示架构已完成。

ROOT已完成：source-facts 11个tracked+5个untracked源码副本精确核销、4个pytest目录和已吸收stash清理、W13历史最终独审/交接补齐。不要重新执行旧W13代码或重复恢复source-facts。当前已有stream/parser owner端口和预算语义必须保留。

| 子项 | 输入/具体任务 | 通过或核销条件 |
|---|---|---|
| T-READ | `3199adab` / X-C04历史CLI；现有 `stream_version`、parser sink、读取预算。Dashboard的24条真实stream测试目前缺配置owner入口，不能用fake代替。 | 当前公开port之上提供确有消费者的兼容CLI；取消/关闭/非primary admission/真实字节验真遵循当前owner。若CLI不再需要，必须给消费者已迁移证据。 |
| T-CANON | `62602102a` 的canonical browser/CN issuer及calendar反例，按报告逐路径移植 | 不新增第二身份库/下载预算；当前公共入口及ROOT精确组合通过。 |
| T-B33 | `dc837a21f` readiness/legacy source link/recovery，历史交付独审仍未完 | 先重放候选测试，用现有restore/source接口承接；本卡独审关闭对应问题，不对生产恢复。 |
| T-B34 | `29b562dac` diagnostic/IPO cover，对照当前local_reconcile多轮owner修复 | 不带回固定8条诊断帽或旧强制前页限制；有证据的cover可用，冲突/未绑定不冒事实。 |
| T-N4 | `2b5bec914` 的CN quarterly/IR等独有反例 | 映射现行source material/stage语义；已绿则核销旧实现，不能恢复旧eligibility策略。 |
| T-CONFIG/W04 | 旧M3的config.py、narrative_batch_configured.py、test_narrative_model_config.py、test_w04_llm_config_scope.py；W04 scoped-negation失败反例 | 主线已有 `Config.load(validation_scope='llm')`，不再接第二load_llm。反例按当前合同证明或注明被替代；保留旧失败记录。 |

A0可读旧工区/refs，不直接覆盖本卡新工区的同名整文件。允许本卡写集合增加上述source_catalog公共入口、其测试和必要薄CLI；内部仍只用当前公开owner端口。具体历史测试路径在报告§3，先比较现行行为再决定测试迁移，不跑旧整仓全量。

旧M3已吸收21个源码/测试/工具blob、R1的98个clean-filter等价JSON和独有审计材料分开处理；本卡完成后给ROOT精确可回收清单，ROOT处理原工区。费用stash由ROOT账目归档，不归CWP代码作者。A0是原A/B/C的输入整理，无需用户逐步签收。

## 任务定位与唯一工区

- 原仓：`C:/Users/郑曾波/Projects/company-wiki`；基线 `08dfe8bf1ae97dff34b28976d532b3482d3ba358`；目标主线 `master`。
- 新工区：`C:/Users/郑曾波/Projects/mb11-cwp`；分支 `codex/mb11-cwp`。本卡尚未开工，不把准备好的卡称为已派发。
- 本仓PWF：`docs/plans/mb11-cwp-2026-11-11/`。先建立 task_plan.md、findings.md、progress.md，记录真实基线与工作量；本卡及公共接口说明可复制到该目录inputs。
- 总控计划：`C:/Users/郑曾波/Projects/company-wiki/docs/plans/module-boundaries-2026-11-11/`。开工只需读本卡、该目录 interfaces.md、acceptance.md、runtime_verification.md 和本仓AGENTS；无需回放旧聊天/全部历史PWF。

```powershell
git -C 'C:/Users/郑曾波/Projects/company-wiki' worktree add -b codex/mb11-cwp 'C:/Users/郑曾波/Projects/mb11-cwp' 08dfe8bf1ae97dff34b28976d532b3482d3ba358
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

## 已确认的问题及职责

当前已有 source stream/parser owner、pathless DTO、DU与summary隔离、新旧公开类型同一性。全部保留。四项静态已确认缺口见 `review/cwp_architecture.md`；本轮尚未重新运行其RED。

1. CWP-01：`automation/narrative_transport.py` 默认从reader反查catalog/config拿OCR能力；来源协议未声明这些成员。让现有composition root显式注入已有normalization，传输只消费协议。
2. CWP-02：`RawNarrativeSelector._select_pdf` 无参读取全局预算配置。把WorkBudget/工厂作为明确输入，从入口读取一次配置，同一document/read调用共享实际账户。
3. CWP-03：`automation/narrative_source_guard.py` 中立类型经source_reader导入具体catalog runtime。直接依赖已有source_contract；扫描相同模式，不新增同义DTO。
4. CWP-04：现有packaging_contract只检查TOML；在实际wheel中验证活动入口、schema/profile资源和声明extras能力，不靠checkout的scripts/src/PYTHONPATH补依赖。

## 写入范围

独占 `src/company_wiki/**` 的本轮边界修改；按下面七责任最小改动。相关 `tests/contract/**`、`tests/unit/**`、`tests/document_normalization/**`、`tests/financial_statements/**` 和需要的tests/support；`pyproject.toml`、依赖声明、`.github/workflows/ci.yml`、`tools/pre_push_gate.py` 仅用于真实包/新边界测试接线；有限CLI脚本仅在其入口组装受影响时改。其余scripts/tools若有现役越界需报告具体调用再归本卡，不能批量重写历史writer。

不写 `integration/**`、`tools/run_source_system_tests.py`、`.github/workflows/source-system.yml`（ROOT在本卡交付后负责组合）；不写其他仓、父PWF、生产config、原件、AUTO生产账、全局skills。

## 实施路线与TDD

| 责任 | 先写测试/检查 | 实施边界与交付 |
|---|---|---|
| 中立合同 | `test_source_guard_imports_without_catalog_runtime`；禁resolver/service/store仍可构造guard | 中立类型用已有contract owner；不把runtime加入__all__掩盖依赖 |
| 中立模型 | owned wire metadata输入别名变化不能改变既有值；borrowed native context另行明确 | 只对真owned值修复别名泄漏，避免全量深拷贝原生大对象 |
| 规范化 | `test_transport_replays_ocr_with_protocol_only_source`；替身没有catalog/config，显式OCR与真实source结果等价 | 现有normalization参数贯通CLI/composition，兼容入口可转发，不做反射猜配置 |
| PDF/reading | `test_raw_selector_uses_injected_work_budget_without_config_io`、双实例不同预算、耗尽/取消；parser backend替换 | 同请求预算单一、无隐式配置文件I/O；旧256MiB额外帽不复活 |
| DU/策略 | 复用`test_document_understanding_core_isolation.py`；当前输入两种parser单元等价 | DU只读单位与显式策略，不改变业务保留/套话算法来混做主线 |
| Catalog/原件/三表 | artifact端口内存/SQLite同合同，owner-only I/O；财务statements CLI原样replay | 单DB/CAS；source→parser事务；Sina格式转换留provider/normalizer owner；如现有StatementsProvider为Sina限定协议就明确限定，不声称已通用替换 |
| AUTO/发布 | protocol-only模型/来源替身，失败/恢复/可选日志；非仓库cwd的实际wheel入口 | 保留既有账本/outbox，成功不因日志变失败；不新增任务库或授权链 |

安装验收至少覆盖pyproject现有11个console入口、processed-document及financial_statements的公开module CLI；先列base与extras适用表，不能把明确需要pdf/catalog extra的真实解析放入base环境冒失败。base公共值导入不加载optional SDK。离线wheelhouse预备由测试环境负责，缺依赖明确归环境。

把35个根模块及source_catalog内部逻辑职责分类为canonical、兼容或退休，补入简明依赖规则。复用现有AST scanner，保持实际绕行反例；不要扩展无限动态Python分析器。代码量大不等于必须拆新仓库。

## 现有证明库与最终命令

```powershell
python -B -m pytest tests/contract/test_layer_public_boundaries.py tests/contract/test_source_reader_public_port_boundaries.py tests/contract/test_processed_document_owner_boundary.py tests/unit/test_document_understanding_core_isolation.py tests/unit/test_source_summary_layer_isolation.py tests/unit/test_document_model_identity.py tests/unit/test_pdf_reading_boundary.py tests/financial_statements/test_layer_ports.py -q -p no:cacheprovider
```

这组命令是最终受影响证明库，不要求每步都跑。新增 `tests/contract/test_module_owner_isolation.py`、`test_installed_public_entrypoints.py` 可集中新增四项缺口及安装场景；若现有测试已有等价证明就扩展原文件。真实本地多文种组合由ROOT承担；本卡提供公开fixture输出。

## 交付判据

七责任均有清楚结果，四缺口有真实RED→GREEN或独立证实原假设不成立；全部活动入口具有归属，兼容不变、安装与替身证明完成，独审无本卡未修问题。当前摘要召回和后续收费恢复不属于本卡关闭条件。
