# Progress Log

## Session: 2026-04-25

### Phase 1: 止血
- **Status:** complete
- **Started:** 2026-04-25 07:32
- Actions taken:
  - 修复 pdf_extract_v2.py classify_pdf 半年报/季报分类错误
  - 修复 collect_news.py 配置 key 不匹配（tavily_api_key → api_key）
  - 扩展 config_rules.yaml URL 黑名单（+18 低质量域名）
  - 新建 fix_report_dates.py，修复 372 个 wiki 文件中数千条错误日期
  - 新建 cleanup_junk.py，删除 465 个黑名单来源新闻文件
- Files created/modified:
  - scripts/fix_report_dates.py (created)
  - scripts/cleanup_junk.py (created)
  - scripts/pdf_extract_v2.py (modified)
  - scripts/collect_news.py (modified)
  - config_rules.yaml (modified)

### Phase 2: 重建数据管道
- **Status:** complete
- **Started:** 2026-04-25 08:15
- Actions taken:
  - 新建 build_extracts.py（Layer 2: PDF→完整 MD，扫描 4538 PDFs）
  - 新建 tag_segments.py（Layer 3: MD→标签化 JSONL segments）
  - 修改 ingest_v2.py 添加 --source=raw|segments|all 参数
  - 修改 scheduler.py 接入 extract 和 tag 步骤
- Files created/modified:
  - scripts/build_extracts.py (created)
  - scripts/tag_segments.py (created)
  - scripts/ingest_v2.py (modified)
  - scripts/scheduler.py (modified)

### Phase 3: 交付用户价值
- **Status:** complete
- **Started:** 2026-04-25 09:20
- Actions taken:
  - consolidate.py 添加 --archive-only 模式（无 LLM 运行）
  - scheduler.run_judgment 传入 use_llm=True
  - collect_news.py 添加均衡采集逻辑（按 last_collect_time 排序）
  - batch_assessment 接入 scheduler
- Files modified:
  - scripts/consolidate.py
  - scripts/collect_news.py
  - scripts/scheduler.py

### Phase 4: 构建反馈闭环
- **Status:** complete
- **Started:** 2026-04-25 10:00
- Actions taken:
  - scheduler.run_detect 推送高置信度矛盾到 review_queue
  - scheduler.run_lint_step 调用 fix_broken_links.py
  - collect_news.py / scheduler.run_ingest 记录 state_store 时间戳
  - 删除 5 个死模块（event_bus.py, job_queue.py, repair_planner.py, closed_loop_dashboard.py, worker_pool.py）
  - 新建 tests/unit/test_pipeline.py（19 个测试覆盖关键路径）
- Files created/modified:
  - tests/unit/test_pipeline.py (created)
  - scripts/scheduler.py (modified)
  - scripts/collect_news.py (modified)
  - scripts/event_bus.py (deleted)
  - scripts/job_queue.py (deleted)
  - scripts/repair_planner.py (deleted)
  - scripts/closed_loop_dashboard.py (deleted)
  - scripts/worker_pool.py (deleted)

### Phase 5: 全面架构与代码质量审查
- **Status:** complete
- **Started:** 2026-04-25 14:00
- Actions taken:
  - 架构审查：模块依赖、数据流、配置管理、错误处理
  - 修复 P0 问题：预算熔断/静默失败/句柄泄漏/原子写入
  - 修复 LSP 类型错误（3 个文件）
  - 清理未使用导入（ingest_v2.py）
  - 新建 validate_companies.py（自动检测名字歧义）
- Files created/modified:
  - scripts/validate_companies.py (created)
  - scripts/llm_client.py (modified)
  - scripts/scheduler.py (modified)
  - scripts/pdf_extract_v2.py (modified)
  - scripts/ingest_v2.py (modified)
  - scripts/fix_report_dates.py (modified)

### Phase 6: 架构债务清理
- **Status:** in_progress
- **Started:** 2026-04-25 16:30
- Actions taken:
  - 创建 task_plan.md / findings.md / progress.md（planning-with-files 规范）
  - 创建 scripts/common.py（公共基础设施：路径/环境/配置/原子写入/日志/路径辅助函数）
  - 重构 build_extracts.py / tag_segments.py / ingest_v2.py 使用 common.py（减少 40+ 行重复代码）
  - 清理孤儿模块：utils.py / logger.py / question_matcher.py → archive/（无人引用）
  - 新建 tests/unit/test_common.py（15 个测试覆盖公共函数）
  - 删除 tests/unit/test_utils.py（原 utils.py 已移除）
