# M8 候选池测试分层：独立设计审查

结论：**PASS，本次属于测试责任层修复，不是在已提供证据下掩盖生产排序缺陷。** 当前三层测试保留了原先有意义的完整候选排序合同，并把有限原文分析的真实性单独验证。无需为本节点增加预算、跨过 physical profile 边界或重构 candidate_count wire。

范围：只读审查 ROOT 新增/调整的 test_reading_production_selection.py 三个测试、对应生产接口与五份日志；未修改源码，未运行模型/收费任务，未重复 full 或20k测试。CodeGraph 先定位 finalize_selection、EvidenceCandidate 和 select_reading_evidence，再阅读确切实现。source-purpose 另作者修改不在本报告签收范围。

## 原失败为什么不能归给排序器

旧测试只替换 understand_units，提供20,000个原文单元、unit_profiles和package行；它没有把这些单元变成已经通过原生物理连续性、来源闭包、事实用途/支持用途评估的 EvidenceCandidate。真实 `_prose_reading_packages` / SourceOperatingSession 仍在运行，并共享有限 WorkBudget。ReadingPlan 的 priority 是分析意图，不是已经完成来源分析的证明。

既有只读日志支持这一责任区分：结构/连续性前沿到3,076处停止，16,924项blocked，末三原文profile仍为priority1；后续整体16M work在第1,052个fact附近耗尽，传给finalizer的实际候选只有1,051个。末三源单元尚未到达排序输入。不能要求最终排序器从未知、未准入材料中选出它们，也不能为满足旧断言把raw units或priority标签直接包装成已评估事实。

这不证明生产已具备“任何长文末尾重要内容都能召回”的能力。有限前沿的效率、公平性和真实长文召回仍是另一个生产问题；本调整没有把该限制改写为通过，也没有移除其partial/unknown责任。

## 当前三层测试是否保留合同

1. **64 source public-selector priority integration：合适。** 仍走真实native/source semantics、public selector、canonical EvidenceSpan与真实finalizer，仅DU计划/优先级由受控seam给定。保留最后三项必须入选、精确candidate/omission、partial和context紧凑断言；最终新增 admitted_count==64、withheld==0、无work_budget_exhausted，防止兼容层候选计数混入deferred IDs而真空满足“全部已评估”。这验证预算内priority传播，不宣称parser/DU本身正确地产生了这些priority。
2. **20,000 assessed typed frontier → real finalize_selection：合适。** 输入使用真实EvidenceCandidate类型与明确的support/value/priority metadata，声明在此层已经准入；生产finalizer、真实planner、原始ID/坐标、EvidenceSpan及默认selection工作界仍执行。末三入选、candidate_count=20,000、omitted=19,997、无selection-work stop与精确diagnostic总数，保留了原全池比较的核心回归。compact断言直接作用于selection_diagnostics；没有对默认None的reading_context做真空检查。
3. **128 source +真实1M work-stop：合适的受控失败路径。** 预算是测试显式收紧，并未增加生产16M界。实际source owner耗尽，assert partial/needs_review、coverage false、document-work diagnostic、admission尝试数<128、withheld>0及selected计数相等。这验证未完成工作不会声称全覆盖。它是128规模的预算不变量回归，不是20k source全链规模实测；20k前沿失败的三份现有诊断仍应保留为该尺度的观察证据。

## 计数与接口应如何解释

finalize_selection的candidate_count只针对传入候选，omission精确为输入减selected。public selector的历史candidate_count还会合并withheld.known_unit_ids；它不能单独充当“实际已准入候选”指标。本次测试已经显式使用selection_trace区分，不需要立即改wire。另须保持admission.count的确切语义：它是admitted_count+rejected_count，即已进入准入判断的次数，不等于typed candidate数量，也不能与withheld package数量直接相加当作唯一source-unit总量。

正确的测试接口就是现有finalize_selection + Sequence[EvidenceCandidate] + reading_metadata。更清楚的后续维护方式是提供一个名称明确的`assessed_candidate_frontier`测试构造器，校验unit IDs一一对应、required IDs闭合，并显式填写priority/value/support/context；不要再通过伪造DU complete字段来跨越source owner。若将来收紧内部类型，可以为reading_metadata增加TypedDict/dataclass，但不需要为本次测试引入新状态库或新public wire。真实source准入证明仍由public-selector integration测试负责，手工构造EvidenceCandidate本身不证明来源事实正确。

## 验证及边界

ROOT原三节点运行：**3 passed /17.84s**，m8-pool-split.log；此时20k frontier与128 work-stop已包含当前断言。新增64 admitted/withheld/work-stop断言后，ROOT仅复跑64节点：**1 passed /5.93s**，m8-pool-64.log。没有把分阶段结果写成一次新的全量命令。本审查者读取并核对这些日志、最终测试字节及生产层实现，没有再跑一次20k。最终ruff由ROOT整体流程负责；本报告不是M8 broad全域重新验收。

无新增阻塞发现。尤其本结论不签收真实20k source完整语义扫描，不保证所有重要末尾scope在固定预算内可被发现，不把旧candidate_count的混合口径解释成实际准入数，也不归因其他七个precision失败。

## 字节绑定

- `tests/unit/document_understanding_selection/test_reading_production_selection.py` raw `1975b24a2b077d73ea4ee67861c6640f58b38600f4bcff0037134775f5c95ff8` / LF `a90a32d4f0aad88a8cdb618815393f5caf8d56a43a7866c8d9f801f18eee1016`。
- `.planning/summary-quality-20261030/m8_large_pool_probe.log` raw `63a6780077b91f57da2d76d35b67c49480ec1c212040d1beabad1200088e54ed` / LF `fe98df937314a751b92ae137fc5b68af9818131b34ba2c6be46c7d9bf456f08d`。
- `.planning/summary-quality-20261030/m8_large_pool_stages.log` raw `acf5c6578c17ebbdc94ef906b5a620511c61d38fe1327a552b3b88391c458498` / LF `25b0dbb8a43e6c0700200507f7175a5d4dcfa5dcc934fcbb312cc7e3511f57e8`。
- `.planning/summary-quality-20261030/m8_large_pool_structure.log` raw `e56c3521a31b8475e49a072d2a04b60daa565a9ec3d931a6c9f82a1f204fd5d1` / LF `ace86799a096dacf1f2fd6a5d0ce99b1757c37c5f23fcc922112a742642b7868`。
- `.planning/summary-quality-20261030/m8-pool-split.log` raw `c76edd0c79670d473cfc8b9c673f3c77ff020e07b7d57ac84b0d8d4a2030e30a` / LF `be8cb3f41570429aafbfaf28bf2bb666540639cf67eb62c8e32cf9e3876d3fe0`。
- `.planning/summary-quality-20261030/m8-pool-64.log` raw `8b66a6e9faf0a6883f5eb45ae7ca2da42039c8393be6d62a4ad870fe5c4779f8` / LF `aaebe0ba2c77d3290eb4f472fded6228873ec49ace5dfb443a31a9d45cbb2ef8`。

最终三个测试节点行号：
- `test_actual_reading_profiles_preserve_important_late_scope_priority`：441。
- `test_large_assessed_candidate_frontier_keeps_all_three_important_late_scopes`：479。
- `test_unassessed_source_work_is_explicitly_partial`：514。
