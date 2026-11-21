# SR-CWP 交接 — 增量发现与有限阅读

日期：2026-11-21 · 交付 commit `c01e6e04e`（分支 `codex/sr-cwp-20261121`，工作区 `C:/Users/郑曾波/Projects/cwp21`） · 基线 `master@29a123ad3`

## 0. 交付状态与平台门记录（先读）

**交付已提交**：`c01e6e04e`（Mimosa L3 前置扫描放行；mypy-contract 钩子拦下的
15 处交付内类型错误已全部修复后过钩）。尚未 rebase 到最新 master、未推送。

首轮 commit 尝试曾被 Mimosa L3 全仓扫描按最高等级阻断（211 high / 38 medium / 6 low），
具名发现全部位于本卡未触及的预存文件（`tests/unit/test_automation_migrations.py`、
`tests/unit/test_llm_client.py`、`src/company_wiki/source_catalog/identity_candidates.py:94,109`
——已核对在基点 `29a123ad3` 逐字存在）。后续提交同一内容时门放行；
预存发现仍归平台/安全 lane 处理，本卡交付面对其贡献为 0（聚焦扫描收据见 §7）。

**基点漂移**：开工后 master 前进了 `4558cdd75`（citation_locator 入库）与
`113a61e02`（FF P1 记录）。交付 commit 已包含 citation_locator 模块文件
（tracked HEAD 文件导入它）；rebase 到最新 master 无冲突（两 commit 只动计划文档与新模块）。

## 1. 首项基线（卡第一步）：混合来源解析回归

**复现**（独立短路径 worktree，loopback 夹具，无网络/无模型）：

```
python -m pytest "tests/integration/test_narrative_batch_cli_e2e.py::
test_cli_infers_sparse_languages_from_verified_pdf_and_transcript_bytes" -q
→ 退出 1；批次报告 failed；单份 dead_letter/PARSER_INCOMPLETE，其余完成。
（主测试失败复现 1 次；随后的独立诊断脚本 2 次产出同一 dead_letter/PARSER_INCOMPLETE
收据，P0 阶段另有两次失败记录。）
```

**定位**：失败件是夹具 `call-mixed.txt`。逐版本对照解析：同一字节在
`0.1.1`（legacy）出 1 unit；`0.2.0/0.3.0/0.3.1/0.4.0`（现行默认 `0.4.0`）均
`transcript_start_missing` → 0 units → 选择 blocked → `PARSER_INCOMPLETE` →
select/summarize/verify 三 job 连环 dead_letter。仓库内另有测试
（`tests/unit/test_narrative_evidence.py::test_transcript_without_recognized_start_is_blocked_not_skipped`）
刻意断言无发言人转写的文本必须 blocked —— 语义是既定契约。

**根因判定**：夹具与真实契约不一致（非运行依赖、非共享解析缺陷）。
夹具作于 2026-10-04（`0c259cce2`，legacy 契约时代），第二行是无标签散文；
2026-10-09 起（`8c154b117`）版本化布局要求可证实的发言人转写。

**修复**（`tests/support/narrative_batch_fixtures.py`）：mixed 夹具第二行改为
`CEO: We discussed the overseas expansion plan. 公司新产品已经完成客户认证，开始批量交付。`
—— 真实发言人转写 + 中英混合正文，覆盖语言推断目标不变。**先改夹具（新样本进
失败用例）后验证原基线**，顺序符合卡要求。原 e2e 单跑通过；同文件全套
15 passed 1 skipped（另一失败预存且已一并修复，见 §4）。

## 2. 交付面

### 2.1 有界元数据发现（interfaces §2）

- `acquisition.py`：`DiscoveryPage`（candidates/coverage/next_cursor/reason_codes/
  covered_from/covered_to）；`DownloadAdapter` 协议加 `discover_page`；
  `AcquisitionCoordinator.discover_page()` 复用市场路由、issuer→listing 收窄与候选校验。
