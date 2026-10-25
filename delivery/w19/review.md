# W19-SINA-STATEMENTS 独立终审报告（第 2 轮：修复复查）

- 审查者：zcode 独立终审 agent（`mimo-v2.6-flash`，未参与实现；全部结论来自本人实跑，不引用作者日志）
- 审查日期：2026-10-25（第 2 轮，对作者 R1–R9 根修的独立复验）
- **最终被审代码版本（binding）**：
  - company-wiki：**`ae317ca9`**（基线链 243993d2→…→ae317ca9；第 1 轮被审 `e583904d`）
  - filing-fetch：**`7d9bb85`**（基线 e0d9642→…→7d9bb85；第 1 轮被审 `a211d3a`）
- 第 1 轮报告原文保留在 git 历史（`ae317ca9` 内 `delivery/w19/review.md`），本文件为其原地更新版。
- 执行环境：Windows / Python 3.13.9；两仓以 `git archive <最终commit>` 导出到 `%TEMP%\w19-re-review` 只读副本实跑。未修改任何源码、未写生产目录、未联网（全部 replay/复用路径）、未提交 commit；临时根按纪律于报告落盘后删除。

## 1. 结论

**PASS_WITH_FIXES** —— 第 1 轮 9 项 finding 中 8 项已根修并经我独立复验通过；但：

1. **W19-R10（major, blocking）**：R1 根修**不完整**，两个变体实测仍谎报 `complete`（`all_history`/无 from 变体、`end_of_data`+范围上界放宽变体）；
2. **W19-R11（major, blocking）**：本轮新增的 R8 重放入口存在**跨实体数据污染**（把 A 公司的报表以 B 公司 security_id 发布，exit 0）。

另有 1 项 medium（continuation 契约一致性）与 2 项 low（replay 旗标/信封形状）。修复并补审前不可交接。

### 第 1 轮 finding 处置表

| ID | 第 1 轮 severity | 状态 | 独立复验证据 |
|---|---|---|---|
| W19-R1 范围放宽谎报 complete | major/blocking | **部分修复 → W19-R10（仍 blocking）** | from 加宽已修（§2.2 T1）；`all_history`/无 from、`end_of_data`+to 加宽两变体仍复现（§2.2 T2/T3） |
| W19-R2 行界截断静默/fields 未暴露 | medium | **修复（fields 部分）+ 残留 → W19-R12** | fields 双路径 e2e 一致；continuation 见 W19-R12 |
| W19-R3 FF 误标 upstream_error | minor | **修复** | §2.3：badrange → `request_error`、exit 2、无 retryable |
| W19-R4 顶层 unavailable 不可达 | minor | **修复** | §2.2：三表全失败 → 顶层 `unavailable` |
| W19-R5 未提交改动 | medium/blocking | **修复** | 两仓 diff 仅含声明文件，全部入 `ae317ca9`/`7d9bb85` |
| W19-R6 retrieved_at 命名 | low | **修复** | 报告键含 `retrieved_at`、无 `captured_at`（§2.1） |
| W19-R7 instant 语义 | low | **修复** | 报告键含 `period_semantics`（balance_sheet=instant） |
| W19-R8 无 SourceRef 重放入口 | low | **修复（主体）+ 新缺陷 → W19-R11/W19-R13/W19-R14** | §2.4 |
| W19-R9 回放字节不计量 | low | **修复** | §2.1：离线字节与夹具解压字节**逐表精确相等** |
| （观察）PIT 同日 as_of | — | **修复** | §2.3：`as_of=2026-10-25` → `pit_verified` |

## 2. 独立实跑与结果

### 2.1 完整链路 + R9 字节账（复验）

自建夹具根（19/19 解压 SHA 对 observations.json 通过 + 2 个 44B 等价终止页）与 wiki 根，真子进程跑 CWP CLI：

