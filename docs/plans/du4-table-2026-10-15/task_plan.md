# DU4-TABLE 独立实施计划

PLAN_ID=du4-table-2026-10-15
PWF_PLAN_ROOT=docs/plans/du4-table-2026-10-15
工作目录：C:/Users/郑曾波/Projects/company-wiki-du4-table
分支：codex/du4-table-20261015，基线：8206e78d4087531b1d7ed57c45a73c942cc702e3

## 先读

1. [本任务施工卡](card.md)
2. [ROOT 固定接口与交接标准](INTERFACES.md)
3. fixtures/manifest.json 和 references/ 中的历史设计。

本卡目录边界优先于旧参考中的广泛接线建议。只写本卡三个所有权目录；不要改主目录或兄弟工作树。此 PWF 由本作者维护，ROOT 总 PWF 只读。无需再等 ROOT，可以开始 A。

## 阶段

- [ ] A：核对实际保存观察，先写独立 expected 的语义反例并留真正 RED。
- [ ] B：实现纯组件，集中单元/契约测试、输入不变、预算/范围/未知值与 holdout。
- [ ] C：Ruff/mypy、交接文档和正常 commit，STOP 等 ROOT 接收。

没有逐小节点签收；仅上述三个大节点。不得调用真实供应商、操作生产资料、同步技能、改 CI 或跳 hooks。ROOT 负责现有引擎接线与真实 E2E/并线。

## Next Step

执行 A，确认本工作目录 src import，再写可复现的语义 RED。完成后把实际命令与证据记入 progress.md。
