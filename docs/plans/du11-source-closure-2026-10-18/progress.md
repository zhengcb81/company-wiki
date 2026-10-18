## C 第七轮：菜单排序/截断不能消除覆盖缺口（2026-10-18）

- 业务优先排序 + 截断 36：28 条，覆盖 30%/60%、PD5、Micro-LED、Preciomo、众硅，仍缺 InP——材料序里 InP 任务排第 40 位，被截断。
- 截断 40（含 InP 任务）：21 条，**仍缺 InP**——模型自己只写 21 条并跳过该任务，不是菜单位置问题。
- 结论：单次调用下 MiMo 写 20–28 条、MiniMax 写 5–8 条，模型自行选择任务；`NarrativeModelCaller` 的契约是 “exactly one model attempt”，二次补写需要改 paid-admission 架构。仅靠 prompt/上限/排序已无法稳定覆盖 10 条 required。
- 用 MiMo 跑 US 的诊断被 runner 的 `PREPARATION_FINGERPRINT_CHANGED`（gold/hk-annual.json）拒绝，未执行，未产生费用。

**阻塞点：** C 内容验收的最后 1–2 条 required 需要产品决策（二次调用 / 换模型 / 调整验收标准）；单次尝试架构下继续调参只能得到 8/10 且缺口每次不同。

---
## C 第六轮：CN 8/10；单次调用的覆盖存在方差（2026-10-18）

- 第三轮内容复审：**CN required 8/10、critical 5/7**；上一轮 5 个 P1 全部关闭（PRISMO PD5、InP、三条 claim 质量），只剩未来五年 60%/70% 与当前 30% 两条——它们在**同一段 t13**。
- 方差实验（均真实计费，全部已回退到 HEAD）：target 15 覆盖 30/60 但缺 InP；40 上限（已推送的 b2v3w）22 条、8/10、缺 30/60；业务优先排序 26 条、覆盖 30/60+InP+Micro-LED、缺 PD5；上限 60 只写 21 条、覆盖 PD5+30/60、缺 InP。
- 结论：单次调用下模型自行选择约 20–30 个任务，**覆盖的 required 子集每次不同**；把上限从 40 提到 60 并不增加产出量。稳定 10/10 需要“覆盖修复”的第二次调用（只对未覆盖任务再问一次并合并），或换用产出更完整的模型。
- **US（MiniMax）**：同一 prompt 只写 5–8 条（MiMo 20–30 条）；提高上限、加强“每 task 必须一条”的措辞（曾致 MiMo 72 条超限）都无效；两次调用是唯一可行路径。

**Next Step：** 产品拍板 ① 覆盖修复二次调用（保留三供应商，需扩展计费/缓存）或 ② US 换 MiMo；之后重跑 CN/US 并做最终内容复审；HK 等 DeepSeek 密钥。

---
## C 第五轮：40 条预算生效，CN 覆盖关键事实；US 模型产出过低（2026-10-18）

- 发现并修复一个 live 专属回归：把 `MAX_SUMMARY_CLAIMS` 传进 `compile_scoped_model_view` 会改变 task-plan binding 标记，worker 在模型调用前以空消息 `HANDLER_EXCEPTION` 死信（0 tokens）。绑定标记保持 20（wire 兼容），**有效预算走 `output_plan.max_claims=40` 与解码器**。
- **CN（MiMo）**：PASS，1 POST，15,970 tokens / $0.002968，**22 条 claims**；已覆盖 PRISMO PD5、InP/磷化铟、Micro-LED、Preciomo Udx、众硅/CMP。
- **US（MiniMax）**：PASS，1 POST，19,115 tokens / $0.009165，但**只写 5 条**，Azure consumption、RPO 375B/368B/40% 仍未覆盖。同一 prompt 下 MiniMax 的产出量（5–9 条）远低于 MiMo（22–30 条），属模型遵从度差异。
- 结论：CN 已接近内容验收；US 需要在“换模型 / 二次补写调用 / 接受部分覆盖”之间做产品取舍（见上一节四选项）。

**Next Step：** 第三轮内容复审确认 CN 覆盖；US 取舍拍板后执行；HK 等 DeepSeek 密钥。

---
## C 第四轮：scoped 摘要 claim 上限 20→40，CN 覆盖全部关键事实（2026-10-18）

**取舍与理由：** 64 个候选任务组配 20 条 claim 预算时，真实模型只能覆盖部分关键事实；历史上覆盖最好的 22 条版本（CN 8/10）被旧上限整单拒绝。将 **scoped 路径**（v4/v5）的 `MAX_SUMMARY_CLAIMS` 提到 **40**、`target_claim_count=36`；v1–v3 legacy 仍保持 20，不受影响。

