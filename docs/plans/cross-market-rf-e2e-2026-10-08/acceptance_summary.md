# 三市场真实 RF 执行与独立审查归总

**审计任务完成；三份条件预测可接受；完整产品端到端仍为 PARTIAL。**

信息截止日2026-10-08。三个执行agent与三个独立审查agent身份分离，失败、修正、复查均留存。工程记录在CWP；预测及不可变快照交付在RF output，不成为CWP投资研究状态。

## 逐家公司结论

| 公司 | 本地复用与新增资料 | 最终模型 | 产品全链 | 最终独立审查 |
|---|---|---|---|---|
| 中微688012 / CN | 本地2025年报；缺失2026半年报经RF→FF→SID→CWP真实下载，再次零下载复用；9辅助公告由SID另路下载 | v3：ACCEPT_WITH_LIMITATIONS | PARTIAL：Worker未跑、IR原件/激励原表缺失，辅助公告未验证统一入库 | [recheck_v3](reviews/CN-688012/recheck_v3.md) |
| 腾讯00700 / HK | 本地2024/2025年报；缺失2026半年报主链Dayu未启动，官网原文另路取得 | v4：有来源及校准限制的条件模型通过 | PARTIAL：Dayu新下载、电话会、完整公告区间、canonical初处理未闭合；年报官方认证/精确公开日未完全证明 | [recheck_v4](reviews/HK-00700/recheck_v4.md) |
| Microsoft MSFT / US | 本地FY2024/2025；FY2026主采集失败；官方结果/完整电话会/22页新口径PPT另路取得 | v2：条件模型及正式技术链PASS | PARTIAL：新财报主链、FF→ET成功入库、SEC HTML canonical处理未闭合 | [recheck_v2](reviews/US-MSFT/recheck_v2.md) |

官网补充不能算FF/Dayu集成成功。中微新半年报原件3,149,962B、实际披露日2026-08-20继续在原库保存；生产原件删除0。

## 审查覆盖与过程证据

- 初审268 claims、183参数、534逐项记录，结论CN PARTIAL、HK/US FAIL；validator绿色不替代事实和经济语义审查。
- 修正版106+325+502=933个claim记录逐条定位；长上下文按既有合同分片，**不是933个不同经济事实**。CN42/HK53/US90参数逐项核对。
- 原文完整上下文、单位、财年/季度、净额/总额、并表范围、日期与信息截止日分别检查。CN9新增公告PDF59页全文重读；US22页原始PPT全视觉审查，变更依赖页再读；HK关键表头/脚注/封面独立重读。
- 全部年度/分部/三情景、历史对账、桥接、增长/CAGR、归因、目标比较、敏感性、置信度标签、JSON/Markdown、强input-required验证、registry及不可变快照独立核对或复算。
- RF技能0–11步骤都有实际matrix；材料搜索未完成项标缺口。未来实际业绩未公布，backtest evaluate不适用，没有以情景伪造回测。
- 7份命令ledger共359条完整起止配对，68失败尝试保留，含先RED回归、provider拒绝及已修中间错误。未配对0、输出字节/SHA不一致0。早期少数尝试只有外层日志，后续显式追踪子进程；范围是已记录进程，不宣称内核级全系统抓取。

## 已修复并发布的实现缺陷

