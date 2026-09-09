# R4 六类痛点：实施步骤与关闭条件补充

日期：2026-09-08。状态：PLAN_ONLY；本次交付是修复计划细化，下面的代码改动、产品测试和现场动作均未执行。

本页是[现有R4计划](simplified-execution-plan.md)的步骤展开，与[36组测试矩阵](simplified-test-matrix.md)、[117项逐行映射](r4-unit-remediation-map.md)配套。保持A/B/C/D及独立M、DR→VR→AR的编排；本页编号只是检查清单，**不是新增机器门或每步独立批准**。旧95门、旧手册G0–G5不重新执行。旧[数据](execution-data-plane.md)/[模型](execution-model-plane.md)/[控制](execution-control-plane.md)手册中的领域反例和原成果要求继续继承。

## 1. 领取、输入和证据规则

先从已获授权的动作范围选择一条路线。未来代码实施从R4 A01开始：核当前三仓HEAD、dirty、配置/schema/依赖和实际调用入口；9/5–7审计描述是基线线索，已被其他任务修正的代码保留回归，不能还原旧bug。本页候选模块由旧审计定位，实施时用CodeGraph核当前定义/调用者后冻结精确文件；不假称本轮重审了最新源码。

| 路线 | 最早可做与先后 | 对应完成范围 |
|---|---|---|
| 原文读取 | A合同/样本→B实现与隔离VR→B真实读取AR→C本地消费AR | 四根位置透明/只读合同；无需先完成M、worker或自然观察 |
| H01 风险控制（组，见 §2） | A.DR后D01–D04可准备，与B设计并行；禁止回收的运行资格先证明所有自动入口不可达 | risk_contained；不等同archive_restore_verified或允许prune |
| 加工/联网 | 对应接口与隔离VR→D.SAFE、v5适用前置、当前动作范围→真实加工/联网AR | 本地、加工、provider分别签；C.local.AR不能代替另两栏 |
| 收入业务 | 独立真实来源与领域DR→对应VR→三公司/历史/发布结果AR | 仅依赖实际使用的B/C接口；不等未使用provider与自然窗口 |
| 持续后台 | 拟启用C路线AR、D性能/恢复结果→有限运行→真实自然观察 | 持续运行资格；不得用人工run或测试时钟填自然窗口 |
| FC903 资格修复（线，见 §5） | 只读历史取证可先做；隔离资格机制可先测；新业务签收等相关真实结果 | 历史绑定有效性与当前业务资格分别记录，不阻无关query/open |

每阶段DR冻结一次命令/输入/独立oracle；VR由非实现者在第二隔离环境验证；AR最终审查者不担任该阶段oracle作者。高风险操作和1→3→7批次按R4关键节点审核。现有有效授权按原范围复用，只有实际超范围或必要条件缺失才请求补充，不因本页拆步骤逐条重新审批。

每个子步骤保存到未来获准run目录：原目标ID及子条款、step、实际entrypoint/文件hash、输入/样本hash、命令卡、预期、stdout/stderr/rc、实际业务状态、前后文件/DB/进程/网络/费用事实、结果hash、review引用、remaining和下一步。未运行字段保持null/not_run；不要现在创建假结果文件。

命令卡必须从当前解析器确定：解释器绝对路径、cwd、argv数组、环境键、读源/写库/registry/output精确路径、允许网络目的地、字节/费用/时间预算、目标进程及子孙清理、恢复入口。不能填猜测CLI参数或默认生产路径。只有文档检查可以现在运行；下列业务执行按未来实施范围开展。

共用停止规则：越界写/外发、原字节漂移、未知已发请求、错误进程终止、恢复冲突或独立审查未通过时停受影响动作，保留事实并按该动作已审恢复卡处理。缺真实样本时该层blocked；mock只能验证故障机制，不能充当真实业务结果。

## 2. H01：先阻断风险，再验证逐条归档/恢复（R4 D01–D04）

Owner：wiki。候选：source_catalog下archive_retired_evidence、prune_retired_evidence、worker及直接contract tests。依据[H01独立复核](retention-independent-review.md)，不推断已发生生产误删。测试：R4 O01/O02、旧WP01 H11–H16及旧数据手册归档反例。

