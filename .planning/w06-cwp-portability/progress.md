# progress — W06-CWP-PORTABILITY

## Session 2026-10-11
- 勘察：worktree 就绪（codex/w06-cwp-portability @ 01ea86a3）；handoff input（construction_card/handoff_contract/inputs.json/ROOT_INTERFACE_AMENDMENT）读毕。
- 实读 source_reader.py/config.py/service.py(store/resolver/scanner/registration_scope/admission)/source_export_v2_cli.py/source_reader_cli.py/source_export_v2.py/document_kinds.py/models.py + test_default_steady_source_reader.py。
- 关键发现：真实方法 open_version(ref, purpose=...)；source_id/document_id 由内容 SHA 派生；非 focus 扫描会把 .source.json 注册成独立文档（fixture 用 routes 规避）；import company_wiki 落到主仓（需 PYTHONPATH 绑定）。
- PWF 三文件已建（task_plan/findings/progress）。
- 阶段A：oracle stub + 22 反例测试 → RED 19 failed（logs/red-oracle.log）→ oracle 实现 → 22 绿。
- 阶段B：fixture_builder/consumer_spy/scenarios/report/run 实现；33 测试绿（logs/green-unit-integration-final.log）。
  调试记录：① sidecar N-02 缺 period → indexed_only/incomplete（改用 nonperiodic 标记，F14）；
  ② 审计钩子用 extract_stack 递归崩（改纯帧遍历+重入锁）；③ 归属被钩子自身帧抢（改任一 company_wiki 帧优先）；
  ④ open_log 200 条被启动噪声占满（只记 raw/catalog 类）；⑤ in_process 计数在 reader 重建时清零（累计属性）。
- 阶段C：E2E attempt-0001 FAIL（oracle 抓 S4 记录缺 content_sha256 字段）→ 修复 → attempt-0002/0003 PASS
  （0003 为最终：7 场景 PASS、oracle PASS、7.4s、source_read_calls 51、HTTP 0、清理恢复基线）。
- 交接阶段进行中。
