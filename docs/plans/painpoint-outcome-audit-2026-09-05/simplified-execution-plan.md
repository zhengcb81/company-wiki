# R4：虚拟数据湖收敛实施计划（唯一活动编排）

日期：2026-09-07。状态：**PLAN_ONLY / NOT_IMPLEMENTATION_AUTHORIZED**。用户批准的是按减法调整规划，不是代码、数据、网络、任务或worker实施。依据[简化诊断](../data-lake-simplification-2026-09-07/README.md)。R4取代R3“15包共同G0–G5/95门”的全局执行顺序；原发现和必要测试保留，逐项归属见[r4-transition.md](r4-transition.md)。历史review不自动签收R4。

## 1. 成果、边界和不再做的事

最终用户只提供公司/报告类型/期间/截至日/所需能力，不提供root或路径。同一真实报告的同版本在任一已批准root中地位相同；目录差异仅影响怎样取得字节，不影响身份、权威或业务可用性。

保留现有sources/documents/locations、只读reader、来源hash、不可变raw与版本化export，先在现有本地API/CLI上改，不重建分布式平台、不强制移动全部文件、不合并仓库、不添常驻服务。kind/adapter只解释格式；priority只影响同内容健康副本的I/O偏好。读取能力、语义有效性、加工状态、外发/写权限分开。

不再：重复维护路径权限判断、把companies作为静默后备特权、以下载URL完备性阻止纯原文预览、由消费者推导上游生产DAG、普通读取pause/resume worker、每个薄wrapper再起Python、用CA/ZR accepted代替效果。也不因“简化”删除真实来源校验/安全边界/失败事实，或将所有来源设为可写。

### 原计划的使用规则

- [旧data手册](execution-data-plane.md)、[旧model手册](execution-model-plane.md)、[旧control手册](execution-control-plane.md)只提供R4映射引用的具体负例/领域算法/恢复要求，不独立领取，不执行其旧依赖图。R4阶段动作以本页为准。
- 收入单位、发布事务、回测等在M轨道，不是打开原文的前置。v5仍负责worker正式版本/冻结/恢复协议；A/B本地读取不等v5，C/D真实后台恢复必须满足它。
- 原117项/GP/历史目标的资格仍逐项保留。旧95节点减少的是重复流程，不代表原目标已经完成；查不到当前证据仍pending。未来不得为了兼容旧verifier重建空receipt或把阶段成功批量回填accepted。

## 2. 简化后的步骤依赖与独立审查

每阶段只有三次常规独立决策：**设计审查DR → 变更与隔离测试审查VR → 真实结果验收AR**。每个小步骤自带检查点；范围扩大、数据迁移、删除、外发、1→3→7放量各是额外关键节点，仍分别独立审查。实现者不能自审，AR审查者不能是本阶段oracle作者；真实task/agent ID、输入hash、原始结果及verdict必须记录。名字字符串、未回复或用量中断不计通过。

| 阶段 | 设计准入 | 隔离验证/验收准入 | 明确不依赖 |
|---|---|---|---|
| A 合同与真实基线 | 文档完成后，未来精确DEV/数据读取许可 | 独立来源oracle和禁止副作用的命令卡 | B/C/D、矿业模型、自然soak |
| B 位置透明索引/读取 | A.DR | A.AR、B.VR；真实生产数据动作另授权 | C完整producer、D后台上线 |
| C 瘦消费者与唯一producer | A.DR；接口设计可并行，接线以B.AR为准 | B.AR、C.VR；涉及worker/外发/写时追加D.SAFE和对应授权 | M、D完整自然观察 |
| D 安全与运维 | D01–D04安全准备在A.DR后可独立进行 | D05以后实际接线取B.AR/C.VR及作用域所需结果；持续上线只取拟启用的C真实加工/provider路线AR，不等未启用市场或M | D.SAFE不等待C.AR或D自然观察 |
| M 收入业务独立轨道 | 独立批准的真实source/业务合同，不等D | 自身VR；新版湖集成时取B.AR/C相关接口AR | D自然soak，未请求的provider/后台任务 |

