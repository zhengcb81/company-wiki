# Task Plan: 上市公司知识库系统改进

## Goal

将知识库从"半自动研究助理"升级为"可自维持的研究助理"，并系统性修复架构债务。

## Current Phase

Phase 8: complete → Phase 9: pending（待用户决策）

## Phases

### Phase 1: 止血 — 修复每日错误数据
- [x] 修复 classify_pdf 半年报/季报分类
- [x] 修复 collect_news 配置 key 不匹配
- [x] 添加 URL 黑名单过滤
- [x] 重处理已损坏条目的日期
- [x] 删除明显垃圾条目
- **Status:** complete

### Phase 2: 重建数据管道 — 三层架构
- [x] 新建 build_extracts.py (PDF→完整MD)
- [x] 新建 tag_segments.py (MD→标签化分段)
- [x] 适配 ingest_v2 支持 --source=segments
- [x] 接入 scheduler 管道
- **Status:** complete

### Phase 3: 交付用户价值
- [x] 压缩超大 wiki 页面
- [x] LLM 投资判断
- [x] 补全综合评估
- [x] 新闻采集均衡化
- **Status:** complete

### Phase 4: 构建反馈闭环
- [x] 矛盾→标记→审核链路
- [x] lint→自动修复链路
- [x] state_store 写入端
- [x] 废弃无价值模块（删除5文件）
- [x] 关键路径测试（19个pipeline测试）
- **Status:** complete

### Phase 5: 全面架构与代码质量审查
- [x] 架构审查（依赖/耦合/职责）
- [x] P0 问题修复（预算熔断/静默失败/句柄泄漏/原子写入）
- [x] LSP 类型错误修复
- [x] 未使用导入清理
- **Status:** complete

### Phase 6: 架构债务清理与公共模块提取
- [x] 提取公共代码到 scripts/common.py（路径/配置/原子写入/UTF-8修复）
- [x] 清理孤儿模块（utils.py, logger.py, question_matcher.py → archive/）
- [x] 添加网络请求重试机制（collect_news.py，3次指数退避）
- [x] 集中硬编码魔法值到 config.yaml（P2，后续迭代）
- [x] 渐进清理未使用导入（50+处，P2，后续迭代）
- **Status:** complete

### Phase 7: 数据质量闭环验证
- [x] 运行完整 pipeline 端到端验证（extract → tag → ingest 连通）
- [x] 检查新 ingest 数据质量（发现 IR 过度拆分 + 日期错误问题）
- [x] 验证矛盾检测准确性（修复年份误报 bug）
- [x] 验证链接修复完整性（36 死链删除）
- [x] 修复 IR 过度拆分（prompt 修改：一个文件一个条目）
- [x] 修复日期提取（支持 20220416 → 2022-04-16）
- [x] 修复 segment 日期（保存/读取 original_date）
- **Status:** complete

### Phase 7: 数据质量闭环验证
- [x] 运行完整 pipeline 端到端验证
- [x] 检查新 ingest 数据质量
- [x] 验证矛盾检测准确性
- [x] 验证链接修复完整性
- [x] 修复 IR 过度拆分和日期提取问题
- [x] 清理历史重复条目（31 个）
- **Status:** complete

### Phase 8: 最终系统验证与报告
- [x] 运行 scheduler dry-run 验证完整工作流
- [x] 生成系统状态报告（233 公司, 345 wiki 页面, 25 行业）
- [x] 检查 companies.yaml 与 graph.yaml 一致性（通过）
- [x] 验证所有 wiki frontmatter 规范（修复 3 个缺失 last_updated）
- **Status:** complete
- **已知遗留问题:**
  - 211 个 wiki 页面缺少综合评估（61%）
  - ~90% wiki 缺少 sources_count frontmatter 字段
  - 新闻采集极度倾斜（7天内仅北方华创有采集）
  - 矛盾检测阈值过宽（200 条低质量矛盾）

### Phase 9: 数据填充与质量提升（建议下一步）
- [ ] 批量补全缺失的综合评估（211 个页面，需 LLM 调用，考虑成本）
- [ ] 补全 wiki frontmatter 的 sources_count 字段
- [ ] 优化新闻采集均衡化（扩大关键词库，按行业轮询）
- [ ] 调整矛盾检测阈值（增加硬性矛盾检测）
- [ ] 提交 Phase 1-8 全部变更到 git
- **Status:** pending

## Key Questions

1. 是否需要保留所有 233 家公司的跟踪？（当前新闻采集极度倾斜）
2. 如何平衡 API 成本与数据覆盖？（tag_segments 消耗大量 tokens）
3. 是否需要更严格的数据来源验证？（中微公司/中微半导体混淆问题）

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| 三层数据架构（PDF→MD→Segments→Wiki） | 解决信息不可重处理、不可验证的问题 |
| 删除 event_bus/job_queue/repair_planner/closed_loop_dashboard | 零订阅者/消费者/调用者，50%完成度代码 |
| 不新建 Controller/DecisionMaker/Executor | 重复之前加模块失败的模式；闭环逻辑集成在 scheduler 内 |
| 提取 common.py 公共模块 | 25+ 文件重复定义路径/配置/原子写入/UTF-8修复 |
| 保留 consolidate.py 和 state_store.py | 质量可接受，接入即可工作 |
| 使用 negative_keywords 防止名字歧义 | 京东/京东方、中微公司/中微半导体等子串冲突 |

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| PDF 句柄泄漏 | 1 | 改用 `with fitz.open(...)` 上下文管理器 |
| 预算熔断失效 | 1 | 成本日志读取异常改为打印 WARN |
| 调度器 9 处静默失败 | 1 | `except Exception: pass` → `except Exception as e: print(...)` |
| tag_segments.py 未加载 .env | 1 | 添加 `load_dotenv()` |
| tag_segments.py 路径处理崩溃 | 1 | 统一使用 `.resolve()` |
| JSON 截断解析失败 | 1 | 添加 `_extract_json_objects` 提取部分对象 |

## Notes
- 每次修改后必须运行完整测试套件（175 tests）
- 优先修复影响数据质量的 P0 问题
- 公共模块提取时要保持向后兼容
- Windows UTF-8 `reconfigure` 是 Python 3.7+ 特性，LSP 误报但运行时安全
