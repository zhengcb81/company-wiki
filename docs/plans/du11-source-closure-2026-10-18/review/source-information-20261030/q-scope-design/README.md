# Q1–Q3：闭合 QA 支持范围的最小接线审查

2026-10-30；主线参数/因果提交 `69c9b178` 已通过，ROOT 告知精确 CI40984342776 success、PWF33d2b91f已推。本文件是下一节点只读设计，不签实现、金标或全流程通过。总目标 active、未完成。

已读 canonical CURRENT_STATUS/task_plan 和 `review/source-information-20261029/C_NEXT_IMPLEMENTATION.md`。最初按简称读 C_NEXT.md 路径不存在，随后采用 canonical 文件指向的实际路径；未新建竞争 PWF。只写本自有目录，不改产品/测试/计划、原件、SDK、供应商或作者工区。

## 当前公共链观察

仅跑一次中性 `select_narrative_evidence → build_summary_task_plan → source_cards → source_task_admission`，无模型/下载/PDF读取。一个问题下有两条独立经营回答、纯财务结果和单独感谢，当前全部四条回答成为 **一个 admitted/support SourceCard**，问题为 context。见 probe.json。这确认问题已到实际任务边界，不能只调整展示或词法打分。

## 推荐接线点与责任

**保持 orchestration 的原 QA parent，不在那里做业务资格或强拆。** 它目前只知道结构关联；它的 `[anchors, required]` 是兼容默认范围，不是最终语义闭包。

在 `narrative_reading._candidates` 中创建现有 `SourceOperatingSession(...)` 后，进入 `for index, package in enumerate(budget_packages)` 的 reference 阶段之前，调用一个小的同 session QA 闭包服务。建议独立 `source_catalog/narrative_qa_scopes.py`，由 `_candidates` 单次调用；这里的服务名/返回类型是设计建议，尚不存在。

其纯内存输入为：原 packages、budget_packages、同一 session、original_units/material units、origins/original_members、structure/observation 的 QA 绑定、同一 work_budget。返回两套**同序且一一对应**的新 packages（原 ID 域）/budget_packages（material ID 域）及既有格式的 deferred 诊断。QA 无 carrier，两个域对它相同；非 QA 包原样通过。

位置必须在任何 `deferred_packages/extra_context/original_extra/reference_support` 的 package-index 内容积累之前。当前这几项在 session 前仅初始化为空，适合此处一次扩展；扩展后才进入现有按 index 的循环，不在循环中途 resplit，避免把另一包的依赖/失败贴错。

### 准确的准备顺序

1. **建立有界 QA 来源序列。** 消费已由结构/适配器确定的实际 source_id、QA parent、answer anchors 和 question/context IDs；按当前原始顺序建立索引。问题永远不是 answer predecessor；另一问答/来源/角色、显式 unread 或错位原生片段终止序列。不要以相同文本或相同 qa_group_id 字符串重新认定来源，也不要重读原件/重复做 SHA 身份校验。
2. **先固定含义依赖的 predecessor 窗口，再问 session。** 现 `build_antecedent_windows` 只接 prose IDs，scope 不含 QA parent；PDF table fragments 往往没有 paragraph_index，直接复用 `_adjacent` 也会拒绝。因此不能只把 qa_exchange 加到 `_REFERENCE_KINDS`。复用已有 window/envelope 上限及停止语义，为同 QA 的真实答案序列准备 predecessor IDs 与 complete/stop_reason，再填入该 session 的 QA antecedents；不跨问题。可以将有界窗口的公共循环抽为私有共享实现，保留 prose 原有 physical 验证；不全局放松 `_adjacent`。
3. **复用 reference 及 pair 语义。** 对答案种子调用现 `session.reference`：unique/collective 保留真实 declaration/member/required IDs；`reference_kind=causal_result` 的实际两端进 support，普通产品指代声明按既有用途进入必要 context。missing/ambiguous/partial 不变成一个较小 complete 答案；保留可读范围和明确 partial 诊断。
4. **建立必要的局部依赖。** 用同 session 的 relation/argument/qualifier 缓存得到受限对象、后置否定、真实前提等必需边。内在限定形成 support 闭包；可选经营相关性只作直接 context，不做无限传递。保留现 `local_qualification_dependencies` 与 `local_operating_context_dependencies` 的区别。
5. **形成候选闭合视图。** 可以每个 answer original 作为临时种子，但不是最终 `[[uid]]`：先合并原生未结束片段及语义必要的限制/因果/指代依赖。只有证明互不依赖的自足断言才分开。尚未证明独立的相关片段保守保留原必要范围并标 partial，不删除限定来追求更小卡片。未知制造仍是 relevant/unresolved，不变 qualified/support。
6. **一次投影 package/citation/cost。** 对每个闭合视图生成稳定子 package：member=该视图实际 support 与必要 context，anchor=该视图答案，required=真实问题/指代/前提等，citation_support_views=同一闭合 support。保留原 parent 的 reading profile/priority/completeness/诊断；parent orphan partial 不能被子范围洗成成功。去重按原始 ID 范围与用途，不按文本。然后整体替换 packages/budget_packages，才继续现有 reference/local dependency/graph/admission 路径。

