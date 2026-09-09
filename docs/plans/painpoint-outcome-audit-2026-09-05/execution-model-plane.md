# 模型与真实三公司链执行手册（WP08–10、WP13）

> **R4状态覆盖（2026-09-07）**：本文正文是R3历史方案/测试细节库，已不再作为活动执行队列。唯一活动编排为[R4实施计划](simplified-execution-plan.md)，测试见[R4矩阵](simplified-test-matrix.md)，原WP归属见[迁移表](r4-transition.md)。仅按迁移表继承领域步骤、反例与原始成果要求；不执行下文旧G0–G5依赖或95门DAG。历史review只签当时字节，本次新增状态头使当前文件hash变化，不能宣称旧签收绑定修改后文件。旧gate-dag.json及validate_execution_plan.py原样保留为R3历史工具，不用于R4验收。文档更新不授权产品实施。

版本：2026-09-06，细化总计划R2；状态：NOT_IMPLEMENTATION_AUTHORIZED。本文只是计划，不表示下列运行/审查已经发生。总计划第5节门级DAG与第6节授权卡优先；不能用本文的小步骤跳过任何安全门。

本手册已依据[收入审计](revenue-audit.md)的RF-A01–08、[上游审计](upstream-asset-audit.md)及[总计划](remediation-plan.md)恢复原要求：上游资产事实不能由收入helper代替；三公司真实旅程不能换名复用合成输入；默认纯验证不能暗写registry；回测不能事后伪造预测origin。

## 1. 开始前的固定协议

### 1.1 不可自行解释的边界

1. 用户本轮批准的是文档同步和计划细化，不是DEV/CANARY/AUTOSTART。所有代码、测试运行、复制生产数据、注册发布、下载、LLM、worker运行均等待各自授权。计划中的候选路径不自动成为允许修改清单。
2. 每包重新读取总计划、task_plan、findings、progress，记录当前三仓HEAD/dirty和涉及文件hash；代码漂移则更新设计差异，经独立review，不照抄旧行号。本文列出的路径本轮用文件清单确认存在，不代表当前函数已再次全文审查。
3. 输入数据层级分开：`synthetic_logic`（小型构造逻辑测试）、`real_source_isolated`（真实字节在批准隔离环境经真实CLI）、`authorized_live_canary`（授权真实环境有限运行）、`natural_soak`（真实自然时间）。前层不能改名抵扣后层。故障注入可以人工制造故障，但正常业务成功路径必须使用真实文件和真实生产入口。
4. “真实E2E”必须填写运行范围。真实历史PDF在隔离库的E2E证明该版本能处理真实数据，不证明生产49GB库、生产任务、自然周期或登录启动已经合格。
5. 隔离数据只在批准路径建立；原始source、生产registry/DB/旧证据不得修改。公司资料中的投资内容只可作为原文来源保存，上游不得生成评级、目标价或第二套研究状态。
6. 命令不得凭记忆猜参数。G1先从当前CLI解析器/文档核对入口及副作用，再在`commands.json`冻结绝对解释器、cwd、argv数组、环境变量键/安全值、允许写路径、source/DB路径、超时、预期退出码。未解析占位符/默认生产路径/未覆盖子进程配置，一律不运行；`--help`/`--dry-run`也需确认无启动副作用。

### 1.2 每一步的共同完成条件

执行者为每一步保存`step_id / input_hashes / command_card / start_end / return_code / observed_files / assertions / remaining_gaps`。每个步骤必须先获得前一步检查点；失败写findings，不直接把预期值改成实际值，不删除失败历史。过程输出保存到未来批准的实施run目录，本文目录不是生产状态库。

每包G0至G5都要独立agent实际完成审查并记录输入hash和verdict。下文Reviewer-A/B/C、Test-Agent、Ops-Agent是待分配角色，不是已经有人签收。实现者不得自审；独立oracle作者不担任该包G5最终审签者。审查没有结束、工具中断或有未关阻断问题均不算通过。

### 1.3 最小真实证据合同

G1由Source/Accounting Reviewer冻结字段与schema，不在本计划伪填source ID或hash。至少包含：

