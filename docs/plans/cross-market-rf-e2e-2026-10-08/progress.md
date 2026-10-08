# Progress

- 2026-10-08 MAIN：读取 PWF/RF/FF 技能与当前主线验收；新建独立本任务计划。
- 只读确认 RF/FF Git HEAD 和既有 WIP；生产 source_catalog 配置未改。
- 当前阶段：来源盘点、真实公司选择和独立执行接口准备。
- MAIN：冻结三公司 metadata 盘点与四配置文件 SHA；CN 已有 2025/2024 年报、2025 半年和 2026Q1；HK 已有 2025/2024 年报；US 已有 FY2025/FY2024 和 Dayu 更早年报。尚未发现 HK 最新半年/US FY2026（非穷尽物理根存在断言）。
- 已启动 `/root/rf_cn_execution`、`/root/rf_hk_execution`、`/root/rf_us_execution`；三个 agent 仅写各自 execution 工程记录与独立临时研究产物。
- Python 一行 baseline 生成有语法错误，未写穿生产；改用 PowerShell 成功生成 baseline.json。
- MAIN：六项源边界回归先RED，四文件修复后69 passed；四文件定点同步安装两物理副本，保留所有配置。
- 新增本请求专属process_trace/sitecustomize，只在显式CWP_AUDIT_PROCESS_DIR/PYTHONPATH启用时记录嵌套真实进程，不改生产runtime。
- MAIN：直调同微软FY2026有界ensure，2秒明确拒绝Dayu adapter不支持bounded acquisition；没有新下载，不隐藏原因。
# 07:17 UTC — 第二批必要修复与真实来源核实

- SID错误官方分类：先2 RED，修复半年与Q1/Q3联合官方分类，API/预算/adapter/latest责任包绿；真实官方响应保存CN执行目录。
- RF已确认混合收入：先9 RED；限制为直接收入/增长模型、真实policy证据及聚合边界，不准隐藏二次确认，集中64 GREEN并定点安装。
- 新测试自身误用claims字段、首次SID责任测试引用不存在文件均保留失败记录；纠正测试工具错误后重跑，未删除经济语义负例。
- CN/HK生产原件字节未变，只有经实读证明的source facts写入标准producer断言链；年报raw SourceRef复用已成功。
- 三执行agent继续完整模型。Dayu budget、ET FMP套餐与HTML worker缺口分开记，不用官网补充冒充集成下载。

## 07:24 UTC — 真实新下载与日期修复

- CN2026H1完整RF→FF→SID→CWP downloaded_new1，原件3,149,962B。实际调用/入库receipt在CN执行目录。
- 官方API milliseconds用UTC日历截日导致前一日披露日期；2个真实回归先失败，再更正为China UTC+08。原毫秒、原fixture不改。最终108责任测试绿（1791444092341612000）；source-facts更正当前元数据，旧下载receipt保留。
- RF一次现有短日常gate 23.297秒绿（1791444160945065600），未加入全套历史检查。
- HK、US正式计算/Markdown/不可变快照均已执行；agent正在补完整交接。全链路是否完成仍待独立审查，不因engine绿而改采集partial结论。

## 07:31 UTC — 独立审查启动

- HK交接齐全，供应链partial、模型强校验已跑、4/6沟通检查。启动全新 `/root/rf_hk_independent_review`，全量69claims/51params与原文/进程/producer接口独立审查，不自行改执行产物签收。
- 未实施Dayu预算桥、ET能力路由、HTML初处理、季度/定性目标表达在 follow_up_plan.md 给出责任层与真实集中E2E设计，避免后续只贴小补丁。
- 本轮工程记录518个小文件约1.65MB；没有新增永久全量转换缓存。command_integrity核对起止/output字节及SHA，目前零不一致。

## 07:38 UTC — 两家公司独立审查及第一批语义问题

- US完整122claims执行交接已完成，正式模型green但供应链partial。启动新的 `/root/rf_us_independent_review`，重新视觉读取22页原始官方PPT、季度/年度/CC口径等。
- CN正式engine/强验证/同源render/逐情景算术/snapshot已绿，交接整理中。
- HK独立审查发现订阅反证页码错绑、网易基准未绑claim、客户集中度缺claim；main findings记录修复队列，旧不可变快照保留，新版再由reviewer复查。

