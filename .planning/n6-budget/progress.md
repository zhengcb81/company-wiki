# N6-BUDGET Progress

2026-10-06 MAIN创建独立worktree及启动文档，分支codex/n6-budget；卡ready。
2026-10-06 本线完成：读两源模块与只读接口/旧测试，离线回放S01-S08真实候选并对比方案（见findings.md）。
2026-10-06 RED两段：先缺API的3个收集错误，再以旧行为桩实现跑出行为RED `13 failed, 19 passed, 1.60s`。
2026-10-06 实现 `n6_budget_dedup.py` + `narrative_budget.py`(`_plan`/`budget_diagnostics`) + `narrative_finalize.py` 计数与去重接线。
2026-10-06 GREEN：三测 `32 passed, 1.57s`；旧 evidence+selection `121 passed, 1.91s`；`tests/unit -k narrative` `584 passed, 55.19s`；相关短测 `122 passed, 53.31s`（1个环境依赖失败：外部 sibling `earnings-transcripts` 根在本lane worktree不存在，失败在读原件的第245行，与本线无关）；`ruff check` 全绿。
2026-10-06 真实回放（同一批只读候选）：required 11→12、选中重复 48→2、noise 1→1、S04 event 占比 146/160→76/160、S05 114/160→88/160；S06 159/160（超预算组被完整舍弃）。
2026-10-06 待办：写 HANDOFF/handoff.json，提交推送 codex/n6-budget。
