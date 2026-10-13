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
| `.../gold/*.json` | 4 份真实金标（38 事实，29 关键） |
| `.../fixtures.py` | 5 份合成夹具，共 14,309 字节 |
| `.../mutations.py` | 19 类反例注入 + 三值判定 |
| `.../observer.py` | **只读**调用现有公共 parser/selector |
| `.../recovery.py` | SHA+mtime 指纹、哨兵、owned 容器清理 |
| `.../holdout.json` | holdout 候选与缺样清单 |
| `.../__main__.py` | offline / native / adapter 三模式 CLI |

金标事实全部**逐字读原件**写成：恒锋 2020 增发 p61–63、万润 IR 20260515 p1–3、名创香港 2024 年报 p12、中微 2026Q1 p2–4；美国四份文件（MSFT 10-K、MSFT 电话会 TXT、TAL 20-F、VRSK 10-Q）由两个独立子代理读取并回报逐字引文。**没有**从 selector 输出反推期待值。

## 2. 边界

只写 `tools/document_understanding_benchmark/**` 与 `.planning/du-bench/**`。
未改 `src/`、其他 tests、生产配置、CI、另外两个 DU 包、母计划、RF/FF/Audit/Dayu/IQS。
`git status` 只有这两个目录；`git diff --name-only <base>...HEAD` 在提交后应为同一范围。

关于 `pytest.ini`：它不是我该改的共享配置，所以没有加 `-m "not real_data"` 默认项。
真实原件测试改为**默认跳过**，只有设置 `DU_BENCH_ALLOW_REAL_DATA=1` 才跑，并且带 `real_data` marker 可按需单独选。这样默认命令保持又快又纯离线。

## 3. 怎么复跑

```bash
# A/B：纯离线、不联网、不调模型
python -X utf8 -m pytest tools/document_understanding_benchmark/tests -q
#   -> 65 passed, 5 skipped, 约 2.1 秒

# 离线 CLI
python -X utf8 -m tools.document_understanding_benchmark \
    --mode offline --output <自有目录>

# 重建本机 bindings（该文件含绝对路径，不提交）
python -X utf8 -m tools.document_understanding_benchmark.make_bindings \
    --manifest docs/plans/document-understanding-2026-10-13/sample_manifest.json \
    --out <本机目录>/bindings.local.json \
    --repo-root C:/Users/郑曾波/Projects/company-wiki
#   -> bound 20/20

# C：真实原件只读回放
python -X utf8 -m tools.document_understanding_benchmark --mode native \
    --bindings <本机 bindings> --output <自有目录> \
    --probe-config config/source_catalog.yaml
```

退出码：`0` 全 PASS、`1` 有 FAIL、`2` 拒绝运行、`3` 有 PARTIAL/UNAVAILABLE。

## 4. A/B/C 实测

### A —— 金标与反例冻结，记录基线真实结果

金标 4 份：`cn-equity`（恒锋，10 事实/7 关键）、`cn-ir`（万润，10/7）、
`cn-q-business`（中微 Q1，11/9）、`hk-annual`（名创，7/6）。引文总计 1,902 字节，
单份最大 573 字节，远低于 8KiB/文档上限。

基线真实关键事实召回（**FAIL 是可交付发现，不是测试工程失败**）：

| 样本 | 关键召回 | 分母 | 结论 |
|---|---:|---:|---|
| cn-equity | 0.000 | 7 | FAIL |
| cn-ir | 0.143 | 7 | FAIL |
| cn-q-business | 0.667 | 9 | FAIL |
| hk-annual | 0.000 | 6 | FAIL |

**最重要的一条**：`cn-ir` 只有 11 个候选，selector **全部选中**，但 10 条金标事实里仍有 9 条缺失。也就是说这里的召回失败**根本不是预算/上限问题**——候选生成阶段从未产出这些事实。这独立证明了「调高 `max_selected` 修不好召回」，而且是在上限完全没起作用的一份文档上证明的。

`hk-annual`（名创）96/254 选中、6,502 units，p12 的 7 条门店/TOP TOY 事实**全部缺失**，与 ROOT 调查一致。
`cn-q-business` 达到 0.667，是「整类跳过季报」的反例：A 股季报确实有可选中的业务事实。

### B —— oracle 与离线 CLI 绿，故意坏观测必须失败

- 默认套件 **65 passed / 5 skipped / 0 failed**，2.14 秒。
- 离线 CLI：5 夹具、4 PASS + 1 PARTIAL（那 1 份是故意不透明的扫描件）、
  14,309 / 204,800 字节、0 网络 / 0 模型 / 0 付费调用、哨兵复原。
