# W19-SINA-STATEMENTS 独立终审报告（第 3 轮：最终补审，针对差异）

- 审查者：zcode 独立终审 agent（`mimo-v2.6-flash`，未参与实现；全部结论来自本人实跑）
- 审查日期：2026-10-25（第 3 轮补审，范围 `ae317ca9..71e98ed0` 与 `7d9bb85..d396fe7` 的差异 + 上轮全部 blocking/medium finding 的原方法复验）
- **最终被审代码版本（binding）**：
  - company-wiki：**`71e98ed0`**（基线链 243993d2→…→71e98ed0）
  - filing-fetch：**`d396fe7`**（git log 最新；基线 e0d9642→…→d396fe7；作者提示的 `6a2db27` 不存在，以 HEAD 为准）
- 第 1/2 轮报告原文保留在 git 历史（`ae317ca9`、`71e98ed0` 内本文件）；本文件为原地最终版。
- 执行环境：Windows / Python 3.13.9；两仓 `git archive <commit>` 导出到 `%TEMP%\w19-final-recheck` 只读副本实跑（另导出 `7d9bb85`/`e0d9642` 做基线对照）。未修改源码、未写生产目录、未联网、未提交 commit；临时根于报告落盘后删除。

## 1. 最终结论

**PASS（第三轮补审通过；遗留 1 项 medium 非阻断残余 W19-R15，交 ROOT 集成前建议顺手修）**

- 第 2 轮全部 blocking（W19-R10、W19-R11）与 medium（W19-R12）均已根修并经我按**原方法**独立复验通过；R13/R14 亦复验通过。
- 新发现 1 项非阻断残余（W19-R15：请求省略 `period_end_to` 时 newer 方向仍不重抓），触发面窄（调用方须显式省略可选上界）、coverage 字段如实暴露旧上沿，定为 medium/非阻断。
- 两仓全量相关测试独立复跑通过（见 §5）；FF 全量套件存在 5 个 **先于 W19 就失败** 的 fc803 e2e（基线 e0d9642 同样失败，依赖生产 editable company_wiki，与 W19 差异无关，见 §6 观察）。

### 前两轮 finding 处置总表

| ID | 状态（第 3 轮复验） | 证据 |
|---|---|---|
| R1（1轮, blocking） | **修复**（经 R10 两轮收敛） | §2 T1/T4（2轮）+ §2 本轮 T2b/T2c/T3b |
| R2（1轮, medium） | **修复** | fields 双路径一致（2轮）；continuation 见 R12 |
| R3/R4/R6/R7（1轮） | **修复**（2轮已验，本轮代码 diff 无回归面） | 2 轮报告 |
| R5（1轮, blocking） | **修复** | 全部入 commit |
| R8（1轮） | **修复**（R11/R13/R14 收尾） | §3/§4 |
| R9（1轮） | **修复** | 2 轮报告（字节精确相等；本轮链路再证 `last_response_bytes=705179`） |
| R10（2轮, blocking） | **修复**（T2b/T2c/T3b 全复验通过；残余 → W19-R15） | §2 |
| R11（2轮, blocking） | **修复**（versions + sidecar 双路闸门 + fail-closed） | §3 |
| R12（2轮, medium） | **修复**（token 按表作用域；reuse_only+continuation 双侧拒绝） | §4 |
| R13（2轮, low） | **修复** | §4 |
| R14（2轮, low） | **修复** | §4 |

## 2. R10 复验（按第 2 轮原方法，真实 CLI + 夹具突变）

| 探针 | 第 2 轮结果 | 本轮（71e98ed0）结果 |
|---|---|---|
| T2b 窄抓(1 HTTP/6期/period_boundary) → 请求去掉 period_end_from | ❌ 0 HTTP、complete、10/36 | ✅ **重抓 5 HTTP → 36 期 complete**；重复请求 0 HTTP |
| T2c 窄抓 → `all_history=true` | ❌ 0 HTTP、complete、10/36 | ✅ **重抓 5 HTTP → 36 期 complete** |
| T3b 全量抓取(to=2026-06-30, end_of_data) → 夹具突变使 lrb 全历史新增 2026-09-30（report_count 各页一致调 37，避免 count_changed 干扰）→ 请求 to=2026-12-31 | ❌ 0 HTTP、complete、缺 2026-09-30 | ✅ **重抓 5 HTTP → 37 期、last=2026-09-30、complete**；**重复同请求 0 HTTP**（fetched_to 包络生效） |
| （对照）refresh / count_changed 守卫 | partial/count_changed 诚实 | 2 轮已验，回归未变 |

coverage 行实证新列：`fetched_from=NULL`（到达终止 null 页，older 方向穷尽）、`fetched_to=2026-06-30`（本次穷尽回答的上界）。`_needs_fetch`（service.py:376-434）方向化判定与上述行为一致。

## 3. R11 复验（归属闸门：versions 路径、sidecar 回退、fail-closed）

wikiX 根内含两家证券（中微 688012 + 美的 000333）：

| 步骤 | 结果 |
|---|---|
| 有版本行的中微 source + `company_query=美的集团` | ✅ **exit 2 `request_error`**："committed source belongs to a different security"；000333 名下版本数保持 **0** |
| 同实体重放（fetch 与 reuse_only intent 均试） | ✅ exit 0，new=0/reused=10 |
| **自构造“无版本行”页面**（reviewer 直接经 writer 导入 type4 页，0 版本行；sidecar 顶层 `security_id=688012`） | sidecar 回退路径成立 |
| 该无版本页 + `company_query=美的集团` | ✅ exit 2（sidecar 归属不符） |
| **篡改 sidecar 删除 security_id** + 正主中微 | ✅ exit 2 "cannot verify source ownership; refusing replay"（**fail-closed**） |
| 恢复 sidecar + 正主中微 | ✅ exit 0，reused=2（跨 type0/type4 同内容幂等复用） |
| 发布后再以美的重放 | ✅ exit 2（versions 路径接管），000333 版本数仍 **0** |

