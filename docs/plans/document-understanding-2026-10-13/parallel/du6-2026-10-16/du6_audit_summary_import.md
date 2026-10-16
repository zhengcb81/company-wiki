# DU6-AUDIT-IMPORT：真实公开摘要导入与审查接线

## 0. 调度状态与独占工区

- 状态：**PREPARING**。此卡已备，不表示工作树已创建、作者已开工或真实验收完成。
- 责任仓：`revenue-forecast-audit`。
- 预定工作目录：`C:/Users/郑曾波/Projects/revenue-forecast-audit-du6-import`。
- 预定分支：`codex/du6-audit-import-20261016`；由 ROOT 创建/交接，作者不自行切换共享主目录。
- 仓内独立 PWF：`docs/plans/du6-import-2026-10-16/{task_plan,findings,progress}.md`。
- 已调查本地 main：`a3f36d1`，包含 DU5 合并 `58b2797`；启动时记录 ROOT 实际交接的完整 base SHA。若 ROOT 推进了主线，读已提交基线及本卡，不能从旧卡恢复已修复的 DU5 代码。
- ROOT 独占 CWP 统一来源准备/预算、FORM/STATE/TABLE 生产接线、v4 和跨仓最终验收。此卡不写这些路径。
- 本卡只在 A/B/C 大节点集中审查，不增加逐文件签收、逐材料批准或每小步全仓测试。

## 1. 目标、实际缺口与完成边界

DU5 已交付并修复 `summary-review-map/1` → 来源盲包 → 输出逐 claim 审查 → 同分母比较。但当前 `tools/run_summary_review_e2e.py` 仍以 `build_holdout_source_map/build_candidate_map/build_old_case_maps` 手组输入，其中候选草稿明确是 synthetic。现有三种 CLI 的通过不能证明真正生产 bundle 已进入该审查链。

本卡将**已发布、可实际读取的 CWP NarrativeBundle** 无损转换为现有 DU5 map，直接复用 DU5 prepare/attach/compare。交付一个薄只读 CLI、明确字段映射、集中测试和实际 CLI 联调。不给模型发请求，不重新生成摘要、不写预测、不改 CWP 解析/选择，不做新语义评分器。

成功意味着真实 claim/引用/原语言/版本和范围进入审查链，旧报告/未知/失败不丢；不意味着摘要事实正确、全文业务召回完整或母 PWF 完成。

## 2. 先读与已存在的接口

先读本仓 AGENTS、当前 `skills/revenue-forecast-audit/SKILL.md`、`references/review-storage.md`、`references/summary-semantic-review.md`、DU5 PWF 的 ROOT 接收收尾及以下实际源码。结构调查优先 CodeGraph；已知文件内字段/字面值可直接读。

### 2.1 当前公开输入，不能等待未来 v4

CWP 仓只读参考：

| 合同/入口 | 当前定义 | 本卡用途 |
|---|---|---|
| `narrative-bundle/2.0`、`narrative-bundle/3.0` | `src/company_wiki/automation/narrative_contracts.py` 的 `NarrativeBundle` | 原始来源与 official JSON 投影的已公开最终产物 |
| `BundleSummaryValue`、`SummaryClaim` | 同文件；`source_catalog/narrative_evidence.py` | `summary.draft.claims` 的真实内容和引用 |
| EvidenceSpan `schema_version=1.0.0` | `source_contract/evidence_span.py` | span_id、source_id、locator、raw_text、structured_value、parser/version、质量 |
| `NarrativeTransportRead` | `automation/narrative_transport.py` | 已有读取返回的 data 与 receipt；历史 carrier 不等于新的当前读取 |
| 公开读取/引用层 | 同文件的 `NarrativeTransportReader` | 仅由现有来源拥有者提供读取产物，不绕开到 DB/真实目录 |