RF主线08673cf87b8a58fc25982b695a9d14e28c6818d3：schema2来源包络、年度缺省FY、历史未知获取时间、已确认mixed聚合边界、registry审计误报未登记。先RED后GREEN，本轮责任包128 PASS，既有短daily108 PASS/25.141秒，普通pre-commit通过。精确提交的[远端quality CI](https://github.com/zhengcb81/revenue-forecast/actions/runs/37747048408)成功，约40秒。

SID维护分支v2-clean-rewrite，提交c0f07e12d4ba3e232d712bb6e5e491832023b0a0：半年/季度官方分类与UTC+08披露日期。干净已提交HEAD只叠加5修复文件的隔离责任包101 PASS；含budget包的另一个清单108 PASS。已推维护分支，不合并旧StockInfoDownloader主线；未观察到该提交GitHub workflow，不称远端CI已通过。

两仓owner未提交文件原样保留；四份生产配置/SKILL SHA不变。生产source-facts仅通过标准producer追加实读支持的元数据，旧断言、原件、旧快照不覆盖。Dayu零代码修改。

## 输入错误及修正

1. 微软“±5pp”误填5.0（±500pp），修为0.05并重算8项完整依赖。
2. 三家均有把收入基数/会计政策当未来增长依据的问题。逐参数补机制、历史、约束或收窄表述，未来精确值仍是条件假设。
3. 非设备残差不能全当售后；季度平均订阅不是期末客户数；季度恒定汇率指引不直接年度化；卖方全年目标不等于买方部分年确认收入。
4. 公告标题不等于全文checked。CN补9全文/19条triage；达产属地销售目标无年份，保留ambiguous/空期间/mismatch/unmodeled，不把邻近专利7年计划套给销售。精确激励schedule未取得仍是缺口。
5. HK v3把网易竞争背景当腾讯增长根one-step支持，误升triangulated。独立复查再次发现后，v4改竞争反证，Games limited与confidence limitation恢复，所有金额及分值64不变。

初审FAIL与HK v3第二轮FAIL均保留，不改成“一直成功”。最终签收只适用于有边界的条件预测，不表示已验证情景概率、未来准确度或所有材料穷尽。

## 仍需施工的功能缺口

| 层 | 本轮真实状态 | 后续重点 |
|---|---|---|
| 原件虚拟接口 | 三公司真实SourceRef/version bytes复用与SHA验证通过 | 新来源及辅助材料也统一producer入库与版本引用 |
| 港美新下载 | 当前CWP Dayu适配在provider启动前拒绝bounded acquisition | CWP-owned有界SDK/transport桥，外部Dayu零修改 |
| FF→ET | 部分请求0费用cap先拒绝、provider_calls0；独立FMP exact probe无电话会套餐权限，discover另有能力缺口 | exact-fetch能力路由；配置/费用/套餐/正文不可用分开报告，不自行买订阅 |
| CWP初处理 | 本轮财报证明raw/研究侧临时解析，未证明canonical Worker运行 | SEC HTML确定性规范化/locator、有限选段处理；不永存全份转换MD/图像 |
| 现有电话会派生 | 既有微软TXT49证据在CWP/RF当前read通过；指定信息日因公开日unknown拒绝，本轮未消费 | 先呈现“已有但日期未核”，不盲抓/重复付费，不伪填会议日 |
| 管理目标与证据构建 | 定性/季度原口径留旁表；年度numeric schema表达有限，范围未校准 | 原始期间/定性范围与明确年度转换；事实/机制/反证/转换依据各司其职 |

详细责任边界、实施顺序和集中真实E2E见[follow_up_plan.md](follow_up_plan.md)。这些功能**尚未实施**，不能由审计完成推断产品全部完成。

每请求0美元provider cap只是测试设定，不是用户总预算为0，零调用也不能证明provider没有内容。本轮没有新增项目外部LLM API调用/费用；旧累计199,534 tokens/估计$0.110737不重置。Agent harness自身账户用量不由项目API账本衡量。

## 交付、清理与复现

- [最终版本选择](delivery_selection.json)：CN v3/HK v4/US v2，绑定三个独立审查JSON SHA。
- RF交付根：C:/Users/郑曾波/Projects/revenue-forecast/output/cross-market-rf-e2e-2026-10-08/；每公司含input.json、forecast.json、forecast.md、snapshot.json。
- [归档索引](delivery_archive_index.json)把历史TEMP绝对路径映射到保留对象或CWP SourceRef。查旧路径先读此索引，不重写历史input/snapshot/receipt/manifest；CWP原件经公共source_reader按ID/SHA读取。
- 237临时文件110,034,773B清理；146唯一对象56,798,301B保留，旧版本与原始来源字节仍在。62明确可重建栅格/解析文本12,539,811B不留；未知文件默认保留；测试TEMP根已不存在。
- [清理证明](cleanup_final_temp.json)、[配置保护](final_configuration_protection.json)、[日志完整性](command_integrity.json)、[既有摘要实际read](existing_narrative_current_vs_asof.json)。
- 归档辅助脚本曾误混snapshot完整结果SHA与forecast经济SHA；已按RF公开强验证器修正并成功交付，已审模型/快照字节未改，失败及正确重跑在命令账中。

## 查完整轨迹

- CN：[初审](reviews/CN-688012/review.md) → [v3修复](executions/CN-688012/repair_v3.md) → [最终复查](reviews/CN-688012/recheck_v3.md)。
- HK：[初审](reviews/HK-00700/review.md) → [v3复查FAIL](reviews/HK-00700/recheck_v3.md) → [v4修复](executions/HK-00700/repair_v4.md) → [最终复查](reviews/HK-00700/recheck_v4.md)。
- US：[初审](reviews/US-MSFT/review.md) → [v2修复](executions/US-MSFT/repair_v2.md) → [最终复查](reviews/US-MSFT/recheck_v2.md)。

共享[PWF计划](task_plan.md)、[发现](findings.md)、[进度](progress.md)记录MAIN决策，各公司matrix/events/commands/manifest与审查逐项表保留完整证据。