## 4. R12 / R13 / R14 复验

- **R12 token 作用域**：手工构造合法 token `fsv-…:5` 发三表请求 → income 正确续传（首报告 72 行、min ordinal=6），**balance 33 期、cash 36 期完整返回**（第 2 轮为 complete+0 报告）✅。
- **R12 reuse_only+continuation**：CWP CLI **exit 2** `request_error`（contracts.py:205-207）；FF `fetch_statements.py` **exit 2** `request_error`（ff_financial_statements.py:78-81）——不再静默丢弃 ✅。
- **R13**：`--replay-source` 已移到 reuse_only 分支之前：`--replay-source <id>` + `intent=reuse_only` → **exit 0**，真实执行重放（不再被忽略）✅。
- **R14**：replay 输出具备 `status/company_identity/statements[]/usage/retrieved_at` 完整 response 形状（statement 条目含 `replayed_source_id/new_version_ids/reused_version_ids`）✅。

## 5. 测试独立复跑（最终 commit 导出副本）

| 套件 | 结果 |
|---|---|
| CWP `pytest tests/financial_statements/ -q`（@71e98ed0） | **106 passed**（68.4s），exit 0 |
| FF `pytest tests/financial_statements/ -q`（@d396fe7） | **16 passed**，exit 0 |
| CWP 窄接缝旧消费者（schema_migration + canonical_writer） | **20 passed**（schema.py 变更后无回归） |
| FF 全量 `pytest tests/ -q`（-x 截断） | 590 passed / 17 skipped 后遇 fc803 失败（见 §6，**基线 e0d9642 同败**，与 W19 无关） |

## 6. 本轮 finding 与观察

### W19-R15 — 省略 `period_end_to` 时 newer 方向仍不重抓（severity: medium，blocking=false）
- 证据：`service.py` `_needs_fetch` end_of_data 分支的新器判定以 `want_to is not None` 为门槛——`want_to=None`（请求省略上界）时即使 `fetched_to` 有界也不重抓。实测（wikiR3，全量 end_of_data 后 + 新期夹具）：**请求去掉 period_end_to → 0 HTTP、complete、36 期、last=2026-06-30**，供应方此刻已有 2026-09-30（对照：显式 to=2026-12-31 会重抓并得 37 期）。
- 判级理由：可选上界的省略显式触发、coverage 如实回显 `last_period_end`/`terminal_reason`，且卡面冻结示例均带显式 `to`；与已修复的 `all_history`（文档钦定旗标）不同，故非阻断。
- 建议：`want_to is None 且 fetched_to is not None`（从未验证过开放上沿）时也重抓一次首页核验，或对该组合返回 partial + named gap；补一条省略 to 的回归。

### 观察（非 finding）
1. **FF 全量套件 5 个 fc803 e2e 失败先于 W19 存在**：`test_lt01/02/05/07/09` 在基线 `e0d9642` 与 `7d9bb85` 上同样失败（我逐一对照）；这些用例经 `tests/e2e_support/isolated_wiki.py` 真跑 `fetch_filing.py` 并 import 环境中 editable 的 company_wiki（=ROOT 生产树，已随 ROOT 演进），与 W19 差异（仅 `ff_financial_statements.py`）无导入关系。作者"FF 127 passed/1 skipped"对应其选定子集；建议 handoff 注明全量套件的既有失败与原因，避免 ROOT 验收时误归因。
2. **1.3.0 未发布期间的 DDL 内定型**：`financial_statement_coverage` 新增 `fetched_from/fetched_to` 仅进 CREATE TABLE。用旧 ae317ca9 形状的 1.3.0 库（我 DROP 两列模拟）打开会得到 `ValueError: source catalog schema structure drift`（store.py 结构闸门，exit 1 无信封）——fail-closed 且无静默损坏，因 1.3.0 从未发布、生产库 ≤1.2.0，可接受；建议 handoff 记一句"分支内旧 1.3.0 试验库需重建"。
3. replay 信封 statement 条目仍无 `coverage/knowledge_mode` 字段（属重放收据，可接受；如后续被外部消费再补）。
4. continuation 服务端仍不可自发产生（20000 行界对 CN 不可达）；token 跨公司复用在理论上仍可清空同名表（token 未绑定 security），因 token 死代码属性维持第 2 轮判级，不再另立 finding。

## 7. 修复与交接要求（最终）

1. W19-R15 建议 ROOT 接收前顺手修（一行判定 + 一条回归），或写入 handoff「当前不足」。
2. 观察 1（fc803 既有失败）与观察 2（旧 1.3.0 试验库）建议写入 handoff。
3. 绑定关系（最终）：reviewed commits = **CWP `71e98ed0` / FF `d396fe7`**；此后仅文档交接 commit 可动 HEAD，再改被审代码须差异补审（COMMON §4）。

## 8. 临时产物与清理

全部实跑在 `%TEMP%\w19-final-recheck\`（`cwp/`、`ff/`、`ff_7d9bb85/`、`ff_e0d9642/`、`roots/`、`out/`、`setup_roots.py`、`driver.py`）；报告落盘后整体删除。未触碰生产目录 `Projects/company-wiki`；两仓无任何 commit；本文件与 `review.json` 原地更新（作者随后以文档 commit 收尾）。
