# 实施控制目录

本目录把 `task_plan.md` 中的自然语言约束变成机器可检查的验收规范。

## 权威边界

- `acceptance.json`、`acceptance.lock.json`、`tests/acceptance/` 和 gold expected 属于 Reviewer。
- Implementer 不得在实现 Work Unit 中修改 Reviewer-owned 文件。
- Implementer 只能把 Work Unit 标记为 `candidate`。
- `verified/completed` 必须来自 Gate Runner receipt 和独立 Reviewer。

## 硬规则

- 任何 failed、collection error、unexpected skip/xpass 或 pytest return warning 都阻断。
- 低于硬阈值时 `pass_with_notes` 无效。
- 普通 Gate 禁止真实网络、真实 LLM 和正式数据写入。
- Gate 必须在 clean worktree/venv 安装当前项目，不接受测试文件自行注入 `PYTHONPATH` 作为 clean-install 证据。
- 已验证 commit/tree 发生变化后，旧 receipt 自动 stale。

## 修改规范

规范变更必须独立 Work Unit，由 Human Owner/Reviewer 批准并重新生成 lock；不得与业务实现混在同一个 diff。
