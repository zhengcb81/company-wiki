# W19-SINA-STATEMENTS 独立终审报告（第 4 轮：R15 差异补审，最终版）

- 审查者：zcode 独立终审 agent（`mimo-v2.6-flash`，未参与实现；全部结论来自本人实跑）
- 审查日期：2026-10-25（第 4 轮，仅针对 `71e98ed0..43995453` 差异及 W19-R15 复验）
- **最终被审代码版本（binding）**：
  - company-wiki：**`43995453`**（基线链 243993d2→…→71e98ed0→43995453）
  - filing-fetch：**`d396fe7`**（第 3 轮起无变化）
- 第 1–3 轮报告原文保留在 git 历史（`ae317ca9`、`71e98ed0`、`43995453` 内本文件）；本文件为原地最终版。
- 执行环境：Windows / Python 3.13.9；`git archive 43995453` 导出到 `%TEMP%\w19-r15-recheck` 只读副本实跑。未修改源码、未写生产目录、未联网、未提交 commit；临时根于报告落盘后删除。

## 1. 最终结论

**PASS（四轮审结，无未决 finding）**

- 第 3 轮唯一遗留的 medium 非阻断项 **W19-R15 已根修并复验通过**；本轮差异（`service.py` `_needs_fetch` 12 行 + 1 条回归）语义正确、无回归面扩散。
- 全部历史 finding（R1–R15）处置见 §4 总表。
- 观察（非 finding）2 条新增于 §5，建议随 handoff 记录。

## 2. R15 差异审阅（71e98ed0..43995453）

差异内容：`service.py` `_needs_fetch` 两处——
1. **end_of_data 分支**：`want_to is None`（省略上界=想要最新）时，仅当已穷尽包络本身无上界（`fetched_to IS NULL`）才 0 HTTP 复用，否则 `return fetched_to is not None`（即有界包络 → 重抓）；原 `want_to is not None` 冗余门同步移除（语义不变）。
2. **period_boundary 分支**：`want_to is None` 一律重抓。

与我的 R15 建议（"want_to 为 None 且 fetched_to 有界时重抓一次核验，或 partial+gap"）一致；作者取"重抓一次，重抓后无界包络视为已穷尽"的复用妥协，兼顾卡面"重复相同请求 0 HTTP"要求，可接受（见 §5 观察 1 的固有姿态说明）。

回归 `TestR15UnboundedToDirection.test_omitted_to_refetches_newer_provider_period`（服务级，供应方新增 2026-09-30 → 省略 to 的请求重抓到 37 期、重复 0 HTTP）真实有效。

## 3. R15 独立复验（真实 CLI + 夹具突变，reviewer 自建根）

| 探针 | 结果（43995453） |
|---|---|
| A1 有界全量抓取（to=2026-06-30，end_of_data，`fetched_to=2026-06-30`） | complete 36 期，5 HTTP |
| A2 **有界重复请求（复用路径不受影响）** | ✅ **0 HTTP** |
| A3 省略 to + 供应方新增 2026-09-30（各页 report_count 一致调 37） | ✅ **重抓 5 HTTP → 37 期、last=2026-09-30、complete**；coverage 变为 `fetched_to=NULL` |
| A4 同一省略-to 请求重复 | ✅ **0 HTTP、37 期**（无界包络已穷尽） |
| B1 窄抓（from=2025, to=2026-06-30 → period_boundary 包络） | complete 6 期，1 HTTP |
| B2 from=2025 且省略 to | ✅ **重抓 1 HTTP**（`want_to is None → True`） |
| B3 B2 重复 | 仍 1 HTTP（见 §5 观察 2：from 有界 + to 无界的组合结构性无法 0 HTTP 缓存；诚实性无问题） |

CWP `pytest tests/financial_statements/ -q`（@43995453）：**107 passed**（64.9s），exit 0（第 3 轮 106 + R15 回归 1）。

## 4. 全部 finding 处置总表（四轮）

| ID | 来源轮 | severity | 最终状态 |
|---|---|---|---|
| R1 范围放宽谎报 complete | 1 | major/blocking | 修复（2/3 轮复验） |
| R2 行界截断静默/fields 未暴露 | 1 | medium | 修复（2 轮复验） |
| R3 FF 误标 upstream_error | 1 | minor | 修复（2 轮复验） |
| R4 顶层 unavailable 不可达 | 1 | minor | 修复（2 轮复验） |
| R5 被审 commit 外未提交改动 | 1 | medium/blocking | 修复（2 轮复验） |
| R6 retrieved_at 命名 | 1 | low | 修复 |
| R7 instant 语义 | 1 | low | 修复 |
| R8 无 SourceRef 重放入口 | 1 | low | 修复（3 轮加固） |
| R9 回放字节不计量 | 1 | low | 修复（字节精确相等） |
| R10 R1 残余变体（all_history/无 from、to 加宽） | 2 | major/blocking | 修复（3 轮原方法复验） |
| R11 replay 跨实体污染 | 2 | major/blocking | 修复（3 轮：versions+sidecar 双闸门 + fail-closed） |
| R12 continuation 契约不一致 | 2 | medium | 修复（3 轮复验） |
| R13 replay 旗标被静默忽略 | 2 | low | 修复 |
| R14 replay 信封形状 | 2 | low | 修复 |
| **R15 省略 period_end_to 不重抓 newer** | 3 | medium（非阻断） | **修复（本轮复验，§3 A1–A4）** |

## 5. 观察（非 finding，建议写入 handoff）

1. **无界包络的信任姿态**：省略 to 的请求在"无界已穷尽包络"（`fetched_to=NULL`）上 0 HTTP 复用——若供应方此后再发布新期间，需 refresh 或一次有界→无界的范围变化才会再核验。这是离线复用保证的固有妥协（与 refresh 覆盖更新的既定姿态一致），coverage 如实回显 `last_period_end`，可接受。
2. **from 有界 + to 无界的组合结构性无法 0 HTTP 缓存**（§3 B3）：该组合每次请求都重抓（stop_before 边界使包络永远停在 period_boundary）。诚实性无问题、字节经 dedup 不增长，仅效率边缘；如在意可在包络上记录"无界上沿已核验"时戳后放行复用。
3. FF 全量套件 5 个 fc803 e2e 失败**先于 W19 存在**（基线 e0d9642 同败，依赖生产 editable company_wiki，与 W19 无导入关系）——第 3 轮已对照验证。
4. `fetched_from/fetched_to` 仅进 CREATE TABLE：旧 ae317ca9 形状 1.3.0 库打开 fail-closed 报 `schema structure drift`（1.3.0 未发布，可接受；分支旧试验库需重建）。
5. continuation 服务端 token 实际不可自发产生（20000 行界对 CN 不可达）；如日后启用分页，建议 token 再绑定 security_id。

## 6. 最终绑定与收尾

- reviewed commits（最终）：**company-wiki `43995453` / filing-fetch `d396fe7`**。
- 四轮全程：零外网、零生产目录写入、零 commit、零源码修改；各轮临时根均已删除（本轮 `%TEMP%\w19-r15-recheck`）。
- 此后仅文档交接 commit 可动 HEAD；再改被审代码须差异补审（COMMON §4）。可以完成 handoff 提交与清理。
