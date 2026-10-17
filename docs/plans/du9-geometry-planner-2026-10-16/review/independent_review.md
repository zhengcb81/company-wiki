# DU9 独立审查报告（实施者外 agent 执行）

审查者：`agent_5dd60502-f82e-49e2-b382-41d7cfc8b2c8`（general-purpose agent，非实施者）。
审查对象：提交 `61120fe14348f5ddfc7166ecdf925101383e915d`（实现）与其修复
`db126f24e32a8f6986d58049eb295b646c41a3d0`；基线 `bf160c8e3fd8b9620f6bbc891ba448fd5647e388`。
审查方式：自读全部代码与合同（construction_card/INTERFACES/AGENTS）、自建反例独立重算，
不复述作者报告；全程只读，仓库零残留（mtime/pyc 归因已核）。

## 最终判定

**final_status = PASS，unresolved_count = 0。**

两轮独立审查 + 一轮最终验证补跑（审查者亲自执行）：

- **首轮（对 61120fe1）：FAIL** — F1(P1) + F2/F3/F4/F5(P2)，见 findings。
- **复核（对 db126f24）：PASS（范围内）** — F1-F4 经审查者自建反例实证关闭，零新 finding；
  4 项 NOT_VERIFIED（全量测试/ruff/20k 计时/全流复跑）转最终验证轮。
- **最终验证补跑：全部实测符合** — du9 47 passed（1.21s）；四邻域 618 passed 17 skipped
  （17 skip 逐条确认为既有 env-gated 真实原件测试 CW_DU2_LAYOUT_REAL×6、DU_ROOT_BINDINGS×11，
  与本案无关）；ruff All checks passed；20k 窗口合成 plan 单 admit 142.4/157.5 ms
  （修复前基线 32.8 ms，线性同阶，无复杂度类变化；真实规模亚毫秒）；审查运行零仓库残留。

## findings（首轮，全部已关闭）

| id | severity | 位置 | cause | 状态 |
|----|----------|------|-------|------|
| F1 | P1 | planner.py `_require_plan`/`_require_state` | admission 路径只比对 state 内存储的 digest 字符串，不重推导内容：state 创建后篡改 plan（改 limits/quotas 保留旧 digest）可携旧 state 越过硬限放行（审查者实测 max_pages=2 被越至 3） | CLOSED @db126f24：每次 plan 使用（mint/admit/summarize）重推导 `canonical_digest(_plan_core(plan))`；三路径（digest 过期 / digest 重签 / 异 plan 绑定）全部 ValueError 拦截，审查者独立反例复验 |
| F2 | P2 | planner.py `_echo_keys`/`_decision` | decision 信封无界回显调用方对象（1MB page→1MB 信封；1MB key 截断前回显全量；巨列表先物化） | CLOSED @db126f24：`_echo_keys` islice 64 项 + str 截断 MAX_STRING + 非 str 类型名；`_echo_page` 非 int 只回显 `<type>`、>16 位 int 回显 `<int:Ndigits>`；实测 1MB page→`<str>` 357B、1MB key→4096 截断、10^18 页→`<int:19digits>`、合法页逐字回显 |
| F3 | P2 | planner.py `_intent_value` | rule 缺字段静默回退 default_intent，违反 INTERFACES"缺字段保守unknown"字面（激进 default 可无诊断地授予重型请求能力） | CLOSED @db126f24：不再回退 default_intent；缺字段/null→unknown+POLICY_INTENT_MISSING，非法值→unknown+POLICY_INTENT_INVALID；实测激进 default 不赋权、完整 policy 零 MISSING 噪声、fixture 配额无漂移。default_intent 现为 planner-inert，已在 docstring 声明并列入交接 known_limits 供 ROOT/POLICY 定夺 |
| F4 | P2 | planner.py `_require_plan` | 手工畸形 plan 触发 KeyError 而非 ValueError（profile/行字段未校验） | CLOSED @db126f24：补齐 core 字段/allocations 行字段/class_quota 行/reserved 类归属/state 内层校验；9 个畸形用例全 ValueError，partial plan 仍可 mint+replay |
| F5 | P2 | task_plan.md/progress.md | B/C 状态过期（实现落地后未回写 PWF） | CLOSED @交接 commit：B/C→done、progress 条目、handoff.md/json 与本报告一并落地（代码 SHA 未变，docs-only commit） |

