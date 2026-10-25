# W19-SINA-STATEMENTS 独立终审报告

- 审查者：zcode 独立终审 agent（`mimo-v2.6-flash`，未参与实现；本报告全部结论来自本人实跑，不引用作者日志）
- 审查日期：2026-10-25
- 被审代码版本（binding）：
  - company-wiki：branch `codex/w19-sina-statements-20261025`，基线 `243993d2`，被审 commit **`e583904d`**
  - filing-fetch：同分支，基线 `e0d9642`，被审 commit **`a211d3a`**
- 执行环境：Windows / Python 3.13.9 / httpx 0.28.1；两仓在 `%TEMP%\w19-indep-review` 用 `git archive <被审commit>` 导出的**只读副本**上实跑（`cwp/` = e583904d，`ff/` = a211d3a，`cwp_dirty/` = e583904d + 工作区未提交改动 overlay）。未修改任何源码、未写生产目录（`Projects/company-wiki` 全程只读）、未联网（全部 replay / 复用路径）、未提交任何 commit；临时根结束前保留在 `%TEMP%` 供复核，见 §6 清单。
- 夹具：`docs/plans/w19-sina-statements-2026-10-25/inputs/research/capture/*.json.gz`，由本人脚本 `setup_roots.py` 独立组装 fixture 根（url→file manifest，**19/19 份解压 SHA 与 observations.json 逐一比对通过**；fzb/llb 缺 page5 终止页，按施工卡允许用 `sh999999-…` 的 44 字节真实观测等价构造）。

## 1. 结论

**PASS_WITH_FIXES**（存在 1 项 blocking 实质问题 W19-R1 与 1 项 blocking 流程问题 W19-R5；须根修/处置并补审后方可交接。其余为非阻断改进项。）

关键链路、负例、测试、空间与清理证据见 §2–§5；测试在被审 commit 上全绿，但实现层存在下述诚实性缺陷。

## 2. 独立实跑命令与结果摘要

### 2.1 完整链路（不经作者测试辅助函数，自建临时根）

| # | 命令（摘要） | 结果 |
|---|---|---|
| 1 | `python setup_roots.py`（本人脚本：组装 fixture 根 + `write_market` 生成 CN security_master + `SourceCatalog.scan()` + 自写 `config/source_catalog.yaml`） | fixtures=21（19 真实 + 2 等价终止页），**SHA 校验 19/19 通过**；wiki 根 config/security_master 就绪 |
| 2 | `python -m company_wiki.source_catalog.financial_statements.cli --wiki-root <root> --fixture-root <fixtures>` stdin=三表全量请求（2016-01-01..2026-06-30, fetch_if_missing, limits 8MB/120s/0.00） | exit 0；`status=complete`；income **36** 期 / balance **33** 期 / cash **36** 期；每表 4 页 + 1 终止页，`http=5/5/5`（共 15）、`cost=0.00`；`terminal=end_of_data`；**响应无任何物理路径**（grep w19-indep-review/AppData/catalog.sqlite 均无）；DB schema=1.3.0；versions=105、**value 行=9729**（36×77+33×141+36×64 逐表吻合）、originals=12+12 provenance、`document_kind=financial_statement_dataset`、`provider=sina_finance`、value_decimal 全部 TEXT/null（无 REAL） |
| 3 | 同一请求二次运行，**先移走 fixture manifest**（任何 HTTP 尝试都会失败） | exit 0；三表 `http_requests=0`；versions/values/sources/documents/originals **零增长**；`statement_version_id` 与 rows 与首次**逐行完全一致**；`last_checked_at` 只更新观察（refresh 时另行验证） |
| 4 | 9,729 行 `json_pointer` 全量回读：按 `source_ref.content_sha256` 定位已提交原件，逐行走指针比对 `raw_value` | **9729/9729 全部精确解析**（SourceRef/locator 可回读独立成立） |
| 5 | 空间测量（catalog 目录 + lake） | 4,726,785B + 2,484,737B = **6.88 MiB ≤ 16 MiB** 目标 |

### 2.2 作者未提供的负例 / 突变（本人自拟）

**W19-R1 复现（range-widening → 虚假 complete）** —— 施工卡/作者测试均未覆盖：

```
# 新建独立根 wikiB；step1 窄范围
cli --wiki-root roots/wikiB --fixture-root roots/fixtures  < req_narrow.json   # from=2025-01-01, to=2026-06-30
# step2 放宽范围（仅改 period_end_from=2016-01-01）
cli --wiki-root roots/wikiB --fixture-root roots/fixtures  < req_wide.json
```

