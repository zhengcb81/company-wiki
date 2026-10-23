# W08 预算基线接入交接

## 状态

MERGED_NOT_COMMITTED_READY_FOR_ROOT_REVIEW。正常三方合并 ab95027b 到 W08 1712ed10，MERGE_HEAD 保留，未提交、未推送。唯一冲突为 decision_inventory inventory 版本行：保留 W08 1.9.0 与原实际源码 closure，同时加入预算 document_work_limit 依赖。narrative_reading 自动合并，partial诊断与未完整inventory均保留。

## 现有材料保全

事前逐一冻结370个 dirty/untracked 文件，共5,969,379字节；事后370/370内容、大小、SHA完全不变。唯一原 tracked dirty仍是 narrative_business_policy.py，仍未暂存；77项measure正式测试和20项guidance正式测试仍untracked。没有stash/reset/revert，没有将旧失败包装为通过。before.json与preservation-after.json给全表。

## 有限测试

合并后预算70项 + 因果inventory/共享工量 + 77项measure，合计335PASS，15.30s。独立重跑guidance为原7FAIL/13PASS，2.01s，完整失败节点保留guidance.xml/txt；这是预存开放功能缺口，不是预算整合新增失败。没有跑全仓重门；未宣称全源/正式摘要验收。测试均断网、无真实LLM，并assert实际import来自本工区src。

所有本次请求/实际重定位basetemp已清理并验证不存在，收据bounded-execution.json、guidance-execution.json。没有删除历史pytest目录、诊断材料、原件和配置。

## ROOT下一步

先独审本次有限三方整合及measure实现。待决定提交时，只stage本次合并tree和确实完成的measure代码/测试/收据；开放guidance不可冒充完成。当前index已是正常合并生成的incoming变更并解完冲突，MERGE_HEAD存在；可用正常commit完成merge，不要reset或再次merge。母仓CURRENT_STATUS与作者W09/W11工区均未写。后续继续guidance、跨页、真实annual14和摘要/恢复/RF验收。

## 文本检查实况

source/config/tests/tools 的 staged diff --check 通过；全 staged 检查提示 incoming 历史 w08-red-design-20261022.md/json 两个额外 EOF 空行。未擅自改写历史绑定报告；全树检查不记 PASS，原输出保留 diff-check-full.txt。正常提交如确需规范这两份历史文档，由 ROOT 决定并记录，不能冒称预算代码失败或取消质量门。
