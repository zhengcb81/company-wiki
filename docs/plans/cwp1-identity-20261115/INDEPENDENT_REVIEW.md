# 独立重审报告 — OWNERPKG-CWP-CANDIDATES-01 / CWP-1

- **reviewer_status**: `approved`
- **OPEN P1/P2**: P1 = 0，P2 = 0（**0 OPEN P1/P2 成立**）；P3 记录 4 条（CLOSED，不阻断）
- **被审 commit 列表**（分支 `codex/cwp1-identity-suffix-20261115`，worktree `company-wiki-cwp1-identity-20261115`）：
  - `ac8841c55` 基线（master HEAD @ 开工，docs-only）
  - `7fa16a213` A1 后缀归一化
  - `7595473f2` A2 具名双上市 reason
  - `a311c3127` PWF 收尾（docs）
  - `8cdff1e5e` F-01 勘误（docs）
  - `4b0fc3fe5` 本轮验收证据提交（HEAD，40 位 `4b0fc3fe5179feda5f090f5685e0a138fd0da14d`）
- **审查性质**：独立重审员，未参与实现与证据采集；全程只读（仅 Read/Glob/Grep/`git` 只读子命令/`cmp`/`diff`/`wc`/`ls`）。未修改任何实现、证据、PWF；未运行写生产数据的命令；未 commit/push/checkout。
- **依据**：施工包 `CANDIDATES-FIX-01.md` §4/§5/§6；§8 沿例 `BUILD-PACKAGE.md:77-105` 与 `INPUT-PREPARATION-PACKAGE.md:117`；仓 `AGENTS.md`（R4.1 配置卫生、职责边界、R7）。

## 结论摘要

§5 四项验收全部 `delivered`，证据均为真实 CLI 输出（非 mock/单测）。三处特别核验点与六路线两树一致性逐字段/字节级复核属实；route3 成功被正确标注为「非本包功劳」，剩余 5 条失败如实登记为既有下游契约缺口。红线全部合规：仅改 `security_identity.py` + `observability.py`（+测试），生产配置零写穿，零下载零模型，独立 worktree、未 push、未并 master。无 OPEN P1/P2，可进入 §6 交接（交接动作内需闭环 F-R7，见下）。

## Findings

### F-R1 / severity P2 / reviewer_status CLOSED
- **reproduction**: `evidence/baseline-master/master-ff-20f-reuse.stdout`(=`exit.txt` 2) 与 `evidence/ff-alibaba-20f-reuse.stdout.json`(=`exit.txt` 0) 逐字段比对。
- **root_cause**: 基线 `Alibaba Group Holding Limited` 因 Ltd/Limited 差异掉入 strong_fuzzy → `identity_error / fuzzy_candidates_require_user_selection`；A1 后缀归一化使 `official_name_exact` 单命中。
- **retest**: 基线 `status=identity_error`、`reason="...ambiguous / fuzzy_candidates_require_user_selection"`、`downloads=0`；修复后 `status=source_candidate`、`resolution_outcome=reused_existing`、`download_events=0`、`downloads=0`、命中 sha256 `36daec0c…`。与 README §5.2 及 findings F-04 逐字一致。施工包 §1 现象被复现并消除。

### F-R2 / severity P2 / reviewer_status CLOSED
- **reproduction**: 比对 `evidence/rf-routes/alibaba-routes-after-fix.json` 与 `evidence/rf-routes-master/alibaba-routes-master.json`；`cmp`/`diff` 三份 route3 stdout；`cmp` 两树 route3 `command.json`。
- **root_cause**: route3 用 `company_query=阿里巴巴－Ｗ` 精确别名 + 元数据完整的 FY2025 原件，从未撞身份歧义，故两树都成功。
- **retest**: 六路线 `exit_code/status/reason/upstream_cause/local_prepare_reason/downloads` 逐条一致；route3 两树 `exit=0 / found_capture_ready`。三份 stdout 同为 7335 字节，`diff` 差异仅 5 行——`tool_call_id`/`timestamp`/`read_at` 运行时刻及派生 `receipt_sha256`，所有业务字段（source_id/title/published_date/capture_method/snapshot_sha256/status）全同；两树 `command.json` 字节完全相同。证实为两次独立实跑、结果等价，「非本包功劳」归因真实。

