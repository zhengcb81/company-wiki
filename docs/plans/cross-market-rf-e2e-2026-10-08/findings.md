# Findings

## Phase6 P1预算与桥接共用层（实施中）

- 基础组件335df5d3发布后远端CI在collect阶段缺httpx，具体日志已取证。本机有包导致局部和全量collect未暴露；CI只安装requirements.txt，我只加pyproject直接依赖，且2026-10当前openai 3.26.1的传递依赖已为httpx2，不再保证httpx。根因是双安装入口声明漂移/错误依赖传递包。新增所有直接runtime依赖须出现在CI requirements的责任测试，先RED再补显式HTTPX声明，并将这个毫秒级静态检查纳入现有快速push集合；不删除HTTP测试、不扩大普通commit完整E2E。

- 最小RED共8失败/1通过，实证：无效cost已经改变byte计数，byte超额报告丢掉cost和实际bytes，hard-timeout丢stderr usage，失败响应信任错误adapter version，bytes耗尽仍能发新请求。原两个测试将actual usage错当成预约量；先记录独立反例后改其计数期望，超额拒绝仍保留。失败账不能抹去已经下载的流量或发生的费用。
- 修正为两维先校验、完整实际计量后再拒绝；剩余额度不负数，失败账允许恢复超额实际值。timeout只取最后完整同名/同版本progress，不累加重复checkpoint；硬杀无法证明最终读/flush完整，明确usage_complete=false、计量为已知下界，不冒称全量零费用。
- CWP-owned HTTPX同步/异步transport在全部HTTP状态、重定向和重试的stream计量，强制identity并拒绝服务器无视此要求，避免解压后原件大于计量。拒绝已知超长body，HEAD资源长度不当作body。未知长度最多最后一底层chunk超额，记录实际值后终止；sync阻塞仍须父进程hard deadline，不能声称chunk检查可以中断阻塞socket。接口依据[HTTPX官方transport文档](https://www.python-httpx.org/advanced/transports/)。
- Windows async loop需内部socketpair：普通沙箱运行被平台阻塞；pytest函数级禁止network也会误伤loop构造。测试session先造内部loop，随后仍禁止外连且只用MockTransport；正常OS运行22项1.01秒通过。没有解除整个测试包的network禁止，也没有把该环境错误算provider失败。
- SEC UA真源为已配置SEC_USER_AGENT（只验证非空，未记录值），不是workspace/run.json；Dayu构造/下载限流state全部指向CWP-owned workspace。HK注入client后UA/timeout必须由client显式配置。桥不调用CLI init或Pipeline，不修改Dayu或产生其pyc。

2026-10-08 新任务。CWP 生产根 company_raw / dayu_portfolio / dropbox_stock / future_lake 由同一配置接入。RF 仓 main=7cf337e1，FF main=211a56ff；RF 三份 assurance 日志是既有 owner WIP，保持。RF 实际 runtime=4.1.0，五个来源运行文件 repo/installed SHA 相同（不存在所疑安装漂移）。EARNINGS_TRANSCRIPTS_TOOL 当前环境未配置，必须真实验证配置路径，不能冒称电话会已自动下载。

## 第一轮真实链路缺陷

- RF 客户端仅认 legacy capture_ready，拒绝 FF schema2 source_candidate；真实 CN/US 失败已留原日志。
- raw source reader 和 source builder 对原始 retrieved_at=null 强制 datetime 校验；前轮 narrative reader 修复没覆盖 raw 路径。原件和公开日不修改，null 保留，新的 local capture 使用实际 verified read_at。
- annual 请求省略可选 fiscal_period 与 canonical FY 冲突；仅 annual 的唯一 FY 可默认，季度不能猜。
- FF schema2 极简 pathless candidate 与旧 metadata-rich candidate 不同；builder 应接受确切 v2 shape，并从实读 manifest 获取身份/标题/日期，不伪造缺省 producer metadata。
- 六新增回归先6失败，四责任文件修复后69测试绿，定点安装4文件×2物理副本；配置不改。
- Dayu HK/US 下载在当前有限预算策略下不可用：MAIN 同请求直接 CWP ensure 得到 `adapter dayu-sec-cli does not support bounded acquisition`。先定位CWP adapter边界，绝不修改Dayu/取消预算来假装成功。
- HK年报可选language=zh导致no_local_match，去掉后CWP source query fiscal_year mismatch；公开日期/正文均有，需要进一步源元数据追踪。
- CN年报 source_url仍HTTP；不能私自改为HTTPS，需官方HTTPS实际验真后按producer source-facts机制登记。

## 第二轮原文与契约核实（07:17 UTC）

- CN 官方 HTTPS 实际 GET 得到相同原件 SHA 后，使用 producer source-facts 仅登记 source_url；原件、原始 retrieved_at=null 保留。FY2025 RF→FF→CWP 两次零下载复用已经成功。
- HK 年报 sidecar 没有 fiscal_year/language，query 返回 null 并导致 RF拒绝；执行 agent 实读封面/正文后，以标准 source-facts 登记 FY2024/FY2025 和语言，原件SHA不变，随后两年 source-preparation 均成功。不是目录差异导致。
- StockInfoDLSimple 将 semi/quarterly 都映射到 annual 分类。实际 688012 官方 POST：年报 category_ndbg_szsh 只给年报；半报 category_bndbg_szsh 给2026H1（1225482884）；Q1 category_yjdbg_szsh；Q3 category_sjdbg_szsh（本期未发布）。不存在通用 category_jdbg_szsh，它会被官方忽略而返回208个公告。再次真实联合分类 yjdbg;sjdbg 只返回Q1一条772B，证实可用。
- 分类回归先2失败/1通过；修复后 CN官方API、预算、适配器、latest分页四责任包绿。初次测试错误引用不存在文件导致收集失败，保留日志，不计通过；纠正实际文件路径后集中重跑。
- 三公司真实分部均有 mixed timing/presentation，而 RF只允许一种。新增仅 `modeled_as_recognized`+`direct_growth/direct_revenue` 的已确认聚合 mixed 描述，要求 aggregation_boundary+原确认政策引用，拒绝progress/lag/carryin和活动模型。先9回归失败，最终64责任测试绿；数值保持已确认收入，不再填 progress=1冒充单一确认政策。定点同步3文件，安装配置未变。
- MSFT 2026-09-02 官方 FY2027 segments/metrics 原稿为图片PPT，执行 agent逐页实际打开，不依赖无文本OOXML；两新分部、FY2025/FY2026比较及八收入流必须由独立 reviewer 复看。
- Dayu外部代码零修改。CWP旧dayu_cli_v1不支持bounded，ensure在provider启动前拒绝。SDK已有client注入，但CLI没有metadata-only/budget入口；本轮不能把网页补充资料算成Dayu集成新下载。完整桥接需CWP-owned预算transport+SDK边界另行实现，不能只加supports=true。
- ET/FMP真实精确fetch诊断返回 provider_entitlement_required；discover返回 candidate_discovery_unavailable。未订阅、未翻译、未调用外部LLM，不能声称 FF自动补电话会成功。
- SEC HTML在当前 CWP narrative worker不支持；US agent临时BS4解析与consumer capture分别记录，不声称worker处理过。季度/纯定性管理层目标不能偷换成年FY数值，以原材料旁表+data_gap保留。

## 独立审查实际发现（持续更新）

- HK reviewer已核38命令配对/output SHA、所有manifest artifacts/runtime SHA、69claims excerpt对原PDF页逐一重提匹配。
- 但文本语义绑定不等于excerpt存在：paid_social_stabilization反证使用259m vs264m订阅数，却仅绑定H1 PDF47收入表；需PDF6真实claim。
- NetEase H1+8.3%及竞争franchises被benchmark/行业/反证使用，但69claims零条绑定NetEase来源；需完整原文claim，不只是把source列入source_ids。
- customers维度写top-five6.5%/largest3.4%，未有对应披露claim。不能以strong validator green宣称全部事实证据已闭环。
- 上述为HK执行产物修复队列；待完整初审后执行者产新版本，独立reviewer复查改变的依赖。当前并发4槽满，向已完成执行agent发消息被工具thread limit拒绝；不偷偷超额并发或让reviewer自己改写签收。

- US独立逐页确认22/22官方PPT全部关键重述数值/互斥流/季度guidance正确，90manifest artifact SHA与42命令成对有效；manifest41count因seal finish在写manifest之后，按最终ledger计数，不当成数据错。
- **US P1输入数值错误**：8个敏感性name写FY27 growth ±5pp，但ratio维度percentage_point shock_value=5.0实际直接加减5即±500pp；应0.05。代码按契约计算，错误在输入单位语义，strong validator仅算术一致无法读自由文本意图。修复8项及sensitivity/confidence/report/snapshot依赖，新版复审；当前旧版不能称敏感性可靠。
- US72个未来growth rationale_support claims仅截各stream FY26基数，不能支持range/fade rationale；虽然未来值明确analyst assumption，需绑定完整历史growth上下文、实际需求/供给、季度guidance与外部benchmark，且CC季度与reported annual不当同口径下限。独立审查继续列完整定位。
- HK FY2025登记HKEX URL实际404，正文与公司身份/期间核对成立，但当前URL不能重证public provenance；reviewer只读查官方真实PDF与公开日/同SHA，再给producer修复建议，不能直接改旧raw。

- US consumer_cycle支持与反证绑定同一库存上升句；反证应为真实gaming FY27恢复增长预期且不外推Windows。enterprise_migration服务扩张不受license下降一句支持。四根季度falsifier与年度模型口径错位，需同口径年度条件或有原始季度阈值。
- HK独立实复现RF registry audit误报：by_generation以四元组为key，却用input_sha字符串做成员检查；所有已登记产物均被报never registered。MAIN新增注册正例、跨版本/快照、未注册/冲突/日期过滤、真实CLI退出码7回归；先3 RED/4 PASS，修复单独registered_anchors集合后与发布事务集中37 PASS。链/hash/冲突验证未放宽。
- 定点安装首次选择新测试文件被当前runtime闭包拒绝，零安装写入；改为只同步审计程序与契约参考。测试留仓库，实际安装约定优先于历史文档推测。

## 最终归总（09:10 UTC）

- CN v3/HK v4/US v2经原独立reviewer复查，模型技术及透明条件预测可接受；三公司产品全E2E均PARTIAL，不据此签采集/Worker全部完成。逐条关闭与残留见acceptance_summary.md及各最终recheck。
- HK v3仍有质量标签错误：网易竞争背景被one_step支持而误升Games triangulated。独立复查再次FAIL，执行v4改contrary并恢复limited/confidence limitation，数值不变，v4复查通过。合法摘录、正确算术和相同分值不能替代证据角色核对。
- CN残差/售后范围已收窄；9公告59页补读，达产属地贡献300000万元目标period未知，不套邻近专利计划年份、不并入公司年营收；激励schedule仍缺。辅助公告仅SID到研究目录，不冒称FF→CWP入库。
- HK官方年报认证/真实公开日仍未完全证明；2026-10-08仅为实读可用上界。US33管理指引原季度/CC/定性边界保留，不虚造年度中点。
- 原R3微软TXT正式摘要49证据在CWP与RF当前公共read实测通过，但显式信息日read拒绝公开日unknown，本輪输入没有消费；不会把已有能力泛称不存在，也不会重复付费生成。
- 已审研究产物与来源按SHA交付RF output，原input/snapshot/manifest不改；测试TEMP237文件清理，原始资料字节保留。归档辅助错误混用两种SHA后按公开强校验器修正，不更改模型或测试成功标准。
- 后续优先修CWP-owned Dayu有界桥、FF→ET exact能力/预算/套餐诊断、SEC HTML初处理和RF证据构建/目标表达，完整施工设计在follow_up_plan.md，尚未实施。

## 固定回归套件发现（Phase 5）

2026-10-08 最新用户纠正：身份核验简化仍有遗漏。查实 writer post-scan/source_ref_for_import 借历史选择验证入库，unknown-date 分支又要求 title/provider/company/security/market 全匹配；ensure 再次 resolve。已建立 phase6/identity_responsibility_simplification.md，优先整条责任收敛，保留真实冲突负例，缺辅助信息仅诊断，不新增签收许可。

- 初版小测试先收集失败（runner不存在）；实现后16责任单元测试绿，含明确5pp/同行反证/未定年达产目标负例、不同样本不能伪称改进、删除失败检查视为missing、故障及只读账清理。沙箱默认pytest TEMP无法创建，改用独立短basetemp正常OS运行，未改断言。
- 真原件full当前71检查点：46PASS、3BLOCKED、1FAIL、14NOT_RUN、7NOT_APPLICABLE；完整基线在 `benchmarks/cross_market_rf/baseline_replay.json/.md`。CN/HK PDF与MSFT TXT有限Worker各一个loopback POST，96/12/49原文证据；全部locator由公共read回放验证，CLI lookup验证入口，RF/CWP视图相同，再次运行0新增POST且不翻译。
- **新增真实RF缺陷**：MSFT正式输出在seed=0下可强校验，换Python hash seed后出现 `confidence components recomputation mismatch`。定位 `scripts/analysis/confidence.py`：`parameter_revenue_weights` 的refs为set，无序迭代影响weights插入顺序，后续sum/浮点累加存在最后位差异；validator对components要求精确相等，进程内测试漏掉此维度。经济情景路径没有变化，不能把这个失败误称全部营收事实错误。不同seed强校验成为固定检查，不用删断言/只固定seed掩盖。
- HTML/PPTX都实际运行有限Worker并返回unsupported_source_type，0tokens/0费用；不是静态猜不支持。PPT仍须22页图片/文字定位支持，不能用研究agent看图冒称canonical处理完成。
- 输出目录曾因测试registry的Windows只读属性不能删除；先注入只读单元回归，再仅在已核绝对owned根解除属性。实际失败残留仅10134B测试账，逐文件核对后清理。现在marker最后删除，失败也有明确拥有标记，不碰原件。所有最后运行均TEMP不存在。
- 额外定位检查不能每个span重启CLI重解析259页PDF：最初full224秒；改为公共read一次验证全部locator、每span合同验证、一次CLI lookup，功能不缩水，最终92.555秒。普通commit/CI只增加0.28秒小测试。
- 可搬移包35文件56,835,555B，只包含被引用样本和固定研究输入/旧产物，按SHA去重，不复制数据库/密钥。故意提供不存在的生产catalog，用这个包重跑90.309秒；71状态全相同、比较0regression/0missing；证明独立复现。验证后该导出副本删除，Git无新增大原件。
- 真实在线隔离验证：CN H1 2026新增3,149,962B、SHA182e2062...；FF下载1→复用0，CWP复核身份/年份/字节，RF source preparation再次读取通过；HK/US仍producer ensure fatal、download0。FF用既有年报复用独立触发HK/US companion，0费用请求返回zero_cost_budget/provider_calls0、ET未启动；与无套餐和已启动的offline契约严格区分。未调用外部LLM、未改Dayu、未触碰邻仓WIP。

## 根因修复要求补充

用户要求每个暴露问题修共用机制，不能逐症状补丁。已将已证实机制、待验证假设、责任层、漏检维度及集中验收整理到root_cause_remediation.md。尤其区分ET启动前zero_cost_budget与实际账户套餐拒绝；正文真实与官方公开日证实；NarrativeRef可读与预测实际消费；算术/字节正确与证据含义正确。当前有界桥/格式/输入语义/P0改造尚未实施，不重新签为已解决。

## 泛化验收补充

用户要求全部做完后换三家公司再测试，防止针对第一组修复。第二组应固定在改造后的版本上，独立事实oracle与完整新研究审查；不能仅换ticker重放第一组输入，也不能直接比较不同公司的金额或用不同spec的compare宣称改善。新组保留首次失败，发现共性问题后回责任层并同时复核两组。

Phase6只读探索发现共用问题：Dayu budget transport需要覆盖SDK retry/HEAD软吞异常、同步流的总deadline、超限实际usage及压缩口径；仅子进程timeout会丢partial usage。解析层不能只放开MIME，需同时补结构/选片段/回放/表格排除/语言识别/执行版本；现有HTTP模型只收文本，图片型PPT需受配置/预算约束的视觉或OCR接口，不能假称已有支持。记录供责任层TDD，未实施。

P0已完成候选修复：最小3例证实seed/集合顺序/小权重丢失，9 RED（其余6为新增兼容契约）；新增stable-fsum/1数值revision，以稳定key及补偿归约修共用层。新产物逐字段精确；无revision旧产物仅命名无量纲归约64ULP，历史计数类型/分类/身份/来源/hash不放宽。五类原HEAD金标逐一重现并用新validator验证，非confidence经济差异0；dependent receipt/result SHA按载荷依赖变更，不改原产物。根因测试包含64/65ULP边界、NaN/bool、unknown revision、覆盖/浓度/历史计数/score篡改及真正式发布跨进程。

独立worktree快速检查首跑2个CLI失败：默认sibling误取Temp/filing-fetch旧89c8bdb2，实际当前FF=211a56ff支持兼容flag。显式FF_V2_CODE_ROOT/CWP_V2_CODE_ROOT后125通过，断言未改。P0责任闭包62通过（2subtests），非生产数据问题。RF工作树初建复制49k历史文件，已用sparse收窄责任路径，不清理canonical记录。

P0原三家公司结果证明共用修复有效且旧经济情景不变：US不同seed强校验已PASS，原其他70状态不变。套件整体PARTIAL是原采集/HTML/PPTX/新研究尚未实现，不再有确定性FAIL。一次只读报告脚本read_text漏encoding导致GBK诊断错误，已用UTF-8读取；runner本身退出码实现PARTIAL=2正确，不将PowerShell封装非零归一化误判为套件缺陷。
# Phase 6 P1 下载桥机制审查（2026-10-08）

- 实际Dayu SDK公开接口和现存venv兼容HTTPX0.28.1；bridge不启动Docling/LLM/翻译。parent scratch终止后回收，SEC共享throttle/OS mutex写CWP分配根，Dayu源码/缓存零改动。
- 本地微软真实inline XBRL日期是`June 30 , 2025`/`March 31, 2026`，非ISO字面；按声明的[XBRL TR5](https://www.xbrl.org/Specification/inlineXBRL-transformationRegistry/REC-2022-02-16/inlineXBRL-transformationRegistry-REC-2022-02-16.html)已实现两个英文日期转换，保留原值和format，未支持格式明确拒绝，日期/CIK/FY/period语义校验不放松。
- HK元数据窗口中无关旧财年无年份标题不得阻断有效请求；限定请求scope后验证，范围内未知年份不能用请求年份填补。
- SDK `raise_for_status()`允许206，不能作为完整原件证明。现在GET实际200、无Content-Range、实际长度匹配才可stage；receipt采用GET实际版本头，避免HEAD/GET变化隐瞒。
- 7RED/41PASS机制复现后修复；集中117PASS24.49秒，包括真实SDK两个市场metadata-only→唯一GET→真实CWP入库/SourceRef复用。离线fixtures只证明接口和行为，不能证明live供应商可用。
- 固定套件的live新增SDK配置必须把CWP代码/state映射到独立HEAD export；provider解释器仍只读复用，SDK import优先export cwd，防止editable安装指向原checkout。新增路径映射RED→17PASS。原71检查点不改。
- 仍未实现的范围：SEC8-K/6-K exhibit bundle、HK英文发现；不能宣称支持，真实请求给具名能力拒绝。生产acquisition配置尚未提升。

后续验收：实际三市场full/live全部download→import→reuse→RF read通过，正式配置已提升。Windows实际SDK解释器的redirector暴露另一类漏检：原hard-kill测试只有直接子进程，没覆盖子孙；新真实子孙RED确认超时后活动，用共用owned进程树/管道截止机制关闭。增加的OS测试覆盖阻塞stdin、stdout/stderr上限及嵌套job；不是加人工门禁。原件和外部Dayu保持不变；独立live目录141MB已恢复不存在。电话会zero_cost_budget仍是FF启动前判断，需要责任层下一步修复，而不能归咎FMP账户权限。


电话会修复确认：max_cost=0限制增量费用，并非禁止已订阅配额HTTP。FMP exact支持和当前账户权限是两个独立状态；现账户真实一次请求仍拒绝，不能将离线绿说成可下载。用量保留独立stderr回执，public内容和SHA不改；unknown supervisor usage不伪造0、不自动重试，legacy provider_calls仅attempt。默认CLI静默合同保留，FF显式请求回执；公开v2 serializer也需传实际用量，直接调用companion不能替代该接口验证。

三条根因任务可并行：纯格式normalization包只写CWP新document_normalization子目录，不触现有Worker；RF共用输入构建不依赖新解析器，使用现有SourceRef/NarrativeRef；FF失败原因传播可对当前CWP结构输出做离线/实际CLI验收，不要求同时改producer。最后由MAIN统一接线和真实两组公司审查。未提供机器元数据只能unknown，不能靠文本猜provider_started或公开日。相互独立来自写范围和接口，不来自“同一主目录不同agent不会冲突”的假设。

MAIN 来源资格只读调查已记录在 phase6/source_qualification_investigation.md：indexed 与实读字节不同，已有 source-facts append-only 修正链可复用，未知公开日的 resolve 检查顺序仍待 RED；微软会议日不能替代 transcript 出版日。2026-10-08 再核三条实际独立工作树，分支/基线一致、未提交为空，可立即启动。


2026-10-08 身份责任入库节点已发布95749f84，精确SHA远端CI37843149783成功。冻结full/replay完成220.179秒，47PASS/3BLOCKED/14NOT_RUN/7NOT_APPLICABLE/0FAIL，隔离根恢复且保护原件/输入不变；同规格对比71不变（已有FF→ET→CWP离线契约仍PASS），无回归。后续仍按身份责任施工文档移除Reader任意元数据冲突全局阻断、重复期次检查、旧runtime许可与摘要policy自验，不宣布全项目完成。猜测tools/cross_market_suite/environment.py及execution.py不存在；已查实际文件为core.py/runner.py，后续只读实际路径。


根因扩展：仅去除Reader的旧指纹门仍不足，因为batch恢复自己又比较旧指纹和所有当前源事实，会让已完成资料因标题/期次修正或宽松限额改动无法恢复，甚至诱发重复模型/空间。该门已真实CLI复现，修复同属“原字节身份、选择事实、生成时观察、冻结账本”职责拆分；回执应报告当前观察，旧产物留原样，不用重签许可。


R6集中接线查实更深质量问题：capture.document_kind争议已记录，root column却仍给最后入库分类，显示与capture投影不一致。修共用column alias映射（包括title/filing_date等），保留raw读和完整冲突诊断，未知分类作为unknown路由，而不是再加类型人工许可。格式回放每文档normalize1次，再用全部locator/coordinates/text/parser/metadata匹配；每span不重解析全文。三包本地并线完成，FF/RF远端主线发布成功；真实22页图片deck尚无正文识读，不签全绿。


## R6合并大节点发现

新增字段可选必须对旧实际输入验证：unmodeled_reason与已有rationale重复，是无收益的准入门，已取消；无转换目标仍不产生年度值。HK同摘录正反混用是实质证据缺口，保留FAIL。来源能力错误必须保留机器原因，不能吞异常后按英文substring猜；PPTX22页全图只可具名BLOCKED，不是成功skip。副本存在不等于安装运行一致：两副本现在完整runtime零漂移且3builder实际导入成功。数据与逐项证据见[本节点记录](phase6/r6_handoff_intake.md)。


第二次冻结回放CN/US恢复，43PASS/2FAIL（HK语义、PPTX探针）且无新回退；纠正probe只读顶层的假设，26责任测试绿，真实全图证明仍待最新冻结执行。实际测试/更正/下一接口统一见[查收记录](phase6/r6_handoff_intake.md)。


R6查收收尾：三分支均已包含于远端主线且代码CI绿；最终完整冻结43PASS/1FAIL/2BLOCKED/18NOT_RUN/7NA，HK旧语义问题仍失败、全图PPTX具名未完成，环境恢复/原件保护通过，外部模型费用0。责任验收完成不等于产品全绿；详情与下一MAIN接线见[查收记录](phase6/r6_handoff_intake.md)。

## 2026-10-09：公司池真实审查循环

用户要求随机从已有公司池选公司→真实revenue-forecast-audit→四独立审查→专家共用根因PWF→实施及原公司复验→再选下一家，直到无主要问题/改进点。循环协调计划独立放在 C:/Users/郑曾波/Projects/revenue-forecast-audit/docs/plans/company-pool-cycle-2026-10-09/；此处旧工程责任、原两组回归和未完成Phase6仍保留，不重复创建同因施工包。当前goal active，语义已有继续循环，目标工具没有修改objective接口，未伪造新目标或完成旧目标。

重大修复后以三家不同公司连续四路实读clean并覆盖池中A/H/US、复用与真实新下载作收尾证据；BLOCKED/NOT_RUN/旧主要问题不算clean。预算沿现有效累计USD20/2M tokens，unknown照计。只在大的节点测试和审查。当前首轮尚在选样/预算盘点，真实研究未执行。

## 2026-10-08T23:49:07.468765+00:00 — 首轮公司池封存与隔离候选

NVDA 初始真实执行包位于 revenue-forecast-audit/runs/pool-20261009-001-us-nvda；manifest 8a895b3b1744985f654048bdfc3b1b5b9de526c8c40b637ade4e809386002095，139产物/15步骤/9来源。整体partial，正式RF数据产物校验通过不等于研究高标准通过。测试根6.96MB保留供四独立审查；新supplier LLM0，历史unknown7保留。真实FMP1请求账户entitlement拒绝，不盲重试。

有限叙述入口的script policy错误已隔离TDD修复（177相关PASS），CWP/FF producer cause 公共边界并行候选正在集中测试；RF消费候选97442029已提交，focused57PASS+明确三仓1PASS，当前shortCI125PASS/Ruff/mypyPASS。候选未发布main/install；独立四审查按实际初始版本进行，再做整链集中验收并发布。只修公共责任边界，无新门禁/身份检查/费用数据库；Dayu零修改。

## 2026-10-09T00:14:12.625451+00:00 — 共用候选验证与CI真实根因

CWP candidate d7923191（含producer4c75273a、finite入口65562043）、FF afbef65、RF cf06ba00（含97442029）均已推隔离支线，当前main及installed未切换。CWP组合责任146PASS，FF集中239PASS/1实盘master缺SKIP/39subtests，实际FF25检查；RF当前short125PASS，实际三仓公开CLI23PASS。success真实import→SourceRef读取→reuse无再下载保留，handled/returned-GAP安全cause及operation累计用量一致，supplier费用0，短自有TEMP恢复。CWP原push门因checkout深度固定60字符阈值在pytest前失败，3RED→3GREEN后改系统独占TEMP并以实际进程退出判定；正常hook retry成功，不跳测试。

远端RF精确cf06ba00 CI37862819961成功；CWP候选无workflow run，不宣称CI绿；FF afbef65 CI37861936346失败，公开API仅退出码/只读浏览器signed-out无法读log。逐字采用FF quality.yml curated suite本地419PASS/1FAIL/4SKIP/78subtests，58.17s：test_complexity_ratchet.py仅因ff_provider_cause.py复杂度14>10阻断，无对应业务错误。正在由独立工程线按用户既有简化授权将分数门统一改为维护诊断，保留语法/类型与新责任契约。复现本地用CWP当前main，远端用compatibility pin，不冒称环境完全相同。

NVDA initial storage/fetch/analyst三份报告已封存，均发现实质问题，不计clean；process独立复算正在形成第四报告（已核139产物、32引文与355数值叶子）。四份齐后专家读取原包并逐issue建立独立PWF，再发布修复并原公司新attempt。原财报及生产配置未改，Dayu零代码修改，RF owner assurance/output未碰。

## 2026-10-09T00:21:02.850808+00:00 — 首轮四路完整交付

NVDA四独立reviewers已全部停止写入，storage5/fetch7/process7/analyst5共24发现（12P1/12P2），原执行partial；正式算术无差错但研究与必要处理链仍未完成，clean为空。process复读实际请求确认FY26主filing与FY27Q2 companion独立，原初稿误判断已由其自身按初始dispatch更正。独立expert已实际启动，独占audit run/diagnosis和remediation/work_packages；完整诊断待交付。记录工具check读取4报告needs_remediation/exit2符合发现真实问题阶段，另有两原生角色JSONL缺重复header的格式可观察性问题，专家一起处理，不能删日志或补造执行时间。来源原件仍留在独立测试根供专家实读，无新的模型费/翻译/Dayu代码写入。

## 2026-10-09T00:28:26.063205+00:00 — 数值门关闭与测试恢复

FF独立工程提交e9b0d088已正常hook推隔离支线，精确远端CI37864557151 SUCCESS，UTC00:23:51→00:25:09（78秒）。旧复杂度14>10的许可已删除，以同算法维护诊断保留分数14、语法/读入真实错误仍非零；新provider cause与acquisition consumer责任测试加入curatedCI，未修改业务实现/抬阈值。实际527PASS/5SKIP/78subtests、53.50秒，显式候选CWP代码根只补跑两个环境skip2PASS/16.65秒；余两个实盘snapshot及一个Windows symlink限制保留，次数不误加总为一个全套。

原producer agent确认pytest218/219为其前次133/48测试的unique自有根，MAIN逐一核实绝对父路径及无Reparse后删除423个临时夹具文件，共18,492,724B；此前MAIN220自有根已恢复。见phase6/producer_temp_restore_2026-10-09.json。真实NVDA根仍保留供专家，生产原件删除0，supplier费0。

专家拟7卡并正在细化真实机制与接口；ET读入预算还能复现overflow响应读过后账却是0B，属于FETCH-007同因计量责任，不忽略为外围问题。根因包未交付前不发布新真实运行版本，不认为当前已clean。

## 2026-10-09T00:48:11.532827+00:00: W01已合并并同步

CWP156PASS/1真实数据SKIP、FF110PASS、RF14PASS；真实RF→FF→CWP23checks PASS，owned TEMP恢复，supplier0。RF3/FF4文件仅同步到两个物理副本，30个配置/output文件SHA不变，.claude Junction保留。完整证据 C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\pool-20261009-001-us-nvda\execution_replays\w01-main。调用器先误用unittest（无法导入、后0collection），明确失败未假绿；读实际pytest函数后一次补跑；RF首次零写plan发现destination应parent，写前更正。W01工程完成，实际研究M2/公司池clean仍未完成。

## 主线恢复盘点（2026-10-09）

ET W02已有128责任测试及实际supervisor/worker五种离线CLI证据，但交接/commit未完成；CWP W03公共read复验待收尾；RF W04–W06未写代码。不能以agent摘要代替交付。主线跨run默认复用/全图PPTX/原三家和新三家研究验收仍保留，循环后置不取消责任。W01精确CI与W07工程完成不表示研究全部完成。

## W02集成发现的共享根因（2026-10-09）

原始provider数据不能被要求与本项目的固定字段枚举完全相等。原件附加metadata应保存但不成为许可；必要身份/期间/内容及hash核对保持。ET执行已完成后CWP写/读失败不能抹掉实际供应商receipt、更不能退回不明retryable错误而触发重复下载。两机制已通过独立责任RED与真实三仓CLI验证；账户FMP entitlement与publication unknown仍如实保留。本节点是工程，不代替原/新三家公司独立研究验收。

## 2026-10-09 主线恢复：OCR与新样本准备

本机OCR调查已证实 RapidOCR/ONNX 三模型可离线加载，一页封面0外发；底部小字漏识，正文和22页整体仍未验收。PPTX旧parser将OOXML内部slide_id作页码，现独立包负责版本化ordinal与旧locator。施工卡phase6/main_local_pptx_ocr.md已明确本机模型SHA、限额、真正文对照、多span一次回放与无持久全页副本；batch/缓存共享接线由MAIN负责。

第二组仅做候选准备，尚未选定或执行：官方CATL页面确认2025年报及海外/储能经营描述；吉利官方资料页列2026中期与2025年报；SEC公开Costco FY2026 10-K。业务形态与原中微/腾讯/微软不同，仍须核实当前CWP原件存在性和身份再固定，不能把网页搜索算provider下载成功。官方链接：
- https://www.catl.com/en/news/6773.html
- https://www.geelyauto.com.hk/financial-documents/
- https://www.sec.gov/Archives/edgar/data/909832/000090983226000093/cost-20260830.htm

这些只证明资料可发现；金额/假设oracle在独立执行/审查实读全文建立。未引用非官方搜索结果，未复制完整网页进PWF。

## Worker 失联恢复的输出计量共因

跨 run 包真实 POST-kill 证明：未知供应商 attempt 的 2 MiB output bound 被当成已经增加的最终文件空间求和，单源恢复被错误预算拒绝。MAIN 将费用累计与唯一 summarize job 最终结果槽分开，旧未知账不改；物理 scratch/object 增量仍由原存储 guard 控制。实施细则见 phase6/main_final_output_accounting.md。读取 unit 文件时误猜 contract 路径不存在，已核实际 tests/unit/test_narrative_run_store.py，不把路径错误记作产品 RED。

官方PPTX接线补充：存储成功仅证明原件格式和字节保存，不证明文字已提取；文本和全图原件均须可登记，opaque不能成为原件入库许可。先通过现normalization的纯package解析（禁止OCR），页数非零，再走同一个canonical writer；新入口不建writer/数据库。真实PPTX作为隔离manifest登记后才能形成规范EvidenceSpan。

验收工具记录：normal OS默认mypy调用未带本项目既有ignore_missing_imports，fitz无stub报1 import-untyped；已按项目参数复查，不改运行代码来压制类型错误。默认sandbox本机socket集成停止输出，精确pptgreen进程树已终止，正常OS短TEMP补跑，不能把中断当PASS。

OCR真实首次22页1067行/145.549秒，8 selected spans回放4媒体16.570秒，source-level召回仍不完整，关键页7/18漏行；不假装全文已读。跨run包当前把source coverage_complete当完整派生缓存前提，OCR partial会永远重复POST，MAIN已将其作为共享接线责任测试：精选摘要自身完整可用不等于source全文完整；skip仍须完整扫描。结构查询后误读不存在narrative_select_core.py已停用，实际selector在narrative_evidence/finalize，仅读已定位文件。

## 主线集中整合的实际结果（2026-10-09）

- 真实中断恢复已在包含最终输出槽修复、generation复用和parser的主线2a2bd4d0通过：1PASS/10.93秒。旧unknown费用未退款，恢复后跨AUTO0新POST，公共原语言span实读通过；owned根约数MiB随后恢复不存在，生产配置SHA不变。
- 本机OCR只采用配置中已有RapidOCR3.8.1/ORT1.26.0和三ONNX实际SHA，控制面preflight真实成功、0图片推理、0网络，不自动装资源。source partial与selected precision仍分开；未宣称漏行已修。
- 费用账当前历史199534tokens/110737microUSD含native r3=9499tokens/10235microUSD；核对一致，不能重复加减。unknown7与FXguard2764保留。现有效累计上限2M/USD20，剩1800466tokens/19886499microUSD。给真实OCR节点30k/$0.10独立额度、六公司每家120k/$2加总720k/$12，在已核对余量内；尚未支出。
- 本轮读取旧猜测 `config/worker_config.json` 失败，已改用实际rg目录清单，当前配置文件是source_catalog_worker.yaml及Config loader；没有据错误路径修改配置。

## 2026-10-09：RF已发布，CWP实际CI兼容缺口并入当前责任包

- RF W04–W06修复原四项独立复验25PASS/0.86秒，可并线；MAIN merge `e688b0a2dceeb7de453e43dad3534061bf346bc9`并normal push。原assurance三个修改与output原样保留。canonical pre-push Ruff、7模块mypy、125责任行为/21.49秒通过；精确远端quality [37883658771](https://github.com/zhengcb81/revenue-forecast/actions/runs/37883658771)成功。
- 定点安装闭包22文件x2 physical skill roots=44写入，.claude既有junction仍同.agents，config/output未动。交付工作树CRLF与Git LF必须分别记录SHA，MAIN逐文件证明仅换行规范化再同步exact committed blobs；installed smoke两份实际installed revenue_core native quarter→strong validation PASS、非财报null期合法。工程fixtures不计真实公司研究。
- CWP实际主线是master（不是main）：第一次push不存在main引用已纠正为normal master，a901b67f已远端。精确CI [37883563191](https://github.com/zhengcb81/company-wiki/actions/runs/37883563191)Unit失败；其余lint/mypy/compile/config过。公开annotations指出versioned-resume scoped旧builder生成不完整binding/3、PPTX全格式固定1.0及旧normalize patch。shared owner已实际复现16FAIL/35PASS，按兼容producer/decoder共因修：无generation的合法legacy scoped保持/2，真实完整manifest才/3，坏/3不静默降级；三版freeze/currentfacts/jobhash测试保留，新per-formatparser契约测试迁移。实际风险两文件纳入同shared重大集中节点，不再加每commit全CI/人审。
- 只读PRIMARY调查已证微软PPTX公开日2026-09-02：官方IR公告链接指向相同FY27ExternalKPIs.pptx，SEC8-K Item7.01说明同日发布。另有同presentation SEC HTML正文可作为独立来源补充OCR漏行；不是同binary SourceRef，必须正常CWP登记/实际SHA再消费。旧null日期工程receipt与封存模型不改。记录phase6/msft_presentation_publication_investigation.json。
- 源查找路径错误（worker_config.json、FF company_wiki.example.json、cohort proof旧名）未触发修改，已按rg实际目录纠正；安装smoke最初test helper导入canonical模块并试图default registry，沙箱在写前拒绝，修为fixture JSON→fresh installed subprocess+明确owned registry。错误保留，不包装成产品缺陷/成功，owned测试根已恢复。

Next Step：shared OCR runtime+上述实际CI反例集中通过→合并master/push精确CI→一次真实22页public有限batch/read/跨run默认复用及固定71检查→两组新研究/四审→公司池loop。PWF与goal均保持in_progress/active。


### 主线大节点的额外待观察项（2026-10-09）

RF `prepare_source_result` 对 public narrative read 仍 clamp 30秒，旧元数据/raw读取成本与OCR选中media重放成本不同。parser实际8span/4media16.57秒，更多选中media可能超过30秒；需在真实大节点测量，不臆断已失败，不先任意扩大上限。若发生超时，统一按调用方剩余deadline传递责任层，保留有界终止，禁止偷偷重OCR全文或无期限等待。

本轮两个具体路径读取错误：公司池PWF位于audit项目、CI文件为`.github/workflows/ci.yml`，不是猜测的CWP池路径/tests.yml。后续先用文件清单定位；未产生写入。独立agent仅准备验收脚本和来源映射，不重做工程包、不中途发付费请求。


## 2026-10-09：shared接线发布与大节点新反例

shared交付67b55d72正常合入master979792e0并push，15runtime/test交付SHA及main Gitblob相等，32回执SHA实核；正常prepushgreen；精确远端CI37885534513成功。9份来源准备证据SHA也已核，未生成新研究。

固定71 fullreplay实际144.37秒：40PASS/2FAIL/4BLOCKED/18NOT_RUN/7NA，67,534,494字节临时根已恢复不存在，收费调用0。新反例归因到责任层：三市场真实source preparation都因当前抓取Oct9晚于固定asofOct8而拒绝，需区分publication/可用时间/当前实读时间，不能伪造captured_at；独立诊断`phase6/asof_clock_diagnosis/`优先。旧HK同excerpt正反角色研究FAIL保留；新研究必须改真正证据角色。PPTX纯无OCR fixture诚实partial/未发布，本就应BLOCKED，旧helper只认failed造成报告FAIL；2RED/1PASS→29GREEN/.28秒，仍不把body未识读说成PASS，未知/其他错误和意外已发布仍拒绝。真实OCR public大节点另跑。

另一个共用效率原因已结构定位：legacy缺URL治理retired原件真实存在、普通scan sticky，不会自动成为reuse候选，可能fetch后才按SHA去重。`phase6/legacy_local_reuse_diagnosis/`独立只读反例进行中；应在真实六家前决定通用零下载reconcile入口，不粗暴active所有退休源或用公司特判隐藏缺陷。Dayu code零改动。

当前Next Step：完成这两个实际共因的责任细则/TDD通用修复；真实22页public batch/read/跨run零调用复用；同一固定71对照（未变研究输入不宣称全绿）；原三家、新三家真实执行+四独立审查；最后恢复冻结NVDA及公司池loop。目标仍active，主线未完成，loop尚未启动。


### 2026-10-09 实际OCR节点与新增共因施工

真实22页节点已运行一次，不是NOT_RUN：`phase6/ocr_major_node/runs/mocr-20261009T045902-933be853/acceptance.json`保存FAILED_RETAIN_ORIGIN。官方local import0download完成，首select真实126秒后终止：`PARSER_INCOMPLETE / empty selection does not have complete coverage`，后两依赖dead_letter。原生tokens/cost/unknown/unsettled全0、无模型admission；原件SHA/size/mtime及protected配置/PWF前后全相等。保留owned origin `C:/Users/郑曾波/AppData/Local/Temp/mOCR-srw9_9oe`供诊断，不盲resume不可复活的旧terminal jobs、不开新run绕账。

当前根因优先包：

1. [legacy local reconcile施工卡](phase6/legacy_local_reuse_diagnosis/IMPLEMENTATION_CARD.md)已由MAIN审读，单一CWP owner开始隔离TDD实现；退休原因分类、实际bytes/issuer/period、facts+restore单事务、重复0fetch；真正withdrawn/damaged不active，不去全改9499状态，不动Dayu。source-query继续只读，公共localprepare接线由MAIN整合FF。
2. `phase6/asof_clock_diagnosis/`统一publication/availability/read/capture/verify责任细则正在调查。已定位RF不止一处抓取<=asof门，也存在新claim verified_date直接写asof的错误；必须共用时钟资格，不伪造旧日期，不放行future材料，旧frozen字节保留。RF单一owner负责其目录，CWP可选availability DTO由MAIN统一接口。
3. `phase6/ocr_selection_diagnosis/`独立实查为什么已识读图文未成为任何有效candidate；先判断分行/role/group/filter或该材料真实无业务价值，再通用TDD。不为节点绿降低阈值或强选财务表；需要最小真实页样本才另安排，不重复全22页。脚本原要求selection==selected已修为合法selected/partial，但仍要求completed summary、parsed/high-confidence selected spans、精确publicreplay、原语言、全篇coverage=false；这个validator修正不解释本次empty。

上述根因处置后再真实节点的新合法generation验收、固定71对照、原三家与新三家真实研究/四独立审查；全部主线完成后公司池loop。大节点增加的是此前未接起来的真实路径，不新增小节点签收。

来源时钟施工细则已交付，RF在隔离 `Projects/_harness_worktrees/cmrf-20261008/rf-inputs` 从e688b0a2实施。MAIN以最小事实接口完成CWP receipt2.2：仅解析既有canonical HTTP DownloadReceipt，实际SHA/时间/URL/大小/MIME一致才给availability上界，其他返回null；默认2.1不变，不加许可。集中28PASS/13.51秒、Ruff绿、2个owned短根恢复不存在，收费调用0。详细限制与实际RED性质见phase6/asof_clock_diagnosis/PRODUCER_IMPLEMENTATION.md。a40eb065精确CI37886236535成功。


## 2026-10-09：真实时钟、本地复用、OCR候选根因修复收尾

RF 将 publication/availability 与实际 read/capture/verify 分开，保留未来信息拒绝；实际原三家公司注册原件通过公共 reader Oct9 实读、as-of Oct8 资格成立，各只开原件一次且0下载。旧4.1.0 runtime 重现五族 golden，4.1.1经济字段完全一致。不是伪造旧采集日期。

FF v2 explicit reuse_only 在 source query 真 not_found 后调用 CWP local_prepare，再按原公共query取 pathless SourceRef；FF 不探物理目录/数据库。正常active命中仍两次公共调用，旧v1不变，fetch_if_missing/latest沿CWP ensure共享处理不重复prepare。初次 fixture 请求带不允许的 acquisition_limits，已修 fixture 后取得9FAIL/1PASS的真RED；最终204PASS/2SKIP+39subtests。实际三份SEC季度原件 DEI表单空格须由CWP通用提取处理；CN FY24未知日期/缺完整issuer alias诚实gap，不假造4PASS。

OCR诊断确认经营范围/报告定义变化有价值而原 selector未识别；图片行未进入视觉句子完成，且不能套PDF点坐标。源 partial/漏首行保留，不强选纯数字/标题。独立单页真实 initial+replay 在写收据时因旧字段名失败，保留失败，不新增OCR补测来凑绿；最终以完整公共节点验收。

repair 的职责是版本化重做、父账承接与可追溯失败；不是新的人工许可。真实同版本 repair 拒绝，live=false、protected不变；原失败DB/request/marker/receipt保持。已结算失败可在 durable SHA 对照和原始字节保护后只清理独占测试根，失败记录保留。