## 独立审查追加

- US逐页22/22PPT与全量artifact/进程账完整；发现8敏感性±5pp误写5.0（实际±500pp），P1需输入单位修复及完整依赖重算。72增长rationale仅基数摘录的证据弱项也需修复，不以透明assumption掩盖引用不足。
- HK45分部/情景/年值、15sensitivities、全部driverallocation及两年producer复用独立重算通过；当前源URL404在查真实官方替代证据，不能把本地SHA正确当成URL当前可用。
- CN实际拿到官方SSE195条问答557,100B，按guestCompanyName/companyId/logo精确筛出8条本公司回答；新增原文支持，准备v2，旧snapshot不改。

## 07:56 UTC — 三执行交接及登记审计修复

- CN v2正式交接封存：73关键命令、16失败尝试，344artifact SHA；195互动+29预征集，精确本公司8+1。新的 `/root/rf_cn_independent_review` 开始全量审查；三执行阶段完成。
- HK独立发现registry审计工具误报；MAIN 7新行为回归先3 RED，修复后发布事务等37 GREEN。定点同步审计runtime及单位说明，未改数值引擎、生产配置、旧快照。
- 第一条安装指令含不属于当前runtime闭包的新测试路径而被拒绝，保留失败记录；按真实安装接口改为只同步两runtime文件。

## 08:02 UTC — 已验证修复提交发布

- RF 全部本轮修复责任包128 PASS；现有daily 25.141秒绿，108 smoke PASS；普通pre-commit三hook通过。仅16个本轮文件提交 `08673cf8`，已推origin/main；三个owner assurance日志仍保留未提交。
- SID先用干净已提交HEAD archive+只覆盖本轮5文件，排除全部owner代码，101责任测试PASS，独立tmp自动清理。这与此前包含budget包108测试是不同清单，不混报数量。提交 `c0f07e1` 到当前维护分支v2-clean-rewrite，未合并旧StockInfoDownloader主线；owner14项保持。
- CN独立审查发现服务未来增收rationale误用会计政策、客户集中度/行业未来增速缺原文claim，以及公告只有标题不能记全文checked；正在完成全量复算与单批修复清单。

## 08:14 UTC — 首份全量独立审查及输入修复

- US初审封存FAIL：122claims/90params/16history共228逐项记录，17定性项及22/22原始PPT。8问题中US01–06/08交原US执行者单批v2修复；US07采集/ET/Worker仍BLOCKED。原v1四文件路径与字节保持，新版放独立v2子目录，再由同一独立reviewer复查改变依赖。
- HK完整review已输出，包含145逐项事实/参数/历史/九维/沟通记录与13问题（登记工具1项已解决）；待reviewer封存后派原执行者单批v3修复。数学与原文收入数字独立通过，不等于公开日/证据语义完整。
- RF远端quality精确提交08673cf8成功，约40秒（37747048408）；SID维护分支c0f07e1已推，GitHub API没有该commit workflow run，不冒称远端CI绿色。
- MAIN准备最终交付归档脚本：最终签收版本按明确selection选择，不猜文件名；CWP raw先重新通过producer打开验SHA，保持SourceRef不额外复制原件。其余本任务来源/旧快照按SHA只留一份，生成路径映射，丢弃可重建的临时栅格/解析文本。未执行归档/删除，审查所需文件仍完整。

## 08:18 UTC — 三份初审完成，单批修复并行

- CN初审PARTIAL（161逐项记录），原文金额/并表/真实新下载和复用/27数值路径/4敏感性/4驱动均绿；CN01–03证据/残差范围/公告覆盖待修，CN04来源URL日期仅诊断。原CN执行者正在独立v3修复。
- HK初审FAIL封存：33检查/145逐项记录/13finding，其中registry已解决。原HK执行者独立v3处理claim、policy、sourcefacts观察文字、日期不确定与H2残余情景解释；无法证明的来源/供应链不改成PASS。
- US原执行者独立v2修输入语义与目标映射。三个修复agent只写各自目录，原sealed版本/快照与原manifest均保持；完成后各自独立reviewer复查改变的依赖，不重复无变化全文审查。
- MAIN已清理自身13份补丁stage副本207,360B，仅在核对绝对边界与无reparse后删除，原始文件/研究/审查均不动；完整SHA删除清单见cleanup_staging.json。

