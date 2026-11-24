# 调查发现

## 2026-11-16 真实 provider 复跑

预算补齐后，FF 的首次真跑已进入供应方。CNINFO 发现消费 2,672 字节，精确定位到 StockInfoDLSimple 的候选缺少经核对的证券代码。SID 已在本仓按原公告证券代码校验并输出。HK/US 错误发生在 HTTP 之前。配置中的 Dayu venv 带 Windows Low 完整性标签，部署的 staging 和 provider-state 同为 Low，而旧测试库的普通 Temp 为 Medium。改用 Windows 已有 Low 临时根里的独占测试库后，港美股真实采集通过。四例正式复验、版本及 RF 历史记录见 [收口证据](review/m3-formal-t3-20261116.md)。

## 2026-11-16 有限下载复验

FF 1.1 已能透传有限下载预算。缺三项业务限额时，CWP 会在启动 provider 前拒绝；同一请求补齐后，离线组合成功。已有 CWP 正向夹具的两种失败可以分别复现。一是缺 `security_id`，被正确拒绝；二是整体测试限时 2 秒，发现步骤可能已用尽时间。修正测试输入和运行夹具，保留生产验真及超时合同。来源与复现见 [验收记录](review/ff-cwp-bounded-offline-20261116.md)。

## 2026-11-14 当前仓库所有权决策

模块化的并线动作必须留在代码所属仓库：owner 负责理解本仓提交/脏改动，按当前公开接口适配并做本仓测试，然后提交、并入和推送。ROOT/company-wiki 可以协调接口和做只读组合验收，但不跨仓改文件或操作 Git。StockWiki 有另一项目正在改动，需等该项目 owner 交接后再由 StockWiki owner 自己接续；不能把旧审查结果当作允许 ROOT 直接写入的依据。

## A1逐仓审查与接收（2026-11-11，历史）

完整结果见reconciliation.md及review/repo_reconciliation_20261111三份逐仓报告。范围8仓390分支/remote refs、253工区，另7RF tag和2CWP stash。最重要的纠正是：refs未成祖先不一定漏并（FF job已整合接收）；tracked clean/untracked=0不代表无原件（四个RF Temp仍有msft原文）；release与main确有公开能力差额（RF B37、SW C38/B03、CWP历史CLI），不能说全部已并线。

本轮已受测接收FF明确null发布日期修复与Dashboard边界WIP，均独审、main推送。SID11项WIP的路径子串/跨请求CONFIRMED_EMPTY/空tab全页回退问题已写原卡A0；不直接并入。Dashboard真实stream24-case缺owner入口仍未通过，归CWP T-READ/ROOT组合；静态扫描和mock通过不替代该证明。清理仅限确认测试产物、已吸收副本/空工区/旧生成物，独有账目、原件、业务状态、研究历史保留并分配owner。

## 2026-11-11 初始快照

- CWP HEAD `08dfe8bf1ae97dff34b28976d532b3482d3ba358`，跟踪文件干净；源码最近提交 `54f8b470c` 完成 source stream/parser owner 子节点。
- 父计划 D4/D5 已有局部 ACCEPTED，但 P3 中“所有模块/跨仓 owner 边界”没有有限清单和统一退出矩阵；父计划仍包含更早“全局 ACCEPTED”的完成定义。需要区分历史验收范围与当前全局结论。
- 最新工程证据证明一个 source/parse 子节点，不能代替所有业务入口的依赖和隔离覆盖。
- 本轮只读调查，不执行收费调用、不修改源码、不清理历史运行材料。

三份独立调查已补全，当前静态确认/风险/未运行验证分别记录如下及review/。

## 三路调查归并与采用决策