**D.SAFE的精确定义**：D01–D04的独立安全/恢复审查通过，可信归档未修好时可选择自动prune硬禁用并独立证明不可达；原文只读/目标隔离/有限预算/停止与恢复卡完整。它只是特定动作的安全准备，不是worker或LLM的统一绿灯。真实worker仍需本次worker候选隔离测试、v5对应正式前置、C持久领取/失败恢复测试、操作许可。禁止把“有D.SAFE”当全部C已通过。

**避免自身互等**：VR可以启动被测真实程序在获批隔离副本中测试，不要求先拿到它自身AR。必须由独立operator先核隔离根、OS禁止生产写与网络、显式配置、不访问生产worker控制、无自启动/任务、自动prune0、超时和子孙清理。不能证明隔离则blocked；这不授权当前运行，也不计生产成功。

DR一份合同、VR一份结果包、AR一份决策即可；一个阶段不为每个辅助文件建新的批准系统。继承的是实际安全要求和反例，不是重复的文档仪式。

同一VR/AR结果包按能力分栏，而非再建新审批平台：C至少分“本地读取”“加工”“联网provider”；D分“安全准备”“有限运行”“持续运行”。本文C.local.AR只指本地栏，绝不代表全C通过。VR的required只包含该次设计冻结的隔离测试层；真实外网、受控放量、自然观察属于后续AR层，不能反过来作为VR前置。AR尚未执行写pending，不能删掉它或填不适用来制造阶段全绿。细分规则见测试矩阵第6节。

## 3. 执行者每次接班只核八件事

1. 读本页、[测试矩阵](simplified-test-matrix.md)、[归属表](r4-transition.md)及本阶段run目录的task_plan/findings/progress。
2. 确认精确DEV/数据/运行授权与当前step，文档“继续”不隐含外发/删除/自启动。
3. 记录三仓HEAD、实际输入dirty/config/schema/依赖hash；并发漂移则重审受影响部分，不覆盖别人变更。9/7诊断行号只是定位线索。
4. 检查该step的前置决策、allowlist、已知阻塞；未有独立verdict不可推进。
5. 用当前CLI解析器冻结解释器绝对路径/cwd/argv数组/env键/读写路径/网络目的地/预算/timeout；本文接口名是设计，不猜现成参数。--help/--dry-run也先审副作用。
6. 每次只执行一个小步，保存原始stdout/stderr/rc/实际业务状态、前后文件/DB/进程/费用事实，不用最后一条成功覆盖前一条失败。
7. 对照独立oracle，失败写findings；超scope/未知费用/取消失败先停并按预审卡恢复，禁止改golden、删case、抬阈值解红。
8. checkpoint写last_completed、review_pending、产物hash、未做/unknown、下一精确step；产品结果全部以实际证据填，不能从本文抄PASS。

未来每阶段一个批准run目录，最少task_plan/findings/progress、输入/命令清单、results与reviews即可。原始审计/收据不作临时目录；不要复制生产大库做无目的测试。真实样本与未知字段使用测试矩阵协议。

## A. 统一合同与真实基线（8步）

候选定位：wiki config/models/service/resolver/policy与reader；filing scripts/filing_contracts.py、fetch_filing.py；revenue scripts/company_wiki_source.py、source_preparation.py。这些是核查范围，不是自动批准改所有文件。

