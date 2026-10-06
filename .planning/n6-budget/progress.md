# N6-BUDGET Progress

2026-10-06 MAIN创建独立worktree及启动文档，分支codex/n6-budget；卡ready。
2026-10-06 本线完成：读两源模块与只读接口/旧测试，离线回放S01-S08真实候选并对比方案（见findings.md）。
2026-10-06 RED两段：先缺API的3个收集错误，再以旧行为桩实现跑出行为RED `13 failed, 19 passed, 1.60s`。
2026-10-06 实现 `n6_budget_dedup.py` + `narrative_budget.py`(`_plan`/`budget_diagnostics`) + `narrative_finalize.py` 计数与去重接线。
2026-10-06 GREEN：三测 `32 passed, 1.57s`；旧 evidence+selection `121 passed, 1.91s`；`tests/unit -k narrative` `584 passed, 55.19s`；相关短测 `122 passed, 53.31s`（1个环境依赖失败：外部 sibling `earnings-transcripts` 根在本lane worktree不存在，失败在读原件的第245行，与本线无关）；`ruff check` 全绿。
2026-10-06 真实回放（同一批只读候选）：required 11→12、选中重复 48→2、noise 1→1、S04 event 占比 146/160→76/160、S05 114/160→88/160；S06 159/160（超预算组被完整舍弃）。
2026-10-06 待办：写 HANDOFF/handoff.json，提交推送 codex/n6-budget。
2026-10-06 推送：首次 `git push` 被 `.githooks/pre-push` 拦下——`tools/pre_push_gate.py` 的 `_run_pytest_gate` 强制 basetemp ≤60 字符，本 lane worktree 绝对路径 `<worktree>	mp\ppXXXXXXXX` = 65 字符，在跑任何测试前即 `GATE RED at: CI fast contract smoke set`（路径约束，非测试失败）。与本批 N5-DOCSET 同一根因（见 origin/codex/n5-document-quality `99c7e51`）。
2026-10-06 按既定裁定从主检出上下文推送：`git -C C:/Users/郑曾波/Projects/company-wiki push -u origin codex/n6-budget` → `pytest basetemp verified: short, repository-local, and not relocated` + `pre-push gate GREEN — safe to push`，推送成功 `9495459..0c5d53e`；**未用 `--no-verify`，未改任何门/CI 文件**。
2026-10-06 CI 核对：`.github/workflows/ci.yml` `on.push.branches=[master]`，`actions/runs?branch=codex/n6-budget` → `total_count 0`，lane 分支推送不触发 CI，CI 在 MAIN 合入 master（或开 PR）时触发；未擅自开 PR。
2026-10-06 交付状态：代码 head `805420a`（实现+测试+夹具+PWF+HANDOFF.md），文档 head `0c5d53e`（handoff.json）；本线完成。

