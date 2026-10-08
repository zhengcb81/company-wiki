# RF 本地未提交状态只读审计卡（2026-10-01）

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](../task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

## 目标

在不改 RF 仓库、不恢复、不删除任何文件的前提下，查清 revenue-forecast 根 `fcap` 工作树中的本地变化和唯一未并入 main 的 reader 提交各自是什么、是否仍被计划或测试使用，给总指挥提供精确的并线与清理建议。此卡只做取证和分类；所有清理/恢复/合并由总指挥在审计报告完成后另行执行。

## 写入边界与文件所有权

- RF 读取范围：`C:\Users\郑曾波\Projects\revenue-forecast` 及其同仓已存在 worktree；只读。禁止修改 RF 中任何 tracked/untracked 文件、Git index、refs、worktree、配置、数据库和测试产物。禁止 `reset`、`clean`、`checkout`、`restore`、`stash`、`cherry-pick`、`merge`、`fetch`、`pull`、删除、移动或改名。
- 唯一允许的新文件：本卡的独立执行报告 `harness_lanes/results/revenue_forecast_worktree_audit_2026-10-01.md`，在自己专用 CWP worktree/分支中创建。不得改总计划、接口表、其它 harness card 或 CWP 产品代码；总指挥之后负责收录报告结论。
- 不读写 API key、token、`.env`、credentials 或可能包含凭证的日志正文；如路径名或摘要可能泄露凭证，报告时脱敏，只报告类别、大小和 SHA-256。禁止输出财报原件、公司资料正文或大段运行日志。

## 冻结输入快照（开工时重新核对）

以下是 2026-10-01 完整权限只读复核值，不是允许写入的目标：

| 项目 | 快照 |
|---|---|
| RF 根工作树 | `fcap@ee0a82bf`；12 个 tracked 状态、404 个 untracked 路径 |
| 本地整合主线 | `main@415d8eb3`；对应 `Projects/rf-impl` 工作树干净 |
| Reader 支线 | `codex/revenue-source-reader@3b00b938`；相对 main 有 1 个仅分支提交；其 `rfv2-tdd` worktree 当时干净 |
| 另一个 reader ref | `codex/rf-reader-v2-20260929@415d8eb3`，与本地 main 同一提交 |
| 根 fcap tracked 修改 | `.planning/.../OWNER_DECISIONS.md`、`REMEDIATION_REGISTER.md`、`findings.md`、`progress.md`、`task_plan.md`；`assurance/runs/` 下 4 个运行汇总；`assurance/unified_completion/` 下 3 个测试/实现文件 |
| 根 fcap untracked 初步分组 | 353 个 `.planning` 路径（主要位于 `execution_runs`）、45 个 `.tmp-r41-mutation` 路径、其余为少量 `assurance` 与日志路径；需用完整权限重新解析 Git quoted paths 并逐项归类 |

若开工快照不同，先把差异记入报告，不要为了凑上表而改变仓库状态。若 Git 报权限错误、漏目录或 status 与当前 PWF 不符，停止分类并记录可见性问题；不得把权限造成的假删除算作真实状态。

## 工作步骤

1. 用完整仓库可见性的只读 Git 命令记录：branch/HEAD/upstream、`git status --porcelain=v1 -z`、tracked diff path、untracked path、root/main/reader 关系、worktree 列表。起始与结束各做一次；路径、数量和内容 hash 不一致时说明原因，不自行修复。
2. 阅读 RF 当前 `.planning/2026-09-19-three-project-history-audit/` 的 `task_plan.md`、`progress.md`、`findings.md`、`REMEDIATION_REGISTER.md`、`OWNER_DECISIONS.md` 中与当前轮次对应的部分。沿文档中的 run ID、commit、测试名和输出路径追踪，不把 `execution_runs` 一概当临时垃圾，也不把所有运行目录一概当长期证据。
3. 对 12 个 tracked 变化逐路径比较 `main`、`fcap` 和工作树版本，查 Git blame/log、计划引用、调用者与相关测试。分类为：有效实现/test、计划/阶段证据、可重建运行产物、必须保留的审计证据、被主线覆盖、无法确定。指出每项最适合的后续动作（commit/迁移后 commit/恢复到 main/候选清理/需要总指挥决定），但不执行。
4. 对 404 个 untracked 路径做完整清单或等价的无遗漏分组。逐类记录路径前缀、数量、总字节、主要扩展名、时间范围、是否被 PWF/测试/代码引用；记录精确可安全删除候选清单及依据。对凭证类或正文类路径只报脱敏名称/元数据。显式识别 `.planning/execution_runs` 内的 pre/post image、scratch、test logs、验收收据、脚本和 reviewer/owner 结果，区分一次性中间产物与唯一证据。
5. 单独审查 `codex/revenue-source-reader` 的唯一分支提交：说明提交改动、与当前 main 的差异、对应 PWF 决策和测试证据、是否已被 `codex/rf-reader-v2-20260929` 或 main 替代；给出建议 cherry-pick/合并/丢弃/暂缓，并列主线整合需要运行的最小测试。不要执行这些动作。
6. 检查本地 `main@415d8eb3` 是否已吸收 fcap 中已提交 RF 改进；将提交历史、dirty 工作树变化、untracked 运行资料三者分开报告。不得把“fcap tip 是 main 祖先”写成“fcap 根工作树全部已合并”。
7. 在报告里给出逐项分类矩阵：`path/group | count | bytes | owner/plan citation | current consumer | evidence | recommendation | confidence | risk`。不确定项明确列出，不以路径名字猜用途。

## 交付与验收

- 报告保存到唯一指定路径；至少包含方法与环境、起止 Git 状态快照、12 tracked 逐项结论、404 untracked 全量对账、reader 唯一提交评估、可以清理/必须保留/需总指挥决定的精确分组、预计可释放字节与风险。
- 起始和结束 Git status / HEAD / worktree 清单必须一致；Git index、文件 hash 和数据库不变。任何意外写入都立即停止并报告，不自行回滚。
- 本卡没有产品代码变更，因此不要求跑 RF 产品测试；可以只读查看既有测试输出。`git diff --check` 只检查自己的报告文件。
- 报告结论是技术事实和候选建议，不是删除授权，也不负责并线。总指挥按用户既有指令对有效改动进行必要 commit，将一次性文件在有明确依据后清理，再对 reader 提交作独立整合与测试。