| 步骤 | 具体输入与动作 | 输出、检查点与失败处理 |
|---|---|---|
| A01 | 重核三仓当前代码/配置，列query→identify→resolve→open→消费路径、每次子进程/全文件hash、root分支及副作用 | baseline-map；把已删旧工具/已修代码标已变更，绝不复原旧bug跑红 |
| A02 | 冻结四个已批准root读取等价，root capability与文档证据质量分开；显式deny/未注册root不能因默认等价放行 | root-contract；独立DR确认“全部可读”不等于全部可写/可外发 |
| A03 | 定义query_local、open_version、request_work三个接口；本地latest只指已索引集合，在线refresh另显式动作 | operation-contract与副作用表；任何纯query可能ensure/download/pause则设计退回 |
| A04 | 定义对外引用document_id+版本/source hash+locator，路径诊断不入业务身份；同字节副本与真实修订区分 | identity-contract；无凭据证明同逻辑文档不强行合并，alias迁移不得删除旧引用 |
| A05 | 独立Data-Agent从真实资料挑报告和版本，标公司/期间/页码/原hash；缺URL保留unknown与本地导入provenance | corpus-manifest+独立oracle；真实资料缺失blocked，不synthetic补位 |
| A06 | 冻结L01–L12等本地测试及接口错误状态；生成基线小型只读trace和profile，禁止整库重复扫描 | 每例基线结果；基线已正确者记保留回归，不要求所有case都红 |
| A07 | 独立VR核查询与读取的身份/字节/来源合同，检查preview允许不扩大正式分析/LLM许可 | 设计负例与副作用审查；标准化错误不是新几十态状态机 |
| A08 | 独立AR签“合同/基线可供实施”，而非新读取功能已完成；生成旧目标到阶段/test的初版映射 | 只解锁B的目标明确性；没有B结果不能宣称位置透明已达成 |

## B. 收敛索引与位置透明读取（10步）

主责任wiki；filing/revenue仅最小协议适配，消费者大瘦身留C。候选service._annotate_locations、resolver._handle/resolve、scanner metadata选择、policy/config、只读reader、现有adapter。

| 步骤 | 具体动作 | 检查点/测试/审查 |
|---|---|---|
| B01 | 用A合同列每个root字段的唯一owner：path/adapter在storage，身份在catalog，外发策略在动作边界；明确旧字段版本映射 | DR审字段合并/弃用，不新增第二套effective_reusable；显式false必须保留含义 |
| B02 | 选择同版本的所有候选location：注册/能力→状态→实际可读/同hash→健康I/O偏好；优先级只在合格集合排序 | L01/L02/L03/L04；不靠先canonical后筛把其他副本屏蔽 |
| B03 | 实现稳定只读字节提供：固定已打开句柄或读取既有受控快照；流式hash，处理TOCTOU/云占位/坏字节/中断 | L05/L06；不能只相信mtime/文件名。新建快照是另获批的准备动作，写入路径/空间单列，不可隐藏在query/open内部却宣称零写；纯读取不建缓存 |
| B04 | 将绝对路径与location_id留在诊断；路径移动后source/version/locator可继续解引用 | L03/L07；不重编号已引用source，不以搬家触发重新下载或模型变化 |
| B05 | metadata按原文/捕获来源/质量合并；保留字段provenance及冲突，不以priority决定真伪 | L08；swap priority/scan order不改变业务元数据，真冲突仍blocked/待选择 |
| B06 | 本地可读与正式capture分开：缺URL可预览，身份/期间不明不被默认为可信财报；缺文本只返回所需产物pending | L09/L10；不能把preview合格当forecast合格，不补假https_url |
| B07 | 输出唯一版本化读取合同；缺/未知版本报明确不兼容，旧客户端在边界adapter一次转换 | L11；禁止无policy自动退companies；不让合法旧引用突然不可读，先测N-1支持合同 |
| B08 | 独立VR在新隔离环境重跑L01–L12和必要旧C01–C10；独立文件/OS观察证明本地零副作用 | 不用人工构造catalog结果冒充真实parser/索引；特殊cloud无法测标限制 |
| B09 | 用真实四root/Fifth-root新注册进行一次端到端query→open→consumer最小读取，错副本/移动/离线逐例复验 | 独立AR从原文重新核身份与hash；仅隔离副本变化，不改用户原文件 |
| B10 | 小范围切到单一读取链，旧入口仅显式版本adapter；记录可回退版本与旧字段移除条件 | 变更独立审查后才切换；回退代码/配置不回滚原始数据和历史来源证据。无法兼容则停切换，不永久默默双跑 |

## C. 瘦消费者与唯一生产入口（10步）

本地只读路线C01–C04/C08可以先交付；C05–C07真实写/worker/网络不能借此自动获准。核心归属：wiki管理source/加工，filing适配provider，revenue只消费证据和业务输入；跨仓不共享可写DB。

