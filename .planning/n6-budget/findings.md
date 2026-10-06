# N6-BUDGET Findings

准备时已绿基线58b74d0；准确背景、接口、source路径与真实点见INPUT_CARD。所有结论来自本线只读离线回放（tmp/ 脚本，不入库），0下载/LLM/费用。

## 1. 现状代码事实（只读）

- `narrative_finalize._deduplicate`：键 = sha256(空白折叠文本) + page_number + source_role，**同页才消**；同键保留 pdf_table_row 优先。跨章节同文重复完全保留。
- `narrative_budget.select_budget_items`：`len(items)<=limit` 快路原样返回；否则按 group_id 打包（成本=span数，整组原子），`_reserve` 保两个 reserved reason，`_page_queue` 每页先按 CATEGORY_ORDER 各类暂存一件，`_fill_round_robin` 用**静态页序**（页内最小类别、-最大分、页号）逐轮填充。
- 类别序 CATEGORY_ORDER：critical_risk < … < risk(7) < rationale < event(9) < positioning(10) < project(11) < industry(12) < other。`business_risk_or_constraint` 优先级1（高于 event 3、positioning 4、project 5、industry 6），因此高频泛化风险天然压过具体行业/项目/产品内容。
- Package 计数当前为：candidate_count = 去重后候选数、omitted = 去重后 - 入选 → 去重删掉的候选在计数里不可见。
- group_ids 由 neighbors/group_candidates 提供；pair 组 id 含 role，`_add_linked_questions` 加问题候选时**不**给 group_id；但 finalize 不校验混角色组，输入混组会原样透传 selection_group_id。

## 2. 真实回放（samples.json 注册原件，只读）

对 S01-S08 抓取 finalize_selection 输入（候选、group_ids、route、golden），离线复算基线：selected/duplicates 与 report-main-2026-10-06 完全一致（48 duplicates、required 11/28 + S09 的 1/5 = 12/33），证明回放保真。

| 样本 | 候选入 | 基线去重后 | 页数(候选) | limit | 选中 | 选中重复 | required | 最大类别占比 |
|---|---|---|---|---|---|---|---|---|
| S01 | 182 | 182 | 38 | 96 | 96 | 1 | 1/5 | event 0.54 |
| S02 | 105 | 105 | 28 | 96 | 96 | 4 | 1/4 | event 0.78 |
| S04 | 417 | 416 | 40 | 160 | 160 | 5 | 1/3 | event 0.91 |
| S05 | 875 | 845 | 91 | 160 | 160(34页) | 24 | 2/3 | event 0.70 |
| S06 | 194 | 183 | 46 | 160 | 160 | 14 | 0/4 | event 0.44 |

- 跨页同文候选：S05 **157 组**、S06 20 组、S01 1 组；S05 同页重复 30、S06 12。S05 典型为第3页（提示章节）与160-163页（正文）、128与146页整段重复；S06 为 7↔43、197↔203 等。
- 诊断的5个漏点均已入候选但未选：S01 G02（p40 单件 event）、S01 G05（p75 21件 industry 大组）、S05 G03（p101 project 组成本22）、S06 G02/G03（p43 组成本8）。
- S06 去重后候选 162 ≤ 160 附近，预算立刻松绑；S05 685、S01 181 仍需选材。

## 3. 离线方案对比（同一抓取数据）

| 方案 | required(28点) | 选中重复 | 说明 |
|---|---|---|---|
| 基线 | 11 | 48 | 现状 |
| 仅同签名整组去重 | 11 | 27 | 不够：S06 的包含式重复没消 |
| **整组包含式去重** | **12** | **5** | 丢弃“内容被另一组完全包含”的组，无唯一信息丢失 |
| 整组包含 + 类别软配额轮转 | **12** | **2** | S04 最大类别占比 0.91→0.35、S05 0.70→0.41 |
| 成员级跨组去重（更激进） | 11 | 0 | 会拆组上下文，S05 丢1个 required，不采用 |

包含式去重的取舍已验证：按坐标数值（非 locator 字符串）选 canonical，S05 p3 的摘要副本得以保留；若按 locator 字典序会误留 p161 而丢 p3。

## 4. 选定实现（写集内）

1. `n6_budget_dedup.py`：角色类分组（statement/question 不共用 group_id）→ 组内同文同角色折叠（table 优先）→ 组间**签名包含**判定（大签名先入，被包含者整组丢弃，签名不等且互不包含则保守保留）；返回 kept + 有效 group_ids + drops（reason/locator/被保留者）。归一化 = 去空白 + 表格竖线 + casefold（与基准 duplicate 定义一致）。
2. `narrative_budget.py`：保留 fast path、`_reserve`、页级轮转结构（每页每轮至多一件，保证跨页覆盖，旧T1依赖），把静态页序换成动态 offer 序 `(已达配额, 类别已选span数, 类别序, priority, cost, key, 页号)`；配额 = `max(1, ceil(limit/活跃类别数))` span 数，**软**配额（超过只降序不剔除，不欠配）。新增 `budget_diagnostics`（超限组 `group_exceeds_limit`、预算满 `budget_full`）。
3. `narrative_finalize.py`：用新 dedup；candidate_count = 进入 finalize 的候选数（去重前），omitted = candidate_count - 入选（含去重与预算两部分），status 仍由 omitted/coverage/errors 推出。签名、source_id/sha256、locator、排序不变。

