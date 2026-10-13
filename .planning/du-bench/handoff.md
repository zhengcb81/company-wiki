# DU-BENCH 交接

PLAN_ID=du-bench ｜ 分支 `codex/du-benchmark-20261013` ｜ base `7f6f7cbd`

工作目录：`C:/Users/郑曾波/Projects/_harness_worktrees/document-understanding-20261013/benchmark`

> **审计轮更新（第三轮）**：卡片要求的**最低关键集 14 项现已全部覆盖（0 缺口）**，
> 金标 15 份（开发 10 / holdout 5）、176 事实、128 关键。本轮另查出并修复了
> 4 个自身缺陷：召回分母把「读不到」当「没找到」、make_bindings 会覆盖掉 holdout
> 绑定、金标缺少 fact_scope 区分（叙述 vs 文档元信息）、以及卡片最低集无人守护。

## 1. 做了什么

在独占目录里建了一个**独立**的文档理解质量基准，它测两件当前流水线无法自测的事：

1. **真实遗漏** —— 原件里有、但没进精选证据或摘要的业务事实；
2. **幻觉** —— 观测断言了、但它自己的证据不支持的内容。

产物：

| 路径 | 作用 |
|---|---|
| `tools/document_understanding_benchmark/{schema,records,evaluate}.py` | 冻结 wire 与公开 `evaluate(observed, gold)` |
| `.../checkers.py`、`textutil.py` | 九维检查器与确定性文本/数值/语态原语 |
| `.../gold/*.json` | **15 份真实金标（176 事实，128 关键）** |
| `.../fixtures.py` | 5 份合成夹具，共 14,301 字节 |
| `.../mutations.py` | 19 类反例注入 + 三值判定 |
| `.../review.py` + `reviews/` | 独立语义复核 wire 与真实复核产物 |
| `.../controls.py` | **证明复核层不可省**的负对照 |
| `.../observer.py` | **只读**调用现有公共 parser/selector；含载体能力探测 |
| `.../recovery.py` | SHA+mtime 指纹、哨兵、owned 容器清理 |
| `.../holdout.json` | holdout 覆盖与补采清单 |
| `.../__main__.py` | offline / native / adapter 三模式 CLI |
| `.planning/du-bench/evidence.json` | 由运行产物**程序生成**的证据记录 |

金标事实全部**逐字读原件**写成。开发集（10）：恒锋 2020 增发、万润 IR、名创香港年报、
中微 2026Q1、中微 2026 半年报、鼎龙扫描确认函、世华科技 2026Q1（财务季报负例）、
微软 FY2025 10-K、MSFT FY2026Q4 电话会、TAL FY2024 20-F。
holdout（5）：广联达 2025Q1、雅克科技 2022Q1、阿里巴巴 FY2023、MongoDB FY2026 10-K、
NVIDIA FY2025 10-K —— 后两家美国公司由独立子代理逐字读取回报。
**没有**从 selector 输出反推期待值。

## 2. 边界

只写 `tools/document_understanding_benchmark/**` 与 `.planning/du-bench/**`。
未改 `src/`、其他 tests、生产配置、CI、另外两个 DU 包、母计划、RF/FF/Audit/Dayu/IQS。

关于 `pytest.ini`：它不是我该改的共享配置，所以没有加 `-m "not real_data"` 默认项。
真实原件测试改为**默认跳过**，只有设置 `DU_BENCH_ALLOW_REAL_DATA=1` 才跑，并且带 `real_data` marker 可按需单独选。

## 3. 怎么复跑

```bash
# A/B：纯离线、不联网、不调模型
python -X utf8 -m pytest tools/document_understanding_benchmark/tests -q
#   -> 100 passed, 7 skipped, 约 2 秒

# 离线 CLI（含反例与复核负对照）
python -X utf8 -m tools.document_understanding_benchmark \
    --mode offline --output <自有目录>

# 重建本机 bindings（含绝对路径，不提交；放仓库外保持工作树干净）
python -X utf8 -m tools.document_understanding_benchmark.make_bindings \
    --manifest docs/plans/document-understanding-2026-10-13/sample_manifest.json \
    --out ~/.du-bench/bindings.local.json \
    --repo-root C:/Users/郑曾波/Projects/company-wiki
#   -> bound 20/20

# C：真实原件只读回放
python -X utf8 -m tools.document_understanding_benchmark --mode native \
    --bindings ~/.du-bench/bindings.local.json --output <自有目录> \
    --probe-config config/source_catalog.yaml

# 带独立语义复核
python -X utf8 -m tools.document_understanding_benchmark --mode native \
    --bindings ~/.du-bench/bindings.local.json --output <自有目录> \
    --review tools/document_understanding_benchmark/reviews/fixtures-independent-review.json
```