| 子步骤 | 输入→具体实施动作 | 产物与完成检查；失败处理 |
|---|---|---|
| H01.01 | 当前worker/手动入口、旧归档清单→列所有自动/间接prune调用、apply默认值、配置装载与恢复脚本路径 | 调用/开关清单；每个入口有控制措施，找不到调用者不可声称不可达 |
| H01.02 | 选择默认硬禁用分支→将自动回收关闭落实到实际worker调用边界，验证配置缺失/旧配置/重启/别名入口不能恢复apply | 隔离真实worker或目标调用链的不可达证据；仅paused、改日期、改配置未接线均不合格 |
| H01.03 | 当前schema及真实retired/active/新退役样本→固定小型隔离反例：空旧目录、缺gzip/坏hash、同count异PK、重激活、仍有引用 | 独立禁删集合与原locator清单；旧代码已修则记保留回归，生产删除为0 |
| H01.04 | 原保留期/retired_at/代际与引用合同→冻结一致快照、高水位、逐span内容hash、唯一归档名、保留期起算/边界和恢复冲突规则 | DR签精确集合算法；前1秒/恰到/后1秒、未来目录、新退役/导出中重激活都明确；不缩短生产90天求绿 |
| H01.05 | 稳定读视图→流式导出到staging→校验逐对象PK/内容/locator/parser/hash→原子发布manifest/包 | 原子发布前kill不得留下可回收“完成包”；同日重跑不覆盖已归档文件，COUNT只作辅助 |
| H01.06 | 完整可信manifest→重新检查每个对象当前生命周期/代际/引用/保留期→生成精确PK集合及集合hash→有界事务CAS回收 | 只处理批准集合，max rows/事务时间/取消可控；新增、未归档或重新激活对象不得被宽泛retired谓词删掉 |
| H01.07 | 已发布归档→新隔离库真实恢复入口→逐PK恢复内容、locator、parser/version/hash及必要引用 | 与原稳定快照逐对象比较，冲突不覆盖；中途终止/截断/占用/权限错误可恢复，磁盘满用受控故障注入 |
| H01.08 | 获准真实一致副本→真实archive→校验→隔离prune→真实restore，混入active/未归档对照 | 独立恢复审查核所选全部对象与locator，不只行数；真实样本缺失不签archive_restore_verified |
| H01.09 | 汇总硬禁用、归档、恢复三栏→独立D.SAFE；未来拟允许prune时另核恢复副本、精确PK/范围、预算与每批实际变化 | risk_contained、archive_restore_verified、prune_enabled分开。关闭完整H01需可信归档恢复证据；回退代码不能重新打开不安全自动入口 |

保留回收功能的worker运行前必须有对应保护；采用硬禁用时，worker其他能力仍须C的持久领取/失败恢复VR、v5正式前置和运行许可。D.SAFE不会自动给worker放行。真实生产删除只在实际请求包含该范围时执行，不以隔离恢复成功代授权。

## 3. WP02–WP07：资料供应链逐段修复

以下W编号是旧WP的子步骤，不是新工作包。每组继承旧数据手册同包全部非同义负例；此表列实施顺序和必须观察的消费者结果。

### WP02：policy传递、eligible副本与只读（A02–A04、B01–B09、C03）

候选：wiki config/runtime_policy/cli/resolver/service/reader/acquisition/close_gap；filing fetch_filing/filing_contracts。测试：L01–L12及旧WP02 C01–C10。

| 子步骤 | 实施动作 | 检查点/产物 |
|---|---|---|
| W02.01 | 从query/resolve、existing/latest、下载后re-resolve、close-gap finalize、bundle到filing handle画一次policy传递链 | 每入口policy owner与缺失行为明确；latest本地读取不隐式ensure |
| W02.02 | 在边界一次构造不可变读取上下文，逐段传递；旧客户端只在一个版本adapter转换 | 全段policy/version一致，移除任何一次透传的mutation应在实际消费者失败；不事后另读配置贴标签 |
| W02.03 | 全部location先按注册/能力/实际可读/同版本hash筛选，再按健康I/O偏好排序 | 高priority禁用/失效时选合格低priority；排序/scan顺序不改变身份和业务事实 |
| W02.04 | 分离metadata可信来源与root.priority；缺URL允许明确缺口的preview；缺身份/期间仍不能用于正式输入 | 字段provenance和冲突可追；不会为了capture_ready伪造URL或重下 |
| W02.05 | 缺库零mkdir/DDL；验证live WAL/SHM访问语义，区分SQL编程错误、锁与超时；处理稳定打开后替换/同size篡改/路径逃逸 | SQLite/文件/进程观察，不能用immutable=1忽略live WAL来凑零写；编程错误不无限重试 |
| W02.06 | 四原生root覆盖、同PDF四副本位置等价、移动/离线/第五根注册从真实filing/revenue入口重走 | 两组根证据分别签B.AR；L12只读零网络/写/worker控制，路径只作诊断 |

