# DU11 当前主线接手指南

更新时间：2026-10-18

计划：`PLAN_ID=du11-source-closure-2026-10-18`，`PWF_PLAN_ROOT=docs/plans`
项目总控计划：`docs/plans/document-understanding-2026-10-13`

## 交接结论

先行的 RF、FF 两张 DU11 施工卡已验收并合入各自主线，CWP、RF、FF 本轮发布 CI 均为绿色。**整个计划没有完成。**

## 2026-10-18 最新状态

- **B2 已完成、最终复审 PASS、已发布**：`d55d3369`（三审修复）、`6a2ee853`（性能修复）、`2a80acf6`（复审两个 P1：长名称截断、截断被误判为 missing）。最终复审 PASS（`review/b2-antecedent-final-review-20261018-v3.md`）；`tests/unit/du11_source_closure` **110 PASS**；三源回放绑定 `b2-final3-20261018`（CN 10/10）与 `b2-real-sources-final2-20261018`（HK 7/7、US 8/8），原件/gold 未变、0 API；CI `2a80acf6` success（收据 `ci-39139605025.json`）。
- **C 工程侧已通过**：CN（MiMo）与 US（MiniMax）各 1 次真实 POST，`activation_recovery=PASS`（同 attempt、无新增扣费），`cross_run_zero_POST=true`，FF 复用与 RF 读取通过；HK 因 `DEEPSEEK_API_KEY` 401 未跑（无结算发票，但有一条 69,046 tokens / $0.031208 的 unknown hold）。
- **C 内容侧：按 8/10 收尾（用户决定，2026-10-18）**：CN 最佳 required 8/10（critical 5/7），US 最佳 4/8，HK 未跑（DeepSeek 401）。不是内容验收通过，而是经用户确认的收尾口径；模型评估计划见 PWF 顶部。复审报告：`review/c-content-review-20261018-cn-v3.md`、`...-cn-v4.md`。
- **覆盖修复（A）状态：实验性、默认关闭**。实现走现有 retry（两次 attempt、两次计费），`CW_SUMMARY_COVERAGE_REPAIR=1` 才启用；已实测两次 POST 并合并成功、run 进入 `activation_pending`。未解决：`activation-resume` 与重试 attempt 的 `reopen_paid_output` 冲突；MiMo 首响应 JSON 约每 3 次失败 1 次。默认关闭时不改变任何现有流程。
- **待拍板**：接受 CN 8/10 收尾（推荐），或继续解决上述两个残余问题后再做内容复审。
- 累计付费：44 个 attempt、900,711 tokens / $0.238405（ledger 去重口径，核对于 2026-10-18；不含 metadata 记录的历史基线，上限 2M / $20）。

不要把已接收的 RF/FF 施工卡重新打开，也不要把工程测试通过、原文选择金标命中或已有摘要缓存命中当作正式内容验收通过。

## 当前基线

| 项目 | 当前已发布版本 | 验证结果 |
|---|---|---|
| company-wiki | producer `0ccdc6896ee58063ff827e9ceab16043c7550e0c`；计划/交接当前提交见主仓 `master` | CI `39094787278` success；6801 passed、24 skipped，合同142 passed |
| revenue-forecast | runtime `f8002f5fc8f56533c814f1616b7ecb68016f35e4`；兼容表最终提交 `9669c4d79cff7bf3e023db6cb74c411f4bef7bf` | CI `39095818018` success；416 passed、36 子测 |
| filing-fetch | `e8740748f91999cb24169b42f8e789726ed50482` | CI `39095654355` success；873 passed、7 skipped、78 子测 |

这些是当前已验证的代码依赖版本。不要为了文档提交递归更新兼容 pin。可复查的接收、发布、安装和清理例外见同目录的 `du11-reception-closeout.md` 及对应 JSON 收据。

## 从哪里开始

1. 读取本指南、[`task_plan.md`](../task_plan.md)、[`antecedent-source-interface-final.md`](antecedent-source-interface-final.md) 和 [`antecedent-owner-design.md`](antecedent-owner-design.md)。接口文件是 B2 的行为和边界合同；本指南负责告诉接手者先做什么、在哪做、何时算完成。
2. 以当前 `company-wiki` 远端主线为计划和已发布代码基准。此前 ROOT 实施工区为 `C:/Users/郑曾波/.codex/worktrees/du11-extractive-runtime/company-wiki`，分支 `codex/du11-source-closure`，当时 HEAD `10699188ccb0814abd63582ad24f9943e7ffe92a`。该工区的 tracked 文件干净，但含有历史未跟踪 `.planning/du11-*.log`；**先检查状态，不要 reset、clean 或批量 stage。** 接手时先 fetch 并核对它与当前主线的差别，再决定复用还是从主线建隔离工区。
3. 保持生产原始文件只读；先使用现有真实源回放脚本及已有 SHA/gold 记录。工程 TDD 阶段不需要模型或供应商调用。

