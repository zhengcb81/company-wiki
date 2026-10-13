# layout_hints — 纯布局辅助能力（DU2-LAYOUT lane）

`derive_layout_hints` 消费调用方已有的 units（可选字体/bbox），输出标题、正文分栏、
候选表区/行组/表头/题注/脚注、上下文关系与阅读顺序提示。
它**不是**生产 parser：不打开 PDF/HTML/PPT、不做 OCR、不读配置/网络/时钟、
不分配新来源 locator、不修改输入、不生成投资含义。ROOT 负责把输出映射到既有
parser/section/hints 与唯一几何实现。

```python
from company_wiki.document_understanding.layout_hints import derive_layout_hints

result = derive_layout_hints(observation, limits={"max_work_units": 2_000_000})
```

## 1. 输入 `du2-layout-input/1`

```json
{
  "schema_version": "du2-layout-input/1",
  "source_ref": {"source_id": "opaque", "source_sha256": "opaque"},
  "coverage": {"opaque_pages": [], "deferred_pages": []},
  "pages": [
    {"page": 12, "width": 595.276, "height": 807.874,
     "units": [
       {"unit_id": "u1", "ordinal": 0, "locator": "opaque-locator",
        "text": "门店数量", "bbox": [62, 291, 158, 302],
        "font_size": 8.8, "font_weight": "regular", "kind": "text",
        "upstream_hints": {}}
     ]}
  ]
}
```

约定：

- `unit_id` 全局唯一；`ordinal` 唯一、非负（不要求连续）；重复即 `ValueError`。
- `locator` 为既有 opaque 字符串或 `null`，**原样透传**，辅助函数永不新建/改写来源 locator；
  输出 wire 中没有任何 `locator` 字段。
- `bbox` 缺省或 `null` = 无几何（不等于零）；`font_size`/`font_weight` 缺省 = 未知证据。
  单页同一坐标系，单位不混用（PDF/HTML/PPT 差异由前端适配）。
- `bbox` 上下界反转 → 诊断 `BAD_GEOMETRY` 且该 unit 推迟；
- `bbox` 超出声明页宽/页高 → 诊断 `COORDINATE_OUT_OF_BOUNDS` 且该 unit 推迟；
- `bbox` 缺失 → 诊断 `MISSING_GEOMETRY`，该 unit 仍参与纯文本证据（置信度封顶）。
- `kind`/`upstream_hints` 只作弱提示，**不参与**标题判定（判定仅用文本形态＋字号/字重/几何）。

`limits` 只能**收紧**内置上限（默认 `max_units=50000`、`max_groups=10000`、
`max_work_units=2000000`）：`resolved = min(caller, default)`，调用方无法放宽。

## 2. 输出 `du2-layout-hints/1`

```
{schema_version, source_ref(透传), unit_hints[], groups[], relations[],
 reading_order[], coverage{processed_unit_count, deferred_unit_ids, opaque_pages,
 deferred_pages, complete}, diagnostics[]}
```

- `unit_hints`：每个输入 unit 一条，顺序=输入顺序（页序＋ordinal）。
  `heading_level`（0 基不适用；1=最高层）、`text_column`（0 基正文栏，`null`=无分栏/不限栏）、
  `confidence`（high/medium/low/unknown）、`basis`（短代码，不复制正文）。
- `groups`：`kind ∈ {heading, column_lane, table_region, table_row, caption, footnote}`。
  行与表注通过 `parent_table_id` 归属已存在的 `table_region`（表注=脚注组；题注是上下文组，
  本身不是表注，`parent_table_id` 为 `null`，靠 `caption_for` 关联）；
  `member_unit_ids` 按阅读视图排序（缺失时按 `ordinal`）；
  `required_context_unit_ids` 表示“若断言该行数值就必须同时保留”的表头/期间/单位/题注/脚注 unit
  （跨页续表还会带上原表的题注/表头上下文）；
  `cells` 行列为表内 0 基坐标，`row_span` 当前恒为 `null`，`column_span` 为覆盖列槽数。
- `relations`：`header_for | caption_for | footnote_for | continuation`，
  一律 **from=上下文组 → to=被解释组**；`continuation` 从上一表区指向下一页续表；
  续表的 `basis` 必含 `page_gap=N`，并至少含 `repeated_header` 或 `column_alignment`。
- `reading_order`：每页一条（`ordered_unit_ids` 按行带自上而下、带内自左向右）。
  **只作视图提示**：不改输入 `ordinal`、不删文字；无几何 unit 进 `UNORDERABLE_UNIT` 诊断。