- **反例 53/53 全部检出**，另有 42 条判定为 NOT_APPLICABLE（该夹具里没有它要攻击的目标）。
  三值判定是刻意设计的：把「无处下手」算成漏检会低估，算成检出会造假。
- 独立性：oracle 不 import `company_wiki`；只有 `observer.py` 调现有公共入口。
- 字段缺失 → `unknown` / `NOT_EVALUATED`，既不当审查门，也不伪造 PASS。

### C —— 原生回放、恢复与资源、holdout 清单

四份真实原件全部按 SHA 解析成功，**原件 SHA 与 mtime 全部不变**，
`config/source_catalog.yaml` 指纹不变，0 原件复制，0 网络 / 0 模型 / 0 付费。

| 样本 | 路由 kind | 选中/候选 | units | 读页 | scan | 耗时 |
|---|---|---:|---:|---|---|---:|
| cn-equity | `unknown` | 96/449（触顶） | 3,224 | 96/96 | partial | 7.938s |
| cn-ir | `investor_relations` | 11/11 | 302 | 6/6 | complete | 0.390s |
| cn-q-business | `quarterly_report` | 28/28 | 579 | 15/15 | partial | 2.278s |
| hk-annual | `annual_report` | 96/254（触顶） | 6,502 | 246/246 | partial(1 页不透明) | 23.737s |

已知遗漏复现（逐条核对选区文本，不是照抄计划结论）：

- **恒锋两期建设**：`建设期`、`第一期`、`第二期` 在选区文本里**全部缺席**
  （`募集资金` 在），两期建设/投资事实确实没进证据。
- **名创 p12 门店表**：hk-annual 的 **7 条金标事实全部缺席**，含 p12 的
  `Total 合計` 7,504 门店数、经营模式行、TOP TOY 门店数。
  **一处对计划措辞的更正**：`TOP TOY` 这个裸字符串在选区里**是出现的**
  （来自其它页），所以真正的遗漏是 p12 门店表事实，而不是品牌名本身。
- **96 上限只是部分触顶**：确实触顶的是 `cn-equity`(96/449) 与
  `hk-annual`(96/254)，两者 `selector_status=partial`；`cn-ir`(11/11) 与
  `cn-q-business`(28/28) **没有触顶**。

## 5. 开发 / holdout 与缺失类型

- **开发集 20 份**（ROOT 调查样本）已全部按 SHA 绑定；其中中微、恒锋、万润、名创、鼎龙、世华、金禾参与过调规则，**明确不算 holdout**。
- **holdout 候选**（有真实原件、未被任何调参引用）：A 股广联达（软件）、雅克科技（制造）；H 股阿里巴巴（零售）。
- **US holdout = UNAVAILABLE**，如实记录而非补合成样本：已读的四份美国文件（MSFT 10-K、MSFT 电话会、VRSK 10-Q、TAL 20-F）全属开发集，本机其余根本查不到美国原件。
- **缺失类型**：真实 US S-1/F-1、真实 8-K/6-K 附件容器、修订版与原版配对、第二家非电商 H 股年报。

## 6. 每维度分母（今天能支持的真实分母，不写百分比）

| 维度 | 开发 | holdout | 状态 |
|---|---:|---:|---|
| route_type | 4 | 0 | holdout 待采集 |
| critical_fact_recall | 4 文档 / 38 事实 / 29 关键 | 0 | 可测 |
| context_completeness | 0 | 0 | 基线无结构，NOT_EVALUATED |
| citation_replay | 4 | 0 | 可测 |
| role_modality_quantity | 0 | 0 | 基线无 claims，NOT_EVALUATED |
| bilingual_redundancy | 1 | 0 | 仅名创为双语金标 |
| derived_space / time_resource | 4 | 0 | 可测（用基准自有默认上限） |
| untested_semantics | 4 | 0 | 无独立复核即 NOT_EVALUATED |

现在就报 holdout 召回率会是编造统计，所以分母照实列。

## 7. 基线问题（真实质量发现）

1. `cn-ir` 候选全中仍漏 9/10 —— 问题在候选生成，不在上限。
2. `cn-equity` 路由停在 `unknown`；两期建设期、35,300.00/28,678.71 投资拆分、35,978.71 上限全部没进。
3. `hk-annual` p12 门店表与 TOP TOY 全漏，双语双栏未恢复。
4. `cn-q-business` 达 0.667，证伪「季报可以整类跳过」。
5. 基线不产出 route family / semantic units / claims，因此这三个维度**只能是 NOT_EVALUATED**，不能算 PASS。

## 8. 尚不能自动检验的语义项

