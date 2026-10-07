# Findings：当前事实与待验证项

## 2026-10-07 N6-CANDIDATE查收事实

该卡已完成实际合并和远端发布，交接f31cc0d/merge e8c645e均为master祖先，实时精确CI37547043642全绿；本次47短测试通过。原卡交付阶段21/33与后续S7的29/33属于不同版本测量，分别保留。不能拿外线HANDOFF引用的历史DOCSET CI37528050044验收候选代码。Git blob SHA与Windows CRLF工作副本SHA不是同一比较域；11相关源码按正确域全部与已发布aa52cbd一致。

## N4C真实结果与新并行范围（2026-10-06）

- MiMo年报真实summary/consumer通过，招股两次timeout+SUMMARY_INVALID；DeepSeek IR/英文电话会真实完成。故真实能力不是全部失败，也不是四类已过；需针对招股摘要合同继续调查。现只有通用安全错误信息，原invalid draft随finally清理，不能凭记忆推断是哪一条规则。已知actualusage与unknown全部计入，剩23892tokens小于原请求24863最坏预留，不能直接盲重试。
- 三个真实final合计245396 B，不到0.25MB；独立root峰值主要含测试raw副本与数据库，结束全部恢复，不是生产空间反弹。IR needs_review仍可通过RF读，这是质量事实而非权限签收。两批原件、生产事实、配置/owner均保持；完整结果见run05/06小收据。
- N5-DOCSET补半年报/季报/再融资等黄金评估，标准先读原文而非从selector反推；N5-RAW-DUP给原件exact-SHA重复的真实有限实读收益，不删原件；N5-ET-TXT修本地旧文件空/错期也reused、Characters冒充bytes的已证实问题。三个写集独立，不动当前runtime/shared contracts。ET免费Motley被现有policy禁用、FMP发布日缺失不能造字段，不以这个本地TXT修复声称主线免费抓取升级。

## N4C预算阻塞解除（2026-10-06）

- 用户批准待答的160k累计token方案，美元cap未变；不退旧账或降低模型配置。官方MiMo价格仍国内Flash输入¥1/输出¥2每百万，Token Plan与PAYG不互通；DeepSeek官方USD peak输入$0.3/输出$1.2低于既有CNY/FX6保守proxy，沿用旧proxy不记真实invoice。来源：https://mimo.mi.com/docs/en-US/price/pay-as-you-go 、https://api-docs.deepseek.com/quick_start/pricing/ 。中文DeepSeek页首次超时，英文官方页成功，未调用模型。
- 自动审批拒绝此次具体MiMo资料外发，未开始进程；用户原预算答复不能被当作新增目的地外发授权。已明确提示风险、列两家目的地及各自原文，一次UI请求，未重试绕过。不是模型API/凭证故障，未知费用事实不变。

## N4C实际driver计费缺口（2026-10-06）

- 原临时driver与已提交preflight的算法分化：前者固定Oct5，后者glob全部日期并拒绝重复run。已删除driver重复算法，直接复用后者；跨日期、重复run及默认预算不足提前退出均实际验证，0模型请求。临时driver按N4细则可重建，不新增数据库或永久模型参数配置。
- 预算拒绝发生在创建ROOT之前：run05付费收据不存在、测试根不存在；真实累计仍58523 tokens/33884 microUSD、unknown4，不能以“准备可用”声称真实N4C通过。剩余唯一依赖仍是原累计token cap调整答复。

## P5-RF再次交付复核（2026-10-06）

- 新通知对应既有已验收交付a74b9ceb/31fe65e6，没有新增提交或未提交改动。完整交付已包含于本地/远端main6e6b817a；官方CI37391526925仍attempt1 success。原handoff的旧pin/skip问题已经在MAIN节点解决，不重新打开。
- RF独立卡仍误写ready，现改complete并链接正式收据；默认来源读取原件、旧派生退出与后续生产降容已完成。N4C实际模型产物尚未验收，仍是唯一下一节点。最初沙箱读取显示的批量删除均为ACL假象，正常环境确认只有owner两份周日志dirty且SHA不变。

## N4C当前准备缺口（2026-10-06）

- 预检工具061f534已发布，精确CI37400256960 attempt1 success（73秒）。独立准备已完成，尚无预算答复，0新POST；不以“offline verified”代替N4C完成。唯一旧unknown根461338 B、账本425984 B，继续保留，不属于原46GB旧缓存反弹。

- 新preflight已实跑：当前RF6模块CLI help成功，四份原件SHA准确，旧账58523 tokens/33884 microUSD、unknown4/unsettled0。预算输出预留不可满足（1477<8192），费用剩63352microUSD；确认是真实预算约束，不是凭证/CI问题。配置MiMo/DeepSeek flash与现有端点准确，0 provider/POST/download；n4pf根恢复，生产/owner/用户配置不变。临时driver已更新RF SHA及sample-ids可分两批覆盖四类型，未开始POST。
- 首次Ruff报告bootstrap三项E402，已为必要路径bootstrap明确标注并通过；SHA流式读取支持项目Python3.10，不使用3.11新增file_digest。预检不产生新的运行授权文件或控制库，也不声称真实摘要或RF业务实读通过。

- RF main/remote仍6e6b817a，两份owner日志SHA不变。临时provider driver读取原旧AUTO预算（只读NarrativeRunStore）及run02/03/04收据，保留unknown；finally先保存计费再清根。它仍固定旧RF8a153f33、样本只有P07/T01，不能代表节点C四类型完成。
- MAIN先新增可提交的零模型preflight，验证当前RF提交CLI闭包、四原件SHA和真实旧账，复用Config加载器/原Schema，不重复消费者实现。首次literal工具文件inventory无匹配导致rg exit1，无运行故障。累计cap仍待答复，不执行POST。

## S6收尾实读（2026-10-06）

- 完成态：e481578已发布，精确CI37399248994 attempt1 success；38集中测试、12项smoke及当前架构配置GREEN，三个测试根恢复，18当前链接有效。S6complete，唯一下一步N4C；预算答复待定，未开始新POST。保留driver确实存在tmp/n4c_provider_live_driver.py，但RF固定SHA是旧8a153f33，开批前需要对齐当前正式RF并先做零模型CLI导入验证。

- RF远端/本地主线6e6b817a及两份owner日志SHA不变；CWP只保留用户配置dirty。当前README/运维说明推荐已冻结writer和旧模型，control旧Reviewer/lock规则没有运行代码引用，architecture规则仍有实际调用者。两旧cron壳未检查子命令退出且末尾echo假成功。先按s6_documentation_runtime_closeout.md集中收尾，不重复生产清理/长测试。
- 四个当前smoke候选先跑4 passed/0.58s，数量不增加。实读wrapper发现help先加载配置且不显示自身provider/config参数；两项新反例2 RED/0.98s，修复为先输出两层help再退出，无生产配置/凭证加载。误读不存在narrative_model_config.py/source-export-v2.md，仅只读错误，后续定位实际narrative_http_model与v2 CLI。PowerShell写文档多一个EOF空行已修正；ARCHITECTURE真实Git路径为大写，链接按实际路径改。

## 最新交付核对（2026-10-06，覆盖下方历史P5状态）

- 用户再次通知P5-FF/P5-STORAGE完成，实读两份原始handoff及两个干净工作树，tip仍ab9ce33/f8f414a，没有新增交付。FF交付完整为main758e8f4祖先；STORAGE原分支未整支合并，MAIN集成9fa2166为当前master祖先，后续保护/共享引用修复保留，不回退旧实现。
- 实时ls-remote确认FF main758e8f4、CWP master ed86940；GitHub官方API确认CI37385101051、37375836745、37394193179均精确SHA、attempt1、completed/success。沿用已执行的集中责任测试，不再跑长包。生产降容已经完成，以s5_production_storage_acceptance_2026-10-06.json为准；本次没有新删除/压缩/模型或provider调用。
- 修正STORAGE卡仍写ready、并行总包仍写in_progress的过期状态；保留历史施工方法，不再派发。用户配置SHA3609e707…不变，凭证未读。工具环境gh不在PATH，改用无需凭证的官方API成功复核，不安装工具或读取密钥。

## 2026-10-06 — P5-FF / P5-STORAGE交付复核收口

- 用户通知交付后重核原始handoff、Git ancestry与GitHub exact SHA：FF ab9ce33在main758e8f4中，STORAGE 9fa2166在master历史中；CI37385101051/37375836745均attempt1 completed/success。沿用已经执行的集中53个不同case分步GREEN及真实三仓/原件测试，不重复长包、不增加小节点门禁。
- FF外包报告的无预算旧下载fixture与POSIX待验证项已由MAIN修复、真实Linux CI执行；不再作为当前待办。FF仓内MAIN_ACCEPTANCE.md仍保留发布前过程，当前发布事实以CWP正式JSON receipt为准。STORAGE未知parser分类仍由MAIN明确保留/处置，生产删除不由外包签收自动触发。
- 本轮再核原件：AMEC 9,165,875B/d64c4108…，MSFT 66,324B/4ac3b4f0…，与既有签收完全一致；用户配置3609e707…不变，FMP密钥不读。RF新交付已进入干净MAIN整合树，尚未发布；全套PWF修正过期“WIP/无HANDOFF/FF未并线”描述。
- 环境误差记录：此前RF相对路径命令未进入指定目录，出现file-not-found/0 collected，不是行为RED；后续跨仓命令显式Set-Location并验证根。本轮一次PowerShell花括号路径展开语法错误改为逐个显式路径，无项目写入。
- 本轮0生产原件/派生/span删除、0VACUUM、0LLM/provider调用；没有宣称新增释放空间。下一动作仍为P5-RF MAIN整合节点。

## 2026-10-06 S5剩余caller

- tracked AST补足CodeGraph imports：service导入normalizer.backfill_text_fingerprints；__init__为未使用的LLMSummaryError/SectionSlice加载旧writer；三个旧writer依赖normalized_artifact_reader。其他直接调用在tests，历史artifacts不是正式入口。
- 指纹链解析没有复核原文SHA，扫描后换字节可把新正文指纹写到旧source行。分层节点先TDD原文/manifest绑定及解析前后实字节真实性，复用SourceManifest.verify_file，不引入人工门禁。

## 2026-10-05 MAIN模型预检与P5开工

- 新证据：项目config.yaml的非秘密模型配置为MiniMax-M3、base_url=https://api.minimaxi.com/v1。相同当前env key下，国际站GET /v1/models返回401，已配置国内站返回200并列出MiniMax-M3；因此站点不匹配是已证问题。N4C测试端点应复用当前配置国内站，不自动fallback或轮换secret。官方国内文档已重定向到https://platform.minimax.cn/docs/api-reference/text-openai-api，支持M3显式thinking disabled。旧两个拒绝仍按unknown保守留账，不因只读401检查退款或假造供应商usage。

- N4C run02真实CLI已终态，39.106s，采样process-tree RSS峰499,916,800 B，测试树峰21,647,101 B。IR/TXT两个HTTP客户端拒绝留下unknown，年报/招股保守预留denied，synthetic skip PDF parser incomplete；没有任何final，也没有RF真实read结果。明确N4C未通过，不用先前Replay绿替代本次真实绿。
- 本次账本charged23,335 tokens/11,322 microUSD；与旧unknown合计33,660/16,580，剩余26,340/83,420。unknown不是实际账单，也不假称HTTP拒绝收费为0。小型reservation事实已写根外JSON，测试DB/raw/log/worker根全部删除恢复absent。下一步收集安全数字HTTP status（本次driver漏采）、请求准入体积及skip parse错误；不重复paid retry猜参数。

- 用户确认P5三线均已开工，保留RF/FF/新存储工具独占写集。RF正常账号仅两份assurance owner变更，origin/main为8a153f3；N3a公开CLI及reader可读，不切owner checkout。
- 官方MiniMax OpenAI接口说明M3 thinking默认开启且计入输出token额度，支持显式disabled；不能使用reasoning_effort=none。适配器先解析content再usage，真实同型fixture证明finish_reason=length且content=null丢失usage。未保留旧provider正文，故这是已证代码缺口，不断言旧失败必然属于此型。来源：https://platform.minimax.io/docs/api-reference/text-openai-api。
- RED：10 failed/4 passed（null截断与新thinking配置）；旧unknown仍10,325 tokens/$0.005258，新批累计剩余49,675/$0.094742。修复须保留省略thinking时旧请求hash、绑定显式模式并贯通child factory，不清未知费用、不扩大上限。
- 两项读路径猜测错误已校正：NarrativeModelRequest位于narrative_model.py；RF读取须git show origin/main:scripts/narrative_source_preparation.py。一次patch因request_bytes实际已有payload局部变量而未应用，读准确代码后重做，无部分写入。

> 2026-10-03已采纳激进方案。完整历史已保存在固定Git版本：https://github.com/zhengcb81/company-wiki/blob/bff81afe7cbb11c895764a94c2eabd121539e248/docs/plans/narrative-evidence-pilot-2026-09-26/findings.md；当前不恢复旧门禁/审批/重复任务。

## 已验证事实

- P0已移除private/public读禁令、外发人工许可、prompt人工审核阻断、RF人工发布与缺fixture hash不可闭环；清单状态详见gate_permission_inventory_2026-10-03.md。
- Work Unit/shadow/gold退役候选约2102行/81.7KB，主要维护收益。gold是placeholder，叙述runtime实际只注册select/summarize/verify。旧全局parse/LLM锁才是真实吞吐障碍。
- 旧control.py被ensure/close-gap和AUTO runtime共同调用，不能先整文件删除。通用BLOCKED_HUMAN历史枚举/Store记录可兼容读取，无需DROP表。
- 当前verify/projection/consumer依赖完整bundle；首版只去重复attempt/outbox正文，唯一final短引用保留。冷文档metadata_only不等于全文索引覆盖。
- 完整stat32,821,613,206B/32.82GB；公司原件25.20GB、current DB3.06GB、旧derived/index约2.87GB。已释放13.06GB，24历史测试根已清。managed约0.27GB实际仍在，不计释放。
- FF两安装位置三个脚本同c47c397字节；SKILL仍有旧示例。v2 acquisition_limits仅validator未转执行；ET旧scraper未共用modern provider入口。修真实执行路径，不造人工许可。
- 远端代码CI最近约56–62秒；此前慢因全coverage/全Contract，已退出日常链。更激进目标取消commit pytest与无关config doctor，不随机删廉价Unit。
- PWF旧三入口581351B，压缩的是上下文负担而非GB占用；历史通过Git追溯，无复制归档。

## 本轮责任/缺口

- 2026-10-03 再核 RF：当前可读 checkout 为 `fcap@5319ee263c4af41ac255938c25bebd32cce56f66`，与 `origin/main@6fb2def709d13bda9cfada7ecf62bfc0e3744ae2` 不同。当前 checkout 的 tracked diff 包含大量 `.planning/2026-09-19-three-project-history-audit/execution_runs/**` 删除；按 owner 隔离全部保留，不清理、不合并。只使用本次命令的 `safe.directory` 参数读取 Git，未更改全局配置。RF PWF 主目录为 `.planning/2026-09-19-three-project-history-audit/`。CodeGraph 未能定位正式 pathless read receipt 契约，需直接从 RF main 的规范文件核实后再复用，不从记忆重建接口。
- 直接读 RF 当前可见的 `scripts/contracts/evidence.py::validate_source_capture` 与 `scripts/contracts/document.py::validate_sources` 后确认：RF 消费侧正式验证的是带 `source_id` 的 HTTPS source，含标题/发布者/页节、published/accessed date，以及 capture schema/method/tool call id/captured date/snapshot SHA、`untrusted_data_only`、prompt status、host receipt 和 capture receipt SHA；evidence claim 再绑定 source id、snapshot SHA 与 capture receipt SHA。该合同定义来源身份、时间与字节快照绑定，没有给出 company-wiki 数据湖路径字段。CodeGraph 的名称查询并不能证明存在单独 pathless reader API；跨项目实现应保留 RF 这个消费文档合同，并继续查清是否有独立 reader adapter，不能把 URL/capture receipt 误称为完整读取接口。
- **更正（以 RF 当前 `origin/main@6fb2def7` 为准）**：上一条读的是 `fcap@5319ee26` 旧工作树中的旧 `source_preparation.py`，因此不能据此断言 RF 没有 pathless reader。`origin/main` 已包含 `scripts/narrative_source_preparation.py`，消费 CWP 发布的 `narrative-read-request/1`/`narrative-reference-request/1`，由 `company_wiki_narrative_reader` 做 pathless source read；CWP 2026-10-03 G-C 收尾报告记录 RF main 与真实年报/英文 TXT 跨仓端到端回归。RF 的正式 source/capture contract 仍负责输出 source id、URL、日期、snapshot SHA 和 receipt hash；两种 DTO 在不同边界承担不同职责。
- CWP 侧 `SourceRef`/`SourceRefValue` schema `2.0` 仅含 document/source ID、内容 SHA、字节数、MIME；`VerifiedContent`/`VerifiedVersionReceipt` 在读时重新核当前 catalog/root/read policy 并核原文字节 SHA，receipt schema `2.1` 含 read-at、policy hashes、review snapshot。实际调用已进入 narrative select/verify/batch、transport 和 SourceExport v2；CodeGraph caller 索引有漏报，按符号搜索与源码路径核实，不据其“No callers”报告判定未使用。RF legacy `source_preparation.py` 的 artifact bundle 绝对路径读取仍存在于旧路径，G-C 新 reader 并不自动退役该旧路径；本计划复用已发布的新 consumer API，不重建、不修改 RF。
- FF-S3 调用点已核实：`_command_arguments()` 在每个 ensure/close-gap argv 附上 bytes/seconds/cost，v2 `source_ref_v2` ensure 和 v1 close-gap 都复用该函数；`_shared_deadline()` 又把请求timeout合入全链共享单调deadline。CWP CLI因此能收到请求上限。真正断点位于CWP内部：`JsonCommandAdapter` 无 bounded discover/fetch，Dayu CLI无 bounded方法；CWP预算模式必须在 provider 子进程/HTTP外发前拒绝，不能声称参数透传就有响应体硬限额。
- CWP `JsonCommandAdapter` 的 bounded bridge 已按固定的 `acquisition_budget/1.0`（剩余字节、秒数、美元字符串）和 `acquisition_usage/1.0`（本阶段实收费字节/成本）合同实现本地未提交WIP。bridge要求provider usage字段精确、收费累计进入单个CWP预算，并用fetch收据字节再校验；普通无budget调用保留旧命令。专项进程测试行为RED为三个 `discover_bounded` 缺失失败，GREEN后3项通过。这个 bridge 仍不能使未实现该JSON合同的StockInfo provider自动变安全，需在 provider CLI与HTTP读流接上之后才启用。

- S0退役专属测试时保留混合文件的真实环境隔离/原件保护/故障失败反例；依赖gate_runner的helper迁到已有clean_env_gate/test-only helper。
- N4在推进：scope和模型/预算基础9ccd29f已发布；正式CLI/coordinator与terminal降容首组67绿，跨run/统一owner/父kill/ACK还需收口。测试Replay不是真实provider能力。
- B2当前有normalized/旧summarizer/RF兼容引用，逐caller迁移/退休后可分批删，不需全仓重做摘要。
- 当前DB可回收量、exact-SHA原件重复量、1/2/4并发真实收益均未测；不外推5000份算术为实际体积。
- 默认published-asof、最小配置fingerprint、partial规则会改变公开行为，先写来源/consumer反例再实现，已有hash错配/身份冲突仍失败。
- 应用goal卡最新实读active；旧paused/无resume工具是历史障碍，当前执行持续恢复。

- v4 owner恢复事实：旧v3启用gate没有可安全推导的run owner，因此升级后保持未绑定并拒绝接管；显式pause后可由明确run启动建立归属。父进程被kill后generation改变使旧attempt失效；仅在attempt持久finished且reservation仍reserved时结unknown，reserved费用保留。原子提交后ACK丢失的重试读取已提交状态并no-op。

