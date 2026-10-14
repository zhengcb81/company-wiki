# DU3-GEOMETRY 交接

分支：`codex/du3-geometry-20261014`　base：`195aba20b0aecc2d661d7d04c5ba72f982bc02d0`
worktree：`C:/Users/郑曾波/Projects/_harness_worktrees/shared-reading-completion-20261014/geometry`
lane：`geometry`（DU3 三条独立施工线之一）

状态：**已实现、已测试、未接生产**。全 lane 只有一个公开函数 `project_layout_snapshot`，
没有任何生产入口调用它。旧 `layout_hints` 只作只读消费者回归，未改动。

## 排他写范围（`git status` 只有这四条，全部是新增）

- `src/company_wiki/document_normalization/layout_snapshots/**`
- `tests/unit/document_normalization_layout_snapshots/**`
- `tests/fixtures/document_normalization_layout_snapshots/**`
- `.planning/du3-geometry/**`（含 local-only `bindings.local.json`，已 `.gitignore` 排除、不入库）

未改：现 parser/normalization 父 `__init__`、PDF/HTML/OCR/PPTX 入口、`observation_adapter`、
`layout_hints`/`layout_bridge`、registry/selector/summary、`source_catalog`、automation、
ROOT PWF、依赖/CI/config、其他工作树。没有新增 OCR 后端、第二 PDF parser 或文件存储。

## 冻结接口

```python
def project_layout_snapshot(snapshot, units, *, limits=None) -> dict
```

输入 `du-layout-snapshot/1`（`pages[]`含`page/width/height/coordinate_frame/rotation/bindings`，
每 binding 含已有 `unit_id` + 实际提取 bbox + 可选 `words/cells/font_runs`）与已读 `du-input/1`
units，输出 `du-layout-projection/1`：`unit_metadata`（`unit_id→{layout,hints,upstream_hints}`）
＋ `coverage`/`diagnostics`/`feature_version`。纯内存，无文件/网络/model/OCR；不改 unit_id、
原 text/locator/role，不新造 EvidenceSpan；不推断 column_lane/章节/续表/表头（仍归共享 `layout_hints`）。

## 模块（对应卡片 A/B 命名）

| 文件 | 职责（card 名） |
|---|---|
| `identity.py` | limits_identity：默认预算（10000 units/64 pages/200000 细元素/1000000 work）、只收紧 limits、WorkBudget、坐标 frame 归一/旋转对齐、NFC/trim 字符区间对齐 |
| `contract.py` | snapshot_contract：`du-layout-snapshot/1` 结构校验、页/frame 解析、binding 结构、bbox 合法性/页内越界 |
| `unit_binding.py` | unit_binding：word/cell/font_run 绑定到 unit，保留各自真实 bbox＋原生索引/字符范围依据；混合字体/跨行/NFC 未对齐→unknown/重复字串不合并/row_cells 不算细 geometry |
| `projection.py` | metadata_projection：`project_layout_snapshot` 编排、逐 unit 原子提交、coverage/diagnostics/feature_version；预算/元素/页/单元上限集中判定 |

## 证据（命令 / exit / 耗时 / 小收据）

- **A（RED first）**：`python -B -X utf8 -m pytest tests/unit/document_normalization_layout_snapshots -q`
  在实现前 → `ModuleNotFoundError: layout_snapshots`（2 collection errors）。收据：`evidence/a-red-receipt.md`。
- **A+B（GREEN，离线）**：同命令 → **36 passed, 7 skipped**（real 用例默认 opt-in 跳过）。
- **B（只读消费者回归）**：`pytest tests/unit/document_understanding_layout_hints -q` → **42 passed, 6 skipped**
  （旧 `layout_hints` 无回归，其 real 用例因缺 du2 bindings 跳过）。
- **C（真实原件 opt-in）**：`CW_DU3_GEOMETRY_REAL=1 pytest tests/unit/document_normalization_layout_snapshots/test_c_real_snapshots.py`
  → **8 passed, 1 skipped**（Miniso 原件本机缺失→UNAVAILABLE）。收据：`evidence/c-real-snapshots.json`。
- **静态检查**：`ruff check`（本包三目录）→ All checks passed。
- 真实件对照证据：`python -B -X utf8 .planning/du3-geometry/evidence/gen_c_evidence.py` → 生成
  `evidence/c-real-snapshots.json`（精简，不含原文件路径/整页全文）。

## 真实覆盖 vs 合成覆盖

