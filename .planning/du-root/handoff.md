# DU-ROOT 交接

分支：`codex/du-root-integration-20261013`
base：`7f6f7cbd5c438ecfd06f6ffb1241442f26ff43b8`
worktree：`C:/Users/郑曾波/Projects/_harness_worktrees/document-understanding-20261013/root`
状态：**三包已接收并集成；整链可一键运行；未接入生产入口**。未并 master、未 push、未安装技能。

## 改了什么

在既有扁平 units 之上落一层文档理解，四个组件由冻结 JSON wire 交换，互不 import：

| 组件 | 位置 | 职责 |
|---|---|---|
| observation adapter | `document_understanding/observation_adapter.py` | 既有 parser units → `du-input/1` |
| pipeline | `document_understanding/pipeline.py` | 一键整链 `understand_units` |
| orchestration | `document_understanding/orchestration.py` | structure → `du-packages/1` 依赖闭合包 |
| selection bridge | `document_understanding/selection_bridge.py` | 选择后只增不减地补回上下文与否定 |

三条 lane（profiles / structure / benchmark）由各自分支合入本分支，未改动其内部实现。

## 边界

ROOT 只写：上层 `document_understanding/__init__.py`、ROOT 自己的三个模块、
`tests/unit/document_understanding_root/**`、`.planning/du-root/**`、`docs/ARCHITECTURE.md`
与本计划文档。未改 profiles/structure/benchmark 包内部、未改生产 parser/selector、
未改配置/CI/依赖、未动 Dayu/IQS。

`git status` 干净；`git diff --name-only 7f6f7cbd...HEAD` 仅含上述路径与三条 lane 的
独占路径。无安装动作。0 模型调用、0 网络调用。

## 如何复跑

```bash
cd C:/Users/郑曾波/Projects/_harness_worktrees/document-understanding-20261013/root
python -X utf8 .planning/du-root/acceptance.py \
  --bindings .planning/du-root/bindings.local.json
```

`bindings.local.json` 含本机绝对路径，已 `.gitignore`，不入库。不带 `--bindings`
时真实数据项**跳过**而不是通过。

单包：

```bash
PYTHONPATH=src python -X utf8 -m pytest tests/unit/document_understanding_profiles -q
PYTHONPATH=src python -X utf8 -m pytest tests/unit/document_understanding_structure -q
PYTHONPATH=src python -X utf8 -m pytest tests/unit/document_understanding_root -q
PYTHONPATH=src python -X utf8 -m pytest tools/document_understanding_benchmark/tests -q
```

## 最终验收（合并后实测）

| 检查 | 结果 |
|---|---|
| profiles | **150 passed** |
| structure | **47 passed** |
| root（含真实数据 11 项） | **69 passed** |
| benchmark | **65 passed, 5 skipped**（skip 为设计：真实回放需环境变量） |
| real_data 子集 | **11 passed** |
| ruff | All checks passed |
| paid path | **not_run**（本 harness 从不调用模型/网络） |

合计 **331 项通过，0 失败**。付费摘要路径明确标 `not_run`，绿色结果不构成付费路径证据。

## 集成中发现并修掉的真实缺陷

1. **`section_priorities` 读错对象**：它属于 **profile**（`get_profile`），不属于 route
   （`route_document`）。只传 route 会让每份文档都退化到同一套通用顺序，且看起来是对的。
   已让 `build_dependency_packages` 接受 profile 并优先使用，pipeline 负责解析。
2. **adapter 列号推断把页眉算进分栏**：名创 p12 页眉在右半页，按页中点切分导致左右栏判定反向。
   改为按窄块左边缘聚类 + 最小间隙比例判定；跨栏块（整表）给 `None` 而非猜一侧。
3. **标题正则误伤年份**：`2020 年5 月14 日…` 曾被 `\d+.\d+` 判为标题。已收紧为需要标题字。
4. **环检测方向写反**（structure lane 内，集成时验证）：`question_answer` 被误判成环丢弃。

## 关闭的 adapter 缺口

| 缺口 | 状态 |
|---|---|
| 表头 / `单位：` caption / `table_id` | **关闭**：`row_index==0` 即表头，parser 已携带 `table_headers` |
| `layout.column` | **关闭**：真实几何实测分栏；恒锋/名创均得到 lane 0/1 |
| `heading_level`（编号标题） | **关闭**：第X节 / 一、 / （一） / Item N. |
| `heading_level`（无编号标题） | **未关闭**：见下 |

## 真实覆盖与合成覆盖

**合成**：profiles 150、structure 47、root 58、benchmark 65（离线 fixtures 14,309B / 204,800B 预算）。
**真实**：root 11 项 + benchmark 原生回放 4 份 + profiles C 节点 7 份原件。

真实原件（SHA/mtime 全程未变，未复制进仓库）：
- 恒锋 2020 增发 p62–63：两期建设期跨页保留在同一 project 包内。
- 万润 IR p2–3：选择器只挑中问句时，桥把「公司现无生产 VC（碳酸亚乙烯酯）的情况」补回，
  否定不再与它否定的提问前提分离。
- 名创 2024 港股年报 p12：真实两栏被区分且不混读。
- 中微 2026Q1 p2–3：业务文本可组织，覆盖率 > 50%。

## 哪些仍没证明

1. **无编号纸质标题仍无法判为章节**。真实 PDF parser 只保留 bbox/pdf_block，丢弃 span 字号；
   而页面上同样短小的表格片段使几何猜测必然误伤，故不做猜测。
   **需要 parser 层保留字号证据**，这是本层无法自行补齐的真实工作项。
2. **QA 页双套角色单元未定夺**。parser 同时输出 `investor_question`/`management` 与
   `qa_text_shadow`（unit_id 不同）。结构层不得删任一侧，保留哪套需 adapter/选择层决定。
3. **真实模型摘要与语义蕴含审查未做**。付费路径 `not_run`；基准的 entailment 维度为
   `NOT_EVALUATED`，其 `spot_read_list` 已备好供大节点使用。
4. **未接入生产入口**。没有任何生产调用方 import 本层；切换属后续步骤。
5. **未做跨文档变化、完整召回率、峰值 RSS（本层）**。
6. **US holdout 仍缺**：benchmark 记 5 条采集请求，未用合成样本顶替；20 份调查样本是
   开发集而非盲测集，未声称盲测。

## 性能趋势

structure + orchestration 合计，合成规模夹具：

| units | ms | packages |
|---:|---:|---:|
| 2 000 | 78.1 | 400 |
| 10 000 | 329.1 | 400 |
| 40 000 | 1 714.3 | 400 |

log-log 斜率 **1.03**（近线性）。基准另测峰值 RSS：原生 121.9 MB、离线 21.0 MB。

## 需要 ROOT 后续执行的下一步

1. 决定是否提高 profiles 的 200-unit / 64 000-char 探测预算——当前**每份真实文档**都因
   `ROUTE_PROBE_LIMIT` 返回 `confidence=low`，是诚实的预算状态而非健壮路由。
2. 在 parser 层保留 span 字号，关闭无编号标题缺口。
3. 定夺 QA 双套角色单元保留哪一套。
4. 按母计划跑真实模型摘要大节点与跨公司 G4/G5；付费前确认既有预算。
5. 生产接线（默认路径切换）与缓存失效；本层当前不参与生产。
