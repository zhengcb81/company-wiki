# N6-BUDGET 交接：固定配额的整组去重与业务选材

- lane_id：`N6-BUDGET`，分支 `codex/n6-budget`，worktree `C:/Users/郑曾波/Projects/cwp-lanes-20261006/n6-budget`
- base_head：`58b74d07dd4f8b589c134ef9060a689864a8c089`（卡与启动PWF提交 `9495459` 之上施工）
- 输入唯一依据：`docs/implementation/handoffs/N6-BUDGET/INPUT_CARD.md`；PWF 仅 `.planning/n6-budget/` 三文件（PLAN_ID=n6-budget）
- 0 下载 / 0 LLM / 0 费用 / 无生产批次；源仓只读；原件、配置、数据库、CI、外仓未改

## 1. 交付文件（唯一写集）

| 类别 | 路径 |
|---|---|
| 实现 | `src/company_wiki/source_catalog/n6_budget_dedup.py`（新增）、`narrative_budget.py`、`narrative_finalize.py` |
| 测试 | `tests/unit/test_n6_group_dedup.py`、`tests/unit/test_n6_budget_selection.py`、`tests/integration/test_n6_budget_packages.py`（新增） |
| 夹具 | `tests/fixtures/n6_budget/real_candidates.json`（26,727 B，≤256 KiB） |
| 计划 | `.planning/n6-budget/task_plan.md`、`findings.md`、`progress.md` |
| 交接 | `docs/implementation/handoffs/N6-BUDGET/HANDOFF.md`、`handoff.json` |

未触碰：`narrative_evidence/document/routing/candidates/context/group_candidates/neighbors/pdf_groups`、旧测试、`benchmarks/`、golden/report、`config/`、原件、数据库、CI、外仓。

## 2. 接口与兼容性

保留（签名与返回形状未变）：

```python
EvidenceCandidate(unit, topics, reasons, score)
group_ids: Mapping[str, str]                 # unit_id -> 输入事件组id
BudgetItem(item_id, group_id, page_key, locator, order_key, reasons, score, is_heading, payload)
select_budget_items(items, *, limit) -> tuple[BudgetItem, ...]
finalize_selection(structure, route, candidates, *, group_ids, heading_pattern,
                   dropped_financial_count) -> NarrativeEvidencePackage
```

新增（供 MAIN 接线与质检，均只依赖当前输入）：

```python
# src/company_wiki/source_catalog/n6_budget_dedup.py
DedupDrop(unit_id, locator, group_id, kept_unit_id, reason, text_sha256)
DedupResult(candidates, group_ids, drops)
deduplicate_candidates(candidates, group_ids) -> DedupResult
normalize_text(text) -> str          # 去空白 + 表格竖线 + casefold
role_class(source_role) -> str       # statement / question / other

# src/company_wiki/source_catalog/narrative_budget.py
BudgetDiagnostic(item_id, bundle_key, group_id, category, item_count, item_ids,
                 locator, reason)     # reason ∈ {group_exceeds_limit, budget_full}
budget_diagnostics(items, *, limit) -> tuple[BudgetDiagnostic, ...]
```

**新增映射（MAIN 接线用）**：`DedupResult.group_ids` 是“有效 selection_group_id”——输入组**同时**含 statement(`company_filing`/`management`) 与 question(`analyst`/`investor_question`) 时才拆成 `<原id>:statement` / `<原id>:question`；同质组保持原 id 不变，因此生产上绝大多数 span 的 `selection_group_id` 与旧版逐字节一致。`finalize_selection` 内部已用该映射同时喂 `BudgetItem.group_id` 与 `EvidenceSpan.structured_value.selection_group_id`（同一事件组 = 同一预算 bundle = 同一 summary 分组）。

**计数新定义（不可回退）**：`candidate_count` = 进入 finalize 的候选数（去重前）；`omitted_candidate_count` = `candidate_count - 入选span数`，因此**去重删项不再藏进计数**（旧行为是先缩 candidate_count 再算 omitted，属“为好看瞒删”）。`omitted == 0 ⟺ status == "selected"` 这一既有等价关系保持不变。`dropped_financial_count`、`source_units`、`selection_limit`、`coverage_complete` 语义不变；source-only 状态集（selected/partial/skipped_no_narrative/needs_review/blocked）不变，`partial`/`needs_review` 仍不需人工签收。本线不改空结果政策（`_status` 的职责与 IR 整份 skip 归 MAIN）。

