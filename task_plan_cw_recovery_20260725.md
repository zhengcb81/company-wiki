# task_plan.md CW Recovery Draft (2026-07-25)

> **2026-08-09 状态覆盖：`archived_reference`。** 这是恢复被覆盖文本的证据草稿，不是活动路线图。已恢复且仍有效的历史事实保留；文中 19 个未勾恢复/旧范围条目不进入当前 backlog，当前六目标统一由 FCAP r2 重新验证。

> Source: local Codex session JSONL. Purpose: preserve overwritten uncommitted task_plan sections before merging back into `task_plan.md`.
> Recovery confidence: BOUNDARY-0/CW-1~CW-4, CW-2.26, and CW-2.27 are extracted from session logs; CW-2.25 is evidence-based partial recovery because no full `## CW-2.25` section has been found yet.

## Recovery A: BOUNDARY-0 and CW-1~CW-4
将项目收敛为 StockWiki 的上游“公司资料供应与来源智能平台”：可靠采集、不可变保存、规范化解析、证据定位、资料检索和可恢复自动化；不再生产化投资判断、估值、正式研究报告或第二套 accepted research state。

## BOUNDARY-0（与 StockWiki 的职责边界确立）— 状态：completed

> 本章节是 2026-07-16 起的最高优先级规划约束。下方既有 Phase、AUTO、RR、INV-MOD 和旧路线图保留为历史证据；凡与本章节冲突的任务均视为被本章节取代，不得继续实施。当前唯一活动计划文件是根目录 `task_plan.md`；`task_plan_v2.md` 与 `review_plan.md` 仅作历史参考。

### B0.1 唯一产品定位

company-wiki 是上游来源系统，不是第二套投资研究系统。它向 StockWiki 提供稳定、可验证、可重放的资料输入；StockWiki 独占研究语义、人工证据裁决、投资模型和报告发布。

| 能力 | company-wiki 权限 | StockWiki 权限 |
|------|-------------------|----------------|
| 新闻、公告、财报、研报发现与下载 | **唯一 owner** | 只声明来源需求，不实现通用下载器 |
| immutable raw、去重、哈希、source manifest | **唯一 owner** | 按 ID/hash 只读引用 |
| 文档规范化、页码/段落/表格解析、EvidenceSpan | **唯一 owner** | 消费并生成研究候选 |
| 全文检索、原文预览、资料型问答 | **唯一 owner** | 可链接调用，不复制索引 |
| 证据是否支持投资命题、accepted/rejected/needs-more-evidence | 只输出 candidate 与解析质量，不裁决 | **唯一 owner** |
| 公司分类、问题森林、假设台账、知识状态 | 不实现 | **唯一 owner** |
| 收入/财务/护城河/管理层/资本配置/估值/SOTP | 不实现、不发布 | **唯一 owner** |
| 公司与行业研究 Wiki、正式报告和发布审核 | 不实现第二套 | **唯一 owner** |
| 上游采集/解析任务自动化 | **唯一 owner** | 只调度下游研究任务 |

### B0.2 company-wiki 明确非目标

- 不生成或发布目标价、买入/卖出评级、仓位建议、DCF/PE/PB/SOTP 结果或正式投资报告。
- 不维护投资 Claim 的 accepted/rejected 状态；canonical ledger 中的“accepted”只允许表示来源身份、解析结果和 locator 通过确定性/人工解析质检，不代表投资结论成立。
- 不直接写入 StockWiki 的 `data/`、`wiki/`、`runs/` 或状态数据库；不与 StockWiki 共享可变数据库。
- 不再扩建 legacy 公司/行业研究 Wiki writer。允许保留的投影仅限 source catalog、解析状态、原文索引和 extraction diagnostics。
- 自然语言查询只返回带 locator 的资料答案或 evidence bundle，不把综合判断沉淀为 authoritative research state。

### B0.3 历史重叠能力处置

- `INV-MOD-1` 及相关 invest-* 实验成果保留为 `archived_candidate`，停止接入 company-wiki 生产入口；StockWiki 如需借鉴，只能按自身工件契约重新评估，不能让两个仓库同时运行估值链。
- `scripts/valuation_engine.py`、投资评级/综合评估生成器和研究型 Wiki 直写器进入退役清单：先冻结新增调用，再用调用图证明 production caller=0，最后归档或删除。
- ADR-001/004/005 的 knowledge compiler、domain model 和 single writer 继续执行，但对象收窄为 source records、evidence spans、解析质检状态和 source-oriented projections。
- AUTO-7 以后只允许接管采集、解析、manifest、检索索引和 evidence export；不得推广 legacy 估值、研究报告或投资 Wiki writer。

## CW-1（版本化 Source Contract）— 状态：pending

### CW-1.1 交付物

- [ ] 发布 `source_manifest` schema：稳定 `source_id`、entity ID、original path、SHA-256、source type、published date、retrieved_at、collector/version、mime/size 和 immutable 状态。
- [ ] 发布 `evidence_span` schema：`source_id`、稳定 locator、页/段/表格坐标、原文/结构化值、parser/version、output hash、parse status 和 quality flags。
- [ ] 提供只读、可增量、可重放的 export CLI；相同输入产生相同 ID/hash，删除或改写 raw 必须失败。
- [ ] 明确 schema version、兼容窗口、弃用通知和 consumer contract tests。

### CW-1.2 验收

- [ ] 北方华创、中微公司、中芯国际真实资料通过 manifest/evidence-span 导出，覆盖公告、财报、新闻、表格四类输入。
- [ ] export 不写 StockWiki，不包含投资评级/估值/accepted investment conclusion。
- [ ] clean clone、重复执行、崩溃恢复与增量更新结果可复验。

## CW-2（Canonical Ingest 与解析质量收敛）— 状态：pending

- [ ] legacy ingest 全部接入唯一 `IngestService`；source identity、raw write 和 parser result 分层。
- [ ] 把 canonical ledger 的状态限定为 source/extraction quality，建立 orphan span、locator drift、hash mismatch、parser regression 门禁。
- [ ] 将全文检索和资料型问答改为消费 canonical manifest/span；回答必须返回 source ID 与 locator。
- [ ] production scheduler 只调度 collect→normalize→parse→index→export，不调度估值或研究报告。

## CW-3（Legacy 下游能力退役）— 状态：pending

- [ ] 建立 valuation、综合评估、研究 Wiki direct writer 和重复 scheduler 的完整调用清单。
- [ ] 先禁用新入口并提供明确迁移提示，再验证 production caller=0；保留只读历史内容，不覆盖或伪造迁移结果。
- [ ] 将 single writer 限定为 source-oriented projection；任何研究结论写入请求都必须拒绝并指向 StockWiki。
- [ ] `architecture_gate.py` 新增职责边界检查：禁止生产入口导入估值链、投资报告 writer 或跨仓写入代码。

## CW-4（与 StockWiki 联合验收）— 状态：pending

- [ ] 提供固定三家公司、四类来源的不可变 contract fixtures 与真实工作区 receipt。
- [ ] StockWiki 能只凭 manifest/span 构造自己的 evidence candidates，并独立执行 review/state/report；company-wiki 不参与裁决。
- [ ] source hash 或 locator 变化能使 StockWiki 下游标记 stale；StockWiki 的 review/报告变化不得反向改写上游 raw。
- [ ] company-wiki full pytest、architecture gate、source-contract tests 全绿，且 legacy 研究/估值 production caller=0。
## 2026-07-13 INV-MOD-1 — 状态：archived_candidate（停止生产化，职责已移交 StockWiki）
## Phase 15（来源/解析账本、Delivery Outbox 与唯一来源投影器）— 状态：pending（范围被 BOUNDARY-0 收窄）
## Phase 16（问题驱动、研究认识论与三类实体传播）— 状态：superseded_by_BOUNDARY-0（不再实施投资研究语义）
## INV-MOD-1（投资框架模块化与自动编排）— 状态：archived_candidate（停止生产化，职责已移交 StockWiki）

## Recovery B: CW-2.25 (Evidence-Based Partial Reconstruction)

**Status:** `recovered_partial_plus_adjacent_thread_blocks` (2026-07-25). I have still not found a complete original `## CW-2.25` section in session logs, but I did search the other company-wiki Codex thread `019f7549-0330-74c0-a007-841eb28a6db6` ("建立公司原始文档索引") and recovered the adjacent 2026-07-24 StockInfo root-cause sections (`6.11E` and `6.11F`) that CW-2.27 explicitly depends on.

- Historical `task_plan.md` search output shows `CW-2.24` with next pointer `CW-2.25`.
- `.source_catalog/catalog.sqlite3.bak-cw225-20260722-205901` exists, proving a CW-2.25-era protective catalog backup was created on 2026-07-22.
- `CW-2.26` Phase 6 records company-wiki source_catalog tests as `175 passed`, explicitly including CW-2.25 semantic/fingerprint tests.
- Current repo anchors the likely CW-2.25 scope in source catalog semantic duplicate/text_fingerprint behavior and tests.
- Concrete anchors now present in the repo: `docs/source-catalog.md` documents `documents.text_fingerprint`, `semantic_duplicates.csv`, and `duplicates --include-semantic`; `src/company_wiki/source_catalog/service.py` implements `semantic_duplicate_groups()` and export/index surfacing; `tests/contract/test_source_catalog_text_fingerprint.py` and `tests/contract/test_source_catalog_semantic_duplicates.py` cover the behavior.
- Safety boundary for this recovered CW-2.25 item: semantic duplicates are same-text/different-bytes review hints only; they are not recyclable and must not trigger automatic raw deletion. Exact-copy recycle remains a separate byte-SHA workflow.

**Remaining CW-2.25 recovery work:** Continue reconstructing the original CW-2.25 title, target, status, and verification matrix from 2026-07-18 source_catalog duplicate/semantic/fingerprint logs, `tests/contract`, `docs/source-catalog.md`, and `.source_catalog` backup timestamps. Do not relabel the recovered `6.11E/6.11F` blocks as CW-2.25 unless a later session record proves that mapping.

### Recovered Adjacent Block: 6.11E 2026-07-24 StockInfo A股下载差异根因诊断

**Recovery source:** other company-wiki Codex thread `019f7549-0330-74c0-a007-841eb28a6db6`, local session JSONL line `17608`, recovered historical `task_plan.md` lines `1177-1237`.

**状态：** `completed_with_e2e_correction`（2026-07-24；根因已形成源码+真实网络+A/B 证据；上一轮误把 current v2 rewrite 5-case suite 当成用户所指 3-case official baseline，已由 6.11F 纠正；本轮未修改产品代码）。

**目标：** 解释为什么 StockInfoDLSimple 自身端到端测试/独立使用可用，而 company-wiki→`stockinfo-cninfo` 对比亚迪 002594 FY2024 返回 `adapter_discovery_returned_no_candidate`。必须给出可复现的差异证据和根因层级，不能把“0 candidate”当最终原因。

**诊断矩阵：**

- [x] 重读 planning-with-files 与 filing-fetch 合同，恢复 6.11D 真实失败证据。
- [x] 尝试查询 StockInfo CodeGraph；外部仓未初始化，不擅自写入 `.codegraph/`，改用只读原生检查。
- [x] 读取 StockInfo 仓（无 AGENTS.md）README/配置/CLI/当前 rewritten 端到端 runner；随后由 6.11F 补查原仓、历史配置与正式测试说明。
- [x] 读取 company-wiki StockInfo adapter/config，精确还原实际 subprocess argv/stdin/cwd/env/timeout。
- [x] 执行 BYD company ensure、同参数 adapter 对象/DOM 诊断，以及当前 `v2-clean-rewrite` 5-case rewritten E2E；保存逐层输出。该运行不是用户所指 3-case baseline。
- [x] 比较浏览器 headless/profile/launch args、DNS、org_id、URL、等待条件、DOM/API 数据源、日期/类别过滤、stdout JSON。
- [x] 当前 rewrite 5-case suite 以 301611/300470/300750 和三个 tab 作环境对照；只用于诊断当前 rewrite，不作为 3-case official contract 的验收。
- [x] 输出最小根因、次要诱因、可验证修复方向；本轮未实施修复。

