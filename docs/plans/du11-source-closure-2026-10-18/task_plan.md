## P1–P4 施工包已由 ROOT 接收（2026-10-18）

- 四包全部合入本地 `master`：P1 `09a8dded`（40 tests，ruff/mypy 干净）、P4 `626eb32f`（fixtures catalog 下 34 passed，无 env 时 34 skipped 按设计）、P2（70 passed，独立复审 PASS）、P3（50 passed，独立复审 REJECT→APPROVE）。P1 接收时把重名的 `synth.py` 改为 `p1_synth.py`。
- 合并后全量单测：**6910 passed, 24 skipped**（687s，Miniconda 解释器）；`origin/master` 仍停在 `ccc5bc7e`，推送仍被两个既有失败测试挡住。

---

## C 内容按 8/10 收尾（用户决定，2026-10-18）

- 用户确认：C 内容按 **CN 8/10** 收尾，不再为最后 1–2 条事实继续烧真实调用。
- 已交付：B2 最终复审 PASS；**exact CI 仅覆盖 `2a80acf6`**（`b2-final3-20261018/ci-39139605025.json`，B2 唯一精确 CI）；三源回放绑定当前代码；C 工程侧 receipt/恢复/缓存/FF-RF 证据在**工作区** `.planning/shared-reading-production/du11/`（未入 git，fresh clone 不可复核）。
- **交付状态须知（2026-10-18）**：本地 `master` 领先 `origin/master`（`ccc5bc7e`）**7 个提交、未推送、无 exact CI**；`origin/master` 仍是无条件补写版（"默认关闭"只在本地未推提交，本地开关另推在分支 `du11-repair-flag`）。P1–P4 四张施工卡已在本地 `codex/p1..p4-*` 分支实现完毕，状态为 **IMPLEMENTED_PENDING_ROOT_RECEPTION**，不是 READY_TO_DISPATCH。
- 已知缺口（如实交接）：CN required 8/10（critical 5/7）、US 2–4/8、HK 未跑（DeepSeek 密钥 401）。覆盖修复（两次调用）为实验性、默认关闭。
- **模型评估计划（后续独立课题）**：① 先换有效 DeepSeek 密钥，用同一协议跑一次 CN；② 用同一份请求对照一个更强模型，区分“任务形状”与“模型能力”；③ 多模型只用于审计（查漏/查引用），不交叉生成摘要；④ 固定验收矩阵：严格 JSON 成功率、claims 数、required 覆盖、单位/期间错误。

---
## 覆盖修复（A）：两次调用已跑通，卡在 activation-resume 的预约冲突（2026-10-18）

- 修了三个真问题：`HandlerResult.result` 是不可变 Mapping（`isinstance(dict)` 永假，导致补写退化成重发全量请求）；prior 摘要 wire 需转 plain 容器；phase C 的 `gold_observation` 只接受全量 material，补写子集被 AssertionError 挡下。
- 实测（`CW_SUMMARY_COVERAGE_REPAIR=1`）：CN **两次 POST**（28,045 tokens / $0.005134），摘要成功、run 进入 `activation_pending`，说明补写链路本身工作。
- 但 `activation-resume` 复跑时 `ReservationConflictError`：重试 attempt 的 reservation 与恢复路径重新计算的请求哈希冲突。
- 补写默认关闭**仅存在于本地未推提交**；`origin/master`（`ccc5bc7e`）仍无条件执行补写（覆盖不全时多两次调用）。C 内容仍 8/10。下一步：让 resume 复用/跳过已结算的补写 attempt，或允许同一 attempt 的相同请求哈希复用。

---
## B2 定稿：最终复审 PASS（2026-10-18）

- 最终复审 `b2-antecedent-final-review-20261018-v3.md`：**PASS（代码层），无 P1**；两个复审 P1（长名称截断、截断误判为 missing）已修并各带回归测试。
- `tests/unit/du11_source_closure` **110 passed**；ruff 通过。
- 三源回放绑定当前代码：CN 10/10（`b2-final3-20261018`）、HK 7/7、US 8/8（`b2-real-sources-final2-20261018`）；work 6,133,095 / 13,157,181 / 7,989,484；原件/gold 未变、0 API。
- CI `2a80acf6` success，收据 `b2-final3-20261018/ci-39139605025.json`。

