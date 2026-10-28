# Observer task-level gold 窄修复交接

已冻结，供ROOT独立审查；完成当前手头后按用户要求停止，无真实摘要/PDF/模型运行。

实际反例见cached-counterexample.json：真实v2 cache中行业云第一条原anchor作内存control，full view旧oracle支持；只发送t1、不含该anchor，旧oracle仍支持。未改gold、不冒称完整4-anchor事实已通过。真实group34→t35确有p13:9–12四support+p13:1标题context，wire来自同一compiler。

修复保留旧顶层可用性字段但明确full_selected_source_availability/full_selection；新增sent_tasks，逐actual compiler task沿原group复用score_facts，记录supported_task_keys/not_sent_ids，claim coverage明确not_evaluated。首发完整请求以实际sent任务缺口在原paid caller/reservation前拒绝，initial subset非法；repair仅如实报告当前发送，不强求已完成的全gold重复。

新unit中性6项真RED（3.39s）→新6+旧纯观察4项共10P（3.74s），正常宿主Conda；Ruff和diff检查通过。未跑本地HTTP、PDF、Docling或模型。原oracle数字/CJK边界由另一owner处理；本作者不改source规则/gold。

- `tools/document_understanding_benchmark/phase_c_observer.py`：LF `8f2c44ef2b63b5a434c3789111388edb8a3e3f3065a5b3ce17fbe7243ca46930`；raw `f4457f7a0a3aa58e60840c6090b77a1ae2036348a6b55068b539305ee298ca8c`
- `tests/unit/test_phase_c_observer.py`：LF `18a5cfc93d3e43990babed08144fe4ba38a617d960ba1d3faf9d9d06c7e72a4b`；raw `18a5cfc93d3e43990babed08144fe4ba38a617d960ba1d3faf9d9d06c7e72a4b`

精确正式入口/预算/新runtime metadata revision/收费与恢复边界在../formal-next-readiness.md；它只是恢复后的操作提示，不是启动授权或内容PASS。ownedPID11856/12080终态不可见，两个tmp根已清。ROOT独审/发布暂停交接前，本作者不再编辑这两文件。