**未改**：`_source` reader 公共合同、selector 版本（`NARRATIVE_PARSER_VERSION` 未动）、summary 模型、身份生成与旧 `evidence_id`/`locator`（原 artifact 可读性由 MAIN 做跨版本回放）。

## 3. 算法与理由

### 3.1 整组保守去重（`n6_budget_dedup`）

1. **同 unit 只留一条**：同一 unit 被多次富化时按（分数↓、表格行、坐标、unit_id）取最优，reason=`same_unit_repeat`。
2. **分桶 = 输出组id**：先做角色拆分再分桶，保证“预算 bundle == selection_group_id == 角色同质”。
3. **组内**：同（归一化文本, role）折叠，表格行优先，reason=`intra_group_repeat`；组永远至少留 1 条，不会被拆空。
4. **组间**：签名 = 排序后的 (归一化文本, role) 集合；按（签名更大优先，分数更高，坐标数值更早，unit_id）排序，**签名相等或被包含者整组丢弃**（`duplicate_event_group` / `contained_group`）；互不包含（部分重叠）→ 保守保留。只按内容证明同一事件，绝不按全文 SHA 删原件，也从不读磁盘。
5. 归一化与基准 `duplicate` 定义一致（去空白、去 `|`/`｜`、casefold），因此“空白/表格分隔差异”能合并，而项目/期间/公司/否定/角色差异一定保留（只差字符即不同签名）。
6. 每条 drop 都带真实 `locator` + `text_sha256` + `kept_unit_id` 配对；集成测试断言**被丢内容必在幸存者中出现**（无唯一信息丢失）。

不采用的备选：成员级跨组去重（离线实测会拆掉组上下文、S05 反丢 1 个 required，见 `.planning/n6-budget/findings.md` 第 3 节）；仅同签名整组去重（S06 收益不足）。

### 3.2 固定配额选材（`narrative_budget`）

- `len(items) <= limit` 快路、`_reserve` 两个 reserved reason、组原子且成本=实际 span 数、limit<1 与重复 item_id 报错：全部保持。
- 每轮**每页至多出一件**（跨页覆盖，旧 T1 依赖），但页内与页间都按动态序取：
  `(超过类别配额?, 类别序, priority, -cost, bundle_key, 数值页序)`；
  **类别软配额** `fair_share = ceil(limit / 活跃类别数)`（按 span 计），仅当 `limit >= 2 × 活跃类别数` 才启用——小预算完全沿用既有优先级+按页轮转（旧断言 `test_explicit_capacity_and_certification_constraints_win_tight_prospectus_budget` 即靠此保持），大预算下高频泛化类别到额即降序，让产品验证/产能募投/行业需求拿到份额；**软**配额只降序不剔除，别家需求耗尽后可回填，因此不会欠配。
- `group_exceeds_limit`（成本 > limit，永远放不下 → 整组舍弃）与 `budget_full`（出价时放不下）两类诊断，由 `budget_diagnostics` 给出，不改 `select_budget_items` 返回形状。
- 纯函数：只用传入 `items`；测试用硬失败的 `builtins.open` 证明不读磁盘/模型。

## 4. RED / GREEN

| 阶段 | 命令 | 结果 | 秒 |
|---|---|---|---|
| RED-1（缺API） | `python -m pytest -p no:cacheprovider --basetemp tmp/n6bt tests/unit/test_n6_budget_selection.py tests/unit/test_n6_group_dedup.py tests/integration/test_n6_budget_packages.py` | 3 collection errors | 2.38 |
| RED-2（旧行为桩） | 同上 | **13 failed, 19 passed** | 1.60 |
| GREEN（最终） | 同上（`PLAN_ID=n6-budget PYTHONPATH=$PWD/src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 CW_BASETEMP_FALLBACK_ROOT=$PWD/tmp`） | **32 passed** | 1.57 |
| 旧短测试 | `python -m pytest ... tests/unit/test_narrative_evidence.py tests/unit/test_narrative_selection_architecture.py` | **121 passed** | 1.91 |
| 旧全量narrative | `python -m pytest ... tests/unit -k narrative` | **584 passed** | 55.19 |
| 预算/去重相关 | `python -m pytest ... tests/unit/test_narrative_partial_summary.py tests/unit/test_narrative_english_business_recall.py tests/unit/test_narrative_evidence_view_query.py tests/unit/test_narrative_select_handler.py tests/unit/test_narrative_retrieval.py tests/integration/test_narrative_run_budget.py tests/integration/test_s5_narrative_evidence_view.py` | **122 passed, 1 failed** | 53.31 |
| 静态 | `python -m ruff check src/company_wiki/source_catalog/narrative_finalize.py src/company_wiki/source_catalog/narrative_budget.py src/company_wiki/source_catalog/n6_budget_dedup.py tests/unit/test_n6_budget_selection.py tests/unit/test_n6_group_dedup.py tests/integration/test_n6_budget_packages.py` | All checks passed | — |

