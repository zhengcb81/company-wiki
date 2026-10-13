# DU2-LAYOUT 施工计划（PLAN_ID=du2-layout）

工作树：C:/Users/郑曾波/Projects/_harness_worktrees/document-reading-review-20261013/layout
分支：codex/du2-layout-20261013
卡片：docs/plans/document-understanding-2026-10-13/review/cards/DU2-LAYOUT.md
规格：review/INTERFACES.md 第5节（du2-layout-input/1 → du2-layout-hints/1）

目标：纯辅助函数 `company_wiki.document_understanding.layout_hints.derive_layout_hints`，
以调用方提供的 units + 可选字体/bbox 输出标题/分栏/经营表格结构/关系/阅读顺序提示。
不接生产、不改旧 parser、不分配新来源 locator、0 供应商调用。

## Phase A：接口冻结与正反形态 RED
- Status: complete
- 冻结 du2-layout-input/1 → du2-layout-hints/1 wire 断言（无新 locator、locator 透传）。
- 正反形态 RED：无编号标题vs普通短句、年份不是标题、跨栏页眉、左右中英栏、
  表格数字孤立行、表头/期间/单位/脚注、跨页续表、坏几何/缺字体/空页面。

## Phase B：本包实现与集中 unit
- Status: complete
- 分页/分区域布局分析：字体相对尺度+字重+几何的标题证据；缺字体不得仅因短文高置信；
  栏识别排除全宽页眉/跨栏表；reading_order 只输出关系提示，不改 ordinal 不删文字。
- 经营表结构：bbox 邻接/行列对齐/标题/单位/表头/脚注 → table_region/table_row/caption/footnote；
  跨页续表需列/表头延续依据并保留页差；多时期/地区/经营模式行不混并。
- 反例：相邻无关表、金额相同项目不同、双语非逐句对应、表无表头、脚注属上一图、坐标越界；
  合理低置信/partial 通过，错误 complete/high 失败；无公司名/固定页码/数字白名单。
- 确定性、输入非修改、引用存在、预算（max_units/max_groups/max_work_units）与复杂度（无全量 N²）。
- NEEDS_UPSTREAM_GRANULARITY：整行单 unit 无格子坐标时不虚构列，返回 partial。

## Phase C：真实样本对照与泛化
- Status: complete
- 名创 2024 港股年报 p12 门店表、恒锋工具募集说明书 p62-63 跨页项目、另一公司不同排版
  （金禾实业可转债 p223-225 财务/项目表 + 中微公司年报 p41 叙述表）。
- PyMuPDF 只读采样脚本仅属测试；probe IDs↔原页面坐标映射留证；
  充分输入（span 级）vs 当前生产输入（整行单格）分别报告。
- HTML/PPT 前端无真实几何 → 如实列 needs_upstream。

## 性能观察（非 CI 断言）
- 1k/10k/40k 合成规模：units/groups/work_units/耗时/峰值RSS 记录于 .planning/du2-layout/perf_observations.md。

## 交付
- API 文档（src/.../layout_hints/README.md 或 docs 形式随包）、实现、精简 fixtures 与测试、
  真实样本对照、ROOT 需保留/传入字段清单、handoff.json/handoff.md（含输入几何要求、
  未支持载体、歧义/partial 条件、复杂度、ROOT 接线建议）。

## 验证命令
python -B -X utf8 -m pytest tests/unit/document_understanding_layout_hints -q
python -X utf8 -m ruff check src/company_wiki/document_understanding/layout_hints tests/unit/document_understanding_layout_hints tests/fixtures/document_understanding_layout_hints

## 复核（会话2）
- Status: complete
- 按卡片逐条自检，修复 5 个遗漏/缺陷并补 2 个卡片条款测试（哨兵/finally、原件只读）。
- 离线 34 passed/6 skipped；真实 opt-in 40 passed；ruff 全绿。

## Next Step
实现与复核已交付并验证；等待 ROOT 接收（本 lane 不合主线/push/安装）。
