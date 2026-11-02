# R7 CWP核心过度门禁审计（只读）

状态：**READ_ONLY_AUDIT_COMPLETE_ROOT_IMPLEMENTATION_PENDING**。基线`fa8ef38e`。本线不改代码、测试、Git/index、配置、原件、数据库、keys或主PWF，不跑source/模型/测试。ROOT已接管新观察器的300KB/16KB去除；本报告只审三个核心树的类似残留。

已对source_catalog 212、automation 61、document_understanding 77个Python文件做门禁/权限/阈值字面清扫（共350），详读关键入口、producer/consumer/异常流31文件及对应旧用例。使用CodeGraph status/context/callers定位；部分新重构symbol caller未解析，不能凭空caller推断退休。此为关键链静态审计，不冒称350文件逐行或运行验收。源码SHA清单见JSON。

结论：**默认路径逐材料人工授权、review签收、旧canary开关大体已退役；主要剩余是表示/缓存/局部能力被当成业务准入。** 以下按实施优先排序，不为凑数将正常身份/事实约束列成过度权限。

## R7-G1 / P1 — 正常资料被多层固定wire/诊断体积门否决

证据级别：`CONFIRMED_STATIC_CONTROL_FLOW`。本轮未运行产品/真实资料。

位置（均相对`src/company_wiki/`）：`automation/narrative_contracts.py:48-52,192-196,731-772,953-969,1175-1177,1189-1191,1338,1357,1472,1859,2146-2150`；`automation/narrative_select.py:243-247,312`；`automation/narrative_summarize.py:549-553`；`automation/narrative_verify.py:454-458`；`automation/narrative_transport_contracts.py:32-33,225`；`automation/narrative_transport.py:386-387,447-448,466-467`；`automation/narrative_evidence_view.py:132-133,158-159`。

触发：legitimate canonical selected material/summary or optional diagnostic tree crosses one independent fixed length/count/depth cap after source work succeeded。

实际后果：ContractSizeError/strict contract error -> RESULT_TOO_LARGE/INPUT_SCHEMA_INVALID or transport blocked; valid source bytes/results disappear from operation。

共因：representation and optional diagnostics treated as additional execution permission, independent from configured work/storage/model budget。

最小根修：remove fixed successful result/receipt serialization vetoes; stream writes, de-duplicate optional metadata; separate optional diagnostics schema from material support; retain strict ID/ref/type/finite-number and actual configured resource limits。

测试迁移：split test_select_handler_cap_and_path_leak_fail_with_zero_effect: oversized valid source now success unchanged; path/source-invalid still reject. Migrate reading_context oversized-only cases to full material preserved, optional trace compacted with counts/hash; hostile cyclic/nonfinite/malformed JSON remain explicit encoding diagnostics and do not invent support.。

## R7-G2 / P1 — 自动缓存候选损坏成为新任务全局停止条件

证据级别：`CONFIRMED_STATIC_CONTROL_FLOW`。本轮未运行产品/真实资料。

位置（均相对`src/company_wiki/`）：`automation/narrative_generation.py:535-579`；`automation/narrative_batch.py:1147-1195,1656-1684`。

触发：during fresh automatic reuse discovery, a matching derived artifact candidate has malformed metadata or invalid generated artifact; reader source remains independently valid。

实际后果：reading_candidate_manifest/read_reuse_pin exception -> BATCH_REUSE_ARTIFACT_INVALID and whole preflight fails before a replacement generation; refresh can still enter discovery when pointer.exists()。

共因：disposable cache observation has authority to deny source-owned regeneration; corrupt candidate and explicitly pinned immutable result share failure policy。

最小根修：automatic candidate discovery records corrupt/stale candidate diagnostic and continues next candidate; if none, perform one current source verification/selection and regenerate under actual existing budget. Explicit requested pin/same-run frozen binding and original-source hash failure still reject; do not silently reuse corrupt output or replay an uncertain paid reservation。