### F-R3 / severity P2 / reviewer_status CLOSED
- **reproduction**: `git diff ac8841c55..HEAD -- src/`；`git diff ac8841c55..HEAD -- config/`；`git status --short`（worktree 与主仓 config 限定路径）；`git status -sb`/`branch -r --contains HEAD`/`branch --contains`/`merge-base --is-ancestor`/`worktree list`。
- **root_cause**: 改动限于 `observability.py`（REASONS/STAGES_BY_REASON 各 +1 条纯增量注册）、`security_identity.py`（后缀等价类 + `_suffix_equivalent_text` + 具名 reason 分支）、`tests/contract/test_source_catalog_security_identity.py`。无删除候选、无改已登记实体、`schema_version`/`IDENTITY_RESULT_SCHEMA_VERSION` 未动。
- **retest**: 全部通过，详见「红线核验表」。

### F-R4 / severity P3 / reviewer_status CLOSED（记录，随 handoff 交回）
- **reproduction**: 逐字段读两份汇总 JSON：master 版 `observed` 缺 `calls`，route3 仅 `status/title`，无 `source_id/published_date/capture_method/snapshot_sha256`；after-fix 版字段更全。
- **root_cause**: master 汇总为精简裁剪版，非结果差异。
- **retest**: 核心结果字段逐条一致，结论「两树逐条一致」成立；提示：若以字节/全字段 `diff` 做门禁会误报，应采用字段级归一化比对。

### F-R5 / severity P3 / reviewer_status CLOSED（记录）
- **reproduction**: `ls evidence/identify-*.command.*` → 4 个（仅 4 个 `--market` 变体）；7 个 identify 探针的 `stdout.json/stderr.txt/exit.txt` 齐全；ff 4/4、rf 6×2、baseline 5 均有 command 原件。
- **root_cause**: §5.1 用通用「命令模板」而非逐主探针落盘命令文件；3 个主 identify 探针（`Alibaba…`/`BABA`/`09988`）无 `.command.txt`。
- **retest**: 各 `stdout.json` 内含 `query` 字段 + §5.1 模板可完全推导复现，无实质复现缺口；但 README §5.4「每条探针落盘 command」对上述 3 条字面不成立，如实登记。

### F-R6 / severity P3 / reviewer_status CLOSED（记录）
- **reproduction**: `evidence/rf-six-routes-run.log:3` 中 route3 行为 `{"parse":"not_json","raw_head":""}`；`evidence/rf-routes/alibaba-routes-after-fix.json:29-39` 为 `found_capture_ready`。
- **root_cause**: run.log 是原始逐行运行日志（含一次解析中间态），非结论汇总；权威结论以汇总 JSON 与各路线独立 `.stdout.json` 为准。
- **retest**: 独立 `rf-routes/route3-hk-fy2025-reuse.stdout.json`（7335 字节完整）+ `exit.txt=0` + 与 master 业务字段一致。原始失败/中间记录未被改写，符合 §5.4「失败样本保留」与 findings 的执行插曲登记。

### F-R7 / severity P3 / reviewer_status CLOSED（记录，随 §6 交回时闭环）
- **reproduction**: `docs/plans/cwp1-identity-20261115/*.md` 仅 PWF 三件套；`git ls-files | grep -iE "cwp1|candidates|handoff"` 无本包 handoff；worktree `git status --porcelain` 为空；Dashboard `handoffs/` 内 Grep 包 ID/`4b0fc3fe5` 仅命中施工包原文 `CANDIDATES-FIX-01.md`；`findings.md:186` 的 `head_commit` 为占位符 `<见 handoff.json release_tag_or_commit_for_dashboard>`；`progress.md` 节点 10/11 称「handoff（含 40 位 release commit）」。
- **root_cause**: §8-1 重审尚未完成，实现者以「通过独立重审后」的前瞻措辞引用交接阶段产物；handoff.json 与 40 位 SHA 属 §6 交接动作本身的产物，非本包实现/验收证据，且该 SHA 已存在（当前 HEAD）。
- **retest**: 进入 §6 交接时以 40 位 `4b0fc3fe5179feda5f090f5685e0a138fd0da14d`（可 `git rev-parse`）落盘 handoff.json 的 `release_tag_or_commit_for_dashboard`，替换 `findings.md:186` 占位符并校正 `progress.md` 措辞，由 Dashboard 侧按该 commit 消费。**不升级为 P2 的理由**：§8-1 门禁四维度（§5 完整性/准确性/红线/诚实性）全部通过，该缺口是交接动作产物，不涉及实现或证据返工；作为 P3 随 handoff 一并交回。本重审不替实现者补该文档。

