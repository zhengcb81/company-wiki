# untyped numeric quality：独立最终复审 v3

## 结论与边界

**PASS_BOUNDED_ENGINEERING_NODE**。本次仅验收未绑定数值形状、quality出口传播和其资源/缓存边界，不替ROOT签收项目正文、年报14组完整性、真实模型摘要或生产发布。

原正式15项不变，永久独立反控8项、独立公共probe11项，合计 **34 PASS / 0 FAIL，pytest5.91秒，exit0**。执行前后完整源码、质量section、shape函数、测试和缓存owner字节均一致。完整绑定在execution-v3.json及review-v3.json。

## 两个共因问题都已修并重新验证

1. **裸数字换行误当表格**：原英文/中文完整native正文的数字之间有真实词语接续，旧算法误标table_structure_ambiguous。新共享shape要求连续value-cell run，prose cell断开，dash可在run中但不虚增数字数。原两失败用例当前通过；真实行含尾说明、多run、简繁/英文、Tab/Pipe/Newline、百分号/币种格式/脚注/窄空格仍保持未知归属。无native carrier豁免、无单位或公司词典。
2. **未扫描伪造shape事实**：原budget-risk-red.json记录纯正文在quality预扣失败后被误写table flag且无资源诊断。ROOT现在复用既有_deferred_selection(parsed,effective_route)：真实work_budget_exhausted，needs_review/coverage不完整，0伪造span和0无计量扫描。永久反控从同一来源充分预算的实际used推导used-1，未硬编码旧数字。原文及locators不变。

## 实际公共路径覆盖

- 不注入预制selector结果；public select_reading_evidence运行真正pipeline。
- table未知标志实际进入citation及scoped model parts；约束不把未知列/期间/单位当已知。
- fully bound native table保持精确数字identity无新ambiguity；另一个source parent纯正文不会被污染，引用组不串source。
- exact native range保留真实source_unit_ids；来源raw/metadata/coordinates不变。
- 对table_shapes源码byte的内存指纹探针会改变真实public decision dependencies，恢复后完全恢复，选中证据不变；没有改磁盘生产源码。
- 16M/96/48k保持；模块__file__在pytest内锁定隔离worktree。

## 历史与清理

旧v1/v2失败与有限通过记录保留；reverse-red.txt只是当时请求名，首次永久反控实际已是修复后7PASS，不冒称跑过RED。真实原同断言RED为review-v1的2FAIL/24PASS；预算问题前修复观察在budget-risk-red.json。自有probe的预算断言随纠正后的资源合同更新，旧执行不重新绑定到新helper。

cleanup-v3.json再次核验四个实际重定位basetemp及请求路径都不存在。0原件读取/副本/下载、0模型/网络、0生产和Git修改。若ROOT之后改narrative_reading其它部分，这份旧完整文件SHA不能代表新文件整体；质量section和shape函数hash单独记录，ROOT最终大节点应重新绑定最终完整源码。