- `diagnostics`：`unit_ids` 引用已存在的 unit，`detail` 为短诊断。
  代码集：`BAD_GEOMETRY`、`COORDINATE_OUT_OF_BOUNDS`、`MISSING_GEOMETRY`、
  `UNIT_LIMIT_EXCEEDED`、`WORK_BUDGET_EXCEEDED`、`GROUP_LIMIT_EXCEEDED`、
  `NEEDS_UPSTREAM_GRANULARITY`、`LOGICAL_ROW_UNRESOLVED`、`CONTINUATION_CLAIMED`、
  `CONTINUATION_ROWS_NOT_HEADER`、`UNORDERABLE_UNIT`、`WORK_UNITS`（累计工作计数，信息项）。
  超限类诊断都带受影响 `unit_ids`（`GROUP_LIMIT_EXCEEDED` 列出因组上限而丢失结构的 unit）。

## 3. 判定规则（可复核）

- **正文尺度**：取含 ≥12 字符文本 unit 的字号中位数作为正文尺度。
- **标题**：证据=字号相对尺度、字重、编号（`第X章/一、/（一）/1.1`）、上下留白隔离、
  短文本（≥40 字符不参与）；**否决**=年份行、日期行、纯数字、以句末标点结尾的句子、
  表区成员、题注/脚注行、跨页页眉页脚。缺 `font_size` 时不得判 high；
  短文本单独永远不构成标题。`heading_level` 由编号层级或字号分层给出，不确定则 `null`。
- **分栏**：仅用“非表区、非题注/脚注、非页眉页脚带（上 8%/下 10%）”的正文 unit，
  以空白间隙切分；切分位置由整篇文档的候选 unit 共同学习（稀疏页可复用同版式切分），
  但 `column_lane` 组按页产出。跨栏（跨页眉、跨栏表）unit 不属于任何栏且不拆栏。
- **表区**：按行带聚类→带内按空白间隙聚合为格子→成员行带需满足 ≥2 个多格行带
  （或“整行单格对齐网格”≥3 行带且 ≥2 行带含数量）。正文段落、跨页页眉页脚、
  编号小标题、题注/脚注行带不参与表区。
- **列槽**：只用“含数量的数据行带”的格子做水平区间聚类（因此跨列表头无法合并相邻数量列）；
  表头/题注格子再按区间重合映射到列槽并给出 `column_span`。
- **表头块**：表区前导、无数量证据的行带合并为一个表头行组（多行带=折行表头）；
  若整个表区都没有数量（纯文本表），最多只取首个行带作表头，其余为数据行。
