# RF 独占任务：持久叙述证据薄 consumer

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](../task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

> **已完成，勿重复派发（2026-10-03）：**最终`6fb2def7`正常推送origin/main并快进rf-impl本地主线，Actions37119502901全绿。89项真实文档/原reader节点、生命周期Win20/Linux16/CLI3及静态门已通过；4项历史owner dirty原SHA保留。见[G-C收尾](results/gc_consumer_closeout_2026-10-03.md)。下方为实施历史与接口记录。

## 范围与前置

只写 revenue-forecast 新 consumer、该消费者测试/文档及确有必要的既有入口调用点，不写 company-wiki/FF/ET/StockWiki/IQS。RF `0573c40` 已发布 main、CI 两 job 全绿；开工 fetch 当前 main，使用新 `codex/...` worktree，不清理或修改活动 fcap/历史 execution_runs。

先读 [producer 交接](../narrative_transport_handoff.md) 和当前 CWP 发布收据。只在 producer 已提交推送后接线，不能使用试点 `/0.2.0`、physical source path 或未提交工位。接口与测试资料均在 CWP 主线 `tests/fixtures/narrative_transport_v1/`。

## 顺序

1. 核 RF 现有 SourceRef reader/subprocess/请求身份接口，用新的独立 narrative adapter 复用这些部署入口与错误处理；不得另建 root adapter 或导入 CWP 的 Store/automation。先写严格 request/receipt/bundle/hash/size、unknown version、超时、退出非零、metadata-only不能作证据的 RED。
2. 实现一个精确 NarrativeRef read；匹配原文 SourceRef、公司/证券/期间/as-of，输出 RF 自有 source-oriented context（摘要、原文 ID/SHA、locator、coverage/质量/skip诊断）。旧 raw SourceRef 入口不变；叙述内容不是清洗财务数据，不生成新预测/投资结论，不自动下载或付费。
3. 将 opt-in 入口接到现有来源准备或查询流程。若现有 CLI 无合适调用点，先提供独立明确的 narrative read 子入口，记录如何调用；禁止仅做无人调用的 validator 或偷偷改变默认路径。缺包/未知公开时间/错期给具名状态，不触发全文/LLM回退。
4. 节点 E2E：在 RF 独占短测试根用当前 CWP 真实 producer 生成/持久化包（仅测试进程可使用 CWP测试fixture），经过 RF 正式入口→CWP CLI→RF DTO；正常、重复读取、坏 artifact/raw SHA、错身份/期次/as-of、skip/partial/needs_review、超时/非零均有行为断言。真实样本至少年报和英文 TXT；网络 0、生产目录/DB 0写。不能用 mock CWP receipt 代替此节点。
5. 跑本线测试包、受影响原 SourceRef 回归与既有快速静态门；不恢复每 commit 全仓 coverage。正常提交推送，检查 CI；交总指挥收口 G-C。

## 输出和停止点

交接一页：base/branch/commit、实际调用命令、接口版本/golden SHA、改动路径、测试结果、独立根恢复与 hold。所有生成资料退出清理，不读/提交API key。生产 route保持 opt-in，Worker不由本卡启动。研究语义完整性留在 RF 原有层；无新增人工签收/private/public/prompt-review门。
