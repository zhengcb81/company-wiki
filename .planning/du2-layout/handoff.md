# DU2-LAYOUT 交接

分支：`codex/du2-layout-20261013`　base：`5a297244549d54c34f382835b876ec3d181fcd24`
（检查过：base 就是本 worktree 起点，`git diff --name-only 5a29724...HEAD` 只含本 lane 四个独占路径）
worktree：`C:/Users/郑曾波/Projects/_harness_worktrees/document-reading-review-20261013/layout`
实现 commit：`dc479732cb6818d1b41a4465e199ea2e5263ddb0`（初版）、
`a7868ba75fc8450117e4e7cc88ee38d396cfe76e`（完工后逐条复核的修复）；交接文件随后追加一次提交以准确记录 SHA。

状态：**已实现、已测试、未接生产**。全 lane 只有一个公开函数，没有任何生产入口调用它。

## 改了什么

新增纯包 `src/company_wiki/document_understanding/layout_hints/`，公开：

```python
derive_layout_hints(observation: Mapping, *, limits: Mapping | None = None) -> dict
```

输入 `du2-layout-input/1`，输出 `du2-layout-hints/1`（unit_hints / groups / relations /
reading_order / coverage / diagnostics），严格按 `review/INTERFACES.md` 第 5 节。

| 文件 | 职责 |
|---|---|
| `contract.py` | 输入校验（错误类型/重复 id 抛 `ValueError`）、越界与坏几何诊断+推迟、limits 只收紧、工作预算 |
| `text_evidence.py` | 文本形态：数字/年份/日期/期间/单位/题注/脚注/编号标题/句末标点 |
| `geometry.py` | 行带聚类、带内按空白间隙切格子、列槽区间聚类、格子→列映射 |
| `tables.py` | 表区（行带 run / 整行单格对齐子串）、表头块、行组、题注/脚注、折行诊断、粒度诊断 |
| `headings.py` | 跨页页眉页脚识别、正文尺度、标题证据与层级（年份/日期/句子否决） |
| `columns.py` | 全文学习栏切分、按页产出 lane、排除页眉页脚带与跨栏 unit |
| `relations.py` | 表头/题注/脚注关系与跨页续表判定（列对齐/重复表头 + 页差） |
| `ordering.py` | 每页阅读顺序视图（只提示，不改 ordinal、不删文字） |
| `README.md` | API 文档 + 判定规则 + ROOT 字段清单 + 歧义/partial 条件 + 复杂度 + 接线建议 |

## 边界（未越界）

- `git status` 只有本 lane 四个独占目录；未改原 document_normalization/parser/observation_adapter/
  structure/profiles/summary、其他测试、pyproject/requirements/config/CI、总 PWF。
- 未创建父包 `document_understanding/__init__.py`（Python 3 命名空间包可正常 import）。
- 未新建 PDF→MD 流水线、OCR 引擎、文档读取器、任务库或供应商配置。
- 0 供应商调用、0 费用、无新增依赖（PyMuPDF/ruff 已装，只用于测试侧只读采样/静态检查）。
- 输出 wire 里没有任何 `locator` 字段，也从不新造来源 locator（有测试锁定）。

> 注意（运维信息，非产品改动）：本 worktree 是 cone 模式 sparse checkout，`.planning/**` 原本不在
> sparse 集合内，为提交本 lane 的计划/交接文件，执行了 `git sparse-checkout add .planning/du2-layout`
> （只影响本 worktree 的本地 sparse 配置，不是仓库文件，其他 lane 的 `.planning` 仍被排除）。

## 如何复跑

```bash
cd C:/Users/郑曾波/Projects/_harness_worktrees/document-reading-review-20261013/layout

# A+B（集中命令，离线；真原件默认 opt-in 跳过）
python -B -X utf8 -m pytest tests/unit/document_understanding_layout_hints -q
# -> 34 passed, 6 skipped

# C（真原件只读，需本机 bindings）
CW_DU2_LAYOUT_REAL=1 python -B -X utf8 -m pytest tests/unit/document_understanding_layout_hints -q
# -> 40 passed（真实用例确实跑了，不是 skip；含"原件 SHA+mtime 未变"断言）

# 仅本包 ruff
python -X utf8 -m ruff check src/company_wiki/document_understanding/layout_hints \
  tests/unit/document_understanding_layout_hints tests/fixtures/document_understanding_layout_hints

# 真实件对照证据（只读，写出 c-evidence）
python -B -X utf8 .planning/du2-layout/c_node_real_check.py

# 规模观察 1k/10k/40k（非 CI 断言）
python -B -X utf8 tests/fixtures/document_understanding_layout_hints/scale_run.py \
  --output .planning/du2-layout/perf_scale.json
```

`bindings.local.json`（`{sample_id: 本地绝对路径}`）位于 `.planning/du2-layout/`，已被该目录
`.gitignore` 排除、不入库；缺失或 SHA 不符时真实用例报 UNAVAILABLE/SKIP，绝不算真实通过。

