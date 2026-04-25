# Findings & Decisions

## Requirements

- 系统性修复上市公司知识库的数据质量问题和架构债务
- 建立三层数据管道（PDF→MD→Segments→Wiki）
- 防止名字歧义导致的数据污染
- 提升代码健壮性和可维护性

## Research Findings

### 架构审查结果
- **循环依赖**: 未发现
- **孤儿模块**: 5 个纯工具库无人使用（utils.py, logger.py, question_matcher.py, config_loader.py, models/__init__.py）
- **过度耦合**: graph.py (20次), llm_client.py (16次) — 核心基础设施，符合预期
- **职责混合**: ingest_v2.py 混合 CLI 入口与库代码

### 代码质量问题
- **代码重复**: 25+ 文件重复定义 SCRIPTS_DIR/WIKI_ROOT/UTF-8修复/原子写入
- **硬编码魔法值**: API URL、超时、预算阈值分散在 20+ 文件中
- **未使用导入**: 50+ 处
- **异常处理漏洞**: 30+ 处 `except Exception: pass` 静默吞掉错误
- **资源泄漏**: PDF 句柄未使用 with 语句（已修复）

### 数据质量问题
- **名字歧义**: 中微公司(688012) vs 中微半导体(MCU芯片)，aliases 包含歧义名称
- **京东/京东方**: 子串匹配导致误关联
- **新闻采集倾斜**: 7天内仅北方华创19篇，其余232家零采集
- **时间线单一**: 59条近期条目全部来自同一个 IR 纪要文件

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| 三层数据架构 | 解决信息不可重处理、不可验证的问题；支持增量更新 |
| 删除 5 个死模块 | 零调用，50%完成度代码，增加维护负担 |
| 提取 common.py | 25+ 文件重复定义路径/配置/原子写入/UTF-8修复 |
| negative_keywords 防歧义 | 无需修改采集逻辑，在 ingest 阶段过滤 |
| 保留 consolidate.py | 已接入 scheduler，archive-only 模式可无 LLM 运行 |
| 保留 state_store.py | 已接入 collect_news 和 scheduler，记录时间戳 |

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| tag_segments.py 未加载 .env | 添加 `load_dotenv()` 调用 |
| tag_segments.py 路径处理崩溃 | 统一使用 `.resolve()` 处理相对/绝对路径 |
| JSON 截断解析失败 | 添加 `_extract_json_objects` 提取部分有效对象 |
| 调度器超时（大文件优先） | 按文件大小排序（小文件优先） |
| 中微公司/中微半导体混淆 | 删除歧义别名 + 添加 negative_keywords |

## Resources

- 项目根目录: C:\Users\郑曾波\Projects\company-wiki
- 核心脚本: scripts/scheduler.py, scripts/ingest_v2.py, scripts/llm_client.py
- 配置: config.yaml, companies.yaml, graph.yaml
- 测试: tests/unit/, tests/e2e/
- 数据: companies/{name}/raw/, companies/{name}/wiki/

## Visual/Browser Findings

- 中微公司 wiki 显示 59 条近期条目全部来自同一个 IR 纪要文件（来源单一）
- 34 条新闻中 13 条属于中微半导体（MCU芯片公司），非中微公司（688012）
- fix_broken_links.py 修复 77 个链接，删除 92 个死链