- step1：`complete`，6 期，`terminal=period_boundary`，`advertised=36`（正确：2025 起的范围已覆盖）
- step2：**`status=complete`，但只返回 10 期（2024-03-31..2026-06-30），`http=0`，请求范围 2016-01-01..2026-06-30 缺 26 期**，`advertised_report_count=36` 与 `observed_periods=10` 并存
- 即：先前一次窄范围抓取留下的 `financial_statement_coverage`（terminal=period_boundary 已属 `_TERMINAL_EXHAUSTED`）使 `_needs_fetch` 判定“本地已命中”，`elif selected: status="complete"` 把“范围内有任意本地期间”当成了“范围已覆盖”——**违反“不把 partial 改成 complete”与 SKILL 自述的 “complete when every requested statement covers its range”**。

其余独立负例（作者单测有同名逻辑、但未走 CLI 真进程的，我补齐了端到端）：

| 负例 | 命令/操作 | 结果 |
|---|---|---|
| `period_end_from > period_end_to` | CLI + `req_badrange.json` | **exit 2**，envelope `status=request_error`，`error=period_end_from must not exceed period_end_to` |
| `all_history` + `period_end_from` 并存 | CLI + `req_allhist.json` | **exit 2**，`request_error`，互斥报错正确 |
| 一表失败不回滚其他表 | 新根 wikiC + 去掉全部 llb 夹具的 fixture 根跑三表请求 | 整体 `partial`；income `complete`(36)、balance `complete`(33) **已落库**（69 版本/8 原件），cash `unavailable(http_error)`；再次请求：前两表 **0 HTTP**，仅 cash 重试 1 次 |
| 全表 provider 失败 | 新根 wikiD + 空 manifest（provider=None） | 三表均 `unavailable(provider_unavailable/http_error)`，**顶层 status=partial（见 W19-R4）** |
| 严格过去 as-of 不冒充 PIT | reuse_only + `knowledge_mode=point_in_time, as_of=2020-01-01` | `point_in_time_quality=historical_asof_unverifiable`，全部 `pit_verified=false`，0 HTTP |
| 同内容刷新不重复版本/原件 | CLI `intent=refresh`（真实重放 15 HTTP） | versions=105、values=9729、originals=12 **均不变**；`last_checked_at` 更新、`first_seen_at` 不变；`provider_update_time` 仅作观察 |
| 查询路径不建库 | 新根 wikiE（仅 config+security_master，**无 DB**）跑 `intent=reuse_only` | exit 0；三表 `not_found + gap_reason=catalog_database_missing`；**结束时仍未创建 catalog.sqlite3**（catalog_dir 仅 security_master） |
| FF 真子进程往返 | `python ff/scripts/fetch_statements.py --config <json>`（PYTHONPATH=CWP/src，真实 CWP 子进程，本地已填充根复用） | **exit 0**，`schema_version=financial-statements-response/1`，`status=complete`，36/33/36 报告，`http=0`，无路径泄漏 |
| FF 非法请求 | 同上输入 badrange | **exit 2**，但 envelope `status=upstream_error`、`retryable=true`（见 W19-R3） |

### 2.3 测试实跑（全部在被审 commit 导出副本上）

| 套件 | 命令 | 结果 |
|---|---|---|
| CWP 本卡 | `python -m pytest tests/financial_statements/ -q` | **91 passed**（49.9s），exit 0 |
| CWP 窄接缝旧消费者① | `pytest tests/contract/test_source_catalog_schema_migration.py tests/contract/test_source_catalog_canonical_writer.py -q` | **20 passed**，exit 0 |
| CWP 迁移旧消费者② | `pytest tests/contract/test_disaster_drill_fc405.py test_migration_drill.py test_migration_tool.py test_migration_engine_fc401.py -q` | **26 passed**（1.2.0 旧库→1.3.0 迁移链成立），exit 0 |
| CWP 架构门 | `pytest tests/contract/test_architecture_gate.py -q` | **5 passed** |
| FF 本卡 | `python -m pytest tests/financial_statements/ -q` | **13 passed**（3.6s），exit 0 |
| FF 传输/契约旧消费者 | `pytest tests/test_p5_process_transport.py tests/test_ff_v2_contract.py -q` | **24 passed** |
| （参考）工作区未提交改动 overlay | 同 CWP 本卡套件 | **92 passed**（见 W19-R5） |

## 3. 逐条 finding

