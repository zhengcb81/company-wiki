# 中微公司 CN-688012：v3 独立复查

## 结论

**模型：ACCEPT_WITH_LIMITATIONS；产品端到端：PARTIAL。** 原CN-01、CN-02、CN-04已关闭；CN-03的标题冒充完整覆盖问题已修，但存在明示的资料/目标缺口，不能签所有目标齐全或完整产品PASS。没有发现新的金额、期间、合并范围或数值计算错误，也无新增阻断修复问题。

这次只检查v3变更及其依赖，原v2初审不改。全部106 claims逐条定位，74条改/新、28个独特上下文；42参数数值未改，逐条检查实际支持方向。新增9份PDF共59页独立重新提取并完整阅读，4张关键页实际视觉读表。19条公告逐件重要性理由与已读/未读状态核对。

## 问题关闭

| 原问题 | 结果 | 核对内容 |
|---|---|---|
| CN-01 残差当售后/确认政策当增长 | CLOSED | 分部改NonEquipmentResidual；9未来路径、驱动、确认和九维一致。业务存在只作背景，残差构成/增长未校准如实标明。保留旧parameter ID不改变语义。 |
| CN-02 引用范围和反证错配 | CLOSED | 39.99%/22.15%绑定9future验收量；SEMI2027/28及中国放缓节点；TSV封装补齐；p32供货交期、p33研发替代/并购分别收窄范围；HQ部分楼层可用与全面可用2027-12并存，未机械减销量。 |
| CN-03 公告只读标题却checked | CLOSED_WITH_VISIBLE_GAPS | 19条逐件triage；8公司公告+1券商意见全文分清。资金/借款/预计交易额不等于收入。300000万元达产属地销售登记目标且不入年度预测；激励原schedule没取，明确缺口。 |
| CN-04 H1 URL旧UTC查询 | CLOSED | 标准append-only事实校正；独立再走RF→FF→CWP，官方8月20日URL/date、0新下载、原件3149962B同SHA。 |

达产计划原文为300000万元（仅换尺度为3000百万元），未给达产年份、年度/累计和集团外部边界。紧邻“7年内”是专利计划，不能给销售安上年份。新版ambiguous/empty measurement_periods/mismatch/unmodeled_data_gap正确；投资350000万元没有加进收入。

1225482918上海众硅2025单体24411.88万元收入并不是AMEC2025并表CMP收入0的反证，二者公司与合并范围不同。1225482917客户2/3是董事担任董事的关联法人；预计增加20000万元至110000万元是预计交易额度，非保证已验收营收，也非默认集团内抵销。

## 正式结果复查

- 83件v3交付SHA/bytes正确；旧v2 input、forecast.json、forecast.md、snapshot_v2和原manifest全部未变。20对新增命令日志完整，3次失败尝试保留。
- 27分部年度场景、9公司年度场景、增长/CAGR/增量/桥接、4敏感性、4驱动分配独立重算；非交叉与H1下限正确。
- 原input强校验、same-source Markdown、snapshot frozen input/经济载荷、新独立TEMP CLI完整JSON和MD精确重现、publication registry audit均绿。4目标的6benchmark比较另行复算。
- 9个installed/canonical runtime文件与manifest相同；4配置及SKILL基线SHA保持。审查无LLM费用、无邻仓/Dayu写入。

## 剩余范围：继续记录，不能涂绿

1. 生产CWP narrativeWorker未跑，TEMP解析不能替代canonical选择、摘要和质量派生。
2. 最新官方IR-DOCX/presentation及正式中文电话会TXT未取得；SSE问答是另一路，不证明ET中文端到端已测。
3. 1225482880 p6说明存在收入增长考核，但原激励schedule的阈值/年期没取。故**不能保证所有重要目标已抽取**。
4. 非设备残差拆分、量价proxy和情景幅度未实证校准；驱动权重为分析者分配。可以用作透明条件预测，不能当统计概率或已验证准确率。
5. 达产目标范围不清，留unmodeled合理；后续有正式协议/口径才能比较。
6. 九辅助公告由SID下载到research TEMP，未实走FF→CWP统一入库/SourceRef。执行者已区分，不冒称该产品链路成功；全面统一存储仍需后续测试。

## 复查产物

recheck_v3.json包含全部关闭/剩余项；v3_all_facts_semantic_recheck.json为106claims、42参数和19公告逐项；v3_independent_target_checks.json为4目标比较；v3_independent_calculations.json与v3_formal_independent_checks.json为独立数值及正式重现；commands/index.jsonl和v3_independent_nested_commands.json保留实际进程、退出、输出字节/SHA。原初审文件保持。