唯一失败 `tests/integration/test_s5_narrative_evidence_view.py::test_real_transcript_search_lookup_and_directory_restoration`：它读 `../earnings-transcripts/earnings-transcripts/transcripts/MSFT/MSFT_Q4_2026_earnings_call.txt`（相对本仓父目录的外部 sibling 原件），该目录只在 source 仓旁存在、lane worktree 旁不存在，失败发生在第245行 `original.read_bytes()`，先于任何选择代码 → **环境依赖的既有失败，与本线无关**（未改该测试，未假报通过）。

旧断言冲突：**无**。三条 `status == "selected"` 与 `omitted == candidate_count - selected` 的旧断言在其输入下均无重复候选，全部保持。

## 5. 真实材料与测量（real vs fixture）

- **真实**：S01/S05/S06 夹具中的 `raw_text`、`coordinates`、`source_id`、`source_sha256` 全部逐字来自 `benchmarks/narrative_document_types/samples.json` 注册原件（只读打开，SHA 夹具内自校验并与注册表比对）。候选行（topics/reasons/score/group_id）**手工组装**，夹具 `provenance.real_vs_fixture = real_original_text_hand_assembled_candidates` 明确声明“不是生产 parser/selector 输出”。
- **合成**：两单测的 NarrativeUnit/BudgetItem 为合成，走冻结接口。
- **测量**（同一批只读候选回放，baseline=旧算法，n6=本次实现；S09 无本地原件未纳入）：

| 样本 | 选中/limit | required | 选中重复 | 最大类别占比 |
|---|---|---|---|---|
| S01 | 96/96 → 96/96 | 1 → 1 | 1 → 0 | event 52 → 52 |
| S02 | 96/96 → 96/96 | 1 → 1 | 4 → 0 | event 75 → 75 |
| S03 | 15/96 → 15/96 | 3 → 3 | 0 → 0 | 不变 |
| S04 | 160/160 → 160/160 | 1 → 1 | 5 → 1 | event **146 → 76** |
| S05 | 160/160 → 160/160 | 2 → 2 | **24 → 1** | event **114 → 88** |
| S06 | 160/160 → **159/160** | **0 → 1** | **14 → 0** | event 68 → 72 |
| S07/S08 | 11/11、0/96 不变 | 3、0 | 0 | 不变 |
| **合计（28 个 required 点）** | — | **11 → 12** | **48 → 2** | noise 1 → 1 |

S06 少 1 个 span 是某组出价时放不下被**整组**舍弃（诊断 `budget_full`），符合“超大组完整舍弃”。加回 S09（未测量、基线 matched=1）后推算 required 12/33 → **13/33**；最终业务覆盖归总由 MAIN 用 9 样本正式回放确认。**本线不以更大配额获得绿灯**：96/160 未改。

## 6. 每示例去重前后账目（夹具三例）

去重前（候选 → 输入组，cost=span 数）→ 去重后 → 丢弃原因与来源 locator：

### S01（annual_report，limit=96）

- 去重前：`singleton …4d8694` p40 cost=1、`singleton …527070` p40 cost=1、`…e368bd1` p75 cost=5、`…41ad341` p40 cost=1、`…6c9723` p40 cost=1
- 去重后：kept=9，drops=**0**（无重复）
- 预算：selected_spans=9（4 组），dropped_groups=0

### S05（equity_offering_prospectus，limit=160）

