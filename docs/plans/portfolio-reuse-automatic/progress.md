# 进度日志 — portfolio 复用自动化（系统化改进）

> **2026-08-09 状态：`completed_historical_scope + superseded_for_generalization`。** dayu Strategy B 窄范围历史完成；未来 root/Dropbox/统一 resolver 只在 FCAP r2 更新。

## 2026-08-04（根因调查 + 方案制定，未开始实施）

### 完成
- 用 planning-with-files 技能建立本规划目录（`docs/plans/portfolio-reuse-automatic/`）。
- 完成 `findings.md`：三层根因（孤儿手动命令 / 锁阻塞 / 端到端未接线），含穷尽搜索与实测证据。
- 完成 `task_plan.md`：7 个 Phase（0 前置核查 → 1 自动提升集成 → 2 锁健壮性 → 3 语义护栏 →
  4 测试 → 5 文档 → 6 E2E），设计决策、验收标准、风险、文件清单。

### 根因结论（详见 findings.md）
1. **R1（架构）**：`promote_from_portfolio`/`promote_all_for_entity` 仅被 `import-portfolio` CLI 调用；
   worker 管线、acquisition service、filing-fetch 全零调用 → 已提交功能是"孤儿"手动命令。
2. **R2（运维）**：import-portfolio 走 `import_staged` 要取全局 `operation.lock`；worker 回填批
   几乎永远占锁 → 实测三次 `CatalogOperationLockedError`（pid 1980/23160）→ 无 pause-around/重试。
3. **R3（期望）**：原计划刻意 filing-fetch 零改动，获取路径对 portfolio 从未接线。

### 调查中的实测记录
- `git show 7ce2774`：功能已提交（2026-08-03，金山云验证）。
- `grep -rn` src/ + filing-fetch/scripts/：promotion 唯一调用者 = cli.py。
- worker.py 阶段序列：SCANNING→NORMALIZING→FINGERPRINTING→LLM→EXPORT，无提升阶段。
- acquisition_service.py / acquisition.py：grep portfolio = 0。
- import-portfolio（无 dry-run）对 6082：三次 `CatalogOperationLockedError`。
- import-portfolio --dry-run 对 6082：正常返回 dry_run（发现/映射逻辑有效）。
- worker 干预记录：本调查中执行过 1 次 pause → 真实提升尝试（输出被截断，未能确认结果）→ resume
  （新 pid 23160，enabled+running）；批次幂等续跑，无残留。

### 未开始 / 待办
- 全部实施阶段（Phase 0-6）均为 pending。
- Phase 0 前置核查是开工前提（ensure 全流程、MISSING 语义、meta 映射、锁行为基线）。

### 下一步
- 等用户确认 task_plan.md（尤其：自动提升默认开启 vs 配置开关；是否本期顺带做锁重试）后进入 Phase 0。


## 2026-08-04（Strategy B 实施完成——config-driven 只读复用）

### 决策转变
- 用户审查后决定：**弃用 Strategy A（ensure 自动提升）**，改行 **Strategy B（只读复用，config-driven）**：
  "已索引即可复用"、加目录 = 配置加一行、无磁盘拷贝/提升状态机。

### 实施（B）
- **B1 配置化可复用 root**：`CatalogConfig.reusable_root_kinds`（默认 `[company_raw]`）+
  `source_catalog.yaml` 配置 + resolver 改用配置集合（trace 改为 `no_reusable_root_location`）。
- **B2 元数据富化**（scanner dayu_portfolio 专用路径）：filing meta.json 身份/分类回填——
  form_type→document_kind（FY/H1/Q1-Q3，分类器 + admission 同步，繁体 年報/中期報告 token）；
  `security_id←ticker`、`market←实体级 meta.json`；prefer-new 合并增加
  provider_document_id 条件（修复提升 REUSED_EXACT 断言回归）。