- 首次三表请求：`complete`、36/33/36 期、15 HTTP、0 费用、无物理路径；**R9：逐表 `response_bytes` 与夹具解压字节精确相等**（income 705,179 / balance 1,104,886 / cash 647,868，合计 2,457,933 = 各页解压字节和）；报告键含 `retrieved_at`、`period_semantics`，无 `captured_at`。
- 移走 manifest 二次请求：**0 HTTP**，versions/values/sources/documents/originals 零增长，version id 与 rows 逐行一致。

### 2.2 R1 重抓语义矩阵（自拟断言；作者仅加了 from-加宽一条回归）

| 探针 | 操作 | 结果 |
|---|---|---|
| T1 from-加宽（作者案例 e2e） | wikiR1：窄 from=2025（1 HTTP/6 期/period_boundary）→ 宽 from=2016 | **重抓 5 HTTP → 36 期 complete**；同宽再请求 0 HTTP complete ✅ |
| T4 其余不完整终止（作者无回归，我自拟） | 直接改 `financial_statement_coverage.terminal_reason` 为 `count_changed / budget_stopped / max_pages / duplicate_page / no_progress` 后各发 fetch_if_missing | **5 个终止全部重抓（5 HTTP）且恢复 end_of_data** ✅；对照 `end_of_data` → 0 HTTP ✅ |
| T2b 无 from 变体 | 窄抓后请求**去掉 period_end_from** | ❌ **0 HTTP、complete、仅 10/36 期**（adv=36、term=period_boundary） |
| T2c `all_history` 变体 | 窄抓后请求 `all_history=true`（卡面钦定的全历史旗标） | ❌ **0 HTTP、complete、仅 10/36 期**（2016–2023 全缺） |
| T3 to-加宽 + 供应方新数据（突变） | 正常全量抓取（to=2026-06-30, end_of_data）→ 换夹具根使 lrb page1 额外含 2026-09-30（report_count 37）→ 请求 to=2026-12-31 | ❌ **0 HTTP、complete、缺 2026-09-30**（供应方此刻有该期）；对照 `intent=refresh` 会重抓并因 count 变化诚实报 partial（income 37 期/last=2026-09-30/term=count_changed）✅ 守卫生效 |

→ 汇总为 **W19-R10**。

### 2.3 R3 / R4 / PIT / FF 复验

- FF 真子进程往返：exit 0、`financial-statements-response/1`、complete 36/33/36、0 HTTP、无路径泄漏。
- **R3**：FF 输入 `from>to` → **exit 2、`status=request_error`、无 retryable、无 producer_exit_code 误标**（原为 `upstream_error`+`retryable=true`）✅。
- **R4**：新根 + 空 manifest（三表 provider 失败）→ 三表 `unavailable`、**顶层 `unavailable`**（第 1 轮为 partial）✅。
- FF 带 `fields=["BASICEPS"]` 往返 → 行正确过滤 ✅；FF 对 `fields/continuation` 校验放行 ✅。
- PIT `as_of=2026-10-25`（=抓取日）reuse_only → `point_in_time_quality=pit_verified`、全部 `pit_verified=true`、0 HTTP ✅。

### 2.4 R8 重放入口复验（含自拟负例）

- 正向：对 income/balance/cash 三个已提交 source 分别 `--replay-source` → exit 0、`statement_type` 由字节内 `item_source` 正确判定（lrb/fzb/llb 均验证）、`http=0`、`new_version_ids=[]`、`reused=10`。
- **dedup（复查项 2）**：重放前后 `documents=12 / sources=24 / versions=105 / values=9729 / originals=12 / provenance=12` 全部不变，staging 无 page0 残留，二次重放完全幂等 → **不会重复登记 document、不会产生第二个原件** ✅。
- 非法 source_id → **exit 2 `request_error`**（命名理由）；格式合法但未登记 → exit 2 ✅。
- ❌ **跨实体污染（W19-R11，自拟负例）**：同一根内加入第二家证券（美的集团/000333）后，用 `company_query=美的集团` + **中微公司**的 source_id 重放 → **exit 0、status=complete、在 `security_id='000333'`/`entity='美的集团'` 名下新建 10 个版本**（内容为中微的利润表页）。随后对“美的集团”的查询会把中微数据当本地 complete 返回。
- ❌ `--replay-source` 与 `intent=reuse_only` 同用 → **旗标被静默忽略**（reuse_only 提前返回早于 replay 分支），回普通 reuse 响应 exit 0（W19-R13）。
- ❌ replay 输出声明 `financial-statements-response/1` 但无 `statements/company_identity/coverage`（W19-R14）。