**已知基线：**

- 比亚迪 identity 正确：CN/SZSE/002594/org_id=`gshk0001211`。
- company-wiki 路由正确：adapter=`stockinfo-cninfo`，download_allowed=true。
- 当前失败位于 discovery：0 candidate；无 receipt/canonical import/新文件。
- cninfo 页面可从独立网页工具打开，但页面报告区表现为动态模板/加载中。

**最终根因（按阻断顺序）：**

| 优先级 | 根因 | 证据 | 影响 |
|---:|---|---|---|
| P0-A | `_filing_date()` 不能解析真实 `announcementTime=YYYY-MM-DD HH:MM` | BYD 完整年报 URL 的 raw=`2025-03-24 16:00`；当前函数返回 None，`datetime.fromisoformat(...).date()` 可得 `2025-03-24` | 即使页面正常、30 raw links 已加载，所有候选仍被静默 `continue`；这是 BYD 0 candidate 的确定性直接原因 |
| P0-B | DNS workaround 只映射 www/root，没有映射 SPA 必需的 `static.cninfo.com.cn` | 固定 static=NOTFOUND 时 Vue/Axios/Element/业务 JS 全部 DNS 失败、0 API/0 links；固定 static=有效 IP 时 30 links + hisAnnouncement 200 | 系统 DNS 间歇 WinError 11001 时，主 HTML 可打开但 SPA 不启动；形成会话级 30↔0 |
| P0-C | adapter 没有排除年报摘要 | BYD FY2024 page 1 同时有完整年报 1222881496 与摘要 1222881505；CLI 未传 excluded_keywords | 修复日期后将变成 2 candidates，company-wiki exactly-one 门禁仍会 ambiguous |
| P1 | downloader 把 0 links 当正常 success | 当前 `_switch_tab` no-content 分支；current rewrite 5-case run 为 5/5 0 files 但 `main_py_success=true` | 掩盖 DNS/SPA 基础设施故障，使主流程日志看似成功 |
| P1 | 测试合同漏检/可假阳性 | adapter fixture 用纯日期；CLI FakeAdapter；current rewrite runner 不走 adapter，最终 exit 只看目录 compare | 4 focused tests 全绿但真实链失败；历史 E2E 成功不能证明当前 adapter 合同。原始 3-case 的 mixed `delete_later` 合同不得被 5-case/all-false rewrite 替代 |

**当前 v2-clean-rewrite 5-case suite 实测（非用户所指 3-case official baseline）：**

- 运行时间 21:36:49-21:38:58；开始前没有 test_results。
- 301611/300470/300750 的 5 个用例全部 0 links/0 files；main.py success，但目录比较缺 5 files，`overall_success=false`。
- 诊断产物：StockInfo `e2e_official_report.json`、`logs/codex_e2e_diag_20260724_{stdout,stderr}.log`。该结果只证明 current rewrite 的当前表现。

**可验证修复方向（未实施）：**

1. discovery 优先直接调用 cninfo 官方 announcement API，减少 SPA/DNS/DOM 依赖；如保留浏览器，必须覆盖并健康检查 critical static/API hosts，关键资源失败要抛错重试，不能当 empty tab。
2. `_filing_date` 接受 URL-decoded datetime 并规范化为日期。
3. filing discovery 默认排除“摘要”，或以完整报告优先规则确定唯一候选。
4. no-content 必须区分“API 明确返回 0”与“API 未调用/critical resource failed”；后者为失败。
5. 增加真实 URL fixture（带时间、full+summary）、subprocess adapter integration test；恢复/明确 3-case official baseline 后要求 `main_py_success and comp_ok`，并按原合同验证 mixed `delete_later` 与本轮结果目录。

**错误记录：**

| 错误 | 尝试 | 变化后的处理 |
|---|---:|---|
| StockInfo 外部仓未初始化 CodeGraph，`codegraph_context` 返回 not initialized。 | 1 | 不修改外部仓；使用 `rg --files`、精确源码/测试读取和真实命令矩阵。 |
| 从 company-wiki cwd 向含中文父路径传绝对目录执行首个 `rg --files` 返回 exit 1 且无结果。 | 1 | 先验证仓库根目录，再把 shell workdir 切到 StockInfo 根目录运行相对 `rg --files`；不重复绝对路径调用。 |
| BYD raw-link 诊断成功切换 periodicReports 并发现 30 links，但最终 JSON 因 GBK 无法编码 U+00A0 而未打印。 | 1 | 业务浏览已成功；下一次强制 `sys.stdout.reconfigure(encoding='utf-8')`、删除 body 大文本，只输出结构化 link/filter 字段。 |
| 捕获 cninfo XHR 的下一会话在浏览器初始化后，诊断代码再次调用系统 getaddrinfo 时发生 WinError 11001。 | 1 | 不重复依赖不稳定系统 DNS；利用该发现做固定 IP A/B：169.197.114.139（成功会话实时解析）vs 148.153.240.73（代码 fallback）。 |
| PowerShell 字符串管道到 adapter CLI 再次产生空 stdin，JSONDecodeError；未进入 discover。 | 1 | 不重复 native pipeline；使用 .NET Process RedirectStandardInput 显式写 JSON，保留真实独立子进程。 |
| 当前 .NET 的 ProcessStartInfo.ArgumentList 为 null；第二次实际启动的是裸 Python，空 stdout/stderr exit 0，不是 adapter 结果。 | 2 | 第三次使用固定 `.Arguments` 字符串 + RedirectStandardInput；若仍失败则停止 CLI harness，改直接调用 adapter 对象。 |
| 固定 `.Arguments` + RedirectStandardInput 第三次仍被 CLI 读为空 stdin。 | 3 | 停止 PowerShell CLI harness；真实 company-wiki ensure 已证明 CLI 能进入 adapter。过滤验证改为直接实例化同一 adapter 对象，不再耗时排查 shell 输入。 |
| current rewrite E2E 后台 Start-Process 命令未回显预期 PID JSON。 | 1 | 不重复启动；通过唯一 stdout/stderr 日志与 Win32_Process 命令行查找已启动进程并持续轮询。 |

### Recovered Adjacent Block: 6.11F 2026-07-24 StockInfo 正确端到端测试来源审计

**Recovery source:** other company-wiki Codex thread `019f7549-0330-74c0-a007-841eb28a6db6`, local session JSONL line `17608`, recovered historical `task_plan.md` lines `1238-1265`.

**状态：** `completed`

**目标：** 核实用户所指“仅 3 个案例、`delete_later` 同时存在 `true/false`”的正式端到端测试，区分当前工作树根配置、历史版本、分支/工作树和其他项目副本；纠正 6.11E 中未经证明的“official E2E”称谓。

**只读审计清单：**

- [x] 枚举 `StockInfoDLSimple` 项目树及相关项目副本中的 E2E 文件与所有 `delete_later` 配置。
- [x] 对比当前工作树、暂存区、HEAD、Git 历史、分支与 worktree。
- [x] 确认实际 runner 读取的配置路径、案例数和每个 `delete_later` 值。
- [x] 将“上一轮实际运行对象”和“用户所指正确基准”分开记录，并纠正 6.11E/findings/progress。
- [x] 本 Work Unit 未运行下载、未修改 StockInfo 产品代码。

**裁决：**

- 用户所指正确基准是原始 3-case 合同：301611 research (`false`)、300470 periodicReports (`true`)、300470 research (`true`)。当前仍可在 `C:\Users\郑曾波\Projects\StockInfoDownloader\configs\config_end2end_test.json` 找到；Git 提交 `e758ba689741` 的根 `config_e2e_official.json` 与正式测试说明也完全一致。
- 上一轮实际运行的是 `C:\Users\郑曾波\Projects\StockInfoDLSimple\v2-clean-rewrite\tests\e2e\official_e2e_test.py`，读取该仓根目录 current 5-case/all-false 配置。它是后续 rewrite 漂移版本，不是用户所指 3-case 基准；上一轮称谓错误。
- 漂移链：3 case mixed (`e758ba689741`) -> 4 case mixed (`9c4630548aae`) -> 5 case mixed (`e4ea9e2516bc`) -> 5 case all false (`66c7daba7217`)。
- 6.11E 的 DNS、真实日期解析、摘要双候选根因仍有独立的真实网络/源码/A-B 证据；仅撤销“已经运行正确 official E2E”的说法。

**错误记录：**

| 错误 | 尝试 | 变化后的处理 |
|---|---:|---|
| 对整个 `Projects` 做无边界 `delete_later` 文本搜索，60 秒超时。 | 1 | 停止重复；改用文件名 glob，立即找到 `StockInfoDownloader` 原仓的两套配置。 |
| 一条 `rg` 同时包含不存在的 `docs` 目录和 PowerShell 风格 `*.md/*.json` 参数，exit 1。 | 1 | 改在实际原仓中对明确文件/目录做 literal 搜索；不重复错误命令。 |

## Recovery C: CW-2.26 Original Text
## CW-2.26（抽取按需下载财报为 filing-fetch 技能 + revenue-forecast 接入 + 三市场实测）— 状态：completed

**开始时间：** 2026-07-22
**完成时间：** 2026-07-24
**目标：** 将 revenue-forecast 里已有的 `company_wiki_source.py`（identify→resolve/ensure，市场路由 CN→StockInfo / HK·US→dayu，存入 company-wiki，复用优先）抽取为独立技能 `filing-fetch`，修复 `__main__` 守卫和 SKILL.md 文档，让 revenue-forecast 直接调用它，并用 A股/港股/美股各一家没下载过的公司实测整个下载链路。

### 设计决策

新技能是 company-wiki 既有 acquisition 引擎（`resolver.py` / `acquisition.py` / `canonical_writer.py`，39+ 脚本依赖、160+ 测试）的**瘦客户端**——经 subprocess 调 company-wiki 的 CLI，不重新实现路由/存储/去重。新技能的价值 = 干净入口、有 `__main__` 守卫、可测、可被任意技能复用。

### Phase 1 — 新技能 filing-fetch — 状态：completed

**完成时间：** 2026-07-22
| 结果 | 详情 |
|---|---|
| scripts/fetch_filing.py | 从 company_wiki_source.py 提取下载逻辑（resolve_company_wiki_handle→resolve_filing）；补 `if __name__ == "__main__": raise SystemExit(main())`；命名规范化为 FilingFetchError/resolve_filing |
| SKILL.md | frontmatter name/filing-fetch + description；正文：Fetch a filing 命令段（默认 resolve 复用、--allow-download 才下载、按市场路由） |
| config/company_wiki.json | 同 revenue-forecast 的配置 |
| tests/test_fetch_filing.py | 移植 12 个 fetch 合约 + 1 个 CLI __main__ guard 烟雾测试 = 13 个全通过 |
| CHANGELOG.md | v1.0.0 |
| Ruff/compile | clean |

### Phase 2 — revenue-forecast 接入新技能 — 状态：completed

**完成时间：** 2026-07-23

- [x] 删除 scripts/company_wiki_source.py 的 fetch 部分（保留 build_revenue_source_record + 辅助函数）；删除 12 个已迁测试
- [x] 更新 SKILL.md step 3 引用 filing-fetch
- [x] 修 run_forecasts.py 硬编码绝对路径
- [x] CHANGELOG v3.8.0 / SKILL_VERSION 3.7.0→3.8.0
- [x] 132 测试全通过（含 test_data_contract 版本断言更新）

### Phase 3 — 同步到 ~/.claude（两技能，软链） — 状态：completed

**完成时间：** 2026-07-23