## 环境约定

Git写入/联网用正常用户，sandbox .git只读不是产品权限。测试创建/运行/finally清理同OS账号；用短独立根，生产config不能作fixture。外仓owner dirty保留，记录ref后隔离操作；不改全局ACL/safe.directory。

## 新实施事实

- 旧工程/Gold/HumanInbox/shadow真实入口与专属测试已整套退出；通用BLOCKED_HUMAN历史解码和Store恢复原语保留。S0 reviewer只是actor记录，原件/身份/哈希仍验证。
- N4A scope已贯通所有批内状态修改与prepared SQL-before-LIMIT；root1161项集成全绿。scope外父依赖只读，不会因为本批维护修改外部子任务。
- 未知发布日期索引验证的JSON数组/acquisition数组原先AttributeError，经4 RED反例收敛metadata_state后具名无匹配/正确好行回查，实际身份/SHA/公开日期条件保持。
- 数字复杂度门已退出，commit不再pytest，config检查只相关变更；PWF旧三入口历史由Git固定版本恢复。剩余prompt诊断/旧archive工具和外仓数字coverage按S3/S6处理，不把未实现项记完成。

- S0/N4A ff5396c已发布，CI37131769647 success/job53秒。S2公开接口的生产装配暴露了真实Reader Protocol dict协变问题，已收敛Mapping；泛化接口让真实对象可直接装配。
- selector漏召回：英文管理层entered two new markets / signed pilot agreements未选入，candidate_count=0并needs_review；S3用独立真实样本验证召回改善，不为factory正例强行放宽shared规则。
- 新run持久预算只保ID/hash/费用/用量，不保存prompt或原文；actual usage超声明仍记账并停后续外发。缺key证明未调用为0，transport/timeout未知保持占额。

## 并行实施的新调查（2026-10-03）

- FF origin/main实际c47c397，常用根仍fcap d35b6f5；已安装脚本同c47，SKILL仍旧v1。acquisition_limits三字段仅validator；ensure/close-gap producer尚无三caps CLI，新I1接口由root实现。FF可以独立改透传/deadline/安装面/说明，生产限额联调pending不伪报。
- ET tracked干净4924d57，现代工具已交付；旧scraper仍defaultFool、直接Session/旧v3/吞异常、默认翻译，FMP list会落下载/翻译、dry-run未定义变量，计划模式先写目录。ET独立包收敛这些真实路由，不重复实现W wire/importer。
- StockWiki已aa98848且四项quick-scan CLI/maintenance/test dirty，IQS44b805f正在W07后续；不开第二线。RF四dirty保留。新三外线专属工作目录互不包含，不写共同PWF/全局安装。
- S5/S6适合独立只读审计workspace：B2实际调用者、dbstat/freelist/保留事实、SHA候选物理重复量；真实删除/收缩统一主线。不重新hash25GB、不完整备份恢复、不把既释放13.06GB再计。
- cross-run缺口已RED→GREEN：verify effect绑定job+bundleSHA、工件work-key/2绑定effect，三run真CLI发布/同正文去重/旧pin回读/同run零POST均过。旧effect保work-key/1使prepared可恢复；不放松Store immutable冲突。
- owner实读纠正：当前没有独立AUTO生产daemon CLI，factory已严格固定run.scope；generic scope=None只库兼容。真实风险来自catalog Worker/once/start/resume/startup与全量normalize/run，和batch owner互不相认；生产control paused，任务启用状态人类账户待查。最小run行generation绑定+CAS和OS mutex分别解决恢复归属/活进程事实，退出旧实际caller，不加泛化人工门或FF下载长锁。

## 2026-10-03 — legacy Worker 现场与退役证据

- CWP 正式 `worker-status` 只读返回：`desired_state=paused`、`runtime_state=stopped`、production/temp/foreign worker 与 supervisor 均为空；startup task `installed=false`。因此移除 launcher 与控制菜单不会让已安装任务或活进程失去入口。
- 旧 Worker 对外执行链已不在 parser/CLI/Windows launcher：全库 normalize/summarize/run、worker one-shot/daemon、start/resume/pause、startup install 已移除；状态/身份安全 stop/startup query/uninstall 作为迁移期清理接口保留。`ensure --allow-download` 和 close-gap 的 acquisition 不再依赖全局 paused 状态，但FF兼容开关暂保留 no-op。
- 生产 catalog/config/raw/worker-control/runtime/数据库在改动前后未写；改动只触及 tracked source、README、操作文档和测试。
- Windows 启动链及旧启动测试此前以 4,000+ 行实现/测试维护；本批删除无活动调用者的 UI/launcher/bootstrap 套件。process inventory、进程身份与 stop 行为的合同测试仍保留。

## 2026-10-03 — ET-S3 交付审查与 producer 限额核实

- ET-S3 handoff: branch `codex/et-s3-bounded-runtime`, base `4924d57`, delivery `66557c6`, latest `53e1e60`; external worktree clean. ET-specific offline group independently passed 87 tests, `/2` goldens 10/10, Ruff clean. Full suite was 150 passed / 1 failed: unchanged translator-factory test requires an available LLM backend; this isolated runtime fell back to Google. No live API/key was used.
- ET-S3 remains pending one contract correction: `--max-seconds` is documented as total batch duration but blocking connect/read can overrun its deadline; the 1-second minimum and request-library connect/read timeout semantics do not prove a hard wall-clock cap. Explicit `--translate` also runs outside that retrieval budget. ET's task_plan still says stages 2–5 not started and progress says waiting to commit/push despite the pushed handoff. Do not report the cap as hard or the PWF as closed until reconciled.
- RF status check: `rf-impl main/origin/main@6fb2def7` includes N3a narrative consumer and two pipe/descendant deadline fixes. Four pre-existing execution-evidence files remain dirty due line-ending changes; left untouched. Keep using RF's committed versioned pathless reader/receipt; do not reimplement a second consumer or edit its dirty workspace.
- FF-S3 is actively implementing its frozen `ensure`/`close-gap` flags in the isolated `filing-fetch-s3-limits` worktree; do not touch that worktree or claim integration before its handoff.
- Provider capability evidence changes the CWP implementation design: `StockInfoDLSimple` CNINFO `fetch_pdf` calls `response.read()` before writing the PDF and exposes no caller byte/cancellation argument; Dayu SEC `_http_download` returns a fully materialized `bytes` response and has no byte-limit argument. CWP `DayuCliDownloadAdapter.discover()` invokes a range `download` subprocess, polls every 3 seconds and may stop it after candidates appear; it is not metadata-only. Adding CLI flags or checking `DownloadReceipt.byte_size` after the fact would not establish provider-response byte caps.
- `CloseGapTransaction` performs provider-backed latest-as-of rediscovery before and inside its lock, then an exact staging acquisition; because current Dayu `discover()` performs downloads, revalidation may repeat body egress. Before adding caps, separate metadata discovery from fetch or fail closed unless a provider transport consumes the same operation budget. Resource caps stay outside `SourceRequest.identity` per FF contract.
- Owner boundary update (2026-10-03): Dayu is an external project and must not receive code changes. The one pre-existing tracked SEC downloader edit was restored to `HEAD` at the owner's direction; the unrelated untracked `docs/architecture_report.html` was preserved. CWP must work with Dayu's existing contract or reject a Dayu-backed request before network egress whenever a hard response-byte/deadline budget cannot be enforced. A post-download size check, subprocess polling, or CWP-only flag is not evidence of a hard provider cap. No Dayu worktree or source edit is authorized by the current plan.
- StockInfoDLSimple remains separately authorized for a narrow budget-capability change, but its current worktree contains a large uncommitted company-wiki adapter integration, including the CNINFO transport module. Do not edit that original worktree or create a cap change against an assumed clean interface. First identify a safe isolated basis that includes the exact adapter code under review; otherwise finish CWP work with CNINFO fail-closed and record the provider gap for the adapter owner.

## 2026-10-03 — FF-S3 与 SPACE-S5 交付复核

- FF-S3 branch `codex/ff-s3-single-request-limits@8f17cbd` 已推送至 `origin`。提交包含快 pre-push gate 与单次精选 CI 回归方案；本地 responsibility/regression set 为 358 passed、4 skipped、78 subtests，独立 CWP SourceRef CLI E2E 为 1 passed，正常 push hook 的 Ruff/compile/import/mypy/config/plan/BOM 检查通过。`gh` 不可用，GitHub Actions 页面读取也未取到数据，所以远端 CI 记为 unknown，不冒充绿色。
- FF-S3 暂不合 FF main：CWP 参数/限额当前只进入 CLI/WIP budget path，生产 CNINFO/Dayu 传输没有 bounded capability；v1 `--allow-download` 与 `latest_as_of` 的限额承载/只读复用语义也需要 root 确定。Dayu 不可改；无真实 provider 上限时必须在外发前 fail closed。
- SPACE-S5 `storage-audit/1` 报告及15个只读工具测试通过，明确 `production_mutations=[]`。无活动代码调用者的候选共 138,648,023 B；`derived/` 实测 2,826,010,634 B 有生产 reader 和 8,191 条 artifact 路径引用；DB 3,055,800,320 B、freelist 0、evidence_spans 家族 2,833,915,904 B 且全部为 active 文档。只能将报告用于分批计划；没有执行删除、VACUUM、生产回写或全量原件重 hash。审计期间代码 HEAD 移动，root 真正实施前仅重核受影响调用者与集合。
- CWP 临时测试目录清理限制：此前一组 33 项 producer-budget 测试在 `%TEMP%\\cw-pytest-basetemp\\20261003-210201-7b69b511` 留下3个测试文件（402,088 B）；Windows ACL 拒绝清理，包括一次已授权 elevated 尝试。没有改 ACL/接管所有权，路径不在生产仓；将此列作明确的临时数据清理异常，不能声称目录恢复完成。
- CWP `AcquisitionCoordinator.resolve_or_stage` 的原二次检查只比较 `receipt.byte_size` 与总上限。新增 under-reporting adapter RED 用例证明 discovery 已先用20 B、下载回执21 B、总上限30 B时仍会被旧代码放行。现在以下载前后的 `response_bytes_used` 差值核回执收费，并校验文件大小不超 discovery 后剩余额度；该防线不能替代 adapter 在流读取时逐块计费。CN `JsonCommandAdapter` 和 Dayu CLI adapter 在预算模式下都在子进程启动前 fail closed。5文件责任包35 passed，Ruff/diff clean，短测试根已移除。
- 本次检查的 StockInfoDLSimple checkout 为 `v2-clean-rewrite@1693045`，含24个tracked修改和额外未跟踪源码/测试；本次未写入。其现有未提交 `CninfoAnnouncementClient.fetch_pdf` 仍用 `response.read()` 后才写文件，没有字节/期限额。要继续适配，必须先形成不覆盖该 owner 状态的隔离快照；之后对 discovery JSON 和 PDF body 都按同一预算流式计费。Dayu 代码不动。

## 2026-10-04 — CNINFO provider transport 与 CWP budget bridge

- 在 StockInfoDLSimple 隔离分支 `codex/cninfo-bounded-budget@947e839`（父提交 `1693045`）完成 bounded CNINFO transport：discovery JSON 与 PDF 响应按块计量同一预算，报告 `acquisition_usage/1.0`；提交仅含13个相关源码、fixture和测试文件。原 `v2-clean-rewrite` owner 工作树未写入或清理。随后通过GitHub公开API确认该远端ref精确指向 `947e839`，`v2-clean-rewrite` 仍指向父提交 `1693045`；provider仓未发现Actions workflow。
- provider测试此前按最终focused集合 **61 passed**；本轮另外跑的51项到达100%但pytest未打印结束摘要，Python进程仍占CPU，故中断退出阶段。这次补跑不计作完整新绿。改动文件限定Ruff检查通过，`git show --check HEAD`通过；对全 `tests/` 跑Ruff会出现19个既有无关lint问题，不据此扩大清理范围。
- CWP当前bounded JSON桥接、真实子进程deadline、usage/partial usage计费与fetch receipt复核责任集 **38 passed**。跨仓E2E使用真实CWP预算服务 + StockInfo CLI/client，仅HTTP响应被测试桩替代、不访问外网或生产目录；发现1个候选，PDF为399 B，discovery+PDF总计713 B，与provider上报及CWP扣费精确一致；临时root已回收。
- CWP生产配置仍是 `stockinfo-cninfo` 1.1.0 且没有 `supports_acquisition_budget` 声明；能力默认false。因此当前生产严格限额路径仍fail closed。只有provider分支进入其owner集成工作树后，才能将CWP配置切到1.2.0并明确启用，随后完成FF正式入口E2E。Dayu未改，继续拒绝无法真正施加硬下载上限的请求。
- 本轮一次补跑在 `company-wiki/.t-cninfo-provider-final` 生成的模拟文件/测试staging已按目录内均为本轮pytest fixture确认后删除；CWP 38项回归的basetemp hook将测试根重定位到`%TEMP%`且自动cleanup失败，实测仅18个测试fixture、987,840 B后按精确路径手动删除。两处测试根均确认不存在；真实原件、生产DB、source catalog和provider原工作树未变。
- 继续复核发现计量边界缺陷：provider失败回执在deadline刚过时才到达，旧`consume_response_bytes/cost`先执行`ensure_open`，导致已发生响应流量/费用未记入CWP budget。先加入两项测试，旧逻辑均RED；修改为`ensure_open`只阻止后续请求，usage消费方法始终记录已报告用量、仍独立执行字节/费用上限。最终六文件责任集 **41 passed / 14.83s**，Ruff与diff check通过；短basetemp `.t-bud`经finally清除。
- CWP本地commit `288b02857d0a27b5622fb96c9e2156b6132a0deb`（父 `ba71ed4`）已推送到master；push前本地快smoke gate绿，远端Actions run `37162544905` 对应同一SHA且 `completed/success`。工作树干净。`gh` CLI缺失，CI由GitHub公开REST API核实。
- StockInfo远端ref盘点：`v2-clean-rewrite`=`1693045`，bounded分支=`947e839`且以其为父；默认`main`=`6df45a1`。GitHub compare API返回main与v2-clean-rewrite无共同祖先，因此不能将v2功能当作普通PR直接合到默认main。CWP配置原本指向v2路线；后续沿v2 owner集成线推进，避免全量恢复未提交功能WIP。

## 2026-10-04 — FF→CWP→CNINFO 真实数据闭环与 FF 主线合并

- StockInfo隔离 provider worktree `codex/cninfo-bounded-budget` 当前提交 `8ed5fdd`，在原 `947e839` 限额实现上修复 JSON CLI stdout 污染：日志handler写入stderr，stdout只含一个JSON响应。provider责任集62 passed / 0.87s，`git diff --check` clean；提交已推送到其远端支线。原 `v2-clean-rewrite` owner工作树保持隔离，Dayu仓未改。
- CWP `config/source_acquisition.yaml` 已切到 provider 1.2.0隔离路径并声明 `supports_acquisition_budget: true`。`load_acquisition_config()` + `build_registry()` smoke通过，HK/US配置保持不变。
- 正式端到端使用公开真实BYD FY2024年报及真实CNINFO网络响应，预算100,000,000 B / 240 s / $0。FF-S3 v2 exact `fetch_if_missing` 返回 `source_candidate/downloaded_new`，单次下载10,092,140 B；SourceRef SHA-256 `e9c2d7fdd088e151ccb6c8ad3d95587b2b014b10f2c9731508d23ce07fde4de3` 与raw PDF实际字节/hash一致，journal只有一次 `downloaded_new`。
- 同一临时root中的 `latest_as_of + reuse_only` 使用5,000,000 B / 90 s / $0额度完成元数据查询，返回GAP且missing/newer_revision均为0；journal为 `gap_plan`，原件清单/hash没有变化。legacy v1 exact reuse返回 `capture_ready` 且没有新增下载；legacy v1缺件加 `--allow-download` 但无额度参数时以返回码2失败，且没有写公司文件。所有临时root由finally清除，生产配置与CN identity snapshot指纹前后不变。
- 真实E2E首轮发现provider CLI logger向stdout写日志、破坏单JSON协议；新增回归并修复后重跑62项provider测试及E2E通过。CWP acquisition/来源适配器精选集32 passed / 18.08s。
- FF-S3发现 `latest_as_of + reuse_only` 仍查询provider元数据，因此必须要求并转交request ceilings；新增TDD合同覆盖限额转交、缺限额拒绝且不增加 `--allow-download`，exact reuse不产生采集上限参数。FF focused集23 passed / 11.72s，pre-push本地检查全绿；提交 `5b9a8c1` 将远端FF main从 `c47c397` 快进到新头，本地 `filing-fetch` owner工作树也从祖先提交快进同步。未跟踪 `config/FMP_API_KEY.txt` 未被读取、暂存或覆盖。

## 2026-10-04 — FF Actions Linux mypy 根因与修复

- 纠正前一条根因判断：GitHub Actions Runs #52 (`37166994628`)、#53 (`37167094753`) 和 #54 (`37167803001`) 的公开 Jobs API 都明确显示 `Strict type check on public contracts (FC-1204-c)` step 7 failure；pytest步骤被跳过。匿名网页隐藏job日志，本地 fcap 的安装清单测试确有另一个环境假设问题，但它并非这些远端运行的失败原因。
- 用本机 Python 3.12.12/mypy 1.19.0做Linux目标复现，精确报错为 `scripts/transcript_tool_transport.py:100: Module has no attribute "CREATE_NO_WINDOW" [attr-defined]`。Windows分支本地类型检查通过，掩盖了Linux平台对可选 subprocess 常量的缺失。
- TDD先加 `test_creationflags_handles_a_missing_windows_constant`，旧代码在模拟Windows常量缺失时RED (`AttributeError`)；改成 `int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0` 后GREEN。随后Python 3.12/mypy 1.19指定 `--platform linux` 与CWP runtime `PYTHONPATH`复核成功。
- 完整FF workflow精选pytest命令 **361 passed / 5 skipped / 78 subtests / 48.97s**；FF正常pre-push gate全绿。`1d0c73c` 已快进推到FF main，fcap本地工作树同步且未跟踪API key保持原样。Actions #55 (`37182527153`) 已 completed/success；远端真实workflow通过。
- 独立修正：安装清单credential测试由 `2936ad1` 改为在 `tmp_path` 使用假key；这修复了本机有key的工作树上测试先决条件脆弱，但与GitHub远端mypy失败无关，不能将其记作CI根因修复。

## 2026-10-04 — StockInfo 原工作树 WIP 审查

- 用户明确要求核对 StockInfoDLSimple 未提交改动并清理不需要项。CWP `config/source_acquisition.yaml` 当前实际引用 `../StockInfoDLSimple/v2-clean-rewrite` 的 1.1.0 JSON CLI；因此恢复掉当前checkout中 adapter、CLI、CNINFO client 等未提交文件会使该配置失效。bounded commit `947e839` 虽已存在于独立分支/远端，但尚未切入配置所指目录、CWP也未切至1.2.0。故未做全量 restore；保留功能性代码、测试与夹具。
- 相关回归 **88 passed / 19.96s**：下载器、CNINFO API、真实/合成fixture合同、company-wiki adapter与CLI。全局 pytest plugin autoload 首次因 `langsmith` → `pydantic_core` DLL import 权限错误无法启动；仅本次命令禁用自动插件加载后通过，没有改测试配置。`git diff --check HEAD`通过。
- 清理项限于：`lookup_a_shares.py`（硬编码读取company-wiki物理目录并生成已存在名单，违背pathless来源接口）、`reorganize_downloads.py`（未被调用且会按文件名无hash删重，目录分类已由`save_subdir`完成）、确认0字节的意外 `nul` 文件；另将11个仅有无用import/格式调整的tracked文件恢复至当前HEAD，index未动。保留 README 使用的 `a_share_companies.txt` 与研究目标 `companies.txt`、fixture捕获脚本、适配器和功能WIP；未触碰任何下载原件。StockInfo工作树仍有未提交功能改动，需在其owner集成节点再审查/提交。