## 当前要解决的问题

真实 CN 半年报中，旧 t32“求的同时……”在页内编号修复后已不再入选；t34“该系列产品已交付……”仍单独入选，缺少能证明“该系列”指向哪个产品系列的前文。现有材料显示可能需要段落9–14共五个原始物理块，超过四块上限；目前没有证据证明可以安全缩成更小的声明。实现必须能在现有上限内找出充分证据，否则只 defer 这张卡。不得挑一个产品名代替整体指代、扩大额度或从模型补造事实。

## B2 实施顺序

把以下内容作为一个工程节点集中完成，不在每个小改动后另设签收：

1. **先补行为测试。** 在现有 `tests/unit/du11_source_closure/` 范围覆盖来源顺序与边界、唯一/集合/歧义指代、原文与分析文本引用映射、额度、缓存上下文键及真实候选组装。先确认新场景能暴露缺陷，再实现。
2. **只扩展现有责任层。** 来源前驱窗口归 `narrative_reading._candidates`；引用/原文回退与同一账户协调归 `SourceOperatingSession`；指代语法复用 `OperatingRelationSession` 的已准备文本与缓存。不要新增第二套 detector、Store、预算、产品词典或模型纠错步骤。
3. **先完成所有 readiness，再构建一次图和事实。** 原文 target、已要求的 context 和需要的声明文本必须一起计费、一起进入包；成功时 target 是 support、声明是 context。不能先算 fact/缓存，再补上下文。
4. **保留严格来源与额度语义。** 只按来源真实 ordinal 找前文。跨 parent、section/project/body、QA、表格、未读/不透明页、未证明物理顺序都要停止。正文、已有 context、声明合并去重后仍受 8 个原始单元、4 个 `(source,page,pdf_block)` 和 2048 原文字符限制，并使用同一 parent 16M WorkBudget。未知、歧义、截断或超额只 defer 受影响的卡。
5. **验证端到端来源组装。** 从 `_candidates` 经过 selection、`_context` 到 summary task/source card，检查支持与上下文各自保留正确原文 ID、定位、SHA、期间、单位和引用。任何必要声明丢失时整张依赖卡 defer，不能只留下不完整 target。
6. **在节点结束时做独立审查。** 独立 reviewer 检查完整度、边界反例、引用精确性、预算/复杂度和真实样本；把发现的问题修完，再对最终文件 SHA 复审。不要把旧 SHA 的审查报告签给新代码。
7. **完成后回放现有 CN/HK/US 三个真实来源一次。** 核对原始文件 SHA 前后不变、既有 gold 不变、预算未超、无模型/API 请求；CN t34 必须有原文充分支持或明确 defer。优先复用本计划已有 `replay_budget_checkpoint.py`、`replay_physical_checkpoint.py` 和 `investigate_current_page_scope.py`，每次输出到新的唯一子目录；更底层只读探针见 `../../du11-source-priority-2026-10-18/real-source-probe/probe.py`。保留历史回放，不覆盖旧收据。
8. **正常提交并推送。** 先跑新增/受影响的 focused tests，例如 `python -m pytest tests/unit/du11_source_closure -q`；然后正常走 `.githooks/pre-push`。该 hook 根据本次变更选受影响的 unit tests 并跑既有 fast contract smoke；GitHub CI 仍运行完整 unit 和其 curated contract set。用 CI 的精确 commit/run 做发布验收；不要每次另跑完整本地套件、删测试、放宽期限或绕 hook。记录 commit、远端 HEAD、精确 CI run 和所有失败尝试。完成后更新本计划的 `task_plan.md`、`progress.md`、`findings.md` 顶部状态。

完整测试矩阵和 source/ref 字段定义见接口文档第 2–6 节；如果本指南与接口、代码现状不一致，先查明并把计划更正，再实现，不要自行缩小范围。

## B2 通过之后：真实摘要与恢复验收