## 逐条验收对照表（施工包 §5）

| 条目 | 判据 | 结论 | 证据路径 |
|---|---|---|---|
| §5.1 三查询探针 | 三查询 named 结果，非 fuzzy 模糊集 | **delivered** | `evidence/identify-Alibaba_Group_Holding_Limited.stdout.json`（resolved/one_verified_exact_identity/US BABA official_name_exact/1 候选）；`evidence/identify-BABA.stdout.json`（ambiguous/`cross_market_dual_listing_requires_market_selection`/resolved=null/2 候选 HK 09988 alias_exact + US BABA ticker_exact）；`evidence/identify-09988.stdout.json`（resolved/HK 09988 ticker_exact/1 候选）；`evidence/identify-BABA_market_US|HK.stdout.json`、`identify-Alibaba_Group_Holding_Limited_market_US.stdout.json`、`identify-09988_market_HK.stdout.json`（4 个消歧全 resolved）；`evidence/baseline-master/master-identify-*.stdout`（原 strong_fuzzy/无名 multiple_verified_exact_identities） |
| §5.2 FF reuse_only 20-F | 对阿里 20-F 返回确定 resolve，不 ambiguous | **delivered** | `evidence/ff-alibaba-20f-reuse.stdout.json`（source_candidate/reused_existing/download_events=0/downloads=0，sha256 `36daec0c…`）、`ff-alibaba-20f-reuse-nomarket`、`ff-baba-reuse-us`（同上）；`evidence/ff-baba-reuse-nomarket.stdout.json`+`.exit.txt`（exit=2 失败样本，具名 `cross_market_dual_listing_requires_market_selection`，**非 fuzzy**）；`evidence/baseline-master/master-ff-20f-reuse.stdout`+`.exit.txt`（exit=2 / identity_error / `fuzzy_candidates_require_user_selection`） |
| §5.3 RF 六路线 | ≥1 条 found+capture_ready 或具名新原因说明剩余缺口 | **delivered** | `evidence/rf-routes/route3-hk-fy2025-reuse.stdout.json`+`.exit.txt`（exit=0，完整来源记录 + verified_read 收据，汇总 status=found_capture_ready）；`evidence/rf-routes/alibaba-routes-after-fix.json` 与 `evidence/rf-routes-master/alibaba-routes-master.json`（六条逐条一致）；route1/2/4/5/6 `.stderr.json`（`invalid_local_prepare_request` / `acquisition_validation_failed`，downloads=0、provider_started=false）；`evidence/baseline-master/master-rf-route3.stdout`、`evidence/rf-routes-master/route3-*` |
| §5.4 证据带命令输出 + 失败样本保留 | 全部证据带命令输出；失败样本保留 | **delivered**（含 F-R5/F-R6 两处 P3） | `evidence/README.md`（索引）；ff 4/4、rf 6×2、baseline 5、market 4/4 的 `.command.txt|.command.json`；各探针 `.stdout/.stderr/.exit` 三件套齐全；失败样本 `ff-baba-reuse-nomarket.*`、route1/2/4/5/6 `.stderr.json`、`evidence/rf-six-routes-run.log`（原始未改写逐行日志）；§5.1 命令模板可推导 3 个主 identify 探针命令 |

## 红线核验表（施工包 §4 + AGENTS.md）