### WP03：期间修订、补缺授权、deadline与失败计数（B04、C06/C09）

候选：wiki gap_plan/acquisition/authorization/close_gap；filing fetch_filing/filing_contracts。测试：L07、P05/P06，旧freshness四反例及T01–T08。

| 子步骤 | 实施动作 | 检查点/产物 |
|---|---|---|
| W03.01 | 冻结CN/HK/US真实metadata、FY/Q1/Q2/H1/非自然年与真实修订关系 | 来源oracle独立读官方已存证据；accession词序/mtime不作为修订真值 |
| W03.02 | 实现规范期间与版本关系、unknown/ambiguous；本地latest仅已有索引，在线发现另动作 | 真实初版/修订不被吞并；季度与半年不误认，不能改fixture为递增编号救绿 |
| W03.03 | 将授权绑定候选身份/URL/期间/版本/大小范围/费用；锁内重查候选；未知size按stream硬上限处理 | TTL不同但同候选可共享合法幂等结果，授权变更不等于新下载身份；候选漂移重核许可 |
| W03.04 | 对每个gap持久记录计划、开始、下载、提交与未完；同候选单飞，全部required闭合才completed | 多gap首项成功仍partial；同候选并发不重复付费，非同候选不错误合并 |
| W03.05 | 锁等待/provider/retry共享monotonic deadline，每次异常后重算remaining并截断sleep；统一成功/异常账本 | 10秒总预算不可9秒调用后再睡5秒；fetch成功commit/handle失败仍保留真实calls/bytes，unknown不填0 |
| W03.06 | 隔离注入commit失败/回复丢失/坏JSON/取消；获准后分别跑真实三市场首次下载→复用→真实修订 | 独立request ID/网络字节/attempt/磁盘对账。post-send unknown先查回，不盲重发；缺某市场或真实修订该AR仍pending |

### WP04：唯一持久需求、attempt和真实产物消费（C04–C05、C07–C09）

候选：wiki processing_demand/scheduler/worker/producer_journal/artifact_read_model/reader/resolver；revenue source_preparation只经受控API。测试：P03/P04/P07，旧D01–D10。

| 子步骤 | 实施动作 | 检查点/产物 |
|---|---|---|
| W04.01 | 盘点两套内存队列、当前可用持久存储及提交/claim/读回调用；DR确定唯一owner与最小迁移 | 一套job/attempt权威入口；不新建第三套队列，不跨仓共享可写DB |
| W04.02 | 定义source hash+role/version幂等键、lease/fencing、重试权限、terminal/unknown、quota | schema迁移/回退卡保留旧已提交任务；重复100次、旧lease提交必须有确定预期 |
| W04.03 | 先接持久submit/query/claim：提交者退出、不同进程重启仍能查询/领取 | 独立进程机制测试即可验证，不等待完整worker AR；被安全阻止应保留pending与理由 |
| W04.04 | worker实际领取→开始前reservation/attempt→成功/失败/unknown；崩溃后对账再决定重试 | 无artifact的失败仍有attempt；费用事实不从artifact INSERT计数，不被回滚清除 |
| W04.05 | reader/service/resolver读同一版本化artifact视图，真实消费binding；消费者提交needed_roles，producer负责失效闭包 | 改source/单role版本只重算实际依赖；bundle内容canonical重算有唯一责任边界，不能只比两段hash字符串 |
| W04.06 | A提交退出→B真实worker处理真实PDF→C新消费进程读取；再精确重复，升级单role并恢复受控崩溃 | 加工AR保留逐边trace与二次0download/parser/LLM；未运行worker只签机制/本地栏 |

### WP05：policy/eligible之外的外发与语义readiness（A03、B06、C06/C09、D03）

候选：wiki llm_summarizer/readiness_graph/source_lifecycle/section_extractor及所有实际generate/fallback出口。测试：L10、P05/P08、O03，旧S01–S11。

