# 最终复审 v5：来源优先级质量检查与调用内观察

## 结论

**PASS_BOUNDED_ENGINEERING_NODE，当前有效结论只绑定 e03e20ab0d7bf320102c9245ceb8df37e96da3c9c3dd96ce3b61e6451fdeb575。**

最终实际 **44 PASS / 0 FAIL，pytest18.45s / process24.66s**：原正式15、永久独立反控8、独立公共probe11、原20k保护1、两条原pipeline纯度测试函数实际9个参数。事前曾估13个纯度参数，实际收集9，按JUnit/console真实44记，不声称13全跑。

源码、入口质量预扣section、出口质量投影section、完整_candidates、shape函数及全部测试在execution-v5.json前后字节完全一致。无旧收据签新文件：v3全文件f654189d、v4全文件0da06520均是历史；最终仅e03有效。ROOT后续若改源码应重新绑定或按真实字节差异做补充审查。

## 修复的是责任层与资源生命期

- shape仍是纯文字格式判断，连续数字值run才观察为cell；完整native散文数字换行不伪装为表格。
- 质量与事实入口同按既有reading priority消耗同一个WorkBudget；每个实际required来源单元/carrier只计量检查一次。标题、限定等真正引用成员也受检查，不只扫anchor。
- 未检group因实际资源不足延期，0真实helper调用、0伪造table flag；不把资源不足说成发现了表格问题。
- 已检高优先级来源保留，后面的低优先级耗尽不能在出口重新收费并撤销整个结果。出口只投影实际观察；完整native table的正向结构证明仍保留。
- 观察只存既有本次调用_session_state；不是改格式pipeline、不是新任务库或全局缓存。原始ID/locator、精确carrier映射和跨parent边界不变。

## 旧20k断言未改

实际读取baseline b6395b6c的Git blob，与当前test_reading_production_selection.py做LF归一比较，**完整文件相等**。保护函数SHA均为5e4dc91827d528915071f731aaaa1dcc7ebc1f8ea02bb75d819b44e081298278。

原用例真实20,000个canonical source units和供给的ReadingPlan seam，末三项priority1，预期仍全部入选、candidate_count/omitted/status不变、reading_context仍受64k约束。当前通过。它不是20k原件解析验收，不夸大测试范围。

## 为什么预算反控随架构更新

旧v3全局末端延期可以避免伪标，但集中节点发现其丢掉先前已验真的重要prefix；不能改旧断言或提高预算来维护该方案。反控因此从“整体total_used-1碰末端”改为观察真实has_unbound_numeric_cells首次调用时已预扣的共享used，再用used-1拒绝该真实预扣。保持不执行扫描不伪造质量、准确资源原因和原文不变，没有绑定特定阶段位置、没有硬编码成本。精确旧v3新test已保存prior-prose-controls-v3.py，历史失败/有限通过记录保留。

v4的35项在0da有限通过后，完整测试又暴露把临时观察写进pipeline的纯度回归。最终e03把它移回_session_state，本次加原纯度断言并实际复跑；这说明集中节点测试补足了有限审查，不删除旧断言换绿。

## 其余边界及清理

未知数字在实际citation/model质量和约束中保留；不猜列、期间、单位或币种。完全绑定表正控不误标；另parent纯正文不污染。对shape源码bytes的内存变更会改变实际public decision dependencies，恢复后完全一致，无磁盘生产修改。

全部测试内检查模块__file__属于隔离worktree；保留16M/96/48k，0原件/下载/副本、0模型/网络、0生产和Git修改。cleanup-v5.json再次确认六次实际重定位basetemp和请求目录均不存在。

本结论不签收项目正文全量泛化、真实年报14组完整性、正式摘要、RF联调或生产发布；这些由ROOT后续大节点验收。