内部模型请求 None/v1/v2/v3/v4、`drafts_by_task`、新 FORM/STATE/TABLE 瞬时字段一律不是本卡输入。ROOT 未来即使切换模型，只要公开 bundle 合同不变，本卡继续可用。遇未知公开 schema 如实诊断 unsupported，不借未来字段猜着读。

### 2.2 必须复用的 audit 能力

- `summary_review_contracts.validate_map` 和现有 map/target/report 合同；不复制新一套验证器。
- `summary_review_packet.prepare_source_packet`、`prepare_output_packet`、`attach_review`、`compare_versions` 或它们真实 CLI。
- DU5 已有 output-packet/2 的一次性 fragment_registry，attachment/2 与 /1 历史兼容；不要重建重复全文结构。
- `audit_contracts` 的新 attempt 留证/原子写入和现有脱敏；W08 `EvidenceReader` 的明确根、locator 和整次有界读取。若用现有 DU5 reader 包装函数，沿当前实际参数调用。

本卡不修改上述核心模块。发现其真实缺陷先保留最小反例交 ROOT，不在白名单外修补或放宽断言。

## 3. 薄 CLI 与输入输出

保持标准库薄适配；不强制建立新 request/schema/authorization 信封。建议 CLI 参数在 A 节点冻结并在方法文档给出实际 `--help`：

```text
python -B skills/revenue-forecast-audit/scripts/summary_review_import.py \
  --bundle <现有公开bundle的JSON绝对路径> \
  --run-id <实际执行run_id> --attempt-id <实际执行attempt_id> \
  --out-root <新的owned输出根> \
  [--read-receipt <现有公开读取收据的绝对路径>] \
  [--source-inventory <已有summary-review-source-packet/1的绝对路径>] \
  [--evidence-root <本轮明确的只读carrier根>]
```

`--bundle` 消费已封存公开读取产物，不从底层 AUTO/objects 路径自行发现当前 bundle。确实没有本地正式产物时，使用已提交保留的小型公开合同样本；真实/合成边界严格标明，不触发 provider/LLM 补样本。`--read-receipt` 可缺失：carrier 实读记当前载体 observed SHA，来源是否为当前 generation 仍 unknown，不因为缺收据新增人工许可。

可用 `run.json` 的现有字段替代两个 ID 参数，但不得同时引入另一套运行身份规则或随意由文件名推 run/attempt。A 节点选一种实际参数后固定。

输出位于一次全新 attempt：

- `map.json`：现有 `summary-review-map/1`，只有真实可审 fragment 存在且映射无歧义时生成。
- `import-report.json`：字段映射/输入定位、carrier 实读观察、支持的公开版本、selected-only 或独立摘录范围、丢失/冲突/unknown/跳过原因、实际预算与大小。是资料诊断，不发语义 PASS。
- `attempt.json`：沿现有留证方式引用确切输入/输出，正文只一份。

这些是现有工具所需的数据与普通诊断文件，不新设版本许可协议。参数冲突、未知版本或本工具限额超出给具体原因；旧报告、来源和已有 attempt 不覆盖。

## 4. 字段逐项映射与不可推定事项

