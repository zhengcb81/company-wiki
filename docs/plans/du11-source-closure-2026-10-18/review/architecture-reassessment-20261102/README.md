# 整改效果、真正卡点与按仓并行（2026-11-02）

> 最新调度：用户要求先完成解耦后再按模块派发；本页原有“可立即并行”建议已由[DECOUPLING_FIRST](DECOUPLING_FIRST.md)取代。调查证据仍有效，RF/AUDIT任务暂不启动。

**整改有效，但“所有过度门禁已清净”不成立。存储虚拟化已有，跨仓契约和测试仍有耦合；先完成解耦验收，再按模块并行。** 本轮只复核代码/证据、跑小型离线反例、改进计划；没有产品修复、真实下载/模型调用或公司重跑。

唯一项目状态仍在 ../../CURRENT_STATUS.md。上一轮六仓提交、独审和四仓精确CI绿是有界工程成果，不因新发现作废，也不能覆盖新缺陷。

## 效果与遗漏

| 项目 | 结论 |
|---|---|
| 已删摘要条数/字数、可选日志/收据、mtime、review、公式500字/指数10等门 | 上轮具体路径有独审和发布证据；本轮再测21条完整引用全部保留，修复有效 |
| 本地输入表示门 | **新确认，未修**：OCR配置695B仅加空白至66231B被拒；SourceExport请求66→16777282B、official请求54→65590B、query请求315→65851B同样被旧16MiB/64KiB帽拦。详见[实测](rectification.md)及可重放探针 |
| 电话会最终入库 | **新确认，未修**：ET/FF可接受显式预算，CWP仍固定原文16MiB/结果25MiB；17MiB原文被拒，甚至2B原文配22MiB预算也拒。FF实际调用该import链，详见[边界审查](boundaries.md) |
| official capture/import | 源码128MiB/300s上帽仍在，属于显式资源参数二次约束，归同一预算责任整改；不要与配置JSON表示帽混为一谈 |
| T4父链 | 真实H1三个selected view继承旧备注标题，仍OPEN；12/12召回不能代父链正确 |
| SEM-QUAL-01 | 当前legacy/v7 decoder仍可把有计划/验收条件的合成有源内容写成actual且无诊断；是真逻辑缺口，尚非已证实的付费公司事故 |
| RF ghost/期间补集 | 原R4 carry未实施；document.py仍仅derived分支解释formula；period_flow仍要求输入窗都包含于结果窗，合法FY-H1→H2受阻 |
| 新真实摘要/恢复/RF采用 | 历史有界证据保留，新版完整链仍待验；整个公司loop不因此完成 |

原41项有处置，不等于所有入口清零。RF artifact ID长度/Stock quality flag闭集和summary citation_views最多2目前只是兼容性/角色协议候选，不冒充已确认缺陷，也不见数字就删。

## 根因与改进方向

1. **端点选错**：上轮FF→ET联调截止worker，没有测最终CWP入库。需要把同一请求预算传至入库后verified-open，不能只追加相似单测或继续抬局部常量。
2. **材料真与改写真混淆**：SHA、引用、召回不能证明父链/主体/限定正确。当前semantic_status=not_evaluated是诚实边界，不能用needs_review=false冒任意语义已证。
3. **完成单位偏向包和文件**：局部工程完成不可相加成公司预测完成；验收终点应是用户结果。小P3/可选优化不再反复重开主里程碑。
4. **主计划集中了所有仓实施细节**：可独立的RF算术语义、AUDIT记录整改被CWP关键路径串行拖住。实施计划回所属仓，ROOT保接口、依赖和组合验收。

采用现有对象的收敛方案，**不重建数据库/调度器/共享SDK仓或微服务**：

- CWP存储owner负责原件/定位/版本/实收字节；消费者不扫描物理公司目录。
- 结构owner产生真实父链与member/support/context。利用已有SourceSummaryTask、SourceCard，在完整任务作用域绑定主体、时间、条件、否定和计划/实际；legacy/current薄复用。歧义保unknown，不任意借邻段，也不整篇禁读。
- 现有quote-primary/extractive保完整原话；模型排名和展示改写不能覆盖来源事实。有限regex无诊断不代表已证明任意自然语言蕴含。不要以公司词、无限句式补丁或人工签收实现“语义完美”。
- RF负责采用的证据、数值/期间和投资假设；不重做PDF结构。AUDIT负责记录与独立评价，native成功、观察完整、质量通过分别表达。
- 实际费用/token/原文字节/deadline由请求/配置与操作账户确定，各层计真实消耗。编码预算可由原文额度推导，解析和入库不另缩成隐藏常量。真实显式进程/空间/时间上限保留，省略值使用公开默认，不等于资源无上限。
- 现有SourceRef/SourceExport v2和narrative协议继续。生产者拥有核心语义与便携正反例；消费者适配本地类型。可选诊断扩展不应强迫全仓同步，未知核心语义须明确unsupported/unknown，不盲目接受。暂不另建共享Python大包。

更详细的实际代码归因见[语义设计审查](semantic-design.md)。

## 解耦现状

| 边界 | 已做到 | 未完全解耦 |
|---|---|---|
| 存储→消费者 | v2通过SourceRef/公开reader；未见主链必须扫物理原件目录 | RF部分集成夹具直接构造CWP内部SQLite表 |
| CWP→RF/Stock | JSON/子进程；正常uncertain/needs_review可读并传播 | 多仓手写exact字段集/enum；内部reading结构与部署命令存在耦合 |
| FF→ET→CWP | provider与采集编排已分开 | 同预算未贯穿最终import，末端16MiB帽证实 |
| source→summary→research | 原文、来源卡和正式预测有责任边界 | 跨段限定责任不集中；局部绿不证明真实采用 |

**架构尚未完成解耦；按用户最新要求先由ROOT集中收口，通过后再按仓派发。** 下述原分工仅为解耦后的候选分工。Dayu/IQS/Dashboard不动。

仓内唯一入口和交付要求见[协调文件](COORDINATION.md)。这不是再扩一轮产品施工包，而是将原R4责任移交所属仓实施。旧封存不迁移、不改写历史状态。

## 关键路径与收口

1. ROOT清新发现**两族**：本地codec表示门；采集→最终入库重复预算。离线完整FF→ET→CWP→verified-open，含复用0下载和真实超额/错身份反控。
2. ROOT修T4+SEM：normalize/select→实际model-input→decode；真实actual/已满足条件正控；一次来源大节点独审，单H1原90s/16M/112复验。
3. 先完成DECOUPLING_FIRST的D1–D3，再激活RF/AUDIT仓内工作。汇合后选一组已测commit，按现有配置完成新正式摘要→prepared恢复→同/跨run零重复POST→同artifact真实RF参数/公式/报告/snapshot。
4. 一个真实链大节点独审，回原公司四审/固定八家/新公司责任。研究不足保持conditional/unknown，不为绿造数；P0/P1及影响当前节点正确性的P2先修，无关P3进维护队列。

不按包数量报项目百分比，不给缺证据的完成日期。下一产品里程碑是**同一新来源材料可靠进入实际RF报告、恢复不重复付费**，其后才是完整公司循环收口。