## 08:31 UTC — 已有生产处理能力与本轮资格分开

- MAIN重新读取原R3正式生产/消费记录后实跑CWP与installed RF公开narrative入口，微软66324B原TXT对应正式摘要106792B、49证据同SHA；as_of:null两read通过，explicit2026-10-08两read拒绝，原公开日unknown保持。
- 这是真实现有CWP处理/虚拟化能力，不等于本轮SEC HTML已被Worker处理或RF已消费摘要。既有成熟能力不能因新预测链缺口而泛称不存在；日期未核候选也不能说“本地没有电话会”。零新Worker/模型，旧199534tokens/$0.110737账本不动。
- CN修复实际用有界SID取得9份重要公告全文。新增300000万元属地达产收入目标缺年度/达产年份，不能加成公司年收入；HQ研发可用日顺延2027年12月需进入capacity反证。待新版与独立复查，原模型不盲增收入。

## 08:43 UTC — 三修正版封存，独立复查并行

- CN v3 106 claims、HK v3 325 claims、US v2 502 claims分别交接；执行者无权签收自己。原三独立reviewer已各自复查变更闭包，原初审保留。
- CN达产属地收入目标保留文字target_period、ambiguous/空measurement_periods/mismatch/unmodeled，无虚构target_year。未取得激励schedule不宣称全部管理目标完整。
- 最终归档规则收紧为“未知文件保留”。明确列出58份已核可重建栅格/HTML解析文本；扫描全部旧input的source capture保护旧版本来源。命令stdout/stderr TXT以及其他未知TXT不得按后缀丢弃。归档和测试目录清理尚未执行。
- Git只读核对：RF主线修复和SID维护分支均远端同SHA，owner WIP原样。CWP实际主线master；先前误查询origin/main失败无写入，已核真实branch/remote，不复用错误ref。

## 08:55 UTC — CN签收，HK质量标签残余修复

- CN独立recheck_v3封存：106claims/42params/19公告及9PDF59页复查，模型ACCEPT_WITH_LIMITATIONS，产品E2E仍PARTIAL；CN01/02/04关闭，CN03原覆盖错误关闭但原激励schedule/IR/Worker等gap保留。83新artifact与旧v2保持，正式重现及来源复用全绿。
- HK独立复查发现v3仍将仅证明网易竞争的peer节点标one_step/noncontrary，导致Games evidence_status从limited错误升triangulated并移除confidence limitation，虽然金额和score未变。不能只靠字节/算术绿签收。原执行者获窄幅v4分类修复，旧v3不改；同reviewer再查engine标签/置信度全依赖。
- 审计日志常见API key query/Bearer明文模式只读扫描零匹配；未输出环境变量或凭证。本任务临时日志与源码不承载凭证。

## 09:10 UTC — 三份最终复查封存及交付清理

- US v2独立复查封存：US01–06/08 CLOSED；72future/33目标/502claims/8敏感性、正式技术链均PASS，US07仍BLOCKED。研究产物条件可接受，产品E2E PARTIAL；原v1与初审SHA保持。
- HK v4独立复查封存：HK-V3-R01/R02 CLOSED；7处diff、325claims/53params全文不变，188旧文件与51runtime保持。Games limited/warning恢复、score64，所有金额/allocation不变；完整模型技术链PASS，产品E2E PARTIAL与来源/校准限制保留。
- 最终selection明确CN v3/HK v4/US v2并绑定三个独立review JSON SHA。研究产物交付到RF/output/cross-market-rf-e2e-2026-10-08，旧路径以delivery_archive_index.json解析，不重写旧input/snapshot/manifest。
- 归档辅助脚本首跑错误混用“snapshot完整结果SHA”与“forecast经济载荷SHA”。按实际revenue_backtest公开实现核对后，采用validate_snapshot/validate_published_forecast及嵌套economic result SHA；已审产物字节和测试标准不改。失败保留，再跑9.932秒成功。
- 本轮TEMP237文件110,034,773B已逐个核原字节及保留对象、精确目录/无reparse后清理。146唯一对象56,798,301B保留，CWP原件引用避免复制8,158,067B，62明确可重建中间件12,539,811B不留；全部原始来源字节保留，生产原件删除0，中微新半年报继续在原库。
- 最终7份命令ledger共359起止配对，68失败命令保留（含RED、provider拒绝和已修中间错误）；起止缺失0、输出SHA/字节不一致0。后续Git发布记录只纳本任务工程目录，邻仓owner WIP不动。

