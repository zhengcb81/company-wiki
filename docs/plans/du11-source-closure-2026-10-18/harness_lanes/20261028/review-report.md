# W20 独立施工卡批次审查

结论：三卡可以拆开并行，产品 owner 和写入工区互不重叠。初审发现两项 FF 执行合同缺口，ROOT 已加入 R7/R8 修复；最终复核状态和卡片 SHA 见 report.json。此为施工卡设计审查，不是实现或生产验收，不新增审批节点。

## 初审发现及修复

**F1 / P2，FF 外部依赖必须绑定已提交版本，而不是 ROOT 正在变化的主工区。** 卡写显式源码根、实际 module/SHA 及 A 冻结，但没有明确 CWP/ET 采用哪个稳定已提交版本、当 ROOT 在同一主工区持续改动时如何避免一批混入多版源码。当前 FF 矩阵 `cli_main.py` 按显式 `--cwp-project/--et-project` 启动真实子进程并在批初记录依赖；ROOT 正在修改 CWP，单纯“只读”不等于输入稳定。DU10 已有固定依赖快照/模块 SHA 的成熟做法。建议卡明确：A 选定已提交 CWP、ET commit 与公共合同；使用 ROOT 已有稳定只读快照或 owned 最小 Git 导出（不复制原件/历史环境）；开工记录版本、测试后核相关源码未漂移。若必须依赖未提交变更，单列反例交 ROOT，不将其当卡间等待条件或自行修改。无需运行/审批额外矩阵。

**F2 / P2，FF 选择 case 与原 41 例全覆盖 oracle 的关系。** 当前 `cli_main.main` 没有 case filter；`case_specs.py` 是 mandatory registry，`oracle.audit` 将完整覆盖视为 authority。卡允许新增选择和恢复，但没明确 scoped case PASS 与完整矩阵 PASS 的机器语义。建议卡明确：默认原完整 41 例 authority 不缩小；选择/新故障演练报告必须携带实际 selected IDs、expected scope、完成/未跑状态，不能通过重写 `required_cases`、减少分母或排除旧失败获得全覆盖 PASS。故障补充用例在现有 runner/owner 内加法扩展，不造第二状态库/矩阵；仅局部运行成功可以表示其声明 scope 成功，不能宣称原 41 例或新增故障全集均通过。增加一个“删改 required_cases/仅跑一例不能绿全域”的中性反控即可，非额外逐步审查。

ROOT 修复：R7 显式冻结 CWP 已发布 commit `618df929ffa889424b3346d5299d67b9b1c72709`、ET 在 A 只读解析后冻结完整已提交 commit，并用最小只读代码视图、实际模块 SHA、owned 清理避免 ROOT 工区漂移；R8 明确 supplemental/partial、selected/completed/skipped、原 41 authority 不缩小、不冒全量 PASS。独审另提醒 DU10 旧 CWP 视图实际为 `900dbf6489f3b995a0bfb7fcbb8a001a68df241d`，不能直接当成 618df929；复用应指构建方法，仅 commit 完全相同才复用现成视图。该项最终确认见 JSON。

## 已确认无需改的部分

- **不重复旧工程。** W17 已交付六维 coverage_observations、独立未知状态和 carrier scope；W20-AUDIT 明确复用现 owner，新增角色/语义等价/信息量检查点，没有再造计数器。W19 是新浪结构化三表服务；W20-FF 明确不重做 W19/文种路由。DU10 的受控中断是批次重启，新卡要求 durable 前/后、回执损坏和真实再请求的事务语义反证，属于增量可靠性覆盖。
- **RF 不假推采用。** 当前 `source_narrative_context.consume_narrative_input` 已有 claim→used parameter→formula_refs 的显式引用链，可供新只读工具复用。卡要求同 source/run/version、context 与事实分离、缺追踪 unknown、无关键词猜测，且明确不强迫所有来源都进入预测、不签经济合理性。其产物是诊断，不是新 forecast schema/门禁。
- **AUDIT 四角色保留。** storage/fetch/process/analyst 与四报告后的 expert 明确；fixture 报告的离线导入不冒充四 agent 真实研究，交接仍须真正独立 agent 全面审查并修复/复审。question 前提只作 context，management answer 与 unknown speaker 不洗白，混合 QA 绑定各自实际 IDs；不要求下游重造 CWP 文本分类器。
- **故障边界可实现。** 现矩阵确有 FF 公共 CLI→ET supervisor/worker→HTTP fixture 边界→CWP 真实 import→reader 实读。卡允许现有 private test seam、fixture provider 和 subprocess 中断，不要求改 CWP/ET 生产。R3 只对 durable 后重试要求额外下载零，对未 durable 失败明确不承诺 exactly-once/盲重放。发现 CWP/ET 缺陷可以保留真实 counterexample 交 ROOT，不得伪报全链通过。
- **并行无暗依赖。** 三个物理 worktree、三个仓、各自 PWF/delivery；AUDIT/RF 均不等待对方新 report，FF 不写 CWP/ET。ROOT 保留主线 source/PDF 内容修复、收费调用、全局安装与跨仓合线。三卡允许无真实缺陷时给 no-code 回归结论，避免为 diff 强行重构。
- **大节点而非繁琐门禁。** A/B 不等 ROOT 签收，C 集中相关短测/真实 CLI/独审；完整实现版本、测试版本、独审版本与文件 SHA 绑定，后续纯交接文档 commit 可不同。无 canary、人工授权 JSON、许可签名或每 commit 全域矩阵。

## 工区事实与局限

只读 Git（`--no-optional-locks`）核对三个工区 HEAD/branch 与 setup 一致、tracked clean；RF sparse=true。主仓 RF 保持三项 assurance/runs WIP，FF/AUDIT tracked clean；没有 checkout/index/reset/安装/产品修改。

旧 FF README 仍保留 19P/21F/1PARTIAL 的历史段落，而 DU10 handoff 记录固定依赖下 41/41 PASS；卡引用 DU10 足以区分，不应把旧段落改成今天已跑的结果。卡 A 应引用具体收据版本，不盲目声称当前版本仍全绿。W17 手工全量约203s；卡已限定可稳定短时才执行一次，没有要求每 commit 运行，可保留。

本次没有运行测试、CLI、矩阵、SDK、模型、HTTP、下载，没有读取密钥。CodeGraph FF/RF 结构查询返回的旧条目不足定位本次新 owner，故按卡中明确文件直接只读核对；AUDIT 未初始化，本次不初始化索引。没有凭本审查声称三个实现已经完成。报告写入仅本目录，卡/仓/PWF 不改。
