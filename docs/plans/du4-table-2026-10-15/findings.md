# 发现与限制

真实观察的来源及 SHA 见 fixtures/manifest.json。参考设计是未实施方案，不能当作已通过测试。目录内不含原始财报或生产数据库；生产接线由 ROOT 承担。

## 实施发现（2026-10-15）

- 真实保留包证实施工卡判断：表 0/1（门店数，as-of 2023/2024）与表 2/3/4（GMV，six/twelve months
  2023 + fiscal 2024）中，旧年标签与旧年值都位于左侧大合并格（覆盖标签列＋旧年列，甚至三列），
  逐值原生定位不存在 → 绑定输出明确 ambiguous；真正的新年值都在后续右列行的原生槽中，
  按真实表头路径绑定到 as-of 2024-12-31 或 fiscal 2024（fiscal_label "2024"）。
  全部 5 张表合计 bound 34 / ambiguous 7 / unavailable 0。
- 六个月 2023 与十二个月 2023 是两个不同列/期间（duration_months 6 vs 12），与 fiscal 2024
  三者互不合并；fiscal year 未被写成 12 个月；无披露的 start 保持 null。
- 表头证据只认 `header_rows` + 原生槽/`provenance` 的归属：粗整表 bbox（无 span 结果）只产生
  `coarse_geometry_ignored` 诊断，不被复制为细格；跨度覆盖关系（如 as-of 表头横跨两列）来自
  保留格 bbox 投影的 span 归属（适配器派生，已在 real_packet.py 文档头注明）。
- 空槽/未提取槽/合并未知严格区分（`slot_empty`/`slot_unavailable`/`slot_merged_unknown`）；
  负号、括号、破折号、百分比区间按 value_ref 原文保留，不做零化或换算。

## 限制（交给 ROOT/后续）

- 输入契约语义由本卡冻结：数据格 `text_refs` 为逐值字符引用，`header_refs` 为标注/表头引用；
  出现在任何 `header_refs` 中的引用视为标签、不产生 measurement。合并大格可以整格一条
  value_ref（无法逐值拆分时）→ ambiguous。
- 真实包表 4（p20t1）raw_rows 截断，行槽只能从 replay unit 的 row_cells 恢复（无格 bbox、
  空串与 none 不可分）；其合并格因此按"无表头路径"判 ambiguous，观测 `observation_truncated`。
- 单位/范围/脚注识别是有限词表＋括号组的有界匹配，只扫描标签与表头路径文本（值文本仅识别
  单元格级 % / 币种），不是通用语义理解；未知单位保持空 `unit_refs` 而非猜测。
- 未实现/未验证：真实引擎接线、真实 E2E、cache/旧 Ref 恢复、另一公司/格式真实 holdout
  （由 ROOT 负责）。未调用任何供应商 API。