### 2.5 R2 fields/continuation 一致性（复查项 3）

- `fields`：**双路径一致** —— 采集路径与 reuse_only 路径对 `fields=["BASICEPS","DILUTEDEPS"]` 均只回所选行（e2e 逐值核对）✅。
- `continuation`：**不一致** ——
  1. reuse_only 接受该字段（契约校验通过）但**静默丢弃**（带 token 与不带 token 响应逐行相同，回显 `continuation=None`）；
  2. 服务端 `max_rows=20000` 对 CN 数据不可达（单表最大 ~6k 行），**服务永远发不出 token**，分页路径实际是死代码（仅 repository 单测覆盖）；
  3. 手工构造合法 token `fsv-…:5` 复测：**income 正确续传**（首报告 72 行、min ordinal=6），但同一请求里的 balance/cash 被 token 逻辑整段跳过 → **`status=complete` 且 `reports=0`**（谎报）。
  → 汇总为 **W19-R12**（token 今日不可自发产生，故为契约级/潜伏，非数据损坏）。

### 2.6 全套测试独立重跑（复查项 5，全部在最终 commit 导出副本）

| 套件 | 结果 |
|---|---|
| CWP `python -m pytest tests/financial_statements/ -q` | **97 passed**（37.9s），exit 0 |
| FF `python -m pytest tests/financial_statements/ -q` | **16 passed**（3.7s），exit 0 |
| CWP 窄接缝旧消费者 `tests/contract/test_source_catalog_schema_migration.py + test_source_catalog_canonical_writer.py` | **20 passed**，exit 0 |
| FF 旧消费者 `tests/test_fetch_filing.py` | **111 passed, 1 skipped, 39 subtests passed**，exit 0 |
| FF 传输/契约旧消费者 `test_p5_process_transport.py + test_ff_v2_contract.py` | **24 passed**，exit 0 |

## 3. 本轮 finding（按新编号）

### W19-R10 — R1 根修不完整：`all_history`/无 from 与 `end_of_data`+to 加宽仍谎报 complete（severity: major，**blocking=true**）
- 证据：`cwp/src/company_wiki/source_catalog/financial_statements/service.py:366-389` `_needs_fetch`：`period_boundary` 分支仅在 `period_from and period_from < first_stored` 时重抓——`period_from is None`（无 from 或 `all_history=true`，`effective_period_from` 返回 None）恒不重抓；`end_of_data` 分支直接 `return False` 并注释“exhausted in both directions”，但该结论只对更旧方向成立，对更新方向（新期间会随时间发布）不成立。实跑：§2.2 T2b（0 HTTP、complete、10/36）、T2c（all_history 同样 0 HTTP、complete、10/36）、T3b（to=2026-12-31、0 HTTP、complete、缺供应方已有的 2026-09-30）。
- 根因：覆盖判断没有把“请求范围是否被既有存储跨度完整包含”作为统一条件；两个分支各自用局部规则近似。
- 影响：与第 1 轮 R1 同类的“partial→complete”谎报，触发面包括卡面钦定的 `all_history` 全历史请求与跨期自然请求（先抓后宽）。
- 建议：`_needs_fetch` 改为范围包含判定——`period_boundary` 下 `period_from is None`（或 `all_history`）必须重抓；`end_of_data` 下若 `period_end_to > last_stored_period`（或 to 为空即无上界）也须重抓（一次页请求即可核验最新期），否则降级 `partial` + named gap（如 `range_not_covered`）；补 3 条回归（无 from、all_history、to 加宽+新数据突变）。