服务可复用已算依赖，避免后续再扫 QA 同对；非 QA 的原逻辑继续。若后续通用 reference 阶段仍处理这些包，使用同 session 已冻结的 QA 窗口及 cache，不再重新推断或改边界。

## 依赖 matcher 的抽取边界：不能伪造物理证明

`SourceOperatingSession.local_qualification_dependencies` 目前只消费 `basis=source_body_adjacency`；仅“属于同一 QA”不等于这一物理证明。`local_operating_context_dependencies` 还显式要求同 page/section 等。**不能构造假的 source_body_adjacency，也不能让所有非物理输入通过旧 physical validator。**

最小改动是从原 method 抽取现有“已验证两源范围的受限对象/关系/模态匹配”私有 matcher，仍由同一 SourceOperatingSession 持缓存和预算：

- 旧 physical 入口保留全部 source/role/page/section/range 检查，再调用 matcher，行为不变。
- QA 闭包服务先消费已存在的来源 QA sequence/record 关联，验证当前 pair 属于同一实际回答、顺序和原生范围后，以不同的内部来源依据调用同一个 matcher；它没有资格生成 physical/source-proof wire。
- PDF 真正连续 cell fragments 可以消费现有 cell SHA、fragment start/end 与成员字节范围，但“不带这些字段”不自动获得物理证明。JSON 用真实记录/字段的来源顺序；不是把 ordinal 当 PDF 坐标。
- 两种依据只说明该局部 pair 可以一起解释；是否存在限制/主语同一性/因果仍归现有语义 matcher。不要以“同 QA+相邻”直接加入 support 传递边。
- `native_speaker_turn` 的 backward-plan 特例不能通过捏造 turn metadata 套用到所有 QA。若要支持同一种后置限定，把它的语义识别抽成同 matcher，分别由真实 turn 或真实 QA sequence 提供局部范围。

这不是新增 provider/路由或第二个分类器；不在 helper 里复制产品、财务、计划/否定词库。必要原生边不完备时诚实 partial，不能让语义关联冒充几何证据。

## Session/cache、projection 的关键不变量

1. 同一工作预算；先计费再建索引/闭包，不复制整个未读尾部。窗口/envelope/任务/费用上限不抬高。
2. **含义作用域先冻结，assessment 后发生。** 当前 `facts/results` 按 owner 缓存，而 `_candidates` 后面还会设置 `session.contexts`。新服务不能先 fact(owner)，再改变该 owner 的语义 context 并期待自动重算。为闭合 `(support原IDs, meaning-context原IDs)` 注册独立分析 owner，或一次性固定其 context 后再读取；不改原 unit 的另一 owner。
3. 同 support 但不同实际含义 context 不能共用证明；问题/主持人仅 model context，不能进入 NP/actor donation。复用 `scope_use` 的“独立 source-support owner，不重写 unit ownership”方式，必要时将注册这一小段提为 session 私有方法。
4. `scope_use`、`_admitted`、`_context` 消费同一已冻结 scope/use/value；不能一处用单句，另一处仍用全 QA。finance/greeting 独立范围只走它自己的 prepared 结果，不靠另一答案的 payload 获支持。
5. `_context` 现在会把 entry 的所有其他 IDs 当 context，`build_summary_task_plan.register` 要求 support/context 恰好 partition members。因此必须先缩紧 entry 自身 member/required；仅改 citation_support_views 会继续把全 QA 塞进每卡。
6. 子包的稳定标识绑定 parent+原 source/range/用途；native ID/locator/text不改。原段内含礼貌语不能靠字符串删除；这里移除的是独立无关片段的成员关系，不是改写原文。
7. 原文全文照常能展开。必要财务基期/因果端点可以成为该经营范围的 context/support，但不会再独立生成纯结果卡。没有被选择不等于没读取；未判断/截断不得写 skipped_no_narrative。
8. 新文件/语义路径进入现有 decision inventory/recipe 实际内容绑定；不新建许可、签收或 canary。缓存 recipe 应因 scope membership 变动正确失效。