| 步骤 | 具体动作 | 检查点/测试/审查 |
|---|---|---|
| C01 | 列filing/revenue全部root/path/ROLE_DEPENDENCIES读取及子进程；把删除/合并候选逐个标实际caller | DR审没有新catalog/第二权限中心；保留必要诊断与完整性防护 |
| C02 | 合并identify+query，一次本地请求最多一个跨仓CLI边界；已加载库调用不再起额外Python | P01；只统计query_local，不拿provider复杂流程充预算；缺entrypoint先实现/审查，不猜flag |
| C03 | 消费者只用文档版本/所需能力；source open由湖提供，不独自展开root；重复hash只在稳定字节边界合同证明后移除 | P02/L05；不能简单删除所有hash。每个保留复验说明独立信任边界 |
| C04 | 去除消费者上游DAG/重试/失效闭包，发送needed_roles；revenue consumer_analysis缓存仍归revenue | P03；只要原文不强制summary/sections；研究state不搬wiki |
| C05 | 采用唯一现有持久job/attempt入口，定义source+角色+版本幂等key、lease/fencing、开始/失败/unknown与恢复 | 旧D01–D10+P04；实现队列API机制测试可以先做，实际worker待隔离测试与D.SAFE，不建第三套队列 |
| C06 | query_local与refresh/fetch_missing/process分开；下载修订/授权候选/字节费用上限/deadline保留 | P05/P06及旧T01–T08；缺预算/未知post-send结果不自动重发，多gap不得首项成功即总completed |
| C07 | 用单写者/短事务消除普通调用者pause/resume；先在隔离真实数据验证读写争用、崩溃/锁释放/取消 | P07；未证明替代安全则保留现保护且不称C完整通过。绝不在生产试删锁/强制resume |
| C08 | 独立VR与真实无网络消费AR：从真实source→湖读取→filing/revenue预览或已验证输入；精确二次0download/parser/LLM | C.local.AR只签L12与P01/P02/P03的只读部分；P04队列机制归加工VR，真实worker归加工AR。usage unknown只能“不证明零调用”，不阻纯预览；付费请求unknown仍受预算门 |
| C09 | 获D.SAFE/本候选隔离运行验证/v5适用前置及精确动作授权后，真实1→3→7加工、首次下载/复用/修订 | 每批独立Ops检查scope/成本/副作用后再放大；P04–P08及M08的broker真实解析，外部响应不得mock；安全拒绝与正向成功分开。broker目标归C解析能力，不等待M收入模型；纯离线解析可在隔离VR先验证 |
| C10 | 独立AR签本地读取、真实加工、真实provider各自状态；仅已通过路线退出旧wrapper和兼容flag | 不把本地成功当联网/后台成功；其他未完成路线明确保留后继与期限条件，不强制全局等M或soak |

## D. 安全、性能与运维收尾（10步）

D01–D04应在A.DR后尽早并行准备，不等C.AR。它们保留真实风险约束；D05以后不是单纯删门。

