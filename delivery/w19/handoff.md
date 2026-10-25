# W19-SINA-STATEMENTS 交接（handoff）

状态：**COMPLETE**（四轮独立审查通过，最终 verdict PASS，绑定 CWP code commit `43995453`（基线 `243993d2`）/ FF code commit `d396fe7`（基线 `e0d9642`），分支均为 `codex/w19-sina-statements-20261025`）

## 1. 交付物总览

| 仓 | 内容 |
|---|---|
| CWP | 新包 `src/company_wiki/source_catalog/financial_statements/`（contracts/normalize/sina_provider/schema/repository/service/cli）；窄接缝：`store.py`+`models.py`（schema 1.2.0→1.3.0，两长表+coverage 观察表进唯一 DDL 链）、`canonical_writer.py`（`ThirdPartyDatasetOriginal`+`import_third_party_dataset_staged` 复用唯一 `_commit_staged`）、`document_kinds.py`（登记 `financial_statement_dataset`→SourceType.OTHER）；测试 `tests/financial_statements/`（97项） |
| FF | `scripts/fetch_statements.py` + `scripts/ff_financial_statements.py`（复用 `ff_process_transport`/`ff_configuration`，无第二套实现）；SKILL.md 增加"要历史三表数值→fetch_statements；要原件→fetch_filing"路由与完整用法/partial/PIT 说明；测试 `tests/financial_statements/`（16项） |

产品文件 SHA256 绑定清单见 `handoff.json` 的 `independent_review.reviewed_file_sha256`。

## 2. ROOT 需处理的窄接缝（逐项）

1. `source_catalog/store.py`：`_UPGRADEABLE_SCHEMA_VERSIONS` 增加 `"1.2.0"`；`_DDL` 追加 `financial_statements.schema.FINANCIAL_STATEMENTS_DDL`；新增 `_enable_wal_with_contention_retry`（并发首初始化时 journal_mode WAL 有界重试，20×0.05s 退避）。语义不变：1.0/1.1 老升级链原样，未知版本仍 fail-closed。
2. `source_catalog/models.py`：`CATALOG_SCHEMA_VERSION` `"1.2.0"`→`"1.3.0"`。旧测试 `tests/contract/test_source_catalog_schema_migration.py` 中4处"当前版本"字面量改为引用常量（断言强度不变，仍验 fresh/1.0/1.1 全部到达当前版）。
3. `source_catalog/canonical_writer.py`：新增 `ThirdPartyDatasetOriginal` 数据类与 `import_third_party_dataset_staged`（拒绝 provider=official；staged 字节校验；走同一 `_commit_staged`/去重/provenance/registration）；`_destination_subdirectory` 增加 `financial_statement_dataset→financial_statements`；`_write_provenance` 增加第三方 collector 块。原 filing 单年语义零改动（旧 canonical_writer 13项契约测试全绿）。
4. `source_catalog/document_kinds.py`：`SIDECAR_KIND_MAP` 增加一行（不进 `PERIODIC_DOCUMENT_KINDS`）。

无其他既有行为改动；W16/W17/W18 及 ROOT narrative/document_understanding 路径零触碰。

## 3. 冻结接口（与卡 §3 一致）

- FF 命令：`python scripts/fetch_statements.py --config <company_wiki.json> [--request-file f] [--timeout-seconds N] [--pretty]`；stdin JSON 请求；信封恒在 stdout；退出码 0=业务信封(complete/partial/not_found/unavailable)、2=request/config（含CWP透传）、1=fatal。
- 请求 `financial-statements-request/1`：`company_query/market=CN/statements/report_types/period_end_from|to/all_history/knowledge_mode/as_of_date/intent/acquisition_limits` + 可选 `fields/continuation`。`intent=reuse_only` 零网络免限额；fetching 意图必须三限额；all_history 与 from 互斥。
- 响应 `financial-statements-response/1`：request 回显、一次识别的 `company_identity`、顶层/逐表 `status`、`coverage`（advertised/observed/pages/首尾期/terminal_reason）、逐表真实 `usage`、`reports[]`（`statement_version_id/period_end/period_kind/period_semantics/consolidation/currency/provider_publish_date/retrieved_at/pit_verified/source_ref/source_locator/report_hash/rows[]`）；行含 `provider_field/label/raw_value/value_decimal(精确十进制字符串)/value_kind(numeric|null|empty|non_numeric|group)/unit/scale(仅证据字段)/provider_precision/json_pointer/quality_flags`。逐表带 `continuation/truncated`（行界默认 20,000）。
- CWP 命令：`python -m company_wiki.source_catalog.financial_statements.cli --wiki-root <root> [--fixture-root <离线重放根>] [--replay-source <source_id>]`；识别在 CWP 内一次完成；reuse_only 路径零写（不建库不迁移）。
- 三类状态示例（真实收据见 progress.md）：complete（36/33/36 全历史）、partial（fzb 403 时另两表可读）、not_found（BJ no_data / 身份未解析 / 歧义带 candidates）、unavailable（provider_error）。