- **题注/脚注**：表区上/下相邻、匹配“表N/图N/单位：/截至…as of”或“注：/*/[n]”的单格行带，
  分别建 caption/footnote 组并经关系指向该表区；孤立题注（如图注）不连到下方表格。
- **跨页续表**：仅当上一表区贴页底（≥70% 页高）、下一表区贴页顶（≤25% 页高）、
  下一页表区**没有新题注**、且存在 ≥2 个对齐列槽或重复表头时才成立；页差写入 `basis`。
  金额相同、内容相似都不作为延续依据。
  仅有列对齐（无重复表头）的续表：其前导行带视为**续行**，不新称表头
  （诊断 `CONTINUATION_ROWS_NOT_HEADER`）；只有重复表头才建立 `header_for`。
- **整体降级**：整行单格（无格子坐标）→ 表区 `low` + `NEEDS_UPSTREAM_GRANULARITY`，`cells=[]`，
  绝不按空格虚构列；列内容跨行带折行无法判定逻辑行 → `LOGICAL_ROW_UNRESOLVED`，该行封顶 `medium`。

## 4. ROOT 需保留/传入的字段清单

必须（缺一项则能力降级）：

| 字段 | 要求 | 缺失后果 |
|---|---|---|
| `unit_id` / `ordinal` | 稳定唯一，与来源 locator 绑定 | `ValueError` |
| `locator` | 既有 opaque 值原样带出（本包不新建） | 消费侧无法回原文 |
| `bbox` | 单页同坐标系 `[x0,y0,x1,y1]`，**span/cell 级**（不是整行） | 列恢复失效 → `NEEDS_UPSTREAM_GRANULARITY` |
| `page`/`width`/`height` | 物理页号与页面尺寸（同一单位） | 越界检测、栏切分、跨页续表失效 |
| `font_size` | 绝对字号（pt 或前端等价尺度） | 标题降为 medium 以下 |
| `font_weight` | `bold/regular/...` 或数值字重 | 标题证据减弱 |
| `coverage.opaque_pages/deferred_pages` | 透传 | 消费侧无法区分未读页 |

增强（有则更准）：span 级 `bbox`（列/格子）、表头单元格几何、DOM 路径（HTML）、
形状框（PPT）、跨页页眉文本、`kind` 弱提示。

**未支持载体**：HTML 与 PPT——当前前端不产出 bbox/font_size，无法提供真实几何，
因此不做真实几何断言（`needs_upstream`）；前端补齐 span 级几何后可直接复用本包，
无需第二套布局实现。

## 5. 歧义与 partial 条件（诚实边界）

- 整行单格抽出（当前生产输入的名创门店表形态）→ 只能给表区/行组提示，不给列；
- 折行逻辑行、跨行单元格交错 → 保留视觉行带并诊断，不猜逻辑行；
- 双栏并不逐句对应时不做任何句级配对，双语只给栏与阅读顺序提示；
- 表区无表头时不产出 `header_for`，表区置信度封顶 `medium`；
  续表若没有重复表头证据，其前导行带只作续行，不新称表头；
- 图注脚注只按“上方题注”归属，不连到其下方表格；
- 预算/上限耗尽 → `coverage.complete=false` 且未分析 unit 进入 `deferred_unit_ids`。

## 6. 复杂度与预算

- 按页/行带/邻接处理，列槽聚类只比较聚类区间；工作计数逐次累加（`WORK_UNITS` 诊断），
  1k/10k/40k 合成规模实测 ≈ 5.78 work/unit（近线性），无全量 N²、无无限跨页关联。
- `max_units` 截断、`max_work_units` 中止均产生 partial + deferred，绝不提高外部
  时间/像素/OCR/模型预算。

## 7. ROOT 接线建议

1. 让 PDF 前端以 **span 级**透传 `bbox`/`font_size`/`font_weight`（PyMuPDF span 即可），
   HTML 用已有 DOM 几何，PPT 用形状框；`locator` 必须来自公共解析器。
2. 用一个共享几何实现替换旧的 column/heading 猜测：ROOT 只接 `derive_layout_hints`，
   删除被替代的重复推断，不再新增第二套布局判定。
3. 章节识别用 `heading_level`＋行顺序；表结构用 `groups`/`cells`＋`required_context_unit_ids`；
   `reading_order` 只用于展示/选包顺序，不写回 `ordinal`。
4. `NEEDS_UPSTREAM_GRANULARITY` 出现时，ROOT 应触发前端补采细粒度几何（或标 partial），
   不要在下游按空格切列。
5. 预算：ROOT 用既有全局上限收紧本包 `limits`；`complete=false` 必须原样传给下游覆盖报告。


## 8. ROOT 接收修复（1.1.0）

`feature_version=1.1.0` 记录算法版本；wire 的 du2-layout-hints/1 不变。

- 唯一 WorkBudget 在操作前预留工作量；耗尽立即通过私有中止异常返回 partial。预算耗尽时不发布未完成表/高置信提示，所有输入 unit 明确 deferred，原件、ID、locator 不变，WORK_UNITS 不超过限额。
- 标题上下留白通过两个方向扫描与压缩坐标区间索引查找；任何横向重叠均视作潜在邻居，属于保守证据（可降低标题置信，不制造留白）。表列只扫描水平活动区间；正文栏和上下文使用局部/顺序索引。密集歧义匹配仍受同一工作预算中止，不声称所有病理输入严格线性。
- 多页续表必须唯一匹配，题名、期间、单位、表头、脚注和先前继承的上下文沿前向链传递；一对多/多对一匹配保留 CONTINUATION_AMBIGUOUS，不拼接项目。
- 上游 opaque_pages/deferred_pages 使 complete=false。
- 前端若知道 unit 的框是整行/整块/整表，应传 upstream_hints.geometry_granularity=row|block|table_region。此声明不证明表格列，不输出 cells；保留 NEEDS_UPSTREAM_GRANULARITY/partial。span/cell 只表示前端已实际提供该颗粒度，不应按空格造坐标。
- 输入验证、结果序列化及原始文本处理仍随输入量线性工作；WORK_UNITS 计量布局分析遍历/比较，并非 CPU 指令/字节数或独立墙钟超时。

接收证据见 .planning/du2-layout-reception：初始五项行为 RED；模块 41 PASS/6 real SKIP；最终八项根因测试 PASS；四份原件两种粒度回放 SHA/mtime/size 不变。完整模型摘要、OCR、生产定位适配、真实 50k 单元及多进程峰值内存尚未验证；作者旧 5.78 work/unit 数值不能代表修复后的计量。