- **CN（MiMo）：PASS**，30 条 claims，15,746 tokens / $0.002893；已覆盖 PRISMO PD5 阶段、InP/磷化铟、Micro-LED、Preciomo Udx、众硅/CMP 收购、当前 30%、五年 60%/70%。
- **US（MiniMax）：PASS 但只写 8 条**，Azure consumption、RPO 375B/368B/40% 仍缺；同一 prompt 下 MiniMax 的产出量显著低于 MiMo，属模型遵从度差异，待第三轮内容复审确认后再决定（换模型或分块二次调用）。
- 触发点：`validate_against` 等共享校验不设 20 上限；scoped 解码器与请求构建统一用 `MAX_SUMMARY_CLAIMS`。

**Next Step：** 第三轮内容复审（CN 预期接近 10/10，US 仍不足）→ 决定 US 的处理方式 → HK 等密钥。

---
## C 第三轮配置：全量视图 + target 15；内容覆盖仍是瓶颈（2026-10-18）

- 第二轮内容复审（view 收敛到 20 个任务时）：CN required **2/10**（critical 2/7）、US **4/8**（critical 4/8），均 CONTENT_FAIL。复审明确指出 20-task 位置抽样把上一轮已覆盖的 f-five-year-target、f-current-coverage、f-cmp-acquisition、f-microled-sample 等又丢了——**位置抽样不可用**。
- 已回退“按位置抽样”的视图收敛；恢复全量 64 个任务，改为：schema 每 task 至多 2 条、prompt `4.0.5` 要求 `target_claim_count=15`（给 20 条硬上限留 5 条余量，因为 MiMo 在 target 18 时仍输出 21 条）。
- 最新 CN（`live-cn-h1-b2v3r-20261018`）**PASS**：1 POST，15,382 tokens / $0.002772，15 条 claims；已覆盖 CMP 收购、当前 30%、五年 60%/70%、Micro-LED、Preciomo Udx；仍缺 InP 与 PRISMO PD5。
- 结论：**工程验收已稳定，内容验收未达成**。20 条 claim 上限对 64 个候选任务组，模型实际只写 15–22 条，且每次覆盖的 required 子集不同；这是“预算 vs 候选集 vs 模型遵从度”的结构问题，继续微调 prompt 的收益在递减。

**Next Step（需产品取舍）：** ① 提高 claim 上限（20→24/28）；② 为 selector 增加可传递的值分数，按分数而非位置选视图；③ 换用能稳定遵从 20 条上限的模型；④ 接受部分覆盖并在收据里显式列出未摘要任务。选定后重跑 CN/US 并交内容复审。

---
## C 第二轮：模型视图收敛到 20 个任务，CN/US 再次 PASS（2026-10-18）

**根因：** 任务计划有 64 个 citation view，却只有 20 条 claim 预算。真实模型因此出现三种失败：只写 8 条（覆盖不足）、写满 64 条（`CLAIMS_LIMIT`）、把 task-local part key 串错（`EVIDENCE_REFERENCE`）。

**修复：** 模型视图只暴露 **20 个任务**（按文档位置均匀抽样，避免摘要压缩在开头章节）；完整 plan 仍保留 64 个任务供覆盖统计；prompt `4.0.3` 要求约 18 条、每 task 至多 1 条。

- **CN（MiMo）：PASS**，1 POST，9,843 tokens / $0.001798，13 条 claims；InP/磷化铟已覆盖，PRISMO PD5 阶段仍缺。
- **US（MiniMax）：PASS**，1 POST，10,829 tokens / $0.005353。
- 第二轮内容复审进行中（上一轮 11 条 P1 逐条复核）。
- HK 仍被无效 DeepSeek key（401）阻塞。

**Next Step：** 内容复审结论 → 关闭剩余 P1 → US/CN 定稿；HK 密钥轮换后补跑。

---
## 正式 C 内容审查：CN/US 均 CONTENT_FAIL；两处根因已修（2026-10-18）

独立内容审查（非作者，只读）：**CN CONTENT_FAIL**、**US CONTENT_FAIL**。