## 4. 验收证据摘要

- **真实 RED**（A节点，CWP eb4a0f05/FF be35dc2）：缺功能 collection error/CLI 失败，非夹具问题；18+1 份夹具 `.gz` 与解压字节双 SHA 全对 observations.json。
- **离线 E2E**（`tests/financial_statements/test_offline_e2e_full.py`）：真 CLI 子进程→冻结真实响应→canonical 原件→两表→公共 query；36/33/36 期、9,729 源行、锚点逐值+pointer 回读；重复请求 0 HTTP 零增长同版本；损坏原件 reader 拒绝；叙述链零产物；空间 10.26MB≤16MiB。
- **真实有界 E2E**（独占根，~25 公开请求，0费/0LLM）：中微三表（15 请求）+完整复用 0 HTTP；招行 fzb（2请求6期）；美的 SZ（2请求5期）；BJ 名称歧义透出 candidates、ticker 解歧后 no_data 诚实 gap。
- **官方原件逐值对照**（独立财务正确性）：ensure+StockInfoDL 真实下载中微2025年报 PDF（9,168,457B，0费）；四表锚点与官方 PDF 逐值一致（营业总收入/基本每股收益/货币资金/销售商品收现，含页码）。
- **空间**：原件+sidecar 3,578,895B + catalog.sqlite3 6,680,576B = 10.26MB；重复请求文件/版本/值行零增长（离线E2E断言）。
- **独立审查（四轮，同一独立 agent，全部真实实跑）**：R1 PASS_WITH_FIXES(9)→R2 PASS_WITH_FIXES(新增R10/R11 blocking+R12-R14)→R3 PASS(R10-R14复验，遗留R15 medium非阻断)→R4 PASS(R15差异补审fixed_verified)。**最终 verdict PASS，R1–R15 全部关闭，无未决 finding**；每轮报告原样保留于 `review.md`/`review.json`。
- **测试命令与结果**：
  - CWP：`python -m pytest tests/financial_statements/ -q` → **97 passed**；`python -m pytest tests/contract/test_source_catalog_schema_migration.py tests/contract/test_source_catalog_canonical_writer.py -q` → **20 passed**；`python -m ruff check <变更文件>` 通过。
  - FF：`python -m pytest tests/financial_statements/ -q` → **16 passed**；`python -m pytest tests/test_fetch_filing.py tests/financial_statements/ -q` → 127 passed/1 skipped；ruff 通过。

## 5. 独立审查轮次

- 首轮（reviewer: agent_2d649eaf，独立自建临时根实跑全链+自拟负例）：verdict `PASS_WITH_FIXES`，findings W19-R1..R9 + 4 observations，原报告保留于 `review.md`/`review.json`。
- 修复轮：R1 `_needs_fetch` 边界感知（end_of_data=双向穷尽不重抓；period_boundary 仅新范围更老才重抓；其余终止一律重抓）+回归；R2 fields/continuation 全链；R3 FF 状态透传+退出码；R4 顶层 unavailable；R6 retrieved_at；R7 period_semantics；R8 `replay_source`+CLI `--replay-source`（reader 验SHA、item_source 自动判型、幂等、零网络）；R9 惰性流真实计量；PIT 同日有效。
- 复审（同审查者对 ae317ca9/7d9bb85）：**结果见 review.json `recheck` 字段**。

## 6. 逐 finding 处置对照