B2 和真实三源工程回放完成后，才进入正式 C。此前 CN/MiMo、HK/DeepSeek、US/MiniMax 的真实请求只是基线；独审发现了业务噪声、主体归属、指代闭合、表格遗漏和预算挤占问题，明确不是内容验收通过。共享摘要/缓存和 paid-response 恢复代码已发布，但本轮正式内容与故障恢复验收仍未完成。

进入正式 C 时，读取当前供应商配置和累计预算账本，通过项目既有客户端使用实际配置的 `mimo-v2.6-flash`、`deepseek-flash`、`MiniMax-M3`，保持原文语言，不翻译、不读取或输出密钥。metadata 记录的旧基线为 742,228 tokens / $0.421556 估算费用；当前 ledger 去重口径是 **44 个唯一 attempt、900,711 tokens / $0.238405**（核对于 2026-10-18），历史未知费用继续作为 hold 保留。每次运行前重新读账本并核对累计上限 2,000,000 tokens / $20，不把未知数计为零。不要因为本段计划增加新授权文件或逐材料许可。

真实 C 必须同时证明：

- 摘要内容覆盖业务动态、产品/客户/产能/地区及风险，出处定位到正确原文；独立内容审查确认没有重要事实遗漏、指代错接、主体混淆或单位/期间错误。
- 已付费响应在激活/最终落库前发生可恢复失败时，重启能恢复该响应而不重复收费；相同任务的同 run 与跨 run cache hit 不产生重复 POST，真正输入变化才重新调用。
- FF 和 RF 以各自已发布接口读取真实结果，验证来源身份、期间、SHA、支持/上下文分区和 `source_availability_unknown` 等状态，不重复下载已存在的原件。
- 测试目录前后内容可核对；本轮新增原始材料、临时响应或缓存只放隔离测试目录，并在验收结束恢复原样。原始公司文档、生产 catalog、gold 和供应商配置不作为测试写入目标。

C 未通过则按共同根因修复后在真实受影响链路复验；工程层、提供商运行状态或 gold 命中不能代替内容质量通过。C 完成后再执行冻结的 holdout 与 revenue-forecast 审查循环计划。

## 保持的边界

- 不修改/删除已下载的原始财报、原文 TXT、生产配置、gold 或用户未提交数据。
- RF/FF 的 DU11 作者工区已接收；外部作者目录只读。Dayu 是纯外部项目，不改；IQS 有自己的并行工作，不碰。
- 不触碰 StockWiki 或其他仓库；不新建通用审批/身份/许可系统，不提高资源上限。
- 不查看、复制、打印或提交密钥/环境变量；不在未完成 B2 前花供应商预算。
- 一处旧 RF 审查临时目录 `C:/Users/郑曾波/AppData/Local/Temp/rf-du11-final-3a_yd5_8` 曾被平台拒绝清理，记录为 `NOT_CLEAN`。不得通过其他方式重试删除，也不得声称它已清理。
- RF 旧 3 个 assurance 工作文件及 `output/` 保持原样；不要 reset、stage 或清理。

## 最终交接报告格式

完成时在本计划 `review/` 留一份 Markdown 报告和机器可读 JSON，至少包含：

1. 起止分支/commit、变更文件、最终每个生产/测试文件 SHA；
2. 按类别列出 RED→修复→GREEN 的测试、完整测试/合同结果、真实数据回放与原件 SHA 前后核对；
3. t32/t34 的最终状态及支持/上下文引用；额度和预算测量；
4. 独立审查者、检查范围、发现与修复、其绑定的最终 HEAD/SHA；
5. push 结果、远端 HEAD、精确 CI 链接/编号；
6. 真实 provider、实际配置模型、新增/累计已知 token/费用与未知 hold 的处理、cache hit/miss 和恢复证据；
7. 测试目录清理前后清单、未清理项目及原因；
8. 仍未完成事项和唯一下一步，不得用笼统的“完成”替代状态。

## 主要入口

- [总计划当前状态](../../document-understanding-2026-10-13/task_plan.md)
- [本轮收尾与已发布证据](du11-reception-closeout.md)
- [B2 最终接口和 TDD 矩阵](antecedent-source-interface-final.md)
- [先行词责任层设计](antecedent-owner-design.md)
- [主计划进度](../../document-understanding-2026-10-13/progress.md)
- [主计划发现](../../document-understanding-2026-10-13/findings.md)