## 09:18 UTC — 发布记录的字节保持

- 本轮新增审计目录局部.gitattributes禁用换行转换，保留原记录CRLF/LF。只影响本次审计，不改全仓Git设置。原始日志的空白必须保留，不为可选diff whitespace检查改写日志。
- 1470份暂存文件通过git cat-file --batch逐blob比对工作区SHA/字节，差异0；派生检查报告不自哈希。该检查证明发布内容字节，不能替代前述事实/模型独立审查。

## 09:24 UTC — 主线发布和远端CI收尾

- 工程审计提交c72d532baa117d97d088cf0c8bae78e13cd7849a已推origin/master；正常pre-commit按文件范围跳过生产代码检查，正常pre-push快速契约smoke GREEN。1471个工程文件完整保留，不含原库删除或邻仓owner代码。
- 精确完整SHA的company-wiki远端CI https://github.com/zhengcb81/company-wiki/actions/runs/37756152210 成功，09:22:08→09:23:15（67秒）。首查短SHA空结果仅是错误筛选，改完整40位后取得实际run，不误报没有CI。
- 本轮Phase1–4审计任务完成。后续能力缺口仍未实现，独立follow_up_plan不涂绿；CWP/RF/SID发布与预算/原件/配置/临时清理结论见归总。此后仅提交共享PWF收尾Markdown，不重跑生产或外部模型。

## Phase 5 — 用户要求固化可复现的公司端到端套件

- 施工前写regression_suite_plan，先失败分类/域错误/故障清理小测试，再实现tools/cross_market_suite和benchmarks/cross_market_rf。已固定3公司、71检查点、所有来源与输入/旧结果/快照/独立审查SHA；不覆盖前轮记录。
- 16轻量责任测试、ruff通过；full真实原件运行92.555秒；CN/HK PDF及MSFT TXT Worker 96/12/49证据，原语言、不重复推理，正式engine/Markdown/新snapshot/registry及原件搬移/错误SHA/重复注册均实际运行。微软HTML和图片PPT由实际Worker拒绝，明确BLOCKED。
- 便携去重数据包35文件56,835,555B；用不存在的生产catalog参数，从此包full重放90.309秒，71状态完全一致，0regressed/0missing。包验证后删除，Git只留约0.34MB清单/报告，不复制大量原件。全部随机TEMP恢复不存在；Windows只读注册账失败演练也已恢复。
- 在线core真实运行53.438秒：CN H1 2026通过实际SID下载1→CWP入库3,149,962B→第二次download0→RF真实读取。港/美股缺文档ensure仍BLOCKED；年报复用下FF companion实际返回zero_cost_budget/provider_calls0，ET未启动，不冒称无套餐或已调用。0收费模型/Dayu零改动/邻仓WIP未动。
- 新检出MSFT不同Python hash seed跨进程强校验失败；原情景金额不变。基线保持FAIL，单列P0根因及实施卡，不改断言、不固定seed掩盖。当前总计46PASS/3BLOCKED/1FAIL/14NOT_RUN/7NOT_APPLICABLE；新一轮研究/线上供应商/新摘要实际消费不能由离线固定输入替代。
- 普通CI只增加16小测试，真实下载、PDF/Worker、多仓流程不加入每次commit。README提供run/pack/compare、环境/退出码、完整新研究大节点卡及故障处理。旧总体计划导航新增入口，不重写原完成签收。
- 提交前host-assumption-guard抓到负向测试写死机器盘符路径，已改为tmp_path生成绝对路径及平台无关Windows drive属性测试；不绕过hook。16项重新运行0.25秒全绿。