| ID | 严重度 | 处置 | 证据 |
|---|---|---|---|
| R1 范围放宽谎报 complete | major/blocking | 根修 `_needs_fetch`；窄10期→宽36期确实5HTTP、同宽再请求0HTTP complete | `test_widened_range_after_narrow_fetch_actually_refetches` |
| R5 被审commit之上有未提交改动 | medium/blocking | 全部入 ae317ca9/7d9bb85；此后仅文档commit | git log |
| R2 行截断静默/无fields/continuation | medium | 契约+服务+复用路径+FF校验全链；响应带 continuation/truncated | `test_fields_filter_and_continuation_surface_in_response` |
| R3 FF 误标 upstream_error/retryable | minor | `_valid_error_envelope` 透传 + main 按状态退出 2/2/1 | `test_cwp_request_error_envelope_passes_through` 等2项 |
| R4 顶层 unavailable 不可达 | minor | `_overall_status` 增全 unavailable 分支 | `test_all_statements_unavailable_is_top_level_unavailable` |
| R6 captured_at 命名 | low | 响应字段改 `retrieved_at` | `_report_payload` |
| R7 instant 无机器标记 | low | 报告级 `period_semantics` | `_report_payload` |
| R8 无 SourceRef 重放入口 | low | `service.replay_source` + CLI `--replay-source`，幂等零网络 | `test_replay_source_republishes_offline_and_idempotently` |
| R9 fixture 计量为0 | low | `_LazyFixtureStream` 惰性流经 BudgetedHTTPTransport 计量 | cli.py；复审抽查 |
| 观察：PIT 同日保守拒绝 | - | 改按日期部分比较 | `test_point_in_time_same_day_capture_is_valid` |
| 观察：count_changed 丢已抓页 | - | 维持原语义：drift 页不入库（其前各页照常入库），handoff 记录 | provider 实现 |
| 观察：coverage 三数两语义 | - | advertised=provider report_count、observed=本地去重期数，SKILL 已述 | SKILL.md/响应 |
| 观察：18/19 夹具文档漂移 | - | BJ 探针后 capture 共19份；progress.md 已记 | observations.json |
| R10 T2b/T2c/T3b 范围边界残存变体 | major/blocking(第2轮) | coverage 表加 `fetched_from/fetched_to` 抓取包络；`_needs_fetch` 方向化（older 穷尽=NULL、newer 超包络即重抓） | test_t2b/t2c/t3b×2 |
| R11 replay 跨实体污染 | major/blocking(第2轮) | `_source_owner_security` 归属闸门（versions→sidecar 回退，fail-closed） | test_r11 + 审查者自构造零版本行页面复验 |
| R12 continuation 三缺陷 | medium(第2轮) | token 按 statement 作用域；reuse_only+continuation 双侧拒绝 | test_manual_continuation_does_not_blank_other_statements |
| R13/R14 replay CLI 忽略/信封缺形 | low(第2轮) | replay 分支前置；输出完整 statements 信封 | test_r13 CLI 子进程；test_r14 |
| R15 省略 to 不重抓 | medium(第3轮,非阻断) | want_to None 时仅无界已穷尽包络（fetched_to IS NULL）可 0 HTTP；boundary 一律重抓 | TestR15UnboundedToDirection（第4轮 fixed_verified） |

## 7. 当前不足（未声明实现的能力）

- **BJ/北交所**：该端点对 bj 前缀返回 data=null（真实探针）——named capability gap，provider 诚实 no_data；非覆盖承诺。
- **母公司口径**：样本中 rType 均为"合并期末"；母公司口径映射已实现（parse_consolidation）但无真实样本验证。
- **历史修订序列**：接口不提供历史修订链；publish_date 反例（2023年报 publish=2025-04-18）原样保留，不支持任意历史 as-of 回测（PIT 无证据即 `historical_asof_unverifiable`）。
- **单季/TTM 派生**：未实现（卡明确初版不要求）。
- **provider 范围**：仅 sina_finance/CN；HK/US 不适用本入口。
- 0 人工授权 JSON / 无新身份库 / 无 LLM / 费用恒 0。

## 8. 兼容与 ROOT 接入步骤

- 新旧组合互操作：CWP 1.3.0 库 + 旧 FF（fetch_filing 不读新表）不受影响；新 FF 指向 1.2.0 旧库时，采集入口首写触发 1.2→1.3 迁移，reuse_only 路径遇缺表返回 named gap（不建库）。已测：fresh/1.0/1.1/1.2 全部到 1.3.0 且旧数据保留、未知版本 fail-closed、并发双初始化。
- 建议 ROOT 接入顺序：CWP 原件/表/公共接口先发布 → FF fetch_statements/技能更新 → 定点安装同步 → 一次跨仓真实复用（可复用本 handoff §4 的中微三表命令）。
- RF 数值/模型采用由其责任层接手（本卡未实现 RF 历史基数算法，不与 W16 重复）。
- 真实 interface_requests：无（未发现需要改动对方仓既有公开契约的需求）。

## 9. 环境恢复收据（已完成）

- 两个真实测试根已删除并验证不存在：合计 66 文件 / 31,364,256 字节（`delivery/w19/cleanup_receipt.json`）。
- 生产 `config/source_catalog.yaml` sha256 `3d159a4e…` 全程未动（CWP tests 的 production_config_integrity 会话守卫在所有测试会话通过）；生产 catalog 与既有原件指纹未动。

## 10. 给 ROOT 的审查者观察（非 finding，详 review.md §5）

1. 无界-newer 包络的信任姿态：重复无界（省略 to）请求重证一次穷尽后即 0 HTTP（满足卡面"重复相同请求 0 HTTP"的合理妥协）。
2. from 有界 + to 无界的请求诚实但不可缓存（每次重抓 1 页）——效率边缘非正确性问题。
3. FF 全量套件中 5 个 fc803 e2e 失败先于 W19 存在（审查者在基线 e0d9642 复现同样失败）；作者跑的是选定聚焦子集。
4. `fetched_from/fetched_to` 仅在 CREATE TABLE 中：1.3.0 从未发布，但分支中期生成的旧试验库会 fail-closed（structure drift），需重建。
5. continuation token 目前按 statement 的 version 作用域；若将来启用多表分页导出，建议把 token 再绑上 security_id。
- 生产 `config/source_catalog.yaml`、生产 catalog、既有原件指纹全程未动（CWP tests/conftest 的 production_config_integrity 会话守卫在所有测试会话通过）。