- 去重前：`…4737bde4` p101 cost=2、`…9ecc8814` p101 cost=2、`…-certification-timeline:1` p161 cost=2、`…-certification-timeline:1` p3 cost=2（8 候选 / 7 个不同 unit）
- 去重后：kept=5，drops=**3**
  - `same_unit_repeat` `loc:v1/page:101/paragraph:3` → kept=`…651d208e`（同 unit 被富化两次，留分数 133 的记录）
  - `duplicate_event_group` `loc:v1/page:161/paragraph:25` → kept=`…735a0d98`
  - `duplicate_event_group` `loc:v1/page:161/paragraph:26` → kept=`…9b773dea`
    （p3 与 p161 两组签名完全相同：`航空数字` + `化集成中心项目需要进行合格供应商认证和产品认证，预计需要4-9 个月。`，按坐标数值取 p3 组为 canonical，p161 整组丢弃；两条被丢文本的归一化形式都能在 p3 幸存者中找到）
- 去重后组成本：`…4737bde4`=1、`…9ecc8814`=2、`…-certification-timeline:1`=2
- 预算：selected_spans=5（3 组），dropped_groups=0（limit 未约束）

### S06（convertible_bond_prospectus，limit=160）

- 去重前：`…44890b6` p43 cost=3、`…f054a2` p43 cost=2、`…a59c140e` p43 cost=2（7 候选 / 6 个不同 unit）
- 去重后：kept=6，drops=**1**
  - `same_unit_repeat` `loc:v1/page:43/paragraph:10` → kept=`…eb3e17aa`（同段落同时存在 score=3 与 score=94 两条候选记录）
- 去重后组成本：`…44890b6`=2、`…f054a2`=2、`…a59c140e`=2
- 预算：selected_spans=6（3 组），dropped_groups=0

预算丢弃原因样例（合成，见 `test_n6_budget_selection.py`）：成本 5 的组在 limit=4 下 `group_exceeds_limit`（`item_count=5`，`item_ids` 为整组，`locator` 为组内首件真实坐标）；成本可容纳但出价时放不下 → `budget_full`。两个 reason 之外不会出现其他值。

## 7. protection / cleanup / calls

- `originals_unchanged: true`：只读打开注册原件（`hashlib.sha256` 校验后比对 `samples.json`），未写、未移动、未删除任何 `companies/`、`config/`、数据库。
- `production_state_unchanged: true`、`owner_files_unchanged: true`：`git status` 仅上表白名单路径。
- `cleanup`：临时根 `tmp/n6bt`（`--basetemp`）在收口删除；`CW_BASETEMP_FALLBACK_ROOT` 指向仓内 `tmp/` 且测试后无残留；`tmp/` 下其余为本线开发脚本与回放抓取（gitignored，不入库）。
- `calls`：`model_posts=0, provider_http=0, downloads=0`；网络由 hermetic conftest 硬阻断，未绕过。
- 未做真实 ACL、未做完整大备份演练；未跑 9 样本正式 benchmark（归 MAIN 收口节点）。

## 8. main_wiring / remaining

**MAIN 需要做的**

1. 合线后跑一次 9 样本正式 benchmark 与 Worker→检索→RF E2E，确认 required/optional/noise/duplicate 与本线回放一致；`report/golden` 由 MAIN 决定是否随新计数重生成。
2. 关注计数语义变更：`candidate_count` 改为去重前、`omitted` 含去重；下游若按 `candidate_count` 估算“待处理候选”需同步。`status` 可能因文档内存在重复候选由 `selected` 变 `partial`（等价关系 `omitted==0 ⟺ selected` 未变）。
3. 使用新 API（可选）：质检/回放可用 `deduplicate_candidates(...).drops` 与 `budget_diagnostics(...)` 拿“去重/预算丢弃原因 + locator”；若要落库请由 MAIN 决定字段，本线不加 schema。
4. 角色拆分产生的 `<gid>:statement|question` 仅在输入组混角色时出现；若下游有按 `selection_group_id` 精确匹配的旧断言，需抽查。
5. 环境依赖失败（`test_real_transcript_search_lookup_and_directory_restoration`）需要在有 `../earnings-transcripts` 的环境复核。

**remaining（本线不做）**

- 未扩 96/160、未改 golden/阈值/公共合同/selector 版本；空结果政策与 `_status` 职责归 MAIN；未跑正式 Worker E2E；S09（无本地原件）未纳入回放。
- 诊断字段目前只存在内存，未新增持久化字段。
