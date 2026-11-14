# Owner 卡独立审查记录

## 结论

**PASS**。独立 reviewer 对总计划、Projects 顶层目录清单、总派发矩阵和七张 owner 卡做了只读审查。最终复核确认各 lane 的写集合互不重叠，StockWiki/IQS 明确暂缓，暂停中的 native goal 没被计划自动恢复。

## 审查范围

- `task_plan.md`
- `findings.md`
- `projects_directory_inventory.md`
- `dispatch.md`
- `owner_cards/*.md`
- 父计划 `CURRENT_STATUS.json` 的新指针与 JSON 有效性

## 首轮问题与修复

1. **失效的目录清单链接（P1）**：多个文档用了带日期的文件名，但实际文件不带日期。统一改为 `projects_directory_inventory.md`，并通过相对链接检查。
2. **卡片离开总表后缺少路径上下文（P1）**：RF、ET、RFAudit 卡补入各自 Projects 子目录完整名单，让每张卡可独立交付。
3. **跨物理目录越界风险（P1）**：两个 CWP Git worktree 的物理路径在 `investment-dashboard/.worktrees/`。CWP 卡现明确禁止 CWP 删除、移动、checkout 或清理这些目录；只记录 CWP branch/HEAD/dirty 摘要，由 Dashboard owner 协调物理目录处置。
4. **把 dirty 误当成活动证明（P1）**：这两个工区改为 `UNCLASSIFIED_HOLD`，不能据 dirty 直接判定仍活动或可删除。
5. **ET 目录数量不一致（P2）**：派发矩阵已由六个更正为七个额外目录。
6. **未知状态缺少统一分类（P2）**：目录清单补入 `UNCLASSIFIED_HOLD`，规定 owner/PWF/branch/dirty 归属未查清前不得清理。

## 最终检查

- `CURRENT_STATUS.json` 可被标准 JSON parser 解析。
- 新计划与父状态入口的相对 Markdown 链接有效。
- `git diff --check` 通过。
- 不包含外仓代码修改、Git 操作、外部下载、产品测试或生产数据清理。

## 后续单卡自包含性复核（2026-11-14）

用户追问单张卡能否独立交给 harness 后，ROOT 对七张可执行卡逐张复读并补充了此前不够具体的交接信息：目标仓的 PWF 读取入口、固定 handoff JSON/Markdown 文件名、独立审查报告文件名、统一处置状态词义，以及由未参与实施的 reviewer agent 审最终已发布 HEAD 的顺序。另对照实际目录确认列出的 PWF 入口均存在，`git diff --check` 通过。

首轮复核对更新版本给出 FAIL，发现 ET、RF、SID、RFAudit 仍有“自行选择唯一入口”的歧义。ROOT 将其分别固定为 ET 根 `task_plan.md`、RF 根 `PLANNING_STATUS.md`、SID `docs/plans/mb11-sid-2026-11-11/task_plan.md`、RFAudit `docs/plans/company-pool-cycle-2026-10-09/task_plan.md`，并禁止新增或选择第二入口。随后独立 reviewer 对七张卡的最新版复核为 **PASS**：交付路径、JSON schema、处置状态、commit→独审→修复复审→push顺序及 RFAudit 无 remote 例外一致。ROOT 另只读确认这四个固定入口和其余卡中列出的入口在各目标仓存在；此路径核对不涉及外仓写入。各 lane 实施完成时仍须按卡内约定由另一名 agent 审查最终提交 HEAD，修复后复核通过。
