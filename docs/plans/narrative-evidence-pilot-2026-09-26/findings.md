# Findings：当前事实与待验证项

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

## 2026-10-04 — StockInfo 原工作树 WIP 审查

- 用户明确要求核对 StockInfoDLSimple 未提交改动并清理不需要项。CWP `config/source_acquisition.yaml` 当前实际引用 `../StockInfoDLSimple/v2-clean-rewrite` 的 1.1.0 JSON CLI；因此恢复掉当前checkout中 adapter、CLI、CNINFO client 等未提交文件会使该配置失效。bounded commit `947e839` 虽已存在于独立分支/远端，但尚未切入配置所指目录、CWP也未切至1.2.0。故未做全量 restore；保留功能性代码、测试与夹具。
- 相关回归 **88 passed / 19.96s**：下载器、CNINFO API、真实/合成fixture合同、company-wiki adapter与CLI。全局 pytest plugin autoload 首次因 `langsmith` → `pydantic_core` DLL import 权限错误无法启动；仅本次命令禁用自动插件加载后通过，没有改测试配置。`git diff --check HEAD`通过。
- 清理项限于：`lookup_a_shares.py`（硬编码读取company-wiki物理目录并生成已存在名单，违背pathless来源接口）、`reorganize_downloads.py`（未被调用且会按文件名无hash删重，目录分类已由`save_subdir`完成）、确认0字节的意外 `nul` 文件；另将11个仅有无用import/格式调整的tracked文件恢复至当前HEAD，index未动。保留 README 使用的 `a_share_companies.txt` 与研究目标 `companies.txt`、fixture捕获脚本、适配器和功能WIP；未触碰任何下载原件。StockInfo工作树仍有未提交功能改动，需在其owner集成节点再审查/提交。
