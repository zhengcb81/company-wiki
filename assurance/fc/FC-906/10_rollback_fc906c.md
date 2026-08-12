# FC-906-c Rollback Plan — 生产 apply（2026-08-12，已成功，预案备查不执行）

> 生产 apply 已完成并验证（29 v2 artifacts 全绑定、15 review receipts、幂等 0 重复）。
> 本文件记录**如果**需要回滚的精确命令（零删除原则：所有回滚都是删除本 apply INSERT/UPDATE 的行，不触碰任何用户/既有数据）。

## 回滚范围（本次 apply 写入的，可安全撤销）

| 对象 | 数量 | 回滚命令（预案） |
|---|---|---|
| artifacts（v2，本次 INSERT） | 29 | `DELETE FROM artifacts WHERE created_at > '2026-08-11T23:40:00Z'`（仅本次写入行；不影响 7718 legacy） |
| derived 新文件（本次 normalize 产出） | 63 | 删除 derived 下 created_at 对应的 63 个新文件（路径从 artifacts.path 列表导出） |
| documents.metadata_json 的 prompt_injection_review | 15 | `UPDATE documents SET metadata_json=json_remove(metadata_json,'$.prompt_injection_review') WHERE document_id IN (<15 ids>)` |
| producer_events（journal） | 29 | 保留（审计 journal 无 FK 且只增；回滚不删 journal——它是事实记录） |
| llm_cost_log.csv | 5 | `git revert` 本次 chore 提交（若已提交） |
| normalize 队列修复（代码） | — | `git revert 0ee0d09`（恢复 pre-fix 队列行为） |

## 为什么不需要回滚（现状）

- apply 全绿：14/15 + 11/11 + 3/3 REUSABLE；0 重复；29↔29 journal。
- 零删除：未删除任何既有行/文件；legacy 7718 保持 untouched。
- 真实副作用如实记账：LLM 5 次调用（$成本）已写入 llm_cost_log.csv（git diff 可见）。
- FC-901 apply 判定：生产 dry-run 0 bindable → **apply 为 no-op，不执行**；"source-bound artifact > 0" 由 v2 运行时绑定达成（validate_artifact REUSABLE，无需 artifact_bindings 表）。

## 触发回滚的条件（手册 §9）

- shadow diff 无法解释 / fingerprint 漂移 / 新失败回归 / 用户 dirty path 被触碰。
- 当前均未触发；预案仅备查。