剩余唯一未完成项：**C 内容验收**（产品决策 A 二次调用 / C 换模型）。

---
## C 第九轮：4.0.8 覆盖指令回归，已回退（2026-10-18）

- 第四轮 CN 复审（4.0.8，14 条 claims）：required **6/10**、critical **4/7**。上一轮缺的 30%/60% 已关闭，但 InP、SiC 回归缺失，PD5 仅 partial 且与 gold 的 must_not 冲突，另有一条 claim 文本损坏（“上\nte海临港”）。
- 结论：4.0.8 的“必须包含覆盖率/多年目标”指令压缩了其他更新，整体变差 → 已 **revert**（`46ffee41`），恢复 4.0.6（22 条、8/10）。
- 单次调用路径的最佳记录仍是 4.0.6 的 **8/10**；继续 prompt 微调只会换一条漏项，且已两次引入回归（72 条超限、6/10）。

**Next Step：** 需要产品决策：A（覆盖修复二次调用，改 paid-admission）、C（换模型）、D（调整验收标准）。不再做 prompt/上限类实验。

---
## C 第八轮：section 任务合并实测失败并回退（2026-10-18）

- 实现：把相邻同页同节的 citation view 合并为至多 5 个成员的任务（CN fixture 64→40），所有 96 个 span 仍恰好定义一次，support/context partition 校验通过；103 个 scoped 测试绿。
- 实测：两次 CN live 均 `MODEL_RESPONSE_INVALID`（模型返回畸形 JSON，119 bytes 级），说明多成员任务的 parts/support_parts 结构反而让 MiMo 失稳。
- 处置：`4a983c98` 推送后按规则 **revert**（`12914f62`），恢复 40 任务 + prompt 4.0.6 的已知稳定行为；不保留未验证的合并路径。
- 结论：B 路径（任务合并）在当前模型上不可行；剩余只有 A（覆盖修复二次调用，需改 paid-admission）或 C（换模型）或 D（调整验收标准）。

---
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

**累计账：** ledger **44 个唯一 attempt，900,711 tokens / $0.238405**（去重口径，核对于 2026-10-18；不含 metadata 记录的历史基线）。HK 的 401 没有结算发票，但有一条 **69,046 tokens / $0.031208 的 unknown 预算占用（hold）**，按规则不能计为零。

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

# DU11 ROOT 剩余来源闭合实施

PLAN_ID=du11-source-closure-2026-10-18; PWF_PLAN_ROOT=docs/plans。唯一实现owner ROOT。作者工区沿用当前ROOT隔离checkout；母仓主线正常推送期间不改母仓源码/HEAD。RF/FF两DU11外包工区、Dayu/IQS不写。

## 入口与完成定义

**当前工程位置（2026-10-18）：** B1已正常发布9c681ed2，精确CI39092308121 success；RF外包已独立18项验收、main与远端f8002f5f、精确CI39092538354 success、安装6文件定点同步，旧3个assurance WIP不变。FF初审102项主链绿但4反例暴露发布日期及代码解释漏洞，隔离修后28边界＋真实HK TXT1链独审通过；待ROOT先发布CWP producer的canonical_identity可选投影，再正常发布FF，不让新flag先上线断链。

ROOT本节点是物理跨页/真实parser MIME/共享语法/因果cache以及FF reader端口完整组件，**不代表唯一/集体先行词或正式C已完成**。32ab6e06已合母仓5ad4295f/6ee5ebf1但尚未发布：正常push的全量单测在600s到约96%超时，保留原失败日志，不称已推送。现有xdist依赖用于完整unit目录的两个隔离worker，窄测/contract保持原运行方式、集合和600s期限不变；完整运行与远端CI仍待正常push验证。

新真实诊断查明paragraph_index每页重置，而ordinal为source全局位置；未知下一页底部计数块也不能抢先清掉上一页半句。修在同一native owner，未知前缀只defer而不伪造家具/正向拼接。77项相关行为通过、独立10个不同控制跨两轮通过；本次实源诊断旧t32“求的同时…”selected_matches=0，t34“该系列产品…”仍1，原件/gold不变、0API。该诊断明确不是冻结内容验收/性能收据；不得把10/10 gold命中当语义闭合通过。剩余有界先行词设计参见review/antecedent-owner-design.md。继续不读作者密钥、不写原件/gold/生产配置。