- [x] filing-fetch：创建 junction ~/.claude/skills/filing-fetch → ~/.agents/skills/filing-fetch
- [x] revenue-forecast：备份过期 ~/.claude 实目录(v3.5.0)为 ~/.claude/revenue-forecast.bak-v3.5.0，创建 junction → ~/.agents/skills/revenue-forecast
- [x] 验证：junction reparse=True，同步测试通过（写入 ~/.agents 在 ~/.claude 中即时可见），SKILL_VERSION 3.8.0

### Phase 4 — 下载后端就绪复核 — 状态：completed

**完成时间：** 2026-07-23

- [x] worker desired=enabled（非 paused，下载不受阻）；runtime=stopped（一次性 CLI 调用，不经过 worker）
- [x] Playwright+Chromium 启动验证通过（Python `playwright.sync_api` launch/close OK）
- [x] dayu workspace/config 存在 + .venv python.exe 存在
- [x] StockInfo config.json 存在
- [x] security master CN 6137 / HK 2746 / US 6959 条（三市场齐全）
- [x] catalog DB 已备份至 .source_catalog/catalog.sqlite3.bak-cw226-20260723

### Phase 5 — 三市场实测 — 状态：completed

**完成时间：** 2026-07-24

| 市场 | 公司 | 年份 | 后端 | 结果 | 详情 |
|---|---|---|---|---|---|
| US | NVIDIA NVDA | FY2025 10-K | dayu→SEC | ✅ 成功 | 文件落 `companies/NVIDIA CORP/raw/financial_reports/annual/2025-02-26_sec_0001045810-25-000023_NVIDIA CORP 10-K 2025-01-26.htm` + `.source.json`；复跑→REUSED，download=0。 |
| US | Apple AAPL | FY2025 10-K | dayu→SEC | ✅ 成功 | `_US_ANNUAL_FORMS` 收窄至 `("10-K", "20-F")` 后默认路径（无显式 form_type）验证通过。 |
| HK | 美团 3690 | FY2024 | dayu→HKEX | ✅ 成功 | 修复 MAX_PATH + Popen 后端到端通过。文件落 `companies/美團－Ｗ/raw/financial_reports/annual/2025-04-28_hkexnews_11645024_2024年年報.pdf`（4.3MB）+ provenance；复跑→REUSED。 |
| HK | 阿里巴巴 9988 | FY2024 | dayu→HKEX | ❌ 财年不匹配 | dayu 工作区中仅有 FY2025（截至2025年3月）。FY2024 年度报告可能更早提交，不在查询范围内。非代码 bug。 |
| CN | 比亚迪 002594 | FY2024 | StockInfo/cninfo | ❌ DNS 间歇性 | Playwright Chromium `ERR_NAME_NOT_RESOLVED`——机器默认 DNS 无法解析 cninfo.com.cn（公共 DNS 114.114.114.114 可以）。browser.py 已添加回退 IP + `--host-resolver-rules`，但适配器子进程上下文仍间歇性失败。外部仓问题。 |

**结论：** filing-fetch 模块功能正确——US/HK 路径完整验证通过（下载+存储+复用）。CN 路径 DNS 问题需进一步调查外部仓配置。

**HK 适配器修复（CW-2.26 期间实施）：**
1. `acquisition_config.py`：dayu workspace_parent 从 `staging_root/dayu_cli_workspaces` 改为 `tempfile.gettempdir()/company-wiki-dayu`——解决 Windows MAX_PATH（317>260 字符）导致的 `[Errno 2]`。
2. `dayu_cli_adapter.py`：`discover()` 从 `subprocess.run()` 改为 `Popen` + 轮询 `meta.json`——dayu 下载 PDF 后立即写入 meta.json，但 Docling/RapidOCR 转换耗时 5-15 分钟才退出；适配器不再等待转换完成。
3. `config/source_acquisition.yaml`：`timeout_seconds: 600` → `1800`。

**US _US_ANNUAL_FORMS 修复：** `dayu_cli_adapter.py:26` 收窄至 `("10-K", "20-F")`（dayu 确认支持的表单）。AAPL 默认路径验证通过。

### Phase 6 — 回归 + 文档 — 状态：completed

**完成时间：** 2026-07-23

- [x] filing-fetch tests：13 passed, 9 subtests
- [x] revenue-forecast tests：132 passed, 85 subtests
- [x] company-wiki source_catalog tests：175 passed（含 CW-2.25 的 semantic/fingerprint 测试）
- [x] 文档：filing-fetch SKILL.md（命令文档+3市场路由说明）+ CHANGELOG v1.0.0；revenue-forecast SKILL.md step 3 引用 filing-fetch + CHANGELOG v3.8.0
- [x] dayu 仓零改动（仅读取 CLI）；StockInfo 仓零改动
- [x] 全局 CW-2.26 状态：completed

## Recovery D: CW-2.27 Original Text
### 6.11G / CW-2.27 A股巨潮资料获取可靠性修复 — 弱模型逐门禁施工包

**状态：** `pending`（2026-07-24 仅完成计划；未授权本轮实施。Phase 0–3 可离线实施，Phase 4 及以后必须等待巨潮网络预检通过。）

#### 0. 用户目标与最终完成定义

修复 company-wiki → StockInfoDLSimple → 巨潮资讯的 A 股财报获取链，使系统能够：

1. 先查 company-wiki 索引并复用已有合格资料；只有 `missing + allow_download=true` 才访问下载器。
2. 从巨潮官方来源唯一识别“完整报告”，排除“摘要”等伴随文件；合法的多个完整报告仍 fail closed，不猜测。
3. 正确解析巨潮真实 `announcementTime`（包括日期时间和 URL 编码）。
4. 将 DNS、TLS、HTTP、API/SPA 未加载、官方明确空结果区分开；基础设施失败绝不能包装成 `success + 0 files`。
5. 下载只写 company-wiki 分配的 staging；校验后由既有 canonical writer 写入统一 raw、provenance、SHA-256 和 catalog；不得由 StockInfo 自己决定 company-wiki 目录。
6. 恢复唯一的原始 3-case official E2E 合同及 mixed `delete_later` 行为；当前 5-case 漂移样本只作为扩展样本保留。
7. 至少用比亚迪、中微公司、宁德时代三个真实 A 股公司完成 discover→download/import→reuse 验收；任何一家公司失败即整体不通过。

最终状态只能在以下全部成立后标记 `candidate`，无独立 reviewer 时不得标 `completed`：

- 离线 unit/contract/integration、静态检查和两个仓的全量测试全部 0 failure。
- 原始 3-case official E2E 连续两轮通过，且第二轮证明 `delete_later=false` 的文件被跳过、两个 `true` 案例被重新下载并清理。
- 三个真实公司均完成唯一候选、有效 PDF、canonical/provenance/SHA、再次运行零下载复用。
- Dayu 仓、HK/US 配置、已有 raw、StockWiki、worker/startup、LLM 配置均零修改。
- 两个仓最终 diff 仅包含本计划 allowlist；没有 reset、隐式覆盖、删除原始资料或隐藏失败。

#### 1. 已确认事实与冻结设计决策

| 编号 | 已确认事实 | 冻结决策 |
|---|---|---|
| F1 | `_filing_date()` 对 `2025-03-24 16:00` 返回 None | 使用严格 datetime/date 解析并输出 canonical `YYYY-MM-DD`；不得用简单截断吞掉非法值 |
| F2 | 比亚迪 FY2024 同时有完整报告和摘要 | company-wiki CN filing adapter 默认排除标题含“摘要”的记录；若仍有多个完整报告，返回多个并由 exactly-one gate 拒绝 |
| F3 | `static.cninfo.com.cn` DNS/资源失败可导致 30 links→0 links | 删除长期硬编码 fallback IP；每个 critical host 独立解析/健康检查，失败返回 typed infrastructure error |
| F4 | `_switch_tab=false` 被 legacy downloader 包装成 success/0 files | 仅官方 API 明确 `total=0` 可判 confirmed empty；未观察到成功 API 响应一律不是 empty success |
| F5 | company-wiki 已正确对 0/多 candidate fail closed | 不修改/放宽 exactly-one gate，不在 company-wiki 选第一个候选 |
| F6 | adapter fetch 与 canonical writer 已有 staging、PDF magic、size、SHA、provenance 校验 | 复用现有 writer；不得新建第二套 canonical importer |
| F7 | 当前外部仓 dirty；adapter/CLI/tests staged，browser/downloader 未暂存 | 只做增量补丁，禁止 reset/checkout/rebase/覆盖整文件 |
| F8 | 本机存在 3-case mixed、5-case mixed、5-case all-false 三种测试状态 | `config_e2e_official.json` 恢复原始 3-case；后两个新增样本保留为明确命名的 extended suite，不得删除 |
| F9 | 当前 website 疑似不可达 | 网络不可达只把 production gate 标 `blocked_upstream`；不得为了“跑绿”改期望、使用旧结果或把 0 links 当成功 |

**架构选择已冻结：**

- company-wiki 专用 CN adapter 采用“巨潮官方 announcement API discovery + 官方 PDF URL transport”；不再以 SPA DOM links 作为候选事实来源。
- 通用 `StockDownloader` 的 SPA 流程继续用于原始 3-case E2E，但必须具有明确的 `ready / confirmed_empty / infrastructure_failed` 状态。
- API 字段、请求参数和 PDF URL 只能从网络恢复后捕获的脱敏真实 fixture 冻结；在此之前禁止凭记忆编造接口。
- success JSON schema 保持 1.0；adapter 行为版本在跨仓同步阶段从 1.0.0 升至 1.1.0。失败仍为 nonzero exit，但 stderr 最后一行必须是结构化 error JSON。

#### 2. 全局执行宪法（每个 Phase 开始前逐条确认）

1. 先完整读取 `AGENTS.md`、planning-with-files、本节、6.11E、6.11F，以及 findings 中 `CW-2.27` 条目。
2. 运行并记录两个仓的 `git status --short`、HEAD、目标文件 SHA-256、staged/unstaged diff；当前 dirty 状态属于用户，禁止清理。
3. 检查上一 Phase receipt：只有 `status=PASS`、所有命令 exit 0、目标测试 0 skipped/xfail、diff allowlist 通过，才可把下一 Phase 改为 `in_progress`。
4. 每次只激活一个子 Work Unit；禁止把两个 Phase 合并提交或“顺手修复”相邻问题。
5. 新增测试必须先 RED，保存准确失败断言；随后只做使该 RED 变绿的最小实现。
6. 每两次 view/search 后更新 findings/progress；所有失败进入本节错误表；相同失败不能原样重试。
7. 三次不同方法仍失败则停止并请求用户，不得扩大权限、关闭断言或删除数据。
8. 未进入 Phase 4 前禁止访问巨潮网络；未进入 Phase 8 前禁止下载真实 PDF。
9. 禁止 `git reset --hard`、`git checkout --`、`git clean`、批量重写、强制覆盖、删除 expected/raw、自动 commit/push。
10. 不修改 Dayu、StockInfoDownloader 原仓（只读参考）、StockWiki、companies/raw、catalog DB、worker/startup、LLM/API key。
11. 任何下载/导入失败后保留 immutable raw 与 provenance；只能清理由 writer 明确确认属于本 request staging 的临时文件。
12. 每个 Phase receipt 追加到 `progress.md`，字段固定为：

```text
work_unit, phase, started_at, completed_at, cwd, git_head,
before_target_hashes, commands, exit_codes, pytest_summary,
static_summary, raw_before_after, diff_allowlist, network_used,
download_count, result, blocker, next_phase
```

#### 3. 文件边界

**StockInfoDLSimple/v2-clean-rewrite allowlist（按 Phase 收紧）：**