### W19-R11 — `replay_source` 跨实体污染：请求身份与 source 归属实体不校验（severity: major，**blocking=true**）
- 证据：`service.py:536-603` `replay_source`：以请求 `company_query` 解析身份 → 仅按 `documents.primary_source_id=?` 查 document（`service.py:554`，**不比对 document/entity 与解析出的 security**）→ `_commit_and_publish_page(security=请求方)`。实跑（§2.4）：`company_query=美的集团` + 中微 source_id → 10 个 `fsv-*` 版本写入 `security_id='000333'`、`entity='美的集团'`，内容为中微利润表；exit 0、status=complete。随后 reuse 查询“美的集团”会把该数据当本地 complete 返回。
- 根因：重放入口只做了 source_id 形态/登记校验，缺少“source 所属实体 == 请求身份”的一致性校验（卡面要求“公司名与 hint 冲突才报明确问题”）。
- 影响：共享两长表被写入错误公司数据且状态诚实性被绕过（数据完整性缺陷，虽需显式错配调用，但静默成功不可接受）。
- 建议：`replay_source` 校验 `documents.entity`（及 market/security 归属）与解析身份一致，冲突时报明确 `request_error`/`identity_error` 并 exit 2；补跨实体负例回归；顺带核对 `code/exchange`。

### W19-R12 — continuation 契约三重不一致（severity: medium，blocking=false）
- 证据（§2.5）：reuse_only 接受并静默丢弃 `continuation`；服务端 20000 行界对 CN 数据不可达导致 token 永不发放（分页死代码）；手工 token 下多表请求对非目标表返回 `complete + reports=0`（income 侧续传本身正确，72 行/ordinal≥6）。`service.py` 复用路径只传 `fields` 不传 `continuation`；`_handle_statement` 对每张表都回传同一个 request-level token。
- 建议：continuation 作用域改为“单表请求”或在 token 内绑定 statement_type 并在不匹配时明确报错；reuse_only 要么支持续传要么显式拒绝该字段；截断时状态降级 `partial`；若短期不打算启用分页，移除/标注该字段为 reserved，避免死契约。

### W19-R13 — `--replay-source` 在 `intent=reuse_only` 下被静默忽略（severity: low，blocking=false）
- 证据（§2.4）：`cli.py` reuse_only 提前返回位于 replay 分支之前 → 旗标请求得到普通 reuse 响应 exit 0，无任何提示。
- 建议：reuse_only 分支前先处理 `--replay-source`，或对“旗标+reuse_only”组合报 `request_error`。

### W19-R14 — replay 输出声明 `financial-statements-response/1` 但缺该 schema 的必备载荷（severity: low，blocking=false）
- 证据（§2.4）：输出键仅 `schema_version/request/status/statement_type/source_id/new|reused_version_ids/usage`，无 `statements/company_identity/coverage`。
- 建议：为重放操作定义独立收据 schema（如 `financial-statements-replay-receipt/1`），或补齐 response/1 的必备字段。

## 4. 修复与复审要求

1. **W19-R10、W19-R11 必须根修**并补回归（建议各含一条 CLI 级 e2e），随后由独立审查者对差异第三轮补审。
2. W19-R12 建议本轮修复或在 handoff“当前不足”逐条声明；W19-R13/R14 建议随手修。
3. 绑定关系更新为：reviewed commits = CWP `ae317ca9` / FF `7d9bb85`；再改被审代码须继续补审（COMMON §4）。

## 5. 临时产物与清理

- 全部实跑在 `%TEMP%\w19-re-review\`（`cwp/`、`ff/`、`roots/`、`out/`、`setup_roots.py`、`setup_wiki.py`、`t3_driver.py`、`r8_r2_driver.py`）；报告落盘后整体删除，可按 §2.1 描述一键重建。
- 未触碰生产目录 `Projects/company-wiki`；两仓无任何 commit；本文件与 `review.json` 原地更新（不自行 commit）。