| 步骤 | 动作 | 检查点/独立审查 |
|---|---|---|
| D01 | 从旧H01/worker诊断取当前实现，重核自动prune可达入口、scope/任务/外发/数据库恢复对象 | DR核当前真正风险；旧源码已变则记录delta，不复制旧断言 |
| D02 | 默认关闭自动回收，或实现可信稳定snapshot/精确PK/hash/引用检查/原子归档与恢复后才允许回收 | O01/O02及旧H11–H16；空旧日期目录不能授权删除全部retired；关闭分支必须有实际不可达证明 |
| D03 | 集中操作策略：批准读取域可复用，不每文档再申请；外发按source/privacy/review当前绑定、目标与预算；写/删除精确对象 | O03/旧S01–S11；移动root不能绕安全拒绝；本轮不改owner全public决定 |
| D04 | 独立Ops在隔离环境核D01–D03、恢复/timeout/子孙清理和允许路径；签D.SAFE并列不覆盖项 | 仅安全准备合格；不能以D.SAFE掩盖队列未持久/worker未测/v5未冻结 |
| D05 | 按v5正式合同测扫描/SQL/hash/parser/commit/等待/取消；采集wall/CPU/RSS/I/O/队列年龄 | O04及旧WP06阈值，缺真实规模只报告有限范围；不能重跑生产902秒基线或取消hash换速度 |
| D06 | 收敛一套runtime配置/reader/bundle与唯一观察账本；代际/路径迁移显式，旧日志保持 | O05；旧epoch/canary不直接永久带入，改路径不等于时间连续或资格满足；无全量语义等价不删bridge |
| D07 | CI保留最小有效阻断：真实required case、实际失败/skip/unknown、current组合；质量工具未跑not_run | O06；旧accepted/rc0/空stdout不当结果；机器格式审核不阻普通原文读取 |
| D08 | 若要持续上线，另审schedule/watchdog/用户告警/有限预算/有效期/恢复任务快照，实际读Action与平台事件 | O07；手动run不算自然触发。7/2/1/1及v5观察只对对应上线资格，不阻A/B本地使用 |
| D09 | C真实路线成功后分批退出旧reader/影子/bridge：独立影响审查→隔离回归→真实小cohort→回退演练 | O08；已被其他任务删除的符号不再删除、不擅自恢复，先审替代覆盖。引用/来源历史不删 |
| D10 | 独立AR逐项签运行资格与未闭原目标；只有用户明确恢复批准才能后台/登录启动 | 默认仍paused；自然窗口不足observing不是失败，但不准提前宣布后台完成 |

## M. 收入业务独立轨道（6步 + 原领域步骤）

不作为A/B/C本地读取的前置。沿用[模型手册](execution-model-plane.md)WP08–10/13的数值和故障细节，**取消其旧跨包G依赖**，采用下面DR/VR/AR；同一测试不重复造收据。

1. **M01 来源与领域DR**：独立建立本公司真实source manifest，不等后续三公司E2E；资产事实仍由wiki来源层负责，revenue计算消费只读export。缺新adapter的case待B相关接口，其余真实资料可独立做。
2. **M02 单位/权属/合并**：按旧08.01–08.12执行；独立Decimal/原文oracle，矿石/金属/湿干/TC-RC/payability/期间股权/内部双计与operating_units实际驱动逐个测。M01–M03测试，纯局部测试不替上游资产事实。
3. **M03 generator与发布**：按旧09.01–09.12；真实模板只填值不换结构，validate零写；发布prepared/committed/aborted、同operation幂等、各fault点进程重启与文件/registry一致。M04/M05。
4. **M04 历史回测/confidence**：按旧10.01–10.12；真实当时origin与后来actual分开，禁止事后回填旧预测；去重/单位/样本cap实际影响输出。缺origin保持cap，M06。
5. **M05 独立VR**：按阶段重跑领域红例、公式oracle、真实资料链与失败恢复；仅适用数据能力与当前版本，不等待D自然周期。
6. **M06 三公司AR**：紫金、异构矿企、非矿企必须不同原文，按旧13.01–13.12来源→参数→节点→输出join及1→3→7关键批次独立审查；对网络/worker动作仍取C/D安全与批准，M07/M08。结果不完整逐公司/层级未闭，不把湖能读证明模型正确。

## 4. 复杂度与验收完成定义

每阶段交付“保留/合并/退役的概念清单”：权限规则一个来源；消费者零root特例；一次本地查询≤1跨仓CLI；本地读取零写/网络/worker控制；副本位置不改变source身份与业务字段；状态有唯一owner；新root已有格式不改消费者。不能把逻辑藏进巨型函数/删验证满足指标。

测试ID与独立oracle见[simplified-test-matrix.md](simplified-test-matrix.md)。原WP红例由归属表继承，实施DR必须展开到具体测试路径/当前源码/独立期望；缺映射不得宣布原目标完成。定义DR/VR/AR中的“通过”是实际review，不是本计划勾选。真实业务/后台验收、文档审查、旧账本状态分别报告。

回滚：代码/配置回到审过的兼容候选，受影响派生行按精确合同恢复；原始来源、旧receipt和费用失败记录不删。外部调用/费用不可撤销，保留事实与人工处置；不把回滚等同resume worker。中断接班继续同一stage run，不重建假成功历史。