- CWP已有边界实质有效；剩余共因是消费者依赖protocol未声明的能力、纯类型经具体runtime导入、低层隐藏读配置及实际安装证明不全。CWP-01..05由单一作者覆盖七内部责任，避免多个harness争抢catalog/tests。
- FF已提供WikiConnection/TranscriptTransport/六operation；缺的是全交付形态隔离与请求配置/启动细节的明确归属。测试先行，若已满足则NO_CHANGE_PROVEN，不强制搬目录或创建wheel。
- RF主来源链pathless已有；旧canary随runtime直读上游SQL、core/report聚合依赖仍需收敛。历史B34路径要求是已声明profile兼容范围，不能为可移植性重签旧材料；默认操作不得因此依赖CWP私有布局。
- ET supervisor/provider和worker协议依赖方向需分离；worker固定结果表示帽是静态风险，先RED验证再按实际请求quota归一，不能直接认为已经发生真实生产误拒。
- SID两个同owner根因：fetch丢错误类别/retryable；API反向导入adapter私有metadata。合一张卡修纯domain与typed结果，保留原11项WIP。
- StockWiki/Audit主要公开边界已有，没有为它们强造实现卡。Dashboard两份可见配置使用release code roots与主仓data roots，实际在用tuple尚未核验；不能说主仓缺CLI就是部署坏，也不能覆盖既有4项WIP。
- 新浪三表实际owner为CWP source_catalog/financial_statements，FF是公开客户端；PDF策略/SDK归解析/阅读层。本轮不将金融表移回PDF路径。

三份独立源证据在review/；它们记录静态确认、风险及未验证，完整测试只在后续owner实施和ROOT大节点进行。源清单479项是覆盖清点，不是逐行功能审计声明。

## 避免再次无限收尾

固定boundary_matrix的有限责任项与E01–E09出口；活动入口和交付包覆盖也进入清单。局部测试/代码行数不是完成标准。原主线摘要召回、模型/假设、真实付费恢复与公司循环单独待办，关闭架构后继续。

已有AST规则保留实际越界反例，不继续扩建通用Python解释器。设计本身用pure值、显式依赖、状态单owner、替换实现和无邻仓安装验收隔离；工程检查不变成生产审批/授权/日志大小许可。

## 方案独审发现及修复

1. 原interfaces文字会要求lane等待ROOT新的contract fixture，且仍误称四卡；已改为本仓合同/fixture立即A→B→C，ROOT只在M2选真实组合样本。
2. RF卡原“移动自包含执行包”可能误导作者改B34历史绝对路径身份；已限定历史profile兼容与当前默认隔离，可移动测试只覆盖已声明可移植artifact。
3. 原安装指令不够具体；新增runtime_verification.md，明确CWP wheel、FF/RF canonical installer临时destination，以及ET/SID脚本runtime显式闭包；任何卡不得省略参数同步全局目录。

## 最终方案复核

独立方案复核PASS，全部本轮可行动意见已关闭。安装参数、37个既有测试路径的静态存在已核；没有运行产品测试或实际安装。后续卡完整验收由各owner实施，ROOT最后组合。

## 2026-11-14 继续核查实际边界

- CWP `SourceVersionReader.catalog` 暴露了底层目录对象，调用者也能直接调用读取器内部方法。解析和导出装配把完整读取器交给消费者。导出只使用 `open_version`、`verify_version` 和 `describe_version`，当前运行时却要求解析与流式方法。分别用属性反例、公开读取行为和独立后端证明。
- StockWiki 本地 `master@f2bc73f` 已有 MC-SW 接收的 C38 接口和 B03 assessment。真实主工作区另有 Quick Scan 未提交改动，复验以提交为基线。仍需验证 StockWiki 的 CWP 证明客户端能否使用独立安装的公开命令。
- Dashboard 老测试绕过 adapter，调用 CWP 已移除的私有读取器和锁函数。应该在调用方用真实公开流和已知夹具验证拒绝语义，在 CWP owner 内验证打开字节和事务提交语义。Dashboard 主工作区有另一路正在改动的文件。

## 2026-11-15 — Distinct company legal forms must not auto-resolve