## Phase 5 发布收尾

- 套件提交71fec1554abf1b0fc6350da28589593b8e345adb已推origin/master；正常pre-commit/pre-push通过。远端CI https://github.com/zhengcb81/company-wiki/actions/runs/37765260153 成功，10:42:41→10:44:09 UTC（88秒；Fast checks job84秒）。基线的产品FAIL/BLOCKED不因CI成功改写。
- 最后16项单元测试0.25秒，独立pytest测试目录只剩keep哨兵4B，按精确路径/内容及无reparse复核后删除，恢复不存在；原件删除0。工作区无邻仓改动。本次只固化回归基础设施，follow_up_plan中的产品能力和P0置信度问题仍待实施。

## 用户要求：全部问题按根因治理

- 新增root_cause_remediation.md，统一问题记录六字段、责任层分组、最小反例和共用改造、大节点回归及严格区分未运行/供应商限制；不新增人工审批或每小节点签收。
- 更新follow_up_plan中过期的“先完成审查”指令，审计/固化已结束，下一实施项为P0跨进程计算确定性。已有修复与仍待实现分别标示，原基线/独立审查/原件均不改。

## 安排第二组完整端到端泛化验收

- 新增second_cohort_generalization.md，规定全部改造后再选A/H/US各一家不同公司，按本地/官方真实资料选样并固定，覆盖复用/新下载、正确工具、规范化/摘要真实消费、完整RF技能及独立审查。
- 已写入task_plan和根因施工顺序；沿用现有检查原则、配置及累计预算，独立测试环境退出恢复。此轮只更新计划，不提前跑新公司、不声称已通过、不触碰封存的第一组清单或原件。

## Phase 6 开始实施

用户追加预批并明确选择累计USD20、2,000,000 tokens；包含原消耗，详见phase6/budget_authorization.md。当前实现/测试收费模型0，继续使用原配置和现有累计账，未知费用不清除。

- 已启动持续目标，读取当前PWF和RF技能；RF main=08673cf8，owner未提交仅3个assurance日志及output，不能重置。按AGENTS的explore建议委派Dayu和parser两项只读结构探索；源码修改仍由MAIN按责任仓推进。
- RF无AGENTS文件，读取尝试FileNotFound不作为项目缺陷；此前只读盘点也确认其父链无此文件。准备独立工作树与最小跨进程RED，不改失败成功定义。

P0候选72ce94c1已在独立RF分支提交，62责任测试3.79秒、125快速检查19.75秒通过；旧新五类金标语义核对通过后才刷新新revision金标。正在跑固定三公司full，待确认process_seed_stability改善及其他检查无退化后才并main/定点安装。HTML/PPTX和provider缺口仍待施工。

P0大节点签收：RF候选72ce94c160bbb5b9399c8716307588b443a72a83的三公司full108.527秒，47PASS/3BLOCKED/14NOT_RUN/7NOT_APPLICABLE，0FAIL；与封存基线比较1改善（US process_seed_stability FAIL→PASS）、70不变、0missing/0退化，TEMP恢复不存在。已快进main并逐SHA确认owner三日志未变；安装计划只有.agents/.codex两份现存副本，各4文件，未选择文件漂移0。P0代码问题可关闭，其他能力仍未完成。