| 对象 | 必填绑定 | 独立验证与拒绝条件 |
|---|---|---|
| sample | case_id、entity_id/法定名称、角色/市场、原始文档路径、SHA-256/字节数、来源URL或既有manifest、发布日期、报告期间、授权范围 | reviewer打开真实原文核公司/期间；不同公司不能同一raw SHA换名称；来源不可用记blocked |
| locator | source_id/SHA、物理页码和印刷页码对应、表格/行列或段落、parser/version、原文摘录hash | 从原PDF/HTML独立定位；章节存在不等于单元格值正确；OCR结果需回看图像 |
| fact assertion | fact_id、asset_id、原值/原单位、标准值/单位、basis、measurement date、期间、source locator、冲突组/review引用 | 不以来源条目数代替事实；同值不同单位、资源/储量、权益/100%分别保留 |
| parameter | parameter_id、fact_id或assumption_id、转换公式/版本、币种/scale、scenario、有效期、review选择 | 参数不能只带任意非空source文本；每个forecast输入必须能join回事实或明确许可假设 |
| model | node_id、模型/recognition版本、参数ID、asset/commodity/product、quantity/price单位、归属/合并视图 | 缺source/basis或未决冲突阻止对应模型发布，不猜数补零 |
| output | generation/operation ID、input/candidate/policy/schema hash、逐节点trace、分部与公司结果、registry/receipt hash | 从真正CLI生成且读回磁盘；人工拼出的输出/仅helper调用不计端到端 |
| independent reference | source locator、company/period/currency/unit/basis、独立提取值、事前容差与理由、reviewer | 禁用模型结果作reference；历史预测与后来actual区分；未知差额不能plug归零 |

真实链检查采用显式join：`source SHA → locator → assertion → review selection → export/artifact → parameter → model node → output`；处理事件另外连`request → demand → attempt → artifact`。节点必须唯一且跨公司/跨期间不串线；缺一条必需边即该case不完整。同一个source可支持多事实，但不得因此把同一观测拆成多个独立样本。

## 2. WP08：资产事实、矿业计量与外部收入（12步）

准入：G0需WP02.G1与WP07.G1；G3需WP02.G3与WP07.G3。矿业真实运行还需总计划第5.3节的全部动作门。候选文件：wiki `src/company_wiki/source_catalog/section_chunk_fact.py`、`service.py`、资产事实/只读export合同的未来明确新增文件；revenue `scripts/{mine_year_operation,commercial_terms,asset_ownership,internal_flow,reconciliation,schema_optin,mixed_recognition,revenue_core}.py`、`scripts/contracts/document.py`、`scripts/forecast/segments.py`。不能为了便利把601–604所有事实存储迁到revenue。