### W19-R1 — 范围放宽后 fetch_if_missing 谎报 `complete`（severity: major，**blocking=true**）
- 证据：`cwp/src/company_wiki/source_catalog/financial_statements/service.py:334-352`（`_needs_fetch` 只比较 `observation.observed_periods == stored_periods` 与 terminal 是否 exhausted，**从不比较请求范围与既有覆盖边界**）、`service.py:268-269`（`elif selected: status="complete"`）、`repository.py:360-406`（`record_coverage_observation` 不落请求范围/最早抓取边界）；实跑复现见 §2.2 第一组（窄→宽两步，第二步 10/36 期却 `complete`）。
- 根因：覆盖观察只记“抓到过多少期”，没有“已覆盖到哪个范围”的状态；`selected` 非空被等同于范围覆盖完整。
- 影响：真实调用序列“先取近端再取全历史”会得到 `complete` 但缺 2016–2024 数据的响应，违反施工卡 §2.1/§3.1“诚实 partial、不把 partial 改成 complete”。
- 建议：在 coverage 观察中持久化本次抓取的请求范围（或最早抓取边界 `fetched_from`）；`_needs_fetch` 对超出既有覆盖边界的请求重新抓取，或返回 `partial` + named gap（如 `range_not_covered`），并补一条窄→宽回归测试。

### W19-R2 — 行数上限截断静默发生，continuation/fields 未进公共接口（severity: medium，blocking=false）
- 证据：`service.py:279-290` 调用 `query_statement_rows(max_rows=DEFAULT_MAX_ROWS)` 后**丢弃**返回的 `continuation`/`truncated`（`repository.py:321-331` 计算了但无人消费）；`contracts.py:150-157` 请求允许字段里**没有** `fields`/`continuation`/`max_rows`；`repository.py:456-561` 只读查询同样不回 continuation。
- 根因：卡片 §3.2 的“行/字节界限 → continuation 或 partial”只实现了“界限”，没实现“续传/截断标记”，`fields` 过滤停留在 repository 内部 API。
- 影响：当前 CN A 股单表最大 ~40 期×~150 行 ≈ 6k 行 ≪ 20000，**现实不可达**，但契约半实现：一旦触发截断，响应仍可能标 `complete` 且无法续取。
- 建议：`_handle_statement` 透传 `truncated`/`continuation`（截断时强制 `partial`），或在请求契约中补 `fields`/`continuation`；至少写明上限与行为。

### W19-R3 — FF 把 CWP 的 `request_error` 误报为 `upstream_error` 且 `retryable=true`（severity: minor，blocking=false）
- 证据：`ff/scripts/ff_financial_statements.py:143-148`（任何非零子进程退出 → `code="upstream_error"`，丢弃子进程 stdout 里已有的 `request_error` envelope）；实跑：FF 输入 `from>to` → exit 2 正确，但 envelope `status=upstream_error`、`retryable=true`、`producer_exit_code=2`。
- 根因：`run_bounded_json` 的 `ChildFailed` 分支未解析子进程错误 envelope。
- 影响：调用方自己的错误被归因为上游故障并被标“可重试”，与 SKILL 状态表（`request_error`）不符；exit code 本身正确。
- 建议：exit 2 时读取子进程 stdout envelope，透传 `status=request_error/config_error`（保留 `producer_exit_code`），`retryable=false`；或 FF 侧先做 `period_end_from>to` 等确定性校验。

### W19-R4 — 顶层 `unavailable` 状态不可达，全表失败报 `partial`（severity: minor，blocking=false）
- 证据：`service.py:169-177` `_overall_status` 只会产出 complete/not_found/partial；实跑 wikiD 全表 `unavailable` → 顶层 `partial`（§2.2）。
- 根因：`_overall_status` 缺少“全部 unavailable → unavailable”分支。
- 影响：卡片 §3.2 的状态枚举中 `unavailable` 在响应顶层是死值；全站故障被 `partial` 掩盖（逐表仍诚实）。
- 建议：`all(unavailable)` 时顶层返回 `unavailable`，并补测试。

### W19-R5 — 被审 commit 之上存在未提交代码改动（severity: medium，**blocking=true**，流程/绑定）
- 证据：CWP 工区 `git status`：`M src/company_wiki/source_catalog/financial_statements/service.py`、`M tests/financial_statements/test_service_contracts.py`（新增 `_apply_identity_gap`/ambiguous candidates 语义 + 1 条新测试）；overlay 实跑 **92 passed**。
- 根因：作者在 `e583904d` 之后继续改代码但未提交，本次审查只能绑定 `e583904d`。
- 影响：违反 COMMON §4“绑定 reviewed_code_commit，之后只有文档 commit 可动 HEAD；再改被审代码须补审”。
- 建议：交接前将该改动作为新 commit 提交并**对差异补审**，或回退；handoff 中明确最终绑定 SHA。