## 真实覆盖与合成覆盖各多少

- 合成：17 个冻结 `du2-layout-input/1` fixture（23 文件 / 118 KiB），覆盖卡片要求的全部正反形态：
  无编号标题vs普通短句、年份不是标题、跨栏页眉、左右中英栏、表格数字孤立行、表头/期间/单位/脚注、
  跨页续表（含"下一页是新表"反例）、坏几何/缺字体/空页面、相邻无关表隔离、金额相同项目不同、
  双语非逐句对应、表格无表头、脚注属上一图、坐标越界、整行单格无格子坐标、多时期/地区列不混并。
  另加程序化规模生成器（1k/10k/40k）。
- 真实：4 份原件、7 个真实用例（名创 p12 门店表 span 级 + 整行单格两种输入、恒锋 p61-62、
  金禾 p223-224、中微 p41 负例，外加 2 个离线探针管道自检）。
  结果：**充分输入下**名创 2 表区 high/3 列、金禾 3 表区 high/6 列且跨页续表成立
  （basis 含 page_gap=1；无重复表头，故续表不新称表头）、恒锋 4 表区含两列表；
  **当前生产式整行输入下**名创不虚构任何列并给出 NEEDS_UPSTREAM_GRANULARITY。
- 原件只读保持：跑前/跑后 SHA-256 与 mtime 完全一致（4/4，且有 opt-in 测试锁定该断言）。
- probe id ↔ 原页面坐标映射留证于 `.planning/du2-layout/c-evidence/probe_mapping.json`
  （每 source 引文 ≤8 KiB，并明确标注不是生产 locator）。

## 哪些仍没证明（诚实清单）

1. **未接生产**：没有任何 parser/section/selector 消费本包，因此**不声称**修复了最终召回或摘要质量；
   本 lane 的 PASS 只表示纯辅助能力合格。
2. 折行逻辑行（金禾备案表）只到"标记 partial"（LOGICAL_ROW_UNRESOLVED），没有恢复逻辑行合并。
3. `row_span` 恒为 null；多行表头只合成为一个表头行组（不还原多层级行结构）。
4. HTML/PPT/DOCX 前端当前不产出 bbox/字号，**未做真实几何断言**，如实列 needs_upstream。
5. 未在真实 5 万 unit 原件上跑满默认上限；40k 合成只测到 `max_groups=10000` 触顶 partial；
   并发/多进程内存叠加未测。
6. 恒锋 p61 概况表尾行（跨页包住的"建设周期"值）被当作未认领行带，没有强行并成一个表区。
7. 无数量表（纯文本表）只取首个行带作表头，因此其真实的两级表头不会被还原。
8. `GROUP_LIMIT_EXCEEDED` 是**截断结构**而不是把 unit 标 deferred（unit 仍保留 unit_hints）；
   诊断会列出所有丢失结构的 unit，便于消费侧判断影响范围。

## 复杂度与性能（集中节点观察，无脆弱毫秒断言）

| units | groups | work_units | work/unit | 耗时 | 峰值 RSS | complete |
|---|---|---|---|---|---|---|
| 1,000 | 346 | 5,779 | 5.779 | 0.55s | 26.3 MB | true |
| 10,000 | 3,471 | 57,904 | 5.790 | 5.60s | 84.3 MB | true |
| 40,000 | 10,000（封顶） | 231,665 | 5.792 | 25.76s | 274.9 MB | false（GROUP_LIMIT_EXCEEDED，诊断列出丢失结构的 unit） |

work/unit 三档稳定，近线性、无全量 N²、无无限跨页关联；详见 `perf_observations.md`。
未测项在该文件中明确标注"未测"。

## ROOT 接线建议（详见包内 README 第 4、7 节）

1. 前端以 **span/cell 级** 透传 `bbox`/`font_size`/`font_weight` 与**调用方自己的 `locator`**
   （PDF 用 PyMuPDF span，HTML 用 DOM 几何，PPT/DOCX 用形状几何）；缺几何时本包会明确降级而不是猜。
2. 用**一个**共享几何实现替换旧的 column/heading 猜测：ROOT 接 `derive_layout_hints`，
   删除被替代的重复推断，不要并存两套布局判定。
3. 章节识别用 `heading_level` + `reading_order`；表结构用 `groups`/`cells` +
   `required_context_unit_ids`（表头/期间/单位/题注/脚注依赖）；`reading_order` 只作展示与选包顺序，
   **不要写回 `ordinal`**。
4. 看到 `NEEDS_UPSTREAM_GRANULARITY` 时应触发前端补采细粒度几何或标 partial，
   不要在下游按空格切列；`coverage.complete=false` 必须原样传给覆盖报告。
5. 预算用既有全局上限**收紧**本包 `limits`；本包不会提高任何外部时间/像素/OCR/模型预算。