1. **08.01／G0 原要求卡。** 输入117项ledger与ZR601–611/707/711原条款。拆为“wiki事实生产”“只读export”“下游计量”“权属合并”“独立对账”五组，列允许路径、已实现保留点、当前红例和禁止研究writer。产物`wp08-requirements.csv`和范围卡。检查点：Reviewer-A逐行核owner及原目标，不能拿收入单测关闭上游原卡；遗漏一组则停止设计。
2. **08.02／G1 真实样本与字段清点。** Source Reviewer在批准数据中挑真实紫金资产表、结构不同矿企表和关联期间的收入披露；逐页人工抽取单位、权益口径、储量标准、测量日期。列`present / missing / conflicting / assumed`，事实缺失不写默认0。产物source manifest和原文定位表。检查点：每个拟计算参数已知来源或明确待批准假设；缺关键单位/口径则对应case blocked，不转合成数据。
3. **08.03／G1 身份与事实合同。** 冻结asset_id、alias时效、地域、commodity/product、资源/储量分类、assertion原值/标准化值、来源/解析版本、review状态及只读export版本。设计别名循环/同名碰撞/资产改名/来源矛盾的处理，不覆盖旧assertion。产物schema ADR、迁移与回滚卡。检查点：独立Source-Contract-Agent证明只保留来源事实不夹带投资判断，Accounting-Agent核basis；两个审查缺一不得进入G2。
4. **08.04／G1 RED与外部oracle先冻结。** 保留M01–M12，再增加0产量/0权益、NaN/inf、湿/干吨、FX方向、TC按干精矿吨与RC按金属单位、资源冒充储量。独立Decimal表逐步记录量纲消去，至少一个矿、分部、公司；不得调用生产计算函数来生成golden。产物`wp08-oracle.csv`、红例结果及容差ADR。检查点：当前基线在真实被审入口失败，失败原因必须对应错误而不是缺文件；阈值先冻结后看候选结果。
5. **08.05／G2 先接上游事实链。** 按小diff顺序实现原文table/locator→assertion→冲突→review选择→versioned export；每次只改一个可审核层。输入真实原始字节的隔离副本，不传预解析pages数组冒充parser。检查点：Reviewer-A验证每个字段确由本次source生成、旧事实保留、未review冲突不能被收入消费者自动择优；任何跨仓DB写立即停止并回到合同设计。
6. **08.06／G2 单位与商业条款。** 显式归一化`ore → contained → recovered → payable`，记录每步单位和payability已应用标志；TC/RC/premium区分总额与费率并绑定分母，FX含方向/币种/日期。0是合法业务值时保留，缺值与非有限数拒绝；不把所有数都做positive。检查点：原例2.8%与2.8不能同义，改payability必须有合同规定的可观测效果或明确拒绝重复；Reviewer-A审所有实际callers而非单一helper。
7. **08.07／G2 权属与内供。** 按整个期间全部变更点核share/control，不只比较首尾；默认跨期变化block，若批准pro-rata则记录模型假设及独立结果。按唯一flow ID、seller/buyer、同期间单位币种、合并范围从毛额消重；区分100% operational、equity attribution、consolidated external。检查点：A→B→A仍识别变化，associate不被当控股并收入，双边缺失不假定external。独立Accounting-Agent签设计及样本算账。
8. **08.08／G2 主引擎消费。** 将合法operating_units结果接到真实forecast DAG并在输出保留单位、参数和节点trace；旧3.7单独回归，新3.8不许仅validate后丢弃。产物caller清单和输入→输出映射。检查点：只改一个真实矿的有效参数，必须只改变相关依赖节点；其他矿/其他公司不变。若仅input hash变化而收入不变，G2不得关闭。
9. **08.09／G3 独立重跑与突变。** Test-Agent在新隔离环境跑单元、合同、真实parser→export→模型入口，再独立改单位、source hash、review状态、asset alias、flow重复和期内持股。保存每条实测结果/跳过原因。检查点：所有required负例在真正consumer被拒绝；真实提取与手工oracle在事前阈值内；skip或无样本保持pending，不以测试总数抵扣。
10. **08.10／G4 批准真实CLI集成。** 获本包integration_scope授权后，用sample manifest绑定的真实source运行wiki export→filing消费→revenue draft链；所有网络/LLM/worker另按动作授权。产物真实argv、OS/文件快照、join report、分层对账。检查点：Ops-Agent独立从原文与磁盘核每条边；隔离真实链只标real_source_isolated，未经生产cohort验证不能写production_verified。
11. **08.11／G4 差额与故障审查。** 比较独立披露同口径reference与模型历史重建值，分asset→segment→company解释差额；未来forecast不是已披露actual，不能要求“预测等于历史值”假通过。未知差额列unallocated及影响，不塞plug。注入一条必需事实失效，确认对应输出降级/阻断而非继续正式发布；回滚保留来源与审计历史。检查点：Accounting/Ops独立签真实结果及未覆盖资产清单。
12. **08.12／G5 签收与剩余限制。** Reviewer-C重新抽取至少一个非实现者选择的事实，重算一个矿、分部、公司；检查三种视图区分、真实source覆盖率、全部G0–G4证据hash和未关finding。能力可签isolated_verified，缺真实tier/主要资产/来源则相应目标保持pending。禁止把少数资产正确泛化成整家公司全部资产完成；发布/自动运行授权不从本签收继承。

## 3. WP09：真实generator、无副作用验证、发布事务（12步）