- CN：required 命中 8/10（critical 5/7），缺 PRISMO PD5 阶段与 InP 起步；另有 3 条 claim 质量问题（“该新产品”未闭合、源句截断、从句中起头）。
- US：required 命中 2/8，缺 6 个 critical（Azure consumption-based、三段结构、2024-08 分部重组、RPO 375B/368B 与 40% 前瞻）；8 条 claim 本身逐字、数字正确。
- 两者：无评级/目标价/估值，语言保持 zh/en，未发现数字或单位换算错误。报告：`review/c-content-review-20261018.md/json`。

**根因与修复：**

1. 任务计划有 **64 个 citation view** 对 20 条 claim 预算，模型只写 8 条；schema 每 task `maxItems=1` 进一步压制覆盖。已把 per-task 上限做成动态值并在 4.0.2 指令中要求“每个有直接支持的 task 输出一条，直到预算”。
2. MiMo 某次把 clause 输出成 **JSON 字符串数组**（双层编码），被判 `CONTRACT_INVALID`；解码器现在容忍一层编码并保留全部合同校验（新增 transport 控制测试）。
3. 曾尝试按 `max_claims` 截断任务计划，但违反既有合同“claim limit never silently drops source tasks”，已回退（160+ 任务测试保持绿）。

最新一次 CN 重跑因 `MODEL_TIMEOUT` 失败（provider 延迟），不是合同问题；US 待用 4.0.2 重跑。HK 仍等 DeepSeek 密钥轮换。

**Next Step：** 用 4.0.2 重跑 CN/US → 再次独立内容审查 → HK 密钥修复后重跑 → holdout。

---
## 正式 C：CN(MiMo) 与 US(MiniMax) 真实 PASS；HK(DeepSeek) 被无效密钥阻塞（2026-10-18）

**根因修复（摘要 claims 上限）：** `max_claims=20` 只写在自然语言指令里，而响应 schema 的每个 task 数组允许 20 条，模型按 schema 输出 22 条 → `SUMMARY_INVALID / CLAIMS_LIMIT`。修复：`output_plan.max_claims_per_task = 20 // task_count`，响应 schema 的 `maxItems` 改为该动态值，prompt 版本升到 `reading-source-scoped/4.0.1` 并在指令中引用；新增 3 个控制测试。

**CN（MiMo `mimo-v2.6-flash`）：PASS。** 1 次 POST，15,394 tokens / $0.002783；`activation_recovery.status=PASS`（同 attempt、无新增 charge）、`cross_run_zero_POST=true`、exact-ref PASS，artifact `fe70c9f0…`。收据：`live-cn-h1-b2v3i-20261018/receipt.json` 与 `overall.json`。

**US（MiniMax `MiniMax-M3`）：PASS。** 1 次 POST，18,093 tokens / $0.007782；同一恢复/缓存链 PASS，artifact `fb73610d…`。收据：`live-us-10k-b2v3-20261018/`。

**HK（DeepSeek `deepseek-flash`）：BLOCKED。** 真实调用返回 `MODEL_HTTP_CLIENT_ERROR` 401；直接探测确认 `DEEPSEEK_API_KEY` 无效（API 原文 “Authentication Fails … ****449c is invalid”）。未替换 provider、未伪造数据；需要轮换该密钥后重跑 HK。

