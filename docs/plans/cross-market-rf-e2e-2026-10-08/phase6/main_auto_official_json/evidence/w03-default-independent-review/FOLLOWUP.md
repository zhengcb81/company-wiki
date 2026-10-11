# W03 列举语法补充：独立定点验收 PASS

2026-10-11。此结论对应新 policy `c7e900878cf3a21438ae53ee53cff01e6eecb8615a46468ef3ba70a49f0e852f` 和追加测试 `10b96c8fef3502d4348747ffb356ef6bd714f94512f155bf94102388d8d1f7cd`，不改写原 REVIEW.md 的历史 BLOCKER、原最小反例或任何 owner 原证据。

## 实际修复和测试

已完整读 owner HANDOFF-enumeration-supplement.md，实际 SHA `7ffc12e995972d5eba85efc0e871af2f77b4e46ad1cede4c5b5cf1ff54792e87`。实际源码只增加通用列举语法分类：`以及`优先完整分割，end-anchored `等/等等`及普通类别后缀从临时分类 token 去除。并非按公司/文件特例，不改 source/raw EvidenceSpan/locator；具体产品词中间的“等”（如等离子）仍保留。旧显式0.6不调用该业务扩展。

owner 新五案例真实 **3 FAIL/2 PASS/1.62s RED → 新5+旧20合计25 PASS/0.63s pytest、3.1432608s外围**；3file Ruff绿。全部7个补充证据索引 SHA已核对。早前122PASS仅属于早前快照，此补充没有冒称新快照重跑122/public3/whole suite。原五断言及14新增边界/原子案例均保持，groups SHA `7e1852eca0b041cecf0f9b97325e93d0f75bb452b5c0d26ee4139861402d60c0`未再变。

## 本轮实际独立重放

只用原生select_narrative_evidence、显式0.7、招股说明书类型，构造两个内存单元；没有pytest、数据库、下载、HTTP服务或供应商调用：

| 原文 | 期望 | 实际 |
|---|---|---|
| 公司产品包括各类设备及配套服务等。 | 不选通用类别 | needs_review、未选、PASS |
| 公司的产品包括工业控制器与电动执行器等。 | 保留具体组件 | selected、business_structure、原文完全不变、PASS |

原失败共因已消除，具体IPO业务构成正控保留。本结论不声称有限启发式语义穷尽。

## 保护、费用和冻结

13个精确source/test/TXT/config SHA以此新快照作本轮开始值，结束全部相同；不保护并行W08写集或全src。原 REVIEW.md/receipt/minimal-probe 三文件SHA保持。owner TEMP已不存在；本轮没有创建TEMP。0模型/供应商调用、0费用、0源码/测试/配置/原件/Git/安装写入，仅本自有目录新增本FOLLOWUP及receipt/native log。冻结交ROOT正常发布；不添加签收/许可/身份门。
