# FC-906-d T2 Consumption Trace — 真实用户链消费 bound artifacts（2026-08-12）

> 从 revenue 用户入口（`scripts/source_preparation.py`）启动真实三仓链：
> revenue → filing-fetch client → company-wiki resolve → bundle → selector → RevenueSourceRecord。

## 请求（精确文档）

```json
{"schema_version":"1.1","company_query":"北方华创","market":"CN",
 "document_kind":"annual_report","fiscal_year":2025,"as_of_date":"2026-08-12"}
```

## RevenueSourceRecord / reuse_receipt（完整值）

| 字段 | 值 | 判定 |
|---|---|---|
| outcome | `reused_existing` | 真实复用 ✓ |
| bundle_status | `available` | 绑定可用 ✓ |
| **artifact_read** | `['normalized']` | **bound artifact 被消费 ✓（>0）** |
| producer_events（DAG closure） | `['consumer_analysis','markdown','sections','summary']` | 消费者需要但无 artifact 的角色（正确 DAG 语义，非盲全量） |
| parser_calls | `1` | journal 历史（apply 时 1 次真实 parser）；**本次消费 0 新增** |
| llm_calls | `0` | 消费不产生 LLM ✓ |
| download_calls | `0` | 消费不下载 ✓ |
| prompt_injection_status | `not_detected` | FC-905-b 门通过（策略 review receipt 生效）✓ |
| activation_epoch | `epoch-canary-2026-08-10` | policy snapshot ✓ |
| source_type / publisher | `regulatory_filing` | record 生成 ✓ |

## producer=0 证据（本次消费零副作用）

- producer_events journal：消费前 **33** → 消费后 **33**（两次独立消费运行均不变）。
- parser_calls=1 是 apply 时的历史计数（同一文档仅 1 次 parser 事件）；消费只读。
- download_events=0（envelope 事件，非推断）。

## 旧 unbound 不复用

- 星环科技 2024（legacy normalized，未重跑）：`query_source_bundle` → **valid_handles 空**，invalid reason=`artifact_schema_unsupported`（fail closed，绝不复用 unbound）✓。
- 紫金矿业（legacy 多期）→ resolve ambiguous（身份 fail-closed）✓。

## 前置修复（本 FC 包含，均已 accepted 前提交）

1. `a61dd35` producer 写 `schema_version` **列**（bundle 消费方读列；FC-906-a 只写了 metadata_json → 生产 bundle 全 unsupported）。+ 生产回填 33 行。
2. `6a76000` `bundle_for_resolution` 默认 allowed_roots 加 `derived_dir`（artifacts 所在；默认只含源根 → 全 path_outside_allowed_root）。
3. 生产 bundle 验证：北方华创 2025 → `valid_handles=['normalized']`（REUSABLE）。

## 边界说明

- 完整三进程 T1 自动化测试（temp 三根 fixture + spy）属 FC-1002（Phase 10 跨仓 E2E）——本 FC 提供真实 T2 trace + 两个契约测试（column、derived_root）。