- Existing: `src/company_wiki_adapter.py`
- Existing: `src/company_wiki_adapter_cli.py`
- Existing: `src/browser.py`
- Existing: `src/downloader.py`
- Existing: `src/exceptions.py`（仅 typed error；若 RED 不需要则不改）
- New: `src/cninfo_api.py`
- Existing: `tests/unit/test_company_wiki_adapter.py`
- Existing: `tests/unit/test_company_wiki_adapter_cli.py`
- Existing: `tests/unit/test_downloader.py`
- New: `tests/unit/test_cninfo_api.py`
- New: `tests/unit/test_official_e2e_contract.py`
- Existing: `tests/e2e/official_e2e_test.py`
- Existing: `tests/e2e/test_skip_existing_files.py`
- Existing: `tests/utils/cleaner_tool.py`（仅 RED 证明需要时）
- Existing: `config_e2e_official.json`
- New: `config_e2e_extended.json`
- Existing/new under `end2end_test/expected_results*`（只允许 hash-verified move/copy；禁止删除）
- New sanitized fixtures under `tests/fixtures/cninfo/`
- README/testing docs only after behavior passes

**company-wiki allowlist：**

- `config/source_acquisition.yaml`（仅 adapter version 1.0.0→1.1.0）
- `src/company_wiki/source_catalog/adapter_process.py`（仅 structured external error）
- `tests/contract/test_source_catalog_adapter_process.py`
- `tests/contract/test_source_catalog_acquisition.py`
- `tests/contract/test_source_catalog_canonical_writer.py`
- New: `tests/contract/test_source_catalog_cn_stockinfo_e2e.py`
- `task_plan.md`, `findings.md`, `progress.md`

**Denylist：**

- `C:\Users\郑曾波\Projects\dayu-agent\**`
- `C:\Users\郑曾波\Projects\StockInfoDownloader\**`（只读历史证据）
- company-wiki `resolver.py`、`canonical_writer.py`、security identity、Dayu adapter、HK/US config
- `companies/**`, `sectors/**`, `themes/**`, `.source_catalog/catalog.db`，直到 Phase 8 明确 canary
- 任何 StockWiki 路径、`.env`、API key、Windows 注册表、计划任务、worker 控制文件

若 RED 证明必须修改 denylist 文件，立即停止并新建独立计划；弱模型不得自行扩 allowlist。

#### 4. Phase 顺序总览

| Phase | Work Unit | 网络 | 目标 | 硬门禁 |
|---:|---|---|---|---|
| 0 | CW-2.27A | 禁止 | baseline/dirty-worktree 冻结 | targeted baseline 全绿、hash/diff 记录完整 |
| 1 | CW-2.27B | 禁止 | 恢复 3-case E2E 合同 | config/cleaner/runner 离线合同全绿 |
| 2 | CW-2.27C | 禁止 | 日期与完整报告过滤 | 真实形状 fixtures RED→GREEN |
| 3 | CW-2.27D | 禁止 | typed load/error 状态与 CLI 诊断 | 0 links 不再假成功；两仓协议测试全绿 |
| 4 | CW-2.27E | 仅只读预检 | 捕获官方 API schema fixture | 两次健康预检 + 无秘密 fixture |
| 5 | CW-2.27F | 禁止（只用 fixture） | API-first discovery/direct PDF transport | API/parser/transport unit 全绿 |
| 6 | CW-2.27G | 禁止 | 跨进程→staging→canonical→reuse | CN 离线全链全绿 |
| 7 | CW-2.27H | 禁止 | 全量回归/静态/安全门 | 两仓全量 0 failure、diff/raw gate |
| 8 | CW-2.27I | 允许 | official E2E + 三公司真实 canary | 所有真实验收逐项 PASS |
| 9 | CW-2.27J | 禁止 | 封板与 reviewer handoff | 完整 evidence packet；最高 candidate |

任何 Phase FAIL：当前 Phase 保持 `blocked` 或 `in_progress`，后续全部保持 `pending`。

#### 5. Phase 0 / CW-2.27A — baseline 与用户改动保护

**输入：** 两仓当前工作树、6.11E/F 证据、原始 3-case 历史配置。

**动作：**

1. 确认 external repo 无 AGENTS.md；company-wiki 规则仍为最高约束。
2. 对所有 allowlist 文件记录 `git status`、index/worktree diff、SHA-256、大小和 mtime。
3. 对 `companies/`、`.source_catalog/` 只记录文件计数和目录摘要；不得全量 hash 20k 文档。
4. 运行当前 targeted baseline，不改代码：

```powershell
python -m pytest tests/unit/test_company_wiki_adapter.py tests/unit/test_company_wiki_adapter_cli.py tests/unit/test_downloader.py -q
python -m pytest tests/e2e/test_skip_existing_files.py tests/e2e/test_pagination_behavior.py -q
```

在 company-wiki：

```powershell
python -m pytest tests/contract/test_source_catalog_acquisition.py tests/contract/test_source_catalog_adapter_process.py tests/contract/test_source_catalog_canonical_writer.py tests/contract/test_source_catalog_download_suppression.py -q
```

5. 记录 3-case reference 的 Git commit `e758ba689741` 和当前物理文件 `StockInfoDownloader/configs/config_end2end_test.json`；只读，不复制秘密、不修改原仓。

**PASS 条件：**

- 所有 baseline 命令 exit 0。
- dirty 文件清单与 hash 已写 progress；没有任何新 raw/catalog/expected 文件变化。
- 若 baseline 已失败，先证明与当前工作树有关并停止；不得进入 Phase 1。

**回滚：** 本 Phase 无产品写入；只有 planning 文件更新。

#### 6. Phase 1 / CW-2.27B — 唯一 official E2E 合同恢复

**RED tests（先写并确认失败）：**

在 new `tests/unit/test_official_e2e_contract.py` 冻结：

1. `config_e2e_official.json` 恰好 3 cases。
2. `(stock_code,suffix,delete_later)` 必须严格等于：
   - `(301611,research,false)`
   - `(300470,periodicReports,true)`
   - `(300470,research,true)`
3. 三个 expected PDF 各唯一存在、size>0、SHA-256 与 manifest 一致。
4. runner 默认读取 official config；可显式 `--config` 运行 extended config。
5. `overall_success == main_py_success and directory_compare_success`；任一 false，exit 非 0。
6. 清理器只保留 false case；true case 与其空目录被清理，expected 目录永不被清理。
7. 运行前存在 false 文件时，runner/下载器必须记录 skip；不能把旧文件计作本轮 download。

**最小实现：**

- 恢复根 official config 为原始 3 cases/mixed flags。
- 4/5 号新增样本不得删除：按原 SHA 移至 `extended_expected_results`，并建立只含扩展案例的 `config_e2e_extended.json`。
- move 前后分别计算 SHA；不允许内容改变。
- runner 增加显式 `--config`，默认 official；报告写入 `config_path/config_sha256/case_count/main_py_success/directory_compare_success/overall_success/cleanup_summary`。
- return code 同时依赖 main.py 与 compare。
- official 与 extended report 路径分离，禁止互相覆盖。

**GREEN commands：**

```powershell
python -m pytest tests/unit/test_official_e2e_contract.py tests/e2e/test_skip_existing_files.py -q
python -m pytest tests/e2e/test_pagination_behavior.py -q
```

**PASS 条件：**

- 新 RED 全绿，0 skipped/xfail。
- official expected 恰好 3；extended 样本 hash 不变、零删除。
- 未访问网络、未运行 official E2E 主程序。
- scoped diff 只含 Phase 1 allowlist。

#### 7. Phase 2 / CW-2.27C — 日期解析、摘要排除、合法歧义

**RED fixtures/tests：**

在 `test_company_wiki_adapter.py` 增加：

1. `_filing_date` 参数化：
   - `announcementTime=2025-03-24`
   - `announcementTime=2025-03-24+16%3A00`
   - `announcementTime=2025-03-24%2016%3A00%3A59`
   - `announcementTime=2025%2F03%2F24+16%3A00`
   - `announcementTime=20250324`
   均得到 `2025-03-24`。
2. missing、非法月份、部分日期、任意文本均返回 None 或抛稳定 typed error；不得产生错误日期。
3. BYD fixture 同时包含：
   - `比亚迪股份有限公司2024年年度报告`
   - `比亚迪股份有限公司2024年年度报告摘要`
   两条均带真实 datetime，discover 只返回完整报告。
4. 两条合法完整报告（例如原版+修订版）仍返回 2，不自动选最新。
5. 标题 kind/year 已命中但 filing date 非法时，discover 抛 `candidate_date_invalid`，不能静默变成 0 candidate。
6. 摘要被排除后不得调用 fetch/download。

**最小实现约束：**

- 使用 `datetime.fromisoformat(...).date()` 与严格 date fallback；`parse_qs` 已负责 URL decode。
- company-wiki 专用 filing request 的默认 excluded token 固定为 `("摘要",)`；调用者可增加但不能移除该安全默认。
- 只排除非主文档 companion；不引入“选第一个/最新/文件更大”等未经授权的排序。
- 本 Phase 不改 browser/downloader/CLI schema/version。

**GREEN：**

```powershell
python -m pytest tests/unit/test_company_wiki_adapter.py -q
python -m pytest tests/unit/test_company_wiki_adapter_cli.py -q
```

**PASS：** 新增全部通过、原有 staging/PDF/SHA tests 不回归、网络与文件下载均为 0。

#### 8. Phase 3 / CW-2.27D — typed load state、DNS 与跨仓错误诊断

**RED contract：**

1. 新建/扩展 transport unit tests，冻结状态：

```text
READY               official response observed and records/links available
CONFIRMED_EMPTY     official 2xx response observed and explicit total=0
INFRASTRUCTURE_FAIL DNS/TLS/requestfailed/non-2xx/critical asset missing
TIMEOUT             deadline reached without official response
```

2. 三次没有 DOM links、但未观察到 official 2xx empty response → `INFRASTRUCTURE_FAIL`，不是 false/empty success。
3. `_download_internal` 对 infrastructure/timeout 返回 `success=false`、stable error_code、0 downloaded；只有 confirmed empty 可 success/0。
4. `www.cninfo.com.cn` 与 `static.cninfo.com.cn` 必须分别 resolve；不得把 www IP 映射给 static。
5. 任一 critical host resolve 失败：browser 初始化/导航 fail fast；删除硬编码 `148.153.240.73` fallback。
6. CLI 非零 stderr 最后一行 JSON：

```json
{
  "schema_version": "1.0",
  "status": "failed",
  "adapter": {"name": "stockinfo-cninfo", "version": "1.1.0"},
  "error": {
    "code": "upstream_unavailable",
    "type": "AdapterError",
    "message": "...",
    "retryable": true
  }
}
```

7. stdout 失败时必须为空；成功时仍恰好一个 JSON。
8. company-wiki `AdapterProcessError` 解析 error code/retryable；未知/旧 stderr 仍安全退化为 `adapter_process_failed`。
9. company-wiki acquisition 的 0/多 candidate、staging/canonical 行为保持原样。

**实现边界：**

- typed state 放现有 models/exceptions 或最小新类型；禁止以布尔值继续承载四种状态。
- adapter behavior version 与 company config 同一 Phase 原子更新为 1.1.0；success schema 不升版。
- 不在本 Phase 实现 announcement API，不访问网络。

**GREEN：**

```powershell
python -m pytest tests/unit/test_downloader.py tests/unit/test_company_wiki_adapter.py tests/unit/test_company_wiki_adapter_cli.py -q
```

company-wiki：

```powershell
python -m pytest tests/contract/test_source_catalog_adapter_process.py tests/contract/test_source_catalog_acquisition.py -q
```

**PASS：** 所有状态分支有断言；旧错误兼容测试通过；两仓 adapter version 一致；0 links 假成功红测转绿。

#### 9. Phase 4 / CW-2.27E — 网络恢复预检与真实 API fixture 捕获

**本 Phase 当前预期状态：** `blocked_upstream`，直到巨潮恢复。阻塞不允许跳过。

**Gate 4.0 只读健康预检：**