CWP1's broad suffix class treated `PLC`, `AG`, `SE`, `NV`, `SA`, `LP`/`LLP`, and two different Chinese company types as interchangeable. An exact-name fixture reproduced a false `resolved`; after narrowing exact normalization, a long canonical name with a suffix-free alias still auto-resolved through strong fuzzy matching. The general fix is owner-side: preserve only same-form spelling expansions, encode the two Chinese within-type alternatives in Company Law Article 7, and inspect the selected security record's canonical name plus every alias before fuzzy auto-resolution. Keep an explicit exact alias usable. No new status or manual-review gate was added; conflicts use the existing ambiguous candidate result. RED/GREEN, legal sources, exact hashes, test scope, and independent PASS are in `review/cwp1-legal-form-identity-20261115.md`.


## 2026-11-15 — Git worktree-status error isolated to sandbox context

The previous read-only commands in the restricted sandbox returned fatal: this operation must be run in a work tree for FF, RF, and StockWiki, although rev-parse reported a worktree. Repeating the same status operation in the approved elevated host context succeeded for all three, and fresh git ls-remote calls confirmed live FF/RF main refs. This establishes an execution-context difference; there is no evidence of a repository configuration defect. FF and StockWiki tracked files are clean. RF has two tracked weekly-assurance modifications and its local main is eight commits ahead of live remote. Status was run with --untracked-files=no, so no conclusion is made about untracked files. All owner repositories remained read-only.


## 2026-11-15 — Root-level planning files are historical indexes

Inspection found the root PLANNING_STATUS.md still presents a 2026-09-12 approval snapshot, while root progress.md and findings.md stop at 2026-10-04. The selected PWF plan is under docs/plans/du11-source-closure-2026-10-18 and its M3 child; root files are retained as historical logs, not rewritten. Added prominent links at their tops to the current-status, module-boundary matrix, and handoff. This removes competing apparent execution entrypoints without deleting history.


## 2026-11-15 — Root planning-doc push range falls through the runtime smoke classifier

A PWF-only commit changed root PLANNING_STATUS.md, progress.md, and findings.md. The pre-push hook ran its fixed 18-case smoke and mislabeled the range as runtime/configuration; its scope preview listed nine unique target nodes, but parametrized cases produced 18 test instances. The smoke passed and explicitly left full CI pending. The classifier recognized README.md and docs/ or .planning/ paths, but not the four root PWF filenames; its generic fallback overstated what it knew. Root PWF Markdown contains no executable behavior. RED tests reproduced both defects (12 failed / 4 passed); the exact root PWF files are now classified as documentation and the fallback says only that the range was not positively classified as documentation. Runtime, mixed, and unknown ranges still run the fixed smoke. The combined regression later passed; see progress.md.

## 2026-11-15 — pytest scratch cleanup must clear Git's read-only object bit safely



## 2026-11-15 — Full-CI regressions were outside the fixed push smoke

The failures in run `43749426185` were not blocked by pre-commit because the commit hook is deliberately static and does not execute pytest. The prior fixed push smoke omitted relevant exact regression cases. Focused reproduction found a joined-group predecessor scope error, an eligible 79-row operating table incorrectly routed through a prose-only group bound, a planned-PDF observation test patching the wrong imported name, a work-budget fixture calibrated before the existing negative resource scan, and a paid-response replay test with a stale expected set of current qualifier diagnostics. The table fix retains structural qualification only after the owner has qualified the table and selected eligible rows/context; normal fact and semantic admission remain. Five cases were added to the bounded daily smoke. GitHub's annotation reported 32 failed instances; the full annotation-driven 12-file subset passed 469/469 locally on Python 3.13.9. Exact root causes, test output and independent review are recorded at [CI failure root cause](../du11-source-closure-2026-10-18/review/ci-failure-root-cause-20261115.md). Commit `895f66f57` is pushed, and exact-head GitHub CI `43755195576` later completed with four failures. The initial 469-case local result did not cover the inventory parent contract or test host mismatch; keep this incident open until the follow-up's exact-head CI is verified.
Follow-up: the four residual CI failures were test inventory/platform assumptions, not additional product defects. The five new unit nodes now also appear in parent `FAST_CONTRACT_CASES`; CI's contract remainder still filters unit nodes because the full Unit phase owns them. The Windows no-replace rename case is scoped to Windows, and a POSIX-adapter companion proves hard-link denial propagates without replacing a racing object. The 13-file annotation-driven set passes 500/500 locally. Independent review PASS at baseline `895f66f57` confirmed the inventory filter and no-clobber assertions. Commit `1391ae81d8126b5026209e26ae56a7d9bb0a9f0c` is pushed; exact Linux GitHub rerun `43757282611` passed. See [CI root-cause review](../du11-source-closure-2026-10-18/review/ci-failure-root-cause-20261115.md).