准入：G0需WP00.G1；G3需WP00.G3；真实矿业case额外WP08.G3。候选文件：revenue `scripts/{generate_input_template,schema_fields,revenue_forecast,revenue_core,publication_registry}.py`、`scripts/contracts/document.py`及真正CLI/renderer调用者。既有单文件atomic-write、CLI validate-only draft等正确局部行为必须保留。

1. **09.01／G0 范围与实际发布路径。** 从generator、prepare、validate-only、draft、formal、registry audit每个公开入口列调用图/默认路径/环境fallback，区分纯计算与显式发布。产物入口表及允许文件清单。检查点：Reviewer-A确认registry-before-output的真实失败窗口在范围内，不能把任务缩成atomic-write helper重构。
2. **09.02／G1 schema/generator合同。** 固定minimal和mining两模板的模型维度、monetary currency/scale、required字段、base_year/as_of合法关系、版本兼容及capture。产物生成合同与可填写字段allowlist。检查点：Reviewer-B证明使用者只填值/source/已许可假设便能进入引擎，不需修key/模型/维度；无法表达的模板记设计缺口。
3. **09.03／G1 真实填值输入。** 由本包Source Reviewer独立建立非矿企与矿企真实来源manifest，可复用已经存在且重新核验的WP08来源，但不等待WP08整包或WP13产物/签收；未来WP13引用本包合格样本，不构成反向依赖。冻结`template_sha → filled_sha`结构diff规则，仅允许合同白名单位置变化，参数source join必须完整。产物填值清单及独立输入oracle。检查点：禁止测试后半段改用forecast_document/_zijin_document；缺数据保留gap，不生成伪“真实完整”输入。
4. **09.04／G1 纯度RED。** 在批准隔离环境，将真正配置的registry、key、output、markdown、cache、日志路径全部纳入写观察，记录子进程和网络权限。测试默认prepare、validate-only带output/md、验证失败、renderer失败均不能发生未声明写入。产物OS哨兵规则及基线RED。检查点：独立Test Reviewer核路径确实传到引擎，未传入tmp_path为空不算证据；只检查exit0不足。
5. **09.05／G1 事务ADR与故障矩阵。** 定义operation_id、intent/prepared/committed/aborted/unknown、stage/final输出、registry authority、并发锁/CAS、恢复命令和所有可见状态。明确同operation重试一次commit，而同input不同显式operation可按合同形成不同publication。独立Release-Agent逐一审compute/validate/render/sign/fsync/json rename/md rename/registry commit/response九点。检查点：必须给出每点kill之后磁盘允许状态和恢复动作，不能只写“失败回滚”。
6. **09.06／G2 schema及generator小步实现。** 先修合同机器来源，再让generator使用，最后接lint/engine；每次diff保留旧版本有效行为，增加lint clean但engine fail负例与docs可执行例。产物模板原始输出、填值diff、验证结果。检查点：Reviewer-A确认实际build_template产物走完整链，版本号字符串统一不抵扣字段语义统一。
7. **09.07／G2 纯计算分离。** 实现明确无写prepare/validate与显式commit入口；签署、key创建、registry append不得藏在默认pure路径。必要的breaking change先写兼容ADR，不能悄悄改变调用者。检查点：09.04所有实际配置路径及子进程哨兵通过；Reviewer-A逐caller确认默认不formal注册，错误不被吞成成功draft。
8. **09.08／G2 事务与audit实现。** 按ADR加入stage、journal、atomic可见性、commit协调及恢复；修by_generation四元组/字符串错比较并加入已登记正例、未登记负例和冲突例。产物逐资源状态表。检查点：不得删除旧registry记录掩盖孤儿，不得把两个同prev的append链头都认作committed；独立Release-Agent核历史兼容只读与新写路径。
9. **09.09／G3 真CLI故障运行。** 用09.03真实输入在隔离registry执行P01–P09，每点分别抛异常与实际终止进程，再从新进程恢复。并行同operation/不同operation、文件占用、只读目录、长路径、父目录缺失、stdout中断；磁盘满只能受控fault facade或容量受限隔离卷，禁填系统盘。检查点：Test-Agent从磁盘读取每个状态，不信summary；无静默孤儿，同operation最终恰一次committed且所有交付物hash完整。
10. **09.10／G3 generator真正闭环。** 对两个真实模板分别运行冻结命令链generator→allowlist填值→lint→hash/capture→validate→draft→render→输出读回；再删除currency/改dimension/非法as_of/错recognition验证真实入口拒绝。检查点：独立Test-Agent检查模板结构diff、原文source join、数值oracle及全域零未授权写，不能以一种模板成功推广另一种。
11. **09.11／G4 集成与有限正式发布。** 依G1 scope可先在授权隔离registry做真实CLI正式发布；生产registry另要精确发布授权，不由DEV推导。Ops-Agent核候选版本、真实输入、签署来源、磁盘交付物、registry commit与恢复记录一致，再进行同operation重放及新operation同input合同验证。检查点：返回超时但commit已发生应被识别，不自动再次新operation重复发布；外部不可撤回动作保持真实历史。
12. **09.12／G5 独立验收。** Reviewer-C选择未被实现者固定的一个故障点与一个真实模板复演，重算receipt/artifact hash并执行真实registry audit正例。签署“纯入口零声明外写”“多资源恢复”“真实generator消费”三个子结果及各自tier；任一required失败不整包accepted。生产未发布可保持production_pending，不制造生产结果。