| 当前公开 bundle / 来源 | 现有 map 目标 | 严格语义 |
|---|---|---|
| 实际本次执行 run/attempt | `run_id` / `attempt_id` | 原样；不把生成新 import attempt 当成新的 RF 执行 |
| `source_metadata.document_kind` | `document_kind` | 用真实值；缺失不能按 title/市场猜。partial 记录诊断，不默认年报 |
| `versions`、各 span parser/version | `observed_versions` 与来源定位 | 已观察的值原样；未知保留 null。不把 Git HEAD 说成 installed runtime |
| `evidence_spans[].span_id` | `source_fragments[].fragment_id`、`source_ref.span_id` | 保留原生 ID，不能按顺序重编号，也不按相同文字合并不同位置 |
| `EvidenceSpan.raw_text` | fragment `text` | 原语言/原字节语义不改，不翻译/拼句/重新 OCR；null 不用 structured_value 的 repr 伪造正文 |
| `EvidenceSpan.source_id/locator` | fragment `source_ref` | 用该 span 自己的真实 source/locator；`/3.0` 不把 subject anchor 替换所有 span 母页 |
| carrier 的实际 JSON pointer | `source_ref.artifact/artifact_locator` | 指向实读 bundle/span；与原 PDF/page locator 分列。carrier 可打开不等于重新读过原件 |
| source/subject binding | 来源上下文和 import-report | `/2.0` 保留 source_ref；`/3.0` 保留真实 subject_binding 及其原生父引用，不退化为伪 raw 记录 |
| `structured_value.source_role` 等已有显式角色 | fragment `role`，原角色留证 | 仅对生产实际已声明的 question 角色作有限别名映射，使 DU5 question 诊断可用；保留 native role。不能看内容猜发言人/公司身份 |
| source 明确 data_period/unit/模态 | fragment 对应字段 | 只取已有字段及定位；正文出现数字不自动猜 unit/期间。无显式值则 null/unknown |
| `summary.draft.claims[].claim_id/text` | `claims[].claim_id/text` | 一条不丢、顺序原样、原语言。不得为凑金标切句重写 |
| claim `evidence_ids` | `claims[].support` | 精确自身 IDs，不加全 selected、不借其他 claim |
| claim `context_evidence_ids` | `claims[].context` | 精确独立 context；旧合同省略时表示没有显式 context 声明，不凭 QA 邻接自动补事实 |
| claim `claim_type/modality/needs_review` | 可用既有字段及 native 留证 | 原值不擅改；forecast/question/uncertain 等不能硬塞 actual/planned。DU5不支持的观察维度明确 unknown，不改旧核心词表 |
| claim 在真实 bundle 中的索引 | `claims[].text_locator` | 定位其真实 JSON 字段；不要把摘要文本定位到某个 source 原文段落 |
| 已选 `evidence_spans` | `selection.selected_fragment_ids` 与其证据 | 实际选择声明，不等于全文已读，也不等于摘要已覆盖 |
| `selection`、`quality_status`、`reading_context.unread` 等 | import-report 的范围/诊断 | 明确来源声明与本次观察；selected count、coverage_complete、verified 都不能替代独立业务召回判断 |
| 目标/审查报告引用 | `targets` / `reviews` | 新导入尚未审查时 null/空数组。不能复用旧 reviewed_scope 去冒认新 packet SHA |

保留每项映射实际路径与未取值原因，但不复制整个 reading_context 或模型请求进 map。禁止给自己支持不了的投影、locator、模态编出可信默认值。

## 5. selected-only 与独立 source inventory

### 5.1 没有 source inventory

公开 bundle 本质是精选资料；由它生成的来源包必须注明 **selected_evidence_only**。本卡可以验证“精选片段→摘要”和“摘要→自身支撑”的记录映射；**原文→选择的业务 recall 为 not_evaluated**。

范围说明写 import-report 和薄入口产物的 limitations，不改 DU5 核心，也不能向 coordinator 说“盲包已经全文审过”。未读/未拿到的原文不要伪造 span、target 或 reading_state。仅有 selected 的 blind 包虽排除了候选文本，仍有选择偏差，应如实说明。

### 5.2 提供 source inventory

`--source-inventory` 仅消费已有 DU5 `summary-review-source-packet/1`，不再发明库存 schema。它来自来源 reviewer 或既有 CWP 公开摘录的真实已读/未读记录；允许含未被候选选择的片段。适配器不得从 candidate claims 反向制造库存，也不复制 selected 改名成“全文原文”。

