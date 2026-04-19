# 差距改进计划

> 基于 Karpathy LLM Wiki 对比分析
> 创建日期: 2026-04-17

## 差距清单

### 1. Query 答案存回 (高优先级)
**Karpathy**: "good answers can be filed back into the wiki as new pages"
**现状**: 查询结果不会自动存回 wiki
**目标**: 用户问了好问题，答案自动存回 wiki

### 2. 矛盾检测 (中优先级)
**Karpathy**: "noting where new data contradicts old claims"
**现状**: 基础实现，只能检测过时页面
**目标**: 检测不同页面之间的矛盾陈述

### 3. 源发现建议 (低优先级)
**Karpathy**: "new sources to look for"
**现状**: 未实现
**目标**: 根据知识缺口建议新的数据来源

---

## 实施步骤

### Phase 1: Query 答案存回 ✅ 完成

#### 1.1 创建 Query 模块
- ✅ 创建 `scripts/query.py`
- ✅ 实现 wiki 搜索功能
- ✅ 实现答案综合功能
- ✅ 实现答案存回功能

#### 1.2 创建测试
- ✅ `tests/unit/test_query.py` (14个测试通过)

#### 1.3 集成到现有系统
- ✅ 添加 CLI 命令
- ✅ 自动保存答案到 wiki

### Phase 2: 矛盾检测增强 ✅ 完成

#### 2.1 创建矛盾检测模块
- ✅ 创建 `scripts/contradiction_detector.py`
- ✅ 实现数值矛盾检测
- ✅ 实现时间矛盾检测
- ✅ 实现分类矛盾检测

#### 2.2 创建测试
- ✅ `tests/unit/test_contradiction_detector.py` (9个测试通过)

#### 2.3 功能
- ✅ 生成矛盾报告
- ✅ 支持 --report 参数

### Phase 3: 源发现建议 ✅ 完成

#### 3.1 创建源发现模块
- ✅ 创建 `scripts/source_discoverer.py`
- ✅ 实现知识缺口分析
- ✅ 实现来源建议生成

#### 3.2 创建测试
- ✅ `tests/unit/test_source_discoverer.py` (10个测试通过)

#### 3.3 功能
- ✅ 检查缺失页面
- ✅ 检查空时间线
- ✅ 检查过时页面
- ✅ 检查未回答问题
- ✅ 生成来源建议报告