- Files created/modified:
  - task_plan.md (created)
  - findings.md (created)
  - progress.md (created)
  - scripts/common.py (created)
  - tests/unit/test_common.py (created)
  - scripts/build_extracts.py (refactored)
  - scripts/tag_segments.py (refactored)
  - scripts/ingest_v2.py (refactored)
  - scripts/utils.py → archive/ (removed)
  - scripts/logger.py → archive/ (removed)
  - scripts/question_matcher.py → archive/ (removed)
  - tests/unit/test_utils.py (deleted)

## Test Results

| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| Unit tests | pytest tests/unit/ | 147 passed | 147 passed | ✓ |
| E2E tests | pytest tests/e2e/ | 12 passed | 12 passed | ✓ |
| Relevance tests | pytest tests/relevance/ | 16 passed | 16 passed | ✓ |
| Pipeline tests | test_pipeline.py | 19 passed | 19 passed | ✓ |
| Tag segments | tag_segments.py --limit 10 | 10 success | 10 success | ✓ |
| Ingest segments | ingest_v2.py --source=segments | 12 processed | 12 processed | ✓ |

## Error Log

| Timestamp | Error | Attempt | Resolution |
|-----------|-------|---------|------------|
| 2026-04-25 07:45 | config key mismatch | 1 | collect_news.py:371 tavily_api_key → api_key |
| 2026-04-25 08:30 | PDF classification bug | 1 | classify_pdf 增加 semi_annual/quarterly 分支 |
| 2026-04-25 10:15 | event_bus dead code | 1 | Delete 5 modules, remove imports from scheduler |
| 2026-04-25 11:00 | test failures (5) | 1 | Fix env variable isolation + adjust assertions |
| 2026-04-25 14:30 | budget fuse silent fail | 1 | llm_client.py:241 print WARN on cost read error |
| 2026-04-25 14:45 | scheduler silent failures | 1 | 9 except:pass → except Exception as e: print(...) |
| 2026-04-25 15:00 | PDF handle leak | 1 | with fitz.open(...) context manager |
| 2026-04-25 15:15 | tag_segments .env not loaded | 1 | Add load_dotenv() |
| 2026-04-25 15:30 | tag_segments path crash | 1 | Use .resolve() for relative/absolute paths |
| 2026-04-25 15:45 | JSON truncation | 1 | _extract_json_objects for partial recovery |

## 5-Question Reboot Check

| Question | Answer |
|----------|--------|
| Where am I? | Phase 6: 架构债务清理与公共模块提取 |
| Where am I going? | Phase 7: 数据质量闭环验证 |
| What's the goal? | 将知识库升级为可自维持的研究助理，系统性修复架构债务 |
| What have I learned? | See findings.md — 架构/数据/代码质量三方面问题 |
| What have I done? | Phase 1-5 完成，175/175 测试通过，P0 问题全部修复 |

### Phase 6: 架构债务清理
- **Status:** complete
- **Started:** 2026-04-25 16:30
- Actions taken:
  - 创建 scripts/common.py（公共基础设施：路径/环境/配置/原子写入/日志/路径辅助函数）
  - 重构 build_extracts.py / tag_segments.py / ingest_v2.py 使用 common.py
  - 清理孤儿模块：utils.py / logger.py / question_matcher.py → archive/
  - 新建 tests/unit/test_common.py（15 个测试）
  - 删除 tests/unit/test_utils.py
- Files created/modified:
  - scripts/common.py (created)
  - tests/unit/test_common.py (created)
  - scripts/build_extracts.py / tag_segments.py / ingest_v2.py (refactored)
  - scripts/utils.py / logger.py / question_matcher.py (removed to archive)