- `adapter_process.py`：`JsonCommandAdapter.discover_page(.bounded)` —— 外部适配器
  未声明 coverage 时降为 partial（不能凭沉默声明完整）。
- `dayu_cli_adapter.py`：`discover_page` 按实际枚举窗口申报 coverage。
- `resolver.py`：`SourceRequest.cursor`（不透明 provider 页游标；**不进 `identity_dict`**，
  目标身份与页位无关；`to_dict` 仅在非 None 时携带）。
- 新 `incremental_discovery.py`：`cwp-incremental-discovery-request/1` →
  `cwp-incremental-discovery/1`。coverage 合并取最弱声明；provider 窗口不覆盖请求区间
  → partial + 具名 reason；真空区间且覆盖完整 → complete；候选限额/请求/页/时间到限
  → partial + 可续 cursor；多页沿 provider cursor 续举；已登记原件由 owner 解析回填
  `existing_source_ref`（精确 SourceRef v2）；**不回传 provider URL**；
  无匹配且范围真正完整是一种完成结果。

### 2.2 有限阅读（interfaces §3）

- `narrative_artifact_store.py`：新角色常量 `NARRATIVE_READ_RESULT_ROLE`；
  新增读结果数据类与 `prepare_read_result` / `activate_read_result` /
  `latest_visible_read_result`（写侧）与 `read_exact_read_result`（读侧，读后复核父源）。
  bundle 全部既有查询未动。
- `store.py` + `models.py`：**加性新表 `narrative_read_results`**，
  `CATALOG_SCHEMA_VERSION 1.4.0 → 1.5.0`，`_UPGRADEABLE_SCHEMA_VERSIONS` 增 `1.4.0`；
  迁移与 fingerprint 表同一模式（DDL + 逐表守卫），零破坏性重建。
- 新 `incremental_read.py`：
  - 本地档（`local`）：现有 `SourceVersionReader` 验真打开 → 现有 `RawNarrativeSelector`
    （同一解析/选择引擎）→ `verify_selected_material` 证明通过 → 紧凑读结果
    （selection + 带 locator 证据段 + parser/selector 身份 + `model_requests: 0`）
    落 `narrative_read_results`（content-addressed 复用：同 work_key 同内容 → 同
    artifact_version_id，reused=true）。**构造上零模型**：无 HTTP 配置、无模型端口。
  - 状态机：`read` / `skipped`（真无业务材料，具名） / `failed`（PARSER_INCOMPLETE、
    语言不可分类，带 owner 错误码） / `uncertain`（source_ref 变更、源 owner 拒绝、
    IO） / `deferred`（summary 档待配置批次） / `summarized`（已有正式 bundle）。
  - summary 档（`summary`）：只从 owner 正式处理索引派生 —— 读结果可见 → `read`；
    正式 bundle 可见 → `summarized`（紧凑 bundle ref）；否则 `deferred`
    （`summary_batch_required`，沿 `scripts/narrative_batch_configured.py` 的现行配置组合，不在本卡另起执行链）。
  - 单份失败隔离同批兄弟；重复 SHA 查回同产物。
- 积压（`cwp-reading-backlog-request/1` → `cwp-reading-backlog/1`）：注册原件按
  实体/文种/发布日期窗过滤，**keyset 分页**（`document_id` 游标），状态由持久产物派生
  （unread/read/skipped/summarized），不靠文件名、mtime 或目录猜测。

### 2.3 公开入口

`source_catalog.cli` 新增 `discover-incremental` / `read-incremental`（沿 `official`
前置委托模式 → `incremental_cli.py`；stdin JSON 请求 → stdout JSON 回执；错误具名
`cwp-incremental-error/1` 退出 2）。`read-incremental` 同时受理读请求与积压请求。

### 2.4 基线附带修复（预存红）