| 子步骤 | 实施动作 | 检查点/产物 |
|---|---|---|
| W05.01 | 列所有主/备用外发与写入口，拆读取、normalized/sections能力、语义资格、外发许可 | public或preview通过不能替代动作许可；历史214产物按owner既有决定保留 |
| W05.02 | DR冻结当前source/normalized hash、policy、identity、review TTL、目的地、token/字节/费用与cohort精确集合 | 消费者所需语义明确到字段/质量；不以任意span或published_date非空算ready |
| W05.03 | 真正发送前对同一稳定输入复核，fallback也走相应目的地许可；范围变动用精确集合/CAS拒绝 | 移动root不能洗掉拒绝；批准7不得扩大成kind全部752 |
| W05.04 | 在隔离环境测试TTL边界、policy/normalized漂移、恶意原文、未知fallback、超预算和cohort增删 | 独立网络/文件observer证明拒绝，无权请求实际0发送/0越界写 |
| W05.05 | 获准一份真实source-only输入，真实LLM响应与发送hash/request ID/费用对账，再精确复用 | 正例与安全拒绝分栏，费用未知保留unknown；来源系统不生成投资判断 |
| W05.06 | 独立VR/AR审每个出口及真实语义消费，保留unsupported和缺必需role | 合法拒绝不等于业务成功；对应解析/加工/外发能力未齐不签整体完成 |

### WP06：真实性能、取消和恢复（B03、C02/C07、D05）

候选：当前SQL候选选择、scanner、parser子进程、worker/checkpoint与supervisor；v5独占正式冻结合同。测试：P01/P02/P07、O04；旧SQL/取消/circuit全部反例。

| 子步骤 | 实施动作 | 检查点/产物 |
|---|---|---|
| W06.01 | DR冻结数据拓扑/规模、cold/warm定义、分位数算法、完整输入/有序结果oracle及资源上限 | 真实库一致副本和合成复杂度分开；当前不足49GB不声称该规模通过 |
| W06.02 | 分段计enumerate/metadata/SQL prepare-consume/hash/启动-parser/commit/queue/export/cancel | 原始wall/CPU/peakRSS/I/O/队列年龄全保留；局部SQL不代替完整resolver或worker |
| W06.03 | 隔离库优化SQL/索引与流式hash，先证force/retry/terminal/重复location结果集合与顺序等价 | query/open不隐式DDL；旧坏查询scratch硬限2秒，不生产重跑902秒基线 |
| W06.04 | 分离取消轮询、限制parser/子孙时间、原子完成checkpoint；新查询清理旧cancel handler | 真进程hang/kill/恢复可验证；heartbeat更新不算完成进度 |
| W06.05 | 持久失败预算与circuit：仅完整成功cycle可reset，同signature3次/30min5次及v5规则 | 重启/登录/uptime不清预算，授权reset后仍paused；单线程约束不靠并行LLM绕开 |
| W06.06 | 按同协议交替baseline/candidate；测SQL warm≥30且P95<2s、cold-ish≥10且max<10s、pause P95≤5s/max≤10s；scanner交替≥10、P95≤120s及原倍数要求 | 原VM proxy≤2.8/wall median≤3等阈值继续由v5正式冻结；不删慢样本/放宽阈值，未达标不扩大对应运行范围 |

完整2倍扫描目标须同拓扑/协议；VM回调只是proxy。旧902秒/96.8%CPU仅历史线索。实际有限worker批次仍先取得对应隔离验证与D.SAFE，不能用“为了测性能”绕过运行条件。

### WP07：broker七PDF、两HTML真实语义（C09/C10，测试M08）

候选：wiki normalizer/html_capture/section_extractor/service与实际parser/artifact消费者。测试：M08（归C），旧B01–B10。不等待收入M完成。

| 子步骤 | 实施动作 | 检查点/产物 |
|---|---|---|
| W07.01 | 逐份冻结7PDF+2HTML真实source/原hash/公司/期间；覆盖列表、多栏、跨页表、多实体 | 九份独立来源可追；缺样本逐份blocked，不以手写文本或一份改名替代 |
| W07.02 | 两位独立原文标注者核物理页/印刷页、DOM/表cell、单位、币种、期间、实体和合法unknown | oracle在看candidate结果前冻结；列表无章节允许明确unsupported，不编造section |
| W07.03 | 真raw→生产parser/normalizer→page/table→section/fact接线；HTML从真实导入入口进入 | 保持阅读顺序、跨页关系和每条fact身份；预拼pages只作机制测试 |
| W07.04 | 持久demand→artifact视图→consumer真读回，校source/parser/policy版本与locator | 一项来源/版本漂移触发适当失效，不能仅有“生成了文件” |
| W07.05 | 换页/跨页/单位/多实体/期间/HTML策略/缺字段/恶意/无section/cache漂移及中断逐例验证 | 独立字段准确/缺失/拒绝表；一个坏文件不得持续占队首 |
| W07.06 | 真实九源逐份AR；1→3→7每批停止审查，两HTML使用独立明确manifest纳入 | 7文档批次不隐含9源全通过；parser速度按页数/大小/route分桶，跳过困难报告不算提速 |

