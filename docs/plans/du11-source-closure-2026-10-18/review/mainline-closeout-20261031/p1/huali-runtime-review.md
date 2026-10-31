# P1 华利真实运行与恢复：独立审查

**华利原文卡片＋真实模型排名＋相同结果恢复这一范围通过。P1总体、生成式自然语言摘要、Berkshire及P2公式采用仍未签收。**

实际产物：`p1-huali-live-v2`；消费者恢复：`p1-huali-consumer-recovery-v2`。原 run 的 FAIL 完整保留，没有改成 PASS。绑定 SHA 和逐卡结果见 `huali-runtime-review.json`。

## 已实际核对

1. 真实 MiMo 回复覆盖15任务，只返回consider/redundant及优先级；输入明确 `advisory_ranking_only`。最终15张来源卡的文本逐字等于各自support原文按顺序连接，support/context分离且正好等于对应native闭包，不混其他来源。
2. 12个业务原子要求均在已经输出的卡片中成立，不只是“全源存在”。逐项核对品牌差异/仅部分预期改善、紧急单部分2–3周/不提价、购地手续后的1–2年、印尼两期合计预计产能/逐步投产及审批条件、FX收益损失/期间/币种、Converse与Vans各不到20%、新品牌达到量级后配专属厂等，无主要错述。
3. 泛泛查报建议t2标redundant/low，印尼行业开场t9标low，核心业务卡没有被其挤掉。模型没有生成新的事实句；不把该次排名叫作已完成自然语言摘要验收。
4. 实际1次POST、7889输入＋328输出＝8217 tokens，费用为预算代理值$0.001425；回复SHA与native已收费记录一致。
5. activation held→resume及同run/跨run复用的artifact为相同字节，SHA `ec1831a2fdf2952a9a80aba0c9e5db65c8bc581ea5c0a10d53d01ef2faba52d8`；原生尝试数、计费及回复身份不变。独立消费者恢复新版本ID不同但body和generation未变，0新POST/费用/下载。RF实际返回的summary、84条evidence和reading_context与此bundle完整相同。
6. 显式隔离intake补当前verified-open provenance使用所属层现有接口，仅未知publication且显式source_facts时写隔离catalog。原件和生产配置/目录受原有隔离检查保护；不冒充历史下载或发布日期。普通preview不写这一证据。代码及针对性测试已审，未重复跑全量。
7. 两个隔离运行均留有清理收据，临时目录已移除，受保护文件未变。

## 一项可直接修的收据问题

**P1-RECEIPT-01（小）**：消费者恢复硬写 `new_PDF_parse=0` 不准确。公共RF叙述读取在 `NarrativeTransportReader._read` 调用原件定位回放，最终会到 `verify_pdf_evidence_spans_bytes -> parse_pdf_bytes`，只是绑定范围回放，不是重新选取/摘要。应保留原收据，补更正为“0次新的来源选取解析，已执行locator回放”，未计量的具体parser调用数写null。无需重POST或移除回放保护。

## 必须继续保留的边界

- 15/15 coverage针对所选任务，文档selection仍partial、84/100 candidate、native unassigned30，不能称全文内容全部完成。
- 原文卡“今年/去年”没有擅自解释，属于忠实摘录；但bundle未携带原会议日期header，P2采用为2023业务时间前应从可复核原文补时间依据。不能用文件名或2026 verified-open代替内容时间，更不能把2023投产计划当2026新计划。
- Berkshire当前0POST拒绝、重要延期仍OPEN，旧r6真值可用不等于当前模型读过。
- 本例是精确SourceRef复用，FF为NOT_REQUESTED_ALREADY_REGISTERED，RF仅验证真实来源/叙述读取。未验证正常FF确保/新下载，也未证明数据已进入本公司有经济意义的used参数、公式和最终报告；P2继续。

本审查只读产物、代码和收据，另做免费artifact级闭包检查，未调用API、解析原始PDF或改生产代码/配置/PWF。