## 2026-10-04 — FF-S3 技能安装同步

- FF 主仓 `SKILL.md` 已推荐 schema 2.0、pathless `source_ref`、单次 `filing_intent` 与请求内 `acquisition_limits`；两个实际安装副本（`.agents/skills/filing-fetch`、`.codex/skills/filing-fetch`）此前各有10项manifest漂移，仍展示旧的1.4/v1.1说明和运行脚本。
- 用 FF 仓库显式 allowlist 安装器同步两个实际目标：安装后各 **MATCH 11 files**，二次 `--check` 也全部匹配。安装器按manifest清理的旧测试夹具/cache仅位于这两个 skill 子目录；FF `fcap` checkout 的未跟踪 `config/FMP_API_KEY.txt` 保留，未读取或改动。
- 这只闭合了技能安装面。S3 获取默认和缺失关键元数据时的 latest-as-of 语义，仍需按来源合同核对并记录后才能关闭该阶段。
## 2026-10-04 — latest_as_of 缺失发布时间语义

- `SourceResolver` 在 identity、年度/表单匹配后，若来源 `published_date` 缺失，会记录 `published_date_unknown` 并跳过该候选；若没有任何可用的带日期匹配、但存在此类候选，结果为 `AMBIGUOUS / matching_sources_have_unknown_published_date`，不会把它猜成“最新”或按mtime补日期。
- 已有测试覆盖latest选择、as-of cutoff、gap不fetch；reason taxonomy注册了unknown-date reason，但没有直接钉住“只有无发布时间匹配来源”的resolver合同。该缺口值得用一个短合同测试补上。
- 此行为与字段性质一致：`published_date` 是 latest-as-of 的核心时序条件；可缺失的非核心描述元数据可以保持未知，不能因此弱化latest判定。旧总计划短语“缺元数据partial”需要在收口时拆清两种语义。
## 2026-10-04 — latest_as_of 回归验证与本机 pytest 隔离

- 新增 `tests/contract/test_source_catalog_latest_mode.py::test_latest_as_of_does_not_guess_a_missing_published_date`：把匹配来源的 `published_date` 置空，断言状态为 AMBIGUOUS、无返回handle且诊断包含 `published_date_unknown`。现有实现通过，无生产代码改动。
- 默认 pytest 首次被全局 `langsmith/pydantic_core` DLL加载失败拦截；禁用自动插件后又因受限的默认 `%TEMP%\pytest-of-郑曾波` ACL在tmp_path fixture阶段失败，未进入测试。以仓内唯一短basetemp `.tla-1004`、禁用外部插件及cache provider后，latest mode责任组 **4 passed / 0.75s**；短根finally移除。pytest hook初次重定位创建的唯一临时根也已按精确路径核对并清理。
- 仅剩 pytest.ini 里的 `asyncio_mode` 在禁用插件时显示既有unknown-option warning；本次不改全局/仓库pytest配置，避免把环境问题误诊为项目行为失败。
## 2026-10-04 — R2/R6 细则核对

- 原激进方案中的R2明确要求：读取只用SourceRef、一次verified-open；read-policy pin应绑定本次来源/存储实际依赖与相关配置，避免无关root/runtime变化让原文失效。R6要求普通请求按公开发布日期as-of；缺非核心描述字段或局部解析/引用失败标partial/coverage；真实identity/period/hash和发布时序仍必须正确。
- `SourceResolver` 的unknown `published_date`路径不是通用partial：它跳过无日期候选，仅有这种候选时报告AMBIGUOUS；新测试已钉住。`finalize_selection` 的可用partial由 coverage 不全或候选被预算省略产生，不能用它替代来源时序事实。
- 读取层已具备pathless `VerifiedVersionReceipt`（source IDs/SHA/size/read time/read-policy pins）；具体read-policy hash到底只纳入实际依赖配置、是否排除无关字段，仍需查看实现和变更反例测试，才能评价R2是否完成。
- 一次审计命令将 FF 仓库测试路径误从CWP cwd读取，收到FileNotFound后转回正确仓库；未改文件、未运行任何测试或writer。
## 2026-10-04 — read-policy 指纹范围待收敛

- 实读 `source_read_policy_sha256()` 发现：当前fingerprint把 `asdict(CatalogConfig)` 全量canonical JSON与runtime snapshot SHA一起hash。现有测试覆盖 admission dimension 与 runtime snapshot的变化，但尚未见无关配置变化保持fingerprint稳定的反例。
- 这比R2目标“绑定本次读取真正依赖的root/admission/激活配置，忽略日志批大小等无关变化”更宽。须列出 `CatalogConfig` 字段并区分读资格/根绑定字段与运行参数；再用正反两类测试确认，不能直接删掉根/激活/来源hash相关校验。
## 更正：read-policy fingerprint 字段范围

- `CatalogConfig` 当前仅含 `project_root`、`catalog_dir`、`roots`、`reusable_root_kinds`。`RootSpec` 中还含路径、根类型/顺序、重用资格、路由、大小/状态/文档种类、adapter、symlink及sidecar解析等root约束；没有日志格式、批大小或模型运行参数。
- `test_source_read_policy.py` 明确覆盖privacy、max size、allowed status、symlink、routes、adapter version、sidecar suffix和encoding改变时pin必须变化；这些均被当前来源发现/解析策略消费。因此前条“可能超宽”尚无具体反例，不能只因使用 `asdict` 就判为架构缺陷。仍需看runtime snapshot是否把不影响读取的更新时间纳入hash；只有找到真实无关字段后才加稳定性反例并考虑收窄。
- CodeGraph对两个测试函数名未返回节点；已改用项目测试源文件和 `CatalogConfig`/`RootSpec` AST信息核实，不影响代码或测试状态。
## Runtime fingerprint 具体反例候选

- Runtime snapshot的 `snapshot_hash()` 把除自身SHA外的整个payload做canonical hash；`source_read_policy_sha256()`再把该snapshot SHA纳入reader pin。payload当前含 `updated_at`，所以只更新时间但不改变epoch/cohort/flags/policy hash，也会改变reader pin。这是已确认的非读取字段候选，和R2“无关变化不使来源失效”直接相关。
- 不立即重构：先读Resolver实际消费哪些activation字段，再加一条RED反例，证明只更新 `updated_at` 应保持reader pin，而current_epoch/cohort/影响读取的flag/policy变动必须改变。随后仅收窄reader-specific fingerprint；runtime_snapshot自身wire/存储哈希和现有运行合同不改。
## 2026-10-04 — Runtime reader pin 的实际依赖字段

- `SourceResolver`通过 `resolver_visibility()` 只消费 `v2_resolve_active`（选择v1/v2 reader）、`current_epoch`、`active_cohorts`、`legacy_bridge_enabled`。`SourceReader`另校验runtime `policy_hash` 与当前RootPolicy 2.x导出相符。
- 但当前reader fingerprint取整个 `snapshot_sha256`，连同 `updated_at`、v2 scan/persist/bundle等不参与这次SourceRef resolve/open的flags一起绑定。故“只更新时间/扫描激活切换使旧read pin失效”是明确的不必要耦合。
- 实施方向：保留runtime snapshot自身完整hash与加载校验；仅将reader专用pin改为对`schema + policy_hash + resolver_visibility有效值`计算canonical fingerprint。先写RED测试：更新时间及非读取flag不改变reader pin；reader/epoch/cohort/bridge/policy真正变化必须改变。
## 2026-10-04 — 收敛 reader-specific policy pin

- 新合同RED证明纯 `updated_at` + `v2_scan_shadow` 变化会让旧SourceRef read pin意外失效。增加共享 `resolver_visibility_projection()`，由resolver与fingerprint共用，有效读取投影为reader模式、current epoch、active cohorts和legacy bridge；fingerprint另绑定snapshot schema与RootPolicy hash。runtime snapshot的原始完整SHA、加载校验及SourceRef真实字节验证保持不变。
- 有效runtime flags负例确保scan-shadow独立变化不影响pin；epoch/cohort/reader mode/legacy bridge变化必须影响pin。新相关合同通过。
## 2026-10-04 — FF/ET companion contract review

- Canonical FF v2 and the newly synced installed skills expose `companion_transcript` as an independent result. Fetch requires exact FY+Q and its own byte/time/cost caps; annual FY alone never invents Q4. Transcript language stays as published, no translation; failure/config absence does not undo a filing. `EARNINGS_TRANSCRIPTS_TOOL` is the explicit entry point; `"0.00"` means zero provider calls.
- FF has subprocess transport tests and offline companion tests. A live ET→CWP import through the real tool has not yet been evidenced in this session; check tool availability/owner state before deciding whether it can be safely added to the next real-sample batch.

## 2026-10-04 — pathless virtualization and gate status snapshot

- CWP's pathless `SourceVersionReader` / SourceExport v2 is already consumed by RF main and StockWiki; the plan has real cross-repository consumer E2E receipts for annual-report and transcript-text examples. This proves the common read boundary works for those consumers, not that every legacy caller/provider or the live ET tool import is complete.
- S3 has stronger evidence than the 2026-10-03 gate baseline: FF request limits reach CWP, bounded CNINFO discovery/download is implemented, and the real BYD FY2024 flow verified downloaded PDF bytes, `SourceRef` hash/size, reuse-only metadata lookup, and legacy exact reuse. HK/US Dayu remains fail-closed where the provider cannot enforce the cap.
- Gate simplification is incomplete across repositories. CWP has just retired unused AUTO approval model/store APIs while preserving old table data. StockWiki's `check_all.sh` invokes one coverage-wrapped pytest run. RF, StockWiki, and IQS working trees are owner-active; use their current plan/receipt and read-only inspection, no overlapping edits.
- The gate inventory's 2026-10-03 section 6 is a historical snapshot. In particular, deletion-manifest code is already absent, FF request-budget wiring has advanced, and N4A/N4B are implemented; use the 2026-10-04 overlay in that inventory and this file instead of carrying those old gaps forward.

## 2026-10-04 — optional review database failure on export

- The source reader already converts review lookup failures into `not_reviewed`, but `build_resolution_envelope()` called the same optional diagnostic without catching its `PromptInjectionReviewError`/SQLite errors. A database-lock simulation reproduced an export failure before any source-envelope result was returned.
- The resolver now treats that failure as `not_reviewed` and continues the export. Regression plus the SourceVersionReader suite: **35 passed**. This does not soften source identity/hash, identity/period, root, configuration, or qualification validation.
- At the time of this finding, the Ed25519 write path and 30-day cache TTL utility had no production callers. They have since been retired in G1; the scanner and old receipt reader remain diagnostic-only.

## 2026-10-04 — signed prompt-review and TTL gate retired

- CodeGraph plus source caller review and repository text search found no production callsites for the signed writer or `evaluate_review`; only tests and read-chain heuristic candidates referred to them. Existing producer/consumer surfaces only read optional receipt status.
- Removed signature verification/trust-root setup, human disposition authorization, the 30-day TTL cache evaluator and its cache-domain states. Kept deterministic `scan_text`, source/evidence SHA binding, and read-only compatibility for historical `prompt_injection_review` metadata.
- A detected status can now be stored without a human signature and remains a diagnostic. Existing source opening and export checks continue to bind real bytes SHA, source ID, identity/period, and root policy. Review-store failures on resolver export now report `not_reviewed`.
- Final focused source/diagnostic/export/CLI test set: **110 passed**. The fake bounded-provider test was updated with explicit caps and usage receipt; it then passed without running fetch.

## 2026-10-04 — stale test node in the fast push gate