### W19-R6 — 报告级字段名 `captured_at` 与卡片冻结清单的 `retrieved_at` 不一致（severity: low，blocking=false）
- 证据：卡片 §3.2 每报告字段清单含 `retrieved_at`；实现 `service.py:468-511` 输出 `captured_at`（响应顶层 `retrieved_at` 存在，`service.py:111`）。
- 建议：报告级增加 `retrieved_at` 别名或在 handoff/接口文档中记录该命名偏差（语义上 `captured_at` 更贴近卡片 §5“真实 capture 时点”，建议保留并补别名）。

### W19-R7 — balance_sheet 的 instant 语义无机器可读标记（severity: low，blocking=false）
- 证据：`schema.py:25-27` `period_kind CHECK IN ('annual','semi_annual','q1','q3')`，全包 grep 无 `instant`；`test_normalize.py::test_balance_sheet_period_kind_and_statement_semantics` 断言 balance sheet `period_kind=='semi_annual'`，注释称 instant 语义“live in the report contract（statement_type）”。
- 影响：`period_start` 全表恒 null，消费者只能靠 `statement_type=balance_sheet` 推断瞬时性；与卡片 §4.3“balance_sheet 用 instant”的字面要求不完全一致（未伪造期间，方向正确）。
- 建议：handoff 明确写出该编码约定，或增加 `value_basis= instant|duration` 字段（不动旧 CHECK 亦可）。

### W19-R8 — 无“从已提交 SourceRef 重放规范化”的入口（severity: low，blocking=false）
- 证据：`service.py:435` 先提交原件再 `page.normalized()`；规范化失败会抛到 `cli.py:171-176`（fatal exit 1），coverage 观察未记录 → 下次 `fetch_if_missing` 会**再次联网**（原件虽 dedup 不重复，但 HTTP 重来）；grep 全包仅 `--fixture-root` 回放（回放的是夹具根，不是 catalog 原件）。
- 影响：违反卡片 §2.1“原始页保存后规范化失败可从该 SourceRef 重放，不再联网”的字面要求；属可用性/成本问题，不产生错误数据。
- 建议：增加按 `source_id` 读已提交字节→normalize→publish 的重放入口（或至少在失败重试时优先从已提交原件读字节），并补一条“坏 payload 落原件后零网络重放”测试。

### W19-R9 — fixture 回放模式 `response_bytes` 恒为 0（severity: low，blocking=false，测试基础设施）
- 证据：实跑三次响应 `usage.response_bytes=0` 而 `http_requests=15`；复现：`BudgetedHTTPTransport(MockTransport(handler))` + `response.content` 读取 → `budget.response_bytes_used=0`（httpx 对 `content=` 构造的响应短路 `read()`，不经过被替换的计量流）。生产路径（真实 `HTTPTransport` 流式读取）会计量。
- 影响：离线收据无法佐证字节计量与 `max_bytes` 预算执行；若交接文档把离线 `response_bytes=0` 当真实字节即为不实。
- 建议：回放 transport 自行计量并写入 budget（或文档明确“离线模式字节不计量，字节账仅生产有效”），交接中不得引用离线 `response_bytes` 作为真实字节证据。

### 观察项（非 finding）
- PIT 同日 `as_of` 因 `captured_at`（datetime 字符串）与 `as_of_date`（date 字符串）字面比较被判为晚于 as_of → `pit_verified=false`；方向保守（只可能少认、不会多认），可接受，建议注释说明。
- 中途 `count_changed`/`provider_error` 时已抓页面被整体丢弃（`service.py:231-243` 只 persist 非 provider_error 分支）：保守且状态诚实，代价是重复抓取；`count_changed` 页本身不入库（provider 在 append 前 return，`sina_provider.py:246-253`）。
- coverage 响应只暴露 advertised+selected（`observed_periods` 字段实为范围内选中数），卡片“advertised/observed/selected 三个数”只落库两个语义，建议文档化。
- capture 份数：卡面写 18 份 gzip，实际 `capture/` 有 19 份（175,846B vs 文档 175,785B，差一份 61B 终止页）；仅文档计数漂移，SHA 全部可验。

## 4. 对照施工卡逐节核查（代码层）