母计划 document-understanding-2026-10-13 为总控。前置代码9eff4ee7随e33d40ed已正常发布：6741PASS/24SKIP/580.05s和142独立合同PASS/37.31s；精确CI39090720114 success。母仓后续文档0099dd5d已正常推送，未触发新的行为CI。剩余真实CN断句/指代见 ../du11-source-quality-2026-10-18/closure-investigation/findings.md；具体20源码接口调查见 ../du11-source-tail-geometry-2026-10-18/review/remaining-closure-design.md/json。

完成要求：所有可证明的跨页原support和有限明确先行词context可复现；缺证/多义/超过原上限仅该卡defer，不创造事实；正式三供应商摘要、真实收费/activation恢复、同/跨run缓存和FF/RF消费均通过且有独立内容审查。金标命中/元数据/局部测试不替代完整内容质量。

## 阶段A — 先写端到端依赖行为与纯反例（IN PROGRESS）

1. 用现unit IR/观察/结构/SourceOperatingSession，不新增parser/store/第二预算。先写新公司名通用fixtures：两物理页原句切断、明确同列/同scope和真正running furniture，输出一个多原span support，禁止伪造跨页native_page_view。
2. 缺上一页/列未知/真实页眉证据缺失/TOC/表格/QA/新project或section/source/font/frame/页序不匹配/下一页独立新断言为反控。只知道block_char_start=0不能宣称语义闭合；也不能把所有singleton判残缺重演HK0/7。
3. 唯一/集体产品先行词(简繁/EN)跨窗口；明确列举的A/B/C仍集体，不把每个成员各宣称验证成功。两个竞争series、普通章标题、另一公司或问题、前文缺失及预算不容纳均defer。
4. typed summary/public-context链检查target与context refs同数值offset也不混映、原文SHA/locator/parser/否定/计划/日期/单位原样、所有支持与上下文事先计入同budget。重复page pdf_block号码必须按(source,page,block)计，不得低估。
5. 真实问题与新组合先RED留证。无需每小步人审/签收。

## 阶段B — 现source owner生产接线

### B1 完整组件：共享预算与线性metadata索引（已正常发布、精确CI绿）

不与B2混签：B1只包含已完成的test_source_metadata_budget.py九项及两owner改动，当时跨页RED仍隔离。包external-context只索引一次、exclusions只union一次；每个实际member/context fanout、section heads×body和排序在扩展前扣现WorkBudget。几何局部200K只是同parent嵌套上限，不克隆余额；预算不足在source owner返回有限partial，不能释放半句。

独审两个预遍历遗漏先写反例，RED7PASS/2FAIL，修后集中739PASS/50.52s。之前733PASS/4FAIL是新测试未定义fixture及deepcopy不兼容不可变MappingProxy，已改为正确source_case及递归全字段快照；保留失败日志，不修改生产IR迁就pickle。两预遍历修复为headings在prose成功后单独预扣；native sections先按len预扣再chain，预算0时真实ID访问0。

### B2 剩余物理与指代闭合（OPEN）

物理组件现30行为反控/8依赖与性能控制/既有states及cache集中219PASS10.11s；最终不同agent27有限PASS8.51s（含5个逐owner CRLF等价反控）已签精确5源码/2测试SHA的PASS_PHYSICAL_BUDGET_CACHE_COMPONENT，自有Temp删除。不能忽略实源接线：真实PDF IR此前mime_type=None，已先RED后在唯一PDF parser声明实际格式；全source coverage_complete含细表deferred，不能因此全局关闭物理处理再让半句退回singleton。现按完整coarse正文和pair实际opaque/deferred状态判断，pair未知只defer该pending依赖；页9缺细表不能禁页7→8已观察的延续。复用同account，当前未知column不伪造证明。

共享statement边界复用operating_states脚本/issuer/NP/aux grammar，修繁体新issuer及English新产品主语；首个真实predicate只扫描subject一次，不能遍历每个后续predicate形成N²或借object当subject。Inventory1.8补实际5个共享grammar/matching/兼容owner源字节hash，不仅依赖import方偶然变化。

