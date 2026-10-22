# W03-A RF consumer 非作者独立审查

**PASS_ENGINEERING_CONSUMER_ONLY**。独立新反例 **26 PASS /0 FAIL /0 SKIP，0.47秒**；未发现需要作者继续修复的产品问题。作者的47例及296P不是本报告的独立证据。

## 版本与独立性

RF产品 `b76fb96f9b410abceefc6b264120c5101654492b`（含6efbebc3）；作者工区HEAD `43b5d2429a76bfb7b887144c4dd8b7c4a12190d4` 仅后续文档，产品字节相同，tracked clean。唯一改动runtime文件 `scripts/company_wiki_narrative_contracts.py`，物理SHA256 **`0af725599bda25c883a040605a20e1bc2d3204de0a032ce1116f8c2b0e248ac6`**。完整diff已读，运行前后此文件与独立测试SHA不变；LF映射和Git blob绑定见[机器报告](r1-w03-rf-independent-20261022.json)。

审查人未编写或修改RF产品及作者测试。独立测试直接读取已公布的静态golden字节，不导入作者test helper，不改artifact内容。仅写本报告和[紧凑证据包](r1-w03-rf-independent-20261022/README.md)，未写母PWF或安装副本。此报告不自审该审查人编写的CWP producer；其独立接收由ROOT负责。

## 26项检查

| 检查点 | 数量 | 结果 |
|---|---:|---|
| prior/archive/current-open三个合法同SHA proof，null publication和完整read_receipt保留 | 3 | PASS |
| 坏schema、错SHA、物理路径、额外许可字段、非法日期、错误basis类型 | 6 | 全部拒绝 |
| 历史模式unknown pub且proof省略/null | 2 | 仍source_publication_unknown |
| 已知未来/非法pub，即使同时给错误的更早proof | 2 | 旧日期拒绝优先 |
| proof晚于as-of | 1 | 拒绝 |
| 实际read_at早于资格proof，或retrieved_at晚于实际read | 2 | 复用source_clock_conflict拒绝 |
| 旧current模式省略/null proof，unknown或未来pub | 4 | 保留原当前读取语义，不追加historical gate |
| current模式实际提供proof：合法与晚于实际read UTC日 | 2 | 正确通过/拒绝 |
| 已知早期publication不被更晚capture替换 | 1 | PASS |
| projected receipt/3给单parent根proof（含null） | 2 | 原精确字段合同拒绝 |
| 实际有界RF reader child输出完整合法wire | 1 | proof精确保留，pub仍null |

产品继续在既有ref/manifest/请求绑定后调用公共source_clock，没有二次原件hash、公司身份库或审批签收。optional只增加在raw receipt/1，既有raw2.2 lineage规则未动。当前提供proof时复用实际read日和actual-event规则；省略/null proof的旧current路径不增加历史要求。proof不进immutable body、模型输入或cache identity。

## 工程证据与清理

[receipt.json](r1-w03-rf-independent-20261022/receipt.json) 保留实际argv、UTC、解释器、环境和退出码；[results.xml](r1-w03-rf-independent-20261022/results.xml)及日志保留26例。一次真实子进程使用公开静态wire，未启动真实CWP原件处理、下载或模型；**0 API、0下载、$0**。

独占 `.planning/r1w3r` 初始不存在，结束后已按解析绝对路径确认只位于该自有根并删除，恢复不存在；数量与字节见[cleanup.json](r1-w03-rf-independent-20261022/cleanup.json)。未删除或改动生产原件、其他owner材料或RF工作文件。不声称未测的峰值已通过。

## 结论边界

本报告接收单文件consumer工程边界。projected两例仅证明收据精确字段不能接受root proof，未冒称完整多parent内容语义已验收。ROOT另行执行真正CWP producer→RF公开CLI组合、定点安装、并线发布；先兼容consumer再producer。W03-B实际0.9/v5内容、W07正式摘要/普通paid恢复/cache及RF真实used参数公式消费仍需后续实施，本报告不代签。