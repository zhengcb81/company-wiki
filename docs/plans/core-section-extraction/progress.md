# 进度日志 — 核心章节提取

## 2026-08-06（方向澄清 + 调研 + spike + 计划批准）

### 路径演进（重要：从 backfill 转向章节提取）
- 起点是"CW-2.28 语义去重 backfill 生产化"。分析后发现全量 20,266 篇 × 单篇 ~195s ≈ 47 天（月级），worker 本身就在 backfill（FINGERPRINTING 阶段每轮 3 篇）。
- 用户选方案 D（缩小范围）并明确：真正要的是**核心章节内容用于研究**（MD&A / 主营业务 / 业务与技术），不是字节级去重。
- ⇒ **backfill 降级**（让 worker 自然消化，不专门加速）。转向**核心章节提取**新功能。

### 调研（两次 Explore）
1. 第一轮：两套平行栈（规范无章节维度 / 遗留有完整正则但冻结）、消费方缺口、推荐方案 C。
2. 第二轮：artifact_role 自由字符串、worker 集成 7 处、evidence char 对齐（PyMuPDF 有 / docling 无）、单写者三件套复用、实现骨架。

### Spike 验证（`_spike_sections.py`，项目根临时脚本）
- 独立正则 + 关键词表对真实 normalized.md：年报/半年报/招股书召回 100%、零噪音。
- MD&A 两变体、招股书"第X章"、子节全覆盖。详见 findings.md 发现 3。

### 计划批准
- plan-mode 计划 `C:\Users\郑曾波\.claude\plans\abstract-churning-matsumoto.md` 已批准。
- 首版范围：**核心三件套**（正则模块 + extract-sections CLI + sections-list 只读查询）。不含 worker 自动批、不含 evidence 映射。
- 落成项目三件套：`docs/plans/core-section-extraction/`（本目录）。

### 当前状态
- Phase 1（正则模块）：in_progress。已读现有模式（models/normalizer `_atomic_write`/artifact SQL/测试 fixture）。
- 下一步：写 `section_extractor.py` 纯函数 + `models.py` 版本常量 + 单元测试。

### 临时脚本（待清理）
- `_spike_sections.py`（项目根）：spike 验证脚本，Phase 3 清理时删（正则已移植进模块则删，或保留作参考）。
- `_observe_backfill.py`（项目根）：backfill 速率观测脚本，后台任务 `b1v3ctp8i`（25 分钟采样）。backfill 已降级，观测结果次要；任务结束后删脚本。

### backfill 速率观测结果（2026-08-06，后台 b1v3ctp8i，25 分钟采样）
- NOT NULL 3167→3171，**delta=4 篇**，rate **9.6 篇/小时**，pending 20,705。
- **不干预 ETA ≈ 90 天**（2,157 小时）。lock_ops 序列：normalize×4 / backfill×2 —— 印证 backfill 被严重夹击。
- 结论：backfill 降级正确（90 天季度级，不值得专门加速）。语义去重随 worker normalize 自然消化。观测脚本已删。

### 已验证事实（便于后续会话恢复）
- 真实文档 normalized.md 路径：`.source_catalog/derived/{sha[:2]}/{sha}/normalized.md`
- 已 normalize 的年报/半年报/招股书可通过 `SELECT d.title,a.path FROM artifacts a JOIN documents d ON d.document_id=a.document_id WHERE a.artifact_role='normalized' AND d.document_kind IN ('annual_report','semi_annual_report','prospectus')` 定位。
- normalized artifact 总数 4,792（含年报/半年报/招股书若干）；pending 未 normalize 仍多。

## 2026-08-06 实施完成（Phase 1-3 核心三件套）

### 完成项
- **Phase 1**：`section_extractor.py` 纯函数（`SECTION_RE`/`SECTION_KEYWORDS`/`SectionSlice`/`extract_sections_from_text`）+ `models.py` `SECTION_EXTRACTOR_VERSION` + 8 单元测试。全绿。
- **Phase 2**：`extract_sections_catalog`（选文档 SQL + 读 normalized.md + 切片 + `_atomic_write` 产物 + `store.transaction()` INSERT artifacts `role='sections'`）+ `service.py` `extract_sections`（`CatalogOperationLock` 包装）+ `__init__.py` 导出 + `cli.py` `extract-sections` 子命令 + 集成测试（写入 + 幂等 + force）。全绿。
- **Phase 3**：`section_query.py` `SectionQueryService`（只读 `mode=ro`）+ `cli.py` `sections-list` 子命令 + 集成测试覆盖查询。全量回归 **414 passed**（含新 9 项）；Ruff All checks passed；compileall ok。
- **清理**：`_spike_sections.py`（正则已移植进模块）、`_observe_backfill.py`（观测完成）已删。

### 产物
- 新文件：`src/company_wiki/source_catalog/section_extractor.py`、`section_query.py`
- 改：`models.py`、`service.py`、`__init__.py`、`cli.py`
- 测试：`tests/contract/test_source_catalog_section_extractor.py`（9 项）
- 运行时产物：`{catalog_dir}/derived/{sha[:2]}/{sha}/sections/{index.json, mda.md, business_overview.md, ...}` + artifacts 表一行 `role='sections'`
- CLI：`extract-sections --document-id/--document-kind/--limit/--force`、`sections-list --document-id`

### 真实库端到端验证（2026-08-06，已完成 ✅）
- `worker-pause` → 对三类真实文档各 1 篇跑 `extract-sections --document-id`：annual / semi / prospectus 全部 `completed=1, failed=0`。
- `sections-list` 验证返回章节：
  - 年报七一二（5）：financial_data / **business_overview** / **mda** / important_events / financial_statements
  - 半年报万华（4）：financial_data / **mda** / important_events / financial_statements
  - 招股书七一二 IPO（4）：risk_factors / **business_and_technology** / **mda** / important_events
- 三类全部命中核心章节（MD&A / 业务概览 / 业务与技术）；产物 `sections/index.json` + 各 role.md 结构正确（含 char_start/end 边界）。
- `worker-resume` 后 `desired=enabled, runtime=running`，已恢复。

### 未做（后续）
- Phase 4 worker 自动批 / Phase 5 evidence 映射：记 task_plan.md 末尾。
- git 提交：改动未提交，待用户决定。
