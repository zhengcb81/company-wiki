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

## 合并阶段修掉的三个接线缺陷

这三个都**只在三包并成一条链、且四个套件在同一次 pytest 调用下运行时**才暴露；
每个 lane 单跑全绿时看不见它们。每个都补了回归锁，都没有靠放松断言过关。

1. **路由对编排是 no-op（静默失效）。**
   `build_dependency_packages` 从 `route["section_priorities"]` 读章节优先级，但该键在
   **profile** 上而不在 route 上——`route_document` 并不返回它。结果每份文档都拿到同一套
   通用优先序，"按文档类型决定先读什么"完全没生效，而且**不报错**。
   修复：`build_dependency_packages` 接受 `profile=`，`_role_priority` 优先用 profile、
   仍兼容只传 route；由 `test_du_root_lane_seam.py` 锁死（断言 profile 必须真的改变优先序，
   且只传 route 时确实等于通用序）。

2. **两 lane 的 fixtures 同名，四套件同跑直接收集失败（CI 的跑法）。**
   structure lane 把自己的 fixture 目录插进 `sys.path` 后写 `from fixtures import ...`，
   而仓库另有 `tests/fixtures` 也在 `sys.path` 上。单跑 structure 通过；与 profiles/root/bench
   同跑即 `ImportError: cannot import name 'available_inputs' from 'fixtures'`。
   修复：fixture 模块改名为唯一的 `tests/fixtures/document_understanding_structure/du_structure_fixtures.py`，
   按该名导入。

3. **四个测试模块算错仓库根路径，真实节点静默 skip。**
   `tests/unit/<lane>/test_*.py` 用 `Path(__file__).parents[2]`，得到的是 `<repo>/tests`
   而不是 `<repo>`，于是 bindings 永远找不到，真实原件节点报 **10 SKIPPED**——一个诚实但
   误导的"绿"。修复为 `parents[3]` 后真实节点实际运行并通过。
   ⚠️ 注意：structure lane 自己的 `FIXTURE_ROOT = parents[2] / "fixtures" / ...` 在**同一深度**
   下是**正确**的，不要跟着一起改（改了就会变成 `<repo>/tests/fixtures`→错位）。

合并后：**371 passed / 5 skipped**（同一调用，约 26s），`ruff check src tests/unit tools` 全绿。

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

合计 **371 项通过，0 失败**。付费摘要路径明确标 `not_run`，绿色结果不构成付费路径证据。

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
3. ~~定夺 QA 双套角色单元保留哪一套。~~ **已在本次交接中定夺**，见下节。
4. 按母计划跑真实模型摘要大节点与跨公司 G4/G5；付费前确认既有预算。
5. 生产接线（默认路径切换）与缓存失效；本层当前不参与生产。

## 本次收尾新增的内容

### 1. QA 双套角色单元：已定夺（原第 3 项）

真实 parser 把每个问答页输出**两遍**：扁平的 `qa_text_shadow`（正文文本层）与结构化的
`investor_question`/`management`（带发言人与轮次）。

实测万润 IR 原件（302 unit：219 shadow / 18 question / 55 management）：本层产出的 74 个包中
**53 个完全由 shadow 构成**，只有 14 个完全由结构化角色构成；而 192 条 shadow 文本里只有 10 条
与结构化文本逐字相同——两份拷贝是**同一内容的不同切分**，不是两份内容。

决定（与生产选择器已有的 `_EXCLUDED_ROLES` 规则一致，不另立第二套约定）：

- **两份都留在 observation**：结构层需要用它们跨页配对问答；删掉任一侧都会让覆盖率虚高。
- **shadow 不可被选为证据**：它重复了结构化拷贝，选它会重复计数并丢掉发言人归属。
  现在在 wire 上用 `hints.qa_text_shadow` 显式标注，消费者不必知道 parser 的内部角色名。
- 新增 `is_selectable()` / `selectable_unit_ids()`；8 项测试锁定，其中包括
  "结构层仍然看得到每一个 unit"。

### 2. 摘要请求（implementation.md 第 5 步"按 profile 聚合摘要"）

`profile.summary_focus` 此前**没有任何消费者**，摘要实际会由通用指令驱动。
新增 `build_summary_input(pipeline_result, ...)` → `du-summary-input/1`：

- 焦点取自 **profile**（不同文档类型得到不同焦点，已有测试断言）；
- 证据包按编排层给出的顺序排列（profile 章节优先级在前、语义类型在后作为同带并列）；
- 每个成员保留 `unit_id`/`locator`/`page`；observation 里没有的 unit **丢弃而不是编造**；
- 预算截断记为 `deferred`、未读页/延后单元记为 `unread`——两者都不会变成对完整性的暗示；
- 约束文本明令保留原语言、并禁止输出评级/目标价/仓位。

它**不调用模型**，付费预算仍由现有 transport 决定。已在 4 份真实原件上验证
（offering / investor_qa / hk_periodic / cn_quarterly）：各自拿到自己的焦点、provenance 全部可回指、
deferred 计数如实报告。

### 3. 合并阶段修掉的接线缺陷（3 项）

见上文"合并阶段修掉的三个接线缺陷"。其中 fixtures 同名那一条会让 CI 的四套件同跑直接收集失败。

## 当前完成状态

| 套件 | 测试 |
|---|---:|
| profiles | 150 |
| structure | 47 |
| root | 109 |
| benchmark | 65 |
| **同一调用合计** | **371 passed / 5 skipped** |

`ruff check src tests/unit tools` 全绿；`.planning/du-root/acceptance.py` 六项全 passed、
0 skipped、exit 0；真实原件节点实际运行（不再 skip），原件 SHA/mtime 未变、0 份复制进 worktree。

## 唯一未做的一项，及具体原因

**implementation.md 第 7 步的付费模型大节点与第 8 步生产切换：未执行。**

这不是"等待人工批准"，具体原因是：

1. **计划本身把它排在母计划 G4/G5 窗口**：task_plan 写"生产切换与真实模型大节点按母计划
   G4/G5 另行执行"，且明确本层不得替代或签收 G4/G5。
2. **本层刻意未接入生产入口**，而"同配置真实摘要"要求先做第 8 步的生产接线，而计划把第 8 步
   排在第 7 步之后。
3. **无法确认累计预算余量**：`config.yaml` 只有单次调用上限（`llm.max_tokens=8192`、
   `llm_max_input_chars=120000`），没有累计 USD/token 上限；而 `llm_cost_log.csv` 已有
   7025 行、约 43.0 USD / 282.7M token，远超计划文本引用的 $20/2M 口径。在无法确认余量的
   情况下支出，无法给出正当依据。

**凭据是存在的**（主检出 `.env` 内有 DEEPSEEK/MINIMAX/MIMO），所以这是**预算与排序**上的关卡，
不是缺配置的关卡。推进方式：确认当前累计预算余量 → 接入生产摘要路径 → 跑真实模型节点与
母计划 G4/G5 审查。