P0发布收尾：72ce94c1已推origin/main，正常pre-push的125项检查通过；[精确SHA远端CI](https://github.com/zhengcb81/revenue-forecast/actions/runs/37820231186)成功。两份现存技能副本定点同步共8文件，配置/output及未选择文件保持不变，剩余漂移0。独立RF工作树只剩本次五个pytest生成目录，核对TEMP绝对边界、HEAD及无reparse后清理并移除已合并分支；主仓仍只有原owner三日志和output未提交，原件删除0。

P1下载层基础责任组件完成：8个RED实证后修复actual usage、两维原子计账、精确adapter版本和hard-timeout最后完整checkpoint；未知最终用量不自动重试，预算usage_complete=false保留未结算状态。新增同步/异步HTTPX包裹覆盖redirect/retry/error body/HEAD/gzip/late chunk/slow drip/限时退避。79项责任及既有公共入库合同正常OS12.19秒通过，新增真实子进程hard-kill保留usage证明。达到额度时仍可完成本地验真/入库，只有新provider请求拒绝。Dayu桥和真实两个市场仍未完成，不能把基础组件绿记为P1全绿。

335df5d3已提交推送，远端CI37822907874收集失败；本机单独/全量收集都绿，取得真实日志后证实requirements入口漏声明HTTPX、openai当前改依赖httpx2。先新增直接依赖一致性RED，再修两安装入口；快速push只增加这条静态责任检查，等待修复SHA远端验证。没有删除新功能测试。

CI修复7071e035已推master；[远端CI37823912376](https://github.com/zhengcb81/company-wiki/actions/runs/37823912376)成功。继续P1 SDK桥：跨年/52周SEC候选FY与quarter（fetch必须原件DEI确认）、HK明确标题年份27测试通过；公开SDK metadata-only发现/历史JSON/原始profile保留7测试通过；新配置兼容3项通过（首次RED返回仍运行即修改，未算RED，另在隔离Python装载已提交旧配置补证真实3RED）；fetch客户端计流/原件错误拒绝/SDK资产清理4通过。新桥尚未切生产、尚无真实市场下载，不以这些mock绿代替live。父进程分配scratch并在hardkill后清理，使用UTF8明确编码修正Windows测试读路径的GBK错误。

P1 SDK桥集中节点：真实Dayu公开SDK/实际venv离线联调，两市场metadata-only发现→唯一原件GET→CWP真实入库→SourceRef/零网络resolve复用通过；117责任/旧公共合同/SDK集成测试24.49秒全绿。独立只读结构审查发现3项共性缺陷，7RED/41PASS实证后修复：按声明的XBRL TR4/5日期转换规范化原文并保留观察值，不猜日期；先限定HK请求范围再验证标题年份，未知年份不能冒充；实际GET必须完整200且无Content-Range、长度一致，receipt使用GET而非HEAD版本头。SDK测试夹具的lambda替换HTTPX类导致真实SDK子类导入TypeError（零HTTP），改为真正transport子类，未改Dayu。供应商源码/缓存前后不变；费用0、模型0。真实网络下载及生产配置提升仍待下一节点。

live套件适配新桥：CWP-owned bridge代码和provider-state必须映射独立HEAD export，已有外部venv只读复用，SDK import优先明确provider cwd，防止editable安装绕过冻结版本。先新增路径隔离RED（旧入口缺能力），再实现共用配置命令展开；不改变原71检查点/旧样本。Next Step：提交SDK桥后用复制候选配置运行真实两市场FF→CWP→零下载复用→RF读取；确认后才提升生产配置，8-K/6-K exhibit与HK英文仍明确列未支持。

P1真实大节点已通过：d77cd6c1精确SHA远端CI37828217259成功。复制SDK候选配置的full/live278.703秒，50PASS/3BLOCKED/10NOT_RUN/8NOT_APPLICABLE、0FAIL，test_root_restored_absent=true，结束前隔离数据141,417,079B全部清理。三市场真实FF→对应provider→CWP原件入库/SHA/身份/期间→再次0下载→RF读取均PASS：CN中微H1原文3,149,962B、HK腾讯H1原文5,451,089B、US微软FY2026 HTML8,585,610B。新Byte SHA见phase6/dayu_sdk_live_1.json；正文没有留重复测试副本。电话会仍NOT_RUN（zero_cost_budget旧逻辑），格式能力等仍待施工，产品整体PARTIAL。此live与replay不同mode不作虚假同模式改善比较。

真实进程观测补充根因：Windows venv解释器有redirector子进程；原subprocess.run只杀根，owned grandchild在timeout后仍写文件。新增真实子孙进程1RED/10PASS实证后引入CWP-owned OS进程树运行器（沿用FF已验证的Job/barrier/管道/截止机制，不跨仓import），在临时根清理前停止整个tree；timeout保留最后usage下界，输出上限故障也不自动重试。48既有adapter/入库与usage合同13.63秒、4管道上限/阻塞stdin/嵌套Windows Job测试1.35秒均通过，SDK两市场再次离线入库验证。正式source_acquisition配置提升为raw-only bounded SDK，旧Dayu CLI兼容入口保留；默认180秒且不启动Docling/模型，仍取请求更小额度，Dayu源码与workspace零写。Next Step：FF/ET费用与能力门的责任层改造。

P1 FF/ET费用能力集中验收：6RED/7PASS→ET费用13PASS，实际用量3RED及FF7RED后共用接口修复；ET原API/CLI/真实Worker截止74PASS33.77秒、FF26PASS5.60秒。0.00费用的实际FF→ET CLI/Worker→CWP离线链入库/验SHA/零HTTP复用/timeout清理通过。旧stderr静默合同5失败后改用显式--report-usage，不改旧调用默认或内容schema。对外v2白名单吞掉新用量另1RED后补字段。真实FMP精确Q4 FY2026请求2.117秒、HTTP1次，provider_entitlement_required，费用0/模型0；账户外部BLOCKED保留。施工细则与原始小报告见phase6/transcript_capability_implementation.md和et_fmp_live_probe.json。

已发布 ET282e8908与FF3945efb到main，owner未提交列表不变。FF远端37832787908实际418行为通过/5skip/78subtests，仅complexity_ratchet限制新顶层函数15>10失败；改共用回执身份/计数类型分别负责（不放宽测试阈值），49相关测试7.58秒和commit静态检查通过，697af966已再推main。安装三份既有FF副本定点4文件共12，首次postcheck把Windows分隔符当成未选文件误报；修正as_posix后验证选定字节相同、未选内容不变，报告见phase6/ff_selected_install_sync.json。共享PWF仅统一LF，避免上轮混合CRLF的diff-check误报。

用户要求新分包：新增R6-FORMAT/RF-INPUT/FF-CAUSE三卡、总分工/交接格式；按真实未完成机制拆分，不重发旧卡。分别创建独立codex分支与工作树，CWP/RF稀疏检出避免历史/原件复制；worktrees.json记录精确SHA、干净状态、implementation_started=false。MAIN保留共享PWF、来源资格和现有Worker集成，三线各写独占项目/子目录，待用户发出开工。

收尾发布证据：FF697af966精确SHA远端CI37833957140成功；ET没有工作流（API空列表），使用实际74责任测试/跨仓E2E，不报CI。跟进同一FF运行文件在3份安装副本单点同步，无未选漂移。清9个已完成owned测试根释放1,875,413B，2已并线的临时FF/ET工作树及其缓存移除；新3分包工作树保留，18,580,471B，无原件副本或密钥。主体目标active，分包不构成暂停。

### 三卡交付复核与 MAIN 调查记录

- 再核 R6-FORMAT / R6-RF-INPUT / R6-FF-CAUSE：三工作树实际存在，分支与登记的精确基线一致，git status 均为空；允许现在并行开工，MAIN 维持原独占边界。卡、接口、PWF 和测试包已在总 README 链接。
- 邻工作树的默认沙箱 git 只读报 Permission denied；正常 OS 同一只读命令成功，未修改工作树。调用 gh 查询 CI 失败因本机无 gh 命令；不是远端 CI 失败，不将失败工具输出写成 CI 状态。
- 只读来源资格结构调查与出版证据注意事项写 phase6/source_qualification_investigation.md；尚未代码实施或宣称待证问题已修。原件改动0、收费模型0。
- 改用公开 GitHub REST 查询完整 SHA：a7c6705cd4c5158cc2435d7c74a917c001454e4e 对应 [CI 37834777705](https://github.com/zhengcb81/company-wiki/actions/runs/37834777705) completed/success。不使用缩短 SHA 的空查询或旧取消运行冒充结果。

来源资格先 RED：新 contract 运行 6 失败，其中 1 是新夹具错误（SourceCatalog 不支持 context manager，不算产品 RED）；5 项实际缺口，其中真实原件删失＋未知公开日错误 AMBIGUOUS 已复现。CLI 夹具已改显式 close/实际 SHA/既有 helper 签名，随后重跑；不修改生产原件。实现前已有 source-facts/current-preview/as-of 行为保留。

夹具修正后 29RED（含新纯分类 API 缺失）→29PASS/3.38秒；实质错误原件删失已独立复现并改善。共用日期分类接 query/resolve，排除候选只输出逻辑引用，空诊断保持旧 CLI 字段。正常 OS 的两项对照回归 2PASS/4.03秒；此前沙箱集中 83PASS/32FAIL，全部失败集中在真实 provider 子进程和原子 artifact prepare，仅对照证明环境差异，不据此宣称另外30项已绿。正在正常 OS 完成集中回归；不会放宽原断言。

正常OS集中188项：185PASS/3FAIL（64.35秒），原沙箱失败32项均通过。新增E2E发现一个真实更深的责任耦合：原件恢复已成功，却因历史日期未知被 canonical writer/ensure 报失败；另一新夹具须把 SourceRefValue 转为正式 SourceRef。两个均处理后集中24项23PASS/1FAIL（7.10秒），唯一剩余是旧机器原因码未登记。改共用返回函数的具名，避免通用result的静态签名混淆；登记实际公开机器原因，不放宽测试。下一集中覆盖入库/ensure/日期与旧contract全部，然后三公司冻结回归。

用户确认三张施工卡已分派，README和Next Step同步；MAIN继续来源资格/现有Worker，所有外包独占目录保持零写，不新增第4–6张卡。

来源资格后一集中：231项229PASS/2FAIL，72.99秒，全部行为绿，2FAIL为已登记原因码没有stage映射。新增宽期间导入引用1FAIL/1.74秒是真实设计耦合：2025未知公开日原件被历史选择器排除，writer引用查到2024。用户进一步要求系统性减少身份核验，当前主任务升级为责任层收敛，先计划和RED，再实施。三张外包写范围不变。

身份责任只读结构审查完成，四/五次完整resolve、候选冲突污染全请求、writer与coordinator名称规则不一致均查实。先18项8RED/10PASS，再3项3RED，开始共用责任层重构：writer工程结果2.0只返回SourceRef，原文sidecar1.0不动；service一次历史结果查询、缺辅助身份不拒绝、坏本地候选排除后可取正确目标、普通candidate允许未知公开日、两个入口复用字段比较规则。集中88项86PASS/2FAIL，14.33秒；两个为新fixture exact请求遗漏及stage顺序，已更正。尚未发布或宣称全量绿。

第一次更广集中261项259PASS/2FAIL，85.29秒：一个stage次序错误修正；HTTP本地capture旧测试要求全局阻断，与已提交HEAD行为不一致。只读加载HEAD旧resolver对照首跑因SourceRequest类绑定错误失败（夹具错误），修正绑定后0.97秒重现同一capture_sparse错误；证明不是本次放开了原本有效的防护。新测试保留HTTP不可capture-ready/无https_url的断言，并要求已有原文可复用。再次猜测tests/contract/test_source_catalog_fc808_v2_binding.py失败，已rg --files核对实际source_operation_v2.py，禁止复用错路径。

目标按用户最新要求扩展为两组验收后继续归纳共性问题入PWF并实施的循环。只读审查发现formal envelope缺entity_ids/期次及任意metadata冲突、Reader对runtime_policy损坏阻断等残留，加入最高优先级简化方案下一集中节点，不把当前入库重构宣称全部门禁清理完成。

第一责任节点最终300PASS/106.36秒，公开v2、envelope、真实ensure/CLI/Worker、并发及原文负例均绿。补充未指定市场1RED/5PASS发现新helper误拒绝None，改为只比较显式请求市场并由candidate登记已知市场；49范围/writer/single-intent PASS/15.10秒。ruff所有改动文件和mypy五责任模块通过；精确记录见phase6/identity_responsibility_acceptance.md。先提交冻结版本再三市场full replay，随后继续剩余元数据/旧policy门禁节点，不宣称整体完成。
