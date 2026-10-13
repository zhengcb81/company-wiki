# DU2-LAYOUT 性能与规模观察（集中节点，非 CI 断言）

工具：`tests/fixtures/document_understanding_layout_hints/scale_run.py`（测试侧脚本，
每个规模起独立子进程以取得干净的进程峰值 RSS）。
合成数据：`cases.scale_case(n)`，固定形态混合（编号标题、叙述段、中英双栏、含表头/脚注的数量表）。
原始输出：`.planning/du2-layout/perf_scale.json`。

| units | pages | groups | table_regions | rows | work_units | work/unit | 耗时(s) | 峰值 Python | 峰值 RSS | complete |
|---|---|---|---|---|---|---|---|---|---|---|
| 1,000 | 14 | 346 | 69 | 138 | 5,779 | 5.779 | 0.55 | 2.3 MB | 26.3 MB | true |
| 10,000 | 139 | 3,471 | 694 | 1,388 | 57,904 | 5.790 | 5.60 | 23.0 MB | 84.3 MB | true |
| 40,000 | 556 | 10,000（封顶） | 2,500 | 5,000 | 231,665 | 5.792 | 25.76 | 87.8 MB | 274.9 MB | **false** |

结论与说明：

- **近线性**：work/unit 在 1k/10k/40k 三档稳定在 5.78–5.79，无全量 N²、无无限跨页关联；
  耗时随规模近似线性（0.55s → 5.6s → 25.8s）。
- **40k complete=false 的原因**：该合成文档每约 4 个 unit 产出一个组（10k 组上限被触顶），
  诊断 `GROUP_LIMIT_EXCEEDED`（`unit_ids` 列出丢失结构的 unit），`coverage.complete=false`；
  这是“限额来自调用方、超限 partial”的预期行为，不是崩溃或静默丢数据。
- 未测项：**未在真实 5 万 unit 原件上跑满默认上限**；**未测多进程/并发下的内存叠加**；
  **未测 OCR/图像页**（本包不读像素，输入无几何即降级）。以上均明确未测，不推断。
- 工作计数为实际累计（每次行带/格子/聚类/映射比较计 1），通过 `WORK_UNITS` 诊断回传，
  可被调用方核对与收紧。