真实最新0收费三源仍10/10、7/7、8/8 source及canonical；实际parent work6106955/12820408/7975948未超16M，原件/gold不变、0copy/0POST、自有Temp删除。历史第一次physical回放的PDF MIME和全局coverage使新flow未生效，保留该收据，不把它代签当前实际路径，也不称全部语义质量绿。

### FF/CWP 最终读取端口（已按producer→consumer顺序发布、精确CI绿、安装完成）

CWP source_reader_cli可选--include-canonical-identity，由现security_code唯一owner投影market/security_id（schema source-canonical-identity/1），manifest保持观察值。现CLI复用open_described_version一次metadata观察与字节验证，原global/source lineage指纹兼容，旧hash不作权限阻断；显式None的not-applicable scope与未观察由sentinel区分，避免重复读取。5新及既有reader/identity/CLI共59PASS37.37s；两reader最终SHA与FF跨仓独审相同。

FF当前manifest的future/invalid/None不再继承旧query资格，使用已有date primitive；provider未知不能满足显式fmp；FF严格消费CWP canonical projection、legacy严格值比对，不再抄市场normalizer。原作者工区不改，根修在ROOT独立FF工区，独审29unique跨次通过非伪造单轮全绿。

- native_continuity只负责可观察物理proof，原同页edge/native_range保持严格；跨页原多span的closure planner返回reference-only包与不足诊断，不生成新原文。
- 入口在narrative_reading._prose_reading_packages -> _candidates carrier替换之前。旧body windows由新完整group消费/替换；同unit不得多个analysis owner静默最后覆盖。独立context可共享但不能暗变第二body owner。
- 只有structure诊断REPEATED_RUNNING_HEADER等已证明的ID可跳家具；excluded_furniture union包含TOC，不能全跳。列None相等、matching margins alone、no_column_gap不是现成单列证明。
- SourceOperatingSession.groups已能暂态CJK连接并返回5类原unit refs。新增referent proof由现operating_states owner复用prepared views/NP/对象规则，不能PDF adapter再造产品词典。明确unique/collective/ambiguous/missing与真实上下文refs；context refs原始namespace不得送_original_refs当target坐标重映。
- citation_support_views/required_context_unit_ids原端口保持；project原子上下文/公共最多2视图、typed execution原上限不放宽。缺proof在现deferred/withheld通道说明，不加人工许可。

## 阶段C — 大节点验收与发布

一次集中相关unit/integration/typed-public-context + 不同agent最终源码独审，全修真实发现后正常提交并线推送并核精确CI。真实CN/HK/US0收费源检查，再按母现配置/同累计ledger依次真实供应商摘要与缓存/FF-RF C。源码变动与收据按版本绑定，不把历史成功重签新SHA；测试owned目录原样恢复，生产raw/config/gold不写。

## 资源与范围

仍同WorkBudget16M、96spans/48kchars、物理8原unit/4个(source,page,block)/2048chars、draft56KiB/summary64KiB/execution32KiB。必要先行词也计原block/unit/char，不能作为freecontext绕限。实际CN p17/9–14全纳为5blocks，若无法证明更小真实充分context则诚实defer，不升上限/猜单个产品。

先建立一次metadata索引和有界邻窗，最多常数邻居/每scope有限已读上下文；每次新观察预扣原account，耗尽不能重启balance或释放半句。原paid run/未知费用不改，当前累计742228tokens/$0.421556proxy、历史unknown7+401新hold保留；限2Mtokens/$20，供应商按真实现配置，不读/打印密钥。

## Next Step

RF最终pin9669c4d7精确CI已success；本次PWF汇总正常提交/推送后，不重复接收/发布这两卡。下一工程节点：按最终接口先TDD写有界先行词（非event描述同样检查）与original/analysis namespace、原始联合限额及不重复扫描反例，再在现唯一owner接线。保留原文fallback只读视图，先readiness/context后单一graph与fact；未知/多义/超过原4blocks/8units/2048chars仅该卡defer，不编公司特例/raise上限/克隆16M余额。真实三源仅在完整节点完成后回放一次并独立内容检查，随后正式三供应商摘要及收费/activation/同跨run缓存/FF-RF C；holdout/RF循环仍OPEN。