## 4. WP08–WP10：上游事实与收入业务（R4实施M01–M06）

此节的“实施M”与矩阵“测试M”明确区分。wiki仅来源事实/locator/质量/只读export；revenue负责经营驱动与收入模型。任何更高层投资研究状态不得写入wiki。

### WP08：真实资产、单位、权属和引擎消费

候选：wiki section_chunk_fact/service及资产事实/export；revenue mine_year_operation/commercial_terms/asset_ownership/internal_flow/reconciliation/revenue_core及实际contracts/forecast consumers。继承旧08.01–08.12、测试M01–M03和M07。

| 子步骤 | 实施动作 | 检查点/产物 |
|---|---|---|
| W08.01 | 将ZR601–604拆上游提取/身份与冲突/只读export/下游消费子条款，独立挑真实资产表及收入披露 | 每字段present/missing/conflicting/assumed，真实source/locator/单位/有效期可追 |
| W08.02 | DR冻结asset别名时效、同名/改名、资源vs储量、原值/标准值、basis与review选择 | 不覆盖旧assertion；来源质检accepted不等于投资结论accepted |
| W08.03 | 真raw/table→assertion→冲突/review→versioned export→revenue实际读取 | 必需每条边有实际输出，手写输入/helper单测不关闭上游事实目标 |
| W08.04 | 用独立Decimal oracle实现ore→contained→recovered→payable；湿干/kt-t/%/g-t、TC/RC分母、FX方向及payability次数显式 | 0合法时保留，缺失/NaN/inf拒绝；商业费用费率与总额不混算，不重复施加payability |
| W08.05 | 枚举整个期间所有股权/control变更点；默认跨期变动阻断，获认可模型才按期间分段；internal flow双边及合并边界消重 | A→B→A仍发现变化；100%产量、权益、合并external区分，associate不当控股并收入 |
| W08.06 | operating_units接真实forecast节点，单矿参数mutation观察相关节点/收入变化；保留旧schema合法回归 | input hash变而模型不消费即失败；其他公司/无关节点不变 |
| W08.07 | 真source→export→参数→节点→输出join与矿/分部/公司独立同口径对账 | 真实历史重建与未来假设分开；差额unallocated不plug清零；主要资产缺口保留，不能少数正确签全公司 |

### WP09：generator、纯验证、发布事务

候选：revenue generate_input_template/schema_fields/revenue_forecast/revenue_core/publication_registry及renderer。继承旧09.01–09.12、测试M04/M05。

| 子步骤 | 实施动作 | 检查点/产物 |
|---|---|---|
| W09.01 | 盘点generator/prepare/validate/draft/formal/audit入口、真实配置及所有隐式默认路径 | registry/key/output/Markdown/cache/log都纳入写观察，不只检查未被使用的tmp_path |
| W09.02 | 冻结minimal/mining模板schema、currency/scale/dimension/as_of与填值allowlist，接统一schema→generator→lint/engine | 真模板仅填来源值即可走通，不中途换手工forecast_document或改结构 |
| W09.03 | 把prepare/validate的纯计算与显式签署/建key/registry commit分开，逐caller接线 | 默认、带output/md、验证失败、render失败均零未声明写，rc0不足作证 |
| W09.04 | DR冻结operation_id、prepared/committed/aborted/unknown、stage/final文件与registry权威点、CAS/恢复规则 | 九故障点逐个有磁盘允许状态；同operation恰一次commit，不同合法operation允许同input |
| W09.05 | 实现staging/journal/多资源commit与新进程恢复，修真实registry audit查询与历史读取兼容 | 不能只做单文件atomic-write；不能删孤儿历史或承认同prev两个链头皆完成 |
| W09.06 | 用真填值输入在compute/validate/render/sign/fsync/JSON rename/Markdown rename/registry commit/response九点分别异常及kill | 新进程实际恢复并读磁盘hash；含磁盘满故障注入、占用、并发、响应丢失，保留失败事实 |
| W09.07 | 两真实模板从generator到输出读回与audit独立重演，再测试同operation重放及新operation同input | 隔离发布与生产发布资格分开；超时已commit先对账，不能另开operation重复发布 |

