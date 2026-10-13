# W08-AUDIT ROOT 修后独立试读

2026-10-13。只读工区 `C:/Users/郑曾波/Projects/_harness_worktrees/w08-root/audit`，ROOT分支 `codex/root-w08-audit-20261013` 未提交候选。读修后 EvidenceReader、numeric计数、report binding、event pairing、13项边界测试及真实CLI `e2e-final.json`，不重跑全套。独立脚本 `postfix_probe.py` 跑7个有界合成包，每例独占临时目录并恢复；实际JSON `postfix-observations.json`。零付费、未修改ROOT/作者/DU。

## 已修好的核心项

有限整数/finite秒限额及默认最大值已兑现；读取最多cap+1、溢出不返回完整SHA/正文。读取统一resolve，pointer下调实际执行。shared locator允许，value ID与unique reference分开显示，不把共用证明当经济错误。实际报告已知 run/role/显式attempt有mismatch诊断；错误事件身份/不同captureID均已实际抓到。结果始终quality_status=not_evaluated，没有新增许可、签收或预测阻断。基准独立包：MATCH、matched1、unchecked为空、numeric3。

## 剩余明确缺口（建议同批补小量行为，均为诊断）

1. **未知报告绑定未进未核查摘要**：真实当前 `storage.json={}`，row.binding_status=UNKNOWN正确，但unchecked=[]。坏JSON或缺run/role同样应留当前报告binding未核查，而不能只在深层字段显示未知。未知不改成MISMATCH、不要求补hash/人签。

2. **legacy事件分类被丢弃，run未知仍当本轮绑定**：移除storage的真实两行event.run_id，其余保留；既有parse_event_observation回legacy_native_event/observation_only，但summary忽略返回classification，matched_calls=1且unchecked=[]。可保留真实ID配对的事实，但另报legacy/unknown_run counts并在unchecked明确run binding未验证，不强迫旧事件升级canonical。

3. **显式旧review_attempt事件未隔离**：当前reports attempt-1均正常，两行event.data.review_attempt=old-attempt，仍matched_calls=1/unchecked=[]。没有attempt字段时不应推定没工作；有明确不同值时应单列旧attempt、排除本轮绑定或标run-only匹配。当前API需将已有review_attempt作为比较上下文，不新建身份解析机制。

4. **日期行被当算式位置**：V1.recompute指向仅一行`Published 2026-10-13`的真实文本，行范围可解析，但numeric_observation regex把连字符当减号，因此recompute_rows_observed仍3且V1不进未解析数字列表。工具不重算经济公式是正确边界；数字已定位应基于实际数值/显式表达式形状，日期/元数据文本不能通过。建议把数值观察kind写清楚，真正的公式/有限数值和任意数字出现分开；非支持形状诊断即可。

位置分别为：`review_evidence_reconcile.py` unchecked组装、`review_evidence.py` summarize_events（parse_event_observation返回值未消费）、summarize_events/reconcile的attempt比较上下文、`review_evidence.py` line_range numeric_observation。

`postfix_probe.py` 的case依次baseline、unknown_actual_report_fields、legacy_events_without_run_id、old_explicit_attempt_events、date_line_is_not_recompute、capture_id_pair_fixed、stale_run_event_fixed；输入改变与真实output全部保存在同目录。最后两项已变绿，前四需上述语义补齐。

报告实读MATCH只能说明已知字段一致，不能证明payload声明与磁盘checks/findings完全一致或真实agent执行；当前输出quality_status与limitations没有冒称这些质量真值，应保留。不建议增加每行经济复算、真实模型大测试或新小节点门禁。ROOT已有集中测试和C真实CLI证据足够；补上述四个纯本地反例后即可完成本卡的离线工程接收。