测试迁移：keep test_matching_artifact_metadata_corruption_is_an_error_not_spend_permission at strict candidate parser, but add discovery integration bad-first/good-next/no-good+valid-source fallback/explicit refresh; retain test_new_operation_rejects_changed_reused_original_before_new_fee, same-run pin/publication corruption and unknown-cost ledger controls。

## R7-G3 / P2 — 同unit一个未知语法子句可否决另一个独立已证资料子句

证据级别：`STATIC_SCOPE_RISK_REQUIRES_TARGETED_RED`。本轮未运行产品/真实资料。

位置（均相对`src/company_wiki/`）：`source_catalog/narrative_source_passage.py:337-353,379-386,424-436,487-495`；`source_catalog/narrative_reading_admission.py:117-118`；`source_catalog/narrative_reading.py:1213-1237,1271`。

触发：one prepared statement scope contains known independent source material and another clause with unavailable/scope_limit grammar; uncertainty return precedes existing independent support reuse。

实际后果：entire native unit passage assessment_complete=False/relevant=False, then admission false; partial source annotation may withhold usable independent clause with it。

共因：processing completeness and supported material availability aggregated into one per-unit bool instead of preserving independent local support scope。

最小根修：first add same-native-unit mixed control using existing prepared clause keys; retain independently supported subclause/context closure while deferring unknown clause and marking source partial; reuse prepared observations, no unknown -> fact promotion and no new state/permission system。

测试迁移：existing test_one_deferred_scope_does_not_stop_an_independent_healthy_scope covers two different units only; add same-unit known typed clause+missing-resource generic clause, inverse order, positive/negative condition attachment and shared context. Not executed in this read-only audit; do not claim public-selector reproduction.。

## R7-G4 / P2 — VerifiedContent上层再次整buffer SHA且再次查metadata

证据级别：`CONFIRMED_STATIC_DUPLICATE_WORK`。本轮未运行产品/真实资料。

位置（均相对`src/company_wiki/`）：`source_catalog/source_reader.py:585-608,680-724`；`source_catalog/resolver.py:363-464`；`automation/narrative_source_guard.py:45-86,89-110`；`automation/narrative_select.py:301-307`；`automation/narrative_verify.py:249-255`。

触发：public reader has just read/hashes actual bytes and returns same immutable VerifiedContent; handler guard recomputes sha256(opened.data), then describe_version queries same identity separately。

实际后果：source select and verify each pay redundant full-buffer digest plus duplicate metadata observation; old read-policy string is already diagnostic and is not needed as a second permission。

共因：consumer does not fully rely on lower verified-source port responsibility; defensive unit fakes encouraged repeated verification。

最小根修：retain exact per-operation real reader byte SHA/current state/root/path resolution once; thin upper checks compare requested ref/returned identity only; use existing open_described_version where source and metadata both needed. No long-lived cross-request trust cache; changed originals must still fail actual reader。

测试迁移：move wrong-byte/mtime/source-change tests to real reader boundary; handler tests retain wrong ref/ID/subject/metadata rejection and assert one reader hash/description per operation. Do not change as-of selection or event-number proof.。

## R7-G5 / P2 — 几何导航hint有多套任意固定天花板且整份丢弃

证据级别：`CONFIRMED_STATIC_ADVISORY_HARD_CEILING`。本轮未运行产品/真实资料。

位置（均相对`src/company_wiki/`）：`document_understanding/geometry_intent/reading.py:21-23,48-59,74-76,87-95,123,282-285`；`document_understanding/geometry_intent/contracts.py:49-52`；`document_understanding/geometry_intent/planner.py:876-881`。

触发：otherwise valid native outline >4096 rows / level>32 / title>4096, or explicit requested max_pages/max_requests>64 or >64 same-page window keys。

实际后果：valid hint set becomes empty/partial, caller limits silently clamped to64, page request rejected because key count not physical ambiguity; original shared WorkBudget already exists。

共因：optional navigation format bounds and local constants duplicate work/request allocation owner; these caps do not prevent native get_toc allocation (already occurred upstream)。