退出码：`0` 全 PASS、`1` 有 FAIL、`2` 拒绝运行、`3` 有 PARTIAL/UNAVAILABLE。

## 4. A/B/C 实测

### A —— 金标与反例冻结，记录基线真实结果

金标 15 份：开发 10、**holdout 5**（A 股 2、H 股 1、US 2），176 事实、128 关键。
单份引文最大 2,094 字节，上限 8KiB。卡片最低关键集 **14/14 覆盖，0 缺口**（有测试守护）。

**基线真实召回，开发与 holdout 分开报，从不合并：**

| 划分 | 文档 | 关键召回 | 可评/声明 | 覆盖 | 叙述类(全事实) | 文档元信息 |
|---|---:|---|---:|---:|---|---:|
| development | 10 | **10/57 = 0.175** | 57/83 | 0.687 | 13/68 = 0.191 | **0/9 = 0.000** |
| **holdout** | 5 | **0/22 = 0.000** | 22/45 | 0.489 | **0/36 = 0.000** | n/a |

分母口径说明：`UNAVAILABLE`（读不到）**不计入分母**，另列 `coverage`。
所以「读不到」不会被报成「没找到」——这正是本轮修掉的一个自身缺陷。

逐份：

| 样本 | 划分 | 路由 kind | 选中/候选 | units | 关键召回 |
|---|---|---|---:|---:|---:|
| cn-equity（恒锋） | dev | `unknown` | 96/449 | 3,224 | 0.000 |
| cn-h1（中微半年报） | dev | `semi_annual_report` | 96/369 | 5,500 | 0.250 |
| cn-ipo-confirmation（鼎龙） | dev | **`prospectus`** | 0/0 | 0 | n/a（整页不透明） |
| cn-ir（万润） | dev | `investor_relations` | **11/11** | 302 | 0.143 |
| cn-q-business（中微Q1） | dev | `quarterly_report` | 28/28 | 579 | 0.667 |
| cn-q-sparse（世华季报） | dev | `quarterly_report` | **0/0** | 429 | 0.000 |
| hk-annual（名创） | dev | `annual_report` | 96/254 | 6,502 | 0.000 |
| us-10k（微软10-K） | dev | — | — | — | n/a（载体不支持） |
| us-txt（MSFT电话会） | dev | **`investor_call_transcript`** | 96/107 | 489 | **0.091** |
| us-20f（TAL 20-F） | dev | — | — | — | n/a（载体不支持） |
| holdout-cn-glodon-q1 | **HOLD** | `quarterly_report` | **0/0** | 257 | 0.000 |
| holdout-cn-yake-q1 | **HOLD** | `quarterly_report` | **2/2** | 369 | 0.000 |
| holdout-hk-alibaba | **HOLD** | `annual_report` | 96/2,221 | 18,038 | 0.000 |
| holdout-us-mongodb | **HOLD** | — | — | — | n/a（载体不支持） |
| holdout-us-nvidia | **HOLD** | — | — | — | n/a（载体不支持） |

### B —— oracle 与离线 CLI 绿，故意坏观测必须失败

- 默认套件 **105 passed / 7 skipped / 0 failed**，约 2.3 秒。
- 离线 CLI：5 夹具、4 PASS + 1 PARTIAL（故意不透明的扫描件）、
  14,301 / 204,800 字节、0 网络 / 0 模型 / 0 付费调用。
- **反例 53/53 全部检出**，42 条 NOT_APPLICABLE。三值判定是刻意的。
- **复核层负对照**：注入 3 个**确定性检查完全看不见**的语义缺陷，
  实测 **3/3 全部 PASS 确定性检查、3/3 全部被复核判 FAIL**；
  另证明**全 ENTAILED 的复核无法把确定性 FAIL 变成通过**。
- 独立性：oracle 不 import `company_wiki`；只有 `observer.py` 调现有公共入口。

