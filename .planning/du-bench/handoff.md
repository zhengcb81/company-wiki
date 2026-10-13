# DU-BENCH 交接

PLAN_ID=du-bench ｜ 分支 `codex/du-benchmark-20261013` ｜ base `7f6f7cbd`

工作目录：`C:/Users/郑曾波/Projects/_harness_worktrees/document-understanding-20261013/benchmark`

## 1. 做了什么

在独占目录里建了一个**独立**的文档理解质量基准，它测两件当前流水线无法自测的事：

1. **真实遗漏** —— 原件里有、但没进精选证据或摘要的业务事实；
2. **幻觉** —— 观测断言了、但它自己的证据不支持的内容。

产物：

| 路径 | 作用 |
|---|---|
| `tools/document_understanding_benchmark/{schema,records,evaluate}.py` | 冻结 wire 与公开 `evaluate(observed, gold)` |
| `.../checkers.py`、`textutil.py` | 九维检查器与确定性文本/数值/语态原语 |
| `.../gold/*.json` | **11 份真实金标（122 事实，81 关键）** |
| `.../fixtures.py` | 5 份合成夹具，共 14,301 字节 |
| `.../mutations.py` | 19 类反例注入 + 三值判定 |
| `.../review.py` + `reviews/` | 独立语义复核 wire 与真实复核产物 |
| `.../controls.py` | **证明复核层不可省**的负对照 |
| `.../observer.py` | **只读**调用现有公共 parser/selector；含载体能力探测 |
| `.../recovery.py` | SHA+mtime 指纹、哨兵、owned 容器清理 |
| `.../holdout.json` | holdout 候选与缺样清单 |
| `.../__main__.py` | offline / native / adapter 三模式 CLI |
| `.planning/du-bench/evidence.json` | 由运行产物**程序生成**的证据记录 |

金标事实全部**逐字读原件**写成。开发集：恒锋 2020 增发、万润 IR、名创香港年报、中微 2026Q1、中微 2026 半年报、鼎龙扫描确认函。holdout：广联达 2025Q1、雅克科技 2022Q1、阿里巴巴 FY2023、MongoDB FY2026 10-K、NVIDIA FY2025 10-K —— 后两家美国公司由独立子代理逐字读取回报。**没有**从 selector 输出反推期待值。

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

金标 11 份：开发 6、**holdout 5**（A 股 2、H 股 1、US 2），122 事实、81 关键。
单份引文最大 842 字节，上限 8KiB。

**基线真实关键事实召回，开发与 holdout 分开报，从不合并：**

| 划分 | 文档 | 关键召回 | 分母 |
|---|---:|---|---:|
| development | 6 | **9/41 = 0.220** | 41 |
| **holdout** | 5 | **0/45 = 0.000** | 45 |

逐份：

| 样本 | 划分 | 路由 kind | 选中/候选 | units | scan | 关键召回 |
|---|---|---|---:|---:|---|---:|
| cn-equity（恒锋） | dev | `unknown` | 96/449 | 3,224 | partial | 0.000 |
| cn-h1（中微半年报） | dev | `semi_annual_report` | 96/369 | 5,500 | partial | 0.250 |
| cn-ipo-confirmation（鼎龙） | dev | **`prospectus`** | 0/0 | 0 | partial(1页不透明) | 0.000 |
| cn-ir（万润） | dev | `investor_relations` | **11/11** | 302 | complete | 0.143 |
| cn-q-business（中微Q1） | dev | `quarterly_report` | 28/28 | 579 | partial | 0.667 |
| hk-annual（名创） | dev | `annual_report` | 96/254 | 6,502 | partial | 0.000 |
| holdout-cn-glodon-q1 | **HOLD** | `quarterly_report` | **0/0** | 257 | partial | 0.000 |
| holdout-cn-yake-q1 | **HOLD** | `quarterly_report` | **2/2** | 369 | partial | 0.000 |
| holdout-hk-alibaba | **HOLD** | `annual_report` | 96/2,221 | 18,038 | partial | 0.000 |
| holdout-us-mongodb | **HOLD** | — | — | — | **unavailable** | 0.000 |
| holdout-us-nvidia | **HOLD** | — | — | — | **unavailable** | 0.000 |

### B —— oracle 与离线 CLI 绿，故意坏观测必须失败

- 默认套件 **100 passed / 7 skipped / 0 failed**，约 2 秒。
- 离线 CLI：5 夹具、4 PASS + 1 PARTIAL（故意不透明的扫描件）、
  14,301 / 204,800 字节、0 网络 / 0 模型 / 0 付费调用。