零新 finding；白名单外零改动（`git diff bf160c8e..db126f24` 恰为 15 个白名单路径）。

## 审查者独立三方复核的手算基准（与实现一致）

- 类配额（max_pages=64，4 可请求类，base=16，借用序 (priority, 类名)）：
  administrative 6（释放 10）、context 16+10=26、operating 16、project 16，合计 64。
- 窗口配额（最大余数法，规范序）：w-admin 6、w-risk 11、w-notes 13、w-gov 2、w-mda 6、
  w-outlook 3、w-attach-op 7、w-proj-a 9、w-proj-parent 7、w-proj-b 0（透明嵌套）、w-toc cancelled。
- 全候选顺序流（96 页 + 页 71 重复 ACK）：admitted 64、deduplicated 1、exhausted 29、
  cancelled 3；spent {64,64}；class_spent {6,26,16,16}；not_arrived 0。
- 预算精确记账：fixture 全 plan 108 charge（41 prepay + 其余按遍历）；budget=107 → partial
  且零 allocations（收费先于大遍历，未做保持 unknown）；budget=108 → 完整且 digest 一致。
- RED 回执真实性：基线贪心独立重算 {context 49, admin 6, operating 9}, project 0,
  attach-op 0, 末页 64——与 receipts/red_first_fail.txt 逐字吻合；8ff47e28 时包不存在
  （`git grep geometry_intent bf160c8e` 为空），行号/版本全吻合。

## 测试真实性核查

断言加强无放宽（test_a 唯一改动是 `quotas` 从过滤比较改为全等含 0）；du9 测试内无
skip/xfail/吞异常/恒真断言；20 随机种子洗牌输入 digest+allocations 全同；sparse 物化
（`git sparse-checkout add docs/plans/document-understanding-2026-10-13`）解决的 2 个邻域
失败经审查者显式复跑确认为真实读取、非掩盖。

## 审查者最终可摘录结论段（verbatim）

> **independent_review: final_status = PASS, unresolved_count = 0**
> reviewer_agent_id：`agent_5dd60502-f82e-49e2-b382-41d7cfc8b2c8`（非实施者）；
> reviewed_commit：`db126f24`（基线 `61120fe1`，前序 `8ff47e28`）。
> 两轮独立审查：首轮（对 61120fe1）FAIL——F1（P1）admission 不复验 plan_digest，篡改 plan
> 可携旧 state 越限放行（实测 max_pages=2 被越至 3）；F2（P2）decision 回显无界（1MB 输入→1MB
> 信封）；F3（P2）缺字段静默继承 default_intent 违反"缺字段保守unknown"字面；F4（P2）畸形
> plan 抛 KeyError；F5（P2）PWF B/C 状态过期。全部根因修复于 `db126f24`（仅触碰白名单内 2
> 文件）。复核实证：F1 三路径全部 ValueError 拦截且合法 plan 不受影响；F2 全部回显有界；F3
> 激进 default 不再赋权、完整 policy 零 MISSING 噪声、fixture 配额无漂移；F4 九例全 ValueError
> 且 partial plan 可正常 mint/replay；零新 finding。最终验证：du9 47 passed、邻域 618 passed
> 17 skipped、ruff clean、20k 窗口 plan 单 admit 142.4/157.5 ms（线性，无复杂度类变化）、
> 审查运行零仓库残留。**结论：PASS，无未解决问题。**

## 审查者声明的残余边界（非 finding）

- 同时篡改 plan+digest 且改写 state.plan_digest 可继续——等于伪造调用方自有 in-call state；
  INTERFACES 明令不建签收/token 系统，此边界外于威胁模型。
- per-admit 成本为 O(plan+state)：20k 窗口合成极端 plan 约 142-158 ms/admit（真实规模亚毫秒）。
- `default_intent` 现被 planner 按合同字面忽略，建议 ROOT/POLICY 定稿其用途。
