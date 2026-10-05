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