## 4. WP10：真正历史回测与置信度消费（12步）

准入：G0需WP08.G1/WP09.G1；G3需WP08.G3/WP09.G3。候选文件：revenue `scripts/rolling_backtest.py`、`scripts/confidence_policy.py`、`scripts/analysis/confidence.py`及实际snapshot、actuals、historical_accuracy验证/主输出消费者；G0重新确定具体路径。不得移除现有主validator重算hash/拒绝重复backtest_id的正确保护。

1. **10.01／G0 目标与现有快照盘点。** 只读列现有历史snapshot、publication/来源日期证据、actuals和评估文件，分类“当时真实冻结”“现在按历史资料重建”“无可靠时间证据”。产物历史资格清单。检查点：Reviewer-A确认后两类不能冒充当时做过预测；没有两独立真实origin不是催促补造旧时间戳的理由。
2. **10.02／G1 三类时间合同。** 明确forecast_origin、目标期间、evaluation_as_of、source publication/可获得时间、actual publication日期；预测所用资料必须在origin可知，actual应在evaluation可知但可晚于origin。产物时间规则及实例。检查点：Reviewer-B能解释每个字段不是同一个as_of；文件mtime/自签JSON日期单独不证明当时已冻结。
3. **10.03／G1 观测身份与coverage。** 冻结company/asset/product/segment/period/unit/basis、唯一snapshot origin、actual source/version和forecast node组成的observation key；规定多层级coverage、最低独立origin数、单观测cap、无矿量预测cap。产物identity/cap ADR。检查点：同snapshot换日期、拆分同actual不增加独立窗口；为预先达到7/2/1/1而改计数是不同概念且禁止。
4. **10.04／G1 真实actual与独立误差oracle。** Source Reviewer逐页核真实已披露actual，冻结同单位同期间配对表；独立分析者从底层forecast和actual手算绝对误差、WAPE分子分母、零分母/负值适用性和coverage。不得调用生产backtest/confidence函数生成oracle。检查点：缺配对/不可比重述单列gap，不剔除困难观测美化误差。
5. **10.05／G1 RED与评分政策。** 固定K01–K09，加未来actual泄漏、同原文不同文件名、evaluation先于actual、真实快照不存在、改源后重hash、跨公司替身。冻结confidence权重/阈值/cap/version与主入口预期数值。检查点：Reviewer-B核零误差单观测仍受cap，政策改变后必须按合同影响实际主评分或记录数学不变原因；不能只增加disclosure文本。
6. **10.06／G2 外部证据链校验。** 实现snapshot→inputs/来源→actuals→evaluation→accuracy的内容hash、身份与时间验证，缺文件/旧版本/不可解析都返回明确不合格；保留历史资料版本，不覆盖初始预测。检查点：Reviewer-A验证不只检查record_sha非空或自包含hash相等，不能用任意合法JSON构成虚假高分记录。
7. **10.07／G2 真正滚动与矿量配对。** 从snapshot读预测矿量、从actual读实际矿量，以10.03 key连接，逐窗口计算误差及聚合；只有actual分解时记uncovered，不把wape=None当合格。处理restatement规则必须事前冻结，原始披露和重述版本均留来源。检查点：Reviewer-A用手动独立配对核窗口不重复，新增同origin不增加有效样本数。
8. **10.08／G2 confidence真实接线。** 将policy与qualified records注入实际主confidence计算及输出验证，输入版本/hash进receipt，数值cap沿aggregate传播；不新增孤立helper留旧路径不变。检查点：相同输入更改一个qualified历史事实应影响预期误差/评分，policy/coverage限制可从最终CLI输出观察；缺required矿量不能被分部高分掩盖。
9. **10.09／G3 独立恶意变体与基线回归。** Test-Agent构造同snapshot换日期、跨公司、改WAPE重hash、fake非空hash、重复拆分、单观测完美、future source/actual、缺mine预测等，运行真实回测和最终confidence入口。检查点：拒绝/降cap发生在被发布输出，而不是测试辅助返回值；既有合法hash/duplicate校验和旧可比样本数值回归均通过。
10. **10.10／G4 真实历史运行。** 获精确数据/输出授权后，使用10.01中合格真实origin运行实际CLI，输出配对明细、误差、cap、来源与签署hash；没有合格历史origin则该“真实历史预测检验”blocked，允许另列historical_reconstruction实验但不解除cap。检查点：Ops/History Reviewer独立核当时可知性和证据保管链，不把今天生成快照换旧as_of签成历史预测。
11. **10.11／G4 输出消费复查。** 将本次合格accuracy记录交到WP09真实draft/允许的publication入口，核最终score可由独立policy oracle复算，修改或移除一条记录触发预期限制。产物backtest→confidence→output join及缺口清单。检查点：回测报告正确但主引擎未消费不得关闭；真实数据不足就保留低覆盖/置信限制，不能增加模拟窗口补足。
12. **10.12／G5 双重真实性签收。** Reviewer-C独立抽查一个origin的历史来源、一个actual原文、一个矿/segment的误差与最终score，核所有结果同三仓triplet及policy。分别签算法能力、真实历史可用性、主输出消费；算法通过但真实origin不足保持production/history_pending，不标整目标closed。未来自然观察由WP12/14负责，不能本包补造。