`test_cli_finishes_when_owned_storage_file_disappears_during_sampling` 在干净
master（本卡基点）即红：`a7b384ab9` 把存储采样函数移入
`narrative_storage_budget.file_tree_bytes`，测试 launcher 仍 patch 旧名
`batch._tree_bytes`。launcher 改 patch 现名。**同文件全套 15 passed 1 skipped**。
（主仓 master 最新 commit `4558cdd75` 未含此修复；如与并行工作冲突以本工作区版本为准复核。）

## 3. 隔离测试与验收夹具映射

全部隔离（tmp 夹具 catalog + 本地 stand-in 适配器；**零网络、零模型调用、零生产配置写入**）：

| 卡/夹具 | 测试 | 关键断言 |
|---|---|---|
| A1 | `test_sr_cwp_incremental_discovery.py` × 10 | 同窗两份均入账、旧件下载 0（复用 ref 回填）、修订 accession 缺失如实；同日多文档不折叠；跨 provider 页游标续举；截断→partial 可续；窗口不覆盖→partial 具名；真空+完整覆盖→complete |
| A2 | 同上（非期次用例） | IR/非期次候选 `fiscal_period=None` 正常枚举 |
| A3（CWP 部分） | 发现部分覆盖不推进 + cursor 恢复语义 | 部分状态不越缺口推进水位（调用方契约由 FF 落实） |
| A4 | `test_sr_cwp_incremental_read.py` × 10 | TXT 直读（transcript 契约）回定位证据；PDF 走 filing 路径含 parser 身份；纯模板具名 `skipped`；同 SHA 二读 reused=true 同 artifact（CAS 对象数不变）；**新进程读回零重复写入**（对象数、同 ref）；ref wire 往返；批次内单份 `uncertain` 不拦兄弟 |
| 积压 | `test_sr_cwp_reading_backlog.py` × 7 | unread 派生、读后状态追踪、文种/实体过滤、日期窗两端、keyset 分页无丢重、wire 往返 |
| CLI | `test_sr_cwp_incremental_cli.py` × 3 | 真子进程 stdin→stdout；零模型回执；二调用 reused=true；未知 schema 拒绝退出 2 |
| 回归 | batch e2e 15+1、schema 迁移 7、财务仓储 16、artifact store 18、架构门 4 | 全绿（含 1.4.0→1.5.0 升级链） |

复放命令：

```
cd C:/Users/郑曾波/Projects/cwp21
python -m pytest tests/integration/test_sr_cwp_incremental_discovery.py \
  tests/integration/test_sr_cwp_incremental_read.py \
  tests/integration/test_sr_cwp_incremental_cli.py \
  tests/integration/test_sr_cwp_reading_backlog.py -q
python -m pytest tests/integration/test_narrative_batch_cli_e2e.py \
  tests/contract/test_source_catalog_schema_migration.py \
  tests/financial_statements/test_repository_migration.py \
  tests/unit/test_narrative_artifact_store.py -q
```

## 4. 真实环境余项（待组合，本卡未跑）

- 真实 provider（StockInfoDLSimple / Dayu SDK）discover_page 接线与 Windows 长路径下的
  外部进程行为 —— 夹具 stand-in 只覆盖宿主侧契约。
- 正式 summary 档的真实回环模型组合（现有 batch e2e 已覆盖该引擎；本卡 summary 档只派生状态）。
- A3 的 FF 组合段（同槽一次活动运行、强退恢复、重复下载/付费 0）由 FF 卡收口。
- catalog 1.4.0 → 1.5.0 在真实生产库上的升级走查（升级链单测 16 项含 1.4.0 起点，
  真库抽查建议在组合验收前）。
- commit 解除（§0 平台门）后 rebase 最新 master 并复跑上述命令。

## 5. 清理收据

- 本卡生成的临时目录已删：`tests/integration/test_sr_cwp_diag.py`（临时探针）、
  `Projects/scratch21/`（解析探针）、`Projects/.sr_cwp_diag.json`（诊断转储）。
