# N6-CANDIDATE Progress

2026-10-06 MAIN创建独立worktree及启动文档，分支codex/n6-candidates；卡ready，尚未由人类宣布分派。所有代码仍固定基线，后续由本harness记实际进度。

2026-10-06 本harness施工记录：
- 核HEAD 81d4524（=基线58b74d0+启动文档），工作树干净；INPUT_CARD.md与源仓最新卡同步（S07境内口径）。
- 阶段1：读4模块+共享只读（narrative_evidence/pdf_groups/finalize/budget/document）；基线实测required金标：15个assess层MISS、反例全部MISS/dropped。RED命令（卡原文）：18 failed / 12 passed / 3.24s。
- 阶段2：新增 n6_candidate_operating_facts.py（10个通用检测器+OPERATING_FACT_JOIN）、n6_candidate_completion.py（句内补全+1600/1200常量+linkable）；改4模块（见changed_paths）。GREEN（卡原文命令）：30 passed / 0.99s；ruff（卡原文命令）：All checks passed。
- 既有相关短测试（未改动）：test_narrative_evidence + test_narrative_selection_architecture + test_narrative_english_business_recall + english_operations + pdf_bytes + retrieval + select_handler + verify_handler = 181 passed；连同新测试合计211 passed / 2.91s。
- 阶段3：真实样本8份原件（S01-S04,S06-S09）先SHA核对后parse_pdf(table_pages=目标golden页)/parse_transcript_text → select_narrative_evidence全管线回放：目标14点全部在候选层恢复（14/14），9/14同时进入96/160预算选择；原件终检sha/size/mtime全不变；0下载/LLM/付费。tmp临时脚本与产物删除，pytest basetemp目录由fixture自动清理并验证absent。
- 旧断言冲突：无（181既有测试全绿，未修改任何旧文件）。

2026-10-06 推送与门禁：
- 提交：`9a4b815`（代码+测试+PWF+INPUT_CARD同步，pre-commit ruff/mypy/守卫全过）→ `ce61cdd`（HANDOFF.md+handoff.json）。
- 首次在lane工作树 `git push` 被 `.githooks/pre-push` 结构性拦下：`tools/pre_push_gate.py::_run_pytest_gate` 要求 basetemp 绝对路径≤60字符，本工作树 `...\cwp-lanes-20261006\n6-candidates\tmp\pp*`=69字符，在跑任何测试前即 `GATE RED at: CI fast contract smoke set`（路径约束，非测试失败；与n6-budget/n6-footprint/n5同根因，见origin记录）。
- 根因核实：本工作树逐条跑门禁同款 `FAST_CONTRACT_CASES`（12条）= **12 passed / 5.25s**；ruff全范围/compileall/config_doctor/host守卫在提交与门禁前均绿 → 红仅为环境依赖型路径检查（ci_root_fix.md §8类）。按协议不用 `--no-verify`、不改共享门禁（`tools/pre_push_gate.py`/`.githooks`属CI写集，本线不可写→main_wiring）。
- 处置（按n6-budget既定裁定，不建第二工作树，符合本卡"不再建第二工作树"）：`git -C C:/Users/郑曾波/Projects/company-wiki push origin codex/n6-candidates` → 门禁在主检出（basetemp 49字符）完整跑并GREEN → 推送；随后 ls-remote 核验。主仓worktree文件零写（gate临时 `tmp/pp*` 由上下文管理器自动删除）。
- 遗留给MAIN：lane路径长度与门禁60字符上限的结构性冲突仍在（本批所有lane同理），根因修复属共享CI写集，本线只提案不执行；lane分支推送不触发CI（on.push.branches=[master]），CI由MAIN合入时触发，未擅自开PR。
