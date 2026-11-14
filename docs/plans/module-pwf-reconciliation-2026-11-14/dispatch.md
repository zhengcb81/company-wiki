# Owner 卡派发总表

## 派发状态

可并行执行：CWP、FF、RF、ET、SID、Dashboard、RFAudit 七条 owner lane。它们只写自己的仓库，互不共享产品代码。CWP 是 ROOT 当前责任；其余卡可分别交给对应项目 owner/harness。StockWiki 和 IQS 当前暂停派发，避免撞到并行工作。

| Lane | 独立施工卡 | 唯一写入仓 | 当前基线/规模 | 工作顺序 |
|---|---|---|---|---|
| CWP | [CWP PWF与工区收尾](owner_cards/cwp_closeout.md) | `company-wiki` | `master@1f9f3dcf3`；8 个注册 worktree；13 个非祖先候选 refs | 更新 CWP 状态索引 → 核销本仓 branch/worktree → 精确清理已结案工区 → 更新 CWP 后续主线入口 |
| FF | [FF PWF与工区收尾](owner_cards/ff_closeout.md) | `filing-fetch` | `main@d4f35ca`；35 个 worktree；3 个待归因 refs | 校正唯一入口及冲突历史 → 归因 refs/worktrees → owner 本仓并线 → 清理 → 更新 FF 主线 |
| RF | [RF PWF与工区收尾](owner_cards/rf_closeout.md) | `revenue-forecast` | `main@ec5ba004`；61 个 worktree；19 个非祖先 refs | 先统一 MB-RF/W20 状态 → 逐项分支对账 → owner 本仓并线 → 清理 → 更新 RF 主线 |
| ET | [ET PWF与工区收尾](owner_cards/et_closeout.md) | `earnings-transcripts/earnings-transcripts` | `main@915f216`；12 个 worktree；0 个非祖先 refs | 校正根计划与已完成MB卡 → 归因7个额外目录 → 清理 → 明确 ET、FF、CWP 各自余责 |
| SID | [SID PWF与工区收尾](owner_cards/sid_closeout.md) | `StockInfoDLSimple/v2-clean-rewrite` | `v2-clean-rewrite@d084c4a`；3 个 worktree；0 个非祖先 refs | 校正G4旧待办 → 归因注册工区/备份 → 保留用户名单 → 清理 → 写后续SID主线 |
| Dashboard | [Dashboard PWF与工区收尾](owner_cards/dashboard_closeout.md) | `investment-dashboard` | `main@50602de`；80 个 worktree；92 个 local refs | D00更新主线快照 → 刷新三个CWP卡基线 → 对账分支与80个工区 → owner本仓并线/清理 → 更新Dashboard主线 |
| RFAudit | [审查技能 PWF与工区收尾](owner_cards/rfaudit_closeout.md) | `revenue-forecast-audit` | `main@fa0564fb`；18 个 worktree；无remote；1个未跟踪W08计划目录 | 建唯一状态入口 → 对齐cycle状态 → 先保留W08证据 → owner清理已结案工区 → 更新循环任务 |

### 暂缓，不派卡

| 模块 | 暂缓理由 | 恢复条件 |
|---|---|---|
| StockWiki | 用户说明另一项目正在修改；当前代码/PWF/worktree全部保持原样 | 并行项目 owner 提供最终 handoff、最终 HEAD 和工区处置记录后，由 StockWiki owner 自己接续 |
| invest-quick-scan | 已有并行 owner 工作，需避免另开重叠线 | 当前 owner 交付后，先核唯一入口和 write-set，再决定是否补卡 |

Dayu 是纯外部项目，不纳入清理、PWF 或代码卡。`revenue-forecast-audit` 是独立仓，不并入 RF。项目顶层候选完整清单见 [Projects 清单](projects_directory_inventory.md)。

## Owner 卡共用执行约定

每张卡都是独立上下文，可以单独交给一个 harness。卡片 author 只在目标模块仓内写入，自己更新本仓 PWF、在本仓做变更和 Git 发布；不得接收 ROOT 对其他模块的代操作。总控只读取 handoff 并在 CWP 运行公开接口组合验证。

1. 起步先核实际 HEAD、remote HEAD、worktree 列表和 dirty/untracked 摘要；本卡快照只是起点，若有新提交或在途改动则更新快照继续，不回滚新工作。
2. 将每个 PWF 入口、branch、worktree、Projects 子目录映射到唯一任务/owner；结果分 `ACTIVE_KEEP`、`EVIDENCE_KEEP`、`ABSORBED`、`UNCLASSIFIED_HOLD`、`DELETE_AFTER_OWNER_CONFIRMATION`。用途或归属未知的路径标 `UNCLASSIFIED_HOLD`。不以名称、日期、是否 tracked 单独做删除决定。
3. 先收敛本仓 PWF：一个 canonical `START_HERE` 或 status 页面指向当前计划、已完成收据、余项、唯一下一步。其他计划保留并标清 `historical` / `subplan`，不得删掉有效交接证据。
4. 由模块 owner 按公开接口处理本仓 branch/worktree。实现确有变化时运行该模块最相关回归；在模块最终大节点运行一次完整相关 CI。纯文档清理不重复跑产品全量测试。
5. 只清理已结案、可重建、无 dirty work、无运行配置引用且保留其必要 handoff/收据后的精确路径。每次清理后记录目录、文件数/字节数及保留/删除依据。
6. 完成后由**独立 reviewer**按最终 HEAD 检查完整性、接口边界、测试收据、未提交文件归因、Projects 目录收据和 PWF 下一步。发现问题由 owner 修完再交接；只做一个最终大节点审查，不逐小步签收。
7. 提交 `handoff.md` 与 `handoff.json`，字段至少含：repo、canonical PWF、base/final HEAD、remote status、branch/worktree逐项处置、dirty/untracked摘要、Projects目录分类、清理数量/字节、测试、独审绑定HEAD、剩余项、下一步。

## 总控的整合顺序

1. 七条可执行 lane 各自更新 PWF 并完成本仓收尾；它们可并行，不能互相等待或共写文件。
2. ROOT先验收交接与当前代码版本一致性，不直接替作者改其他模块。缺少收据只退回所属 owner 补齐。
3. 所有必要的 producer/consumer owner ref 到位后，CWP ROOT 才做一次有限公开接口组合验收；按失败所属层回给对应 owner。
4. PWF/目录清理关闭后，重新核对父计划 `du11-source-closure-2026-10-18` 的当前 status，再依其顺序继续真实摘要、缓存恢复、RF实际采用与公司循环。当前 native goal 为 paused，本卡不自动恢复。
