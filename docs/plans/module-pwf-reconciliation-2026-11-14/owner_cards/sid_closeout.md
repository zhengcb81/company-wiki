# SID-PLAN-WORKTREE-CLOSEOUT

**Owner / 唯一写入仓：** `C:\Users\郑曾波\Projects\StockInfoDLSimple\v2-clean-rewrite`。

## 目标与边界

对齐 SID 的 MB11 与 G4 PWF 状态、清点本仓 worktree/备份并保留用户名单；完成后明确 SID 本仓后续主线。只写 SID 仓，不改 CWP/FF 的 provider adapter。

## 起始事实

- `v2-clean-rewrite@d084c4a` = `origin/v2-clean-rewrite`；tracked clean；未跟踪 `a_share_companies.txt`、`companies.txt` 是用户名单，必须保留。
- 3 个注册 worktree、0 个 non-ancestor refs。Projects顶层仅一个 `StockInfoDLSimple` 容器，内含 `cwp-cninfo-bounded-budget` 注册工区与 `lineage-cleanup-backup-20261004` 备份目录。
- MB11 SID 卡已收尾；G4 latest 也标完成，但仍遗留“主线待做 1.3.0 路由升级”，需核对当前 HEAD 后决定完成或开放。

## 执行步骤

1. SID owner 在 `docs/plans/mb11-sid-2026-11-11/` 或本仓现行入口写当前 status，记录最新主线 HEAD、G4状态和唯一下一步；不得把两个计划都称为 canonical。
2. 按当前源码与G4 handoff核对1.3.0路由是否已进入主线；已完成则追加收据并把旧待办标成 superseded，未完成则保留为明确任务。
3. 对3个worktree、bounded-budget工区和backup逐项查看关联PWF/branch/dirty/内容；用户名单、真实返回数据和唯一测试证据保留。
4. 只由 SID owner 删除已结案、clean、可重建的本仓工区；为每条 Projects 目录记录 keep/delete 与字节收据。
5. 更新 SID 下个主线任务和与 CWP/FF 的公开 wire 依赖；跨仓差异只开 owner handoff，不直接修改邻仓。

## 完成条件与审查

最新ref、G4下一步、MB11完成状态一致；3工区和额外目录都有归属；用户名单仍在；最多一个长期主仓目录。代码改动跑SID定向suite和最终相关整套回归；纯文档用JSON/link/`git diff --check`检查。独立 reviewer 按最终 HEAD 核对，修复后由SID owner提交并推送，交 `handoff.md/json`。