## 5. WP13：三公司连续真实旅程与逐批canary（12步）

准入严格依总计划R2：G0需WP01.G1至WP12.G1；G3需WP01.G3至WP12.G3（只需12a隔离能力）；每项G4另满足动作安全祖先和有效授权。WP13.G5先签真实case定义，WP12b再使用这些case持续运行，禁止互相等待成环。以下既不是启动命令，也不是实际canary授权。

候选真实入口：wiki `src/company_wiki/source_catalog/cli.py`与`worker.py`、filing `scripts/fetch_filing.py`、revenue `scripts/source_preparation.py`、`scripts/generate_input_template.py`、`scripts/revenue_forecast.py`及WP10冻结的回测CLI。此为入口定位，不保证可直接用`python 文件.py`运行；G1从当前解析器冻结安装模式、module/script与argv，不能猜命令。

1. **13.01／G0 选择不是填名字。** 冻结紫金、结构显著不同矿企、非矿企的真实entity及选取理由、四root实际身份/可用资料，结合原CA302/ZR806要求。产物选择矩阵、缺口表和每公司必需旅程。检查点：Reviewer-A检查三公司raw SHA/事实/模型结构确实不同；root没有资料记录blocked，不复制companies目录充第四root，不缩小目标后仍称完整。
2. **13.02／G1 实物盘点与授权。** 对候选真实文件读manifest并独立复核SHA/大小/公司/期间，列需provider/LLM/worker/发布的动作子类型、范围、token/bytes/cost/time/run cap、撤销和恢复方法。产物精确source/cohort allowlist与命令卡。检查点：Safety/Ops独立核生产原文不可改、原worker保持paused；有一个默认路径指向生产可写位置而未授权就停止。
3. **13.03／G1 独立真值冻结。** 非实现者从原始PDF/HTML标注必要页表、事实、单位/期间/basis及参考历史收入；为矿企独立算至少一个矿、一个分部、公司external，为非矿企按其真实经营驱动/recognition核一个分部和公司。产物oracle及事前容差/主要资产覆盖门。检查点：参考不能来自同一个模型输出或合成fixture；未来假设与已披露历史分栏，不把假设贴成事实。
4. **13.04／G1 干净环境与运行图。** 独立reviewer建立三仓精确triplet的干净checkout，按批准manifest导入真实数据隔离副本并核hash；明确read-only source、独立可写DB、registry、artifact、journal、网络deny及有限例外。产物完整环境/路径/命令DAG、前快照与reset协议。检查点：未跟踪运行必需输入须逐项审核，不整树复制实施者目录伪称clean；不修改开发者生产配置来方便测试。
5. **13.05／G2 串联可观测入口。** 只在批准测试/观测allowlist实现旅程驱动与必要trace，不直接代写事实/需求/产物/forecast结果。调用实际resolver→source preparation→持久demand→worker→export→generator→engine→render，各步骤从前一输出提取后一步ID。产物逐节点命令及receipt接口。检查点：Reviewer-A搜索并人工审查是否偷偷调用forecast_document、_zijin_document、预构造pages/手写队列complete或自比较reference；发现替身立即退回。
6. **13.06／G3 隔离RED与安全演练。** 在批准隔离环境测试existing/partial/missing/stale/amended/safety_pending、错误locator、同source换公司、失效一个role、越cohort多一ID及中途失败。构造边界状态时仅改隔离副本，并标fault-derived，不伪称生产曾有该状态。检查点：Test-Agent核失败留下上游成功receipt/真实attempt，no-network模式provider/LLM实际调用0；安全拒绝是正确结果但不是成功forecast。
7. **13.07／G3 真实资料隔离E2E。** 用三公司真实字节和真实CLI完整运行无外发可运行部分；确需LLM/下载的步骤未授权则blocked，不用mock response拿到终点。逐source→fact→parameter→node→output全join，并读回所有磁盘产物校验hash。检查点：Test-Agent重新抽取原文事实/外部reference对照结果；该层通过标real_source_isolated，不能写T3自然运行完成。
8. **13.08／G4 Batch 1。** G3及所有安全门通过后，独立Ops再次核有效CANARY子授权，执行1份精确document/source cohort；按实际动作可以在隔离真实数据环境或授权现场，必须明确层级。记录所有写集合、真实attempt、调用/费用/资源/退出状态，结束即停止领取下一份。检查点：独立source/安全review双签，0越界写、账实一致、原raw不变、回滚可验证；失败不进入Batch 3。
9. **13.09／G4 Batch 3。** 单独批准3份manifest及新增内容，复用已过case但不得借kind-only扩大范围；每份都有原文事实和独立oracle。产物逐项结果不是一个总ok。检查点：Ops-Agent复核集合准确、失败隔离、暂停/恢复和费用真实；跨公司若此批覆盖须各自事实链成立，不能用一公司的准确率代表另一公司。任一阻断项停批并保留失败证据。
10. **13.10／G4 Batch 7及复用。** 单独批准7份manifest，按前两批门继续；对同source/policy/parser/prompt/role精确重复运行第二次，要求实际download/parser/LLM均0并由独立事件/进程/network观察对账。再在隔离分支分别改变source/policy/parser/prompt，检查只有必要DAG失效重算；不能为mutation改生产raw。检查点：Reviewer签的是实际副作用计数，不是planned tasks长度；1→3→7是文档cohort，不等于三公司完整旅程自动通过。
11. **13.11／G4 三公司终点及故障恢复。** 每家公司分别验证完整输出、独立历史对账、未决事实/模型覆盖、draft纯度或另授权formal事务；真实未解gap保留blocked。挑实际持久队列/worker/publish阶段注入受控故障，在批准隔离环境新进程恢复，核本地精确对象RPO0、raw不变、append-only失败事实保留。已发生provider调用/费用不可回滚，结果未知必须单列人工处置。检查点：Ops与Accounting独立签每家公司结果，不能只审总计7份产物。
12. **13.12／G5 case冻结交接。** Reviewer-C从干净环境挑未固定的重放顺序，核三公司真实来源差异、四root覆盖、每阶段join、独立oracle、CI矩阵、全部批次G4签署及剩余限制。case定义与source/command/result hash交WP12b；只有已通过真实case可计后续自然soak。缺root/公司/关键来源或未完成所需真实tier不能整包原目标关闭。运行结束回paused；本门不恢复登录启动，也不代替7daily/2weekly/月度/drill与WP14最终资格。