- **反例 53/53 全部检出**，42 条 NOT_APPLICABLE。三值判定是刻意的。
- **复核层负对照（本轮的 methodological 补强）**：注入 3 个**确定性检查完全看不见**的语义缺陷
  （给正确数字附加无支撑解读、丢掉限定语、编造因果归因），
  实测 **3/3 全部 PASS 确定性检查、3/3 全部被复核判 FAIL**；
  另证明**全 ENTAILED 的复核无法把一个确定性 FAIL 变成通过**。
  也就是说复核层只能加严、不能放松 —— 这是实测数字，不是主张。
- 独立性：oracle 不 import `company_wiki`；只有 `observer.py` 调现有公共入口。

### C —— 原生回放、恢复与资源

11 份真实原件**全部按 SHA 解析**（2 份 HTML 见下），**原件 SHA 与 mtime 全部不变**，
`config/source_catalog.yaml` 指纹不变（2 个探针），哨兵复原，
**0 原件复制 / 0 网络 / 0 模型 / 0 付费**，峰值 RSS 实测 116 MiB。

## 5. 本轮最重要的三个发现

### 发现 1：holdout 召回为 0，且两份真实 A 股季报**根本没产生候选**

- `holdout-cn-glodon-q1`：**257 个 units 产出 0 个候选**，召回 0/7 是构造性的，不是预算问题。
- `holdout-cn-yake-q1`：369 个 units 只产出 **2 个候选**。
- `holdout-hk-alibaba`：18,038 units / 360 页产出 2,221 个候选，96 上限下一个金标事实都没选中。

这三份互相独立地指向同一结论：**瓶颈在候选生成阶段，不在选择上限**。
`cn-ir` 是同一结论的最干净证据：11 个候选全选中，10 条金标仍缺 9 条。

### 发现 2：US 文件**今天根本无法被评分**（HTML 无通路）

生产回放路径 `narrative_retrieval.py` 只有两种格式：PDF（`parse_pdf`）与
transcript_txt/transcript_html（`parse_transcript_text`）。**没有 SEC 文件 HTML 通路。**

实测（`probe_non_pdf_html`，两份真实 10-K：MongoDB FY2026、Microsoft FY2025）：

- `extract_transcript_material` **接受**字节，不报错；
- 随后 `parse_transcript_text` 返回 **units=0、page_count=0、errors=('transcript_start_missing',)**；
- 抽出的文本还被内联 XBRL 分类法 token（`http://fasb.org/us-gaap/2025#…`）打头，正文之前全是元数据噪声。

所以基准把 US 文件记为 **UNAVAILABLE**，而不是「无业务内容」——
后者会把「载体不支持」伪装成「文档没料」，是最危险的假阴性。
运行报告里显式列出不支持的载体，二者不会被混淆。

### 发现 3：`cn-ipo-confirmation` 精确复现了标题陷阱

一页扫描确认意见被标题正则判成 **`prospectus`**，产出 0 units / 0 候选，唯一一页记为不透明。
这正是 ROOT 预测的失败，现在有了实测。

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
| route_type | 6 | 3 | 可测（US 因载体不支持无法测） |
| critical_fact_recall | 6 文档 / 41 关键 | 5 文档 / 45 关键 | 可测 |
| context_completeness | 0 | 0 | 基线无结构，NOT_EVALUATED |
| citation_replay | 6 | 3 | 可测 |
| role_modality_quantity | 0 | 0 | 基线无 claims，NOT_EVALUATED |
| bilingual_redundancy | 1 | 1 | 名创 + 阿里巴巴 |
| derived_space / time_resource | 6 | 3 | 可测（用基准自有默认上限） |
| untested_semantics | 11 夹具 claim 已复核 | — | native 无 claim，仍 NOT_EVALUATED |

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

1. **为 SEC 文件加 HTML 前端**（REQ-1）——否则整个 US 支线无法评分。
2. 通过 `observer.observe_du_adapter` 注入真实 `du-input/1` 适配器，
   让 `context_completeness` 与 `role_modality_quantity` 不再是 NOT_EVALUATED；
   并接上摘要产出，`semantics.entailment` 才有 claim 可复核。
3. 用 `evaluate(limits=...)` 传 ROOT 的真实派生/时间上限。
4. 决定五个补采请求。

**需要 ROOT 注意的基线事实**：开发集关键召回 0.220、holdout 0.000，
且一份真实 A 股季报产出 **0 个候选** —— 这是候选生成层的缺陷，不是上限问题。

本条线到此停止，不再自行推进；合主线、三包集成与真实摘要大节点归 ROOT。
