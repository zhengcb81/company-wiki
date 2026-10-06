# Progress：激进简化实施

## 2026-10-06 — N4C两家真实批次与N5三包

- MiMo run05已终态failed/362.258s：年报P01实际摘要20claims/96locators、RF read0、quality verified；招股P04两次MODEL_TIMEOUT后返回计量但SUMMARY_INVALID，无final；policy skip/RF read0/0LLM。DeepSeek run06 completed/48.427s：IR13claims/11locators与英文电话会14claims/14locators，RF read0、完整引用回放、原语言通过；IR needs_review仅质量诊断。receipt中中文实际无U+FFFD，shell显示乱码来自stdout编码，不改原文。
- 两批终于finally恢复根absent，原件/生产/用户配置/owner不变。峰值root21769241/1221344 B、RSS497098752/353435648 B；实际三个real final共245396 B，policy2×1418 B，未保留生产新final。旧账+本轮累计136108tokens/63228microUSD，unknown6/unsettled0，费用扣FX后余34008microUSD、token23892。招股同请求最坏24863不可直接复测；先诊断规则，再修复/合理降低输入预留，不能改8192/清账/冒称四类全过。
- 初次只读状态probe用relative.as_uri失败已改用现成RunStore；后续一次对已终态session读取Unknown process id，直接验run06终态收据，未重启批次。两次猜不存在summary文件/Windowsrg glob读取错误仅是定位问题，后续使用CodeGraph定位，不能当产品RED。
- 新N5施工总包和3独立卡已写：CWP仅新benchmarks质量目录；CWP仅新只读raw_duplicate_audit工具目录；ET仅本地scraper/TXT receipt，三独立worktree且物理/写集不重叠。StockWiki只读调查无明确独立待办，CodeGraph索引陈旧不据之编造任务；ET真实空/错期/Characters虚报复用缺口已Mock复现。未启动外包，不等N5才处理MAIN招股失败。

## 2026-10-06 — N4C预算答复到达，恢复真实节点

- 用户明确批准累计token从60k提高至160k；费用仍$0.10，旧58523tokens/33884microUSD及unknown4、FX2764照计。RF本地/remote main仍6e6b817a，仅owner两份周日志dirty。先MiMo年报/招股，再按实际余量DeepSeek IR/英文电话会，配置参数保持，不再等待预算答复。
- MiMo run05 exec在CreateProcess前被自动审批拒绝，尚无live handle/模型请求。理由为资料/目的地授权未具体覆盖MiMo（此前MiniMax明确授权）；已一次UI询问两家与各自两份资料，不换端点绕过。run05测试根/付费收据未创建，账本不增加。批准预算与此次外发权限是两个不同事实，等待仅具体外发答复。
- 用户随后明确授权上述两家及对应资料外发，run05已实际启动（MiMo、年报/招股+policy、P4计算/单model）。此前拒绝不重复问、不绕过；运行结果待实际终态，未称通过。

## 2026-10-06 — N4C跨日计费接线补漏

- 上一turn为progress：P5-RF卡状态修正及PWF 11cffb2已发布，pre-push GREEN。fresh RF main/remote仍6e6b817a，仅owner原有两份周日志dirty。
- 发现待用driver只算Oct5收据，替换为已提交preflight.prior_budget统一汇总；所有日期/unknown计入、重复run拒绝。实际小夹具验证跨日+107 tokens/+211 microUSD与重复拒绝，finally清根；真实账58523/33884、unknown4不变。报告n4c_campaign_accounting_check_2026-10-06.json。
- 默认60k真实命令在ROOT/POST之前exit1，明确预算不能预留配置8192；run05收据/测试根未创建。help正常，0 provider/模型/下载。沙箱psutil DLL被ACL拒绝，正常用户环境执行后成功显示help及预期预算拒绝，不是产品故障。临时driver改动和重新构造步骤已记入N4实施细则；没有新增生产控制或更改配置/cap。
- 剩余N4C真实产物、consumer与总空间验收依赖累计token cap答复；没有live进程或待运行CI可当作verified wait，不改变目标或宣称完成。

## 2026-10-06 — P5-RF交付通知复核收口

- 交付worktree干净，a74b9ceb完整为main祖先、main..交付分支无提交；RF本地/远端main均6e6b817a。官方API再次确认代码ca67eab7的CI37391526925 attempt1 completed/success。沿用正式MAIN验收收据中的108个不同case分步GREEN、107项pre-push及真实默认CLI/篡改反例，不重复长测或合并。
- 修正RF独立施工卡过期ready标题，P5三线均已验收发布。owner周日志SHA不变，未改RF代码/原件/用户配置，0模型调用。沙箱git status产生大量ACL假删除，正常用户环境只读重核后确认仅原有两份周日志dirty；不据假删除恢复或清理文件。N4C累计token cap答复仍待，交付通知不视为预算授权。

## 2026-10-06 — N4C离线恢复点实证

- 代码061f534d941054d6489d4a2147e24be6f89b62b8已正常提交/推送，pre-push GREEN；精确CI37400256960 attempt1 completed/success、job73秒。没有盲重跑。当前模型cap待答复这一条件在P5交付复核、S6收尾和本轮预算实读中连续存在；独立S6及当前RF/四样本/账本准备已经做完，CI也已terminal。剩余真实POST/产物/消费者/空间验收需要预算答复，无运行任务可继续等待，不额外新增审查或无关清理。

- 上一目标turn属于progress：S6实际控制/说明/短smoke收尾及精确CI绿已发布5339eac。本轮fresh RF main/remote6e6b817a、owner周日志SHA不变，新增可提交tools/n4c_live_preflight.py并实跑零模型入口。
- 原旧AUTO及保存收据合计58523tokens/33884microUSD，unknown4/unsettled0；60k剩1477、扣FX后美元proxy剩63352microUSD。四真实raw SHA/size、当前RF6模块bootstrap/help、Config加载两家Flash均通过；独立n4pf根finally消失，原件/生产/用户配置/owner不变。报告n4c_current_main_preflight_2026-10-06.json不含秘密或原正文，0外部provider/POST/download。
- 待用临时driver RF_HEAD改当前6e6b817a，样本参数支持P01/P04和P07/T01两小批，实际help成功；节点C仍需四类型真实产物+RF消费，不能用两种样本或GET/Replay代替。160k累计token cap答复仍待，未改默认60k/费用$0.10/模型8192参数。
- 首次Ruff E402来自必须的项目loader bootstrap，明确标注后GREEN；一次无匹配rg inventory exit1不代表运行失败。preflight与交接已发布，预算答复到达才能实际POST；没有重新清库、长E6或修改RF/Dayu。旧unknown实验根只读量461338 B，其中账本425984 B，不是GB反弹；保持唯一费用事实，不为省几百KB删账。

## 2026-10-06 — S6当前流程与无效控制收尾（已发布，精确CI一次GREEN）

- 上次目标turn属于progress（P5交付状态修正已推送）；本次完成S6，代码e481578872309f50141fcd2555b1e8a206bd7a47正常commit/push，钩子GREEN。官方API确认CI37399248994 attempt1 completed/success，所有job绿，不重试旧失败SHA。S6complete，全目标仍active，未宣称N4C真实摘要成功。
- N4C预算答复尚待，已向用户明确60k余额1477不足配置8192预留，请求160k、费用仍$0.10；旧账照计。实际待用driver位于tmp/n4c_provider_live_driver.py，RF_HEAD仍历史8a153f33，正式RF已6e6b817a；开始新批前须只读核并更新其固定RF依赖/CLI导出，不从旧模板猜接线。P01/P04、P07/T01及policy的真实验证范围按节点C，不能仅以GET或Replay宣称四类型模型验收。

- RF fresh主线/remote6e6b817a，owner两份周日志SHA未变；不写外仓。重写README/OPERATIONS/ARCHITECTURE，更新source-catalog/AGENTS当前provider、目录抽象、独立进程并发及存储已完成状态，三份旧手册/调用者审计标为历史。
- 移除无运行调用者的10份acceptance/lock/known_bad/work-unit/full-pytest控制JSON及2个忽略失败的旧cron壳。保留显式架构检查器，规则改为当前Config/有限runtime接线及source不导入下游；取消旧proposal人工审批/冻结writer强制接线/全scripts零写入正则。
- 四项旧全文producer日常smoke换为当前业务证据、招股书上下文、final/golden绑定和原件SHA更换拒绝；数量仍12，既有6项真实CI回归与诊断/read-chain保持。候选4 passed/0.58s，集中38 passed/1.59s、Ruff/同组fast smoke/实际架构命令GREEN。
- help新反例2 RED/0.98s，修复wrapper先显示自身与batch参数、不加载配置/凭证；真实help显示provider/config，配置测试通过。三个短测试根s6baseline/s6helpred/s6node已精确移除恢复absent，18当前文档链接有效；配置SHA3609e707…不变，0生产/原件/模型/provider操作。
- 只读误读不存在的narrative_model_config.py/source-export-v2.md后改实际路径；文档EOF空行diff check失败已纠正，真实ARCHITECTURE大小写已校正。未增加CI矩阵或日常长测试。Next Step N4C，生产库收缩与控制收尾不重复。

## 最新交付核对（2026-10-06，覆盖下方历史P5状态）

- 已接收P5-FF/P5-STORAGE通知并核对原始handoff、工作树及Git提交：两线无新增提交/dirty。FF已整支包含于远端main758e8f4；STORAGE已选择性集成9fa2166并由MAIN补充修复，旧交付分支不再merge覆盖当前工具。
- 远端HEAD与官方Actions API复核成功：FF CI37385101051、STORAGE集成37375836745、后续修复37394193179均attempt1 success。已有责任测试、FF→ET→CWP联调及生产原文保护结果继续有效，不重复长测/删除/VACUUM。修正施工卡和并行总包的开工状态；Next Step仍S6当前说明/钩子残留核销，然后N4C。
- 本轮只改本线PWF；用户配置SHA3609e707…保持，外线目录/其他owner文件不改。gh不在PATH导致只读CI命令失败，改官方API后成功；没有实际产品测试失败。

## 2026-10-06 — RF MAIN稀疏环境根因确认

- 前一目标turn为progress：两份P5交付重核精确CI/原件SHA，PWF 2145661已推送，正常pre-push GREEN。本轮fresh RF remote main仍8a153f33、MAIN树干净a74b9ceb。
- 显式Set-Location后文件仍缺失；git sparse-checkout list及git ls-files -t证明MAIN旧审计树仅展开日志/UC，源码、tests、quality.yml均为skip-worktree。此前相对路径错误判断不充分，实际根因是稀疏checkout，不是产品RED。只展开MAIN专属干净树；owner/外包树不变，随后实跑默认CLI节点。

## 2026-10-06 — P5-FF / P5-STORAGE交付复核收口

- 用户通知交付后重核原始handoff、Git ancestry与GitHub exact SHA：FF ab9ce33在main758e8f4中，STORAGE 9fa2166在master历史中；CI37385101051/37375836745均attempt1 completed/success。沿用已经执行的集中53个不同case分步GREEN及真实三仓/原件测试，不重复长包、不增加小节点门禁。
- FF外包报告的无预算旧下载fixture与POSIX待验证项已由MAIN修复、真实Linux CI执行；不再作为当前待办。FF仓内MAIN_ACCEPTANCE.md仍保留发布前过程，当前发布事实以CWP正式JSON receipt为准。STORAGE未知parser分类仍由MAIN明确保留/处置，生产删除不由外包签收自动触发。
- 本轮再核原件：AMEC 9,165,875B/d64c4108…，MSFT 66,324B/4ac3b4f0…，与既有签收完全一致；用户配置3609e707…不变，FMP密钥不读。RF新交付已进入干净MAIN整合树，尚未发布；全套PWF修正过期“WIP/无HANDOFF/FF未并线”描述。
- 环境误差记录：此前RF相对路径命令未进入指定目录，出现file-not-found/0 collected，不是行为RED；后续跨仓命令显式Set-Location并验证根。本轮一次PowerShell花括号路径展开语法错误改为逐个显式路径，无项目写入。
- 本轮0生产原件/派生/span删除、0VACUUM、0LLM/provider调用；没有宣称新增释放空间。下一动作仍为P5-RF MAIN整合节点。

## 2026-10-06 — P5-RF交付到达，优先主线整合

- 上一目标turn为progress：CWP b148123生成器退出/精确CI全绿及f65e8c9 PWF均已发布。本轮fresh RF交付由WIP变为干净a74b9ceb（代码31fe65e6），HANDOFF位于docs/implementation/handoffs/P5-RF而非.planning；remote main仍8a153f33。
- 复用9项TDD/98相关回归/2项CLI签收，MAIN只补当前FF/CWP及部署/CI节点。确认旧compat FF不支持v2、新E2E默认skip、已删evaluate_review测试及RF重复长CI是真实待收口项；先写MAIN整体整合步骤，不走一步猜一步。
- 原RF owner2份weekly日志、rf-impl main树242项staged WIP均保留，干净旧整合树可复用。没有生产删除或新模型外发。本轮计划见harness_lanes/results/p5_rf_main_integration_plan_2026-10-06.md。

## 2026-10-06 — S5剩余生成器分层接续

- P5-FF已主线758e8f4/精确CI GREEN、P5-STORAGE已主线e570daf/验收，未执行生产删除。fresh RF独立树8a153f33仍WIP、无HANDOFF，owner仍两份assurance，不修改它。
- CodeGraph+tracked AST确认canonical导入仍经指纹和历史public类型载入全量生成器；正文reader只有旧writer使用。原文临时parser和去重指纹有实际职责，不能整文件删除。先写详细分层/TDD/真实副本验收顺序，再实施；当前尚无代码改动或生产降容。

## 2026-10-05 — MAIN provider预检、P5三卡运行

- 只读接口调查确认测试端点错用国际站：api.minimax.io/v1/models=401；项目已配置api.minimaxi.com/v1/models=200/MiniMax-M3可用。两次GET无文档/推理；不输出key。下一真实批使用既有国内端点；先离线量长文请求并查skip错误，不盲重试。官方CN价格页web访问失败，未据此猜人民币/USD计价。

- run02收尾：正式batch 39.106s，budget_exhausted；两个真实HTTP客户端拒绝/usage unknown，年报招股预算预留拒绝，synthetic skip parser incomplete。0 final、RF消费者实际读取未完成。原件/生产/用户配置/RF owner fingerprint全同、测试根absent。实测收据n4c_live_2026-10-05_run02.json保存保守budget/reservations，旧未知不清零；剩余26,340 tokens/$0.083420。不能用REPLAY验收标真实节点完成。

- 第一次真实批次观测器遇到正常消失的SQLite SHM文件，stat抛FileNotFoundError，测试driver提前停止。已确认所创建CLI/child终止、原件/生产/owner不变、目录恢复；持久账本0个reservation/0新增费用，收据n4c_live_2026-10-05.json保留。修正观测器对临时文件消失容忍，新的run02独立root重新执行，不因超时误重启活进程、不清旧预算。

- 自动审批先拒绝具体MiniMax批次，要求资料/供应商明确。用户回复“给你永久授权”，明确覆盖本批四份公开来源向api.minimax.io做原语言业务摘要；同类授权沿用，不再重复询问。预算仍含旧unknown，最多60,000 tokens/$0.10；本次剩余49,675/$0.094742。不扩展为修改原件/翻译/购买套餐授权。
- 集中GREEN：92 Unit（8.03s）及正式batch CLI 2 E2E（23.71s），新thinking穿过spawn factory，双语言/skip/同run恢复/真实费用和hash拒绝均通过；Ruff绿。一次测试插入误把原read-policy断言移入新用例导致NameError，已恢复原断言归属后全绿。测试根n4green/n4green2/n4cli均已关闭并清除。

- P5三卡由用户确认已开工；MAIN不进入其写集。RF固定main N3a CLI只读复用，owner两份assurance文件不动。
- 先RED模型截断/usage与显式thinking：10 failed/4 passed，loopback无外发。实现null length先归类计量，thinking可选disabled/adaptive并绑定run配置、贯通factory；正在集中GREEN与真实小批准备。没有新的provider请求。

> 历史Phase 1–64及详细运行记录：https://github.com/zhengcb81/company-wiki/blob/bff81afe7cbb11c895764a94c2eabd121539e248/docs/plans/narrative-evidence-pilot-2026-09-26/progress.md。当前只记录本计划的真实完成项与下一步，不重复旧验收。

## 2026-10-03 — 采纳方案、恢复实施

- 用户明确要求以八束激进方案改整个PWF并继续执行。已将task_plan改为S0–S6当前顺序、具体接口/owner/大节点与原件保护；README统一入口，旧卡的执行要求由当前页覆盖，不复制大体积历史。
- CWP当前bff81af已核clean。正常用户只读外仓：RF main6fb2def7/4 tracked dirty，fcap5319ee26保留；FF c47c397 clean，ET4924d57 clean；StockWiki d4779e6/2 tracked dirty，IQSbfaf04c clean。未覆盖其他owner。
- 并行分工：R1先精确退役清单，N4A先scope接口负例；root拥有PWF/hooks与汇合。写入必须独占文件，shared Store与registry/planner分开。
- goal实读paused；工具只有get/create/update(complete/paused/blocked)，无resume/修改objective；继续已授权本轮工作，不错误mark旧goal complete。
- 初始决定：先保存计划，然后S0 TDD/退休，N4A在独占范围并行（已完成，见下文）。旧Worker仍paused，未调用provider或删除原件。

## 当前步骤

S0/N4A及S2模型预算基础、CLI阶段与CI修复已正常发布，当前CI绿；跨run节点已绿、owner/父kill/ACK整体待收口；S3英文召回已绿、其他来源默认/caps待做，S4–S6 pending。外部FF/ET/只读空间包running；不新增每文件review/coverage门。

## S0 / N4A TDD进行中

- root先取得4项确定性RED：commit重复pytest、config always_run、activation CLI无reviewer失败、restore无reviewer失败；实现自动actor记录与静态commit后，36相关测试GREEN/6.62秒，Ruff/mypy3模块通过，测试根finally删除。
- R1 agent先取得11项退休行为RED；整套退出后节点包157通过/3静态失败，真实叙述3个E2E与23个内容质量测试均绿。收敛import层级误判与B10现行metadata handoff，未弱化原件/引用断言。
- N4A agent取得19项scope初测，12项缺scope接口RED；正实施SQL先LIMIT过滤与prepared effect scope，通用状态/Store schema不改。
- root整套删除旧deletion_manifest及仅服务它的Unit/过期ignore；合法ignored凭证的旧rotation门已先RED再改，真实tracked/history泄露检测仍保留。可选prompt签名writer只服务fixture但有多个consumer测试构造，合入S3诊断协议收口，不在本批留下新签收替代物。

## Errors Encountered

- sandbox只读Git提示用户ignore/cache权限；正常用户元数据盘点正常，不修改ACL或reset。工具agent线程上限沿用现有agent，不继续创建新线程。
- 两个猜测测试文件名不存在，改用CodeGraph给出的实际activation/restore文件；rg混合显式文件和目录导致过宽输出，后续只列命中文件/精确片段。pytest插件隔离下asyncio_mode警告不影响结果；测试根已清。施工中另agent文件EOF提示交该owner收尾，不跨线修改。

## S0 / N4A集中验收完成

- root一次集成全Unit及受影响activation/restore/transcript/automation/B10合同：1161 passed /178.40s（Windows）；隔离根finally删除。该大节点不进入每次commit，提交只静态检查，CI继续现有快速组。
- R1首次157绿/3红，根因修复责任包22全绿；11退休RED与4数组元数据RED均转绿。净删约4027行；gold内容质量和三份真实叙述E2E保留绿。
- N4A相关120绿/1新增spawn夹具身份错误，修夹具后该项绿，root集成21scope全部绿。覆盖批外parent只读、空scope零事务、101早prepared及库外ACK不被本批处理。没有schema升级。
- secret ignored-local规则1 RED→9相关GREEN/17.55s；真实tracked/history泄露检测仍在。复杂度冻结及其镜像断言退出，tools/complexity_report.py只报告；不新增数值门。
- root extra mypy发现现有Spec float→Worker int秒注解不一致，统一真实支持的float秒，不截断lease。生产raw/config/control/DB未写，测试不联网、不读实际key。
- goal重新创建尝试被工具拒绝：cannot create a new goal because this thread has an unfinished goal。旧目标尚未完成，不能mark complete绕过；应用卡仍需用户侧resume，执行持续推进。
- 当前准备正常提交推送S0/N4A和PWF；S2新adapter文件若已创建不混入本次阶段提交。

## S0/N4A发布与S2模型接口

- ff5396c3a8766f557c016c30cbbf33571d67b288已正常commit/push；Ruff/mypy/host静态hook通过，pre-push精选通过，无跳过hook。CI37131769647成功，Fast checks job53秒。
- 15项usage字段先RED后GREEN：可选成对token、0有效、bool/负值/部分字段拒绝；4位置参数replay兼容，坏JSON仍可带真实usage。
- 完整schema/同语言wire示例先4 RED，prompt升级1.1.0；41项summarize/model字段包GREEN/1.62s。模型端清楚业务叙述、来源引用、角色/情态和质量诊断；不新增第二轮LLM。
- gh不在PATH/常见安装位置；改用GitHub公开API取得真实CI收据。发布前scope测试多一个EOF空行被diff-check拦住，修空白后正常提交，未绕过检查。测试独立根已finally清除。

## S2/N4节点A：持久预算与生产factory

- AUTO v3只新增run/run_jobs/reservations三表，v1/v2事实与只读classification竞态保留；当前reopen只读，旧v2明确迁移且仅一次小库backup。预算不创建第二CSV/数据库。
- 55项预算/迁移相关契约累计GREEN，含真实双spawn抢最后额度仅一份成功、kill/expired lease后预留保留、异常聚合整数上界仍记账并block。ctor不初始化/迁移生产库。
- HTTP33项真实loopbackGREEN/2.13s，无redirect/retry/fallback；truncate带已知usage、确定零HTTP的credentials具名区分，不保存响应正文或key。
- caller先7 RED，再7绿/1新storage-failure RED，修后8全绿/0.98s；settle-before-decode，未知保占额，确定未调用才0，DB结算失败保预留metrics。handler新增4 RED，45包全绿/1.43s，坏JSON/坏claim不丢已付费metrics，skip0调用。
- 请求16 RED→16绿；round-trip补1 RED修正规范金额后17绿/0.69s。1–100精确refs、折叠重复、路径在composition、integer microUSD，profile/时限/模型/费率/版本共同bind hash，secret值不进入options。
- 正式factory15项已各自GREEN含真实spawn+真实Reader零外网/原件不变；真实Reader的dict返回不协变，用只读Mapping Protocol收敛，无cast/第二Reader。6模块mypy与现行Ruff scope全绿。
- root大节点集中1241项：1238绿/3旧预期红，旧expected error tuple/v2 version+table set；同步真实v3后117责任包GREEN/13.35s。不重跑全部既有1238绿、不放宽注入/版本/lease断言。所有独立根finally清除，生产DB/config/control/raw未写。
- 尚未完成：正式batch coordinator/CLI、terminal降容、完整本地HTTP CLIE2E、真实四样本live与S3–S6。新markets/agreements业务句零召回已记S3质量缺口；不能将factory synthetic成功当真实叙述召回验收。

## S2阶段发布、正式CLI/降容与并行卡

- 节点A 9ccd29f47d7bcfac895b6ceba71db9d1aae8c524正常commit/push，静态hooks/pre-push绿；CI37135709529成功。没有stage尚在实施的CLI E2E。
- 正式CLI先6模块缺失RED→6 GREEN；OS mutex两RED→8责任包GREEN/1.99s，共用基础设施函数，进程死亡自动释放，无PID签收文件。Factory尊重请求max_final_bytes，不只写DTO。
- 新terminal/lease 24责任节点、真实62组合GREEN/36.67s，Store兼容49 GREEN，故障SQLite第二条UPDATE abort整组rollback后恢复4 GREEN/5.27s；预算/outbox不改，exact visibility/hash+三job终态后才去attempt正文，repeat只读no-op。
- 正式多文档CLI独立subprocess：P2三原件（中/英+制度skip）2真实loopback POST/184tokens/222µUSD/3可读final；同run重跑0新增POST、同refs；之后原文SHA变化具名失败且账仍222µUSD。另0费用/原文失配/4KiB空间cap三故障均0POST/no artifact，生产原件/外批READY不动。所有fixture根finally恢复原样。
- root正式集中节点 **67 passed/55.05s**，含CLI、factory、terminal、自动mutex/进程kill及既有catalog lock/runtime兼容；短根C:\cwt\n4b-node-73bd798d已finally清除。尚未验正式batch父kill/ACK窗口/跨run，不能记N4B全完成。
- CLI首次TypeError源于浅dict保tuple冻结结果，改用HandlerResult.to_dict深投影；同run时间变化put_event幂等冲突，改复用同ID且input/payload/policy/subject完全一致的stored event时间，不放松Store通用幂等。合法失败回执从原ledger读费用，不误报0。
- S3 selector 11正例RED/11负例绿→新23+既有114 GREEN，版本/架构/请求/factory70 GREEN，Ruff/mypy绿。版本0.2.0仅补明确英文业务对象/完成动词，安全港/套话/财务表继续跳过，原文和locator精确回放；parser0.1不改。
- 用户要求可交其他harness的目录独立大包。最新外仓只读核：FF c47c397真实主线、ET4924d57、RF6fb2def7四dirty/原fcap5319ee26；StockWiki推进aa98848四dirty，IQS44b805f活跃；保留owner。新增parallel_execution_plan与FF-S3/ET-S3/SPACE-S5三独立卡，ready未派、输入/输出/范围/集中测试/主线汇合写明。
- 当前get_goal实读active，应用目标已恢复；不再报告paused。未外发live key、未paid FMP/LLM、未生产DB/control/raw修改。
- root只读大节点复核发现cross-run effect/work_key与idle旧daemon所有权缺口，写入N4卡/root nextstep；外线不抢Store/worker/producer。S5审计只读报告不带删除权；三线可现在启动，FF producer caps由root补齐后联调。
- 发布前静态检查补齐两处类型表达：OS mutex用sys.platform分支供Windows/Linux类型存根正确收窄；失败预算明确允许ledger不可读时的null。6模块mypy、Ruff、diff-check均绿，未放宽运行时校验。准备把已绿阶段与三张施工卡一起正常commit/push；N4B未完成项仍由root实施。
- cf662cc2e71e9a04e96f2cc767b2cfd29e502037已正常commit/push到master，28个文件；Ruff/mypy/host hooks和pre-push精选绿，工作树clean，专用临时根finally清除。CI37139201102首次查询in_progress，未冒报成功。三卡仍ready未派；本轮不启动live批次。

## 三外线启动与CI两项确定性修复

- 用户确认FF-S3、ET-S3、SPACE-S5已全部派出；三线登记running，root只处理CWP主线与联调，不改三独占工作目录。空间卡在CWP存放，执行和输出在独立workspace，生产全只读。
- CI37139201102最终Unit两红：mutex子进程无显式src，CI没装editable，父pytest的sys.path不会继承；使用-S/cwd tmp/去PYTHONPATH先确定RED，再显式仓内src bootstrap，真实kill/重取锁断言保留。无需改锁算法或skip Linux。
- 旧worker expiry夹具直接构造Attempt默认generation0，与enabled gate不符，实际RUNTIME_GENERATION_CHANGED合理。先复现RED，改真实claim绑定当前generation，增加未过期reap=0，保留精确LEASE_EXPIRED断言；Store新分类不放松。
- 一次相关mutex/worker/runtime/terminal/catalog lock责任包54 passed/15.16s，Ruff/diff绿；agent额外worker/terminal真实集成41 passed/23.23s。短独立目录finally清除，原件/生产DB/config不动。接下来正常发布修复并继续跨run节点，不扩CI矩阵或恢复慢测试。
- a104d259923e5bf6121ac9c09d8ef6a902642de9正常commit/push，CI37139842105 success。两项远端失败已闭合；不绕过hooks或新增慢矩阵。

## S2跨run身份节点及下一owner实施