- **身份归一化**：resolver `_identity_matches` security_id 去前导零 + 小写（HKEX 03896==3896）。
- **B3 filing-fetch 围栏配置化**：`allowed_handle_roots`（config/company_wiki.json，token 展开），
  `validate_handle(allowed_roots=...)`；修复 CLI 默认 `--config=None` 导致 allowance 回退的 bug。
- **回滚 A**：移除 ensure 自动提升钩子/开关/测试（acquisition.py、acquisition_config.py、
  cli.py、yaml、test_source_catalog_auto_promote.py）；`_retry_on_catalog_lock` 保留
  （直接 ensure/import-portfolio 的锁退避）；`import-portfolio` CLI + promoter 保留为固化工具。
- **陈旧防护**：`_handle` 文件存在性校验（已存在，覆盖所有 root）。

### 验证
- 契约测试：`test_source_catalog_reusable_roots.py`（3 项：配置化放行/默认排除/陈旧不复用）+
  filing-fetch 围栏 3 项（放行/拒绝/配置加载）；回归 32+ 项通过（promoter 4 项修复后全绿）。
- **真实 E2E（2020.HK 安踏体育 FY2023 年报）**：filing-fetch 只读请求 → `capture_ready`，
  collector=`filesystem-catalog-dayu_portfolio`，**零下载、零提升**，https_url/日期/年份齐全。
- 过程中发现的存量问题：worker 写突发导致 SQLite `database is locked`（读连接 5s busy_timeout
  偏短；主 store 读连接 30s 无碍）——E2E 以暂停 worker 规避；列为后续改进候选。

### 文档
- ADR-008 重写为 B 方案；OPERATIONS.md §一点五 改为 config-driven 直接复用；filing-fetch SKILL.md
  Notes 补充；task_plan.md 状态更新。

### 待办/候选
- scanner 元数据富化对存量文档需重扫生效（scanner 复用未变更文件元数据）——可加 force/reprocess
  或文档化"删 location 行重扫"。
- SQLite 读连接 busy_timeout 提升（5000→30000）与 worker 写突发共存性，列为后续。


## 2026-08-06（两项候选收尾完成）

### 候选 1：存量文档重扫 re-enrich —— 验证为"普通重扫即生效"，无需 force/删行
- **实证**：构造 dayu_portfolio 文档，把 DB 中 `metadata_json` 手工降级为 pre-ADR-008 最小标记
  （仅 source_title/filing_date），文件字节不动，普通 `catalog.scan()` 后 `dayu_meta` 恢复
  form_type/fiscal_year/security_id/market/source_url 全部字段，`document_kind` 也回填为
  annual_report。机制 = scanner 每轮重建文档元数据 + `prefer_new` 提升更完整富化副本。
- **落地**：新增回归测试 `test_plain_rescan_re_enriches_existing_dayu_document`
  （test_source_catalog_url_enrichment.py，7 passed）。
- **文档修正**：OPERATIONS.md §一点五 原先"可删除对应 location 行后重扫重建"的注记改为
  "普通重扫即自动生效，无需删行；需立即生效时手动 scan 该 root"。
- 结论：**不需要 force/reprocess 子命令**——普通重扫已覆盖存量，新增 force 属冗余表面。

### 候选 2：SQLite 读连接 busy_timeout 5000→30000 —— 完成
- 读连接与主 store 读连接（已 30000）对齐，容忍 worker 写突发，不再产生 E2E 中偶发的
  `database is locked`（读连接 5s busy_timeout 偏短）。
- 改动：`store.py::read_pipeline_status`、`extraction_quality.py::_connection`、
  `evidence_query.py::_connection` 三处 `timeout=5.0`→`30.0`、`busy_timeout=5000`→`30000`。
- 回归测试：三个只读连接各新增 busy_timeout=30000 断言
  （test_source_catalog_extraction_quality.py / evidence_query.py / control.py）。

### 验证
- source_catalog 全量 contract：**406 passed**（226s）；Ruff、compileall 全绿。
- 相关 focused：extraction_quality/evidence_query/control/url_enrichment/reusable_roots/
  placeholder_governance/portfolio_promoter = 75 passed。