- 对确切原生 span ID/source/locator 的一致引用做连接，保留源包的 fragment ID 和范围声明；不同 ID 不按 quote 相同模糊合并。
- 库存 fragment ID 与 native span ID 使用同一原生命名时可直接连接；否则只采用已有明确 source_ref.span_id 的一对一映射，并在报告保留原引用对应关系。不得重写已冻结 target/reviewer 的 ID/哈希。
- 不能无歧义连接时给出 source_inventory_unlinked，不把不相同的解析版本说成“未选中”，也不宣布完整召回。保留 selected-only 可做的审查及库存不可比原因。
- 同 ID 却不同正文/来源/locator 是明确冲突，不能最后一条胜出。原始输入和诊断保留。
- inventory 可能本身只读了若干页/段；最大可主张的范围是该已读摘录范围，不自动升级为整份年报。
- 独立来源目标先由 reviewer 读取该包形成，DU5 source-only observation/hash 不证明审查时序。旧 target/claim 报告保持历史身份，新 import 不伪造独审时间或 signature。

## 6. 跳过、失败与资源边界

- `skipped_no_narrative` / `summary_not_needed` 按真实状态写 import-report；空 span 不捏造 placeholder 以通过 `validate_map`，可以不生成 map。
- partial、opaque/deferred、缺失 raw_text、未知角色、source-current 未验、支持/上下文引用缺失分别保留。可审 claim 不因旁支 unknown 全丢，也不将 unknown 计 PASS。
- 实际需要的 bundle/span 合同形状由当前公开责任层定义。适配器只检查自己映射所需字段，不能复制整套 CWP 身份/期间/raw SHA/权限校验。
- 同一次导入使用一个 reader/预算；重复引用同一 carrier 不能重开新预算。沿 DU5 当前 8 MiB 输入、16 MiB 输出及行/引用上限，额外资源配置只能更小，不静默放大。
- 薄入口不扫描生产根、安装目录、密钥、全部 runs 或公司池，不触发 source ensure/download/模型/worker。
- 不从 pipeline 临时结构或付费模型 raw response 绕开公开 bundle；既有读取收据缺失时说明历史观察范围，不冒称 production current verified。

## 7. 排他文件白名单

仅可写独立 audit worktree 下：

```text
skills/revenue-forecast-audit/scripts/summary_review_import.py
skills/revenue-forecast-audit/references/summary-review-import.md
tests/test_du6_summary_review_import.py
tests/fixtures/du6_summary_review_import/**
tools/run_summary_review_import_e2e.py
docs/plans/du6-import-2026-10-16/**
docs/handoffs/du6-audit-import/**
```

不预设额外 contract 文件或新 schema；适配逻辑确实大于一个小模块时在本卡 PWF 说明模块拆分理由并交 ROOT 确认界面，不能自行扩大白名单。这个说明是 owner 接口协调，不是每步人签。

禁止写 DU5 packet/contracts、既有测试与真实 fixtures、SKILL、四角色卡、audit_run、pool、review_protocol、W08 reader、安装/同步工具、母 PWF、其他仓库或作者树。ROOT 最后单点接 SKILL/角色调用入口及定点安装。无 Git stage/commit 范围外文件、无自动 merge main/push/建 remote。

## 8. 实施顺序和三个验收节点

### A — 合同核实、样本边界与真实 RED

1. 保存实际 base/工作树现状，只在白名单施工。
2. 在独立 PWF 写当前字段映射、已排除的旧 schema/暂态输入、实际 CLI 参数和清理方法。
3. 从**现已提交可读的公开 bundle/现有保留小摘录**取得必要样本，列原产物引用、源合同版本和最小抽取说明。不可因本机恰有大 AUTO 就整树复制。
4. 真实产物、真实摘录、真实历史审查、synthetic 合同边界各自标记。没有真实 `/3.0` 样本可先用明确 synthetic 合同样本验证代码，真实投影审查标 NOT_RUN，不能写成已验收。
5. 先写行为 RED，至少覆盖：claim 内容/顺序/ID丢失；support/context交换；同字不同源/位；母页与锚点混淆；question角色误作公司事实；实际模态不保真；selected-only冒称全文；empty/skip伪成功；旧收据冒认当前；重复预算/全文复制；覆盖既有 attempt。RED不是只有import缺函数。