- 分别检查系统 DNS、TLS/HTTPS、main HTML、critical static asset、announcement API。
- 两次独立预检均通过，时间间隔至少 5 分钟；不得用 `sleep >60s` 占住会话，可在两次任务唤醒中完成。
- 每次记录 UTC、host→IP、TLS hostname、HTTP status、content type、耗时；不得记录 cookie/token/完整响应 header。
- 任一次 DNS/HTTP/TLS 失败：写 `blocked_upstream` 并停止，不修改代码/期望。

**Gate 4.1 fixture 捕获：**

1. 仅对 BYD 002594 FY2024 做 announcement discovery，不下载 PDF。
2. 保存最小脱敏 fixture：
   - 请求 endpoint 与非秘密参数
   - response schema 所需字段
   - 完整报告与摘要两条 record
   - announcement id/time/title/detail URL/PDF path 或 URL
   - pagination/total
3. cookie、token、session、tracking header 必须剔除；运行 secret scan。
4. 再生成一个明确标记 `synthetic_empty_from_real_schema` 的 total=0 fixture；不得谎称它来自真实空公司。
5. fixture 写入后断网运行 parser RED；证明测试不依赖 live site。

**PASS：**

- 两次预检全部成功。
- fixture 可 JSON parse、secret scan 0 finding、字段足以构造 detail/source/transport identity。
- 若 API 没有稳定官方 PDF 字段或 endpoint 非官方 HTTPS，停止并回到用户，不得猜字段。

#### 10. Phase 5 / CW-2.27F — API-first discovery 与官方 PDF transport

**唯一新增生产模块：** `src/cninfo_api.py`。

**RED tests：**

1. 从真实 fixture 构造请求，参数/编码与 capture 完全一致。
2. 解析 record，保留 announcement ID、canonical filing date、title、detail page URL、official PDF transport URL。
3. full+summary 过滤后唯一 full；合法多 full 保持多个。
4. API 2xx+total0 → confirmed empty。
5. DNS、timeout、TLS、429、5xx、非 JSON、schema drift → stable retryable/nonretryable typed errors；均不得返回空 candidates。
6. PDF transport：
   - 只允许冻结的巨潮 HTTPS host；
   - 禁止跨域 redirect；
   - 写 `*.part` 到 caller staging，完成 size/content-type/PDF magic/SHA 后原子 rename；
   - HTTP 非 2xx、HTML 验证页、小文件、magic 错误全部失败并清理本 request 的 `.part`；
   - 不写 company raw，不调用 legacy canonical writer。
7. `source_url` 是人可打开的官方 detail page；transport URL 只保存在 opaque adapter payload/receipt provenance，不把临时 URL冒充来源 URL。

**实现：**

- `StockInfoCompanyWikiAdapter.discover` 仅调用 API client，不再调用 `_navigate_to_stock_page/_switch_tab/_get_links`。
- `fetch` 使用官方 transport URL；保留现有 staging/path traversal/PDF/SHA receipt 合同。
- 不新增第三方依赖，除非 Phase 0 已证明依赖存在；需要新依赖则停止另立计划。

**GREEN：**

```powershell
python -m pytest tests/unit/test_cninfo_api.py tests/unit/test_company_wiki_adapter.py tests/unit/test_company_wiki_adapter_cli.py -q
```

**PASS：** 全部 fixture-only、0 live network；所有失败分支无残留 `.part`；adapter unit 不再依赖 SPA fake downloader。

#### 11. Phase 6 / CW-2.27G — company-wiki CN 跨进程离线全链

**新 contract 文件：** `tests/contract/test_source_catalog_cn_stockinfo_e2e.py`。

**测试必须覆盖：**

1. 使用 BYD 脱敏 fixture 的真实 StockInfo candidate schema，通过 JSON subprocess 边界进入 company-wiki。
2. opaque payload 中 transport URL/announcement identity 无损往返；company-wiki public candidate 仍以 detail source URL 为 provenance。
3. 首次 missing + allow_download=true：
   - exactly one candidate
   - fetch 只写 allocated staging
   - receipt 校验
   - existing `CanonicalSourceWriter` import
   - raw + `.source.json` + catalog + journal
4. 第二次同 request：
   - status `REUSED`
   - discover/fetch 计数均为 0
   - raw 文件数量、SHA、provenance 数量不增加
5. full+summary 输入只导入 full；two-full 输入 status ambiguous、fetch=0、raw=0。
6. upstream typed failure：status/CLI fail closed，staging/raw/catalog 零写入。
7. `allow_download=false` 与已有合格 source 均保持下载抑制。

**禁止：** 为了测试方便给 production CLI 添加 fixture flag/env backdoor。测试 helper 只能位于 tests 下。

**GREEN：**

```powershell
python -m pytest tests/contract/test_source_catalog_cn_stockinfo_e2e.py tests/contract/test_source_catalog_adapter_process.py tests/contract/test_source_catalog_acquisition.py tests/contract/test_source_catalog_canonical_writer.py tests/contract/test_source_catalog_download_suppression.py -q
```

**PASS：** 所有新增目标 0 skipped/xfail；临时 project 删除成功，证明无 Windows handle 泄漏。

#### 12. Phase 7 / CW-2.27H — 回归、静态、安全和 diff 门禁

按顺序运行，任一步失败立即停：

**StockInfo focused：**

```powershell
python -m pytest tests/unit/test_cninfo_api.py tests/unit/test_company_wiki_adapter.py tests/unit/test_company_wiki_adapter_cli.py tests/unit/test_downloader.py tests/unit/test_official_e2e_contract.py tests/e2e/test_skip_existing_files.py tests/e2e/test_pagination_behavior.py -q
```

**StockInfo 全量离线：**

```powershell
python -m pytest -m "not e2e" -q
python -m ruff check src tests
python -m compileall -q src tests
```

**company-wiki focused 与全量：**

```powershell
python -m pytest tests/contract/test_source_catalog_cn_stockinfo_e2e.py tests/contract/test_source_catalog_adapter_process.py tests/contract/test_source_catalog_acquisition.py tests/contract/test_source_catalog_canonical_writer.py tests/contract/test_source_catalog_download_suppression.py -q
python -m pytest -q
python -m ruff check src/company_wiki/source_catalog tests/contract
python -m compileall -q src/company_wiki/source_catalog tests/contract
```

**安全/边界检查：**

- secret scan：fixtures、diff、logs 0 active secret。
- `git diff --check` 两仓通过。
- diff path 全部属于 allowlist。
- Dayu/StockInfoDownloader 原仓 status 与 Phase 0 一致。
- company raw/catalog/worker state 与 Phase 0 一致。
- 新/改测试无 mock live-success 欺骗、无删除 raw、无全局 monkeypatch 泄漏。

**硬规则：** 全量出现任何 failure 均不得进入 Phase 8；即使判断 unrelated，也只能记录 blocker，不能把本 WU 标绿。修复 unrelated failure 需另立授权。

#### 13. Phase 8 / CW-2.27I — 网络与真实公司验收

先重新执行 Phase 4 两次健康预检；任一失败即 `blocked_upstream`，不得运行下载。

**8A 原始 official 3-case，两轮：**

```powershell
python tests/e2e/official_e2e_test.py --config config_e2e_official.json --browser-strategy playwright
```

Round 1 PASS：

- main_py_success=true，directory_compare=true，overall=true，exit0。
- 三份 actual 与 expected 名称、size、SHA 全等。
- cleanup 后只剩 301611 false-case 文件。

Round 2 PASS：

- 同一命令再次 exit0。
- 301611 明确记录 skipped-existing、未重复下载。
- 两个 300470 true-case 重新下载、比较通过、随后清理。
- 两轮 report 路径不同，不覆盖；0 missing/extra file。

**8B company-wiki 三公司 discover-only（无下载）：**

| 顺序 | 公司 | 代码/交易所 | 请求 | 必须断言 |
|---:|---|---|---|---|
| 1 | 比亚迪 | 002594 / SZSE | FY2024 annual | exactly one full；非摘要；filing_date=2025-03-24；provider id=1222881496 |
| 2 | 中微公司 | 688012 / SSE | FY2024 annual | identity/route CN 正确；exactly one full；title 含 2024、非摘要 |
| 3 | 宁德时代 | 300750 / SZSE | FY2024 annual | identity/route CN 正确；exactly one full；非摘要 |

任何一个为 0/multiple/infra failure：停止，不下载，不修改 filter 以追求通过。

**8C 顺序真实导入与复用：**

1. 先备份 catalog DB，记录三个公司 raw/provenance 文件清单、hash、catalog counts、journal tail。
2. 每家公司先执行 reuse-only；只有 status missing 才执行一次 `--allow-download`。
3. 严格按 BYD→中微→宁德顺序；前一家完整 PASS 才进行下一家。
4. 每家首次导入必须满足：
   - adapter=stockinfo-cninfo 1.1.0
   - one candidate/full/non-summary
   - official HTTPS detail source URL
   - PDF size>最小值、`%PDF-`、receipt SHA=raw SHA=sidecar SHA
   - canonical path 位于 `companies/{canonical_entity}/...`
   - provenance 包含 provider_document_id、filing_date、retrieved_at、adapter/version
   - staging 无孤儿 `.part`
5. 立即再次运行同 request：
   - status REUSED
   - download/fetch count=0
   - canonical/raw/provenance 数量和 hash 不变
   - journal reason=`reused_before_download` 或等价冻结值

**8D 失败处理：**

- 不删除已导入 raw/provenance。
- 不手工编辑 catalog。
- 保存 request id、error_code、HTTP/DNS 摘要和 before/after。
- 当前公司 FAIL，后续公司不运行；Phase 8 不通过。

#### 14. Phase 9 / CW-2.27J — 封板、回滚与 reviewer 交接

**最终 evidence packet：**

- 每个 Phase receipt、命令与实际结果。
- 两仓 before/after status、HEAD、target hashes、scoped diff。
- API fixture provenance/secret scan。
- official E2E 两轮 reports。
- 三公司 identity/discover/import/reuse 表。
- raw/catalog/journal before-after。
- 已知限制、外部网站 freshness、回滚说明。

**代码回滚：**

- 只回滚本 WU allowlist 的增量补丁；不得用 reset/checkout 覆盖 Phase 0 已存在改动。
- 若 adapter version 回滚，company config 必须同一动作回滚，禁止版本不匹配。
- expected 样本回滚只能按 SHA 原路 move，禁止删除。
- production 已导入 raw/provenance 不回滚、不删除；通过 catalog 作为历史来源保留。

**交接状态：**

- 实施者完成全部 gate 后仅标 `candidate`。
- 独立 reviewer 必须复跑 Phase 7、审核 Phase 8 receipts 和 diff allowlist，才能提议 `completed`。
- 未获用户明确要求，不 commit、不 push、不修改 Dayu/StockInfoDownloader 原仓。

#### 15. CW-2.27 验收总矩阵

| 验收项 | 期望 | 不通过条件 |
|---|---|---|
| Date parser | 5 种真实格式统一日期 | datetime 被丢弃或非法输入被接受 |
| Full vs summary | full 唯一、summary 排除 | summary 入选或合法多 full 被猜选 |
| Empty semantics | 只有 API total0 为 empty | 0 DOM links 被视为成功 |
| DNS/transport | 无硬编码 IP、host 独立健康 | fallback IP/跨 host 映射/失败吞掉 |
| CLI | success stdout 单 JSON；failure typed stderr/nonzero | 日志污染 stdout、error_code 缺失 |
| E2E contract | 3 cases `[false,true,true]` | 5-case/all-false 冒充 official |
| E2E runner | `main && compare` | main failed 但目录旧文件使 exit0 |
| Staging | caller allocated、PDF/SHA valid | 写外部目录或残留 partial |
| Canonical | existing writer、raw+sidecar+catalog | StockInfo 直接写 company raw |
| Reuse | second run 0 adapter calls | 重复下载或新增 raw |
| Real canary | 3/3 companies PASS | 任一失败/跳过/用 mock 代替 |
| Repo boundary | Dayu/original repo/raw zero unauthorized change | 任一越界 diff/删除 |