- 公开verify handler先1 RED（两job同effect ID）；正式3run CLI先RED：A完成，B partial，C OUTBOX_FAILED。修effect action hash为verify job+bundle SHA，projector work-key/2加入publication effect key；bundle本体/intended SHA/Store冲突语义保持，正文对象仍按SHA只存一份。
- 真CLI新节点GREEN/18.76s：三run各92tokens/111µUSD，三个independent versions/effects/workkeys、A/B同正文对象、C异正文，物理对象2份；B重复0新增HTTP，三旧exact pins全实读，outsideREADY无attempt、原件/sidecar/config不变，unique root恢复。
- root责任包32 passed/20.23s，升级前prepared新增夹具先因旧helper目录前缀、outbox返回dict误用失败，修fixture后该项1 passed/2.11s；旧effect继续work-key/1准备/ACK/可见，版本ID和bytes不变。Ruff/mypy2模块绿。已充分验证，不重复全部历史大包。
- 只读owner审计纠正假设：没有AUTO独立生产daemon；正式factory已拒None/空/非run scope。真正入口为catalog worker、once、start/resume、startup PS/VBS及全量normalize/run；旧周期会全局normalize/旧LLM summary且长持catalog lock。生产control为paused、runtime不存在；sandbox无法查人类计划任务，未知不报禁用。
- 下一步现有run行最小generation绑定+原库正确迁移，未知ENABLED不接管、父kill自身可恢复；退役上述旧执行入口，generic库None兼容保留、FF下载不占长owner锁。统一在节点B验owner/正式父kill/ACK及全生命周期deadline，不加手工审批/新control面。

## S2 run owner 与父进程崩溃恢复闭环

- AUTO schema v4给现有run增加nullable `last_runtime_generation`；v1/v2/v3历史迁移保持旧业务事实不变，旧启用generation无owner时明确拒绝接管。通用Store启停保持兼容；run专属`activate_run`在同一写事务检查CAS、generation和归属后绑定并fence。
- 正式batch CLI在启用gate时，先校验并恢复原run归属，再写入AUTO事件/任务；paused gate下先幂等准备原run，随后原子启用。finally只暂停自己持有的generation，unknown/别run冲突不会改变DB。
- 父进程在真实本地HTTP POST等待期间被kill：观察到真实worker退出、OS文件锁可重取、旧attempt以`RUNTIME_GENERATION_CHANGED`结束；同run CLI重启完成/预算封顶。旧请求reservation由`reserved`转为`unknown`，保留原token/费用上限、不记response hash、不退款；外批READY、原文/config保持原样。
- ACK丢失单元故障注入覆盖SQLite事务已commit但调用方收到超时：同run重试读到unknown，不重复费用结算。另覆盖active attempt不提前结算、已结束attempt幂等结算。
- 首轮53项owner/migration/recovery责任包全绿。扩展165项关联包164 passed、1 skipped；唯一失败的旧Store schema v3断言已改为v4并单测通过。最终batch/owner/正式父kill恢复22 passed/13.11s，Ruff与三模块mypy全绿。正常提交hook的host guard抓到新E2E硬编码POSIX `/proc`；改成POSIX `ps`进程表并实测Windows分支，guard新违规0、E2E 1 passed。CI将验证POSIX分支。禁用pytest plugin autoload时出现`asyncio_mode`未识别警告；该组无async依赖，CI正常加载插件，不更改pytest配置。
- 接下来完成旧source_catalog Worker/CLI启动入口退役，再汇总S2全生命周期/容量证据；之后与三条外线和root的S3 producer caps在大节点汇合。外线FF/ET/空间目录未被本组修改。
- CI37143351537唯一失败为v3只读分类测试。根因是冻结数据库夹具使用`with sqlite3.connect(...)`，该上下文管理器只提交/回滚、不关闭连接；我实测fixture返回后切换WAL模式会被旧连接以`database is locked`拒绝。改为明确commit并close；保留原WAL读路径的重复只读断言。修后53项owner/migration/recovery责任包全绿，远端修复CI待推送。

## 2026-10-03 — 旧 Worker 公共运行链退役

- TDD：新增 CLI 退役测试，覆盖 `normalize`、`summarize`、`run`、`worker`、start/resume/pause 和 install-startup 不再注册；确认 `scan/status/query/export/worker-status/worker-stop/uninstall-startup` 保留。重写 paused-guard 合同：显式 `ensure --allow-download` 与 `close-gap` 不再读取旧 Worker pause 状态，FF 外线兼容参数暂时保留为 no-op。
- 只读生产检查发现 Worker paused/stopped、进程清单为空、登录 startup 未安装。删除旧 CLI 执行分支、启动安装实现、控制菜单和 PS/VBS launcher、BG7 pilot；保留能发现/停止旧进程和卸载历史任务的诊断路径。未写生产配置、控制状态、SQLite、派生目录或原件。
- 删除旧 Windows launcher/bootstrap 专属测试及过期启动断言；保留 WorkerController 的旧 PID identity stop/process-inventory 测试与当前 finite batch 恢复 E2E。
- 相关集中测试首次 153 passed / 2 stale assertion failures（64.73s）；修正后两个失败用例 2 passed。CLI/ensure/close-gap/parser 责任包 18 passed；最终 74 项控制器/进程识别/恢复 E2E 通过。Ruff、有限 mypy 与 `git diff --check` 均通过。
- 下一步：正常提交并推送该退役节点；之后 root 独占实现 CWP ensure/close-gap 三个 producer cap，参数与 FF-S3 同步，然后进入 N4C。

## 2026-10-03 — 复核 ET-S3 / RF / producer egress 边界

- ET-S3 handoff 已独立复核：交付分支 `codex/et-s3-bounded-runtime@53e1e60` 干净；ET 离线责任组 87 passed、`/2` goldens 10 matched、Ruff clean。全量套件 150 passed / 1 failed；唯一失败为未改动的翻译器工厂测试，本隔离运行没有 LLM 后端。真实 API/key 未读取。
- ET-S3 不是最终闭环：总时长限额在同步 HTTP 阻塞/1 秒最小 timeout 下没有硬 deadline 保证；显式翻译在预算路径外；handoff 的局部 task_plan/progress 未更新实际 push 状态。该问题不改变 `/2` 交接字段，也不阻止先做 CWP 内部实现，但跨仓声称“端到端硬时限”前必须修正。
- RF owner 状态刷新：`rf-impl main/origin/main@6fb2def7` 已包含 N3a consumer 和 pipe/后代回收 deadline 修复；4个 execution_evidence 文件 dirty，严格保留。版本化 pathless read receipt 合同复用，不碰 RF 文件。
- FF-S3 已在独立 `filing-fetch-s3-limits` worktree 实际改动/加测试，仍未提交；CWP只按卡片冻结参数接口实现，不访问该 worktree写入、不把 pending 标绿。
- 发现 CWP producer 限额必须覆盖实际 transport：CNINFO `response.read()`、Dayu `_http_download()->bytes` 都没有 caller byte/cancel 控制；CWP Dayu `discover()` 通过 bulk download 进程取候选而非 metadata-only。仅 argparse/`DownloadReceipt` 后验检查会造成“看似限额、实际未限额”，不能采用。
- close-gap 当前有锁外最新期重探、锁内再探、exact stage三段；Dayu discover存在体下载副作用时可能重复下载。后续先做 capability contract 与RED测试，解决 metadata-only/一次预算贯通/失败零外发；在 provider transport可真实消费预算之前，不声称 byte ceiling 已实现。
- 复核临时目录 `.tmp-et-full-review-20261003` 已删除，外部 ET worktree未改变；本条只更新 CWP PWF，未改生产代码/数据库/原件。
- Owner boundary correction: Dayu provider code changes are cancelled. Restored the pre-existing tracked `dayu/fins/downloaders/sec_downloader.py` diff to `HEAD` as explicitly directed; its worktree now has only the pre-existing untracked `docs/architecture_report.html`. Did not create a Dayu worktree. CWP will not claim hard download limits for Dayu unless its existing CLI/API can enforce them; unsupported hard-cap requests fail before egress.
- StockInfo provider changes remain authorized but are not started. Its original worktree has a broad uncommitted adapter integration, so the next step is to establish a safe isolated snapshot containing that exact adapter implementation before touching provider code. If that cannot be done without absorbing unrelated owner work, CWP will fail closed for CNINFO under strict caps and report the missing capability.

## 2026-10-03 — FF-S3 / SPACE-S5 外包包验收

- FF-S3 仓内交付审查完成：branch `codex/ff-s3-single-request-limits` commit `8f17cbd` 已正常推送，push gate 的快速静态/配置检查全绿；责任回归358 passed/4 skipped/78 subtests，独立 CWP SourceRef CLI E2E 1 passed。新增 CI 仅跑一次精选回归，取消重复全仓/coverage与持久 `.runs` E2E。FF main 合并仍等 CWP 实际 provider budget 能力及 v1/latest_as_of 语义；远端 Actions 状态当前不可查询，记 unknown。
- SPACE-S5 交付审查完成：报告 `company-wiki-storage-audit-20261003/results/storage_audit.{json,md}`，schema `storage-audit/1`；15项工具测试通过，production mutation 为0。报告供主线拆分 S5/S6，不是自动删除清单；优先候选138,648,023 B，derived 2.826 GB先迁移，DB无free pages。
- ET-S3 状态更正：已合并并推送到 earnings-transcripts main，merge commit `93fe52c`；旧计划中仍写“running/未合main”的状态已纠正。其同步网络调用和显式翻译是否受总时限约束仍开放，不能把ET报告成硬端到端deadline。
- 测试临时目录异常如 findings 所述：3个文件、402,088 B 因ACL残留于`%TEMP%`，未调整权限，清理失败事实已记录；该测试目录未达到恢复原样。

## 2026-10-03 — CWP producer budget 回执二次校验

- RED：新增 under-reporting bounded adapter，discovery先计20 B、下载产物21 B、总cap 30 B；旧逻辑未拒绝。原因是它把 receipt 与总cap比较，没有验证本次 fetch 实际记账，也没有扣除 discovery 消耗。
- GREEN：fetch 前记录累计响应字节，fetch 后要求 `receipt.byte_size` 不大于本次新增计费字节及 discovery 后剩余额度；新增 CN `JsonCommandAdapter` 子进程 marker 测试证明不支持 bounded 的 adapter 会在外发前 fail closed。5个相关测试文件最终 **35 passed / 1 existing pytest config warning**；Ruff与`git diff --check`通过。所有本轮 `.t-*` basetemp 均确认移除。此修正只挡住漏记账回执；生产 CNINFO/Dayu bounded transports 仍未实现，不能宣称真实 provider cap 已生效。
- StockInfoDLSimple 状态复核：`v2-clean-rewrite@1693045` 原 checkout 有24个tracked修改及其他未跟踪文件；其现有 `CninfoAnnouncementClient.fetch_pdf` 仍先完整 `response.read()` 再写。没有修改原 checkout；后续需先建立精准隔离快照并将 discovery 与 PDF 下载统一到一个逐块消耗的 budget。Dayu 保持未改。

## 2026-10-03 — 跨仓阶段重新核对

- 开始下一阶段前先检查 RF：当前本地 checkout 是 `fcap@5319ee263c4af41ac255938c25bebd32cce56f66`，`origin/main` 是 `6fb2def709d13bda9cfada7ecf62bfc0e3744ae2`；checkout 保留大量 `.planning/2026-09-19-three-project-history-audit/execution_runs/**` tracked 删除。本轮只读并保留 owner 工作，没有恢复、合并或修改 RF；Git dubious-ownership 用命令级 `safe.directory` 读取，没有改全局配置。
- RF 当前 PWF 根为 `.planning/2026-09-19-three-project-history-audit/`。CodeGraph 对 pathless receipt 的模糊查询没有给出规范合同，下一步从 RF main 的正式合同文件直接核实并复用，再决定 company-wiki 的接口与回归范围。
- 已直接检查 RF `scripts/contracts/evidence.py` 与 `scripts/contracts/document.py`：消费者模型将 source identity、HTTPS URL、日期、snapshot SHA 和 host/capture receipt 纳入验证；这证明的是 forecast evidence data contract。它没有声明数据湖路径，也未找到独立 pathless reader 的证据；继续定位真实 reader adapter 前不新造第二份合同。
- 随后发现本地 `fcap` 是旧 checkout，改从 `revenue-forecast origin/main@6fb2def7` 与 CWP G-C 收尾记录复核：main 已发布 `scripts/narrative_source_preparation.py` + `company_wiki_narrative_reader`，以 pathless `narrative-read-request/1` 读取 CWP source-only context；年报与英文 TXT 的 RF/CWP CLI 真实跨仓端到端已记录通过。CWP `SourceVersionReader` 已被 narrative/SourceExport v2 正式调用。前一条“未找到pathless reader”只适用于旧 `fcap` checkout，已由 findings 明确更正；RF 文件保持只读。
- 计划状态：G-C 消费接口能力已有交付，不重复实现或改 RF；N4C 的真实多文档 Worker 批处理、1/2/4并行实测、四类叙述召回/引用覆盖及空间增量仍未被该消费者 E2E 替代，S4 继续 pending。S3 仍由 CWP 的真实 provider download limits 和 FF 汇合阻塞。
- FF-S3 当前源码将 `acquisition_limits` 接入共享deadline，并含 CWP `--max-download-*` 参数适配；但 CWP 的 `JsonCommandAdapter` 仍无 `discover_bounded/fetch_bounded`，外部 provider是否逐块计费仍未闭合。接下来逐个核 FF 实际命令路径及CWP预算分流，避免把 schema/argparse通过当成实际下载限额。
- 已核 FF-S3 实际 argv：`_command_arguments()` 将三项上限附至 ensure/close-gap；v2 pathless ensure与legacy close-gap都调用它，`_shared_deadline()` 贯穿全请求。预算确实传到CWP CLI；差口是CWP生产provider transport，不是FF漏传。
- CWP bounded JSON桥接先写了RED合同：发现与fetch用同一budget，子进程收到剩余bytes/time/cost并必须返回usage；另覆盖usage缺失/超额。第一次pytest未进用例，失败在全局可选`langsmith`插件导入`pydantic_core` DLL被拒；不是项目测试红。测试根已在finally清除；接着仅本次命令禁用外部plugin autoload，继续得到真实行为RED，不改pytest配置。
- 隔离插件autoload后行为RED为3项，根因正是 bounded CLI methods不存在。实现 `JsonCommandAdapter.discover_bounded/fetch_bounded`：请求携带schema `1.0`剩余字节/秒/成本，subprocess timeout受同一剩余时限约束；输出须精确返回 `acquisition_usage/1.0`，再计入原budget，fetch收据字节不得超过该fetch本次收费。既有无预算`discover/fetch`形状未动。三条进程合同 **3 passed**；初次plugin failure与RED/Green basetemp均由finally清理，pytest cache plugin关闭以绕开ACL warning。CNINFO实际HTTP仍未启用bounded。
- 补充真实子进程sleep合同验证剩余deadline会杀掉慢provider；bounded adapter责任组最终 **4 passed / 1现有 unknown `asyncio_mode`配置warning / 4.25秒**。关闭全局plugin autoload是仅本次测试命令的环境选择，没有修改CI/pytest配置。
- company-wiki 仍有 producer-budget 未提交 WIP；上一节点35项相关测试通过，但生产 provider 响应流尚未接入硬限额。无外仓写入、无原件/生产库操作。

## 2026-10-04 — CWP / StockInfo bounded provider 节点

- CWP producer-budget 代码与新增测试已覆盖共享 AcquisitionBudget、明确provider capability、bounded JSON子进程、严格usage与部分失败计费、receipt二次校验，以及缺能力时外发前fail closed。复核发现deadline已过时仍须记录provider已报告usage，新增两项先RED后GREEN；最终六文件责任回归 **41 passed in 14.83s**，Ruff与`git diff --check`通过。pytest hook曾重定位并漏删987,840 B fixture，本轮按精确路径清除；短路径 `.t-bud` 通过finally删除。
- StockInfo CNINFO bounded transport在隔离分支 `codex/cninfo-bounded-budget@947e839`（基于 `1693045`）完成并提交，仅13个相关文件；original dirty checkout未改。focused测试此前61 passed、限定改动文件Ruff clean。今天额外51项运行到100%但退出阶段挂住并被中断，不算完整测试结果。随后GitHub API核实远端隔离分支精确为947e839，`v2-clean-rewrite`仍是父提交1693045；provider仓未发现Actions workflow。
- CWP→StockInfo CLI/client跨进程模拟HTTP E2E通过：1个候选，PDF 399 B，discovery+PDF用量713 B且精确对账；测试没有外网请求、生产目录变更，临时root已删除。
- 配置保持不变且正确fail closed：`config/source_acquisition.yaml`仍指向旧 `v2-clean-rewrite` provider 1.1.0，没有 `supports_acquisition_budget`，默认能力false。故本阶段完成provider和CWP桥接实现，不等于生产下载限额已经启用。下一步先将StockInfo分支纳入owner集成工作树，再显式配置1.2.0和budget capability，完成FF正式入口端到端及v1/latest_as_of复用语义验证，然后合入FF-S3。Dayu无改动。
- CWP budget桥接与额度计量修复已commit `288b028` 并推送；远端CI `37162544905` 已对该SHA成功。这个阶段完成的是安全fail-closed桥接，不是生产provider已经启用。
- StockInfo分支拓扑：远端bounded分支947e839是`v2-clean-rewrite@1693045`的直接子提交；默认`main@6df45a1`与v2-clean-rewrite无共同祖先。CWP原配置使用v2工作树，后续按v2集成线处理；本轮依用户授权仅清理无调用者辅助脚本和空文件，功能WIP保留，不把commit强行迁到不相关的默认main。
- 按用户要求检查 StockInfo 原 `v2-clean-rewrite` 未提交改动。`config/source_acquisition.yaml` 仍指向该目录，当前工作树中的 `stockinfo-cninfo` 1.1.0 CLI 仍是本项目配置的适配器入口；整体 restore 会让当前配置失去该入口，所以保留 adapter/client/CLI、预算分支前的源码、测试与夹具，以及 downloader/browser 的功能改动。README/config 变更与现存批量 CLI 能力吻合，`a_share_companies.txt`、`companies.txt` 保留。删除未被代码/文档引用且会绕过 pathless 抽象的 `lookup_a_shares.py`、可能按同名直接删 PDF 且已被 `save_subdir` 取代的 `reorganize_downloads.py`，以及确认的0字节 `nul`；另将11个仅有未使用import/格式调整的tracked文件恢复至当前HEAD，index未动。没有改动或移动任何原始下载资料。
- 当前脏工作树相关回归 **88 passed / 19.96s**（downloader、CNINFO API/fixture contract、adapter/CLI）。首次 pytest 自动加载全局 `langsmith` 插件时在 `pydantic_core` DLL import 失败；仅本次测试关闭 plugin autoload 后测试正常，未修改项目 pytest 配置。StockInfo 其余功能改动仍未提交；隔离分支 `947e839` 与原目录WIP保持分开，CWP仍配置1.1.0且budget capability关闭，后续集成工作仍待办。

## 2026-10-04 — FF/CWP/StockInfo 真实采集闭环并合入 FF main

- StockInfo provider隔离分支 `codex/cninfo-bounded-budget` 从 `947e839` 补上 JSON stdout 修复，提交并推送 `8ed5fdd`；聚焦 provider suite **62 passed / 0.87s**。原 `v2-clean-rewrite` owner工作树没有整体恢复或覆盖。
- CWP配置改为 StockInfo隔离 provider路径、版本1.2.0、`supports_acquisition_budget: true`；本地配置加载与 registry smoke通过。CWP限额与适配器责任集 **32 passed / 18.08s**。
- 真实CNINFO年报E2E经 FF-S3 v2入口下载BYD FY2024 PDF **10,092,140 B**，SourceRef SHA `e9c2d7fdd088e151ccb6c8ad3d95587b2b014b10f2c9731508d23ce07fde4de3` 与PDF实际内容一致。`latest_as_of + reuse_only` metadata lookup、legacy v1 exact reuse均无重复下载/原件改动；v1缺件且无budget在外发前失败。生产配置和CN身份快照指纹未变，隔离root已清理。
- E2E发现provider logger污染JSON stdout，先写回归再修复；修后测试通过。FF发现latest_as_of reuse-only仍访问provider metadata，追加request ceilings合同，FF重点回归 **23 passed / 11.72s**；本地pre-push检查全绿。
- FF-S3提交 `5b9a8c1` 已从 `origin/main@c47c397` 快进推入远端main；`Projects\\filing-fetch` 本地owner工作树也同步到 `5b9a8c1`。保留未跟踪 `config/FMP_API_KEY.txt`，未读取或暂存。FF合入后的GitHub Actions状态待查。
- 当前S3余项是确认FF发布CI、检查安装示例和采集默认/缺元数据语义；随后按总计划转N4C，做四类真实资料有限批次、摘要引用覆盖和空间增量测量。Dayu不改，不能实施bounded的Dayu请求仍外发前拒绝。

## 2026-10-04 — 修复 FF Actions 安装清单测试的工作树依赖

- FF `5b9a8c1` Actions #52/#53失败；GitHub匿名页面可见run状态和step注释，但隐藏详细job logs。按项目同一CI pytest命令本地复现为 **359 passed / 5 skipped / 78 subtests，1 failed**：`test_manifest_excludes_a_fake_fmp_api_key_file` 假定真实owner工作树不存在 `config/FMP_API_KEY.txt`，而 fcap 有用户未跟踪key，于前置断言失败。测试失败发生在读写key之前，没有读取key内容。
- 修正测试只在 `tmp_path/canonical/config/FMP_API_KEY.txt` 写入假值，并构造三个必需公开manifest模板文件；不读写真实checkout、不清理用户key。聚焦安装面 **7 passed / 4.42s**。
- 同一完整GitHub CI精选pytest命令 **360 passed / 5 skipped / 78 subtests / 52.86s**。提交 `2936ad1` 已正常快进推至FF main；本地pre-push gate全绿，远端Actions run `37167803001` 当时仍in progress。`Projects\\filing-fetch` 本地owner工作树同步至该提交，未跟踪key仍保留。
- 更正：上述是本机安装清单测试的独立环境脆弱点；不能据此断言GitHub Actions根因。Actions #52/#53/#54实际失败于mypy step，真实根因及修复见下节。

## 2026-10-04 — 修复 FF Actions 的 Linux mypy 失败

- Actions公开 Jobs API确认 #52/#53/#54都失败于第7步 `Strict type check on public contracts (FC-1204-c)`，pytest步骤被跳过。Python 3.12.12/mypy 1.19.0 Linux目标复现：`scripts/transcript_tool_transport.py:100` 无保护引用平台专有 `subprocess.CREATE_NO_WINDOW`；Windows默认目标本地类型检查通过，掩盖了Linux平台存根问题。
- RED新增缺少该常量时的creationflags合同；改用 `int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0` 后GREEN。新增回归1 passed，Python 3.12/mypy 1.19.0 `--platform linux` + CI CWP `PYTHONPATH` 返回 no issues。
- 完整FF CI精选pytest命令 **361 passed / 5 skipped / 78 subtests / 48.97s**；正常pre-push gate全绿。提交 `1d0c73c` 已从 `2936ad1` 快进推入main；fcap工作树同步且保留未跟踪API key。Actions #55 `37182527153` 已 completed/success；根因修复经真实远端workflow验证。
- `2936ad1` 的假key测试改造仍保留：它解决了本机key工作树上的真实测试前置条件脆弱点，但不是GitHub Actions失败根因。

## 2026-10-04 — FF-S3 技能安装同步

- 检查发现 FF 主仓推荐 schema 2.0 技能说明与两个实际安装副本不一致，`.agents` 和 `.codex` 各有10项manifest漂移。
- 运行 FF allowlist installer 后，两个目录各报告 **MATCH 11 files**；再次 `--check` 均匹配。旧测试夹具/cache只从这两个 skill 目录按manifest清理；`filing-fetch/config/FMP_API_KEY.txt` 仍为未跟踪原样，未读取。
- 一次锚定尾行的PWF补丁因上下文不匹配而未应用、未修改文件；改为UTF-8追加。本次工作树状态另行核实。
- 下一步核对 CWP `latest_as_of` 遇到缺失 `published_date` 的处理：这是核心时序字段，不能被当作可忽略缺省值或据此声称latest已命中；然后决定S3是否收口并转N4C。
## 2026-10-04 — latest_as_of 缺失发布时间语义

- 代码复核确认：无 `published_date` 的候选会被 latest-as-of 排除；仅有这类匹配来源时返回 `AMBIGUOUS / matching_sources_have_unknown_published_date`，不会伪造“最新”结果。source classification也不会仅凭年份捏造完整发布日期。
- 现有latest合同测了排序和cutoff，没有单测该缺失日期路径；下一步先加一个短合同回归，运行该测试确认当前实现，再按来源默认/FF响应语义完成S3大节点校验。
## 2026-10-04 — latest_as_of 缺失日期合同测试

- 新增缺失 `published_date` 回归，确认 resolver 不会用无日期的匹配文件满足latest-as-of；只报 AMBIGUOUS + `published_date_unknown` trace，四项latest模式测试 **4 passed / 0.75s**，无生产实现变化。
- 测试环境的外部pytest plugin DLL加载失败、默认Temp目录ACL枚举失败均发生在测试执行前；改用唯一短路径 `.tla-1004` 并禁用外部插件/cache后执行成功。pytest hook另生成的唯一Temp测试树已按精确路径清除；本轮短根不存在，测试文件使用临时目录且已自动清理。
- pytest.ini 的 `asyncio_mode` warning因单次禁用插件而出现，未改配置。下一步核对 S3 剩余指纹/缺省合同，完成后刷新阶段状态并转 N4C。
## 2026-10-04 — R2/R6 合同复核

- 对照激进方案细则厘清两个语义：缺非核心采集描述/局部摘要覆盖可标partial；缺 `published_date` 时不能满足latest-as-of，现为AMBIGUOUS并已加合同测试。finalizer的partial依赖coverage/预算遗漏，真实来源时序仍由resolver负责。
- `VerifiedVersionReceipt` 已有pathless source ID/SHA/size/read-at及policy pin字段；尚需确认policy fingerprint输入是否只含本次读取实际依赖配置，并查其测试。
- 审计过程中曾在company-wiki cwd读取FF相对测试路径导致FileNotFound，改到filing-fetch checkout后继续；无文件变动。
## 2026-10-04 — read-policy fingerprint 调查

- CWP `source_read_policy_sha256()` 当前直接对整个 `CatalogConfig` 的 `asdict` 和runtime snapshot SHA取哈希；现有合同证明admission配置/activation变化会变，但未证明无关配置变化不会变。它可能超出R2的最小依赖绑定目标。
- 下一步查CatalogConfig真实字段和现有fixture，再判断是否要窄化hash输入以及增加“相关配置变更拒绝、无关配置变更仍可用”合同测试。
## 2026-10-04 — read-policy 范围更正

- `CatalogConfig`只有project/catalog位置、RootSpec列表、可复用root kind四项；RootSpec本身承载来源路径、准入/版本/路由/边界等source读策略。现有合同测试覆盖多项相关变更。故当前hash全量取CatalogConfig并未证明夹带日志、批大小等运行设置，不擅自重构。
- 下一步只核 runtime snapshot hash 是否包含纯时间字段等无关变化；如果没有具体不必要输入，保留现实现并在S3计划说明其范围，而不是为“最小”泛化出新合同。
- 两个CodeGraph测试节点按名未找到，直接读取对应测试文件补足证据。
## 2026-10-04 — 定位 runtime timestamp fingerprint 候选

- 确认runtime snapshot自身SHA包含 `updated_at`；reader pin又直接包住该SHA，因此一个纯更新时间会使verified-open pin变化。它很可能不是读取实际依赖项。
- 将按TDD核Resolver消费字段；准备只对read-policy pin排除更新时间，保留runtime snapshot原schema/hash以及真正影响准入的flags/epoch/cohorts/policy hash。
## 2026-10-04 — reader pin 依赖集合确定

- CodeGraph解析 `resolver_visibility` 后确定 SourceResolver消费范围仅为reader模式、epoch、active cohorts和legacy bridge；SourceReader还复核当前RootPolicy `policy_hash`。其余snapshot flags及`updated_at`不参与这次读取。
- 当前read pin全量包住snapshot SHA，确认会让无关扫描flag或纯更新时间触发pin drift。下一步按TDD先补相关/无关字段两组测试，再把read-specific fingerprint收敛到实际消费字段；不改runtime snapshot存储哈希或root config admission pin。
## TDD 运行记录：read-policy 反例 fixture 初次被schema拦截

- 新 RED 用例第一次未触及fingerprint断言：fixture将 `v2_scan_shadow=false` 与 `v2_persist_assertions=true` 组合，runtime snapshot校验拒绝该不合法依赖（persist assertions requires scan shadow）。没有项目行为失败或配置写入。修正为有效成对变化后重跑。
- 第二次fixture调整仍未执行目标断言：把 `v2_persist_assertions` 关闭但保留 `v2_resolve_shadow=true`，又违反snapshot前置关系（resolve shadow requires persist assertions）。停止猜flag组合，先读取validator约束，改用独立无关flag变化。
- Validator代码复核找到前述flag依赖链：`persist_assertions→scan_shadow`、`resolve_shadow→persist_assertions`、`resolve_active→resolve_shadow`、`bundle_active→resolve_active`。第三次RED尝试将采用全关闭有效基线；测试有效启用reader时只打开完整依赖链，不再用无效组合探路。
- 用合法全关闭基线重跑后，目标测试按预期RED：只改 `updated_at` 并启用无关 `v2_scan_shadow`，完整runtime snapshot SHA改变，当前read pin也错误地从 `2b111c…59fc` 变为 `0d2f7f…2dba5`。测试触及目标断言；没有生产库或config写入，basetemp已清理。
## 2026-10-04 — reader-specific policy pin实现与验证