## 6. 阶段审查、停止与恢复的统一签收表

| 门 | 本手册必须提交的独立审查材料 | 不能通过的情况 |
|---|---|---|
| G0 | 原条款/owner、实际路径/HEAD/hash、允许动作、依赖门与完整目标；Reviewer-A逐项签 | 以更窄helper代原目标、缺授权、未解释并发修改 |
| G1 | 真实source manifest、字段/单位/时间/交易合同、独立oracle、RED、命令/故障/恢复/预算卡；Reviewer-B及source/accounting/safety角色签 | 用实际输出生成golden、未知期间单位、猜CLI、没有kill后恢复定义 |
| G2 | 每个小diff、实际callers、source→output join设计、阶段测试及不变条件；Reviewer-A复核 | 下游仍未消费、纯函数暗写、同号测试偷换owner、修改golden救绿 |
| G3 | 独立Test-Agent在新环境重跑；真实字节/真实入口、mutation、零越界写、完整raw结果 | required skip、mock替真实路径、self-reconcile、无真正失败基线 |
| G4 | 独立Ops及相关领域agent逐批/逐公司查原文、OS/DB/磁盘、账实、授权时效及恢复 | 超scope、unknown费用、没有前后快照、只信被测ok、自然时间不足冒充完成 |
| G5 | Reviewer-C核本包全部review/result hash、原目标资格、未完成真实层级和后继阻断 | 实现者代签、没有最终verdict、将隔离E2E变生产/soak/自启动资格 |