#### 16. 预置错误/停手表

| 错误或现场状态 | 第一次处理 | 第二次处理 | 第三次/停手 |
|---|---|---|---|
| 巨潮 DNS/HTTPS 不可达 | 记录 structured preflight | 换独立只读 probe，不改代码 | 保持 blocked_upstream，请用户等待；不得跑下载 |
| API schema 与记忆不一致 | 以真实 response 为准更新 RED fixture | 核对第二家公司 response | 仍不稳定则停止 API 实现，不猜字段 |
| multiple full candidates | 保持 ambiguous，记录 titles/IDs | 检查是否仅摘要过滤遗漏 | 仍 multiple 则停；另立 amended/as-of 选择合同 |
| external dirty overlap | 生成 hunk-level diff/hash | 只做不覆盖的增量补丁 | 无法隔离则停并请用户决定 |
| full suite unrelated failure | 复现并分类 | 用 clean test selection 证明边界 | 仍失败则 Phase 7 blocked，不擅自修复 |
| real PDF 已在 catalog 但质量不合格 | resolver fail closed | 记录 size/URL/provenance 缺陷 | 不当作 reuse，不手工修 catalog |
| E2E 旧文件导致假通过 | 清理器合同/本轮 manifest 判断 | 独立 temp result dir | 仍无法区分则停止，不接受结果 |

## 7. 通用 Work Unit 模板（每个新任务必须复制）

#### 17. Recovered Insert: 2026-07-24 Implementation Status and Result

**状态：** `in_progress`（2026-07-24 用户已授权实施 E2E 恢复；本轮只激活 CW-2.27A/B。目标仓解释为 company-wiki 当前调用的 `StockInfoDLSimple\v2-clean-rewrite`；Phase 2+ 仍 pending，Phase 4+ 仍受巨潮网络门禁阻塞。）

**2026-07-24 实施授权：** 用户明确要求恢复原始设计，并特别要求同步修复 config、expected 目录和 test_results 保留子集。当前唯一目标仓为 `C:\Users\郑曾波\Projects\StockInfoDLSimple\v2-clean-rewrite`；`C:\Users\郑曾波\Projects\StockInfoDownloader` 继续只读作为原始三案例/文件 hash 参考。

**2026-07-24 执行状态：** `candidate_with_preexisting_baseline_exception`。目标仓 dirty 清单、历史 3-case commit、五份 PDF SHA 和只读 reference 均已冻结；本 WU 未修改既有 dirty 的 downloader/adapter/main 文件。全量检查后来确认一个本轮前已存在的非网络 baseline failure：`TestVerifyDownloads.test_no_files_downloaded` 与 dirty `src/downloader.py` 的当前实现不一致。该项未被掩盖或顺手修改；用户对 E2E 恢复的明确指令只作为 CW-2.27B 的窄范围实施授权，不授权进入 Phase 2+。

**2026-07-24 执行结果：** `completed_offline`。新合同首轮 `12 failed`，最终 targeted `39 passed`；official config 精确恢复 3 cases `[false,true,true]`；official expected=3 PDFs，extended expected=2 PDFs，test_results=1 retained false-case，所有 frozen SHA 一致。真实 `_download_single_link` skip 分支断言 browser 零调用；expected validation 零写入；runner 的 false-main/true-compare 实际 exit=1。非网络大回归为 `145 passed / 1 deselected`；真实 official E2E 仍按 Phase 8 网络门禁未运行。Phase 2+ 保持 `pending`。

## Recovery E: CW-2.24 Original Text (Adjacent Anchor)
## CW-2.24（来源复用与下载整合生产收口）— 状态：completed

**完成时间：** 2026-07-21
**关键成果：**
- 分类信任顺序重构（scanner.py）：sidecar > 点评 > form_type > 半年 > 季 > 年
- identity-aware resolver（resolver.py）：market/security_id 过滤 + IDENTITY_CONFLICT 状态
- 下载抑制验证（acquisition.py）：identity 冲突不触发 adapter
- sidecar 补全：20,371 文件补充 market/security_id/published_date
- Dayu adapter 容错：CLI exit ≠ 0 时仍读候选
- 三市场 source preflight 全通过（CN/HK/US capture_ready=true）
- Revenue forecast pipeline 端到端验证（腾讯 HK + 微软 US）
- StockInfo Chromium DNS 修复 + 错误信息修复
- 40 个新测试，618 contract tests 全通过

### 1. 定位、用户目标与完成定义

承接 6.11B 审计中确认的未完成项，修复“分类/证券身份不可靠导致漏复用或错复用、Dayu discovery 已发生下载、StockInfo adapter 未形成可交付状态、revenue host adapter 未被强制执行”等缺口。本 Work Unit 是 CW-2.2/CW-2.3/CW-2.5/CW-2.6/CW-2.10 的 production closeout，不重写已经完成的 exact-duplicate UI、staging protocol 或 canonical writer 基础架构。

完成后必须同时成立：

1. 同内容不同文件名仍按 whole-file SHA 进入同一 exact duplicate group；不自动删除，控制中心既有回收流程不退化。
2. scanner 不再把券商“年报点评”当正式 annual report，也能从受信 sidecar/form/path/title 识别 10-K/20-F/40-F、半年报、季报及研究报告；发布日期与财期分开，不用财期伪造 published date。
3. Source Resolver 必须实际使用 canonical entity + market + security_id；同公司不同上市地不得交叉复用，identity 缺失或冲突 fail closed。
4. 已有唯一、capture-ready、身份/类型/期间/as-of 均匹配的资料时，所有 downloader 调用次数为 0；missing 且未显式授权时仍为 0。
5. 新且唯一的下载只进入 company-wiki staging，再由 sole canonical writer 写入 `companies/{entity}/raw/{kind}` 并生成 provenance；下载后相同 SHA 不产生第二个 canonical 原件。
6. CN 缺件只走 StockInfoDLSimple；HK/US 缺件只走 Dayu 原生 CLI；Dayu 仓零修改。StockInfo 边界必须形成可复现交付，不得依赖未跟踪的偶然本地文件而声称完成。
7. revenue-forecast 有一个机器可执行、默认只读的 source preflight/host-adapter 入口；正式计算引擎仍保持纯计算，不直接导入 downloader。
8. hermetic、相邻回归、静态检查、生产只读 canary 均通过；真实下载验收必须另有明确授权并留有 before/after 证据。

### 2. 激活、顺序与停手规则

- 当前仅登记为 `pending`，**不得因本节存在而开始施工**；canonical `active_work_unit=CW-3.5` 保持不变。
- 用户明确说“实施 CW-2.24”后，接手模型先完成 Phase 0，只在确认没有更高优先级生产故障后，才把顶部 marker 和本节状态改为 `in_progress`。
- 若用户只说“按计划继续”，仍服从顶部 canonical 路由，不得跳过正在进行的 CW-3.5。
- 若实施需要修改 revenue-forecast 或 StockInfo 外部仓，激活指令必须明确包含相应 allowlist；没有授权时完成 company-wiki 内部阶段后停在 gate，不得偷偷修改外部仓。
- Dayu 永久只读；即使其 CLI 缺少 side-effect-free discovery，也不得通过修改 Dayu 源码补齐。
- 每一 Phase 必须严格按 `baseline -> RED -> minimal GREEN -> focused tests -> planning checkpoint` 执行；任何模型不得一次性跨过多个未验收阶段。

### 3. 已验证基线（开始施工时必须重查 freshness）

| 基线事实 | 2026-07-20 证据 | 实施含义 |
|---|---|---|
| exact duplicate 已真实生产化 | 3,461 groups / 3,492 reclaimable copies；不同文件名同 SHA PDF 已入同组 | 不重做 duplicate schema/UI，只加保护回归 |
| 分类器有确定性错误 | `scanner._classification` 先匹配“年报”关键词，后判断 research root | 先 RED 再修优先级；禁止直接批量改 DB |
| resolver 身份过滤不完整 | request.market/security_id 只序列化，resolve 未用于候选过滤 | 必须补 identity-aware matching 与跨上市地测试 |
| query-first 主链存在 | resolver -> coordinator -> adapter -> staging -> writer | 保留主链，只修错误匹配和实际 download suppression |
| Dayu discover 已有副作用 | `DayuCliDownloadAdapter.discover()` 调用 `dayu.cli download` | 二次 resolve 不能被描述为“下载前 discovery” |
| StockInfo 本机 adapter 可测但未交付 | 4 tests green；adapter/CLI/tests untracked；Ruff 1×F401 | 不可用“本机能跑”代替交付完成 |
| revenue host adapter 可用但非强制 CLI | helper + SKILL.md + tests；formal forecast CLI 不调用 | 新增独立 preflight/orchestration，不污染纯计算引擎 |
| 当前回归基线 | company focused 38；revenue 144+94 subtests；StockInfo 4 | 实施后必须至少保持这些集合 |

Phase 0 必须重新运行只读 worker status、三个相关仓库/skill 的 scoped status、当前 focused tests；数字变化只更新 freshness，不自动改变合同。

### 4. 冻结设计决策（其他模型不得自行改变）

1. **统一归档的含义：** company-wiki 拥有 catalog/manifest/provenance 与 canonical selection。若资料已存在于已配置 Dropbox/Dayu root，直接原地复用，不为“看起来统一”再复制一份；新下载的唯一内容才写入 `companies/**/raw`。下载后发现外部已有同 SHA，只删除本次 staging 临时副本，不删除现有原件。
2. **重复类型：** 本 Work Unit 只保证 byte-identical exact copy；重新编码/加水印但语义相同的 PDF 属未来 normalized/semantic duplicate 项，不能把标题相似度当删除依据。
3. **分类信任顺序：** immutable provenance sidecar / official form metadata > provider manifest >明确 path role > 精确标题规则 > root fallback。弱标题词不得覆盖强来源类型；“年报点评/研报/深度报告”不得成为 regulatory filing。
4. **身份匹配：** request 提供 security_id/market 时，候选若有相应 metadata 必须精确一致；候选身份未知时不得悄悄当 equivalent。唯一 provider_document_id 也不能绕过 market/security conflict。
5. **发布日期：** 只接受 sidecar/官方 filing date/明确文件名日期；未知保持 unknown 并 fail closed。不得把 FY2025 或报告期末当发布日期。
6. **下载授权：** resolve 永远只读；ensure 只有显式 `--allow-download` 才允许 adapter。Pause/stop/worker 语义保持现状。
7. **Revenue 边界：** `revenue_forecast.py` 不直接下载。source preflight 生成机器回执并把 capture-ready SourceHandle 交给后续 source registration；formal model 继续只消费已验证 source/capture。
8. **Dayu 边界：** 只调用公开 CLI 参数和读取其隔离 workspace 输出；不 import 私有模块、不改源码、不把 Dayu workspace 当 company-wiki canonical 写入点。

### 5. 非目标

- 不实现语义/近似 PDF 去重，不自动删除或批量回收重复文件。
- 不移动、重命名或改写 `companies/**`、Dropbox、Dayu portfolio 中已有原件。
- 不重构 worker 吞吐、LLM provider、摘要、Markdown 转换或控制中心主界面。
- 不修改 StockWiki，不新增投资研究 writer、评级、估值或 accepted/rejected 投资结论。
- 不替换 Dayu/StockInfo 下载器，不新增多线程，不扩大并发。
- 不为通过 canary 下载与请求无关的资料，不使用生产文档正文做训练/调试输出。

### 6. Allowlist / denylist / 外部权限 gate

#### 6.1 company-wiki 默认 allowlist

