# W20-AUDIT返工第二轮ROOT复验（2026-10-29）

**结论：原R2已关闭，原R1部分修复但仍有一个P2共同根因未闭合。建议只把R1的剩余范围退回原harness；不增加新审批、不重开已通过部分，不并线/安装本包。**

## 本轮确实修好的内容

实际HEAD `da17f2b5b4404c650e77671601e10553b879d2e7`，代码 `4ed94fcce99135d7c45ea1f16b5f0ed013b77313`；之后只交接/PWF/返工独审文档。工区clean，交接清单20文件SHA全匹配，观察器SHA `6b1dae0edbf45de4e9fe347fa6664e04e83f5819cc5d1d973f9f2346022006a9`。原初审/原RED保留，作者返工独审为APPROVE/0 OPEN，ROOT并未据此直接签过。

ROOT真实复跑原7条独立断言 **7通过**（0.321秒wall）；作者W20 **35通过**（0.390秒wall）；既有numeric **7通过**（0.599秒wall）；公开离线synthetic CLI **11步成功**（3.954秒wall），records_complete/0 gaps。未重跑121秒全仓。原比例/金额、负号、日元→人民币、H1/H2具体错误均已改正。

R2共享`_available_fragments`在公共锚点入口一次计算显式read/非空文本，standalone与packet一致，unread保留文字不再提供正向锚点，元数据/context仍保留；**本轮确认R2关闭**。

## 原R1仍未闭合：typed约束没有绑定同一个数值

责任文件 `skills/revenue-forecast-audit/scripts/summary_checkpoint_observations.py`，L298–300与L316–324。

### A. 明确的金额单位被正文中另一个百分比覆盖

输入claim `text="收入1000元，同比增长10%"`, `value="1000"`, `unit="元"`，支持原文 `收入1,000元，同比增长10%`。当前value anchor竟是 **anchor_absent**，不是原值确实存在的literal_match。

L298对`_scale_tokens(unit_text)`空结果直接退回整段claim text；合法scale=1的金额单位`元`与“没有声明单位”被混为一谈。正文增长率`10%`把整个claim value归成ratio，随后源金额candidate被拒绝。参数化`1000/1,000`、`2500/2,500`、`-1000/-1,000`三例全部失败；并非特定公司/用词/数字。

### B. 错币种金额可借同段另一笔金额的币种

输入claim `value="12.5"`, `unit="亿元人民币"`，原文 `收入USD 1,250,000,000；人民币余额2元。`。当前value anchor报 **scale_equivalent**。这里美元12.5亿不能无FX变成人民币12.5亿，余额2元的人民币不属于该美元金额。

L316取整个fragment的currency families，与claim币种做交集，错位候选因另一个金额的人民币token获得full。参数化CNY claim/USD候选、HKD claim/CNY候选、USD claim/HKD候选，均由同段另一个小余额捐赠匹配币种，三例全部失败。不是要求semantic投资判断，而是typed numeric比较的币种对应不能串值。

## 共因修法与验收边界

两类仍归**原R1**，不拆新工程：显式unit的identity scale与未声明unit分清；金额class不能向claim正文别的增长率借值。源候选的value/scale/currency保持同一局部对应，混合币种不能确定绑定时保留unknown/partial，不能从整段token交集签full。可保守处理含混输入，不要求无限词典或LLM判定。

复用现有numeric owner的显式typed兼容能力，避免复制规则漂移；**是否调用某个既有函数本身不是独立阻塞项，阻塞来自上述实测错误。** 字面数字token出现可与typed等价分开，不能把机械免责声明当错误等价的豁免。没有新增权限、来源重新签收或资料外发请求。

[本轮参数化可运行反例](evidence/audit/test_typed_binding.py)共4测试方法：2正向控制通过、2负向方法下6个subcase真实RED；[日志](evidence/audit/new-red.txt)、[收据](evidence/audit/new-red-receipt.json)。原7条期望保持全绿。建议将这两类参数化反例加入作者测试包，修共因后仅跑W20/受影响numeric及一次离线CLI，再由真正独立agent检查最终代码及SHA后新交接；不必再全量检查、不重开R2。

辅助观察（不另立阻塞）：`decimal↔percent`已有numeric能力在新class映射中仍未复用；该诊断可帮助改共同owner，不强迫为本包新增生产字段。生产者claim缺少锚点字段仍是此前明确ROOT followup，不转嫁本卡。

## 测试隔离与证据

所有新测试只写总控自有 `.planning/w20-reception-r2-20261029/audit/temporary`；原不存在、结束恢复不存在，45自有文件、清理前235818B已删，peak未采样保持unknown。只保留小脚本/JSON/日志，无真实资料副本、下载、付费、密钥读取、作者工区改写或安装。详细[机器报告](audit-review.json)、[测试](evidence/audit/tests.json)、[清理](evidence/audit/cleanup.json)、[20文件SHA](evidence/audit/sha-verification.json)。所有反例synthetic，不冒充真实公司预测/四agent研究或公司循环完成。