- 生产 `config/source_catalog.yaml`、`config/source_acquisition.yaml`、
  `.source_catalog/` 零写入（测试全用 tmp 夹具；`git status` 变更清单仅含 §1/§2 所列文件）。
- 网络采集与真实付费调用：0。

## 6. 独立审查发现与修复（第一轮）

独立 agent（只读复核 + 独立重跑）首轮结论 FAIL：4 P1 + 7 P2。全部按建议修复并补回归测试：

| # | 级别 | 发现 | 修复 |
|---|---|---|---|
| 1 | P1 | CLI 发现成功路径未测且坏：夹具 interface 非法、适配器缺 bounded 面 | 新增真子进程 `json_command_v1` 夹具适配器 CLI（含 `acquisition_usage` 回报）；夹具适配器补 `discover_page_bounded`/`fetch_bounded`/budget 标志；新增 CLI 发现成功测试（wire receipt + 复用 ref + URL 不外泄） |
| 2 | P1 | `prepare_read_result` 抛 `NarrativeArtifactConflictError`（如行被 retire）会中止整批 | `_read_local` 捕获 `NarrativeArtifactError` → 单份 `uncertain/read_store_error`；新增 retired-行批次隔离测试 |
| 3 | P1 | summary 档先查读结果表（违背 bundle-first 契约）且从不产生摘要 | 重构：summary 档只认正式 bundle，其余经 `summary_generator` 组合现有配置化批次入口（`run_batch` + 现行 LLM 配置装载器 + CWP 侧车配置），回执按文档映射回 `summarized/failed/skipped/uncertain`；CLI 加 `--llm-config/--summary-batch-config/--automation-db/--work-dir`；新增回环模型端到端测试（生成一次→二读 bundle-first 复用零请求） |
| 4 | P1 | 未证发布日期候选静默丢弃且 coverage 仍可 complete | 完整页遇未证日期强制 partial + `candidate_date_unproved` 具名诊断 + `usage.unproved_dates` 计数；新增测试 |
| 5 | P2 | `_require_bounded_adapter` 缺 `discover_page_bounded` 门 | 门补齐 |
| 6 | P2 | `_candidate_key` 漏 amended/期次，修订与原件折叠 | key 纳入 fiscal_year/period/form_type/amended；新增同 accession 修订双候选测试 |
| 7 | P2 | CLI 读路径 `sqlite3.Error` 逃逸成 traceback | 错误映射补 `sqlite3.Error` |
| 8 | P2 | `prepare()` 不校验 bundle 角色 | 对称角色守卫 |
| 9 | P2 | 未跟踪 citation_locator / handoff 目录 | 归入 rebase+commit 步骤（§0） |
| 10 | P2 | Dayu 适配器永报 partial（无 fiscal_year 窗口） | 保留诚实 partial；记录为真实 provider 接线余项 |
| 11 | P2 | backlog 无挂牌过滤、run_id 收据不持久、`_local_sources` 吞异常等 | 列入余项（§7），首版按实体/文种/日期过滤已满足最小组合 |

修复后 SR-CWP 套件 **35 passed**（发现 12 + 阅读 11 + CLI 5 + 积压 7）；审查复验的
基线回归（batch e2e/schema 迁移/财务仓储/artifact store/适配器 SPI/registry/采集职责
7 文件）**79 passed + 1 skip**（skip 为预存环境门控用例）；artifact store 直接消费方
（transport/reading transport/outbox/summary artifacts/cross-run/reading projection
generation）**154 passed**。
其中 summary 端到端经回环模型：首次生成 1 次模型请求 → 二次 bundle-first 复用 0 次请求，key 不入回执。

**全量套件说明**：本机全量 `pytest tests/` 超 1 小时无法完成（3600s 超时杀于 24%），
不作为本卡验收面。已对照 pristine master 确认的预存红（与本卡无关）：
`test_p5_storage_retirement_e2e.py`（1F）、`test_source_system_docs.py`（5F）、
`test_holdout_acceptance_controller_e2e.py`（12F）——master 同样复现。

