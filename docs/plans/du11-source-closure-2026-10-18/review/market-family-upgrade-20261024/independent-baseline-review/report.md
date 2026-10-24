# 分市场/文种baseline独立复审

## 结论

**三份FAIL混合了真实未选内容、观测字段缺口及金标问题，不能整体当作生产失败，也不能整体判假警报。**

四份原件SHA及阅读后SHA均一致。四份selected/mapped分别19/19、30/30、96/96、7/7；本次没有exact-locator helper造成的漏映射。该helper对0.9 native range的泛化风险仍存在，但不能拿一般风险解释本次结果。

## 每份样本

|样本|实际策略|有限结论|
|---|---|---|
|吉比特DOCX电话会|generic/unknown|真实漏后续存量运营、企稳不确定性及未落地更新计划；已选分析师问题保留说话人1/条件/问号，basis字面FAIL并不证明归属被篡改。|
|珀莱雅Q1|cn_quarterly/quarterly|唯一业务原因（回款减少、推广费增加、-84.16）已选；大部分财务值是correctness_if_emitted，不在required分母；元数据/未审计通道未观测。30片段中仍有大量常规财务/治理噪声可减。|
|金山云中报|hk_periodic/interim|分部收入百万元描述已选；总额/亏损/capex及千元/汇率完整定义未选。按USGAAP的片段存在但完整编制基础缺失。强制财务精确值进叙述分母需对齐项目职责。|
|微软EX99.1 HTML|presentation/presentation|FY27两段组织结构已选；bookings/RPO定义、旧指引机械调整及Azure新定义恒汇率展望确实未选，原HTML可读，不是图像不可读。|

## 必须分开的测量问题

1. research脚本读reading_context.route，但实际没有该key；应记录真实reading_policies/profile。route=null不能证明未路由。
2. 未生成claims，无compiled tasks；不得用basis FAIL宣布数字幻觉、公司误认分析师问题，亦不得用全文片段在场宣布局部限定已完整。
3. must_preserve中的“说话人1/分析师提问”“如果…趋缓”是编辑注释，不是原文的字面字符串。实际已选问题有“说话人1”、完整条件和问号，仍会触发假FAIL。
4. 吉比特原ASR“买量会不会再走到原来的水平了”不能不核音频就强判明确“不会”。应保留歧义，不能训练/修代码去满足错误确定性。
5. 金山云capex替代support“折旧摊销449.5百万元增加”不足以证明现金购置设备数；珀莱雅扣非替代support单纯标题也不足以证明精确金额。需独立审gold语义充分性，旧gold不改。
6. 金山云分部收入允许百万元替代support，但must_preserve又要求精确千元；替代锚点召回与数值精度/限定不能混为一项。
7. 元数据没有context_evidence，NOT_EVALUATED是未观测；珀莱雅critical required分母0不意味着整个文档正确率100%。

## 每项critical原文→已选

逐项真实SHA、anchor原件验证、selected locator及语义/角色限制见report.json：共26项critical，全部以原gold不变进行检查；非字面相等仅作定位辅助，不自动代签完整语义。

## 下一步共因

优先完善研究观测完整性与语义金标，再用真实输出修通用连续句/说话人/指标定义与限定依赖。用策略配置覆盖不同文种，不按公司或固定金额特判；精确财务数按需SourceRef/API取回并证明采用，不为分数全表切片。

只写本独审目录；没有下载、模型调用、产品/gold/PWF改写。原件仅SHA与定向文本读取，不是视觉/OCR验收。

## 复现边界

这份research baseline未封存执行时完整source tree/parser代码SHA；本独审绑定现有产物和当前observer/replay文件，不能冒称已验证最初执行的完整代码版本。这4份旧DU5 holdout已用于诊断，后续同源调参复跑应算开发回归，不能再冒充未见公司holdout。