### WP10：历史回测、coverage与最终confidence消费

候选：revenue rolling_backtest/confidence_policy/analysis.confidence及snapshot/actuals/accuracy/发布消费者。继承旧10.01–10.12、测试M06及M07最终输出。

| 子步骤 | 实施动作 | 检查点/产物 |
|---|---|---|
| W10.01 | 只读盘点真实当时冻结origin、当前历史重建和无时间证据三类；标source可获得时间及actual披露时间 | mtime或今天填旧日期不能证明历史预测；无真实origin保留history_pending |
| W10.02 | 冻结forecast_origin/目标期间/evaluation_as_of、company/asset/product/unit/basis observation key及重述规则 | 同snapshot改日期/同actual拆分不增独立窗口；预测资料在origin已可知 |
| W10.03 | 独立来源/数学oracle配对forecast与后来actual，手算误差/WAPE分子分母、零分母策略、coverage和cap | 不调用生产评分函数生成期望；困难不可比样本列缺口，不任意剔除 |
| W10.04 | 从snapshot/来源/actual/evaluation真正校内容hash、身份、时间；按矿/分部做滚动配对 | record_sha非空或两字符串相等不足；无矿预测不得用actual单边分解冒充配对 |
| W10.05 | qualified历史记录与policy版本注入实际主confidence和输出验证，cap沿汇总传播 | 单观测零误差仍受cap；改变/移除一条合格事实，在最终输出体现预期变化或数学不变原因 |
| W10.06 | 真实至少两独立origin运行回测→confidence→实际draft/发布消费，独立查future泄漏/跨公司/重hash篡改/重复观测 | 算法、真实历史可用性、主输出消费三栏分别签；历史不足只证明机制，不能伪造旧预测补齐 |

## 5. FC-903：原收据绑定与新结果资格（A08、D07/D10；旧WP00）

依据[旧总计划WP00第6条](remediation-plan.md)和[filing审计](filing-audit.md)。对象是legacy **FC-903**，不是ZR-903；继承关系为ZR-307、ZR-404、ZR-405，不扩大或合并其独立目标。GP004同类历史问题按实际绑定另查。

| 子步骤 | 输入→动作 | 产物/关闭条件 |
|---|---|---|
| FC903.01 | 从legacy继承表及原registry定位准确unit/revision的11 implementer与12 reviewer路径，读取schema中被绑定字段 | evidence-case清单：绝对路径、revision、schema、raw字节hash/size、取证时间；不按文件名猜同一revision |
| FC903.02 | 对12所指对象逐字节重算SHA，按当时schema区分raw SHA与canonical/payload hash | 原审计所指010d0b9e…和当时实际010699ca…是历史值，现场重新计算；不通过换行/排序重编码凑匹配 |
| FC903.03 | 按原revision引用、已知Git对象、旧manifest和获准备份有界查找被签原字节，记录每处查询及结果 | 找到对象须raw hash匹配并验证review确实指向该revision；禁止全盘无界扫描、改旧12的绑定或倒填旧11 |
| FC903.04 | 找到则仅恢复历史可验证引用；找不到则在新附属状态记录binding_unknown及缺失对象 | 原11/12/签名不变；found历史有效也不证明当前业务完成。无法恢复原字节不是伪造旧签收的理由 |
| FC903.05 | 核FC903原目标及ZR-307/404/405各自条款，在当前隔离checkout真实复验缺口，独立review实际输入/命令/结果hash | 当前新结果只能按本次真实测试层签；无所需E2E保留partial，旧accepted不继承 |
| FC903.06 | 用当前支持的revision流程新增实现/独立审查结果及supersedes关系，附旧记录失配/替代原因 | 新revision身份独立、旧历史append-only；未有正式接口先设计/审实现，不直接改原registry字段 |
| FC903.07 | 在实际资格消费者加入坏绑定、另revision替身、换行变字节、最新rejected/未完后继、缺结果等负例 | 坏历史绑定不能用于当前关闭；合法rejected可保存但不得作为business accepted；仅schema校验不足 |
| FC903.08 | 独立证据审查重算全部新绑定，分别签历史可恢复性、当前原目标结果、资格消费者行为 | 历史unknown可永久保留；新独立完整结果可建立当前资格，但不得声称补证reviewer当年审过那些字节 |