最小根修：consolidate processing under same WorkBudget + explicit request/page allocation; stream iterative stack and preserve independently valid navigation; remove silent clamp/additive hard ceilings. Keep malformed hierarchy/page destinations and physical ambiguity negative controls; do not guess page/ancestor when evidence truly absent。

测试迁移：migrate test_limits_cannot_raise_native_hard_ceiling/test_large_outline_bounded_before_iteration to explicit budget depletion and valid large/deep outline preserved; retain invalid parent jump/page order/shared-page conflicts. Do not simply delete all geometry validation.。

## 不应再误报为活动新门禁

- `SourceResolver(..., runtime_policy=None)`默认steady，不自动从rollout快照获得许可。`runtime_policy` schema1的epoch/cohort和activation journal只属显式历史兼容；schema2/无快照生产不依赖它。`register_canary`的CodeGraph调用只有历史contract tests。不要因文件/字符串仍在就重开canary迁移工程。
- `authorization.py`、`close_gap.py`已明确plan/policy hash/expiry不授予或拒绝执行，仅可选兼容对象缩窄目标和实际资源。`CloseGapTransaction`调用统一ensure，不再另设许可事务。可以以后删未用DTO噪声，但不是现在阻断主线的新增审批。
- `source_reader._current_review`缺失/存储错误均返回not_reviewed；prompt review只诊断。registry的human_errors为空；旧BLOCKED_HUMAN不新增人工状态。`PolicyConfig`默认network=False在通用底层仍在，但batch/CLI实际都显式True；当前非生产人工授权阻塞，不应宣称又要求用户许可。
- `source_processing_complete=False`本身不是全局不准摘要：健康其它unit仍留span/status=partial，summarizer有span便可处理；未知未处理不能伪装无业务或完整。只审G3同unit聚合过宽，不能把partial诊断一删了之。
- output-language observer超自身观察范围/缺依赖返回unavailable，summarizer只加needs_review，未阻断；模型确实翻译且判different才拒绝，属于原语言正确性，不是多余人工审查。

## 保留，但各自归一个owner

1. 原件不可丢；存储owner每次真正打开的字节SHA/ID/MIME/当前状态校验、同SHA备用位置、路径归属继续。G4去掉的是同buffer上层重复hash，不是采样hash或跨请求信任mtime。
2. 身份/期间/as-of由来源选择owner负责，不能跨句/跨公司借用。非期次招股/IR不应再强塞annual期次。上层只消费已绑定source ref/metadata，保必要引用比较。
3. 数字/币种/单位/issuer/计划与已发生、source locator/context closure是内容正确性与职责边界。unknown不是fact，不以减少门禁为由制造支持；原工程独审语义反控保留。
4. 用户真实累计美元/token、下载时长/bytes、文档work、存储资源上限继续；统一预算归属，不能再另叠每层固定小阈值。source-reader256MiB单候选、2GiB/64候选默认属于内存/IO兜底，可后续统一配置/streaming，不作为本轮未经测量直接无限打开内存的建议。
5. lease/generation CAS/outbox是幂等恢复与费用不重复归属，不是人工签收；显式冻结pin损坏仍拒绝，G2只改变自动候选发现对可重建缓存的策略。
6. wire的type/ref/ID/finite-number/不允许循环与实际原文定位必须保留。删除G1的任意体积许可，不等于放宽所有unknown fields/接受未定位内容，也不通过悄删mandatory信息凑小字节数。

## ROOT建议实施顺序

先完成ROOT当前观察器soft表示；再G1合并所有结果/receipt尺寸硬门为可序列化的资料＋可选诊断表示，单次大节点独审；随后G2恢复可重建缓存路径、G4单owner读校验，分别有界集成；G3先一例同native-unit RED核真实行为再定scope修复；G5统一几何hint预算与上下文保留。每节点跑真正受影响测试，不扩逐小节点审批，不重跑超时全仓或提前真实source。旧坏pin/原件变化/数值归属等关键反控不放松。全部为ROOT总控可直接执行建议，无需用户重新授权。

尚未实施或复验，当前真实C及公司循环状态不因本审计升级；ROOT负责把选定项归入唯一PWF并推进。本线STOP。