## 2026-11-15 20:52 UTC — M3 reconciliation clarifications (historical snapshot; superseded by 21:28)

- A passing provider E2E is evidence only for its exact fixture/ref. FF's S3 BYD bounded-provider test and FF-1 merge are separate from the four failed RF weekly T3 download requests; the latter still need finite `acquisition_limits` plus a rerun against current FF main.
- RF's current local main is nine commits ahead of live remote, not eight; two tracked weekly-assurance files remain modified. Preserve the exact failed run's historical dependency tuple in its owner PWF rather than attributing it to current source heads.
- StockWiki is no-remote, tracked-clean; recent committed source-link/handoff changes do not update its stale root task plan automatically.
- Historical 20:52 finding: the uncommitted CWP 64MB→512MB cap change had only a threshold assertion. It was not retained; the root cause and behavior-level fix are recorded below.


## 2026-11-15 21:28 UTC — CN issuer proof had a duplicate resource-budget owner

The standalone 64MB cap rejected a valid 126MB/36-filing corpus because `open_described_version()` could not accept the shared SourceCatalog `ReadBudget`. Increasing it to 512MB would keep a second quota owner and encode one corpus size as policy. The fix passes one browse-scoped budget through the source reader into the existing resolver, and removes the local cap/counter. Exact SHA/size checks and per-PDF/page/text ceilings stay with their existing owners. Full details and independent review: [CN issuer shared-budget review](review/cwp-cn-issuer-read-budget-20261115.md).

The same test run also exposed a pytest resource-lifecycle defect: an existing test created a second SQLite-backed SourceCatalog and closed only the first, making Windows teardown fail after test assertions passed. Both catalogs now close in `finally`. This is test cleanup, not a product workaround. This 21:28 checkpoint is superseded by the 21:54 publication receipt below.

## 2026-11-15 21:54 UTC — shared-budget root fix published and exact CI passed

Commit `56d10f269b7c67845c7af66b33083f62d46cde4d` replaces the unpublished 512MB candidate with a browse-scoped SourceCatalog `ReadBudget` passed through the source reader to the existing verifier. The affected contracts passed 62/62, independent review passed, push smoke passed 23/23, and exact GitHub Actions run `43765642890` / job `132969996667` passed on the same SHA in 7m13s (Python 3.12). StockWiki's parallel handoff recorded the earlier `7fd7f248d` state; it remains a historical run observation, and ROOT did not modify the StockWiki repository. M3 is still open for FF T3 and RF PWF/ref owner evidence only.

## 2026-11-16 浏览边界与各 owner 的待验收接口

交错调用复现了浏览实例的请求状态串扰。目录枚举还先读完整历史，再在 Python 侧报告有界前缀；CN 发行人证明另外直接打开 PDF SDK。整改把一次调用的证明、观察和预算绑定在同一私有请求实例，目录返回路径无关的有界投影，解析适配器读取完整物理页。响应字段和版本 token 经独立对照保持兼容。Python 3.14 的 JSON 解码不复现 3.13 的固定深度异常，回归改用实际异常注入验证信封。详情见 [浏览边界验收](review/cwp-browse-owners-20261116.md)。