## 6. 117项逐条执行与最终关闭

[逐行表](r4-unit-remediation-map.md)在本轮列出每个原ID、原审计结论、修复归属和验收条件，构成执行输入；仍不能替代实施DR对原注册条款的完整展开。原53 CONTRADICTED、58 PARTIAL、6 HISTORICAL_ONLY是9/5–6版本观察，不直接断言当前HEAD仍有同一缺陷。

| 子步骤 | 动作 | 检查点 |
|---|---|---|
| U117.01 | 读取逐行表、原CA/ZR注册条款、legacy/GP继承和各分报告；按原ID生成子条款键及原文引用/hash | 117唯一ID全覆盖且原25CA+92ZR；多仓/多真实层级拆子行，不通过总表一句“已覆盖”省略条款 |
| U117.02 | 当前HEAD重核各条款对应实现/生产调用者/既有结果，记录已修回归、仍有反例、历史only或未验证 | 保留原审计列，新增当前列；不得从旧CONTRADICTED直接制造当前失败，也不从旧accepted推通过 |
| U117.03 | 对每个子条款冻结R4步骤、旧finding/RED、当前测试路径、oracle、required层、目标消费者与关闭条件 | A08初版可增量做；进入某阶段DR前该阶段全部required条款必须明确，不让117全冻结阻普通读取设计 |
| U117.04 | 按前述线路执行并在同一结果包记录unit/subrequirement/case/layer/input/command/result/review关联 | 明确not_run/blocked/fail/pass；某VR通过不回填对应真实AR；同义测试共享实际结果但保留多ID引用 |
| U117.05 | 独立对当前资格消费者运行旧E01–E13及新真实结果变体：空required、skip、未知ID、坏hash、过期/未来、旧组合、仍未闭后继 | 输出应拒绝相应关闭；合法保存历史记录不等于当前资格。模型/CI/自然时间各看实际消费者 |
| U117.06 | D10及M最终按每个原条款核全部required结果与未闭finding，再计算原ID资格 | 任何一必需子条款未过则原ID未闭；区分风险控制、能力验证、真实效果、持续资格；不按包批量accepted |
| U117.07 | 交付117逐项当前结论/证据/remaining/下一步，另列GP10和legacy继承覆盖 | 未知ID不丢弃；ZR-1002/1003波次展开两项皆保留；缺历史origin/自然时间如实保留，不追造证据 |

实施记录最少字段：unit_id、subrequirement_id、original_clause_ref/hash、original_audit_status、current_input_hashes、owner、step、case、required_layer、oracle_ref/hash、actual_entrypoint、result_status/ref/hash、review_ref、blocking_findings、remaining。**本轮逐行表是规划映射，实际命令/样本/结果在各阶段DR/执行时填写**；禁止现在编造实际hash。自然7/2/1/1、真实三公司、四原生root、现场恢复/迁移等原要求不能仅以机制正确关闭。

## 7. 9个复杂度泄漏点与7类真实验收逐项落地

下表按[诊断原九行](../data-lake-simplification-2026-09-07/README.md)次序，CL编号仅本文导航。性能阈值在运行前冻结；文件数减少不等于复杂度或耗时改善。

| 泄漏点 | 实施步骤 | 验收/删除旧逻辑的条件 |
|---|---|---|
| CL01 先canonical遮蔽健康副本 | W02.03；B02 | L01/L03/L04；合格低优先级成功，全失效明确unavailable |
| CL02 priority决定metadata | W02.04；B05 | L08；交换priority/扫描顺序业务字段不变，真实冲突保留 |
| CL03 kind与per-root双重policy | W02.01–02；B01/B07 | L04/L11；唯一合同透传、显式deny有效，未知版本明确拒绝 |
| CL04 filing无policy退companies | W02.02/06；B07 | L11/L02；当前/N-1边界协商，四原生root从真实入口可用 |
| CL05 capture完备性阻本地预览 | W02.04；B06 | L09/L10；缺URL原文可读，身份不足不能作正式输入 |
| CL06 重复全文件hash及路径身份 | W02.05；C03/W06.02–03 | L05/L07、P02；稳定字节和信任边界成立后减少重复I/O，旧引用不变 |
| CL07 薄subprocess及latest隐式ensure | C02、W03.02；W06.02 | P01/L12/P05；一次query≤1跨仓CLI，冷/热≥10，0隐式外发 |
| CL08 普通取资料pause/resume | C07、W04.06；P07 | 唯一writer/短事务与真实争用恢复通过才退出保护；query不控制worker |
| CL09 usage未知阻预览、消费者重建DAG | C04/C08、W04.05/W05.01 | P03/L10/L12；声明needed_roles，preview可报告unknown但不能谎称0调用 |

