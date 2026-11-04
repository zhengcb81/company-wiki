# 当前交接 — D4 范围已收口；先完成 D5 全局解耦

PLAN_ID=`du11-source-closure-2026-10-18`；唯一状态入口 [CURRENT_STATUS](CURRENT_STATUS.md) / [机器状态](CURRENT_STATUS.json)，主线细节见 [task_plan](task_plan.md)。

## 当前交接给谁、做什么

当前唯一开放节点是 [D5-CWP-STOCKWIKI 外包卡](review/decoupling-recheck-20261104/harness_lanes/D5-CWP-STOCKWIKI-PROCESSED-READING.md)。可交给一个 harness，在各自独立 worktree 中完成 CWP 的 pathless 规范化文档 port 与 StockWiki 的三个 provider 默认入口消费。D4 验收仍有效，但只覆盖原定义范围；尚不能据此恢复 T4/SEM 或任何其它业务主线。

ROOT（本线程）独占 FF V1/V2 边界组合测试、CWP ROOT 组合测试、跨仓最终验收与独立总审。只读调用方盘点已确认当前 RF production preparation 走 V2/pathless；V1 `canonical_path` 是显式兼容合同。验收要证明 V2 无法回退到该分支，并单独覆盖 V1 兼容，不盲删仍承诺的接口。外包实施和 ROOT 工作都完成、交付版本一致、独立测试及组合测试通过、测试隔离恢复后，才把全局解耦标为完成。不得改写 RF/FF/ET/AUDIT/StockWiki 其他未提交 WIP。

## 已完成节点

D4-01～D4-05 已接收、独审并合入各自主线；ROOT 完成 D4-06 AUDIT 测试归位和一次完整组合验收。六项 D4 缺口状态均 CLOSED。结果和链接见 [D4 closeout](review/d4-closeout-20261104/README.md)，报告/JUnit/pytest.log 保存在同目录 `run-1/`。

- company-wiki D4 merge 与 ROOT suite commit `e7469d684b10a4cd37772e045eb3e588254c5ab8` 已推到 `origin/master`。固定 push smoke 17 passed；GitHub exact-head CI #41919818618 和 Source system integration #41919818624 均成功（`e7469d68`）。
- revenue-forecast D4 测试代码提交 `96713029`；D4 收口后的 PWF-only 提交 `90c562ac` 已推到 origin/main。
- filing-fetch D4-05 已在 main `bf7e1dab` 并推送。
- StockWiki D4-01 本地主线 `23d84586`；无 remote。AUDIT D4 测试迁移 commit `2449df4a`、PWF-only commit `3589b69`；均本地，无 remote。保留这些仓现有未跟踪文件。
- ET 没有 D4 产品代码改动；保留其现有未跟踪产物。

## 唯一下一步

1. 启动 D5 外包卡；实施者按卡完成 CWP→StockWiki 解析产物合同、三个消费入口、隔离真实样本 E2E 和交付前独立审查，问题全部修好后再交接。
2. ROOT 已完成 FF V1/V2 只读调用方盘点；下一步用测试确保默认 schema 2.0 provider 流程只经 SourceRef v2/pathless，V1 兼容入口独立隔离并受测；保留必要的明确本地导入 adapter，不做无证据的兼容删除。
3. ROOT 用公开入口完成 D5 跨仓组合 E2E 与一次独立总审，核对 CWP/StockWiki/FF 实际 HEAD、测试、原件 SHA 与测试目录恢复；问题按 owner 根修并复验。
4. 只有 D5 外包交付、FF 收敛、组合验收、最终独审全部通过，才更新为全局解耦 ACCEPTED，随后恢复 T4/SEM。D5 期间不做真实摘要、缓存恢复、RF 采用或公司循环。

RF/AUDIT 业务计划仍保留为 READY_NOT_STARTED 的工作清单，但全局调度状态是 DEFERRED_UNTIL_D5_GLOBAL_DECOUPLING；不会提前开工。RF PWF commit `90c562ac` 已推送，AUDIT PWF commit `3589b69` 已本地提交（无 remote）。保持原件和其他仓现有 WIP，不改 Dayu/IQS/Dashboard。