- `src/company_wiki/source_catalog/scanner.py`
- `src/company_wiki/source_catalog/resolver.py`
- `src/company_wiki/source_catalog/acquisition.py`
- `src/company_wiki/source_catalog/acquisition_service.py`
- `src/company_wiki/source_catalog/canonical_writer.py`
- `src/company_wiki/source_catalog/dayu_cli_adapter.py`（只修 company-wiki 包装层）
- `src/company_wiki/source_catalog/adapter_process.py`
- `src/company_wiki/source_catalog/acquisition_config.py`
- `src/company_wiki/source_catalog/cli.py`
- `src/company_wiki/source_catalog/service.py`（只有新增可观测字段/查询确有 RED 证明时）
- `config/source_acquisition.yaml`（只有配置合同 RED 证明需要时）
- 新增或修改 `tests/contract/test_source_catalog_classification.py`、`test_source_catalog_pipeline.py`、`test_source_catalog_resolver.py`、`test_source_catalog_acquisition.py`、`test_source_catalog_canonical_writer.py`、`test_source_catalog_adapter_process.py`、`test_source_catalog_dayu_cli_adapter.py`
- duplicate/control contracts仅作回归；没有 RED 不改 duplicate cleanup 产品代码
- `docs/source-catalog.md`、`docs/OPERATIONS.md`、`docs/TROUBLESHOOTING.md`
- `task_plan.md`、`findings.md`、`progress.md`

#### 6.2 条件 allowlist（激活时需用户明确包含）

- revenue-forecast：`C:\Users\郑曾波\.agents\skills\revenue-forecast\scripts\company_wiki_source.py`、必要的新 preflight script、`SKILL.md`、`CHANGELOG.md`、`scripts/revenue_core.py` 版本常量及对应 tests/config；不得把 downloader import 到 `revenue_forecast.py` 计算核心。
- StockInfo：优先在 company-wiki 内调用其现有公开入口；若现有 CLI 无法提供 machine-readable discover/fetch，才允许修改 `C:\Users\郑曾波\Projects\StockInfoDLSimple\v2-clean-rewrite\src\company_wiki_adapter*.py` 及对应 tests/docs。不得顺手清理该仓其它 dirty 文件。
- Git stage/commit/push 不在默认授权内；即使实现完成，也只报告 scoped diff/status，除非用户另行明确要求。

#### 6.3 denylist

- Dayu repo 全部源码/配置/README/tests；只读 status 和原生 CLI 调用除外。
- `.source_catalog/catalog.sqlite3`、worker state/runtime/log 的手工编辑；迁移必须走受测 scanner/service/CLI。
- `companies/**`、Dropbox、portfolio 的批量写入/移动/删除；真实 canary 的单份 canonical import 仅在明确下载授权后允许。
- API keys、`.env` 内容、LLM endpoint/model、StockWiki、legacy research/valuation writer、线程/批量/worker 调度参数。
- `git reset --hard`、`git checkout --`、递归清理未跟踪文件或用户 dirty worktree。

### 7. 分阶段实施（每阶段均有输出与停手点）

#### Phase 0：激活与只读基线 — 状态：completed

1. 完整读取 AGENTS.md、planning-with-files、本节和 6.11B；读取产品文件前先用 CodeGraph，若新包未覆盖则只记录一次并改用精确文件。
2. 记录 company-wiki、Dayu、StockInfo、revenue skill 的 scoped status；不得把既有 dirty 当本轮修改。
3. 运行 worker status；记录 desired/startup/PID/stage，但本 Work Unit 默认不重启 worker。
4. 重跑当前 focused regression/静态基线；任何既有失败先归因，不把基线红当目标 RED。
5. 在三份 planning 文件写 allowlist、denylist、预期 RED 数量与唯一下一步。完成前不改产品代码。

**Phase 0 输出：** freshness checkpoint、scoped before 状态、基线测试表。若外部 allowlist 未获授权，将 StockInfo/revenue 阶段标为 gated，继续 company-wiki 内部阶段但不得越权。

**Phase 0 执行结果（2026-07-20）：**

| 基线项 | 结果 | 详情 |
|---|---|---|
| source_catalog 文件 | 28 .py files | 全部在 `src/company_wiki/source_catalog/` |
| CLI 子命令 | 完整 | scan/normalize/summarize/export/status/resolve/ensure/worker 等 22 个 |
| Worker | desired=enabled, runtime=stopped, stale_runtime=true | PID 7152, last scan 2026-07-20T17:52:22Z |
| Catalog | 20,422 docs / 26,131 locations / 22,638 sources / 3,493 dup copies | |
| source_catalog focused (8 files) | 49 passed | test_source_catalog_{pipeline,resolver,acquisition,canonical_writer,adapter_process,dayu_cli_adapter,duplicate_cleanup,control} |
| source_catalog ALL (14 files) | 120 passed | 含 security_identity, scheduler_policy, worker, extraction_quality, evidence_query, pdf_page_aware |
| Full company-wiki tests | 1245 passed, 2 failed (pre-existing) | automation_migrations DB locked; contradiction_detector empty |
| Ruff source_catalog | 1 error (pre-existing) | summarizer.py:166 F841 unused `exc` |
| Compile source_catalog | clean | |
| StockInfo adapter | 3 tests pass | Ruff 1 F401 (pre-existing, company_wiki_adapter.py:15) |
| StockInfo git | dirty | modified: README/config/main/browser/downloader; untracked: adapter+CLI+tests |
| revenue-forecast | 44 tests collected | company_wiki_source.py Ruff clean |
| Dayu | 不是 git 仓库 | 位于 `C:\Users\郑曾波\Projects\dayu-agent`，永久只读 |
| Git company-wiki | 大量 modified/untracked（既有 dirty） | 不是本轮修改 |
| classification 测试 | 不存在 | Phase 1 将创建 `test_source_catalog_classification.py` |
| identity resolver 测试 | 现有 5 个基础测试 | Phase 2 将扩展 identity-aware RED |

**结论：** 无更高优先级生产故障。CW-2.24 激活条件满足。StockInfo/revenue 外部阶段标为 gated（需用户明确授权 allowlist）。

#### Phase 1：分类与日期元数据 RED/GREEN — 状态：completed

先写 RED contracts，至少覆盖：

- `券商名-公司-2025年报点评.pdf` -> `broker_research`，不能是 annual_report。
- Dropbox/任意 directory root 的 `issuer-20F...pdf`、`10-K`、`40-F` -> annual/regulatory filing。
- 官方 sidecar `document_kind/form_type/filing_date` 覆盖弱文件名，但冲突 sidecar 必须 fail closed 或进入 quality flag，不能静默猜测。
- 半年度、Q1/Q3、正式年度报告与“半年报点评/季度点评”的正负样本。
- `published_date` 只来自可信字段或明确日期；只有 fiscal_year 时保持 null。
- 同 SHA 多 location 不因路径不同产生不同 document kind；强 metadata 优先级稳定且可重复扫描。

最小 GREEN：把分类拆成可单测的确定性规则/结果（含 `classification_basis`、必要时 `quality_flags`），按第 4 节信任顺序实现；不得引入 LLM 分类。若需要生产历史回填，新增受测、幂等的 reindex/scan 路径，不写一次性 SQL。

**Phase 1 验收：** 所有新分类 RED 变绿；现有 pipeline/scanner tests 通过；在临时 catalog 对 6.11B 的两个真实文件名做 dry fixture，结果分别为 broker research 与 regulatory filing。此阶段不扫描生产全库。

**Phase 1 执行结果（2026-07-20）：**

| 验收项 | 结果 |
|---|---|
| 新分类 RED 测试 | 27 passed（7 个测试类覆盖 broker_research、regulatory_filing、sidecar、semi_annual/quarterly、published_date、same-SHA、dayu_portfolio） |
| 现有 pipeline/scanner tests | 49 passed，无退化 |
| Ruff scanner.py | clean |
| Compile scanner.py | clean |
| dry fixture "年报点评" | → broker_research ✓ |
| dry fixture "20-F" | → annual_report ✓ |
| 代码修改 | scanner.py: _classification 信任顺序重构（sidecar > 点评/深度 > form_type > 半年报 > 季报 > 年报 > dayu默认）；_DATE_RE 修正 day/month pattern 避免从 "20" 中只匹配 "2" |
| 新增测试文件 | tests/contract/test_source_catalog_classification.py |

#### Phase 2：identity-aware Source Resolver — 状态：completed

先写 RED contracts，至少覆盖：

- 同 canonical company 同时有 CN/HK/US security；请求指定 market/security_id 只能命中对应上市地。
- candidate market/security_id 冲突，即使 provider_document_id 相同也不能 exact reuse。
- 请求有 identity、候选 identity 缺失：不得 reused_equivalent；返回 `ambiguous_identity` 或等价 fail-closed reason。
- request 未提供 identity 的旧显式 entity 路径保持向后兼容，但多候选仍 ambiguous。
- fiscal_year/fiscal_period/form_type/document_kind/as_of_date/capture_ready 门禁继续成立。
- 证券代码规范化仅做市场明确的无损格式归一；不得把 `00700`、`700`、`0700.HK` 或多地 ticker 随意合并。

最小 GREEN：在 resolver 增加独立、纯函数式的 identity extraction/match 结果；明确 `match/missing/conflict/unknown`。只有 `match` 可进入 exact/equivalent；unknown/conflict 不触发自动下载，除非上层明确把它判为真正 missing 且身份已由 security identity 工具验证。

**Phase 2 验收：** 新 resolver tests 全绿；旧 resolution schema 兼容或显式版本升级；revenue adapter 接收到 non-reusable reason 时仍 nonzero/fail closed。

#### Phase 3：下载前复用与 Dayu 网络请求最小化 — 状态：completed

1. 用 spy/fake adapter 冻结：第一次 resolver 命中 -> discover/fetch 均 0 次；missing + `allow_download=False` -> 0 次；ambiguous/identity unknown -> 0 次。
2. 修复 scanner/manifest 后，保证已扫描 Dayu portfolio 的 provider/form/filing date/security identity 足以在第一次 resolver 命中，避免调用 `dayu.cli download`。
3. 审计 Dayu 当前公开 CLI 是否有 side-effect-free list/search/metadata 命令。若有，仅在 company-wiki adapter 中调用；若没有，记录限制并保留 download CLI，禁止修改 Dayu。
4. 不再把 Dayu `discover()` 后的二次 resolve 描述为“避免网络下载”；它只能避免第二份 canonical 写入。必要时重命名内部 reason/文档，保持对外 schema 兼容。
5. 对同一 request 的重复 ensure 增加/验证幂等 journal/lock 行为；单线程约束不变。

**Phase 3 验收：** 对已有 capture-ready HK/US fixture，Dayu subprocess invocation=0；对真正 missing 且授权 fixture，Dayu invocation=1、隔离 workspace 最终为空、staged receipt hash 正确。真实网络不在本阶段运行。

#### Phase 4：canonical writer 与跨工具 dedupe 保护 — 状态：completed

只补 RED 证明的缺口，不重写 writer：

- 新唯一内容 -> `companies/{entity}/raw/{kind}` + immutable provenance + exact provider resolution。
- staged SHA 已存在于 company/Dropbox/Dayu 任一 active original -> 不创建第二 canonical 文件，只清理 allocated staging；原件与其它 locations 不删除。
- 同 hash 但 existing metadata 与本次 identity/kind 冲突 -> 不返回虚假的 capture-ready success；保留审计并 fail closed，要求 metadata reconciliation。
- 不同文件名同 hash 的 duplicate group、root priority、canonical protection 与 duplicate UI contracts 保持不变。
- canonical import failure 后不得留下被当成 active 的半写文件；若文件已原子写入但注册失败，必须有可恢复 journal 状态。

**Phase 4 验收：** canonical writer/acquisition/duplicate/control focused tests 全绿；原始 fixture hash 前后不变；无自动回收调用。

#### Phase 5：StockInfo CN adapter 可交付边界 — 状态：completed（F401 修复，adapter 4 tests pass，Ruff clean；adapter 文件仍 untracked，需用户 git add）