额外迁移分支epoch/cohort/shadow/bridge按D06/D09、O05/O08退出：先当前caller与兼容范围→隔离回归→真实小范围→回退演练→删已证明替代的分支；永久运行scope/费用约束不可当临时迁移逻辑一并删。

| 原七类真实验收 | 实际执行与独立证据 | R4测试 |
|---|---|---|
| AC01 同PDF四根等价 | 隔离真实PDF逐根单独/共同索引并交换priority，比较source/version/业务字段/字节 | L01/L08；另L02验证四原生root，不混淆两组 |
| AC02 首选副本失效 | 只在隔离副本撤首选/两个/全部再恢复，从真实consumer读取 | L03/L06；同版本切换，不下载/重解析 |
| AC03 移动与修订 | 保存source/locator后移动改名重索引，重新打开；真实修订另版本 | L07/L05；原引用不变，不吞修订 |
| AC04 第五根 | 已支持格式只加隔离注册，消费者代码hash不变；测deny/未知adapter | L04/L11；无需新增root特例 |
| AC05 缺历史下载URL | 真本地导入source分别请求preview和正式输入 | L09/L10；前者显示provenance不足，后者按真实身份要求判断 |
| AC06 零副作用及精确复用 | 真query→open两次，独立OS/DB/进程/network和attempt记录对账 | L12/P01/P02；零写/外发/worker控制，二次0parser/LLM/download须实证 |
| AC07 安全边界不随位置改变 | 越界/读时替换/未知外发/超cohort，移动root后重复拒绝链 | L05/O03/P05/P08；真实拒绝不冒充正向业务完成 |

## 8. 完整E2E、旧95门退出和接班终点

| 子步骤 | 执行安排 | 判定与接班 |
|---|---|---|
| X01 | 独立Source Reviewer冻结三家不同公司、四原生root、broker9源、修订对与历史origin；可按当前路线逐批准备 | 来源不足按具体case缺口；紫金/异构矿企/非矿企不得一份改名 |
| X02 | 第二干净checkout锁三仓组合及全部必要dirty输入；明确隔离raw只读、DB/registry/output可写与网络范围 | 真实CLI/程序入口从上一步输出提取ID传下步；不预写completed/产物/forecast替代链 |
| X03 | 分别执行本地读取、真实加工、CN/HK/US联网、模型/发布/回测旅程，逐source→locator→artifact→parameter→node→output join | 本地、加工、provider、三公司、历史分栏；missing/pending不得用mock补终点 |
| X04 | 在适用真实加工/cohort按1→审→3→审→7，费用/字节/写集合/取消每批对账；再精确复用和单role失效 | 每级独立签收再扩大；九broker与三公司各自覆盖不能用7文档数量替代 |
| X05 | 独立注入持久队列/worker/发布恢复点，新进程恢复；真实CI required和质量工具实际运行 | 文件/registry/队列按精确已提交对象恢复，raw与费用历史保留；skip/not_run/空stdout不作通过 |
| X06 | 拟持续上线的已验路线才进入D08自然7daily/两weekly间隔≥7天/monthly窗口/drill告警ack及原legacy/v5窗口 | 单次真实E2E不等自然完成；观察不足observing，平台Action/SID/事件与告警独立核验 |
| X07 | 将旧gate-dag.json、validate_execution_plan.py和95个pending仅保留历史引用，当前接班只写R4阶段/能力/step及真实结果 | 不生成95个空receipt凑绿；旧结构校验不能推进R4产品资格，普通query不查开发审查收据 |
| X08 | 独立AR核本页六类问题与117逐条结果，交付已闭/未闭/必要后继；回退演练和兼容退出仅操作已审范围 | 默认不因报告完成恢复后台/登录启动；历史签名和原目标保留，current资格只来自本次真实证据 |

完成本次“计划细化”的标准是文档步骤/映射/引用自洽且新增内容经审查；完成未来“修复”的标准是上述实际结果成立。当前[R4独立审查](r4-independent-review.md)只绑定原两核心文档；本补充的审查见另行生成的r4-remediation-detail-review.md，不扩大历史签署范围。