- Running the actual `pre_push_gate.py --fast-contracts-only` found one curated node still named `test_c2_recorded_review_unblocks`, while the behavior-preserving test rename now calls it `test_c2_recorded_review_is_diagnostic_metadata`. Pytest therefore collected no fast-gate tests and failed before execution.
- Updated only the curated node ID. The fast gate then completed GREEN with all 15 selected nodes. The first attempt with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` was an environment mistake because it also disabled the installed `pytest-timeout` plugin required by `pytest.ini`; running with normal plugin discovery and disabling only the unrelated `langsmith_plugin` worked. No project pytest or CI configuration was changed.

## 2026-10-04 — 本轮优先级与分包基线复核

- 用户再次明确：先门禁精简，再抽象层虚拟化；本轮更新计划和独立施工卡，不抢外部 owner 工作。`get_goal` 实读仍为 active。
- 正常用户上下文只读 Git：CWP `master@376ed90`，仅 `config/source_acquisition.yaml` 一项本机 provider 配置未提交；RF `rf-impl main@6fb2def7` 有242项未提交/暂存记录，另一个 RF `fcap@5319ee26` 只有2项 assurance/runs 更新。不要将 sandbox 中的异常 dirty 计数或两个工作树合称“RF大量改动”。
- FF `fcap@1d0c73c` 只有未跟踪 key 文件；ET嵌套仓 `main@93fe52c` 有 `.workbuddy-ai/` 和 `eval_results.json` 两项未跟踪记录。本轮不读取凭证、不改这些文件、不将工作树内容视为已合并。
- 门禁清单仍有“当前代码未commit”，并行文档仍有 FF/ET 旧 HEAD，N4细卡末尾仍有直接进入N4C的旧下一步；这些是文档漂移，当前应以已发布 `1cfec10`（CI37188829582 success）和 `376ed90` 及 G1→S3→N4C 顺序覆盖。
- 已交付 FF-S3、ET-S3、SPACE-S5、StockWiki W01/W04、SourceExport与既有消费者线不重新分派。新分包必须有独立实际工作目录与明确文件归属；核心来源默认、Store/预算、共享CLI与最终合入仍由 root 负责。

## 2026-10-04 — 门禁与可分包的实际剩余

- G1首组已发布，不等于全局门禁精简完成。`source_reader` 的filing_reuse仍要求HTTPS、retrieved_at、collector_name/version；这些缺描述字段不应阻断真实可验证原件，MAIN下一步先TDD清这一项。
- 来源query_local/latest_as_of已默认按公开日期筛选，现有回归允许cutoff后采集的旧公开资料。叙述 `narrative_transport._require_historical_source` 仍要求capture<=cutoff，应在G1取消误拒；不重新改已正确的查询端，也不为缺需求模式造新配置。
- `writer_policy` 双环境许可仍在。config_doctor普通启动help成功，但scripts在PYTHONPATH时被sitecustomize拒绝；支持入口应不因启动环境变化。六个完成运维脚本只有自身链/专属测试caller，现场退休事实不删；源层archive/prune仍有真实入口且CLI漏now，归MAIN而非脚本包。
- secret_audit ignored本机凭证已是诊断，不再安排重复施工。PDF SourceExport manifest-only是能力边界；现有NarrativeTransport PDF回放不重复实现。
- ET零网络小复现：0.02秒预算、fake get阻塞0.25秒，0.250秒后才拒绝；当前不是硬deadline。独立ET-DEADLINE包采用最小内部子进程隔离，正式tool/batch共用，不改wire/golden、不扩翻译预算。
- 新G1-LEGACY和ET-DEADLINE是两个ready代码包，分别独占company-wiki-g1-legacy与earnings-transcripts-s3-deadline；ET-LIVE改为独占company-wiki-et-live-20261004，只交小报告。三包尚未收到用户启动登记。
- ET-LIVE明确区分FF companion确定性测试与真实ET→临时CWP段；直接ET调用不证明完整FF live链。无provider权益则NOT RUN，不强加provider或订阅。

## 2026-10-04 — ET worktree 重复样本实测

- 正式ET main、旧 `earnings-transcripts-s3-runtime`、新 `earnings-transcripts-s3-deadline` 三处各有130份 `transcripts/` 文件，每处合计15,953,731 B；按相对路径逐份比较SHA-256，三处内容完全相同。两个额外worktree因此重复占用31,907,462 B文本样本空间，未计少量源码、缓存与本机配置；不是46GB空间的主要来源。
- ET-S3旧runtime提交 `53e1e60` 已是main `93fe52c`的祖先，旧worktree Git状态干净；deadline worktree仍在修改代码，不能在其交付前清理。Git worktree共享仓库对象库，但各自检出文件，所以样本文本仍占独立空间。
- G1-LEGACY和ET-DEADLINE都只是外包施工线，不因目录存在或有未提交代码而视为已验收或已合入；当前状态以总进度记录为准。


## 2026-10-04 — 来源字段与叙述as-of实际简化

- raw open/verify移除URL HTTPS与retrieved_at/collector描述必填，仍实读SHA/size、校验当前版本/根/公开日与报告期间。candidate保完整度false/null，并保留缺一项时仍已知的采集字段，不合拼不同位置制造完整capture。
- 叙述as-of改公开日原则，删除无实际用途的capture时间解析；公开当天可读取后来采集的原文及已发布叙述，未来公开/未知公开仍拒绝。
- 审计证明正式链还有resolver/planner/canonical_writer/FF资格门；这是下一组收口，不用reader单点GREEN声称整体G1完工。FF旧owner/key树不改，后续MAIN隔离工作树集成。
- normalizer现代已绑定187条全1.0.0，生产WAL为0；历史抽样字节/状态拒绝不是版本误拒，保留格式与真实SHA底线。
- 用户已确认两代码包派发；ET Git三个实际worktree已核，新deadline已创建，旧runtime已合、未删除。双目录是代码隔离，不是两套生产资料。


## 2026-10-04 — G1正式来源调用链与跨仓状态复核

- CWP `capture_ready`混合了来源身份/字节真实性与URL/collector采集描述。URL/collector不可再作复用资格；raw SHA、公司/证券身份、期次、公开日期、版本与真实冲突仍验证。缺字段candidate保留false/null/gaps/preview。
- resolver、gap planner、canonical writer三个阻断已按正式来源合同收敛，六个CWP测试文件集中100项回归通过；canonical writer消歧用receipt SHA + source_id + provider身份，不使用capture_ready。
- RF `main@6fb2def7`、`fcap@5319ee26`、merge-base `ee0a82bfd1eec935cf4e567eb42f0ef79efa0226`。SourceRef v2消费代码是main侧merge-base后的提交，尚未进入fcap；fcap没有提交改动这些文件。RF当前两个本地dirty文件只是assurance周报账本，本轮只读。
- FF正式checkout `fcap@1d0c73c2`的唯一额外状态为未跟踪`config/FMP_API_KEY.txt`，不读取。存在`codex/transcript-companion@29085f7`工作树，改动覆盖`fetch_filing.py`和`filing_contracts.py`，与拟收敛的SourceRef v2门重叠；MAIN本轮没改FF，先厘清这条线再施工。

## 2026-10-04 — 当前G1关闭条件复核、FF SourceRef v2与ET测试路径根因

- RF当前`fcap@5319ee26`状态再次经提升权限核实为两项周报账本变化；普通sandbox对`.planning/.../execution_runs`拒绝读取会虚报成数千项删除。该树保持只读，本轮未更改RF合同或工作记录。
- FF `e1eda60`将SourceRef v2的HTTPS URL、collector/retrieval/provider说明和`capture_ready`改为诊断字段；通过真实本地CWP pathless query请求后仍验证SHA/ID/公司证券/period/published-date/as-of。`validate_handle`的legacy pathful路线没有改。完整责任集177 pass/1 skip/39 subtests，push gate GREEN，已推远端main。
- CWP电话会E2E原始失败不是导入合同错：复制目标`companies/Acme Inc/raw/investor_relations/transcripts/...`附加`.pid.importing`后超过Win32 MAX_PATH，`shutil.copyfile`因此抛`FileNotFoundError`。把临时测试根叶名由长UUID收缩为`e2e-`加12位随机后，同一真实子进程导入链全绿；CWP full-chain + importer CLI **12 passed**，测试根由finally清理。此项只改测试夹具路径，不改生产canonical目录或正文命名。
- G1第3/4项审计：modern normalizer绑定版本187条均1.0.0且历史compat回放已存在；canonical叙述summary合同校验source ID/SHA、原语言与citation spans，局部不可回放span降coverage；GapPlan按项保留reuse/missing/newer/future/provider-error，不整体拒绝。旧whole-catalog LLM summary的禁词regex无生产caller；`CloseGapBinding`和source archive/prune API同样未找到生产caller。故当前CWP公开路径没有手工binding门/禁词误拒门；不为不活跃代码再开阻断式改造，随S5/S6按caller清理。
- G1可以关闭；S3未关闭。FF companion确定性测试和fake-provider CWP全链均不能代替一次真实ET工具导入。S3需要检查ET-LIVE最多一次真实请求的实际权益/工具路径，使用全新临时CWP根，读回并验证原语言/hash/size/SourceRef，退出恢复为空；ET-DEADLINE仍在独立worktree，不并发编辑其写集。

## 2026-10-04 — ET-LIVE provider entitlement 与deadline测试错配

- 一次授权的真实ET工具调用返回unavailable/provider_entitlement_required。ET实现中_read_fmp_payload对FMP端点只调用一次session.get(..., allow_redirects=False)；HTTP 402被映射为此错误码，公共JSON没有保留http_status字段。可据此记录本次HTTP请求数1/status 402；无原文，后续导入及SourceRef验证必须标NOT RUN，不重试。
- CWP importer 7项、FF companion 17项确定性前置全部通过。LIVE验收报告在独占目录，随机TEMP根已删除、生产两份来源配置hash未变；精确随机根名称未留存，报告如实注明。
- ET-DEADLINE责任集91项通过、1项失败。失败测试注入RuntimeError作为session factory的异常；该调用处在transcript_api.fetch_transcript宽泛except Exception内，因此wire返回provider_error/unexpected_provider_failure是当前API语义。它不能证明worker死掉；runtime独立单测已经以SystemExit:7证明监督器的worker_failure路径。应调整e2e故障注入来造成子进程异常退出后重跑，除非真实异常退出仍映射错误，才改生产代码。
- 截至检查时，ET-DEADLINE worktree从93fe52c起有未提交的三个修改文件及多个未跟踪runtime/测试/PWF文件；其自有PWF仍写Stage 2 Not Started，未有commit/handoff。保持只读等待该包交付，不把部分实现当作已合入。
- 追加CLI层真实异常退出单点复核：初次临时脚本漏把请求写入stdin，故结果为invalid_json；修正stdin后SystemExit:7使worker真实非零退出，正式CLI稳定返回provider_error/retrieval_worker_failure，且无key/body泄漏、worker目录清空。失败测试确为夹具类别不符，尚需外线把其测试用例改成SystemExit后再运行整包并交commit/handoff。

## 2026-10-04 — Provider路径可移植性边界

- CWP配置loader已支持${PROJECT_ROOT}和${PYTHON_EXECUTABLE}；`JsonCommandAdapter`把adapter checkout作为子进程工作目录。这些是来源provider配置层的部署细节，SourceRef/SourceExport和consumer不接触它们。
- 本地source_acquisition.yaml相对HEAD的三处差异是CNINFO adapter由1.1.0升至1.2.0、project_root从旧provider worktree改指向cwp-cninfo-bounded-budget worktree、显式打开supports_acquisition_budget。它是正在使用的集成测试配置，保持未提交/未暂存。
- 所以当前所谓“配置可移植”无需新增通用DATA_LAKE_ROOT/adapter-path环境解析器。待bounded provider进入其稳定checkout后，仅将该adapter路径校正到真实canonical目录并发布正常配置；其他HK/US仍由纯外部Dayu配置持有，Dayu代码不改。

## 2026-10-04 — N4C真实样本来源预检（只读）

- 使用当前CWP `SourceCatalog.reader` 与 SQLite `mode=ro/query_only` 做样本盘点；未调用模型、未启动Worker、未写数据库或复制原件。catalog中active记录有annual 46、semi-annual 8、quarterly 7、investor-call transcript 7、investor-relations 3,682；229份prospectus全部为retired。verified/active metadata assertion目前只覆盖annual 13、quarterly 2、semi-annual 1，不能把active等同v2 metadata可见。
- 可用的同公司财报组为金山云：2025年报SHA `efe2ccd9…` / 4,826,662 B、2025中报 `4f589193…` / 3,396,644 B、2026年3月季报 `37f0eb13…` / 309,955 B。2025年报和中报已有parsed spans与normalized/summary工件，季报没有spans/artifacts；它们可用于检查复用/idempotency与未处理输入的增量差异，不能把旧工件记作本次Worker产量。
- 实读三七互娱2026-05-11 IR活动记录（SHA `3e25aab4…` / 133,294 B，3页，提取2,394字符）：`SourceVersionReader.query_local` 找到as-of候选；`open_version(..., purpose="narrative_derivation")` 返回完整字节且SHA/size匹配。正文包含具体游戏储备、品类布局、海外区域与产品上线/榜单动态，也有重复的“提升经营质量/按法规披露”模板回复，适合作为叙述筛选正反样本。但`describe_version`在当前v2 reader下返回`metadata_not_visible`，默认`filing_reuse`因非财务期次返回`period_unknown`；正文可读不代表已能作为pathless叙述export。须通过现有来源metadata/admission合同使其身份和公开日期可见，不能绕过。
- 代表性招股书“盛美上海首次公开发行股票并在科创板上市招股说明书”有旧记录SHA `02adc989…` / 7,073,891 B，但document与original-primary location均为`retired`；当前`SourceVersionReader`不允许把它当active SourceRef。其余228份招股书同样retired。不得直接开物理路径或改状态；N4C要包含招股书，须用正式再入库/metadata验证流程取得可见的active SourceRef，且原始字节SHA一致。
- 当前CWP的7条active `investor_call_transcript`记录是旧PDF或JSON sidecar，没有已验证的ET原语言TXT；ET-LIVE真实请求返回402，未导入。N4C电话会样本须来自ET的既有原语言TXT并经正式importer生成SourceRef，或等合法provider权益恢复后按S3合同导入，不把旧PDF冒充TXT闭环。
- 结论：N4C仍排在G1/S3之后。先固定active verified财报基线，再将IR、招股书、ET TXT的来源可见性列入样本入场检查；无法通过现有来源合同的样本要报告为未就绪，不能通过松开验证把批次做绿。实际Worker/模型并发、来源覆盖、成本与总空间测试仍未开始。

## 2026-10-04 — RF消费者合同与IR元数据入场根因（只读）

- 最新RF复核：`origin/main` / `rf-impl main@6fb2def7`；`fcap@5319ee26`仅有`assurance/runs/weekly_alert.jsonl`、`weekly_manifest.json`两项本地修改。`rf-impl`主线工作树另有大量owner未提交的planning/evidence改动，保持只读；没有尝试恢复或合并。RF未初始化CodeGraph；因本项目边界禁止改RF目录，未在那里初始化索引，按只读源码与测试核实接口。
- 财报消费复用`scripts/company_wiki_source_reader_v2.py`：请求为pathless `SourceRef/2.0`精确字段；CWP CLI按`filing_reuse`打开精确`document_id + source_id + SHA`，RF再核验实际字节数/SHA、manifest身份/期间、财年、公开日、检索日和as-of。prompt review在该合同里明确是诊断字段。不要在CWP另造相同的财报reader。
- 叙述消费复用RF `scripts/company_wiki_narrative_reader.py`和既有`narrative-read-request/1`；它读取的是已有叙述工件引用，做有界只读传输，不是新的原始来源下载协议。CWP仍是原件、解析、EvidenceSpan与摘要工件的owner。
- SQLite只读查询三七互娱2026-05-11 IR：document与source均active、公开日为2026-05-11、真实SHA记录一致；`documents.metadata_json`只有`acquisition/dayu_meta/group_key/root_id/scanner_version`，该document在`source_metadata_assertions`中为0行。故`describe_version=metadata_not_visible`不是路径或原件问题，而是从未写入可供v2 reader消费的normalized metadata assertion。
- 当前`upsert_verified_assertion`对规范化metadata作幂等写入，但新行默认`decision=verified, visibility_state=shadow`；需独立`activation.apply_activation`以epoch/cohort/policy hash等改变可见性，v2 reader只读active且匹配当前snapshot/cohort的行。不要直接改数据库状态或伪造财报期间。G1门禁简化需补审这条通用shadow/activation流程是否仍有实际生产必要；N4C需先确定最小可靠的IR metadata生产/可见路径，再复用SourceRef，而不是跳过manifest校验。
- 本次只读核对没有改RF、ET、CWP生产代码/配置/数据库/raw。ET-DEADLINE仍有未提交worktree；本机PWF仍写Stage 2 RED待做，当前checkout无handoff文件，最新源码/测试mtime显示为本地10:59，此后未更新。目录静止不能证明外部harness已停，故状态保持“未交付、不可合入”，不触碰它的写集。

## 2026-10-04 — Sparse SourceExport metadata TDD

- 先改测试复现两项预期RED：v2 runtime关闭legacy bridge后`describe_version`仍因`metadata_not_visible`拒绝；真实SourceExport CLI子进程也以同一原因拒绝完整pathless请求。其余责任集32项通过。
- 只移除`SourceVersionReader.describe_version`对“v2 metadata不可见”的整份拒绝。精确SourceRef、catalog状态、R4 metadata损坏/冲突检查和字节SHA/size验证保留；缺失capture不被legacy bridge补值，描述字段保持null。`open_version(... purpose="filing_reuse")`仍经`describe_candidate`严格拒绝缺身份/期间来源。
- 目标责任集转绿：`test_source_version_reader.py` + `test_source_export_v2_cli.py` **34 passed / 10.00s**。合成catalog CLI E2E证明SourceRef/hash/size/MIME和grounded text span可导出、无原始正文泄漏、所有不可见描述字段为null，临时catalog/fixture快照不变。不是实际IR生产CLI导出证据。
- 第一轮pytest basetemp过长，pytest自动改写到TEMP且其cleanup标记`removed=false`；检查该次测试独占目录无reparse point后，仅删除该精确run目录并核实消失。重跑使用仓内`tmp/pt1004b`（46字符，`relocated=false`），完成后删除且核实该唯一basetemp不存在；未清理任何既有TEMP目录。
- Worker当时仍未解锁：`build_batch_events`要求非空`language`，而这份IR无可见language assertion。该缺口已于本轮通过下方的确定性byte-pinned语言桥关闭；RF财报消费者原合同保持不变。

## 2026-10-04 — Sparse SourceExport发布与ET目录区分

- CWP sparse SourceExport提交`48d3a9d`已推送`origin/master`；pre-commit的Ruff、contract mypy、host assumption guard通过，pre-push fast contract smoke GREEN。`git status`确认远端与本地HEAD一致，唯一未提交项仍是用户本机`config/source_acquisition.yaml`。
- 当前harness身份检查只读使用一次性`git -c safe.directory=...`，没有改全局Git设置。`earnings-transcripts-s3-deadline`仍在`codex/et-s3-deadline@93fe52c`，scraper/tool/test有tracked改动，runtime/worker/test/PWF等未跟踪；没有提交或deadline专属交接。目录里的`s3-et-runtime-handoff.md`记载的是此前runtime施工包，不能当作当前deadline交接。
- 这两个ET工作目录用途不同：已完成的S3 runtime工作树代码已进入ET main的提交祖先；deadline工作树是后来为补硬deadline创建的独立、尚未交付施工现场。不要把后者和前者当同一批重复工作，也不要清理未交付目录。
- `gh` CLI在当前环境未安装；远端推送由pre-push gate确认成功，但本轮没有取得GitHub Actions运行状态，不把本地gate当远端CI结果。

## 2026-10-04 — Sparse narrative language bridge verified

- 仅当catalog language缺失时，Worker事件构建器通过`narrative_derivation`打开精确SourceRef，验证身份、SHA、size、MIME与read-policy后识别语言，并将结果绑定到event input hash。已有非空catalog语言优先；之后若catalog出现冲突的非空语言则拒绝。
- 检测范围有界：UTF-8文本最多256 KiB、PDF最多5页，HTML/JSON复用已有transcript extractor；只返回zh/en/mixed。空/短/损坏文本、其他脚本、无效PDF和不支持MIME均具名失败，不猜测、不翻译、不调用LLM、不落临时PDF。
- 隔离focused单元+CLI/Worker E2E **23 passed / 41.06s**，包含中/英/混合TXT、年报PDF、有无语言metadata、低价值IR skip、模型请求计数、重复执行幂等和原始夹具字节保持。该证据只验证桥接机制，不代表真实生产N4C或ET文档已导入。

## 2026-10-04 — ET-DEADLINE交付收据与并线边界

- 独立只读盘点报告 `docs/plans/repository-state-audit-2026-10-04/results/earnings_transcripts.md` 已按其范围完成。实时本地checkout复核与报告一致：ET main/origin/main=`93fe52c450c79dded53fb8b1e466a2193546bb28`；deadline本地与origin分支=`0017f24a999c5ecb224b646f47ebc8804769be73`，相对main仅1个独有提交，工作树干净；runtime分支tip已在main历史中。ET main的 `.workbuddy-ai/`、`eval_results.json` 是未跟踪资料，按审计建议保留。
- ET-DEADLINE handoff声明92项集中测试、全量172 passed、10 goldens matched、ruff和diff check clean；只读审计按卡没有运行测试，也没有CI run URL，因此这些是交接记录，不是本次独立测试证据。handoff列出的清理失败后无法确认进程退出、`--api-key` child-env覆盖和Windows受限环境仍有未单独验证项；一次跨仓联调只覆盖核心生产CLI/批次路径，不将防御边缘项扩大成额外人工门。
- 公共wire、serializer和goldens在ET-DEADLINE提交中未改；主线之外是ET内部supervisor/worker、预算路由及专属测试/文档。提交可作为单提交候选，但由CWP主线完成一次FF→ET生产CLI→CWP importer/SourceExport离线E2E后并线。已知合同缺口是FMP 26字段JSON vs CWP当前只接受Motley形状的24字段；不能把Motley既有12项E2E说成FMP已验收。
- 本次复核未触及ET原件、owner未跟踪文件、ET配置、FF/RF工作树或CWP生产配置；CWP仍只有用户已有 `config/source_acquisition.yaml` 未提交修改。

## 2026-10-04 — FF→ET→CWP 契约联调后的事实更正

- 上文“当前CWP只接Motley 24字段，FMP 26字段不能导入”来源于ET deadline 分支golden说明和较早的只读快照；已与当前CWP源码/测试重新核实，结论过期。CWP存在provider-aware的FMP 26-field JSON合同，准确保存原始payload，保留unknown publication，并阻止它进入历史as-of查询。对应消费者E2E：`tests/contract/test_transcript_import_cli_e2e.py::test_fmp_unknown_publication_cli_stores_original_but_excludes_historical_cutoff`。
- FF→ET→CWP隔离离线完整链已运行并通过：真实FF子进程、真实ET deadline CLI/supervisor/worker、真实CWP query/import/verified-open，假的FMP HTTP响应；原文bytes/SHA/size/MIME、SourceRef pathless、identity/FYQ、重复导入、unknown publication及scratch清理均核验。没有声称真实FMP权益可用；ET-LIVE仍因HTTP 402未获正文。
- 联调发现FF把`NASDAQ`大写值直接传给只接受`nasdaq`/`nyse`的ET CLI；FF adapter已统一lowercase并由单测和端到端覆盖。另复现FF外层timeout与ET内部硬deadline同刻导致被迫杀父进程、遗留`et-retrieval-*`目录。FF现给ET cleanup预留3秒，并在总余时不足时停止发起，ET子进程有限慢响应E2E证明目录清空。
- 以上实现分别归FF和ET owner目录；FF聚焦测试5 passed/Ruff clean，ET CLI E2E 6 passed，CWP importer E2E 5 passed，三个仓库链路脚本GREEN。FF修复和ET README说明修正都尚待提交/推送；在提交时继续只stage明确文件，保护`config/FMP_API_KEY.txt`、ET未跟踪资料及CWP用户配置。

## 2026-10-04 — FF/ET已发布并线的最新状态

- 上述“尚待提交/推送”是联调后、发布前快照；当前FF `eb0af13`已在远端main，ET `63c4090`已在远端main并包含deadline `0017f24`。ET快进合入不是squash/cherry-pick，保留交付提交祖先；候选branch与main同指`63c4090`。
- 合入后完整离线契约再次成功，ET CLI E2E 6 passed、10 goldens matched、FF companion 5 passed、CWP FMP importer 5 passed。ET main无tracked改动；个人未跟踪文件保留。CWP唯一用户配置和FF未跟踪API key均没有被stage或写入。
- S3完成条件满足，N4C真实样本文档资格和有限Worker批次是当前计划下一步。待验证的真实内容资格包括IR metadata可见性、招股书当前来源状态和ET TXT是否已有可规范化SourceRef；不可绕过admission或直接改数据库。positive dollar amount的provider实际计费未被ET wire提供，不能写作已实施美元实时扣费上限。

## 2026-10-04 — N4C失败账本与分派卡的只读复核

- 读取隔离运行 `tmp/n4c-20261004-pilot-a` / `n4c-20261004-wave1` 的结构化结果：四个SourceRef均已验证来源身份与原文字节SHA；年度报告选出3条span、5,593 source units；招股说明书选出160条span，另有784条省略及430条财务行移除。招股说明书summary因预算拒绝而无最终产物。
- 中文季报和IR均无候选/span并报PARSER_INCOMPLETE。另用正式SourceCatalog、SourceVersionReader及只读catalog查询确认两份PDF都可verified-open、SHA/size有效、PDF页均可抽取且季报全表格扫描完成；故本轮发现指向选材覆盖，不是原件损坏或来源身份失败。现行规则对已知valuable种类拒绝把空选择静默skip是正确的失败保护。
- 模型请求的未知reservation为5,258 micro-USD、2,400 max-output token；累计保守记账10,325 token、$0.005258，响应usage、HTTP状态和response SHA均缺失。不能由此推断MiniMax的真实失败原因；后续不复用该run，也不把reservation退为零。
- 源码对照确认HTTP适配器保留HTTP status于ModelHTTPError，但预算调用层将其折叠为MODEL_RESPONSE_INVALID。该状态丢失是已证实的诊断缺口，不是旧请求根因结论。MiniMax官方Chat Completions文档示例采用choices/message/content字符串及prompt_tokens/completion_tokens；旧事件没有存响应形状，所以不能断言是否为协议不兼容。参考：[MiniMax Chat Completions API](https://platform.minimax.io/docs/api-reference/text-chat-openai)。
- 本轮创建三张READY TO DISPATCH卡：N4-T1仅改automation模型错误/账本诊断；N4-T2仅改source_catalog中文叙述选材；MeetingConverter卡只限定另一仓CI workflow。前两者源代码与测试目录互斥，必须使用两个worktree；第三张卡跨仓独立。Main仍保留集成、真实文档/模型调用、预算和最终端到端验收。IQS不检查、不修改。

## 2026-10-04 — MAIN模型请求投影收缩与真实字节复测

- 首先按正常账号只读复核RF：fcap仍在5319ee26，tracked仅两项assurance运行记录；origin/main为8a153f3。沙箱目录ACL显示的大量删除仍是假象，未恢复/修改RF。CWP只有既有用户配置修改；没有发现新N4 worktree注册，不据此宣称外线是否正在运行。
- 旧run招股书160条证据原文共12,201 B，完整span重复source/hash/parser/coordinates/bbox/规则使HTTP请求252,185 B；它在HTTP发送前因60,000-token预算拒绝，和年报的unknown HTTP失败是两个独立问题。
- MAIN仅修改narrative_model.py及新增专属请求测试。模型现在接收所有原文片段、原span_id、source_role、非空quality_flags；共同身份与选择coverage一次携带。locator、parser及完整structured_value仍在原select结果保存/校验/回放，不重复发送给模型。prompt version升级1.2.0，旧run原有账本保持原样。
- 正式HTTP body builder只读复测：年报7,797→4,285 B；招股书252,185→47,202 B（减少81.3%），160条证据ID/原文全部一一匹配。数据库文件SHA前后相同，无HTTP/模型调用。这是请求体字节减少，不是全仓磁盘释放量或实际供应商费用测量。
- 默认2,400-output上限下招股书保守预留49,730 token，旧unknown为10,325 token，合计60,055仍超过首次aggregate60,000上限。不能宣称新真实批次已可直接成功；下次先明确新请求输出上限和总余量，再逐次预留，不能清旧未知账本或静默扩大总额。传输/选材两卡与真实模型遵约、consumer读取和P1/P2/P4空间吞吐仍待完成。

## 2026-10-04 — Worktree隔离的实际需求

- Worktree隔离解决同时施工共享文件/index的问题，不要求串行卡也各建一份目录。N4-T1/T2文件互斥，可在一个专用worktree依次完成并分卡commit；T2按自己的base..head验收，不把已提交T1误记为T2越界。共享MAIN活动checkout仍会混入总指挥的提交/分支操作，应保留独立施工目录。
- 模型输入收缩的正式提交df529a9远端CI37239069991已success；本轮说明与卡片修正没有引入代码变更。此收据不替代后续真实模型/消费者/N4C并发及空间验收。

## 2026-10-04 — S5当前调用者复核与首批清理准备

- 正常账号只读复核RF仍为fcap5319ee26、仅weekly alert/manifest两项owner修改，主线8a153f3。限定读取origin/main的scripts后确认source_preparation.py默认source_reader_v2=False，旧分支调用company_wiki_source的artifact角色选择与实际读取；不能用“v2已实现”推断旧derived没有消费者，也不能用.planning中的历史副本判定当前调用者。
- SourceBundle当前实现允许原件与单个失效artifact独立；删除normalized不会让原件自动失效。但RF旧路径仍会失去派生复用、报告待生产角色，CWP公开extract-sections也仍读normalized。因此2.826GB derived与8,191条artifact记录继续保留，下一批需要明确退休旧功能或迁正式来源接口。
- 首批仅处理审计已交付的七类缓存：index、drills、parser_tmp、qa、wheel-test、worker_runs.jsonl及worker_stdout/worker_stderr尝试日志。现行代码仅有旧生产者，未发现新读取者；drill目录确为2026-07演练库副本，parser_tmp仅旧结果JSON，qa仅PNG，wheel-test仅wheel。
- Win32当前进程枚举未发现旧source-catalog Worker、supervisor或narrative-batch；worker_control为paused。清理前仍按实际文件计数/bytes、路径包含与reparse检查执行，保护生产DB、原件、配置、derived/staging/security_master/artifacts和旧失败run；不复制整库，不启动下载/模型，不修改RF/IQS/Dayu。
- 执行完成：七类923文件/138,648,023 B删除，所有目标路径不存在。保护快照前后相同；公司原件33,133个/25,198,502,813 B清单未变，生产DB3,055,841,280 B完整SHA未变。四种真实资料正式source-reader CLI前后各4次、每轮12,343,802 B，SHA/size/identity/policy均一致。一次性脚本和重复临时JSON已删除，保留约9KB机器收据与短说明，不把这一结果当作全仓最新空间盘点。

## 2026-10-04 — S5旧section公开入口退休范围

- RF重新fetch origin/main后仍为8a153f3；其根task_plan自称历史底稿，audit_review/README和UC state记录旧项目completed/no owner。当前本线不复活旧CA签收流程。RF source preparation的旧默认还同时出现在SKILL和多组CLI夹具，后续迁移需一起更新配置接线与有效断言，不能仅改bool便宣称完成。
- 本轮先处理CWP独占的extract-sections CLI和SourceCatalog.extract_sections方法：它们是normalized文件的实际公开消费者/section派生生产者。退休这两个入口后，低级纯章节解析及历史artifact测试仍保留，用显式低级函数生成隔离历史夹具；不让旧fixture迫使公开入口继续存在。normalizer/fingerprint所需解析、原件读取、query/export和新叙述选材保持各自职责。
- 当前旧Worker的Python兼容类仍有extract_sections调用；其公开执行/启动入口此前已退休，不算活动入口。本轮不宣称所有旧writer或derived消费者已退出，RF及SourceCatalog旧normalize/summarize库方法仍列后续。外部N4-T1/T2写集不修改。
- 本轮extract-sections CLI及SourceCatalog公开方法已删除；TDD三项RED转GREEN，入口/纯章节解析/历史artifact binding合计48项通过。历史fixture改用原低级section函数，定位/正文/质量等断言未放松。新叙述入口按source raw选择与final包工作，旧derived消费的剩余项仍由后续S5处理。

## 2026-10-04 — N4-T1与MeetingConverter外包验收/并线

两仓真实主线CI已确认：CWP66808ee/run37241977614为success、job72秒；MC8a33a7f/run37241709261为success、job22秒。接受状态不是“分支绿但主线未并”；旧未知用量、N4-T2和N4C待办仍保持明确。

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

## 2026-10-05 — MeetingConverter施工卡当前远端状态

- GitHub API确认PR #1已合并关闭（2026-10-04 22:53:12 UTC），merge SHA `8a33a7f96292af8e6574d98b959703c6d11919eb`；live `master`及`ci/fast-gate` refs相同。run `37241709261`（master push）、`37241093118`（PR）、`37241089223`（分支push）全部`completed/success`。
- MeetingConverter的原始HANDOFF中base/head/master与PR状态仍记为`3c0b053`/`f1272fd`/open，和后续真实合并状态冲突，属于过期交接字段。CWP的验收收据记录并线和CI绿状态；未改MeetingConverter仓库，既有`.coverage` dirty保持不动。

## 2026-10-05 — S5旧Worker API边界与RF消费者现状

- `WorkerSession/open_session/read_desired_state`已无生产调用者，故本轮可退役其启动/心跳执行面；旧status/stop仍须消费升级前runtime文件，AUTO pause/interlock也仍是实际保留行为。normalize/summarize与normalized仍被CWP质量/证据链及RF默认SourceBundle角色读取，因此目前不能以SourceRef v2代码“存在”推断derived消费者已迁移。
- RF `origin/main@8a153f3` 含SourceRef v2 opt-in flag与真实三仓离线读原文合同；参数默认`false`，默认source preparation仍输出/使用legacy normalized Markdown、summary、sections角色。`tests/test_source_ref_v2_three_repo_e2e.py`对原文复用与字节损坏拒绝验证通过（1项），但不覆盖N4叙述选材或RF默认consumer切换。
- RF `fcap`为`origin/main`落后15、没有独有提交；3,833个`.planning/.../execution_runs`删除及两个weekly assurance修改是owner未提交状态，本线没有清理或重写。

## 2026-10-05 — RF叙述消费合同与物理存储依赖更正

- RF `origin/main` 已包含独立的N3a叙述来源入口：`scripts/narrative_source_preparation.py` 与 `company_wiki_narrative_reader.py` 通过有界子进程调用CWP `company-wiki-narrative-read`。它是现有正式接口，不应另造第二套wire。RF N3a收件报告记录89项主节点测试、年报PDF与电话会TXT原件样本，并明确“未接入收入计算”。
- N3a叙述包读取与 `source_preparation.py --source-reader-v2` 是两条不同consumer路线。SourceRef v2 filing路径默认仍关闭（`false`），默认SourceBundle继续读取normalized/summary/sections；N3a不会自动证明默认filing route或预测公式已改用精选叙述。
- 当前CWP源码中，`EvidenceQueryService`从SQLite EvidenceSpan行返回raw_text/span_json、locator与来源事实；`ExtractionQualityService`读SQLite artifact状态/metadata与EvidenceSpan，不读normalized Markdown正文。直接正文读取点见 `llm_summarizer.py`、`section_extractor.py`、`summarizer.py`。这意味着物理Markdown删除与DB EvidenceSpan删除可分阶段，但artifact状态/句柄和quality语义需同步，且所有真实正文consumer先迁移或退休。
- 本机只读ref核对为RF `fcap@5319ee263c4af41ac255938c25bebd32cce56f66`、缓存 `origin/main@8a153f3387ae75fb172e70f8ab63ffd38100779a`。本轮网络连接GitHub失败，故远端SHA使用此前已验证的live检查，不把缓存ref冒称为本轮live结果。无RF写入。
- `codex/rf-state-audit@447d1c7`补充报告称6处ACL不可读、全量分类未完成、确认安全释放为0；它与主线已有同路径报告冲突且没有新增删除候选。结论仅记录为审计限制，不覆盖较完整主线报告，不执行清理。

## 2026-10-05 — CWP当前真实原件transport回放

- 当前主线 `tests/e2e/test_narrative_transport_real_samples.py` 将真实原始字节及预期SHA复制到隔离发布fixture，再经CWP公开transport CLI读取bundle并完整重放locator；production capture metadata明确是测试fixture，不宣称现场目录具备准入资格。
- 这次4项样本是2025年报PDF、招股说明书PDF、投资者关系活动记录PDF和Microsoft Q4 2026 earnings-call TXT，均断言原件SHA、公开CLI工件hash、至少一个EvidenceSpan locator及 `replay_status=verified`；同时断言生产fingerprint、原件SHA/mtime不变。未包含季报，未调用网络，未覆盖RF adapter、正式Worker摘要或并发吞吐。
- pytest执行结果4 passed / 31.70s。Path guard因requested basetemp长度72超过阈值60，将测试目录移至短TEMP路径；退出输出`cleanup removed=true`。禁用第三方插件后有既有`asyncio_mode` unknown-option警告，pytest cache目录因当前sandbox ACL拒绝写入warning；二者均未导致失败，且没有重试或放宽测试断言。

## 2026-10-05 — RF N3a pathless消费者跨仓真实样本联调

- RF `fcap`本地HEAD为`5319ee263c4af41ac255938c25bebd32cce56f66`，cached `origin/main`为`8a153f3387ae75fb172e70f8ab63ffd38100779a`；本轮sandbox连接GitHub HTTPS/443失败，未声称fresh live检查。只用该已提交origin/main快照；owner checkout中3,835项tracked变化（3,833项execution_runs删除、两项weekly assurance修改）未触碰。
- 首次临时导出只含N3a四个模块，15项均在RF子进程导入缺失的`company_wiki_narrative_tree`时失败；未到达consumer断言，判定为测试快照漏带依赖，不是产品失败。纠正后从同一SHA完整导出51个`scripts/`文件和149个`tests/`文件（未包含`.git`或owner未提交内容），并显式从CWP `tests/`导入真实样本的只读fingerprint helper。
- 运行RF `tests/test_narrative_source_preparation_e2e.py`，由CWP已发布producer写入隔离fixture，再经公开CLI和RF bounded subprocess；设置`RF_RUN_NARRATIVE_REAL_SAMPLES=1`及`COMPANY_WIKI_NETWORK=blocked`。**15 passed / 39.81s**：txt/JSON/PDF/skip四种路径、实体/年度/期间/as-of/artifact/raw tamper拒绝、未知公开日期、畸形/超限输入，以及现场P01年报PDF和T01电话会TXT读取。
- 真实样本测试校验原件SHA和mtime、RF上下文中的原文SHA、至少一个EvidenceSpan locator及production fingerprint不变；夹具内也检查SQLite字节hash不变和scratch恢复。该实测证明RF现有N3a pathless子进程接口可读取CWP当前叙述包，不证明RF收入预测公式接线、CWP实际Worker并发/摘要、季报选材或SourceBundle默认切换。
- requested basetemp超过60字符预算，项目guard自动迁至TEMP；退出事件明确`removed=true`。独立CWP `tmp/rf-n3a-main-e2e-20261005b`通过绝对路径包含校验后清除，`scratch_removed=True`。仅有既有`asyncio_mode` unknown-option warning。无网络请求、生产catalog/raw/database写入；CWP只保留既有`config/source_acquisition.yaml`用户修改，RF未写入。

## 2026-10-05 — Worker多文档并行、profile吞吐与掉进程恢复

- CodeGraph确认当前`Supervisor.profile_slots`：P1=一个mixed worker；P2=一个compute+一个model worker；P4=三个compute+一个model worker。`NarrativeBatchRequest`要求显式选择P1/P2/P4；扩大profile不会增加模型并发，仍只有一个model slot。批次run已有输入hash冲突拒绝、source bytes开工前验证、single-owner lock、bounded time/token/cost/storage、逐job持久化和可恢复run。
- 将opt-in的`tests/integration/test_narrative_runtime_e2e.py`真实资料测试从P1/P2扩成P1/P2/P4（函数名随之更新）。命令使用`COMPANY_WIKI_RUN_E6=1`、独立空`COMPANY_WIKI_E6_TEST_BASE`和本地deterministic replay model；样本P01中微年报、P04招股书、P07万润IR活动记录、T01英文电话会，加一份IR格式政策文档skip。最终 **1 passed / 101.44s**：三档均5 visible artifact、4次模型夹具调用、满足话题/证据/字节门，重试0、SQLite busy error 0。
- 同一批约20,597,846 B原文下，P1 36.296s、max concurrency 1、RSS 359,493,632 B、396.7 docs/hour；P2 34.384s、concurrency 2、RSS 437,956,608 B、418.8 docs/hour；P4 29.091s、concurrency 4、RSS 630,353,920 B、495.0 docs/hour。P4相对P2墙钟少15.4%、RSS 1.44倍。各profile narrative objects 419,428 B，skip artifact另1,441 B；测试逐份验证原件SHA/mtime及production fingerprint未变。该4份文档、单轮、回放模型数据不代表生产总体吞吐/摘要质量；sqlite busy p95与catalog lock wait指标仍为null。
- 独立合成profile基准`test_e7_profiles_measure_bounded_worker_throughput_and_space`显式设`COMPANY_WIKI_RUN_E7_BENCHMARK=1`后 **1 passed / 77.10s**；45个本地作业、P1/P2/P4各两轮，最大并发分别1/2/4，median wall分别13.735/10.409/6.830s；P2相对P1速度指标+32.0%，P4相对P2+52.4%。P4中位RSS 267,538,432 B、P2为170,479,616 B（1.57倍），P4满足原speed/RSS候选阈值；六轮均0 SQLite busy error、retry 0，但busy p95/catalog lock wait未埋点，不能当成已经测得。
- 实际中断恢复合同`test_e7_r11_100_narrative_jobs_recover_after_worker_restart_without_duplicates` **1 passed / 19.43s**：34个合成来源生成102个选择/摘要/验证作业；强制杀死一个compute worker，租约过期后由新supervisor重跑；最终34个bundle均唯一可见、34个distinct work key/对象、模型调用34，目标作业恰有一次`LEASE_EXPIRED`与一次成功重试，原文hash不变。证明丢worker可恢复和效果幂等，不等价于真实网络传输中断或外部provider超时/计费语义。
- 真实E6中`tmp/e6p4`与pytest的`tmp/pt6p4`、E7/R11各自scratch都经绝对路径范围核验后清除；E6工作根在退出断言为空，之后才删除。无外部API/网络/生产写入。N4-T2只改source_catalog与其selector测试，不与本轮E6 integration test重叠；N4-T2的selector交付后仍需用P4候选档做一次新的集成真实批次。P4可作为有界N4C candidate，不应宣称已经验证大批量真实锁争用或收入预测consumer接线。

## 2026-10-05 — N4-T2真实季报/IR来源只读诊断

诊断收据：[n4t2_real_source_diagnostic_2026-10-05.md](harness_lanes/results/n4t2_real_source_diagnostic_2026-10-05.md)。本轮重新核对RF：本地 `origin/main` 缓存仍为 `8a153f3387ae75fb172e70f8ab63ffd38100779a`；`fcap` 与 `rf-impl` owner工作区的未提交/历史 execution_runs 状态未改。远端实时访问不可用，不声称刷新live ref。

- 用正式 `SourceVersionReader.open_version` 与当前read-policy pin，按完整字节SHA/size验证N4C请求中的IR和季报PDF；内存解析，无网络、模型、生产写入、字节副本或正文输出。
- IR SHA前缀 `3e25aab404a1` 默认扫描复现旧样本57 units/2,350字符，表格完整扫描为67/4,689字符且coverage complete；完整扫描后仍零candidate。已有new-business/overseas主题的3个PDF group同时含进度与时间线索、并命中特定行动词，但不命中high-value-event；候选资格仅对 `industry_dynamics` 放行progress+recency，确认是业务/出海叙述选材漏检。
- 季报SHA前缀 `37f0eb13fc97` 完整扫描为13页、192 units/11,645字符、零解析错误/opaque、coverage complete；当前7个主题类和事件模式均零命中，仍有少量宽泛进展/时间词。它不能仅因“当前词典零命中”就安全skip，应由扩展后的测试证明何时是真正无业务叙述。
- N4-T2须补具象业务进展 fallback、中文四类别及titleless kind-fallback合成测试，并对每个选中span执行locator replay；不扩大仅按零候选自动skip的类型范围。代码仍无改动，N4-T2仍awaiting delivery，MAIN后续做真实Worker/N3a/P4验收。

## 2026-10-05 — S5旧写者调用面与RF默认读取复核

- CWP当前 `master@5cabe47` 与 `origin/master` 同步，唯一未提交改动仍是用户的 `config/source_acquisition.yaml`。本地refs、linked worktrees及可见Codex任务列表均未出现N4-T2交付；这不能证明外部 harness 已停止，因此不复制或修改该卡专属的selector文件。
- CWP CodeGraph确认 `SourceCatalog` 仍暴露 `normalize/summarize/summarize_with_llm` 包装方法；针对 `src/` 和 `scripts/` 的精确引用核验未发现生产代码直接调用这些包装方法，旧合同/单测仍直接调用。service wrapper仍连到旧normalizer、summarizer和LLM summarizer；后者以及`section_extractor.py`仍经`read_verified_normalized_text`打开物理normalized正文。CodeGraph同名调用关系有歧义，故不把其“零caller”单独当作退役证据；结论以源码引用核验和RF合同共同约束。
- RF当前本地只读refs为 `main@6fb2def7`、`fcap@5319ee26`、缓存 `origin/main@8a153f33`。owner工作树3,835项tracked变化由3,833项 `.planning/.../execution_runs`删除与2项`assurance/runs/weekly_{alert,manifest}.json`修改构成，全部保持原样。只读检查缓存 `origin/main:scripts/source_preparation.py` 确认 `source_reader_v2` 默认 `false`；本轮未做live fetch，所以不将该缓存SHA称为实时远端HEAD。
- 当前安全实施边界：N4-T2交付后先完成N4C真实有限Worker及RF N3a消费验证；RF owner切换默认SourceBundle路线之前，保留normalized/summary/sections文件、可读句柄和DB span。后续退役生成器与删除文件分为两个不同动作；旧文件reader迁移与EvidenceSpan表收缩也分开验收。无RF/CWP生产数据改动。
- 正常用户路径下的真实只读空间实测：`.source_catalog/derived` 7,104文件共2,826,010,634 B；`normalized.md` 3,528个、2,748,621,075 B；`sections` 596个、67,624,394 B；`summary.md` 2,980个、9,765,165 B。normalized约占97.3%，后续优先迁移其读者后再删除。`catalog.sqlite3`只读immutable查询得746,055页、freelist 0、1,490,530条EvidenceSpan；artifact状态计数见总计划。derived目录没有reparse entry。本次不是全盘/全项目大小重测，不声称净释放量；原件目录未扫描或修改。
- `git ls-remote --heads origin`实时核验CWP发布端为`master@66a4eb1`；名称匹配N4/selector/narrative的远端分支目前只有已集成的`codex/n4t1-model-transport-diagnostics`，没有N4-T2分支。当前Codex线程/工件列表也无其交接；外部非Codex harness不可见，故只记“尚未收到”，不据此宣告对方停止。

## 2026-10-05 — N4-T2 selector implementation and false-skip boundary

- The verified IR sample previously had three complete PDF context groups with current business topics, progress, recency, and concrete action words, but the selector admitted progress+recency only for `industry_dynamics`. Added a narrow business-progress candidate requiring a recognized current-business topic plus progress, recency, and a concrete action. Synthetic RED/GREEN coverage exercises industry, core-business progress, new business/project, and overseas expansion; locator replay is asserted for each selected synthetic span.
- MAIN real-source recheck through `SourceCatalog`/`SourceVersionReader.open_version` verified SHA/size under `narrative_derivation` policy. IR `3e25aab404a1`: full scan 67 units, 2 selected spans/4,813 bytes, 2/2 replay success. Quarterly `37f0eb13fc97`: full scan 192 units, 0 candidates. The quarterly output correctly remains `needs_review`; a complete parse with zero matches cannot prove there is no valuable narrative when the target sample itself exposed a selector vocabulary false-negative.
- Empty-result skip policy now distinguishes business-bearing documents from low-value administrative formats. Reports, prospectuses, IR activity and transcripts remain reviewable on zero candidates. A fully scanned document whose every unit was positively classified as a financial table may skip; administrative IR policy and meeting notices may also skip when empty. All three conditions preserve the no-financial-claims scope and avoid treating incomplete parses as success.
- N4-T2 code is commit `ea9dd26`, now on live `origin/master`. CI run `37268779206` completed successfully for the exact commit (about 82 seconds). Focused MAIN tests: 104 passed/2.33s; Ruff, diff check, and pre-commit Ruff/mypy/host guard passed. One initial test setup error was only a missing basetemp parent and was corrected; the rerun was green.
- User says the external N4-T2 harness is still running. Its worktree has not been read or modified; its write set overlaps this commit. Treat its eventual handoff as a delta to review, not as a second independent merge. Card closeout waits for that comparison; CI is green.

## 2026-10-05 — N4-T2 external delta and E6 capacity evidence

### External delivery decision

- `codex/n4t2-selective-narrative-coverage@2b5bec91466e13deeb92feb5ac369ecb222563f0` descends from N4-T1 `4a53080` rather than current MAIN `ea9dd26`; the N4-T2 six-path write set overlaps the already published selector. It is therefore reviewed as a delta, not merged wholesale. Branch was clean; its 82 tests, Ruff, and `git diff --check` passed. No standalone handoff report was present.
- Retained improved Chinese recall for industry prosperity, production and volume, capacity utilization, overseas business/revenue/base, and explicit establishment of a business unit, institute, product or R&D project. These terms still need to satisfy MAIN's current-business topic, concrete action and recency signals. Added four-category, titleless quarterly/IR synthetic PDF coverage; boilerplate and TOC rows remain excluded, every selected span replays against its byte source.
- Rejected the external proposal to drop the specific-action predicate and to auto-skip a business document when the present vocabulary finds nothing. Real quarterly source SHA prefix `37f0eb13fc97` is a counterexample to treating complete parser coverage as complete selector coverage: 192 fully scanned units and zero candidates remain `needs_review`.

### Post-integration real Worker replay

- E6 ran the same isolated annual/prospectus/IR/transcript plus admin-skip sample at P1/P2/P4 after vocabulary integration; **1 passed / 246.39s**. Each profile: 5 visible artifacts, 4 model calls, raw 20,597,846 B, narrative objects 445,842 B (2.16% of raw), skip object 1,441 B, retries 0, SQLite busy errors 0, WAL 0. Exact source checks/locator replay, per-profile storage/budget assertions, unchanged production/source/config fingerprints, and cleanup assertions all passed. Test root and pytest basetemp were confirmed absent after exit.
- P1: 93.006s, 154.8 docs/hour, max concurrency 1, queue p95 76.177s, handler p95 41.639s, process-tree peak RSS 373,583,872 B, DB 1,097,728 B. P2: 89.453s, 161.0 docs/hour, max concurrency 2, queue p95 73.355s, handler p95 40.521s, RSS 459,042,816 B, DB 1,101,824 B. P4: 62.527s, 230.3 docs/hour, max concurrency 4, queue p95 41.893s, handler p95 38.773s, RSS 686,489,600 B, DB 1,101,824 B. All profiles had 4 model calls, 0 retries, 0 SQLite busy errors, and no WAL.
- Compared with the prior E6 record (P1 36.296s/P2 34.384s/P4 29.091s; P4 RSS 630,353,920 B), the rerun was substantially slower and used more process-tree memory, despite matching sample count and concurrency levels. This is not evidence that the selector change itself caused the slowdown; selector code does not alter Worker pool topology. It is evidence that profile capacity cannot be set from the old single-run speedup alone. N4C must inspect elapsed/queue/handler measurements in its actual run, retain a finite P4 cap, and avoid unlimited parallel work until latency and memory headroom are explained.
- Environment note: pytest's default optional-plugin autoload failed before collection because `langsmith` could not load `pydantic_core` DLL. Re-running with irrelevant plugin autoload disabled produced 107/107 focused tests and the known `asyncio_mode` warning only. Ruff passed.

## 2026-10-05 — pause boundary after N4-T2

- N4-T2 acceptance and selective integration are complete and pushed (`0657579d` code; `7b87ff3` receipt). The user explicitly asked to finish the current item, update PWF, then pause.
- N4C has **not** been resumed beyond the completed post-selector E6 P1/P2/P4 replay. No additional consumer test, latency experiment, or RF edit is authorized by the current pause instruction. On resume, first investigate why queue/handler timing is materially higher than the earlier E6 run; then continue the planned bounded consumer-integrated N4C stage. Keep the user's dirty `config/source_acquisition.yaml` unchanged.

## 2026-10-05 — resumed state and latency hypothesis

- Goal is active again. RF main was checked live at `8a153f3`; its normal-user checkout has only two assurance owner edits. The earlier 3,833 historical deletions observed under the sandbox were ACL failures, not confirmed deletions. Do not propagate that count as normal-user state.
- RF N3a consumer and its handoff are committed on origin/main but absent from the active fcap checkout. Use the committed main implementation read-only; do not modify or switch the owner's checkout.
- E6 fixes the local model delay at 0.8 seconds/call, so 4 calls cannot explain a 60+ second profile solely through configured model latency. Handler measurements include PDF selection/replay and other work; queue timestamps currently begin for all jobs before their dependencies finish, so the reported queue p95 also includes dependency wait. Stage timing is needed before interpreting it as scheduler contention.
- Prior claim that unchanged Worker topology excludes selector-caused slowdown is unsupported. The candidate regex/rules changed and may affect compute cost; a same-source old/current parse-select-replay experiment will test that hypothesis.

### Controlled profile result

- Same three real PDFs were SHA-checked before/after, parsed in memory using baseline `069c8d4`'s four selector modules versus current modules, with identical current dependencies. Under cProfile: annual baseline parse/select/replay 16.333/4.579/3.727s; current17.980/5.081/3.577s. Prospectus baseline45.731/9.199/6.048s; current47.032/9.804/6.425s. IR baseline1.476/0.037/0.456s (7 spans/1,619 B); current1.367/0.047/0.964s (11 spans/3,920 B).
- Prospectus profile shows PyMuPDF `find_tables` dominates: baseline143 calls/39.083s versus current146/40.465s; selected source bytes and span count remain10,391 B/160. Current rules add a modest amount of CPU work, not the 2.4x observed E6 wall increase. cProfile overhead affects absolute numbers; next use an unprofiled prospectus control to quantify table discovery costs and empty calls before changing parsing.
- Diagnostic root was removed by finally and restoration marker returned. No source text/results copied or model/provider call made. Source fingerprints and exact SHA passed.
- Found a separate versioning gap: N4-T2 changed selection behavior but `NARRATIVE_SELECTOR_VERSION` is still0.2.0, also used in batch input hash. A newly computed selector result can share an old generation binding. Before real model batch, add a failing legacy-generation hash test and release the current selection behavior under a new version.

## 2026-10-05 — 无profiler复核、版本修复及暂停收口

- 同招股书、同依赖、旧四模块overlay对照：无profiler旧parse/select/replay为27.730/4.890/4.797s，当前30.165/4.988/5.041s，总37.417→40.194s（约7.4%）。两边160 span/10,391 B并全部locator replay通过。当前表格发现144次/26.726s，84次空结果，占parse约88.6%。这是实测的解析成本；不能据此声称已解释整个E6涨幅，亦不能直接跳过无框表格/IR问答扫描。
- 已修复selector版本到`0.3.0`，parser仍`0.1.0`。新增batch input hash与event ID不得复用旧`0.2.0`的RED→GREEN回归；同版本幂等行为由既有测试保持。旧英文测试改为最早召回版本下界，全部英文原文/定位行为断言保留，避免未来合法版本升级被旧常量误挡。
- 117项聚焦回归绿，完整Unit及发布结果见progress。本次未重跑三档E6、未调用模型或写生产catalog。诊断根两次finally恢复，临时脚本删除；原件SHA/size/mtime不变。
- RF正常账号状态更正已写回主计划：只有两个assurance owner文件修改，旧3,833删除计数来自sandbox ACL误读；N3a源码和交接在已提交main，不在active fcap目录。
- 用户最新要求当前工作收尾后暂停。统一停止点和唯一恢复动作见[收尾收据](harness_lanes/results/n4c_latency_version_closeout_2026-10-05.md)，不启动后续真实模型/消费者/存储迁移。此前活动状态和旧暂停记录只表示各自时刻。
- 完整Unit首次1425 passed/1 failed：唯一失败是已完成G1-LEGACY外包卡用`git status`限制整个当前checkout写集；用户配置及本次计划/修复因此被误拒。这是一次性交付审计被混入永久产品Unit的缺陷。移除该测试、同类删除集合检查和仅供它们的allowlist，保留旧入口动态退出、初始化/写入陷阱、原件夹具快照、已退役工具/导入链等行为测试。外包写集审计保留在交付收据，不扩旧白名单、不清理用户修改来骗绿。
- 修复`b09e845`发布后实际快速push门和精确SHA的Actions [37354477263](https://github.com/zhengcb81/company-wiki/actions/runs/37354477263)均GREEN；完整CI job约77秒。这关闭本次版本/测试收尾，不解决尚未完成的真实模型/消费者大节点。原件与用户配置保持原样；目标按用户要求暂停。

## 2026-10-05 — P5可独立施工的真实缺口

- RF已发布main仍把SourceRef v2作为opt-in，默认legacy source preparation实读normalized/summary/sections。现有v2 builder/reader/三仓E2E已经在main；需要迁默认及真实调用者，不重写N3a或预测模型。这是S5释放derived的直接依赖。
- FF v2 CLI已自动设SourceRef route，不再派一个重复“v2默认化”包。剩余`PausedWorkerScope`及磁盘refcount/owner可以退出；主JSON runner与transcript runner先capture再限长，filing还按字符计数而非UTF-8 bytes。既有32MiB cap要在读期间执行，共用deadline/有限树回收，保持wire。
- 旧derived和active旧span降容可以提前实现独立tools与隔离fixture测试；它不修改CWP当前src/schema，也不在外线执行生产删除。S5消费者迁移与N4C只是MAIN live执行前置，非外线编码前置。现有retired-only prune不解决active全量span，不应再安排完整只读审计或大备份。
- P5三包源仓RF/FF/CWP，实际目录为`Projects/cwp-lanes-20261005`下三个互不包含的兄弟worktree；storage源码写集仅新增tools/tests，与MAIN runtime/core无重叠。共享wire固定；每包有独立上下文/PWF/测试/交接，MAIN统一合入和最终清理。
- StockWiki已完成N3b/SourceExport/W01–W04，ET deadline已完成；不以新名字重复旧工作。三新包是ready并非running，外部harness不可见部分不推测；IQS仍不碰，Dayu零代码写入。

## 2026-10-05 — 用户纠正后的LLM配置遵从

- 真实错误来自试点composition绕过既有配置：Config.load默认MiniMax-M3/API国内api.minimaxi.com/v1、8192输出、temperature1.0、reasoning_split=true；旧driver另写api.minimax.io、2400和thinking disabled。正常用户只读GET国内/models200/国际401，返回内容没有文档或推理；该结果支持端点错配，不能回填run02未保存的POST numeric status，旧unknown不退费。
- 权威配置和.env优先级在scripts/config.py已定义，legacy LLMClient也已有minimax/mimo用max_completion_tokens及MiniMax reasoning_split策略。typed package配置没有credential/dotenv加载能力，本次没有新建第三个loader或provider默认表。模型配置只在composition复制非秘密设置；child-local adapter保持独立限流/预算，无legacy全局客户端。
- 新scripts/narrative_batch_configured.py复用Config.load，向既有有限batch CLI注入配置快照；请求内旧model/thinking参数不能覆盖它，输入hash固定真实配置。未配置thinking保持省略。HTTP增加可选temperature/reasoning_split/token-field，DTO/factory透传及run hash同步；旧纯DTO/测试请求省略时保持原形。
- 正常账号加载现配置成功，credential_present=true，值未输出。当前错误不是本机缺key。国内正式价格/当前配置请求准入仍待验证，不能把国际报价当国内账单或按2400输出继续假设额度够用。N4C真实final/消费者仍未绿。

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
# 2026-10-05 — 配置遵从与真实run03计量依据

- `e1cc87f3aec6bd682ebc97c6574974d53eb76ae8`已发布到master；正常pre-push GREEN，精确SHA Actions37364555560当前queued。用户source_acquisition配置SHA仍3609e707466e…，未暂存。
- 旧`scripts/llm_client.py`成本表没有MiniMax项，落到0.27/1.10 USD默认价，不能当作实际计费配置。新有限批次继续使用原有版本化operation pricing，生成设置/凭证只由Config.load提供；不变更模型、协议、8192、reasoning或凭证来源。
- 官方[国内定价](https://platform.minimax.cn/docs/pricing/overview)2026-10-05可读取：MiniMax-M3标准、input<=512k为2.10/8.40 CNY每百万输入/输出；priority需明确service_tier，当前请求没有该字段。缓存优惠不用于最坏预留。账户PAYG/订阅权益仍未查询，不从key格式推断，不购买、不切Key。
- [ECB 2026-10-02参考率](https://www.ecb.europa.eu/stats/shared/pdf/eurofxref.pdf)：EUR/USD1.1225、EUR/CNY7.5259，推算CNY/USD约6.7046。为本次预算采用更保守下限6，operation价0.35/1.40 USD每百万；不是供应商账单/换汇报价。旧账33,660 tokens/16,580microUSD不改，另保留2,764microUSD历史汇率余量，使run03费用上限80,656microUSD。
- run03范围固定为P04招股书+synthetic English IR policy。最多26,340tokens；实际配置请求上界24,863，skip零模型。先读真实usage/final/RF接口，不重复四份盲调用；本条记录时尚未POST。RF live main仍8a153f33、owner仅两份assurance变更；P5正式handoff目录没有交付，不能把历史execution_runs/handoff.json当作新交付。

## 2026-10-05 — MiMo/DeepSeek 配置与多供应商实测准备

- 用户要求实测 MiMo 和 DeepSeek，避免只依赖有5小时额度的MiniMax；继续遵守现有Config，不重写生产配置。正常用户读取安全元数据确认三家key均存在。MiMo为已配置fallback：mimo-v2.5-pro / token-plan-cn.xiaomimimo.com/v1；DeepSeek由同一loader已有defaults提供deepseek-v4-flash / api.deepseek.com；共享8192/temperature1.0，不临时改thinking。
- 增加显式 `--llm-provider` 的配置选择；fallback用现有完整profile，DeepSeek复用已有默认表，主配置和API key均不序列化。六项TDD先RED：不存在选择方法/关键字及CLI未接线；实现后待集中责任测试。这是显式选择，不冒称自动retry/failover已实现。
- [MiMo官方API](https://mimo.mi.com/docs/en-US/api/chat/openai-api)与[首调用](https://mimo.mi.com/docs/en-US/quick-start/summary/first-api-call)使用max_completion_tokens；思考默认开启，温度实际固定1.0；不切协议。[官方价格](https://mimo.mi.com/docs/en-US/price/pay-as-you-go)公开V2.5-Pro输入未缓存$0.435/百万、输出$0.87/百万；当前是Token Plan专用endpoint，现金费用与Credit消耗须区分，不推定PAYG扣款。
- [DeepSeek官方价格](https://api-docs.deepseek.com/quick_start/pricing/)仍接受配置的旧别名deepseek-v4-flash，由V4.1-Flash服务；峰值USD输入未缓存0.3/百万、输出1.2/百万，闲时半价。实测仍按峰值/无缓存保守计量。返回model ID可能与请求别名不同，需要实际证明；不先放宽模型身份验证。
- run04实际失败收据已保存：新增24,863 tokens /17,304 microUSD（usage未知，全部最坏预留）；累计58,523 /33,884，另保留历史FX余量2,764；旧60k只剩1,477 tokens。已询问是否提高累计token cap到160k、仍保留$0.10；得到答复前只做离线准备，不擅自突破旧cap。run04原件、生产、RF owner文件和用户配置均不变，独立测试根恢复。新safe envelope诊断防止以后丢失错误阶段与已知usage；旧未知账不回退。

### 用户纠正后的最新事实（覆盖上段当前模型/凭证判断）

- 用户指定MiMo v2.6 Flash、DeepSeek Flash。实际Config路径确为本仓config.yaml；没有.env模型覆盖项。本仓YAML、脚本Config/default client与typed fallback仍写旧Pro/别名，是本地配置未同步，不是用户指定错误。三个Flash一致性测试先RED，已统一为mimo-v2.6-flash / deepseek-flash；显式自定义旧模型的兼容夹具保留，不批量改历史收据。
- 用户指出DeepSeek key在环境变量。加载前捕获进程环境（与Windows User scope相同）再请求同一/models：200、flash存在；加载后的key与加载前不同，使用加载后key才401。确定根因是本仓managed dotenv强制覆盖环境密钥。此前“已排除环境覆盖/用户需修复key”的结论撤回：那个比较是在覆盖后进行，没有比较加载前值，证据不充分。
- TDD纠正环境密钥测试一度被PYTEST_CURRENT_TEST跳过dotenv，修正夹具模拟真实默认load后复现覆盖RED。现在DeepSeek环境优先、dotenv只补缺；MiniMax/MiMo项目受管凭证规则保留。更新旧默认断言并验证：53配置/旧客户端责任tests、16 defaults/legacy来源适配、34最终配置/环境优先tests均GREEN。改后的真实Config `/models`两家均200、Flash都列出，DeepSeek environment_preserved=true；仅安全元数据保存到n4c_flash_preflight_2026-10-05.json，零模型POST。
- Flash预算代理按[MiMo国内官方价](https://mimo.mi.com/docs/en-US/price/pay-as-you-go)1/2 CNY与FX floor6：0.166667/0.333334 USD每百万；Token Plan [规则](https://mimo.mi.com/docs/en-US/price/token-plan)输入未缓存100、输出200 Credits/token。此前Pro价格是旧配置历史准备依据，未来run不再使用。新driver仍保留旧未知账及$0.10总cap；已发出的160k token cap问题尚未收到批准，真实摘要调用未执行。
- 配置/诊断修复已发布a0ea41bd1aef8ffcdf535e065cb9ed5836abaf2b，正常pre-push GREEN，精确SHA远端CI37368647773最后queued；本机只剩用户既有配置变更，SHA不变。不得把清单认证200说成模型摘要验收成功。


## 2026-10-05 — run03零费用失败与空间采样竞态

- run03正式配置入口仅P04+English policy，CLI报NARRATIVE_BATCH_FileNotFoundError。账本模型预留/新增tokens/费用均0，policy三阶段成功，P04 select未结束，没有RF实读；异常栈未保存，不声称唯一定位那次FNF。
- 确定性两个RED复现_tree_bytes的is_file→stat间文件删除竞态；修为一次stat，仅忽略FNF，PermissionError保留。31批次/请求责任测试GREEN，正式CLI+spawned Worker+loopback HTTP删除竞态故障注入1项GREEN（4.75s），原件/foreign jobs不变、final可用、根恢复。Ruff通过。
- 临时driver的with sqlite3.connect未关闭连接，cleanup WinError32；进程退出后保存小型run03费用/attempt收据，再按绝对路径验证删除唯一scratch。原件SHA和用户配置SHA一致；丢失的峰值/耗时/生产前后fingerprint列明，不伪造。driver已显式close，今后清理前先保存账本，避免丢费用事实。
- 下一run04仍只P04+policy，配置模型/8192/reasoning不动；run03不增加旧总额，保留26,340tokens/80,656microUSD与2,764microUSD历史汇率余量。N4C未完成，P5写集继续保留。详见harness_lanes/results/n4c_storage_sampling_fix_2026-10-05.md。


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

## 2026-10-05 — P5-STORAGE 节点二依据

- 复核主线4df5d12/候选72b1116，候选干净；RF普通沙箱status因旧临时目录读权限出现伪删除，正常账号只读复核实际只有两份assurance owner改动，HEAD5319ee26、origin/main8a153f33。RF/FF约定交付目录尚不存在，保持写集隔离。
- 工具core.read_connection只用mode=ro，会生成WAL/SHM；prune的dry-run也开RW+BEGIN IMMEDIATE。复用主线EvidenceQueryService/ExtractionQualityService的静态immutable-read策略，活动WAL缺SHM具名诊断。主线CodeGraph已给出代码；候选树没有独立index，新增工具文件用明确路径读，不为本节点再建第二索引。
- SQLite官方说明VACUUM最多需要原库两倍大小的额外空闲空间，且无INTEGER PRIMARY KEY的表可能改变ROWID。故空间预检按实际页数/文件量取最大值，fact digest按列/主键排序并有界读取；压缩前后的事实必须真正分别取样。保持标准VACUUM，不用VACUUM INTO制造第二份完整库。依据：[SQLite VACUUM](https://www.sqlite.org/lang_vacuum.html)。
- 测试先覆盖零预览写入（包括WAL/SHM）、有界span报告、严格parser范围、keep计数、压缩前事实变化和低磁盘空间；再一次集中工具/真实年报TXT E2E。0外部模型POST，不动原件/生产库。两个误猜vacuum.py/compaction.py路径及一次PWF patch定位失败均无写入，已按实际shrink.py继续。

## P5工具主线验收收口

e570daf已发布，精确CI37375836745 success。53个不同case分步GREEN。真实年报/MSFT TXT stdout SHA及新摘要完整locator replay、实际source facts/new final保持，测试根已恢复；副本derived释放6,360,944B、DB释放30,617,600B，不是生产数字。保留的路径/身份/SHA/事务/资源校验均有实际原件破坏或错误计量RED支撑，没有新增人工签收。工具和测试记录见P5集成审查/验收JSON；下一步实际caller与metadata_only语义迁移。

## S5 质量与读取迁移调查（2026-10-05，进行中）

- 主线0c05c58与远端一致，只有用户source_acquisition配置未提交；RF远端仍8a153f33、两份assurance owner改动，RF/FF约定HANDOFF尚未到。
- CodeGraph对ExtractionQualityService/EvidenceQueryService构造调用返回零，但已知CLI明确构造两者，属于索引解析遗漏；不能据此删除合法来源查询。旧normalize_catalog仅发现tests/support夹具调用；其余旧generator仍须按实际导入核证。
- quality现状仅从normalized artifact metadata及全量旧span评估；不接受retired状态，未处理原件被归unavailable/normalization_pending，新visible narrative没有入口。evidence查询仍直接读取旧DB span，尚未迁移。新叙述transport已有当前来源/对象SHA/完整locator回放，不复制第二套读取实现。
- 本节点先框住quality对metadata_only、精选/跳过/不完整叙述及旧retired的公开行为。质量诊断不等于字节已验证；真正读取继续走现有transport。未处理不自动转换、不建全量span，不新增人工review门。
- 本轮首次PWF patch用了不存在的英文标题，验证失败且零写入；按已读尾部精确锚点更新。

- 11个新公开行为case先10 RED/1通过（15.51s）；第一次实现8 GREEN/3失败（14.40s）。实际TXT质量CLI与完整回放已通过，未调用外部模型。三处树变化为SQLite旁文件：新包facade另开只读连接时可创建WAL/SHM；改为借用质量查询既有只读session，关闭facade不关闭借用session。静态无WAL仍immutable，已有活动WAL的SHM读标记可合法变化，不能等同正文/事实写入。
- 当前生产叙述批次与正式transport均以config.catalog_dir作为LocalNarrativeObjectStore根；quality允许注入对象store，默认同目录。没有猜多个目录尝试读，亦未新增对象位置配置或第二状态库。
- 一个多文件patch最后使用错误source属性名，整patch校验失败、零写入；随即按content_sha256真实字段修正。两次literal搜索误猜不存在的factory/RF src路径，改用已知batch及结构发现，不据缺路径推断无caller。

- 静态快照前只关闭cached reader不足以清空旧WAL，改在fixture setup阶段正规checkpoint/关闭；没有在实际quality里执行checkpoint或写SQL，也没有删除WAL绕过验证。活动WAL独立测试保留DB/WAL/原件及全部持久内容相等，容许仅SHM协调读标记变化。SQLite官方说明reader有end mark，wal-index使用映射共享内存，最后关闭会checkpoint/清理旁文件：[SQLite WAL](https://www.sqlite.org/wal.html)。本机SHM变化与read mark机制一致，属于由官方机制及实测作出的判断。
- 最终质量v2 55个不同case分步GREEN，真实TXT回放/恢复通过。新增final大小在读取前检查，精确版本固定后读，policy/selection绑定冲突不静默fallback。schema只升级该诊断2.0.0，不改变NarrativeRef/read/SourceRef及RF正式wire。生产没有执行清理，EvidenceQuery旧span依赖仍待下一节点。

- 发布dd35d2f、精确CI37378430383 attempt1 GREEN。pre-push第一次是本任务禁用插件环境导致--timeout选项不识别，移除该临时变量即GREEN，没有CI代码缺陷或新门。一次误猜tools/pre_commit_gate.py读取失败无写，使用实际正常hook。
- 328份当前生产Python AST只见normalizer的fingerprint backfill与两项public类型导入（LLMSummaryError/SectionSlice），没有旧batch writer的直接导入。第一次git pathspec *.py也匹配tests，计740；过滤生产前缀后才得328。三外仓当前tracked运行脚本未发现旧EvidenceQuery/质量CLI literal引用；RF有大量.planning/assurance历史复制，不算活动消费者。尚未覆盖动态生成命令或用户手动脚本，不以零匹配证明任意未知消费者不存在。
- 后续不能把不同parser/version的loc:v1裸坐标默认混用：旧normalizer与当前selector的段落切分可能不同。优先复用已绑定artifact版本的NarrativeRef与完整transport回放；保留source-only查询/预览责任，而不是恢复1.49M永久全量span。此为下一节点实施细则，不冒称已迁。

## S5 精选检索运行接线（2026-10-05，施工中）

- 本次按用户再次提示实读运行配置：DeepSeek使用DEEPSEEK_API_KEY且与进程环境一致，dotenv加载前后不变；模型deepseek-flash/API https://api.deepseek.com。MiMo实际mimo-v2.6-flash/受管token-plan-cn endpoint；两家max_tokens=8192、temperature=1.0，未临时降参数或POST。凭证只输出存在/相等布尔值。旧60k累计额度待答复不由密钥存在替代。
- 恢复调查中几次rg把通配符当Windows路径、误猜model_factory/操作文档/transport测试路径；均只读无改动。已改为已知具体路径或rg --files的literal发现；CodeGraph宽泛配置context偏离主题且_build_config遗漏，不作为凭证优先级证据，直接读取已知scripts/config.py并用真实Config.load验证。

- fresh主线32d92af与origin一致；RF remote main8a153f33、owner两份assurance改动未变。RF外线codex/p5-rf-source-default已有source_preparation及一组测试WIP，计划在实际`.planning/p5-rf-source-default/task_plan.md`，尚无HANDOFF，保持隔离。误猜其PWF目录/不存在progress只读失败，按git实际路径核查。
- CodeGraph对SectionQuery构造caller同样漏报；实际CLI有sections-list。该旧查询只读sections metadata且输出物理index/section路径，没有筛除retired状态，不适合作为新接口。EvidenceQuery旧CLI唯一明确当前运行入口；外仓运行literal搜索先前无引用，历史backend可供读夹具，不要求保全全文库。
- scanner的旧artifact/span EXISTS只是保护尚有引用的空逻辑文档不被扫掉，并不触发重建；status的旧计数是诊断，不是提取调度门。本节点保留这些来源事实保护/计量，不因降容误删document或重新制造全文。
- `NarrativeEvidenceSearch`已实现内存BM25/中英分词，但只接受早期0.2试点package；resolver仍用source→raw物理路径映射，正式final的运行检索尚未接线。仅删除旧CLI不足以完成用户要求，因此同时接正式NarrativeRef的精选list/lookup/search。复用正式transport原文SHA/完整回放与现有排序，不建设第二磁盘索引/数据库或新权限层。

- 正式view节点现已本地GREEN：102个不同case分步过；全来源verify/replay后才查询，过期裸locator无转换。固定旧版本在新partial final可见后仍返旧spans，技术partial/coverage显式展示；skip零items，所有输入资源边界在打开前验证。summary_input仅抽纯分组函数，旧read/reference golden字节不变。没有调用早期physical resolver或新DB/index。
- 新测试首猜hash_mismatch再猜resolver内部content_sha256_mismatch均非公开wire；实读SourceVersionReader._verified_version证明SHA失败按location聚合，公开unavailable/no_verified_location。修测试与公开协议一致，完整raw SHA验证不改。历史backend的archive/readonly/hash等测试仍保留，旧CLI迁为未注册断言。
- FF交接由缺失变已到：实际干净codex/p5-ff-runtime-cleanup@ab9ce33，code7c6cf48，handoff机器schema/2的delivery b5c1c82之后仅文档收尾；尚未MAIN验收。报告463过/10 baseline-red/14skip不是全绿；10处下载fixture未提供CWP限额，下一阶段补fixture真实合同，不新增或放宽门。RF远端仍8a153f33/owner两处assurance、尚无HANDOFF。沙箱读FF Git报dubious ownership，改用真实所有者正常上下文只读，不增加全局safe.directory或改文件。

- S5正式精选节点1b0feb4已发布/正常钩子GREEN，CI37381429717 attempt1 success、所有步骤成功，无重跑。代码CI不由后续纯文档收据覆盖。生产原件/derived/span零删除，user配置原SHA保持。
- FF额外只读实测：受控实际child输出9/10/11 bytes对10B cap依次ok/OutputLimitExceeded/OutputLimitExceeded（0.399/0.051/0.057s）；等于cap的有效输出被错误拒绝，交付不可直接签全绿。源码另见stdin同步写发生在期限起算前、两管道EOF后proc.wait()无timeout、只等双EOF可能不及时响应单流overflow、POSIX父退出后getpgid(pid)失效等风险；后三者当前是读码推断而非已跑证明，需下一节点受控watchdog TDD。零网络/项目写入；读取不存在FF AGENTS.md失败无写，不创建文件。

- fresh FF owner未提交测试只是已交付mock接缝迁移的相同bytes，双方SHA24f3a7272c28aaf1ebbf0e932ee62aa9187feb0e848c8453f3bc09a8c4b35c9d；仍不在活动树施工或reset。MAIN独立整合树从干净ab9ce33创建。外线task_plan checkbox尚未随handoff逐项勾选，不能拿checkbox当产品通过/失败证明；以代码与实际责任测试验收，不增人工补签。

- 受控实际child/watchdog19项有14RED，已把先前读码风险升级为实证。原实现依赖Popen之后的pywin32 job赋值，父退出后POSIX动态getpgid也不能回收已存在组；采用标准库Windows原生Job和先阻塞的启动器，job赋值后才允许运行实际命令；POSIX自建session并保存PGID。进程整个生命周期使用spawn前的一个绝对deadline，精确cap再读一个byte判EOF，stdout/stderr任一错误及时唤醒，stdin独立写入线程；最后先终止树再有界join。依据：[Microsoft AssignProcessToJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject)、[Job limit structure](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information)、[Python subprocess](https://docs.python.org/3/library/subprocess.html)。这是待GREEN验证的实现方案，不冒称Windows/POSIX都已通过。

## P5-FF MAIN验收收口（2026-10-05）

- 真正原因包含三层：进程层生命周期缺陷；legacy 1.1/1.2禁止传上游必需限额；离线spy/noop fixture未声明预算能力/返回usage。不是统一“上游坏了”或只改测试期望。分别修共享进程层、复用已有可选限额对象验证、fake-provider实际计量，响应/golden/原文校验保持。37项进程责任11.08s及53个不同节点case分步GREEN；真实三仓chain与9165875B年报公开v2/原字节读取通过，测试根恢复。
- Windows stdio必须显式从bootstrap传给实际child；不使用丢状态的os.execv或Popen后实际命令已运行才assign job。本机所有期限/PID/线程边界已实测；POSIX真实执行待Ubuntu CI，类型已在linux/win32目标均通过。
- 首发58568e7的CI37384744223仅Linux类型失败，因本地同mypy按Windows stub执行。WinError构造改sys.platform守卫，本地既有mypy目标改linux与CI一致，不增加新hook或commit pytest。修正758e8f4已正常推main，CI37385101051进行中。
- FF原活动fcap是d4d2fac，但旧local main停c9799b7。只有一份未提交测试，SHA与已提交交付相等；最终main快进758e8f4补全66commit，文件SHA仍24f3a727…；仅FMP key未跟踪且未读。真实owner的三仓config doctor GREEN；独立整合树pre-push的doctor SKIP不能替代这项。

- 最终精确CI37385101051/758e8f4 attempt1全部GREEN；实际Ubuntu运行新生命周期用例，POSIX session/父退出孙持pipe也完成验证。FF本地/远端main已一致，原owner已交付WIP收口。生产清理仍未执行，P5-STORAGE工具验收与P5-FF消费/进程验收是两个不同完成节点；不把工具可用当已释放生产字节。

### S5分层验收事实（2026-10-06）

- 指纹真实性缺口已TDD修复：manifest必须匹配调度source_id/SHA，解析前/后实字节核验；同大小替换/解析中替换/错source manifest均retryable具名失败，后续健康文件完成。来源事实与原件不改。
- 真实PDF揭示第二缺口：PyMuPDF直接打印“Consider using…”到stdout，污染CLI JSON。完整report其实completed=2；复现后将child的Python及原生fd诊断送stderr，保留可观测性和严格JSON，最终真实CLI验收GREEN，不用最后一行猜JSON。
- 退出的是安装包全量生成能力，历史测试造数器尚保留；它们复用唯一原文parser、不被343份生产Python导入。2.826GB生产derived及3.056GB来源库尚未删除/收缩；剩余实际默认消费者迁移是RF外包卡。

- S5生成器节点最终收口：精确代码b148123/CI37388329668 attempt1 completed/success，全部步骤GREEN，无rerun。本节点所有s5g*测试根已恢复absent；源配置原SHA保持。MAIN下一动作为RF默认迁移验收，未交付时仅做生产只读预览；0生产删除。代码CI以b148123为准，纯PWF [skip ci]收尾不替换该收据。

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

## 2026-10-06 — 共享引用修复证据

- 新12项TDD首跑12 RED/22.73s，其中1项测试外键夹具错误已改为真实存在source，11项为产品缺口；修复后12新增项+8既有恢复项20 passed/36.68s。
- 采用物理对象为删除单位：已验证manifest提供SHA/size证明，闭合所有同document+source旧handle；失配旧hash不改写，未知现代/准备中/跨来源引用阻止整个共享组。sections对子文件有所有权，阻断沿组传递；BEGIN IMMEDIATE中复核相关当前完整row集合再统一退休，之后才unlink。
- 已确认历史reader具有pymupdf_page_text→pdf_page_aware_core兼容别名，现parser/version与生产盘点一致；空标签summary只按历史SHA目录+summary.md+role识别，不解除所有unknown保护。
- 本轮误读不存在tools/legacy_storage/cli.py、__main__.py和migrations.py，仅只读错误；由rg --files定位真实入口tools/legacy_storage_retirement.py，继续按实际文件施工。

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
# 2026-10-06 — run10真实业务效果与N5-ET-TXT验收更新

- 用户已明确批准累计费用$0.12，token cap200000不变，原模型配置/端点/默认thinking/8192输出保持。run10 DeepSeek电话会一次POST成功：20 claims，其中15 management陈述/5 analyst问题；46个locator回放全部通过，RF正式reference/read退出0。最终包99479 B，batch35.217秒/总42.828秒，试点根峰值1016373 B/RSS324960256 B，零生产final持久化。
- 业务复核复用生产的`extract_transcript_material`规范化再parse/select，逐条验证实际claim的evidence ID与角色。六类重点经营主题均在精选原文证据，短摘要覆盖五类：31座数据中心、新模型、Fabric客户采用、Copilot付费席位、seat+usage商业模式。GPU dock-to-live效率未单列，不伪称穷尽；该片段仍可由精选证据读取。旧run06真实收据计数为8 analyst/6 management，纠正此前9/5粗读数字。全部合法引用不能代替摘要内容覆盖。
- 本次已知9151tokens/9853microUSD，新unknown0/unsettled0；累计190035/100502，历史unknown7和FX2764保留；200000/$0.12下余9965tokens/16734microUSD。费用仍是配置价格代理，不冒充现金账单。同配置完整请求预留18755tokens大于余额，不再次盲POST。N4C原定有限样本节点达成，不宣称全类型穷尽、多provider同时外发或MiMo稳定性已证明。
- N5-ET-TXT交付96c9bc8代码+2b9fb84交接，复用唯一纯验证器：严格UTF8、真实body/file SHA与字节、头部/receipt ticker与期间；错身份/坏字节具名冲突且原件不丢，无下载receipt旧文件只诊断legacy_unverified。新下载加约618 B sidecar，与TXT一起计输出预算；audit默认只读，不增人工签名/许可文件，不改公开wire。
- MAIN集中验收受影响3个测试文件92 passed/26.24秒、10 goldens matched、相关Ruff绿，未重复外线234项/77.76秒全包。正式ET main只读审计43份真实TXT，全legacy_unverified、0收据写入，所有原件SHA/size/mtime和ignored配置SHA保持，独立报告目录/测试根恢复absent，0HTTP/翻译/模型。已从63c4090快进并推main2b9fb84；真实git ls-remote核一致。该仓未配置CI，不冒称远端CI绿。
- S0–S6核心已有实际收据；N5-DOCSET/RAW-DUP扩展仍由外线负责，未收到完整交接，不接管/重派/标完成；RAW-DUP约7.44GiB只是元数据上界。用户CWP source_acquisition修改、RF owner两日志和ET两个untracked文件全部保留，Dayu/IQS零写。
- 工具/验证夹具错误：run10前sandbox psutil DLL拒绝访问，在POST前失败，正常用户环境运行成功，未改配置/依赖；ET首轮audit索引Windows反斜杠、查询用斜杠而KeyError，改相对路径as_posix并在已合入主线实际核验43份通过。首轮编排未因退出码截断，导致并线先于该只读audit，代码责任包与public wire已先绿；后续依赖mutation必须检查返回码。电话会离线首轮直接decode原TXT导致span IDs不匹配，改复用产品material规范化后原断言全通过，没有放松引用校验或改产品代码。

## 2026-10-06 — R6实际缺口、兼容容错与RAW-DUP审查入口

- 已采纳R6与旧实现存在差距：任一未知citation/extra会整体失败。新私有边界投影仅保留canonical字段，坏claim整条丢；来源/语言/全坏/翻译与严格JSON仍失败。RF质量枚举不支持新增partial，因此复用needs_review表示摘要不完整、无人工签收；public parser继续严格。共享identity/claim纯验证器，分析师问题必须question，费用在解码前结算。prompt1.5.1绑定请求hash，不改Config或付费预算。
- 184责任Unit及真实字节/确定性模型正式CLI离线E2E通过；不会把loopback称新vendor验收，也不拿citation合格冒称语义蕴含正确。两次reader unavailable是fixture config布局错误，修标准config/后CWP与RF读均绿，不改生产接口。测试根已恢复absent。
- N5-RAW-DUP完整交付e40b4ec，7,804,167,537 B逻辑重复候选上界不是磁盘释放；只有3组/158,223,532 B实际SHA复核，3528组未实读，deleted0。MAIN审查物理空间测量/预算/输出路径，未验收，不自动删除原件。

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

## 2026-10-06 — MAIN兼容与业务标准先行

N6三包人类已分派，MAIN只做共享责任。正式final按完整EvidenceSpan/parser定位回放，不重跑selector；旧summary-only孤立pilot相反，不能把pilot风险外推成正式reader缺陷。冻结旧0.3.2、模拟当前0.4.0且禁用selector的9项真实catalog/artifact Integration已过4.85秒，包含新group IDs发布后旧ref不变、raw等长篡改与恢复、legacy spans0/持久字节不变。fixture由正式Worker/outbox生成一次，3格式合成原件+local模型，冻结JSON17KB，不在未来实现下重新造oracle。无运行时代码修改或新门。

33 required保留原分母与golden不变，独立业务解释划28经营事实+1项目完整上下文、3纯财务指引/金额、1正文外provider摘要。主要语义修正：S07 G01是境内约8.19亿元/22%，不能标成海外22%；S08是历史2023克重口径产品组合，不称2026数据；S06行业进口替代为2016—2020回顾。industry forecast、拟收购/认证/建成投产/意向书和actual必须按原话保留。统一表绑定实际golden/samples字节SHA与quote SHA/locator，未来仍报告实际/33及每点原因，不用业务分类把漏项清零。

RF6e6b817a/2 owner SHA与CWP user config3609e707保持，三外线零写。独立scratch和两生成脚本均absent；正式9样本新selector基准与Worker→search/exact→RF仍等质量代码交付后做一个大节点，没用本回合合成compat冒称新实际质量已完成。

MAIN已实际推0947cea，精确CI37532408169 attempt1 success/job80秒，普通CI没有新增长Integration。请求input_hash已有selector/parser/prompt，批次生成身份包含此请求，shared selector_version更新会区分新批次；最终fresh process联调需复核实际传播。保存CI JSON里的job/steps已实读验证；OrderedDictionary的Select-Object显示null是输出展示问题，未影响真实收据。

## 2026-10-06 — MAIN业务路径施工框架

复用正式configured batch/Worker/outbox与RF六模块committed export，三类合成PDF/TXT最终1 passed/27.65秒，恢复无新增POST。正式RF校验所有transcript bindings但context不返回它们；因此E2E从CWP同ref的正式read取得bundle，核artifact SHA和RF spans一致后按start/end对象映射原文quote字节到material行。不能直接把golden原TXT行号当material行，也不能扩大RF公开投影只为测试方便。合成TXT已实际覆盖映射路径，真实节点仍待新selector合入，未运行不计绿。

只有测试helper增加可选timeout，默认60秒不变；真实180秒batch/240秒subprocess为明确fixture请求，不改生产限时。没有运行时代码/外线写入/供应商调用/日常CI长测。RF owner新增daily日志，三个SHA实读保持；三个自有tmp根已恢复absent。框架receipt与施工细则在MAIN独占目录，后续验收按原四个不可变业务点与九类完整基准，不修改golden或分母。

框架实际发布13bba07/远端master一致，精确CI37534879855一次success，全部step绿/job74秒。本地Integration和CI快集合分别记账，不假报远端跑了此新长测试。三外线仍独占bootstrap工作树，MAIN只读核对不恢复/跨写；下一实际交付后统一合入，当前质量仍12/33。

## 2026-10-06 — 升级隔离实证与旧队列修正

build_batch_events确用request中selector/parser/prompt hash划新身份；正式CLI/Worker实证旧run拒绝复用、新run/目录三job独立、new artifact绑定测试下一版本、旧ref继续返回旧字节、新run恢复不增任务。1 passed/16.33秒，纯流程PDF0模型。只改变测试子进程bootstrap的版本常量，不能代替未来实际候选/预算业务验收。Windows测试launcher须__main__保护；SourceRef内部DTO与public SourceRefValue、ir_policy路由标签与investor_relations来源身份必须分清，不放松产品合同迁就测试。

完成证据旧N5待交付状态与总计划矛盾，已修成ET/RAW/DOCSET实际并线SHA与精确CI，以及当前N6/S7未完；未来RF owner保护按执行前status再读，目前三份。四tmp根恢复absent，产品/外线/外仓零写。此节点复用AUTO与reader，没有第二任务库/来源合同，也未加日常CI长测。

实际发布55a55c2，精确CI37536310001一次success/全部step绿/job54秒；已保存真实head/job/start/end/steps。本地新责任case的16.33秒与远端日常快集合证据分开，整体目标不因本项通过而complete。

## N6-FOOTPRINT验收发现（2026-10-06）

路径叫tmp/cache不能覆盖已知原件或采集staging的保留身份；automation.*不是可证的Store标记，更不能把根目录及全部子树归为AUTO。目录枚举属于时间预算责任，单次OS阻塞仍不可抢占。MAIN修正并以52反例/责任测试验证。报告只列逻辑量，不把stat当已证磁盘分配量；本目录96.2941%为原件，旧清理没有把原件删掉，新派生只有约2MB。不新增处置审批文件；可重建/未使用是实际正确性检查。新小报告/保护收据在results，详情见n6_budget_footprint_main_acceptance.md。

## N6-BUDGET验收发现（2026-10-06）

整组内容集合相同不足以证明同一事件：相同答案可能属于两个问题，相同表格行可能在不同年份表头下。来源/解析版本/语言/精确角色/QA父问题与发言上下文均保守绑定；跨组比较保留句子顺序，混合summary组拆分且不与现有ID碰撞；budget group/item键也必须分命名空间。15个反例RED→GREEN，实际0.3.3责任145及真实TXT/AUTO2绿。旧0.3.2final不用重跑选择器，冻结9项通过。候选算法还未交，不能把hand-built候选的13/33预测记成正式质量达标。空间工具精确CI已全绿68秒，预算发布之后补本线精确CI。

实际budget3cd4960已并线/推，footprintcf24f34已并线/推；git祖先核查两分支均包含于master。候选新交接ce61cdd只读可见，下一MAIN集中验收，不重派旧卡。最终S7完整节点仍未执行。

两个代码提交精确CI各68/72秒成功；无新增日常长测试。GitHub同URL状态缓存需nonce/no-cache复核，避免过时in_progress误导。下一候选新交接只读可见，正式S7仍需统一真实质量节点。

## N6-CANDIDATE MAIN责任审查（2026-10-07）

外线9a4b815保留原locator/parser0.1.0与原语言；MAIN实际合入f31cc0d。先RED的9个边界失败已修正，另一个固定预算竞争反例证明quantified_operating_status原先掉入other，使具体经营结构输给笼统行业背景；映射经营状态rank3/独立category后GREEN。共享selector升0.4.0，原96/160不扩、原golden/33分母不动。264项责任包3.20秒绿（外线30+MAIN12+预算/旧选择/解析/检索），Ruff与7源模块mypy绿。

并线没有文本冲突不代表语义组合正确。补全现在同时校验source/parser/language/role/page和问答、speaker、section；关联问句在相同source/parser/language中找answer，允许问答角色不同。经营窗口统一调用传入OperatingFactDetector。九文档正式全表与真实Worker/RF/search/exact/恢复、旧final9和升级1正在独立tmp执行；0模型供应商请求。不把候选覆盖手推值或旧CI作为本次完成证明。

真实组合E2E两次因EPI遗漏失败，默认annual396候选/393去重/96精选证明不是PDF丢字。第二次深入候选显示补全普通尾句继承全页product_milestone/score20而挤掉真实EPI11。修正逐句topics/reasons/score和独立sentence组；一般开工→未来投产timeline单独表达、已有候选保留全部fact reasons。最终269项2.81秒、Ruff/8模块mypy、真实三样本四经营点+旧9+升级1共11项66.48秒绿。原parser0.1.0/原定位/96与160不变，0供应商/费用。

初次full18/33不作为最终完成证明；已保留报告。S08两噪声实读同一219字orphan_answer cell，含数字4/5题与接待套话，旧问答parser未分段；保留质量诊断与原golden，后续解析责任整改，不能为噪声删掉占比事实或静默篡改旧parser回放。全文→永久MD没有恢复，此次仅tmp解析与小报告。

最终正式全表在集中修正后21/33、optional5/17，旧所有full无回退；业务/项目上下文20/29只是解释子集，原正式33分母不变。764定位0失败、重复3、精选66195B；372.044秒只用于大节点、非日常CI。明确remaining9与IR两套话/年报重复1进入S7后续；原required3个scope漏项及incidental guidance命中不当业务增益。详细逐点对照、8源模块精确SHA、原件9SHA、user config/生产配置/RF三owner和scratch恢复在n6_candidate_main_acceptance_2026-10-07.json。

## 2026-10-07 发布已完成（覆盖前述等待状态）

候选actual merge e8c645e7afa6e2e60ddfa532e612ba0580d15560已推master，交付f31cc0d为主线祖先。精确CI37547043642 attempt1全部job/step success，job112553429162用时53秒。正常commit/pre-push绿，0日常长测试新增；原件/用户配置/RF三owner/外线保护保持，8个本次tmp根恢复absent。最终nine-doc21/33、old-full零回退、重复3、764定位零失败；269责任项+11真实/兼容/升级节点绿。N6三线实施交付已接收发布，S7继续处理验收单明确的9个业务漏点与3噪声，不冒称整体质量已全达标。[完整收据](harness_lanes/results/n6_candidate_main_acceptance_2026-10-07.json)。

## S7剩余点分层诊断（2026-10-07）

限定原golden表页、同原件全部PDF正文，初探62.298秒，追加contributors探针解释具体组/score/drop，未改变规则。9点中7点candidate/dedup完整但budget淘汰；S01 G05在candidate阶段缺失，S06 G03在dedup后原page43不匹配。后者的完整原句实际已在同原件另一locator精选summary组中存在，是合法canonical去重，不强行保留重复page43或改原33分母。S06 G04同一断句被两个独立operating fact窗口分开：page87 p11以“一定”结尾已选，p12未选，句子不完整。不是所有漏项都需要加关键词/扩额度。

已写11个独立一般表达责任用例，夹具metadata漏项纠正后7个真实产品RED/4通过/0.67秒；正例区分应用/批量销售里程碑、并购（含计划词）、量化行业前景、具体募投生产线与物理产能，负例限制纯收入/募集金额与“投资以下项目”独立引导句。测试预算纯输入/固定16、输入逆序稳定。实施将保留新具体reason，即使旧generic progress已识别，也不能丢掉具体语义；不调公司/页码白名单。

S7后续实证：G-S06-03完整达产quote已在同原件page7 p12—17入选且原情态保留；page43缺口为canonical去重，不为golden复刻重复。G-S06-04两片段一句分组先修为原子组，但泛industry预算仍会挤掉，于是只给量化事实独立类别。G-S01-05识别将达后candidate full，预算仍miss；不增加96/160，按量化行业类别修。S04page34 intro p14/15与具体募投表row1/2真实存在，但抽取顺序中法律段落p17—22插在正文intro与表之前：下一实现不能按索引近邻认定联系。完整报告s7_gap_stage_after_operating_rules_2026-10-07.json明确是声明表页诊断，不是default/full-table正式验收。

本轮quality实测业务解释26/29、原required27/33，不能拿解释子集或canonical另页替代正式golden。两optional退步均有明确原句：主要负责公司海外的销售（静态主体表职责）及项目预计年营业收入/净利润（纯效益数值预测），低于已实现采用/订单/具体收购/量化行业动态的优先级。保留optional退步证据与原始资料，调整收据质量审查口径为required/business无退步+optional透明具体取舍，不修改原benchmark/evaluator/产品断言，也不为最大化所有optional扩大切片预算。


## 2026-10-07 S7经营节点发布收尾

S7最终发布证据：9bf25a5/CI37550268890全部步骤绿71秒，真实业务节点零供应商调用并恢复测试根。空间不因本轮扩大：九文档精选66195→66215B，只多20B；7诊断/质量/收据总354203B（最后补CI字段后略增），14个临时路径恢复absent。未改变96/160、原86点/33分母、原件或任何外仓owner文件；业务必需覆盖21→27，optional退步2项保留原结果。

## S7 IR解析责任发现（2026-10-07）

一个cell不等于一个回答或一个证据。数字4/5混合cell需要先识别问答边界，再按实际原cell范围拆句；相同正文但不同范围/QA的临时unit ID必须不同，否则预算映射可能碰撞。QA多句跨页续答只继承同来源/解析版本/语言及同cell顺序绑定；下一cell或远页答案不能因出现答字而借前题。0.1.1回放核片段SHA和问题归属，0.1.0旧pin不静默换算法。以上不增加人工审查或权限门，不跨仓改消费者。26个新责任用例及91个既有相关用例已集中通过，真实IR两套话已在正式消费链断言clean。


## 2026-10-07 IR集中本地验收收口

最终九文档400.944秒：required27/33不变、761定位零失败、角色/情态混淆0、精选66215→62953B（少3262B），负例命中点3→1、噪声span3→2、重复4不变；S08两套话clean、占比事实仍full。optional3/17→2/17：G-S07-07是投资者提问，内容包括研发占比及PI/PEEK等新品验证/性能担忧，并非只是财务数字；原管理层答复实读为泛研发布局/长期开发/财务同比增长。旧整答案混合得到current_business_progress并挂问题，新句级解析没有具体进展入选，因此问题退出精选。记录这个问答上下文取舍，不把投资者担忧冒作公司已确认事实，不泛化允许丢实际业务动态；原件保留，原golden不改。三条先前optional取舍仍可查。

全Unit一次1688通过/10失败/140.93秒，均为英文测试把默认写死0.1.0；补显式旧TXT pin与新默认的文本/角色/定位同等并回放旧pin，不削业务断言。相关143复验1.35秒绿，新QA含29项；全CI范围Ruff及45源mypy绿。真实节点/冻结9/两种实际升级12项52.16秒绿，不重复长套件。全九报告和IR小收据保存，9原件/两配置/RF三owner/10运行源码SHA不变；10个自身tmp根、包装文件/脚本/缓存全部恢复absent（全Unit临时逻辑58,364,951B已删除）。日常CI没有加入全九或真实长E2E。

正常发布准备，精确CI未完成前不冒称published。后续仍须处理应用句与募投表联系；S7不complete。receipt生成脚本首次补丁上下文不匹配、没有修改，随后修正；UTF-8显式配置继续执行。


## 2026-10-07 IR0.1.1发布完成（覆盖此前准备/等待状态）

实际代码c1295b12b652006ec4713e1155170ac66cad7406已推master；正常commit/pre-push绿，精确CI37552600440 attempt1全部step/job成功，job112571348105/75秒。CI全Unit和短合同全绿，先前版本写死的10失败已在推前责任包解决。11个自身tmp路径/脚本/缓存恢复absent，原件/用户配置/RF三owner及10运行源码SHA保持，另记published Git blob SHA以处理换行差异。正式收据状态published_exact_ci_passed。没有日常长测新增或供应商调用。

下一唯一施工动作已写总task_plan：RF状态核查后处理S01应用事实预算，再处理S04募投intro/项目表真实联系。S08两套话已解决；S7仍in_progress，不能拿九样本定位绿冒充所有业务覆盖完成。旧N6/旧IR等待文字不恢复为门禁。

## 2026-10-07 S7应用事实/募投表节点调查

基线5f8a3ef（代码c1295b1），RF仍6e6b817a且三owner dirty，用户配置只读保护。上一回合IR节点实际发布属于进展；本回合先调查，不重验IR。已用Poppler实际渲染并目视招股page34：募投引导两行在表上方，单位万元之后为“募集资金运用方向”表；两项具体项目为设备扩产升级/研发中心升级，补充流动资金/合计不是业务项目；法律管理段落实际在表下。渲染有用户名路径字体映射警告，但输出汉字/表格完整可读。原解析把表单元附在正文后，不能按paragraph索引联系。

只读探针正在捕获当前默认年报的全部operating_milestone预算竞争与招股page34的原bbox/headers/候选组；招股本探针table_pages=(34,)是局部诊断，不作正式全表质量证明。待真实诊断后写具体接口/TDD/端到端实施单；当前运行代码未改，无供应商或下载。

新诊断已完成33.485秒，protected/原件SHA保持，默认年报400候选/96精选；operating_milestone花16span，真实客户采用和基地投用混类，全球应用句13分miss。招股table34探针885候选/160精选，两项目行均未入候选，仅引导2span低优先级被淘汰。按真实布局/表头与类别责任写了s7_adoption_fundraising_implementation_2026-10-07.md，生产代码尚未改，下一集中TDD，不按公司或页码保留，不增加配额。

应用分类与募投联系实现后，局部真实探针31.596秒：默认年报G01/G02/G03/G04/G05均full；招股table34解析G01/G03/G04均full，引导2+具体用途项目行2为一个原子组，法律说明不借组，单财务用途行不参与。该招股诊断仍非默认/完整全表证明，必须以正式Worker与全九验收为准。预算分类使用具体事实reason，不追加分数；视觉关系只在同源/版本/语言/角色/页、有效坐标、有限距离/遮挡/上限下建立。28新用例含NaN与同距两表歧义，相关总200项绿；static完整CI范围+新源47mypy/Ruff绿。

0.4.2完整九文档29/33，原required/optional full零回退，精选+120B、761定位全绿。剩余四个正式required miss：纯融资金额G-S06-01、同原件其他页已canonical的产能G-S06-03、正文外provider G-S09-01、纯财务guidance G-S09-03；不得改golden分母。canonical另页在当前默认pipeline已重新验证2span full，不能只沿用旧版本证据。新6重复中S04增加2，评价器仅比较原文，不比较事件/表头语境；现去重层按整组、表头和角色保守处理，不能仅用字符串相同拆掉完整募投联系。具体重复诊断另记，不将低比例或省空间当假零重复。

本节点精确CI37555504675对应aa52cbd，全部步骤成功/81秒；不是此前IR提交绿灯。依赖安装26秒、Unit35秒，本次既有简化CI仍一平台一Python，无真实全表/外发矩阵增加。正式发布与测试恢复证据已完整，可进入原目标逐项核查；核查单只归集已有证据与真正缺口，不增人工签收或要求重复旧大节点。

完整目标核查实读：CWP ed2dc51仅用户配置dirty，RF6e6b817a三owner保持。正式narrative_batch._final_documents实际调用终态压缩；Supervisor P1为mixed1、P2 compute1/model1、P4 compute3/model1，子进程factory各自创建客户端和SourceVersionReader。不是所有模型并发4。准备阶段当前deadline在_run_owned才开始计，build_batch_events及逐原件open前后没有剩余时间检查；这是需TDD验证的资源预算缺口，不新增人工门。下一仅针对准备超时和停止读取下一来源验证，已绿S7全九/付费/kill大包不重复。