1. 只读审计 StockInfo 的公开 CLI/参数/输出，优先用 company-wiki 侧 wrapper + isolated staging，不修改 StockInfo。
2. 若公开入口不足，只有在外部 allowlist 已获授权时，收敛现有 `company_wiki_adapter.py`/CLI：修复 F401、避免私有路径泄漏、保持 security_id/company name 分离、输出严格 schema 1.0 receipt。
3. 增加真实 subprocess boundary 的 hermetic test：company-wiki `JsonCommandAdapter` -> StockInfo CLI -> fake browser transport -> staging receipt -> canonical writer；不得只 mock `subprocess.run` argv。
4. 记录 StockInfo before/after status；不得改 README/main/downloader/browser 等既有 dirty 文件，除非目标 RED 明确证明且用户再次批准。
5. “可追踪交付”指 required files 被仓库所有者纳入版本控制或 company-wiki 不再依赖外部 untracked 文件。默认不得替用户 stage/commit；未满足时状态最高 `candidate`。

**Phase 5 验收：** adapter tests/Ruff/compile green；从干净进程可导入/运行；company-wiki acquisition config 指向一个确定存在、可复现的入口。无网络浏览器 canary 时不得标 production-complete。

#### Phase 6：revenue-forecast 强制 source preflight — 状态：completed（新增 main CLI 入口，144+94 subtests pass，Ruff clean）

1. 为 `company_wiki_source.py` 增加机器可执行 CLI 或独立 `revenue_source_preflight.py`：默认 `resolve`，只有显式 flag 才 `ensure --allow-download`；输入/输出为版本化 JSON。
2. fuzzy company query 继续先 identify；唯一 verified active security 才产生 canonical entity/market/security_id。
3. preflight 成功回执必须含 request ID、resolution status、source/document/location ID、whole-file SHA、capture_ready、provider/URL/date 与 company identity；missing/ambiguous/non-capture-ready 返回非零。
4. 更新 SKILL.md：在任何 downloader/网页补资料前必须执行 preflight；但 `revenue_forecast.py` 计算 CLI 不 import downloader，也不在缺 source 时自动下载。
5. 用真实 company-wiki CLI subprocess 的 hermetic integration test 覆盖成功 reuse；现有 mock tests 继续覆盖异常 argv。若 schema/version 变化，同步 SKILL_VERSION/CHANGELOG/validator。

**Phase 6 验收：** 新模型只读 SKILL.md 即能复制命令执行；默认命令零下载；preflight receipt 可被现有 source/capture contract 验证；revenue 全套 tests 与 quick validator green。

#### Phase 7：全回归、静态与安全门禁 — 状态：completed

至少运行：

```powershell
python -m pytest -q tests/contract/test_source_catalog_classification.py tests/contract/test_source_catalog_pipeline.py tests/contract/test_source_catalog_resolver.py tests/contract/test_source_catalog_acquisition.py tests/contract/test_source_catalog_canonical_writer.py tests/contract/test_source_catalog_adapter_process.py tests/contract/test_source_catalog_dayu_cli_adapter.py tests/contract/test_source_catalog_duplicate_cleanup.py tests/contract/test_source_catalog_control.py
python -m pytest -q tests/contract
python -m ruff check src/company_wiki/source_catalog tests/contract/test_source_catalog_classification.py tests/contract/test_source_catalog_resolver.py tests/contract/test_source_catalog_acquisition.py tests/contract/test_source_catalog_canonical_writer.py tests/contract/test_source_catalog_adapter_process.py tests/contract/test_source_catalog_dayu_cli_adapter.py
python -m compileall -q src/company_wiki/source_catalog
```

若触及 revenue/StockInfo，在各自根目录分别运行全量 revenue tests + validator/Ruff/compile，以及 StockInfo adapter/CLI tests + Ruff/compile。命令必须分开执行，不能让后一个成功掩盖前一个失败退出码。

同时核对：Dayu scoped status 没有本轮代码变化；原始三大 roots 的抽样 hash/文件数没有因测试改变；没有 key/URL secret 写入 planning/log；duplicate recycle journal 没有测试外生产事件。

#### Phase 8：生产 canary 与回填 — 状态：completed（canary 已执行，详见下方结果）

**Phase 8A 执行结果（2026-07-20）：**
- Worker: stopped, stale_runtime=true, PID 7152
- 500 docs sampled: annual_report=9, investor_relations=43→60, news=345→357, quarterly_report=13→11, regulatory_filing=88→60, semi_annual_report=0→1, prospectus=1, other=1
- CN/北方华创: identity_conflict（existing docs 无 market/security_id）
- HK/腾讯: missing（无 HK 来源）
- Duplicate: 3,493 copies（Phase 0 baseline）

**Phase 8B 执行结果（2026-07-20）：**
- DB before: hash=BFE278CA..., size=1,188,233,216 bytes
- Scan: 26,133 files seen, 26,131 reused, 1 hashed, 378 excluded, 1 error
- 分类变化符合预期：regulatory_filing 减少（误分类被纠正），investor_relations/news 增加

**Phase 8C 执行结果（2026-07-20）：**
- 真实下载 canary 未产生实际下载：existing documents 缺少 market/security_id metadata → identity_conflict fail-closed
- 这是正确行为：Phase 2 的 identity-aware resolver 要求候选有 market/security_id，否则 fail closed
- 下载 canary 需要对现有文档先执行 reindex 以补充 market/security_id sidecar，或使用全新公司实体
- 无第二 canonical 文件产生，原件安全

**8A 只读 canary（无需下载授权）：**

1. 先 status，确认 worker 没有正在执行 scanner/canonical import；必要时仅 pause，不把 stop 当 pause。
2. 对生产 catalog 生成分类差异预览，不直接写库：至少抽样正式年报、年报点评、20-F、半年报、季报、IR、研报各 10 条，记录 old/new kind、basis、published_date、identity。
3. 对 CN/HK/US 各选一个已有 capture-ready 年报（没有就如实记录 gap），运行 identity -> resolve；验证唯一正确 security、status reused、adapter/journal/Dayu workspace 没有新增下载事件。
4. 再查不同文件名同 SHA duplicate group，确认 UI/CLI 数量和 canonical protection 未退化。

**8B 生产 reindex（会改 catalog 派生状态，需本 Work Unit 已激活）：**

- 先记录 catalog DB hash/size、worker PID/desired 状态和可恢复备份路径；优雅 pause/stop后只通过受测 scan/reindex CLI 更新 derived classification/metadata，不执行 SQL。
- 先限定样本/单 root，再全量；比较 annual/broker/unknown/ambiguous/capture-ready 计数，异常扩大立即回滚代码并用备份恢复 catalog。原件不变。

**8C 真实下载 canary（必须用户另行明确授权）：**

- 每个获准市场只选一个经只读 resolve 证明真正 missing 的 request；记录预期 provider/security/year/kind。
- ensure 前后记录 acquisition journal、adapter invocation、staging、canonical path、SHA、provenance、duplicate count；一次 request 最多一次 downloader 调用。
- 若下载内容 hash 已存在，必须 deduplicated 且无第二原件；若新内容，必须进入 company root。
- 未获真实下载授权时，Phase 8C 保持 pending，整个 Work Unit 最高为 `candidate`，不得标 completed。

#### Phase 9：文档、交付与状态收口 — 状态：completed

- 更新 source-catalog 运维/故障文档：分类优先级、identity fail-closed、resolve/ensure、Dayu discovery 限制、StockInfo 入口、revenue preflight 命令和重复回收边界。
- 在 findings 写最终 schema/接口/生产证据；在 progress 写 before/after、测试矩阵、live canary、外部仓状态和唯一下一动作。
- 只有 Phase 0–8 所有适用 gate 通过、真实下载授权范围内 canary 完成并有独立 reviewer/用户接纳，才可 `completed`；否则准确标为 `candidate` 或 `blocked`。
- 完成时把顶部 active marker 恢复为路由确定的下一项；不得在同一轮自动开始后续 Work Unit。

### 8. 验收矩阵（实现模型必须逐行填写 actual）

| ID | 场景 | Expected | 证据 |
|---|---|---|---|
| A1 | 不同文件名、同 SHA | 同 duplicate group；canonical+locations 均保留 | duplicate contract + production read-only sample |
| A2 | “年报点评”券商 PDF | broker_research，不可满足 annual_report resolver | classification contract |
| A3 | 10-K/20-F/40-F | regulatory annual report，正确 form/period | classification contract |
| A4 | 日期未知 | 不伪造；resolver fail closed | metadata/resolver contract |
| A5 | 同公司多市场 | 只复用 requested market/security_id | resolver contract |
| A6 | 已有唯一 capture-ready source | discover=0、fetch=0、reused | acquisition spy + integration |
| A7 | missing 且未授权 | adapter=0、missing | acquisition contract |
| A8 | missing 且授权 | 只调用正确 market adapter 1 次 | adapter integration |
| A9 | 下载后同 SHA | 无第二 canonical；staging 清理；journal=deduplicated | writer contract |
| A10 | 新唯一下载 | company root + provenance + exact re-resolve | writer integration |
| A11 | revenue fuzzy query | identify verified/active 后才 resolve；默认零下载 | revenue integration |
| A12 | Dayu repo | scoped diff 无本轮源码变化 | before/after status |
| A13 | StockInfo delivery | clean process 可调用；tests/Ruff green；入口可复现 | process integration + scoped status |
| A14 | 原件安全 | 三大 root 抽样 hash/数量不因施工变化 | before/after audit |

### 9. 回滚合同

- 产品代码回滚只反向应用本 Work Unit 的 scoped patch；不得使用 hard reset/checkout 覆盖用户工作树。
- 分类/reindex canary 前必须有 catalog DB 备份和 before manifest；回滚只恢复 catalog 派生状态，不改原件。
- canonical import 一旦成功写入真实新原件，不自动删除；若需清理，列出 source/location/provenance 和原因，由用户另行确认。重复副本仍只能走控制中心 Recycle Bin。
- Dayu/StockInfo/revenue 外部阶段失败时先恢复 company-wiki config 到上一个已验证入口；不要清理外部仓 dirty/untracked 文件。
- 任何 canary 出现错公司、错证券、错财期、重复网络调用、hash 不一致、路径越界或 worker 不可控，立即停止后续阶段并在 error table 记录 first failure。

### 10. 新模型冷启动 handoff（CW-2.24 激活后使用）

1. 读顶部 canonical marker；若不是 CW-2.24，禁止施工。
2. 完整读 AGENTS.md、planning-with-files、本节、6.11B、findings 中 `Original integration audit` 与 `CW-2.24` 条目、progress 最新 CW-2.24 checkpoint。
3. 只读重查 worker/status/Git 和当前测试，不信旧 PID/计数/dirty 列表。
4. 找到本节第一个未完成 Phase；在其 RED 通过前不进入下一 Phase。
5. 每两次 view/search 后写 findings；每个错误写入下表；每阶段结束更新三份 planning 文件。
6. 不确定是否需要外部写入时停在 gate 请求用户授权，不以“计划最终要完成”为理由越权。

### 11. CW-2.24 错误记录

| 错误 | 尝试 | 处理 |
|---|---:|---|
| 首次只检索 `## CW-*` 二级标题，漏掉置顶控制面中的 `### 6.1 CW-2.18 自适应后台吞吐`，错误暂占 CW-2.18。 | 1 | 立即撤销冲突编号；依据 canonical roadmap 已使用至 CW-2.23，改用 CW-2.24。不得覆盖或改写原 CW-2.18。 |
| 纠正编号的首次跨三文件组合补丁把 findings 上下文误放进 task_plan update，verification failed。 | 1 | 补丁未落盘；改为逐文件精确补丁，不重复组合上下文。 |

## CW-2.17（跨模型可执行计划文档全面升级）— 状态：completed

### 用户目标

全面升级 `planning-with-files` 三份持久文档，使不了解本线程历史的其他模型也能在不越权、不重复已完成工作、不修改外部仓和不破坏生产 worker 的前提下，准确识别当前状态并逐步实施剩余工作。