- 先有目标行为RED：timestamps/scan flag使read pin变化。将`resolver_visibility_projection`放在runtime policy层，SourceResolver仍通过兼容`resolver_visibility()`返回相同tuple；`source_read_policy_sha256()`改为绑定CatalogConfig + snapshot schema/policy hash/有效resolver visibility，不再绑定不相关flag与`updated_at`。运行时snapshot完整SHA仍由load_runtime_policy校验。
- read policy + version reader + activation snapshot + latest-as-of合同 **58 passed / 5.10s**；通用SourceResolver合同 **13 passed / 1.68s**；Ruff、`git diff --check`及PWF claim检查均通过。测试仅因本机全局plugin/Temp ACL使用仓内唯一短basetemp与禁用外部pytest plugins/cache；短根已清理。唯一warning是该环境禁用pytest插件后`asyncio_mode`未知，不影响所选同步合同。
## 2026-10-04 — FF/ET companion wiring review

- FF schema 2.0 documents exact fiscal year+quarter, separate transcript caps, unchanged source language, no inferred Q4, and independent failure behavior. The two active local skill installs now carry that same canonical v2 protocol. FF tests invoke a subprocess fixture for the tool/SourcePayload contract.
- Before declaring the FF+ET edge fully exercised, check current earnings-transcripts main/working-tree and configured entry-tool availability; no live transcript acquisition is claimed yet.

## 2026-10-04 — AUTO approval API cleanup (CWP G1 first tranche)

- Retired the unused public `Approval` / `ApprovalDecision` model exports and `AutomationStore` approval CRUD. Source-level caller review found no live production workflow using these APIs; `remediation.approval_id` is a separate historical remediation field and was left unchanged.
- Kept the SQLite `approvals` table and migration intact. Added a regression that writes a valid historical approval row linked to an event/job, reopens the store, and confirms the row survives; no production database was opened or modified.
- TDD focused suite: initial API assertions went RED as expected. The first preservation fixture was correctly rejected because it violated the table foreign key; the fixture was corrected to create valid parent rows. Final relevant suite: **148 passed / 10.63s**. Changed-file Ruff and `git diff --check` passed. pytest needed `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` and a workspace-local short basetemp because a global `langsmith` plugin DLL and the default Temp ACL prevent test collection here; no pytest/CI configuration was changed. All `.tga*` scratch roots were removed.
- This is one CWP cleanup slice, not completion of the 46-item cross-repository gate audit. Next: close remaining S3 examples/metadata semantics, then prioritize G1 gate cleanup before N4C. External repositories remain read-only and owner-scoped.

## 2026-10-04 — Prompt-review storage failure is diagnostic on resolver export

- TDD added `test_pi10_review_storage_failure_is_diagnostic_not_export_blocker`. It failed before the fix: `build_resolution_envelope()` propagated `PromptInjectionReviewError` from optional prompt-review metadata and aborted an otherwise valid export.
- Resolver now catches the review-specific store error and SQLite failures, reports `not_reviewed`, and continues building the source envelope. SourceRef/hash identity and other source qualification checks are unchanged.
- Resolver envelope plus SourceVersionReader regression set passed **35 tests / 8.10s**; Ruff on the changed code/test passed. The one pytest warning is the known `asyncio_mode` warning caused by disabling the incompatible globally installed pytest plugin; no project config changed. The short scratch root was removed.
- At the time of this fix, the signed receipt writer and TTL evaluator were still present; they were subsequently retired in the next G1 slice below. This entry records the storage failure fix only.

## 2026-10-04 — Retire prompt-review signature and TTL machinery (CWP G1)

- The prompt review writer had no production callers. Removed its Ed25519/trust-root/signature and disposal authorization path; `detected_and_ignored` is now a scanner-bound diagnostic that requires no human authorizer. The 30-day review-cache TTL/evaluator, cache-state machinery, and stale read-chain candidate entries were removed.
- Kept `scan_text`, source/evidence hash binding, its optional metadata write, and the legacy receipt reader so existing source status can still be shown. SourceReader/resolver expose it as optional diagnostics; resolver database failure now returns `not_reviewed` and does not interrupt a valid export. Raw SHA, identity, period, root, and configuration checks were not changed.
- Updated the old shadow assertion test descriptions so they no longer claim an unreviewed source blocks consumption. Updated latest-as-of CLI fixtures to declare bounded discovery support, return usage, and pass explicit 5 MB / 90-second / $0 limits; this keeps the existing bounded-provider contract test valid.
- TDD retirement tests initially RED on the required authorizer and TTL API. Final focused suite: **110 passed / 59.78s**. Ruff passed on all changed Python files; `git diff --check` passed. A transient earlier run exposed the stale fake-provider fixture and was corrected without relaxing budget enforcement. Test scratch roots were removed. This is a CWP G1 tranche; the full gate inventory and cross-repository owner queues remain open.

## 2026-10-04 — Remove the last manual reviewer field from legacy activation mapping

- CodeGraph/caller review found `map_existing_activation` had no production caller and was the only activation path still requiring a typed reviewer label. Activation, rollback, restore, and their CLI already accepted an omitted reviewer and filled the actor from the current process user.
- TDD added a regression for omitted and blank labels; it first failed because the keyword was required. The mapping now uses the same `operation_actor()` fallback. It still requires an explicit reason and keeps transaction, assertion state, and policy-hash checks.
- Activation plus restore focused contracts: **22 passed / 2.58s**; Ruff passed. The pytest scratch directory was removed. This closes the reviewer-required part of G1 item #1, not the full gate audit.

## 2026-10-04 — Reprioritize PWF and prepare an isolated ET live-import lane

- Reordered the master plan explicitly: G1 gate/sign-off simplification first; S3 SourceRef/SourceExport virtualization second; N4C real multi-document batch after both. Clarified that IQS intentionally treats company-wiki as an optional read-only deep-research link, so it is not forced into document download/source consumption.
- Refreshed the cross-repository snapshot from read-only Git status: RF `rf-impl@6fb2def7`, RF fcap `5319ee26`, StockWiki `3a3d061`, IQS `6a8b8f3`, FF `1d0c73c`, ET `93fe52c`; owner worktrees remain dirty, so no external code-writing lane is safe to dispatch.
- Added the standalone ET-LIVE acceptance card. It permits at most one real transcript request, no translation, uses a brand-new temporary CWP root, checks SourceRef/SourceExport pathless reading and raw SHA/size, and writes only its unique result report. It can run alongside G1 because it does not change code/config; any fix waits until G1 closes.
- `verify_plan_claims.py --plan-dir .` and `git diff --check` passed after the PWF refresh.

## 2026-10-04 — Publish the G1 tranche and refresh N4 handoff order

- Commit `1cfec10` pushed to `origin/master`. Pre-commit Ruff, contract mypy, host-assumption guard, the fast contract push gate, and plan-claim verification passed. GitHub Actions run `37188829582` completed with `success`.
- The machine-specific `config/source_acquisition.yaml` provider path remains local and was excluded from the commit; it points to an isolated StockInfo integration worktree and needs a portable provider location before publication.
- Corrected the N4 detail card: N4A/N4B acceptance is complete; N4C remains pending and now explicitly follows G1 and S3. This prevents the detailed card's older sequence from overriding the master plan.

## 2026-10-04 — 本轮PWF重审与两个独立代码施工包

- 按用户要求固定MAIN顺序：G1门禁/签收精简→S3抽象层虚拟化收口→N4C真实多文档/并发/空间→S5/S6。本轮只改计划文档，不改生产代码、配置、原件或数据库。
- 正常用户Git复核CWP仅本机provider配置dirty；RF rf-impl242项与fcap2项分别记录，FF/ET已合提交复用，保留各owner未提交记录。`get_goal`仍active。
- 更新task_plan、46项清单当前安排、并行总计划与N4细卡；修正“未commit”、陈旧FF/ET HEAD、将N4C反写成N4B未完成、以及末尾旧下一步。已交付三施工卡增加醒目完成标记，不再重派。
- 新建 `gate_simplification_closeout_2026-10-04.md`、G1-LEGACY及ET-DEADLINE代码卡，冻结独占目录/写集/接口/TDD/集中测试/交接；ET-LIVE移到独占验收目录并澄清真实链范围。用户尚未登记启动，状态保持ready。
- root下一实施是filing_reuse非核心字段阻断TDD，其后清叙述capture cutoff；G1-LEGACY可以同时施工，ET-DEADLINE提前准备但合入排S3。MAIN独占共享来源核心、CLI/合同、配置发布和最终跨仓接线。
- 文档核验：`python tools/verify_plan_claims.py --plan-dir .` GREEN（11个plan）；`git diff --check` GREEN。本轮纯Markdown，不重复已绿业务测试，不增加小节点审查；本机provider配置继续排除于提交。
- 包级复核补足ET-LIVE的现行四字段import envelope、调用前SourceRequest/request_id及临时catalog配置，避免唯一一次取数后导入必然失败；ET-DEADLINE明确硬保证为worker采集终止，parent有界验证的返回开销不虚报为可抢占。
- 本轮发布提交以 `Clarify gate-first plan and isolated harness packages` 为Git标识；仅13份计划/卡片/进度Markdown，本机provider配置排除。总计划与卡片ready状态不代表外部harness已启动；用户可直接交出两个代码包，MAIN统一合入。


## 2026-10-04 — G1来源open与叙述日期第一组实现

- 先RED：缺URL/HTTP provenance/缺collector仍可verified raw、公开日在cutoff之前但capture在之后仍可叙述回读。初次叙述夹具误传SourceRefValue触发TypeError，改用真实reader.query_ref后得到目标source_after_as_of红灯。
- 生产实现移除这两项非核心资格门，保留真实SHA/身份/期间/公开cutoff；稀疏candidate不再丢已知字段，capture_ready仍False。坏字节反例验证门禁简化没有绕过raw hash。
- 来源reader/latest-as-of/叙述第一组56 passed / 29.81s；包含候选CLI与稀疏字段新行为的最终集中责任包64 passed / 57.25s。mypy暴露optional dict收窄问题，改为逐值校验后2个修改模块mypy GREEN、稀疏候选定点复跑1 passed；Ruff GREEN。
- G1整体仍in_progress：正式resolver/gap_plan/canonical_writer与FF重复资格门是下一动作。没有修改外包G1-LEGACY/ET-DEADLINE写集、其他owner树或生产原件/数据库。本机provider配置继续排除提交。
- 两外包包登记dispatched，ET worktree已创建；没有将目录存在当运行进程证明。旧runtime未清理，原正式ET main保留。


## 2026-10-04 — CWP resolver / planner / canonical 消歧收口

- TDD先红：`SourceResolver.resolve` 对有原文但缺URL/collector的期次资料返回MISSING；qualification envelope因此没有来源handle；`build_gap_plan`过滤capture_ready=false；canonical writer在provider身份有歧义时仅因capture_ready=false拒绝了匹配本次提交SHA的版本。
- 实现让身份、期次、公开日和候选字节校验决定复用。resolver不再因采集描述丢弃已验证候选；gap planner删除`_usable_handles` helper；canonical writer用receipt SHA、source_id与provider身份消歧。capture_ready与preview/gaps仍作为诚实诊断。
- 集中责任测试：`test_source_catalog_resolver.py`、`test_r4b06_qualification.py`、`test_zr406_gap_plan_orthogonality.py`、`test_source_catalog_gap_plan.py`、`test_source_catalog_canonical_writer.py`、`test_source_operation_v2.py`共100 passed / 9.03s。原件SHA/size、identity/period/publication/future cutoff保留；随后在发布门继续跑Ruff/mypy/hook。
- RF先行核查：main@6fb2def7；fcap@5319ee26，merge-base ee0a82bfd1eec935cf4e567eb42f0ef79efa0226。main侧后加SourceRef v2消费代码尚未进入fcap；支线没有在merge-base后改这些源消费者文件。本轮不改RF，未来合支线需保留main的pathless verified-open链路。
- FF核查：正式checkout fcap@1d0c73c2只有未跟踪API key，本轮未读未改；已有`codex/transcript-companion@29085f7`工作树改动`fetch_filing.py`/`filing_contracts.py`，与剩余SourceRef v2资格门重叠。先协调这条现存工作线，不并发改FF同文件。
- G1未完：CWP reader/as-of/resolver/gap planner/canonical writer门已收敛；FF v2 consumer和G1-LEGACY外包旧入口收口还在前面。未改RF/FF、外包目录、原始财报、catalog数据库或本机采集配置。

## 2026-10-04 — 外包工作树状态与ET样本占用复核

- 只读检查G1-LEGACY：分支实现提交 `1cf8183` 基于 `1cfec10`；交接文件仍未跟踪，尚非完整commit/push交付。交接报告称责任包142 passed、Ruff通过；共享合同包另有1条旧断言仍期待环境变量能放行旧入口（其余25项通过）。主线合入时需按已批准的新静态策略改该合同断言，并在合并代码上集中跑受影响责任包；没有提前改外包写集。
- 只读检查ET-DEADLINE：worktree仍基于 `93fe52c`，`scraper.py`、`transcript_tool.py`、`test_batch_runtime.py`已修改，worker/supervisor及专属测试/PWF为未跟踪；这是活动中的未交付实现，不能当完成包或清理。
- 实测正式ET main、旧runtime、新deadline三处各130个transcript文件，每处15,953,731 B，按相对路径SHA-256全部相同；两个worktree额外重复31,907,462 B。旧runtime提交 `53e1e60` 已在main历史内且Git工作树干净，暂不删除其本机配置/缓存；这项重复量只占约30.4 MiB，不能解释CWP的数十GB占用。
- RF `fcap@5319ee26` 只读检查遇到当前sandbox账号对 `.planning/.../execution_runs` 的访问拒绝；Git输出大量表观删除项并伴随2个assurance文件变化，无法区分真实删除与不可访问路径。本轮未恢复、删除或合并RF内容；原先“两项dirty”的快照在当前账号下无法重新确认，后续需在有权读取这些目录的owner上下文核实后再做RF合支判断。
- CWP生产代码、raw原件、目录数据库和本机provider配置均未改；本轮只补充PWF实测记录。

## 2026-10-04 — RF fcap 权限表象复核

- 随后获准以只读提升权限复查RF：`fcap@5319ee26` 的tracked status为0个删除、2个修改（仅 `assurance/runs/weekly_alert.jsonl` 与 `weekly_manifest.json`）；此前`.planning/.../execution_runs`的大量表观删除来自普通sandbox账号的目录访问拒绝。样本路径现可读取。本轮仍未修改RF任何文件，恢复原先“两项tracked dirty”的判断。

## 2026-10-04 — G1门禁收口并转入S3电话会真实导入

- RF先行只读复核：`revenue-forecast@fcap/5319ee26`经提升权限核实仍只有2项tracked变更（`assurance/runs/weekly_alert.jsonl`、`weekly_manifest.json`）；普通sandbox访问拒绝曾把执行记录显示成大量假删除。RF/StockWiki/IQS owner树均未改。
- FF隔离工作树先以两条RED合同证明：pathless SourceRef v2缺`https_url`、provider/collector/retrieval描述或`capture_ready=false/缺失`时仍会被外层拒绝；实现后保留hash、SourceRef ID、公司/证券、期次、公开日/as-of校验，仅将采集完整度字段降为诊断。旧pathful v1 `validate_handle`未动。
- FF责任集最终 **177 passed, 1 skipped, 39 subtests**；唯一skip为本机没有生产security-master快照。Ruff、diff check通过；正常push gate的ruff、compileall、import、contract mypy、host/config/plan/BOM检查全GREEN。提交`e1eda60`从当前`fcap`快进并推送到远端`main`；push返回`1d0c73c..e1eda60`。
- CWP→ET→CWP确定性端到端先暴露临时根叠加长规范文件名导致Win32 MAX_PATH超限，准确栈在`canonical_writer._atomic_copy`打开`.importing`临时文件时`FileNotFoundError`。只缩短E2E临时根名字，保留导入/原文SHA/selector/去重/字节漂移断言；`test_transcript_provider_full_chain.py`加`test_transcript_import_cli_e2e.py` **12 passed**，临时测试根自动删除。CWP产品写入逻辑没有改。
- 通过CodeGraph重新分类G1清单：`CloseGapBinding`、`archive_retired_evidence`、`prune_retired_evidence`以及旧`llm_summarizer.summarize_catalog_with_llm`未发现生产caller；因此不存在当前公开流程要求用户手工准备binding文件。canonical `NarrativeSummarizeHandler`按SourceRef ID/SHA、语言与evidence span校验，不走旧禁词regex。旧未调用能力进入S5/S6 caller清理，不挡G1；source SHA/身份/期间/公开日/可回放引用和不生成投资结论的职责边界继续保留。
- G1大节点完成；S3进入真实ET工具→临时CWP导入→SourceRef/SourceExport pathless回读。ET-LIVE卡明确最多一次取数、不翻译、保留原始语言；ET-DEADLINE仍在独立worktree施工。当前CWP端到端用fake provider、FF companion用确定性工具测试，均不能冒称真实ET live。

## 2026-10-04 — ET-LIVE单次实测与ET-DEADLINE集中验收快照

- RF先行只读复核：fcap@5319ee26，tracked仅assurance/runs/weekly_alert.jsonl与weekly_manifest.json两项修改；FF为fcap@e1eda60（未跟踪API key留存未读）；ET正式main为93fe52c（两个用户未跟踪文件保留）。没有更改这些owner目录。
- CWP transcript importer确定性测试 7 passed / 11.30s；FF companion/transport 17 passed / 7.65s；pytest缓存关闭、bytecode关闭，两个独立TEMP basetemp均删除。
- 按已授权仅调用ET/FMP一次：MSFT US FY2026 Q3、英文原语言请求、10秒与1,000,000字节上限。ET返回unavailable/provider_entitlement_required；读取实现确认这是FMP HTTP 402映射，一次GET、redirect关闭、没有重试。工具wire没有回传http_status字段，因此报告按映射记录402。无正文，CWP导入与SourceRef回读为NOT RUN；不购买或重复调用。
- 临时CWP根用系统TEMP下随机et-*新目录，唯一配置只指向该根；cleanup PASS、根确认消失，生产source_catalog.yaml和source_acquisition.yaml散列未变。独占验收报告：C:\Users\郑曾波\Projects\company-wiki-et-live-20261004\report.md；报告不含正文/密钥。
- 只读ET-DEADLINE集中责任包按卡执行，91 passed / 1 failed / 51.46s，测试scratch恢复。唯一失败test_tool_worker_failure_never_leaks_key_or_body把build_failure="RuntimeError:boom"当成worker退出；异常发生在transcript_api.fetch_transcript捕获范围内，正确回传provider_error/unexpected_provider_failure，并非supervisor收到worker退出。真正的异常退出已有runtime单测（SystemExit:7）证明映射为worker_failure；e2e夹具应改为真正worker退出后复跑。独立worktree仍未提交，主线未改其写集。
- CWP唯一本机未提交项仍为config/source_acquisition.yaml，未暂存。CWP本轮只更新总计划/进度/发现/验收卡并修正ET-LIVE报告状态，不改生产代码/配置。
- 随后用一次独立TEMP、假provider正式CLI检查真正worker异常退出映射：初次临时脚本漏设stdin，得到invalid_json后立即修正脚本；修正版以SystemExit:7让子进程真实退出，CLI返回provider_error/retrieval_worker_failure，无key/body泄漏且worker临时目录为空，父TEMP根清理完成。无项目代码改动。
- provider配置审查确认现有${PROJECT_ROOT}/${PYTHON_EXECUTABLE}变量已处理CWP与Python解释器定位；唯一脏差异是用户本地把CNINFO adapter指向隔离集成worktree并标记budget能力。保持该设置不动；CNINFO进入稳定StockInfo checkout后只校正adapter路径，不新增根路径解析层。

## 2026-10-04 — N4C真实样本来源预检（只读）

- N4C仍按总计划等待S3收口；本次只用read-only catalog/API预选真样本，没有启动Worker/模型、写数据库或复制原文。
- 金山云2025年报、2025中报和2026年3月季报构成同公司可见财报组；前两份已有parsed/normalized/summary工件，季报尚无spans/派生物，正式批次必须区分复用与新处理增量。
- 三七互娱2026-05-11 IR记录经SourceRef narrative_derivation读出、验证133,294 B SHA，实际包含游戏储备、重点品类和海外上线等信息，也重复出现一般性模板话术；但当前v2 `describe_version` 返回`metadata_not_visible`，未满足pathless export入场条件。
- catalog内229份招股书全为retired；其中盛美上海招股书7,073,891 B的记录和原件位置状态均retired，不通过物理路径绕过。7条active电话会记录为旧PDF/JSON而非ET TXT；ET-LIVE仍因HTTP 402未导入。
- N4C细卡已新增逐项入场要求：先通过既有source admission得到active、v2 metadata可见且字节SHA匹配的IR/招股书/ET TXT；若未就绪，阶段如实保持pending。下一步仍是验收ET-DEADLINE交付并完成S3确定性联调。

## 2026-10-04 — RF接口复核与IR来源门诊断

- 实施下一步前先只读检查RF：`origin/main`=`rf-impl main@6fb2def7`；`fcap@5319ee26`只有weekly alert/manifest两项dirty。RF main工作树还有owner未提交的规划/证据改动，全部保持不动。RF没有CodeGraph索引；没有为本次任务向RF写入索引。
- 确认复用RF已发布接口而非重造：财报消费用`SourceRef/2.0` exact ref、CWP pathless `filing_reuse` CLI、RF bytes SHA/size + identity/period/publication/as-of校验；审查状态仅诊断。RF叙述reader `narrative-read-request/1`面向已有叙述工件，走有限只读子进程传输，不替代CWP的raw/source处理。
- 只读SQL查明三七互娱2026-05-11 IR没有任何`source_metadata_assertions`，现有`metadata_json`只有scanner/acquisition字段。当前v2不可见的直接原因是缺normalized assertion，而非活跃状态或字节验证失败。通用upsert新建的是shadow assertion，激活流程单独依赖epoch/cohort/policy snapshot；已将其列为G1剩余复杂度审查项和N4C入场路线设计点，不绕开或直接写数据库。
- ET-DEADLINE worktree仍为`codex/et-s3-deadline@93fe52c`且代码/测试未提交；当前PWF未更新、无handoff文件。最新观测到代码文件修改时间为本地10:59，不能据此断言harness终止。保持外线写集不动，S3仍pending。
- 本轮只有证据收集与PWF更新；无代码测试需要重跑。待提交前执行`verify_plan_claims.py`和`git diff --check`，只提交本次计划文档，保留`config/source_acquisition.yaml`用户本地变更。

## 2026-10-04 — Sparse SourceExport implementation

- CWP `SourceVersionReader.describe_version` now permits a pathless sparse manifest when v2 capture metadata is absent; absent display/provenance/period fields remain null. `filing_reuse` still rejects the same incomplete financial source.
- TDD: focused reader/export tests RED for the intended block, then **34 passed / 10.00s** after the narrow change. Synthetic CLI E2E verifies source ID/SHA/size, grounded span, no raw-body leak, and unchanged scratch tree.
- Pytest scratch cleanup was verified: the first long basetemp was relocated and its exact run directory manually removed; the successful rerun used short unique `tmp/pt1004b`, `relocated=false`, and that directory was removed after the test.
- Remaining sample gate: the IR can now be represented as a sparse manifest but batch creation still requires language metadata. Next implement deterministic language resolution from the exact opened SourceRef bytes, bind it into the event hash, then prove through isolated Worker/consumer E2E before N4C real batch.

## 2026-10-04 — Sparse SourceExport published; ET deadline still open

- Commit `48d3a9d` pushed to `origin/master`. Pre-commit Ruff, contract mypy and host assumption guard passed; pre-push fast contract smoke passed. Local/remote HEAD match. Preserve the one user-owned dirty config file, `config/source_acquisition.yaml`.
- Read-only status check of `earnings-transcripts-s3-deadline` confirms the actual deadline worktree is still uncommitted at `93fe52c`; `s3-et-runtime-handoff.md` inside it describes the earlier runtime package, not this deadline work. Do not merge or clean the active worktree before its dedicated handoff and focused acceptance.
- The two ET work directories serve separate stages: completed runtime integration (already in main history) and later deadline hardening (still WIP). Remote Actions was not checked because `gh` is unavailable; pre-push GREEN is not a claim that remote CI completed.
- Next: accept the deadline-specific commit/handoff, run its consolidated tests plus golden check, then close S3. The N4C language-resolution issue remains planned and is not yet implemented.

## 2026-10-04 — G1-LEGACY验收与稀疏language桥收口

- G1-LEGACY复核：隔离分支`codex/g1-legacy-entry-retirement@c3209ee`干净并跟踪origin；实际实现提交`1cf8183`已作为`6394271`第二父提交合入主线。主线结果报告与外包`docs/implementation/g1-legacy-entry-retirement-handoff.md` SHA-256相同；分支额外的局部PWF/交接提交没有待合入生产代码。
- 在干净G1 worktree重跑责任包 **142 passed / 58.05s**；Ruff与`git diff --check 1cfec10..HEAD`通过。主线接手合同、clean-env与config-doctor测试 **44 passed / 10.40s**。一次直接在当前主工作树运行G1写集检测时会把本机`config/source_acquisition.yaml`及当前未提交的narrative改动列为超出G1写集；该检查属于预期的dirty-worktree保护，故改在干净外包worktree复跑并全绿。初次无显式临时根的pytest还受到当前sandbox对系统TEMP ACL的限制；成功验收使用隔离basetemp，测试目录在结束后清理。
- N4 sparse language bridge聚焦包 **23 passed / 41.06s**，覆盖中文/英文/混合电话会TXT、年报PDF、有/无语言元数据、低价值IR skip、Worker真实CLI+本地模型、重复执行不增模型请求及raw夹具不变。Ruff与mypy聚焦检查通过。未运行生产N4C批次，未改catalog/raw/本机来源配置。
- 计划同步：S4仍pending，但“缺少从verified SourceRef字节推导language”的阻塞已关闭。剩余N4C工作是S3/ET-DEADLINE收口、为真实多类型样本取得符合现行admission/import合同的SourceRef，再测consumer引用/语言覆盖、1/2/4并发吞吐和总空间增量。当前IR normalized assertion、retired招股书及ET 402分别仍是样本资格/可用性缺口；不绕过合同。

## 2026-10-04 — ET-DEADLINE 只读交付验收

- 接收并核对 `docs/plans/repository-state-audit-2026-10-04/results/earnings_transcripts.md`。ET main=`93fe52c`；ET-DEADLINE=`0017f24`，对照本地refs，deadline branch-only为1个提交且远端分支SHA一致；main无tracked修改，两个owner未跟踪资料及两个linked worktree均保留。
- ET-DEADLINE handoff记录92项责任测试、全量172 passed、10 goldens、ruff与diff检查通过；这是交付报告中的既有结果。本次只读盘点未运行测试，且没有独立CI链接。旧progress里的“待commit/push”已经过期。
- ET只读审计包验收通过；ET实现提交暂不并main。下一节点是隔离fake-provider的FF→ET正式CLI/supervisor→CWP importer/SourceExport联调，特别检查FMP 26字段JSON与CWP当前Motley 24字段exact-key差异；不改变ET wire、不请求付费API。
- 本轮没有修改ET、FF或RF；CWP既有未提交配置 `config/source_acquisition.yaml` 保持原样。

## 2026-10-04 — 并线前 FF→ET→CWP 联调门细化

- 按用户要求，在总计划中把该联调列为ET-DEADLINE合入前的明确必过节点，不再只作为一句后续建议。
- 细则固定使用FF正式调用入口、ET正式CLI/supervisor/worker和CWP importer/SourceExport真实路径，provider侧使用fake HTTP；包含FMP golden与已知26字段/24字段形状差异、原语言及hash/size/身份/期次、共享限额/截止时间、重复导入、失败回收和空scratch恢复的验收标准。
- 这是计划细化，尚未运行联调；测试前必须使用隔离短TEMP根，零付费API/LLM调用，生产raw/catalog/config不变。全部通过后才快进合入ET提交。

## 2026-10-04 — FF→ET→CWP 离线契约联调与缺陷修复