- 摘要句是否真被其引用证据蕴含（需 ROOT 大节点独立复核；结果里带 `spot_read_list`）。
- 数值在单位/期间/口径标签之外是否经济上正确（如管理层自己的算术）。
- 表格在从未被抽取时是否完整。
- 双语对是真翻译还是另一语言车道里的另一件事。
- 公司计划是否现实（只能判「说成计划」还是「说成既成事实」）。
- 图表内容——基线从不读，金标也不断言。

## 9. 资料补采请求（交给 ROOT）

REQ-1 两份非开发集美国 10-K/10-Q（一软件一工业）｜REQ-2 一份真实 US S-1/F-1｜
REQ-3 一份真实 8-K/6-K 且附件本身是业务文件｜REQ-4 一份修订版+原版配对｜
REQ-5 一份非电商 H 股年报。详见 `holdout.json`。

## 10. 0 付费 / 0 原件写入 / 恢复 / 体积

- **0 模型调用、0 付费调用、0 网络调用、0 原件复制、0 原件写入、0 原件 SHA 或 mtime 变化**，
  0 数据库写入，0 生产配置写入。原生读数 6,413,909 字节，全部只读。
- 恢复：**哨兵改为「运行前保存原始字节+mtime，运行后原样写回」**。
  离线 `sha D98FC286…/mtime 639274754759568590`、原生 `sha 404B754C…/mtime 639274754759600862`
  运行后逐字节与 mtime 均一致。
  这里修掉了一个真 bug：原先 `install_sentinel()` 每次运行都无条件重写哨兵，
  于是 `sentinel_stable` 拿新写的文件和自己比，**永远发现不了**预先存在的哨兵被覆盖。
  现在 `restoration.sentinel_restored` 区分 `restored` / `created_by_this_run`。
  清理只删带 `.du-bench-owned` 标记的目录，未标记目录**拒绝删除**（有测试断言）；未删除任何未知目录。
- 体积：金标引文 1,902 字节；合成夹具 14,309 字节（预算 204,800）；报告只留摘要与引用。
  保留下来的输出目录共 220,351 字节，最大单文件 112,579 字节 < 最小原件 153,851 字节，
  因此目录内**没有任何原件全文副本**。
- 峰值 RSS **已真实测得**：原生 121,929,728 字节（约 116 MiB），离线 21,049,344 字节（约 20 MiB）。
  早先 `peak_rss_measured=false` 是个真 bug：`recovery.peak_rss_bytes()` 通过 ctypes 调
  `GetProcessMemoryInfo` 时没设 `argtypes`/`restype`，64 位 HANDLE 被截断，psapi 与 K32
  两个入口都返回 0。补上函数原型后即可测出；上面两个数字是修复后的实跑值。

## 11. 本轮修掉的基准自身缺陷

基准也是代码，会自己出错。这一轮原生回放复跑时暴露出 4 个真问题，都已修并加了回归测试：

1. **峰值 RSS 恒为 None** —— ctypes 调 `GetProcessMemoryInfo` 没设函数原型，
   64 位 HANDLE 被截断，两个入口都返回 0。补 `argtypes`/`restype` 后测得真实值。
2. **哨兵检查形同虚设** —— `install_sentinel()` 无条件重写哨兵，
   `sentinel_stable` 变成「新文件 vs 自己」，预先存在的哨兵被覆盖也报 true。
   改为运行前保存、运行后还原，并区分 `restored` / `created_by_this_run`。
3. **`restore_sentinel()` 拼写错误**（`preeexisting`）—— 被新加的哨兵保持测试当场抓到。
4. **`config_unchanged` 在没传 `--probe-config` 时报 count=0** ——
   看起来像通过，实际什么都没证明。现在打印探针数量，并把哨兵纳入探针集合。

另有两个**遗漏结论的精化**（不是缺陷，是措辞）：名创真正的遗漏是 p12 门店表事实
而非 `TOP TOY` 字符串本身；96 上限只在 2 份文档上触发，另 2 份压根没触顶。

## 12. 需要 ROOT 做的事

1. 通过 `observer.observe_du_adapter` 注入真实 `du-input/1` 适配器，让
   `context_completeness` 与 `role_modality_quantity` 不再是 NOT_EVALUATED。
2. 用 `evaluate(limits=...)` 传 ROOT 的真实派生/时间上限（现在用的是基准默认值）。
3. 对 `spot_read_list` 跑独立语义复核，把 `semantics.entailment` 从 NOT_EVALUATED 推进。
4. 决定五个补采请求，以便写出真正盲测的 holdout 金标。

本条线到此停止，不再自行推进；合主线、三包集成与真实摘要大节点归 ROOT。