**临时目录根因：** Python 子进程在本机 `%TEMP%` 和 `C:\` 根目录创建目录被 ACL 拒绝（WinError 5），`tempfile.mkdtemp` 因此反复重试——这就是此前多次 C 卡在 preparation 的原因。改到 `C:\Users\郑曾波\Projects\cwp-temp`（仓库外、可写）后全部通过；未改生产配置。

**累计账：** ledger 20 个唯一 attempt，479,369 tokens / $0.135217（不含 metadata 记录的历史基线）；HK 的 401 未计费。

**Next Step：** CN/US 摘要交独立内容审查（关键事实、指代、主体、单位/期间、当前/未来）；HK 等密钥轮换后重跑；之后 holdout 与 RF 审查循环。

---
## B2 性能修复已发布；正式 C 受本机负载阻塞（2026-10-18；优先于上一节）

- `6a2ee853` 已推送：声明回看改为 64 字有界窗口 + 按原文缓存，单次 26ms → 3.7ms（缓存命中约 0）；CI `39123679375` success。105 测试与三源召回不变。
- 正式 C 共尝试 5 次：第 1 次跑完选择→真实 POST→activation 恢复→cache→cross-run→read→reference 全链，但 `TEMP` 未设置使临时湖建在仓库内，收尾断言失败、receipt 未写出（真实计费 15,141 tokens / $0.002722，重复 ledger 行按 attempt 去重）。第 2–5 次均在 preparation 阶段超过 15 分钟只有 `preparation.json`；py-spy 显示卡在 `tempfile.mkdtemp`，且本机另有两个 agent 各占约 1,500s CPU。第 5 次改用收窄 root + `C:\cwp-temp` 干净临时目录仍无进展。
- 结论：**C 仍 OPEN**，当前具体阻塞是本机资源争用/临时目录，不是 B2 语义；已停止所有未完成的付费 run，未再产生费用。
- 本地门禁仍被两个非 CI 范围的测试挡住（`test_fresh_cache_behavior_receipts`、`test_official_projection_...`），shim + runner 守卫保存在 parked patch，未推、未绕 hook。

**Next Step：** 等机器空闲窗口重跑 cn-h1 live（干净临时目录、narrowed root）；同时定位两个合同测试；之后再推 shim/guard。

---
## B2 三审：中文泛称与 head 匹配已修（2026-10-18；优先于上一节）

三审仍判 **REJECT**（工程 7/10、合同 5/10）：v2 的 P1-B、P2-A、P2-D 关闭；P1-A 只修了拉丁泛称，另发现新 P1（head 不比较）。已修：

- **P1-A 中文泛称**：声明改为“先找 head、再向前取专名”，并剥离 公司/推出/开发/销售 等前缀；加入技术描述词与产品 head 黑名单、计量词/指代词拒绝。`公司主要产品系列`、`各类产品`、`所有系列`、`上述系列产品`、`前道集成电路设备产品`、`可覆盖存储器件` 均不再成为声明。
- **P1-B head 匹配**：series 指代只接受 series 声明，device 只接受 device；泛称 `these products` 仍接受任意产品声明。`Omega设备` 不再闭合 `该系列产品`。
- **P2-A 专名形态**：支持 `iPhone 15系列`、`Model 3系列`、`3M系列`、`Preforma uniflash系列`、`小米系列产品`（系列后缀从名字挪到 head）。
- **P2-B 前置枚举**：新增 `包括A、B在内的X系列` 这一形态；同句客户列举不再误挂。
- **P2-C 归属**：`公司客户…` → quoted；`公司表示客户…` → issuer。
- **P2-D 泛称英文**：`products or services`、`internal control`、`accounting systems` → not_applicable，US 未闭合从 11 降到 6。

测试 **105 PASS**；selection/w04 **738 PASS**。三源回放：CN 10/10、HK 7/7、US 8/8；work 6,133,095 / 13,157,181 / 7,989,484；收据 `b2-v3-20261018/`、`b2-real-sources-v3-20261018/`。

**正式 C 的进展与阻塞（如实记录）：**

- 首次 cn-h1 live（`live-cn-h1-b2v3-20261018`）跑完了选择→真实 POST→activation 恢复→cache→cross-run→read→reference 全链，但收尾断言失败：本机 `TEMP` 未设置时 `tempfile.gettempdir()` 回退到仓库目录，runner 在仓库内建临时湖，最后 `ROOT not in root.parents` 断言失败；**receipt 未写出**。真实计费已入母账（attempt `76fe00f0…`，15,141 tokens / $0.002722）。
- 母账该 attempt 出现两行重复（`append_native` 追加两次），`mother_totals` 按 `(database, attempt_id)` 去重，累计不受影响；文件保留不改。
- 第二次显式设置 temp 重跑（`live-cn-h1-b2v3b-20261018`）超过 20 分钟无产出，已停止进程；仅 preparation/harness 两文件，未写 receipt。原因待查（非网络连接态）。
- 结论：**C 仍 OPEN**；需先修 runner 的 temp 前置校验（应在付费前 fail fast），再以 loopback 验证链路耗时，然后重跑真实三源。

**Next Step：** 提交/推送本轮 B2 修复 → 修 runner temp 前置校验并补测试 → loopback 计时 → 重跑 cn-h1 live。

---
## B2 复审 v2：2 个新 P1 已修（2026-10-18；优先于上一节）

复审仍判 **REJECT**（工程 7/10、合同 5/10）：v1 的 P1-1/2/3/5 关闭，P1-4 部分关闭（furniture 邻接错误），另发现 P1-A/P1-B 与 6 个 P2。已逐条修复：

- **P1-A 泛称伪声明**：拉丁名改为“大写专名 token 序列”，CJK 名排除公司/产品/这些/计量词；`We sell products…`、`Our products…`、`公司产品系列丰富`、`这些产品线` 不再成为声明。
- **P1-B furniture 邻接**：回溯改为与“最后保留的 unit”比较，并记录被跳过的 proven furniture 数；跨页 carry 仍按真实邻居 `(p1,p2)`，错误 carry `(p1,header)` 不再接受。
- **P2-A** deictic 先识别实际 head（含系统/平台/方案），不支持的 head 回退 legacy，不再把“这些平台”当产品。
- **P2-B** collective marker 必须出现在声明之后，同句客户列举不再挂到产品系列。
- **P2-C** 客户/供应商主导句判 `quoted_related_party`（不捐赠），公司主语判 `issuer`；新增正反例。
- **P2-D** 重跑三源并绑定最终代码：bindings 含 `product_reference a1300818`、`narrative_antecedent 41d42ef7`、`relations dce431d9`、`narrative_reading ddc36db5`；`deferral_reasons` 三源均可见（CN 5、HK 2、US 11 unresolved）。
- **P2-E** 新增 9 个负例/正例：泛称句、unsupported head、同句 collective、attribution 正反、furniture carry 正反、separate-window。
- **P2-F** 同页跨窗口由 ordinal 证明；跨页只认已证明窗口边，separate-window 不桥接（有反例）。`SourcePageFlow` 只暴露汇总、不暴露边，故不接线并如实记录。

测试 `tests/unit/du11_source_closure` **99 PASS**；selection 738 PASS；全量 unit 见 progress。真实三源：CN 10/10、HK 7/7、US 8/8，work 6,133,095 / 13,157,181 / 7,993,449，0 API、原件/gold 不变。收据：`b2-v2-20261018/`、`b2-real-sources-v2-20261018/`。

**Next Step：** 三修后复审 → 提交/推送核精确 CI → 正式 C。

---
## B2 独立审查 REJECT → P1 全修（2026-10-18；优先于上一节）

独立审查（非作者 agent，绑定 family-scope 快照 SHA）结论 **REJECT**：工程完整度 6/10、合同一致性 4/10，P1×5、P2×11。已逐条修复，报告见 `review/b2-antecedent-independent-review.md`。

**P1 修复：**

- P1-1 声明上下文端到端：`_candidates` 现在把声明的原始 unit id 同时写入 budget 包与原始 eligible 包；`_context`/citation view 的 target 组变成 support=target、context=declaration（新增 `select_reading_evidence` 端到端断言）。
- P1-2 envelope 命名空间：声明按原始 id 计数，carrier 通过 `expand` 展开为全部 originals；不再拿 carrier id 查 `original_units`。
- P1-3 offset：声明/成员 ref 直接在原文上匹配（不再用压缩空白的匹配视图），CJK 换行场景新增回放断言。
- P1-4 跨页：从 continuity window 导出 `page_carries` 并传入窗口构建；未证明物理顺序 → `complete=False`/`partial`；proven running furniture 可跳过；`project_for` 与真实 section key 接线。
- P1-5 内部声明：只接受 deictic **之前**的声明；forward declaration → `missing`；两个内部 family → `ambiguous`。

**P2 修复：** 单卡 reference deferral 不再让整篇 `status=partial`/`coverage_complete=False`；unread/unproved/cap → `partial`；envelope block key 改为 `(parent, page, pdf_block)` 且 carrier 展开；坐标缺失不再借为相邻；collective members 只取声明所在句；attribution 按 role 保守判定；产品 head 词表改为 `PRODUCT_SUFFIX` 子集＋import 断言（无第二套词典）；reference deferral 前置于 128 截断；probe `source_bindings` 绑定 3 个新模块；readiness 异常统一转 `partial`。

测试 `tests/unit/du11_source_closure` **90 PASS**（新增端到端 context、forward、内部 ambiguous、换行 offset、carrier envelope、跨页 carry、文档状态、collective 负例、客户声明不可捐赠）。

真实三源（修复后，0 API、原件/gold 不变、同 16M）：CN 10/10、HK 7/7、US 8/8；work 6,133,095 / 13,157,180 / 7,987,497。CN 收据首次可见 `REFERENCE_UNRESOLVED=3`、`REFERENCE_ENVELOPE=1`；t32/t34 精确 SHA 仍 `selected_matches=0`。收据：`b2-reviewed-final-20261018/`、`b2-real-sources-reviewed-20261018/`。

仍未关闭（如实记录）：单数产品指代按计划保留 legacy admission；第三方归属只做句内启发式（`THIRD_PARTY` 出现在声明前且无 `ISSUER_WORD` 即不捐赠），不做完整引述解析；运行期 selection cache 是否因语法模块字节变化而失效未验证。

**Next Step：** 复审 → 正常提交/推送/核精确 CI → 进入正式 C。

---
## B2 有界先行词工程节点完成（2026-10-18；优先于历史）

B2 已按 `review/antecedent-source-interface-final.md` 实现，并跑通真实三源回放。状态：**ENGINEERING_GREEN（独立审查/发布进行中）**；正式内容 C 仍 OPEN。

本轮改动（只扩展现有责任层，没有第二套 detector/Store/预算/产品词典）：

- 新增 `document_understanding/operating_states/product_reference.py`：产品 deictic 与具名声明/集体枚举的纯语法；单数指代与族指代分开标记。
- `OperatingRelationSession.reference_closure()`：按 target + 有序 predecessor + window_complete 缓存，返回 `not_applicable/unique/collective/ambiguous/missing/partial`；声明 ref 保持原始 namespace。
- 新增 `source_catalog/narrative_antecedent.py`：按真实 source ordinal 的有界前驱窗口（同 source/section/project/role/kind，连续性不足即停，cap 截断标记 incomplete）＋ 联合 envelope（8 原 unit、4 个 `(source,page,pdf_block)`、2048 原文字符）。
- `SourceOperatingSession` 增加 originals 只读回退、antecedents、`reference()`；声明 ref 按自身原文校验，不经过 target offsets 重映。
- `_candidates` 把 readiness 前移到 graph 与任何 fact/cache 之前；`ambiguous/missing/partial` 只 defer 该卡（`REFERENCE_UNRESOLVED`），envelope 超限只 defer（`REFERENCE_ENVELOPE`），`unique/collective` 把声明原 unit 计入 required context。

范围收敛（详见 findings）：只有**族/系列指代**（系列、产品线、上述、前述、这些、该等、these/those/such）进入门禁；单数「该设备/该产品」保留 legacy admission，避免把没有跨窗身份主张的句子误 defer。该收敛由 4 个既有 selection 测试暴露后决定，不是放宽断言。

真实三源回放（0 API、0 原件副本、原件/gold 前后 SHA 不变、同 16M 账户）：CN 10/10、HK 7/7、US 8/8；selected 96；CN 6,141,589、HK 13,171,440、US 7,993,452 work units。t32/t34 精确 SHA `selected_matches=0`；p17「该系列设备已付运」以 `REFERENCE_UNRESOLVED/missing` 显式 defer；CN withheld 137（`REFERENCE_UNRESOLVED` 2、`REFERENCE_ENVELOPE` 1、其余为既有非可选/预算）。收据：`b2-family-scope-20261018/`、`b2-real-sources-20261018/`。

测试：`tests/unit/du11_source_closure` 78 PASS；全量 unit 结果见 `progress.md`（4 项宿主环境失败不计本节点，逐项列出原因）。

**Next Step：** 独立审查 → 修复确认项 → 正常提交/推送并核精确 CI；之后才进入正式 C（三供应商原语言摘要、付费恢复、同/跨 run 缓存、FF/RF 真实消费），不得用本节点工程绿或金标命中代替内容 C。

---
## 当前两卡接收与发布结果（2026-10-18；优先于历史）

接手下一主线时先读[DU11 当前主线接手指南](review/harness-handoff.md)；本文件后续各节定义 B2 的详细行为和测试合同。

RF/FF两张DU11卡功能工程已接收、全部交付提交进入各自主线。CWP producer先发布0ccdc689（6801PASS24SKIP346.26s＋142合同PASS48.31s，精确CI39094787278 success）；RF runtime f8002f5f（18独立行为接收、416PASS＋36子测、CI39092538354 success、6源码定点安装）；FF最终e8740748（873PASS7SKIP78subtests91.13s、精确CI39095654355 success、6物理源码依赖序原子安装，双根imports/help通过）。RF唯一兼容版本表两阶段正常更新：e7364639的wiki pin/CI39094965965 success，再9669c4d7收敛filing=e874、wiki=0cc、revenue=f800，最终416PASS＋36子测73.74s、远端一致，精确CI39095818018已completed/success，三仓本次发布CI全部绿。

正常FF发布共3次尝试=2RED+1GREEN：先修异构schema类型丢失及既有mypy hook漏掉transitive scripts依赖，再修旧“未知日期”夹具缺provider导致测试错位。保留原完整拒绝/0下载/日期资格断言，不删测试/提高阈值/跳hook。JSON stdout的GBK/UTF8根因和集中CI表漏DU11纯回归也已修并独审；最终类型delta独立公共mypy＋10有限控制通过。详细收据见review/du11-reception-closeout.md以及各publication报告。

未动生产原件/gold/配置/密钥/Dayu/IQS或作者树，没有新收费模型调用。RF旧3个assurance WIP保留，stage1曾观察weekly_manifest自然变化，不归因/不恢复旧值；stage2前后相同。一个RF外层审查Temp仍NOT_CLEAN，历史PermissionError后平台拒删，保留且不换通道重试；内部端到端原样恢复。未知发布日期的/3投影仍如实source_availability_unknown，不伪造日期或另加许可。

整体PWF仍OPEN：t32最新真实诊断不再selected；t34仍缺有界先行词。下一实现按review/antecedent-source-interface-final.md，在现source/operating唯一owner、同parent16M及8units/4原block/2048chars封闭依赖，再做正式三供应商摘要、收费/activation恢复、同跨run缓存及真实FF/RF消费C，之后holdout与RF循环。不要把工程/金标命中当内容C通过，不重做已接受DU11或新增小节点签收。

## 当前发布结果（优先于下方历史）

CWP已正常发布remote master=0ccdc6896ee58063ff827e9ceab16043c7550e0c：全量6801PASS24SKIP346.26s、独立合同142PASS48.31s，未删测/提时限/跳hook。精确CI39094787278已completed/success，匿名API核对相同HEAD。详见review/du11-cwp-publication.md/json及保留的原push日志。RF runtime已发布，集中compatibility/current.json须先更新CWP producer pin，随后正常发布FF，再同步安装源码/核精确CI。t32最新诊断不再selected；t34有界先行词及正式C仍OPEN，下一实现接口/TDD见review/antecedent-source-interface-final.md。

# Progress

## 最新：正常push超时与两个独审delta（2026-10-18）

母仓6ee5ebf1正常push未成功：完整unit约96%时达到600s，日志在母仓`.planning/shared-reading-production/du11/push-source-flow-reader-port.log`；远端仍9c681ed2。原日志保留，非断言失败证明，也不能因PowerShell尾部命令exit0误报发布。现用已声明xdist对完整unit目录启两个file-scheduled worker，不删测试/改期限，窄测和contract不增加启动开销。实现先3FAIL/1PASS，修后4新及80既有gate控制共84PASS6.44s。独立4新控制PASS4.69s，另3窄测/非零退出控制通过；真实2-worker/SQLite超时反控5s期限后20.064s返回124（既有execnet约15s关停），返回时worker均退出、gate/outer Temp均删除。完整7000组运行提速未签收，留待正常push；不增加第二进程管理框架。

源编号修复先3RED、补未知counter反控1FAIL/3PASS，再77PASS3.95s。独立新4＋自选6跨两轮10个不同控制通过，首轮9PASS/1FAIL是审查控制误要求局部拒扣后parent.exhausted=True；按既有B1语义应保留父余额，仅修外部审查控制且单跑通过，生产源码未迁就错误断言。报告精确SHA绑定见review/page-local-readiness-independent.md/json。实源诊断page-scope-after-counter-fix明确非冻结验收/计时证据：CN10/10、parent6142162、旧t32不再选中，t34仍选中，0API/原件gold不改。该剩余先行词问题不混签绿。

## 当前发布与接收（2026-10-18）

物理/cache最终独审已完成：PASS_PHYSICAL_BUDGET_CACHE_COMPONENT，27有限PASS8.51s、5源码/2测试精确SHA前后相同、两自有Temp均删除；未重跑219/763，不代签一般语义/先行词C。FF隔离根修已正常commit a9c2dcf7，等待先producer发布；新CWP test唯一静态F811以同既有pytest fixture参数noqa说明，runtime与各独审冻结一致。

B1远端9c681ed2已精确CI39092308121 success，正常push5221PASS/11SKIP517.05s，未跳hook/改deadline。RF外包已18项独立行为接收，正常main发布f8002f5f（416PASS＋36子测65.46s），精确CI39092538354 success，2物理技能目录6源码同步、原3WIP SHA不变；验收一次外层Temp被平台拒绝删除仍NOT_CLEAN，其内部E2E恢复真，未再换方式删除。

FF初审102PASS＋4实际反例发现日期/股票码根因，ROOT隔离修34PASS后不同agent28控制＋真实HK TXT1链最终复审PASS；29unique跨次通过、0ET/network/原件修改，作者树未写。仅待CWP先发布reader canonical端口，再正常FF commit/merge/push/定点同步。

物理早期763PASS45.71s后独审新发现繁体新issuer、English显式新产品主语被接到旧半句；修共享grammar后225PASS4.70s，又补source grammar缓存漏口/N²/真实parser MIME/per-pair coverage，先6FAIL及8FAIL30PASS后修，最终219PASS10.11s。最终实源零收费CN/HK/US10/7/8及canonical一致，parent work6106955/12820408/7975948，原件/gold不改、0copy/ownedTemp删除。但实际CN t32/t34仍selected，整个语义闭合/先行词及正式C仍OPEN。最后delta独审进行中，未拿旧收据重签当前源。

CWP reader新端口及同次manifest读取先3RED，第一次相关54P3F（2fixture config目录错、1暴露global pin兼容），改后4针对PASS；新filing_reuse单观察反控2FAIL3PASS指出None未观察混淆，复用scope sentinel修，最终59PASS37.37s。FF跨仓最终review绑定两reader真实源SHA，原manifest/原文不变、不新增人工门禁。

## 最新 B1 节点（2026-10-18）

最终独审PASS_B1_ENGINEERING，精确3文件SHA前后相同；独立9PASS/3.27s＋3有限控制（两入口预扣失败0访问、外部context正控不丢），自有及pytest重定位Temp均删除。真实三源budget-source-replay/receipt.json：CN10/10、HK7/7、US8/8，canonical同分；分别12.665/27.042/11.721s，同一16M账户各用5758585/12269996/7975948，无耗尽。原件/gold不变、0POST/0原文复制、ownedTemp删除。内容/C仍OPEN，不能用此工程节点代签。

现production source metadata与native continuity已复用同parent账户，移除逐member重建容器集合的N²行为。独审指出两预扣前遍历并新增CountedIds反控；RED为7PASS/2FAIL，修复后739集中PASS/50.52s。首次大组733PASS/4FAIL是四个新fixture错误，完整失败保留budget-index-full-green.log（文件名非结论）；改正后目标行为才真正执行。最终独审及真实三源回放进行中，B2物理跨页与先行词未实现，正式付费C仍OPEN。

母e33d40ed正常push6741PASS/24SKIP/580.05s+142合同PASS/37.31s，精确GitHub CI39090720114 success；文档0099dd5d已推。B1未发布前的后续记录与母结果分开。下方是历史顺序证据，不作为当前Next Step。

2026-10-18：建立ROOT后续独立包；无新生产源码改动、无API/原件写入。前置工程9eff4ee7已独审正常提交并合母e33d40ed，母正常push进行中。阶段A RED尚未实施，阶段B/C均OPEN。

## Stage A physical behavior RED

Existing production _prose_reading_packages/_candidates/finalize_selection, not a missing-module placeholder: tests/unit/du11_source_closure/test_cross_page_reference_plan.py collected15,8FAIL/7PASS4.45s. Six CN/EN × background/event/risk positive multi-original carries currently split; five distinct (source,page,block) sentence can expose right suffix; one-span budget currently exports only half a cross-page sentence. Seven unknown/changed-column/page-gap/scope/font/heading/table controls pass. No production changes yet; draft tests remain only ROOT isolated branch and are not in mother pending push. Next write furniture/independent-statement/parent-budget and antecedent cases, then shared owner implementation.

StageA expanded19cases:10FAIL/9PASS5.61s, including explicit running furniture and exhausted parent geometry scan. Root began systematic budget connection: _Analysis uses existing WorkBudget.scoped, source candidate metadata reserves before indexes, same parent flows into geometry and operating session. First zero-parent controlGREEN1PASS/102deselected4.83s: -k applied to all requested paths, so this is explicitly not103PASS. Correct explicit-node compatibility command is separately running. Full physical crosspage/antecedent implementation and independent review remainOPEN; mothere33 normalpush succeeded6741PASS24SKIP580.05s +142contracts37.31s and remote master exactlye33d40ed7688cfdcead1e02d55542f7026d0b8e5. RemoteCI352/runs39090720114 currentlyIn progress.

Metadata performance root cause reproduced on actual _prose:16/32members visited288/1088times (quadratic),2FAIL5.05s; no timing-only claim. One owner external-context index and one combined exclusion set now avoid rebuilding whole member/context sets for each paragraph. Reservations account actual membership/section/header-context edges and sort work on the same parent; _candidates returns finite partial if preprocessing cannot reserve. Concentrated88PASS5.59s covers2linear controls/2parent-budget+previous native/prose readiness controls. Source crosspage/antecedent RED remains intentionallyOPEN and unmerged. New design review approved overall owner direction but is not final implementation acceptance.