### B — 责任实现与集中回归

按“输入实际读取→字段映射→来源/选择范围→生成现有map→现有DU5工具消费→普通诊断”实现，程序不发语义判决。

```text
python -B -X utf8 -m unittest discover -s tests -p test_du6_summary_review_import.py -v
python -B -X utf8 -m unittest discover -s tests -p "test_du5*summary*.py" -v
```

保留现 DU5 的原29 + ROOT19回归，不删改原断言/真实8PASS/6WARN/6FAIL。整仓测试仅在发布大节点由 ROOT 决定，不每小步重跑。发生邻包失败按真实责任记录，不绕过 gate 或修改金标。

### C — 实际 CLI E2E 与独立只读试用

```text
python -B -X utf8 tools/run_summary_review_import_e2e.py \
  --owned-root <最初不存在的测试绝对目录> --receipt <唯一交付绝对路径>
```

至少实际走：import → DU5 prepare source/output → attach-review → compare。调用真实 CLI，不用 mock stdout 代替。每条 child 记录实际 argv/exit/elapsed 和产物定位。

覆盖最小集合：

- 一份真实公开 `/2.0` bundle；一份 `/3.0` 合同样本（真实与合成明确分列，真实缺失即 NOT_RUN）。
- 至少一种问答/多 fragment 支撑场景，且有期间/单位/模态保真的反例。
- selected-only 与独立 inventory 两种范围；后一项含一个真实未选摘录，否则不能验证原文侧遗漏。
- carrier可打开但语义错误的负控；正确数字错误对象、context-only不成为support、旧attempt/材料变化不可比。
- 独立 reviewer 未参与实现，实际比对原 bundle 与导入包的全部 claim/reference 映射、范围和未知；可继续给旧摘要 FAIL，不能预设全绿。

可复用已有独审报告演示历史保留，但其 reviewed_scope 仍指向旧对象；不得修改旧 SHA 让其接受新包。新包若没有新的真实独立语义审查，标 not_reviewed；工程 E2E 不替代语义结论。

测试隔离：新测试根开跑前 absent，或明确保存原有清单；结束恢复原状。所有 child 的输出、map、临时解压/carrier 都在该根。只删本次新增测试文件，不动生产原件、fixtures、他人WIP或现有报告。保留小型收据/报告/SHA，原文通过引用。默认 0 网络/0供应商/0模型调用，费用0；host独立agent试读不伪装成provider API。

## 9. 交接、ROOT 接线和停止

交付 `docs/handoffs/du6-audit-import/handoff.md` 与 `handoff.json`，列：

```text
card_id=DU6-AUDIT-IMPORT
base_commit / implementation_commits / changed_files / source_sha256
actual_cli / exact_input_contracts / field_mapping_reference
fixture_manifest: real_record|real_excerpt|synthetic + origin + SHA
source_scope: selected_only|inventory_excerpt_scope + unavailable/unknown
A_red / B_focused / C_actual_cli_receipts
independent_review_reports / retained_failures / NOT_RUN
read_budget / retained_bytes / source_occurrence_counts
supplier_calls=0 / production_writes=0 / cleanup_before_after
ROOT_install_files / remaining_items / resume_entry
```

PWF 三文档写真实结果与唯一 Next Step；提交已验证白名单代码/小型证据至独立分支，交接完整 SHA 后 **STOP 等 ROOT 接收**，不合并主线、不安装、不新建远端。本仓目前无 origin，不能把“已提交”说成“已推远端”。

ROOT 接收：核真实映射与独立试读→集中跨边界验收→本地主线正常并线→仅相关技能文件定点安装→把真实原三/新三公司摘要审查入口接入母计划。接收不应重跑整套已知同因付费研究；本卡不代替 CWP 正式摘要、默认切换或 RF 买方模型验收。