| 红线 | 核验命令/方法 | 结论 | 证据路径 |
|---|---|---|---|
| 只动 `security_identity.py` + `observability.py`（+测试）；不动已登记实体/不删候选 | `git diff --name-status ac8841c55..HEAD` 与 `git diff ac8841c55..HEAD -- src/` | **通过**：仅 M 两个 src 文件 + 1 测试；其余全为 A（PWF/evidence）；无 D、无 config/、无其它 src。`observability.py` 纯增量 2 条注册；`security_identity.py` +89/-4，无数据删改 | `src/company_wiki/source_catalog/security_identity.py`、`src/company_wiki/source_catalog/observability.py`、`tests/contract/test_source_catalog_security_identity.py` |
| 未改 Dashboard 侧适配器 | 同上改动全集 + `rf-routes/route3-hk-fy2025-reuse.command.json`、`ff-*.command.txt` | **通过**：改动全集全在 company-wiki 仓内；FF/RF 官方入口为只读复用（指向外部仓脚本与 RF 原始请求体），未修改 | `evidence/rf-routes/route3-hk-fy2025-reuse.command.json`、`evidence/ff-alibaba-20f-reuse.command.txt` |
| 生产配置 `config/source_catalog.yaml` / `config/company_wiki.json` 未被探针写穿 | worktree `git diff ac8841c55..HEAD -- config/`、`git status --short -- config/`；主仓 `git status --short -- config/...`、`git diff -- config/...` | **通过**：四处均为空；探针用 tmp 夹具 `C:/Users/…/Temp/cwp1-probe/company_wiki_probe.json` + `catalog_probe.yaml`（AGENTS.md R4.1 合规） | `evidence/README.md:6-12`；命令原件中的 `--config` / `--company-wiki-config` 路径 |
| 零下载零模型 | 各证据 `downloads`/`download_events`/`provider_started`/`cost_usd`/`http_exchanges` 字段 | **通过**：FF 全探针 downloads=0、download_events=0；RF 全探针 downloads=0、provider_started=false、cost_usd=0、http_exchanges=0；基线 FF downloads=0；`rf-six-routes-run.log` 六条 provider_started=false | `evidence/ff-alibaba-20f-reuse.stdout.json`、`evidence/baseline-master/master-ff-20f-reuse.stdout`、`evidence/rf-routes/route2-hk-fy2026-fetch-if-missing.stderr.json`、`evidence/rf-six-routes-run.log` |
| 提交前核分支 / 独立 worktree / 未 push / 未并 master | `git branch --show-current`、`git worktree list`、`git status -sb`、`git branch -r --contains HEAD`、主仓 `git branch --contains 4b0fc3fe5`、`git merge-base --is-ancestor 4b0fc3fe5 master` | **通过**：分支=`codex/cwp1-identity-suffix-20261115`；独立 worktree 在册；`status -sb` 无 upstream、`branch -r --contains HEAD` 空 → 未 push；`branch --contains` 仅本包分支、`is-ancestor` 退出码 1 → 未并入 master；基线 `ac8841c55` 是 master 祖先（主仓 master 已前进至 `07d481180`，在途 WIP，与 §8-3 情形 2 明示交接一致） | `git` 只读输出；`task_plan.md:8-9,64-65`、`findings.md:179-189` |

## §8-1 门禁判定与 §6 交接

- **完整性**：§5.1/§5.2/§5.3/§5.4 全部 `delivered`，无静默缩水（BABA 无 market 的 ambiguous 是 §3 允许的「带消歧语义的具名响应」，有 4 个消歧探针佐证，非遗漏）。
- **准确性**：抽查 JSON 的 status/reason/resolved/candidates/downloads 与 `README.md`/PWF 逐字段一致；三处特别核验点全部属实；六路线两树结果逐条一致（F-R2）。
- **诚实性**：route3 成功在 `README.md:84-90`、`findings.md` F-05、`progress.md` 节点 8 均明确标注「非本包功劳」；剩余 5 条失败如实登记为既有下游契约/元数据缺口（FF↔CWP local_prepare schema 1.0/1.1、ensure 采集校验层），非缩水、非 fuzzy 复发；NOT_RUN 完整（`findings.md:63-69,168-177`：未跑全仓套件、未修 FC-1301 既有漂移、未 push/未并 master、后台拒绝插曲、未改 A1/A2）；§5 证据均为真实 CLI（`company_wiki.source_catalog.cli identify`、`scripts/fetch_filing.py`、`revenue-forecast/scripts/source_preparation.py` + 原始 RF 请求体），单测数字单列于 PWF，**无 mock/单测冒真实链证据**。
- **红线**：五条全部通过（见上表）。
- **OPEN 计数**：P1 = 0、P2 = 0；P3 共 4 条（F-R4/F-R5/F-R6/F-R7）全部 CLOSED，仅记录、不阻断。

**结论**：`0 OPEN P1/P2` **成立**，`reviewer_status = approved`，**可以进入 §6 交接**。交接动作内需闭环 F-R7：以 40 位 `4b0fc3fe5179feda5f090f5685e0a138fd0da14d` 落盘 handoff 的 `release_tag_or_commit_for_dashboard`，替换 `findings.md:186` 占位符；按 §8-3 情形 2（主工作区在途 WIP + ff1-catalog lane 未收口）不强行并线，Dashboard 侧按该候选 commit 重跑阿里 FF drill 与 RF 采集路线，并把 5 条下游契约缺口分别派给 FF owner 与 CWP FF1 lane。