- 用真实 FF companion/`EarningsTranscriptsTransport`、ET deadline 分支 `0017f24` 正式 `transcript_tool.py`→supervisor→worker→FMP parser/serializer、CWP真实query/import/source-reader CLI跑通离线链路。只有HTTP由ET既有私有worker launcher换成fake session；没有付费API、LLM或生产目录写入。工具 `tests/e2e/run_ff_et_cwp_offline_acceptance.py` 使用短TEMP scratch并在退出时验证它确已删除。
- 成功链保留原始FMP JSON字节，SHA-256/size/MIME一致；SourceRef无物理路径；unknown publication不伪造日期且不参加历史as-of；第二次调用复用同一SourceRef、provider调用数为0、raw只1份。key未进FF结果/日志，成功后ET worker临时目录为空。
- 联调最初因ET `request_schema`失败，追溯到FF将公司身份的`NASDAQ`直接传给只接受`nasdaq`/`nyse`的ET公共CLI。FF adapter现有小写规范化和回归测试；此处只改exchange传输字段，不重写身份合同。
- 有限慢provider场景复现另一个真实问题：FF外层subprocess timeout与ET worker deadline同为2秒，FF先杀ET父进程，导致`et-retrieval-*`目录在worker结束后仍残留。FF现按ET下游60秒上限裁剪，先为清理保留3秒并延长外层等待；FF总余时不足3秒时不启动ET子进程。用5秒fake响应/2秒采集预算复测后映射`provider_deadline`，没有raw入库且worker scratch清空。
- ET独立 `tests/test_retrieval_cli_e2e.py` **6 passed / 19.13s**；FF `tests/test_transcript_companion_transport.py` **5 passed / 9.77s**，改动文件Ruff通过；CWP FMP importer责任包 **5 passed / 9.45s**。最终FF→ET→CWP离线脚本成功；pytest basetemp与E2E scratch逐路径验证删除。CWP测试禁用第三方pytest插件时有一条`asyncio_mode`未知配置warning，无测试失败。
- 旧ET golden README和早期findings中的“CWP只接受Motley 24字段、FMP 26字段尚不能导入”是已过期快照。当前CWP源码与`test_fmp_unknown_publication_cli_stores_original_but_excludes_historical_cutoff`确认FMP provider contract已存在；不增加CWP adapter。ET deadline分支的golden说明已按现状更新。
- 发布状态：FF两文件已测但尚未提交；ET deadline候选原`0017f24`新增一个producer README修正尚未提交。提交前确认各自远端头未前进，不带入FF API key、ET未跟踪文件、CWP用户配置和其他审计结果；随后FF修复推送、ET分支快进并入main后推送。

## 2026-10-04 — ET deadline并线及合入后验收

- 上一条是提交前快照，现已完成：FF adapter/test commit `eb0af13`推至`filing-fetch/main`；ET deadline commit `0017f24`及golden README更正`63c4090`经纯快进进入`earnings-transcripts/main`，远端也已推至`63c4090`。候选branch同步到同一tip。
- 合入后在ET `main`重新运行FF→ET→CWP完整离线脚本成功；ET CLI E2E **6 passed / 22.54s**且**10 goldens matched**；FF companion **5 passed / 10.55s**；CWP FMP importer **5 passed / 14.98s**。Ruff之前在FF两个变更文件上通过；实际测试basetemp逐项清除。CWP pytest禁用第三方插件运行，有一条仓库`asyncio_mode`配置warning，没有失败。
- ET main工作树仍只有两个原有未跟踪个人文件 `.workbuddy-ai/`、`eval_results.json`；deadline worktree无跟踪改动。FF的未跟踪API key文件保持未读、未暂存、未推送。CWP本机provider配置仍未改。
- S3跨仓合同与deadline接线已完成；真实FMP取数权益仍未知/HTTP 402，不阻塞offline合同。下一步转S4/N4C：先逐类型只读确认active、metadata可见、原文字节SHA一致的真实样本；再跑有限Worker批次并测consumer实读、证据定位/语言与总空间。样本不合格就通过正式producer/activation流程解决，不手改catalog。

## 2026-10-04 — 新增外部harness施工包

- 已创建并接入总计划、并行计划的三个可独立派发卡：N4-T1模型传输错误诊断、N4-T2中文财报/IR叙述选材覆盖、MeetingConverter CI快速门。当前仅为READY TO DISPATCH，尚未收到这三张卡的施工交付。
- N4-T1和N4-T2限定在CWP不同代码目录和不同测试文件，需从同一已提交基线各自创建隔离worktree；不得共用checkout、修改共享PWF/配置/生产数据或执行付费请求。交付后由MAIN联合做跨层测试与新的有限真实批次。
- MeetingConverter卡限定其独立仓库CI配置；先核查远端最新workflow是否已有真实job和测试。如已修复只交证据，不为制造改动而改工作流。StockQAbyLLM与MeetingConverter早期只读盘点卡仍按原收据保持验收状态，IQS不派新任务。
- N4C run账本复核结果及不确定性已写入findings/task_plan：季报与IR来源可验证且解析覆盖完成但零span；MiniMax旧失败无状态码/响应摘要，确切原因未知；错误分类丢失HTTP状态是源码已确认的独立缺口。旧unknown reservation保留，不复用run ID。
- 无代码、source catalog、raw文件或生产数据库修改；本机用户文件 `config/source_acquisition.yaml` 原样保留。计划文档后续执行diff check/plan-claims检查并仅提交本轮明确的PWF及三张卡。

## 2026-10-04 — MAIN长文模型输入收缩完成（N4C仍未GREEN）

- RF先行只读核查正常账号状态：fcap5319ee26仍仅两项owner运行记录dirty，origin/main8a153f3；没有修改RF/IQS或外包卡的写集。本线新代码只有automation/narrative_model.py和tests/unit/test_narrative_model_request.py。
- 先补施工细则，再TDD：新请求测试初跑5 failed / 0.92s，准确暴露完整span请求超限、无coverage和coverage不入hash；没有修改原摘要/引用断言。最终精简模型投影保留全部selected原文/ID/角色/有意义质量标记，定位仍由canonical证据负责，schema/example继续完整教给模型，prompt1.2.0。
- 最终单元/handler聚焦35 passed / 1.05s；预算caller+正式CLI/Worker本地HTTP端到端14 passed / 40.16s；合计49项通过。命令为pytest -p no:cacheprovider --basetemp tmp/ptcmp加上述四个测试文件，两次最终责任集均未relocate。Ruff和diff check通过。pytest禁用第三方插件后仅有既有asyncio_mode配置warning。
- 精确自建tmp/ptcmp在同账号下确认位于workspace后删除，测试scratch已恢复；旧失败run保留用于诊断和未知费用记账。真实select结果只读请求大小复测招股书252,185→47,202 B、年报7,797→4,285 B，全部ID/原文匹配且旧ledger文件SHA不变，没有外部调用。
- S4改为in_progress，纠正旧“批次尚未开始”文字；真实summary/consumer与并发/空间验收仍未通过。下一主线动作整合N4-T1/T2，先核算剩余总预算，再另建run；原unknown费用和原件不丢。用户source_acquisition.yaml不纳入提交。

## 2026-10-04 — 发布收据与串行复用施工目录