其它模块分别按 [逐仓计划入口](owner_plans.md) 对账。StockWiki `b4ca912` 更新子计划。IQS 与 Dashboard 的混尺度兼容是实际公开接口的后续问题，历史 StockWiki V2 的 wire 和 IQS 样例仍保有各自的验收证据。FF T3 限额和 RF 周跑归位继续是 M3 待收件。

## 2026-11-24 全 12 模块架构独立性与私有调用深度审计（只读）

对全部 12 个生产仓（1,654 个生产 Python 文件、466,417 LOC + Dashboard 前端 `apps/web`）执行了 AST 全量扫描 + 四路源码级人工核验（已剔除 `self`/`cls`、Win32 `Popen._handle`、`python-docx`/`pptx` 内部节点、相对导入误报及 `TYPE_CHECKING`-only 环）。详细逐行落点见 [完整审计报告](review/full-12-module-architecture-logging-audit-20261124.md)。

- **为何 M1–M3 后仍存在大量跨模块私有调用**：M1–M3 主要收口了跨仓公开端口，而仓内模块拆分时未建立分层子包契约与内部 `__all__` 门面，且 CWP 现有 `tests/support/layer_boundary_scan.py` 存在 6 个结构性盲区（同包内 `_foreign()` 豁免、`<shared>` 根无方向规则、`tools/feedback_loop/` 未纳入、`_LEGACY_EDGES` 永久豁免 6 条越层边、无 SCC 循环依赖检测、无注解参数盲区）；其余 11 仓尚无统一 AST 私有访问与循环依赖检查。
- **P0 级仓内耦合缺陷**：(1) `StockQAbyLLM` `src/utils/quick_scan_*.py` 24 文件靠 184 处延迟导入形成单一运行时循环环，围绕 7,530 LOC `quick_scan_work_store.py`，且 `_environment` 在 5 个文件中混用方法调用与字典读取；(2) `company-wiki` 存在 9 个真实运行时环（含跨包反向环 `source_contract/announcement_collector <-> source_catalog/announcement_collector` 与 12 文件 `source_catalog` 核心环），`automation/scheduled_summary.py:33-36` 运行期注入 `sys.path` 导入仓根 `scripts/config.py`。
- **P1 级跨仓与封装越界**：`revenue-forecast/scripts/processed_artifact_canary.py`（及 4 工具）直读 CWP SQLite 私有 `artifacts` 表；`filing-fetch/tools/offline_contract_matrix` 直读 CWP SQLite 并导入 ET `tests.*`；`invest-quick-scan/.../stockwiki_g2b_acceptance.py` 导入 9 个 StockWiki 私有测试函数与 8 个内部 Store；`MeetingConverter/company.py:14,130` 硬编码 `~/company-wiki/graph.yaml`；`StockWiki` 38 处跨域私有导入 + 52 处外部私有调用 + ~20 处绕过 Store 直连 SQLite；`revenue-forecast` 7 文件 `report_catalog*` 环 + 40+ 私有导入；`investment-dashboard` `ops/*` 41 处调 `DashboardService._*`；`invest-quick-scan` 142 个顶层 `scripts/*.py` `sys.modules` 垫片；`filing-fetch` 3 个生产环；`earnings-transcripts` 9 处私有导入；`industry-research` 2,817 LOC `quick_scan_client.py` 占仓 54%。
- **封装标杆与边界基准**：`MeetingConverter` 生产代码实现 0 跨文件私有导入/0 外部私有属性/0 循环依赖；`industry-research`、`StockInfoDLSimple`、`earnings-transcripts` 均实现 0 运行时循环依赖与 0 跨仓 Python 导入，可作为其余模块收敛后的静态目标。

## 2026-11-24 Status
- Full 12-module audit completed.
- 日志发布及进度见[S1 分仓发布台账](../feedback-loop-2026-11-17/s1-p0-blackhole-plan.md)和[S2 实施状态](../feedback-loop-2026-11-17/s2-unified-logging-plan.md)。
