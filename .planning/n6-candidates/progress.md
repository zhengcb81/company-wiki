# N6-CANDIDATE Progress

2026-10-06 MAIN创建独立worktree及启动文档，分支codex/n6-candidates；卡ready，尚未由人类宣布分派。所有代码仍固定基线，后续由本harness记实际进度。

2026-10-06 本harness施工记录：
- 核HEAD 81d4524（=基线58b74d0+启动文档），工作树干净；INPUT_CARD.md与源仓最新卡同步（S07境内口径）。
- 阶段1：读4模块+共享只读（narrative_evidence/pdf_groups/finalize/budget/document）；基线实测required金标：15个assess层MISS、反例全部MISS/dropped。RED命令（卡原文）：18 failed / 12 passed / 3.24s。
- 阶段2：新增 n6_candidate_operating_facts.py（10个通用检测器+OPERATING_FACT_JOIN）、n6_candidate_completion.py（句内补全+1600/1200常量+linkable）；改4模块（见changed_paths）。GREEN（卡原文命令）：30 passed / 0.99s；ruff（卡原文命令）：All checks passed。
- 既有相关短测试（未改动）：test_narrative_evidence + test_narrative_selection_architecture + test_narrative_english_business_recall + english_operations + pdf_bytes + retrieval + select_handler + verify_handler = 181 passed；连同新测试合计211 passed / 2.91s。
- 阶段3：真实样本8份原件（S01-S04,S06-S09）先SHA核对后parse_pdf(table_pages=目标golden页)/parse_transcript_text → select_narrative_evidence全管线回放：目标14点全部在候选层恢复（14/14），9/14同时进入96/160预算选择；原件终检sha/size/mtime全不变；0下载/LLM/付费。tmp临时脚本与产物删除，pytest basetemp目录由fixture自动清理并验证absent。
- 旧断言冲突：无（181既有测试全绿，未修改任何旧文件）。