### C —— 原生回放、恢复与资源

15 份真实原件按 SHA 解析，**原件 SHA 与 mtime 全部不变**，
`config/source_catalog.yaml` 指纹不变（2 探针），哨兵复原，
**0 原件复制 / 0 网络 / 0 模型 / 0 付费**。

## 5. 本轮（审计轮）新发现

### 发现 1：候选生成是瓶颈，且又多了两份「零候选」实证

- `cn-q-sparse`（世华科技 2026Q1，**429 units → 0 候选**，`status=needs_review`）
- `holdout-cn-glodon-q1`（**257 units → 0 候选**）
- `holdout-cn-yake-q1`（369 units → 2 候选）
- `cn-ir`（11/11 全选中，10 条金标仍缺 9 条）

四份互相独立地指向同一结论：**瓶颈在候选生成，不在选择上限**。

### 发现 2：文档元信息召回 **0/9** —— 没有前置层

开发集 9 条 `document_meta` 关键事实（是否经审计、财年 vs 日历年、目录 vs 正文、
页数、来源出处、截断、Q&A 无标题）**一条都没进证据**。这与叙述类 0.191 是两类问题：
叙述类是选得不够，元信息类是**根本没有层去承载**。

### 发现 3：电话会通路能跑，但角色事实几乎全丢

`us-txt` 载体受支持且路由正确（`investor_call_transcript`），96/107 选中、489 units、
`scan=complete` —— 但 11 条关键事实只召回 **1 条**（0.091），角色与语态类事实几乎全缺。

### 发现 4：US 文件仍无通路（4 份 .htm 全部 UNAVAILABLE）

生产回放路径只有 PDF 与 transcript 两种格式；实测两份真实 10-K 走唯一 HTML 通路得
`units=0` + `transcript_start_missing`，抽出文本还被内联 XBRL 分类法 token 打头。
所以 US 记为 **UNAVAILABLE by carrier**，运行报告显式列出不支持的载体。

### 发现 5：`cn-ipo-confirmation` 精确复现标题陷阱

一页扫描确认意见被判成 **`prospectus`**，0 units / 0 候选，唯一一页不透明。

## 6. 独立语义复核（把 `semantics.entailment` 推进一步）

- 真实复核产物：`.../reviews/fixtures-independent-review.json`，
  由独立子代理复核 5 个夹具、11 条 claim，**11 条全部 ENTAILED**。
- 复核者主动指出一条**方法论缺口**：该夹具集里**没有种子化语义缺陷**，
  所以它本身不能作为有区分度的负对照。→ 我据此补了 `controls.py`（见 B 节）。
- 复核者另提 4 条 advisory gap（已记入 handoff.json）：日期不在引文中、
  引文无法证明 28,000 万元仍是未花的计划、土地款是子项而非项目总额、三处 quantity 上的 `period:"2020"` 噪声。
- **native 的 `semantics.entailment` 仍是 NOT_EVALUATED**：基线在 11 份文档上
  **实测产出 0 条 claim、0 个 semantic unit**，没有东西可复核。要推进必须由 ROOT 接上摘要产出。

## 7. 每维度分母（今天能支持的真实分母）

| 维度 | 开发 | holdout | 状态 |
|---|---:|---:|---|
| route_type | 10 | 3 | 可测（4 份 US 因载体不支持无法测） |
| critical_fact_recall | 10 文档 / 83 关键 | 5 文档 / 45 关键 | 可测（分母另计 coverage） |
| context_completeness | 0 | 0 | 基线无结构，NOT_EVALUATED |
| citation_replay | 10 | 3 | 可测 |
| role_modality_quantity | 0 | 0 | 基线无 claims，NOT_EVALUATED |
| bilingual_redundancy | 1 | 1 | 名创 + 阿里巴巴 |
| derived_space / time_resource | 10 | 3 | 可测（基准自有默认上限） |
| document_meta（前置层） | 9 关键 | 0 | 可测且**全 0** —— 说明缺层 |
| untested_semantics | 11 夹具 claim 已复核 | — | native 无 claim，仍 NOT_EVALUATED |

## 7b. 本轮修掉的基准自身缺陷（4 个）