## 10 个必要 RED（先短包，不跑全仓）

| # | 中性构造 | 必须观察的结果 |
|---|---|---|
| 1 | 同 QA：经营 A、纯财务、单独感谢、经营 B；交换财务前后，JSON/PDF 同义 | 两个独立经营 scopes；财务/感谢不进入 admitted support，也不作为无必要 context 重复携带；问句仅 context |
| 2 | 业务问题，只有财务/套话答案；另加陌生制造 NP 的完整否认 | 问题不能捐业务；陌生 NP 保 relevant/unresolved 可读，不由 QA 服务升级 qualified/support |
| 3 | 已完成设备开发；后片“但该设备尚未通过客户验收” | 原安全 PASS 必须保留：后置否定与先句同 support/必需闭包，不能裸发已完成/已商业化 |
| 4 | 实际同 cell/record 的未结束片段跨 unit 组成一个主语/宾语/谓词；缺一片或 fragment 错序 | 真连续片段先还原原范围；缺片/错序 partial；不通过猜拼/全文相似修复；locator保持 |
| 5 | 客户验证/审批条件在前后不同片，计划/尚未限定；另一个明确新主体自足句在后 | 必要条件不丢；独立新主体不继承前句模态/actor；无法证明断开则保留必要范围并 partial |
| 6 | 同回答已声明一组产品→该产品/该系列；声明缺失、两个竞争声明、只在问题里出现声明 | 唯一真实答案前文可闭合；缺失/歧义/问题前提不能被用作事实；另一 QA 也不得借入 |
| 7 | 产品业务收入下降；下一片 This decline was due to lower customer demand；对比期单独一片 | 复用因果 reference 保两端/比较基期，纯财务端点不独立成卡；次序/方向/基期不兼容则 unresolved/partial |
| 8 | 多条 QA 同 cell，或不同来源碰巧同 qa_group_id，或跨 speaker/章节/unread | 不跨记录、来源或断点闭包；不能伪造 source_body_adjacency；原 source/role不变 |
| 9 | 新 QA 子包夹在两个非 QA 包之间，后一个已有 reference/失效依赖；同字不同 locator | packages/budget index 对齐，诊断不串包；不按字符串合并原文；子包与 actual task member集合完全同scope |
| 10 | 0/小额度在窗口、closure中途耗尽；重复读取已准备scope；同support不同meaning-context | 及时停且 partial，不遍历未付尾部；已确认项保留；cache正确隔离且不重复扫描；实际member/cost不因某视图漏context变小 |

测试用真实 owner＋公共 `select → task plan → source cards/admission`，不以私有 helper 返回列表通过代签实际发送范围。#1 的“纯感谢独立 unit”与“业务同一 unit 内含感谢”要区分，后者不能删原文。#3 目前 all-answer 天然保留的控制要继续保留。

## 建议实施收束

先冻结上述短 RED/控制；实现同 session 的 QA sequence/闭包投影与必要 matcher 抽取；再做相关域一次检查和关键节点独审。使用已有 parsed 验证 source/tasks 的实际成员及 draft/发送范围，记录旧 20 spans 基线，不拿候选数下降或成本降低代签业务召回。真正摘要/恢复/RF采用另按主线后续验收，不在此节点冒领完成。

本设计本次仅新增上述一次公共链中性 probe；无全域测试、SDK、供应商 POST、下载或原件读取。ROOT 的正在推送/CI与外包工作均未触碰。