停止时不得顺手修生产：先停止本次获授权的执行单元，保留错误、实际发生的调用/费用及未完成状态；按照G1独立审查的恢复卡只操作其精确对象。无法确认哪些动作已发生时标unknown并升级人工处理，不以重试清空风险，不删除原始失败收据。受影响G3/G4证据因代码/合同/输入变动失效时重跑对应及下游门，而不是沿用旧绿。

## 7. 交付字段与不跑偏检查

未来每包实施结束须交付：requirements映射、候选triplet与dirty说明、source/command/oracle manifests、G0–G5真实review记录、RED→GREEN结果、真实入口与阶段trace、文件/DB前后快照、费用/资源账、故障恢复结果、未完成tier列表、下一步独立授权需求。缺任一required产物保持pending，不填假hash。

最终检查逐问回答“是/否/未验证”并附结果hash：

- 原始事实是否从本公司的真实source提取，而不是换名输入？每个模型参数能否回到locator或明确假设？
- 计量/期间/权益/合并视图是否一致？模型结果改变是否由真实被消费参数驱动？
- 独立reference与oracle是否在候选结果前冻结、没有引用模型自身作为期望？
- generator真实产物是否只填值即通过主链？prepare/validate的真实配置路径是否零未声明写？
- 每个发布故障点是否从新进程恢复，并从磁盘证明恰一次commit而不是仅return code？
- 回测是否有当时冻结的真实origin，actual后来可知而未泄漏回预测，cap是否进入最终输出？
- 三公司/四root/1→3→7/第二次零调用是否分别实测？是否清楚区分隔离真实E2E、有限现场canary和自然soak？
- 每阶段独立review是否已实际完成？本文只是安排这些检查，不是其PASS证据。

本文件仅补充实施粒度，不改总计划R2门级DAG、owner边界、生产安全要求或暂停状态。
