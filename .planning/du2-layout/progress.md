# DU2-LAYOUT 进度日志

## 2026-10-13 会话1（施工完成）
- 读取卡片、report、root_implementation、INTERFACES §5、DU/1 INTERFACES、DU-STRUCTURE 卡、sample_manifest。
- 建立 `.planning/du2-layout` PWF；只读探查真实页面几何（PyMuPDF）。
- **A 节点 RED**：先写 17 个冻结合成 fixture（`tests/fixtures/.../inputs/*.json`）+ 4 个测试模块，
  集中命令首跑 `ModuleNotFoundError: company_wiki.document_understanding` → 确认 RED 后实现。
- **B 节点**：实现 `contract/text_evidence/geometry/tables/headings/columns/relations/ordering/__init__`，
  修掉 11 个实现缺陷（见 findings.md 表）。离线集中命令：**32 passed, 5 skipped**，ruff 全绿。
- **C 节点**：`CW_DU2_LAYOUT_REAL=1` 集中命令：**37 passed**（5 个真实原件用例全跑，非 skip）；
  写 `.planning/du2-layout/c-evidence/{c_node_summary.json,probe_mapping.json}`；
  4 份原件跑前/跑后 SHA+mtime 一致（只读保持）。
- **性能观察**：1k/10k/40k 合成规模，work/unit 稳定 5.78–5.79（近线性）；
  40k 触顶 `max_groups=10000` → `GROUP_LIMIT_EXCEEDED` + complete=false（预期 partial）。
  记录于 `perf_observations.md` / `perf_scale.json`。
- **交付**：包内 `README.md`（API + ROOT 字段清单 + 歧义/partial 条件 + 复杂度 + 接线建议）、
  fixtures（23 文件 118 KiB）、测试、真实对照、handoff。
- 下一步（本 lane 不做）：ROOT 接收并把输出映射到既有 parser/section/hints，删除被替代的重复几何推断。

## 2026-10-13 会话2（完工后逐条复核）
- 按卡片 7 条步骤 + 三节点 + 测试/恢复条款逐条自检（不只跑测试）。
- 发现并修复 5 个遗漏/缺陷：表注 parent_table_id 不符接口、缺少"哨兵/finally 清理"测试、
  缺少"原件只读"自动断言、`GROUP_LIMIT_EXCEEDED` 诊断不带受影响 unit、
  续表上下文未传播到表区组；并修掉真实金禾 p224 续表误称表头（错误 high 类）。
- 新增测试模块 `test_b_recovery_and_readonly.py`；测试数 37→40（离线 34 passed/6 skipped）。
- 重新生成 c-evidence 与 perf_scale（work/unit 仍 5.78–5.79）。
- 最终：离线集中命令 34 passed/6 skipped；`CW_DU2_LAYOUT_REAL=1` 40 passed；ruff 全绿。

## 验证命令与结果（最终一次）
| 节点 | 命令 | exit | 结果 |
|---|---|---|---|
| A+B 离线（集中命令） | `python -B -X utf8 -m pytest tests/unit/document_understanding_layout_hints -q` | 0 | 34 passed, 6 skipped（真实原件 opt-in 未开） |
| C 真实原件 | 同命令 + `CW_DU2_LAYOUT_REAL=1` | 0 | **40 passed**（含原件 SHA/mtime 未变断言） |
| lint（仅本包） | `python -X utf8 -m ruff check src/company_wiki/document_understanding/layout_hints tests/unit/document_understanding_layout_hints tests/fixtures/document_understanding_layout_hints` | 0 | All checks passed |
| 规模观察 | `python -B -X utf8 tests/fixtures/document_understanding_layout_hints/scale_run.py --output .planning/du2-layout/perf_scale.json` | 0 | 见 perf_observations.md |