- **合成**：`tests/fixtures/.../synth.py` 13 个 builder 覆盖卡片 A 全部反例——旋转 frame（0/90/180/270）、
  未知 frame、混合字号/字体、跨行 offset、NFC/trim 未对齐、重复字串异 block、缺/坏 bbox、
  错页/缺 unit、无细 cells 整行、真实 cell 粒度、前端无几何（HTML/PPTX/OCR）、双栏不推断、
  zero/small work、输入不变、max_pages 计数（非页号）。
- **真实**：4 份原件（恒锋 p61-62 跨页项目表、金禾 p223-224 多列表、中微 p41 叙述负例、
  世华 p5 新公司样本），全部 PyMuPDF 只读提取真实 dict/words/`find_tables` cell。
  - 恒锋：197 units 全绑定，76 细 cells，4 列，24 cell 粒度。
  - 金禾：218 units，51 细 cells，**最多 6 列**（6 列表真实细格绑定），12 cell 粒度。
  - 中微：45 units，**0 cells**（叙述页不虚构表格），仅 word/block。
  - 世华（新公司）：147 units，91 细 cells，3 列，31 cell 粒度。
  - Miniso：**UNAVAILABLE**（原件不在本机数据湖，binding 缺失→诚实跳过，绝不算真实通过）。
- 原件只读保持：4/4 SHA-256 + mtime + size 完全一致（opt-in 测试锁定 + `c-real-snapshots.json` 佐证）。

## 哪些仍没证明（诚实清单）

1. **未接生产**：无 parser/selector 消费本包，**不声称**修复了双栏顺序/细表头/关键业务召回；
   本包只证明真实细元数据可绑定投影。
2. 测量/绑定可靠 **≠** 正式细分栏/细表召回已通过：真实页仅作测量 oracle，未做召回率基准。
3. Miniso 经营表原件本机缺失（UNAVAILABLE），该优先样本未在本轮实测。
4. HTML/PPTX/OCR 前端当前不产出 bbox/字/格坐标，本包对它们保持 unknown，未做真实几何断言
   （缺字段不凭空造坐标）。合成用例只锁定"不虚构"行为。
5. 未在真实 5 万 unit 原件上跑满默认上限；预算上限用合成 large_case 验证 zero/small work 真停。
6. 坐标 frame 只对显式声明 dict/rect/rotation 做一致性和 transform 记录；未实现任意仿射变换换算
   （未知 frame 一律 partial、不猜物理尺寸）。

## ROOT 接线建议（additive，本包不改其他包）

1. ROOT 把原 parser **同一次** snapshot/table 读取显式传入（dict span/words/`find_tables` cell），
   本包绑定到已有 unit；随后接 `observation_adapter`/`layout_hints` 消费 `upstream_hints.words/cells/font_runs`。
2. 共享 wire 若缺字段，建议 additive 增补（不改既有字段含义）：binding 每细元素带
   `native_index`＋bbox＋可选 `char_start/end`；`cells` 带真实 `row/column/table_id`；
   页带 `coordinate_frame/rotation` 与可选 `dict_*/rect_*`/`transform` 供 frame 对齐。缺则 unknown，不猜。
3. `coverage.complete=false` / `unknown_frame_unit_ids` / `NO_FINE_GEOMETRY` 必须原样传给覆盖报告；
   看到 `NO_FINE_GEOMETRY`/`NO_REAL_GEOMETRY` 应触发前端补采细 geometry 或标 partial，不要下游按空格切列。

## 复跑

```bash
cd C:/Users/郑曾波/Projects/_harness_worktrees/shared-reading-completion-20261014/geometry
python -B -X utf8 -m pytest tests/unit/document_normalization_layout_snapshots -q          # A+B 离线 36 passed
CW_DU3_GEOMETRY_REAL=1 python -B -X utf8 -m pytest tests/unit/document_normalization_layout_snapshots/test_c_real_snapshots.py  # C 真实
python -X utf8 -m ruff check src/company_wiki/document_normalization/layout_snapshots tests/unit/document_normalization_layout_snapshots tests/fixtures/document_normalization_layout_snapshots
python -B -X utf8 .planning/du3-geometry/evidence/gen_c_evidence.py                        # 真实件证据
```

`bindings.local.json`（`{sample_id: 本地绝对路径}`）位于 `.planning/du3-geometry/`，已被该目录
`.gitignore` 排除、不入库；缺失或 SHA 不符时报 UNAVAILABLE/SKIP，绝不算真实通过。
