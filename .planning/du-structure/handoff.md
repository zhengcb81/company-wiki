# DU-STRUCTURE 交接

分支：`codex/du-structure-20261013`
base：`7f6f7cbd5c438ecfd06f6ffb1241442f26ff43b8`
worktree：`C:/Users/郑曾波/Projects/_harness_worktrees/document-understanding-20261013/structure`
状态：**已实现、已测试、未接生产**。本 lane 只有一个公开函数，没有任何生产入口调用它。

## 改了什么

新增纯包 `src/company_wiki/document_understanding/structure/`，公开：

```python
build_structure(observation: Mapping, *, limits: Mapping | None = None) -> dict
```

输入 `du-input/1`，输出 `du-structure/1`（sections / semantic_units / relations / coverage / diagnostics）。

模块划分：

| 文件 | 职责 |
|---|---|
| `contract.py` | 输入校验、单位视图、limits 收敛、布局自相矛盾标记 |
| `layout.py` | 阅读顺序、页眉/TOC 家具识别、跨行延续、书写系统与并排判定 |
| `sections.py` | 章节栈、父子层级、跨页有界延续、置信度 |
| `projects.py` | 募投/建设项目的可预算小包，含跨页主体保持 |
| `qa.py` | 问答单元，角色分离、跨页问句尾巴、否定保留 |
| `tables.py` | 经营表格，绑定表头/单位/期间/脚注，拒绝财务表混入 |
| `paragraphs.py` | paragraph_event / risk / background，语义不明不编因果 |
| `relations.py` | 6 类关系、去重、存在性、依赖环检测、语言 lane |

## 边界（未越界）

`git status` 只有本 lane 四个独占目录；`git diff --name-only 7f6f7cbd...HEAD` 为空。
未改 profiles、benchmark、现有 source_catalog、document_normalization、生产配置、CI、依赖清单。
未创建父包 `document_understanding/__init__.py`。不 import profiles（已用运行时检查确认）。
0 次模型调用，0 次网络调用，无新增文件读写。

## 如何复跑

```bash
cd C:/Users/郑曾波/Projects/_harness_worktrees/document-understanding-20261013/structure
PYTHONPATH=src python -X utf8 -m pytest tests/unit/document_understanding_structure -q
python -X utf8 -m ruff check src/company_wiki/document_understanding/structure tests/unit/document_understanding_structure
```

结果：**47 passed in ~4s**，ruff 全绿。

C 节点（需要本机原件，只读）：

```bash
python -X utf8 .planning/du-structure/c_node_real_check.py \
  --bindings .planning/du-structure/bindings.local.json \
  --output .planning/du-structure/c-evidence
```

`bindings.local.json` 含本机绝对路径，已 `.gitignore`，不入库。缺原件或缺绑定会输出 `UNAVAILABLE`，
不会标 PASS。

## 真实覆盖与合成覆盖各多少

**合成（19 份断言输入，8 个夹具）**：A 节点 22 项反例全部通过，覆盖目录/正文同标题、跨页项目、
相邻项目、多小节项目、双语双栏、跨页问答、经营表单位/年份/脚注、扫描缺页、人工 bad layout。
B 节点 25 项契约测试，覆盖纯函数不变性、字节稳定、引用可解析、枚举合法、无环、预算、
bad layout 不标 high、规模趋势。

**真实（3 份原件）**：名创港股年报 p12（双栏）、恒锋增发 p62–63（跨页项目）、万润 IR p2–3（QA 否定）。
原件 SHA-256 与计划 `sample_manifest.json` 完全一致，mtime 未变，未复制进仓库。
摘录 3216 / 4321 / 8147 字节，均 ≤8KiB/文档。

真实数据证实的关键点：

- 恒锋 p62→63 建设期延续被保留在同一 project 包内（9 成员，带 `CROSS_PAGE_CONTINUATION`）。
- 万润「公司现无生产 VC（碳酸亚乙烯酯）的情况」与其提问同包，否定未被丢弃或改写。
- 名创 p12 双栏产出 `language_parallel`。

## 哪些仍没证明

1. **经营表格没能在真实数据上产出**。真实 parser 把整张表输出成单个 `pdf_table_row`，
   没有表头 / `单位：` caption 兄弟单元，本 lane 无法建立依赖，因此 `operating_table` 为空。
   这不是本 lane 的缺陷，是适配缺口（见下 DU-S-ADAPT-4）。
2. **真实 PDF 的章节置信度上限为 medium**，因为 parser 不给 `heading_level`。
3. **`language` 字段在真实数据上不可用**：名创英文栏也标 `zh`。
   本 lane 改用文本自身书写系统（CJK/Latin）+ 真实并排几何，能工作，但比显式列号弱。
4. 三份样本只解析指定页，`native_scan=partial`，因此 `coverage.complete` 不代表整份文档覆盖。
5. 未做：真实 LLM 摘要与语义蕴含审查、完整召回率、跨文档变化、峰值 RSS、生产接线。
6. 未判断恒锋项目的**经济内容**正确性（计划 vs 实际、金额口径）——本 lane 只保证结构关联与成员完整。

## 属于 ROOT adapter 的工作

| id | 需要 | 为什么 |
|---|---|---|
| DU-S-ADAPT-1 | `hints.heading_level` | 真实 PDF 全是 `pdf_text_block`，无层级 |
| DU-S-ADAPT-2 | `layout.column` | parser 只给 bbox，无列号；显式列号可提升置信度 |
| DU-S-ADAPT-3 | `language` 字段可信 | 英文栏标 `zh`，不能用于 lane/对齐判断 |
| DU-S-ADAPT-4 | 表头与 `单位` caption 独立单元 + 共享 `table_id` | 否则经营表格永远建不起来 |
| DU-S-ADAPT-5 | QA 页去重决策 | parser 同一页输出两套角色单元（`investor_question/management` 与 `qa_text_shadow`），unit_id 不同；本 lane 不得删任一侧，需 ROOT 决定保留哪套 |
| DU-S-ADAPT-6 | 行上的 `table_id` | 缺失时只能按页松分组，同页两表无法区分 |

## 性能趋势

| units | best ms | sections | semantic_units | relations |
|---:|---:|---:|---:|---:|
| 1 000 | 37.2 | 40 | 200 | 760 |
| 2 000 | 79.0 | 80 | 400 | 1 520 |
| 5 000 | 206.2 | 200 | 1 000 | 3 800 |
| 10 000 | 384.5 | 400 | 2 000 | 7 600 |
| 20 000 | 1 058.2 | 800 | 4 000 | 15 200 |
| 40 000 | 1 751.9 | 1 600 | 8 000 | 30 400 |

10k→40k 的 log-log 斜率 **1.09**（近线性）。

实现中查出并修掉三处 O(n²)：
`sections._layout_inconsistency` 与 `sections._dominant_language` 每个 section 重建全量索引；
`relations` 脚注回退对每个脚注扫描全部 units。
测试里只放了一个宽松趋势断言（<25×），没有毫秒级 CI 断言。

## 接口偏差（均为附加字段，未改既有语义）

- `coverage.deferred_pages`：区分「opaque 页」与「调用方预算 defer 页」。
- `coverage.excluded_furniture_unit_ids`：TOC/重复页眉，与预算 defer 区分。
- `coverage.limits`：回显已收敛的 limits（调用方更低值优先，绝不抬高）。
- `diagnostics[].code` 新增一批枚举（见 handoff.json）。

## 原始件与恢复

三份原件 SHA-256 与 mtime 均未变，未复制进仓库。`c-evidence/` 只含有界摘要。
无安装动作，无技能安装，不 push，不并主线。
