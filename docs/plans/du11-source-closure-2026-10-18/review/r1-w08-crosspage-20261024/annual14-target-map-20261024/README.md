# W08：报告规则分类、断言边界和完整14目标链

唯一当前入口仍是母PWF CURRENT_STATUS。本目录只保留本节点的必要证据，不是新队列、许可链或第二套投资研究状态。

## 已完成的共因修复

1. 按“金融报告对象＋处理关系”区分外币折算、套期会计和信用风险评估规则，避免泛风险/管理词让它们占用经营片段。纯金融名词不是充分证据；真实客户平台、产品用途、交付和收入汇率风险继续保留。
2. 完整clause保留真实经营断言，不删除匹配文本。评估条件中的前置/后置“是否、能否、whether、if”和共享问题列表不能冒充已经发生的经营事件；明确已完成观察和转折断言另行判断。没有公司、页码、金额或产品名特判。
3. 新规则模块注册到现有 decision_inventory 的 `business_algorithms` 字节依赖，规则独立变更不会复用旧决策。没有新增版本许可、人工签收或任务库。

## 实测与边界

| 证据 | 结果 | 范围 |
|---|---|---|
| `independent/report.md/json` | 320 passed，0 failed/skip，5.19秒 | 21独立语义反控＋33作者语义测试＋107原用途测试＋155旧版兼容＋4缓存反控；绑定最终4份源码/2份作者测试SHA |
| `natural-receipt.json`、`natural.xml` | 2302 passed / 11既有skip，51.32秒 | selection/structure/root、DU11两整包、跨页/异构材料、缓存和版本；373份源码运行期间稳定 |
| `cache-dependency-green.xml` | 58 passed，13.94秒 | 后续依赖注册的库存/cache回归；先复现只改新规则字节仍被判same的RED |
| Ruff / mypy | 通过；373源文件0错 | 最终发布前再次检查，正常hook和精确CI另留发布收据 |
| `selection.json`、`trace.json`、`replay-receipt.json` | 原文249页、1526候选、96片段、7689字符；8845814/16M | 同一个WorkBudget完成parse/select；0下载、0模型、0raw copy，生产配置/来源DB原SHA保持 |
| `model-view.json` | 55任务；A12前提在同任务 | 真实production scoped compiler的离线可见性；没有发送请求/审模型响应 |
| `content-review/report.md/json` | **7 pass / 5 partial / 2 missing** | 原14项gold未改，19个原页字符区间逐字匹配；selected与fallback严格分开 |

自然包在cache依赖注册及最后业务结构guard之前，旧收据如实保留。最终源码经320项独审；`final_source_recheck.py`又实际只读原SourceRef，`final-source-selection.json`与先前已独审材料的SourceRef、全部96个EvidenceSpan/原文、task-local groups、55任务成员逐项相同，见`final-source-receipt.json`；本轮内容分数经此完整等价桥继续适用，未篡改旧SHA收据。发布最终版的正常pre-push另行验证。`natural-receipt.initial.json`保留更早2297P/11skip历史，也不能当最终代码验收。

最后补漏：公开的业务结构helper必须带原业务事实路径已有的`_OBJECT`条件。否则会计方法“consists of …”会绕过规则分类而成为unknown；两条自然反例先2F后GREEN。修复恢复原外层条件，不改变旧_business_fact行为。

## 诊断得出的下一行动

`target-map.json`先从V5冻结材料、原页字符偏移和实际budget target行确认A01/A03/A04延期，不以aggregate统计倒推。之后`replay_all_targets.py`复用旧观察器，扩展原14项来源引用，捕获72个原始目标单元及admission/候选/依赖/offer结果。完整trace的 `candidate_count=470` 是最后一次candidate回调，不是整份package的1526；不可用未观察阶段代签完整闭环。

本轮移除7个旧片段、加入7个新片段，但独审gold **没有净改善**：位置被治理、通用战略和确认规则等补上。A01完整业务范围、A03客户地域、A04集团订单仍缺；A05 Chemistry父级与子业务、A09日期/容量仍分任务。下一步应TDD修**共享语义包排序与边际闭包竞争**，随后修真实父子和日期局部依赖，保留原96/48000/16M与8/4/2048，不继续只补几类模板。精确财务数可按需从原SourceRef/API读取，但没有实际读取采用就不能算gold满足。内容闭合后再正式摘要/cache、W09/W10实际采用矩阵和W12四审。

## 复现及必要修复记录

- `diagnose_frozen.py`只读冻结V5和既有原页摘录，不重解析原件。
- `replay_all_targets.py`的完整命令保存在`replay-receipt.json`；固定旧SourceRef/原gold，从当前指定代码根只读解析。首轮旧观察器的缩进JSON达562377B，超512KiB真实失败；只移除格式空白后一次重放468115B，未删观察或提高上限。旧有效selection与最终业务片段完全相同，已用小收据`observer-overflow-receipt.json`去重保留。
- `compile_model_view.py`复用已跟踪观察器和production compiler，仅投影任务成员，拒绝覆盖冻结输出。
- `run_natural_suite.py`声明全部测试范围与短TEMP，记录源摘要和恢复；`cleanup.json`确认仅清本节点创建的scratch，保留其他WIP、原件、旧封存和费用账。
- 独审最初8项失败、后续判据语序/列表/转折反控和修复均留在报告中，没有删旧断言换绿。cache测试首版缺carrier的fixture问题与随后真RED也写入母progress。

本节点代码发布不代表公司分析通过；整体主线目标继续ACTIVE。