- **硬编码**：`grep 中微/688012/000333/2016-12-31/2026-06-30` 在 `src/company_wiki/source_catalog/financial_statements/**` 与 `ff/scripts/*.py` **零命中**（仅测试/夹具/SKILL 示例出现）；端点、交易所前缀映射、type 参数表均为数据驱动。
- **三表/单位/期间/Decimal**：三表独立结果；`value_decimal` SQLite 全 TEXT/null（实测 `typeof` 分布 text=4049/null=5680，无 REAL）；`UNIT_EVIDENCE` 仅 EPS→`CNY/share, scale=1`，`provider_precision`(f2/ps4) 单列不冒充单位；`BIZTOTINCO` 与 `BIZINCO` 保留为独立行；非法数值保留 raw + `non_numeric` + `invalid_numeric_value`（单测 `test_invalid_numeric_keeps_raw_and_flags`）；null/empty/0/group 分类齐全（DDL CHECK 五值）。
- **PIT 诚实性**：见 §2.2（过去 as-of 拒绝冒充；`point_in_time` 未验即 `historical_asof_unverifiable`，不升门禁）。
- **迁移链唯一 owner**：`models.CATALOG_SCHEMA_VERSION=1.3.0` + `store._DDL += FINANCIAL_STATEMENTS_DDL`（DDL 文本唯一 owner 在 `financial_statements/schema.py`）；`_UPGRADEABLE={1.0.0,1.1.0,1.2.0}`，未知未来版本 fail-closed（单测 + 旧迁移消费者 26 passed）；WAL 并发双初始化补丁为窄接缝必要增量；查询路径 `mode=ro + PRAGMA query_only`，无库返回 named gap（实跑 §2.2 证实零建库）。
- **canonical writer**：新增 `ThirdPartyDatasetOriginal` + `import_third_party_dataset_staged`，复用唯一 `_commit_staged`/dedup/SourceRef；拒绝 `provider=="official"`（单测）；`document_kind=financial_statement_dataset` 映射 `SourceType.OTHER` 不伪造财年；无第二套 writer；`git diff` 显示窄接缝改动仅 4 文件（store/models/canonical_writer/document_kinds）+ 1 个旧契约测试的版本号跟常量（未删断言）。
- **幂等/预算/边界**：同内容刷新零新增版本/原件（实跑）；`provider_update_time` 不入 `business_identity`（`normalize.py:168-197`，单测）；单一 `AcquisitionBudget` 跨页跨表共享（单测 `test_one_budget_shared_across_all_pages` + 实跑 15 请求记账）；`max_pages=64` 上限、重复页/无进展/count 变化/403/429/500/预算停止均有命名终止；无隐藏重试（provider 无 retry 分支）。
- **FF 薄客户端**：只 import `ff_configuration.load_connection_root` 与 `ff_process_transport.run_bounded_json`，**无第二套子进程/配置实现**；FF 与 CWP 各自校验请求（FF 校验形状，CWP 是唯一语义 owner）；SKILL.md 新增“原件 vs 三表数值”路由表 + 可直接执行的 `fetch_statements` 示例 + partial/PIT 说明（我按该示例形状实跑成功）。
- **测试独立性**：本卡 91 条测试在被审 commit 导出副本独立运行全绿，测试不依赖作者日志；夹具 SHA 我另行独立核验。

## 5. 修复与复审要求

1. **W19-R1 必须根修**（覆盖范围状态 + 窄→宽回归测试），并复跑 `tests/financial_statements/` 与本报告 §2.1/§2.2 链路。
2. **W19-R5 必须处置**（提交补审或回退），更新 handoff 绑定 SHA。
3. W19-R2/R3/R4/R6/R7/R8/R9 建议在交接前修复或在 handoff“当前不足”中逐条声明。
4. 修复后由独立审查者对差异补审（COMMON §4）。

## 6. 临时产物与清理

- 全部实跑在 `%TEMP%\w19-indep-review\`（`cwp/`、`cwp_dirty/`、`ff/`、`roots/wiki*`、`roots/fixtures*`、`out/*.json`、`setup_roots.py`、`setup_wiki.py`、`check.py`）；**按环境纪律，报告落盘后该临时根整体删除**（`rm -rf %TEMP%\w19-indep-review`），可按 §2.1 的 `setup_roots.py` 说明一键重建复现。
- 未触碰生产目录 `Projects/company-wiki`，未在两个工区产生 commit（两仓 `git status` 仅剩作者原有 2 个未提交改动 + 本次新增 `delivery/w19/` 未跟踪目录）。
- 本报告写入 `delivery/w19/review.md`、`review.json`（不 commit）。