1. **召回分母把「读不到」当「没找到」**：`critical_fact_recall` 用的是声明分母，
   而同一文件的 `fact_recall` 用的是扣掉 UNAVAILABLE 的有效分母 —— 同一概念两种口径。
   未读文档因此被报成 `0.000` 召回（读起来像「找了但一条没找到」）。
   已统一为有效分母，并新增 `coverage` 与 `*_denominator_declared`，两条回归测试守护。
2. **`make_bindings` 会覆盖 holdout 绑定**：manifest 只有 20 份调查样本，
   而 holdout 5 份不在其中；重建 bindings 会静默丢弃它们，丢绑定与「原件缺失」在报告里
   **无法区分**。改为默认保留非 manifest 条目（`--replace` 才清空），并有回归测试。
   *本轮真的踩到了这个坑*：一次重建把 5 条 holdout 绑定清掉，holdout 覆盖一度掉到 0.000。
3. **金标缺叙述/元信息区分**：`us-txt` 的 14 条事实混了「业务内容」与「文档属性」
   （参与者名单、来源出处、截断、财季 vs 日历年）。混在一个分母里会把
   「选择器该带的事实」与「前置层该给的事实」算成同一个分数。新增 `fact_scope`
   字段（默认 `narrative`）并分开报。
4. **卡片最低关键集无人守护**：审计发现 9 项里缺 4 项（`cn-q-sparse`、`us-10k`、
   `us-txt`、`us-20f` 全无金标）。已补齐并加测试，改名/删档/掏空金标都会让它失败。

## 8. 尚不能自动检验的语义项

- 摘要句是否真被其引用证据蕴含（需独立复核；结果里带 `spot_read_list`）。
- 数值在单位/期间/口径标签之外是否经济上正确。
- 表格在从未被抽取时是否完整。
- 双语对是真翻译还是另一语言车道里的另一件事。
- 公司计划是否现实（只能判「说成计划」还是「说成既成事实」）。
- 图表内容——基线从不读，金标也不断言。
- **给正确数字附加的无支撑解读**：实测为确定性盲区（见 B 节负对照）。

## 9. 资料补采请求（交给 ROOT）

- **REQ-1（高）**：为 SEC 文件加 HTML 前端。实测两份真实 10-K 走现有唯一 HTML 通路得 0 units，US 质量今天无法评分。
- REQ-2（高）真实 US S-1/F-1｜REQ-3（中）真实 8-K/6-K 且附件是业务文件｜
  REQ-4（中）修订版+原版配对｜REQ-5（低）非电商 H 股年报。

## 10. 0 付费 / 0 原件写入 / 恢复 / 体积

- **0 模型调用、0 付费调用、0 网络调用、0 原件复制、0 原件写入、0 原件 SHA 或 mtime 变化**。
- 恢复：哨兵写入自有容器并逐字节校验；清理只删带 `.du-bench-owned` 标记的目录，
  未标记目录**拒绝删除**（有测试断言）。
- bindings 放在仓库外 `~/.du-bench/`，工作树保持干净。
- 体积：金标单份引文 ≤842 字节；合成夹具 14,301 字节（预算 204,800）。
- 峰值 RSS 实测：native 116 MiB、offline 20 MiB。

## 11. 需要 ROOT 做的事

1. **为 SEC 文件加 HTML 前端**（REQ-1）——否则 4 份 US 文档（含 2 份 holdout）无法评分。
2. 通过 `observer.observe_du_adapter` 注入真实 `du-input/1` 适配器，
   让 `context_completeness` 与 `role_modality_quantity` 不再是 NOT_EVALUATED；
   并接上摘要产出，`semantics.entailment` 才有 claim 可复核。
3. **补一个文档元信息/前置层**：`document_meta` 召回实测 **0/9**，
   说明「是否经审计、财年口径、目录 vs 正文、页数、来源出处」这类事实没有任何层承载。
4. 用 `evaluate(limits=...)` 传 ROOT 的真实派生/时间上限。
5. 决定五个补采请求。

**需要 ROOT 注意的基线事实**：开发集关键召回 0.175（叙述类 0.191）、holdout 0.000（叙述类 0/36），
且**两份真实 A 股季报产出 0 个候选**（世华 429 units、广联达 257 units）——
这是候选生成层的缺陷，不是上限问题。电话会通路虽可用，角色/语态事实召回仅 0.091。

本条线到此停止，不再自行推进；合主线、三包集成与真实摘要大节点归 ROOT。