## 5. 约束核对

- 不改 narrative_evidence/document/routing/candidates/context/group_candidates/neighbors/pdf_groups、旧测试、benchmark/golden/report、配置/原件/数据库、CI、外仓。
- 预算/去重纯内存：不读磁盘、不调模型（测试用 open/socket 硬失败证明）。
- 旧断言 `omitted == candidate_count - selected` 与 status=selected 的三条测试输入无重复文本，预期不冲突；若冲突按卡列给MAIN。

## 6. 落地实现与收口实测（2026-10-06）

实现细节（与第4节一致，最终形态）：
- `n6_budget_dedup.deduplicate_candidates(candidates, group_ids) -> DedupResult(candidates, group_ids, drops)`：
  1) 同 unit_id 只留最丰富记录（分数高者，reason=`same_unit_repeat`）；
  2) 按**输出组id**分桶（输入组同时含 statement 与 question 时才拆成 `<gid>:statement` / `<gid>:question`，同质组原样保留）；
  3) 组内同 (归一化文本, role) 折叠，表格行优先（`intra_group_repeat`）；
  4) 组间按签名（排序后的 (归一化文本, role) 集合）做大者先入、被包含者整组丢弃（`duplicate_event_group`/`contained_group`），互不包含则保守保留；
  5) drops 按 (reason, locator, unit_id) 稳定排序，均带 locator + text_sha256 + kept_unit_id 配对。
- `narrative_budget._plan(items, limit)`：校验 limit/唯一 id → `len(items)<=limit` 快路 → `_reserve` 原样 → 每轮每页动态出最优件，offer 序 `(超过类别配额, 类别序, priority, -cost, bundle_key, 数值页序)`；
  配额 `fair_share = ceil(limit/活跃类别数)`，且仅当 `limit >= 2*类别数` 才启用（小预算完全沿用既有优先级+按页轮转，避免旧断言被公平序推翻）。`select_budget_items` 与 `budget_diagnostics` 共用 `_plan`，诊断原因只有 `group_exceeds_limit`（成本>limit，永远放不下）与 `budget_full`。
- `finalize_selection`：`candidate_count=len(输入候选)`、`omitted=candidate_count-入选`（含去重与预算两部分，不再把去重删项藏掉），status 仍由 `omitted/coverage/errors` 推出。

收口实测（同一批只读真实候选，baseline=旧算法回放，n6=本次实现）：

| 样本 | 选中/limit baseline→n6 | required | 选中重复 | 最大类别占比 |
|---|---|---|---|---|
| S01 | 96/96 → 96/96 | 1→1 | 1→0 | event 52→52 |
| S02 | 96/96 → 96/96 | 1→1 | 4→0 | event 75→75 |
| S04 | 160/160 → 160/160 | 1→1 | 5→1 | event **146→76** |
| S05 | 160/160 → 160/160 | 2→2 | **24→1** | event **114→88** |
| S06 | 160/160 → 159/160 | **0→1** | **14→0** | event 68→72 |
| S03/S07/S08 | 不受预算约束，完全一致 | 3/3/0 | 0 | 不变 |
| **合计(28点)** | — | **11→12** | **48→2** | noise 1→1 |

S06 少 1 个 span 是某个组放不下被整组舍弃（诊断 `budget_full`），属“超大组完整舍弃”预期行为。

## 7. 测试与红线

- RED（旧行为桩）：`13 failed, 19 passed, 1.60s`；GREEN：`32 passed, 1.57s`。
- 旧测试：`tests/unit/test_narrative_evidence.py + test_narrative_selection_architecture.py` `121 passed`；`tests/unit -k narrative` `584 passed`；预算/去重相关短测 `122 passed`。
- 唯一失败 `tests/integration/test_s5_narrative_evidence_view.py::test_real_transcript_search_lookup_and_directory_restoration`：读 `../earnings-transcripts/...` 外部原件（相对 source 仓的 sibling 目录），本 lane worktree 无该目录，失败于第245行 `original.read_bytes()`，先于任何选择代码，属环境依赖的既有失败。
- `python -m ruff check` 覆盖本线全部 src 与测试文件：全绿。
- 无 golden/threshold/公共合同/selector 版本改动；原件、配置、数据库、CI 未触碰；`tmp/` 下仅本线开发脚本与回放抓取（gitignored）。