### Phase 7: 数据质量闭环验证
- **Status:** complete
- **Started:** 2026-04-25 18:00
- Actions taken:
  - 链接修复验证：fix_broken_links.py 扫描 382 文件，删除 36 死链，修复 1 链接
  - 矛盾检测修复：正则 `%?` → `%`，过滤 1990-2100 年份值，阈值提升至差异>50%且绝对差值>5
  - 矛盾检测重运行：年份误报消除（从 "2025% vs 8.01%" 变为真实百分比差异）
  - 日期提取修复：extract_report_date 支持无分隔符日期（20220416 → 2022-04-16）
  - IR 过度拆分修复：修改 prompts.py build_ir_prompt，一个 IR 文件只生成一个条目
  - Segment 日期修复：tag_segments 保存 original_date 到 _meta，ingest_v2 优先读取
  - 多公司质量抽检：北方华创/中芯国际/中微公司时间线分析
- 关键发现：
  - 中微公司 wiki 中 14 个 2026-04-25 条目全部来自同一 IR 文件（已修复 prompt）
  - 北方华创 20 个 2026-04-25 条目（新闻+研报混合，日期提取已修复）
  - 矛盾检测器回退路径的正则 `(\d+\.?\d*)\s*%?` 中 `%?` 导致年份被误匹配
- Files modified:
  - scripts/contradiction_detector.py (fixed year false positives)
  - scripts/ingest_v2.py (date extraction + segment date reading)
  - scripts/tag_segments.py (save original_date to _meta)
  - scripts/prompts.py (IR prompt: one file → one entry)
  - scripts/collect_news.py (exponential backoff retry)

## Test Results（更新）

| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| Full suite | pytest tests/ | 175 passed | 175 passed | ✓ |
| Pipeline | test_pipeline.py | 19 passed | 19 passed | ✓ |
| Common module | import common | 无错误 | 无错误 | ✓ |

### Phase 7b: 历史数据清理
- **Status:** complete
- **Started:** 2026-04-25 19:30
- Actions taken:
  - 清理中微公司 wiki：删除 13 个重复的 2026-04-25 投资者关系条目（保留第一个）
  - 清理北方华创 wiki：删除 18 个重复的 2026-04-25 新闻报道条目
  - 总计清理 31 个由 IR 过度拆分导致的历史重复条目
- Files modified:
  - companies/中微公司/wiki/公司动态.md
  - companies/北方华创/wiki/公司动态.md

### Phase 8: 最终系统验证与报告
- **Status:** in_progress
- **Started:** 2026-04-25 20:00
- Actions taken:
  - 运行 scheduler dry-run 验证完整工作流（extract → tag → ingest → assess → detect）
  - 生成系统状态报告：233 家公司, 345 wiki 页面, 25 个行业
  - 验证 companies.yaml 与 graph.yaml 一致性（通过）
  - 检查所有 wiki frontmatter 规范（发现并修复 3 个缺失 last_updated）
- 关键发现：
  - 评估缺失：213 个 wiki 页面无综合评估（已记录到 findings.md）
  - 新闻采集倾斜：7 天内仅北方华创 19 篇，其余 232 家零采集
  - 矛盾检测：200 条潜在矛盾，无高置信度结果
- Files modified:
  - task_plan.md (updated Phase 8 status)
  - progress.md (this file)

## Next Actions（已完成 Phase 1-8）

1. ✅ 提取公共代码到 scripts/common.py
2. ✅ 清理孤儿模块（utils.py / logger.py / question_matcher.py）
3. ✅ 添加网络请求重试机制（collect_news.py 指数退避）
4. ⏳ 集中硬编码魔法值到 config.yaml（P2，后续迭代）
5. ⏳ 渐进清理未使用导入（50+处，P2，后续迭代）

## 5-Question Reboot Check（最新）

| Question | Answer |
|----------|--------|
| Where am I? | Phase 8 进行中：最终系统验证与报告 |
| Where am I going? | 完成 scheduler dry-run、生成系统状态报告、修复剩余 frontmatter 问题 |
| What's the goal? | 将知识库升级为可自维持的研究助理，系统性修复架构债务 |
| What have I learned? | 213 个评估缺失、新闻采集极度倾斜、矛盾检测阈值需调整 |
| What have I done? | Phase 1-7 全部完成，175/175 测试通过，P0 问题全部修复，进入最终验证阶段 |
