# DU9-CWP-GEOMETRY-PLANNER 交接

交接方：实施 agent（本 PWF 作者）。验收方：ROOT。状态：READY（独立审查 PASS、
unresolved_count=0；结构化数据见 handoff.json，审查详情见 review/independent_review.md|json）。

## 交付物

`src/company_wiki/document_understanding/geometry_intent/`（新包，纯组件，独立 import，
未改顶层 `__init__`、未动白名单外任何文件）：

- `plan_geometry_requests(policy, windows, *, page_count, limits, work_budget)`
  → `du-geometry-plan/1`：按 demand class（operating/project/mixed/context/
  administrative/unknown）对 `limits.max_pages` 做公平配额 + 计划期借用（借用序
  (reading_priority, 类名)）+ 全局硬余额（类配额和 ≤ max_pages）；窗口配额按类内专属页
  最大余数法分摊（嵌套重复窗为透明窗 quota 0）；WorkBudget 耗尽 → 零 allocations 的
  partial plan（未做保持 unknown，收费先于大遍历）。
- `admit_geometry_request(plan, state, *, page, window_keys, tabular_evidence, remaining)`
  → `(decision, next_state)`：仅 observed_candidate 申请重活；absent=not_found 不消耗；
  unknown 不假称无表；同 (scope, page) 去重一次、重复 ACK 不重复扣、父文 scope 台账隔离；
  priority-1 行政（demand_class=administrative）任何 priority 都不自动触发 fine；
  调用方 remaining 只是额外闸门——state 计数才是权威（重复传 remaining=64 无法重开已花页）；
  原因分离：exhausted/cancelled/not_arrived(摘要)/not_found/unknown/deduplicated/rejected。
  每次使用重推导 plan 内容摘要（防篡改/损坏 replay），state 为纯 JSON 可序列化调用内值。
- `new_admission_state(plan)` / `summarize_admission_state(plan, state)`：初始 state 与
  因果运行摘要（not_arrived = 已预留未到达）。

## 测试与回执

- `tests/unit/du9_geometry_planner/`：47 tests（test_a 根因+冻结期望、test_b 反例集中
  回归、test_c E2E/重放/无IO证明）全绿；邻域 `document_understanding_{root,layout_hints,
  profiles,structure}` 618 passed 17 skipped（全部既有 env-gated）；ruff clean。
- 回执：`receipts/red_first_fail.txt`（首次 RED）、`receipts/final_test_log.txt`（最终
  集中日志 + cleanup git status）。
- 隔离：0 供应商调用、0 生产写入；fixture/生产配置 SHA+mtime 由 test_c 断言未变；
  审查 agent 全程只读零残留（mtime 归因见 review 报告）。

## 已知边界（真实限制，非缺陷）

1. 计划期借用：配额借用只在 plan 时确定性结算；admission 期不动态再借——窗口配额固定，
   节省内存页留在 not_arrived，不回流其他窗（换确定性；卡内"顺序到达与未来预留明确"语义）。
2. 透明嵌套窗（quota 0）需 ROOT 传全部覆盖 window_keys 才可通过其预留放行；只传透明窗键
   会得到 exhausted/window_quota_exhausted（诊断说明由覆盖窗预留）。
3. 行政 fine 抑制按 demand_class=administrative 对**所有** priority 生效（卡面只点名
   priority-1；实现更保守，少做重活）。
4. `default_intent` 字段现被 planner 按合同字面（缺字段保守 unknown）忽略，rule 级
   geometry_intent 必须完整；请 ROOT/POLICY 定稿该字段预期消费方。
5. per-admit 成本 O(plan+state)：2 万窗口合成极端 plan 实测 142-158 ms/admit（线性，
   修复前基线 32.8 ms）；真实规模（几十~几百窗口）亚毫秒。
6. 无原生书签时单遍 + 两页缓存不保证未来全局最优（诚实记录，未用无限缓存修复）。
7. 调用方自伪 state+plan+digest 超出威胁模型（合同明令不建签收/token 系统）。

## 未运行（不冒称）

深页真实 E2E（ROOT 独占原生导航/章节匹配/单 TextPage/生产 source）、find_tables 真实成本、
摘要质量——本卡只签纯请求规划组件。

## ROOT 接线方法

1. POLICY 卡产出 `du-geometry-policy/1`（rule_key 为规则规范内容稳定 SHA；每 rule 完整
   geometry_intent——缺字段按 unknown 处理并产生 POLICY_INTENT_MISSING 诊断）。
2. ROOT matcher 绑定 windows（window_key/scope_id/rule_key/physical_start/end/
   native_navigation_refs/navigation_status），保证同页事件传全部覆盖 keys、单事件不跨 scope。
3. `plan = plan_geometry_requests(policy, windows, page_count=…, limits={"max_pages","max_requests"},
   work_budget=ROOT 的 WorkBudget 实例)`——budget 不重置、不每页新建。
4. `state = new_admission_state(plan)`；每物理页观察事件调 `admit_geometry_request`，
   tabular_evidence 取 observed_candidate/absent/unknown；remaining 传 ROOT 剩余额度。
5. 中断恢复：JSON 序列化 plan+state 后原样继续（与一次完整运行逐 decision 等价，test_c 已证）。
6. 调用结束用 `summarize_admission_state` 取因果摘要（含 not_arrived）。