## 7. 聚焦安全复核（Mimosa）

- 全仓 commit 门：见 §0（预存 high 全仓阻断，非本卡引入）。
- 本卡交付面聚焦扫描（depth=normal，focusFiles=本卡全部新/改源文件）已完成：
  job `scan-job-mwq8hv9g-ea3b7e7ff3fbc00f`，scanId
  `scan-2026-11-21T09-58-07.416Z-fe0e604f90e3`，
  seal `sha256:a53788305bd76398c9a1cc8f5e6a78d609ff1a1ec48f3a65b02405028722ce20`。
  全仓 137 条发现中，**本卡交付文件（incremental_discovery/incremental_read/
  incremental_cli/sr_cwp_fixtures 及全部修改的 source_catalog 源文件）贡献 0 条**。
  收据目录：`~/.mimosa/security-scans/project-a6c2b412c6bad97f65b5c60a/scan-2026-11-21T09-58-07.416Z-fe0e604f90e3/`。

## 8. FF 接线摘要（给总控）

- FF 按 interfaces §2/§3 调 `python -m company_wiki.source_catalog.cli
  discover-incremental|read-incremental --config <CWP目录配置> --acquisition-config
  <采集配置>`，stdin 请求、stdout 回执、stderr 仅具名错误。
- 发现候选 → 用 `provider + provider_document_id` 走既有 `ensure`（精确复用；已登记
  候选直接带 `existing_source_ref`，下载 0）。
- 阅读（local 档）→ `cwp-incremental-read-request/1`（零模型，产物落
  `narrative_read_results`；重复 run 复用产物）。summary 档由 CWP 侧组合：CLI 加
  `--llm-config`（现行配置装载器）+ `--summary-batch-config`（CWP 自有的 profile/
  caps/pricing 侧车）+ `--automation-db/--work-dir`；同一 `run_id` 续原 AUTO 批次。
  未达档位 → `cwp-reading-backlog-request/1` 分页取精确 refs。
- 结果读回 → `result_ref`（`cwp-read-result-ref/1`；bundle ref 走既有 narrative transport）。

## 9. 卡片条目对照与余项（组合前）

对照施工卡与 interfaces §2/§3/§5 的逐条核对结论（完整清单见交付汇报）：

**达成**：发现面字段/覆盖语义/游标、阅读六态、零模型本地档、bundle-first summary、
同批单份失败隔离、两进程零重复、backlog 分页、无 URL/路径外泄、生产配置零写入、
临时目录清理、handoff 双格式、独审两轮、按 commit 交付。

**披露余项**（审查员确认为可接受的组合前项）：

- run_id 收据读口：恢复语义靠幂等重提交（同 work_key→同产物 reused=true，无双花/
  重复）；interfaces §4.3 的“按原 run_id 查收据”读口在组合时按 AUTO 运行库补。
- 阅读样本 kind 覆盖：带业务内容的 PDF 走 annual_report 样本（与招股/再融资同走
  filing→PDF 解析路径）；招股/再融资 kind 未单独采样，组合验收时补。
- “强退和未知用量只查原记录”的注入测试属 A3 组合段（FF 侧）与 AUTO 引擎既有
  恢复测试域；本地档零模型无费用语义，summary 档经 run_batch 原生账目恢复。
- backlog 挂牌级过滤（现支持实体/文种/发布日期窗；挂牌维由 FF 名单侧收窄后传入）。
- 真实 provider discover_page 接线（StockInfoDLSimple / Dayu SDK；Dayu 窗口申报改进）。
- 生产 catalog 1.4.0→1.5.0 真库升级走查。

**最终 commit 重验**：审查员验证集（SR-CWP 4 文件 + batch e2e + schema 迁移 +
财务仓储 + artifact store + 适配器 SPI/registry + 采集职责，共 11 文件）在
`fc9cf2e7f`（= c01e6e04e + 交接文档）上复跑 **114 passed + 1 预存 skip**。