- 模型请求投影收缩提交df529a9已推origin/master，pre-commit Ruff/mypy/host检查和pre-push快速门通过；GitHub CI [37239069991](https://github.com/zhengcb81/company-wiki/actions/runs/37239069991) 已completed/success，head_sha匹配df529a9。
- 用户询问同目录先后执行N4-T1/T2，已将两张卡、总计划与并行计划改为：并行各用一个worktree；串行可复用同一专用worktree，T1测试完且commit后T2接续，分别记录base/head。T2允许以T1交付HEAD为base，不reset已交付代码；MAIN活动checkout仍由主线独占。没有新增人工签收或测试节点。
- 此后续改动只有文档，diff check通过；不再重复业务测试。并行计划头部同步G1/S3已完成的事实，旧同日记录标为历史过程，防止重新派发ET-DEADLINE。用户配置保留。

## 2026-10-04 — S5首批旧缓存实际清理完成

- RF先行正常账号只读复核仍为fcap5319ee26、origin/main8a153f3、两项owner记录dirty。本轮只读其主线scripts确认默认仍走legacy SourceBundle；不能按v2实现存在便删全部derived。IQS/Dayu与外线代码写集未动。
- 新增S5/S6实施细则：RF生产入口迁pathless、CWP旧section/全量writer退休、derived和artifact状态同批退出、旧全量span消费者逐项迁移后DB收缩。原件/来源版本/撤回事实保留，不等全量文档重新摘要，不复制巨大恢复备份，不加小节点人工门。
- 首次只读dry-run逐集合数值正确但PowerShell对ordered hashtable的Measure-Object汇总得0，尚未删除即发现；改collection为PSCustomObject，第二次得到138,648,023 B/923文件，与交付审计一致。受限账号只读CIM访问拒绝后用正常账号核活进程；没有重复启动清理进程。
- 一个有界PowerShell进程2026-10-04 22:21:38–22:26:27 UTC完成七集合删除；进程终态exit0/status=success。公司原件清单、完整catalog DB SHA、配置、保留derived/staging/security_master/artifacts、旧失败run及控制状态前后相同。一次性全量保护检查耗时约5分钟，不放进commit/CI。
- 清理前后正式source_reader_cli各4次读取真实年报/招股书/IR/季报，共8次、每轮12,343,802 B，完整bytes SHA、来源身份、size及policy一致。没有下载/模型/原件副本；生产DB mutation0、原件删除0。所有923目标文件消失，按文件逻辑大小释放138.65MB；不声称磁盘free-space净变化或完整总量新实测。
- 一次性两个脚本及重复临时读取JSON逐绝对路径验证并删除，只保留合并机器收据和短说明。用户配置不stage。S5仍in_progress；derived主体、旧全量span及N4C两卡集成/真实摘要/并发与消费者仍待完成。仅文档/收据提交，无新业务代码，不全仓重测。
- 发布：`3f7dd2b`已推origin/master，pre-commit无相关代码文件正确跳过，pre-push快速门GREEN；git status仅剩既有用户配置。顶层当前状态同步本轮完成项，避免弱模型按较早文字重复收缩模型请求或再次清理923文件。

## 2026-10-04 — 旧normalized section公开生产入口退休

- 先重新fetch RF主线8a153f3，确认owner两项记录未变；其旧来源准备默认、SKILL文档及CLI夹具仍相互绑定，后续迁移一起处理，不仅改开关。CWP独占改动先处理extract-sections；本轮没有修改RF代码。
- TDD新增CLI未注册、公开SourceCatalog不再提供section writer、真实子进程在配置打开前拒绝旧命令且raw不变。首轮一个根为空的fixture不满足CatalogConfig要求，修成合法RootSpec后再次得到**3 failed/15 passed（1.89s）**，三个失败都对应待退休的实际入口行为。
- 删除extract-sections CLI注册/分派与SourceCatalog.extract_sections方法，修正CLI用途说明。旧纯解析和artifact完整性回归通过显式低级函数创建隔离legacy夹具，原断言保持；不再为这些fixture保留公开生产入口。
- 集中入口退休、章节解析与producer binding测试 **48 passed/24.30s**；改动Python Ruff与diff check GREEN。pytest禁用第三方插件仅有既有asyncio_mode warning；测试根短路径未relocate。正式新Worker回归与N4-T1集成一起执行。
- 旧normalize/summarize库方法、兼容旧Worker类和RF artifact读取仍待后续；没有删除2.826GB derived或生产DB span。当前用户报告N4-T1完成，已定位提交4a53080（base349d331），远端分支一致，六个文件符合独占写集；没有改该worktree，先将本轮入口改动commit，再查收集成T1。

## 2026-10-04 — N4-T1与MeetingConverter外包验收/并线

最终发布收据：company-wiki master/origin/master代码交接为66808ee，包含71f867a及5de9154；pre-push精选契约GREEN，远端run37241977614实际job72秒，Unit30秒/精选契约2秒，均success。MeetingConverter master/origin/master为8a33a7f，主线run37241709261实际job22秒且success。测试根ptn4t1/ptn4sql已按绝对包含路径删除；CWP唯一保留用户config/source_acquisition.yaml未提交。后续仅补本条文档状态，不增加小节点测试。

- N4-T1外线4a53080只含六个允许文件；MAIN cherry-pick为5de9154，没有覆盖其旧基线之后的PWF/紧凑请求/S5内容。外线工作树保持原样，T2可从4a53080接续，只交自己的新增提交。跨层114 passed/48.56s；MAIN新增实际HTTP400→正式CLI→SQLite attempt/unknown reservation端到端1 passed/6.59s，敏感正文/密钥不入输出或库。详见harness_lanes/results/n4t1_model_transport_acceptance_2026-10-04.md。
- MeetingConverter仅三个允许文件，交付8a33a7f；分支push/PR实际非空job绿18/19秒。MAIN正常用户上下文fetch核ref、merge --ff-only并push master；.coverage/config.json完整SHA/size/mtime和output清单前后相同，原dirty .coverage保留。PR1自动merged=true；新master run37241709261实际job绿22秒、Run tests2秒。外线全量204测试，本次未删业务回归；MAIN未在主checkout跑pytest。详见harness_lanes/results/meetingconverter_ci_acceptance_2026-10-04.md。
- MeetingConverter既存mimo.py:137未定义logger仍未修，卡片禁止应用代码改动，不把CI绿误报业务缺陷已消失。当前没有恢复全仓lint要求。
- N4C仍未完成；T2仍待交付。真实新run继续计入旧10,325token/$0.005258未知reservation，不扩总60,000token/$0.10预算；ET live仍402。用户配置、RF owner、IQS与Dayu均未改。

## 2026-10-05 — MAIN S5旧整库Worker退役与测试

- CWP现状核对修正计划此前的误记：旧Worker执行类曾残留，但没有任何src/scripts生产调用者；CLI的启动入口已移除，Win32无运行进程或任务。因此本次删除自动整库Worker及其专用scheduler_policy/测试，保留worker-status/worker-stop/uninstall用于遗留进程清理。
- 没有删除SourceCatalog的normalize/summarize按需接口或历史产物：RF远端main仍为`8a153f3`且`source_reader_v2=False`，实际默认分支消费SourceBundle normalized artifact；CWP evidence-query、extraction-quality及若干解析/PDF合同测试也仍依赖该读取面。等RF与CWP locator读取迁移完成再做API与derived退役。
- 保留旧摘要兼容测试并从混合worker大测试中提取到`test_source_catalog_legacy_summary.py`；移除的是死掉的后台Worker循环、stage policy专用测试，以及两个纯worker进程生命周期测试。新退休合同同时证明旧Worker/scheduler模块不可导入，而按需source catalog方法仍可用。
- RED：新退休合同先因`SourceCatalog.normalize`仍存在而失败；基于生产调用及下游依赖调查，把目标改为只退休无人调用的自动Worker，并加注释约束normalize API在读者迁移前保留。GREEN集中集：**127 passed / 64.28s**（退休入口、worker control/status、摘要、SourceCatalog pipeline/section、fingerprint）。
- 初次sandbox运行125 passed/2失败：HTML parser的Windows spawn受受限`<stdin>`/本机权限影响，python-docx etree DLL access denied；按项目正常用户上下文单独复核2 passed，并重跑同一127项完整集全绿。pytest专用目录最终恢复/删除。stdin诊断脚本和一次跨执行账户清理失败均记录为测试工具问题，已按真实脚本入口和原目录owner纠正。
- 代码和测试限定CWP，未改`config/source_acquisition.yaml`；RF的fcap两份weekly assurance用户记录保持原样。N4-T2/N4C和真实模型运行仍未完成。

## 2026-10-05 — S5退役提交发布与CI验收

- `ff0eec01137eac23e5142ce7863e20efd27fdfd4` 已推送 `origin/master`；pre-push快速契约门通过。GitHub Actions [37244400156](https://github.com/zhengcb81/company-wiki/actions/runs/37244400156) 对应head SHA完全匹配，最终 `completed/success`（Fast checks Python 3.12）。Ruff、严格类型检查、compileall/config doctor、unit、focused contract、CLI smoke 与 secret scan 均成功。
- N4-T1的独立收据此前已确认 ACCEPTED/INTEGRATED/PUBLISHED（114项跨层回归加真实loopback HTTP 400持久账本E2E；主线CI run 37241977614 success），此次没有新变更或需补验内容。N4-T2仍待交付。
- 发布后 `master` 与 `origin/master` 同步；仅保留原用户改动 `config/source_acquisition.yaml` 未提交，没有暂存或覆盖它。

## 2026-10-05 — MeetingConverter外包卡远端复核

- 按用户要求重新核对原始handoff、远端Git refs、PR和Actions。PR #1已closed/merged，merge SHA为`8a33a7f96292af8e6574d98b959703c6d11919eb`；远端`master`与`ci/fast-gate`、本地`master`/`origin/master`均为该SHA。主线push run `37241709261`、PR run `37241093118`、分支push run `37241089223`均success。
- 发现外仓`HANDOFF.md`的SHA/“PR未合并”段落仍是并线前版本；CWP验收收据和GitHub live状态一致且权威，本轮已在验收收据补充该过期字段说明。外仓文件未修改；MeetingConverter本地仅保留既有tracked `.coverage` dirty状态。

## 2026-10-05 — S5移除无人调用的Worker session launcher

- 源码调用调查确认`WorkerSession`、`WorkerController.open_session()`和`read_desired_state()`无剩余src/scripts生产调用者。移除该旧启动/心跳API与专用循环测试；`worker-status`、`worker-stop`、pause/interlock仍保留，并继续读取和清理升级前写下的runtime snapshot。
- TDD先以新增契约证明旧API确实退出；最终聚焦`test_source_catalog_control.py`、CLI retirement与automation race共 **55 passed / 17.48s**。Ruff四个改动Python文件及`git diff --check`通过。普通插件自动加载先因环境的`langsmith/pydantic_core` DLL权限在collection前失败；禁用无关插件后同一测试集完整通过（仅pytest.ini中缺asyncio plugin的既有`asyncio_mode` warning）。短路径`tmp/ptworker-s5-sandbox2`已在验证归属后删除。
- RF只读对账：remote `origin/main@8a153f3387ae75fb172e70f8ab63ffd38100779a`；`fcap`领先0、落后15提交，其3,833个execution_runs删除及两条weekly assurance dirty记录都属于owner WIP，未触碰。远端SourceRef v2仍为opt-in（默认`false`）。用RF/CWP两端都与对应主线匹配的代码跑三仓SourceRef原件复用/篡改拒绝E2E：**1 passed / 8.51s**，未下载或请求外部服务；隔离测试目录已移除。该测试不证明RF默认叙述/derived消费者迁完。
- 本次S5改动提交`a9b1a06f520c7d2565e2a5d93b90e26e9cdd28f2`并推送`origin/master`；pre-push fast contract smoke GREEN。GitHub Actions [37246820601](https://github.com/zhengcb81/company-wiki/actions/runs/37246820601) 对应SHA匹配，所有步骤通过，最终`completed/success`（Fast checks Python 3.12）。推送后仅保留既有用户配置`config/source_acquisition.yaml`未提交。

## 2026-10-05 — RF叙述消费者与S5空间依赖复核

- 先查RF再更新CWP计划。最近一次可信live检查记录 `origin/main@8a153f3387ae75fb172e70f8ab63ffd38100779a`；本轮sandbox直接访问GitHub HTTPS/443失败。只读本地ref为 `fcap@5319ee263c4af41ac255938c25bebd32cce56f66`、缓存 `origin/main@8a153f3`，未对RF执行写入或状态清理。
- 阅读RF main的N3a交接：已存在 `narrative_source_preparation.py` → bounded subprocess → CWP `company-wiki-narrative-read` 的跨仓路径；ref只发现metadata，read校验原文/工件SHA与size、身份/期间/as-of、locator和claim citations。N3a报告记录89项主节点测试，表格列明年报PDF 9,165,875 B/96 locators及电话会TXT 66,324 B/14 locators；收件报告仍明确“未接入收入计算”。RF filing `source_reader_v2` 另一路默认false，默认SourceBundle仍读旧派生角色。计划据此改为复用N3a，不造新wire，后续再与RF当时的PWF协调预测入口接线。
- 用CodeGraph查到CWP `NarrativeTransportReader` 和 `company-wiki-narrative-read` CLI/合同；精确源码引用也确认RF adapter会调用该CLI。因此此前“没有可调用入口”的推断不成立，已在说明中更正。旧的 `NarrativeEvidenceResolver` 要求caller提供raw path；它不应被误当成跨仓正式接口。
- 精确读CWP `EvidenceQueryService` / `ExtractionQualityService`：前者从SQLite EvidenceSpan行读span正文/locator；后者读artifact元数据和span汇总；二者不打开normalized Markdown正文。字面调用点仍在 `llm_summarizer.py`、`section_extractor.py`、`summarizer.py`。据此修正S5依赖图：先退正文消费者并处置指向已删文件的artifact句柄/quality状态，再删物理Markdown；EvidenceSpan表迁移另列S6。
- 检查本地 `codex/rf-state-audit@447d1c7` 两个纯文档提交：补充报告因ACL拒绝而未完成全量分类，与主线同路径完整审计报告形成冲突；只新增“安全可删0 B/应停止”保守结论，不形成清理候选。未合并覆盖、未改RF。
- PWF三文件已更新：总计划写明N3a消费边界、未接预测入口及后续实测；S5/S6细则分开物理derived、artifact metadata、EvidenceSpan；findings/progress记载证据与限制。初次细则补丁因目标句实际位于总计划而匹配失败，没有落盘；重新读取定位后已修正确切段落。
- 本轮没有跑产品测试（代码未改）；下一大节点仍是N4-T2交付与N4C真实样本，随后用当前RF/CWP代码运行pathless N3a离线真实文档端到端。仅Markdown改动，后续执行`git diff --check`与本计划声明核对；不得称RF live ref本轮可达，也不得删除normalized正文或旧span。
- Git暂存首次因sandbox账户无`.git/index.lock`写权限而失败；未创建/残留index lock，未暂存任何文件。按用户此前授权改用正常权限，只暂存本段列出的四份PWF文档；`config/source_acquisition.yaml`继续排除。

## 2026-10-05 — CWP真实原件transport/locator E2E

- 为独立验证当前CWP读取端，运行 `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 COMPANY_WIKI_RUN_EXTERNAL_DATA_TESTS=1 python -B -m pytest -q tests/e2e/test_narrative_transport_real_samples.py --basetemp tmp/ptnarrative-real-current-20261005`。实际结果 **4 passed / 31.70s**，4类是年报PDF、招股说明书PDF、投资者关系活动记录PDF、电话会TXT。
- 测试读取现场原始字节和SHA，但在独立`published_fixture`根内发布/读取；验证hash绑定、公开CLI输出与artifact hash一致、locator>0且replay verified，生产fingerprint、原件hash和mtime前后不变。测试文件声明no network/no production catalog write。它不是实际N4 Worker/summary run，metadata是隔离fixture，也不覆盖RF N3a外部CLI adapter或季度选择缺口。
- Path guard将长度72的requested basetemp自动移至TEMP短目录；运行结束事件明确`removed=true`。pytest报告两个无失败warning：插件禁用时缺asyncio插件的`asyncio_mode`选项，以及现有`.pytest_cache` ACL写入拒绝。测试没有因warning失败，没有再次重跑。目标requested目录由本会话finally逻辑按workspace包含检查后清理。
- 本轮任务计划合并补丁第一次因过长上下文不匹配失败，未落盘；读取精确行后用较小范围补丁更新S4进度与本节点收据。没有产品代码改动，下一动作仍是接N4-T2后跑集成Worker/N3a消费与真实批次；本收据不能算N4C完成。

## 2026-10-05 — RF N3a pathless真实年报/电话会离线联调

- 开始前只读核查RF：当前owner checkout为`fcap@5319ee263c4af41ac255938c25bebd32cce56f66`，cached `origin/main@8a153f3387ae75fb172e70f8ab63ffd38100779a`。fresh `ls-remote`因sandbox至GitHub HTTPS/443连接失败；N3a状态与测试结果只绑定该已缓存commit，不声称它是本轮实时远端HEAD。RF owner约3,835项tracked WIP原样保留。
- 第一次归档只带N3a直接脚本，15项在子进程导入缺失的RF `company_wiki_narrative_tree`时失败。结果属于临时harness漏打包依赖，尚未触及CWP读取断言；随后从同一commit归档完整`scripts/`和`tests/`，显式让真实CWP只读样本fingerprint helper可导入后重跑。
- 完整离线端到端：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHON_DOTENV_DISABLED=1 RF_RUN_NARRATIVE_REAL_SAMPLES=1 COMPANY_WIKI_NETWORK=blocked`，`CWP_NARRATIVE_CODE_ROOT=<CWP root>`，pytest经`PYTHONPATH=<CWP root>/tests;<CWP root>`加载CWP producer与RF快照。`tests/test_narrative_source_preparation_e2e.py` **15 passed / 39.81s**，含四类文件、拒绝/限额输入和真实P01年报PDF+T01电话会TXT；真实原件SHA/mtime与CWP生产fingerprint测试前后不变，RF从CWP pathless CLI得到正文和locator。
- 输出只证明已存在RF N3a bounded subprocess能消费真实CWP叙述transport，不证明预测计算、N4 Worker摘要/并发、季报选择或SourceBundle默认路径已经迁移。pytest唯一warning是禁用插件后的既有`asyncio_mode`未知选项。
- Path guard自动将basetemp移到TEMP，运行后确认`removed=true`；CWP隔离导出目录经绝对路径范围检查后删除，`scratch_removed=True`。无网络/付费API调用、无生产原件/catalog/database写入，RF无写入；CWP状态仍只有原用户修改`config/source_acquisition.yaml`。对应findings与总计划已同步此收据，下一步仍是N4-T2联合验收后做实际Worker批次，不重复跑空fixture adapter测试。

## 2026-10-05 — 主线Worker并行档与恢复能力的三项大节点验证

- 依据CodeGraph与`profile_slots`源码确认worker采用多进程档：P1=1 mixed；P2=1 compute+1 model；P4=3 compute+1 model。所有profile保持单model slot。扩大profile能让多个文档在选择/验证阶段并行，并让不同文档的计算与模型阶段重叠；不会并行发送多个LLM请求。
- 扩展真实样本E6测试以覆盖P4并更名为`test_e6_real_samples_run_isolated_p1_p2_p4_and_restore_test_root`。完整重跑命令使用`COMPANY_WIKI_RUN_E6=1`、`COMPANY_WIKI_E6_TEST_BASE=tmp/e6p4`、插件自动加载关闭及本地network-blocked replay模型；**1 passed / 101.44s**。四类现场原件P01/P04/P07/T01加格式化skip样本，P1/P2/P4全通过，同为5 visible artifacts/4 model calls，0 retry/SQLite busy，object bytes 419,428、skip 1,441；原件及生产fingerprint保持不变。
- 实测 profile 收据：P1 36.296s、359,493,632 B peak RSS、396.7 docs/h；P2 34.384s、437,956,608 B、418.8 docs/h；P4 29.091s、630,353,920 B、495.0 docs/h。P4比P2快15.4%、内存1.44倍；目前只能推荐P4作为下一次有界N4C集成批次的candidate。E6每档仅一轮，且sqlite busy p95/catalog lock wait未测，不能外推生产100文档吞吐。
- `COMPANY_WIKI_RUN_E7_BENCHMARK=1`运行合成45-job、三档各两轮：**1 passed / 77.10s**。median wall P1/P2/P4为13.735/10.409/6.830s；对应max concurrency 1/2/4；E7定义的相对throughput指标P2/P4分别+32.0%/+52.4%。P4/P2 peak RSS中位数为267,538,432/170,479,616 B（1.57倍）；满足既有speed/RSS candidate threshold；busy error与retry皆0，但lock p95字段未测。
- `test_e7_r11_100_narrative_jobs_recover_after_worker_restart_without_duplicates`：**1 passed / 19.43s**。34个测试文档、102个作业中，强制杀死一名compute worker后租约过期、重启recovery；34个bundle各自唯一可见、34 distinct work keys、34次模型夹具调用，目标作业一次`LEASE_EXPIRED`后一次成功，raw hashes不变。
- E6专用数据根、旧/新basetemp、E7与R11 pytest scratch均已按绝对路径校验并删除，E6的测试根在用例退出时为空。唯一warning仍是缺插件时pytest.ini中的`asyncio_mode` unknown option。无provider/LLM外调或生产写入。此处只有E6 opt-in integration test改动；N4-T2卡不包含此文件、不重叠。N4-T2仍待交付；合入其selector修复后，MAIN要在P4 candidate档把改良选择、实际Worker摘要、CWP公开读取与RF N3a合成一轮真实业务样本验到底。
- 发布收据：上述opt-in E6 P4覆盖和三份PWF以`069c8d4db0d1e4537c1de1e79d7784201c45ff66`提交并推送。Pre-commit Ruff和host-assumption guard通过；pre-push fast contract smoke通过。GitHub Actions [37253121382](https://github.com/zhengcb81/company-wiki/actions/runs/37253121382) head SHA匹配、唯一`Fast checks (Python 3.12)` job **73秒 completed/success**，包含Ruff、严格类型检查、compile/config doctor、unit、focused contract、CLI smoke及secret scan。提交后`master`与`origin/master`同步；仅保留用户原有`config/source_acquisition.yaml`未提交变化。此后新增本段是docs-only，按CI的`paths-ignore`不触发Actions。

## 2026-10-05 — N4-T2真实季报/IR选择器基线

- 交接收据：[n4t2_real_source_diagnostic_2026-10-05.md](harness_lanes/results/n4t2_real_source_diagnostic_2026-10-05.md)。重新检查RF，本地 `origin/main` cached ref仍为`8a153f3387ae75fb172e70f8ab63ffd38100779a`；owner `fcap`未提交assurance与大量历史execution_runs状态保持原样，没有RF改动。此工作区不能fresh核验GitHub live ref。
- IR真实SourceRef `3e25aab404a1`经正式SourceVersionReader验证。默认解析57单位/2,350字符、覆盖不完整；延后表格扫描后67/4,689字符、完整覆盖、零错误/opaque，但仍没有候选。完整扫描有3个PDF group共同包含new-business/overseas主题、progress、recency及具体行动信号，然而当前candidate rule只允许industry progress+recency。这是具体规则漏检，N4-T2应给其他目标业务主题补有界进展条件，并用真实PDF locator replay验收。
- 季报真实SourceRef `37f0eb13fc97`完整扫描13页/192 units/11,645字符，覆盖完整、无解析错误/opaque，7类既有主题和high-value event均零命中；不能将“现词库未识别”当作“无业务内容”。保留needs_review，直到更高召回覆盖和负例证明可以跳过。当前catalog标题并非空值，titleless fallback仍须用synthetic empty-title+known-kind测试。
- 无原文打印/存盘、无临时字节副本、无模型/provider/network和生产写入。该诊断没有改代码；N4-T2仍待交付，下一阶段仍要联合N4-T1、测试locator与skip边界，之后再跑N4C真实Worker/P4/RF N3a消费。

## 2026-10-05 — S5旧写者与RF默认reader只读对账

- 重新核对CWP：`master`与`origin/master`均为`5cabe47`；N4-T2尚无可见交付分支/worktree/任务结果。唯一dirty文件为用户配置`config/source_acquisition.yaml`，保持未读写入范围之外。
- CodeGraph与定向源码检索确认旧`SourceCatalog`全文normalize/summarize API仍存在，旧合同测试仍调用；`src/`、`scripts/`未发现这些包装方法的业务入口直接调用。旧LLM/extractive summary与sections流程仍读取normalized正文。CodeGraph对同名方法caller存在错配风险，未用其零结果作为删除依据。
- 先检查RF：用只读的每命令`safe.directory`参数读取本地refs，未改全局Git配置。RF当前本地`main@6fb2def7`、`fcap@5319ee26`、缓存`origin/main@8a153f33`；tracked owner改动共3,835项，含3,833项execution_runs删除和2项weekly assurance修改。读取缓存`origin/main`源码确认`source_reader_v2=False`；本轮没有网络live检查，也没有修改RF。
- 这让S5下一动作更明确：先完成N4-T2与N4C，使新叙述reader有实际Worker产物和RF N3a实样证据；RF默认SourceBundle转换之前不得删除旧normalized/summary/sections或span。旧写者代码退役、物理文件清理、DB span收缩分别保留为不同的大节点。本轮为PWF只读收据，未改生产代码或数据。

## 2026-10-05 — S5真实derived与SQLite空间实测

- 使用正常用户工作目录 `C:\Users\郑曾波\Projects\company-wiki`，确认resolved root不是sandbox overlay；只读盘点 `.source_catalog/derived`，未遍历/打开公司原件。无reparse entries。
- derived共7,104文件、2,826,010,634 B：normalized Markdown 3,528个、2,748,621,075 B；sections 596个、67,624,394 B；summary Markdown 2,980个、9,765,165 B。normalized占约97.3%，决定S5先解决RF默认normalized读取，再争取主要空间收益；旧消费者迁移之前不删除这些文件或相应handle。
- SQLite以`mode=ro&immutable=1`和`query_only=ON`打开：746,055 pages、freelist 0、1,490,530 EvidenceSpan；artifact状态计数：normalized completed 4,842、partial 127、unsupported 15；sections completed 238；summary completed 2,969。没有写库、VACUUM或全库副本。
- 上次Stage A已释放的138,648,023 B为受限缓存逻辑长度；本次derived实测仍为2,826,010,634 B。两者集合不同，当前不把旧释放量当作本轮收益，也不把文件逻辑大小等同于磁盘free-space。原件、数据库和配置未修改。本轮PWF记录的`git diff --check`与推送门将在提交时复验；不跑产品测试。
- 同一轮对CWP origin执行只读`git ls-remote --heads`，live `master@66a4eb1`；远端只见既有N4-T1匹配分支，没有N4-T2分支。当前Codex线程/工件列表也没有N4-T2收据；这是“尚未收到”的证据，不表示外部非Codex harness已停止。RF本轮只查本地refs/owner状态，没做live fetch。

## 2026-10-05 — N4-T2 MAIN implementation; external delivery still running

- MAIN learned after publication that the dispatched external N4-T2 harness was still running. The implementation was already committed and pushed as `ea9dd26`; its six code/test paths overlap the external card. No external worktree was read or written. The external card remains open until its base..head and handoff are compared; do not merge duplicate paths blindly.
- TDD exposed six failing route cases: complete annual, interim, quarterly, IR activity, prospectus, and transcript sources with zero recognized candidates were all eligible for automatic skip. This was unsafe because complete parser coverage does not prove selector vocabulary coverage. Business-bearing kinds now stay `needs_review` when empty. An empty result can skip for administrative IR policy/meeting notices or when every fully scanned unit was positively classified and removed as a financial-table row.
- Verified real sources through exact SourceRefs and `SourceVersionReader.open_version` with `purpose=narrative_derivation` and the current read-policy pin. IR SHA `3e25aab404a1`: 67 full-scan units, 2 selected spans/4,813 bytes, 2 verified replays. Quarterly SHA `37f0eb13fc97`: 192 units, zero candidates, `needs_review`. The title field was absent in both manifest views; the known document kind routed them. No raw text printed/persisted/copied, no model/provider/download request, no catalog mutation.
- Focused MAIN set **104 passed / 2.33s**; Ruff and diff check passed. Pre-commit Ruff, contract mypy, and host-assumption guard passed. GitHub Actions run [37268779206](https://github.com/zhengcb81/company-wiki/actions/runs/37268779206) matched the pushed SHA and completed successfully (about 82 seconds).
- One focused pytest attempt had 2 setup errors because the new basetemp parent was absent; created that parent and reran the same set successfully. The branch test scratch and MAIN scratch were both removed after exact-path checks. One earlier PowerShell-through-Python patch attempt had Unicode conversion in the script pipe and stopped before the intended test edits; corrections used direct UTF-8 file I/O and were covered by the green suite.
- Commit `ea9dd26` is fast-forwarded and pushed; `origin/master` readback matched. `config/source_acquisition.yaml` remains the only known pre-existing user modification and was untouched. Next: reconcile the still-running external N4-T2 delivery, then run N4C bounded real Worker/P4 + RF N3a consumer/storage batch; don't reopen validated selector tests unless the external delta changes this code.

## 2026-10-05 — N4-T2外包交付验收与选择性吸收

- 外包分支 `codex/n4t2-selective-narrative-coverage@2b5bec9` 基于N4-T1 `4a53080`，工作树干净。N4-T2六路径增量与主线 `ea9dd26` 重叠，不是主线后续提交；不整支合并。外线82项测试、Ruff和`git diff --check`通过，未找到正式handoff报告，以commit/测试及逐路径差异作交付依据。外包工作树保持只读、未修改。
- 选择性吸收外线遗漏的“行业景气、生产装置/产销量/产能利用率、境外业务/收入/基地”等词汇，并识别“设立/成立/启动新业务、新产品、事业部、研究院/研发项目”的事件。明确拒绝移除“具体业务动作”条件或按词汇无命中自动跳过季度/业务文件；真实季度完整扫描零候选仍为`needs_review`。这防止扩大到泛泛陈述与未知词库盲区。
- 新增titleless quarterly/IR PDF综合测试，覆盖行业变化、生产经营、新业务单元/产品、境外业务四类及套话/目录排除；所有选中span都以原PDF字节重放。聚焦主线回归 **107 passed / 1.50s**、Ruff通过。首次pytest在插件自动加载阶段遇到`langsmith`依赖的`pydantic_core` DLL access denied；禁用无关插件后同一测试集全绿，只有既有`asyncio_mode`未知选项warning。测试basetemp已按精确路径删除。
- 新selector完成E6真实Worker P1/P2/P4复测：**1 passed / 246.39s**，四类原件年报、招股书、IR活动PDF、电话会TXT，加一类格式化IR文档skip。每profile可见5对象/4模型调用，真实原件共20,597,846 B，叙述对象445,842 B（2.16%），skip对象1,441 B；重试0、SQLite busy 0、WAL 0。生产目录/原件/配置指纹和locator replay断言通过，退出后E6工作根与pytest basetemp均不存在。
- 当前profile：P1 93.006s、154.8文档/小时、queue p95 76.177s、handler p95 41.639s、RSS 373,583,872 B；P2 89.453s、161.0/小时、queue p95 73.355s、handler p95 40.521s、RSS 459,042,816 B；P4 62.527s、230.3/小时、queue p95 41.893s、handler p95 38.773s、RSS 686,489,600 B。相较先前E6记录P2 34.384s/P4 29.091s明显变慢，P4又有更高内存；不将一次profile提升解释为默认并发可扩。N4C接下来先看真实调用trace/handler与等待时间来源，再以有限P4为候选接RF N3a公开reader，核summary/citation/language、空间和预算。
- 验收收据：[n4t2_selector_acceptance_2026-10-05.md](harness_lanes/results/n4t2_selector_acceptance_2026-10-05.md)。外包差异已关闭；选择性吸收提交`0657579d43dc51f327991a0e41aee552e18eb483`已推送`origin/master`，pre-push fast contract GREEN，GitHub Actions [37273071081](https://github.com/zhengcb81/company-wiki/actions/runs/37273071081)匹配该SHA且completed/success。`config/source_acquisition.yaml`及RF/ET/其他仓库owner工作均未改动。

## 2026-10-05 — 按用户要求暂停于N4-T2验收后

- 本轮交付完成：外包N4-T2差异已评估，安全且有数据依据的词汇/事件补充已选择性合入；测试、真实Worker P1/P2/P4复测、CI与PWF收据均已完成和发布。代码提交`0657579d`的Actions成功；收尾文档提交`7b87ff3`已推送。
- 用户要求“把手头任务做完，然后更新PWF文档，暂停”。当前停止点是**N4-T2已关闭、N4C尚未继续**；未启动新的E6、RF consumer联调或其他写入。唯一下一步（用户恢复后）：先归因E6队列等待/handler延迟升高，再以有限P4候选推进N4C和RF N3a消费实测。
- 用户配置`config/source_acquisition.yaml`仍是唯一工作树未提交项，保持原样。主线已推送到远端，代码CI结果及验收报告已记录。整体目标尚未完成，暂停不等于完成。

## 2026-10-05 — 恢复N4C，先作阶段耗时控制实验

- 用户恢复整体目标；工具实读active，上一目标turn已完成N4-T2代码/测试/远端CI与PWF发布，属于progress。
- CWP仍为`master@f26a712`，只有既有用户配置未提交。RF正常账号只读核实fcap `5319ee26`、本地main `6fb2def7`、origin/main及live main同为`8a153f3`；未提交只有weekly_alert.jsonl、weekly_manifest.json两文件。RF旧execution_runs沙箱ACL拒绝所呈现的3,833删除并非正常账号工作树删除；本线没有修改RF。
- RF正式N3a交接不在fcap checkout，已从origin/main提交读取；复用其reference/read DTO、bounded subprocess和stdout结果，不另造接口。初次sandbox广域diff产生大量ACL拒绝；改正常账号聚合计数后结果明确。PWF恢复脚本已显式解析到本计划目录，未更换共享active pointer。
- 下一动作是同一真实PDF字节上的旧/新选择器控制实验：分别计parse/select/replay及CPU/wall，原件只读，摘要/正文不输出；只导出四个旧源码模块到新建独立测试根，结束删除该根。不能因Worker池拓扑未变便断言选择器不影响延迟。

## 2026-10-05 — 当前耗时调查与版本修复收尾，随后暂停

- 用户最新指令是完成手头任务、更新PWF并暂停。仅收口控制实验和版本修复；没有执行新的付费模型批次、RF消费联调或S5/S6删除。
- 两轮对照（cProfile三PDF、无profiler招股书）均结束且诊断根恢复；完整聚合结果在[本次收尾收据](harness_lanes/results/n4c_latency_version_closeout_2026-10-05.md)。当前招股书40.194s/旧37.417s，表格发现26.726s、84/144空结果；选材增量不足以解释旧E6差异，不编造已知全根因。
- TDD RED：当前与强制旧`0.2.0` batch hash相同；将`NARRATIVE_SELECTOR_VERSION`升为`0.3.0`后input hash和event ID均不同。聚焦`test_narrative_batch/evidence/select_handler/selection_architecture`共117 passed/1.62s，独立root恢复；只有插件关闭造成的asyncio配置提示及sandbox pytest-cache权限提示。
- 字面版本搜索发现英文召回测试旧固定`0.2.0`，实跑得到一个旧pin失败和9个sandbox默认TEMP setup权限错误。版本断言改为召回引入版本下界，保留parser和真实行为断言；后续完整Unit用正常用户账号、独立短根`tmp/n4u`、cacheprovider关闭，避免该环境误报。更早`rg`通配目录参数触发Windows错误123，改为目录配`-g`；不重复同错误命令。
- 主计划顶部、S4状态、Next Step及N4实施卡已统一；更正RF ACL误读计数和RSS把B误标MiB的当前表述，N4-T2已关闭，不再等待外包交付。真实provider下一run最多剩49,675 tokens/$0.094742，旧未知预留保留；暂停期间不执行。
- 完整Unit首次结果：**1425 passed/1 failed/185.74s**。唯一失败为`test_git_changes_stay_inside_the_card_write_set`，它把已结束G1-LEGACY卡写集套在整个脏checkout，拒绝用户配置及新计划/版本改动。移除该项及同类删除集合检查（共2项）、不用的allowlist，保留所有产品行为与原件夹具保护。独立`tmp/n4u`已finally恢复；不为这次目录门修改而再跑三分钟全Unit，最终以远端同SHA完整Unit及push精选门验收。
- 4个Python文件的Ruff、mypy合同与host-assumption hooks均通过，config doctor无相关改动按范围跳过；代码提交`b09e845a845e172a3659acef6ad6d172f7565d2f`。commit hook临时保存/恢复未暂存文档与用户config后成功；只提交本轮4文件。
- 发布验证完成：`b09e845`已推到`origin/master`，live `ls-remote`匹配完整SHA；实际push运行精选契约门GREEN。Actions [37354477263](https://github.com/zhengcb81/company-wiki/actions/runs/37354477263)匹配该SHA且completed/success，job为18:14:46–18:16:03 UTC（77秒），完整Unit、精选合同及静态/CLI检查全绿。没有为日常commit恢复pytest门。
- 最后清理核验：`tmp/n4c-timing-20261005`、`tmp/n4c-stage-benchmark.py`、`tmp/n4u`及请求的版本测试根均不存在；自动迁移basetemp的cleanup removed=true。原件未写，用户`config/source_acquisition.yaml`收尾前后SHA一致（`3609e707466e…`），未暂存或提交。其他仓无写入。
- 本轮主计划、findings、progress、N4实施卡、并行总计划与新收尾收据统一为同一停止点及恢复动作；6份文档随收尾提交发布。用户明确要求暂停，目标在这些交付完成后设置paused；整体S4/S5/S6尚未完成，暂停不等于完成。

## 2026-10-05 — 再次恢复，新增三个互斥P5施工包

- 用户恢复运行，工具确认goal active。CWP `f775406`与live master一致，只有原有用户provider配置dirty；RF正常账号仍2份assurance owner变化，main/live `8a153f33`。凭证仅检查存在性，未输出或调用模型。
- 用户随后要求几个可独立较大施工包，作为当前主线的并行拆分。只读盘点确认RF默认source-preparation仍legacy；FF v2 CLI已自动pathless、旧Worker scope还在、两个JSON runner为capture后限长且filing用字符计数。StockWiki narrative consumer和ET deadline均已完成，不凑数重派；IQS/Dayu不写。
- 新建`harness_lanes/p5_parallel_packages_2026-10-05.md`及3张自包含卡：P5-RF默认SourceRef迁移、P5-FF旧Worker/实际有界进程、P5-STORAGE独立旧派生/span/VACUUM工具。各自新兄弟worktree、独立PWF/HANDOFF与测试包；storage只写新增tools/tests，不改MAIN src。均ready尚未派发；没有新建外仓工作树或修改外仓。
- MAIN继续N4C真实模型/消费者，源wire固定，RF/FF两包可对当前正式接口独立测试；storage工具只对隔离fixture执行，生产清理前置留MAIN。统一handoff JSON/MD仅作交接，不是新人工许可/签名门；大节点验收不变。
- 调查过程修正：第一次假设FF/StockWiki有`src/`得到路径不存在，改`rg --files`核实际`scripts/`和`stockwiki/`；RF sandbox git-show被dubious ownership拒绝，改正常用户只读，不写global safe.directory。一次无命中字面检索exit1属未命中，不当成功或阻塞。
- 本轮只新增计划/卡片，未运行新Worker/provider/模型，未改原件、生产DB/config或owner文件；下一MAIN动作仍是有界N4C，不重复已绿E6。
- 文档校验：4份P5总包/卡片相对链接无缺失，storage专属新tools/tests路径当前均未占用，`git diff --check`通过。handoff明确delivery_head取功能提交、报告可另commit，避免自引用SHA循环；本地Replay/fake调用与真实外部调用分开，不造0计数。纯文档交付不重复运行长行为包；正常commit/push保已有hook。

## 2026-10-05 — LLM配置遵从修正（零新增外部调用）

- 用户要求必须遵守已配好的LLM使用方式。先写配置→HTTP和配置身份测试，再实现无秘密转换；权威入口使用已有Config.load及受管.env优先级，转发model/base_url/key-env/8192输出/temperature/reasoning_split、既有max_completion_tokens策略。测试与真实入口均移除另写国际端点和默认thinking disabled。源配置没有改写。
- 配置单元首轮RED为新API缺失；实现后发现跨unit测试import路径无package，改为共享support夹具（不复制selection实现）。实际CLI首轮模型参数全部正确，唯一失败是复用scratch峰值0与首次峰值4059不能相等；收据断言改为同产物、同预算、同持久增量、零重复HTTP，而不要求临时峰值相等。
- 集中责任包104 passed/30.13s，覆盖既有配置、HTTP、batch DTO、factory、真实child Worker/本地HTTP及恢复；随后配置13 passed/0.85s补齐6个新边界（7个已含在前轮），共110个不同case通过。Ruff、git diff --check绿。默认命令帮助可正常启动；正常账号只读Config.load确认实际国内模型参数及key存在，不打印凭证。
- 自建n4cfgred/green/green2/cli/node/final与n4aliasred目录已精确清理；policy/原件测试夹具由finally恢复。未实施alias草稿移除，下一节点再以现配置写真实RED，不把collection失败或旧2400阈值算alias通过。离线旧请求大小收据标记为historical/hardcoded，保留测量限制。
- 临时真实driver已接配置入口并扣除run02与旧unknown：下一run最多26,340 tokens/83,420 microUSD；未启动run03。PWF主计划/N4卡统一下一步，P5外线继续互斥施工。本轮零HTTP模型/零下载，用户config SHA仍3609e707466e…；RF仅原有两份assurance owner修改，其他仓无写入。

- 发布：`f099288`已推到master，正常pre-push快速合同GREEN；精确SHA CI [37361729624](https://github.com/zhengcb81/company-wiki/actions/runs/37361729624)当前queued，尚无远端测试结果，不冒称GREEN。收口复查补齐配置组合仍保留请求原有timeout/max-request/max-response caps，generation设置仍全由Config控制；配置14 passed/0.90s，合计111个不同case，实际CLI恢复复测GREEN。测试目录恢复，零新增paid call。

## 2026-10-05 — 私有请求降重和英文政策实际路由修复

- RF live main仍8a153f33，正常账号仅两份assurance owner修改；三个P5 worktree存在，约定handoff路径尚无新交付，保持各线写集独占。上一配置修正3daa9cc精确SHA CI37362106534已completed/success。
- 先写9项别名RED，修正两个非法测试夹具：EvidenceSpan的output/span哈希不能靠replace篡改，改用正式create生成角色/定位差异。生产私有prompt1.3.0、请求schema1.1采用columns+短alias行、常用role/flags默认值，逐条原文完整保留；例外角色及空flags覆盖也保留。选集不变，模型draft入canonical层前恢复完整span IDs，未知引用静态拒绝，final/SourceRef公开wire未改。
- 持久预算原本只hash HTTP body，未绑定本地alias映射。独立RED复现相同body/不同mapping得到同hash；现在请求身份同时绑定HTTP bytes SHA与model input SHA（后者含完整映射），不新增DB/签收表。旧run绑定prompt/selector版本，不静默重用。
- policy小探针证明不是PDF损坏：旧ir_policy或canonical investor_relations入库后，都得到通用IR类型及完整英文标题；两者英文都失败，中文policy标题成功。英文IR Policy/Management Policy规则缺失。修规则且selector升0.3.1；真实SourceCatalog→SourceRef→handler三小夹具全部skipped_no_narrative/coverage_complete，零模型请求。未将业务文件无候选或不完整扫描改成自动skip。
- 134项集中Unit/选择/预算/摘要回归GREEN（4.97s）；真实有限CLI+spawned Worker+loopback HTTP三case GREEN（39.28s），包含原语言中英输出、配置8192/reasoning、full canonical引用、相同run零重复HTTP、稀疏元数据英文policy跳过及原件/foreign jobs不变。Ruff/diff-check绿。
- 同一真实四份选集、同一已有LLM配置，对照3daa9cc私有prompt的最终测量：P01 33146→15805 B/上界24125tokens；P04 45471→16543 B/上界24863tokens；P07 10257→8035 B/上界16355tokens；T01 8064→5810 B/上界14130tokens。年报96 spans/10,551 B正文，招股160/10,391 B，IR11/3,920 B、TXT14/1,809 B，均未减证据或换输出上限。结果是HTTP输入降重，不是已释放GB；诊断根finally恢复、原件SHA不变。本轮没有新的模型HTTP/下载。
- 下一P04最坏24,863tokens可以进入剩余26,340额度；四份全部最坏预留79,473，大于剩余额度，不能承诺单批全成功。先从最难招股书+policy有限批取实际usage/final/RF公开read，再按实际余量推进其他类型；未知旧预留不退。国内pricing页面不可访问，官方input_tokens仅是Responses估算接口，与当前Chat Completions不是同一wire，不用估算替代硬上界，不切模型/协议/思考参数。价格与套餐事实先核，避免新的盲paid call。

- 正常账号只读Config确认仍为MiniMax-M3/国内base，key存在；未匹配官方sk-cp订阅Key前缀，不据此推定无订阅或实际费率，不输出key。国内公开pricing读取失败已记为待查；未发新的模型POST。列名与行位一致的9项最终检查通过，临时测试/诊断根全部恢复。本轮中间object投影收据未发布，仅保留最终测量和必要policy前后证据。
# 2026-10-05 — 配置修正发布及run03准备

- 134集中回归+3实际CLI/Worker E2E节点提交`e1cc87f`已推送master；pre-push GREEN，精确SHA CI37364555560 queued，未冒称成功。
- 沿用PWF指定plan；用户配置SHA不变。RF main live核对8a153f33，owner两份assurance原样；只查约定P5 handoff目录，暂无新交付。
- 官方国内价格现可读取，基于2.10/8.40 CNY与保守汇率下限6构造本次版本化费用代理；保留旧账并加历史汇率余量2,764microUSD。run03仅P04+policy、26,340tokens/80,656microUSD；配置入口/原参数/凭证不改。账户权益不猜，按全额PAYG上界估计，不新增购买或订阅。
- 临时driver只调整有限样本和计量依据，加入attempt数字HTTP诊断的清理前保存；原件保护/独立根finally恢复继续执行。第一次patch匹配旧pricing版本字符串失败，atomic未改文件，修正精确字符串后成功；语法解析通过。此记录时尚未发送新模型POST。


## 2026-10-05 — run03零费用失败与空间采样竞态

- run03正式配置入口仅P04+English policy，CLI报NARRATIVE_BATCH_FileNotFoundError。账本模型预留/新增tokens/费用均0，policy三阶段成功，P04 select未结束，没有RF实读；异常栈未保存，不声称唯一定位那次FNF。
- 确定性两个RED复现_tree_bytes的is_file→stat间文件删除竞态；修为一次stat，仅忽略FNF，PermissionError保留。31批次/请求责任测试GREEN，正式CLI+spawned Worker+loopback HTTP删除竞态故障注入1项GREEN（4.75s），原件/foreign jobs不变、final可用、根恢复。Ruff通过。
- 临时driver的with sqlite3.connect未关闭连接，cleanup WinError32；进程退出后保存小型run03费用/attempt收据，再按绝对路径验证删除唯一scratch。原件SHA和用户配置SHA一致；丢失的峰值/耗时/生产前后fingerprint列明，不伪造。driver已显式close，今后清理前先保存账本，避免丢费用事实。
- 下一run04仍只P04+policy，配置模型/8192/reasoning不动；run03不增加旧总额，保留26,340tokens/80,656microUSD与2,764microUSD历史汇率余量。N4C未完成，P5写集继续保留。详见harness_lanes/results/n4c_storage_sampling_fix_2026-10-05.md。

## 2026-10-05 — run04结算与三家配置入口验证

- run04实际80秒左右完成批次，但P04模型返回无效envelope且未保留细分阶段/usage，不能判断是供应商错误、正文为空还是其他shape。P04没有final；policy正常跳过。新增24,863tokens/17,304microUSD均为未知响应的最坏结算，不退款；总58,523tokens/33,884microUSD，另保留2,764历史FX余量。原件/生产fingerprint/用户配置/RF owner全不变，独立根恢复；详细JSON已保存。
- 先TDD复现invalid envelope丢已知usage，再保留静态response_stage、数字provider_code/HTTP status与成对合法usage；不保存原始错误正文、reasoning或Key。真实CLI失败/恢复case证明92已知tokens与111microUSD正确落账，unknown/unsettled均0；恢复零额外HTTP。旧未知费用不重算。先前run04的RF四文件bootstrap不完整；临时driver现从固定RF已提交SHA按AST导出六文件闭包，并在首次模型POST前校验CLI import。真实help退出0、零模型、测试根恢复；没有冒称RF业务实读已验收。
- 用户要求MiMo与DeepSeek也实测，避免MiniMax5小时额度耗尽。新增Config.llm_for_provider与Config.load(llm_provider=...)，正式配置CLI接受--llm-provider。六项RED先行后20配置Unit GREEN；fallback原配置不变，其他provider共用现有defaults和generation参数，不保存Key，不复制第二套model表。
- 集中责任集139 passed /8 deselected（35.14s）：135 Unit +4真实CLI/Worker/local HTTP E2E，三家各自token字段/参数、MiMo主配置不可达但fallback正确选中、重复运行零额外调用及独立根恢复均通过。Ruff/diff-check GREEN。一次patch因预期if实际为elif而失败，atomic未改文件；重新读取后精确修正。未以全仓慢测试作为新门。
- 正常用户真实GET：MiMo清单200，mimo-v2.5-pro在清单；DeepSeek401，key存在、无首尾空白、header字符合法、config等于环境、项目dotenv仅一项定义。没有模型POST，不宣称两家摘要可用。已请求token cap160k/美元仍0.10，以及用户修复DeepSeek配置凭证；答复前继续离线准备。MiMo官方公告旧v2.5-pro于2026-10-21退役，记入配置维护待办，不擅自切v2.6。
- RF live main再次只读核对8a153f33，仅两份assurance owner变更；三P5约定交接目录无HANDOFF。用户source_acquisition既有变更保留。采样修复0ae191a精确SHA CI37365773471成功。临时模型driver已准备P07/T01+policy对照、聚合run04及后续费用、防重run ID、完整RF依赖、清理前保存收据，不覆盖旧实验。

### 随后用户纠正：Flash模型与DeepSeek环境变量

- 实际本仓YAML/Config/default client/typed fallback仍用旧mimo-v2.5-pro和deepseek-v4-flash；先写3项RED，再按用户指定统一mimo-v2.6-flash / deepseek-flash。保留显式custom模型兼容夹具，更新真正依赖默认配置的断言。53项配置/客户端责任tests GREEN（16.38s），16项defaults/legacy适配GREEN（24.36s）。
- 初次401的诊断有遗漏：覆盖后config等于环境不代表加载前环境也一样。用户提醒后真实加载前环境key GET200，加载后key不同且GET401；Windows User/Process key相同。旧managed dotenv覆盖有效DeepSeek环境key是根因，无需更换key。移除DeepSeek的强制覆盖，仅环境缺项时dotenv补缺；MiniMax/MiMo受管key规则保持。
- 测试夹具初版被PYTEST_CURRENT_TEST跳过dotenv，出现不正确RED路径；改成模拟真实默认loader后环境存在case复现覆盖RED、补缺case通过。最终25配置tests+9 defaults=34 passed（10.20s）。修后正式配置两家/models均200，mimo-v2.6-flash与deepseek-flash均存在，环境密钥保留true；小JSON无key/正文，零模型POST。之前请求用户修复DeepSeekkey的问题已失效，已明确告知用户无需更换。
- 下一真实provider批次需160k token cap问题答复，仍限累计$0.10。Flash代理价与Credits已同步临时driver/交接报告；不声称摘要已完成。配置修正前的旧报告保持历史事实，最新Next Step和preflight报告已经纠正。
- 发布前Ruff/diff-check GREEN，用户source_acquisition配置SHA仍3609e707466e…，不暂存。本线测试根全部恢复：正常账号删除5个早期sandbox创建的RED目录遇到ACL拒绝，转回创建它们的sandbox执行经绝对路径验证的同一范围删除成功；不是生产权限变更，也未改ACL。旧未知费用SQLite与临时待用driver保留，原件/外包目录未清理。
- 已发布：a0ea41bd1aef8ffcdf535e065cb9ed5836abaf2b提交/推送成功；commit Ruff/mypy/config-doctor/host guard与正常pre-push快速合同均GREEN。精确SHA CI37368647773 queued，尚无远端结果。本地仅config/source_acquisition.yaml用户既有变更，SHA3609e707466e…完全相同。


## 2026-10-05 — S5公开writer退休节点与P5存储交付复核

- structural-first CodeGraph遗漏旧模块，补充当前Git tracked AST后，运行src/scripts内部仅service连接三个旧批量writer；历史canary不是当前入口。删除SourceCatalog.normalize/summarize/summarize_with_llm，不添替代flag或writer。21测试模块66处造数改到tests/support；读校验、指纹、撤回、清理断言保留，底层legacy函数暂留等待读者迁移。
- 公开入口TDD先4 RED，退出后23 GREEN。受影响集中包首轮235 collected：231 passed/4 failed，388.78s。两项操作文档过期、一项已删控制面板脚本断言、一项子进程PYTHONPATH缺tests/support。更新当前操作说明、退休已删面板测试、修父进程fixture路径；三个具体红灯+两个正式有限CLI中英/幂等E2E共5 passed/25.11s。原包有效234个case已分步绿，另2 CLI；不重复6分钟全包、不加日常CI慢门。
- P5报告的TXT golden RED亦在MAIN复现。公开producer/read重生成时先证明除selector/prompt版本和Replay响应hash外，source/spans/summary全等；更新bundle/ref/request/receipt/metadata哈希，单case GREEN3.14s。固化refresh工具与fixture说明，零外部模型；不能照旧报告归因bundle_producer版本，实际bundle_producer仍1.0.0。
- Ruff/diff-check GREEN；四个S5测试根已恢复absent。用户配置SHA仍3609e707466e…，生产原件/库没有执行写入或删除，本节点没有重新制造生产全库前后快照。生成golden的TEMP由finally恢复。DeepSeek/MiMo配置修正a0ea41b精确CI37368647773 success。
- 新收到P5-STORAGE delivery7ac1e3d（handoff文档f8f414a），真实功能diff17个新文件/3181行；未整支合入。四个真实schema独立fixture小试验实证：修改managed_files能删raw副本并仍报succeeded/来源DBdigest不变；全局index sweep删未登记孤立index；已retired但未unlink的文件rerun不续删；missing file仍留completed句柄。四根均恢复；没有生产删件/外部调用。正式JSON与修复顺序另存review，验收尚未通过。
- Probe先误以raw直接含md，两次StopIteration；读实际fixture后改为locations登记路径。一次PowerShell替换引号解析失败未改文件；改apply_patch。probe自己sqlite with不关闭导致一处WinError32，显式closing后修复并精确清除该scratch，再完成四项。不是生产权限/数据故障。
- RF live main只读核8a153f33、仅两份assurance owner修改；RF/FF无约定HANDOFF，写集不碰。旧N4C token cap问题仍无答复；本轮新增model POST/download均0，未重算或退款旧未知预留。


## MAIN节点一接续收据

独立验收树 `.codex/worktrees/p5-storage-integration/company-wiki`，分支 `codex/p5-storage-integration`。基于已发布MAIN18da250，导入原交付为候选d6b6e36/4387661；没有merge main。八项真实schema故障TDD先8 RED/26.63s；修复包21 case先20 passed/1 failed/60.48s，失败为managed子项缺artifact_id字段，修正后该幂等case GREEN3.64s。追加事务内全身份匹配后8保护/恢复cases再次GREEN21.51s。节点一提交72b11160b926e7ead0f163786f141ce2ead5f470；Ruff tool/helper/recovery全绿，commit host guard通过。旧底层业务代码src未改，真实原文/消费者E2E整体尚未复验，节点二仍pending，不把21项局部GREEN当工具全验收。

边界/spans/vacuum/recovery均调用实际parser/SQLite，已从unit移到`tests/integration/test_p5_storage_retirement_*.py`，共享夹具在`tests/support/p5_storage_catalog_fixture.py`。它们不进入CI默认全Unit包，CLI也无额外门。维护metadata只记录验证过的sections小型managed hashes以续删，不复制正文。没有新增授权JSON/签名/审批。

主线S5公开writer退休18da250已推送，pre-push快速合同GREEN，精确CI37371220690最新queued。节点一原文保护与恢复可接续，工具整体仍在候选树；下一步按本报告节点二执行。8项RED、21项组合、幂等及最终8项测试根p5red/p5green/p5final/p5bind全部恢复absent。已附着旧n4t2 worktree记录的目录实际不存在，未复用/恢复；新建托管验收树成功，无生产数据复制。


- 72b1116存储工具节点一候选已推到origin/codex/p5-storage-integration；从primary checkout运行相同baseline的正常快速pre-push GREEN，新工具专属行为此前在实际候选树验证。未merge主线、未伪称工具整体验收或生产释放。


- CI37371220690后续读取：attempt1 completed/failure，唯一job cancelled、runner空、steps0，check-run无summary/原因annotation；源远端仍18da250。只请求同SHA重跑一次HTTP201（既有Git凭证仅内存传递，未输出/落盘），不是重复改代码或重跑全仓本地包。收尾只有PWF/receipt，不触发新的代码CI来取消这个重跑。

## 2026-10-05 — 节点二开工

- 主线精确代码SHA18da250的CI37371220690 attempt2 completed/success；第一轮零step取消后只重跑同SHA一次，代码未为CI改动。PWF收尾4df5d12不触发替代代码CI。[同SHA结果](https://github.com/zhengcb81/company-wiki/actions/runs/37371220690)。
- 候选72b1116新增12个真实schema行为case，先RED：包括所有预览拒绝写连接、静态WAL sidecar、1200段聚合报告、keep计数、无效scope不扩大、压缩前事实/空闲空间、runtime对象根、ROWID顺序无关digest。测试只在tmp/p5n2red；不会进入日常Unit CI。

## 2026-10-05 — 节点二首次 GREEN

- 12项先行测试12 RED/30.75s，再12 GREEN/28.42s；静态WAL read确实创建两个sidecar、1200段dry-run报告183,867B、保留行误计absent1、无效scope未拒绝、before实际取在压缩后、runtime对象53B误计0，以及带空格未来表名未引用均已在fixture中实证。新span实现单次显式范围SQL DELETE，内存仅实际keep refs；聚合报告无逐span列表。标准VACUUM分别前后digest，排序不依赖ROWID，实测空闲空间和checkpoint。生产未删件。
- 为避免压缩前重复全库hash，空间预检只取page/文件数，进入既有operation锁后才取一次完整before；失败不报database untouched。真实E2E升级为固定SHA的AMEC年度PDF+微软Q4 2026电话会原TXT，原文stdout实际计算SHA，不用旧永真断言。SQLite连接显式closing；模块fixture finally恢复唯一样本根。旧交接一次性生成器移除，保留历史收据。
- 一次收口脚本相对路径误用候选cwd，未执行写入；改主仓绝对脚本路径后成功。Ruff两个旧E2E晚置/未使用subprocess导入随实际E2E收口删除；diff-check/Ruff GREEN。集中47项责任+真实四操作CLI验收已启动，句柄48508；不因观察超时重启。

- CLI报告路径另外3项具体RED/7.68s：--output误指raw/new final/数据库均会写坏fixture数据并报成功。MAIN新增自动路径保护；只限定收据不得写穿资料/目录，不加人工许可。真实47项包当时在跑，保持被测工具不变，先完成该包再改CLI；新case独立根p5pathred，原件/生产无写。

## 2026-10-05 — 集中验收首次结果与 teardown 定位

- 47业务case passed/256.28s，但模块teardown有1 error，工具整体尚未GREEN。真实PDF解析setup143.09s、四操作/原文read/final replay12.90s。实际副本retire9 files，derived6,360,914→0B；删15,962旧PDF spans；VACUUM DB32,796,672→2,174,976B、freelist7474→0，新final24,637B，事实相等/完整性ok。不是生产释放量。
- WinError32发生在删除mx/catalog/catalog.sqlite3。根因是_new_catalog返回的SourceCatalog缓存ReadOnlyCatalogReader持有连接，测试build helper没有close；Store短事务/4 CLI操作均已正常结束。主线SourceCatalog.close文档明确该生命周期责任。使用ExitStack登记catalog.close，保证setup失败/成功都在rmtree前关闭；不加盲目sleep/删除重试，也不放松测试恢复断言。
- 小型实测收据保存根外tmp/p5node2-space-metrics.json，测试进程退出后按绝对tmp路径核验删除p5node2成功。原AMEC/MSFT原件及用户配置SHA与固定基线全等。Ruff/diff-check GREEN。新3个报告路径RED经自动保护复跑，另加目录锁/SQL错误回滚两项；只复跑这5项+具体失败的真实E2E（句柄37533），不重跑47全包。E2E用JUnit property存根外聚合计量，测试根仍须finally恢复absent。

- 后续异常观测新增1 RED/3.67s：VACUUM已经执行、post-read失败时，旧report把before数值当after。将after不可观测明确表示null/after_measurement_available=false；不冒称数据库没变。修复只改失败报告逻辑，正常压缩由现有实际vacuum责任包覆盖。
- 第一轮集中包basetemp tmp/p5node2与本轮自建临时施工payload同名，pytest清掉了本任务自己的临时payload；无用户文件。已执行的payload无保留需求，根在失败后已恢复absent。后续最终测试用独立p5node2final；剩余编辑payload另用p5-edit，今后运行前确认测试根不存在，不混入施工脚本。此项不改变原文/费用历史根。

## 2026-10-05 — P5 工具合入与发布收口

- 候选9fa216677826fe90f2db3b35c08327e5732d4d47正常push后合入master@e570dafb92a3f6aaec51176682d348a1c9303535并发布，两次正常pre-push精选合同GREEN。精确主线CI37375836745 completed/success，没有重试。[远端结果](https://github.com/zhengcb81/company-wiki/actions/runs/37375836745)。53个不同case分步GREEN，不增加日常慢包。
- 真实E2E+路径/锁/回滚6 passed/196.98s（setup158.44s、call19.76s）；已关闭缓存reader，唯一真实fixture恢复absent。最后post-readback不可测RED修复，正常vacuum+该异常6 passed/14.63s。最新副本数据是derived6,360,944→0B，span删15,962，DB32,792,576→2,174,976B；完整source/new-final及PDF/TXT原文SHA/locator replay全等。验收JSON保存根外聚合实测，不存正文/库副本。
- 主/分PWF、S5/S6细则、并行总表、集成审查与小JSON已同步。P5-STORAGE不再派发；托管验收树已发起归档（附件状态archived，物理删除仍待核），工具/测试分支全部推送；原外包树保持未改。RF/FF交付尚未到，RF remote main8a153f33，owner两份assurance修改仍原样。
- 下一动作是CWP旧底层caller/质量metadata_only语义，随后接RF默认SourceRef迁移再做生产处置。生产derived/DB本轮没有清理、0外部模型POST；N4C累计token cap问题仍待答，不把key修复或GET200当付费摘要成功。

- 托管归档工具返回queued，附件随后显示archived；正常账号再次核对，Git仍注册且checkout目录存在。手工删除预检因仍注册而停止，零删除；不重复归档/强删。收据更正为物理归档未完成，后续只读复核后台状态，不阻S5代码工作。所有测试根已恢复absent，已发布代码/CI不受影响。

## 2026-10-05 — S5质量迁移节点

- RF/FF约定交付未到，不动其owner写集。CWP当前只有本线quality/projection/只读facade、相关测试/docs和PWF施工；用户source_acquisition原SHA保持3609e707466e…。
- 节点实施细则先写入S5/S6文档。11个行为先10 RED/1通过15.51s；初次实现8 passed/3 failed14.40s，失败是额外只读连接创建WAL/SHM及活动SHM读标记。复用已有严格只读connection，final通过既有NarrativeBundleReader验证有界bytes、source/selection/quality/policy，输出body-free，不转换raw、不建立永久span。不请求人工review；v2状态合同明确metadata_only/skip。
- 集中quality/transport/layering责任集51项正在运行（28425），未到GREEN前不提交、不宣称全节点完成。真实MSFT原TXT只读副本经正式质量CLI+transport replay已通过；仍有静态测试fixture需在快照前结束先前cached reader，以区分活动WAL read mark与数据写入。

- 集中51项50 passed/1 failed43.04s；剩余是已有活动SHM read mark被误计数据变更。关闭cached reader仍可留下WAL，15项随后13 passed/2 failed24.69s（四个新case已绿）。静态夹具改为在快照前正规checkpoint/关闭，另独立实测活动WAL可读到新提交source状态，原件、DB/WAL及全部持久文件不变，仅允许SQLite共享读标记。两具体红灯2 passed2.22s。共55个不同case已分步GREEN，不重跑全部旧慢包。
- 真实原TXT66324B固定SHA通过真实三任务select→Replay summary→verify/publish，再经质量CLI和正式reference/read CLI全引用回放；实际final计数与bundle相等，原件前后SHA不变，退出唯一测试根恢复。0外部模型/网络请求；不是MiMo/DeepSeek live摘要收据。五个本轮basetemp均按绝对tmp范围核验并删除。
- Ruff/diff-check GREEN，用户配置SHA保持。新15项解析/CLI测试在integration，未添加日常全Unit/快速CI慢门。下一步正常commit/push，精确代码CI后收口PWF发布字段。

- 代码dd35d2fc8abb9f7d72e36c0fbc27e7299c6c05f6已commit/push；正常commit GREEN。首次pre-push因本轮临时PYTEST_DISABLE_PLUGIN_AUTOLOAD=1未加载timeout插件而退出，零远端push；仅移除临时变量，正常精选pre-push GREEN后推送成功。没有改门或跳过检查。精确CI37378430383 attempt1 completed/success，全部步骤成功；不是取消后rerun。
- 后续只读caller调查：328份当前src/scripts/root Python AST仅导入fingerprint backfill、LLMSummaryError和SectionSlice，无旧batch writer直接运行导入；后两项只是public类型兼容，不能据此断言所有动态调用不存在。RF/FF/StockWiki排除.planning、assurance、tests、docs/artifacts后，没有旧EvidenceQuery/quality CLI运行literal引用；初搜未排除历史复制导致噪声，已收敛，不把审计快照当生产caller。RF remote main仍8a153f33/owner两份assurance改动，外线HANDOFF仍未到。
- 当前生产0删除、0模型POST，用户配置SHA保持3609e707466e…；下一集中节点是旧查询运行入口/精选消费，不复跑已绿quality或P5四操作包。PWF代码发布状态已收口。

## 2026-10-05 — S5正式精选检索节点

- RF外线在独立p5-rf-source-default工作树施工，main仍8a153f33，暂无HANDOFF；MAIN保持隔离。已先写完整精选节点实施细则，再进入测试。实际Config.load核准DeepSeek环境密钥优先与两家Flash模型/参数，零新API POST。
- 第一轮公开行为TDD 55 collected：17 failed/38 passed，43.14s。RED准确复现新operation不存在、旧evidence/sections CLI及public backend尚未退役；s5vred根恢复absent。
- 实现只接已有NarrativeTransportReader/精选BM25；旧read/reference wire不变。纯分组函数从现有summary_input抽出，不新增磁盘索引、任务表或provider。新view有版本/身份/selection/coverage及全回放收据；全部filters先于目录/原件打开验证。退出旧三个运行CLI和public EvidenceQuery exports，显式历史backend/夹具校验保留。
- 增加旧版本固定/新partial版本、真实TXT原语言search→lookup→恢复及API资源输入unit tests。原始raw tamper拒绝沿用resolver已定义content_sha256_mismatch，纠正测试最初猜测的reason，不改校验。一次多文件patch因progress错误锚点整体验证失败、零写入；按实际尾部重做。集中GREEN验收尚未完成；生产derived/span未删。

- 集中相关包102 collected：100 passed/2 failed，106.08s；test root s5vgreen恢复absent。真实MSFT search→lookup、全部locator replay、原始read/reference golden、旧版本固定/partial和中英PDF/TXT/skip均已绿。两处RED分别为新测试猜错公开错误名、历史archive case仍调用退役CLI。实际SourceVersionReader逐location实读SHA失败后公开聚合为unavailable/no_verified_location；内部content_sha256_mismatch不直接透过CLI，生产逻辑保持。修测试为公开语义，archive历史backend原有四类校验全保留，只更新已退出CLI断言。另增加新view读取前后全部持久文件SHA/集合不变证明（仅豁免协调用SHM）。仅复核这6个受影响cases，不重跑106秒全包、不加日常门。

- 六个受影响case复核6 passed/6 deselected、23.41s；s5vfinal根恢复absent。节点102个不同case已分步GREEN，四类持久文件集合/bytes、实际TXT原始文件与引用仍相等。Ruff/diff-check GREEN；用户配置SHA原样，0模型POST/0生产删件。
- FF正式handoff现已收到，正常OS账号Git核干净ab9ce33；报告code7c6cf48/18+194责任项GREEN，全仓10baseline-red需MAIN按当前下载合同补隔离fixture限额。暂未验收合入。RF远端只读复核仍8a153f33、两处assurance WIP不碰，HANDOFF未到。已校正并行总计划旧“均ready未派发”过期状态，不新建重复卡。当前下一动作是本节点正常commit/push和精确CI，不重复已绿长包。

- S5精选代码已提交/推送1b0feb44ff1695a8bae761eac538ce68236c04d6；正常commit及快速pre-push均GREEN，原用户配置被正规stash/restore且SHA一致。精确CI37381429717一次attempt completed/success，全steps成功，无rerun。三根s5vred/green/final已恢复；没有生产释放或新model POST。最后同步PWF/小收据，只做文档提交，不触发新的长代码CI。
- FF只读接续预验收3个实际短child：9B/10B/11B对10B限额为ok/OutputLimitExceeded/OutputLimitExceeded，等号边界确实错误；无网络/项目写入。其stdin、EOF/process wait、单流overflow与POSIX孤儿进程风险仅从源码确认结构，尚待受控watchdog试验。已把下一节点TDD/修复/限额fixture/三仓E2E/正常并线顺序写在独立预验收报告，不触FF owner/源码，不把源码推断冒充实测。

## 2026-10-05 — MAIN FF整合接续

- 上轮为progress：正式精选检索1b0feb4及PWF3fe77ae均已发布、精确代码CI GREEN。本轮fresh RF main仍8a153f33、owner两份assurance、无P5-RF HANDOFF。FF正式fcap仍d4d2fac，新增未提交test_source_ref_v2_db_query.py；SHA24f3a727…与已提交外包文件完全相同（mock接缝迁移），保留不reset，FMP key不读。外包树干净ab9ce33。
- 创建全新独立ff-main-integration，codex/p5-ff-main-integration基于ab9ce33，不修改原FF活动目录、交付树或外线.planning。遵循已发布预验收顺序，下一步实际child/watchdog RED→单生命周期实现；当前未验收并线/生产清理/外部模型调用。

- MAIN实际生命周期TDD：19 collected，14 failed/5 passed，33.81s。stdout/stderr等于cap的两项、七项无效资源预检及五项实际生命周期均RED；五项生命周期由独立watchdog终止自建树，不是无限等待。证明stdin阻塞、双管道关闭但进程未退出、单流溢出和孙进程持pipe都必须纳入同一个期限。短根tmp/ffmred已恢复absent，0网络/0模型/0真实下载。下一步实现Windows先入job再释放bootstrap及POSIX保存自有PGID，异常先终止树再收线程；API/caps/费用与原件保持。
- 用户再次交付P5-FF/P5-STORAGE：STORAGE主线e570daf及精确CI37375836745已验收，生产清理仍未执行；FF以MAIN实际RED为准，不能直接把交付complete等同可并线。

- 首次修复集中37项：18 failed/19 passed，77.56s，ffmgreen恢复absent。无效资源预检及三个期限/回收场景已GREEN。对同一短命令进行独立Popen对照，实证Windows启动器未显式传stdio会丢输出；显式stdin/stdout/stderr后完整得到hello/error。修启动器句柄接线，不放宽字节断言。另两项旧测试指向根本不存在的_run_bounded别名，实际两个runner都使用_run_bounded_json，更新为同一实际函数identity检查。sandbox Ruff cache写失败，无代码诊断，改同所有者--no-cache执行。0原件/网络/模型。

- 修stdio后集中37 passed/11.08s，ffmgreen2恢复absent；包括提前派生同步场景、孙持pipe、stdin阻塞、单流overflow、恰好cap、全部deadline和真实thread/PID回收。随后报告中的10处旧下载红灯全部实际复现（10 failed/10 deselected、43.50s），公开结果为ensure fatal。按当前下载合同只补测试请求的acquisition_limits，不降低生产校验；下一步复核这10项及三仓离线链/真实年报。
- 当前Config.load再次实读DeepSeek环境变量存在且与实际LLM key相等，加载前后不变；DeepSeek=deepseek-flash、MiMo=mimo-v2.6-flash，两家8192/1.0，endpoint沿配置。只输出布尔和非密配置，零模型POST。

- 10项fixture补limits后的复核仍10 RED/19.92s：真实原因是1.1/1.2 validator根本禁止已有acquisition_limits字段，不能仅补fixture就修复。这纠正交付报告及MAIN初判“仅fixture”的结论。MAIN兼容修法为旧请求也接受同一个可选、明确的acquisition_limits对象并复用现有验证/argv/共享deadline，不猜预算或放宽CWP；已有response/handle/golden与版本不变，v2复用禁limits规则不变。先追加8项legacy限额TDD，再实施薄兼容；普通无限额历史reuse保持。

- 旧限额TDD8 RED/0.12s；实施后集中53项45 passed/8 failed、84.83s：8个legacy/23生命周期均绿，剩余一个复杂度、四个spy、三个noop下载。实际gap的provider_reason明确是spy-provider不支持bounded acquisition（0次provider），并非生产下载器错误。为离线fake adapter补supports_acquisition_budget和真实模拟字节usage/预写限额；noop无外网/正文返回零usage，不放宽生产能力校验。资源输入按期限/caps/命令三个责任拆纯验证函数；mypy四处是OS条件原语和异常推断，已按实际平台类型修正，公开两文件mypy GREEN。下一步只复核剩余8项并增强孙PID同步，不重复53项长包。

- 剩余风险复核10 passed/35 deselected、57.17s，包括加强真实grand PID同步、legacy下载fake预算/计量及Worker状态。37项进程责任加本节点53个不同case已分步GREEN，不声称一次53全绿。FF→ET→CWP正式offline acceptance GREEN：真实三仓代码，FMP provider HTTP由私有worker seam替换，重复0provider，2秒provider deadline与ET临时根清理、原语言JSON/text各自SHA/size通过。ffme2e恢复absent；同次自建真实年报脚本只因把v2 source_candidate/filing误当v1 capture_ready/handle而RED，修断言为既有公开v2合同，生产接口未改，单独复核原字节。ET主线63c4090，两份未跟踪owner文件保持；原件SHA仍固定，0网络/模型/生产删件。

- 实际中微年报单独复核GREEN：9165875B、d64c4108…固定SHA；真实FF v2两次source_candidate/pending_verified_open→CWP公开source_reader_cli返回完整原字节及SHA/size receipt。重复provider0、pause文件0、fixture根内部finally回原样，ffmreal整体恢复absent。身份/期间/公开日是标注fixture，不冒称live元数据验证。正常发布前RF owner仍5319ee26/two assurance WIP，FF远端main仍d4d2fac无并发推进；外线历史/owner/Dayu/ET未改。MAIN验收说明保存FF新MAIN_ACCEPTANCE，不覆盖原handoff；现有一个Ubuntu CI仅加入短生命周期与legacy限额用例，实际POSIX待精确远端CI验证，不加矩阵/日常大E2E。

- 正常FF commit被既有host-assumption静态门拒绝：Linux procfs PID状态（/proc/）被当机器路径，真实中微固定内容SHA未登记。Ruff/mypy均绿；没有提交/push。按已有门的具体登记机制写明理由：procfs仅Linux分支、文件存在才读且用于区分已终止zombie；内容SHA由用户明确原件固定、CLI输入路径不固定。没有拼接路径绕过、删除验证或改三仓vendored检查器。

- 正常commit/pre-push GREEN，FF58568e70cae3c275da9df47a96a49b74a6b13770已推origin/main（d4d2fac→58568e7非强制快进，包含完整外包历史）。独立树pre-push三仓doctor因无RF同级目录明确SKIP，未伪称执行；远端单Ubuntu job需实际验证。gh缺失只读失败，改公开API查精确CI。原owner仍d4d2fac、dirty测试SHA保持24f3a727…与交付一致；RF外线有源准备/相关测试WIP，无HANDOFF，未碰。

- 精确CI37384744223 attempt1 failure：Ubuntu mypy在原生Windows错误构造的5处识别WinError/get_last_error不可用（10 attr-defined），不是进程行为红灯；测试步骤尚未运行。用Git既有凭证仅内存读取具体日志，未输出/落盘secret。Windows本地mypy平台不同，解释了同一工具本地绿、CI红；把既有单mypy目标固定linux以对齐CI，不新增commit测试。用sys.platform守卫集中Windows错误构造，另手动两个type platform核验。Linux外层watchdog自身session不能包含生产新session，记录本调用自建PGID供watchdog回收，不扫描其他进程；Windowsjob保护不变。原CI不盲rerun，修具体代码后新SHA发布。

- FF修正已正常提交/推main758e8f4c116ef9760c657433e4ccbfbd10652029；local linux/win32类型均GREEN，两个具体生命周期case2 passed/1.73s、ffmcifix恢复absent。CI37385101051 attempt1开始。
- FF owner唯一dirty测试再次核24f3a727…，与已提交integration文件字节相同；正规restore该文件后switch main，再--ff-only到758e8f4，最终该测试SHA仍原样。此前local main实际停在c9799b7（owner fcap才是d4d2fac），本次同时补齐66份已有commits，未rebase/reset/force。现在本地main和remote main一致，tracked干净，仅FMP_API_KEY.txt未跟踪并未读/暂存。真实owner目录三仓config_doctor --require-revenue-config GREEN，不再依赖独立树skip结论。

- FF精确CI37385101051/758e8f4 attempt1 completed/success，所有步骤GREEN，含新POSIX生命周期责任包、原精选回归、三仓doctor。前次失败未重跑；正常新SHA修复通过。所有10个本轮ffm测试根逐一Test-Path=false；原用户配置仍3609e707…，e570daf确认在CWP主线。一次rg整个tmp遇到其他历史受限目录，仅只读失败，随后只检查本次确切根，不清他人目录。FF accepted_main收据与总PWF/并行包/预验收历史状态同步；STORAGE已验收状态不重做，生产0删除。下一步剩余旧generator caller及RF交付验收，不新增权限门。

### S5生成器边界节点收口（b148123，CI待核）

- 10项TDD初跑9 failed/1 passed、4.99s；修复后65项入口/指纹/读链25.10s GREEN，兼容包160 passed/2 skipped、121.50s，新Worker双语言/policy与存储smoke 3 passed、25.45s。新增stdout案例1项RED后，解析/指纹31 passed、80.12s。229个不同case分步GREEN，并非单次229项全包；两项跳过来自已有夹具，不冒称已验证。一次命令选错不存在的test name为选择错误，未当产品RED。
- 旧全文generator/正文reader移到tests/support/legacy_catalog，normalizer仍独占临时原文格式解析/指纹。运行层减少2182行；343份tracked生产Python无test-support导入。历史generator metadata仍为读兼容保留，不等于生产writer。
- 真实年报副本初跑与有限诊断复跑均在JSON协议处失败：PyMuPDF安装建议污染stdout，实际report completed=2。未放宽JSON；真实子进程Python/native输出TDD复现，生产child诊断统一stderr。最后实际scan/backfill/重复backfill GREEN：AMEC 9165875B及MSFT 66324B原SHA不变，sources/documents/locations事实不变，0artifact/span/derived，最终tmp/s5g-oa0wgnpp恢复absent；0外部LLM/download、0生产删除。
- 已正常commit/push b148123d1ada7d0d222574b6b5852f976c2985e8，静态commit与快速pre-push GREEN；用户配置SHA原样。精确CI37388329668进行中，待核结果后发纯PWF收尾。RF仍无HANDOFF，不碰WIP，下一步接收RF或生产只读预览。

- S5生成器节点最终收口：精确代码b148123/CI37388329668 attempt1 completed/success，全部步骤GREEN，无rerun。本节点所有s5g*测试根已恢复absent；源配置原SHA保持。MAIN下一动作为RF默认迁移验收，未交付时仅做生产只读预览；0生产删除。代码CI以b148123为准，纯PWF [skip ci]收尾不替换该收据。

## 2026-10-06 — P5-RF默认链与短CI主线节点

- 稀疏树展开后新默认/真实CLI11 passed、1旧evaluate_review失败，18.27s。TDD短CI先2 RED/1旧opt-in skip，3.72s，修改后5 passed/0.92s。集中来源/核心计算107 passed、1新schema夹具误用source_id失败，16.10s；改primary_source_id后唯一失败及相关5 passed/7.23s，共108不同case分步GREEN。
- 补强删除E2E的空目录假设：在真实catalog_dir/derived先创建三份旧文件和artifact行，实际删除后默认CLI仍raw-only。固定真实AMEC年报公开RF CLI三次成功+篡改一次拒绝，来源事实不变、原SHA不变、三文件/行删除仅在fixture、测试根恢复、0外部调用。
- RF b110502f已正常推main；pre-commit静态与pre-push同CI精选107 passed/19.74s，保留原owner周日志SHA和rf-impl 242份WIP摘要。CI37391276302确认live，停留checkout未执行测试；未称CI绿。
- root量化RF .planning47079、assurance1392、scripts51/tests151跟踪文件；新ca67eab7把daily checkout限定责任代码/配置（官方checkout文档验证），不删历史原件/记录。107 passed/18.17s正常push gate绿，首次推送GitHub remote500，复核远端后正常重试同commit；不是代码RED或盲CI rerun。
- 默认E2E无env不skip，current pins为published FF758e8f4/CWP2145661；旧workflow byte签名专属测试退出默认收集，Gitrevision保留。每天一Ubuntu、一个pytest、无全量coverage第二遍/Windows历史审计/安装同步/生产库门/人工签收。
- 只读S5真实inventory已启动，等待实际清单；无生产删除/span prune/VACUUM。模型预算问题仍独立，不阻本节点。

## 2026-10-06 — RF实际发布与部署闭环

- ca67eab7正常推main，GitHub CI37391526925 attempt1全部步骤completed/success，单job32秒，checkout1秒、安装7秒、兄弟仓7秒、共享检查11秒。107项本地pre-push19.12秒。未把缓存jobs null当全绿；加fresh query后核完整步骤。
- RF正式root已切main与远端同SHA；fcap祖先校验exit0。旧rf-impl只更名分支，242条status和1704098B staged diff的SHA完全不变；owner两weekly日志SHA未变。三处installed source_preparation实读都为19e329c5…，无需额外安装改写；sandbox拒绝读不能当副本不存在。
- 正式完整收据p5_rf_main_acceptance_2026-10-06.json。S5只读inventory session30784仍confirmed live，未删除生产derived/spans或压缩DB；随后按实际parser/引用清单推进。

## 2026-10-06 — 存储范围与安装依赖补核

- 实读readonly/immutable库聚合：db3055841280B，新narrative versions0；legacy spans1490530，parser/version为antiword1.0.0=16、dayu_docling1.10.0=6230、html_markdownify1.0.0=6、openpyxl3.1.5=22、pdf_page_aware_core1.26.7=1479827、plain_text1.0.0=4040、python_docx1.0.0=28、structured_text1.0.0=361。这里只聚合，不删除，不把页数变化伪称释放空间。
- installed入口SHA一致不能证明整个package一致。进一步实读72份生产代码/config/schema/SKILL，发现每个独立安装7项滞后（research coverage/drivers及5份schema说明）；仅同步这14份已发布文件到agents/codex，claude是agents别名，随后全部72逐字节一致。安装config/output未变；正式receipt修正“无安装写入”的先前局部观察，记录实际部署。
- inventory session30784仍live；源码证实正在做单次旧文件SHA、百万legacy表流式摘要和完整性，不写production DB/原件。观察超时不重启。下一存储选择须覆盖明确旧parser，并保留实际refs/unknown表，不凭这份计数立即删。

## 2026-10-06 — 生产inventory完成、修正下一施工点

- session30784已terminal exit0/succeeded；manifest5588419B保存tmp/s5-storage-20261006/manifest.json供恢复处置，不把一次性大清单纳入Git。小型preflight正式JSON只列聚合与缺口。原件/生产库未修改。
- 新生产反例：1712 excluded含1477个直接parser旧行，全部同document_id/同候选路径，814 hash相同、663旧hash失配；另235个空generator/version summary。当前工具只退休候选row后unlink会留下共享路径旧handle。candidate_bytes还因managed成员重合高于physical derived；不能立即apply或按行总和报空间收益。
- 下一大节点明确TDD共享路径原子退休/未知现代alias拒绝/空标签旧summary判据/物理路径计量。具体步骤已写S5/S6细则，不多加小节点门、不重新盘点全legacy表，不执行整库恢复演练。
- RF收尾6e6b817a已正常提交推送，本地main同步；精确代码ca67eab7的CI37391526925保持全绿，纯文档未另触发长CI。两周日志SHA再次相同。目标active，尚未完成生产清理与N4C真实模型批次。

## 2026-10-06 — P5-FF / P5-STORAGE 交付复核

- 用户再次通知交付；核对现有正式收据，确认是已验收并发布的同一交付，无需重派或重跑已绿大包。
- 本次直接读取 GitHub 公共 Actions API：FF 37385101051 对应758e8f4、STORAGE 37375836745 对应e570daf，均 completed/success、attempt1。git ls-remote确认FF main758e8f4与本地一致，CWP master c46560a与本地一致且包含e570daf。
- 保持两卡 accepted/published_green；生产清理仍未执行。下一动作仍为共享路径退休与物理字节去重TDD修复，覆盖1477条同路径旧handle；不将工具验收等同生产空间释放。用户source_acquisition改动与未跟踪FMP密钥未读写/暂存。
- 复核工具错误：gh未在PATH，改公共REST API成功；rg通配符路径在Windows无效，改用已知文件；一次空标题patch未匹配且未产生写入，改为明确日志追加。没有重复失败或新增人工门。

## 2026-10-06 — 共享路径实际TDD开工

- 上一交付复核未推进产品实现；本轮转入可执行下一动作。RF仍main/origin main6e6b817a，仅owner原两周日志dirty，本线零写RF。
- 新真实schema小夹具责任包12 collected，12 RED/22.73s；11项证实同路径handle未同步退休、未知/active/跨document共享引用可被删、事务快照后新增alias未阻止物理删除、重复字节累计及空标签summary不识别。1项测试夹具给不存在source_id违反外键，改为另一个已存在来源，保持拒绝跨来源要求。
- CodeGraph未覆盖tools旧清理模块，返回来源类入口；沿已知工具文件检查。历史0254847 parser metadata/summary.md布局及生产exact parser版本提供窄识别依据。实现已开始；不自动放开unknown，不写生产库，不重建旧转换。短根s5sharedred已finally恢复absent。
- 新增切片成员与独立记录重合、未知index传递阻断、未选index子文件保护、direct parser及空标签summary实际退休；最终存储集中节点49 passed/87.25s，Ruff和git diff --check GREEN。s5sharedred/green/node均恢复absent，user config SHA保持，生产0删除。收据s5_shared_path_acceptance_2026-10-06.json已写；准备正常发布，不增加日常慢CI。
- 代码96f44a14127b40d97d00f30fa7ebbb183d94064a已正常commit/push，pre-commit与pre-push GREEN。GitHub精确CI37394193179 attempt1 completed/success，全部job成功（75秒）；不是未提交候选或旧SHA重跑。
- 原manifest保留，tmp/s5-storage-20261006/preview_shared_scope.py按已识别范围补充空标签summary并按实际唯一物理路径计量。修正manifest已写，生产readonly retire-derived preview session56274 confirmed live；0生产删除，等待同一handle，不因观察超时重启。
- 生产preview session56274 terminal exit0/succeeded：补235空标签summary，6714候选记录/7072唯一文件/2825969544 B，8191退休handle含1477共享alias，excluded0；来源17表/新final/配置SHA均保持。旧manifest与修正manifest都保留供恢复。独立只读SQL证实共享document/source冲突0，新final0，其他表没有span/locator列引用，保持来源事实全部不变。
- 已启动已授权实际S5/S6节点execute_storage_node.py：先四份公开原文CLI字节核验和17表小型source-only checkpoint；再retire、8类明确旧parser范围prune、VACUUM、同四份原文与事实校验。不完整备份3GB库/恢复演练，不调用模型/下载。只在成功小收据写出后清理临时操作材料；失败保留恢复点。
- 修正前日志通配路径又一次只读rg错误，已改精确文件列表；不再使用Windows rg字面通配路径。
- 第一次实际节点exit1，在before原文CLI遇capture_incomplete；尚未创建checkpoint/retire/prune/VACUUM，生产零删除。原因是施工脚本省略purpose导致default filing_reuse，四份历史原文有缺公开日期的资料；本存储验收应为已有preview模式的原字节可读，不应伪报财报复用资格。核当前reader后显式--purpose preview再执行，保持财报身份/期次/公开日校验和原SHA断言，不修改产品门禁或生产来源字段。
- 修正preview目的后的实际节点session15696 confirmed live，production.before已ready：同四份raw公开stdout SHA/size通过，17表source-only checkpoint161251328 B（不包含artifacts/evidence全文或原件），checkpoint事实digest与当前17表一致。进入retire执行；尚未终态前不声称生产释放字节，恢复清单/checkpoint/分阶段报告保留。
- production.retire已succeeded：实际删除7072文件2825969544 B，derived2826010634→41090 B；8191旧handle退休，1477共享alias闭合；excluded0，source facts17表完全一致，新final0→0、integrity ok。当前session15696继续prune/VACUUM，不把freelist变化报为物理释放。来源恢复点与大操作材料仍保留；终态前不写总体成功。
- 顺手强化N4实施卡顶部交接：纠正旧run02余额/旧MiMo Pro/DeepSeek401历史恢复点，引用实际flash配置GET200与run04保守账；160k/$0.10授权问题尚待答复、旧未知账不退，不能依据旧段落重跑或更改参数。读tmp全路径遇旧cw-retire-r1 ACL仅只读失败，后续改精确已知报告路径。

## 2026-10-06 — S5生产清理/来源库物理降容完成

- 实际节点session15696 terminal exit0/succeeded：8个明确parser/version共1490530旧span全部删除，当前span0/可消费legacy artifact0；8191旧handle均retired。原件0删除，17表source facts的count/digest逐表完全一致，FK空/完整性ok，四份公开原文preview stdout SHA/size前后相同；中微2025年报/微软Q4 FY2026 TXT固定SHA另实读匹配。RF/FF/ET/Dayu源码零写，本地user config SHA不变。
- 主retire7072文件2825969544 B，剩32文件41090 B逐个实读证实21 structured_text normalized+11旧LLM summary，都是侧车元数据的无registered handle缓存；在同一catalog锁下按精确SHA/header角色/源SHA目录、非locations原件、无artifact引用再次核实后unlink。最终derived7104文件2826010634 B全清零，4240空目录只rmdir；没有泛扫未知对象。
- DB退休前3055841280 B，退休metadata更新后/压缩前3059736576 B，最终222408704 B。VACUUM阶段减2837327872 B，但整个节点DB净减2833432576 B；加旧文件后净减5659443210 B（5.659GB/5.271GiB），不使用更大的压缩前基线多报收益。
- 正式小收据s5_production_storage_acceptance_2026-10-06.json保存原文/来源事实/8类计数/实际净空间与代码CI，10KB级；验证成功后按绝对路径/reparse检查清除唯一tmp/s5-storage-20261006，操作恢复点/清单/大报告/脚本186486185 B移除，目录恢复absent。临时材料清理不额外加进5.659GB净释放，未做完整3GB/46GB备份或恢复演练。
- S5标complete；S6库收缩完成，剩当前docs/hook兼容引用核销再回N4C。49集中责任测试/96f44a1精确CI37394193179一次全绿复用，不新增小节点验收或日常慢CI；N4C累计预算问题仍独立等待，目标保持active，未宣称真实多provider批次已完成。

## 2026-10-06 — SUMMARY_INVALID诊断与prompt精简集中节点

- 本轮先核RF main/origin main6e6b817a，仅原owner两周日志dirty；零写RF/FF/ET/Dayu。用户source_acquisition SHA3609e707保持并排除提交。
- 旧MiMo招股响应已随隔离根清理，不能推断具体失败规则。新增只输出固定rule标签的安全诊断，错误source/language/role/fields/quality仍终态拒绝，不留provider未知键或正文。8项TDD RED，相关71项GREEN。
- 1项prompt投影TDD RED后实现私有prompt1.4.0/request1.2：完整严格schema只传一次，移除重复示例/constraints及模型无需的辅助计数；160段原文、角色、flags、alias、canonical selection/locator全保留，完整selection仍参与输入hash。实测body16525→15479 B、保守预留24845→23799，旧账仍136108tokens/63228microUSD，剩23892/费用34008microUSD。配置8192/温度1.0/端点和估算法不变。
- 146相关Unit/5.35s、Ruff、mypy2文件GREEN。正式CLI/HTTP、跨run及kill恢复首轮13 passed/1 failed/79.41s；唯一过期断言读constraints.translate，改查真实HTTP No translation且最终bundle仍验translate=false，单项1 passed/10.73s。14项分两次全过，不伪称整包单次全绿，不再重跑79秒已绿范围。
- 六个明确测试根绝对路径/无reparse检查后恢复absent；固定旧unknown账本不动。小收据n4c_prompt_node_2026-10-06.json与两份零POST请求测量已落盘；正常发布后仅MiMo P04+policy复测一次，不盲循环或自增预算。
- 一次PWF补丁因假定progress标题为# Progress未匹配而拒绝，未产生该次写入；改精确N4段落和追加日志。没有修改产品要求或增加小节点门。

## 2026-10-06 — run07真实超时与客户端边界调查

- 唯一新MiMo P04+policy复测终态budget_exhausted，batch127.140s/总131.382s；MODEL_TIMEOUT attempt61秒、随后MODEL_BUDGET_DENIED在外发前终态拒绝。实际POST1、unknown1/unsettled0、保守23799tokens/5332microUSD，累计159907tokens/68560microUSD、unknown7；扣历史FX2764后费用剩28676microUSD，tokens仅93。没有合法P04 final、没有新SUMMARY_INVALID，不能声称诊断修复解决了旧合同失败。policy仍skip/0model/RF read0，所有protected checks true，短根恢复absent。
- HTTP adapter、batch model defaults及旧LLMClient均为60秒；配置LLMConfig没有timeout字段，当前configured wrapper投影保持该既有默认。61秒终态与此一致，但没有分阶段header/body证据，不能断言供应商算力、队列、网络或thinking哪一个导致耗时。没有擅改timeout/stream/thinking或模型配置。
- MiMo官方API Integration FAQ（2026-10-06读取，更新2026-09-20）建议合理连接/读取超时、指数退避，长响应使用stream；速度还受请求复杂度、服务负载/地域与stream影响。来源：https://mimo.mi.com/docs/en-US/quick-start/faq/api-integration 。这是后续传输策略设计依据，不是本次超时根因证据；未采用第三方论坛推论、未偷偷增加paid calls或provider fallback。
- 当前既定token cap不允许任何8192输出预留。已向用户提出累计200000tokens+$0.10不变、P04同一精选片段明确外发DeepSeek的单次方案，待答期间零POST。旧unknown不退，现有三类型成功保留。891dd41精确CI37506642500 attempt1全部job/步骤GREEN，单job83秒，正式小CI收据已保存。
- 只读观察先误用jobs.state列，PRAGMA核实际status后修正；两份猜测计划文件及两份猜测模块不存在，已改已知具体文件/rg --files；一次rg字面*.py在Windows失败，后续统一目录+-g过滤。这些读取错误不改生产或放松产品校验。

## 2026-10-06 — run08招股成功与英文经营业务修复节点

- 用户明确授权累计200000tokens/$0.10与P04→DeepSeek后，run08完成：batch83.159s、峰值RSS481517568 B、隔离根峰值12576222 B；10480tokens/10397microUSD、unknown0。招股25claims/160locators、238766 B final、RF read0/verified、原语言不翻译；policy skip/0model，全部保护与目录恢复通过。累计170387tokens/78957microUSD，历史unknown7/unsettled0保留，余29613tokens/扣FX后18279microUSD。
- 读T01真实摘要发现14claims中9条分析师问题，管理层五条多为泛述；原文六类重要经营更新漏选，形式上四类型链绿不代表实际业务效果合格。根因是英语规则识别范围过窄；动作+经营对象、当前采用数量、交付时间、商业模式变化缺失，不能靠品牌词和财务增长扩大召回。
- 新正例先8 RED，再补充效率/席位/商业模式4 RED；实现selector0.3.2，parser0.1.0不变。新23＋原通用46项69 passed/2.84s。检查原英文23项发现1条收入句中的customers补语误召回，增加句中非财务主语条件，新/旧英文46项passed/1.58s。总92个不同case分步通过，Ruff/mypy绿；不伪称全部单包一次绿，不重跑既绿的长E6/storage包。
- T01只读对比f264609：原14段/1809 B（管理层6）→46段/6852 B（管理层35），新数据中心、模型、Fabric采用、GPU交付效率、Copilot席位、seat+usage六个管理层原文点均选中，46/46引用回放。第一版测量误把实际“paid Fabric customers”写成“paid customers”，两次断言失败后逐字读原文修正测量短语；没有调整生产规则迎合品牌。runpy首次导入support失败已补tests到sys.path，均零POST、不改原件。
- 按Config DeepSeek测量body10228 B、保守18548tokens/14376microUSD，在批准余量内。小收据n4c_english_selection及n4c_english_node落盘，无原文/请求大副本；下一正常发布/精确CI后只复测同一T01＋零模型policy一次。用户source_acquisition与RF owner不动，N5独立写集保持。

## 2026-10-06 — 电话会截断、短摘要目标与费用恢复点

- 英文选材代码27d51d5已正常提交/推送，精确CI37510236806 attempt1全部job/步骤success，72秒，小CI收据落盘。RF正常账号HEAD/origin/main/live main仍6e6b817a，owner两文件与用户配置SHA保持。
- run09单次T01+policy真实DeepSeek：batch36.024s/总40.269s，finish_reason=length、input2305/output8192，MODEL_OUTPUT_TRUNCATED终态拒绝发布。已知10497tokens/11692microUSD；policy skip/0model/RF read0，全部保护检查通过，根恢复absent。累计180884tokens/90649microUSD，unknown7/unsettled0，余19116tokens/扣FX后6587microUSD。未把failed/legacy blocked_human当新人工门，未丢usage或把截断算成功。
- 原prompt无输出长度目标，更多业务证据可能诱发逐段膨胀。DeepSeek官方当前pricing/model页明确Flash默认thinking（https://api-docs.deepseek.com/quick_start/pricing/），但run09未保留reasoning/content分项，只能确认总输出8192/length；两次thinking-guide页面读取timeout，精确站内搜索无结果，不猜测具体推理耗时。
- 按实施卡先2 RED/6 passed，再实现私有prompt1.5的20条/280字符/8alias目标及管理层优先、去重，不裁选材、不改公共reader与配置。相关59项Unit/4.17s、现有双语言正式CLI E2E2项/24.07s、Ruff/mypy GREEN。第一次测试命令猜了不存在的model_decode.py（0tests），只读命令也误读不存在model.py并使用Windows不展开的glob；随后按真实文件列表改model_aliases.py，不以文件不存在冒充测试绿。
- 新零POST真实请求10435 B，预留18755tokens/14445microUSD；token足够但费用不足。已向用户提出累计费用$0.12、同一T01→DeepSeek单次复测，token200k/Config8192/温度1.0和全部旧费不变；截至本记录答复未到，不增加paid calls。短摘要目标本地完成不等于真实业务摘要已完成，目标保持active。两份节点/请求小收据、run09和CI更新PWF，正常提交发布。

- 最终发布复核：短摘要代码4d019b5435b8b277c059f6d4abbe62cc09f684f3与origin/master一致，正常commit/pre-push GREEN；精确CI37511515796 attempt1所有job/步骤success，76秒，小收据与节点状态已更新。仅用户source_acquisition.yaml仍dirty，SHA3609e707保持；其他仓零写。run08/run09/本轮11个明确测试根全部恢复absent；N4本轮小收据总计约0.2MB，不留大正文/请求/无效响应。累计费用$0.12答复仍未到，未提高执行cap、未再POST，目标active且唯一Next Step明确。

## 2026-10-06 — 自动续跑：旧长草案读取兼容与完成证据核对

- 前一goal turn为实质进展（两次代码发布及精确CI、run08/09真实证据、prompt修复），非无进展等待。本轮重新实读CWP master/origin master b32cc2e；RF HEAD/origin/main6e6b817a仅原owner两文件dirty、三份保护SHA保持。$0.12费用答复尚未到，无live模型任务，未重启run09或提高执行cap。
- 具体未直接验证的承诺是私有输出目标不能使public reader拒绝旧长草案；新增一个integration case，25个真实临时原文段落、25条>280字符的模拟旧prompt1.4草案，真实artifact prepare/activate及public transport原字节读取、完整引用回放/原件不变通过，1 passed/3.09s、Ruff绿。首轮StopIteration来自夹具把多句当完整span，改单句夹具、不改解析/产品代码；不算TDD产品RED。两个独立根已恢复absent，0POST/0生产写入，收据明确合成兼容证据，不冒充真实模型效果。
- 完成核对仍仅N4C业务效果待实测。修正task_plan的160k历史授权段与S4表中陈旧的“待发布/待CI”，唯一Next Step保持费用答复后同一T01一次，已绿长包不再重跑。N5三卡未收交付、不代写外线。目标保持active；此轮有具体兼容证据及已提交测试进展，未达到真正无可推进的三轮blocked阈值。

- 发布结果：86c8793901f9254e922cadf00fda9bf120156df8已推origin/master，正常pre-commit/pre-push绿；精确CI37512605771 attempt1全部job/steps success/75秒。新增兼容integration case本地1 passed，日常CI不重复这项integration，仅运行既有Unit/短contract/compile等，收据明确区分范围。费用答复仍未到，本轮新POST0，目标未完成；保护配置SHA及RF owner保持。

## 2026-10-06 — 当前计划收敛与显式预算准备修复

- 前一用户状态答复没有改变权威状态，本轮继续核查后发现真实交接风险：task_plan仍有已完成S3/S5的“下一步”、旧施工卡和160k/60k恢复段。总计划现只保当前恢复点、S0–S6状态、资源/职责、N5外线、唯一Next Step；旧全文以已发布659bcefc Git链接保留，不丢技术记录、不产生新签收。
- 正常用户只读复核CWP HEAD659bcefc、RF HEAD/cached main6e6b817a，RF tracked dirty仅两weekly日志；sandbox首次status出现大量假删除/ACL警告，未作清理，正常用户复核排除。CWP用户source_acquisition SHA3609e707保持。
- 发现离线preflight仍写死60000 tokens/$0.10，当前累计180884会误报余额。公开CLI现要求显式--campaign-token-cap和--campaign-cost-cap-micro-usd，计算复用原prior_budget，不改原账/模型/生产配置。报告schema /2并说明configured-output bool只评估输出token，不表示完整费用请求可行。
- 新责任测试第一轮3 RED/2 PASS，两个CLI case是未知flag引发exit2的假通过；强化错误原因断言后5 RED/1.96s，修复后5 passed/0.70s、Ruff和diff check GREEN。120000费用仅测试假设，不是实际授权；未扩大日常CI矩阵。
- 实际零网络CLI按已批准200000/100000运行exit0：四份真实raw指纹、RF已提交六模块help、配置/生产/owner保持、短根恢复absent均true；旧账仍180884/90649，unknown7/unsettled0，FX2764后剩19116 tokens/6587microUSD。小收据n4c_explicit_limits_preflight_2026-10-06.json，provider/model/download均0。
- 累计$0.12仍待答，run10未启动，S4不标complete。此轮有具体工具修复与真实离线证据，目标保持active；不重跑已绿长测、不代做N5、不写RF/IQS/Dayu/StockWiki owner树。完成代码后正常commit/push与精确CI。

- 收尾检查发现task_plan多余EOF空行，已去掉；实际code/doc差异仅本线。离线收据全部保护true/零外发，计划所有本地链接存在。旧run与费用历史保留。

- 发布：4826ad9c67bce3d3e2b977173d283341d18bc141已推origin/master，正常pre-commit/pre-push GREEN；CI37514053091 attempt1全部job/step success，52秒，精确小收据已保存。当前总计划215→93行、45067→11142字节（发布状态行更新前），所有历史全文保留659bcefc链接。唯一未提交仍用户config，SHA不变；run10 receipt absent、0新POST，累计费用提高未获答。

## 2026-10-06 — 核心收尾阻塞复核与N5实际材料

- 上一goal turn是progress：显式预算工具修复、五项TDD、真实零网络preflight及4826ad9精确CI52秒绿色；1b8c54c收尾已推远端。此轮不重复已绿包、不启动费用不足的请求。
- 正常用户fresh CWP HEAD/cached master1b8c54c，仅用户config dirty且固定SHA保持；RF HEAD/cached main6e6b817a仅两weekly owner文件。prior_budget实际仍180884 tokens/90649microUSD、unknown7/unsettled0；余19116/6587，既有prompt1.5请求预留18755/14445。当前真实费用阻塞没有消失，run10 receipt absent，没有可等待的live模型/CI句柄。
- 新发现：三份N5实际工作树已存在。DOCSET基线e46108b、未提交本线PWF/benchmarks；RAW-DUP同基线、未提交本线PWF/tools；ET从63c4090推进到96c9bc8代码commit、当前干净，三者都缺指定HANDOFF.md/handoff.json，未达到交付，不提前验收/合入或修改owner代码。早先仅-uno看不到CWP两包新目录，已补正常untracked只读状态；一次PowerShell混合对象表格隐藏目录字段，改JSON确认。没有依据声称已确认live进程。
- RAW-DUP的工作进度里出现metadata候选逻辑重复上界约7.44GiB、1007云占位文件；尚未提供本卡真实字节复核报告，不能称已确认重复收益，更不能删原件或触发云hydrate。本线净释放数字仍取S5实际收据，不加此估计。
- 核心阻塞审计：同一$0.12费用未答在短摘要修复后、历史草案兼容验收后、显式额度修复后及本轮连续存在，已超过三goal turn；期间有独立进展，但现在所有不依赖该答复的核心工作已完成，N5没有完整交付可接收。无法以离线/Replay冒充剩余真实效果，不擅改配置/降低证据/退款unknown来绕费用。本轮记录外线实际状态后，主线达到blocked条件；不是整体complete或用户requested pause。外线保持独立，费用答复或完整交付到达后恢复对应工作。
# 2026-10-06 — 用户费用批准、run10与ET-TXT实际收口

1. 人类对累计$0.12回复“批准”，目标active；唯一run10按Config执行T01 DeepSeek+零模型policy。终态succeeded：20 claims/46 locators/15管理层陈述/5问题，RF reference/read0、replay verified、English/translate=false，99479 B final；batch35.217s/总42.828s，原件/生产/user config/RF owner全部checks true，tmp/n4live05x10恢复absent。没有新unknown，本次9151tokens/9853microUSD；累计190035/100502，历史unknown7/FX2764保持。正式小收据n4c_live_2026-10-05_run10.json。
2. 零POST独立复核真实claims。首轮原TXT直接decode与生产material规范化不同，span IDs断言红；复用生产extract_transcript_material+verify后ID/角色绑定全部通过，6类主题精选覆盖6/6、短摘要5/6，GPU效率未单列。业务收据n4c_live_business_review_2026-10-06.json记录非穷尽边界、原件保护和当前余额9965tokens/16734microUSD；旧run06实数8问题/6管理层，纠正历史粗读9/5，不改旧收据。
3. 收到N5-ET-TXT完整交接，读取卡/PWF/HANDOFF/Git差异，public wire/goldens零改；正常用户责任包92 passed/26.24s，10 goldens matched、相关Ruff绿。只重复3个受影响文件，未重跑外线234项已绿全包。ET worktree/tmp/n5accept恢复absent，0真实HTTP/LLM/下载。
4. ET首次真实只读audit脚本路径键KeyError，finally清理；编排没在exit1后中断，main快进/推送先发生。修改脚本相对路径as_posix后，在已经合入的正式main实际audit通过：43 TXT全legacy_unverified，原件SHA/size/mtime、ET配置SHA保持，0写收据，tmp/n5etread恢复absent。独立spot MSFT Q1 2025为60363 B/SHA ac1cc6170dcfaa68e586dfcdc6c5bf2e4de05cc0bfb7836013c37cc60eb701ae。依赖修改以后显式检查退出码，不能把失败前命令拼接当成功。
5. ET local main/真实远端main均2b9fb84660f98ce27a05709a7e31342ab044b4d2，代码96c9bc8包含其中；只保留owner .workbuddy-ai/、eval_results.json。正式n5_et_text_main_acceptance_2026-10-06.json说明green为MAIN责任测试/goldens/Ruff，不冒称无workflow仓库远端CI已绿。
6. 更新当前task_plan、完成证据、N4恢复细则、并行总计划/N5总包/ET卡与findings/progress，S4有限样本complete、S0–S6核心收口；N5-DOCSET/RAW-DUP未完整交付，整体目标active。当前代码CI4826ad9/37514053091已一次全绿52秒，纯文档与收据复用此代码证明，不新增慢测试或小节点门。本记录随本轮文档/小收据正常commit/push；精确文档提交由git log检索，不暂存用户config。发布前diff --check发现两日志末尾空行，已清除，单独检查退出0后才提交。

## 2026-10-06 — R6局部摘要容错集中节点与RAW-DUP交接

完成审计发现R6已采纳要求未实装，重新打开S4具体缺口并先写实施卡。TDD初30项17失败/13通过；严格JSON非有限数三反例先失败再修。私有模型adapter丢整条坏claim、忽略未消费扩展，保留好claim及其原引用/角色；全局身份/语言/显式translate仍拒绝，公共合同不放宽。partial用现行needs_review质量诊断，无人工许可。最终184责任测试/2.04秒、Ruff及两个模块mypy绿。

正式configured CLI离线E2E 1 passed/16.62秒，真实原件字节+隔离Acme元数据+loopback响应，Worker/outbox→public读/检索/exact→RF已提交consumer，46定位回放、同run无重复POST，原件/生产/配置/RF owner保护通过。两次E2E初红因测试config不在config/导致默认project-root不同；仅修fixture标准布局，RF零改。mypy两处schema类型红修显式注解。七个本线测试根核绝对路径/无reparse后恢复absent，0真实外发/费用。receipt r6_partial_summary_node_2026-10-06.json；代码发布CI尚待。

人类通知N5-RAW-DUP已交付，完整handoff与clean branch e40b4ec/a1418a0已读。只读产出约7.27GiB逻辑候选上界、3组158223532 B已实读潜在重复，deleted0；不计已释放。审查发现需验证物理allocated口径、硬字节上限、local-output与原件路径隔离，MAIN集中处理后才并线，不接管DOCSET。worktree无CodeGraph索引，用已知交接列出的模块读取；两次猜测文件名不存在已改实际模块名，不修改owner设置。

## 2026-10-06 — R6发布绿与N5-RAW-DUP集中接收

R6代码eae2dd4557491e6621ddbe73f972f01a841a8f00已推master，对应CI37521679387 attempt1 success、job59秒；S4具体缺口关闭。RF6e6b817a与用户config SHA3609e707保持。

RAW-DUP交付e40b4ec/a1418a0原包30项6.63秒绿，完整报告Git blob SHA/体积与真实数字核一致；metadata上界7804167537 B，3组实读158223532 B、读316447064 B、原件deleted0，3528组未实读。WindowsGetCompressedFileSizeW字段不是簇分配量，保留历史报告但主收据判该字段无效，当前工具null；不能算释放或CWP目录实际占用。所列510组497为CWP/Dropbox、11为CWP/Dayu、1三根、1仅CWP，未外推全量。暂不生产迁移/硬链接，不动外部项目与云原件。

MAIN同一集中节点TDD16初红/1绿，修双输出与未知旧文件保护、独占随机.tmp、非整块硬cap/精确EOF/partial账、云候选与读取前ID/path变化；再补2.69MB诊断反例/路径反例，原路径断言repr转义假绿修为精确静态标签后RED，实现列表截断+精确report_bytes/静态错误。最终51项/9.09秒含两实际CLI隔离联调、Ruff/diff绿，1生产长E2E明确deselected而非假报MAIN新live验证。保留外线已有生产实测收据，不重复150秒全测、不扩CI。

清理初轮Remove-Item非终止error导致exit0但四个ACL夹具仍在；后续逐项实际检查，icacls/remove与Set-Acl均AccessDenied。核自有tmp绝对路径后直接File.Delete四个测试新文件再Remove-Item，恢复absent；产品原件与系统ACL零修改。旧测试finally未检查恢复exit是根因，改PermissionError注入，最后rawclean目录正常清理。全部8个测试根恢复absent；以后清理用ErrorAction Stop且检查实际结果。一次文档大补丁误猜README标题被拒、原子未写，读取实际标题后重做；CodeGraph外worktree无索引，主图也无相关tools符号，按交接已知文件读取，不改索引/权限。

接收卡与JSON已写；下一完成merge/push精确CI，DOCSET保持独立。原始报告不改、不假称任何空间已释放。

RAW发布期间只读复核DOCSET工作树，发现完整交接已到且干净，HEAD2c3583e084a6fc632bd0970db02a439187214c0f、代码9ff251ec、已推独立分支，不再写待交付。旧selector0.3.1基准9原件/86golden/required11of33、712定位全回放，英文0of5/程序性IR0候选未skip/融资预算截断等需当前0.3.2对照，不能把旧报33%当现行效果或马上改预算。MAIN下一次集中验收基准代码/独立标注与parser scope，再一次零LLM当前主线实证；残留真实缺口先TDD修，不改golden凑绿，不自动加预算，不触碰外线或生产。整体目标仍active，RAW只读包完成不意味着文档质量任务全部完成。

RAW-DUP实际merge a41244a4994643551d314618146d0074fc4e6221已推master，git merge-base确认e40b4ec为祖先，ls-remote核master一致；CI37523080920 attempt1 completed/success、job57秒（19:59:56→20:00:53 UTC），主验收complete，小CI收据落盘。旧无nonce GET返回过时in_progress，jobs steps已全complete，再fresh query取得明确终态，不用缓存假报。只有用户config dirty且SHA3609e707保持，不改RF/Dayu/IQS；纯文档最终发布采用skip ci，不重复已绿代码测试。S7记录DOCSET待MAIN对照，整个目标仍active，不自动实施原件去重。

## 2026-10-06 — N5-DOCSET集中接收与真实主线对照

完整交接2c3583e已读，真实no-commit/no-ff merge已暂存。17路径写集仅本线工具/标注/交接，无运行时代码或生产写入。MAIN新增10反例先全RED，修运行HEAD、TXT字节/行双核、scope外标注、原件/未知输出路径、失败scratch、事后实字节SHA、peak双计与原子2MiB报告；原有22单测一起绿。标注辅助两覆盖反例再RED，改只写tmp新目录/失败清理，增加clean clone与成功路径证明。不同case合计43：一次39项/57.83秒含6 Integration、真实3PDF正式reader E2E271 locator；最终14 MAIN单测/1.10秒含新增4项，未虚报一次43项全跑。Ruff绿。

当前c8bf461c/selector0.3.2真实九类全表基准378.983秒，12/33 required、4/17 optional、744定位全回放、48重复、72042 B精选正文、76302 B runner scratch峰值。旧0.3.1报告11/33/golden不改；新报告另名、实际HEAD与源码SHA明确。noise2/25与136个in-scope未判定不能外推整体，情态0仅问句/陈述角色。读新报告首次误猜selected_noise键而KeyError，改读真实noise/duplicate字段，不当成功。

一次限定表页诊断21漏项：20 parsed完整，5 candidate完整但最终漏、1 candidate部分；唯一未parsed点为电话会marker前provider摘要。多数不是PDF识别失败或简单扩大cap能解决。S08实际页3有克重/一口价产品组合事实，程序性标签不能整份skip。已写S7细则，候选最小上下文→固定预算去重/排序→一次质量节点/正式Worker-RF E2E，0新模型，不改golden凑绿，不自动原件去重。

9原件、2配置、生产catalog、RF2 owner共14份SHA/size/mtime前后保持，RF6e6b817a；user config SHA3609e707保留，外仓零写。待最终清理自有测试根/local配置与实际merge/push、精确CI；工具接收不等于整体语义完成。人类随后要求新的独立施工包，MAIN在完成发布后按不同物理worktree与互斥写集拆N6，不重复已交N5、不接管IQS/Dayu。

## 2026-10-06 — DOCSET正式发布与N6三包准备

DOCSET实际merge58b74d07dd4f8b589c134ef9060a689864a8c089已推master，2c3583e为祖先，ls-remote一致，pre-push快合同GREEN；精确CI37528050044 attempt1全部job成功，75秒。7个本线测试根、临时local配置、辅助脚本/保护capsule与新增benchmark字节码恢复absent，原件0删除、user config SHA3609e707保持。前一文档复合补丁因卡首行只截半句原子拒写，随后用完整原行修正，未丢更新。

按人类新要求已准备N6-CANDIDATE、N6-BUDGET、N6-FOOTPRINT三张完整卡与三个独立物理worktree，全部固定已绿58b74d0。候选4文件/预算2文件/空间新目录互斥，独立测试夹具/PWF/handoff，MAIN拥有shared入口/版本/最终联调；三条ready但未宣称人类已分派或已开跑。候选接口设计经只读结构审查：QA不同角色绝不混组、NarrativeUnit无source_sha256属性、旧Rules可选默认值与MAIN注入职责明确。不改RF/IQS/Dayu/ET/StockWiki，不重派旧N5。

三树只取已跟踪代码文档，单树逻辑74490854 B、三树约223MB，共享Git历史/不复制ignored原件；验收后MAIN清理自己创建的worktree并先核需要ignored材料。新卡均有输入副本和PLAN_ID唯一PWF草稿。ROOT目标仍active，S7业务required12/33残缺；任务包ready不等于实现完成。FOOTPRINT只测本CWP占用与保留事实，不自动删/迁移/启动监控，不将跨根重复上界当已释放量。

N6启动PWF和INPUT_CARD已各自纯文档提交并推分支，工作树干净：候选81d4524、预算9495459、空间ec7a573，均以58b74d0为代码祖先；master卡/CI收据cc0c032也已推。不存在未提交的启动WIP，不需要harness重复建目录、拉最新main或reset。所有runtime代码仍原基线。

## 2026-10-06 — N6已分派与MAIN先行兼容/业务标准

用户明确三施工包已分派；ROOT总卡标已分派待交付，只读三worktree尚无新修改，不据此宣称存在live进程。上一目标回合是实际进展（DOCSET发布、独立PWF/card/branch推送），本回合继续MAIN独占材料，不跨写外线或RF。

先核RF main6e6b817a及其两owner日志、CWP user config SHA，与上一节点一致。发现旧isolated-pilot NarrativeEvidenceResolver重跑selector且限制版本；正式NarrativeTransportReader存完整EvidenceSpan，只重放原bytes，不存在相同耦合。未改旧pilot为第二canonical，不通过放宽ID/hash修它。路由只配置96/160/空结果策略，未候选前hard skip行政标题，不需要修改外线。

在代码ca6d9ce/selector0.3.2下，一次通过正式3 job/outbox与确定性本地模型生成TXT/JSON/PDF历史final；冻结3 JSON共17056 B，含README18247 B。新MAIN Integration最初9红均为夹具将catalog内部ID错比public URN，改成完整SourceRef对比后9绿，强化篡改前后成功读取/legacy spans0后最终9 passed/4.85秒、Ruff/diff绿；没有声称产品RED。模拟未来0.4.0且当前selector不可调用，旧bytes/IDs保持；新canonical group IDs产物同时合法读，旧reference仍pin旧bytes；等长raw篡改拒绝并恢复后成功。persistent文件无变化（SQLite SHM read marks除外），0网络/paid/生产写。

统一33个required业务解释表已写，原golden/86点/报告/分母零改：28经营点+1项目引句上下文，3纯财务金额/指引不独立作为业务摘要，1正文外provider摘要不冒充management。读原quote发现S07是境内收入占比约22%而非海外22%，更正ROOT候选卡/S7；S08历史2023产品克重口径、S06历史2016—2020进口替代也明确时间边界，不为模型/选择器凑绿。外线INPUT_CARD副本不写，最终MAIN核交付语义。

自有tmp/n6freeze、n6mct及两生成脚本均核绝对路径/无reparse/实际恢复absent；原测试fixture保留已存在keep文件。RF2 owner SHA和用户config SHA实测保持，Dayu/IQS/StockWiki/ET零写。查询曾猜不存在的pilot/reader/view模块名和Windows rg通配路径报错，改为已知正式模块/目录，不当产品缺陷或新增门。当前准备正常commit/push与精确CI；S7质量两线未交，完整目标active。

本轮实际发布0947cea63140d515620f563daf2058f4520cd6a3已推master，ls-remote一致，正常commit/pre-push绿。精确CI37532408169 attempt1全部步骤/job completed/success，job112504813892/80秒；9项新Integration只本地节点运行，不扩日常CI。CI收据先用PowerShell OrderedDictionary直接Select-Object打印null，文件内JSON实际字段完整；从保存文件反序列化后验证job ID/seconds/全部step结果，不能拿空打印作为证据。

已核NarrativeBatchRequest.input_hash确实包含selector/parser/prompt、build_batch_events纳入生成身份，narrative_select结果也绑定共享版本；最终两质量线合入后从新进程执行既有generation责任测试，不改历史read版本门。最后文档/收据用skip ci发布，用户config保持独立未提交；三外线原写集与INPUT_CARD副本不写。MAIN先行完成不等于S7整体质量完成。

## 2026-10-06 — MAIN业务E2E框架独立完成

三外包已由用户分派，MAIN不写外线六个模块/工具/独立PWF。RF main仍6e6b817a，新增daily_alert.jsonl owner改动与旧weekly/manifest一起保护，当前三份日志，不恢复。新增主线E2E细则先于实施；复用既有_prepare/_invoke/隔离目录/loopback/生产保护fixture和committed RF六模块导出，不复制任务库或修改生产模型配置。

首RED 1 failed/2.47秒为私有测试helper缺少timeout_seconds参数，零模型请求，非产品RED；加可选参数且默认60秒不变后1 passed/27.79秒。只读RF合同发现context投影不返回transcript_byte_bindings，且正式range是start/end对象；改成同ref从CWP正式read取原bundle，核artifact SHA/回放/evidence_spans与RF一致，再核原TXT quote字节/SHA/完整覆盖→material行。合成TXT实际走这个分支，最终1 passed/27.65秒，真实分支1 deselected，Ruff/diff绿。一次pytest关闭插件时出现既有asyncio_mode配置warning，不改全局设置去消除它。

三类合成原件/3次本地HTTP→configured Worker/outbox→RF reference/read→CWP search/exact→同run恢复，模型恢复0新增POST。真供应商请求/费用0；raw/config/catalog/RF owner指纹由fixture前后验证，用户config SHA3609e707保持。三个本线tmp根n6br/n6bp/n6bq核绝对路径/非reparse后用ErrorAction Stop清理并确认absent。查询曾误猜transport模块路径与CodeGraph参数，随后按实际结构定位和已提交合同核对；不当产品错误。

真实S01/S07/S09四经营点入口已写、明确待两质量线交付接线后执行，不拿合成绿当required12/33已改善，不再跑旧长基准/付费模型。当前准备正常commit/push/精确CI，整体S7/目标仍active。

实际提交13bba07f9e848fac4194b17313c4f4a608775a1c已推master且ls-remote一致；正常commit及pre-push快合同GREEN，用户配置由正常hook临时stash/restored并保持原SHA，未stage。精确CI37534879855 attempt1 completed/success，job112513173461全部step成功，21:34:50→21:36:04 UTC/74秒。此次代码CI仅执行原快集合，27.65秒合成E2E为本地大节点测试，未混作CI内测试。收据已转published_ci_passed；最终收据文档skip ci发布，不重复已绿代码CI。

## 2026-10-06 — MAIN实际批次的升级隔离

上一回合为progress：主线框架/收据已推并精确CI绿。本轮权威核CWP6b68b78、RF6e6b817a三owner、三外线仍bootstrap且干净；没有已确认live句柄，不记verified wait。MAIN不抢外线任务，先写执行升级实施卡，补旧artifact读取兼容以外的实际AUTO generation责任。

一份合成纯流程PDF，当前版本旧run完成后保存正式ref/字节/job/账；scratch版本bootstrap进入新Python及Worker子进程，仅模拟下一selector常量，不改实现。旧run/work-dir拒绝误复用且全部job/run账不变；新run ID/独立work-dir完成三新job、new artifact绑定模拟版本；旧ref仍旧字节，新run恢复不新增job。全部0 POST/tokens/费用，foreign jobs与raw/生产fixture保护保持。最终1 passed/16.33秒、Ruff/diff绿；三个先行红为测试DTO/规范化身份/Windows launcher入口问题（7.09/6.48/15.41秒），不宣称产品失败，不改SHA/身份或Worker生产代码。_invoke可选expected_run_id默认不变。

四个自有根tmp/n6uv/n6uw/n6ux/n6uy全部核绝对路径/非reparse，用ErrorAction Stop清理并实证absent；用户config SHA3609e707及RF三owner SHA保持。无生产原件/外仓/外线写入，不重复已绿长测或模型；实际质量12/33不变。main_completion_evidence中N5待交付/下一收N5的旧状态已纠正为三包完成、下一N6/S7，避免弱模型恢复旧队列；S7未来保护owner数更新三份。

当前准备正常commit/push/精确CI，最终实际版本接线与九样本/业务E2E仍待两线交付，整体目标active。

本节点实际55a55c291e77ae7a824240b2903f48bfcf63ef03已推master且ls-remote一致，正常commit/pre-push GREEN。精确CI37536310001 attempt1 completed/success、job112518036680全部step成功，21:47:17→21:48:11 UTC/54秒；16.33秒Integration为本地责任包，不在日常CI假称跑过。收据已published_ci_passed，最终纯文档发布skip ci避免重复运行。

## 2026-10-06 — 等待N6交付的依赖审计

55a55c2/f7500b7发布后MAIN独立准备完成。连续三个目标回合核同一依赖：三个本地/远端分支仍为bootstrap（81d4524/9495459/ec7a573），准确N6交接HANDOFF.md与handoff.json均不存在；没有可供共享接线/实际merge的交付。第三次空间线新增两份owner PWF改动，已只读理解，不能恢复/提交对方WIP，也不能据文件改动冒称已确认live进程或代码验收完成。候选/预算树仍干净。RF仍6e6b817a及三owner日志，CWP只有已知用户config dirty。

这三个回合没有MAIN实质实施进展，不将目录/状态查询算测试或新进展；未重复已绿长测、模型、源码备份或新增小节点门。询问实际施工目录/分支的问题仍待答，以防外线在其他位置交付。主线自动目标将标blocked等待外部交付，不暂停或取消外线，完整目标不缩减，当前质量仍12/33，禁止提前complete。

恢复入口：先核RF当前HEAD/owner和N6准确交付路径；收到任一完整交接就接收合法写集与已有责任测试，空间线可独立合入；两质量线齐备后候选→预算实际merge，MAIN按main_wiring共享接线/实际selector版本，再一次九样本、正式业务E2E、冻结兼容和升级隔离集中节点。无需重派、reset外线或重跑已绿付费试点。空间线交接时核known raw/staging的保留建议不会被tmp/cache路径覆盖，AUTO目录标记不会误覆盖整仓，报告不引入新的人工处置审批要求；当前只是owner计划风险提示，不冒称实现失败。

## 2026-10-06 — N6-FOOTPRINT MAIN验收

用户交付预算/空间两线；按新指示先收空间。budget首次暂存merge安全abort，外线零写，14个上下文/组ID/逆序反例已RED，待重新接线。预算最新交接18dbd0e，空间7f27f63均已提交；不要求补人工签收。

FOOTPRINT修正原件/staging优先、AUTO精确非根标记、有限deadline、显式根及父路径reparse保护、目录枚举期间deadline，以及报告内重复人工审批措辞。MAIN12反例RED后52项GREEN/7.70秒，含外线40项和CLI零正文读审计；Ruff/diff绿。枚举桩首次类型错误改成真实os.scandir迭代器后，旧实现访问100条才停的反例明确RED。详见[n6集中验收](n6_budget_footprint_main_acceptance.md)。

最终真实metadata扫描18.969秒，完整54298文件/逻辑24365900191 B；raw23462933638 B占96.2941%，tmp277935342 B+tmp DB45232912 B仅是323168254 B候选上界，不是实际可删/已释放。1007云占位跳过，allocated=null。旧报告保留，新报告与保护收据放harness_lanes/results/n6_footprint_main_*.json。五原件/DB metadata、用户配置/配置/RF三owner SHA一致。0原件正文/模型/下载/删除。

首次扫描脚本保护键拼错在扫描前失败，空scratch已清理；首次stdout编码不匹配但保存JSON合法，明确PYTHONUTF8后重测stdout/file对账且stderr空。自己的pytest-855/856和临时脚本已删除恢复absent，未碰并发owner的pytest-857。空间准备正常并线提交推送，日常CI没有加入新长套件，S7完整质量仍待候选线。

## 2026-10-06 — N6-BUDGET MAIN集中验收

实际merge交接18dbd0e，外线提交完整保留，未写候选线/外仓。先14个反例RED/0.89秒证明文本相同不能跨来源、语言、问答、发言人、表头互删，混合summary组与逆序事件/派生组ID碰撞也不合法。新增预算item/group键碰撞先1 RED/1.50秒。MAIN修正保守context key、顺序子序列包含、稳定无碰撞组ID和bundle命名空间；按首内容索引可能包含组，避免无关候选全量两两比较。原件/定位不改，96/160不扩，原golden不生成。

最终145责任项/7.46秒（外线32+旧选择89+MAIN15+冻结兼容9），Ruff、3源模块mypy、diff绿。真实微软TXT search/exact与实际0.3.3 AUTO批次升级隔离2项/23.73秒绿，补掉外线仅因worktree缺sibling原件的那个失败，不改该旧测试。原件字节SHA回放且目录恢复、升级任务/旧ref/恢复幂等通过；0供应商调用/费用。三个tmp/n6ba/bb/bc核绝对路径非reparse后删除恢复absent。共享selector0.3.3区分新的预算算法批次，候选合入后再更新版本。

FOOTPRINT已实际推cf24f3455f01b5e143107f1584cc47fa1ceb9d83，精确CI37542743196 job112539384015/68秒全部步骤success，收据已补。两外包HANDOFF中的手工候选覆盖与需要另开人工处置审批/golden重生成建议不成为MAIN规范：新真实质量与业务大节点仍等候选；原golden/33分母不变；处置只查可重建/未使用，不新增人签。

当前准备预算正常提交推送并核精确代码CI。S7未complete；下一接候选线，统一真实九样本及正式Worker/RF节点。RF6e6b817a三owner、用户config3609e707继续保护。

实际预算并线提交3cd49606eee2a9b752bc5f22bf84ca00bb5d8ba4已推master，正常commit/pre-push绿；远端master实读一致，两外线分支均为master祖先。空间CI37542743196全步骤绿68秒。只读发现候选线新交接ce61cdd（实现9a4b815）已存在，下一MAIN验收而非重派/等bootstrap；本回合不抢其写集。暂记预算CI37543349021运行中，结果以最终收据为准。

最终预算精确CI37543349021 attempt1全部step/job success，job112541358759/72秒，实际代码3cd4960与远端一致；空间cf24f34同样全绿68秒，收据均published_ci_passed。API复用同URL曾返回过时in_progress；用nonce/no-cache核当前状态与精确head/全部steps，不把旧缓存当CI仍在执行。RF三owner实际SHA与前一收据一致，用户config SHA3609e707保持。最后纯文档skip ci发布，不重复已绿代码CI。导入预算PWF曾有末尾多空行导致diff --check提示，MAIN只去掉空白，未改owner施工树；最终diff绿。

## 2026-10-07 — N6-CANDIDATE MAIN集中验收启动

只读核交接f31cc0d（实现9a4b815），实际无冲突merge到MAIN待验收。先写11个边界用例，旧实现9失败/2通过/0.82秒：八片段上限多取一个、英语句号不终止、跨问答/发言人/section补全、绕过注入detector、跨来源/语言关联问题。按测试修正，原golden与96/160预算不动；详细执行单n6_candidate_main_acceptance_2026-10-07.md。用户source_acquisition.yaml和RF三owner文件继续保护。S7尚未完成，不拿旧DOCSET CI替代新代码验收。

组合真实E2E首次1失败/10通过/54.16秒：旧final9与实际AUTO升级1均绿，失败在G-S01-02 EPI完整业务断言，不改断言。默认解析诊断annual396候选/393去重/96精选，EPI位于page40 paragraph8，真实原文完整但仅event分类且budget_full；页40其他项目/并购同样遭截断。补两个独立合成责任反例：忙页第二category仍须进入预算竞争、设备客户端量产验证必须作产品里程碑。两者明确RED（测试夹具最初漏language/错误coverage字段已修复后才确认产品RED）。九样本全表原运行仍在执行，源代码待其结束后集中修正，避免运行期间混合源码。

首次正式九样本全表403.731秒：required18/33（旧12/33）、764定位零失败、重复3（旧48）、精选67047B。不能宣告质量完成：G-S01-04旧full退为miss，S08增加两条套话噪声，EPI真实E2E失败。保留初次报告n6_combined_quality_initial_2026-10-07.json供对比。两个责任RED修正后266项2.98秒绿：客户端量产验证按一般产品里程碑分类（无公司名规则），soft quota有效时忙页即时重offer下一category，保留同category/page轮转与极小budget历史策略。等待真实E2E责任重验，先做定位诊断，集中修正后再做最终全表一次，不逐helper重复。

忙页/产品分类修正后真实E2E仍失败EPI（1失败/10通过/53秒），未隐瞒或放松。深入抓包发现whole-page completion继承全页理由，普通尾句变product_milestone且score20，挤掉真实EPI score11。新增局部理由反例明确RED后修正按句计算topics/reasons/score与sentence group，EPI默认解析短探针已full。补工程时间表反例与多reason注入反例两RED，修正一般开工→未来建成/投产分类（保留计划原文），已有candidate保留所有窗口reason，避免只保留第一条而丢产品/项目语义。最终269责任项2.81秒、全CI范围Ruff及8模块mypy绿。

S08新增噪声实证来自一个orphan_answer_needs_review的pdf_table_qa_fragment：旧parser不识别“4：/5：”问题，219字整cell包含有价值占比+两段套话；不是跨speaker拼接。不得为此删整条事实或放宽定位；QA解析/局部可回放单元整改进入S7 remaining，原golden/噪声计数保留，不改parser/version来掩盖。集中修改后启动最终全九样本（另存final报告）与真实E2E+旧9+升级1责任复验，不加CI长套件。

最终九样本全表372.044秒：21/33（旧12/33）、optional5/17（旧4/17），全部旧full无回退，764 locator/0失败，重复3（旧48），精选66195B，scratch峰值61277B。正式业务节点+旧9+升级1共11项66.48秒绿。业务/项目上下文解释子集20/29（不改33分母），remaining9个业务点详见验收单；3噪声为年报重复1与S08 orphan cell两条套话，保留原标注。实现可正常合入，S7语义整改不complete。

已验证绝对路径均在本仓tmp且无root/子级reparse，n6cr/ct/ce与n6q-input/scratch/final-scratch/report/final-report均恢复absent；自己的pytest新副本、DB、包装配置/报告临时副本删除，保留≤2MiB小报告/逐点收据，原件与RF三owner/user config保护不变。初次清理PowerShell foreach直接pipe语法错误发生在任何删除前，包数组后执行成功；不碰其他并发tmp。准备正常merge commit/push，日常CI没有新增长套件。
